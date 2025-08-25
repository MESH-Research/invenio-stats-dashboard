#!/usr/bin/env python3
"""
Demo script showing how to use the process management utilities.

This script demonstrates how to start, monitor, and cancel background processes
using the ProcessManager and ProcessMonitor classes.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import the utils
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from invenio_stats_dashboard.utils.process_manager import (
        ProcessManager,
        ProcessMonitor,
        list_running_processes,
    )
except ImportError:
    print("❌ Could not import process management utilities")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)


def demo_background_process():
    """Demonstrate starting and managing a background process."""

    print("🚀 Process Management Demo")
    print("=" * 50)

    # Create a process manager
    process_manager = ProcessManager(
        "demo-process", "/tmp", package_prefix="invenio-community-stats"
    )

    # Check if process is already running
    if process_manager.is_running():
        print("⚠️  Demo process is already running, cleaning up...")
        process_manager.cancel_process()
        time.sleep(1)

    # Start a simple background process (sleep for 60 seconds)
    print("📝 Starting demo background process...")
    try:
        pid = process_manager.start_background_process(
            ["sleep", "60"], stdout=open("/tmp/demo-process.log", "w")
        )
        print(f"✅ Started process with PID: {pid}")

        # Update status with some progress
        process_manager.update_status(
            {"progress": 10, "current_task": "Demo task in progress..."}
        )

        # Wait a bit and show status
        print("\n⏳ Waiting 3 seconds...")
        time.sleep(3)

        # Show process status
        print("\n📊 Current Process Status:")
        monitor = ProcessMonitor(
            "demo-process", "/tmp", package_prefix="invenio-community-stats"
        )
        monitor.show_status(show_log=True, log_lines=5)

        # Update progress
        process_manager.update_status(
            {"progress": 50, "current_task": "Halfway through demo..."}
        )

        print("\n⏳ Waiting another 3 seconds...")
        time.sleep(3)

        # Show updated status
        print("\n📊 Updated Process Status:")
        monitor.show_status(show_log=True, log_lines=5)

        # Cancel the process
        print("\n🛑 Cancelling demo process...")
        if process_manager.cancel_process(timeout=5):
            print("✅ Process cancelled successfully")
        else:
            print("❌ Failed to cancel process")

        # Show final status
        print("\n📊 Final Status:")
        monitor.show_status()

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True


def demo_process_listing():
    """Demonstrate listing running processes."""

    print("\n📋 Process Listing Demo")
    print("=" * 50)

    # List all running processes
    running_processes = list_running_processes("/tmp")

    if running_processes:
        print(f"🔄 Found {len(running_processes)} running process(es):")
        for process_name in running_processes:
            print(f"  • {process_name}")

            # Show status for each
            monitor = ProcessMonitor(
                process_name, "/tmp", package_prefix="invenio-community-stats"
            )
            monitor.show_status()
            print()
    else:
        print("📭 No background processes are currently running")


def demo_status_monitoring():
    """Demonstrate monitoring a specific process."""

    print("\n👀 Status Monitoring Demo")
    print("=" * 50)

    process_name = "demo-process"
    monitor = ProcessMonitor(
        process_name, "/tmp", package_prefix="invenio-community-stats"
    )

    # Check if process exists
    if monitor._pid_file.exists():
        print(f"📊 Monitoring process: {process_name}")
        monitor.show_status(show_log=True, log_lines=10)
    else:
        print(f"❌ Process '{process_name}' not found")


if __name__ == "__main__":
    print("🎯 Process Management Utilities Demo")
    print("This demo will show how to use the process management features.")
    print()

    try:
        # Run the demos
        if demo_background_process():
            print("\n✅ Demo completed successfully!")
        else:
            print("\n❌ Demo failed!")

        demo_process_listing()
        demo_status_monitoring()

    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

    print("\n🎉 Demo finished!")
    print("\n💡 Try running these commands manually:")
    print("  invenio community-stats migrate-events-background --max-batches 5")
    print("  invenio community-stats process-status event-migration")
    print("  invenio community-stats cancel-process event-migration")
