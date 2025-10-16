# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for content negotiation serializers."""

import json
import pytest

from invenio_stats_dashboard.resources.serializers.basic_serializers import (
    StatsJSONSerializer,
    StatsCSVSerializer,
    StatsXMLSerializer,
    StatsHTMLSerializer,
    StatsExcelSerializer,
)


@pytest.fixture
def sample_list_data():
    """Sample list data for testing."""
    return [
        {
            "period_start": "2025-01-01T00:00:00",
            "period_end": "2025-01-01T23:59:59",
            "community_id": "knowledge-commons",
            "records": {"added": 5, "removed": 1},
            "subcounts": {
                "resource_types": [
                    {"id": "publication-article", "label": "Article", "count": 3},
                    {"id": "publication-book", "label": "Book", "count": 2},
                ]
            },
        },
        {
            "period_start": "2025-01-02T00:00:00",
            "period_end": "2025-01-02T23:59:59",
            "community_id": "knowledge-commons",
            "records": {"added": 3, "removed": 0},
            "subcounts": {
                "resource_types": [
                    {"id": "publication-article", "label": "Article", "count": 2},
                    {"id": "publication-chapter", "label": "Chapter", "count": 1},
                ]
            },
        },
    ]


@pytest.fixture
def sample_dict_data():
    """Sample dict data for testing."""
    return {
        "record_deltas_created": [
            {
                "period_start": "2025-01-01T00:00:00",
                "period_end": "2025-01-01T23:59:59",
                "community_id": "knowledge-commons",
                "records": {"added": 5, "removed": 1},
            }
        ],
        "usage_deltas": [
            {
                "period_start": "2025-01-01T00:00:00",
                "period_end": "2025-01-01T23:59:59",
                "community_id": "knowledge-commons",
                "total_events": 150,
                "unique_visitors": 45,
            }
        ],
        "summary": {"total_records": 100, "total_views": 1000},
    }


class TestStatsJSONSerializer:
    """Test JSON serializer."""

    def test_serialize_list(self, sample_list_data):
        """Test serializing list data."""
        serializer = StatsJSONSerializer()
        response = serializer.serialize(sample_list_data)

        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["community_id"] == "knowledge-commons"

    def test_serialize_dict(self, sample_dict_data):
        """Test serializing dict data."""
        serializer = StatsJSONSerializer()
        response = serializer.serialize(sample_dict_data)

        assert response.mimetype == "application/json"

        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert "record_deltas_created" in data
        assert "usage_deltas" in data


class TestStatsCSVSerializer:
    """Test CSV serializer."""

    def test_serialize_list(self, sample_list_data):
        """Test serializing list data to CSV."""
        serializer = StatsCSVSerializer()
        response = serializer.serialize(sample_list_data)

        assert response.mimetype == "text/csv"
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert (
            "attachment; filename=stats.csv" in response.headers["Content-Disposition"]
        )

        csv_data = response.data.decode("utf-8")
        lines = csv_data.strip().split("\n")
        assert len(lines) == 3  # Header + 2 data rows
        assert "period_start" in lines[0]  # Header row

    def test_serialize_dict(self, sample_dict_data):
        """Test serializing dict data to CSV."""
        serializer = StatsCSVSerializer()
        response = serializer.serialize(sample_dict_data)

        assert response.mimetype == "text/csv"

        csv_data = response.data.decode("utf-8")
        lines = csv_data.strip().split("\n")
        assert len(lines) > 0


class TestStatsXMLSerializer:
    """Test XML serializer."""

    def test_serialize_list(self, sample_list_data):
        """Test serializing list data to XML."""
        serializer = StatsXMLSerializer()
        response = serializer.serialize(sample_list_data)

        assert response.mimetype == "application/xml"
        assert response.headers["Content-Type"] == "application/xml; charset=utf-8"

        xml_data = response.data.decode("utf-8")
        assert "<stats>" in xml_data
        assert "<item" in xml_data
        assert "knowledge-commons" in xml_data

    def test_serialize_dict(self, sample_dict_data):
        """Test serializing dict data to XML."""
        serializer = StatsXMLSerializer()
        response = serializer.serialize(sample_dict_data)

        assert response.mimetype == "application/xml"

        xml_data = response.data.decode("utf-8")
        assert "<stats>" in xml_data


class TestStatsHTMLSerializer:
    """Test HTML serializer."""

    def test_serialize_list(self, sample_list_data):
        """Test serializing list data to HTML."""
        serializer = StatsHTMLSerializer()
        response = serializer.serialize(sample_list_data)

        assert response.mimetype == "text/html"
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"

        html_data = response.data.decode("utf-8")
        assert "<html>" in html_data
        assert "<table>" in html_data
        assert "Statistics Dashboard" in html_data
        assert "knowledge-commons" in html_data

    def test_serialize_dict(self, sample_dict_data):
        """Test serializing dict data to HTML."""
        serializer = StatsHTMLSerializer()
        response = serializer.serialize(sample_dict_data)

        assert response.mimetype == "text/html"

        html_data = response.data.decode("utf-8")
        assert "<html>" in html_data
        assert "Statistics Dashboard" in html_data


class TestStatsExcelSerializer:
    """Test Excel serializer."""

    def test_serialize_list_without_openpyxl(self, sample_list_data, monkeypatch):
        """Test serializing list data when openpyxl is not available."""

        # Mock ImportError for openpyxl
        def mock_import_error(*args, **kwargs):
            raise ImportError("No module named 'openpyxl'")

        monkeypatch.setattr("builtins.__import__", mock_import_error)

        serializer = StatsExcelSerializer()
        response = serializer.serialize(sample_list_data)

        # Should fallback to CSV
        assert response.mimetype == "text/csv"

    @pytest.mark.skipif(
        not pytest.importorskip("openpyxl", reason="openpyxl not available"),
        reason="openpyxl not available",
    )
    def test_serialize_list_with_openpyxl(self, sample_list_data):
        """Test serializing list data to Excel when openpyxl is available."""
        serializer = StatsExcelSerializer()
        response = serializer.serialize(sample_list_data)

        assert response.mimetype == (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert (
            "attachment; filename=stats.xlsx" in response.headers["Content-Disposition"]
        )

        # Verify it's a valid Excel file (starts with PK signature)
        assert response.data.startswith(b"PK")

    @pytest.mark.skipif(
        not pytest.importorskip("openpyxl", reason="openpyxl not available"),
        reason="openpyxl not available",
    )
    def test_serialize_dict_with_openpyxl(self, sample_dict_data):
        """Test serializing dict data to Excel when openpyxl is available."""
        serializer = StatsExcelSerializer()
        response = serializer.serialize(sample_dict_data)

        assert response.mimetype == (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Verify it's a valid Excel file
        assert response.data.startswith(b"PK")


class TestSerializerIntegration:
    """Test serializer integration with Flask app."""

