# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for StatsAggregationRegistry operations."""

import pytest

from invenio_stats_dashboard.constants import FirstRunStatus, RegistryOperation
from invenio_stats_dashboard.resources.cache_utils import StatsAggregationRegistry


@pytest.fixture
def registry(running_app):
    """StatsAggregationRegistry instance using real Redis with automatic cleanup.

    Yields:
        StatsAggregationRegistry: The configured registry instance.
    """
    reg = StatsAggregationRegistry()
    yield reg
    # Cleanup after test completes - clear ALL keys
    reg.clear_all("*")


def test_registry_basic_set_get(running_app, registry):
    """Test basic registry set and get operations."""
    key = "test_community_agg"
    value = "2024-01-01T12:00:00.000"

    # Set a value
    success = registry.set(key, value, ttl=3600)
    assert success is True

    # Get the value
    retrieved = registry.get(key)
    assert retrieved == value


def test_registry_delete(running_app, registry):
    """Test registry delete operation."""
    key = "test_community_agg"
    value = "2024-01-01T12:00:00.000"

    # Set a value
    registry.set(key, value, ttl=3600)

    # Verify it exists
    assert registry.get(key) == value

    # Delete it
    success = registry.delete(key)
    assert success is True

    # Verify it's gone
    assert registry.get(key) is None


def test_make_registry_key_with_agg_operation(running_app):
    """Test make_registry_key with RegistryOperation.AGG."""
    community_id = "test-community-123"
    key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.AGG
    )
    assert key == f"{community_id}_{RegistryOperation.AGG}"


def test_make_registry_key_with_cache_operation(running_app):
    """Test make_registry_key with RegistryOperation.CACHE (with year replacement)."""
    community_id = "test-community-123"
    year = 2024
    cache_operation = RegistryOperation.CACHE.replace("{year}", str(year))
    key = StatsAggregationRegistry.make_registry_key(community_id, cache_operation)
    assert key == f"{community_id}_cache_{year}"


def test_make_registry_key_with_first_run_operation(running_app):
    """Test make_registry_key with RegistryOperation.FIRST_RUN."""
    community_id = "test-community-123"
    key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )
    assert key == f"{community_id}_{RegistryOperation.FIRST_RUN}"


def test_first_run_status_in_progress(running_app, registry):
    """Test setting first_run status to IN_PROGRESS."""
    community_id = "test-community-123"
    first_run_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )

    # Set to IN_PROGRESS
    registry.set(first_run_key, FirstRunStatus.IN_PROGRESS, ttl=None)

    # Verify it's stored correctly
    retrieved = registry.get(first_run_key)
    assert retrieved == FirstRunStatus.IN_PROGRESS


def test_first_run_status_transition_to_completed(running_app, registry):
    """Test transitioning first_run from IN_PROGRESS to COMPLETED."""
    community_id = "test-community-123"
    first_run_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )

    # Set to IN_PROGRESS first
    registry.set(first_run_key, FirstRunStatus.IN_PROGRESS, ttl=None)
    assert registry.get(first_run_key) == FirstRunStatus.IN_PROGRESS

    # Transition to COMPLETED
    registry.set(first_run_key, FirstRunStatus.COMPLETED, ttl=None)
    assert registry.get(first_run_key) == FirstRunStatus.COMPLETED


def test_first_run_completed_persists(running_app, registry):
    """Test that COMPLETED status persists."""
    community_id = "test-community-123"
    first_run_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )

    # Set to COMPLETED
    registry.set(first_run_key, FirstRunStatus.COMPLETED, ttl=None)

    # Verify it persists (no TTL means it should stay)
    assert registry.get(first_run_key) == FirstRunStatus.COMPLETED

    # Get again to verify persistence
    assert registry.get(first_run_key) == FirstRunStatus.COMPLETED


def test_registry_operation_with_ttl_expires(running_app, registry):
    """Test that operations with TTL expire correctly."""
    key = "test_community_agg"
    value = "2024-01-01T12:00:00.000"

    # Set with a short TTL (1 second)
    registry.set(key, value, ttl=1)

    # Verify it exists immediately
    assert registry.get(key) == value

    # Wait for expiration (using pytest's time mocking or actual sleep)
    import time

    time.sleep(2)

    # Verify it's expired
    assert registry.get(key) is None


def test_first_run_without_ttl_persists(running_app, registry):
    """Test that first_run entries without TTL persist."""
    community_id = "test-community-123"
    first_run_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )

    # Set without TTL
    registry.set(first_run_key, FirstRunStatus.COMPLETED, ttl=None)

    # Verify it persists
    assert registry.get(first_run_key) == FirstRunStatus.COMPLETED

    # Wait a bit and verify it still exists
    import time

    time.sleep(1)
    assert registry.get(first_run_key) == FirstRunStatus.COMPLETED


def test_registry_get_all_with_pattern(running_app, registry):
    """Test get_all with pattern matching."""
    community_id = "test-community-123"

    # Set multiple keys
    agg_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.AGG
    )
    cache_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.CACHE.replace("{year}", "2024")
    )
    first_run_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )

    registry.set(agg_key, "2024-01-01T12:00:00.000", ttl=3600)
    registry.set(cache_key, "2024-01-01T12:00:00.000", ttl=3600)
    registry.set(first_run_key, FirstRunStatus.COMPLETED, ttl=None)

    # Get all keys for this community
    pattern = f"{community_id}_*"
    results = registry.get_all(pattern)

    # Should find all three keys
    assert len(results) == 3
    keys = [r[0] for r in results]
    assert agg_key in keys
    assert cache_key in keys
    assert first_run_key in keys


def test_registry_get_all_returns_strings(running_app, registry):
    """Test that get_all returns strings (not bytes) when decode_responses=True."""
    community_id = "test-community-123"
    first_run_key = StatsAggregationRegistry.make_registry_key(
        community_id, RegistryOperation.FIRST_RUN
    )

    registry.set(first_run_key, FirstRunStatus.COMPLETED, ttl=None)

    # Get all should return strings
    results = registry.get_all(f"{community_id}_*")
    assert len(results) == 1
    key, value = results[0]

    # Both key and value should be strings
    assert isinstance(key, str)
    assert isinstance(value, str)
    assert value == FirstRunStatus.COMPLETED

