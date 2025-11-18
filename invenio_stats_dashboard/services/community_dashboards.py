# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service class for operations with community dashboard settings."""

import traceback
from datetime import datetime

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

    def enable_community_dashboards(
        self,
        first_active: arrow.Arrow | datetime | None = None,
        active_since: arrow.Arrow | datetime | None = None,
        record_threshold: int = 0,
        filter_priority: list[str] = None,
    ) -> dict[str, list]:
        """Enable individual communities' dashboards if they match criteria.

        Arguments:
            first_active (arrow.Arrow | datetime | None): Include only communities
                that were first active prior to or on the provided date. Defaults
                to None.
            active_since (arrow.Arrow | datetime | None): Include only communities
                that have been active on or since the provided date. Defaults to None.
            record_threshold (int): Include only communities with the provided number
                of records or more. Defaults to 0.
            filter_priority (list[str] | None): List of argument names in the order
                in which the filters should be applied. Defaults to None.

        Returns:
            dict[str, list]: A dictionary with two keys:
                communities_updated: A list of community ids whose dashboard
                    was successfully enabled.
                communities_failed: A list of objects representing the communities
                    who matched the criteria but whose dashboard could not be enabled.
                    Each object includes the community's "id" and an "error_message".

        """
        events_service = CommunityRecordEventsService()
        communities_to_enable = events_service.filter_communities_by_activity(
            first_active=first_active,
            active_since=active_since,
            record_threshold=record_threshold,
            filter_priority=filter_priority,
        )

        results: dict[str, list] = {
            "communities_updated": [],
            "communities_failed": [],
        }
        for community_id in communities_to_enable:
            try:
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
                current_app.logger.error(traceback.format_exc(e))
                results["communities_failed"].append({
                    "id": update_dict["id"],
                    "error_message": f"{e}",
                })

        return results
