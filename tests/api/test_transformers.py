# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""tests for the data series transformers."""

import pytest
from datetime import datetime

from invenio_stats_dashboard.transformers.base import (
    DataPoint,
    UsageSnapshotDataSeries,
    UsageDeltaDataSeries,
    RecordSnapshotDataSeries,
    RecordDeltaDataSeries,
)
from invenio_stats_dashboard.transformers.types import AggregationDocumentDict
from tests.conftest import RunningApp


class TestDataPoint:
    """Test DataPoint class functionality."""

    def test_data_point_creation_with_string_date(self):
        """Test creating DataPoint with string date."""
        dp = DataPoint("2024-01-15", 100, "number")
        assert dp.date == "2024-01-15"
        assert dp.value == 100
        assert dp.value_type == "number"

    def test_data_point_creation_with_datetime(self):
        """Test creating DataPoint with datetime object."""
        dt = datetime(2024, 1, 15)
        dp = DataPoint(dt, 100, "number")
        assert dp.date == "2024-01-15"
        assert dp.value == 100

    def test_data_point_to_dict(self):
        """Test DataPoint to_dict conversion."""
        dp = DataPoint("2024-01-15", 100, "number")
        result = dp.to_dict()

        expected = {
            "value": ["2024-01-15", 100],
            "readableDate": "Jan 15, 2024",
            "valueType": "number",
        }
        assert result == expected

    def test_data_point_readable_date_formatting(self):
        """Test readable date formatting."""
        dp = DataPoint("2024-01-15", 100, "number")
        assert dp._format_readable_date() == "Jan 15, 2024"

    def test_data_point_invalid_date_formatting(self):
        """Test handling of invalid date format."""
        dp = DataPoint("invalid-date", 100, "number")
        assert dp._format_readable_date() == "invalid-date"


class TestDataSeriesBasicFunctionality:
    """Test basic DataSeries functionality using concrete subclasses."""

    def test_usage_snapshot_series_with_raw_documents(self, running_app: RunningApp):
        """Test creating UsageSnapshotDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                    "download": {"total_events": 50, "total_volume": 1024000},
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                    "download": {"total_events": 75, "total_volume": 2048000},
                },
            },
        ]

        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="global",
            metric="views",
            chart_type="line",
        )

        assert series.id == "test_series"
        assert series.name == "Test Series"
        assert series.category == "global"
        assert series.metric == "views"
        assert series.type == "line"
        assert series.value_type == "number"
        assert len(series.data) == 2
        assert series.data[0].value == 100
        assert series.data[1].value == 150

    def test_usage_snapshot_series_without_data(self, running_app: RunningApp):
        """Test creating UsageSnapshotDataSeries without data points."""
        series = UsageSnapshotDataSeries(
            series_id="empty_series",
            name="Empty Series",
            raw_documents=[],
            category="global",
            metric="views",
            chart_type="bar",
        )

        assert series.id == "empty_series"
        assert series.name == "Empty Series"
        assert series.data == []
        assert series.type == "bar"
        assert series.value_type == "number"

    def test_usage_snapshot_series_get_summary_stats(self, running_app: RunningApp):
        """Test get_summary_stats method with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                },
            },
            {
                "snapshot_date": "2024-01-17T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                },
            },
        ]

        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="global",
            metric="views",
        )

        stats = series.get_summary_stats()
        assert stats["count"] == 3
        assert stats["total"] == 450
        assert stats["min"] == 100
        assert stats["max"] == 200
        assert stats["avg"] == 150.0

    def test_usage_snapshot_series_get_summary_stats_empty(
        self, running_app: RunningApp
    ):
        """Test get_summary_stats with empty series."""
        series = UsageSnapshotDataSeries(
            series_id="empty_series",
            name="Empty Series",
            raw_documents=[],
            category="global",
            metric="views",
        )

        stats = series.get_summary_stats()
        assert stats["count"] == 0
        assert stats["total"] == 0
        assert stats["min"] == 0
        assert stats["max"] == 0
        assert stats["avg"] == 0

    def test_usage_snapshot_series_filter_by_date_range(self, running_app: RunningApp):
        """Test filter_by_date_range method with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                },
            },
            {
                "snapshot_date": "2024-01-17T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                },
            },
        ]

        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="global",
            metric="views",
        )

        filtered_series = series.filter_by_date_range("2024-01-15", "2024-01-15")
        assert filtered_series.id == "test_series"
        assert filtered_series.name == "Test Series"
        assert filtered_series.start_date == "2024-01-15"
        assert filtered_series.end_date == "2024-01-15"

    def test_usage_snapshot_series_to_dict(self, running_app: RunningApp):
        """Test to_dict method with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                },
            },
        ]

        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="global",
            metric="views",
            chart_type="line",
        )

        result = series.to_dict()
        expected = {
            "id": "test_series",
            "name": "Test Series",
            "data": [series.data[0].to_dict()],
            "type": "line",
            "valueType": "number",
        }
        assert result == expected

    def test_usage_snapshot_series_for_json(self, running_app: RunningApp):
        """Test for_json method with category name conversion."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                },
            },
        ]

        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="access_statuses",
            metric="views",
            chart_type="line",
        )

        result = series.for_json()

        # Check that category is converted to camelCase for JSON
        assert result["category"] == "accessStatuses"
        assert result["id"] == "test_series"
        assert result["name"] == "Test Series"
        assert result["type"] == "line"
        assert result["valueType"] == "number"
        assert len(result["data"]) == 1

    def test_usage_snapshot_series_for_json_global_category(
        self, running_app: RunningApp
    ):
        """Test for_json method with global category (no conversion)."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                },
            },
        ]

        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="global",
            metric="views",
            chart_type="line",
        )

        result = series.for_json()

        # Global category should remain unchanged
        assert result["category"] == "global"
        assert result["id"] == "test_series"
        assert result["name"] == "Test Series"


