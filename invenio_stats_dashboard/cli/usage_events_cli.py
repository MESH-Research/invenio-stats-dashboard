# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2025 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Usage events CLI commands for generating and managing usage statistics events."""

import arrow
import click
from flask.cli import with_appcontext
from halo import Halo

from ..proxies import current_event_reindexing_service
from ..tasks import reindex_usage_events_with_metadata
from ..utils.process_manager import ProcessManager
from ..utils.usage_events import UsageEventFactory
from .core_cli import check_stats_enabled


@click.group(name="usage-events")
def usage_events_cli():
    """Usage events commands."""
    pass


@usage_events_cli.command(name="generate")
@click.option(
    "--start-date",
    type=str,
    help="Start date for filtering records by creation date (YYYY-MM-DD). "
    "If not provided, uses earliest record creation date.",
)
@click.option(
    "--end-date",
    type=str,
    help="End date for filtering records by creation date (YYYY-MM-DD). "
    "If not provided, uses current date.",
)
@click.option(
    "--event-start-date",
    type=str,
    help="Start date for event timestamps (YYYY-MM-DD). "
    "If not provided, uses start-date.",
)
@click.option(
    "--event-end-date",
    type=str,
    help="End date for event timestamps (YYYY-MM-DD). "
    "If not provided, uses end-date.",
)
@click.option(
    "--events-per-record",
    type=int,
    default=5,
    help="Number of events to generate per record (default: 5).",
)
@click.option(
    "--max-records",
    type=int,
    default=0,
    help="Maximum number of records to process (default: 0 = all records).",
)
@click.option(
    "--enrich-events",
    is_flag=True,
    help="Enrich events with additional data matching extended fields.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Generate events but don't index them.",
)
@click.option(
    "--yes-i-know",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@click.option(
    "--use-migrated-indices",
    is_flag=True,
    help="Use migrated indices with -v2.0.0 suffix when they exist.",
)
@with_appcontext
def generate_usage_events_command(
    start_date,
    end_date,
    event_start_date,
    event_end_date,
    events_per_record,
    max_records,
    enrich_events,
    dry_run,
    yes_i_know,
    use_migrated_indices,
):
    """Generate synthetic usage events (view/download) for testing purposes.

    This command creates synthetic view and download events for testing the
    statistics system. It generates events with configurable parameters and
    can enrich them with additional metadata fields.


    Examples:

    \b
    - invenio community-stats usage-events generate
    - invenio community-stats usage-events generate --events-per-record 10
    - invenio community-stats usage-events generate --dry-run
    - invenio community-stats usage-events generate --max-records 100 --enrich-events

    Warning:
    This will generate synthetic usage events in your search indices. These
    events are intended for testing purposes only and cannot be easily removed
    without deleting the indices and losing any genuine usage events.
    """
    check_stats_enabled()

    # Show configuration and ask for confirmation
    click.echo("Configuration for usage event generation:")
    click.echo(f"  • Events per record: {events_per_record}")
    if max_records > 0:
        click.echo(f"  • Max records to process: {max_records}")
    else:
        click.echo("  • Max records to process: ALL records")
    if start_date:
        click.echo(f"  • Record creation start date: {start_date}")
    if end_date:
        click.echo(f"  • Record creation end date: {end_date}")
    if event_start_date:
        click.echo(f"  • Event timestamp start date: {event_start_date}")
    if event_end_date:
        click.echo(f"  • Event timestamp end date: {event_end_date}")
    click.echo(f"  • Enrich events: {'Yes' if enrich_events else 'No'}")
    click.echo(f"  • Use migrated indices: {'Yes' if use_migrated_indices else 'No'}")
    click.echo(f"  • Dry run mode: {'Yes' if dry_run else 'No'}")

    # Ask for confirmation unless --yes-i-know is specified
    if not yes_i_know:
        if not click.confirm(
            "\nWARNING: This will generate synthetic usage events in "
            "your search indices for view and download events. It is "
            "intended for testing purposes only. YOU WILL NOT BE ABLE TO "
            "REMOVE THEM WITHOUT DELETING THE INDICES AND LOSING ANY "
            "GENUINE USAGE EVENTS."
            "Are you sure you want to continue?"
        ):
            click.echo("Operation cancelled by user.")
            return

    click.echo("\nStarting usage event generation...")

    try:
        factory = UsageEventFactory()

        if dry_run:
            click.echo("\n📊 Generating events (dry run)...")
            events = factory.generate_repository_events(
                start_date=start_date or "",
                end_date=end_date or "",
                events_per_record=events_per_record,
                max_records=max_records,
                enrich_events=enrich_events,
                event_start_date=event_start_date or "",
                event_end_date=event_end_date or "",
            )

            total_events = len(events)
            click.echo("✅ Dry run completed successfully!")
            click.echo(f"Generated {total_events} events")
            click.echo("No events were indexed (dry run mode)")
        else:
            click.echo("\n📊 Generating and indexing events...")
            result = factory.generate_and_index_repository_events(
                start_date=start_date or "",
                end_date=end_date or "",
                events_per_record=events_per_record,
                max_records=max_records,
                enrich_events=enrich_events,
                event_start_date=event_start_date or "",
                event_end_date=event_end_date or "",
                use_migrated_indices=use_migrated_indices,
            )

            click.echo("✅ Usage event generation completed successfully!")
            click.echo(f"Indexed: {result.get('indexed', 0)} events")
            if result.get("errors", 0) > 0:
                click.echo(f"Errors: {result.get('errors', 0)} events")

    except Exception as e:
        click.echo(f"❌ Error generating usage events: {e}")
        raise


@usage_events_cli.command(name="generate-background")
@click.option(
    "--start-date",
    type=str,
    help="Start date for filtering records by creation date (YYYY-MM-DD). "
    "If not provided, uses earliest record creation date.",
)
@click.option(
    "--end-date",
    type=str,
    help="End date for filtering records by creation date (YYYY-MM-DD). "
    "If not provided, uses current date.",
)
@click.option(
    "--event-start-date",
    type=str,
    help="Start date for event timestamps (YYYY-MM-DD). "
    "If not provided, uses start-date.",
)
@click.option(
    "--event-end-date",
    type=str,
    help="End date for event timestamps (YYYY-MM-DD). "
    "If not provided, uses end-date.",
)
@click.option(
    "--events-per-record",
    type=int,
    default=5,
    help="Number of events to generate per record (default: 5).",
)
@click.option(
    "--max-records",
    type=int,
    default=0,
    help="Maximum number of records to process (default: 0 = all records).",
)
@click.option(
    "--enrich-events",
    is_flag=True,
    help="Enrich events with additional data matching extended fields.",
)
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory to store PID and status files.",
)
@click.option(
    "--yes-i-know",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@with_appcontext
def generate_usage_events_background_command(
    start_date,
    end_date,
    event_start_date,
    event_end_date,
    events_per_record,
    max_records,
    enrich_events,
    pid_dir,
    yes_i_know,
):
    """Start usage event generation in the background with process management.

    This command provides the same functionality as `usage-events generate` but runs
    in the background with full process management capabilities. It allows you to
    start long-running usage event generation processes without blocking the terminal.

    WARNING:

    This will generate synthetic usage events in your search indices. These
    events are intended for testing purposes only and cannot be easily removed
    without deleting the indices and losing any genuine usage events.

    Examples:

    \b
    - invenio community-stats usage-events generate-background
    - invenio community-stats usage-events generate-background --events-per-record 10
    - invenio community-stats usage-events generate-background --enrich-events
    - invenio community-stats usage-events generate-background --pid-dir /var/run/invenio-community-stats

    Process management:

    \b
    - Monitor progress: invenio community-stats processes status usage-event-generation
    - Cancel process: invenio community-stats processes cancel usage-event-generation
    - View logs: invenio community-stats processes status usage-event-generation --show-log

    """
    check_stats_enabled()

    if not yes_i_know:
        if not click.confirm(
            "\nWARNING: This will generate synthetic usage events in "
            "your search indices for view and download events. It is "
            "intended for testing purposes only. YOU WILL NOT BE ABLE TO "
            "REMOVE THEM WITHOUT DELETING THE INDICES AND LOSING ANY "
            "GENUINE USAGE EVENTS. "
            "Are you sure you want to continue?"
        ):
            click.echo("Operation cancelled by user.")
            return

    # Build the command to run
    cmd = [
        "invenio",
        "community-stats",
        "usage-events",
        "generate",
        "--events-per-record",
        str(events_per_record),
        "--yes-i-know",
    ]

    if start_date:
        cmd.extend(["--start-date", start_date])
    if end_date:
        cmd.extend(["--end-date", end_date])
    if event_start_date:
        cmd.extend(["--event-start-date", event_start_date])
    if event_end_date:
        cmd.extend(["--event-end-date", event_end_date])
    if max_records > 0:
        cmd.extend(["--max-records", str(max_records)])
    if enrich_events:
        cmd.append("--enrich-events")

    # Create process manager
    process_manager = ProcessManager(
        "usage-event-generation", pid_dir, package_prefix="invenio-community-stats"
    )

    try:
        pid = process_manager.start_background_process(cmd)
        click.echo("\nBackground usage event generation started successfully!")
        click.echo(f"Process ID: {pid}")
        click.echo(f"Command: {' '.join(cmd)}")

        click.echo("\nMonitor progress:")
        click.echo("  invenio community-stats processes status usage-event-generation")
        click.echo(
            "  invenio community-stats processes status usage-event-generation --show-log"
        )

        click.echo("\nCancel if needed:")
        click.echo("  invenio community-stats processes cancel usage-event-generation")

    except RuntimeError as e:
        click.echo(f"Failed to start background usage event generation: {e}")
        return 1

    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        return 1


def _report_validation_errors(validation_result):
    """Report validation errors in a consistent format.

    Args:
        validation_result: ValidationResult dictionary containing validation details
    """
    if not validation_result:
        return

    click.echo("    Validation Errors:")

    if validation_result.get("errors"):
        click.echo("      Validation errors:")
        errors = validation_result["errors"]
        for error in errors[:3]:  # Show first 3 errors
            click.echo(f"        - {error}")
        if len(errors) > 3:
            remaining = len(errors) - 3
            click.echo(f"        ... and {remaining} more errors")

    missing_ids = validation_result.get("missing_community_ids", 0)
    if missing_ids > 0:
        click.echo(f"      Missing community_ids: {missing_ids}")

    click.echo("    Retry commands:")
    click.echo(
        "      The bookmark has been automatically reset, so you can safely retry:"
    )
    # Note: We don't have event_type and month in the validation_result,
    # so we'll provide a generic retry command
    click.echo("        invenio community-stats usage-events migrate")


def _report_interrupted_migrations(interrupted_migrations):
    """Report interrupted migrations in a consistent format.

    Args:
        interrupted_migrations: List of interrupted migration dictionaries
    """
    if not interrupted_migrations:
        return

    click.echo("\n⚠️  INCOMPLETE MIGRATIONS:")

    # Group by reason
    interrupted = [
        m for m in interrupted_migrations if m.get("reason") == "interrupted"
    ]
    failed = [m for m in interrupted_migrations if m.get("reason") == "failed"]

    if interrupted:
        click.echo("\n⏸️  INTERRUPTED (can resume):")
        click.echo(
            "The following migrations were interrupted due to " "max_batches limit:"
        )
        for migration in interrupted:
            click.echo(
                f"  • {migration['event_type']} {migration['month']}: "
                f"{migration['processed']:,} events processed in "
                f"{migration['batches']} batches"
            )
            click.echo(f"    Last processed ID: {migration['last_processed_id']}")
            click.echo(f"    Source: {migration['source_index']}")
            click.echo(f"    Target: {migration['target_index']}")

    if failed:
        click.echo("\n❌ FAILED (needs investigation):")
        click.echo("The following migrations failed due to errors:")
        for migration in failed:
            click.echo(
                f"  • {migration['event_type']} {migration['month']}: "
                f"{migration['processed']:,} events processed in "
                f"{migration['batches']} batches"
            )
            click.echo(f"    Source: {migration['source_index']}")
            click.echo(f"    Target: {migration['target_index']}")

    if interrupted:
        click.echo("\n💡 To resume interrupted migrations:")
        click.echo("  1. Use the same command with --max-batches to continue")
        click.echo("  2. Or use 'migrate' command with the --months flag for ")
        click.echo("     specific months:")
        for migration in interrupted:
            click.echo(
                f"     invenio community-stats usage-events migrate "
                f"--event-types {migration['event_type']} "
                f"--months {migration['month']}"
            )

    if failed:
        click.echo("\n🔧 To retry failed migrations:")
        click.echo("  1. Check logs for error details")
        click.echo("  2. Fix the underlying issue")
        click.echo("  3. Run the migration again:")
        for migration in failed:
            click.echo(
                f"     invenio community-stats usage-events migrate "
                f"--event-types {migration['event_type']} "
                f"--months {migration['month']}"
            )


def _report_migration_results(results):
    """Report migration results in a consistent format.

    Args:
        results: Migration results dictionary with consistent structure
    """
    # Count completed, interrupted, and failed months
    completed_count = 0
    interrupted_count = 0
    failed_count = 0

    for event_results in results["event_types"].values():
        for month_results in event_results["months"].values():
            if month_results.get("completed", False):
                completed_count += 1
            elif month_results.get("interrupted", False):
                interrupted_count += 1
            else:
                failed_count += 1

    click.echo("=" * 50)
    click.echo("\nMigration Summary:")

    click.echo("\n\n")
    if results["completed"]:
        click.echo("All migrations completed successfully")
    elif failed_count > 0 and interrupted_count == 0 and completed_count == 0:
        click.echo("All migrations failed")
    else:
        if completed_count > 0:
            click.echo("Some migrations were completed")
        if interrupted_count > 0:
            click.echo("Some migrations were interrupted")
        if failed_count > 0:
            click.echo("Some migrations failed")

        if results.get("error"):
            click.echo("\nTop-level error:")
            click.echo(f"- {results['error']}")

        if results.get("health_issues"):
            click.echo("\nHealth issues:")
            for issue in results["health_issues"]:
                click.echo(f"  - {issue}")

    click.echo(f"  Processed: {results['total_processed']:,} total events")
    for event_type_name, event_results in results["event_types"].items():
        click.echo(f"  {event_type_name} events: {event_results['processed']:,}")
    click.echo(f"  Total errors: {results['total_errors']:,}")
    click.echo(f"\n  Completed: {completed_count:,} monthly indices")
    click.echo(f"  Interrupted: {interrupted_count:,} monthly indices")
    click.echo(f"  Failed: {failed_count:,} monthly indices")
    total_months = completed_count + interrupted_count + failed_count
    click.echo(f"  Total: {total_months:,} monthly indices")

    click.echo("\nResults for each month:")
    click.echo("=" * 50)

    for event_type, event_results in results["event_types"].items():
        click.echo(f"\n{event_type.upper()} Events")
        for month, month_results in event_results["months"].items():
            click.echo(f"\n{month}")
            click.echo(f"    Source Index: {month_results.get('source_index', 'N/A')}")
            click.echo(f"    Target Index: {month_results.get('target_index', 'N/A')}")
            # Show clearer migration counts
            processed = month_results.get("processed", 0)
            click.echo(f"    Attempted: {processed:,} events")

            # Show successful migration count if validation passed
            if not month_results.get("validation_errors"):
                click.echo(f"        Successfully migrated: {processed:,} events")
            else:
                # If validation failed, show the actual successful count
                validation_errors = month_results.get("validation_errors")
                if validation_errors and "document_counts" in validation_errors:
                    target_count = validation_errors["document_counts"].get("target", 0)
                    click.echo(
                        f"        Validated successfully: {target_count:,} events"
                    )
                    failed_count = processed - target_count
                    click.echo(f"        Failed validation: {failed_count:,} events")
                else:
                    click.echo("        Successfully migrated: 0 events")
                    click.echo(f"        Failed validation: {processed:,} events")
            click.echo(
                f"    Total Batches: {month_results.get('batches_succeeded', 0):,}"
            )
            click.echo(
                f"        Batches Attempted: {month_results.get('batches_attempted', 0):,}"
            )
            completed = month_results.get("completed")
            click.echo(
                f"    Migration Status: {'Completed' if completed else 'Incomplete'}"
            )
            interrupted = month_results.get("interrupted")
            if interrupted:
                click.echo("    Interrupted: Yes")
            click.echo(
                f"    Last Processed ID: "
                f"{month_results.get('last_processed_id', 'N/A')}"
            )

            if month_results.get("total_time"):
                click.echo(f"    Migration took: {month_results['total_time']}")

            if month_results.get("validation_errors"):
                _report_validation_errors(month_results["validation_errors"])

            if month_results.get("operational_errors"):
                click.echo(
                    f"    Operational Errors: {month_results['operational_errors']}"
                )
                for op_error in month_results["operational_errors"]:
                    click.echo(f"      - {op_error['type']}: " f"{op_error['message']}")

            if month_results.get("completed"):
                click.echo("    Status: ✅ Completed successfully")
            elif month_results.get("interrupted"):
                click.echo("    Status: ⏸️ Interrupted (can resume)")
            else:
                click.echo("    Status: ❌ Failed")

    if interrupted_count > 0 or failed_count > 0:
        click.echo("\n" + "=" * 50)
        click.echo("MIGRATIONS NEEDING ATTENTION:")

        if interrupted_count > 0:
            click.echo(
                f"\n⏸️  {interrupted_count:,} migration(s) were interrupted or unfinished "
                f"and can be resumed:"
            )
            click.echo("   • The bookmark system automatically tracks progress")
            click.echo("   • Resume with the same command (bookmarks are preserved)")

        if failed_count > 0:
            click.echo(
                f"\n❌  {failed_count:,} migration(s) failed and need attention:"
            )
            click.echo("   • Check logs for detailed error information")
            click.echo(
                "   • Failed migrations automatically reset bookmarks for safety"
            )
            click.echo("   • You can safely retry with the same command and migrated ")
            click.echo("     documents will be repaired as necessary.")

    click.echo("\n" + "=" * 50)
    click.echo("NEXT STEPS:")

    click.echo("\n📈  Check progress of event migrations:")
    click.echo("   invenio community-stats migration-status")

    click.echo("\n🗑️  Clear bookmarks to start fresh:")
    click.echo(
        "   invenio community-stats clear-bookmarks "
        "[--event-type TYPE] [--month MONTH]"
    )
    click.echo("\n")


@usage_events_cli.command(name="migrate")
@click.option(
    "--event-types",
    "-e",
    multiple=True,
    help="Event types to migrate (view, download). Defaults to both.",
)
@click.option(
    "--max-batches", "-b", type=int, help="Maximum batches to process per month"
)
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Number of events to process per batch (max 10,000).",
)
@click.option(
    "--max-memory-percent",
    type=int,
    default=85,
    help="Maximum memory usage percentage before stopping.",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be migrated without doing it"
)
@click.option(
    "--async",
    "async_mode",
    is_flag=True,
    help="Run reindexing asynchronously using Celery.",
)
@click.option(
    "--delete-old-indices",
    is_flag=True,
    help="Delete old indices after migration (default is to keep them).",
)
@click.option(
    "--fresh-start",
    is_flag=True,
    help="Delete existing bookmarks and start fresh for each month.",
)
@click.option(
    "--months",
    "-m",
    multiple=True,
    help=(
        "Specific months to migrate (YYYY-MM) or range (YYYY-MM:YYYY-MM). "
        "Use multiple times for multiple months that are not contiguous."
    ),
)
@with_appcontext
def migrate_events_command(
    event_types,
    max_batches,
    batch_size,
    max_memory_percent,
    dry_run,
    async_mode,
    delete_old_indices,
    fresh_start,
    months,
):
    """Migrate events to enriched indices with monthly index support.

    This command migrates existing usage (view and download) events to enriched
    indices with community and record metadata. It processes events in batches
    and can be run incrementally with bookmark tracking.

    Examples:

    \b
    - invenio community-stats usage-events migrate
    - invenio community-stats usage-events migrate --dry-run
    - invenio community-stats usage-events migrate --event-types view
    - invenio community-stats usage-events migrate --max-batches 10
    - invenio community-stats usage-events migrate --months 2024-01 --months 2024-02

    Note:

    The --fresh-start flag will delete any existing bookmarks for each month
    and start the migration from the beginning, ignoring any previous progress.
    """
    check_stats_enabled()

    if not event_types:
        event_types = ["view", "download"]

    service = current_event_reindexing_service
    service.batch_size = batch_size
    service.max_memory_percent = max_memory_percent

    if dry_run:
        click.echo("DRY RUN - No changes will be made")
        estimates = service.count_total_events()

        click.echo("Estimated events to migrate:")
        for event_type, count in estimates.items():
            click.echo(f"  {event_type}: {count:,} events")

        click.echo("\nMonthly indices found:")
        for event_type in event_types:
            indices = service.get_monthly_indices(event_type)
            click.echo(f"  {event_type}: {len(indices)} indices")
            for index in indices:
                click.echo(f"    - {index}")

        return

    click.echo(f"Starting migration for event types: {event_types}")
    click.echo(f"Batch size: {batch_size}")
    click.echo(f"Max memory: {max_memory_percent}%")
    if max_batches:
        click.echo(f"Max batches: {max_batches}")
    click.echo(f"Delete old indices after validated migrations: {delete_old_indices}")

    if async_mode:
        click.echo("Running as a background task...")
        task = reindex_usage_events_with_metadata.delay(
            event_types=list(event_types),
            max_batches=max_batches,
            batch_size=batch_size,
            max_memory_percent=max_memory_percent,
            delete_old_indices=delete_old_indices,
            fresh_start=fresh_start,
        )
        click.echo(f"Task ID: {task.id}")
        click.echo("Use 'invenio community-stats migration-status' to check progress")
    else:
        click.echo("Running synchronously...")
        try:
            # Configure service with batch settings
            service.batch_size = batch_size
            service.max_memory_percent = max_memory_percent

            with Halo(text="Migrating events...", spinner="dots"):
                results = service.reindex_events(
                    event_types=list(event_types),
                    max_batches=max_batches,
                    delete_old_indices=delete_old_indices,
                    fresh_start=fresh_start,
                    month_filter=months,
                )

            # Use the consolidated reporting function
            _report_migration_results(results)

            # Show incomplete migrations details
            if results.get("interrupted_migrations"):
                _report_interrupted_migrations(results["interrupted_migrations"])

        except Exception as e:
            click.echo(f"❌ Migration failed with error: {e}")
            raise


