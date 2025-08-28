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

from .core_cli import check_stats_enabled
from ..proxies import current_community_stats_service
from ..utils.process_manager import ProcessManager


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
@with_appcontext
def generate_community_events_command(community_id, record_ids):
    """
    Generate community events for all records in the instance.
    """
    check_stats_enabled()
    current_community_stats_service.generate_record_community_events(
        community_ids=list(community_id) if community_id else None,
        recids=list(record_ids) if record_ids else None,
    )


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
    "--pid-dir",
    type=str,
    default="/tmp",
    help="Directory to store PID and status files.",
)
@with_appcontext
def generate_community_events_background_command(community_id, record_ids, pid_dir):
    """Start community event generation in the background with process management.

    This command provides the same functionality as generate-community-events but runs
    in the background with full process management capabilities.
    """
    check_stats_enabled()

    # Build the command to run
    cmd = [
        "invenio",
        "community-stats",
        "generate-community-events",
    ]

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
        click.echo("\n🎯 Background event generation started successfully!")
        click.echo(f"Process ID: {pid}")
        click.echo(f"Command: {' '.join(cmd)}")

        click.echo("\n📊 Monitor progress:")
        click.echo(
            "  invenio community-stats process-status community-event-generation"
        )
        click.echo(
            "  invenio community-stats process-status "
            "community-event-generation --show-log"
        )

        click.echo("\n🛑 Cancel if needed:")
        click.echo(
            "  invenio community-stats cancel-process community-event-generation"
        )

    except RuntimeError as e:
        click.echo(f"❌ Failed to start background event generation: {e}")
        return 1

    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        return 1
