# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Types for the stats dashboard aggregations."""

from typing import TypedDict

# ============================================================================
# Record snapshot aggregation types
# ============================================================================


class RecordTotals(TypedDict, total=False):
    """Totals structure for record aggregation documents."""

    metadata_only: int
    with_files: int


class RecordFilesTotals(TypedDict):
    """Totals structure for record files aggregation documents."""

    file_count: int
    data_volume: float


class RecordSnapshotSubcountItem(TypedDict, total=False):
    """Individual subcount item for record snapshot aggregations."""

    id: str
    label: str
    records: RecordTotals
    parents: RecordTotals
    files: RecordFilesTotals


class RecordSnapshotTopSubcounts(TypedDict, total=False):
    """Subcount data structure for record aggregations."""

    by_view: list[RecordSnapshotSubcountItem]
    by_download: list[RecordSnapshotSubcountItem]


class RecordSnapshotDocument(TypedDict):
    """Snapshot document for record aggregations."""

    timestamp: str
    community_id: str
    snapshot_date: str
    subcounts: dict[str, list[RecordSnapshotSubcountItem] | RecordSnapshotTopSubcounts]
    total_records: RecordTotals
    total_parents: RecordTotals
    total_files: RecordFilesTotals
    total_uploaders: int
    updated_timestamp: str


# ============================================================================
# Record delta aggregation types
# ============================================================================


class RecordDeltaCounts(TypedDict):
    """Counts for record delta aggregations."""

    metadata_only: int
    with_files: int


class RecordFilesDeltaCounts(TypedDict):
    """Counts for record files delta aggregations."""

    file_count: int
    data_volume: float


class RecordDeltaTotals(TypedDict):
    """Totals for record delta aggregations."""

    added: RecordDeltaCounts
    removed: RecordDeltaCounts


class RecordFilesDeltaTotals(TypedDict):
    """Totals for record files delta aggregations."""

    added: RecordFilesDeltaCounts
    removed: RecordFilesDeltaCounts


class RecordDeltaSubcountItem(TypedDict):
    """Individual subcount item for record delta aggregations."""

    id: str
    label: str
    records: RecordDeltaTotals
    parents: RecordDeltaTotals
    files: RecordFilesDeltaTotals


class RecordDeltaDocument(TypedDict, total=False):
    """Delta document for record aggregations."""

    timestamp: str
    community_id: str
    period_start: str
    period_end: str
    records: RecordDeltaTotals
    parents: RecordDeltaTotals
    files: RecordFilesDeltaTotals
    uploaders: int
    subcounts: dict[str, list[RecordDeltaSubcountItem]]
    updated_timestamp: str


# ============================================================================
# Usage aggregation types
# ============================================================================


class UsageViewMetrics(TypedDict):
    """View metrics for usage aggregations."""

    total_events: int
    unique_visitors: int
    unique_records: int
    unique_parents: int


class UsageDownloadMetrics(TypedDict):
    """Download metrics for usage aggregations."""

    total_events: int
    unique_visitors: int
    unique_records: int
    unique_parents: int
    unique_files: int
    total_volume: float


class UsageCategories(TypedDict):
    """Totals structure for usage snapshot documents."""

    view: UsageViewMetrics
    download: UsageDownloadMetrics


class UsageSubcountItem(TypedDict, total=False):
    """Totals structure for usage snapshot subcount items."""

    id: str
    label: str | dict[str, str]
    view: UsageViewMetrics
    download: UsageDownloadMetrics


class UsageSnapshotTopCategories(TypedDict):
    """Subcount data structure for usage snapshot aggregations."""

    by_view: list[UsageSubcountItem]
    by_download: list[UsageSubcountItem]


class UsageSnapshotDocument(TypedDict, total=False):
    """Document structure for usage snapshot aggregations.

    Used by:
    - CommunityUsageSnapshotAggregator
    """

    community_id: str
    snapshot_date: str
    totals: UsageCategories
    subcounts: dict[str, list[UsageSubcountItem] | UsageSnapshotTopCategories]
    timestamp: str
    updated_timestamp: str


class UsageDeltaDocument(TypedDict, total=False):
    """Document structure for usage delta aggregations.

    Used by:
    - CommunityUsageDeltaAggregator
    """

    community_id: str
    period_start: str
    period_end: str
    timestamp: str
    totals: UsageCategories
    subcounts: dict[str, list[UsageSubcountItem]]
