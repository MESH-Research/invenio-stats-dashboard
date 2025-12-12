# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file
# for more details.

"""Service for managing cached stats responses."""

from collections.abc import Callable
from typing import Any, cast

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index

from ..constants import FirstRunStatus, RegistryOperation
from ..models.cached_response import CachedResponse
from ..resources.cache_utils import StatsAggregationRegistry, StatsCache
from .community_dashboards import CommunityDashboardsService


class CachedResponseService:
    """Service for managing cached stats responses.

    This service orchestrates between the CachedResponse domain model
    and the StatsCache infrastructure layer.
    """

    def __init__(self):
        """Initialize the service."""
        self.cache = StatsCache()
        self.categories = self._get_available_categories()
        self.default_ttl = current_app.config.get("STATS_CACHE_DEFAULT_TTL", None)

    def _get_available_categories(self) -> list[str]:
        """Get available category queries from STATS_QUERIES configuration.

        Returns:
            list[str]: List of available category names.
        """
        configured_queries = current_app.config.get("STATS_QUERIES", {})

        # Filter for category queries (those ending with "-category")
        category_queries = [
            query_name
            for query_name in configured_queries.keys()
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
        overwrite: bool = False,
        progress_callback: Callable | None = None,
        optimize: bool | None = None,
    ) -> dict[str, Any]:
        """Create cached responses for sets of communities, years, and categories.

        Args:
            community_ids: str, list, or None - Community IDs to process
            years: int, list, str, or None - Years to process
            overwrite: bool - Overwrite existing cache. Applies only to years prior
                to the current year. (Current year's cache objects are always
                re-generated to capture recent data changes)
            progress_callback: Callable - Optional callback function for progress
                updates. Called with (current, total, message) parameters
            optimize: If True, only include metrics used by UI components.
                     If None, uses STATS_DASHBOARD_OPTIMIZE_DATA_SERIES config value.

        Returns:
            dict - Results summary
        """
        if optimize is None:
            optimize = current_app.config.get(
                "STATS_DASHBOARD_OPTIMIZE_DATA_SERIES", True
            )

        community_ids = self._normalize_community_ids(community_ids)
        years_per_community = self._normalize_years(years, community_ids)

        registry = StatsAggregationRegistry()
        current_year = arrow.utcnow().year
        active_registry_keys: list[str] = []

        try:
            active_registry_keys, first_runs_completing = self._setup_registry_keys(
                registry, community_ids, years_per_community, current_year
            )

            # Check for community/year combinations that need cache updates
            # due to recent aggregations and merge them into years_per_community
            updated_combinations, years_per_community = (
                self._get_updated_aggregation_combinations(
                    registry, years_per_community, community_ids
                )
            )
            
            all_responses = self._generate_all_response_objects(
                community_ids, years_per_community, optimize=optimize
            )
            
            # Overwrite responses if:
            # 1. overwrite=True (explicit request)
            # 2. Current year (always regenerate)
            # 3. In updated_combinations (recent aggregation)
            skipped_count = 0
            responses_to_process = []
            registry_keys_to_cleanup: list[str] = []
            
            for response in all_responses:
                should_overwrite = (
                    overwrite
                    or response.year == current_year
                    or (response.community_id, response.year) in updated_combinations
                )
                
                if should_overwrite:
                    responses_to_process.append(response)
                    
                    # Track registry keys to clean up after processing
                    if (response.community_id, response.year) in updated_combinations:
                        operation = RegistryOperation.AGG_UPDATED.replace(
                            "{year}", str(response.year)
                        )
                        registry_key = registry.make_registry_key(
                            response.community_id, operation
                        )
                        registry_keys_to_cleanup.append(registry_key)
                elif response.year != current_year and self.exists(
                    response.community_id, response.year, response.category
                ):
                    skipped_count += 1
                else:
                    responses_to_process.append(response)
            
            results = self._create(responses_to_process, progress_callback)
            results["skipped"] = skipped_count

            self._mark_first_runs_completed(
                first_runs_completing, results, current_year, registry
            )

            for registry_key in registry_keys_to_cleanup:
                registry.delete(registry_key)

            return results
        finally:
            if active_registry_keys:
                for key in active_registry_keys:
                    registry.delete(key)

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
        """Read all cached responses for a community/year combination.

        Returns:
            list[CachedResponse]: List of cached response objects.
        """
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
        """Convert various inputs to list of community IDs.

        Returns:
            list[str]: List of community IDs.
        """
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
        """Convert various inputs to years per community.

        Returns:
            dict[str, list[int]]: Dictionary mapping community IDs to year lists.
        """
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

    def _setup_registry_keys(
        self,
        registry: StatsAggregationRegistry,
        community_ids: list[str],
        years_per_community: dict[str, list[int]],
        current_year: int,
    ) -> tuple[list[str], dict[str, str]]:
        """Set up registry keys for tracking cache generation.

        Args:
            registry: StatsAggregationRegistry instance
            community_ids: List of normalized community IDs
            years_per_community: Dictionary mapping community IDs to year lists
            current_year: Current year for first run tracking

        Returns:
            tuple: (active_registry_keys, first_runs_completing)
                where first_runs_completing is a dict mapping community_id to
                first_run_key
        """
        active_registry_keys: list[str] = []
        first_runs_completing: dict[str, str] = {}

        # Set registry keys for all community/year combinations being processed
        for community_id in community_ids:
            years_list = years_per_community.get(community_id, [])
            for year in years_list:
                cache_operation = RegistryOperation.CACHE.replace("{year}", str(year))
                registry_key = registry.make_registry_key(community_id, cache_operation)
                registry.set(
                    registry_key,
                    arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS"),
                    7200,
                )
                active_registry_keys.append(registry_key)
                # Track first runs that are completing
                if year == current_year:
                    first_run_recs = registry.get_all(
                        f"{community_id}_{RegistryOperation.FIRST_RUN}*"
                    )
                    if (
                        len(first_run_recs)
                        and first_run_recs[0][1] == FirstRunStatus.IN_PROGRESS
                    ):
                        first_runs_completing[community_id] = first_run_recs[0][0]

        return active_registry_keys, first_runs_completing

    def _get_years_for_community(self, community_id: str) -> list[int]:
        """Get valid years for a specific community based on its creation date.

        Returns:
            list[int]: List of valid years for the community.
        """
        current_year = arrow.now().year

        if community_id == "global":
            first_record_year = self._get_first_record_creation_year()
            return list(range(first_record_year, current_year + 1))
        else:
            creation_year = self._get_community_creation_year(community_id)
            if not creation_year:
                creation_year = self._get_first_record_creation_year()
            return list(range(creation_year, current_year + 1))

    def _resolve_community_id_or_slug(self, community_id: str) -> str:
        """Resolve community ID from slug or return as-is if already UUID.

        Args:
            community_id(str): The community ID (UUID), slug, or 'global' to resolve.

        Returns:
            str: Resolved community UUID or 'global'. Returns original if resolution 
                 failed.
        """
        if community_id == "global":
            return "global"

        # If it looks like a UUID, return as-is
        if len(community_id) == 36 and community_id.count("-") == 4:
            return community_id

        try:
            communities_result = current_communities.service.search(
                system_identity,
                params={"q": f"slug:{community_id}"},
                size=1,
            )
            result_dict = communities_result.to_dict()
            hits = result_dict.get("hits", {}).get("hits", [])
            if hits:
                return str(hits[0]["id"])
        except Exception as e:
            current_app.logger.warning(
                f"Could not resolve community slug '{community_id}': {e}"
            )

        return community_id

    def _get_all_community_ids(self) -> list[str]:
        """Get all community IDs from communities service.

        Filters communities based on opt-in config and dashboard_enabled custom field
        if STATS_DASHBOARD_COMMUNITY_OPT_IN is True.

        Returns:
            list[str]: List of community IDs (filtered if opt-in is enabled).
        """
        try:
            # Use scan to get all communities without size limits
            communities_result = current_communities.service.scan(system_identity)
            all_communities = list(communities_result.hits)
            # Filter based on opt-in config and dashboard_enabled
            enabled_communities = CommunityDashboardsService.get_enabled_communities(
                all_communities, include_global=True
            )
            return list(enabled_communities)
        except Exception:
            current_app.logger.warning(
                "Could not fetch community IDs, using global only"
            )
            return ["global"]

    def _get_first_record_creation_year(self) -> int:
        """Get the creation year for the first record.

        Returns:
            int: Year of first record creation.
        """
        first_record = current_search_client.search(
            index=prefix_index("rdmrecords-records"),
            body={
                "query": {"match_all": {}},
                "size": 1,
                "sort": [{"created": {"order": "asc"}}],
            },
        )
        created_date = first_record["hits"]["hits"][0]["_source"]["created"]
        return int(arrow.get(created_date).year)

    def _get_updated_aggregation_combinations(
        self,
        registry: StatsAggregationRegistry,
        years_per_community: dict[str, list[int]],
        community_ids: list[str],
    ) -> tuple[set[tuple[str, int]], dict[str, list[int]]]:
        """Get community/year combinations that need cache updates and merge them.

        Checks the registry for AGG_UPDATED entries that indicate recent
        aggregations for historical years. Only includes combinations that are
        in the current batch being processed. Merges these combinations into
        years_per_community and adds communities to community_ids as needed.

        Args:
            registry: StatsAggregationRegistry instance
            years_per_community: Dictionary mapping community IDs to year lists
            community_ids: List of community IDs being processed

        Returns:
            Tuple of:
            - Set of (community_id, year) tuples that need cache updates
            - Updated years_per_community dict with merged combinations
        """
        combinations: set[tuple[str, int]] = set()
        updated_years_per_community = years_per_community.copy()
        updated_community_ids = community_ids.copy()
        communities_in_batch = set(community_ids)
        
        try:
            pattern = "*_agg_updated_*"
            entries = registry.get_all(pattern)
            
            for key, _value in entries:
                if "_agg_updated_" in key:
                    parts = key.split("_agg_updated_")
                    if len(parts) == 2:
                        community_id = parts[0]
                        
                        if community_id not in communities_in_batch:
                            continue
                        
                        try:
                            year = int(parts[1])
                            combinations.add((community_id, year))
                            
                            # Merge into years_per_community
                            if community_id not in updated_years_per_community:
                                updated_years_per_community[community_id] = []
                            if year not in updated_years_per_community[community_id]:
                                updated_years_per_community[community_id].append(year)
                            
                            # Add community to community_ids if not already present
                            if community_id not in updated_community_ids:
                                updated_community_ids.append(community_id)
                                
                        except ValueError:
                            current_app.logger.warning(
                                f"Could not parse year from registry key: {key}"
                            )
        except Exception as e:
            current_app.logger.warning(
                f"Error reading updated aggregation combinations: {e}"
            )
        
        # Update community_ids in place (since it's a list reference)
        community_ids.clear()
        community_ids.extend(updated_community_ids)
        
        return combinations, updated_years_per_community

    def _get_community_creation_year(self, community_id: str) -> int | None:
        """Get the creation year for a community.

        Uses the minimum of:
        1. The earliest stats-community-events event_date (for migrated communities
           where created dates may be incorrect)
        2. The actual community created date (for new communities or as fallback)

        This ensures we get the earliest possible year even if events don't exist
        yet or were created later than the community itself.

        Args:
            community_id: The ID of the community to get the creation year for

        Returns:
            The creation year for the community, or None if no creation year is found
        """
        event_year = None
        try:
            earliest_event = current_search_client.search(
                index=prefix_index("stats-community-events"),
                body={
                    "query": {"term": {"community_id": community_id}},
                    "size": 1,
                    "sort": [{"event_date": {"order": "asc"}}],
                },
            )

            if earliest_event["hits"]["total"]["value"] > 0:
                event_date = earliest_event["hits"]["hits"][0]["_source"]["event_date"]
                event_year = int(arrow.get(event_date).year)
        except Exception as e:
            current_app.logger.warning(
                f"Could not find earliest event for community {community_id}: {e}"
            )

        # Also check the actual community created date
        community_year = None
        try:
            community = current_communities.service.read(
                system_identity, id_=community_id
            )
            community_year = arrow.get(community.data.get("created", "")).year
        except Exception as e:
            current_app.logger.warning(
                f"Could not read community {community_id}: {e}"
            )

        # Return the minimum (earliest) year, or whichever is available
        if event_year is not None and community_year is not None:
            return int(min(event_year, community_year))
        elif event_year is not None:
            return int(event_year)
        elif community_year is not None:
            return int(community_year)
        else:
            return None

    def _generate_all_response_objects(
        self,
        community_ids: list[str],
        years: list[int] | dict[str, list[int]],
        optimize: bool = False,
    ) -> list[CachedResponse]:
        """Generate CachedResponse objects for all combinations.

        Args:
            community_ids: List of community IDs
            years: Years per community or single list
            optimize: If True, extract layout and component names for each community

        Returns:
            list[CachedResponse]: List of generated cached response objects.
        """
        responses = []

        for community_id in community_ids:
            # Get years for this specific community
            if isinstance(years, dict):
                community_years = years.get(community_id, [])
            else:
                # Fallback to original logic for backwards compatibility
                community_years = years

            # Extract component names if optimization is enabled
            component_names: set[str] | None = None
            if optimize:
                from ..config.component_metrics import (
                    extract_component_names_from_layout,
                )
                from ..views.views import get_community_dashboard_layout

                dashboard_type = "community" if community_id != "global" else "global"

                if community_id != "global":
                    try:
                        community = current_communities.service.read(
                            system_identity, community_id
                        )
                        layout = get_community_dashboard_layout(
                            community, dashboard_type
                        )
                    except Exception:
                        layout = current_app.config["STATS_DASHBOARD_LAYOUT"].get(
                            "global_layout", {}
                        )
                else:
                    layout = current_app.config["STATS_DASHBOARD_LAYOUT"].get(
                        "global_layout", {}
                    )

                component_names = extract_component_names_from_layout(layout)

            for year in community_years:
                for category in self.categories:
                    response = CachedResponse(
                        community_id,
                        year,
                        category,
                        optimize=optimize,
                        component_names=component_names,
                    )
                    responses.append(response)

        return responses

    def get_or_create(
        self, request_data: dict, as_json_bytes: bool = False
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
        if as_json_bytes:
            return cast(  # type: ignore[redundant-cast]
                bytes, response.bytes_data
            )
        else:
            return cast(  # type: ignore[redundant-cast]
                dict | list, response.object_data
            )

    def _mark_first_runs_completed(
        self,
        first_runs_completing: dict[str, str],
        results: dict[str, Any],
        current_year: int,
        registry: StatsAggregationRegistry,
    ) -> None:
        """Mark first runs as completed if all categories were processed.
        
        Args:
            first_runs_completing: Dictionary mapping community_id to first_run_key
            results: Results dictionary from _create with "responses" key
            current_year: The current year
            registry: StatsAggregationRegistry instance
        """
        for community_id, first_run_key in first_runs_completing.items():
            expected_category_count = len(self.categories)
            
            processed_responses = [
                response
                for response in results.get("responses", [])
                if (
                    response.get("community_id") == community_id
                    and response.get("year") == current_year
                )
            ]
            processed_count = len(processed_responses)
            
            if processed_count == expected_category_count:
                registry.set(first_run_key, FirstRunStatus.COMPLETED, ttl=None)
            else:
                skipped_count = expected_category_count - processed_count
                current_app.logger.info(
                    f"Not marking first_run as COMPLETED for {community_id}: "
                    f"{processed_count}/{expected_category_count} "
                    f"categories processed, {skipped_count} skipped"
                )

    def _create(
        self,
        responses: list[CachedResponse],
        progress_callback: Callable | None = None,
    ) -> dict[str, Any]:
        """Create responses synchronously.

        Args:
            responses: List of CachedResponse objects to generate
            progress_callback: Optional callback for progress updates

        Returns:
            dict[str, Any]: Results dictionary with success/failed/skipped
                counts and errors.
        """
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "responses": [],
        }
        total_responses = len(responses)

        for i, response in enumerate(responses):
            try:
                if progress_callback:
                    message = (
                        f"Processing {response.community_id}/"
                        f"{response.year}/{response.category}"
                    )
                    progress_callback(i, total_responses, message)

                response.generate()

                if response.aggregation_complete:
                    # Redis SET operation atomically overwrites existing keys
                    if response.save_to_cache():
                        results["success"] += 1  # type:ignore
                        results["responses"].append(  # type:ignore
                            {
                                "community_id": response.community_id,
                                "year": response.year,
                                "category": response.category,
                                "cache_key": response.cache_key,
                            }
                        )
                    else:
                        results["failed"] += 1  # type:ignore
                        results["errors"].append(  # type:ignore
                            {
                                "community_id": response.community_id,
                                "year": response.year,
                                "category": response.category,
                                "cache_key": response.cache_key,
                                "error": "Failed to save to cache",
                            }
                        )
                        current_app.logger.error(
                            f"Failed to save to cache for {response.community_id}/"
                            f"{response.year}/{response.category}: key "
                            f"{response.cache_key}"
                        )
                else:
                    # Aggregation incomplete - skip caching but don't count as error
                    current_app.logger.info(
                        f"Skipping cache for {response.community_id}/"
                        f"{response.year}/{response.category} - "
                        "aggregation incomplete"
                    )
                    # Type: ignore needed because results dict is typed as Any
                    current_skipped = results.get("skipped", 0)  # type: ignore
                    results["skipped"] = current_skipped + 1  # type: ignore
            except Exception as e:
                results["failed"] += 1  # type:ignore
                results["errors"].append({  # type:ignore
                    "community_id": response.community_id,
                    "year": response.year,
                    "category": response.category,
                    "error": str(e),
                })
            finally:
                response.clear_data()

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

    def list_cached_responses(
        self,
        community_id: str | None = None,
        include_sizes: bool = False,
        include_ages: bool = False,
    ) -> list[dict[str, Any]]:
        """List all cached responses with human-readable identifiers.

        This method reconstructs the human-readable information (community_id,
        year, category) for each cached response by checking all possible
        combinations against the actual cache keys.

        Args:
            community_id: Optional community ID or slug to filter by. If None,
                lists all communities including "global". Slugs will be
                automatically resolved to UUIDs.
            include_sizes: If True, include size in bytes for each entry.
                Uses batched Redis pipelining for efficiency.
            include_ages: If True, include age in seconds for each entry.
                Age is calculated from TTL if available. Uses batched Redis
                pipelining for efficiency.

        Returns:
            List of dictionaries with keys: community_id, year, category,
            cache_key, and optionally size_bytes and age_seconds
        """
        all_cache_keys = set(self.cache.keys())

        if community_id:
            # Resolve slug to ID if needed
            resolved_id = self._resolve_community_id_or_slug(community_id)
            community_ids = [resolved_id]
        else:
            community_ids = ["global"] + self._get_all_community_ids()

        results: list[dict[str, Any]] = []
        cache_keys_to_size = []
        cache_keys_to_age = []

        for comm_id in community_ids:
            years = self._get_years_for_community(comm_id)

            for year in years:
                for category in self.categories:
                    response = CachedResponse(comm_id, year, category)
                    cache_key = response.cache_key

                    if cache_key in all_cache_keys:
                        result = {
                            "community_id": comm_id,
                            "year": year,
                            "category": category,
                            "cache_key": cache_key,
                        }
                        results.append(result)
                        if include_sizes:
                            cache_keys_to_size.append(cache_key)
                        if include_ages:
                            cache_keys_to_age.append(cache_key)

        # Batch fetch sizes if requested
        if include_sizes and cache_keys_to_size:
            sizes = self.cache.get_key_sizes_batch(cache_keys_to_size)
            for result in results:
                cache_key = cast(str, result["cache_key"])
                result["size_bytes"] = sizes.get(cache_key)

        # Batch fetch ages if requested
        if include_ages and cache_keys_to_age:
            default_ttl = current_app.config.get("STATS_CACHE_DEFAULT_TTL", None)
            default_ttl_seconds = (
                default_ttl * 86400 if default_ttl else None
            )

            ttls = self.cache.get_key_ttls_batch(cache_keys_to_age)
            for result in results:
                cache_key = cast(str, result["cache_key"])
                ttl = ttls.get(cache_key)
                # Age can only be calculated if:
                # 1. TTL is available from Redis
                # 2. Default TTL is configured
                # 3. TTL is not -1 (no expiration)
                if ttl is not None and default_ttl_seconds is not None:
                    if ttl == -1:
                        result["age_seconds"] = None
                    elif ttl >= 0:
                        age = default_ttl_seconds - ttl
                        result["age_seconds"] = max(0, age)  # Ensure non-negative
                    else:
                        result["age_seconds"] = None
                else:
                    result["age_seconds"] = None

        return results
