#!/usr/bin/env python3
"""Test content negotiation wrapper functions."""

import json
import tarfile
import tempfile

from flask import Response

from invenio_stats_dashboard.resources.serializers.wrapper_functions import (
    brotli_json_serializer_func,
    data_series_csv_serializer_func,
    data_series_excel_serializer_func,
    data_series_xml_serializer_func,
    gzip_json_serializer_func,
    json_serializer_func,
)


class TestBasicSerializerWrapperFunctions:
    """Test basic serializer wrapper functions."""

    def test_json_serializer_func(self, running_app):
        """Test JSON wrapper function creates proper Flask Response."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        response = json_serializer_func(test_data)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json"

        # Check response data
        json_data = json.loads(response.data.decode("utf-8"))
        assert isinstance(json_data, dict)
        assert "usage-delta-category" in json_data


class TestCompressionSerializerWrapperFunctions:
    """Test compression serializer wrapper functions."""

    def test_gzip_json_serializer_func(self, running_app):
        """Test Gzip JSON wrapper function creates proper Flask Response."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        response = gzip_json_serializer_func(test_data)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Content-Encoding"] == "gzip"
        assert (
            "attachment; filename=stats.json.gz" 
            in response.headers["Content-Disposition"]
        )

        # Check that data is compressed
        assert isinstance(response.data, bytes)
        assert len(response.data) > 0

    def test_brotli_json_serializer_func(self, running_app):
        """Test Brotli JSON wrapper function creates proper Flask Response."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        response = brotli_json_serializer_func(test_data)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Content-Encoding"] == "br"
        assert (
            "attachment; filename=stats.json.br" 
            in response.headers["Content-Disposition"]
        )

        # Check that data is compressed
        assert isinstance(response.data, bytes)
        assert len(response.data) > 0


class TestDataSeriesSerializerWrapperFunctions:
    """Test data series serializer wrapper functions."""

    def test_data_series_csv_serializer_func(self, running_app):
        """Test Data Series CSV wrapper function creates proper Flask Response."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
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
                                },
                            ],
                        }
                    ],
                    "downloads": [
                        {
                            "id": "open",
                            "label": "Open Access",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 25],
                                    "valueType": "number",
                                }
                            ],
                        }
                    ],
                },
                "countries": {
                    "views": [
                        {
                            "id": "us",
                            "label": "United States",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 100],
                                    "valueType": "number",
                                }
                            ],
                        }
                    ],
                },
            }
        }

        response = data_series_csv_serializer_func(test_data)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/gzip"
        assert response.headers["Content-Type"] == "application/gzip"
        assert response.headers["Content-Encoding"] == "gzip"
        assert (
            "attachment; filename=data_series_csv.tar.gz" 
            in response.headers["Content-Disposition"]
        )

        # Check that data is compressed tar.gz archive
        assert isinstance(response.data, bytes)
        assert len(response.data) > 0

        # Verify it's a valid tar.gz archive
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(response.data)
            temp_file.flush()

            with tarfile.open(temp_file.name, "r:gz") as tar:
                members = tar.getnames()
                # Should have nested structure:
                # usage-delta-category/access_statuses/data_volume.csv
                assert any("usage-delta-category" in member for member in members)
                assert any("access_statuses" in member for member in members)
                assert any("data_volume.csv" in member for member in members)
                assert any("downloads.csv" in member for member in members)
                assert any("countries" in member for member in members)
                assert any("views.csv" in member for member in members)

    def test_data_series_xml_serializer_func(self, running_app):
        """Test Data Series XML wrapper function creates proper Flask Response."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        response = data_series_xml_serializer_func(test_data)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/xml"
        assert response.headers["Content-Type"] == "application/xml; charset=utf-8"
        assert (
            "attachment; filename=data_series_xml.xml" 
            in response.headers["Content-Disposition"]
        )

        # Check XML data
        xml_data = response.data.decode("utf-8")
        assert xml_data.startswith('<?xml version=\'1.0\' encoding=\'utf-8\'?>')
        assert "<dataSeriesCollection" in xml_data
        assert "usage-delta-category" in xml_data
        assert "access_statuses" in xml_data
        assert "data_volume" in xml_data

    def test_data_series_excel_serializer_func(self, running_app):
        """Test Data Series Excel wrapper function creates proper Flask Response."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ],
                    "downloads": [
                        {
                            "id": "open",
                            "label": "Open Access",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 25],
                                    "valueType": "number",
                                }
                            ],
                        }
                    ],
                },
                "countries": {
                    "views": [
                        {
                            "id": "us",
                            "label": "United States",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 100],
                                    "valueType": "number",
                                }
                            ],
                        }
                    ],
                },
            }
        }

        response = data_series_excel_serializer_func(test_data)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/gzip"
        assert response.headers["Content-Type"] == "application/gzip"
        assert response.headers["Content-Encoding"] == "gzip"
        assert (
            "attachment; filename=data_series_excel.tar.gz" 
            in response.headers["Content-Disposition"]
        )

        # Check that data is compressed tar.gz archive
        assert isinstance(response.data, bytes)
        assert len(response.data) > 0

        # Verify it's a valid tar.gz archive containing Excel files
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(response.data)
            temp_file.flush()

            with tarfile.open(temp_file.name, "r:gz") as tar:
                members = tar.getnames()
                # Should have nested structure:
                # usage-delta-category/access_statuses.xlsx
                assert any("usage-delta-category" in member for member in members)
                assert any("access_statuses.xlsx" in member for member in members)
                assert any("countries.xlsx" in member for member in members)

                # Verify Excel files are valid (start with PK signature)
                for member in members:
                    if member.endswith(".xlsx"):
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            content = file_obj.read()
                            assert content.startswith(b"PK"), (
                                f"Invalid Excel file: {member}"
                            )

    def test_data_series_csv_serializer_func_with_community_id(self, running_app):
        """Test Data Series CSV wrapper function with community_id parameter."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        community_id = "test-community-123"
        response = data_series_csv_serializer_func(test_data, community_id=community_id)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/gzip"
        assert response.headers["Content-Type"] == "application/gzip"
        assert response.headers["Content-Encoding"] == "gzip"
        # Filename should include community ID
        assert "test-community-123" in response.headers["Content-Disposition"]

    def test_data_series_xml_serializer_func_with_community_id(self, running_app):
        """Test Data Series XML wrapper function with community_id parameter."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        community_id = "test-community-456"
        response = data_series_xml_serializer_func(test_data, community_id=community_id)

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/xml"
        assert response.headers["Content-Type"] == "application/xml; charset=utf-8"
        # Filename should include community ID
        assert "test-community-456" in response.headers["Content-Disposition"]

    def test_data_series_excel_serializer_func_with_community_id(self, running_app):
        """Test Data Series Excel wrapper function with community_id parameter."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        community_id = "test-community-789"
        response = data_series_excel_serializer_func(
            test_data, community_id=community_id
        )

        # Check response properties
        assert isinstance(response, Response)
        assert response.mimetype == "application/gzip"
        assert response.headers["Content-Type"] == "application/gzip"
        assert response.headers["Content-Encoding"] == "gzip"
        # Filename should include community ID
        assert "test-community-789" in response.headers["Content-Disposition"]

    def test_data_series_serializer_funcs_with_custom_headers(self, running_app):
        """Test that custom headers are properly added to responses."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "data_volume": [
                        {
                            "id": "metadata-only",
                            "label": "Metadata Only",
                            "data": [
                                {
                                    "readableDate": "Jun 1, 2025",
                                    "value": ["2025-06-01", 3072.0],
                                    "valueType": "filesize",
                                }
                            ],
                        }
                    ]
                }
            }
        }

        custom_headers = {
            "X-Custom-Header": "test-value",
            "Cache-Control": "no-cache",
        }

        # Test CSV serializer with custom headers
        csv_response = data_series_csv_serializer_func(
            test_data, headers=custom_headers
        )
        assert csv_response.headers["X-Custom-Header"] == "test-value"
        assert csv_response.headers["Cache-Control"] == "no-cache"

        # Test XML serializer with custom headers
        xml_response = data_series_xml_serializer_func(
            test_data, headers=custom_headers
        )
        assert xml_response.headers["X-Custom-Header"] == "test-value"
        assert xml_response.headers["Cache-Control"] == "no-cache"

        # Test Excel serializer with custom headers
        excel_response = data_series_excel_serializer_func(
            test_data, headers=custom_headers
        )
        assert excel_response.headers["X-Custom-Header"] == "test-value"
        assert excel_response.headers["Cache-Control"] == "no-cache"
