#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

import click
from flask.cli import with_appcontext
from halo import Halo

from ..proxies import current_community_stats_service
from ..utils.process_manager import ProcessManager
from .core_cli import check_stats_enabled


@click.group(name="community-events")
def community_events_cli():
    """Community events commands."""
    pass


@community_events_cli.command(name="generate")
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
@click.option(
    "--start-date",
    type=str,
    help=(
        "Start date for filtering records by creation date (YYYY-MM-DD). "
        "If not provided, uses earliest record creation date."
    ),
)
@click.option(
    "--end-date",
    type=str,
    help=(
        "End date for filtering records by creation date (YYYY-MM-DD). "
        "If not provided, uses current date."
    ),
)
@click.option(
    "--show-progress",
    is_flag=True,
    default=True,
    help=("Show progress information during processing (default: True)."),
)
@with_appcontext
def generate_community_events_command(
    community_id, record_ids, start_date, end_date, show_progress
):
    """
    Generate community events for all records in the instance.

    This produces "added" events indexed in the community-event-stats index
    for any records that do not already have them. If the record is part of
    a community it will add an "added" event for each community it belongs to.
    It will also add an "added" event for the "global" community_id, representing
    all records across the entire instance.

    Since we cannot establish when a record was originally added to a community,
    the record "created" date is used as the event date.
    """
    check_stats_enabled()

    # Show initial configuration
    click.echo("\nStarting to generate stats-community-events documents...")
    click.echo("\n" + "=" * 50)
    if community_id:
        click.echo(f"Communities to process: {', '.join(community_id)}")
    else:
        click.echo("Processing all communities")

    if record_ids:
        click.echo(f"Records to process: {len(record_ids)} specific records")
    else:
        click.echo("Processing all records")

    if start_date:
        click.echo(f"Start date: {start_date}")
    if end_date:
        click.echo(f"End date: {end_date}")

    # First, count how many records need events
    click.echo("\nAnalyzing records to determine scope...")
    with Halo(text="Counting records...", spinner="dots"):
        count_results = current_community_stats_service.count_records_needing_events(
            community_ids=list(community_id) if community_id else None,
            recids=list(record_ids) if record_ids else None,
            start_date=start_date,
            end_date=end_date,
        )

    click.echo(
        f"Found {count_results['records_needing_events']:,} records needing events"
    )
    click.echo(f"Total events to create: {count_results['total_events_needed']:,}")

    if count_results["records_needing_events"] == 0:
        click.echo("\nAll records already have the required community events!")
    else:

        click.echo("\nProcessing records and generating events...")

        with Halo(text="Generating community events...", spinner="dots"):
            results = current_community_stats_service.generate_record_community_events(
                community_ids=list(community_id) if community_id else None,
                recids=list(record_ids) if record_ids else None,
                start_date=start_date,
                end_date=end_date,
            )

        records_processed, new_events_created, old_events_found = results

        click.echo("\n" + "-" * 50)

        click.echo("Summary of community-record-events generation:")
        click.echo(f"  • Records processed: {records_processed:,}")
        click.echo(f"  • New events created: {new_events_created:,}")
        click.echo(f"  • Existing events found: {old_events_found:,}")
        total_events = new_events_created + old_events_found
        click.echo(f"  • Total events in system: {total_events:,}")

        if new_events_created > 0:
            click.echo(
                f"\nSuccessfully created {new_events_created:,} new community events!"
            )
        else:
            click.echo("\nNo new events were created (all events already existed)")

        if old_events_found > 0:
            click.echo(f"Found {old_events_found:,} existing events that were skipped")

    click.echo("\nNext steps:")
    click.echo("  • Check the stats-community-events index for the new events")
    click.echo("  • Use `invenio community-stats community-events status` for ")
    click.echo("      updated counts of records needing events")
    click.echo("  • Run `invenio community-stats usage-events --help` to see how ")
    click.echo("      to migrate view and download events the the enriched format")
    click.echo("  • Run `invenio community-stats aggregate --help` to see how to ")
    click.echo("      update community statistics")


