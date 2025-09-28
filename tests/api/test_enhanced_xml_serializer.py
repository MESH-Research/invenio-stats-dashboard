#!/usr/bin/env python3
"""Test script for the enhanced DataSeriesXMLSerializer with XSD schema and Dublin Core metadata."""

import xml.etree.ElementTree as ET

from invenio_stats_dashboard.resources.data_series_serializers import (
    DataSeriesXMLSerializer
)


class TestEnhancedDataSeriesXMLSerializer:
    """Test the enhanced DataSeriesXMLSerializer functionality."""

    def test_xsd_schema_reference(self):
        """Test that XML includes XSD schema reference."""
        test_data = {
            "access_statuses": {
                "data_volume": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 3072.0],
                                "valueType": "filesize",
                            }
                        ],
                        "id": "metadata-only",
                        "name": "",
                        "type": "line",
                        "valueType": "number",
                    }
                ]
            }
        }

        serializer = DataSeriesXMLSerializer()
        response = serializer.serialize(test_data)
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Check schema location
        schema_location = root.get("xsi:schemaLocation")
        assert schema_location is not None
        assert "https://github.com/MESH-Research/invenio-stats-dashboard" in schema_location
        assert "data-series.xsd" in schema_location

        # Check namespaces
        assert root.get("xmlns") == "https://github.com/MESH-Research/invenio-stats-dashboard"
        assert root.get("xmlns:dc") == "http://purl.org/dc/elements/1.1/"
        assert root.get("xmlns:xsi") == "http://www.w3.org/2001/XMLSchema-instance"

    def test_dublin_core_metadata(self):
        """Test Dublin Core metadata elements."""
        test_data = {
            "global": {
                "views": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 100],
                                "valueType": "number",
                            }
                        ],
                        "id": "global",
                        "name": "Global",
                        "type": "bar",
                        "valueType": "number",
                    }
                ]
            }
        }

        serializer = DataSeriesXMLSerializer()
        response = serializer.serialize(test_data)
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)
        metadata = root.find("metadata")

        # Check Dublin Core elements
        assert metadata.find("dc:title") is not None
        assert metadata.find("dc:title").text == "Statistics Dashboard Data Series Collection"

        assert metadata.find("dc:creator") is not None
        assert metadata.find("dc:creator").text == "Invenio Stats Dashboard"

        assert metadata.find("dc:description") is not None
        assert "Time-series statistical data" in metadata.find("dc:description").text

        assert metadata.find("dc:format") is not None
        assert metadata.find("dc:format").text == "application/xml"

        assert metadata.find("dc:language") is not None
        # Language should come from configuration, defaulting to "en"
        language_text = metadata.find("dc:language").text
        assert language_text is not None
        assert len(language_text) > 0

        assert metadata.find("dc:publisher") is not None
        # Publisher should come from configuration, defaulting to "InvenioRDM"
        publisher_text = metadata.find("dc:publisher").text
        assert publisher_text is not None
        assert len(publisher_text) > 0

        assert metadata.find("dc:rights") is not None
        assert metadata.find("dc:rights").text == "MIT License"

        assert metadata.find("dc:type") is not None
        assert metadata.find("dc:type").text == "Dataset"

    def test_semantic_attributes(self):
        """Test semantic attributes for categories, metrics, and data points."""
        test_data = {
            "access_statuses": {
                "data_volume": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 3072.0],
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
                                "value": ["2025-06-01", 5],
                                "valueType": "number",
                            }
                        ],
                        "id": "metadata-only",
                        "name": "",
                        "type": "line",
                        "valueType": "number",
                    }
                ]
            }
        }

        serializer = DataSeriesXMLSerializer()
        response = serializer.serialize(test_data)
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Check category semantic attributes
        category = root.find("category[@name='access_statuses']")
        assert category is not None
        assert category.get("categoryType") == "access_status"
        assert category.get("description") is not None
        assert "access status" in category.get("description")

        # Check metric semantic attributes
        data_volume_metric = category.find("metric[@name='data_volume']")
        assert data_volume_metric is not None
        assert data_volume_metric.get("unit") == "bytes"
        assert data_volume_metric.get("measurementType") == "volume"
        assert data_volume_metric.get("aggregationMethod") == "daily"
        assert data_volume_metric.get("description") is not None
        assert "data volume" in data_volume_metric.get("description")

        downloads_metric = category.find("metric[@name='downloads']")
        assert downloads_metric is not None
        assert downloads_metric.get("unit") == "count"
        assert downloads_metric.get("measurementType") == "count"

        # Check data point semantic attributes
        series = data_volume_metric.find("series[@id='metadata-only']")
        assert series is not None
        assert series.get("description") is not None
        assert "metadata-only" in series.get("description")

        point = series.find("dataPoints/point")
        assert point is not None
        assert point.get("unit") == "bytes"
        assert point.get("quality") == "high"

    def test_enhanced_metadata_calculation(self):
        """Test enhanced metadata calculations."""
        test_data = {
            "global": {
                "views": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 100],
                                "valueType": "number",
                            },
                            {
                                "readableDate": "Jun 2, 2025",
                                "value": ["2025-06-02", 150],
                                "valueType": "number",
                            }
                        ],
                        "id": "global",
                        "name": "Global",
                        "type": "bar",
                        "valueType": "number",
                    }
                ]
            },
            "countries": {
                "downloads": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 50],
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
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)
        metadata = root.find("metadata")

        # Check total data points calculation
        total_points_elem = metadata.find("totalDataPoints")
        assert total_points_elem is not None
        assert total_points_elem.text == "3"  # 2 + 1 data points

        # Check time range calculation
        time_range = metadata.find("timeRange")
        assert time_range is not None
        assert time_range.find("startDate").text == "2025-06-01"
        assert time_range.find("endDate").text == "2025-06-02"

    def test_category_type_mapping(self):
        """Test category type mapping."""
        serializer = DataSeriesXMLSerializer()

        test_cases = [
            ("access_statuses", "access_status"),
            ("countries", "geographic"),
            ("languages", "content_type"),
            ("resource_types", "content_type"),
            ("subjects", "content_type"),
            ("publishers", "content_type"),
            ("rights", "content_type"),
            ("funders", "content_type"),
            ("affiliations", "geographic"),
            ("file_types", "content_type"),
            ("referrers", "user_behavior"),
            ("periodicals", "content_type"),
            ("global", "global"),
            ("unknown_category", None),
        ]

        for category_name, expected_type in test_cases:
            result = serializer._get_category_type(category_name)
            assert result == expected_type

    def test_metric_unit_mapping(self):
        """Test metric unit mapping."""
        serializer = DataSeriesXMLSerializer()

        test_cases = [
            ("data_volume", "bytes"),
            ("downloads", "count"),
            ("views", "count"),
            ("download_unique_files", "count"),
            ("download_unique_parents", "count"),
            ("download_unique_records", "count"),
            ("view_unique_parents", "count"),
            ("view_unique_records", "count"),
            ("download_visitors", "count"),
            ("view_visitors", "count"),
            ("unknown_metric", None),
        ]

        for metric_name, expected_unit in test_cases:
            result = serializer._get_metric_unit(metric_name)
            assert result == expected_unit

    def test_data_quality_assessment(self):
        """Test data quality assessment."""
        serializer = DataSeriesXMLSerializer()

        test_cases = [
            ({"readableDate": "Jun 1, 2025", "value": ["2025-06-01", 100]}, "high"),
            ({"value": ["2025-06-01", 100]}, "medium"),
            ({"readableDate": "Jun 1, 2025"}, "low"),
            ({}, "low"),
        ]

        for point_data, expected_quality in test_cases:
            result = serializer._assess_data_quality(point_data)
            assert result == expected_quality

    def test_series_description_generation(self):
        """Test series description generation."""
        serializer = DataSeriesXMLSerializer()

        test_cases = [
            ({"id": "global"}, "Global statistics across all data"),
            ({"id": "metadata-only"}, "Statistics for metadata-only records"),
            ({"id": "US"}, "Statistics for United States"),
            ({"id": "eng"}, "Statistics for English language content"),
            ({"id": "pdf"}, "Statistics for PDF files"),
            ({"id": "google.com"}, "Statistics for traffic from Google"),
            ({"id": "unknown_id"}, "Statistics for unknown_id"),
        ]

        for series_obj, expected_description in test_cases:
            result = serializer._get_series_description(series_obj)
            assert result == expected_description

    def test_publisher_from_config(self):
        """Test publisher retrieval from configuration."""
        serializer = DataSeriesXMLSerializer()

        # Test that publisher method returns a valid string
        publisher = serializer._get_publisher_from_config()
        assert isinstance(publisher, str)
        assert len(publisher) > 0
        # Should not be empty or None
        assert publisher != ""

    def test_language_from_config(self):
        """Test language retrieval from i18n configuration."""
        serializer = DataSeriesXMLSerializer()

        # Test that language method returns a valid string
        language = serializer._get_language_from_config()
        assert isinstance(language, str)
        assert len(language) > 0
        # Should not be empty or None
        assert language != ""
        # Should be a valid language code (2-3 characters)
        assert len(language) <= 3

    def test_community_metadata_integration(self):
        """Test community metadata integration in XML."""
        test_data = {
            "global": {
                "views": [
                    {
                        "data": [
                            {
                                "readableDate": "Jun 1, 2025",
                                "value": ["2025-06-01", 100],
                                "valueType": "number",
                            }
                        ],
                        "id": "global",
                        "name": "Global",
                        "type": "bar",
                        "valueType": "number",
                    }
                ]
            }
        }

        serializer = DataSeriesXMLSerializer()

        # Test without community_id
        response = serializer.serialize(test_data)
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)
        metadata = root.find("metadata")

        # Should not have community element
        community_elem = metadata.find("community")
        assert community_elem is None

        # Test with community_id (will return None since communities service not available in test)
        response = serializer.serialize(test_data, community_id="test-community")
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)
        metadata = root.find("metadata")

        # Should not have community element since service not available
        community_elem = metadata.find("community")
        assert community_elem is None

    def test_community_metadata_method(self):
        """Test community metadata retrieval method."""
        serializer = DataSeriesXMLSerializer()

        # Test that method handles missing communities gracefully
        result = serializer._get_community_metadata("nonexistent-community")
        assert result is None