@usage_events_cli.command(name="status")
@click.option(
    "--show-bookmarks",
    is_flag=True,
    help="Show the migration bookmarks.",
)
@click.option(
    "--show-indices",
    is_flag=True,
    help="Show the individual monthly indices.",
)
@click.option(
    "--show-incomplete",
    is_flag=True,
    help="Show the details of incomplete migrations.",
)
@click.option(
    "--show-completed",
    is_flag=True,
    help="Show the details of completed migrations.",
)
@click.option(
    "--show-not-started",
    is_flag=True,
    help="Show the details of migrations that have not yet begun.",
)
@with_appcontext
def migration_status_command(
    show_bookmarks,
    show_indices,
    show_incomplete,
    show_completed,
    show_not_started,
):
    """Show the current migration status and progress.

    This command displays the current status of event migration processes across
    all monthly indices. It shows progress, health status, and detailed information
    about completed, interrupted, and pending migrations.

    Examples:

    \b
    - invenio community-stats usage-events status
    - invenio community-stats usage-events status --show-bookmarks
    - invenio community-stats usage-events status --show-incomplete
    - invenio community-stats usage-events status --show-completed --show-indices
    """
    check_stats_enabled()

    service = current_event_reindexing_service

    progress = service.get_reindexing_progress()
    counts = progress["counts"]
    health = progress["health"]

    click.echo("\nMigration Status")
    click.echo("===============")

    # Health status
    status_icon = "✅" if health["is_healthy"] else "❌"
    click.echo(f"System Health: {status_icon} {health['reason']}")
    click.echo(f"Memory Usage: {health['memory_usage']:.1f}%")

    # Event counts
    click.echo("-" * 50)
    click.echo("Event Counts:")
    total_old_events = counts.get("view_old", 0) + counts.get("download_old", 0)
    total_migrated_events = counts.get("view_migrated", 0) + counts.get(
        "download_migrated", 0
    )
    total_remaining_events = counts.get("view_remaining", 0) + counts.get(
        "download_remaining", 0
    )
    click.echo(f"  Total old events: {total_old_events:,} events")
    click.echo(f"     view: {counts.get('view_old', 0)}")
    click.echo(f"     download: {counts.get('download_old', 0)}")
    click.echo(f"  Total migrated events: {total_migrated_events:,} events")
    click.echo(f"     view: {counts.get('view_migrated', 0)}")
    click.echo(f"     download: {counts.get('download_migrated', 0)}")
    click.echo(f"  Total remaining events: {total_remaining_events:,} events")
    click.echo(f"     view: " f"{counts.get('view_remaining', 0)}")
    click.echo(f"     download: " f"{counts.get('download_remaining', 0)}")

    # Monthly indices
    click.echo("-" * 50)
    click.echo("Monthly Indices:")
    if show_indices:
        _format_monthly_indices(counts)
    else:
        click.echo("  Not showing indices (use --show-indices to show)")

    # Bookmarks
    click.echo("-" * 50)
    click.echo("Migration Bookmarks:")
    if show_bookmarks:
        for enriched_idx in counts["migrations_in_progress"]:
            if enriched_idx["bookmark"]:
                bookmark = enriched_idx["bookmark"]
                timestamp = arrow.get(bookmark["last_event_timestamp"])
                click.echo(f"  {enriched_idx['source_index']}:")
                click.echo(f"    Last event ID: {bookmark['last_event_id']}")
                click.echo(
                    f"    Last event timestamp: "
                    f"{timestamp.format('YYYY-MM-DD HH:mm:ss')}"
                )
    else:
        click.echo("  Not showing bookmarks (use --show-bookmarks to show)")

    # Incomplete migrations
    click.echo("-" * 50)
    click.echo("Incomplete Migrations:")
    has_incomplete = _format_interrupted_migrations(
        progress, show_resume_commands=True, show_details=show_incomplete
    )
    if has_incomplete and not show_incomplete:
        click.echo("  (use --show-incomplete to show details of each)")

    # Completed migrations
    click.echo("-" * 50)
    click.echo("Completed Migrations:")
    has_completed = _format_completed_migrations(progress, show_details=show_completed)
    if has_completed and not show_completed:
        click.echo("  (use --show-completed to show details of each)")

    # Not started migrations
    click.echo("-" * 50)
    click.echo("Migration Yet to Begin:")
    has_not_started = _format_not_started_migrations(
        progress, show_details=show_not_started
    )
    if has_not_started and not show_not_started:
        click.echo("  (use --show-not-started to show details of each)")
    click.echo("\n")


