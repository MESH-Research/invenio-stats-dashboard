#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Mesh Research
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

from ..proxies import current_community_stats_service
from ..tasks import format_agg_startup_message


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
@with_appcontext
def aggregate_stats_command(
    community_id,
    start_date,
    end_date,
    eager,
    update_bookmark,
    ignore_bookmark,
    verbose,
):
    """Aggregate community record statistics."""
    check_stats_enabled()
    check_scheduled_tasks_enabled()

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
