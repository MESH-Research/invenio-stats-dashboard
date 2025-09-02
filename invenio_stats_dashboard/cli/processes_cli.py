#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

import click

from ..utils.process_manager import (
    ProcessManager,
    ProcessMonitor,
    list_running_processes,
)


@click.group(name="processes")
def processes_cli():
    """Process management commands."""
    pass


@processes_cli.command(name="status")
@click.argument("process_name", default="event-migration")
@click.option(
    "--show-log",
    is_flag=True,
    help="Show recent log output from the process.",
)
@click.option(
    "--log-lines",
    type=int,
    default=20,
    help="Number of log lines to show (default: 20).",
)
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory containing PID and status files.",
)
def process_status_command(process_name, show_log, log_lines, pid_dir):
    """Show the status of a background process."""
    monitor = ProcessMonitor(process_name, pid_dir)
    monitor.show_status(show_log=show_log, log_lines=log_lines)


@processes_cli.command(name="cancel")
@click.argument("process_name", default="event-migration")
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Seconds to wait for graceful shutdown before force kill.",
)
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory containing PID and status files.",
)
def cancel_process_command(process_name, timeout, pid_dir):
    """Cancel a running background process."""
    process_manager = ProcessManager(process_name, pid_dir)

    if process_manager.cancel_process(timeout=timeout):
        click.echo(f"✅ Process '{process_name}' cancelled successfully")
    else:
        click.echo(f"❌ Failed to cancel process '{process_name}'")
        return 1


@processes_cli.command(name="list")
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory containing PID files.",
)
@click.option(
    "--package-only",
    is_flag=True,
    help="Only show processes managed by invenio-stats-dashboard.",
)
def list_processes_command(pid_dir, package_only):
    """List running background processes."""
    # Filter to only show invenio-stats-dashboard processes if requested
    package_prefix = "invenio-community-stats" if package_only else None
    running_processes = list_running_processes(pid_dir, package_prefix)

    if not running_processes:
        if package_only:
            click.echo(
                "No invenio-stats-dashboard background processes "
                "are currently running"
            )
        else:
            click.echo("No background processes are currently running")
        return

    if package_only:
        click.echo("Running invenio-stats-dashboard Background Processes:")
    else:
        click.echo("Running Background Processes:")
    click.echo("=" * 40)

    for process_name in running_processes:
        click.echo(f"• {process_name}")

    click.echo(f"\nTotal: {len(running_processes)} process(es)")
    click.echo(
        "\nUse 'invenio community-stats processes status <process_name>' "
        "to check status"
    )
    click.echo(
        "Use 'invenio community-stats processes cancel <process_name>' "
        "to stop a process"
    )
