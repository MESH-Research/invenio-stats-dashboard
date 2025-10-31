# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the data series transformers."""

from pprint import pformat

from flask import current_app

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
from tests.helpers.sample_stats_data.sample_record_delta_docs import (
    MOCK_RECORD_DELTA_DOCS_2,
)
from tests.helpers.sample_stats_data.sample_record_snapshot_docs import (
    MOCK_RECORD_SNAPSHOT_DOCS,
)
from tests.helpers.sample_stats_data.sample_usage_delta_docs import (
    MOCK_USAGE_DELTA_DOCS_2,
)
from tests.helpers.sample_stats_data.sample_usage_snapshot_docs import (
    MOCK_USAGE_SNAPSHOT_DOCS,
)


class TestRecordDeltaDataSeriesSet:
    """Test RecordDeltaDataSeriesSet functionality."""

    def test_record_delta_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of RecordDeltaDataSeriesSet with sample documents."""
        documents: list[AggregationDocumentDict] = MOCK_RECORD_DELTA_DOCS_2  # type:ignore

        series_set = RecordDeltaDataSeriesSet(documents)
        result = series_set.build()

        current_app.logger.error(f"RecordDeltaDataSeriesSet {pformat(result)}")

        # Verify the structure - check all expected subcounts
        assert "global" in result

        # All subcounts that have "records" configuration
        expected_subcounts = [
            "access_statuses",
            "resource_types",
            "languages",
            # subjects disabled for usage events
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "countries",
            # referrers disabled for usage events
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
                assert metric in result[subcount], (
                    f"Missing metric {metric} in subcount {subcount}"
                )

        # Verify data points exist
        assert len(result["global"]["records"]) == 1  # Single global series

        # Check that subcounts with data have series
        for subcount in subcounts_with_data:
            series_count = len(documents[0]["subcounts"][subcount])  # type: ignore
            assert len(result[subcount]["records"]) == series_count, (
                f"Expected {series_count} series for {subcount} records"
            )

        # Check that empty subcounts (countries, referrers) have no series
        for subcount in ["countries", "referrers"]:
            assert len(result[subcount]["records"]) == 0, (
                f"Expected 0 series for empty {subcount} records"
            )

        # Check that file_presence special subcount exists
        assert "file_presence" in result
        assert "records" in result["file_presence"]
        assert "parents" in result["file_presence"]
        assert "file_count" in result["file_presence"]
        assert "data_volume" in result["file_presence"]

        # Check that file_presence has series
        assert len(result["file_presence"]["records"]) == 2
        assert len(result["file_presence"]["parents"]) == 2
        assert len(result["file_presence"]["file_count"][0]["data"]) == 2

        # Verify data point format is correct
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

        # Verify file volume data is correct format
        global_data_volume_series = result["subjects"]["data_volume"][0]
        assert global_data_volume_series["data"][0]["valueType"] == "filesize"


class TestRecordSnapshotDataSeriesSet:
    """Test RecordSnapshotDataSeriesSet functionality."""

    def test_record_snapshot_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of RecordSnapshotDataSeriesSet."""
        documents: list[AggregationDocumentDict] = [
            MOCK_RECORD_SNAPSHOT_DOCS[0]["_source"],
            MOCK_RECORD_SNAPSHOT_DOCS[1]["_source"],
        ]

        series_set = RecordSnapshotDataSeriesSet(documents)
        result = series_set.build()

        # Verify the top-level structure
        assert "global" in result

        expected_subcounts = [
            "access_statuses",
            "file_types",
            "resource_types",
            "affiliations",
            "funders",
            "languages",
            "periodicals",
            "publishers",
            "rights",
            "subjects",
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
            "file_types",
            "resource_types",
            "affiliations",
            "funders",
            "languages",
            "periodicals",
            "publishers",
            "rights",
            "subjects",
        ]

        # Subcount metrics (same as global but without uploaders)
        subcount_metrics = ["records", "parents", "file_count", "data_volume"]

        for subcount in subcounts_with_data:
            for metric in subcount_metrics:
                assert metric in result[subcount], (
                    f"Missing metric {metric} in subcount {subcount}"
                )

        # Verify data points exist
        assert len(result["global"]["records"]) == 1  # Single global series

        # Check that subcounts with data have series
        for subcount in subcounts_with_data:
            series_count = len(documents[0]["subcounts"][subcount])  # type: ignore
            assert len(result[subcount]["records"]) == series_count, (
                f"Expected {series_count} series for {subcount} records"
            )

        # Check that file_presence special subcount exists
        assert "file_presence" in result
        assert "records" in result["file_presence"]
        assert "parents" in result["file_presence"]
        assert "file_count" in result["file_presence"]
        assert "data_volume" in result["file_presence"]

        # Check that file_presence has series
        assert len(result["file_presence"]["records"]) == 2
        assert len(result["file_presence"]["parents"]) == 2
        assert len(result["file_presence"]["file_count"][0]["data"]) == 2
        assert len(result["file_presence"]["data_volume"][0]["data"]) == 2

        # Verify data point format
        global_records_series = result["global"]["records"][0]
        assert "data" in global_records_series
        assert len(global_records_series["data"]) == 2  # Two data points (two days)

        # Check first data point format: [date, value] array
        first_data_point = global_records_series["data"][0]
        assert "value" in first_data_point
        assert isinstance(first_data_point["value"], list)
        assert len(first_data_point["value"]) == 2  # [date, value] array
        assert first_data_point["value"][0] == "2025-08-27"  # date string
        assert (
            first_data_point["value"][1] == 2
        )  # total records (metadata_only + with_files)

        # Check readableDate is localized (not just the raw date)
        assert "readableDate" in first_data_point
        assert first_data_point["readableDate"] != "2025-08-27"  # Should be localized
        assert "2025" in first_data_point["readableDate"]  # Should contain year

        # Check valueType
        assert "valueType" in first_data_point
        assert first_data_point["valueType"] == "number"

        # Test specific subcount series creation
        # Check that affiliations has individual series
        affiliations_series = result["affiliations"]["records"]
        assert len(affiliations_series) == 1  # One affiliation in first doc
        assert affiliations_series[0]["id"] == "03rmrcq20"
        assert affiliations_series[0]["name"] == ""

        # Check that subjects has multiple series
        subjects_series = result["subjects"]["records"]
        assert len(subjects_series) == 11  # 11 subjects in first doc
        # Check that each subject has its own series
        subject_ids = [series["id"] for series in subjects_series]
        assert "http://id.worldcat.org/fast/911979" in subject_ids
        assert "http://id.worldcat.org/fast/845111" in subject_ids

    def test_record_snapshot_empty_subcounts(self, running_app: RunningApp):
        """Test RecordSnapshotDataSeriesSet with empty subcounts."""
        # Use the second document which has empty subcounts
        documents: list[AggregationDocumentDict] = [
            MOCK_RECORD_SNAPSHOT_DOCS[1]["_source"],
        ]

        series_set = RecordSnapshotDataSeriesSet(documents)
        result = series_set.build()

        # Check that empty subcounts have no series
        empty_subcounts = [
            "access_statuses",
            "file_types",
            "resource_types",
            "affiliations",
            "funders",
            "languages",
            "periodicals",
            "publishers",
            "rights",
            "subjects",
        ]

        for subcount in empty_subcounts:
            # Empty subcounts should exist but have empty dictionaries
            assert subcount in result, (
                f"Expected empty subcount {subcount} to exist in result"
            )
            assert result[subcount] == {
                "data_volume": [],
                "records": [],
                "parents": [],
                "file_count": [],
            }, (
                f"Expected empty subcount {subcount} to have empty value, "
                f"got {result[subcount]}"
            )

        # Check that global series still exists
        assert len(result["global"]["records"]) == 1
        assert result["global"]["records"][0]["data"][0]["value"][1] == 0  # No records

    def test_record_snapshot_file_presence_processing(self, running_app: RunningApp):
        """Test file_presence special subcount processing."""
        # Use documents with file data
        documents: list[AggregationDocumentDict] = [
            MOCK_RECORD_SNAPSHOT_DOCS[0]["_source"],  # type: ignore
            MOCK_RECORD_SNAPSHOT_DOCS[2]["_source"],  # type: ignore
        ]

        series_set = RecordSnapshotDataSeriesSet(documents)
        result = series_set.build()

        # Check file_presence structure
        assert "file_presence" in result
        assert result["file_presence"]["records"][0]["id"] in [
            "metadata_only",
            "with_files",
        ]
        assert result["file_presence"]["records"][0]["id"] in [
            "metadata_only",
            "with_files",
        ]

        # Check that file_presence has data
        metadata_only_series = [
            r for r in result["file_presence"]["parents"] if r["id"] == "metadata_only"
        ]
        with_files_series = [
            f for f in result["file_presence"]["parents"] if f["id"] == "with_files"
        ]
        assert len(metadata_only_series) == 1
        assert len(with_files_series) == 1
        current_app.logger.error(
            f"metadata_only_series: {pformat(metadata_only_series)}"
        )
        current_app.logger.error(f"with_files_series: {pformat(with_files_series)}")
        current_app.logger.error(list(result.keys()))

        # Check data points
        assert len(metadata_only_series[0]["data"]) == 2  # Two data points
        assert len(with_files_series[0]["data"]) == 2  # Two data points

        # Check values
        # First document: 1 metadata_only, 1 with_files
        # Second document: 1 metadata_only, 3 with_files
        metadata_values = [
            point["value"][1] for point in metadata_only_series[0]["data"]
        ]
        with_files_values = [
            point["value"][1] for point in with_files_series[0]["data"]
        ]

        assert metadata_values == [1, 1]  # metadata_only records
        assert with_files_values == [1, 3]  # with_files records

    def test_record_snapshot_multiple_documents(self, running_app: RunningApp):
        """Test RecordSnapshotDataSeriesSet with multiple documents over time."""
        # Use all three documents to test time series
        documents: list[AggregationDocumentDict] = [
            MOCK_RECORD_SNAPSHOT_DOCS[0]["_source"],  # 2025-08-27
            MOCK_RECORD_SNAPSHOT_DOCS[2]["_source"],  # 2025-08-31
            MOCK_RECORD_SNAPSHOT_DOCS[3]["_source"],  # 2025-09-01
        ]

        series_set = RecordSnapshotDataSeriesSet(documents)
        result = series_set.build()

        # Check that we have 3 data points for each series
        global_records_series = result["global"]["records"][0]
        assert len(global_records_series["data"]) == 3

        # Check dates are in order
        dates = [point["value"][0] for point in global_records_series["data"]]
        assert dates == ["2025-08-27", "2025-08-31", "2025-09-01"]

        # Check values progression
        values = [point["value"][1] for point in global_records_series["data"]]
        assert values == [2, 4, 3]  # Records: 2 -> 4 -> 3

        # Check that subcount series also have 3 data points
        access_status_series = result["access_statuses"]["records"][0]
        assert len(access_status_series["data"]) == 3

    def test_record_snapshot_metric_discovery(self, running_app: RunningApp):
        """Test metric discovery functionality for record snapshots."""
        # Use a document with comprehensive data
        documents: list[AggregationDocumentDict] = [
            MOCK_RECORD_SNAPSHOT_DOCS[2]["_source"],  # Document with rich data
        ]

        series_set = RecordSnapshotDataSeriesSet(documents)
        discovered_metrics = series_set._discover_metrics_from_documents()

        # Check global metrics
        expected_global_metrics = [
            "records",
            "parents",
            "uploaders",
            "file_count",
            "data_volume",
        ]
        for metric in expected_global_metrics:
            assert metric in discovered_metrics["global"], (
                f"Missing global metric: {metric}"
            )

        # Check subcount metrics
        expected_subcount_metrics = ["records", "parents", "file_count", "data_volume"]
        for metric in expected_subcount_metrics:
            assert metric in discovered_metrics["subcount"], (
                f"Missing subcount metric: {metric}"
            )

        # Verify files metric is split into file_count and data_volume
        assert "files" not in discovered_metrics["global"]
        assert "files" not in discovered_metrics["subcount"]
        assert "file_count" in discovered_metrics["global"]
        assert "data_volume" in discovered_metrics["global"]