def _format_monthly_indices(estimates):
    """Format and display monthly indices with counts."""
    # View events
    view_indices = [
        idx
        for idx in estimates["migrations_in_progress"]
        if "view" in idx["source_index"]
    ]
    if view_indices:
        click.echo("  View Events:")
        for enriched_idx in view_indices:
            _format_index_mapping(enriched_idx)

        # Add completed migrations (deleted old indices)
        completed_view = [
            idx
            for idx in estimates["migrations_old_deleted"]
            if "view" in idx["source_index"]
        ]
        for migration in completed_view:
            click.echo(
                f"    {migration['source_index']} → {migration['index']} "
                f"(completed)"
            )
            # Extract the original source index name by removing -v2.0.0 suffix
            # Note: The enriched index name should already have the -v2.0.0 suffix from the template
            original_source = migration["index"].replace("-v2.0.0", "")
            click.echo(
                f"      [{original_source}](deleted) → "
                f"{migration.get('migrated_count', 0):,}, Remaining: 0"
            )

    # Download events
    download_indices = [
        idx
        for idx in estimates["migrations_in_progress"]
        if "download" in idx["source_index"]
    ]
    if download_indices:
        click.echo("  Download Events:")
        for enriched_idx in download_indices:
            _format_index_mapping(enriched_idx)

        # Add completed migrations (deleted old indices)
        completed_download = [
            idx
            for idx in estimates["migrations_old_deleted"]
            if "download" in idx["source_index"]
        ]
        for migration in completed_download:
            click.echo(
                f"    {migration['source_index']} → {migration['index']} "
                f"(completed)"
            )
            # Extract the original source index name by removing -v2.0.0 suffix
            # Note: The enriched index name should already have the -v2.0.0 suffix from the template
            original_source = migration["index"].replace("-v2.0.0", "")
            click.echo(
                f"      [{original_source}](deleted) → "
                f"{migration.get('migrated_count', 0):,}, Remaining: 0"
            )


