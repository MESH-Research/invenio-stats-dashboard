# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

from invenio_search.proxies import current_search_client
from .records_snapshot_aggs import (
    CommunityRecordsSnapshotCreatedAggregator,
    CommunityRecordsSnapshotAddedAggregator,
    CommunityRecordsSnapshotPublishedAggregator,
)
from .records_delta_aggs import (
    CommunityRecordsDeltaCreatedAggregator,
    CommunityRecordsDeltaPublishedAggregator,
    CommunityRecordsDeltaAddedAggregator,
)
from .usage_snapshot_aggs import CommunityUsageSnapshotAggregator
from .usage_delta_aggs import CommunityUsageDeltaAggregator
from .base import CommunityEventsIndexAggregator


def register_aggregations():
    return {
        "community-records-snapshot-created-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_snapshot_created"
            ),
            "cls": CommunityRecordsSnapshotCreatedAggregator,
            "params": {
                "client": current_search_client,
            },
        },
        "community-records-snapshot-added-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_snapshot_added"
            ),
            "cls": CommunityRecordsSnapshotAddedAggregator,
            "params": {
                "client": current_search_client,
            },
        },
        "community-records-snapshot-published-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_snapshot_published"
            ),
            "cls": CommunityRecordsSnapshotPublishedAggregator,
            "params": {
                "client": current_search_client,
            },
        },
        "community-records-delta-created-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_delta_created"
            ),
            "cls": CommunityRecordsDeltaCreatedAggregator,
            "params": {
                "client": current_search_client,
            },
        },
        "community-records-delta-published-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_delta_published"
            ),
            "cls": CommunityRecordsDeltaPublishedAggregator,
        },
        "community-records-delta-added-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_delta_added"
            ),
            "cls": CommunityRecordsDeltaAddedAggregator,
        },
        "community-usage-snapshot-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_usage_snapshot"
            ),
            "cls": CommunityUsageSnapshotAggregator,
            "params": {
                "client": current_search_client,
            },
        },
        "community-usage-delta-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_usage_delta"
            ),
            "cls": CommunityUsageDeltaAggregator,
            "params": {
                "client": current_search_client,
            },
        },
        "community-events-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_events"
            ),
            "cls": CommunityEventsIndexAggregator,
        },
    }
