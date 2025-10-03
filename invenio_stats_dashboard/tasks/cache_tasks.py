# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for cache generation."""

from celery import shared_task
from flask import current_app

from ..models.cached_response import CachedResponse


@shared_task
def generate_cached_response_task(community_id: str, year: int, category: str) -> dict:
    """
    Generate a single cached response using CachedResponse.

    Args:
        community_id: Community ID or 'global'
        year: Year for the cached response
        category: Data series category

    Returns:
        dict - Task result with success status and details
    """
    try:
        response = CachedResponse(community_id, year, category)
        response.generate_content()
        response.save_to_cache()

        current_app.logger.info(
            f"Successfully generated cache for {community_id}/{year}/{category}"
        )

        return {
            'success': True,
            'community_id': community_id,
            'year': year,
            'category': category,
            'cache_key': response.cache_key
        }
    except Exception as e:
        current_app.logger.error(
            f"Failed to generate cache for {community_id}/{year}/{category}: {e}"
        )
        return {
            'success': False,
            'community_id': community_id,
            'year': year,
            'category': category,
            'error': str(e)
        }


@shared_task
def generate_batch_cache_task(community_year_category_triples: list) -> list:
    """
    Generate multiple cached responses in batch.

    Args:
        community_year_category_triples: List of (community_id, year, category) tuples

    Returns:
        list - Results for each task
    """
    results = []
    for community_id, year, category in community_year_category_triples:
        result = generate_cached_response_task(community_id, year, category)
        results.append(result)
    return results


@shared_task
def clear_expired_cache_task() -> dict:
    """
    Clear expired cache entries.

    Returns:
        dict - Results of the cleanup operation
    """
    try:
        from ..resources.cache_utils import StatsCache

        cache = StatsCache()
        all_keys = cache.list_cache_keys()

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
