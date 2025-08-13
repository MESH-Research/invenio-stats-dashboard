#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

from pprint import pprint

import arrow
import click
from flask import current_app
from flask.cli import with_appcontext
from halo import Halo
from invenio_stats_dashboard.proxies import current_event_reindexing_service
from opensearchpy.helpers.search import Search

from .proxies import current_community_stats_service
from .service import EventReindexingService
from .tasks import reindex_usage_events_with_metadata


def check_stats_enabled():
    """Check if community stats are enabled."""
    if not current_app.config.get("COMMUNITY_STATS_ENABLED", True):
        raise click.ClickException(
            "Community stats dashboard is disabled. "
            "Set COMMUNITY_STATS_ENABLED=True to enable this command."
        )


def check_scheduled_tasks_enabled():
    """Check if scheduled tasks are enabled."""
    if not current_app.config.get("COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED", True):
        raise click.ClickException(
            "Community stats scheduled tasks are disabled. "
            "Set COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED=True to enable "
            "aggregation tasks."
        )


@click.group()
def cli():
    """Community stats dashboard CLI."""
    pass


@cli.command(name="generate-events")
@click.option(
    "--community-id",
    type=str,
    multiple=True,
    help="The ID of the community to generate events for. "
    "Can be specified multiple times.",
)
@click.option(
    "--record-ids",
    type=str,
    multiple=True,
    help="The IDs of the records to generate events for. "
    "Can be specified multiple times.",
)
@with_appcontext
def generate_events_command(community_id, record_ids):
    """
    Generate community events for all records in the instance.
    """
    check_stats_enabled()
    current_community_stats_service.generate_record_community_events(
        community_ids=list(community_id) if community_id else None,
        recids=list(record_ids) if record_ids else None,
    )


@cli.command(name="aggregate-stats")
@click.option(
    "--community-id",
    type=str,
    multiple=True,
    help="The UUID or slug of the community to aggregate stats for",
)
@click.option(
    "--start-date",
    type=str,
    help="The start date to aggregate stats for (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=str,
    help="The end date to aggregate stats for (YYYY-MM-DD)",
)
@click.option(
    "--eager",
    is_flag=True,
    help="Run aggregation eagerly (synchronously)",
)
@click.option(
    "--update-bookmark",
    is_flag=True,
    default=True,
    help="Update the bookmark after aggregation",
)
@click.option(
    "--ignore-bookmark",
    is_flag=True,
    help="Ignore the bookmark and process all records",
)
@with_appcontext
def aggregate_stats_command(
    community_id,
    start_date,
    end_date,
    eager,
    update_bookmark,
    ignore_bookmark,
):
    """Aggregate community record statistics."""
    check_stats_enabled()
    check_scheduled_tasks_enabled()

    community_ids = list(community_id) if community_id else None
    current_community_stats_service.aggregate_stats(
        community_ids=community_ids,
        start_date=start_date,
        end_date=end_date,
        eager=eager,
        update_bookmark=update_bookmark,
        ignore_bookmark=ignore_bookmark,
    )


@cli.command(name="read-stats")
@click.option(
    "--community-id",
    type=str,
    default="global",
    help="The ID of the community to read stats for.",
)
@click.option(
    "--start-date",
    type=str,
    default=arrow.get().shift(days=-1).isoformat(),
    help="The start date to read stats for.",
)
@click.option(
    "--end-date",
    type=str,
    default=arrow.get().isoformat(),
    help="The end date to read stats for.",
)
@with_appcontext
def read_stats_command(community_id, start_date, end_date):
    """Read stats for a community."""
    check_stats_enabled()
    print(f"Reading stats for community {community_id} from {start_date} to {end_date}")
    stats = current_community_stats_service.read_stats(
        community_id, start_date=start_date, end_date=end_date
    )
    pprint(stats)


