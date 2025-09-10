# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

import datetime
import numbers
import time
from collections.abc import Generator
from functools import wraps
from itertools import chain
from typing import Any, TypedDict

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.aggregations import StatAggregator
from invenio_stats.bookmark import BookmarkAPI
from opensearchpy import AttrDict, AttrList
from opensearchpy.exceptions import NotFoundError
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from .exceptions import CommunityEventIndexingError, DeltaDataGapError
from .proxies import current_community_stats_service
from .queries import (
    CommunityRecordDeltaQuery,
    CommunityUsageDeltaQuery,
    CommunityUsageSnapshotQuery,
)

# ============================================================================
# Record snapshot aggregation types
# ============================================================================


class RecordTotals(TypedDict, total=False):
    """Totals structure for record aggregation documents."""

    metadata_only: int
    with_files: int


class RecordFilesTotals(TypedDict):
    """Totals structure for record files aggregation documents."""

    file_count: int
    data_volume: float


class RecordSnapshotSubcountItem(TypedDict, total=False):
    """Individual subcount item for record snapshot aggregations."""

    id: str
    label: str
    records: RecordTotals
    parents: RecordTotals
    files: RecordFilesTotals


class RecordSnapshotTopSubcounts(TypedDict, total=False):
    """Subcount data structure for record aggregations."""

    by_view: list[RecordSnapshotSubcountItem]
    by_download: list[RecordSnapshotSubcountItem]


class RecordSnapshotDocument(TypedDict):
    """Snapshot document for record aggregations."""

    timestamp: str
    community_id: str
    snapshot_date: str
    subcounts: dict[str, list[RecordSnapshotSubcountItem] | RecordSnapshotTopSubcounts]
    total_records: RecordTotals
    total_parents: RecordTotals
    total_files: RecordFilesTotals
    total_uploaders: int
    updated_timestamp: str


# ============================================================================
# Record delta aggregation types
# ============================================================================


class RecordDeltaCounts(TypedDict):
    """Counts for record delta aggregations."""

    metadata_only: int
    with_files: int


class RecordFilesDeltaCounts(TypedDict):
    """Counts for record files delta aggregations."""

    file_count: int
    data_volume: float


class RecordDeltaTotals(TypedDict):
    """Totals for record delta aggregations."""

    added: RecordDeltaCounts
    removed: RecordDeltaCounts


class RecordFilesDeltaTotals(TypedDict):
    """Totals for record files delta aggregations."""

    added: RecordFilesDeltaCounts
    removed: RecordFilesDeltaCounts


class RecordDeltaSubcountItem(TypedDict):
    """Individual subcount item for record delta aggregations."""

    id: str
    label: str
    records: RecordDeltaTotals
    parents: RecordDeltaTotals
    files: RecordFilesDeltaTotals


class RecordDeltaDocument(TypedDict, total=False):
    """Delta document for record aggregations."""

    timestamp: str
    community_id: str
    period_start: str
    period_end: str
    records: RecordDeltaTotals
    parents: RecordDeltaTotals
    files: RecordFilesDeltaTotals
    uploaders: int
    subcounts: dict[str, list[RecordDeltaSubcountItem]]
    updated_timestamp: str


# ============================================================================
# Usage aggregation types
# ============================================================================


class UsageViewMetrics(TypedDict):
    """View metrics for usage aggregations."""

    total_events: int
    unique_visitors: int
    unique_records: int
    unique_parents: int


class UsageDownloadMetrics(TypedDict):
    """Download metrics for usage aggregations."""

    total_events: int
    unique_visitors: int
    unique_records: int
    unique_parents: int
    unique_files: int
    total_volume: float


class UsageCategories(TypedDict):
    """Totals structure for usage snapshot documents."""

    view: UsageViewMetrics
    download: UsageDownloadMetrics


class UsageSubcountItem(TypedDict, total=False):
    """Totals structure for usage snapshot subcount items."""

    id: str
    label: str | dict[str, str]
    view: UsageViewMetrics
    download: UsageDownloadMetrics


class UsageSnapshotTopCategories(TypedDict):
    """Subcount data structure for usage snapshot aggregations."""

    by_view: list[UsageSubcountItem]
    by_download: list[UsageSubcountItem]


class UsageSnapshotDocument(TypedDict, total=False):
    """Document structure for usage snapshot aggregations.

    Used by:
    - CommunityUsageSnapshotAggregator
    """

    community_id: str
    snapshot_date: str
    totals: UsageCategories
    subcounts: dict[str, list[UsageSubcountItem] | UsageSnapshotTopCategories]
    timestamp: str
    updated_timestamp: str


class UsageDeltaDocument(TypedDict, total=False):
    """Document structure for usage delta aggregations.

    Used by:
    - CommunityUsageDeltaAggregator
    """

    community_id: str
    period_start: str
    period_end: str
    timestamp: str
    totals: UsageCategories
    subcounts: dict[str, list[UsageSubcountItem]]


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


class CommunityBookmarkAPI(BookmarkAPI):
    """Bookmark API for community statistics aggregators.

    This is a copy of the BookmarkAPI class in invenio-stats, but with the
    community_id added to the index to allow separate bookmarks for each community.
    """

    MAPPINGS = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "date": {"type": "date", "format": "date_optional_time"},
                "aggregation_type": {"type": "keyword"},
                "community_id": {"type": "keyword"},
            },
        }
    }

    @staticmethod
    def _ensure_index_exists(func):
        """Decorator for ensuring the bookmarks index exists."""

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not Index(self.bookmark_index, using=self.client).exists():
                self.client.indices.create(
                    index=self.bookmark_index, body=CommunityBookmarkAPI.MAPPINGS
                )
            return func(self, *args, **kwargs)

        return wrapped

    @_ensure_index_exists
    def set_bookmark(self, community_id: str, value: str):
        """Set the bookmark for a community."""
        self.client.index(
            index=self.bookmark_index,
            body={
                "date": value,
                "aggregation_type": self.agg_type,
                "community_id": community_id,
            },
        )
        self.new_timestamp = None

    @_ensure_index_exists
    def get_bookmark(self, community_id: str, refresh_time=60):
        """Get last aggregation date."""
        # retrieve the oldest bookmark
        query_bookmark = (
            Search(using=self.client, index=self.bookmark_index)
            .query(
                Q(
                    "bool",
                    must=[
                        Q("term", aggregation_type=self.agg_type),
                        Q("term", community_id=community_id),
                    ],
                )
            )
            .sort({"date": {"order": "desc"}})
            .extra(size=1)  # fetch one document only
        )
        bookmark = next(iter(query_bookmark.execute()), None)
        if bookmark:
            return arrow.get(bookmark.date)


class CommunityEventBookmarkAPI(CommunityBookmarkAPI):
    """Bookmark API specifically for community event indexing progress.

    This tracks the furthest point of continuous community event indexing
    for each community, allowing us to distinguish between true gaps
    (missing events that should exist) and false gaps (periods where
    no events occurred because nothing happened).
    """

    def __init__(self, client, agg_interval="day"):
        super().__init__(client, "community-events-indexing", agg_interval)


