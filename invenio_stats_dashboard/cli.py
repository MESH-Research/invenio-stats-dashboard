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
from flask import current_app as app
from flask.cli import with_appcontext
from halo import Halo
from .proxies import current_community_stats_service
from .service import EventReindexingService
from .tasks import reindex_events_with_metadata


@click.group()
def cli():
    """Stats dashboard CLI commands."""
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
    current_community_stats_service.generate_record_community_events(
        community_ids=list(community_id) if community_id else None,
        recids=list(record_ids) if record_ids else None,
    )


@cli.command(name="aggregate-stats")
@click.option(
    "--community-id",
    type=str,
    help="The ID of the community to aggregate stats for.",
)
@click.option(
    "--start-date",
    type=str,
    help="The start date to aggregate stats for.",
)
@click.option(
    "--end-date",
    type=str,
    help="The end date to aggregate stats for.",
)
@click.option(
    "--eager",
    is_flag=True,
    help="Whether to aggregate stats eagerly.",
)
@click.option(
    "--update-bookmark",
    is_flag=True,
    help="Whether to update the bookmark.",
)
@click.option(
    "--ignore-bookmark",
    is_flag=True,
    help="Whether to ignore the bookmark.",
)
@with_appcontext
def aggregate_stats_command(
    community_id, start_date, end_date, eager, update_bookmark, ignore_bookmark
):
    """Aggregate stats for a community."""
    current_community_stats_service.aggregate_stats(
        community_ids=[community_id] if community_id else None,
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
    print(f"Reading stats for community {community_id} from {start_date} to {end_date}")
    stats = current_community_stats_service.get_community_stats(
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
@with_appcontext
def migrate_events_command(
    event_types, max_batches, batch_size, max_memory_percent, dry_run, async_mode
):
    """Migrate events to enriched indices with monthly index support."""
    from flask import current_app

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

    if async_mode:
        click.echo("Running asynchronously with Celery...")
        task = reindex_events_with_metadata.delay(
            event_types=list(event_types),
            max_batches=max_batches,
            batch_size=batch_size,
            max_memory_percent=max_memory_percent,
        )
        click.echo(f"Task ID: {task.id}")
        click.echo(
            "Use 'invenio stats-dashboard get-reindexing-progress' to check progress"
        )
    else:
        click.echo("Running synchronously...")
        try:
            with Halo(text="Migrating events...", spinner="dots"):
                results = service.reindex_events(
                    event_types=list(event_types), max_batches=max_batches
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
                            status = "✅" if month_results["completed"] else "❌"
                            click.echo(
                                f"    {status} {month}: "
                                f"{month_results['processed']:,} events"
                            )
            else:
                click.echo("❌ Migration failed!")
                click.echo(f"Errors: {results['total_errors']}")

        except Exception as e:
            click.echo(f"❌ Migration failed with error: {e}")
            raise


@cli.command(name="migration-status")
@with_appcontext
def migration_status_command():
    """Show the current migration status and progress."""
    from flask import current_app

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
@with_appcontext
def migrate_month_command(
    event_type, month, max_batches, batch_size, max_memory_percent
):
    """Migrate a specific monthly index."""
    from flask import current_app

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

    try:
        with Halo(text="Migrating monthly index...", spinner="dots"):
            results = service.migrate_monthly_index(
                event_type=event_type,
                source_index=source_index,
                month=month,
                max_batches=max_batches,
            )

        if results["completed"]:
            click.echo("✅ Migration completed successfully!")
            click.echo(f"Processed: {results['processed']:,} events")
            click.echo(f"Batches: {results['batches']}")
            click.echo(f"Target index: {results['target_index']}")
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
    reindexing_service = EventReindexingService(app)
    estimates = reindexing_service.estimate_total_events()

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
