# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Process management utilities for long-running CLI commands."""

import atexit
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import click
import psutil
from flask import current_app


class ProcessManager:
    """Manages background processes with PID files and status tracking."""

    def __init__(
        self,
        process_name: str,
        pid_dir: str | None = None,
        package_prefix: str = "invenio-community-stats",
    ):
        """Initialize process manager.

        Args:
            process_name: Name of the process (used for PID file naming)
            pid_dir: Directory to store PID files (defaults to /tmp)
            package_prefix: Prefix for all processes managed by this package
        """
        self.process_name = process_name
        self.pid_dir = Path(pid_dir or "/tmp")
        self.package_prefix = package_prefix

        # Use package prefix in process naming
        self.full_process_name = f"{package_prefix}-{process_name}"
        self.pid_file = self.pid_dir / f"{self.full_process_name}.pid"
        self.status_file = self.pid_dir / f"{self.full_process_name}.status"
        self.log_file = self.pid_dir / f"{self.full_process_name}.log"

        # Ensure PID directory exists
        self.pid_dir.mkdir(parents=True, exist_ok=True)

        # Register cleanup on exit
        atexit.register(self.cleanup)

    def start_background_process(self, cmd: list, **kwargs) -> int:
        """Start a process in the background.

        Args:
            cmd: Command to execute as a list
            **kwargs: Additional arguments for subprocess.Popen

        Returns:
            Process ID of the started process

        Raises:
            RuntimeError: If process is already running
        """
        if self.is_running():
            raise RuntimeError(
                f"Process {self.process_name} is already running "
                f"(PID: {self.get_pid()})"
            )

        # Start process in background
        process = subprocess.Popen(
            cmd, stdout=open(self.log_file, "w"), stderr=subprocess.STDOUT, **kwargs
        )

        pid = process.pid

        # Write PID file
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(pid))
        except Exception as e:
            current_app.logger.error(f"Failed to create PID file {self.pid_file}: {e}")
            click.echo(f"Warning: Failed to create PID file: {e}")
            # Don't fail the entire operation, but warn the user

        # Write initial status
        self.update_status(
            {
                "pid": pid,
                "start_time": time.time(),
                "status": "running",
                "command": " ".join(cmd),
                "progress": 0,
                "current_task": "Starting...",
            }
        )

        # Best-effort: if PID file is missing (e.g., due to permissions race), try again
        if not self.pid_file.exists():
            try:
                with open(self.pid_file, "w") as f:
                    f.write(str(pid))
            except Exception:
                pass

        click.echo(f"Started {self.process_name} in background (PID: {pid})")
        click.echo(f"PID file: {self.pid_file}")
        click.echo(f"Log file: {self.log_file}")
        click.echo(f"Status file: {self.status_file}")
        click.echo(
            f"Use 'invenio community-stats process-status {self.process_name}' "
            "to monitor progress"
        )
        click.echo(
            f"Use 'invenio community-stats cancel-process {self.process_name}' "
            "to stop the process"
        )

        return pid

    def is_running(self) -> bool:
        """Check if the process is currently running.

        Falls back to the status file if the PID file is missing.
        """
        pid: int | None = None

        # Primary source: PID file
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
            except (ValueError, FileNotFoundError):
                pid = None

        # Fallback: status file
        if pid is None:
            status = self.get_status() or {}
            raw_pid = status.get("pid") if isinstance(status, dict) else None
            try:
                pid = int(raw_pid) if raw_pid is not None else None
            except (TypeError, ValueError):
                pid = None

        if pid is None:
            # No way to determine running state
            return False

        # Check if process exists and is running
        if not psutil.pid_exists(pid):
            self.cleanup()
            return False

        try:
            process = psutil.Process(pid)
            running = bool(process.is_running())
        except psutil.NoSuchProcess:
            running = False

        if running and not self.pid_file.exists():
            # Recreate missing PID file for stability
            try:
                with open(self.pid_file, "w") as f:
                    f.write(str(pid))
            except Exception:
                pass

        if not running:
            self.cleanup()
        return running

    def get_pid(self) -> int | None:
        """Get the PID of the running process."""
        # Try PID file first
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    return int(f.read().strip())
            except (ValueError, FileNotFoundError):
                pass

        # Fallback to status file
        status = self.get_status() or {}
        raw_pid = status.get("pid") if isinstance(status, dict) else None
        try:
            return int(raw_pid) if raw_pid is not None else None
        except (TypeError, ValueError):
            return None

    def get_status(self) -> dict[str, Any] | None:
        """Get the current status of the process."""
        if not self.status_file.exists():
            return None

        try:
            with open(self.status_file) as f:
                result = json.load(f)
                return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def update_status(self, status_update: dict[str, Any]):
        """Update the process status."""
        current_status = self.get_status() or {}
        current_status.update(status_update)
        current_status["last_update"] = time.time()

        with open(self.status_file, "w") as f:
            json.dump(current_status, f, indent=2)

    def cancel_process(self, timeout: int = 30) -> bool:
        """Cancel the running process gracefully.

        Args:
            timeout: Seconds to wait for graceful shutdown before force kill

        Returns:
            True if process was successfully cancelled, False otherwise
        """
        if not self.is_running():
            click.echo(f"❌ Process {self.process_name} is not running")
            return False

        pid = self.get_pid()
        if not pid:
            click.echo(f"❌ Could not determine PID for {self.process_name}")
            return False

        try:
            process = psutil.Process(pid)

            # Send SIGTERM for graceful shutdown
            click.echo(f"🔄 Sending SIGTERM to process {pid}...")
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
                click.echo(f"✅ Process {pid} terminated gracefully")
                self.cleanup()
                return True
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown fails
                click.echo(
                    f"⚠️  Graceful shutdown failed, force killing process {pid}..."
                )
                process.kill()
                process.wait()
                click.echo(f"✅ Process {pid} force killed")
                self.cleanup()
                return True

        except psutil.NoSuchProcess:
            click.echo(f"❌ Process {pid} no longer exists")
            self.cleanup()
            return False
        except Exception as e:
            click.echo(f"❌ Error cancelling process: {e}")
            return False

    def cleanup(self):
        """Clean up PID and status files.

        Skips deletion if the background process still appears to be running,
        based on either the PID file or the status file.
        """
        try:
            pid = self.get_pid()
            if pid and psutil.pid_exists(pid):
                return

            if self.pid_file.exists():
                self.pid_file.unlink()
            if self.status_file.exists():
                self.status_file.unlink()
        except OSError:
            pass  # Ignore cleanup errors

    def get_log_tail(self, lines: int = 50) -> str:
        """Get the last N lines of the process log."""
        if not self.log_file.exists():
            return "No log file found"

        try:
            with open(self.log_file) as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading log file: {e}"


