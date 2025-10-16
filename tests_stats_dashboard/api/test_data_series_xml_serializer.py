#!/usr/bin/env python3
"""Test script for the enhanced DataSeriesXMLSerializer."""

import xml.etree.ElementTree as ET

from invenio_stats_dashboard.resources.serializers.data_series_serializers import (
    DataSeriesXMLSerializer
)


class TestDataSeriesXMLSerializer:
    """Test the DataSeriesXMLSerializer functionality."""

    def test_xml_structure_creation(self):
        """Test the XML structure creation functionality."""
        # Sample data structure similar to sample_usage_delta_data_series
        test_data = {
            "access_statuses": {
                "data_volume": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 3072.0],
                                "valueType": "filesize",
                            },
                            {
                                "readableDate": "Jun 2, 2025",
                                "value": ["2025-06-02", 4096.0],
                                "valueType": "filesize",
                            }
                        ],
                        "id": "metadata-only",
                        "name": "",
                        "type": "line",
                        "valueType": "number",
                    }
                ],
                "downloads": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 3],
                                "valueType": "number",
                            }
                        ],
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
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 1],
                                "valueType": "number",
                            }
                        ],
                        "id": "US",
                        "name": "",
                        "type": "line",
                        "valueType": "number",
                    }
                ]
            }
        }

        serializer = DataSeriesXMLSerializer()
        response = serializer.serialize(test_data)

        # Check response properties
        assert response.mimetype == "application/xml"
        assert "application/xml; charset=utf-8" in response.headers["Content-Type"]
        content_disposition = response.headers["Content-Disposition"]
        assert "attachment; filename=data_series.xml" in content_disposition

        # Parse XML and verify structure
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Check root element
        assert root.tag == "dataSeries"
        expected_ns = "http://invenio-stats-dashboard.org/schema/data-series"
        assert root.get("xmlns") == expected_ns
        assert root.get("version") == "1.0"

        # Check metadata
        metadata = root.find("metadata")
        assert metadata is not None
        assert metadata.find("generatedAt") is not None
        total_categories_elem = metadata.find("totalCategories")
        assert total_categories_elem is not None
        assert total_categories_elem.text == "2"

        # Check categories
        categories = root.findall("category")
        assert len(categories) == 2

        # Check first category
        access_statuses = None
        countries = None
        for category in categories:
            if category.get("name") == "access_statuses":
                access_statuses = category
            elif category.get("name") == "countries":
                countries = category

        assert access_statuses is not None
        assert access_statuses.get("id") == "access_statuses"
        assert access_statuses.get("metricsCount") == "2"

        assert countries is not None
        assert countries.get("id") == "countries"
        assert countries.get("metricsCount") == "1"

        # Check metrics in access_statuses
        metrics = access_statuses.findall("metric")
        assert len(metrics) == 2

        data_volume_metric = None
        downloads_metric = None
        for metric in metrics:
            if metric.get("name") == "data_volume":
                data_volume_metric = metric
            elif metric.get("name") == "downloads":
                downloads_metric = metric

        assert data_volume_metric is not None
        assert data_volume_metric.get("id") == "data_volume"
        assert data_volume_metric.get("dataPointsCount") == "1"

        assert downloads_metric is not None
        assert downloads_metric.get("id") == "downloads"
        assert downloads_metric.get("dataPointsCount") == "1"

        # Check series in data_volume metric
        series_list = data_volume_metric.findall("series")
        assert len(series_list) == 1

        series = series_list[0]
        assert series.get("id") == "metadata-only"
        assert series.get("type") == "line"
        assert series.get("valueType") == "number"

        # Check data points
        data_points = series.find("dataPoints")
        assert data_points is not None
        assert data_points.get("count") == "2"

        points = data_points.findall("point")
        assert len(points) == 2

        # Check first point
        first_point = points[0]
        assert first_point.get("readableDate") == "Jun 1, 2025"
        assert first_point.get("date") == "2025-06-01"
        assert first_point.get("value") == "3072.0"
        assert first_point.get("valueType") == "filesize"

        # Check second point
        second_point = points[1]
        assert second_point.get("readableDate") == "Jun 2, 2025"
        assert second_point.get("date") == "2025-06-02"
        assert second_point.get("value") == "4096.0"
        assert second_point.get("valueType") == "filesize"

    def test_xml_id_sanitization(self):
        """Test XML ID sanitization for XML compatibility."""
        serializer = DataSeriesXMLSerializer()

        # Test various problematic names
        test_cases = [
            ("normal_name", "normal_name"),
            ("name with spaces", "name_with_spaces"),
            (
                "name/with\\invalid?chars*[brackets]",
                "name_with_invalid_chars__brackets_"
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
            assert result[0].isalpha() or result[0] == '_'
            assert all(c.isalnum() or c in '_-.' for c in result)

    def test_empty_data_handling(self):
        """Test handling of empty or invalid data."""
        serializer = DataSeriesXMLSerializer()

        # Test with empty data
        response = serializer.serialize({})
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Should have root element and metadata
        assert root.tag == "dataSeries"
        assert root.find("metadata") is not None
        total_categories_elem = root.find("metadata/totalCategories")
        assert total_categories_elem is not None
        assert total_categories_elem.text == "0"
        # Should have no categories
        assert len(root.findall("category")) == 0

        # Test with invalid data structure
        invalid_data = {
            "level1": "not_a_dict"
        }

        response = serializer.serialize(invalid_data)
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Should have root element and metadata
        assert root.tag == "dataSeries"
        assert root.find("metadata") is not None
        total_categories_elem = root.find("metadata/totalCategories")
        assert total_categories_elem is not None
        assert total_categories_elem.text == "1"
        # Should have one category but no metrics
        categories = root.findall("category")
        assert len(categories) == 1
        assert categories[0].get("metricsCount") == "0"

    def test_timestamp_generation(self):
        """Test timestamp generation."""
        serializer = DataSeriesXMLSerializer()
        timestamp = serializer._get_current_timestamp()

        # Should be in ISO format and end with Z
        assert timestamp.endswith("Z")
        assert "T" in timestamp
        # Should be parseable as ISO format
        from datetime import datetime
        datetime.fromisoformat(timestamp[:-1])  # Remove Z for parsing
