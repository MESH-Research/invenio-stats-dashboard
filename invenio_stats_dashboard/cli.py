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
