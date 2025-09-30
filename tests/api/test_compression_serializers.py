# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for compression serializers."""

import json

import pytest

from invenio_stats_dashboard.resources.serializers.data_series_serializers import (
    CompressedStatsJSONSerializer,
    GzipStatsJSONSerializer,
    BrotliStatsJSONSerializer,
)


@pytest.fixture
def sample_data():
    """Sample data for testing compression."""
    return {
        "series_id": "test-series",
        "series_name": "Test Data Series",
        "metric": "views",
        "category": "global",
        "type": "line",
        "value_type": "number",
        "data": [
            {"date": "2024-01-01", "value": 100, "value_type": "number"},
            {"date": "2024-01-02", "value": 150, "value_type": "number"},
            {"date": "2024-01-03", "value": 200, "value_type": "number"},
        ]
    }


@pytest.fixture
def large_sample_data():
    """Large sample data for better compression testing."""
    return {
        "global": {
            "views": [
                {
                    "series_id": "global-views",
                    "series_name": "Global Views",
                    "metric": "views",
                    "category": "global",
                    "type": "line",
                    "value_type": "number",
                    "data": [
                        {"date": f"2024-01-{i:02d}",
                         "value": i * 10,
                         "value_type": "number"}
                        for i in range(1, 232)  # 231 days of data
                    ]
                }
            ]
        }
    }


class TestCompressedStatsJSONSerializer:
    """Test parameterized compression serializer."""

    def test_gzip_serialization(self, sample_data):
        """Test gzip compression serialization."""
        serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        response = serializer.serialize(sample_data)

        # Check response properties
        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert response.headers["Content-Encoding"] == "gzip"
        assert "stats.json.gz" in response.headers["Content-Disposition"]

        # Check that data is compressed (should be smaller than original JSON)
        original_json = json.dumps(sample_data, indent=2, default=str)
        assert len(response.data) < len(original_json.encode("utf-8"))

    def test_gzip_serialization_with_dict(self, large_sample_data):
        """Test gzip compression with dictionary data."""
        serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        response = serializer.serialize(large_sample_data)

        assert response.mimetype == "application/json"
        assert response.headers["Content-Encoding"] == "gzip"
        assert len(response.data) > 0

    def test_gzip_serialization_with_list(self):
        """Test gzip compression with list data."""
        list_data = [{"key": f"value_{i}"} for i in range(100)]
        serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        response = serializer.serialize(list_data)

        assert response.mimetype == "application/json"
        assert response.headers["Content-Encoding"] == "gzip"
        assert len(response.data) > 0

    def test_brotli_serialization(self, sample_data):
        """Test brotli compression serialization."""
        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        response = serializer.serialize(sample_data)

        # Check response properties
        assert response.mimetype == "application/json"
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert response.headers["Content-Encoding"] == "br"
        assert "stats.json.br" in response.headers["Content-Disposition"]

        # Check that data is compressed (should be smaller than original JSON)
        original_json = json.dumps(sample_data, indent=2, default=str)
        assert len(response.data) < len(original_json.encode("utf-8"))

    def test_brotli_serialization_with_dict(self, large_sample_data):
        """Test brotli compression with dictionary data."""
        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        response = serializer.serialize(large_sample_data)

        assert response.mimetype == "application/json"
        assert response.headers["Content-Encoding"] == "br"
        assert len(response.data) > 0

    def test_brotli_serialization_with_list(self):
        """Test brotli compression with list data."""
        list_data = [{"key": f"value_{i}"} for i in range(100)]
        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        response = serializer.serialize(list_data)

        assert response.mimetype == "application/json"
        assert response.headers["Content-Encoding"] == "br"
        assert len(response.data) > 0

    def test_brotli_fallback_to_gzip(self, sample_data, monkeypatch):
        """Test that brotli falls back to gzip when brotli is not available."""
        # Mock brotli as unavailable
        monkeypatch.setattr(
            "invenio_stats_dashboard.resources.data_series_serializers.BROTLI_AVAILABLE",
            False
        )

        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        response = serializer.serialize(sample_data)

        # Should fall back to gzip
        assert response.headers["Content-Encoding"] == "gzip"
        assert "stats.json.gz" in response.headers["Content-Disposition"]


class TestConvenienceSerializers:
    """Test the convenience serializer classes."""

    def test_gzip_convenience_serializer(self, sample_data):
        """Test GzipStatsJSONSerializer convenience class."""
        serializer = GzipStatsJSONSerializer()
        response = serializer.serialize(sample_data)

        assert response.headers["Content-Encoding"] == "gzip"
        assert "stats.json.gz" in response.headers["Content-Disposition"]

    def test_brotli_convenience_serializer(self, sample_data):
        """Test BrotliStatsJSONSerializer convenience class."""
        serializer = BrotliStatsJSONSerializer()
        response = serializer.serialize(sample_data)

        assert response.headers["Content-Encoding"] == "br"
        assert "stats.json.br" in response.headers["Content-Disposition"]


class TestCompressionComparison:
    """Test compression ratio comparison between gzip and brotli."""

    def test_compression_ratio_comparison(self, large_sample_data):
        """Compare compression ratios between gzip and brotli."""
        gzip_serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        brotli_serializer = CompressedStatsJSONSerializer(compression_method="brotli")

        gzip_response = gzip_serializer.serialize(large_sample_data)
        brotli_response = brotli_serializer.serialize(large_sample_data)

        gzip_size = len(gzip_response.data)
        brotli_size = len(brotli_response.data)

        # Both should compress the data
        original_json = json.dumps(large_sample_data, indent=2, default=str)
        original_size = len(original_json.encode("utf-8"))

        assert gzip_size < original_size
        assert brotli_size < original_size

        # Log compression ratios for analysis
        gzip_ratio = (gzip_size / original_size) * 100
        brotli_ratio = (brotli_size / original_size) * 100

        print(f"\nCompression Analysis:")
        print(f"Original size: {original_size} bytes")
        print(f"Gzip size: {gzip_size} bytes ({gzip_ratio:.1f}%)")
        print(f"Brotli size: {brotli_size} bytes ({brotli_ratio:.1f}%)")

        if brotli_size < gzip_size:
            improvement = ((gzip_size - brotli_size) / gzip_size) * 100
            print(f"Brotli is {improvement:.1f}% smaller than gzip")
        else:
            difference = ((brotli_size - gzip_size) / gzip_size) * 100
            print(f"Brotli is {difference:.1f}% larger than gzip")
