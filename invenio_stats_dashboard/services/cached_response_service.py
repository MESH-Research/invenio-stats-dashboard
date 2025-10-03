# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service for managing cached stats responses."""

from datetime import datetime
from typing import Any

import arrow
from flask import current_app

from ..models.cached_response import CachedResponse
from ..tasks.cache_tasks import generate_cached_response_task


class CachedResponseService:
    """Service for managing cached stats responses."""

    def __init__(self):
        """Initialize the service."""
        self.categories = [
            "record_delta",
            "record_snapshot",
            "usage_delta",
            "usage_snapshot",
            "record_delta_data_added",
            "record_delta_data_removed",
            "usage_delta_data_views",
            "usage_delta_data_downloads",
        ]
        self.default_timeout = current_app.config.get(
            "STATS_CACHE_DEFAULT_TIMEOUT", None
        )

    def create(
        self,
        community_ids: str | list[str] | None = None,
        years: int | list[int] | str | None = None,
        force: bool = False,
        async_mode: bool = False,
    ) -> Any:
        """Create cached responses for given communities, years, and all categories.

        Args:
            community_ids: str, list, or None - Community IDs to process
            years: int, list, str, or None - Years to process
            force: bool - Overwrite existing cache
            async_mode: bool - Use Celery tasks

        Returns:
            dict - Results summary
        """
        community_ids = self._normalize_community_ids(community_ids)
        years = self._normalize_years(years, community_ids)

        responses = self._generate_all_response_objects(community_ids, years)

        if not force:
            responses = [
                r
                for r in responses
                if not self.exists(r.community_id, r.year, r.category)
            ]

        if async_mode:
            return self._create_async(responses)
        else:
            return self._create_sync(responses)

    def read(
        self, community_id: str, year: int, category: str
    ) -> CachedResponse | None:
        """Read a specific cached response."""
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

    def update(
        self, community_id: str, year: int, category: str, data: Any
    ) -> bool | Any:
        """Update a cached response with new data."""
        response = CachedResponse(community_id, year, category)
        response._data = data
        response._created_at = arrow.utcnow()
        response._expires_at = self.default_timeout
        return response.save_to_cache()

    def delete(self, community_id: str, year: int, category: str | None = None) -> bool:
        """Delete cached response(s)."""
        if category:
            response = CachedResponse(community_id, year, category)
            return response.delete_from_cache()
        else:
            results = []
            for cat in self.categories:
                response = CachedResponse(community_id, year, cat)
                results.append(response.delete_from_cache())
            return all(results)

    def exists(self, community_id: str, year: int, category: str) -> bool:
        """Check if a cached response exists."""
        response = CachedResponse(community_id, year, category)
        return response.load_from_cache() is not None

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
    ) -> list[int]:
        """Convert various inputs to list of years."""
        lifespan: list[int] = self._get_years_since_creation(community_ids)
        first_year = sorted(lifespan)[0]
        if years is None or years == "auto":
            return lifespan
        elif isinstance(years, int) and years in lifespan:
            return [years]
        elif isinstance(years, list):
            return [y for y in years if int(y) >= first_year]
        else:
            return []

    def _get_all_community_ids(self) -> list[str]:
        """Get all community IDs from existing community model."""
        try:
            from invenio_communities.models import Community

            return [str(c.id) for c in Community.query.all()]
        except Exception:
            current_app.logger.warning(
                "Could not fetch community IDs, using global only"
            )
            return ["global"]

    def _get_years_since_creation(self, community_ids: list[str]) -> list[int]:
        """Get years since creation for given communities."""
        years: set[int] = set()
        current_year = datetime.now().year

        for community_id in community_ids:
            if community_id == "global":
                # For global, use a reasonable range
                years.update(range(2020, current_year + 1))
            else:
                # Get community creation year
                creation_year = self._get_community_creation_year(community_id)
                years.update(range(creation_year, current_year + 1))

        return sorted(list(years))

    def _get_community_creation_year(self, community_id: str) -> int:
        """Get the creation year for a community."""
        try:
            from invenio_communities.models import Community

            community = Community.query.get(community_id)
            if community:
                return community.created.year
        except Exception:
            pass
        return 2020  # Default fallback

    def _generate_all_response_objects(
        self, community_ids: list[str], years: list[int]
    ) -> list[CachedResponse]:
        """Generate CachedResponse objects for all combinations."""
        responses = []

        for community_id in community_ids:
            for year in years:
                for category in self.categories:
                    response = CachedResponse(community_id, year, category)
                    responses.append(response)

        return responses

    def _create_sync(self, responses: list[CachedResponse]) -> dict[str, Any]:
        """Create responses synchronously."""
        results = {"success": 0, "failed": 0, "errors": [], "responses": []}

        for response in responses:
            try:
                response.generate_content()
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

        return results

    def _create_async(self, responses: list[CachedResponse]) -> dict[str, Any]:
        """Create responses asynchronously using Celery tasks."""
        try:
            task_ids = []
            for response in responses:
                task = generate_cached_response_task.delay(
                    response.community_id, response.year, response.category
                )
                task_ids.append(task.id)

            return {"async": True, "task_count": len(task_ids), "task_ids": task_ids}
        except Exception as e:
            current_app.logger.error(f"Failed to create async tasks: {e}")
            # Fallback to sync
            return self._create_sync(responses)