class CommunityAggregatorBase(StatAggregator):
    """Base class for community statistics aggregators."""

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = ""
        self.aggregation_field: str | None = None
        self.copy_fields: dict[str, str] = {}
        self.event_index: str | list[tuple[str, str]] | None = None
        self.first_event_index: str | None = None
        self.record_index: str | list[tuple[str, str]] | None = None
        self.aggregation_index: str | None = None
        self.community_ids: list[str] = kwargs.get("community_ids", [])
        self.agg_interval = "day"
        self.client = kwargs.get("client") or current_search_client
        self.bookmark_api = CommunityBookmarkAPI(
            self.client, self.name, self.agg_interval
        )
        self.catchup_interval = current_app.config.get(
            "COMMUNITY_STATS_CATCHUP_INTERVAL", 365
        )
        # Field name for searching community event indices - overridden by subclasses
        self.event_date_field = "created"
        self.first_event_date_field = "created"
        self.event_community_query_term = lambda community_id: Q(
            "term", parent__communities__ids=community_id
        )

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        raise NotImplementedError

    def _first_event_date_query(
        self, community_id: str
    ) -> tuple[arrow.Arrow | None, arrow.Arrow | None]:
        """Get the first event date from a specific index.

        A min aggregation is more efficient than sorting the query.
        """
        current_search_client.indices.refresh(index=self.first_event_index)
        if community_id == "global":
            query = Q("match_all")
        else:
            query = self.event_community_query_term(community_id)

        search = (
            Search(using=self.client, index=self.first_event_index)
            .query(query)
            .extra(size=0)
        )
        search.aggs.bucket("min_date", "min", field=self.first_event_date_field)
        search.aggs.bucket("max_date", "max", field=self.first_event_date_field)

        results = search.execute()
        min_date = results.aggregations.min_date.value
        max_date = results.aggregations.max_date.value

        return (
            arrow.get(min_date) if min_date else None,
            arrow.get(max_date) if max_date else None,
        )

    def _find_first_event_date(
        self, community_id: str
    ) -> tuple[arrow.Arrow | None, arrow.Arrow | None]:
        """Find the first event document in the index.

        Raises:
            ValueError: If no events are found in any of the event indices.

        Returns:
            A tuple of the earliest and latest event dates. If no events are found,
            both dates are None.
        """

        earliest_date = None
        latest_date = None

        if isinstance(self.first_event_index, str):

            if not self.client.indices.exists(index=self.first_event_index):
                raise ValueError(
                    f"Required index {self.first_event_index} does not exist. "
                    f"Aggregator requires this index to be available."
                )

            earliest_date, latest_date = self._first_event_date_query(community_id)
        elif isinstance(self.record_index, list):
            for _, index in self.record_index:
                early_date, late_date = self._first_event_date_query(community_id)
                if not earliest_date or early_date < earliest_date:
                    earliest_date = early_date
                if not latest_date or late_date > latest_date:
                    latest_date = late_date

        if earliest_date is None:
            raise ValueError(
                f"No events found for community {community_id} in any event index"
            )

        return earliest_date, latest_date

    def _get_end_date(
        self, lower_limit: arrow.Arrow, end_date: arrow.Arrow | None
    ) -> arrow.Arrow:
        """Get the end date for the aggregation.

        If there's more than self.catchup_interval days between the lower limit
        and the end date, we will only aggregate for self.catchup_interval days.
        """
        upper_limit = end_date if end_date else arrow.utcnow()
        if (upper_limit - lower_limit).days > self.catchup_interval:
            upper_limit = lower_limit.shift(days=self.catchup_interval)
        return upper_limit

    def _index_missing_community_events_with_retry(
        self,
        community_id: str,
        upper_limit: arrow.Arrow,
        lower_limit: arrow.Arrow,
        first_index_event_date: arrow.Arrow,
        last_index_event_date: arrow.Arrow,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> arrow.Arrow:
        """Index missing community events with retry logic and exponential backoff."""
        for attempt in range(max_retries):
            try:
                return self._index_missing_community_events(
                    community_id,
                    upper_limit,
                    lower_limit,
                    first_index_event_date,
                    last_index_event_date,
                )
            except Exception as e:

                if attempt == max_retries - 1:
                    raise CommunityEventIndexingError(
                        f"Failed to index community events for {community_id} "
                        f"after {max_retries} attempts: {e}"
                    ) from e

                delay = base_delay * (2**attempt)
                time.sleep(delay)

        # Never reached due to exception above, but needed for type checker
        raise CommunityEventIndexingError(
            f"Failed to index community events for {community_id} "
            f"after {max_retries} attempts"
        )

    def _index_missing_community_events(
        self,
        community_id: str,
        upper_limit: arrow.Arrow,
        lower_limit: arrow.Arrow,
        first_index_event_date: arrow.Arrow,
        last_index_event_date: arrow.Arrow,
    ) -> arrow.Arrow:
        """Index missing community events using bookmarks when available.

        Uses the community event bookmark to track the furthest point of continuous
        indexing. Falls back to querying the index if no bookmark exists.

        Returns:
            The adjusted upper_limit for aggregation.
        """
        event_bookmark_api = CommunityEventBookmarkAPI(self.client)

        indexing_end_date = min(upper_limit, last_index_event_date.ceil("day"))

        indexing_start_date = None

        bookmark_date = event_bookmark_api.get_bookmark(community_id)
        if bookmark_date:
            indexing_start_date = bookmark_date
        else:
            indexing_start_date = first_index_event_date

        if indexing_start_date >= indexing_end_date:
            return upper_limit

        try:
            current_community_stats_service.generate_record_community_events(
                community_ids=[community_id],
                end_date=indexing_end_date.format("YYYY-MM-DD"),
                start_date=indexing_start_date.format("YYYY-MM-DD"),
            )

            event_bookmark_api.set_bookmark(community_id, indexing_end_date.isoformat())

        except Exception as e:
            raise CommunityEventIndexingError(
                f"Community event indexing failed for {community_id}: {e}"
            ) from e

        return upper_limit

    def run(
        self,
        start_date: arrow.Arrow | datetime.datetime | str | None = None,
        end_date: arrow.Arrow | datetime.datetime | str | None = None,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
        return_results: bool = False,
    ) -> list[tuple[int, int | list[dict]]]:
        """Perform an aggregation for community and global stats.

        This method will perform an aggregation as defined by the child class.

        It maintains a separate bookmark for each community as well as for the
        InvenioRDM instance as a whole.

        To avoid running the aggregators for too many days at once, we limit the
        aggregation to self.catchup_interval days at a time. If there is a longer
        interval between the last bookmark (or the start date) and the current date
        (or end date), we will only aggregate for self.catchup_interval days
        and set the bookmark to the end of the interval. Since the aggregators
        are set to run hourly, this means that the aggregators will catch up
        with the latest data over the next several runs. By default, we set the
        catchup interval to 365 days, which means that for most repositories
        the aggregators will catch up with the latest data in a few hours.

        Args:
            start_date: The start date for the aggregation.
            end_date: The end date for the aggregation.
            update_bookmark: Whether to update the bookmark.
            ignore_bookmark: Whether to ignore the bookmark.
            return_results: Whether to return the error results from the bulk
                aggregation or only the error count. This is primarily used in testing.

        Returns:
            A list of tuples representing results from the bulk aggregation. If
            return_results is True, the first element of the tuple is the number of
            records indexed and the second element is the number of errors. If
            return_results is False, the first element of the tuple is the number of
            records indexed and the second element is a list of dictionaries, where
            each dictionary describes an error.
        """
        start_date = arrow.get(start_date) if start_date else None
        end_date = arrow.get(end_date) if end_date else None

        # If no records have been indexed there is nothing to aggregate
        if (
            isinstance(self.record_index, str)
            and not Index(self.record_index, using=self.client).exists()
        ):
            return [(0, [])]
        elif isinstance(self.record_index, list):
            for _, index in self.record_index:
                if not Index(index, using=self.client).exists():
                    return [(0, [])]

        if self.community_ids:
            communities_to_aggregate = self.community_ids
        else:
            communities_to_aggregate = [
                c["id"]
                for c in current_communities.service.read_all(system_identity, [])
            ]
        communities_to_aggregate.append("global")  # Global stats are always aggregated

        results = []
        for community_id in communities_to_aggregate:
            try:
                first_event_date, last_event_date = self._find_first_event_date(
                    community_id
                )
            except ValueError:
                continue

            previous_bookmark = self.bookmark_api.get_bookmark(community_id)

            if not ignore_bookmark:
                if previous_bookmark:
                    lower_limit = arrow.get(previous_bookmark)
                elif start_date:
                    lower_limit = start_date
                else:
                    lower_limit = min(
                        first_event_date or arrow.utcnow(), arrow.utcnow()
                    )
            else:
                lower_limit = min(start_date or arrow.utcnow(), arrow.utcnow())

            # Ensure we don't aggregate more than self.catchup_interval days
            upper_limit = self._get_end_date(lower_limit, end_date)

            first_event_date_safe = first_event_date or arrow.utcnow()
            last_event_date_safe = last_event_date or arrow.utcnow()

            # Check that community add/remove events have been indexed for the desired
            # period and if not, index them first.
            try:
                upper_limit = self._index_missing_community_events_with_retry(
                    community_id,
                    upper_limit,
                    lower_limit,
                    first_event_date_safe,
                    last_event_date_safe,
                )
            except CommunityEventIndexingError as e:
                current_app.logger.error(
                    f"Could not perform aggregations for {community_id}. "
                    f"Error indexing community events, and we cannot perform "
                    f"aggregations without the community events: {e}"
                )
                continue

            # upper_limit could legitimately be < lower_limit if we spent this iteration
            # indexing prior community add/remove events. If so, skip this community
            # iteration without updating the bookmark or performing aggregations
            if upper_limit < lower_limit:
                continue

            next_bookmark = arrow.get(upper_limit).format("YYYY-MM-DDTHH:mm:ss.SSS")

            results.append(
                bulk(
                    self.client,
                    self.agg_iter(
                        community_id,
                        lower_limit,
                        upper_limit,
                        first_event_date_safe,
                        last_event_date_safe,
                    ),
                    stats_only=False if return_results else True,
                    chunk_size=50,
                )
            )
            if update_bookmark:
                self.bookmark_api.set_bookmark(community_id, next_bookmark)

        return results

    def delete_aggregation(
        self,
        index_name: str,
        document_id: str,
    ):
        """Remove the aggregation for a given community and date."""
        self.client.delete(index=index_name, id=document_id)
        self.client.indices.refresh(index=index_name)

    @staticmethod
    def _get_nested_value(
        data: dict | AttrDict,
        path: list,
        key: str | None = None,
        match_field: str = "id",
    ) -> Any:
        """Get a nested value from a dictionary using a list of path segments.

        Args:
            data: The dictionary to traverse
            path: List of path segments to traverse
            key: Optional key to match when traversing arrays
            match_field: Field name to match on when traversing arrays (default: "id")

        Returns:
            The value at the end of the path, or an empty dict if not found
        """
        current = data
        for idx, segment in enumerate(path):
            if isinstance(current, dict) or isinstance(current, AttrDict):
                current = current.get(segment, {})
            elif isinstance(current, list) or isinstance(current, AttrList):
                # For arrays, we sometimes need to find the item that matches our key
                # This is used for fields like subjects where we need to match the
                # specific subject
                if key is not None:
                    matching_items = [
                        item
                        for item in current
                        if isinstance(item, dict) and item.get("id") == key
                    ]
                    current = matching_items[0] if matching_items else {}
                elif isinstance(segment, int):
                    current = current[segment]
                elif isinstance(current, list):
                    current = current[0] if current else {}
            elif idx == len(path) - 1:
                return current
            else:
                return {}
        return current

    @staticmethod
    def _find_matching_item_by_key(
        data_source: list,
        target_path: list,
        key: str | dict,
    ) -> str | dict[str, str]:
        """Find a matching item in a data source by key and extract the label."""
        if not isinstance(data_source, list) or len(data_source) == 0:
            return ""

        if target_path and target_path[-1] == "keyword":
            target_path = target_path[:-1]

        for item in data_source:
            if isinstance(item, dict):
                if item.get("id") == key:
                    return CommunityAggregatorBase._extract_label_from_item(
                        item, target_path
                    )

                if len(target_path) >= 2:
                    nested_obj = item.get(target_path[0])
                    if nested_obj:
                        if isinstance(nested_obj, list):
                            for nested_item in nested_obj:
                                if (
                                    isinstance(nested_item, dict)
                                    and nested_item.get("id") == key
                                ):
                                    return CommunityAggregatorBase._extract_label_from_item(  # noqa: E501
                                        nested_item, target_path[1:]
                                    )
                        elif isinstance(nested_obj, dict):
                            if nested_obj.get("id") == key:
                                return CommunityAggregatorBase._extract_label_from_item(
                                    nested_obj, target_path[1:]
                                )
        return ""

    @staticmethod
    def _extract_label_from_item(
        item: dict[str, str | dict],
        target_path: list,
    ) -> str | dict:
        """Extract the label from a matching item using the remaining path.

        Args:
            item: The item that matched the key
            target_path: The remaining path to extract the label

        Returns:
            The extracted label string or dict
        """
        if len(target_path) == 1:
            label = item.get(target_path[0], "")
        elif len(target_path) > 1:
            label = CommunityAggregatorBase._get_nested_value(item, target_path)
        else:
            label = item

        if isinstance(label, dict) and not label:
            label = ""
        return label if label else ""

    def _should_skip_aggregation(
        self, start_date: arrow.Arrow, last_event_date: arrow.Arrow | None
    ) -> bool:
        """Check if aggregation should be skipped due to no events after start_date.

        Args:
            start_date: The start date for aggregation
            last_event_date: The last event date, or None if no events exist

        Returns:
            True if aggregation should be skipped, False otherwise
        """
        if last_event_date is None:
            return True
        return bool(last_event_date < start_date)

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> (
        RecordSnapshotDocument
        | RecordDeltaDocument
        | UsageSnapshotDocument
        | UsageDeltaDocument
    ):
        """Create a zero-value document for when no events exist.

        This method should be overridden by subclasses to provide the appropriate
        zero-value document structure for their aggregation type.

        Args:
            community_id: The community ID
            current_day: The current day for the document

        Returns:
            A document with zero values appropriate for the aggregator type
        """
        raise NotImplementedError("Subclasses must override _create_zero_document")


class CommunitySnapshotAggregatorBase(CommunityAggregatorBase):
    """Abstract base class for community snapshot aggregators.

    This class provides common functionality shared between different types of
    snapshot aggregators (records and usage) to reduce code duplication.
    """

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
        )
        self.top_subcount_limit = current_app.config.get(
            "COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT", 20
        )
        self.first_event_date_field = "period_start"
        self.event_community_query_term = lambda community_id: Q(
            "term", community_id=community_id
        )
        self.delta_index: str | None = None

    def _copy_snapshot_forward(
        self,
        previous_snapshot: RecordSnapshotDocument | UsageSnapshotDocument,
        current_date: arrow.Arrow,
    ) -> RecordSnapshotDocument | UsageSnapshotDocument:
        """Efficiently copy a previous snapshot forward to the current date.

        This is much more efficient than calling create_agg_dict with empty data
        just to copy the previous snapshot.

        Args:
            previous_snapshot: The previous snapshot document
            current_date: The current date for the new snapshot

        Returns:
            A new snapshot document with updated dates but same cumulative data
        """
        new_snapshot = previous_snapshot.copy()

        new_snapshot["snapshot_date"] = current_date.format("YYYY-MM-DDTHH:mm:ss")
        new_snapshot["timestamp"] = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss")
        new_snapshot["updated_timestamp"] = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss")

        return new_snapshot

    def _get_previous_snapshot(
        self, community_id: str, current_date: arrow.Arrow
    ) -> tuple[RecordSnapshotDocument | UsageSnapshotDocument, bool]:
        """Get the last snapshot document for a community and date.

        If no previous snapshot exists, returns a zero document as the base.

        Args:
            community_id: The community ID
            current_date: The current date

        Returns:
            Previous snapshot document or a zero document if none exists, and a
            boolean indicating if the snapshot is a zero placeholder document.
        """
        previous_date = current_date.shift(days=-1)

        index_name = prefix_index(
            "{0}-{1}".format(self.aggregation_index, previous_date.year)
        )

        # First try: Query for snapshot with exact previous day's date
        try:
            snapshot_search = Search(using=self.client, index=index_name)
            snapshot_search = snapshot_search.query(
                "bool",
                must=[
                    {"term": {"community_id": community_id}},
                    {
                        "range": {
                            "snapshot_date": {
                                "lte": previous_date.format("YYYY-MM-DDTHH:mm:ss")
                            }
                        }
                    },
                ],
            ).sort({"snapshot_date": {"order": "asc"}})
            snapshot_search = snapshot_search.extra(size=1)
            snapshot_results = snapshot_search.execute()
            if snapshot_results.hits.total.value > 0:
                return snapshot_results.hits.hits[0].to_dict()["_source"], False
            else:
                pass
        except NotFoundError:
            pass

        return (
            self._create_zero_document(community_id, previous_date),
            True,
        )

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> RecordSnapshotDocument | UsageSnapshotDocument:
        """Create a zero-value document for when no events exist."""
        raise NotImplementedError("Subclasses must override _create_zero_document")

    def _get_delta_index_by_date(
        self,
        all_delta_documents: list,
        current_iteration_date: arrow.Arrow,
    ) -> int:
        """Get the index of the delta document for the current iteration date.

        Args:
            all_delta_documents: List of delta documents
            current_iteration_date: The current date we're processing

        Returns:
            Index of the delta document for the current iteration date
        """
        target_date = current_iteration_date.date()

        for i, doc in enumerate(all_delta_documents):
            try:
                doc_date = arrow.get(doc["period_start"]).date()
                if doc_date == target_date:
                    return i
            except (KeyError, arrow.parser.ParserError):
                continue

        raise DeltaDataGapError(
            f"Delta data gap detected. Expected document for date "
            f"{current_iteration_date.format('YYYY-MM-DD')}, but none found."
        )

    def _fetch_all_delta_documents(
        self, community_id: str, earliest_date: arrow.Arrow, end_date: arrow.Arrow
    ) -> list:
        """Get daily delta records for a community between start and end dates.

        Also returns the daily delta records for the community before the start date
        so that we can use them to update the top subcounts.

        Returns:
            A list of daily delta records for the community between start and end dates
        """
        delta_search = Search(using=self.client, index=self.delta_index)
        delta_search = delta_search.query(
            "bool",
            must=[
                {"term": {"community_id": community_id}},
                {
                    "range": {
                        "period_start": {
                            "gte": earliest_date.format("YYYY-MM-DDTHH:mm:ss"),
                            "lte": end_date.format("YYYY-MM-DDTHH:mm:ss"),
                        }
                    }
                },
            ],
        )
        delta_search = delta_search.sort({"period_start": {"order": "asc"}})
        delta_search = delta_search.extra(size=10000)

        delta_results = delta_search.execute()
        delta_documents = delta_results.to_dict()["hits"]["hits"]

        # Extract _source and remap subcount field names for easier access
        remapped_documents = []
        for doc in delta_documents:
            delta_dict = doc["_source"]
            mapped_delta_dict = self._map_delta_to_snapshot_subcounts(delta_dict)
            remapped_documents.append(mapped_delta_dict)

        return remapped_documents

    def _map_delta_to_snapshot_subcounts(self, delta_doc: dict) -> dict:
        """Map delta document subcount field names to snapshot field names.

        This method should be overridden by subclasses to provide the appropriate
        mapping logic for their specific data structures.

        Args:
            delta_doc: The delta document with subcounts to remap (mutated in place)

        Returns:
            The same delta document with remapped subcount field names
        """
        raise NotImplementedError(
            "Subclasses must override _map_delta_to_snapshot_subcounts"
        )

    def _build_exhaustive_cache(self, deltas: list, category_name: str) -> dict:
        """Build exhaustive cache for a category from all delta documents.

        Args:
            delta_documents: All delta documents containing both added and removed data
            category_name: Name of the subcount category

        Returns:
            Dictionary mapping item IDs to their cumulative totals
        """
        accumulated: dict[str, int] = {}

        for doc in deltas:
            if "subcounts" in doc:
                subcounts = doc["subcounts"]
                if category_name in subcounts:
                    self._accumulate_category_in_place(
                        accumulated, subcounts[category_name]
                    )

        return accumulated

    def _update_exhaustive_cache(
        self,
        category_name: str,
        delta_document: RecordDeltaDocument | UsageDeltaDocument,
        exhaustive_counts_cache: dict,
    ) -> None:
        """Update existing exhaustive cache in place with latest delta documents.

        Args:
            category_name: Name of the subcount category
            delta_document: Latest delta document to add to the cache
            exhaustive_counts_cache: The exhaustive counts cache
        """
        subcounts = delta_document.get("subcounts", {})
        if subcounts and category_name in subcounts:
            self._accumulate_category_in_place(
                exhaustive_counts_cache[category_name],
                subcounts[category_name],
            )

    def _accumulate_category_in_place(
        self, accumulated: dict, category_items: list
    ) -> None:
        """Accumulate category items into the existing accumulated dictionary.

        This method should be overridden by subclasses to provide the appropriate
        accumulation logic for their specific data structures.

        Args:
            accumulated: Dictionary to accumulate into
            category_items: List of items from a category in a delta document
        """
        raise NotImplementedError(
            "Subclasses must override _accumulate_category_in_place"
        )

    def _select_top_n_from_cache(self, exhaustive_cache: dict, *args) -> list:
        """Select top N items from the exhaustive cache.

        This method should be overridden by subclasses to provide the appropriate
        selection logic for their specific data structures.

        Args:
            exhaustive_cache: Dictionary mapping item IDs to their cumulative totals
            *args: Additional arguments specific to the subclass implementation

        Returns:
            List of top N subcount items
        """
        raise NotImplementedError("Subclasses must override _select_top_n_from_cache")

    def _update_top_subcounts(
        self,
        new_dict: dict,
        deltas: list,
        exhaustive_counts_cache: dict,
        latest_delta: dict = {},
    ) -> None:
        """Update top subcounts.

        This method should be overridden by subclasses to provide the appropriate
        logic for updating top subcounts based on their specific data structures.

        Args:
            new_dict: The aggregation dictionary to modify
            deltas: The daily delta dictionaries to update the subcounts with
            exhaustive_counts_cache: The exhaustive counts cache
            latest_delta: The latest delta document
        """
        raise NotImplementedError("Subclasses must override _update_top_subcounts")

    def _update_cumulative_totals(self, new_dict: dict, delta_doc: dict) -> dict:
        """Update cumulative totals with values from a daily delta document.

        This method should be overridden by subclasses to provide the appropriate
        logic for updating cumulative totals based on their specific data structures.

        Args:
            new_dict: The aggregation dictionary to modify
            delta_doc: The latest delta document

        Returns:
            The updated aggregation dictionary
        """
        raise NotImplementedError("Subclasses must override _update_cumulative_totals")

    def create_agg_dict(
        self,
        current_day: arrow.Arrow,
        previous_snapshot: RecordSnapshotDocument | UsageSnapshotDocument,
        latest_delta: RecordDeltaDocument | UsageDeltaDocument,
        deltas: list,
        exhaustive_counts_cache: dict = {},
    ) -> RecordSnapshotDocument | UsageSnapshotDocument:
        """Create a dictionary representing the aggregation result for indexing.

        This method should be overridden by subclasses to provide the appropriate
        logic for creating aggregation dictionaries based on their specific data
        structures.

        Args:
            current_day: The current day for the snapshot
            previous_snapshot: The previous snapshot document to add onto
            latest_delta: The latest delta document to add
            deltas: All delta documents for top subcounts (from earliest date)
            exhaustive_counts_cache: The exhaustive counts cache
        """
        raise NotImplementedError("Subclasses must override create_agg_dict")

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing.

        Args:
            community_id: The ID of the community to aggregate.
            start_date: The start date for the aggregation.
            end_date: The end date for the aggregation.
            last_event_date: The last event date, or None if no events exist. In this
                case the events we're looking for are delta aggregations.

        Returns:
            A generator of dictionaries, where each dictionary is an aggregation
            document for a single day to be indexed.
        """
        current_iteration_date = arrow.get(start_date)

        exhaustive_counts_cache: dict[str, Any] = {}
        previous_snapshot, is_zero_placeholder = self._get_previous_snapshot(
            community_id, current_iteration_date
        )
        previous_snapshot_date = (
            arrow.get(previous_snapshot["snapshot_date"])  # type: ignore
            if previous_snapshot and not is_zero_placeholder
            else None
        )

        # Catch up missing snapshots before the start date
        if previous_snapshot_date and previous_snapshot_date < start_date.shift(
            days=-1
        ):
            current_iteration_date = previous_snapshot_date.shift(days=1)
            end_date = min(
                end_date, previous_snapshot_date.shift(days=self.catchup_interval)
            )
        elif not previous_snapshot_date:  # No previous snapshot
            if first_event_date is None:
                # No events exist, return empty generator
                return
            current_iteration_date = first_event_date
            end_date = min(
                end_date, current_iteration_date.shift(days=self.catchup_interval)
            )

        if first_event_date is None:
            # No events exist, return empty generator
            return

        all_delta_documents = self._fetch_all_delta_documents(
            community_id, first_event_date, end_date
        )

        if not all_delta_documents:
            # No delta documents exist, return empty generator
            return

        # Don't try to aggregate beyond the last delta date
        last_delta_date = arrow.get(all_delta_documents[-1]["period_start"])
        end_date = min(end_date, last_delta_date.ceil("day"))

        current_delta_index = self._get_delta_index_by_date(
            all_delta_documents, current_iteration_date
        )

        while current_iteration_date <= end_date:
            sliced_delta_documents = all_delta_documents[: current_delta_index + 1]
            try:
                latest_delta = sliced_delta_documents[-1]
                assert (
                    arrow.get(latest_delta["period_start"]).date()
                    == current_iteration_date.date()
                )
            except IndexError:
                break  # Exit the loop gracefully
            except AssertionError:
                current_app.logger.error(
                    f"Delta data gap detected. Expected document for date "
                    f"{current_iteration_date.format('YYYY-MM-DD')}, but none found."
                )
                break

            source_content = self.create_agg_dict(
                current_iteration_date,
                previous_snapshot,
                latest_delta,
                sliced_delta_documents,  # Use sliced deltas for top aggregations
                exhaustive_counts_cache,
            )

            index_name = prefix_index(
                f"{self.aggregation_index}-{current_iteration_date.year}"
            )
            document_id = (
                f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
            )

            # Check if an aggregation already exists for this date
            # If it does, delete it (we'll re-create it below)
            if self.client.exists(index=index_name, id=document_id):
                self.delete_aggregation(index_name, document_id)

            yield {
                "_id": document_id,
                "_index": index_name,
                "_source": source_content,
            }

            previous_snapshot = source_content
            previous_snapshot_date = current_iteration_date
            current_iteration_date = current_iteration_date.shift(days=1)
            current_delta_index += 1


class CommunityRecordsSnapshotAggregatorBase(CommunitySnapshotAggregatorBase):

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, subcount_configs, *args, **kwargs)
        self.record_index = prefix_index("rdmrecords-records")
        self.event_index = prefix_index("stats-community-events")
        self.delta_index = prefix_index("stats-community-records-delta-created")
        self.first_event_index = prefix_index("stats-community-records-delta-created")
        self.aggregation_index = prefix_index(
            "stats-community-records-snapshot-created"
        )
        self.event_date_field = "record_created_date"

    @property
    def use_included_dates(self):
        """Whether to use included dates for community queries."""
        return False

    @property
    def use_published_dates(self):
        """Whether to use published dates for community queries."""
        return False

    # FIXME: Deprecated. Remove this method.
    def _should_skip_aggregation(
        self,
        end_date: arrow.Arrow,
        community_id: str | None = None,
        previous_snapshot_date: arrow.Arrow | None = None,
    ) -> bool:
        """Check if aggregation should be skipped due to no relevant records.

        This method provides early skip logic for snapshot aggregators by checking if
        there are any records that were added to the community, removed from the
        community, or deleted from the repository between the last snapshot and the
        aggregation end date. If there are no relevant records, we can skip the
        expensive processing pipeline entirely.

        Args:
            end_date: The end date for aggregation
            community_id: The community ID to check (optional, for testing)
            previous_snapshot_date: The previous snapshot date, or None if no snapshot
                exists.

        Returns:
            True if aggregation should be skipped, False otherwise
        """
        if previous_snapshot_date is None:
            return False

        # Search 1: Look for events that occurred after the last snapshot
        # This catches new additions/removals from the community
        community_search = (
            Search(using=self.client, index=self.event_index)
            .filter("term", community_id=community_id)
            .filter(
                "range",
                **{
                    self.event_date_field: {
                        "gte": (
                            previous_snapshot_date.floor("day").format(
                                "YYYY-MM-DDTHH:mm:ss"
                            )
                        ),
                        "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                    }
                },
            )
        )

        community_results = community_search.count()
        if community_results > 0:
            return False  # Continue aggregation - found relevant events

        # Search 2: Look for events that were marked as deleted after the last snapshot
        # This catches records that were added before the snapshot but deleted after
        deletion_search = (
            Search(using=self.client, index=self.event_index)
            .filter("term", community_id=community_id)
            .filter("exists", field="deleted_date")
            .filter(
                "range",
                **{
                    "deleted_date": {
                        "gte": (
                            previous_snapshot_date.floor("day").format(
                                "YYYY-MM-DDTHH:mm:ss"
                            )
                        ),
                        "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                    }
                },
            )
        )

        deletion_results = deletion_search.count()
        if deletion_results > 0:
            return False  # Continue aggregation - found deletion events

        return True

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> RecordSnapshotDocument:
        """Create a zero-value snapshot document for when no events exist.

        Args:
            community_id: The community ID
            current_day: The current day for the snapshot

        Returns:
            A snapshot document with zero values
        """
        # Dynamically build subcounts based on subcount_configs
        subcounts: dict[
            str, list[RecordSnapshotSubcountItem] | RecordSnapshotTopSubcounts
        ] = {}
        for config in self.subcount_configs.values():
            if "records" in config and "delta_aggregation_name" in config["records"]:
                delta_name = config["records"]["delta_aggregation_name"]
                snapshot_type = config["records"].get("snapshot_type", "all")

                # Remove "by_" prefix and add appropriate prefix based on snapshot_type
                subcount_base = delta_name[3:]  # Remove "by_" prefix
                if snapshot_type == "top":
                    subcount_name = f"top_{subcount_base}"
                else:
                    subcount_name = f"all_{subcount_base}"

                subcounts[subcount_name] = []

        return {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "snapshot_date": current_day.format("YYYY-MM-DD"),
            "total_records": {
                "metadata_only": 0,
                "with_files": 0,
            },
            "total_parents": {
                "metadata_only": 0,
                "with_files": 0,
            },
            "total_files": {
                "file_count": 0,
                "data_volume": 0,
            },
            "total_uploaders": 0,
            "subcounts": subcounts,
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    def _update_top_subcounts(  # type: ignore[override]
        self,
        new_dict: RecordSnapshotDocument,
        deltas: list,
        exhaustive_counts_cache: dict,
        latest_delta: RecordDeltaDocument,
    ) -> None:
        """Update top subcounts.

        These are the subcounts that only include the top N values for each field
        (where N is configured by COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).
        (E.g. top_subjects, top_publishers, etc.) We can't just add the new deltas
        to the current subcounts because the top N values for each field may have
        changed. We avoid performing a full recalculation from all delta documents
        for every delta document by using an exhaustive counts cache. This builds
        a cumulative set of subcount totals that includes *all* existing items that
        have been seen for each subcount since the first delta document. This way
        we can simply update the cache with the latest delta document and then select
        the top N items from the cache for each subcount.

        Args:
            new_dict: The aggregation dictionary to modify
            deltas: The daily delta dictionaries to update the subcounts with.
                These are the daily delta records for the community between
                the first delta document and the current date.
            exhaustive_counts_cache: The exhaustive counts cache
            latest_delta: The latest delta document

        Returns:
            The updated aggregation dictionary with the new top subcounts.
        """
        top_configs = [
            config.get("records", {})
            for config in self.subcount_configs.values()
            if config.get("records", {}).get("snapshot_type") == "top"
        ]

        for config in top_configs:
            # Use the mapped field name since delta documents have been processed
            # by _map_delta_to_snapshot_subcounts
            subcount_base = config["delta_aggregation_name"][3:]
            top_subcount_name = f"top_{subcount_base}"
            category_name = top_subcount_name

            if category_name not in exhaustive_counts_cache:
                exhaustive_counts_cache[category_name] = self._build_exhaustive_cache(
                    deltas, category_name
                )
            else:
                self._update_exhaustive_cache(
                    category_name, latest_delta, exhaustive_counts_cache
                )

            new_dict["subcounts"][top_subcount_name] = self._select_top_n_from_cache(
                exhaustive_counts_cache[category_name]
            )

    def _add_delta_to_subcounts(
        self,
        previous_subcounts: (
            list[RecordSnapshotSubcountItem] | RecordSnapshotTopSubcounts
        ),
        latest_delta: RecordDeltaDocument,
        category_name: str,
    ) -> list:
        """Add latest delta subcounts onto previous snapshot subcounts.

        Args:
            previous_subcounts: Previous snapshot's subcounts for this category
            latest_delta: Latest delta document
            category_name: Name of the subcount category

        Returns:
            Updated subcounts with latest delta added
        """

        def calculate_net_value(delta_item, category, field):
            """Calculate net value (added - removed) for a field."""
            return (
                delta_item[category]["added"][field]
                - delta_item[category]["removed"][field]
            )

        def update_or_create_item(item_id, delta_item, previous_dict):
            """Update existing item or create new one with net values."""
            if item_id in previous_dict:
                prev_item = previous_dict[item_id]
                for category in ["records", "parents", "files"]:
                    if category == "files":
                        for field in ["file_count", "data_volume"]:
                            prev_item[category][field] += calculate_net_value(
                                delta_item, category, field
                            )
                    else:
                        for field in ["metadata_only", "with_files"]:
                            prev_item[category][field] += calculate_net_value(
                                delta_item, category, field
                            )
            else:
                previous_dict[item_id] = {
                    "id": item_id,
                    "label": delta_item.get("label", ""),
                    "records": {
                        "metadata_only": calculate_net_value(
                            delta_item, "records", "metadata_only"
                        ),
                        "with_files": calculate_net_value(
                            delta_item, "records", "with_files"
                        ),
                    },
                    "parents": {
                        "metadata_only": calculate_net_value(
                            delta_item, "parents", "metadata_only"
                        ),
                        "with_files": calculate_net_value(
                            delta_item, "parents", "with_files"
                        ),
                    },
                    "files": {
                        "file_count": calculate_net_value(
                            delta_item, "files", "file_count"
                        ),
                        "data_volume": calculate_net_value(
                            delta_item, "files", "data_volume"
                        ),
                    },
                }

        previous_dict = {}
        for item in previous_subcounts:
            previous_dict[item["id"]] = item.copy()  # type: ignore

        if "subcounts" in latest_delta and category_name in latest_delta["subcounts"]:
            for delta_item in latest_delta["subcounts"][category_name]:
                update_or_create_item(delta_item["id"], delta_item, previous_dict)

        return list(previous_dict.values())

    def _update_cumulative_totals(  # type: ignore[override]
        self, new_dict: RecordSnapshotDocument, delta_doc: RecordDeltaDocument
    ) -> RecordSnapshotDocument:
        """Update cumulative totals with values from a daily delta document."""
        new_dict["total_records"]["metadata_only"] = max(
            0,
            (
                new_dict.get("total_records", {}).get("metadata_only", 0)
                + delta_doc.get("records", {}).get("added", {}).get("metadata_only", 0)
                - delta_doc.get("records", {})
                .get("removed", {})
                .get("metadata_only", 0)
            ),
        )
        new_dict["total_records"]["with_files"] = max(
            0,
            (
                new_dict.get("total_records", {}).get("with_files", 0)
                + delta_doc.get("records", {}).get("added", {}).get("with_files", 0)
                - delta_doc.get("records", {}).get("removed", {}).get("with_files", 0)
            ),
        )

        new_dict["total_parents"]["metadata_only"] = max(
            0,
            (
                new_dict.get("total_parents", {}).get("metadata_only", 0)
                + delta_doc.get("parents", {}).get("added", {}).get("metadata_only", 0)
                - delta_doc.get("parents", {})
                .get("removed", {})
                .get("metadata_only", 0)
            ),
        )
        new_dict["total_parents"]["with_files"] = max(
            0,
            (
                new_dict.get("total_parents", {}).get("with_files", 0)
                + delta_doc.get("parents", {}).get("added", {}).get("with_files", 0)
                - delta_doc.get("parents", {}).get("removed", {}).get("with_files", 0)
            ),
        )

        new_dict["total_files"]["file_count"] = max(
            0,
            (
                new_dict.get("total_files", {}).get("file_count", 0)
                + delta_doc.get("files", {}).get("added", {}).get("file_count", 0)
                - delta_doc.get("files", {}).get("removed", {}).get("file_count", 0)
            ),
        )
        new_dict["total_files"]["data_volume"] = max(
            0.0,
            (
                new_dict.get("total_files", {}).get("data_volume", 0.0)
                + delta_doc.get("files", {}).get("added", {}).get("data_volume", 0.0)
                - delta_doc.get("files", {}).get("removed", {}).get("data_volume", 0.0)
            ),
        )

        # Update "all" subcounts by adding latest delta onto previous snapshot
        for config in [
            subcount_config["records"]
            for subcount_config in self.subcount_configs.values()
            if subcount_config["records"]
        ]:
            if config["snapshot_type"] == "all":
                snap_subcount_base = config["delta_aggregation_name"][3:]
                snap_subcount_name = f"{config['snapshot_type']}_{snap_subcount_base}"

                previous_subcounts = new_dict.get("subcounts", {}).get(
                    snap_subcount_name, []
                )

                # Use the mapped field name since delta_doc has been processed
                # by _map_delta_to_snapshot_subcounts
                new_dict["subcounts"][snap_subcount_name] = (
                    self._add_delta_to_subcounts(
                        previous_subcounts,
                        delta_doc,
                        snap_subcount_name,
                    )
                )

        return new_dict

    def create_agg_dict(  # type: ignore[override]
        self,
        current_day: arrow.Arrow,
        previous_snapshot: RecordSnapshotDocument,
        latest_delta: RecordDeltaDocument,
        deltas: list,
        exhaustive_counts_cache: dict = {},
    ) -> RecordSnapshotDocument:
        """Create a dictionary representing the aggregation result for indexing.

        Args:
            current_day: The current day for the snapshot
            previous_snapshot: The previous snapshot document to add onto
            latest_delta: The latest delta document to add
            deltas: All delta documents for top subcounts (from earliest date)
            exhaustive_counts_cache: The exhaustive counts cache
        """
        new_dict: RecordSnapshotDocument = self._copy_snapshot_forward(
            previous_snapshot, current_day  # type: ignore
        )
        records = latest_delta.get("records", {})
        if (
            records.get("added", {}).get("with_files", 0) == 0
            and records.get("removed", {}).get("with_files", 0) == 0
            and records.get("added", {}).get("metadata_only", 0) == 0
            and records.get("removed", {}).get("metadata_only", 0) == 0
        ):
            return new_dict

        new_dict = self._update_cumulative_totals(new_dict, latest_delta)

        # Add top aggregations based on cumulative delta documents
        self._update_top_subcounts(
            new_dict, deltas, exhaustive_counts_cache, latest_delta
        )

        return new_dict

    def _map_delta_to_snapshot_subcounts(self, delta_doc: dict) -> dict:
        """Map delta document subcount field names to snapshot field names.

        This transforms the delta aggregation field names (e.g., 'by_resource_types')
        to the snapshot field names (e.g., 'all_resource_types', 'top_resource_types')
        for consistent processing throughout the aggregator.

        Args:
            delta_doc: The delta document with subcounts to remap (mutated in place)

        Returns:
            The same delta document with remapped subcount field names
        """
        mapped_subcounts = {}

        for delta_field, delta_items in delta_doc.get("subcounts", {}).items():
            for config in self.subcount_configs.values():
                records_config = config.get("records", {})
                if not records_config:
                    continue

                if records_config.get("delta_aggregation_name") == delta_field:
                    # Use snapshot_type to determine the field name
                    snapshot_type = records_config.get("snapshot_type", "all")
                    subcount_base = delta_field[3:]  # Remove "by_" prefix
                    snapshot_field = f"{snapshot_type}_{subcount_base}"
                    mapped_subcounts[snapshot_field] = delta_items
                    break

        delta_doc["subcounts"] = mapped_subcounts
        return delta_doc

    def _accumulate_category_in_place(
        self, accumulated: dict, category_items: list
    ) -> None:
        """Accumulate category items into the existing accumulated dictionary.

        Args:
            accumulated: Dictionary to accumulate into
            category_items: List of items from a category in a delta document
        """
        for item in category_items:
            item_id = item["id"]

            if item_id not in accumulated:
                accumulated[item_id] = {
                    "id": item_id,
                    "records": {"metadata_only": 0, "with_files": 0},
                    "parents": {"metadata_only": 0, "with_files": 0},
                    "files": {"file_count": 0, "data_volume": 0.0},
                    "label": item.get("label", ""),
                    "total_records": 0,  # Pre-calculated for efficient sorting
                }
            # Accumulate net totals (added - removed)
            for field in ["records", "parents"]:
                for subfield in ["metadata_only", "with_files"]:
                    added_val = item[field]["added"][subfield]
                    removed_val = item[field]["removed"][subfield]
                    old_val = accumulated[item_id][field][subfield]
                    new_val = old_val + (added_val - removed_val)
                    accumulated[item_id][field][subfield] = new_val

            for subfield in ["file_count", "data_volume"]:
                added_val = item["files"]["added"][subfield]
                removed_val = item["files"]["removed"][subfield]
                old_val = accumulated[item_id]["files"][subfield]
                new_val = old_val + (added_val - removed_val)
                accumulated[item_id]["files"][subfield] = new_val

            # Update the pre-calculated total for efficient sorting
            accumulated[item_id]["total_records"] = (
                accumulated[item_id]["records"]["metadata_only"]
                + accumulated[item_id]["records"]["with_files"]
            )

    def _select_top_n_from_cache(self, exhaustive_cache: dict) -> list:
        """Select top N items from the exhaustive cache.

        Args:
            exhaustive_cache: Dictionary mapping item IDs to their cumulative totals

        Returns:
            List of top N subcount items
        """
        # Filter out items with zero or negative totals
        filtered_items = [
            (item_id, totals)
            for item_id, totals in exhaustive_cache.items()
            if totals["total_records"] > 0
        ]

        sorted_items = sorted(
            filtered_items,
            key=lambda x: x[1]["total_records"],
            reverse=True,
        )

        top_subcount_list = [
            {k: v for k, v in totals.items() if k != "total_records"}
            for _, totals in sorted_items[: self.top_subcount_limit]
        ]

        return top_subcount_list


class CommunityRecordsSnapshotCreatedAggregator(CommunityRecordsSnapshotAggregatorBase):
    """Snapshot aggregator for community records using created dates.

    This class uses the record creation date as the basis for community addition timing.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index(
            "stats-community-records-snapshot-created"
        )
        self.event_index = prefix_index("stats-community-records-delta-created")
        self.event_date_field = "period_start"
        self.event_community_query_term = lambda community_id: Q(
            "term", community_id=community_id
        )
        self.first_event_index = prefix_index("stats-community-records-delta-created")
        self.first_event_date_field = "period_start"


