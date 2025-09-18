# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Data series transformers for converting indexed documents to chart-ready data."""

from .base import (
    BaseDataSeriesTransformer,
    DataPoint,
    DataSeries,
    create_transformer,
)
from .types import (
    AggregationDocumentDict,
    DataPointDict,
    DataSeriesDict,
    RecordDeltaResultDict,
    RecordSnapshotResultDict,
    TransformationResult,
    UsageDeltaResultDict,
    UsageSnapshotResultDict,
)
from .record_delta import RecordDeltaDataSeriesTransformer
from .record_snapshot import RecordSnapshotDataSeriesTransformer
from .usage_delta import UsageDeltaDataSeriesTransformer
from .usage_snapshot import UsageSnapshotDataSeriesTransformer

__all__ = [
    "AggregationDocumentDict",
    "BaseDataSeriesTransformer",
    "DataPoint",
    "DataPointDict",
    "DataSeries",
    "DataSeriesDict",
    "RecordDeltaDataSeriesTransformer",
    "RecordDeltaResultDict",
    "RecordSnapshotDataSeriesTransformer",
    "RecordSnapshotResultDict",
    "TransformationResult",
    "UsageDeltaDataSeriesTransformer",
    "UsageDeltaResultDict",
    "UsageSnapshotDataSeriesTransformer",
    "UsageSnapshotResultDict",
    "create_transformer",
]