def _format_index_mapping(enriched_idx):
    """Format a single index mapping with counts."""
    old_count = enriched_idx["old_count"]
    migrated_count = enriched_idx["migrated_count"] or 0
    remaining_count = enriched_idx["remaining_count"] or 0

    click.echo(f"    {enriched_idx['source_index']} → {enriched_idx['index']}")
    click.echo(
        f"      Old: {old_count:,}, Migrated: {migrated_count:,}, "
        f"Remaining: {remaining_count:,}"
    )


def _format_interrupted_migrations(
    progress, show_resume_commands=True, show_details=True
):
    """Format and display interrupted migrations.

    Args:
        progress: The reindexing progress data from the service
        show_resume_commands: Whether to show resume commands (default: True)
        show_details: Whether to show the details of interrupted migrations
            (default: True). If False, only show the month and source index.

    Returns:
        bool: True if there are interrupted migrations to show, False otherwise
    """
    counts = progress["counts"]
    interrupted_count = len(
        [
            idx
            for idx in counts["migrations_in_progress"]
            if idx["interrupted"] and not idx["completed"]
        ]
    )

    if not interrupted_count:
        click.echo("\n  No interrupted migrations found.")
        click.echo("  All migrations that have begun appear to be complete.")
    else:
        click.echo(
            f"\n  Found {interrupted_count} interrupted or unfinished index migrations."
        )
        if show_resume_commands:
            click.echo(
                "\n  Use the resume commands below to continue the individual index "
                "migration, \n  or simply run the migrate command again to "
                "resume all incomplete migrations."
            )

    for enriched_idx in counts["migrations_in_progress"]:
        if enriched_idx["interrupted"]:

            month = (
                enriched_idx["source_index"].split("-")[-2]
                + "-"
                + enriched_idx["source_index"].split("-")[-1]
            )
            event_type = (
                "view" if "view" in enriched_idx["source_index"] else "download"
            )

            click.echo(f"\n  {event_type.upper()} {month}:")
            click.echo(f"  Source index: {enriched_idx['source_index']}")
            if enriched_idx["index"]:
                click.echo(f"  Enriched index: {enriched_idx['index']}")
            if show_details:
                click.echo(f"  Original count: {enriched_idx['old_count']}")
                click.echo(f"  Migrated count: {enriched_idx['migrated_count'] or 0}")
            click.echo(f"  Remaining events: {enriched_idx['remaining_count'] or 0}")
            if show_details:
                click.echo(
                    f"  Status: "
                    f"{'Completed' if enriched_idx['completed'] else 'In Progress'}"
                )
                click.echo(
                    f"  Interrupted: {'Yes' if enriched_idx['interrupted'] else 'No'}"
                )
                if enriched_idx["bookmark"]:
                    bookmark = enriched_idx["bookmark"]
                    click.echo("  Bookmark details:")
                    if bookmark.get("last_event_id"):
                        click.echo(
                            f"    Last processed ID: {bookmark['last_event_id']}"
                        )
                    if bookmark.get("last_event_timestamp"):
                        click.echo(
                            f"    Last processed timestamp: "
                            f"{bookmark['last_event_timestamp']}"
                        )
                    if bookmark.get("task_id"):
                        click.echo(f"    Task ID: {bookmark['task_id']}")

            if show_resume_commands:
                click.echo("  Resume command:")
                click.echo(
                    f"    invenio community-stats usage-events migrate "
                    f"--event-types {event_type} "
                    f"--months {month}"
                )

    return interrupted_count > 0