class ProcessMonitor:
    """Monitors and displays process status."""

    def __init__(
        self,
        process_name: str,
        pid_dir: str | None = None,
        package_prefix: str = "invenio-community-stats",
    ):
        """Initialize process monitor.

        Args:
            process_name: Name of the process to monitor
            pid_dir: Directory containing PID files
            package_prefix: Prefix for all processes managed by this package
        """
        self.process_name = process_name
        self.pid_dir = Path(pid_dir or "/tmp")
        self.package_prefix = package_prefix

        # Use package prefix in process naming
        self.full_process_name = f"{package_prefix}-{process_name}"
        self.pid_file = self.pid_dir / f"{self.full_process_name}.pid"
        self.status_file = self.pid_dir / f"{self.full_process_name}.status"
        self.log_file = self.pid_dir / f"{self.full_process_name}.log"

    def show_status(self, show_log: bool = False, log_lines: int = 20):
        """Display the current process status."""
        status = self._get_status()
        # Try to determine PID from pidfile first, then status
        pid: int | None = None
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
            except (ValueError, FileNotFoundError):
                pid = None
        if pid is None and isinstance(status, dict):
            raw_pid = status.get("pid")
            try:
                pid = int(raw_pid) if raw_pid is not None else None
            except (TypeError, ValueError):
                pid = None

        if status is None and pid is None:
            click.echo(f"❌ Process {self.process_name} is not running")
            return

        # Display status information
        click.echo(f"📊 Process Status: {self.process_name}")
        click.echo("=" * 50)
        if isinstance(status, dict):
            click.echo(f"PID: {status.get('pid', 'Unknown')}")
            click.echo(f"Status: {status.get('status', 'Unknown')}")

            if "start_time" in status:
                try:
                    start_time = time.time() - float(status["start_time"])  # type: ignore[arg-type]
                    hours = int(start_time // 3600)
                    minutes = int((start_time % 3600) // 60)
                    seconds = int(start_time % 60)
                    click.echo(f"Runtime: {hours:02d}:{minutes:02d}:{seconds:02d}")
                except Exception:
                    pass

            if "progress" in status:
                try:
                    progress = float(status["progress"])  # type: ignore[index]
                    progress_bar = (
                        "█" * int(progress / 2) + "░" * (50 - int(progress / 2))
                    )
                    click.echo(f"Progress: [{progress_bar}] {progress:.1f}%")
                except Exception:
                    pass

            if "current_task" in status:
                try:
                    click.echo(f"Current Task: {status['current_task']}")
                except Exception:
                    pass

            if "command" in status:
                try:
                    click.echo(f"Command: {status['command']}")
                except Exception:
                    pass
        else:
            click.echo("No status file found")

        # Check if process is actually running
        if self._is_process_running():
            click.echo("🟢 Process is running")
        else:
            click.echo("🔴 Process is not running (stale PID file)")

        # Show log tail if requested
        if show_log:
            click.echo("\n📝 Recent Log Output:")
            click.echo("-" * 50)
            log_tail = self._get_log_tail(log_lines)
            click.echo(log_tail)

    def _get_status(self) -> dict[str, Any] | None:
        """Get the process status."""
        if not self.status_file.exists():
            return None

        try:
            with open(self.status_file) as f:
                result = json.load(f)
                return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _is_process_running(self) -> bool:
        """Check if the process is actually running.

        Falls back to the status file if the PID file is missing.
        """
        pid: int | None = None

        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
            except (ValueError, FileNotFoundError):
                pid = None

        if pid is None:
            status = self._get_status() or {}
            raw_pid = status.get("pid") if isinstance(status, dict) else None
            try:
                pid = int(raw_pid) if raw_pid is not None else None
            except (TypeError, ValueError):
                pid = None

        if pid is None:
            return False

        if not psutil.pid_exists(pid):
            return False

        try:
            process = psutil.Process(pid)
            return bool(process.is_running())
        except psutil.NoSuchProcess:
            return False

    def _get_log_tail(self, lines: int) -> str:
        """Get the last N lines of the log."""
        if not self.log_file.exists():
            return "No log file found"

        try:
            with open(self.log_file) as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading log file: {e}"


def list_running_processes(
    pid_dir: str | None = None, package_prefix: str | None = None
) -> list:
    """List running processes managed by ProcessManager.

    Args:
        pid_dir: Directory containing PID files
        package_prefix: Optional prefix to filter processes
            (e.g., 'invenio-community-stats')

    Returns:
        List of running process names
    """
    pid_path = Path(pid_dir or "/tmp")
    running_processes: list[str] = []

    if not pid_path.exists():
        return running_processes

    for pid_file in pid_path.glob("*.pid"):
        full_process_name = pid_file.stem

        # Filter by package prefix if specified
        if package_prefix and not full_process_name.startswith(package_prefix):
            continue

        # Extract the short process name by removing the package prefix
        if package_prefix and full_process_name.startswith(package_prefix + "-"):
            short_process_name = full_process_name[
                len(package_prefix) + 1 :
            ]  # +1 for the dash
        else:
            # If no package prefix specified, use the full name
            short_process_name = full_process_name

        monitor = ProcessMonitor(
            short_process_name, pid_dir, package_prefix or "invenio-community-stats"
        )

        if monitor._is_process_running():
            running_processes.append(full_process_name)

    return running_processes
