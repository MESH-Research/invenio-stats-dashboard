# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the data series transformers."""

from invenio_stats_dashboard.transformers.record_deltas import RecordDeltaDataSeriesSet
from invenio_stats_dashboard.transformers.record_snapshots import (
    RecordSnapshotDataSeriesSet,
)
from invenio_stats_dashboard.transformers.types import AggregationDocumentDict
from invenio_stats_dashboard.transformers.usage_deltas import UsageDeltaDataSeriesSet
from invenio_stats_dashboard.transformers.usage_snapshots import (
    UsageSnapshotDataSeriesSet,
)
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
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 59117831.0, "file_count": 2},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "resource_types": [
                        {
                            "id": "textDocument-journalArticle",
                            "label": {"en": "Journal Article"},
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 29558915.5, "file_count": 1},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "languages": [
                        {
                            "id": "eng",
                            "label": {"en": "English"},
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 59117831.0, "file_count": 2},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "subjects": [
                        {
                            "id": "http://id.worldcat.org/fast/855500",
                            "label": "Children of prisoners--Services for",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 29558915.5, "file_count": 1},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "rights": [
                        {
                            "id": "cc-by-sa-4.0",
                            "label": {
                                "en": (
                                    "Creative Commons Attribution-ShareAlike 4.0"
                                    " International"
                                )
                            },
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 59117831.0, "file_count": 2},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "funders": [
                        {
                            "id": "00k4n6c31",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 29558915.5, "file_count": 1},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "periodicals": [
                        {
                            "id": "N/A",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 29558915.5, "file_count": 1},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "publishers": [
                        {
                            "id": "Knowledge Commons",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 59117831.0, "file_count": 2},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        }
                    ],
                    "affiliations": [
                        {
                            "id": "013v4ng57",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 29558915.5, "file_count": 1},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        },
                        {
                            "id": "03rmrcq20",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 1},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 29558915.5, "file_count": 1},
                                "removed": {"data_volume": 0.0, "file_count": 0},
                            },
                        },
                    ],
                    "countries": [],  # Empty - no data
                    "referrers": [],  # Empty - no data
                    "file_types": [
                        {
                            "id": "pdf",
                            "label": "",
                            "records": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "parents": {
                                "added": {"metadata_only": 0, "with_files": 2},
                                "removed": {"metadata_only": 0, "with_files": 0},
                            },
                            "files": {
                                "added": {"data_volume": 59117831.0, "file_count": 2},
                                "removed": {"data_volume": 0.0, "file_count": 0},
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
                    "resource_types": [],
                    "languages": [],
                    "subjects": [],
                    "rights": [],
                    "funders": [],
                    "periodicals": [],
                    "publishers": [],
                    "affiliations": [],
                    "countries": [],
                    "referrers": [],
                    "file_types": [],
                },
            },
        ]

        # Create the series set
        series_set = RecordDeltaDataSeriesSet(documents)

        # Build the data series
        result = series_set.build()

        # Verify the structure - check all expected subcounts
        assert "global" in result

        # All subcounts that have "records" configuration
        expected_subcounts = [
            "access_statuses",
            "resource_types",
            "languages",
            "subjects",
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "countries",
            "referrers",
            "file_types",
        ]

        for subcount in expected_subcounts:
            assert subcount in result, f"Missing subcount: {subcount}"

        # Check global metrics
        global_metrics = [
            "records",
            "parents",
            "uploaders",
            "file_count",
            "data_volume",
        ]
        for metric in global_metrics:
            assert metric in result["global"], f"Missing global metric: {metric}"

        # Check subcount metrics for all subcounts with data
        subcounts_with_data = [
            "access_statuses",
            "resource_types",
            "languages",
            "subjects",
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "file_types",
        ]

        # Subcount metrics (same as global but without uploaders)
        subcount_metrics = ["records", "parents", "file_count", "data_volume"]

        for subcount in subcounts_with_data:
            for metric in subcount_metrics:
                assert (
                    metric in result[subcount]
                ), f"Missing metric {metric} in subcount {subcount}"

        # Verify data points exist
        assert len(result["global"]["records"]) == 1  # Single global series

        # Check that subcounts with data have series
        for subcount in subcounts_with_data:
            assert (
                len(result[subcount]["records"]) == 1
            ), f"Expected 1 series for {subcount} records"

        # Check that empty subcounts (countries, referrers) have no series
        for subcount in ["countries", "referrers"]:
            assert (
                len(result[subcount]["records"]) == 0
            ), f"Expected 0 series for empty {subcount} records"

        # Check that file_presence special subcount exists
        assert "file_presence" in result
        assert "metadata_only" in result["file_presence"]
        assert "with_files" in result["file_presence"]

        # Check that file_presence has series
        assert len(result["file_presence"]["metadata_only"]) == 1
        assert len(result["file_presence"]["with_files"]) == 1

        # Verify data point format matches JavaScript dataTransformer.js
        global_records_series = result["global"]["records"][0]
        assert "data" in global_records_series
        assert len(global_records_series["data"]) == 2  # Two data points (two days)

        # Check first data point format: [date, value] array
        first_data_point = global_records_series["data"][0]
        assert "value" in first_data_point
        assert isinstance(first_data_point["value"], list)
        assert len(first_data_point["value"]) == 2  # [date, value] array
        assert first_data_point["value"][0] == "2025-05-30"  # date string
        assert first_data_point["value"][1] == 2  # net value (added - removed)

        # Check readableDate is localized (not just the raw date)
        assert "readableDate" in first_data_point
        assert first_data_point["readableDate"] != "2025-05-30"  # Should be localized
        assert "2025" in first_data_point["readableDate"]  # Should contain year

        # Check valueType
        assert "valueType" in first_data_point
        assert first_data_point["valueType"] == "number"


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
                    "resource_types": [],
                    "languages": [],
                    "subjects": [],
                    "rights": [],
                    "funders": [],
                    "periodicals": [],
                    "publishers": [],
                    "affiliations": [],
                    "countries": [],
                    "referrers": [],
                    "file_types": [],
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

        # Verify data point format matches JavaScript dataTransformer.js
        global_views_series = result["global"]["views"][0]
        assert "data" in global_views_series
        assert len(global_views_series["data"]) == 1  # One data point

        # Check data point format: [date, value] array
        data_point = global_views_series["data"][0]
        assert "value" in data_point
        assert isinstance(data_point["value"], list)
        assert len(data_point["value"]) == 2  # [date, value] array
        assert data_point["value"][0] == "2025-06-01"  # date string
        assert data_point["value"][1] == 3  # view events value

        # Check readableDate is localized
        assert "readableDate" in data_point
        assert data_point["readableDate"] != "2025-06-01"  # Should be localized
        assert "2025" in data_point["readableDate"]  # Should contain year

        # Check valueType
        assert "valueType" in data_point
        assert data_point["valueType"] == "number"

        # Verify data point format matches JavaScript dataTransformer.js
        global_views_series = result["global"]["views"][0]
        assert "data" in global_views_series
        assert len(global_views_series["data"]) == 1  # One data point

        # Check data point format: [date, value] array
        data_point = global_views_series["data"][0]
        assert "value" in data_point
        assert isinstance(data_point["value"], list)
        assert len(data_point["value"]) == 2  # [date, value] array
        assert data_point["value"][0] == "2025-06-01"  # date string
        assert data_point["value"][1] == 3  # view events value

        # Check readableDate is localized
        assert "readableDate" in data_point
        assert data_point["readableDate"] != "2025-06-01"  # Should be localized
        assert "2025" in data_point["readableDate"]  # Should contain year

        # Check valueType
        assert "valueType" in data_point
        assert data_point["valueType"] == "number"

        # Check that all expected subcounts are present
        expected_subcounts = [
            "access_statuses",
            "resource_types",
            "languages",
            "subjects",
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "countries",
            "referrers",
            "file_types",
        ]

        for subcount in expected_subcounts:
            assert subcount in result, f"Missing subcount: {subcount}"

    def test_usage_delta_all_subcounts(self, running_app: RunningApp):
        """Test UsageDeltaDataSeriesSet with all available subcounts."""
        documents: list[AggregationDocumentDict] = [
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
                    "resource_types": [
                        {
                            "download": {
                                "total_events": 2,
                                "total_volume": 2048.0,
                                "unique_files": 2,
                                "unique_parents": 2,
                                "unique_records": 2,
                                "unique_visitors": 2,
                            },
                            "id": "textDocument-journalArticle",
                            "label": {"en": "Journal Article"},
                            "view": {
                                "total_events": 2,
                                "unique_parents": 2,
                                "unique_records": 2,
                                "unique_visitors": 2,
                            },
                        }
                    ],
                    "languages": [
                        {
                            "download": {
                                "total_events": 1,
                                "total_volume": 1024.0,
                                "unique_files": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                            "id": "eng",
                            "label": {"en": "English"},
                            "view": {
                                "total_events": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                        }
                    ],
                    "subjects": [],
                    "rights": [],
                    "funders": [],
                    "periodicals": [],
                    "publishers": [],
                    "affiliations": [],
                    "countries": [
                        {
                            "download": {
                                "total_events": 1,
                                "total_volume": 512.0,
                                "unique_files": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                            "id": "US",
                            "label": "",
                            "view": {
                                "total_events": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                        }
                    ],
                    "referrers": [
                        {
                            "download": {
                                "total_events": 1,
                                "total_volume": 256.0,
                                "unique_files": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                            "id": "google.com",
                            "label": "",
                            "view": {
                                "total_events": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                        }
                    ],
                    "file_types": [
                        {
                            "download": {
                                "total_events": 1,
                                "total_volume": 128.0,
                                "unique_files": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
                            },
                            "id": "pdf",
                            "label": "",
                            "view": {
                                "total_events": 1,
                                "unique_parents": 1,
                                "unique_records": 1,
                                "unique_visitors": 1,
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
        series_set = UsageDeltaDataSeriesSet(documents)

        # Build the data series
        result = series_set.build()

        # Verify all expected subcounts are present
        expected_subcounts = [
            "access_statuses",
            "resource_types",
            "languages",
            "subjects",
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "countries",
            "referrers",
            "file_types",
        ]

        for subcount in expected_subcounts:
            assert subcount in result, f"Missing subcount: {subcount}"

        # Check that subcounts with data have series
        subcounts_with_data = [
            "access_statuses",
            "resource_types",
            "languages",
            "countries",
            "referrers",
            "file_types",
        ]

        for subcount in subcounts_with_data:
            assert (
                len(result[subcount]["views"]) == 1
            ), f"Expected 1 series for {subcount} views"
            assert (
                len(result[subcount]["downloads"]) == 1
            ), f"Expected 1 series for {subcount} downloads"

        # Check that empty subcounts have no series
        empty_subcounts = [
            "subjects",
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
        ]
        for subcount in empty_subcounts:
            assert (
                len(result[subcount]["views"]) == 0
            ), f"Expected 0 series for empty {subcount} views"
            assert (
                len(result[subcount]["downloads"]) == 0
            ), f"Expected 0 series for empty {subcount} downloads"

    def test_usage_delta_metric_discovery(self, running_app: RunningApp):
        """Test metric discovery functionality."""
        documents: list[dict] = [
            {
                "community_id": "59e77d51-3758-409a-813f-efc0d2db1a5e",
                "period_end": "2025-06-01T23:59:59",
                "period_start": "2025-06-01T00:00:00",
                "subcounts": {},
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

        series_set = UsageDeltaDataSeriesSet(documents)

        # Test metric discovery
        metrics = series_set._discover_metrics_from_documents()

        # Check that all expected metrics are discovered
        expected_metrics = [
            "views",
            "downloads",
            "view_visitors",
            "download_visitors",
            "dataVolume",
            "view_unique_parents",
            "view_unique_records",
            "download_unique_files",
            "download_unique_parents",
            "download_unique_records",
        ]

        for metric in expected_metrics:
            assert metric in metrics["global"], f"Missing discovered metric: {metric}"
            assert (
                metric in metrics["subcount"]
            ), f"Missing discovered subcount metric: {metric}"


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

        # Verify data point format matches JavaScript dataTransformer.js
        global_views_series = result["global"]["views"][0]
        assert "data" in global_views_series
        assert len(global_views_series["data"]) == 1  # One data point

        # Check data point format: [date, value] array
        data_point = global_views_series["data"][0]
        assert "value" in data_point
        assert isinstance(data_point["value"], list)
        assert len(data_point["value"]) == 2  # [date, value] array
        assert data_point["value"][0] == "2025-06-01"  # date string
        assert data_point["value"][1] == 3  # view events value

        # Check readableDate is localized
        assert "readableDate" in data_point
        assert data_point["readableDate"] != "2025-06-01"  # Should be localized
        assert "2025" in data_point["readableDate"]  # Should contain year

        # Check valueType
        assert "valueType" in data_point
        assert data_point["valueType"] == "number"