def _format_completed_migrations(progress, show_details=True):
    """Format and display completed migrations.

    Args:
        progress: The reindexing progress data from the service
        show_details: Whether to show the details of completed migrations
            (default: True). If False, only show the count.

    Returns:
        bool: True if there are completed migrations to show, False otherwise
    """
    counts = progress["counts"]
    completed_found = False
    completed_count = 0
    deleted_count = 0

    # Count completed migrations from migrations_in_progress (migrations where
    # old indices still exist)
    for enriched_idx in counts["migrations_in_progress"]:
        if enriched_idx["completed"] and not enriched_idx["interrupted"]:
            completed_found = True
            completed_count += 1
            if "deleted" in enriched_idx["source_index"]:
                deleted_count += 1

    # Count completed migrations from migrations_old_deleted (migrations where
    # old indices were deleted)
    for completed_idx in counts["migrations_old_deleted"]:
        if completed_idx["completed"] and not completed_idx["interrupted"]:
            completed_found = True
            completed_count += 1
            if "deleted" in completed_idx["source_index"]:
                deleted_count += 1

    if not completed_found:
        click.echo("  No completed migrations found.")
        click.echo("  All migrations are either in progress or not started.")
    else:
        click.echo(f"  Found {completed_count} completed index migrations.")
        click.echo(f"  Found {deleted_count} deleted old indices.")
        if deleted_count < completed_count:
            click.echo(
                "\n  To delete old indices for completed migrations, run the "
                "migrate\n  command again with the --delete-old-indices flag."
            )

        if show_details:
            # Show details for migrations_in_progress (migrations where old indices
            # still exist)
            for enriched_idx in counts["migrations_in_progress"]:
                if enriched_idx["completed"] and not enriched_idx["interrupted"]:
                    click.echo("\n")
                    month = (
                        enriched_idx["source_index"].split("-")[-2]
                        + "-"
                        + enriched_idx["source_index"].split("-")[-1]
                    )
                    event_type = (
                        "view" if "view" in enriched_idx["source_index"] else "download"
                    )

                    click.echo(f"    {event_type.upper()} {month}:")
                    click.echo(f"      Source index: {enriched_idx['source_index']}")
                    if enriched_idx["index"]:
                        click.echo(f"      Enriched index: {enriched_idx['index']}")
                    click.echo(f"      Original count: {enriched_idx['old_count']}")
                    click.echo(
                        f"      Migrated count: {enriched_idx['migrated_count'] or 0}"
                    )
                    click.echo(
                        f"      Remaining events: "
                        f"{enriched_idx['remaining_count'] or 0}"
                    )
                    if "deleted" in enriched_idx["source_index"]:
                        click.echo("      Old index deleted: Yes")
                    else:
                        click.echo("      Old index deleted: No")

            # Show details for migrations_old_deleted (migrations where old indices
            # were deleted)
            for completed_idx in counts["migrations_old_deleted"]:
                if completed_idx["completed"] and not completed_idx["interrupted"]:
                    click.echo("\n")
                    # Extract month from the index name (remove -v2.0.0 suffix
                    # first)
                    index_name = completed_idx["index"]
                    if index_name.endswith("-v2.0.0"):
                        base_name = index_name[:-7]  # Remove -v2.0.0
                    else:
                        base_name = index_name
                    month = base_name.split("-")[-2] + "-" + base_name.split("-")[-1]
                    event_type = "view" if "view" in index_name else "download"

                    click.echo(f"    {event_type.upper()} {month}:")
                    click.echo(f"      Source index: {completed_idx['source_index']}")
                    click.echo(f"      Enriched index: {completed_idx['index']}")
                    click.echo(f"      Original count: {completed_idx['old_count']}")
                    click.echo(
                        f"      Migrated count: {completed_idx['migrated_count'] or 0}"
                    )
                    click.echo(
                        f"      Remaining events: "
                        f"{completed_idx['remaining_count'] or 0}"
                    )
                    if "deleted" in completed_idx["source_index"]:
                        click.echo("      Old index deleted: Yes")
                    else:
                        click.echo("      Old index deleted: No")

    return completed_found


