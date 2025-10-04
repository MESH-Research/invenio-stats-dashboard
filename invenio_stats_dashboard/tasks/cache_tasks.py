# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for cache generation."""

import arrow
from celery import shared_task
from flask import current_app

from celery.schedules import crontab

from .aggregation_tasks import AggregationTaskLock, TaskLockAcquisitionError
from ..resources.cache_utils import StatsCache
from ..services.cached_response_service import CachedResponseService


CachedResponsesGenerationTask = {
    "task": "invenio_stats_dashboard.tasks.generate_cached_responses_task",
    "schedule": crontab(minute="50", hour="*"),  # Run every hour at minute 50
    # community_ids, years, force, async_mode, current_year_only
    "args": ("all", None, False, False, True),  
}


@shared_task
def clear_expired_cache_task() -> dict:
    """
    Clear expired cache entries.

    Returns:
        dict - Results of the cleanup operation
    """
    try:
        cache = StatsCache()
        all_keys = cache.keys()

        expired_count = 0
        for key in all_keys:
            try:
                # Check if key has TTL
                ttl = cache.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist
                    continue
                elif ttl == -1:  # Key exists but has no expiration
                    continue
                elif ttl > 0:  # Key has TTL but hasn't expired yet
                    continue
                else:  # Key has expired (TTL = 0)
                    cache.redis_client.delete(key)
                    expired_count += 1
            except Exception as e:
                current_app.logger.warning(f"Error checking TTL for key {key}: {e}")

        current_app.logger.info(f"Cleared {expired_count} expired cache entries")

        return {
            'success': True,
            'expired_count': expired_count,
            'total_keys_checked': len(all_keys)
        }

    except Exception as e:
        current_app.logger.error(f"Failed to clear expired cache: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(ignore_result=False)
def generate_cached_responses_task(
    community_ids: str | list[str] | None = None,
    years: int | list[int] | str | None = None,
    force: bool = False,
    async_mode: bool = False,
    current_year_only: bool = False,
) -> dict:
    """
    Generate cached responses using CachedResponseService.

    This task can be used for both scheduled runs and manual CLI operations.
    It uses the existing CachedResponseService to generate cache for specified
    communities and years.

    Uses distributed locking to prevent multiple instances from running
    simultaneously.

    Args:
        community_ids: Community IDs to process ('all', list, or None for all)
        years: Years to process (int, list, or None for auto)
        force: Whether to overwrite existing cache
        async_mode: Whether to use async Celery tasks (not used in scheduled runs)
        current_year_only: Whether to override years with current year only

    Returns:
        dict - Summary of the cache generation operation
    """
    try:
        if current_year_only:
            years = arrow.now().year

        # Get lock configuration
        lock_config = current_app.config.get("STATS_DASHBOARD_LOCK_CONFIG", {})
        global_enabled = lock_config.get("enabled", True)
        caching_config = lock_config.get("response_caching", {})
        lock_enabled = global_enabled and caching_config.get("enabled", True)
        lock_timeout = caching_config.get("lock_timeout", 3600)
        lock_name = caching_config.get("lock_name", "community_stats_cache_generation")

        service = CachedResponseService()

        if lock_enabled:
            lock = AggregationTaskLock(lock_name, timeout=lock_timeout)
            try:
                with lock:
                    current_app.logger.info(
                        f"Acquired cache generation lock, starting cache generation"
                    )
                    result = service.create(
                        community_ids=community_ids,
                        years=years,
                        force=force,
                        async_mode=async_mode
                    )
                    current_app.logger.info(
                        f"Cache generation completed: {result}"
                    )

                    return result
                    
            except TaskLockAcquisitionError:
                current_app.logger.warning(
                    "Cache generation task skipped - another instance is already running"
                )
                return {
                    'success': False,
                    'skipped': True,
                    'reason': 'Another cache generation task is already running',
                    'community_ids': community_ids,
                    'years': years
                }
        else:
            # Run without locking
            current_app.logger.info(
                f"Running cache generation without distributed lock"
            )
            result = service.create(
                community_ids=community_ids,
                years=years,
                force=force,
                async_mode=async_mode
            )
            current_app.logger.info(
                f"Cache generation completed: {result}"
            )

            return result

    except Exception as e:
        current_app.logger.error(f"Cache generation task failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


