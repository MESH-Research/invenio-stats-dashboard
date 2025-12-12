#!/usr/bin/env python3
"""Test script for the enhanced DataSeriesCSVSerializer."""

import os
import tempfile

from invenio_stats_dashboard.resources.serializers.data_series_serializers import (
    DataSeriesCSVSerializer,
)


class TestDataSeriesCSVSerializer:
    """Test the DataSeriesCSVSerializer functionality."""

    def test_nested_csv_structure_creation(self, running_app):
        """Test nested structure with consolidated CSV files."""
        test_data = {
            "usage-delta-category": {
                "access_statuses": {
                    "dataVolume": [
                        {
                            "data": [["06-01", 3072.0], ["06-02", 4096.0]],
                            "year": 2025,
                            "id": "metadata-only",
                            "label": "Metadata Only",
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
                            "label": "Metadata Only",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        },
                        {
                            "data": [["06-01", 5]],
                            "year": 2025,
                            "id": "open",
                            "label": "Open Access",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        },
                    ],
                },
                "countries": {
                    "views": [
                        {
                            "data": [["06-01", 1]],
                            "year": 2025,
                            "id": "US",
                            "label": "United States",
                            "name": "",
                            "type": "line",
                            "valueType": "number",
                        }
                    ]
                },
            }
        }

        serializer = DataSeriesCSVSerializer()

        # Test the nested structure creation
        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_nested_csv_structure(test_data, temp_dir)

            # Check if category directories were created
            assert os.path.exists(
                os.path.join(temp_dir, "usage-delta-category", "access_statuses")
            )
            assert os.path.exists(
                os.path.join(temp_dir, "usage-delta-category", "countries")
            )

            # Check if consolidated CSV files were created (NOT subdirectories)
            data_volume_csv = os.path.join(
                temp_dir, "usage-delta-category", "access_statuses", "dataVolume.csv"
            )
            downloads_csv = os.path.join(
                temp_dir, "usage-delta-category", "access_statuses", "downloads.csv"
            )
            views_csv = os.path.join(
                temp_dir, "usage-delta-category", "countries", "views.csv"
            )

            assert os.path.exists(data_volume_csv)
            assert os.path.exists(downloads_csv)
            assert os.path.exists(views_csv)

            # Check dataVolume CSV content - should have all columns
            with open(data_volume_csv) as f:
                content = f.read()
                assert "id,label,date,value,units" in content
                assert "metadata-only,Metadata Only,06-01,3072.0,bytes" in content
                assert "metadata-only,Metadata Only,06-02,4096.0,bytes" in content

            # Check downloads CSV content - should consolidate multiple series
            with open(downloads_csv) as f:
                lines = f.readlines()
                assert len(lines) == 3  # Header + 2 data rows
                assert "id,label,date,value,units" in lines[0]
                content = "".join(lines)
                expected = "metadata-only,Metadata Only,06-01,3,unique downloads"
                assert expected in content
                assert "open,Open Access,06-01,5,unique downloads" in content

    def test_consolidated_csv_file_content(self):
        """Test consolidated CSV file creation with multiple series."""
        metric_name = "views"
        data_series_list = [
            {
                "id": "eng",
                "label": {"en": "English"},
                "data": [["06-01", 100], ["06-02", 200]],
                "year": 2025,
            },
            {
                "id": "spa",
                "label": {"en": "Spanish"},
                "data": [["06-01", 50]],
                "year": 2025,
            },
        ]

        serializer = DataSeriesCSVSerializer()

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_consolidated_csv_file(
                metric_name, data_series_list, temp_dir
            )

            csv_path = os.path.join(temp_dir, "views.csv")
            assert os.path.exists(csv_path)

            with open(csv_path) as f:
                lines = f.readlines()
                assert len(lines) == 4  # Header + 3 data rows
                assert lines[0].strip() == "id,label,date,value,units"

                content = "".join(lines)
                assert "eng,English,06-01,100,unique views" in content
                assert "eng,English,06-02,200,unique views" in content
                assert "spa,Spanish,06-01,50,unique views" in content

    def test_filename_sanitization(self):
        """Test that metric names are properly sanitized for filenames."""
        # Metric name with invalid characters
        metric_name = "test/file\\name:with*invalid?chars"
        data_series_list = [
            {
                "id": "test-id",
                "label": "Test",
                "data": [["06-01", 100]],
                "year": 2025,
            }
        ]

        serializer = DataSeriesCSVSerializer()

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_consolidated_csv_file(
                metric_name, data_series_list, temp_dir
            )

            # Check that a sanitized filename was created
            files = os.listdir(temp_dir)
            assert len(files) == 1
            # Filename should be sanitized (no invalid chars)
            invalid_chars = ["/", "\\", ":", "*", "?"]
            assert not any(char in files[0] for char in invalid_chars)
            assert files[0].endswith(".csv")

    def test_empty_data_handling(self):
        """Test handling of empty or invalid data."""
        serializer = DataSeriesCSVSerializer()

        # Test with empty data
        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_nested_csv_structure({}, temp_dir)
            # Should not crash and create no files
            assert len(os.listdir(temp_dir)) == 0

        # Test with invalid data structure
        invalid_data = {"level1": "not_a_dict"}

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_nested_csv_structure(invalid_data, temp_dir)
            # Should not crash and create no files
            assert len(os.listdir(temp_dir)) == 0
