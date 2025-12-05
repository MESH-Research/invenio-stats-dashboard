# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service class for operations with community dashboard settings."""

import traceback
from datetime import datetime
from uuid import UUID

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities as communities

from .community_events import CommunityRecordEventsService


class CommunityDashboardsService:
    """Service class for operations with community dashboard settings."""

    def __init__(self):
        """Initialize a CommunityDashboardsService instance."""
        pass

    @staticmethod
    def _is_valid_community_id(community_id: str) -> bool:
        """Check if a string is a valid community ID (UUID format).
        
        Args:
            community_id: String to validate
            
        Returns:
            bool: True if the string is a valid UUID, False otherwise
        """
        if not community_id or not isinstance(community_id, str):
            return False
        
        try:
            UUID(community_id)
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    @staticmethod
    def _extract_community_id_and_fields(community):
        """Extract community ID and custom_fields from various data structures.

        Handles:
        - Dict with "id" key (from CommunityListResult.hits projections)
        - CommunityItem objects with .id property
        - CommunityItem objects with .data property (dict with "id" key)
        - CommunityItem.to_dict() (returns dict with "id" key)

        Args:
            community: Community data in any supported format

        Returns:
            tuple: (community_id, custom_fields) or (None, {}) if ID not found
        """
        # Priority 1: If dict, use dict.get()
        if isinstance(community, dict):
            return (
                community.get("id"),
                community.get("custom_fields", {}),
            )

        # Priority 2: If has .id property (CommunityItem), use it
        # and extract custom_fields from .data or .to_dict()
        if hasattr(community, "id"):
            community_id = community.id
            # Try to get custom_fields from .data first
            if hasattr(community, "data"):
                custom_fields = community.data.get("custom_fields", {})
            elif hasattr(community, "to_dict"):
                custom_fields = community.to_dict().get("custom_fields", {})
            else:
                custom_fields = {}
            return (community_id, custom_fields)

        # Priority 3: If has .data property, use it
        if hasattr(community, "data"):
            community_data = community.data
            return (
                community_data.get("id"),
                community_data.get("custom_fields", {}),
            )

        # Priority 4: If has .to_dict() method, use it
        if hasattr(community, "to_dict"):
            community_dict = community.to_dict()
            return (
                community_dict.get("id"),
                community_dict.get("custom_fields", {}),
            )

        # No ID found, skip this community
        return (None, {})

    @staticmethod
    def get_enabled_communities(
        communities: list[dict], include_global: bool = True
    ) -> list[str]:
        """Get enabled communities based on opt-in config and dashboard_enabled.

        If STATS_DASHBOARD_COMMUNITY_OPT_IN is True, only returns communities where
        custom_fields.stats:dashboard_enabled is True. Otherwise, returns all
        communities.

        Args:
            communities: List of community dictionaries or hit objects
                (from scan or similar)
            include_global: Whether to include "global" in the result
                (default: True)

        Returns:
            List of community IDs that should be processed
        """
        opt_in_enabled = current_app.config.get(
            "STATS_DASHBOARD_COMMUNITY_OPT_IN", True
        )

        if not opt_in_enabled:
            community_ids: list[str] = []
            for c in communities:
                community_id, _ = (
                    CommunityDashboardsService._extract_community_id_and_fields(c)
                )
                if community_id:
                    community_ids.append(community_id)
            if include_global:
                community_ids.append("global")
            return community_ids

        filtered_ids: list[str] = []
        for community in communities:
            community_id, custom_fields = (
                CommunityDashboardsService._extract_community_id_and_fields(community)
            )

            if not community_id:
                continue

            dashboard_enabled = custom_fields.get("stats:dashboard_enabled", False)
            if dashboard_enabled is True:
                filtered_ids.append(community_id)

        if include_global:
            filtered_ids.append("global")

        return filtered_ids

    def enable_community_dashboards(
        self,
        ids: tuple[str, ...] | None = None,
        first_active: arrow.Arrow | datetime | None = None,
        active_since: arrow.Arrow | datetime | None = None,
        record_threshold: int = 0,
        filter_priority: list[str] | None = None,
        verbose: bool = False,
    ) -> dict[str, list]:
        """Enable individual communities' dashboards if they match criteria.

        Arguments:
            ids (tuple[str, ...] | None): Individual community ids (UUIDs) for
                communities to enable. If provided, this list is used and the other
                filtering arguments are ignored. Defaults to None.
            first_active (arrow.Arrow | datetime | None): Include only communities
                that were first active prior to or on the provided date. Defaults
                to None.
            active_since (arrow.Arrow | datetime | None): Include only communities
                that have been active on or since the provided date. Defaults to None.
            record_threshold (int): Include only communities with the provided number
                of records or more. Defaults to 0.
            filter_priority (list[str] | None): List of argument names in the order
                in which the filters should be applied. Defaults to None.
            verbose (bool): Flag for displaying verbose output. Defaults to False.

        Returns:
            dict[str, list]: A dictionary with two keys:
                communities_updated: A list of community ids whose dashboard
                    was successfully enabled.
                communities_failed: A list of objects representing the communities
                    who matched the criteria but whose dashboard could not be enabled.
                    Each object includes the community's "id" and an "error_message".

        """
        events_service = CommunityRecordEventsService()
        communities_to_enable = list(ids) if ids else []
        if len(communities_to_enable) < 1:
            communities_to_enable = events_service.filter_communities_by_activity(
                first_active=first_active,
                active_since=active_since,
                record_threshold=record_threshold,
                filter_priority=filter_priority,
            )
            if verbose:
                current_app.logger.info(
                    f"filter_communities_by_activity returned "
                    f"{len(communities_to_enable)} communities: "
                    f"{communities_to_enable}"
                )
        elif first_active or active_since or record_threshold:
            current_app.logger.warning(
                "Filtering criteria (first_active, active_since, record_threshold) "
                "are ignored when specific community IDs are provided."
            )

        results: dict[str, list] = {
            "communities_updated": [],
            "communities_failed": [],
        }
        for community_id in communities_to_enable:
            # Skip "global" as it's a business-logic label, not an actual community ID
            if community_id == "global":
                if verbose:
                    current_app.logger.info(
                        "Skipping 'global' since it's not a community"
                    )
                continue
            
            # Validate that the community_id looks like a valid UUID
            if not CommunityDashboardsService._is_valid_community_id(community_id):
                error_msg = (
                    f"Skipping invalid community ID: '{community_id}'. "
                    "Community IDs must be in UUID format. "
                    "This may indicate a parsing error or invalid data."
                )
                current_app.logger.warning(error_msg)
                results["communities_failed"].append({
                    "id": community_id,
                    "error_message": (
                        f"Invalid community ID format: expected UUID, "
                        f"got '{community_id}'"
                    ),
                })
                continue
            
            try:
                if verbose:
                    current_app.logger.info(
                        f"Attempting to read community with ID: '{community_id}' "
                        f"(type: {type(community_id).__name__})"
                    )
                community_item = communities.service.read(system_identity, community_id)
                community_dict = community_item.to_dict()
                community_dict.setdefault("custom_fields", {})[
                    "stats:dashboard_enabled"
                ] = True

                update_result = communities.service.update(
                    system_identity, community_id, community_dict
                )
                update_dict = update_result.to_dict()
                try:
                    assert update_dict.get("custom_fields", {}).get(
                        "stats:dashboard_enabled"
                    )
                    results["communities_updated"].append(update_dict["id"])
                except AssertionError:
                    current_app.logger.error(
                        f"Failed to enable dashboard for community {update_dict['id']}"
                    )
                    results["communities_failed"].append({
                        "id": update_dict["id"],
                        "error_message": (
                            "Update operation did not fail, but the community's "
                            "stats:dashboard_enabled custom field was not updated "
                            "to True."
                        ),
                    })
            except Exception as e:
                error_details = (
                    f"Failed to read community with ID '{community_id}' "
                    f"(type: {type(community_id).__name__}): {e}"
                )
                current_app.logger.error(error_details)
                current_app.logger.error(traceback.format_exc())
                results["communities_failed"].append({
                    "id": community_id,
                    "error_message": f"{e}",
                })

        return results