def _format_not_started_migrations(progress, show_details=True):
    """Format and display not-started migrations.

    Args:
        progress: The reindexing progress data from the service
        show_details: Whether to show the details of not-started migrations
            (default: True). If False, only show the count.

    Returns:
        bool: True if there are not-started migrations to show, False otherwise
    """
    counts = progress["counts"]
    not_started_found = False
    not_started_count = 0

    for enriched_idx in counts["migrations_in_progress"]:
        if not enriched_idx["completed"] and not enriched_idx["interrupted"]:
            not_started_found = True
            not_started_count += 1

    if not not_started_found:
        click.echo("  All migrations have either been completed or are in progress.")
    else:
        click.echo(f"  Found {not_started_count} not-started index migrations.")

    if show_details:
        for enriched_idx in counts["migrations_in_progress"]:
            if not enriched_idx["completed"] and not enriched_idx["interrupted"]:
                month = (
                    enriched_idx["source_index"].split("-")[-2]
                    + "-"
                    + enriched_idx["source_index"].split("-")[-1]
                )
                event_type = (
                    "view" if "view" in enriched_idx["source_index"] else "download"
                )

                click.echo(f"    {event_type.upper()} {month}:")
                click.echo(f"      Source index: {enriched_idx['source_index']}")
                click.echo(f"      Original count: {enriched_idx['old_count']}")
                click.echo("      Status: Not started")

    return not_started_found


