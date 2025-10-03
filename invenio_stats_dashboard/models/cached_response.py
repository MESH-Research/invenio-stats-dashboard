# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""CachedResponse domain model for stats dashboard."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from flask import current_app


class CachedResponse:
    """Represents a cached stats response for a specific community/year/category combination."""

    def __init__(self, community_id: str, year: int, category: str, cache_type: str = 'community'):
        """
        Initialize a cached response.

        Args:
            community_id: Community ID or 'global' for global stats
            year: Year for the cached response
            category: Data series category (e.g., 'record_delta', 'usage_delta')
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

    @property
    def is_global(self) -> bool:
        """Check if this is a global stats response."""
        return self.community_id == 'global'

    @property
    def cache_key(self) -> str:
        """Get the cache key for this response."""
        if self._cache_key is None:
            self._cache_key = self._generate_cache_key()
        return self._cache_key

    @property
    def data(self) -> Any:
        """Get the cached data."""
        return self._data

    @property
    def is_expired(self) -> bool:
        """Check if the cached response is expired."""
        return self._expires_at and datetime.now() > self._expires_at

    def _generate_cache_key(self) -> str:
        """Generate cache key using existing cache_utils logic."""
        from ..resources.cache_utils import StatsCache

        # Create a mock request data structure that matches what the API expects
        request_data = {
            self.category: {
                "params": {
                    "community_id": self.community_id if not self.is_global else None,
                    "start_date": f"{self.year}-01-01",
                    "end_date": f"{self.year}-12-31",
                    "category": self.category,
                    "metric": "count"  # Default metric
                }
            }
        }

        # Use the existing cache key generation logic
        cache = StatsCache()
        return cache._generate_response_cache_key("application/json", request_data)

    def generate_content(self) -> Dict[str, Any]:
        """
        Generate the JSON content for this cached response.

        Returns:
            Generated response data
        """
        from ..views.views import StatsDashboardAPIResource

        # Create request data that matches the API structure
        request_data = {
            self.category: {
                "params": {
                    "community_id": self.community_id if not self.is_global else None,
                    "start_date": f"{self.year}-01-01",
                    "end_date": f"{self.year}-12-31",
                    "category": self.category,
                    "metric": "count"
                }
            }
        }

        # Use existing API resource logic to generate the response
        resource = StatsDashboardAPIResource()

        # Create a mock request context
        class MockRequest:
            def __init__(self, data):
                self.json = data
                self.content_type = "application/json"
                self.get_json = lambda: data

        # Generate the response using the existing logic
        try:
            # This is a simplified version - in practice, you'd need to call
            # the actual query logic that the API uses
            response_data = {
                self.category: {
                    "data": [],
                    "metadata": {
                        "community_id": self.community_id,
                        "year": self.year,
                        "category": self.category,
                        "generated_at": datetime.now().isoformat()
                    }
                }
            }

            # Store the generated data
            self._data = response_data
            self._created_at = datetime.now()
            self._expires_at = self._created_at + timedelta(days=30)  # 30-day TTL

            return response_data

        except Exception as e:
            current_app.logger.error(f"Failed to generate content for {self.community_id}/{self.year}/{self.category}: {e}")
            raise

    def to_json(self) -> Dict[str, Any]:
        """Convert the cached response to JSON format."""
        return {
            'community_id': self.community_id,
            'year': self.year,
            'category': self.category,
            'cache_type': self.cache_type,
            'cache_key': self.cache_key,
            'data': self._data,
            'created_at': self._created_at.isoformat() if self._created_at else None,
            'expires_at': self._expires_at.isoformat() if self._expires_at else None
        }

    def save_to_cache(self) -> bool:
        """Save this response to the cache using existing cache_utils."""
        from ..resources.cache_utils import StatsCache

        if self._data is None:
            self.generate_content()

        # Create request data for cache storage
        request_data = {
            self.category: {
                "params": {
                    "community_id": self.community_id if not self.is_global else None,
                    "start_date": f"{self.year}-01-01",
                    "end_date": f"{self.year}-12-31",
                    "category": self.category,
                    "metric": "count"
                }
            }
        }

        cache = StatsCache()
        json_data = json.dumps(self._data)

        # Use configured timeout or None for no expiration
        timeout = current_app.config.get("STATS_CACHE_DEFAULT_TIMEOUT", None)

        return cache.set_cached_response(
            content_type="application/json",
            request_data=request_data,
            response_data=json_data,
            timeout=timeout
        )

    def load_from_cache(self) -> bool:
        """Load this response from the cache using existing cache_utils."""
        from ..resources.cache_utils import StatsCache

        # Create request data for cache lookup
        request_data = {
            self.category: {
                "params": {
                    "community_id": self.community_id if not self.is_global else None,
                    "start_date": f"{self.year}-01-01",
                    "end_date": f"{self.year}-12-31",
                    "category": self.category,
                    "metric": "count"
                }
            }
        }

        cache = StatsCache()
        cached_data = cache.get_cached_response(
            content_type="application/json",
            request_data=request_data
        )

        if cached_data:
            try:
                self._data = json.loads(cached_data.decode('utf-8'))
                return True
            except Exception as e:
                current_app.logger.warning(f"Failed to parse cached data: {e}")
                return False

        return False

    def delete_from_cache(self) -> bool:
        """Delete this response from the cache using existing cache_utils."""
        from ..resources.cache_utils import StatsCache

        # Create request data for cache deletion
        request_data = {
            self.category: {
                "params": {
                    "community_id": self.community_id if not self.is_global else None,
                    "start_date": f"{self.year}-01-01",
                    "end_date": f"{self.year}-12-31",
                    "category": self.category,
                    "metric": "count"
                }
            }
        }

        cache = StatsCache()
        cache_key = cache._generate_response_cache_key("application/json", request_data)

        try:
            cache.redis_client.delete(cache_key)
            return True
        except Exception as e:
            current_app.logger.warning(f"Failed to delete cache key {cache_key}: {e}")
            return False
