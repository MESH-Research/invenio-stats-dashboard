# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for CommunityRecordEventsService."""

import arrow

from invenio_stats_dashboard.services.community_events import (
    CommunityRecordEventsService,
)


class TestCommunityRecordEventsService:
    """Test CommunityRecordEventsService."""

    def test_filter_communities_by_activity_no_filters(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering with no filters returns all communities."""
        # Create events for multiple communities
        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": "comm-1",
                    "record_id": "rec-2",
                    "event_date": "2024-01-16T10:00:00Z",
                },
                {
                    "community_id": "comm-2",
                    "record_id": "rec-3",
                    "event_date": "2024-01-17T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        result = service.filter_communities_by_activity()

        assert len(result) == 2
        assert "comm-1" in result
        assert "comm-2" in result

    def test_filter_communities_by_activity_record_threshold(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering by record threshold."""
        # Create events: comm-1 has 3 events, comm-2 has 1 event
        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": "comm-1",
                    "record_id": "rec-2",
                    "event_date": "2024-01-16T10:00:00Z",
                },
                {
                    "community_id": "comm-1",
                    "record_id": "rec-3",
                    "event_date": "2024-01-17T10:00:00Z",
                },
                {
                    "community_id": "comm-2",
                    "record_id": "rec-4",
                    "event_date": "2024-01-18T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        result = service.filter_communities_by_activity(record_threshold=2)

        assert len(result) == 1
        assert "comm-1" in result
        assert "comm-2" not in result

    def test_filter_communities_by_activity_first_active(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering by first_active date."""
        # comm-1 first active on 2024-01-15, comm-2 first active on 2024-01-20
        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": "comm-2",
                    "record_id": "rec-2",
                    "event_date": "2024-01-20T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        # Filter for communities first active on or before 2024-01-18
        result = service.filter_communities_by_activity(
            first_active=arrow.get("2024-01-18T00:00:00Z")
        )

        assert len(result) == 1
        assert "comm-1" in result
        assert "comm-2" not in result

    def test_filter_communities_by_activity_active_since(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering by active_since date."""
        # comm-1 last active on 2024-01-15, comm-2 last active on 2024-01-20
        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": "comm-2",
                    "record_id": "rec-2",
                    "event_date": "2024-01-20T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        # Filter for communities active on or since 2024-01-18
        result = service.filter_communities_by_activity(
            active_since=arrow.get("2024-01-18T00:00:00Z")
        )

        assert len(result) == 1
        assert "comm-2" in result
        assert "comm-1" not in result

    def test_filter_communities_by_activity_multiple_filters(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering with multiple filters combined."""
        # comm-1: 3 events, first on 2024-01-15, last on 2024-01-17
        # comm-2: 2 events, first on 2024-01-10, last on 2024-01-15
        # comm-3: 1 event, first on 2024-01-12, last on 2024-01-12
        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": "comm-1",
                    "record_id": "rec-2",
                    "event_date": "2024-01-16T10:00:00Z",
                },
                {
                    "community_id": "comm-1",
                    "record_id": "rec-3",
                    "event_date": "2024-01-17T10:00:00Z",
                },
                {
                    "community_id": "comm-2",
                    "record_id": "rec-4",
                    "event_date": "2024-01-10T10:00:00Z",
                },
                {
                    "community_id": "comm-2",
                    "record_id": "rec-5",
                    "event_date": "2024-01-15T10:00:00Z",
                },
                {
                    "community_id": "comm-3",
                    "record_id": "rec-6",
                    "event_date": "2024-01-12T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        # Filter: first_active <= 2024-01-15, active_since >= 2024-01-16, threshold >= 2
        result = service.filter_communities_by_activity(
            first_active=arrow.get("2024-01-15T00:00:00Z"),
            active_since=arrow.get("2024-01-16T00:00:00Z"),
            record_threshold=2,
        )

        # Only comm-1 should match:
        # - first_active <= 2024-01-15: comm-1 (2024-01-15), comm-2
        #   (2024-01-10), comm-3 (2024-01-12) ✓
        # - active_since >= 2024-01-16: comm-1 (2024-01-17), comm-2
        #   (2024-01-15) ✗, comm-3 (2024-01-12) ✗
        # - record_threshold >= 2: comm-1 (3), comm-2 (2), comm-3 (1) ✗
        assert len(result) == 1
        assert "comm-1" in result

    def test_filter_communities_by_activity_no_matches(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering when no communities match criteria."""
        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        # Filter with impossible criteria
        result = service.filter_communities_by_activity(
            first_active=arrow.get("2024-01-10T00:00:00Z"),
            active_since=arrow.get("2024-01-20T00:00:00Z"),
            record_threshold=10,
        )

        assert len(result) == 0

    def test_filter_communities_by_activity_empty_index(
        self, running_app, create_stats_indices, search_clear
    ):
        """Test filtering when no events exist."""
        service = CommunityRecordEventsService()
        result = service.filter_communities_by_activity()

        assert len(result) == 0

    def test_filter_communities_by_activity_with_datetime(
        self, running_app, create_stats_indices, search_clear, create_community_events
    ):
        """Test filtering accepts datetime objects in addition to arrow.Arrow."""
        from datetime import datetime

        create_community_events(
            [
                {
                    "community_id": "comm-1",
                    "record_id": "rec-1",
                    "event_date": "2024-01-15T10:00:00Z",
                },
            ]
        )

        service = CommunityRecordEventsService()
        # Use datetime instead of arrow.Arrow
        result = service.filter_communities_by_activity(
            first_active=datetime(2024, 1, 18, 0, 0, 0)  # noqa: E501
        )

        assert len(result) == 1
        assert "comm-1" in result