class TestUsageDeltaDataSeriesSet:
    """Test UsageDeltaDataSeriesSet functionality."""

    def test_usage_delta_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of UsageDeltaDataSeriesSet with sample documents."""
        documents: list[AggregationDocumentDict] = MOCK_USAGE_DELTA_DOCS_2  # type: ignore  # noqa: E501

        series_set = UsageDeltaDataSeriesSet(documents)  # type: ignore
        result = series_set.build()
        current_app.logger.error(f"UsageDeltaDataSeriesSet result: {pformat(result)}")

        # Verify the structure
        assert "global" in result
        assert "access_statuses" in result

        # Check core metrics
        assert "views" in result["global"]
        assert "downloads" in result["global"]
        assert "view_visitors" in result["global"]
        assert "download_visitors" in result["global"]
        assert "data_volume" in result["global"]

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
        assert "data_volume" in result["access_statuses"]
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

        # Verify data point format
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
            # "subjects",  # disabled for usage events
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "countries",
            # "referrers",  # disabled for usage events
            "file_types",
        ]

        for subcount in expected_subcounts:
            assert subcount in result, f"Missing subcount: {subcount}"

        assert result["global"]["data_volume"][0]["data"][0]["valueType"] == "filesize"

    def test_usage_delta_all_subcounts(self, running_app: RunningApp):
        """Test UsageDeltaDataSeriesSet with all available subcounts."""
        documents: list[AggregationDocumentDict] = MOCK_USAGE_DELTA_DOCS_2  # type: ignore  # noqa: E501

        series_set = UsageDeltaDataSeriesSet(documents)
        result = series_set.build()

        # Verify all expected subcounts are present
        expected_subcounts = [
            "access_statuses",
            "resource_types",
            "languages",
            # "subjects",  # disabled for usage events
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
            "countries",
            # "referrers",  # disabled for usage events
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
            # referrers disabled for usage events
            "file_types",
        ]

        for subcount in subcounts_with_data:
            current_app.logger.error(pformat(result))
            assert len(result[subcount]["views"]) == 1, (
                f"Expected 1 series for {subcount} views"
            )
            assert len(result[subcount]["downloads"]) == 1, (
                f"Expected 1 series for {subcount} downloads"
            )

        # Check that empty subcounts have no series
        empty_subcounts = [
            # "subjects",  # disabled for usage events
            "rights",
            "funders",
            "periodicals",
            "publishers",
            "affiliations",
        ]
        for subcount in empty_subcounts:
            assert len(result[subcount]["views"]) == 0, (
                f"Expected 0 series for empty {subcount} views"
            )
            assert len(result[subcount]["downloads"]) == 0, (
                f"Expected 0 series for empty {subcount} downloads"
            )

    def test_usage_delta_metric_discovery(self, running_app: RunningApp):
        """Test metric discovery functionality."""
        documents: list[AggregationDocumentDict] = [
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

        metrics = series_set._discover_metrics_from_documents()

        # Check that all expected metrics are discovered
        expected_metrics = [
            "views",
            "downloads",
            "view_visitors",
            "download_visitors",
            "data_volume",
            "view_unique_parents",
            "view_unique_records",
            "download_unique_files",
            "download_unique_parents",
            "download_unique_records",
        ]

        for metric in expected_metrics:
            assert metric in metrics["global"], f"Missing discovered metric: {metric}"
            assert metric in metrics["subcount"], (
                f"Missing discovered subcount metric: {metric}"
            )


class TestUsageSnapshotDataSeriesSet:
    """Test UsageSnapshotDataSeriesSet functionality."""

    def test_usage_snapshot_series_set_basic_usage(self, running_app: RunningApp):
        """Test basic usage of UsageSnapshotDataSeriesSet with sample documents."""
        documents: list[dict] = MOCK_USAGE_SNAPSHOT_DOCS

        series_set = UsageSnapshotDataSeriesSet(documents)  # type: ignore
        result = series_set.build()

        # Verify the structure
        assert "global" in result
        assert "access_statuses" in result

        # Check core metrics
        assert "views" in result["global"]
        assert "downloads" in result["global"]
        assert "view_visitors" in result["global"]
        assert "download_visitors" in result["global"]
        assert "data_volume" in result["global"]

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
        assert "data_volume" in result["access_statuses"]
        assert "view_unique_parents" in result["access_statuses"]
        assert "view_unique_records" in result["access_statuses"]
        assert "download_unique_files" in result["access_statuses"]

        # Verify data points exist
        assert len(result["global"]["views"]) == 1  # Single global series
        assert len(result["access_statuses"]["views"]) == 2  # Two access status series

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
        assert data_point["value"][1] == 45  # view events value (updated total)

        # Check readableDate is localized
        assert "readableDate" in data_point
        assert data_point["readableDate"] != "2025-06-01"  # Should be localized
        assert "2025" in data_point["readableDate"]  # Should contain year

        # Check valueType
        assert "valueType" in data_point
        assert data_point["valueType"] == "number"

        # Check that we have the expected series IDs
        access_status_series_ids = [s["id"] for s in result["access_statuses"]["views"]]
        assert "metadata-only" in access_status_series_ids
        assert "with-files" in access_status_series_ids

        current_app.logger.error(pformat(result))
        # Check data volume valueType
        assert (
            result["access_statuses"]["data_volume"][0]["data"][0]["valueType"]
            == "filesize"
        )
