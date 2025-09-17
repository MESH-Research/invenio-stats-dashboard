# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2025 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Core CLI commands for community statistics aggregation and management."""

from pprint import pprint

import arrow
import click
from flask import current_app
from flask.cli import with_appcontext
from halo import Halo

from ..proxies import current_community_stats_service
from ..tasks import format_agg_startup_message


def check_stats_enabled():
    """Check if community stats are enabled."""
    if not current_app.config.get("COMMUNITY_STATS_ENABLED", True):
        raise click.ClickException(
            "Community stats dashboard is disabled. "
            "Set COMMUNITY_STATS_ENABLED=True to enable this command."
        )


def check_scheduled_tasks_enabled(command="aggregate"):
    """Check if scheduled tasks are enabled."""
    if not current_app.config.get("COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED", True):
        message = (
            "Community stats scheduled tasks are disabled. "
            "Set COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED=True to enable "
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
    start_date,
    end_date,
    eager,
    update_bookmark,
    ignore_bookmark,
    verbose,
    force,
):
    """Aggregate community record statistics."""
    check_stats_enabled()

    # Only check scheduled tasks if not forcing the operation
    if not force:
        check_scheduled_tasks_enabled(command="aggregate")
    else:
        # Log that we're bypassing the scheduled tasks check
        current_app.logger.info(
            "Bypassing scheduled tasks check due to --force flag. "
            "Running aggregation directly."
        )

    community_ids = list(community_id) if community_id else None

    # Display startup configuration using centralized function
    startup_message = format_agg_startup_message(
        community_ids=community_ids,
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
            start_date=start_date,
            end_date=end_date,
            eager=eager,
            update_bookmark=update_bookmark,
            ignore_bookmark=ignore_bookmark,
            verbose=verbose,
            force=force,
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
@with_appcontext
def read_stats_command(community_id, start_date, end_date):
    """Read stats for a community."""
    check_stats_enabled()
    print(f"Reading stats for community {community_id} from {start_date} to {end_date}")
    with Halo(text="Reading stats...", spinner="dots"):
        stats = current_community_stats_service.read_stats(
            community_id, start_date=start_date, end_date=end_date
        )
    pprint(stats)


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
    """Get aggregation status for communities."""
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
            f"\nCommunity: {community['community_slug']} "
            f"({community['community_id']})"
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