@community_events_cli.command(name="status")
@click.option(
    "--community-id",
    type=str,
    multiple=True,
    help="The ID of the community to check. " "Can be specified multiple times.",
)
@click.option(
    "--record-ids",
    type=str,
    multiple=True,
    help="The IDs of the records to check. " "Can be specified multiple times.",
)
@click.option(
    "--start-date",
    type=str,
    help=(
        "Start date for filtering records by creation date (YYYY-MM-DD). "
        "If not provided, uses earliest record creation date."
    ),
)
@click.option(
    "--end-date",
    type=str,
    help=(
        "End date for filtering records by creation date (YYYY-MM-DD). "
        "If not provided, uses current date."
    ),
)
@click.option(
    "--community-details",
    is_flag=True,
    help="Show detailed community information.",
)
@with_appcontext
def community_events_status_command(
    community_id, record_ids, start_date, end_date, community_details
):
    """
    Count records that need community events created.

    This command analyzes records to determine how many need "added" events
    created for their communities and for the "global" community.
    """
    check_stats_enabled()

    click.echo("\n" + "=" * 60)
    click.echo("Community addition/removal event indexing status")
    click.echo("=" * 60)
    click.echo("\nCounting records lacking events in stats-community-events index...")
    if community_id:
        click.echo(f"  Communities to check: {', '.join(community_id)}")
    else:
        click.echo("  Checking all communities")

    if record_ids:
        click.echo(f"  Records to check: {len(record_ids)} specific records")
    else:
        click.echo("  Checking all records")

    if start_date:
        click.echo(f"  Start date: {start_date}")
    if end_date:
        click.echo(f"  End date: {end_date}")

    with Halo(text="Analyzing records...", spinner="dots"):
        results = current_community_stats_service.count_records_needing_events(
            community_ids=list(community_id) if community_id else None,
            recids=list(record_ids) if record_ids else None,
            start_date=start_date,
            end_date=end_date,
        )

    # Display results
    click.echo("\n" + "-" * 50)

    click.echo("Summary of community-record-events indexing:")
    click.echo(f"  • Total records found: {results['total_records']:,}")
    click.echo(f"  • Records missing events: {results['records_needing_events']:,}")
    click.echo(f"  • Total events missing: {results['total_events_needed']:,}")

    if results["records_needing_events"] > 0 and community_details:
        click.echo("\nBreakdown by community:")
        for community_id, count in sorted(results["community_breakdown"].items()):
            click.echo(f"  • {community_id}: {count:,} events needed")

    if community_details:
        click.echo(
            f"\nCommunities checked: {', '.join(results['communities_checked'])}"
        )

    if results["records_needing_events"] > 0:
        click.echo("\nTo generate these events, run:")
        click.echo("  invenio community-stats community-events generate")
        if community_id:
            for cid in community_id:
                click.echo(f"    --community-id {cid}")
        if start_date:
            click.echo(f"    --start-date {start_date}")
        if end_date:
            click.echo(f"    --end-date {end_date}")
    click.echo("\n")


@community_events_cli.command(name="generate-background")
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
@click.option(
    "--start-date",
    type=str,
    help=(
        "Start date for filtering records by creation date (YYYY-MM-DD). "
        "If not provided, uses earliest record creation date."
    ),
)
@click.option(
    "--end-date",
    type=str,
    help=(
        "End date for filtering records by creation date (YYYY-MM-DD). "
        "If not provided, uses current date."
    ),
)
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory to store PID and status files.",
)
@with_appcontext
def generate_community_events_background_command(
    community_id, record_ids, start_date, end_date, pid_dir
):
    """Start community event generation in the background with process management.

    This command provides the same functionality as `community-events generate` but runs
    in the background with full process management capabilities.
    """
    check_stats_enabled()

    # Build the command to run
    cmd = [
        "invenio",
        "community-stats",
        "community-events",
        "generate",
    ]

    # Define option mappings for cleaner command building
    option_mappings = [
        ("--start-date", start_date),
        ("--end-date", end_date),
    ]

    # Add single-value options
    for option, value in option_mappings:
        if value:
            cmd.extend([option, value])

    # Add multi-value options
    if community_id:
        for cid in community_id:
            cmd.extend(["--community-id", cid])

    if record_ids:
        for rid in record_ids:
            cmd.extend(["--record-ids", rid])

    process_manager = ProcessManager(
        "community-event-generation", pid_dir, package_prefix="invenio-community-stats"
    )

    try:
        pid = process_manager.start_background_process(cmd)
        click.echo("\nBackground event generation started successfully!")
        click.echo(f"Process ID: {pid}")
        click.echo(f"Command: {' '.join(cmd)}")

        click.echo("\nMonitor progress:")
        click.echo(
            "  invenio community-stats processes status community-event-generation"
        )
        click.echo(
            "  invenio community-stats processes status "
            "community-event-generation --show-log"
        )

        click.echo("\nCancel if needed:")
        click.echo(
            "  invenio community-stats processes cancel community-event-generation"
        )

    except RuntimeError as e:
        click.echo(f"Failed to start background event generation: {e}")
        return 1

    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        return 1
