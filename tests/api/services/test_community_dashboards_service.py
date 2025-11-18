# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for CommunityDashboardsService."""

import arrow
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities

from invenio_stats_dashboard.services.community_dashboards import (
    CommunityDashboardsService,
)


class TestCommunityDashboardsService:
    """Test CommunityDashboardsService."""

    def test_enable_community_dashboards_with_ids(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
    ):
        """Test enabling dashboards for specific community IDs."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)
        community2 = minimal_community_factory(slug="comm-2", owner=user.user.id)

        service = CommunityDashboardsService()
        result = service.enable_community_dashboards(ids=(community1.id, community2.id))

        assert len(result["communities_updated"]) == 2
        assert community1.id in result["communities_updated"]
        assert community2.id in result["communities_updated"]
        assert len(result["communities_failed"]) == 0

        # Verify the custom field was set
        comm1_dict = current_communities.service.read(
            system_identity, community1.id
        ).to_dict()
        comm2_dict = current_communities.service.read(
            system_identity, community2.id
        ).to_dict()

        assert (
            comm1_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )
        assert (
            comm2_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_with_filtering(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
        create_community_events,
    ):
        """Test enabling dashboards using filtering criteria."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)
        community2 = minimal_community_factory(slug="comm-2", owner=user.user.id)

        # Create events: comm-1 has 3 events, comm-2 has 1 event
        create_community_events(
            [
                {
                    "community_id": community1.id,
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": community1.id,
                    "record_id": "rec-2",
                    "event_date": "2024-01-16T10:00:00Z",
                },
                {
                    "community_id": community1.id,
                    "record_id": "rec-3",
                    "event_date": "2024-01-17T10:00:00Z",
                },
                {
                    "community_id": community2.id,
                    "record_id": "rec-4",
                    "event_date": "2024-01-18T10:00:00Z",
                },
            ]
        )

        service = CommunityDashboardsService()
        # Filter for communities with at least 2 record events
        result = service.enable_community_dashboards(
            ids=(), record_threshold=2
        )

        assert len(result["communities_updated"]) == 1
        assert community1.id in result["communities_updated"]
        assert len(result["communities_failed"]) == 0

        # Verify the custom field was set
        comm1_dict = current_communities.service.read(
            system_identity, community1.id
        ).to_dict()
        assert (
            comm1_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_nonexistent_community(
        self, running_app, db, search_clear
    ):
        """Test enabling dashboard for non-existent community."""
        service = CommunityDashboardsService()
        result = service.enable_community_dashboards(
            ids=("nonexistent-community-id",)
        )

        assert len(result["communities_updated"]) == 0
        assert len(result["communities_failed"]) == 1
        assert result["communities_failed"][0]["id"] == "nonexistent-community-id"
        assert "error_message" in result["communities_failed"][0]

    def test_enable_community_dashboards_mixed_success_failure(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
    ):
        """Test enabling dashboards with some valid and some invalid IDs."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

        service = CommunityDashboardsService()
        result = service.enable_community_dashboards(
            ids=(community1.id, "nonexistent-community-id")
        )

        assert len(result["communities_updated"]) == 1
        assert community1.id in result["communities_updated"]
        assert len(result["communities_failed"]) == 1
        assert result["communities_failed"][0]["id"] == "nonexistent-community-id"

        # Verify the custom field was set for the successful community
        comm1_dict = current_communities.service.read(
            system_identity, community1.id
        ).to_dict()
        assert (
            comm1_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_empty_ids_with_filters(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
        create_community_events,
    ):
        """Test enabling dashboards with empty IDs but filtering criteria."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

        create_community_events(
            [
                {
                    "community_id": community1.id,
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
            ]
        )

        service = CommunityDashboardsService()
        result = service.enable_community_dashboards(
            ids=(), record_threshold=1
        )

        assert len(result["communities_updated"]) == 1
        assert community1.id in result["communities_updated"]

        # Verify the custom field was set
        comm1_dict = current_communities.service.read(
            system_identity, community1.id
        ).to_dict()
        assert (
            comm1_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_no_matches(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
        create_community_events,
    ):
        """Test enabling dashboards when no communities match criteria."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

        create_community_events(
            [
                {
                    "community_id": community1.id,
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
            ]
        )

        service = CommunityDashboardsService()
        # Filter with impossible criteria
        result = service.enable_community_dashboards(
            ids=(), record_threshold=100
        )

        assert len(result["communities_updated"]) == 0
        assert len(result["communities_failed"]) == 0

    def test_enable_community_dashboards_with_first_active(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
        create_community_events,
    ):
        """Test enabling dashboards with first_active filter."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)
        community2 = minimal_community_factory(slug="comm-2", owner=user.user.id)

        create_community_events(
            [
                {
                    "community_id": community1.id,
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": community2.id,
                    "record_id": "rec-2",
                    "event_date": "2024-01-20T10:00:00Z",
                },
            ]
        )

        service = CommunityDashboardsService()
        # Filter for communities first active on or before 2024-01-18
        result = service.enable_community_dashboards(
            ids=(), first_active=arrow.get("2024-01-18T00:00:00Z")
        )

        assert len(result["communities_updated"]) == 1
        assert community1.id in result["communities_updated"]

        # Verify the custom field was set
        comm1_dict = current_communities.service.read(
            system_identity, community1.id
        ).to_dict()
        assert (
            comm1_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_with_active_since(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
        create_community_events,
    ):
        """Test enabling dashboards with active_since filter."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)
        community2 = minimal_community_factory(slug="comm-2", owner=user.user.id)

        create_community_events(
            [
                {
                    "community_id": community1.id,
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": community2.id,
                    "record_id": "rec-2",
                    "event_date": "2024-01-20T10:00:00Z",
                },
            ]
        )

        service = CommunityDashboardsService()
        # Filter for communities active on or since 2024-01-18
        result = service.enable_community_dashboards(
            ids=(), active_since=arrow.get("2024-01-18T00:00:00Z")
        )

        assert len(result["communities_updated"]) == 1
        assert community2.id in result["communities_updated"]

        # Verify the custom field was set
        comm2_dict = current_communities.service.read(
            system_identity, community2.id
        ).to_dict()
        assert (
            comm2_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_ids_override_filters(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
        create_community_events,
    ):
        """Test that when IDs are provided, filtering criteria are ignored."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)
        community2 = minimal_community_factory(slug="comm-2", owner=user.user.id)

        # Create events: comm-1 has 3 events, comm-2 has 1 event
        create_community_events(
            [
                {
                    "community_id": community1.id,
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": community1.id,
                    "record_id": "rec-2",
                    "event_date": "2024-01-16T10:00:00Z",
                },
                {
                    "community_id": community1.id,
                    "record_id": "rec-3",
                    "event_date": "2024-01-17T10:00:00Z",
                },
                {
                    "community_id": community2.id,
                    "record_id": "rec-4",
                    "event_date": "2024-01-18T10:00:00Z",
                },
            ]
        )

        service = CommunityDashboardsService()
        # Provide IDs and filtering criteria - IDs should take precedence
        result = service.enable_community_dashboards(
            ids=(community2.id,), record_threshold=2
        )

        # comm-2 should be enabled even though it doesn't meet the threshold
        assert len(result["communities_updated"]) == 1
        assert community2.id in result["communities_updated"]

        # Verify the custom field was set
        comm2_dict = current_communities.service.read(
            system_identity, community2.id
        ).to_dict()
        assert (
            comm2_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

    def test_enable_community_dashboards_verbose(
        self,
        running_app,
        db,
        search_clear,
        minimal_community_factory,
        user_factory,
    ):
        """Test enabling dashboards with verbose flag."""
        user = user_factory(email="test@example.com")
        community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

        service = CommunityDashboardsService()
        result = service.enable_community_dashboards(
            ids=(community1.id,), verbose=True
        )

        assert len(result["communities_updated"]) == 1
        assert len(result["communities_failed"]) == 0

        # Verify the custom field was set
        comm1_dict = current_communities.service.read(
            system_identity, community1.id
        ).to_dict()
        assert (
            comm1_dict.get("custom_fields", {}).get("stats:dashboard_enabled") is True
        )

