# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service class for operations with community add/remove events."""

from datetime import datetime

import arrow
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.aggs import Max, Min, Terms
from opensearchpy.helpers.query import Match_all
from opensearchpy.helpers.search import Search


class CommunityRecordEventsService:
    """Service class for operations with community add/remove events."""

    def __init__(self):
        """Initialize a CommunityRecordEventsService instance."""

    def filter_communities_by_activity(
        self,
        first_active: arrow.Arrow | datetime | None = None,
        active_since: arrow.Arrow | datetime | None = None,
        record_threshold: int = 0,
        filter_priority: list[str] = None,
    ):
        """Find communities with record events matching the provided parameters.

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
            list[dict]: A list of community record dictionaries that match the filters.
        """
        event_search = Search(
            using=current_search_client, index=prefix_index("stats-community-events")
        ).query(Match_all())

        event_search = event_search.extra(size=0)

        by_community = event_search.aggs.bucket(
            "by_community", Terms(field="community_id")
        )
        by_community.metric("min_event_date", Min(field="event_date"))
        by_community.metric("max_event_date", Max(field="event_date"))

        event_results = event_search.execute()

        community_info = {}
        for bucket in event_results.aggregations.by_community.buckets:
            bucket_dict = bucket.to_dict()
            record_count = bucket_dict["doc_count"]
            first_event = bucket_dict["min_event_date"].get("value")
            last_event = bucket_dict["max_event_date"].get("value")
            if record_count < record_threshold:
                continue
            if first_active and first_active > arrow.get(first_event):
                continue
            if active_since and active_since > arrow.get(last_event):
                continue

            community_info[bucket_dict["key"]] = {
                "record_count": record_count,
                "first_event": first_event,
                "last_event": last_event,
            }

        return list(community_info.keys())
