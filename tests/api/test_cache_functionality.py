# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for cache functionality."""

import json

import pytest

from invenio_stats_dashboard.models.cached_response import CachedResponse
from invenio_stats_dashboard.resources.cache_utils import StatsCache


@pytest.fixture
def stats_cache():
    """StatsCache instance using real Redis."""
    return StatsCache()


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return {
        "record_delta": {
            "data": [
                {"date": "2024-01-01", "value": 100},
                {"date": "2024-01-02", "value": 150},
            ]
        }
    }


def test_cache_key_generation(running_app, db):
    """Test cache key generation using CachedResponse."""
    # Test that same parameters generate same key
    request_data1 = {
        "record_delta": {
            "params": {
                "community_id": "global",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "date_basis": "added",
            }
        }
    }

    request_data2 = {
        "record_delta": {
            "params": {
                "community_id": "global",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "date_basis": "added",
            }
        }
    }

    key1 = CachedResponse.generate_cache_key("application/json", request_data1)
    key2 = CachedResponse.generate_cache_key("application/json", request_data2)

    # Same parameters should generate same key
    assert key1 == key2
    assert key1.startswith("stats_dashboard:")

    # Different parameters should generate different keys
    request_data3 = {
        "record_delta": {
            "params": {
                "community_id": "community-123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "date_basis": "added",
            }
        }
    }

    key3 = CachedResponse.generate_cache_key("application/json", request_data3)
    assert key1 != key3


def test_cache_set_and_get(running_app, db, stats_cache, sample_data):
    """Test setting and getting cached data."""
    cache_key = "test_key"
    data_bytes = json.dumps(sample_data).encode('utf-8')

    # Initially no data should be cached
    cached_data = stats_cache.get(cache_key)
    assert cached_data is None

    # Set data in cache
    success = stats_cache.set(cache_key, data_bytes)
    assert success is True

    # Now data should be cached
    cached_data = stats_cache.get(cache_key)
    assert cached_data is not None
    assert isinstance(cached_data, bytes)
    assert cached_data == data_bytes


def test_cache_set_with_timeout(running_app, db, stats_cache, sample_data):
    """Test setting cached data with timeout."""
    cache_key = "test_key_timeout"
    data_bytes = json.dumps(sample_data).encode('utf-8')

    # Set data in cache with timeout
    success = stats_cache.set(cache_key, data_bytes, timeout=3600)
    assert success is True

    # Data should be cached
    cached_data = stats_cache.get(cache_key)
    assert cached_data is not None
    assert cached_data == data_bytes


def test_cache_delete(running_app, db, stats_cache, sample_data):
    """Test cache deletion."""
    cache_key = "test_key_delete"
    data_bytes = json.dumps(sample_data).encode('utf-8')

    # Set data in cache
    stats_cache.set(cache_key, data_bytes)

    # Verify data is cached
    cached_data = stats_cache.get(cache_key)
    assert cached_data is not None

    # Delete cache entry
    success = stats_cache.delete(cache_key)
    assert success is True

    # Data should no longer be cached
    cached_data = stats_cache.get(cache_key)
    assert cached_data is None


def test_cache_keys_listing(running_app, db, stats_cache, sample_data):
    """Test listing cache keys."""
    # Set some test data
    stats_cache.set("stats_dashboard:key1", b"data1")
    stats_cache.set("stats_dashboard:key2", b"data2")
    stats_cache.set("other_prefix:key3", b"data3")

    # List all keys with default pattern
    keys = stats_cache.keys()
    assert len(keys) == 3
    assert "stats_dashboard:key1" in keys
    assert "stats_dashboard:key2" in keys
    assert "other_prefix:key3" in keys

    # List keys with specific pattern
    stats_keys = stats_cache.keys("stats_dashboard:*")
    assert len(stats_keys) == 2
    assert "stats_dashboard:key1" in stats_keys
    assert "stats_dashboard:key2" in stats_keys


