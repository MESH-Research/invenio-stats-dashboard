# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or
# modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Cache utilities for invenio-stats-dashboard."""

from typing import Any

import arrow
import redis
from flask import current_app


class StatsCache:
    """Low-level Redis cache manager for statistics data.

    This is a generic infrastructure layer that handles Redis operations
    without knowledge of the business domain. It works with string keys
    and byte values.
    """

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
        2. CACHE_REDIS_URL + STATS_CACHE_REDIS_DB - use main cache
           URL with stats DB
        3. Default to redis://localhost:6379/7
        """
        # Check for full override first
        stats_redis_url = str(
            current_app.config.get("STATS_CACHE_REDIS_URL", "")
        )
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

    def get(self, key: str) -> bytes | None:
        """Get cached data by key.

        Args:
            key: Cache key

        Returns:
            Cached data bytes or None if not found
        """
        try:
            cached_data = self.redis_client.get(key)
            if cached_data is not None:
                return cached_data  # type: ignore
            else:
                return None
        except Exception as e:
            current_app.logger.warning(f"Cache get error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: bytes,
        timeout: int | None = None,
    ) -> bool:
        """Set cached data.

        Args:
            key: Cache key
            value: Data to cache (as bytes)
            timeout: Cache timeout in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        try:
            if timeout is None:
                self.redis_client.set(key, value)
            else:
                self.redis_client.setex(key, timeout, value)
            return True
        except Exception as e:
            current_app.logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found or error
        """
        try:
            deleted_count = self.redis_client.delete(key)
            if deleted_count > 0:
                current_app.logger.info(
                    f"Deleted cache key: {key}"
                )
                return True
            else:
                current_app.logger.info(
                    f"Cache key not found: {key}"
                )
                return False
        except Exception as e:
            current_app.logger.warning(
                f"Cache delete error for key {key}: {e}"
            )
            return False

    def keys(self, pattern: str | None = None) -> list[str]:
        """List cache keys matching pattern.

        Args:
            pattern: Redis key pattern (defaults to all keys with cache prefix)

        Returns:
            List of matching cache keys
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
            current_app.logger.warning(
                f"Cache keys error: {e}"
            )
            return []

    def clear_all(self, pattern: str | None = None) -> tuple[bool, int]:
        """Clear all cache entries matching pattern.

        Args:
            pattern: Redis key pattern (defaults to all keys with cache prefix)

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

            deleted_count: int = self.redis_client.delete(*keys)
            current_app.logger.info(
                f"Cleared {deleted_count} cache entries"
            )
            return True, deleted_count

        except Exception as e:
            current_app.logger.warning(
                f"Cache clear all error: {e}"
            )
            return False, 0

    def get_cache_size_info(self) -> dict[str, Any]:
        """Get detailed cache size information.

        Returns:
            Dictionary with cache size information
        """
        try:
            # Get all keys in the database (since it's dedicated to
            # stats cache)
            all_keys = self.keys("*")
            key_count = len(all_keys)

            # Calculate total memory usage
            total_memory = 0
            if all_keys:
                for key in all_keys:
                    try:
                        # type: ignore
                        memory_usage: int | None = (
                            self.redis_client.memory_usage(key)
                        )
                        if memory_usage:
                            total_memory += int(memory_usage)
                    except Exception:
                        # Some Redis versions don't support memory_usage
                        pass

            # type: ignore
            redis_info: dict[str, Any] = self.redis_client.info()

            return {
                "key_count": key_count,
                "total_memory_bytes": total_memory,
                "total_memory_human": self._format_bytes(
                    total_memory
                ),
                "redis_used_memory": redis_info.get(
                    "used_memory", 0
                ),
                "redis_used_memory_human": redis_info.get(
                    "used_memory_human", "unknown"
                ),
                "cache_prefix": self.cache_prefix,
                "timestamp": arrow.utcnow().isoformat(),
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
            # type: ignore
            redis_info: dict[str, Any] | None = (
                self.redis_client.info()
            )
            if isinstance(redis_info, dict):
                return {
                    "cache_type": "Redis (Direct)",
                    "redis_version": redis_info.get(
                        "redis_version", "unknown"
                    ),
                    "used_memory_human": redis_info.get(
                        "used_memory_human", "unknown"
                    ),
                    "connected_clients": redis_info.get(
                        "connected_clients", "unknown"
                    ),
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
