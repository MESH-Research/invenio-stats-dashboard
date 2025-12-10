# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Constants for invenio-stats-dashboard."""

from enum import StrEnum


class FirstRunStatus(StrEnum):
    """Status values for first run flags.

    These values are used to track the status of first-time cache generation
    operations.
    """

    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


class RegistryOperation(StrEnum):
    """Operation types for registry keys.

    These values represent the types of operations tracked in the
    StatsAggregationRegistry. The "cache" and "agg_updated" operations include
    placeholders for the year (e.g., "cache_{year}"). Use .format() or .replace()
    to substitute the year value.
    """

    AGG = "agg"
    AGG_UPDATED = "agg_updated_{year}"
    CACHE = "cache_{year}"
    FIRST_RUN = "first_run"