@usage_events_cli.command(name="clear-bookmarks")
@click.option(
    "--event-type",
    "-e",
    help=(
        "Event type to clear bookmarks for (view, download). "
        "If not specified, clears for both."
    ),
)
@click.option(
    "--month",
    "-m",
    help=(
        "Month to clear bookmarks for (YYYY-MM). "
        "If not specified, clears for all months."
    ),
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm that you want to clear bookmarks without prompting.",
)
@with_appcontext
def clear_bookmarks_command(event_type, month, confirm):
    """Clear reindexing bookmarks for event migration.

    This command clears migration bookmarks for specific months or all months.
    Bookmarks track the progress of event migration and can be cleared to
    restart migration from the beginning.

    Examples:

    \b
    - invenio community-stats usage-events clear-bookmarks
    - invenio community-stats usage-events clear-bookmarks --event-type view
    - invenio community-stats usage-events clear-bookmarks --month 2024-01
    - invenio community-stats usage-events clear-bookmarks --confirm
    """
    check_stats_enabled()

    if not event_type:
        event_types = ["view", "download"]
    else:
        if event_type not in ["view", "download"]:
            click.echo("❌ Event type must be 'view' or 'download'")
            return
        event_types = [event_type]

    if month:
        # Validate month format
        try:
            arrow.get(month, "YYYY-MM")
        except Exception:
            click.echo("❌ Month must be in YYYY-MM format")
            return

    service = current_event_reindexing_service
    cleared_count = 0

    for event_type in event_types:
        if month:
            # Clear bookmark for specific month
            task_id = f"{event_type}-{month}-reindexing"
            if not confirm:
                response = click.confirm(
                    f"Are you sure you want to clear the bookmark for "
                    f"{event_type} {month}?"
                )
                if not response:
                    continue

            try:
                service.reindexing_bookmark_api.delete_bookmark(task_id)
                click.echo(f"✅ Cleared bookmark for {event_type} {month}")
                cleared_count += 1
            except Exception as e:
                click.echo(f"❌ Failed to clear bookmark for {event_type} {month}: {e}")
        else:
            # Clear bookmarks for all months
            monthly_indices = service.get_monthly_indices(event_type)
            for source_index in monthly_indices:
                year, month_str = source_index.split("-")[-2:]
                task_id = f"{event_type}-{year}-{month_str}-reindexing"

                if not confirm:
                    response = click.confirm(
                        f"Are you sure you want to clear the bookmark for "
                        f"{event_type} {year}-{month_str}?"
                    )
                    if not response:
                        continue

                try:
                    service.reindexing_bookmark_api.delete_bookmark(task_id)
                    click.echo(
                        f"✅ Cleared bookmark for {event_type} {year}-{month_str}"
                    )
                    cleared_count += 1
                except Exception as e:
                    click.echo(
                        f"❌ Failed to clear bookmark for {event_type} "
                        f"{year}-{month_str}: {e}"
                    )

    if cleared_count > 0:
        click.echo(f"\n🎯 Cleared {cleared_count} bookmark(s) successfully")
        click.echo(
            "💡 You can now run migration commands with --fresh-start to start fresh"
        )
    else:
        click.echo("📭 No bookmarks were cleared")