class TestUsageSnapshotDataSeries:
    """Test UsageSnapshotDataSeries functionality."""

    @pytest.fixture
    def sample_documents(self):
        """Sample usage snapshot documents for testing."""
        return [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                    "download": {"total_events": 75, "total_volume": 1024000},
                },
                "subcounts": {
                    "access_statuses": [
                        {
                            "id": "open",
                            "label": "Open Access",
                            "view": {"total_events": 100, "unique_visitors": 30},
                            "download": {"total_events": 50, "total_volume": 512000},
                        },
                        {
                            "id": "closed",
                            "label": "Closed Access",
                            "view": {"total_events": 50, "unique_visitors": 15},
                            "download": {"total_events": 25, "total_volume": 512000},
                        },
                    ]
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                    "download": {"total_events": 100, "total_volume": 2048000},
                },
                "subcounts": {
                    "access_statuses": [
                        {
                            "id": "open",
                            "label": "Open Access",
                            "view": {"total_events": 120, "unique_visitors": 40},
                            "download": {"total_events": 60, "total_volume": 1024000},
                        },
                        {
                            "id": "closed",
                            "label": "Closed Access",
                            "view": {"total_events": 80, "unique_visitors": 20},
                            "download": {"total_events": 40, "total_volume": 1024000},
                        },
                    ]
                },
            },
        ]

    def test_usage_snapshot_series_creation_with_raw_documents(
        self, running_app: RunningApp
    ):
        """Test creating UsageSnapshotDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                },
            },
        ]
        series = UsageSnapshotDataSeries(
            series_id="global_views",
            name="Global Views",
            raw_documents=documents,
            category="global",
            metric="views",
            chart_type="bar",
        )

        assert series.id == "global_views"
        assert series.name == "Global Views"
        assert series.category == "global"
        assert series.metric == "views"
        assert series.type == "bar"
        assert len(series.data) == 2
        assert series.data[0].value == 150
        assert series.data[1].value == 200

    def test_usage_snapshot_series_with_raw_documents(
        self, sample_documents, running_app: RunningApp
    ):
        """Test creating UsageSnapshotDataSeries with raw documents."""
        series = UsageSnapshotDataSeries(
            series_id="global_views",
            name="Global Views",
            raw_documents=sample_documents,
            category="global",
            metric="views",
        )

        assert series.id == "global_views"
        assert series.name == "Global Views"
        assert series.category == "global"
        assert series.metric == "views"
        assert len(series.data) == 2
        assert series.data[0].value == 150
        assert series.data[1].value == 200

    def test_usage_snapshot_series_global_views(
        self, sample_documents, running_app: RunningApp
    ):
        """Test global views series creation."""
        series = UsageSnapshotDataSeries(
            series_id="global_views",
            name="Global Views",
            raw_documents=sample_documents,
            category="global",
            metric="views",
        )

        assert series.category == "global"
        assert series.metric == "views"
        assert len(series.data) == 2
        assert series.data[0].value == 150
        assert series.data[1].value == 200

    def test_usage_snapshot_series_global_downloads(
        self, sample_documents, running_app: RunningApp
    ):
        """Test global downloads series creation."""
        series = UsageSnapshotDataSeries(
            series_id="global_downloads",
            name="Global Downloads",
            raw_documents=sample_documents,
            category="global",
            metric="downloads",
        )

        assert series.category == "global"
        assert series.metric == "downloads"
        assert len(series.data) == 2
        assert series.data[0].value == 75
        assert series.data[1].value == 100

    def test_usage_snapshot_series_data_volume(
        self, sample_documents, running_app: RunningApp
    ):
        """Test data volume series creation."""
        series = UsageSnapshotDataSeries(
            series_id="data_volume",
            name="Data Volume",
            raw_documents=sample_documents,
            category="global",
            metric="dataVolume",
        )

        assert series.category == "global"
        assert series.metric == "dataVolume"
        assert series.value_type == "filesize"
        assert len(series.data) == 2
        assert series.data[0].value == 1024000
        assert series.data[1].value == 2048000

    def test_usage_snapshot_series_subcount_series(
        self, sample_documents, running_app: RunningApp
    ):
        """Test subcount series creation."""
        series = UsageSnapshotDataSeries(
            series_id="open_access_views",
            name="Open Access Views",
            raw_documents=sample_documents,
            category="access_statuses",
            metric="views",
            subcount_id="open",
        )

        assert series.category == "access_statuses"
        assert series.metric == "views"
        assert series.subcount_id == "open"
        assert len(series.data) == 2
        assert series.data[0].value == 100
        assert series.data[1].value == 120

    def test_usage_snapshot_series_date_filtering(
        self, sample_documents, running_app: RunningApp
    ):
        """Test date filtering functionality."""
        series = UsageSnapshotDataSeries(
            series_id="filtered_series",
            name="Filtered Series",
            raw_documents=sample_documents,
            start_date="2024-01-15",
            end_date="2024-01-15",
        )

        assert series.start_date == "2024-01-15"
        assert series.end_date == "2024-01-15"

    def test_usage_snapshot_series_summary_stats(
        self, sample_documents, running_app: RunningApp
    ):
        """Test summary statistics calculation."""
        # Add a third document for more comprehensive testing
        extended_documents = sample_documents + [
            {
                "snapshot_date": "2024-01-17T00:00:00Z",
                "totals": {
                    "view": {"total_events": 250, "unique_visitors": 75},
                },
            }
        ]
        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=extended_documents,
        )

        stats = series.get_summary_stats()
        assert stats["count"] == 3
        assert stats["total"] == 600
        assert stats["min"] == 150
        assert stats["max"] == 250
        assert stats["avg"] == 200.0


class TestUsageDeltaDataSeries:
    """Test UsageDeltaDataSeries functionality."""

    def test_usage_delta_series_creation_with_raw_documents(
        self, running_app: RunningApp
    ):
        """Test creating UsageDeltaDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 50, "unique_visitors": 15},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 75, "unique_visitors": 25},
                },
            },
        ]
        series = UsageDeltaDataSeries(
            series_id="net_views",
            name="Net Views",
            raw_documents=documents,
            category="global",
            metric="views",
            chart_type="line",
        )

        assert series.id == "net_views"
        assert series.name == "Net Views"
        assert series.category == "global"
        assert series.metric == "views"
        assert series.type == "line"
        assert len(series.data) == 2
        assert series.data[0].value == 50
        assert series.data[1].value == 75

    def test_usage_delta_series_with_raw_documents(self, running_app: RunningApp):
        """Test creating UsageDeltaDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                    "download": {"total_events": 75, "total_volume": 1024000},
                },
            }
        ]
        series = UsageDeltaDataSeries(
            series_id="net_views",
            name="Net Views",
            raw_documents=documents,
            category="global",
            metric="views",
        )

        assert series.id == "net_views"
        assert series.name == "Net Views"
        assert series.category == "global"
        assert series.metric == "views"
        assert len(series.data) == 1
        assert series.data[0].value == 150

    def test_usage_delta_series_net_views(self, running_app: RunningApp):
        """Test net views series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 50, "unique_visitors": 15},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 75, "unique_visitors": 25},
                },
            },
        ]
        series = UsageDeltaDataSeries(
            series_id="net_views",
            name="Net Views",
            raw_documents=documents,
            category="global",
            metric="views",
        )

        assert series.category == "global"
        assert series.metric == "views"
        assert len(series.data) == 2
        assert series.data[0].value == 50
        assert series.data[1].value == 75

    def test_usage_delta_series_net_downloads(self, running_app: RunningApp):
        """Test net downloads series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "totals": {
                    "download": {"total_events": 25, "total_volume": 512000},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "totals": {
                    "download": {"total_events": 40, "total_volume": 1024000},
                },
            },
        ]
        series = UsageDeltaDataSeries(
            series_id="net_downloads",
            name="Net Downloads",
            raw_documents=documents,
            category="global",
            metric="downloads",
        )

        assert series.category == "global"
        assert series.metric == "downloads"
        assert len(series.data) == 2
        assert series.data[0].value == 25
        assert series.data[1].value == 40

    def test_usage_delta_series_data_volume(self, running_app: RunningApp):
        """Test data volume series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "totals": {
                    "download": {"total_events": 25, "total_volume": 512000},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "totals": {
                    "download": {"total_events": 40, "total_volume": 1024000},
                },
            },
        ]
        series = UsageDeltaDataSeries(
            series_id="net_data_volume",
            name="Net Data Volume",
            raw_documents=documents,
            category="global",
            metric="dataVolume",
        )

        assert series.category == "global"
        assert series.metric == "dataVolume"
        assert series.value_type == "filesize"
        assert len(series.data) == 2
        assert series.data[0].value == 512000
        assert series.data[1].value == 1024000


