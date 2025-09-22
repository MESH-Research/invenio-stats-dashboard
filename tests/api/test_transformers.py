# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the data series transformers."""

from invenio_stats_dashboard.transformers.record_deltas import RecordDeltaDataSeriesSet
from invenio_stats_dashboard.transformers.usage_deltas import UsageDeltaDataSeriesSet
from invenio_stats_dashboard.transformers.usage_snapshots import (
    UsageSnapshotDataSeriesSet,
)
from invenio_stats_dashboard.transformers.types import AggregationDocumentDict
from tests.conftest import RunningApp


class TestRecordDeltaDataSeriesSet:
    """Test RecordDeltaDataSeriesSet functionality."""

    def test_record_delta_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of RecordDeltaDataSeriesSet with sample documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2025-05-30T00:00:00",
                "records": {
                    "added": {"metadata_only": 0, "with_files": 2},
                    "removed": {"metadata_only": 0, "with_files": 0},
                },
                "parents": {
                    "added": {"metadata_only": 0, "with_files": 2},
                    "removed": {"metadata_only": 0, "with_files": 0},
                },
                "uploaders": 1,
                "files": {
                    "added": {"data_volume": 59117831.0, "file_count": 2},
                    "removed": {"data_volume": 0.0, "file_count": 0},
                },
                "subcounts": {
                    "access_statuses": [
                        {
                            "id": "open",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                        }
                    ],
                    "file_types": [
                        {
                            "id": "pdf",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                        }
                    ],
                },
            },
            {
                "period_start": "2025-05-31T00:00:00",
                "records": {
                    "added": {"metadata_only": 0, "with_files": 0},
                    "removed": {"metadata_only": 0, "with_files": 0},
                },
                "parents": {
                    "added": {"metadata_only": 0, "with_files": 0},
                    "removed": {"metadata_only": 0, "with_files": 0},
                },
                "uploaders": 0,
                "files": {
                    "added": {"data_volume": 0.0, "file_count": 0},
                    "removed": {"data_volume": 0.0, "file_count": 0},
                },
                "subcounts": {
                    "access_statuses": [],
                    "file_types": [],
                },
            },
        ]

        # Create the series set
        series_set = RecordDeltaDataSeriesSet(documents)

        # Build the data series
        result = series_set.build()

        # Verify the structure
        assert "global" in result
        assert "access_statuses" in result
        assert "file_types" in result

        # Check global metrics
        assert "records" in result["global"]
        assert "parents" in result["global"]
        assert "uploaders" in result["global"]
        assert "file_count" in result["global"]
        assert "data_volume" in result["global"]

        # Check subcount metrics
        assert "records" in result["access_statuses"]
        assert "records" in result["file_types"]

        # Verify data points exist
        assert len(result["global"]["records"]) == 1  # Single global series
        assert (
            len(result["access_statuses"]["records"]) == 1
        )  # One access status series
        assert len(result["file_types"]["records"]) == 1  # One file type series


