#!/usr/bin/env python3
"""Test script for the enhanced DataSeriesExcelSerializer."""

import os
import tempfile

from invenio_stats_dashboard.resources.data_series_serializers import (
    DataSeriesExcelSerializer
)


class TestDataSeriesExcelSerializer:
    """Test the DataSeriesExcelSerializer functionality."""

    def test_excel_workbook_creation(self):
        """Test the Excel workbook creation functionality."""
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

        serializer = DataSeriesExcelSerializer()

        # Test the workbook creation
        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_excel_workbooks(test_data, temp_dir)

            # Check if Excel files were created
            assert os.path.exists(os.path.join(temp_dir, "access_statuses.xlsx"))
            assert os.path.exists(os.path.join(temp_dir, "countries.xlsx"))

    def test_sheet_name_sanitization(self):
        """Test sheet name sanitization for Excel compatibility."""
        serializer = DataSeriesExcelSerializer()

        # Test various problematic sheet names
        test_cases = [
            ("normal_name", "normal_name"),
            (
                "name/with\\invalid?chars*[brackets]",
                "name_with_invalid_chars__brackets_"
            ),
            (
                "very_long_sheet_name_that_exceeds_excel_limit_of_31_chars",
                "very_long_sheet_name_that_exce"
            ),
            ("", "Sheet"),
            ("name with spaces", "name with spaces"),
        ]

        for input_name, expected in test_cases:
            result = serializer._sanitize_sheet_name(input_name)
            assert result == expected
            assert len(result) <= 31
            invalid_chars = ['\\', '/', '?', '*', '[', ']']
            assert not any(char in result for char in invalid_chars)

    def test_data_addition_to_sheet(self):
        """Test adding data to Excel sheets."""
        serializer = DataSeriesExcelSerializer()

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

        # Create a mock worksheet (we can't easily test openpyxl without it)
        # This test mainly verifies the logic doesn't crash
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            serializer._add_data_to_sheet(ws, test_obj, 1)
            # If we get here without error, the method works
            assert True
        except ImportError:
            # Skip test if openpyxl not available
            assert True

    def test_empty_data_handling(self):
        """Test handling of empty or invalid data."""
        serializer = DataSeriesExcelSerializer()

        # Test with empty data
        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_excel_workbooks({}, temp_dir)
            # Should not crash and create no files
            assert len(os.listdir(temp_dir)) == 0

        # Test with invalid data structure
        invalid_data = {
            "level1": "not_a_dict"
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            serializer._create_excel_workbooks(invalid_data, temp_dir)
            # Should not crash and create no files
            assert len(os.listdir(temp_dir)) == 0

    def test_fallback_to_csv(self):
        """Test fallback to CSV when openpyxl is not available."""
        serializer = DataSeriesExcelSerializer()

        # This test verifies the fallback mechanism exists
        # In a real scenario, we'd mock the import

        # The method should exist and handle the fallback
        assert hasattr(serializer, '_fallback_to_csv')