class TestRecordSnapshotDataSeries:
    """Test RecordSnapshotDataSeries functionality."""

    def test_record_snapshot_series_creation_with_raw_documents(
        self, running_app: RunningApp
    ):
        """Test creating RecordSnapshotDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "total_records": {"metadata_only": 10, "with_files": 20},
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "total_records": {"metadata_only": 15, "with_files": 20},
            },
        ]
        series = RecordSnapshotDataSeries(
            series_id="total_records",
            name="Total Records",
            raw_documents=documents,
            category="global",
            metric="records",
            chart_type="bar",
        )

        assert series.id == "total_records"
        assert series.name == "Total Records"
        assert series.category == "global"
        assert series.metric == "records"
        assert series.type == "bar"
        assert len(series.data) == 2
        assert series.data[0].value == 30  # 10 + 20
        assert series.data[1].value == 35  # 15 + 20

    def test_record_snapshot_series_with_raw_documents(self, running_app: RunningApp):
        """Test creating RecordSnapshotDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "total_records": {"metadata_only": 10, "with_files": 20},
                "total_parents": {"metadata_only": 5, "with_files": 15},
                "total_uploaders": 8,
                "total_files": {"file_count": 50, "data_volume": 1024000},
            }
        ]
        series = RecordSnapshotDataSeries(
            series_id="total_records",
            name="Total Records",
            raw_documents=documents,
            category="global",
            metric="records",
        )

        assert series.id == "total_records"
        assert series.name == "Total Records"
        assert series.category == "global"
        assert series.metric == "records"
        assert len(series.data) == 1
        assert series.data[0].value == 30  # 10 + 20

    def test_record_snapshot_series_total_records(self, running_app: RunningApp):
        """Test total records series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "total_records": {"metadata_only": 10, "with_files": 20},
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "total_records": {"metadata_only": 15, "with_files": 20},
            },
        ]
        series = RecordSnapshotDataSeries(
            series_id="total_records",
            name="Total Records",
            raw_documents=documents,
            category="global",
            metric="records",
        )

        assert series.category == "global"
        assert series.metric == "records"
        assert len(series.data) == 2
        assert series.data[0].value == 30
        assert series.data[1].value == 35

    def test_record_snapshot_series_file_count(self, running_app: RunningApp):
        """Test file count series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "total_files": {"file_count": 50, "data_volume": 1024000},
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "total_files": {"file_count": 60, "data_volume": 2048000},
            },
        ]
        series = RecordSnapshotDataSeries(
            series_id="file_count",
            name="File Count",
            raw_documents=documents,
            category="global",
            metric="fileCount",
        )

        assert series.category == "global"
        assert series.metric == "fileCount"
        assert len(series.data) == 2
        assert series.data[0].value == 50
        assert series.data[1].value == 60

    def test_record_snapshot_series_data_volume(self, running_app: RunningApp):
        """Test data volume series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "total_files": {"file_count": 50, "data_volume": 1024000},
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "total_files": {"file_count": 60, "data_volume": 2048000},
            },
        ]
        series = RecordSnapshotDataSeries(
            series_id="data_volume",
            name="Data Volume",
            raw_documents=documents,
            category="global",
            metric="dataVolume",
        )

        assert series.category == "global"
        assert series.metric == "dataVolume"
        assert series.value_type == "filesize"
        assert len(series.data) == 2
        assert series.data[0].value == 1024000
        assert series.data[1].value == 2048000


class TestRecordDeltaDataSeries:
    """Test RecordDeltaDataSeries functionality."""

    def test_record_delta_series_creation_with_raw_documents(
        self, running_app: RunningApp
    ):
        """Test creating RecordDeltaDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "records": {
                    "added": {"metadata_only": 10, "with_files": 20},
                    "removed": {"metadata_only": 5, "with_files": 10},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "records": {
                    "added": {"metadata_only": 15, "with_files": 25},
                    "removed": {"metadata_only": 5, "with_files": 15},
                },
            },
        ]
        series = RecordDeltaDataSeries(
            series_id="net_records",
            name="Net Records",
            raw_documents=documents,
            category="global",
            metric="records",
            chart_type="line",
        )

        assert series.id == "net_records"
        assert series.name == "Net Records"
        assert series.category == "global"
        assert series.metric == "records"
        assert series.type == "line"
        assert len(series.data) == 2
        assert series.data[0].value == 15  # (10+20) - (5+10)
        assert series.data[1].value == 20  # (15+25) - (5+15)

    def test_record_delta_series_with_raw_documents(self, running_app: RunningApp):
        """Test creating RecordDeltaDataSeries with raw documents."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "records": {
                    "added": {"metadata_only": 10, "with_files": 20},
                    "removed": {"metadata_only": 5, "with_files": 10},
                },
                "parents": {
                    "added": {"metadata_only": 5, "with_files": 15},
                    "removed": {"metadata_only": 2, "with_files": 8},
                },
                "uploaders": 3,
                "files": {
                    "added": {"file_count": 25, "data_volume": 1024000},
                    "removed": {"file_count": 10, "data_volume": 512000},
                },
            }
        ]
        series = RecordDeltaDataSeries(
            series_id="net_records",
            name="Net Records",
            raw_documents=documents,
            category="global",
            metric="records",
        )

        assert series.id == "net_records"
        assert series.name == "Net Records"
        assert series.category == "global"
        assert series.metric == "records"
        assert len(series.data) == 1
        assert series.data[0].value == 15  # (10+20) - (5+10)

    def test_record_delta_series_net_records(self, running_app: RunningApp):
        """Test net records series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "records": {
                    "added": {"metadata_only": 10, "with_files": 20},
                    "removed": {"metadata_only": 5, "with_files": 10},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "records": {
                    "added": {"metadata_only": 15, "with_files": 25},
                    "removed": {"metadata_only": 5, "with_files": 15},
                },
            },
        ]
        series = RecordDeltaDataSeries(
            series_id="net_records",
            name="Net Records",
            raw_documents=documents,
            category="global",
            metric="records",
        )

        assert series.category == "global"
        assert series.metric == "records"
        assert len(series.data) == 2
        assert series.data[0].value == 15
        assert series.data[1].value == 20

    def test_record_delta_series_net_file_count(self, running_app: RunningApp):
        """Test net file count series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "files": {
                    "added": {"file_count": 15, "data_volume": 1024000},
                    "removed": {"file_count": 5, "data_volume": 512000},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "files": {
                    "added": {"file_count": 20, "data_volume": 2048000},
                    "removed": {"file_count": 5, "data_volume": 1024000},
                },
            },
        ]
        series = RecordDeltaDataSeries(
            series_id="net_file_count",
            name="Net File Count",
            raw_documents=documents,
            category="global",
            metric="fileCount",
        )

        assert series.category == "global"
        assert series.metric == "fileCount"
        assert len(series.data) == 2
        assert series.data[0].value == 10
        assert series.data[1].value == 15

    def test_record_delta_series_net_data_volume(self, running_app: RunningApp):
        """Test net data volume series creation."""
        documents: list[AggregationDocumentDict] = [
            {
                "period_start": "2024-01-15T00:00:00Z",
                "files": {
                    "added": {"file_count": 15, "data_volume": 1024000},
                    "removed": {"file_count": 5, "data_volume": 512000},
                },
            },
            {
                "period_start": "2024-01-16T00:00:00Z",
                "files": {
                    "added": {"file_count": 20, "data_volume": 2048000},
                    "removed": {"file_count": 5, "data_volume": 1024000},
                },
            },
        ]
        series = RecordDeltaDataSeries(
            series_id="net_data_volume",
            name="Net Data Volume",
            raw_documents=documents,
            category="global",
            metric="dataVolume",
        )

        assert series.category == "global"
        assert series.metric == "dataVolume"
        assert series.value_type == "filesize"
        assert len(series.data) == 2
        assert series.data[0].value == 512000
        assert series.data[1].value == 1024000


class TestDataSeriesIntegration:
    """Integration tests for DataSeries functionality."""

    def test_multiple_series_creation(self, running_app: RunningApp):
        """Test creating multiple different types of series."""
        # Create usage snapshot series
        usage_documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                },
            },
        ]
        usage_series = UsageSnapshotDataSeries(
            series_id="usage_views",
            name="Usage Views",
            raw_documents=usage_documents,
            category="global",
            metric="views",
        )

        # Create record snapshot series
        record_documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "total_records": {"metadata_only": 10, "with_files": 20},
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "total_records": {"metadata_only": 15, "with_files": 20},
            },
        ]
        record_series = RecordSnapshotDataSeries(
            series_id="record_count",
            name="Record Count",
            raw_documents=record_documents,
            category="global",
            metric="records",
        )

        # Verify all series are created correctly
        assert usage_series.category == "global"
        assert usage_series.metric == "views"
        assert len(usage_series.data) == 2
        assert usage_series.data[0].value == 150
        assert usage_series.data[1].value == 200

        assert record_series.category == "global"
        assert record_series.metric == "records"
        assert len(record_series.data) == 2
        assert record_series.data[0].value == 30
        assert record_series.data[1].value == 35

    def test_series_operations_workflow(self, running_app: RunningApp):
        """Test complete series operations workflow."""
        # Create a series with multiple data points
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 100, "unique_visitors": 30},
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                },
            },
            {
                "snapshot_date": "2024-01-17T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                },
            },
            {
                "snapshot_date": "2024-01-18T00:00:00Z",
                "totals": {
                    "view": {"total_events": 175, "unique_visitors": 55},
                },
            },
        ]
        series = UsageSnapshotDataSeries(
            series_id="test_series",
            name="Test Series",
            raw_documents=documents,
            category="global",
            metric="views",
        )

        # Test summary statistics
        stats = series.get_summary_stats()
        assert stats["count"] == 4
        assert stats["total"] == 625
        assert stats["min"] == 100
        assert stats["max"] == 200
        assert stats["avg"] == 156.25

        # Test date filtering
        filtered_series = series.filter_by_date_range("2024-01-16", "2024-01-17")
        assert filtered_series.start_date == "2024-01-16"
        assert filtered_series.end_date == "2024-01-17"

        # Test JSON output
        json_output = series.to_dict()
        assert json_output["id"] == "test_series"
        assert json_output["name"] == "Test Series"
        assert len(json_output["data"]) == 4
        assert json_output["type"] == "line"
        assert json_output["valueType"] == "number"

    def test_different_metrics_workflow(self, running_app: RunningApp):
        """Test creating series with different metrics."""
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                    "download": {"total_events": 75, "total_volume": 1024000},
                },
            },
        ]

        # Views series
        views_series = UsageSnapshotDataSeries(
            series_id="views",
            name="Views",
            raw_documents=documents,
            category="global",
            metric="views",
        )

        # Downloads series
        downloads_series = UsageSnapshotDataSeries(
            series_id="downloads",
            name="Downloads",
            raw_documents=documents,
            category="global",
            metric="downloads",
        )

        # Data volume series
        volume_series = UsageSnapshotDataSeries(
            series_id="volume",
            name="Data Volume",
            raw_documents=documents,
            category="global",
            metric="dataVolume",
        )

        # Verify each series has correct properties
        assert views_series.metric == "views"
        assert views_series.value_type == "number"
        assert views_series.data[0].value == 150

        assert downloads_series.metric == "downloads"
        assert downloads_series.value_type == "number"
        assert downloads_series.data[0].value == 75

        assert volume_series.metric == "dataVolume"
        assert volume_series.value_type == "filesize"
        assert volume_series.data[0].value == 1024000

    def test_error_handling_empty_data(self, running_app: RunningApp):
        """Test error handling with empty data."""
        # Create series with empty data
        empty_series = UsageSnapshotDataSeries(
            series_id="empty",
            name="Empty Series",
            raw_documents=[],
            category="global",
            metric="views",
        )

        # Test summary stats with empty data
        stats = empty_series.get_summary_stats()
        assert stats["count"] == 0
        assert stats["total"] == 0
        assert stats["min"] == 0
        assert stats["max"] == 0
        assert stats["avg"] == 0

        # Test JSON output with empty data
        json_output = empty_series.to_dict()
        assert json_output["id"] == "empty"
        assert json_output["data"] == []

    def test_full_workflow_with_running_app(self, running_app: RunningApp):
        """Test complete DataSeries workflow with Flask app context."""
        # Sample usage snapshot documents
        documents: list[AggregationDocumentDict] = [
            {
                "snapshot_date": "2024-01-15T00:00:00Z",
                "totals": {
                    "view": {"total_events": 150, "unique_visitors": 45},
                    "download": {"total_events": 75, "total_volume": 1024000},
                },
                "subcounts": {
                    "access_statuses": [
                        {
                            "id": "open",
                            "label": "Open Access",
                            "view": {"total_events": 100, "unique_visitors": 30},
                            "download": {
                                "total_events": 50,
                                "total_volume": 512000,
                            },
                        }
                    ]
                },
            },
            {
                "snapshot_date": "2024-01-16T00:00:00Z",
                "totals": {
                    "view": {"total_events": 200, "unique_visitors": 60},
                    "download": {"total_events": 100, "total_volume": 2048000},
                },
                "subcounts": {
                    "access_statuses": [
                        {
                            "id": "open",
                            "label": "Open Access",
                            "view": {"total_events": 120, "unique_visitors": 40},
                            "download": {
                                "total_events": 60,
                                "total_volume": 1024000,
                            },
                        }
                    ]
                },
            },
        ]

        # Test global views series
        views_series = UsageSnapshotDataSeries(
            series_id="global_views",
            name="Global Views",
            raw_documents=documents,
            category="global",
            metric="views",
            chart_type="bar",
        )

        assert views_series.id == "global_views"
        assert views_series.name == "Global Views"
        assert views_series.category == "global"
        assert views_series.metric == "views"
        assert views_series.type == "bar"
        assert len(views_series.data) == 2
        assert views_series.data[0].value == 150
        assert views_series.data[1].value == 200

        # Test global downloads series
        downloads_series = UsageSnapshotDataSeries(
            series_id="global_downloads",
            name="Global Downloads",
            raw_documents=documents,
            category="global",
            metric="downloads",
            chart_type="line",
        )

        assert downloads_series.category == "global"
        assert downloads_series.metric == "downloads"
        assert downloads_series.type == "line"
        assert len(downloads_series.data) == 2
        assert downloads_series.data[0].value == 75
        assert downloads_series.data[1].value == 100

        # Test subcount series (Open Access views)
        open_views_series = UsageSnapshotDataSeries(
            series_id="open_access_views",
            name="Open Access Views",
            raw_documents=documents,
            category="access_statuses",
            metric="views",
            subcount_id="open",
            chart_type="line",
        )

        assert open_views_series.category == "accessStatuses"
        assert open_views_series.metric == "views"
        assert open_views_series.subcount_id == "open"
        assert open_views_series.type == "line"
        assert len(open_views_series.data) == 2
        assert open_views_series.data[0].value == 100
        assert open_views_series.data[1].value == 120

        # Test series operations
        stats = views_series.get_summary_stats()
        assert stats["count"] == 2
        assert stats["total"] == 350
        assert stats["min"] == 150
        assert stats["max"] == 200
        assert stats["avg"] == 175.0

        # Test date filtering
        filtered_series = views_series.filter_by_date_range("2024-01-15", "2024-01-15")
        assert filtered_series.start_date == "2024-01-15"
        assert filtered_series.end_date == "2024-01-15"

        # Test JSON output
        json_output = views_series.to_dict()
        assert json_output["id"] == "global_views"
        assert json_output["name"] == "Global Views"
        assert len(json_output["data"]) == 2
        assert json_output["type"] == "bar"
        assert json_output["valueType"] == "number"


if __name__ == "__main__":
    pytest.main([__file__])
