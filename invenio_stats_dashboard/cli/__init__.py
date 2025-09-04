#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

import click

from .community_events_cli import community_events_cli
from .core_cli import aggregate_stats_command, read_stats_command
from .processes_cli import processes_cli
from .usage_events_cli import usage_events_cli


@click.group()
def cli():
    """Community stats dashboard CLI."""
    pass


# Register the core commands
cli.add_command(aggregate_stats_command)
cli.add_command(read_stats_command)

# Register the community-events subcommand group
cli.add_command(community_events_cli)

# Register the usage-events subcommand group
cli.add_command(usage_events_cli)

# Register the processes subcommand group
cli.add_command(processes_cli)
