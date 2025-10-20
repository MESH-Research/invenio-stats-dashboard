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
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities

from ..resources.cache_utils import StatsCache


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
            community_id: Community ID, slug, or 'global' for global stats
            year: Year for the cached response
            category: Data series category (e.g., 'record_delta', 'usage_delta')
            cache_type: 'community' or 'global'
        """
        self.community_id = self._resolve_community_id(community_id)
        self.year = year
        self.category = category
        self.cache_type = cache_type
        self._cache_key: str | None = None
        self._bytes_data: bytes | None = None
        self._object_data: dict | list | None = None
        self._created_at: arrow.Arrow | None = None
        self._expires_at: arrow.Arrow | None = None

        self.request_data = {
            "stat": self.category,
            "params": {
                "community_id": (
                    self.community_id if not self.is_global else "global"
                ),
                "start_date": f"{self.year}-01-01",
                "end_date": f"{self.year}-12-31",
                "date_basis": "added",  # Match API resource default
            }
        }

    @staticmethod
    def from_request_data(
        request_data: dict, cache_type: str = "community"
    ) -> "CachedResponse":
        """Create a CachedResponse from raw request data.

        Args:
            request_data: Raw request data to extract parameters from
            cache_type: 'community' or 'global'

        Returns:
            CachedResponse instance with extracted parameters
        """
        query_name = list(request_data.keys())[0]
        query_data = request_data[query_name]
        params = query_data["params"]

        community_id = params.get("community_id", "global")
        year = int(params["start_date"].split("-")[0])
        category = query_name

        return CachedResponse(community_id, year, category, cache_type)

    def _resolve_community_id(self, community_id: str) -> str:
        """Resolve community ID from slug or return as-is if already UUID or 'global'.

        If resolution fails, return the original value. This allows for graceful
        handling of invalid slugs.

        NOTE: This assumes a UUID of the form xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.

        Args:
            community_id: Community ID, slug, or 'global'

        Returns:
            Resolved community UUID or 'global'
        """
        if community_id == "global":
            return "global"

        # If it looks like a UUID, return as-is
        if len(community_id) == 36 and community_id.count("-") == 4:
            return community_id

        # Otherwise, treat as slug and resolve to UUID
        try:
            communities_result = current_communities.service.search(
                system_identity,
                params={"q": f"slug:{community_id}"},
                size=1
            )

            if communities_result.hits:
                return communities_result.hits[0]["id"]
            else:
                return community_id

        except Exception:
            return community_id

    @property
    def is_global(self) -> bool:
        """Check if this is a global stats response."""
        return self.community_id == "global"

    @property
    def bytes_data(self) -> bytes:
        """Get data as JSON bytes.

        If only object_data is populated, serialize it to bytes.

        Returns:
            JSON bytes
            
        Raises:
            ValueError: If data cannot be serialized to JSON.
        """
        if self._bytes_data is not None:
            return self._bytes_data

        if self._object_data is not None:
            self._bytes_data = json.dumps(self._object_data).encode("utf-8")
            return self._bytes_data

        raise ValueError("No data available")

    @property
    def object_data(self) -> dict | list:
        """Get data as Python object (lazily loaded from bytes if needed).

        Returns:
            Python dict or list
            
        Raises:
            ValueError: If bytes data cannot be deserialized from JSON.
        """
        if self._object_data is not None:
            return self._object_data

        if self._bytes_data is not None:
            self._object_data = json.loads(self._bytes_data.decode("utf-8"))
            return self._object_data

        raise ValueError("No data available")

    @property
    def cache_key(self) -> str:
        """Get the cache key for this response."""
        if self._cache_key is None:
            self._cache_key = self.generate_cache_key(
                "application/json", self.request_data
            )
        return self._cache_key

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
        return self._expires_at is not None and arrow.utcnow() > self._expires_at

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

        key_data: dict[str, Any] = {"request_data": request_data}
        if content_type:
            key_data["content_type"] = content_type

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{cache_prefix}:{key_hash}"

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
            response._object_data = json.loads(data.decode("utf-8"))
        else:
            # Store as bytes for passthrough - no unnecessary decode/encode
            response._bytes_data = data
        # We don't know the original timestamps from cached bytes
        return response

    def generate(self) -> "CachedResponse":
        """Generate data by executing the appropriate query.

        Returns:
            Self (for method chaining)
            
        Raises:
            ValueError: If query type is not configured or parameters are invalid.
        """
        configured_queries = current_app.config.get("STATS_QUERIES", {})
        allowed_params = {
            "community_id",
            "start_date",
            "end_date",
            "category",
            "metric",
            "date_basis",
        }

        query_name = self.request_data["stat"]
        query_params = self.request_data["params"]

        if query_name not in configured_queries:
            raise ValueError(f"Unknown query: {query_name}")

        if any([p for p in query_params.keys() if p not in allowed_params]):
            raise ValueError(
                f"Unknown parameter in request body for query {query_name}"
            )

        query_config = configured_queries[query_name]
        query_class = query_config["cls"]
        query_index = query_config["params"]["index"]

        query_instance = query_class(name=query_name, index=query_index)
        query_result = query_instance.run(**{
            k: v for k, v in query_params.items() if k in allowed_params
        })

        self._object_data = query_result
        self._bytes_data = None  # Clear bytes cache
        self._created_at = arrow.utcnow()

        default_timeout = current_app.config.get("STATS_CACHE_DEFAULT_TIMEOUT", None)
        if default_timeout:
            self._expires_at = arrow.utcnow().shift(days=default_timeout)
        else:
            self._expires_at = None

        return self

    def load_from_cache(self) -> bool:
        """Try to load data from cache.

        Stores as bytes_data to avoid unnecessary deserialization.
        Will be lazily deserialized if needed.

        Sets created_at to now and expires_at based on actual Redis TTL.

        Returns:
            True if data was loaded from cache, False otherwise
        """
        cache = StatsCache()
        cached_data = cache.get(self.cache_key)

        if cached_data:
            self._bytes_data = cached_data
            self._object_data = None

            # We don't know when the data was originally created
            self._created_at = None

            ttl_seconds = cache.get_ttl(self.cache_key)
            if ttl_seconds and ttl_seconds > 0:
                self._expires_at = arrow.utcnow().shift(seconds=ttl_seconds)
            else:
                self._expires_at = None

            return True
        return False

    def save_to_cache(self) -> bool:
        """Save data to cache.

        Returns:
            True if successful, False otherwise
        """
        cache = StatsCache()
        default_timeout = current_app.config.get("STATS_CACHE_DEFAULT_TIMEOUT", None)
        timeout = None
        if default_timeout:
            timeout = default_timeout * 86400  # Convert days to seconds

        try:
            cache.set(self.cache_key, self.bytes_data, timeout=timeout)
            return True
        except Exception as e:
            current_app.logger.error(
                f"Failed to cache response for "
                f"{self.community_id}/{self.year}/{self.category}: {e}"
            )
            return False

    def get_or_generate(self) -> "CachedResponse":
        """Load from cache or generate new data.

        Returns:
            Self with data loaded (for method chaining)
        """
        if not self.load_from_cache():
            self.generate()
            self.save_to_cache()
        return self
