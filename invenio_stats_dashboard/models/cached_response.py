# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or
# modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""CachedResponse domain model for stats dashboard."""

import hashlib
import json
from typing import Any

import arrow
from flask import current_app


class CachedResponse:
    """Domain model representing a cached stats response.

    This is a pure data model that handles:
    - Data structure and validation
    - Cache key generation (knows what makes a response unique)
    - Serialization/deserialization

    It does NOT handle:
    - Persistence (delegated to CachedResponseService + StatsCache)
    - Query execution (delegated to CachedResponseService)
    """

    def __init__(
        self,
        community_id: str,
        year: int,
        category: str,
        cache_type: str = "community",
    ):
        """Initialize a cached response.

        Args:
            community_id: Community ID or 'global' for global stats
            year: Year for the cached response
            category: Data series category (e.g., 'record_delta',
                'usage_delta')
            cache_type: 'community' or 'global'
        """
        self.community_id = community_id
        self.year = year
        self.category = category
        self.cache_type = cache_type
        self._cache_key = None
        self._data = None
        self._created_at = None
        self._expires_at = None

        self.request_data = {
            self.category: {
                "params": {
                    "community_id": (
                        self.community_id if not self.is_global else "global"
                    ),
                    "start_date": f"{self.year}-01-01",
                    "end_date": f"{self.year}-12-31",
                }
            }
        }

    @property
    def is_global(self) -> bool:
        """Check if this is a global stats response."""
        return self.community_id == "global"

    @property
    def cache_key(self) -> str:
        """Get the cache key for this response."""
        if self._cache_key is None:
            self._cache_key = self.generate_cache_key(
                "application/json", self.request_data
            )
        return self._cache_key

    @property
    def data(self) -> Any:
        """Get the cached data."""
        return self._data

    @property
    def created_at(self) -> arrow.Arrow | None:
        """Get the creation timestamp."""
        return self._created_at

    @property
    def expires_at(self) -> arrow.Arrow | None:
        """Get the expiration timestamp."""
        return self._expires_at

    @property
    def is_expired(self) -> bool:
        """Check if the cached response is expired."""
        return self._expires_at and arrow.utcnow() > self._expires_at

    @staticmethod
    def generate_cache_key(
        content_type: str,
        request_data: dict,
        cache_prefix: str | None = None,
    ) -> str:
        """Generate a cache key for response caching.

        The cache key is determined by the request data structure and
        content type. This ensures consistent key generation across the
        application.

        Args:
            content_type: Content type for the response
            request_data: Full request data dict
            cache_prefix: Optional cache prefix override (defaults to
                config value)

        Returns:
            Cache key string
        """
        if cache_prefix is None:
            cache_prefix = current_app.config.get(
                "STATS_CACHE_PREFIX", "stats_dashboard"
            )

        key_data = {"request_data": request_data}
        if content_type:
            key_data["content_type"] = content_type

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{cache_prefix}:{key_hash}"

    def set_data(
        self,
        data: dict[str, Any],
        created_at: arrow.Arrow | None = None,
        expires_at: arrow.Arrow | None = None,
    ) -> None:
        """Set the response data and metadata.

        Args:
            data: Response data dictionary
            created_at: Creation timestamp (defaults to now)
            expires_at: Expiration timestamp (optional)
        """
        self._data = data
        self._created_at = created_at or arrow.utcnow()
        self._expires_at = expires_at

    def to_bytes(self) -> bytes:
        """Convert to bytes for cache storage or response.

        Stores just the data (not metadata) as JSON bytes, matching
        the existing cache format.

        If data is already bytes (from cache passthrough), return as-is.
        Otherwise, encode dict to JSON bytes.
        """
        if self._data is None:
            raise ValueError("Cannot serialize CachedResponse with no data")
        # If already bytes (from cache passthrough), return as-is
        if isinstance(self._data, bytes):
            return self._data
        # Otherwise encode dict to JSON bytes
        return json.dumps(self._data).encode("utf-8")

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        community_id: str,
        year: int,
        category: str,
        cache_type: str = "community",
        decode: bool = True,
    ) -> "CachedResponse":
        """Create CachedResponse from cached bytes.

        Args:
            data: Cached data bytes
            community_id: Community ID
            year: Year
            category: Category
            cache_type: Cache type
            decode: If True, decode bytes to dict. If False, store as bytes.
                Only decode when you need to work with the data structure.
                For passthrough (e.g. returning to client), keep as bytes.

        Returns:
            Hydrated CachedResponse instance
        """
        response = cls(community_id, year, category, cache_type)
        if decode:
            response._data = json.loads(data.decode("utf-8"))
        else:
            # Store as bytes for passthrough - no unnecessary decode/encode
            response._data = data
        # We don't know the original timestamps from cached bytes
        return response
