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

import redis
from flask import current_app


class StatsCache:
    """Cache manager for statistics data series."""

    def __init__(self, compression_method: str | None = None):
        """Initialize the cache manager with direct Redis connection."""
        base_redis_url = current_app.config.get(
            'CACHE_REDIS_URL', 'redis://localhost:6379/6'
        )

        self.cache_prefix = current_app.config.get(
            'STATS_CACHE_PREFIX', 'stats_dashboard'
        )

        redis_url = base_redis_url
        self.redis_client: redis.Redis = redis.from_url(
            redis_url, decode_responses=False
        )
        # Get compression method from parameter or config, default to brotli
        if compression_method is None:
            compression_method = current_app.config.get(
                'STATS_CACHE_COMPRESSION_METHOD', 'brotli'
            )

    def _generate_cache_key(
        self,
        community_id: str,
        stat_name: str,
        start_date: str = "",
        end_date: str = "",
        date_basis: str = "added",
        content_type: str | None = None,
    ) -> str:
        """Generate a cache key for the given parameters.

        We hash keys to shorten them for efficiency.

        Args:
            community_id: Community ID or "global"
            stat_name: Name of the statistics query
            start_date: Start date string
            end_date: End date string
            date_basis: Date basis for the query
            content_type: Content type for content negotiation

        Returns:
            Cache key string
        """
        key_data = {
            "community_id": community_id,
            "stat_name": stat_name,
            "start_date": start_date,
            "end_date": end_date,
            "date_basis": date_basis,
        }

        if content_type:
            key_data["content_type"] = content_type

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{self.cache_prefix}:{key_hash}"

    def get_cached_data(
        self,
        community_id: str,
        stat_name: str,
        start_date: str = "",
        end_date: str = "",
        date_basis: str = "added",
        content_type: str | None = None,
    ) -> bytes | None:
        """Get cached compressed data for the given parameters.

        Args:
            community_id: Community ID or "global"
            stat_name: Name of the statistics query
            start_date: Start date string
            end_date: End date string
            date_basis: Date basis for the query
            content_type: Content type for content negotiation

        Returns:
            Cached compressed data bytes or None if not found
        """
        cache_key = self._generate_cache_key(
            community_id, stat_name, start_date, end_date, date_basis,
            content_type
        )

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data is not None:
                if isinstance(cached_data, bytes):
                    return cached_data
                else:
                    return str(cached_data).encode('utf-8')
            else:
                return None
        except Exception as e:
            current_app.logger.warning(f"Cache get error for key {cache_key}: {e}")
            return None

    def set_cached_data(
        self,
        data: Any,
        community_id: str,
        stat_name: str,
        start_date: str = "",
        end_date: str = "",
        date_basis: str = "added",
        content_type: str | None = None,
        timeout: int | None = None,
    ) -> bool:
        """Cache compressed data for the given parameters.

        Args:
            data: Data to cache (will be compressed)
            community_id: Community ID or "global"
            stat_name: Name of the statistics query
            start_date: Start date string
            end_date: End date string
            date_basis: Date basis for the query
            content_type: Content type for content negotiation
            timeout: Cache timeout in seconds (optional)

        Returns:
            True if caching was successful, False otherwise
        """
        cache_key = self._generate_cache_key(
            community_id, stat_name, start_date, end_date, date_basis,
            content_type
        )

        try:
            if isinstance(data, bytes):
                data_to_store = data
            else:
                data_to_store = str(data).encode('utf-8')

            if timeout is None:
                timeout = current_app.config.get('STATS_CACHE_DEFAULT_TIMEOUT', 3600)

            timeout = int(timeout) if timeout is not None else 3600

            self.redis_client.setex(cache_key, timeout, data_to_store)
            return True

        except Exception as e:
            current_app.logger.warning(f"Cache set error for key {cache_key}: {e}")
            return False

    def invalidate_cache(
        self,
        community_id: str | None = None,
        stat_name: str | None = None,
    ) -> bool:
        """Invalidate cache entries matching the given criteria.

        Args:
            community_id: Community ID to invalidate (optional)
            stat_name: Stat name to invalidate (optional)

        Returns:
            True if invalidation was successful, False otherwise
        """
        try:
            if community_id and stat_name:
                cache_key = self._generate_cache_key(community_id, stat_name)
                self.redis_client.delete(cache_key)
                current_app.logger.info(
                    f"Invalidated cache for {community_id}:{stat_name}"
                )
            else:
                current_app.logger.warning(
                    "Bulk cache invalidation not implemented"
                )
                return False

            return True

        except Exception as e:
            current_app.logger.warning(f"Cache invalidation error: {e}")
            return False

    def clear_all_cache(self) -> tuple[bool, int]:
        """Clear all cache entries in the Redis database.

        Returns:
            Tuple of (success, number_of_deleted_keys)
        """
        try:
            # Get all keys in the database (since it's dedicated to stats cache)
            keys: list[bytes] | list[str] | None = self.redis_client.keys("*")

            if keys is None:
                current_app.logger.warning(
                    "Redis keys() returned None - possible connection issue"
                )
                return False, 0

            if not keys:
                current_app.logger.info("No cache entries found to clear")
                return True, 0

            deleted_count: int = self.redis_client.delete(*keys)
            current_app.logger.info(f"Cleared {deleted_count} cache entries")
            return True, deleted_count

        except Exception as e:
            current_app.logger.warning(f"Cache clear all error: {e}")
            return False, 0

    def list_cache_keys(self) -> list[str]:
        """List all cache keys in the Redis database.

        Returns:
            List of cache keys
        """
        try:
            # Get all keys in the database (since it's dedicated to stats cache)
            keys: list[bytes] | list[str] | None = self.redis_client.keys("*")
            if keys is None:
                return []
            return [
                key.decode('utf-8') if isinstance(key, bytes) else str(key)
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
            keys: list[bytes] | list[str] | None = self.redis_client.keys("*")
            if keys is None:
                key_count = 0
            else:
                key_count = len(keys)

            # Calculate total memory usage
            total_memory = 0
            if keys:
                for key in keys:
                    try:
                        memory_usage: int | None = self.redis_client.memory_usage(key)
                        if memory_usage:
                            total_memory += int(memory_usage)
                    except Exception:
                        # Some Redis versions don't support memory_usage
                        pass

            redis_info: dict[str, Any] = self.redis_client.info()

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
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
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
            redis_info: dict[str, Any] = self.redis_client.info()
            if isinstance(redis_info, dict):
                return {
                    "cache_type": "Redis (Direct)",
                    "redis_version": redis_info.get("redis_version", "unknown"),
                    "used_memory_human": redis_info.get(
                        "used_memory_human", "unknown"
                    ),
                    "connected_clients": redis_info.get(
                        "connected_clients", "unknown"
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "cache_type": "Redis (Direct)",
                    "error": "Could not retrieve Redis info",
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            current_app.logger.warning(f"Cache info error: {e}")
            return {"error": str(e)}
