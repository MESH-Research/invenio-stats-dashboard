#!/usr/bin/env python3
"""Test script for the enhanced DataSeriesXMLSerializer."""

import xml.etree.ElementTree as ET
from datetime import datetime

from invenio_stats_dashboard.resources.serializers.data_series_serializers import (
    DataSeriesXMLSerializer,
)


class TestDataSeriesXMLSerializer:
    """Test the DataSeriesXMLSerializer functionality."""

    def test_xml_structure_creation(self, running_app):
        """Test the XML structure creation functionality."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "data": [["06-01", 3072.0], ["06-02", 4096.0]],
                            "year": 2025,
                            "id": "metadata-only",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        }
                    ],
                    "downloads": [
                        {
                            "data": [["06-01", 3]],
                            "year": 2025,
                            "id": "metadata-only",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        }
                    ]
                },
                "countries": {
                    "views": [
                        {
                            "data": [["06-01", 1]],
                            "year": 2025,
                            "id": "US",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        }
                    ]
                }
            }
        }

        serializer = DataSeriesXMLSerializer()
        xml_data = serializer.serialize(test_data)

        # Check that we get XML string data
        assert isinstance(xml_data, str)
        assert xml_data.startswith('<?xml version=\'1.0\' encoding=\'utf-8\'?>')
        # Parse XML and verify structure
        root = ET.fromstring(xml_data)

        # Check root element (with namespace)
        assert root.tag == (
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}dataSeriesCollection"
        )
        assert root.get("version") == "1.0"

        # Check metadata
        metadata = root.find(
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}metadata"
        )
        assert metadata is not None
        assert metadata.find(
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}generatedAt"
        ) is not None
        total_categories_elem = metadata.find(
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}totalCategories"
        )
        assert total_categories_elem is not None
        assert total_categories_elem.text == "1"

        # Check categories
        categories = root.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}category"
        )
        assert len(categories) == 1

        # Check the single category
        category = categories[0]
        assert category.get("name") == "usage-delta-category"
        assert category.get("id") == "usage-delta-category"
        assert category.get("metricsCount") == "3"  # data_volume, downloads, views

        # Check series sets in the category
        series_sets = category.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}seriesSet"
        )
        assert len(series_sets) == 2

        # Find specific series sets
        access_statuses = None
        countries = None
        for series_set in series_sets:
            if series_set.get("name") == "access_statuses":
                access_statuses = series_set
            elif series_set.get("name") == "countries":
                countries = series_set

        assert access_statuses is not None
        assert access_statuses.get("id") == "access_statuses"
        assert access_statuses.get("metricsCount") == "2"  # data_volume, downloads

        assert countries is not None
        assert countries.get("id") == "countries"
        assert countries.get("metricsCount") == "1"  # views

        # Check metrics in access_statuses series set
        metrics = access_statuses.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}metric"
        )
        assert len(metrics) == 2

        # Find specific metrics
        data_volume_metric = None
        downloads_metric = None
        for metric in metrics:
            if metric.get("id") == "data_volume":
                data_volume_metric = metric
            elif metric.get("id") == "downloads":
                downloads_metric = metric

        assert data_volume_metric is not None
        assert data_volume_metric.get("id") == "data_volume"
        assert data_volume_metric.get("dataPointsCount") == "2"

        assert downloads_metric is not None
        assert downloads_metric.get("id") == "downloads"
        assert downloads_metric.get("dataPointsCount") == "1"

        # Check metrics in countries series set
        countries_metrics = countries.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}metric"
        )
        assert len(countries_metrics) == 1

        views_metric = countries_metrics[0]
        assert views_metric.get("id") == "views"
        assert views_metric.get("dataPointsCount") == "1"

        # Check series in data_volume metric
        series_list = data_volume_metric.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}series"
        )
        assert len(series_list) == 1

        series = series_list[0]
        assert series.get("id") == "metadata-only"
        assert series.get("type") == "line"
        assert series.get("valueType") == "number"

        # Check data points
        data_points = series.find(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}dataPoints"
        )
        assert data_points is not None
        assert data_points.get("count") == "2"

        points = data_points.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}point"
        )
        assert len(points) == 2

        # Check first point
        first_point = points[0]
        assert first_point.get("date") == "06-01"
        assert first_point.get("value") == "3072.0"

        # Check second point
        second_point = points[1]
        assert second_point.get("date") == "06-02"
        assert second_point.get("value") == "4096.0"

    def test_xml_id_sanitization(self, running_app):
        """Test XML ID sanitization for XML compatibility."""
        serializer = DataSeriesXMLSerializer()

        # Test various problematic names
        test_cases = [
            ("normal_name", "normal_name"),
            ("name with spaces", "name_with_spaces"),
            (
                "name/with\\invalid?chars*[brackets]",
                "name_with_invalid_chars__brackets_",
            ),
            ("123starts_with_number", "id_123starts_with_number"),
            ("", "unknown"),
            ("name-with-hyphens", "name-with-hyphens"),
            ("name_with_underscores", "name_with_underscores"),
        ]

        for input_name, expected in test_cases:
            result = serializer._sanitize_xml_id(input_name)
            assert result == expected
            # Ensure it's a valid XML ID
            assert result[0].isalpha() or result[0] == "_"
            assert all(c.isalnum() or c in "_-." for c in result)

    def test_empty_data_handling(self, running_app):
        """Test handling of empty or invalid data."""
        serializer = DataSeriesXMLSerializer()

        # Test with empty data
        xml_data = serializer.serialize({})
        root = ET.fromstring(xml_data)

        # Should have root element and metadata
        assert root.tag == (
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}dataSeriesCollection"
        )
        assert root.find(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}metadata"
        ) is not None
        total_categories_elem = root.find(
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}metadata/"
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}totalCategories"
        )
        assert total_categories_elem is not None
        assert total_categories_elem.text == "0"
        # Should have no categories
        assert (
            len(
                root.findall(
                    "{https://github.com/MESH-Research/"
                    "invenio-stats-dashboard}category"
                )
            )
            == 0
        )

        # Test with invalid data structure
        invalid_data = {"level1": "not_a_dict"}

        response = serializer.serialize(invalid_data)
        xml_data = response
        root = ET.fromstring(xml_data)

        # Should have root element and metadata
        assert root.tag == (
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}dataSeriesCollection"
        )
        assert root.find(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}metadata"
        ) is not None
        total_categories_elem = root.find(
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}metadata/"
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}totalCategories"
        )
        assert total_categories_elem is not None
        assert total_categories_elem.text == "1"
        # Should have one category but no metrics
        categories = root.findall(
            "{https://github.com/MESH-Research/invenio-stats-dashboard}category"
        )
        assert len(categories) == 1
        assert categories[0].get("metricsCount") == "0"

    def test_timestamp_in_xml_output(self, running_app):
        """Test that timestamps appear correctly in XML output."""
        serializer = DataSeriesXMLSerializer()
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "data": [["06-01", 3072.0]],
                            "year": 2025,
                            "id": "metadata-only",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        }
                    ]
                }
            }
        }

        xml_data = serializer.serialize(test_data)
        root = ET.fromstring(xml_data)

        # Check that generatedAt timestamp exists and is valid
        generated_at = root.find(
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}metadata/"
            "{https://github.com/MESH-Research/"
            "invenio-stats-dashboard}generatedAt"
        )
        assert generated_at is not None
        assert generated_at.text is not None

        # Should be in ISO format with timezone
        timestamp = generated_at.text
        assert timestamp.endswith("+00:00")  # UTC timezone offset format
        assert "T" in timestamp

        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp)  # No need to remove anything
