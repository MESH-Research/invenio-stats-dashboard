# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for cache functionality."""

import pytest
from unittest.mock import Mock, patch

from invenio_stats_dashboard.resources.cache_utils import StatsCache


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str):
        """Get value from mock Redis."""
        return self._cache.get(key)

    def setex(self, key: str, timeout: int, value) -> bool:
        """Set value in mock Redis with expiration."""
        self._cache[key] = value
        return True

    def delete(self, key: str) -> int:
        """Delete value from mock Redis."""
        if key in self._cache:
            del self._cache[key]
            return 1
        return 0

    def info(self):
        """Get Redis info."""
        return {
            "redis_version": "6.2.0",
            "used_memory_human": "1.00M",
            "connected_clients": "1"
        }


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    return MockRedisClient()


@pytest.fixture
def stats_cache(mock_redis):
    """StatsCache instance with mock Redis client."""
    with patch('redis.from_url', return_value=mock_redis):
        return StatsCache()


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return {
        "global": {
            "views": [
                {
                    "id": "global-views",
                    "name": "Global Views",
                    "data": [
                        {"date": "2024-01-01", "value": 100},
                        {"date": "2024-01-02", "value": 150},
                    ]
                }
            ]
        }
    }


def test_cache_key_generation(stats_cache):
    """Test cache key generation."""
    key1 = stats_cache._generate_cache_key(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31",
        date_basis="added"
    )

    key2 = stats_cache._generate_cache_key(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31",
        date_basis="added"
    )

    # Same parameters should generate same key
    assert key1 == key2

    # Different parameters should generate different keys
    key3 = stats_cache._generate_cache_key(
        community_id="community-123",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31",
        date_basis="added"
    )

    assert key1 != key3


def test_cache_set_and_get(stats_cache, sample_data):
    """Test setting and getting cached data."""
    # Initially no data should be cached
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    assert cached_data is None

    # Set data in cache
    success = stats_cache.set_cached_data(
        data=sample_data,
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    assert success is True

    # Now data should be cached
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    assert cached_data is not None
    assert isinstance(cached_data, bytes)  # Should be compressed


def test_cache_invalidation(stats_cache, sample_data):
    """Test cache invalidation."""
    # Set data in cache
    stats_cache.set_cached_data(
        data=sample_data,
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )

    # Verify data is cached
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    assert cached_data is not None

    # Invalidate cache
    success = stats_cache.invalidate_cache(
        community_id="global",
        stat_name="test_stat"
    )
    assert success is True

    # Data should no longer be cached
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    assert cached_data is None


def test_cache_compression(stats_cache, sample_data):
    """Test that cached data is compressed."""
    # Set data in cache
    stats_cache.set_cached_data(
        data=sample_data,
        community_id="global",
        stat_name="test_stat"
    )

    # Get cached data
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat"
    )

    assert cached_data is not None
    assert isinstance(cached_data, bytes)

    # The compressed data should be smaller than the original JSON
    import json
    original_json = json.dumps(sample_data).encode('utf-8')
    assert len(cached_data) < len(original_json)


def test_cache_with_different_parameters(stats_cache, sample_data):
    """Test cache behavior with different parameters."""
    # Cache data for one set of parameters
    stats_cache.set_cached_data(
        data=sample_data,
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )

    # Different date range should not return cached data
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-02-01",
        end_date="2024-02-28"
    )
    assert cached_data is None

    # Same parameters should return cached data
    cached_data = stats_cache.get_cached_data(
        community_id="global",
        stat_name="test_stat",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    assert cached_data is not None
