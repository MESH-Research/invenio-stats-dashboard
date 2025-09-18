# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Type definitions for data series transformers."""

from typing import Any, TypedDict


class DataPointDict(TypedDict):
    """Type definition for a data point dictionary."""

    value: list[str | int | float]
    readableDate: str
    valueType: str


class DataSeriesDict(TypedDict):
    """Type definition for a data series dictionary."""

    id: str
    name: str
    data: list[DataPointDict]
    type: str
    valueType: str


class GlobalMetricsDict(TypedDict):
    """Type definition for global metrics."""

    records: list[DataSeriesDict]
    parents: list[DataSeriesDict]
    uploaders: list[DataSeriesDict]
    fileCount: list[DataSeriesDict]
    dataVolume: list[DataSeriesDict]


class FilePresenceDict(TypedDict):
    """Type definition for file presence metrics."""

    records: list[DataSeriesDict]
    parents: list[DataSeriesDict]


class SubcountMetricsDict(TypedDict):
    """Type definition for subcount metrics."""

    records: list[DataSeriesDict]
    parents: list[DataSeriesDict]
    uploaders: list[DataSeriesDict]
    fileCount: list[DataSeriesDict]
    dataVolume: list[DataSeriesDict]


class UsageMetricsDict(TypedDict):
    """Type definition for usage metrics."""

    views: list[DataSeriesDict]
    downloads: list[DataSeriesDict]
    visitors: list[DataSeriesDict]
    dataVolume: list[DataSeriesDict]


class FilePresenceUsageDict(TypedDict):
    """Type definition for file presence usage metrics."""

    views: list[DataSeriesDict]
    downloads: list[DataSeriesDict]
    visitors: list[DataSeriesDict]
    dataVolume: list[DataSeriesDict]


class SubcountItemDict(TypedDict):
    """Type definition for a subcount item."""

    id: str
    label: str | dict[str, str]


class SubcountSeriesDict(TypedDict):
    """Type definition for a subcount series."""

    id: str
    label: str | dict[str, str]
    records: dict[str, Any] | None
    parents: dict[str, Any] | None
    uploaders: int | None
    total_uploaders: int | None
    files: dict[str, Any] | None
    view: dict[str, Any] | None
    download: dict[str, Any] | None


class AggregationDocumentDict(TypedDict):
    """Type definition for an aggregation document."""

    period_start: str | None
    snapshot_date: str | None
    records: dict[str, Any] | None
    parents: dict[str, Any] | None
    uploaders: int | None
    total_uploaders: int | None
    files: dict[str, Any] | None
    total_files: dict[str, Any] | None
    total_records: dict[str, Any] | None
    total_parents: dict[str, Any] | None
    totals: dict[str, Any] | None
    subcounts: dict[str, list[SubcountSeriesDict]] | None


# For now, let's use a simpler approach with dict[str, Any] for the main result types
# This avoids the reserved keyword issue with 'global' and keeps the implementation working
RecordDeltaResultDict = dict[str, Any]
RecordSnapshotResultDict = dict[str, Any]
UsageDeltaResultDict = dict[str, Any]
UsageSnapshotResultDict = dict[str, Any]

# Union type for all possible transformation results
TransformationResult = (
    RecordDeltaResultDict
    | RecordSnapshotResultDict
    | UsageDeltaResultDict
    | UsageSnapshotResultDict
)
