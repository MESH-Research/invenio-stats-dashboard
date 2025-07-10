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


@cli.command(name="reindex-events")
@click.option(
    "--event-types",
    type=click.Choice(["view", "download", "both"]),
    default="both",
    help="Which event types to reindex.",
)
@click.option(
    "--max-batches",
    type=int,
    help="Maximum number of batches to process (for testing).",
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
    "--async",
    "async_mode",
    is_flag=True,
    help="Run reindexing asynchronously using Celery.",
)
@with_appcontext
def reindex_events_command(
    event_types, max_batches, batch_size, max_memory_percent, async_mode
):
    """Reindex events with enriched metadata."""
    if event_types == "both":
        event_types = ["view", "download"]
    elif event_types == "view":
        event_types = ["view"]
    elif event_types == "download":
        event_types = ["download"]

    print(f"Starting event reindexing for: {event_types}")
    print(f"Batch size: {batch_size}")
    print(f"Max memory: {max_memory_percent}%")
    if max_batches:
        print(f"Max batches: {max_batches}")

    if async_mode:
        print("Running asynchronously with Celery...")
        task = reindex_events_with_metadata.delay(
            event_types=event_types,
            max_batches=max_batches,
            batch_size=batch_size,
            max_memory_percent=max_memory_percent,
        )
        print(f"Task ID: {task.id}")
        print("Use 'invenio stats-dashboard get-reindexing-progress' to check progress")
    else:
        print("Running synchronously...")
        reindexing_service = EventReindexingService(app)
        reindexing_service.batch_size = batch_size
        reindexing_service.max_memory_percent = max_memory_percent

        with Halo(text="Reindexing events...", spinner="dots"):
            results = reindexing_service.reindex_events(
                event_types=event_types, max_batches=max_batches
            )

        print("Reindexing completed!")
        pprint(results)


@cli.command(name="get-reindexing-progress")
@with_appcontext
def get_reindexing_progress_command():
    """Get current reindexing progress."""
    reindexing_service = EventReindexingService(app)
    progress = reindexing_service.get_reindexing_progress()

    print("Reindexing Progress:")
    print("=" * 50)

    print("Event Estimates:")
    for event_type, count in progress["estimates"].items():
        print(f"  {event_type}: {count:,} events")

    print("\nBookmarks (Last Processed ID):")
    for event_type, bookmark in progress["bookmarks"].items():
        if bookmark:
            print(f"  {event_type}: {bookmark}")
        else:
            print(f"  {event_type}: Not started")

    print("\nHealth Status:")
    health = progress["health"]
    status = "✅ Healthy" if health["is_healthy"] else "❌ Unhealthy"
    print(f"  Status: {status}")
    print(f"  Memory Usage: {health['memory_usage']:.1f}%")
    if not health["is_healthy"]:
        print(f"  Reason: {health['reason']}")


@cli.command(name="estimate-reindexing")
@with_appcontext
def estimate_reindexing_command():
    """Estimate the total number of events to reindex."""
    reindexing_service = EventReindexingService(app)
    estimates = reindexing_service.estimate_total_events()

    total_events = sum(estimates.values())

    print("Event Reindexing Estimates:")
    print("=" * 40)
    for event_type, count in estimates.items():
        print(f"{event_type:>10}: {count:>10,} events")
    print("-" * 40)
    print(f"{'TOTAL':>10}: {total_events:>10,} events")

    # Rough time estimate (very conservative)
    if total_events > 0:
        batches_needed = total_events / 1000  # Assuming 1000 events per batch
        hours_estimate = batches_needed * 0.1  # Assuming 6 seconds per batch
        print(f"\nRough time estimate: {hours_estimate:.1f} hours")
        print(
            "(This is a very conservative estimate - actual time may vary "
            "significantly)"
        )