class CommunityRecordsSnapshotAddedAggregator(CommunityRecordsSnapshotAggregatorBase):
    """Snapshot aggregator for community records using added dates.

    This class uses the date when records were added to the community as the basis for
    community addition timing.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-snapshot-added")
        self.event_index = prefix_index("stats-community-events")
        self.delta_index = prefix_index("stats-community-records-delta-added")
        self.event_date_field = "event_date"
        self.first_event_index = prefix_index("stats-community-records-delta-added")
        self.first_event_date_field = "period_start"

    @property
    def use_included_dates(self):
        """Whether to use included dates for community queries."""
        return True


class CommunityRecordsSnapshotPublishedAggregator(
    CommunityRecordsSnapshotAggregatorBase
):
    """Snapshot aggregator for community records using published dates.

    This class uses the record publication date as the basis for community
    addition timing.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index(
            "stats-community-records-snapshot-published"
        )
        self.event_index = prefix_index("stats-community-events")
        self.delta_index = prefix_index("stats-community-records-delta-published")
        self.event_date_field = "record_published_date"
        self.first_event_index = prefix_index("stats-community-records-delta-published")
        self.first_event_date_field = "period_start"

    @property
    def use_published_dates(self):
        """Whether to use published dates for community queries."""
        return True


class CommunityUsageSnapshotAggregator(CommunitySnapshotAggregatorBase):
    """Aggregator for creating cumulative usage snapshots from daily delta documents."""

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, subcount_configs, *args, **kwargs)
        self.event_index = prefix_index("stats-community-usage-delta")
        self.delta_index = prefix_index("stats-community-usage-delta")
        self.first_event_index = prefix_index("stats-community-usage-delta")
        self.aggregation_index = prefix_index("stats-community-usage-snapshot")
        self.event_date_field = "period_start"
        self.query_builder = CommunityUsageSnapshotQuery(client=self.client)

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> UsageSnapshotDocument:
        """Create a zero-value usage snapshot document for when no events exist.

        Args:
            community_id: The community ID
            current_day: The current day for the snapshot

        Returns:
            A usage snapshot document with zero values
        """
        return {
            "community_id": community_id,
            "snapshot_date": current_day.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "totals": {
                "view": {
                    "total_events": 0,
                    "unique_visitors": 0,
                    "unique_records": 0,
                    "unique_parents": 0,
                },
                "download": {
                    "total_events": 0,
                    "unique_visitors": 0,
                    "unique_records": 0,
                    "unique_parents": 0,
                    "unique_files": 0,
                    "total_volume": 0,
                },
            },
            "subcounts": self._initialize_subcounts_structure(),
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    def create_agg_dict(  # type: ignore[override]
        self,
        current_day: arrow.Arrow,
        previous_snapshot: UsageSnapshotDocument,
        latest_delta: UsageDeltaDocument,
        deltas: list,
        exhaustive_counts_cache: dict = {},
    ) -> UsageSnapshotDocument:
        """Create the final aggregation document from cumulative totals.

        Args:
            current_day: The current day for the snapshot
            previous_snapshot: The previous snapshot document
            latest_delta: The latest delta document
            deltas: All delta documents for top subcounts
            exhaustive_counts_cache: The exhaustive counts cache
        """
        new_dict: UsageSnapshotDocument = self._copy_snapshot_forward(
            previous_snapshot, current_day
        )  # type: ignore

        totals = latest_delta.get("totals", {})
        if (
            totals.get("view", {}).get("total_events", 0) == 0
            and totals.get("download", {}).get("total_events", 0) == 0
        ):
            return new_dict

        self._update_cumulative_totals(new_dict, latest_delta)

        # Add top aggregations based on cumulative delta documents
        self._update_top_subcounts(
            new_dict, deltas, exhaustive_counts_cache, latest_delta
        )

        return new_dict

    def _check_usage_delta_dependency(
        self, community_id: str, start_date: arrow.Arrow, end_date: arrow.Arrow
    ) -> bool:
        """Check if usage delta aggregator has caught up to the snapshot aggregator.

        This method checks if the usage delta aggregator has processed data up to
        the end_date that the snapshot aggregator is trying to process. If the
        delta aggregator hasn't caught up, the snapshot aggregator should skip
        this run to avoid creating incomplete snapshots.

        Args:
            community_id: The community ID
            start_date: The start date for snapshot aggregation
            end_date: The end date for snapshot aggregation

        Returns:
            True if delta aggregator has caught up, False if it hasn't
        """

        # Get the usage delta aggregator's bookmark
        delta_bookmark_api = CommunityBookmarkAPI(
            current_search_client, "community-usage-delta-agg", "day"
        )
        delta_bookmark = delta_bookmark_api.get_bookmark(community_id)

        if not delta_bookmark:
            # If no bookmark exists, check if there are any delta records at all
            search = self.query_builder.build_dependency_check_query(community_id)
            result = search.execute()

            if not result.aggregations.max_date.value:
                # No delta records exist at all, skip
                return False

            # Use the latest delta record date as the bookmark
            delta_bookmark_date = arrow.get(
                result.aggregations.max_date.value_as_string
            )
        else:
            delta_bookmark_date = arrow.get(delta_bookmark)

        # Check if delta aggregator has processed data for the period we want
        # to snapshot
        # The snapshot can run for any day where delta data exists
        if delta_bookmark_date.date() < start_date.date():
            current_app.logger.error(
                f"Usage delta aggregator for {community_id} has not processed "
                f"data for the requested period. Delta bookmark: "
                f"{delta_bookmark_date.date()}, Snapshot start_date: "
                f"{start_date.date()}. Skipping snapshot aggregation."
            )
            return False

        return True

    def _map_delta_to_snapshot_subcounts(  # type: ignore[override]
        self, delta_doc: UsageDeltaDocument
    ) -> UsageDeltaDocument:
        """Map delta document subcount field names to snapshot field names.

        This transforms the enriched aggregation field names (e.g., 'by_resource_types')
        to the snapshot field names (e.g., 'all_resource_types') for consistent
        processing throughout the aggregator.
        """
        mapped_subcounts = {}

        for delta_field, delta_items in delta_doc.get("subcounts", {}).items():
            # Find the config that matches this delta field
            for subcount_name, config in self.subcount_configs.items():
                usage_config = config.get("usage_events", {})
                if not usage_config:
                    continue

                if usage_config.get("delta_aggregation_name") == delta_field:
                    # Use snapshot_type to determine the field name
                    snapshot_type = usage_config.get("snapshot_type", "all")
                    delta_aggregation_name = usage_config.get("delta_aggregation_name")
                    subcount_base = delta_aggregation_name[3:]  # Remove "by_" prefix
                    snapshot_field = f"{snapshot_type}_{subcount_base}"
                    mapped_subcounts[snapshot_field] = delta_items
                    break

        delta_doc["subcounts"] = mapped_subcounts
        return delta_doc

    def _accumulate_category_in_place(
        self, accumulated: dict, category_items: list
    ) -> None:
        """Accumulate category items into the existing accumulated dictionary.

        Args:
            accumulated: Dictionary to accumulate into
            category_items: List of items from a category in a delta document
        """
        for item in category_items:
            item_id = item["id"]

            if item_id not in accumulated:
                accumulated[item_id] = {
                    "id": item_id,
                    "label": item.get("label", ""),
                    "view": {
                        "total_events": 0,
                        "unique_visitors": 0,
                        "unique_records": 0,
                        "unique_parents": 0,
                    },
                    "download": {
                        "total_events": 0,
                        "unique_visitors": 0,
                        "unique_records": 0,
                        "unique_parents": 0,
                        "unique_files": 0,
                        "total_volume": 0.0,
                    },
                }

            for angle in ["view", "download"]:
                for metric, value in item.get(angle, {}).items():
                    accumulated[item_id][angle][metric] += value

    def _select_top_n_from_cache(self, exhaustive_cache: dict, angle: str) -> list:
        """Select top N items from the exhaustive cache.

        Args:
            exhaustive_cache: Dictionary mapping item IDs to their cumulative totals
            angle: The angle to select top N items from (e.g. "view" or "download")
        """
        filtered_items = [
            (item_id, totals)
            for item_id, totals in exhaustive_cache.items()
            if totals[angle]["total_events"] > 0
        ]

        sorted_items = sorted(
            filtered_items,
            key=lambda x: x[1][angle]["total_events"],
            reverse=True,
        )

        top_subcount_list = [
            totals for _, totals in sorted_items[: self.top_subcount_limit]
        ]

        return top_subcount_list

    def _update_cumulative_totals(  # type: ignore[override]
        self,
        new_dict: UsageSnapshotDocument,
        delta_doc: UsageDeltaDocument,
    ) -> UsageSnapshotDocument:
        """Update cumulative totals with values from enriched daily delta documents."""

        def add_numeric_values(target: dict, source: dict) -> None:
            """Add numeric values from source to target dictionary."""
            for key, value in source.items():
                if (
                    isinstance(value, numbers.Number)
                    and key in target
                    and isinstance(target[key], numbers.Number)
                ):
                    target[key] += value
                elif (
                    isinstance(value, dict)
                    and key in target
                    and isinstance(target[key], dict)
                ):
                    add_numeric_values(target[key], value)

        def update_totals(
            new_dict: UsageSnapshotDocument, delta_doc: UsageDeltaDocument, key: str
        ) -> None:
            """Update cumulative totals with values from a daily delta document."""
            for k, value in delta_doc[key].items():  # type: ignore[literal-required]
                # Skip keys that start with "top_" in subcounts
                if k.startswith("top_"):
                    continue

                if k in new_dict[key]:  # type: ignore[literal-required]
                    if isinstance(value, dict):
                        update_totals(new_dict[key], delta_doc[key], k)  # type: ignore[literal-required] # noqa: E501
                    elif isinstance(value, list):
                        for item in value:
                            matching_item = next(
                                (
                                    existing_item
                                    for existing_item in new_dict[key][k]  # type: ignore[literal-required] # noqa: E501
                                    if existing_item["id"] == item["id"]
                                ),
                                None,
                            )
                            if matching_item:
                                add_numeric_values(matching_item, item)
                            else:
                                new_dict[key][k].append(item)  # type: ignore[literal-required] # noqa: E501
                    else:
                        # Sum all numeric values since these are daily deltas
                        if isinstance(new_dict[key][k], numbers.Number):  # type: ignore[literal-required] # noqa: E501
                            new_dict[key][k] += value  # type: ignore[literal-required]
                        else:
                            # Keep strings as is (id and string label)
                            new_dict[key][k] = value  # type: ignore[literal-required]
                else:
                    new_dict[key][k] = value  # type: ignore[literal-required] # noqa: E501

        update_totals(new_dict, delta_doc, "totals")

        # Update simple subcounts from mapped delta document
        # The mapping has already transformed field names to snapshot format
        update_totals(new_dict, delta_doc, "subcounts")

        return new_dict

    def _update_top_subcounts(  # type: ignore[override]
        self,
        new_dict: UsageSnapshotDocument,
        deltas: list,
        exhaustive_counts_cache: dict,
        latest_delta: UsageDeltaDocument,
    ) -> None:
        """Update top subcounts.

        These are the subcounts that only include the top N values for each field
        (where N is configured by COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).
        (E.g. top_subjects, top_publishers, etc.) We can't just add the new deltas
        to the current subcounts because the top N values for each field may have
        changed. We avoid performing a full recalculation from all delta documents
        for every delta document by using an exhaustive counts cache. This builds
        a cumulative set of subcount totals that includes *all* existing items that
        have been seen for each subcount since the first delta document. This way
        we can simply update the cache with the latest delta document and then select
        the top N items from the cache for each subcount.

        Args:
            new_dict: The aggregation dictionary to modify
            deltas: The daily delta dictionaries to update the subcounts with.
                These are the daily delta records for the community between
                the first delta document and the current date.
            exhaustive_counts_cache: The exhaustive counts cache
            latest_delta: The latest delta document

        Returns:
            The updated aggregation dictionary with the new top subcounts.
        """
        top_configs = [
            config.get("usage_events", {})
            for config in self.subcount_configs.values()
            if config.get("usage_events", {}).get("snapshot_type") == "top"
        ]

        for config in top_configs:
            # Use the mapped field name since delta documents have been processed
            # by _map_delta_to_snapshot_subcounts
            subcount_base = config["delta_aggregation_name"][3:]
            top_subcount_name = f"top_{subcount_base}"

            if top_subcount_name not in exhaustive_counts_cache:
                # First time: build exhaustive cache from all delta documents
                exhaustive_counts_cache[top_subcount_name] = (
                    self._build_exhaustive_cache(deltas, top_subcount_name)
                )
            else:
                # Update existing cache with only the latest delta document
                self._update_exhaustive_cache(
                    top_subcount_name, latest_delta, exhaustive_counts_cache
                )

            top_by_view = self._select_top_n_from_cache(
                exhaustive_counts_cache[top_subcount_name], "view"
            )
            top_by_download = self._select_top_n_from_cache(
                exhaustive_counts_cache[top_subcount_name], "download"
            )
            new_dict["subcounts"][top_subcount_name] = {  # type: ignore
                "by_view": top_by_view,
                "by_download": top_by_download,
            }

    def _initialize_subcounts_structure(
        self,
    ) -> dict[str, list[UsageSubcountItem] | UsageSnapshotTopCategories]:
        """Initialize the subcounts structure based on configuration."""
        subcounts: dict[str, list[UsageSubcountItem] | UsageSnapshotTopCategories] = {}
        for config in self.subcount_configs.values():
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            snapshot_type = usage_config.get("snapshot_type", "all")
            delta_aggregation_name = usage_config.get("delta_aggregation_name")
            if not delta_aggregation_name:
                continue
            subcount_base = delta_aggregation_name[3:]  # Remove "by_" prefix
            snapshot_field = f"{snapshot_type}_{subcount_base}"

            if snapshot_type == "all":
                subcounts[snapshot_field] = []
            elif snapshot_type == "top":
                subcounts[snapshot_field] = {"by_view": [], "by_download": []}
        return subcounts


class CommunityUsageDeltaAggregator(CommunityAggregatorBase):

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # Use provided configs or fall back to class default
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
        )
        self.event_index: list[tuple[str, str]] = [
            ("view", prefix_index("events-stats-record-view")),
            ("download", prefix_index("events-stats-file-download")),
        ]
        self.first_event_index = prefix_index("events-stats-record-view")
        self.first_event_date_field = "timestamp"
        self.aggregation_index = prefix_index("stats-community-usage-delta")
        self.event_date_field = "timestamp"
        self.event_community_query_term = lambda community_id: Q("match_all")
        self.query_builder = CommunityUsageDeltaQuery(client=self.client)

    def _should_skip_aggregation(
        self,
        start_date: arrow.Arrow,
        last_event_date: arrow.Arrow | None,
        community_id: str | None = None,
    ) -> bool:
        """Check if aggregation should be skipped due to no usage events in date range.

        This method provides early skip logic for the usage delta aggregator by:
        1. Checking if there are any usage events in the date range for this community
        2. If no events exist, we can skip the expensive processing pipeline entirely

        Args:
            start_date: The start date for aggregation
            last_event_date: The last event date, or None if no events exist
            community_id: The community ID to check (optional, for testing)

        Returns:
            True if aggregation should be skipped, False otherwise
        """
        if last_event_date is None:
            return True
        if last_event_date < start_date:
            return True

        # For usage delta aggregator, we need to check if there are any actual
        # usage events in the date range for this community
        # This is much faster than the full processing pipeline
        events_found = False
        for event_type, event_index in self.event_index:
            # Quick check for any events in the date range
            search = Search(using=self.client, index=event_index)
            search = search.filter(
                "range",
                timestamp={
                    "gte": start_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lte": start_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )

            # If community_id is not "global", we need to check if any of these events
            # belong to records that are in the community on this date
            if community_id != "global":
                # Use the new community_ids field directly from the enriched events
                search = search.filter("term", community_ids=community_id)
            else:
                # For global aggregator, just check if there are any events at all
                pass

            if search.count() > 0:
                events_found = True
                break

        return not events_found

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> UsageDeltaDocument:
        """Create a zero-value usage delta document for when no events exist.

        Args:
            community_id: The community ID
            current_day: The current day for the delta

        Returns:
            A usage delta document with zero values
        """
        return {
            "community_id": community_id,
            "period_start": current_day.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": current_day.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "totals": {
                "view": {
                    "total_events": 0,
                    "unique_visitors": 0,
                    "unique_records": 0,
                    "unique_parents": 0,
                },
                "download": {
                    "total_events": 0,
                    "unique_visitors": 0,
                    "unique_records": 0,
                    "unique_parents": 0,
                    "unique_files": 0,
                    "total_volume": 0,
                },
            },
            "subcounts": {
                config.get("usage_events", {}).get(
                    "delta_aggregation_name", subcount_name
                ): []
                for subcount_name, config in self.subcount_configs.items()
                if config.get("usage_events", {}).get("delta_aggregation_name")
            },
        }

    def _get_view_metrics_dict(self) -> dict:
        """Get the metrics dictionary for view events.

        Returns:
            Dictionary of metrics for view events
        """
        return {
            "unique_visitors": {"cardinality": {"field": "visitor_id"}},
            "unique_records": {"cardinality": {"field": "record_id"}},
            "unique_parents": {"cardinality": {"field": "parent_id"}},
        }

    def _get_download_metrics_dict(self) -> dict:
        """Get the metrics dictionary for download events.

        Returns:
            Dictionary of metrics for download events
        """
        return {
            "unique_visitors": {"cardinality": {"field": "visitor_id"}},
            "unique_records": {"cardinality": {"field": "record_id"}},
            "unique_parents": {"cardinality": {"field": "parent_id"}},
            "unique_files": {"cardinality": {"field": "file_id"}},
            "total_volume": {"sum": {"field": "file_size"}},
        }

    def build_dynamic_view_aggregations(self) -> dict:
        """Build view aggregations dynamically based on SUBCOUNT_CONFIGS.

        Returns:
            Dictionary of aggregations for view events
        """
        aggregations = {}

        for subcount_name, config in self.subcount_configs.items():
            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            field = usage_config.get("field")
            if not field:
                continue  # Skip subcounts that don't have fields

            # Build the base aggregation
            agg_config = {
                "terms": {"field": field, "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            }

            # Add label aggregation if label_field is specified
            label_field = usage_config.get("label_field")
            if label_field:
                label_source_includes = usage_config.get(
                    "label_source_includes", [field]
                )
                agg_config["aggs"]["label"] = {
                    "top_hits": {
                        "size": 1,
                        "_source": {"includes": label_source_includes},
                    }
                }

            aggregations[subcount_name] = agg_config

        return aggregations

    def build_dynamic_download_aggregations(self) -> dict:
        """Build download aggregations dynamically based on SUBCOUNT_CONFIGS.

        Returns:
            Dictionary of aggregations for download events
        """
        aggregations = {}

        for subcount_name, config in self.subcount_configs.items():
            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            field = usage_config.get("field")
            if not field:
                continue  # Skip subcounts that don't have download fields

            # Build the base aggregation
            agg_config = {
                "terms": {"field": field, "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            }

            # Add label aggregation if label_field is specified
            label_field = usage_config.get("label_field")
            if label_field:
                label_source_includes = usage_config.get(
                    "label_source_includes", [field]
                )
                agg_config["aggs"]["label"] = {
                    "top_hits": {
                        "size": 1,
                        "_source": {"includes": label_source_includes},
                    }
                }

            aggregations[subcount_name] = agg_config

        return aggregations

    def build_combined_aggregations(self) -> dict:
        """Build combined aggregations for subcounts that need both ID and name.

        Returns:
            Dictionary of combined aggregations
        """
        combined_aggs = {}

        for subcount_name, config in self.subcount_configs.items():
            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Check if this subcount has combine_queries configuration
            combine_queries = usage_config.get("combine_queries")
            if not combine_queries or len(combine_queries) <= 1:
                continue

            # Build aggregations for each combined query field
            for query_field in combine_queries:
                subfield = query_field.split(".")[-1]
                query_name = f"{usage_config['delta_aggregation_name']}_{subfield}"

                label_source_includes = usage_config.get("label_source_includes", [])
                if subfield not in label_source_includes:
                    label_source_includes.append(subfield)

                combined_aggs[query_name] = {
                    "terms": {"field": query_field, "size": 1000},
                    "aggs": {
                        **self._get_view_metrics_dict(),
                        "label": {
                            "top_hits": {
                                "size": 1,
                                "_source": {"includes": label_source_includes},
                            }
                        },
                    },
                }

        return combined_aggs

    def build_all_aggregations(self) -> dict:
        """Build all aggregations dynamically based on SUBCOUNT_CONFIGS.

        Returns:
            Dictionary containing all aggregations for both view and download events
        """
        all_aggs = {}

        # Add view aggregations
        all_aggs.update(self.build_dynamic_view_aggregations())

        # Add download aggregations
        all_aggs.update(self.build_dynamic_download_aggregations())

        # Add combined aggregations
        all_aggs.update(self.build_combined_aggregations())

        return all_aggs

    def create_agg_dict(
        self, view_results, download_results, community_id: str, date: arrow.Arrow
    ) -> UsageDeltaDocument:
        """Combine results from separate view and download queries.

        Args:
            view_results: Results from view query (or None).
            download_results: Results from download query (or None).
            community_id (str): The community ID.
            date (arrow.Arrow): The date for the aggregation.

        Returns:
            UsageDeltaDocument: Combined aggregation document.
        """
        combined_results: UsageDeltaDocument = {
            "community_id": community_id,
            "period_start": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "totals": {
                "view": {
                    "total_events": 0,
                    "unique_visitors": 0,
                    "unique_records": 0,
                    "unique_parents": 0,
                },
                "download": {
                    "total_events": 0,
                    "unique_visitors": 0,
                    "unique_records": 0,
                    "unique_parents": 0,
                    "unique_files": 0,
                    "total_volume": 0,
                },
            },
            "subcounts": {},
        }

        # Process view results
        if view_results and hasattr(view_results.aggregations, "unique_visitors"):
            # The new query structure has metrics at the top level
            combined_results["totals"]["view"] = {
                "total_events": (
                    view_results.hits.total.value
                    if hasattr(view_results.hits, "total")
                    else 0
                ),
                "unique_visitors": view_results.aggregations.unique_visitors.value,
                "unique_records": view_results.aggregations.unique_records.value,
                "unique_parents": view_results.aggregations.unique_parents.value,
            }

        # Process download results
        if download_results and hasattr(
            download_results.aggregations, "unique_visitors"
        ):
            # The new query structure has metrics at the top level
            combined_results["totals"]["download"] = {
                "total_events": (
                    download_results.hits.total.value
                    if hasattr(download_results.hits, "total")
                    else 0
                ),
                "unique_visitors": download_results.aggregations.unique_visitors.value,
                "unique_records": download_results.aggregations.unique_records.value,
                "unique_parents": download_results.aggregations.unique_parents.value,
                "unique_files": download_results.aggregations.unique_files.value,
                "total_volume": download_results.aggregations.total_volume.value,
            }

        # Process subcounts for each category
        for subcount_name, config in self.subcount_configs.items():
            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Use the delta_aggregation_name as the key in the results
            delta_aggregation_name = usage_config.get("delta_aggregation_name")
            if not delta_aggregation_name:
                continue

            combined_results["subcounts"][delta_aggregation_name] = []

            # Handle combined aggregations (funders and affiliations)
            if (
                usage_config.get("combine_queries")
                and len(usage_config["combine_queries"]) > 1
            ):
                combined_results["subcounts"][delta_aggregation_name] = (
                    self._combine_split_aggregations(
                        view_results, download_results, usage_config, subcount_name
                    )
                )
                continue

            # Get view buckets for this subcount
            view_buckets = []
            if (
                view_results
                and delta_aggregation_name
                and hasattr(view_results.aggregations, delta_aggregation_name)
            ):
                view_agg = getattr(view_results.aggregations, delta_aggregation_name)
                view_buckets = view_agg.buckets

            # Get download buckets for this subcount
            download_buckets = []
            if (
                download_results
                and delta_aggregation_name
                and hasattr(download_results.aggregations, delta_aggregation_name)
            ):
                download_agg = getattr(
                    download_results.aggregations, delta_aggregation_name
                )
                download_buckets = download_agg.buckets

            # Combine buckets by key
            all_keys = set()
            for bucket in view_buckets:
                all_keys.add(bucket.key)
            for bucket in download_buckets:
                all_keys.add(bucket.key)

            for key in all_keys:
                view_bucket = None
                for bucket in view_buckets:
                    if bucket.key == key:
                        view_bucket = bucket
                        break

                download_bucket = None
                for bucket in download_buckets:
                    if bucket.key == key:
                        download_bucket = bucket
                        break

                # Extract label from title aggregation or use key as default
                label: str | dict[str, str] = str(key)
                label_field = usage_config.get("label_field")

                if label_field and view_bucket:
                    if hasattr(view_bucket, "label") and hasattr(
                        view_bucket.label, "hits"
                    ):
                        title_hits = view_bucket.label.hits.hits
                        if title_hits and title_hits[0]._source:
                            source: AttrDict = title_hits[0]._source
                            # Convert AttrDict to regular dict
                            if hasattr(source, "to_dict"):
                                source = source.to_dict()
                            label_result = CommunityUsageDeltaAggregator._extract_label_from_source(  # noqa: E501
                                source, label_field, key
                            )
                            label = (
                                label_result
                                if isinstance(label_result, (str, dict))
                                else str(key)
                            )

                subcount_item: UsageSubcountItem = {
                    "id": str(key),
                    "label": label,
                    "view": {
                        "total_events": 0,
                        "unique_visitors": 0,
                        "unique_records": 0,
                        "unique_parents": 0,
                    },
                    "download": {
                        "total_events": 0,
                        "unique_visitors": 0,
                        "unique_records": 0,
                        "unique_parents": 0,
                        "unique_files": 0,
                        "total_volume": 0,
                    },
                }

                # Extract view metrics from the bucket
                if view_bucket:
                    subcount_item["view"] = {
                        "total_events": view_bucket.doc_count,
                        "unique_visitors": view_bucket.unique_visitors.value,
                        "unique_records": view_bucket.unique_records.value,
                        "unique_parents": view_bucket.unique_parents.value,
                    }

                # Extract download metrics from the bucket
                if download_bucket:
                    subcount_item["download"] = {
                        "total_events": download_bucket.doc_count,
                        "unique_visitors": download_bucket.unique_visitors.value,
                        "unique_records": download_bucket.unique_records.value,
                        "unique_parents": download_bucket.unique_parents.value,
                        "unique_files": download_bucket.unique_files.value,
                        "total_volume": download_bucket.total_volume.value,
                    }

                combined_results["subcounts"][delta_aggregation_name].append(
                    subcount_item
                )

        return combined_results

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        # Check if we should skip aggregation due to no events after start_date
        should_skip = self._should_skip_aggregation(
            start_date, last_event_date, community_id
        )
        if should_skip:
            current_app.logger.warning(
                f"Skipping usage delta aggregation for {community_id} - "
                f"no events after {start_date}"
            )

        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)

        current_iteration_date = start_date

        while current_iteration_date <= end_date:

            # Prepare the _source content based on whether we should skip
            # aggregation
            if should_skip:
                source_content = self._create_zero_document(
                    community_id, current_iteration_date
                )
            else:
                # Execute separate queries for each event type
                view_index = None
                download_index = None
                for event_type, index in self.event_index:
                    if event_type == "view":
                        view_index = index
                    elif event_type == "download":
                        download_index = index

                # Execute view query
                if view_index:
                    view_search = self.query_builder.build_view_query(
                        community_id, current_iteration_date, current_iteration_date
                    )
                    view_results = view_search.execute()
                else:
                    view_results = None

                # Execute download query
                if download_index:
                    download_search = self.query_builder.build_download_query(
                        community_id, current_iteration_date, current_iteration_date
                    )
                    download_results = download_search.execute()
                else:
                    download_results = None

                # Combine results
                combined_results = self.create_agg_dict(
                    view_results, download_results, community_id, current_iteration_date
                )

                source_content = combined_results

            index_name = prefix_index(
                "{0}-{1}".format(self.aggregation_index, current_iteration_date.year)
            )
            doc_id = f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
            if self.client.exists(index=index_name, id=doc_id):
                self.delete_aggregation(index_name, doc_id)

            yield {
                "_id": doc_id,
                "_index": index_name,
                "_source": source_content,
            }

            current_iteration_date = current_iteration_date.shift(days=1)

    def _combine_split_aggregations(
        self, view_results, download_results, config, subcount_name
    ):
        """Combine separate id and name aggregations for funders and affiliations.

        This method handles the case where we have separate aggregations for id and name
        fields (e.g., by_funders_id and by_funders_name) and need to combine them into
        a single list, deduplicating based on unique combinations of id and name.

        Args:
            view_results: Results from view query (or None).
            download_results: Results from download query (or None).
            config: Configuration for the subcount.
            subcount_name: Name of the subcount being processed.

        Returns:
            list: Combined and deduplicated subcount items.
        """
        combine_queries = config.get("combine_queries", [])
        delta_aggregation_name = config.get("delta_aggregation_name")

        if not combine_queries or len(combine_queries) <= 1:
            return []

        agg_names = []
        for query_field in combine_queries:
            subfield = query_field.split(".")[-1]
            agg_name = f"{delta_aggregation_name}_{subfield}"
            agg_names.append(agg_name)

        if len(agg_names) >= 2:
            id_agg_name = agg_names[0]
            name_agg_name = agg_names[1]
        else:
            return []

        # Get buckets from both aggregations
        buckets = self._get_id_name_buckets(
            view_results, download_results, id_agg_name, name_agg_name
        )

        # Combine and deduplicate
        combined_items = {}
        for bucket_type, bucket, agg_type in buckets:
            id_field_path = next(
                (
                    path
                    for path in config.get("label_source_includes", [])
                    if "id" in path
                ),
                "id",
            )
            name_field_path = next(
                (
                    path
                    for path in config.get("label_source_includes", [])
                    if "id" not in path
                ),
                "name",
            )
            id_and_label = CommunityUsageDeltaAggregator._extract_id_name_from_bucket(
                bucket, bucket_type, id_field_path, name_field_path, config
            )
            key = (id_and_label["id"], id_and_label["label"])  # type: ignore

            if key not in combined_items:
                combined_items[key] = self._create_empty_subcount_item(
                    id_and_label["id"], id_and_label["label"]  # type: ignore
                )

            # Add metrics
            if agg_type == "view":
                combined_items[key]["view"] = self._extract_view_metrics(bucket)
            else:
                combined_items[key]["download"] = self._extract_download_metrics(bucket)

        return list(combined_items.values())

    def _get_id_name_buckets(
        self, view_results, download_results, id_agg_name, name_agg_name
    ):
        """Get all buckets from id and name aggregations for both view and download."""
        buckets = []

        def add_buckets(results, agg_name, agg_type):
            if results and hasattr(results.aggregations, agg_name):
                agg = getattr(results.aggregations, agg_name)
                for bucket in agg.buckets:
                    buckets.append((agg_name, bucket, agg_type))

        add_buckets(view_results, id_agg_name, "view")
        add_buckets(view_results, name_agg_name, "view")
        add_buckets(download_results, id_agg_name, "download")
        add_buckets(download_results, name_agg_name, "download")

        return buckets

    @staticmethod
    def _extract_id_name_from_bucket(
        bucket: AttrDict,
        bucket_type: str,
        id_field_path: str,
        name_field_path: str,
        config: dict,
    ) -> UsageSubcountItem:
        """Extract id and name from a bucket based on its type."""
        extracted_values: UsageSubcountItem = {
            "id": bucket.key,
            "label": bucket.key,
        }

        if hasattr(bucket, "label"):
            if hasattr(bucket.label, "hits"):
                title_hits = bucket.label.hits.hits
                if title_hits and title_hits[0]._source:
                    source = title_hits[0]._source

                if "_id" in bucket_type:
                    match_path = id_field_path
                else:
                    match_path = name_field_path

                field_parts = match_path.split(".")
                if len(field_parts) > 1:
                    field_name = field_parts[0]
                    field_data = source.get(field_name, [])
                    match_path = ".".join(field_parts[1:])
                    id_field_path = ".".join(id_field_path.split(".")[1:])
                    name_field_path = ".".join(name_field_path.split(".")[1:])
                else:
                    field_data = source.get(match_path, [])

                if not hasattr(field_data, "__iter__"):
                    field_data = []
                elif (
                    isinstance(field_data, (list, AttrList))
                    and field_data
                    and isinstance(field_data[0], (list, AttrList))
                ):
                    field_data = list(chain.from_iterable(field_data))

                target_values = (
                    CommunityUsageDeltaAggregator._find_and_merge_matching_items(
                        field_data,  # type: ignore
                        bucket.key,
                        match_path,
                        id_field_path,
                        name_field_path,
                    )
                )
                extracted_values = target_values if target_values else extracted_values

        if extracted_values and isinstance(extracted_values, dict):
            return extracted_values
        else:
            return {"id": bucket.key, "label": bucket.key}

    @staticmethod
    def _extract_fields_from_label(bucket, bucket_type, id_field_path, name_field_path):
        """Extract a field value from bucket label aggregation after merging items."""
        if hasattr(bucket, "label"):
            if hasattr(bucket.label, "hits"):
                title_hits = bucket.label.hits.hits
                if title_hits and title_hits[0]._source:
                    source = title_hits[0]._source

                if "_id" in bucket_type:
                    match_path = id_field_path
                else:
                    match_path = name_field_path

                field_parts = match_path.split(".")
                if len(field_parts) > 1:
                    field_name = field_parts[0]
                    field_data = source.get(field_name, [])
                    match_path_string = ".".join(field_parts[1:])
                    id_field_path = ".".join(id_field_path.split(".")[1:])
                    name_field_path = ".".join(name_field_path.split(".")[1:])
                else:
                    field_data = source.get(match_path, [])
                    match_path_string = match_path

                if not hasattr(field_data, "__iter__"):
                    field_data = []
                elif (
                    isinstance(field_data, (list, AttrList))
                    and field_data
                    and isinstance(field_data[0], (list, AttrList))
                ):
                    field_data = list(chain.from_iterable(field_data))

                target_values = (
                    CommunityUsageDeltaAggregator._find_and_merge_matching_items(
                        field_data,  # type: ignore
                        bucket.key,
                        match_path_string,
                        id_field_path,
                        name_field_path,
                    )
                )
                return target_values

        return {"id": bucket.key, "label": bucket.key}

    @staticmethod
    def _get_nested_field_value(item, field_path, fallback):
        """Get a nested field value from an item using dot notation."""
        if "." not in field_path:
            try:
                return item[field_path]
            except (KeyError, AttributeError):
                return fallback

        parts = field_path.split(".")
        value = item
        for part in parts:
            try:
                if isinstance(value, (dict, AttrDict)) and part in value:
                    value = value[part]
                else:
                    return fallback
            except (KeyError, AttributeError):
                return fallback
        return value

    @staticmethod
    def _find_and_merge_matching_items(
        field_data: list,
        bucket_key: str,
        match_path: str,
        id_field_path: str,
        name_field_path: str,
    ) -> UsageSubcountItem | None:
        """Find all items that match the bucket key and return id/label dict.

        Args:
            field_data: List of items to search through
            bucket_key: The value to match against
            match_path: The field path to match on (e.g., "funder.id")
            id_field_path: The field path for the ID (e.g., "funder.id")
            name_field_path: The field path for the name (e.g., "funder.name")

        Returns:
            Dictionary with "id" and "label" keys, or None if no matches
        """

        if not hasattr(field_data, "__iter__") or len(field_data) == 0:
            return None

        matching_items = []

        for item in field_data:
            field_value = None
            if isinstance(item, dict) or hasattr(item, "get"):
                field_value = CommunityUsageDeltaAggregator._get_nested_field_value(
                    item, match_path, None
                )
                if field_value:
                    if match_path == name_field_path:
                        matches = field_value.lower() == bucket_key.lower()
                    else:
                        matches = field_value == bucket_key

                    if matches:
                        matching_items.append(item)

        if not matching_items:
            return None

        if match_path == id_field_path:
            id_val = bucket_key
            label_val = bucket_key
            for item in matching_items:
                name_value = CommunityUsageDeltaAggregator._get_nested_field_value(
                    item, name_field_path, None
                )
                if name_value and str(name_value) != bucket_key:
                    label_val = name_value
                    break
        else:
            label_val = bucket_key
            id_val = bucket_key
            for item in matching_items:
                id_value = CommunityUsageDeltaAggregator._get_nested_field_value(
                    item, id_field_path, None
                )
                if id_value and str(id_value) != bucket_key:
                    id_val = id_value
                    break

        return {"id": id_val, "label": label_val}

    def _create_empty_subcount_item(self, item_id, name):
        """Create an empty subcount item with zero metrics."""
        return {
            "id": str(item_id),
            "label": name,
            "view": {
                "total_events": 0,
                "unique_visitors": 0,
                "unique_records": 0,
                "unique_parents": 0,
            },
            "download": {
                "total_events": 0,
                "unique_visitors": 0,
                "unique_records": 0,
                "unique_parents": 0,
                "unique_files": 0,
                "total_volume": 0,
            },
        }

    def _extract_view_metrics(self, bucket):
        """Extract view metrics from a bucket."""
        return {
            "total_events": bucket.doc_count,
            "unique_visitors": bucket.unique_visitors.value,
            "unique_records": bucket.unique_records.value,
            "unique_parents": bucket.unique_parents.value,
        }

    def _extract_download_metrics(self, bucket):
        """Extract download metrics from a bucket."""
        return {
            "total_events": bucket.doc_count,
            "unique_visitors": bucket.unique_visitors.value,
            "unique_records": bucket.unique_records.value,
            "unique_parents": bucket.unique_parents.value,
            "unique_files": bucket.unique_files.value,
            "total_volume": bucket.total_volume.value,
        }

    @staticmethod
    def _extract_label_from_source(
        source: dict, title_field: str, bucket_key: str
    ) -> str | dict[str, str]:
        """Extract the correct label from source by matching the bucket key.

        This method handles the case where the label sub-aggregation contains all items
        (e.g., all subjects), and we need to find the specific one that matches
        the bucket's key (ID).

        Args:
            source: The source document from the label sub-aggregation
            title_field: The field path (e.g., "subjects.title")
            bucket_key: The bucket key (ID) to match against

        Returns:
            The label string, or the bucket_key as fallback
        """
        if "." not in title_field:
            result = source.get(title_field, str(bucket_key))
            return result if isinstance(result, (str, dict)) else str(bucket_key)

        parts = title_field.split(".")

        # The first part should be the array field (e.g., "subjects")
        array_field = parts[0]
        if array_field not in source:
            return str(bucket_key)

        field_value = source[array_field]

        if not isinstance(field_value, list):
            if len(parts) == 1:
                return str(field_value)
            else:
                label_path = parts[1:]
                value = field_value
                for part in label_path:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = ""
                        break
                return str(value) if value else str(bucket_key)

        if isinstance(field_value, list) and len(field_value) > 0:
            label_path_leaf = parts[1:] if len(parts) > 1 else []
            label = CommunityAggregatorBase._find_matching_item_by_key(
                field_value, label_path_leaf, bucket_key
            )
            if label and isinstance(label, (str, dict)):
                return label
            else:
                return str(bucket_key)

        return str(bucket_key)


class CommunityRecordsDeltaAggregatorBase(CommunityAggregatorBase):
    """Aggregator for community record deltas.

    Uses the date the record was created as the initial date of the record.
    """

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.first_event_index: str = prefix_index("stats-community-events")
        self.event_index: str = prefix_index("stats-community-events")
        self.record_index: str = prefix_index("rdmrecords-records")
        self.aggregation_index: str = prefix_index(
            "stats-community-records-delta-created"
        )
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
        )
        # Default to using record creation dates
        self.first_event_date_field = "record_created_date"
        self.event_date_field = "record_created_date"
        self.event_community_query_term = lambda community_id: Q(
            "term", community_id=community_id
        )

    def _should_skip_aggregation(  # type: ignore[override]
        self,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        last_event_date: arrow.Arrow | None = None,
        community_id: str | None = None,
    ) -> bool:
        """Check if aggregation should be skipped because no records in date range.

        We already know the last event date, so we can skip the aggregation if it's
        before the start date. Otherwise, we need to check if there are any records
        with event dates in the date range.

        Args:
            start_date: The start date for aggregation
            end_date: The end date for aggregation
            last_event_date: The last event date, or None if no events exist
            community_id: The community ID to check (optional, for testing)

        Returns:
            True if aggregation should be skipped, False otherwise
        """
        if last_event_date is None:
            return True
        if last_event_date < start_date:
            return True

        # For record delta aggregators, we need to check if there are any records
        # that were created or added to the community or published (depending on the
        # aggregator) before or on the aggregation date
        if community_id == "global":
            # For global aggregator, just check if there are any records at all
            search = Search(using=self.client, index=self.event_index)
            count_result: int = search.count()  # type: ignore[assignment]
            return count_result == 0
        else:
            # For community-specific aggregators, check if any records were added
            # to the community before or on the aggregation date
            community_search = (
                Search(using=self.client, index=prefix_index("stats-community-events"))
                .filter("term", community_id=community_id)
                .filter(
                    "range",
                    **{
                        self.event_date_field: {
                            "gte": (
                                start_date.floor("day").format("YYYY-MM-DDTHH:mm:ss")
                            ),
                            "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                        }
                    },
                )
            )

            community_results: int = community_search.count()  # type: ignore

            return community_results == 0

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> RecordDeltaDocument:
        """Create a zero-value delta document for when no events exist.

        Args:
            community_id: The community ID
            current_day: The current day for the delta

        Returns:
            A delta document with zero values
        """
        return {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "period_start": current_day.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": current_day.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "records": {
                "added": {
                    "metadata_only": 0,
                    "with_files": 0,
                },
                "removed": {
                    "metadata_only": 0,
                    "with_files": 0,
                },
            },
            "parents": {
                "added": {
                    "metadata_only": 0,
                    "with_files": 0,
                },
                "removed": {
                    "metadata_only": 0,
                    "with_files": 0,
                },
            },
            "files": {
                "added": {
                    "file_count": 0,
                    "data_volume": 0,
                },
                "removed": {
                    "file_count": 0,
                    "data_volume": 0,
                },
            },
            "uploaders": 0,
            "subcounts": {
                config["records"]["delta_aggregation_name"]: []
                for config in self.subcount_configs.values()
                if "records" in config
                and "delta_aggregation_name" in config["records"]
                and not config["records"].get("merge_aggregation_with")
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    @staticmethod
    def _find_item_label(
        added: dict, removed: dict, path_strings: list[str], key: str
    ) -> str | dict[str, str]:
        """Find the label for a given item."""
        label: str | dict[str, str] = ""

        if len(path_strings) > 1:
            label_item = added if added else removed
            label_field = path_strings[1]
            source_path = ["label", "hits", "hits", 0, "_source"]
            label_path_stem = source_path + label_field.split(".")[:2]
            label_path_leaf = label_field.split(".")[2:]

            if label_path_leaf and label_path_leaf[-1].endswith(".keyword"):
                label_path_leaf[-1] = label_path_leaf[-1][:-7]

            label_options = CommunityAggregatorBase._get_nested_value(
                label_item, label_path_stem
            )

            if isinstance(label_options, list) and len(label_options) > 0:
                label = CommunityAggregatorBase._find_matching_item_by_key(
                    label_options, label_path_leaf, key
                )
            elif isinstance(label_options, dict):
                label = CommunityAggregatorBase._get_nested_value(
                    label_options, label_path_leaf
                )
        if isinstance(label, dict) and not label:
            label = ""
        return label

    def _deduplicate_and_merge_buckets(self, buckets):
        """Remove keyword buckets that duplicate ID-based buckets."""
        if not buckets:
            return []

        id_buckets = [b for b in buckets if not b["key"].endswith(".keyword")]
        label_values = [b.get("label", "") for b in id_buckets if b.get("label")]

        return [b for b in buckets if b["key"] not in label_values]

    def _make_subcount_list(self, subcount_type, aggs_added, aggs_removed):
        """Make a subcount list for a given subcount type."""
        config = None
        for cfg in self.subcount_configs.values():
            if (
                "records" in cfg
                and cfg["records"].get("delta_aggregation_name") == subcount_type
            ):
                config = cfg["records"]
                break

        # If no config found, return empty list
        if not config:
            current_app.logger.warning(
                f"No configuration found for subcount type: {subcount_type}"
            )
            return []

        # Validate required config fields
        if "field" not in config:
            current_app.logger.error(
                f"Missing 'field' in config for subcount type: {subcount_type}"
            )
            return []

        # Use centralized configuration
        if config.get("combine_queries"):
            # Handle combined queries (like affiliations)

            # Collect all buckets from different aggregations
            all_added_buckets = []
            all_removed_buckets = []

            for field in config["combine_queries"]:
                field_name = field.split(".")[-1]
                lookup_name = f"{config['delta_aggregation_name']}_{field_name}"
                added_buckets = aggs_added.get(lookup_name, {}).get("buckets", [])
                removed_buckets = aggs_removed.get(lookup_name, {}).get("buckets", [])
                all_added_buckets.extend(added_buckets)
                all_removed_buckets.extend(removed_buckets)

            # Deduplicate by key and merge data
            added_items = self._deduplicate_and_merge_buckets(all_added_buckets)
            removed_items = self._deduplicate_and_merge_buckets(all_removed_buckets)
        else:
            added_items = aggs_added.get(subcount_type, {}).get("buckets", [])
            removed_items = aggs_removed.get(subcount_type, {}).get("buckets", [])

        combined_keys = list(
            set(b["key"] for b in added_items) | set(b["key"] for b in removed_items)
        )
        subcount_list: list[RecordDeltaSubcountItem] = []

        # Handle case where no items found
        if not combined_keys:
            return subcount_list

        for key in combined_keys:
            # Skip None or empty keys
            if not key:
                continue

            added_filtered = list(filter(lambda x: x["key"] == key, added_items))
            added = added_filtered[0] if added_filtered else {}
            removed_filtered = list(filter(lambda x: x["key"] == key, removed_items))
            removed = removed_filtered[0] if removed_filtered else {}

            path_strings: list[str] = []
            if config.get("label_field"):
                path_strings.append(config["field"])
                path_strings.append(config["label_field"])
            else:
                path_strings.append(config["field"])

            label: str | dict[str, str] = (
                CommunityRecordsDeltaAggregatorBase._find_item_label(
                    added, removed, path_strings, key
                )
            )

            subcount_list.append(
                {
                    "id": key,
                    "label": label,  # type: ignore
                    "records": {
                        "added": {
                            "metadata_only": (
                                added.get("without_files", {}).get("doc_count", 0)
                            ),
                            "with_files": (
                                added.get("with_files", {}).get("doc_count", 0)
                            ),
                        },
                        "removed": {
                            "metadata_only": (
                                removed.get("without_files", {}).get("doc_count", 0)
                            ),
                            "with_files": (
                                removed.get("with_files", {}).get("doc_count", 0)
                            ),
                        },
                    },
                    "parents": {
                        "added": {
                            "metadata_only": (
                                added.get("without_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                            ),
                            "with_files": (
                                added.get("with_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                            ),
                        },
                        "removed": {
                            "metadata_only": (
                                removed.get("without_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                            ),
                            "with_files": (
                                removed.get("with_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                            ),
                        },
                    },
                    "files": {
                        "added": {
                            "file_count": added.get("file_count", {}).get("value", 0),
                            "data_volume": (
                                added.get("total_bytes", {}).get("value", 0.0)
                            ),
                        },
                        "removed": {
                            "file_count": removed.get("file_count", {}).get("value", 0),
                            "data_volume": (
                                removed.get("total_bytes", {}).get("value", 0.0)
                            ),
                        },
                    },
                }
            )
        return subcount_list

    def create_agg_dict(
        self,
        community_id: str,
        current_day: arrow.Arrow,
        aggs_added: dict,
        aggs_removed: dict,
    ) -> RecordDeltaDocument:
        """Create a dictionary representing the aggregation result for indexing."""

        agg_dict: RecordDeltaDocument = {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "period_start": current_day.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": current_day.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "records": {
                "added": {
                    "metadata_only": (
                        aggs_added.get("without_files", {}).get("doc_count", 0)
                    ),
                    "with_files": aggs_added.get("with_files", {}).get("doc_count", 0),
                },
                "removed": {
                    "metadata_only": (
                        aggs_removed.get("without_files", {}).get("doc_count", 0)
                    ),
                    "with_files": (
                        aggs_removed.get("with_files", {}).get("doc_count", 0)
                    ),
                },
            },
            "parents": {
                "added": {
                    "metadata_only": (
                        aggs_added.get("without_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                    "with_files": (
                        aggs_added.get("with_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                },
                "removed": {
                    "metadata_only": (
                        aggs_removed.get("without_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                    "with_files": (
                        aggs_removed.get("with_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                },
            },
            "files": {
                "added": {
                    "file_count": aggs_added.get("file_count", {}).get("value", 0),
                    "data_volume": aggs_added.get("total_bytes", {}).get("value", 0.0),
                },
                "removed": {
                    "file_count": aggs_removed.get("file_count", {}).get("value", 0),
                    "data_volume": (
                        aggs_removed.get("total_bytes", {}).get("value", 0.0)
                    ),
                },
            },
            "uploaders": aggs_added.get("uploaders", {}).get("value", 0),
            "subcounts": {
                **{
                    config["records"][
                        "delta_aggregation_name"
                    ]: self._make_subcount_list(
                        config["records"].get("delta_aggregation_name"),
                        aggs_added,
                        aggs_removed,
                    )
                    for config in self.subcount_configs.values()
                    if (
                        "records" in config
                        and "delta_aggregation_name" in config["records"]
                    )
                },
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }
        return agg_dict

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[dict, None, None]:
        """Query opensearch for record counts for each day period.

        Args:
            community_id (str): The community id to query.
            community_parent_id (str): The community parent id to query.
            start_date (str): The start date to query.
            end_date (str): The end date to query.
            search_domain (str, optional): The search domain to use. If provided,
                creates a new client instance. If None, uses the default
                current_search_client.

        Returns:
            dict: A dictionary containing lists of buckets for each time period.
        """
        # Check if we should skip aggregation due to no events after start_date
        # If so, we index a zero document for the community for each day
        should_skip = self._should_skip_aggregation(
            start_date, end_date, last_event_date, community_id
        )
        if should_skip:
            current_app.logger.error(
                f"Skipping delta aggregation for {community_id} - "
                f"no relevant records after {start_date}"
            )

        # Index aggregations in yearly indices
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)
        query_builder = CommunityRecordDeltaQuery(
            client=self.client,  # type: ignore
            event_index=self.event_index,
            record_index=self.record_index,
        )
        for year in range(start_date.year, end_date.year + 1):
            year_start_date = max(arrow.get(f"{year}-01-01"), start_date)
            year_end_date = min(arrow.get(f"{year}-12-31"), end_date)

            index_name = prefix_index("{0}-{1}".format(self.aggregation_index, year))

            for day in arrow.Arrow.range("day", year_start_date, year_end_date):
                day_start_date = day.floor("day")

                if should_skip:
                    source_content = self._create_zero_document(
                        community_id, day_start_date
                    )
                else:
                    day_end_date = day.ceil("day")

                    day_search_added = query_builder.build_query(
                        day_start_date.format("YYYY-MM-DDTHH:mm:ss"),
                        day_end_date.format("YYYY-MM-DDTHH:mm:ss"),
                        community_id=community_id,
                        use_included_dates=(
                            self.aggregation_index
                            == "stats-community-records-delta-added"
                        ),
                        use_published_dates=(
                            self.aggregation_index
                            == "stats-community-records-delta-published"
                        ),
                    )
                    day_results_added = day_search_added.execute()
                    aggs_added = day_results_added.aggregations.to_dict()

                    day_search_removed = query_builder.build_query(
                        day_start_date.format("YYYY-MM-DDTHH:mm:ss"),
                        day_end_date.format("YYYY-MM-DDTHH:mm:ss"),
                        community_id=community_id,
                        find_deleted=True,
                    )
                    day_results_removed = day_search_removed.execute()
                    aggs_removed = day_results_removed.aggregations.to_dict()

                    source_content = self.create_agg_dict(
                        community_id, day_start_date, aggs_added, aggs_removed
                    )

                # Check if an aggregation already exists for this date
                # If it does, delete it (we'll re-create it below)
                document_id = f"{community_id}-{day_start_date.format('YYYY-MM-DD')}"
                if self.client.exists(index=index_name, id=document_id):
                    self.delete_aggregation(index_name, document_id)

                # Process the current date even if there are no buckets
                # so that we have a record for every day in the period
                yield {
                    "_id": document_id,
                    "_index": index_name,
                    "_source": source_content,
                }


class CommunityRecordsDeltaCreatedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community record deltas.

    Uses the date the record was created as the initial date of the record.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-delta-created")
        self.event_date_field = "record_created_date"


class CommunityRecordsDeltaAddedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community records delta added."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-delta-added")
        self.event_date_field = "event_date"


class CommunityRecordsDeltaPublishedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community records delta published."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-delta-published")
        self.event_date_field = "record_published_date"


class CommunityEventsIndexAggregator(CommunityAggregatorBase):
    """Dummy aggregator for registering the community events index template.

    This aggregator doesn't actually perform any aggregation - it's just used
    to register the index template with the invenio-stats system.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # This aggregator doesn't need any specific configuration

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[dict, None, None]:
        """This aggregator doesn't perform any aggregation."""
        # Return empty generator - no aggregation needed
        return
        yield  # This line is never reached but satisfies the generator requirement
