# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file
# for more details.

"""Service for managing cached stats responses."""

from collections.abc import Callable
from typing import Any

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index

from ..models.cached_response import CachedResponse
from ..resources.cache_utils import StatsCache


class CachedResponseService:
    """Service for managing cached stats responses.

    This service orchestrates between the CachedResponse domain model
    and the StatsCache infrastructure layer.
    """

    def __init__(self):
        """Initialize the service."""
        self.cache = StatsCache()
        self.categories = self._get_available_categories()
        self.default_timeout = current_app.config.get(
            "STATS_CACHE_DEFAULT_TIMEOUT", None
        )

    def _get_available_categories(self) -> list[str]:
        """Get available category queries from STATS_QUERIES configuration."""
        configured_queries = current_app.config.get("STATS_QUERIES", {})

        # Filter for category queries (those ending with "-category")
        category_queries = [
            query_name for query_name in configured_queries.keys()
            if query_name.endswith("-category")
        ]

        if not category_queries:
            current_app.logger.warning(
                "No category queries found in STATS_QUERIES configuration"
            )
            return []

        return category_queries

    def create(
        self,
        community_ids: str | list[str] | None = None,
        years: int | list[int] | str | None = None,
        force: bool = False,
        async_mode: bool = False,
        progress_callback: Callable | None = None,
    ) -> dict[str, Any]:
        """Create cached responses for sets of communities, years, and categories.

        Args:
            community_ids: str, list, or None - Community IDs to process
            years: int, list, str, or None - Years to process
            force: bool - Overwrite existing cache
            async_mode: bool - Whether to use async Celery tasks (not implemented yet)
            progress_callback: Callable - Optional callback function for progress
                updates. Called with (current, total, message) parameters

        Returns:
            dict - Results summary
        """
        community_ids = self._normalize_community_ids(community_ids)
        years_per_community = self._normalize_years(years, community_ids)

        all_responses = self._generate_all_response_objects(
            community_ids, years_per_community
        )
        if not force:
            skipped_count = 0
            responses_to_process = []
            for response in all_responses:
                if self.exists(response.community_id, response.year, response.category):
                    skipped_count += 1
                else:
                    responses_to_process.append(response)
            responses = responses_to_process
        else:
            skipped_count = 0
            responses = all_responses

        results = self._create(responses, progress_callback)
        results['skipped'] = skipped_count
        return results

    def read(
        self, community_id: str, year: int, category: str
    ) -> CachedResponse | None:
        """Read a specific cached response from cache.

        Args:
            community_id: Community ID
            year: Year
            category: Category

        Returns:
            CachedResponse if found in cache, None otherwise
        """
        response = CachedResponse(community_id, year, category)
        if response.load_from_cache():
            return response
        return None

    def read_all(self, community_id: str, year: int) -> list[CachedResponse]:
        """Read all cached responses for a community/year combination."""
        responses = []
        for category in self.categories:
            response = self.read(community_id, year, category)
            if response:
                responses.append(response)
        return responses

    def delete(self, community_id: str, year: int, category: str | None = None) -> bool:
        """Delete cached response(s).

        Args:
            community_id: Community ID
            year: Year
            category: Category (if None, deletes all categories for
                this community/year)

        Returns:
            True if successful, False otherwise
        """
        if category:
            response = CachedResponse(community_id, year, category)
            success: bool = self.cache.delete(response.cache_key)
            return success
        else:
            results = []
            for cat in self.categories:
                response = CachedResponse(community_id, year, cat)
                results.append(self.cache.delete(response.cache_key))
            return all(results)

    def exists(self, community_id: str, year: int, category: str) -> bool:
        """Check if a cached response exists.

        Args:
            community_id: Community ID
            year: Year
            category: Category

        Returns:
            True if exists in cache, False otherwise
        """
        response = CachedResponse(community_id, year, category)
        return self.cache.get(response.cache_key) is not None

    def _normalize_community_ids(
        self, community_ids: str | list[str] | None
    ) -> list[str]:
        """Convert various inputs to list of community IDs."""
        if community_ids is None:
            return ["global"]
        elif community_ids == "all":
            return self._get_all_community_ids()
        elif isinstance(community_ids, str):
            return [community_ids]
        else:
            return community_ids

    def _normalize_years(
        self, years: int | list[int] | str | None, community_ids: list[str]
    ) -> dict[str, list[int]]:
        """Convert various inputs to years per community."""
        result = {}

        for community_id in community_ids:
            # Get years valid for this specific community
            community_lifespan = self._get_years_for_community(community_id)

            if years is None or years == "auto":
                result[community_id] = community_lifespan
            elif isinstance(years, int):
                if years in community_lifespan:
                    result[community_id] = [years]
                else:
                    result[community_id] = []
            elif isinstance(years, list):
                result[community_id] = [y for y in years if y in community_lifespan]
            else:
                result[community_id] = []

        return result

    def _get_years_for_community(self, community_id: str) -> list[int]:
        """Get valid years for a specific community based on its creation date."""
        current_year = arrow.now().year

        if community_id == "global":
            first_record_year = self._get_first_record_creation_year()
            return list(range(first_record_year, current_year + 1))
        else:
            creation_year = self._get_community_creation_year(community_id)
            if not creation_year:
                creation_year = self._get_first_record_creation_year()
            return list(range(creation_year, current_year + 1))

    def _get_all_community_ids(self) -> list[str]:
        """Get all community IDs from communities service."""
        try:
            # Use scan to get all communities without size limits
            communities_result = current_communities.service.scan(system_identity)
            return [comm["id"] for comm in communities_result.hits]
        except Exception:
            current_app.logger.warning(
                "Could not fetch community IDs, using global only"
            )
            return ["global"]

    def _get_first_record_creation_year(self) -> int:
        """Get the creation year for the first record."""
        first_record = current_search_client.search(
            index=prefix_index("rdmrecords-records"),
            body={
                "query": {"match_all": {}},
                "size": 1,
                "sort": [{"created": {"order": "asc"}}]
            }
        )
        created_date = first_record["hits"]["hits"][0]["_source"]["created"]
        return int(arrow.get(created_date).year)

    def _get_community_creation_year(self, community_id: str) -> int | None:
        """Get the creation year for a community.

        Because of issues with migrated community creation dates we base this on the
        earliest stats-community-events records for each community.

        Args:
            community_id: The ID of the community to get the creation year for

        Returns:
            The creation year for the community, or None if no creation year is found
        """
        try:
            earliest_event = current_search_client.search(
                index=prefix_index("stats-community-events"),
                body={
                    "query": {"term": {"community_id": community_id}},
                    "size": 1,
                    "sort": [{"timestamp": {"order": "asc"}}]
                }
            )

            if earliest_event["hits"]["total"]["value"] > 0:
                timestamp = earliest_event["hits"]["hits"][0]["_source"]["timestamp"]
                return int(arrow.get(timestamp).year)
        except Exception as e:
            current_app.logger.warning(
                f"Could not find earliest event for community {community_id}: {e}"
            )
        return None

    def _generate_all_response_objects(
        self, community_ids: list[str], years: list[int] | dict[str, list[int]]
    ) -> list[CachedResponse]:
        """Generate CachedResponse objects for all combinations."""
        responses = []

        for community_id in community_ids:
            # Get years for this specific community
            if isinstance(years, dict):
                community_years = years.get(community_id, [])
            else:
                # Fallback to original logic for backwards compatibility
                community_years = years

            for year in community_years:
                for category in self.categories:
                    response = CachedResponse(community_id, year, category)
                    responses.append(response)

        return responses


    def get_or_create(self, request_data: dict, as_json_bytes: bool = False
                      ) -> bytes | dict | list:
        """Get cached response or generate new one.

        Args:
            request_data: Raw request data from API
            as_json_bytes: If True, return JSON bytes. If False, return Python dict.

        Returns:
            JSON bytes if as_json_bytes=True, otherwise Python dict
        """
        # Create CachedResponse and let it handle cache/generation
        response = CachedResponse.from_request_data(request_data)
        response.get_or_generate()

        # Return in requested format
        return response.bytes_data if as_json_bytes else response.object_data


    def _create(
        self, responses: list[CachedResponse], progress_callback: Callable | None = None
    ) -> dict[str, Any]:
        """Create responses synchronously."""
        results = {"success": 0, "failed": 0, "errors": [], "responses": []}
        total_responses = len(responses)

        for i, response in enumerate(responses):
            try:
                # Call progress callback before processing
                if progress_callback:
                    message = (
                        f"Processing {response.community_id}/"
                        f"{response.year}/{response.category}"
                    )
                    progress_callback(i, total_responses, message)

                # Generate and save in one go
                response.generate()
                response.save_to_cache()

                results["success"] += 1  # type:ignore
                results["responses"].append(response)  # type:ignore
            except Exception as e:
                results["failed"] += 1  # type:ignore
                results["errors"].append({  # type:ignore
                    "community_id": response.community_id,
                    "year": response.year,
                    "category": response.category,
                    "error": str(e),
                })

        # Call progress callback for completion
        if progress_callback:
            progress_callback(total_responses, total_responses, "Completed")

        return results

    def invalidate_cache(self, pattern: str | None = None) -> bool:
        """Invalidate cache entries matching the given pattern.

        Args:
            pattern: Redis key pattern (defaults to all stats cache
                keys)

        Returns:
            True if successful, False otherwise
        """
        success: bool
        count: int
        success, count = self.cache.clear_all(pattern)
        if success and count > 0:
            current_app.logger.info(f"Invalidated {count} cache entries")
        return success

    def list_cache_keys(self, pattern: str | None = None) -> list[str]:
        """List all cache keys matching pattern.

        Args:
            pattern: Redis key pattern (defaults to all stats cache
                keys)

        Returns:
            List of cache keys
        """
        keys: list[str] = self.cache.keys(pattern)
        return keys

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the cache.

        Returns:
            Dictionary with cache information
        """
        info: dict[str, Any] = self.cache.get_cache_info()
        return info

    def get_cache_size_info(self) -> dict[str, Any]:
        """Get detailed cache size information.

        Returns:
            Dictionary with cache size information
        """
        size_info: dict[str, Any] = self.cache.get_cache_size_info()
        return size_info