def test_cache_clear_all(running_app, db, stats_cache, sample_data):
    """Test clearing all cache entries."""
    # Set some test data
    stats_cache.set("stats_dashboard:key1", b"data1")
    stats_cache.set("stats_dashboard:key2", b"data2")
    stats_cache.set("other_prefix:key3", b"data3")

    # Clear all stats dashboard keys
    success, deleted_count = stats_cache.clear_all("stats_dashboard:*")
    assert success is True
    assert deleted_count == 2

    # Stats keys should be gone
    assert stats_cache.get("stats_dashboard:key1") is None
    assert stats_cache.get("stats_dashboard:key2") is None

    # Other keys should remain
    assert stats_cache.get("other_prefix:key3") is not None


def test_cache_info(running_app, db, stats_cache):
    """Test getting cache information."""
    info = stats_cache.get_cache_info()

    assert "cache_type" in info
    assert info["cache_type"] == "Redis (Direct)"
    assert "redis_version" in info
    assert "used_memory_human" in info
    assert "connected_clients" in info
    assert "timestamp" in info


def test_cache_size_info(running_app, db, stats_cache, sample_data):
    """Test getting cache size information."""
    # Set some test data
    stats_cache.set("stats_dashboard:key1", b"data1")
    stats_cache.set("stats_dashboard:key2", b"data2")

    size_info = stats_cache.get_cache_size_info()

    assert "key_count" in size_info
    assert size_info["key_count"] == 2
    assert "total_memory_bytes" in size_info
    assert "total_memory_human" in size_info
    assert "cache_prefix" in size_info
    assert size_info["cache_prefix"] == "stats_dashboard"
    assert "timestamp" in size_info


def test_cache_with_real_redis_operations(running_app, db, stats_cache, sample_data):
    """Test cache operations with real Redis backend."""
    # Test basic set/get operations
    cache_key = "test_real_redis_key"
    data_bytes = json.dumps(sample_data).encode('utf-8')

    # Set data in cache
    success = stats_cache.set(cache_key, data_bytes)
    assert success is True

    # Get data from cache
    cached_data = stats_cache.get(cache_key)
    assert cached_data is not None
    assert cached_data == data_bytes

    # Test with timeout
    timeout_key = "test_timeout_key"
    success = stats_cache.set(timeout_key, data_bytes, timeout=60)
    assert success is True

    # Verify timeout key exists
    timeout_data = stats_cache.get(timeout_key)
    assert timeout_data is not None

    # Test key listing
    keys = stats_cache.keys()
    assert cache_key in keys
    assert timeout_key in keys

    # Test pattern matching
    test_keys = stats_cache.keys("test_*")
    assert cache_key in test_keys
    assert timeout_key in test_keys

    # Test deletion
    success = stats_cache.delete(cache_key)
    assert success is True

    # Verify deletion
    deleted_data = stats_cache.get(cache_key)
    assert deleted_data is None

    # Test clear all
    success, deleted_count = stats_cache.clear_all("test_*")
    assert success is True
    assert deleted_count >= 1  # At least the timeout_key should be deleted


def test_cache_integration_with_cached_response(
    running_app, db, stats_cache, sample_data
):
    """Test cache integration with CachedResponse model."""
    # Create a CachedResponse instance
    cached_response = CachedResponse(
        community_id="global",
        year=2024,
        category="record_delta"
    )

    # Set data on the response
    cached_response._object_data = sample_data
    cached_response._bytes_data = None

    # Get the cache key
    cache_key = cached_response.cache_key
    assert cache_key.startswith("stats_dashboard:")

    # Convert to bytes and store in cache
    data_bytes = cached_response.bytes_data
    success = stats_cache.set(cache_key, data_bytes)
    assert success is True

    # Retrieve from cache
    cached_data = stats_cache.get(cache_key)
    assert cached_data is not None
    assert cached_data == data_bytes

    # Create another CachedResponse from cached bytes
    restored_response = CachedResponse.from_bytes(
        cached_data,
        community_id="global",
        year=2024,
        category="record_delta",
        decode=True
    )

    # Verify the data was restored correctly
    assert restored_response.object_data == sample_data
    assert restored_response.community_id == "global"
    assert restored_response.year == 2024
    assert restored_response.category == "record_delta"

    # Clean up
    stats_cache.delete(cache_key)