@cli.command(name="migrate-events")
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
    help="Number of events to process per batch.",
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
@with_appcontext
def migrate_events_command(
    event_types,
    max_batches,
    batch_size,
    max_memory_percent,
    dry_run,
    async_mode,
    delete_old_indices,
):
    """Migrate events to enriched indices with monthly index support."""
    check_stats_enabled()

    if not event_types:
        event_types = ["view", "download"]

    service = EventReindexingService(current_app)
    service.batch_size = batch_size
    service.max_memory_percent = max_memory_percent

    if dry_run:
        click.echo("DRY RUN - No changes will be made")
        estimates = service.estimate_total_events()

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
                )

            if results["completed"]:
                click.echo("✅ Migration completed successfully!")
                click.echo(f"Total processed: {results['total_processed']:,}")
                click.echo(f"Total errors: {results['total_errors']}")

                for event_type, event_results in results["event_types"].items():
                    click.echo(f"\n{event_type.upper()} Events:")
                    click.echo(f"  Processed: {event_results['processed']:,}")
                    click.echo(f"  Errors: {event_results['errors']}")
                    click.echo(f"  Batches: {event_results['batches']}")

                    if "months" in event_results:
                        for month, month_results in event_results["months"].items():
                            if month_results.get("interrupted", False):
                                status = "⏸️"
                                click.echo(
                                    f"    {status} {month}: "
                                    f"{month_results['processed']:,} events "
                                    f"(INTERRUPTED - "
                                    f"{month_results['batches_processed']} batches)"
                                )
                            elif month_results["completed"]:
                                status = "✅"
                                click.echo(
                                    f"    {status} {month}: "
                                    f"{month_results['processed']:,} events"
                                )
                            else:
                                status = "❌"
                                click.echo(
                                    f"    {status} {month}: "
                                    f"{month_results['processed']:,} events"
                                )
            else:
                click.echo("❌ Migration failed!")
                click.echo(f"Errors: {results['total_errors']}")

            # Show incomplete migrations details
            if results.get("interrupted_migrations"):
                click.echo("\n⚠️  INCOMPLETE MIGRATIONS:")

                # Group by reason
                interrupted = [
                    m
                    for m in results["interrupted_migrations"]
                    if m.get("reason") == "interrupted"
                ]
                failed = [
                    m
                    for m in results["interrupted_migrations"]
                    if m.get("reason") == "failed"
                ]

                if interrupted:
                    click.echo("\n⏸️  INTERRUPTED (can resume):")
                    click.echo(
                        "The following migrations were interrupted due to "
                        "max_batches limit:"
                    )
                    for migration in interrupted:
                        click.echo(
                            f"  • {migration['event_type']} {migration['month']}: "
                            f"{migration['processed']:,} events processed in "
                            f"{migration['batches']} batches"
                        )
                        click.echo(
                            f"    Last processed ID: {migration['last_processed_id']}"
                        )
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

                # Resume instructions
                if interrupted:
                    click.echo("\n💡 To resume interrupted migrations:")
                    click.echo(
                        "  1. Use the same command with --max-batches to continue"
                    )
                    click.echo(
                        "  2. Or use 'migrate-month' command for specific months:"
                    )
                    for migration in interrupted:
                        click.echo(
                            f"     invenio community-stats migrate-month "
                            f"--event-type {migration['event_type']} "
                            f"--month {migration['month']}"
                        )

                if failed:
                    click.echo("\n🔧 To retry failed migrations:")
                    click.echo("  1. Check logs for error details")
                    click.echo("  2. Fix the underlying issue")
                    click.echo("  3. Run the migration again:")
                    for migration in failed:
                        click.echo(
                            f"     invenio community-stats migrate-month "
                            f"--event-type {migration['event_type']} "
                            f"--month {migration['month']}"
                        )

        except Exception as e:
            click.echo(f"❌ Migration failed with error: {e}")
            raise


@cli.command(name="migration-status")
@with_appcontext
def migration_status_command():
    """Show the current migration status and progress."""
    check_stats_enabled()

    service = EventReindexingService(current_app)

    estimates = service.estimate_total_events()

    click.echo("Migration Status")
    click.echo("===============")

    # Health status
    health = service.get_reindexing_progress()["health"]
    status_icon = "✅" if health["is_healthy"] else "❌"
    click.echo(f"System Health: {status_icon} {health['reason']}")
    click.echo(f"Memory Usage: {health['memory_usage']:.1f}%")

    # Event estimates
    click.echo("\nEvent Estimates:")
    total_events = sum(estimates.values())
    for event_type, count in estimates.items():
        click.echo(f"  {event_type}: {count:,} events")
    click.echo(f"  Total: {total_events:,} events")

    # Monthly indices
    click.echo("\nMonthly Indices:")
    for event_type in ["view", "download"]:
        indices = service.get_monthly_indices(event_type)
        click.echo(f"  {event_type}: {len(indices)} indices")
        for index in sorted(indices):
            # Check if this is current month
            is_current = service.is_current_month_index(index)
            current_marker = " (current)" if is_current else ""
            click.echo(f"    - {index}{current_marker}")

    # Bookmarks
    click.echo("\nMigration Bookmarks:")
    for event_type in ["view", "download"]:
        indices = service.get_monthly_indices(event_type)
        click.echo(f"  {event_type}:")
        for index in sorted(indices):
            month = index.split("-")[-1]
            bookmark = service.get_reindexing_progress()["bookmarks"][event_type].get(
                month
            )
            if bookmark:
                click.echo(f"    {month}: {bookmark}")
            else:
                click.echo(f"    {month}: not started")


