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
)
from invenio_stats_dashboard.resources.serializers.wrapper_functions import (
    json_serializer_func,
)


@pytest.fixture
def sample_list_data():
    """Sample list data for testing.
    
    Returns:
        list: List of sample data dictionaries with stats information.
    """
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
    """Sample dict data for testing.
    
    Returns:
        dict: Dictionary containing sample stats data with multiple sections.
    """
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

    def test_serialize_list(self, running_app, sample_list_data):
        """Test serializing list data."""
        serializer = StatsJSONSerializer()
        json_data = serializer.serialize(sample_list_data)

        # The serializer returns raw data, not a Response object
        assert isinstance(json_data, list)
        assert len(json_data) == 2
        assert json_data[0]["community_id"] == "knowledge-commons"

    def test_serialize_dict(self, running_app, sample_dict_data):
        """Test serializing dict data."""
        serializer = StatsJSONSerializer()
        json_data = serializer.serialize(sample_dict_data)

        # The serializer returns raw data, not a Response object
        assert isinstance(json_data, dict)
        assert "record_deltas_created" in json_data
        assert "usage_deltas" in json_data


class TestJSONSerializerWrapperFunction:
    """Test JSON serializer wrapper function that creates Flask Response objects."""

    def test_json_serializer_func_with_list(self, running_app, sample_list_data):
        """Test JSON serializer wrapper function with list data."""
        response = json_serializer_func(sample_list_data)

        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json"

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["community_id"] == "knowledge-commons"

    def test_json_serializer_func_with_dict(self, running_app, sample_dict_data):
        """Test JSON serializer wrapper function with dict data."""
        response = json_serializer_func(sample_dict_data)

        assert response.mimetype == "application/json"

        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert "record_deltas_created" in data
        assert "usage_deltas" in data


