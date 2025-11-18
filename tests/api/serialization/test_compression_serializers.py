# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for compression serializers."""

import json

import brotli
import orjson
import pytest

from invenio_stats_dashboard.resources.serializers.data_series_serializers import (
    BrotliStatsJSONSerializer,
    CompressedStatsJSONSerializer,
    GzipStatsJSONSerializer,
)


@pytest.fixture
def sample_data():
    """Sample data for testing compression.

    Returns:
        dict: Sample data dictionary.
    """
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
        ],
    }


@pytest.fixture
def large_sample_data():
    """Large sample data for better compression testing.

    Returns:
        dict: Large sample data dictionary.
    """
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
                        {
                            "date": f"2024-01-{i:02d}",
                            "value": i * 10,
                            "value_type": "number",
                        }
                        for i in range(1, 232)  # 231 days of data
                    ],
                }
            ]
        }
    }


class TestCompressedStatsJSONSerializer:
    """Test parameterized compression serializer."""

    def test_gzip_serialization(self, sample_data):
        """Test gzip compression serialization."""
        serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        compressed_data = serializer.serialize(sample_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Should be gzip compressed (starts with gzip magic bytes)
        assert compressed_data[:2] == b"\x1f\x8b"

        # Check that data is compressed (should be smaller than original JSON)
        original_json = json.dumps(sample_data, indent=2, default=str)
        assert len(compressed_data) < len(original_json.encode("utf-8"))

    def test_gzip_serialization_with_dict(self, large_sample_data):
        """Test gzip compression with dictionary data."""
        serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        compressed_data = serializer.serialize(large_sample_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Should be gzip compressed (starts with gzip magic bytes)
        assert compressed_data[:2] == b"\x1f\x8b"

    def test_gzip_serialization_with_list(self):
        """Test gzip compression with list data."""
        list_data = [{"key": f"value_{i}"} for i in range(100)]
        serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        compressed_data = serializer.serialize(list_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Should be gzip compressed (starts with gzip magic bytes)
        assert compressed_data[:2] == b"\x1f\x8b"

    def test_brotli_serialization(self, sample_data):
        """Test brotli compression serialization."""
        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        compressed_data = serializer.serialize(sample_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Check that data is compressed vs orjson bytes
        original_bytes = orjson.dumps(sample_data, option=orjson.OPT_NAIVE_UTC)
        assert len(compressed_data) < len(original_bytes)

        # Round-trip
        decompressed = brotli.decompress(compressed_data)
        assert orjson.loads(decompressed) == sample_data

    def test_brotli_serialization_with_dict(self, large_sample_data):
        """Test brotli compression with dictionary data."""
        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        compressed_data = serializer.serialize(large_sample_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Check compressed size vs orjson bytes for large payload
        original_bytes = orjson.dumps(large_sample_data, option=orjson.OPT_NAIVE_UTC)
        assert len(compressed_data) < len(original_bytes)

        # Round-trip
        decompressed = brotli.decompress(compressed_data)
        assert orjson.loads(decompressed) == large_sample_data

    def test_brotli_serialization_with_list(self):
        """Test brotli compression with list data."""
        list_data = [{"key": f"value_{i}"} for i in range(100)]
        serializer = CompressedStatsJSONSerializer(compression_method="brotli")
        compressed_data = serializer.serialize(list_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Round-trip
        decompressed = brotli.decompress(compressed_data)
        assert orjson.loads(decompressed) == list_data


class TestConvenienceSerializers:
    """Test the convenience serializer classes."""

    def test_gzip_convenience_serializer(self, sample_data):
        """Test GzipStatsJSONSerializer convenience class."""
        serializer = GzipStatsJSONSerializer()
        compressed_data = serializer.serialize(sample_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Should be gzip compressed (starts with gzip magic bytes)
        assert compressed_data[:2] == b"\x1f\x8b"

        # Should be smaller than original JSON
        original_json = json.dumps(sample_data, indent=2, default=str)
        original_size = len(original_json.encode("utf-8"))
        assert len(compressed_data) < original_size

    def test_brotli_convenience_serializer(self, sample_data):
        """Test BrotliStatsJSONSerializer convenience class."""
        serializer = BrotliStatsJSONSerializer()
        compressed_data = serializer.serialize(sample_data)

        # Should return compressed bytes
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0

        # Test that it can be decompressed back to original data
        decompressed = brotli.decompress(compressed_data)
        assert json.loads(decompressed.decode("utf-8")) == sample_data

        # Should be smaller than original JSON
        original_json = json.dumps(sample_data, indent=2, default=str)
        original_size = len(original_json.encode("utf-8"))
        assert len(compressed_data) < original_size


class TestCompressionComparison:
    """Test compression ratio comparison between gzip and brotli."""

    def test_compression_ratio_comparison(self, large_sample_data):
        """Compare compression ratios between gzip and brotli."""
        gzip_serializer = CompressedStatsJSONSerializer(compression_method="gzip")
        brotli_serializer = CompressedStatsJSONSerializer(compression_method="brotli")

        gzip_data = gzip_serializer.serialize(large_sample_data)
        brotli_data = brotli_serializer.serialize(large_sample_data)

        gzip_size = len(gzip_data)
        brotli_size = len(brotli_data)

        # Both should compress the data (vs compact orjson bytes)
        original_size = len(
            orjson.dumps(large_sample_data, option=orjson.OPT_NAIVE_UTC)
        )

        assert gzip_size < original_size
        assert brotli_size < original_size

        # Log compression ratios for analysis
        gzip_ratio = (gzip_size / original_size) * 100
        brotli_ratio = (brotli_size / original_size) * 100

        print("\nCompression Analysis:")
        print(f"Original size: {original_size} bytes")
        print(f"Gzip size: {gzip_size} bytes ({gzip_ratio:.1f}%)")
        print(f"Brotli size: {brotli_size} bytes ({brotli_ratio:.1f}%)")

        if brotli_size < gzip_size:
            improvement = ((gzip_size - brotli_size) / gzip_size) * 100
            print(f"Brotli is {improvement:.1f}% smaller than gzip")
        else:
            difference = ((brotli_size - gzip_size) / gzip_size) * 100
            print(f"Brotli is {difference:.1f}% larger than gzip")
