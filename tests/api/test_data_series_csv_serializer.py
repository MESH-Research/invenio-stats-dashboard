#!/usr/bin/env python3
"""Test script for the enhanced DataSeriesCSVSerializer."""

import os
import tempfile

from invenio_stats_dashboard.resources.serializers.data_series_serializers import (
    DataSeriesCSVSerializer
)


class TestDataSeriesCSVSerializer:
    """Test the DataSeriesCSVSerializer functionality."""

    def test_nested_csv_structure_creation(self):
        """Test the nested structure creation functionality."""
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

        serializer = DataSeriesCSVSerializer()

        # Test the nested structure creation
        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_nested_csv_structure(test_data, temp_dir)

            # Check if directories were created
            assert os.path.exists(os.path.join(temp_dir, "access_statuses"))
            assert os.path.exists(os.path.join(temp_dir, "countries"))

            # Check if subdirectories were created
            data_volume_dir = os.path.join(temp_dir, "access_statuses", "data_volume")
            downloads_dir = os.path.join(temp_dir, "access_statuses", "downloads")
            views_dir = os.path.join(temp_dir, "countries", "views")

            assert os.path.exists(data_volume_dir)
            assert os.path.exists(downloads_dir)
            assert os.path.exists(views_dir)

            # Check if CSV files were created
            data_volume_csv = os.path.join(
                temp_dir, "access_statuses", "data_volume", "metadata-only.csv"
            )
            downloads_csv = os.path.join(
                temp_dir, "access_statuses", "downloads", "metadata-only.csv"
            )
            views_csv = os.path.join(temp_dir, "countries", "views", "US.csv")

            assert os.path.exists(data_volume_csv)
            assert os.path.exists(downloads_csv)
            assert os.path.exists(views_csv)

            # Check CSV content
            csv_path = os.path.join(
                temp_dir, "access_statuses", "data_volume", "metadata-only.csv"
            )
            with open(csv_path, 'r') as f:
                content = f.read()
                assert "date,value" in content  # Header
                assert "2025-06-01,3072.0" in content
                assert "2025-06-02,4096.0" in content

    def test_csv_file_content(self):
        """Test individual CSV file creation and content."""
        test_obj = {
            "id": "test-id",
            "data": [
                {
                    "readableDate": "Jun 1, 2025",
                    "value": ["2025-06-01", 100],
                    "valueType": "number",
                },
                {
                    "readableDate": "Jun 2, 2025",
                    "value": ["2025-06-02", 200],
                    "valueType": "number",
                }
            ]
        }

        serializer = DataSeriesCSVSerializer()

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_csv_file(test_obj, temp_dir)

            csv_path = os.path.join(temp_dir, "test-id.csv")
            assert os.path.exists(csv_path)

            with open(csv_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 3  # Header + 2 data rows
                assert lines[0].strip() == "date,value"
                assert lines[1].strip() == "2025-06-01,100"
                assert lines[2].strip() == "2025-06-02,200"

    def test_filename_sanitization(self):
        """Test that filenames are properly sanitized."""
        test_obj = {
            "id": "test/file\\name:with*invalid?chars",
            "data": [
                {
                    "readableDate": "Jun 1, 2025",
                    "value": ["2025-06-01", 100],
                    "valueType": "number",
                }
            ]
        }

        serializer = DataSeriesCSVSerializer()

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_csv_file(test_obj, temp_dir)

            # Check that a sanitized filename was created
            files = os.listdir(temp_dir)
            assert len(files) == 1
            # The filename should be sanitized (no invalid characters)
            assert not any(char in files[0] for char in ['/', '\\', ':', '*', '?'])

    def test_empty_data_handling(self):
        """Test handling of empty or invalid data."""
        serializer = DataSeriesCSVSerializer()

        # Test with empty data
        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_nested_csv_structure({}, temp_dir)
            # Should not crash and create no files
            assert len(os.listdir(temp_dir)) == 0

        # Test with invalid data structure
        invalid_data = {
            "level1": "not_a_dict"
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_nested_csv_structure(invalid_data, temp_dir)
            # Should not crash and create no files
            assert len(os.listdir(temp_dir)) == 0
