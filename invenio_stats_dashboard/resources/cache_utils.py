# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Cache utilities for invenio-stats-dashboard."""

import hashlib
import json
from datetime import datetime
from typing import Any

import arrow
import redis
from flask import current_app


class StatsCache:
    """Cache manager for statistics data series."""

    def __init__(self, cache_prefix: str | None = None):
        """Initialize the cache manager with direct Redis connection."""
        redis_url = self._get_redis_url()

        self.cache_prefix = cache_prefix or current_app.config.get(
            "STATS_CACHE_PREFIX", "stats_dashboard"
        )

        self.redis_client: redis.Redis = redis.from_url(
            redis_url, decode_responses=False
        )

    def _get_redis_url(self) -> str:
        """Get the Redis URL for stats cache.

        Priority:
        1. STATS_CACHE_REDIS_URL (if set) - full override
        2. CACHE_REDIS_URL + STATS_CACHE_REDIS_DB - use main cache URL with stats DB
        3. Default to redis://localhost:6379/7
        """
        # Check for full override first
        stats_redis_url = str(current_app.config.get("STATS_CACHE_REDIS_URL", ""))
        if stats_redis_url:
            return stats_redis_url

        main_redis_url = current_app.config.get(
            "CACHE_REDIS_URL", "redis://localhost:6379/0"
        )
        stats_db = current_app.config.get("STATS_CACHE_REDIS_DB", 7)

        if "/" in main_redis_url:
            base_url = main_redis_url.rsplit("/", 1)[0]
            return f"{base_url}/{stats_db}"
        else:
            return f"{main_redis_url}/{stats_db}"

    def _generate_response_cache_key(
        self,
        content_type: str,
        request_data: dict,
    ) -> str:
        """Generate a cache key for entire response caching.

        Args:
            content_type: Content type for the response
            request_data: Full request data dict

        Returns:
            Cache key string
        """
        key_data: dict[str, Any] = {"request_data": request_data}
        if content_type:
            key_data["content_type"] = content_type

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{self.cache_prefix}:{key_hash}"

    def get_cached_response(
        self,
        content_type: str,
        request_data: dict,
    ) -> bytes | None:
        """Get cached response data.

        Args:
            content_type: Content type for the response
            request_data: Full request data dict (post request body, for key generation)

        Returns:
            Cached response bytes or None if not found
        """
        cache_key = self._generate_response_cache_key(
            content_type=content_type, request_data=request_data
        )

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data is not None:
                return cached_data  # type: ignore
            else:
                return None
        except Exception as e:
            current_app.logger.warning(f"Cache get error for key {cache_key}: {e}")
            return None

    def set_cached_response(
        self,
        content_type: str,
        request_data: dict,
        response_data: str,
        timeout: int | None = None,
    ) -> bool:
        """Set cached entire response data.

        Args:
            content_type: Content type for the response
            request_data: Full request data dict (post request body, for key
                generation)
            response_data: Response data to cache (as JSON string)
            timeout: Cache timeout in seconds (defaults to )

        Returns:
            True if successful, False otherwise
        """
        cache_key = self._generate_response_cache_key(
            content_type=content_type, request_data=request_data
        )

        try:
            if timeout is None:
                self.redis_client.set(cache_key, response_data.encode("utf-8"))
            else:
                self.redis_client.setex(
                    cache_key, timeout, response_data.encode("utf-8")
                )
            return True
        except Exception as e:
            current_app.logger.warning(f"Cache set error for key {cache_key}: {e}")
            return False

    def invalidate_cache(
        self,
        pattern: str | None = None,
    ) -> bool:
        """Invalidate cache entries matching the given pattern.

        Args:
            pattern: Redis key pattern to match (e.g., "stats_dashboard:*" for all)

        Returns:
            True if invalidation was successful, False otherwise
        """
        try:
            if pattern is None:
                pattern = f"{self.cache_prefix}:*"

            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)  # type: ignore
                current_app.logger.info(
                    f"Invalidated {len(keys)} cache entries matching {pattern}"  # type: ignore  # noqa: E501
                )
            else:
                current_app.logger.info(f"No cache entries found matching {pattern}")

            return True

        except Exception as e:
            current_app.logger.warning(f"Cache invalidation error: {e}")
            return False

    def clear_all_cache(self, pattern: str | None = None) -> tuple[bool, int]:
        """Clear all cache entries in the Redis database.

        Returns:
            Tuple of (success, number_of_deleted_keys)
        """
        if pattern is None:
            pattern = f"{self.cache_prefix}:*"
        try:
            keys: list[bytes] | list[str] | None = self.redis_client.keys(pattern)  # type: ignore
            if keys is None:
                current_app.logger.warning(
                    "Redis keys() returned None - possible connection issue"
                )
                return False, 0

            if not keys:
                current_app.logger.info("No cache entries found to clear")
                return True, 0

            deleted_count: int = self.redis_client.delete(*keys)  # type: ignore
            current_app.logger.info(f"Cleared {deleted_count} cache entries")
            return True, deleted_count

        except Exception as e:
            current_app.logger.warning(f"Cache clear all error: {e}")
            return False, 0

    def list_cache_keys(self, pattern: str | None = None) -> list[str]:
        """List all stats cache keys in the Redis database.

        Returns:
            List of cache keys
        """
        if pattern is None:
            pattern = f"{self.cache_prefix}:*"
        try:
            keys: list[bytes] | list[str] | None = self.redis_client.keys(pattern)  # type: ignore
            if keys is None:
                return []
            return [
                key.decode("utf-8") if isinstance(key, bytes) else str(key)
                for key in keys
            ]
        except Exception as e:
            current_app.logger.warning(f"Cache list keys error: {e}")
            return []

    def get_cache_size_info(self) -> dict[str, Any]:
        """Get detailed cache size information.

        Returns:
            Dictionary with cache size information
        """
        try:
            # Get all keys in the database (since it's dedicated to stats cache)
            keys: list[bytes] | list[str] | None = self.redis_client.keys("*")  # type: ignore
            if keys is None:
                key_count = 0
            else:
                key_count = len(keys)

            # Calculate total memory usage
            total_memory = 0
            if keys:
                for key in keys:
                    try:
                        memory_usage: int | None = self.redis_client.memory_usage(key)  # type: ignore
                        if memory_usage:
                            total_memory += int(memory_usage)
                    except Exception:
                        # Some Redis versions don't support memory_usage
                        pass

            redis_info: dict[str, Any] = self.redis_client.info()  # type: ignore

            return {
                "key_count": key_count,
                "total_memory_bytes": total_memory,
                "total_memory_human": self._format_bytes(total_memory),
                "redis_used_memory": redis_info.get("used_memory", 0),
                "redis_used_memory_human": redis_info.get(
                    "used_memory_human", "unknown"
                ),
                "cache_prefix": self.cache_prefix,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            current_app.logger.warning(f"Cache size info error: {e}")
            return {"error": str(e)}

    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        value = float(bytes_value)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024.0:
                return f"{value:.2f} {unit}"
            value /= 1024.0
        return f"{value:.2f} PB"

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the cache.

        Returns:
            Dictionary with cache information
        """
        try:
            redis_info: dict[str, Any] | None = self.redis_client.info()  # type: ignore
            if isinstance(redis_info, dict):
                return {
                    "cache_type": "Redis (Direct)",
                    "redis_version": redis_info.get("redis_version", "unknown"),
                    "used_memory_human": redis_info.get("used_memory_human", "unknown"),
                    "connected_clients": redis_info.get("connected_clients", "unknown"),
                    "timestamp": arrow.utcnow().isoformat(),
                }
            else:
                return {
                    "cache_type": "Redis (Direct)",
                    "error": "Could not retrieve Redis info",
                    "timestamp": arrow.utcnow().isoformat(),
                }
        except Exception as e:
            current_app.logger.warning(f"Cache info error: {e}")
            return {"error": str(e)}
