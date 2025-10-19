# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2025 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Core CLI commands for community statistics aggregation and management."""

from pprint import pformat

import arrow
import click
from flask import current_app
from flask.cli import with_appcontext
from halo import Halo

from ..proxies import current_community_stats_service
from ..tasks.aggregation_tasks import format_agg_startup_message
from ..utils.process_manager import ProcessManager


def check_stats_enabled():
    """Check if community stats are enabled."""
    if not current_app.config.get("COMMUNITY_STATS_ENABLED", True):
        raise click.ClickException(
            "Community stats dashboard is disabled. "
            "Set COMMUNITY_STATS_ENABLED=True to enable this command."
        )


def check_scheduled_tasks_enabled(command="aggregate"):
    """Check if scheduled tasks are enabled."""
    if not current_app.config.get("COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED", True):
        message = (
            "Community stats scheduled tasks are disabled. "
            "Set COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED=True to enable "
            "aggregation tasks."
        )
        if command == "aggregate":
            message += " Use --force to bypass this check and run aggregation directly."
        raise click.ClickException(message)


@click.command(name="aggregate")
@click.option(
    "--community-id",
    type=str,
    multiple=True,
    help="The UUID or slug of the community to aggregate stats for",
)
@click.option(
    "--aggregation-type",
    type=str,
    multiple=True,
    help="The type of aggregation to be performed. Can be specified multiple times.",
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
    "--eager/--no-eager",
    default=True,
    help=(
        "Run aggregation eagerly (synchronously). "
        "Use --no-eager for async Celery execution."
    ),
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
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed timing information for each aggregator",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force aggregation even if scheduled tasks are disabled",
)
@with_appcontext
def aggregate_stats_command(
    community_id,
    aggregation_type,
    start_date,
    end_date,
    eager,
    update_bookmark,
    ignore_bookmark,
    verbose,
    force,
):
    r"""Aggregate community record statistics.

    This command manually triggers the aggregation of statistics for one or more
    communities or the global instance. Aggregation processes usage events and
    community events to generate daily statistics.

    If no aggregation type is specified, it will run all configured aggregation
    types. By default these are:

    - community-records-delta-created-agg (currently disabled by default)
    - community-records-delta-published-agg (currently disabled by default)
    - community-records-delta-added-agg
    - community-records-snapshot-created-agg (currently disabled by default)
    - community-records-snapshot-published-agg (currently disabled by default)
    - community-records-snapshot-added-agg
    - community-usage-delta-agg
    - community-usage-snapshot-agg


    Examples:  #

    - invenio community-stats aggregate
    - invenio community-stats aggregate --community-id my-community-id
    - invenio community-stats aggregate --start-date 2024-01-01 --end-date 2024-01-31
    """
    check_stats_enabled()

    if not force:
        check_scheduled_tasks_enabled(command="aggregate")
    else:
        current_app.logger.info(
            "Bypassing scheduled tasks check due to --force flag. "
            "Running aggregation directly."
        )

    community_ids = list(community_id) if community_id else None
    aggregation_types = list(aggregation_type) if aggregation_type else None

    startup_message = format_agg_startup_message(
        community_ids=community_ids,
        aggregation_types=aggregation_types,
        start_date=start_date,
        end_date=end_date,
        eager=eager,
        update_bookmark=update_bookmark,
        ignore_bookmark=ignore_bookmark,
        verbose=verbose,
    )
    click.echo(startup_message)

    with Halo(text="Aggregating stats...", spinner="dots"):
        result = current_community_stats_service.aggregate_stats(
            community_ids=community_ids,
            aggregation_types=aggregation_types,
            start_date=start_date,
            end_date=end_date,
            eager=eager,
            update_bookmark=update_bookmark,
            ignore_bookmark=ignore_bookmark,
            verbose=verbose,
        )

    # Display results
    if isinstance(result, dict) and "timing" in result:
        # Display task ID if available (async mode)
        if "task_id" in result:
            click.echo(f"\nCelery Task ID: {result['task_id']}")

        # Display the pre-formatted report from the task
        if verbose and "formatted_report_verbose" in result:
            click.echo(f"\n{result['formatted_report_verbose']}")
        elif "formatted_report" in result:
            click.echo(f"\n{result['formatted_report']}")
    else:
        click.echo("Aggregation completed successfully.")