class TestUsageDeltaDataSeriesSet:
    """Test UsageDeltaDataSeriesSet functionality."""

    def test_usage_delta_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of UsageDeltaDataSeriesSet with sample documents."""
        documents: list[dict] = [
            {
                "community_id": "59e77d51-3758-409a-813f-efc0d2db1a5e",
                "period_end": "2025-06-01T23:59:59",
                "period_start": "2025-06-01T00:00:00",
                "subcounts": {
                    "access_statuses": [
                        {
                            "download": {
                                "total_events": 3,
                                "total_volume": 3072.0,
                                "unique_files": 3,
                                "unique_parents": 3,
                                "unique_records": 3,
                                "unique_visitors": 3,
                            },
                            "id": "metadata-only",
                            "label": "",
                            "view": {
                                "total_events": 3,
                                "unique_parents": 3,
                                "unique_records": 3,
                                "unique_visitors": 3,
                            },
                        }
                    ],
                },
                "timestamp": "2025-07-03T19:37:10",
                "totals": {
                    "download": {
                        "total_events": 3,
                        "total_volume": 3072.0,
                        "unique_files": 3,
                        "unique_parents": 3,
                        "unique_records": 3,
                        "unique_visitors": 3,
                    },
                    "view": {
                        "total_events": 3,
                        "unique_parents": 3,
                        "unique_records": 3,
                        "unique_visitors": 3,
                    },
                },
            },
        ]

        # Create the series set
        series_set = UsageDeltaDataSeriesSet(documents)  # type: ignore

        # Build the data series
        result = series_set.build()

        # Verify the structure
        assert "global" in result
        assert "access_statuses" in result

        # Check core metrics (matching dataTransformer.js)
        assert "views" in result["global"]
        assert "downloads" in result["global"]
        assert "view_visitors" in result["global"]
        assert "download_visitors" in result["global"]
        assert "dataVolume" in result["global"]

        # Check additional metrics (discovered dynamically)
        assert "view_unique_parents" in result["global"]
        assert "view_unique_records" in result["global"]
        assert "download_unique_files" in result["global"]
        assert "download_unique_parents" in result["global"]
        assert "download_unique_records" in result["global"]

        # Check subcount metrics
        assert "views" in result["access_statuses"]
        assert "downloads" in result["access_statuses"]
        assert "view_visitors" in result["access_statuses"]
        assert "download_visitors" in result["access_statuses"]
        assert "dataVolume" in result["access_statuses"]
        assert "view_unique_parents" in result["access_statuses"]
        assert "view_unique_records" in result["access_statuses"]
        assert "download_unique_files" in result["access_statuses"]

        # Verify data points exist
        assert len(result["global"]["views"]) == 1  # Single global series
        assert len(result["access_statuses"]["views"]) == 1  # One access status series


class TestUsageSnapshotDataSeriesSet:
    """Test UsageSnapshotDataSeriesSet functionality."""

    def test_usage_snapshot_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of UsageSnapshotDataSeriesSet with sample documents."""
        documents: list[dict] = [
            {
                "community_id": "59e77d51-3758-409a-813f-efc0d2db1a5e",
                "snapshot_date": "2025-06-01T23:59:59",
                "subcounts": {
                    "access_statuses": [
                        {
                            "download": {
                                "total_events": 3,
                                "total_volume": 3072.0,
                                "unique_files": 3,
                                "unique_parents": 3,
                                "unique_records": 3,
                                "unique_visitors": 3,
                            },
                            "id": "metadata-only",
                            "label": "",
                            "view": {
                                "total_events": 3,
                                "unique_parents": 3,
                                "unique_records": 3,
                                "unique_visitors": 3,
                            },
                        }
                    ],
                },
                "timestamp": "2025-07-03T19:37:10",
                "totals": {
                    "download": {
                        "total_events": 3,
                        "total_volume": 3072.0,
                        "unique_files": 3,
                        "unique_parents": 3,
                        "unique_records": 3,
                        "unique_visitors": 3,
                    },
                    "view": {
                        "total_events": 3,
                        "unique_parents": 3,
                        "unique_records": 3,
                        "unique_visitors": 3,
                    },
                },
            },
        ]

        # Create the series set
        series_set = UsageSnapshotDataSeriesSet(documents)  # type: ignore

        # Build the data series
        result = series_set.build()

        # Verify the structure
        assert "global" in result
        assert "access_statuses" in result

        # Check core metrics (matching dataTransformer.js)
        assert "views" in result["global"]
        assert "downloads" in result["global"]
        assert "view_visitors" in result["global"]
        assert "download_visitors" in result["global"]
        assert "dataVolume" in result["global"]

        # Check additional metrics (discovered dynamically)
        assert "view_unique_parents" in result["global"]
        assert "view_unique_records" in result["global"]
        assert "download_unique_files" in result["global"]
        assert "download_unique_parents" in result["global"]
        assert "download_unique_records" in result["global"]

        # Check subcount metrics
        assert "views" in result["access_statuses"]
        assert "downloads" in result["access_statuses"]
        assert "view_visitors" in result["access_statuses"]
        assert "download_visitors" in result["access_statuses"]
        assert "dataVolume" in result["access_statuses"]
        assert "view_unique_parents" in result["access_statuses"]
        assert "view_unique_records" in result["access_statuses"]
        assert "download_unique_files" in result["access_statuses"]

        # Verify data points exist
        assert len(result["global"]["views"]) == 1  # Single global series
        assert len(result["access_statuses"]["views"]) == 1  # One access status series