@cli.command(name="show-interrupted")
@with_appcontext
def show_interrupted_command():
    """Show details about interrupted migrations."""
    check_stats_enabled()

    service = EventReindexingService(current_app)
    progress = service.get_reindexing_progress()

    click.echo("Interrupted Migrations")
    click.echo("=====================")

    interrupted_found = False
    for event_type in ["view", "download"]:
        bookmarks = progress["bookmarks"][event_type]
        for month, bookmark in bookmarks.items():
            if bookmark:
                # Check if there are more records to process
                indices = service.get_monthly_indices(event_type)
                source_index = None
                for index in indices:
                    if index.endswith(f"-{month}"):
                        source_index = index
                        break

                if source_index:
                    try:
                        # Check if there are more records after the bookmark
                        search = Search(using=service.client, index=source_index)
                        search = search.sort("_id")
                        search = search.extra(search_after=[bookmark])
                        search = search.extra(size=1)
                        response = search.execute()

                        if response.hits.hits:
                            interrupted_found = True
                            click.echo(f"\n⏸️  {event_type.upper()} {month}:")
                            click.echo(f"  Source index: {source_index}")
                            click.echo(f"  Last processed ID: {bookmark}")
                            click.echo("  More records available: Yes")
                            click.echo("  Resume command:")
                            click.echo(
                                f"    invenio community-stats migrate-month "
                                f"--event-type {event_type} --month {month}"
                            )
                    except Exception as e:
                        click.echo(f"  Error checking {event_type} {month}: {e}")

    if not interrupted_found:
        click.echo("No interrupted migrations found.")
        click.echo("All migrations appear to be complete or not started.")


@cli.command(name="migrate-month")
@click.option("--event-type", "-e", required=True, help="Event type (view or download)")
@click.option("--month", "-m", required=True, help="Month to migrate (YYYY-MM)")
@click.option("--max-batches", "-b", type=int, help="Maximum batches to process")
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Number of events to process per batch.",
)
@click.option(
    "--max-memory-percent",
    type=int,
    default=85,
    help="Maximum memory usage percentage before stopping.",
)
@click.option(
    "--delete-old-indices",
    is_flag=True,
    help="Delete old indices after migration (default is to keep them).",
)
@with_appcontext
def migrate_month_command(
    event_type, month, max_batches, batch_size, max_memory_percent, delete_old_indices
):
    """Migrate a specific monthly index."""
    check_stats_enabled()

    if event_type not in ["view", "download"]:
        click.echo("❌ Event type must be 'view' or 'download'")
        return

    service = EventReindexingService(current_app)
    service.batch_size = batch_size
    service.max_memory_percent = max_memory_percent

    # Find the source index for this month
    indices = service.get_monthly_indices(event_type)
    source_index = None
    for index in indices:
        if index.endswith(f"-{month}"):
            source_index = index
            break

    if not source_index:
        click.echo(f"❌ No {event_type} index found for month {month}")
        click.echo(f"Available indices: {indices}")
        return

    click.echo(f"Starting migration for {event_type} events in {month}")
    click.echo(f"Source index: {source_index}")
    click.echo(f"Batch size: {batch_size}")
    click.echo(f"Max memory: {max_memory_percent}%")
    click.echo(f"Delete old indices after validated migrations: {delete_old_indices}")

    try:
        with Halo(text="Migrating monthly index...", spinner="dots"):
            results = service.migrate_monthly_index(
                event_type=event_type,
                source_index=source_index,
                month=month,
                max_batches=max_batches,
                delete_old_indices=delete_old_indices,
            )

        if results["completed"]:
            click.echo("✅ Migration completed successfully!")
            click.echo(f"Processed: {results['processed']:,} events")
            click.echo(f"Batches: {results['batches']}")
            click.echo(f"Target index: {results['target_index']}")
        elif results.get("interrupted", False):
            click.echo("⏸️  Migration interrupted!")
            click.echo(f"Processed: {results['processed']:,} events")
            click.echo(f"Batches processed: {results['batches_processed']}")
            click.echo(f"Last processed ID: {results['last_processed_id']}")
            click.echo(f"Target index: {results['target_index']}")
            click.echo("\n💡 To resume this migration:")
            click.echo(
                f"  invenio community-stats migrate-month "
                f"--event-type {event_type} --month {month} "
                f"--max-batches <remaining_batches>"
            )
        else:
            click.echo("❌ Migration failed!")
            click.echo(f"Errors: {results['errors']}")

    except Exception as e:
        click.echo(f"❌ Migration failed with error: {e}")
        raise


@cli.command(name="estimate-migration")
@with_appcontext
def estimate_migration_command():
    """Estimate the total number of events to migrate."""
    check_stats_enabled()

    estimates = current_event_reindexing_service.estimate_total_events()

    total_events = sum(estimates.values())

    click.echo("Event Migration Estimates:")
    click.echo("=" * 40)
    for event_type, count in estimates.items():
        click.echo(f"{event_type:>10}: {count:>10,} events")
    click.echo("-" * 40)
    click.echo(f"{'TOTAL':>10}: {total_events:>10,} events")

    # Rough time estimate (very conservative)
    if total_events > 0:
        batches_needed = total_events / 1000  # Assuming 1000 events per batch
        hours_estimate = batches_needed * 0.1  # Assuming 6 seconds per batch
        click.echo(f"\nRough time estimate: {hours_estimate:.1f} hours")
        click.echo(
            "(This is a very conservative estimate - actual time may vary "
            "significantly)"
        )