@usage_events_cli.command(name="migrate-background")
@click.option(
    "--event-types",
    "-e",
    multiple=True,
    help="Event types to migrate (view, download). Defaults to both.",
)
@click.option(
    "--max-batches", "-b", type=int, help="Maximum batches to process per month"
)
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Number of events to process per batch (max 10,000).",
)
@click.option(
    "--max-memory-percent",
    type=int,
    default=85,
    help="Maximum memory usage percentage before stopping.",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be migrated without doing it"
)
@click.option(
    "--delete-old-indices",
    is_flag=True,
    help="Delete old indices after migration (default is to keep them).",
)
@click.option(
    "--fresh-start",
    is_flag=True,
    help="Delete existing bookmarks and start fresh for each month.",
)
@click.option(
    "--months",
    "-m",
    multiple=True,
    help=(
        "Specific months to migrate (YYYY-MM) or range (YYYY-MM:YYYY-MM). "
        "Use multiple times for multiple months that are not contiguous."
    ),
)
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory to store PID and status files.",
)
@with_appcontext
def migrate_events_background_command(
    event_types,
    max_batches,
    batch_size,
    max_memory_percent,
    dry_run,
    delete_old_indices,
    fresh_start,
    months,
    pid_dir,
):
    """Start event migration in the background with process management.

    This command provides the same functionality as the migrate command but runs
    in the background with full process management capabilities. It allows you to
    start long-running event migration processes without blocking the terminal.

    Examples:

    \b
    - invenio community-stats usage-events migrate-background
    - invenio community-stats usage-events migrate-background --event-types view
    - invenio community-stats usage-events migrate-background --batch-size 500
    - invenio community-stats usage-events migrate-background --months 2024-01

    Process management:

    \b
    - Monitor progress: invenio community-stats processes status event-migration
    - Cancel process: invenio community-stats processes cancel event-migration
    - View logs: invenio community-stats processes status event-migration --show-log
    """
    check_stats_enabled()

    if not event_types:
        event_types = ["view", "download"]

    # Build the command to run
    cmd = [
        "invenio",
        "community-stats",
        "usage-events",
        "migrate",
    ]

    # Define option mappings for cleaner command building
    option_mappings = [
        ("--batch-size", str(batch_size)),
        ("--max-memory-percent", str(max_memory_percent)),
        ("--max-batches", max_batches),
        ("--dry-run", dry_run),
        ("--delete-old-indices", delete_old_indices),
        ("--fresh-start", fresh_start),
    ]

    # Add single-value options
    for option, value in option_mappings:
        if value:
            cmd.extend([option, str(value)] if option != "--dry-run" else [option])

    # Add multi-value options
    if months:
        for month in months:
            cmd.extend(["--months", month])

    if event_types:
        for event_type in event_types:
            cmd.extend(["--event-types", event_type])

    process_manager = ProcessManager(
        "event-migration", pid_dir, package_prefix="invenio-community-stats"
    )

    try:
        pid = process_manager.start_background_process(cmd)
        click.echo("\nBackground migration started successfully!")
        click.echo(f"Process ID: {pid}")
        click.echo(f"Command: {' '.join(cmd)}")

        click.echo("\nMonitor progress:")
        click.echo("  invenio community-stats processes status event-migration")
        click.echo(
            "  invenio community-stats processes status event-migration --show-log"
        )

        click.echo("\nCancel if needed:")
        click.echo("  invenio community-stats processes cancel event-migration")

    except RuntimeError as e:
        click.echo(f"Failed to start background migration: {e}")
        return 1

    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        return 1
