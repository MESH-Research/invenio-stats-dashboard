# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2023-2024 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""CLI commands for the stats dashboard."""

import click

from .cache_cli import cache_cli
from .community_events_cli import community_events_cli
from .core_cli import (
    aggregate_stats_background_command,
    aggregate_stats_command,
    clear_bookmarks_command,
    read_stats_command,
    status_command,
)
from .destroy_indices_cli import destroy_indices_command
from .processes_cli import processes_cli
from .usage_events_cli import usage_events_cli


@click.group()
def cli():
    """Community stats dashboard CLI."""
    pass


cli.add_command(aggregate_stats_command)
cli.add_command(aggregate_stats_background_command)
cli.add_command(clear_bookmarks_command)
cli.add_command(read_stats_command)
cli.add_command(status_command)
cli.add_command(destroy_indices_command)

cli.add_command(cache_cli)
cli.add_command(community_events_cli)
cli.add_command(usage_events_cli)
cli.add_command(processes_cli)