@click.command(name="aggregate-background")
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
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed timing information for each aggregator",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force aggregation even if scheduled tasks are disabled",
)
@click.option(
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory to store PID and status files.",
)
@with_appcontext
def aggregate_stats_background_command(
    community_id,
    start_date,
    end_date,
    update_bookmark,
    ignore_bookmark,
    verbose,
    force,
    pid_dir,
):
    r"""Start aggregation in the background with process management.

    This command provides the same functionality as `aggregate` but runs in the
    background with full process management capabilities. It allows you to start
    long-running aggregation processes without blocking the terminal.

    The aggregation runs eagerly (synchronously within the background process),
    not as a Celery task.

    Examples:
    \b
    - invenio community-stats aggregate-background
    - invenio community-stats aggregate-background \\
        --community-id my-community-id
    - invenio community-stats aggregate-background \\
        --start-date 2024-01-01 --end-date 2024-01-31
    - invenio community-stats aggregate-background \\
        --verbose --ignore-bookmark
    - invenio community-stats aggregate-background \\
        --pid-dir /var/run/invenio-community-stats

    Process management:
    \b
    - Monitor: invenio community-stats processes status aggregation
    - Cancel: invenio community-stats processes cancel aggregation
    - View logs: invenio community-stats processes status aggregation \\
        --show-log
    """
    check_stats_enabled()

    # Only check scheduled tasks if not forcing the operation
    if not force:
        check_scheduled_tasks_enabled(command="aggregate")

    # Build the command to run
    cmd = [
        "invenio",
        "community-stats",
        "aggregate",
        "--eager",  # Force eager execution in background process
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

    # Add flag options
    if ignore_bookmark:
        cmd.append("--ignore-bookmark")
    if verbose:
        cmd.append("--verbose")
    if force:
        cmd.append("--force")
    # Note: update-bookmark defaults to True, so we don't need to add it

    process_manager = ProcessManager(
        "aggregation", pid_dir, package_prefix="invenio-community-stats"
    )

    try:
        pid = process_manager.start_background_process(cmd)
        click.echo("\nBackground aggregation started successfully!")
        click.echo(f"Process ID: {pid}")
        click.echo(f"Command: {' '.join(cmd)}")

        click.echo("\nMonitor progress:")
        click.echo("  invenio community-stats processes status aggregation")
        click.echo("  invenio community-stats processes status aggregation --show-log")

        click.echo("\nCancel if needed:")
        click.echo("  invenio community-stats processes cancel aggregation")

    except RuntimeError as e:
        click.echo(f"Failed to start background aggregation: {e}")
        return 1

    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        return 1


@click.command(name="read")
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
@click.option(
    "--query-type",
    type=click.Choice([
        # "community-record-delta-created",
        # "community-record-delta-published",
        "community-record-delta-added",
        # "community-record-snapshot-created",
        # "community-record-snapshot-published",
        "community-record-snapshot-added",
        "community-usage-delta",
        "community-usage-snapshot",
    ]),
    help="Specific query type to run instead of the meta-query.",
)
@with_appcontext
def read_stats_command(community_id, start_date, end_date, query_type):
    r"""Read and display statistics data for a community or instance.

    This command retrieves and displays aggregated statistics data for a
    specific community or the global instance. It can show various types of
    statistics including record counts and usage metrics.

    Available query types:

    \b
    - community-record-delta-created
    - community-record-delta-published
    - community-record-delta-added
    - community-record-snapshot-created
    - community-record-snapshot-published
    - community-record-snapshot-added
    - community-usage-delta
    - community-usage-snapshot

    Examples:

    \b
    - invenio community-stats read
    - invenio community-stats read --community-id my-community
    - invenio community-stats read --start-date 2024-01-01 --end-date 2024-01-31
    - invenio community-stats read --query-type community-usage-delta
    """
    check_stats_enabled()

    if query_type:
        click.echo(
            f"Reading {query_type} stats for community {community_id} "
            f"from {start_date} to {end_date}"
        )
        with Halo(text=f"Reading {query_type} stats...", spinner="dots"):
            success, stats = current_community_stats_service.read_stats(
                community_id,
                start_date=start_date,
                end_date=end_date,
                query_type=query_type,
            )
    else:
        click.echo(
            f"Reading stats for community {community_id} "
            f"from {start_date} to {end_date}"
        )
        with Halo(text="Reading stats...", spinner="dots"):
            success, stats = current_community_stats_service.read_stats(
                community_id, start_date=start_date, end_date=end_date
            )

    if not success:
        click.echo("No data found for the specified date range.")

    click.echo(pformat(stats))


def _abbreviate_agg_name(agg_type):
    """Abbreviate aggregation type name for display."""
    # Remove "community-records" from beginning and "-agg" from end
    name = agg_type
    if name.startswith("community-records-"):
        name = name[18:]  # Remove "community-records-"
    if name.endswith("-agg"):
        name = name[:-4]  # Remove "-agg"
    return name


def _generate_completeness_bar(agg_status, start_date, total_days, bar_length=30):
    """Generate completeness bar and related information for an aggregation.

    Args:
        agg_status: Dictionary containing aggregation status information
        start_date: Arrow object representing the start date for the time range
        total_days: Total number of days in the time range
        bar_length: Length of the bar in characters (default: 30)

    Returns:
        tuple: (bar_string, percentage, days_text)
    """
    import arrow

    if not (
        total_days > 0
        and agg_status.get("first_document_date")
        and agg_status.get("last_document_date")
    ):
        return "[No data available]", 0, ""

    # Calculate the proportion of time covered
    agg_start = arrow.get(agg_status["first_document_date"])
    agg_end = arrow.get(agg_status["last_document_date"])

    # Calculate relative positions within the total time range
    start_offset = max(0, (agg_start - start_date).days)
    expected_total_days = (arrow.utcnow() - agg_start).days + 1
    if start_offset > 0 and expected_total_days > 0:
        start_offset = expected_total_days - agg_status["document_count"]
    end_offset = (agg_end - start_date).days

    # Create the bar
    filled_length = int((end_offset - start_offset) / total_days * bar_length)
    filled_length = max(0, min(filled_length, bar_length))

    # Create the bar visualization
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    # Calculate percentage
    percentage = (end_offset - start_offset) / total_days * 100
    percentage = max(0, min(100, percentage))

    # Show days since last document
    days_text = ""
    if agg_status["days_since_last_document"] is not None:
        days = agg_status["days_since_last_document"]
        if days == 0:
            days_text = " (today)"
        elif days == 1:
            days_text = " (1d ago)"
        else:
            days_text = f" ({days}d ago)"

    return f"[{bar}]", percentage, days_text


@click.command(name="status")
@click.option(
    "--community-id",
    "-c",
    multiple=True,
    type=str,
    help="The ID of the community to check status for. If not provided, "
    "checks all communities. Can be specified multiple times to check status "
    "for multiple communities.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information for each aggregation.",
)
@with_appcontext
def status_command(community_id, verbose):
    r"""Get aggregation status for communities.

    This command provides a comprehensive overview of the aggregation status
    for community statistics. It shows bookmark dates, document counts, and
    completeness visualization for all aggregators.

    The command displays:

    \b
    - Bookmark dates: Current progress bookmarks for all aggregators
    - Document counts: Number of documents in each aggregation index
    - Date ranges: First and last document dates in each index
    - Days since last document: How recently each aggregation was updated
    - Completeness visualization: ASCII bar charts showing the proportion of
      time covered by each aggregation

    Examples:

    \b
    - invenio community-stats status
    - invenio community-stats status --community-id my-community-id
    - invenio community-stats status --verbose
    - invenio community-stats status --community-id comm1 --community-id comm2
    """
    check_stats_enabled()

    with Halo(text="Getting aggregation status...", spinner="dots"):
        community_ids = list(community_id) if community_id else None
        status = current_community_stats_service.get_aggregation_status(community_ids)

    if "error" in status:
        click.echo(f"Error: {status['error']}", err=True)
        return 1

    click.echo("\n" + "=" * 80)
    click.echo("COMMUNITY AGGREGATION STATUS")
    click.echo("=" * 80)

    for community in status["communities"]:
        click.echo(
            f"\nCommunity: {community['community_slug']} ({community['community_id']})"
        )
        click.echo("-" * 60)

        # Calculate the overall time range for completeness visualization
        all_first_dates = []
        for agg_status in community["aggregations"].values():
            if agg_status.get("first_document_date") and agg_status.get(
                "last_document_date"
            ):
                all_first_dates.append(agg_status["first_document_date"])

        # Find the earliest first date across all aggregations
        if all_first_dates:
            earliest_first = min(all_first_dates)
            start_date = arrow.get(earliest_first)
            end_date = arrow.utcnow()
            total_days = (end_date - start_date).days
        else:
            start_date = arrow.utcnow()
            total_days = 0

        for agg_type, agg_status in community["aggregations"].items():
            if verbose:
                # Verbose mode - show detailed information
                click.echo(f"\n{agg_type}:")

                if agg_status["error"]:
                    click.echo(f"  Error: {agg_status['error']}")
                    continue

                if not agg_status["index_exists"]:
                    click.echo("  Index: Does not exist")
                    continue

                click.echo("  Index: Exists")
                click.echo(f"  Document count: {agg_status['document_count']}")

                if agg_status["bookmark_date"]:
                    click.echo(f"  Bookmark date: {agg_status['bookmark_date']}")
                else:
                    click.echo("  Bookmark date: None")

                if agg_status["first_document_date"]:
                    click.echo(f"  First document: {agg_status['first_document_date']}")
                else:
                    click.echo("  First document: None")

                if agg_status["last_document_date"]:
                    click.echo(f"  Last document: {agg_status['last_document_date']}")
                else:
                    click.echo("  Last document: None")

                if agg_status["days_since_last_document"] is not None:
                    days = agg_status["days_since_last_document"]
                    if days == 0:
                        click.echo("  Days since last document: Today")
                    elif days == 1:
                        click.echo("  Days since last document: 1 day")
                    else:
                        click.echo(f"  Days since last document: {days} days")
                else:
                    click.echo("  Days since last document: N/A")

                bar_string, percentage, days_text = _generate_completeness_bar(
                    agg_status, start_date, total_days, bar_length=50
                )
                click.echo(f"  Completeness: {bar_string} {percentage:.1f}%")
            else:
                # Concise mode - show one line per aggregation
                if agg_status["error"]:
                    click.echo(
                        f"{_abbreviate_agg_name(agg_type):<25} "
                        f"[ERROR: {agg_status['error']}]"
                    )
                    continue

                if not agg_status["index_exists"]:
                    click.echo(f"{_abbreviate_agg_name(agg_type):<25} [No index]")
                    continue

                bar_string, percentage, days_text = _generate_completeness_bar(
                    agg_status, start_date, total_days, bar_length=30
                )
                click.echo(
                    f"{_abbreviate_agg_name(agg_type):<25} "
                    f"{bar_string} {percentage:.0f}%{days_text}"
                )

    click.echo("\n" + "=" * 80)
    return 0


@click.command(name="clear-bookmarks")
@click.option(
    "--community-id",
    type=str,
    multiple=True,
    help="The UUID or slug of the community to clear bookmarks for. "
    "Can be specified multiple times.",
)
@click.option(
    "--aggregation-type",
    type=str,
    multiple=True,
    help="The aggregation type to clear bookmarks for. "
    "Can be specified multiple times.",
)
@click.option(
    "--all-communities",
    is_flag=True,
    help="Clear bookmarks for all communities",
)
@click.option(
    "--all-aggregation-types",
    is_flag=True,
    help="Clear bookmarks for all aggregation types",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm that you want to clear bookmarks without prompting",
)
@with_appcontext
def clear_bookmarks_command(
    community_id,
    aggregation_type,
    all_communities,
    all_aggregation_types,
    confirm,
):
    r"""Clear aggregation bookmarks for community statistics.

    This command clears the progress bookmarks that track aggregation state for
    community statistics. When bookmarks are cleared, the next aggregation run
    will start from the beginning of the data range instead of continuing from
    the last processed date.

    Bookmarks are stored per community and per aggregation type, allowing for
    fine-grained control over which bookmarks to clear.

    Available aggregation types:
    - community-records-delta-created-agg (currently disabled by default)
    - community-records-delta-published-agg (currently disabled by default)
    - community-records-delta-added-agg
    - community-records-snapshot-created-agg (currently disabled by default)
    - community-records-snapshot-published-agg (currently disabled by default)
    - community-records-snapshot-added-agg
    - community-usage-delta-agg
    - community-usage-snapshot-agg

    Examples:

    \b
    - invenio community-stats clear-bookmarks --all-communities --all-aggregation-types
    - invenio community-stats clear-bookmarks --community-id my-community-id
    - invenio community-stats clear-bookmarks --aggregation-type \\
        community-records-delta-created-agg
    - invenio community-stats clear-bookmarks --community-id comm1 \\
        --community-id comm2 --confirm
    """
    check_stats_enabled()

    # Validate that we have some criteria for what to clear
    if (
        not community_id
        and not all_communities
        and not aggregation_type
        and not all_aggregation_types
    ):
        click.echo("❌ Error: You must specify at least one of:")
        click.echo(
            "  --community-id, --all-communities, --aggregation-type, "
            "or --all-aggregation-types"
        )
        return 1

    # Convert community_id tuple to list
    community_ids = list(community_id) if community_id else None
    aggregation_types = list(aggregation_type) if aggregation_type else None

    # Show what will be cleared
    click.echo("🗑️  Clearing aggregation bookmarks...")

    if all_communities:
        click.echo("  Communities: ALL")
    elif community_ids:
        click.echo(f"  Communities: {', '.join(community_ids)}")
    else:
        click.echo("  Communities: ALL (default)")

    if all_aggregation_types:
        click.echo("  Aggregation types: ALL")
    elif aggregation_types:
        click.echo(f"  Aggregation types: {', '.join(aggregation_types)}")
    else:
        click.echo("  Aggregation types: ALL (default)")

    # Confirm before proceeding
    if not confirm:
        if not click.confirm("\n⚠️  This will clear aggregation bookmarks. Continue?"):
            click.echo("Operation cancelled.")
            return 0

    # Call the service to clear bookmarks
    try:
        with Halo(text="Clearing bookmarks...", spinner="dots"):
            result = current_community_stats_service.clear_aggregation_bookmarks(
                community_ids=community_ids,
                aggregation_types=aggregation_types,
                all_communities=all_communities,
                all_aggregation_types=all_aggregation_types,
            )

        if not result["success"]:
            click.echo(f"❌ Error: {result['error']}")
            return 1

        # Display results
        total_cleared = result["total_cleared"]
        if total_cleared > 0:
            click.echo(f"\n✅ Successfully cleared {total_cleared} bookmark(s)")

            # Show detailed results
            for comm_id, comm_data in result["cleared"].items():
                comm_slug = comm_data["slug"]
                click.echo(f"\n  Community: {comm_slug} ({comm_id})")

                for agg_type, count in comm_data["aggregation_types"].items():
                    if count > 0:
                        # Abbreviate aggregation type name for display
                        short_name = agg_type.replace("community-records-", "").replace(
                            "-agg", ""
                        )
                        click.echo(f"    {short_name}: {count} bookmark(s)")
        else:
            click.echo("\n📭 No bookmarks were found to clear")

    except Exception as e:
        click.echo(f"❌ Error clearing bookmarks: {str(e)}")
        return 1

    return 0


@click.command(name="clear-lock")
@click.option(
    "--lock-name",
    default="community_stats_aggregation",
    help="Name of the lock to clear (default: community_stats_aggregation)",
)
@click.option(
    "--list-locks",
    is_flag=True,
    help="List all lock keys in the cache",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleared without actually clearing",
)
@with_appcontext
def clear_lock_command(lock_name, list_locks, dry_run):
    r"""Clear stuck invenio-stats-dashboard task locks.

    This command connects to the same Redis cache that invenio-stats-dashboard uses
    and manually removes stuck lock keys that prevent aggregation tasks from running.

    Lock names commonly used:
    - community_stats_aggregation (default)
    - community_stats_cache_generation

    Examples:

    \b
    - invenio community-stats clear-lock
    - invenio community-stats clear-lock --lock-name community_stats_cache_generation
    - invenio community-stats clear-lock --list-locks
    - invenio community-stats clear-lock --dry-run
    """
    check_stats_enabled()

    if list_locks:
        result = current_community_stats_service.list_aggregation_locks()
        if result["success"]:
            click.echo(f"🔍 {result['message']}")
            if result["count"] > 0:
                for lock in result["locks"]:
                    click.echo(f"  - {lock['key']}: {lock['value']}")
            else:
                click.echo("ℹ️  No lock keys found in cache")
        else:
            click.echo(f"❌ {result['message']}")
            return 1
        return 0

    result = current_community_stats_service.clear_aggregation_lock(lock_name, dry_run)

    if result["success"]:
        click.echo(f"ℹ️  {result['message']}")
        if result.get("cleared"):
            click.echo("\n✅ Lock clearing completed successfully!")
            click.echo("You should now be able to run aggregation tasks again.")
        return 0
    else:
        click.echo(f"❌ {result['message']}")
        click.echo("Check your Redis connection and try again.")
        return 1
