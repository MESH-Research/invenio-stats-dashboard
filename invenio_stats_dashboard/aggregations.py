import copy
from collections import defaultdict
from collections.abc import Generator
from functools import wraps
from pprint import pformat
from typing import Any, Callable

import datetime
import time

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from opensearchpy import AttrDict, AttrList
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.bookmark import BookmarkAPI
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.aggs import Bucket
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.search import Search
from invenio_stats.aggregations import StatAggregator
from .queries import (
    daily_record_snapshot_query_with_events,
    daily_record_delta_query_with_events,
)
from .proxies import current_community_stats_service
from .exceptions import CommunityEventIndexingError

SUBCOUNT_TYPES = {
    "resource_type": [
        "metadata.resource_type.id",
        "metadata.resource_type.title.en",
    ],
    "access_rights": ["access.status"],
    "language": ["metadata.languages.id", "metadata.languages.title.en"],
    "affiliation_creator": [
        "metadata.creators.affiliations.id",
        "metadata.creators.affiliations.name.keyword",
    ],
    "affiliation_contributor": [
        "metadata.contributors.affiliations.id",
        "metadata.contributors.affiliations.name.keyword",
    ],
    "funder": [
        "metadata.funding.funder.id",
        "metadata.funding.funder.title.en",
    ],
    "subject": ["metadata.subjects.id", "metadata.subjects.subject"],
    "publisher": ["metadata.publisher.keyword"],
    "periodical": ["custom_fields.journal:journal.title.keyword"],
    "file_type": ["files.entries.ext"],
    "license": ["metadata.rights.id", "metadata.rights.title.en"],
}


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
        # Field name for searching event indices - should be overridden by subclasses
        self.event_date_field = "created"
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
        self, community_id: str, index_name: str
    ) -> tuple[arrow.Arrow | None, arrow.Arrow | None]:
        """Get the first event date from a specific index.

        A min aggregation is more efficient than sorting the query.
        """
        current_search_client.indices.refresh(index=index_name)
        if community_id == "global":
            query = Q("match_all")
        else:
            query = self.event_community_query_term(community_id)

        search = Search(using=self.client, index=index_name).query(query).extra(size=0)
        search.aggs.bucket("min_date", "min", field=self.event_date_field)
        search.aggs.bucket("max_date", "max", field=self.event_date_field)

        results = search.execute()
        min_date = results.aggregations.min_date.value
        max_date = results.aggregations.max_date.value
        current_app.logger.error(f"Min date: {min_date}")
        current_app.logger.error(f"Max date: {max_date}")

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

        if isinstance(self.event_index, str):
            # Single index case
            current_app.logger.error(f"Finding first event date for {self.event_index}")
            earliest_date, latest_date = self._first_event_date_query(
                community_id, self.event_index
            )
        elif isinstance(self.event_index, list):
            # Multiple indices case (e.g., for usage aggregators)
            for _, index in self.event_index:
                current_app.logger.error(f"Finding first event date for {index}")
                early_date, late_date = self._first_event_date_query(
                    community_id, index
                )
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
                current_app.logger.error(
                    f"Community event indexing failed for {community_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt == max_retries - 1:
                    raise CommunityEventIndexingError(
                        f"Failed to index community events for {community_id} "
                        f"after {max_retries} attempts: {e}"
                    ) from e

                # Exponential backoff
                delay = base_delay * (2**attempt)
                current_app.logger.info(
                    f"Retrying community event indexing for {community_id} "
                    f"in {delay} seconds..."
                )
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
        # Initialize community event bookmark API
        event_bookmark_api = CommunityEventBookmarkAPI(self.client)

        # Index community add/remove events only up to the last index event date
        indexing_end_date = min(upper_limit, last_index_event_date)
        current_app.logger.error(f"Indexing end date: {pformat(indexing_end_date)}")

        # Try to use bookmark first, fall back to query if not available
        indexing_start_date = None

        # Check if we have a bookmark for this community
        bookmark_date = event_bookmark_api.get_bookmark(community_id)
        if bookmark_date:
            indexing_start_date = bookmark_date
            current_app.logger.error(
                f"Using bookmark for {community_id}: " f"{pformat(bookmark_date)}"
            )
        else:
            # No bookmark exists - need to do initial indexing
            # Use the first_index_event_date which already handles global vs
            # specific communities
            indexing_start_date = first_index_event_date
            current_app.logger.error(
                f"No bookmark for {community_id}. "
                f"Initial indexing from {first_index_event_date} to {upper_limit}..."
            )

        # Check if indexing is needed
        if indexing_start_date >= indexing_end_date:
            current_app.logger.error(
                f"No indexing needed for {community_id} from "
                f"{indexing_start_date} to {indexing_end_date}."
            )
            return upper_limit

        # Index the community events
        try:
            current_community_stats_service.generate_record_community_events(
                community_ids=[community_id],
                end_date=indexing_end_date.format("YYYY-MM-DD"),
                start_date=indexing_start_date.format("YYYY-MM-DD"),
            )
            current_app.logger.error(
                f"Indexed {community_id} events for {indexing_start_date} "
                f"to {indexing_end_date}"
            )

            # Update the bookmark after successful indexing
            event_bookmark_api.set_bookmark(community_id, indexing_end_date.isoformat())
            current_app.logger.error(
                f"Updated bookmark for {community_id} to {indexing_end_date}"
            )

        except Exception as e:
            current_app.logger.error(
                f"Failed to index community events for {community_id}: {e}"
            )
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
        current_app.logger.error(f"Running aggregation for {self.name}")
        start_date = arrow.get(start_date) if start_date else None
        end_date = arrow.get(end_date) if end_date else None
        # If no records have been indexed there is nothing to aggregate
        if (
            isinstance(self.event_index, str)
            and not Index(self.event_index, using=self.client).exists()
        ):
            return [(0, [])]
        elif isinstance(self.event_index, list):
            for label, index in self.event_index:
                if not Index(index, using=self.client).exists():
                    return [(0, [])]

        # FIXME: We need to find a way to ensure that the last aggregation
        # run isn't still underway and skip if it is

        if self.community_ids:
            all_communities = self.community_ids
        else:
            all_communities = [
                c["id"]
                for c in current_communities.service.read_all(system_identity, [])
            ]
        all_communities.append("global")  # Global stats are always aggregated

        results = []
        for community_id in all_communities:
            current_app.logger.error(f"Running aggregation for {community_id}")
            try:
                first_event_date, last_event_date = self._find_first_event_date(
                    community_id
                )
            except ValueError:
                current_app.logger.error(
                    f"No events found for community {community_id}. "
                    f"Skipping aggregagation for this community."
                )
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
            # Check that community add/remove events have been indexed for the desired
            # period and if not, index them first. Do this even if we're ignoring the
            # bookmark since otherwise we don't have accurate data in the aggregations.
            first_event_date_safe = first_event_date or arrow.utcnow()
            last_event_date_safe = last_event_date or arrow.utcnow()

            # FIXME: Add a bookmark for the community events index
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
                    f"Skipping aggregation for {community_id} due to "
                    f"community event indexing failure: {e}"
                )
                continue
            # FIXME: We need to periodically check for gaps in the community events

            # Check if upper_limit is now < lower_limit after community event indexing
            # If so, skip this community iteration without updating the bookmark or
            # performing aggregations
            # NOTE: upper_limit could legitimately be lower if we spent this iteration
            # indexing prior community add/remove events.
            if upper_limit < lower_limit:
                current_app.logger.error(
                    f"Upper limit {upper_limit} < lower limit {lower_limit} "
                    f"for {community_id}. Skipping this iteration."
                )
                continue

            next_bookmark = arrow.get(upper_limit).format("YYYY-MM-DDTHH:mm:ss.SSS")
            current_app.logger.error(
                f"Lower limit: {lower_limit}, upper limit: {upper_limit}"
                f"for community {community_id}"
            )
            current_app.logger.error(
                f"Running aggregation for {community_id} from {lower_limit} "
                f"to {upper_limit}"
            )

            results.append(
                bulk(
                    self.client,
                    self.agg_iter(
                        community_id,
                        lower_limit,
                        upper_limit,
                        first_event_date,
                        last_event_date,
                    ),
                    stats_only=False if return_results else True,
                    chunk_size=50,
                )
            )
            current_app.logger.error(f"Results: {pformat(results)}")
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

    def _get_nested_value(
        self, data: dict | AttrDict, path: list, key: str | None = None
    ) -> Any:
        """Get a nested value from a dictionary using a list of path segments.

        Args:
            data: The dictionary to traverse
            path: List of path segments to traverse
            key: Optional key to match when traversing arrays

        Returns:
            The value at the end of the path, or an empty dict if not found
        """
        # current_app.logger.error(f"Getting nested value in {data}")
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
        return last_event_date < start_date

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> dict:
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


class CommunityRecordsSnapshotAggregatorBase(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-records-snapshot")

    @property
    def use_included_dates(self):
        """Whether to use included dates for community queries."""
        return False

    @property
    def use_published_dates(self):
        """Whether to use published dates for community queries."""
        return False

    def _should_skip_aggregation(
        self,
        start_date: arrow.Arrow,
        last_event_date: arrow.Arrow | None,
        community_id: str | None = None,
    ) -> bool:
        """Check if aggregation should be skipped due to no relevant records in date range.

        This method provides early skip logic for record aggregators by:
        1. Checking if there are any records that were added to the community before or on the aggregation date
        2. If no relevant records exist, we can skip the expensive processing pipeline entirely

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

        # For record aggregators, we need to check if there are any records
        # that were added to the community before or on the aggregation date
        if community_id == "global":
            # For global aggregator, just check if there are any records at all
            search = Search(using=self.client, index=self.event_index)
            return search.count() == 0
        else:
            # For community-specific aggregators, check if any records were added
            # to the community before or on the aggregation date
            community_search = (
                Search(using=self.client, index=prefix_index("stats-community-events"))
                .filter("term", community_id=community_id)
                .filter(
                    "range",
                    event_date={
                        "lte": start_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                    },
                )
            )

            # Add terms aggregation to get unique records
            record_agg = community_search.aggs.bucket(
                "by_record", "terms", field="record_id"
            )
            record_agg.bucket(
                "top_hits",
                "top_hits",
                size=1,
                sort=[{"event_date": {"order": "desc"}}],
                _source={"includes": ["event_type"]},
            )

            community_results = community_search.execute()

            # Check if any records have "added" as their last event type
            for bucket in community_results.aggregations.by_record.buckets:
                if bucket.top_hits.hits[0]["event_type"] == "added":
                    # Found at least one record that was added to the community
                    return False

            # No records found that were added to the community before the aggregation date
            return True

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> dict:
        """Create a zero-value snapshot document for when no events exist.

        Args:
            community_id: The community ID
            current_day: The current day for the snapshot

        Returns:
            A snapshot document with zero values
        """
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
            "subcounts": {
                "all_resource_types": [],
                "all_access_rights": [],
                "all_languages": [],
                "top_affiliations_creator": [],
                "top_affiliations_contributor": [],
                "top_funders": [],
                "top_subjects": [],
                "top_publishers": [],
                "top_periodicals": [],
                "all_licenses": [],
                "all_file_types": [],
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    def create_agg_dict(
        self,
        community_id: str,
        current_day: arrow.Arrow,
        aggs_added: dict,
        aggs_removed: dict,
    ) -> dict:
        """Create a dictionary representing the aggregation result for indexing."""

        def find_item_label(added, removed, subcount_def, key):
            label = ""

            if len(subcount_def) > 1:
                label_item = added if added else removed
                label_field = subcount_def[1]
                source_path = ["label", "hits", "hits", 0, "_source"]
                label_path_stem = source_path + label_field.split(".")[:2]
                label_path_leaf = label_field.split(".")[2:]

                # We need to find the specific item that matches the key
                # Because the non-nested top-hits agg returns all items
                label_options = self._get_nested_value(label_item, label_path_stem)

                if isinstance(label_options, list) and len(label_options) > 0:
                    matching_option = next(
                        (
                            label_option
                            for label_option in label_options
                            if label_option.get("id") == key
                        ),
                        None,
                    )
                    if matching_option:
                        # Extract the label field directly from the matched object
                        if len(label_path_leaf) == 1:
                            label = matching_option.get(label_path_leaf[0], "")
                        else:
                            # For nested paths, use _get_nested_value
                            label = self._get_nested_value(
                                matching_option, label_path_leaf, key=key
                            )
                elif isinstance(label_options, dict):
                    label = self._get_nested_value(
                        label_options, label_path_leaf, key=key
                    )
            # Convert empty dict to empty string for consistency
            if isinstance(label, dict) and not label:
                label = ""
            return label

        def make_file_type_dict():
            combined_keys = list(
                set(
                    b["key"]
                    for b in aggs_added.get("by_file_type", {}).get("buckets", [])
                    if b["key"] != "doc_count"
                )
                | set(
                    b["key"]
                    for b in aggs_removed.get("by_file_type", {}).get("buckets", [])
                    if b["key"] != "doc_count"
                )
            )
            file_type_list = []
            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        aggs_added.get("by_file_type", {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        aggs_removed.get("by_file_type", {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                file_type_list.append(
                    {
                        "id": key,
                        "label": "",
                        "records": (
                            added.get("unique_records", {}).get("value", 0)
                            - removed.get("unique_records", {}).get("value", 0)
                        ),
                        "parents": (
                            added.get("unique_parents", {}).get("value", 0)
                            - removed.get("unique_parents", {}).get("value", 0)
                        ),
                        "file_count": (
                            added.get("doc_count", 0) - removed.get("doc_count", 0)
                        ),
                        "data_volume": (
                            added.get("total_bytes", {}).get("value", 0)
                            - removed.get("total_bytes", {}).get("value", 0)
                        ),
                    }
                )
            return file_type_list

        def make_subcount_dict(subcount_type):
            # Merge affiliation id and name buckets
            # This is necessary because we can't aggregate on the id and name fields
            # at the same time in the query, so we need to merge them into a single
            # bucket for the aggregation document
            if subcount_type in [
                "by_affiliation_creator",
                "by_affiliation_contributor",
            ]:
                aggs_added[subcount_type] = {
                    "buckets": (
                        aggs_added[f"{subcount_type}_id"]["buckets"]
                        + aggs_added[f"{subcount_type}_name"]["buckets"]
                    )
                }
                aggs_removed[subcount_type] = {
                    "buckets": (
                        aggs_removed[f"{subcount_type}_id"]["buckets"]
                        + aggs_removed[f"{subcount_type}_name"]["buckets"]
                    )
                }

            combined_keys = list(
                set(
                    b["key"]
                    for b in aggs_added.get(subcount_type, {}).get("buckets", [])
                    if b["key"] != "doc_count"
                )
                | set(
                    b["key"]
                    for b in aggs_removed.get(subcount_type, {}).get("buckets", [])
                    if b["key"] != "doc_count"
                )
            )
            subcount_list = []

            for key in combined_keys:
                subcount_name = subcount_type[3:]
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        aggs_added.get(subcount_type, {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        aggs_removed.get(subcount_type, {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                label = find_item_label(
                    added, removed, SUBCOUNT_TYPES[subcount_name], key
                )
                subcount_item = {
                    "id": key,
                    "label": label,
                    "records": {
                        "metadata_only": (
                            added.get("without_files", {}).get("doc_count", 0)
                            - removed.get("without_files", {}).get("doc_count", 0)
                        ),
                        "with_files": (
                            added.get("with_files", {}).get("doc_count", 0)
                            - removed.get("with_files", {}).get("doc_count", 0)
                        ),
                    },
                    "parents": {
                        "metadata_only": (
                            added.get("without_files", {})
                            .get("unique_parents", {})
                            .get("value", 0)
                            - removed.get("without_files", {})
                            .get("unique_parents", {})
                            .get("value", 0)
                        ),
                        "with_files": (
                            added.get("with_files", {})
                            .get("unique_parents", {})
                            .get("value", 0)
                            - removed.get("with_files", {})
                            .get("unique_parents", {})
                            .get("value", 0)
                        ),
                    },
                    "files": {
                        "file_count": (
                            added.get("file_count", {}).get("value", 0)
                            - removed.get("file_count", {}).get("value", 0)
                        ),
                        "data_volume": (
                            added.get("total_bytes", {}).get("value", 0)
                            - removed.get("total_bytes", {}).get("value", 0)
                        ),
                    },
                }
                subcount_list.append(subcount_item)
            return subcount_list

        agg_dict = {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "snapshot_date": current_day.format("YYYY-MM-DD"),
            "total_records": {
                "metadata_only": (
                    aggs_added.get("without_files", {}).get("doc_count", 0)
                    - aggs_removed.get("without_files", {}).get("doc_count", 0)
                ),
                "with_files": (
                    aggs_added.get("with_files", {}).get("doc_count", 0)
                    - aggs_removed.get("with_files", {}).get("doc_count", 0)
                ),
            },
            "total_parents": {
                "metadata_only": (
                    aggs_added.get("without_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                    - aggs_removed.get("without_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                ),
                "with_files": (
                    aggs_added.get("with_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                    - aggs_removed.get("with_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                ),
            },
            "total_files": {
                "file_count": (
                    aggs_added.get("file_count", {}).get("value", 0)
                    - aggs_removed.get("file_count", {}).get("value", 0)
                ),
                "data_volume": (
                    aggs_added.get("total_bytes", {}).get("value", 0)
                    - aggs_removed.get("total_bytes", {}).get("value", 0)
                ),
            },
            "total_uploaders": (
                aggs_added.get("uploaders", {}).get("value", 0)
                - aggs_removed.get("uploaders", {}).get("value", 0)
            ),
            "subcounts": {
                "all_resource_types": make_subcount_dict("by_resource_type"),
                "all_access_rights": make_subcount_dict("by_access_rights"),
                "all_languages": make_subcount_dict("by_language"),
                "top_affiliations_creator": make_subcount_dict(
                    "by_affiliation_creator"
                ),
                "top_affiliations_contributor": make_subcount_dict(
                    "by_affiliation_contributor"
                ),
                "top_funders": make_subcount_dict("by_funder"),
                "top_subjects": make_subcount_dict("by_subject"),
                "top_publishers": make_subcount_dict("by_publisher"),
                "top_periodicals": make_subcount_dict("by_periodical"),
                "all_licenses": make_subcount_dict("by_license"),
                "all_file_types": make_file_type_dict(),
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }
        # current_app.logger.error(f"Agg dict: {pformat(agg_dict)}")
        return agg_dict

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

        Returns:
            A generator of dictionaries, where each dictionary is an aggregation
            document for a single day to be indexed.
        """

        # Check if we should skip aggregation due to no events after start_date
        should_skip = self._should_skip_aggregation(
            start_date, last_event_date, community_id
        )
        if should_skip:
            current_app.logger.error(
                f"Skipping aggregation for {community_id} - "
                f"no relevant records after {start_date}"
            )

        # Make sure we don't miss any old records
        earliest_date = arrow.get("1900-01-01").floor("day")
        current_iteration_date = arrow.get(start_date)

        while current_iteration_date <= arrow.get(end_date):
            # Prepare the _source content based on whether we should skip aggregation
            if should_skip:
                source_content = self._create_zero_document(
                    community_id, current_iteration_date
                )
            else:
                snapshot_added_search = Search(
                    using=self.client, index=self.event_index
                )

                snapshot_query_added = daily_record_snapshot_query_with_events(
                    earliest_date.format("YYYY-MM-DD"),
                    current_iteration_date.format("YYYY-MM-DD"),
                    community_id=community_id,
                    use_included_dates=self.use_included_dates,
                    use_published_dates=self.use_published_dates,
                    client=self.client,
                )
                snapshot_added_search.update_from_dict(snapshot_query_added)

                snapshot_results_added = snapshot_added_search.execute()
                aggs_added = snapshot_results_added.aggregations.to_dict()

                snapshot_removed_search = Search(
                    using=self.client, index=self.event_index
                )

                snapshot_query_removed = daily_record_snapshot_query_with_events(
                    earliest_date.format("YYYY-MM-DD"),
                    current_iteration_date.format("YYYY-MM-DD"),
                    community_id=community_id,
                    find_deleted=True,
                    use_included_dates=self.use_included_dates,
                    use_published_dates=self.use_published_dates,
                    client=self.client,
                )
                snapshot_removed_search.update_from_dict(snapshot_query_removed)

                snapshot_results_removed = snapshot_removed_search.execute()
                aggs_removed = snapshot_results_removed.aggregations.to_dict()

                source_content = self.create_agg_dict(
                    community_id, current_iteration_date, aggs_added, aggs_removed
                )

            index_name = prefix_index(
                "{0}-{1}".format(self.aggregation_index, current_iteration_date.year)
            )
            document_id = (
                f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
            )
            # Check if an aggregation already exists for this date
            # If it does, delete it (we'll re-create it below)
            if self.client.exists(index=index_name, id=document_id):
                self.delete_aggregation(index_name, document_id)

            yield {
                "_id": "{0}-{1}".format(
                    community_id, current_iteration_date.format("YYYY-MM-DD")
                ),
                "_index": index_name,
                "_source": source_content,
            }

            current_iteration_date = current_iteration_date.shift(days=1)


class CommunityRecordsSnapshotCreatedAggregator(CommunityRecordsSnapshotAggregatorBase):
    """Snapshot aggregator for community records using created dates.

    This class uses the record creation date as the basis for community addition timing.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index(
            "stats-community-records-snapshot-created"
        )


class CommunityRecordsSnapshotAddedAggregator(CommunityRecordsSnapshotAggregatorBase):
    """Snapshot aggregator for community records using added dates.

    This class uses the date when records were added to the community as the basis for
    community addition timing.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-snapshot-added")

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

    @property
    def use_published_dates(self):
        """Whether to use published dates for community queries."""
        return True


class CommunityUsageSnapshotAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("stats-community-usage-delta")
        self.aggregation_index = prefix_index("stats-community-usage-snapshot")
        self.event_date_field = "period_start"
        self.event_community_query_term = lambda community_id: Q(
            "term", community_id=community_id
        )

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> dict:
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
            "subcounts": {
                "all_resource_types": [],
                "all_access_rights": [],
                "all_languages": [],
                "all_file_types": [],
                "top_subjects": {"by_view": [], "by_download": []},
                "top_publishers": {"by_view": [], "by_download": []},
                "top_periodicals": {"by_view": [], "by_download": []},
                "top_funders": {"by_view": [], "by_download": []},
                "top_countries": {"by_view": [], "by_download": []},
                "top_user_agents": {"by_view": [], "by_download": []},
                "top_referrers": {"by_view": [], "by_download": []},
                "top_affiliations": {"by_view": [], "by_download": []},
                "top_licenses": {"by_view": [], "by_download": []},
            },
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    def _create_aggregation_doc(
        self,
        community_id: str,
        date: arrow.Arrow,
        cumulative_totals: dict,
        cumulative_subcounts: dict,
    ) -> dict:
        """Create the final aggregation document from cumulative totals."""
        return {
            "community_id": community_id,
            "snapshot_date": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "totals": cumulative_totals,
            "subcounts": cumulative_subcounts,
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

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
            search = Search(using=self.client, index=self.event_index)
            search = search.query(Q("term", community_id=community_id))
            search = search.extra(size=0)
            search.aggs.bucket("max_date", "max", field="period_start")

            result = search.execute()
            if not result.aggregations.max_date.value:
                # No delta records exist at all, skip
                current_app.logger.info(
                    f"No usage delta records found for {community_id}, "
                    f"skipping snapshot aggregation"
                )
                return False

            # Use the latest delta record date as the bookmark
            delta_bookmark_date = arrow.get(
                result.aggregations.max_date.value_as_string
            )
        else:
            delta_bookmark_date = arrow.get(delta_bookmark)

        # Check if delta aggregator has processed up to our end_date
        if delta_bookmark_date < end_date:
            current_app.logger.info(
                f"Usage delta aggregator for {community_id} has not caught up yet. "
                f"Delta bookmark: {delta_bookmark_date}, "
                f"Snapshot end_date: {end_date}. Skipping snapshot aggregation."
            )
            return False

        return True

    def _should_skip_aggregation(
        self,
        start_date: arrow.Arrow,
        last_event_date: arrow.Arrow | None,
        period_delta_records: list,
        community_id: str | None = None,
        end_date: arrow.Arrow | None = None,
    ) -> bool:
        """Check if aggregation should be skipped due to no events with counts.

        Where the other aggregators skip if there are no events after the start date,
        this one skips if there are no events with counts between the start date and
        the last event date. If all the delta records are empty, the cumulative totals
        will not change.

        Args:
            start_date: The start date for aggregation
            last_event_date: The last event date, or None if no events exist
            period_delta_records: List of delta records for the period
            community_id: The community ID (optional, for dependency checking)
            end_date: The end date (optional, for dependency checking)

        Returns:
            True if aggregation should be skipped, False otherwise
        """
        # First check if usage delta aggregator has caught up
        if community_id and end_date:
            if not self._check_usage_delta_dependency(
                community_id, start_date, end_date
            ):
                return True

        total_events = sum(
            delta["totals"]["view"]["total_events"] for delta in period_delta_records
        )
        total_downloads = sum(
            delta["totals"]["download"]["total_events"]
            for delta in period_delta_records
        )
        if last_event_date is None:
            return True
        elif total_events == 0 and total_downloads == 0:
            return True
        elif last_event_date < start_date:
            return True
        return False

    def _get_daily_deltas(
        self, community_id: str, start_date: arrow.Arrow, end_date: arrow.Arrow
    ) -> tuple[list, list]:
        """Get daily delta records for a community between start and end dates.

        Also returns the daily delta records for the community before the start date
        so that we can use them to update the top subcounts.

        Returns:
            A tuple containing:
            - prior_daily_deltas: All daily delta records for the community before
                the start date
            - period_daily_deltas: Daily delta records for the community between
                start and end dates
        """
        search = Search(using=self.client, index=self.event_index)
        search = search.query(
            "bool",
            must=[
                Q("term", community_id=community_id),
                Q(
                    "range",
                    period_start={
                        "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                    },
                ),
            ],
        ).sort({"period_start": {"order": "asc"}})

        all_daily_deltas = sorted(list(search.scan()), key=lambda x: x.period_start)
        prior_daily_deltas = []
        period_daily_deltas = []
        split_index = 0
        for delta in all_daily_deltas:
            if arrow.get(delta.period_start) >= start_date.floor("day"):
                split_index = all_daily_deltas.index(delta)
                break
        prior_daily_deltas = all_daily_deltas[:split_index]
        period_daily_deltas = all_daily_deltas[split_index:]
        return prior_daily_deltas, period_daily_deltas

    def _map_delta_to_snapshot_subcounts(self, delta_doc: dict) -> dict:
        """Map delta document subcount field names to snapshot field names."""
        field_mapping = {
            "by_resource_types": "all_resource_types",
            "by_access_rights": "all_access_rights",
            "by_languages": "all_languages",
            "by_file_types": "all_file_types",
            "by_licenses": "top_licenses",
            "by_subjects": "top_subjects",
            "by_publishers": "top_publishers",
            "by_periodicals": "top_periodicals",
            "by_funders": "top_funders",
            "by_countries": "top_countries",
            "by_referrers": "top_referrers",
            "by_affiliations": "top_affiliations",
        }

        mapped_doc = delta_doc.copy()
        mapped_subcounts = {}

        for delta_field, delta_items in delta_doc.get("subcounts", {}).items():
            snapshot_field = field_mapping.get(delta_field)
            if snapshot_field:
                mapped_subcounts[snapshot_field] = delta_items

        mapped_doc["subcounts"] = mapped_subcounts
        return mapped_doc

    def _update_cumulative_totals(
        self,
        current_totals: dict,
        current_subcounts: dict,
        delta_doc: dict,
    ) -> tuple[dict, dict]:
        """Update cumulative totals with values from a daily delta document."""

        def update_totals(current_totals: dict, delta_totals: dict) -> Any:
            """Update cumulative totals with values from a daily delta document."""
            for key, value in delta_totals.items():
                if key in current_totals:
                    if isinstance(value, dict):
                        update_totals(current_totals[key], value)
                    elif isinstance(value, list):
                        # Handle lists by recursively processing each item
                        if not current_totals[key]:
                            current_totals[key] = []
                        for idx, item in enumerate(value):
                            matching_item = next(
                                (
                                    existing_item
                                    for existing_item in current_totals[key]
                                    if existing_item["id"] == item["id"]
                                ),
                                None,
                            )
                            if matching_item:
                                update_totals(matching_item, item)
                            else:
                                current_totals[key].append(item)
                    else:
                        # Sum all numeric values since these are daily deltas
                        if isinstance(current_totals[key], int) or isinstance(
                            current_totals[key], float
                        ):
                            current_totals[key] = current_totals[key] + value
                        else:
                            # Keep strings as is (id and label)
                            current_totals[key] = value
                else:
                    current_totals[key] = value

        counts_default = {
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

        if not current_totals:
            # Initialize totals from first delta
            current_totals = copy.deepcopy(counts_default)

        if not current_subcounts:
            # Initialize subcounts from first delta
            current_subcounts = {
                "all_resource_types": [],
                "all_access_rights": [],
                "all_languages": [],
                "all_file_types": [],
            }

        update_totals(current_totals, delta_doc["totals"])
        update_totals(
            current_subcounts,
            {
                "all_resource_types": (
                    delta_doc["subcounts"].get("all_resource_types", {})
                ),
                "all_access_rights": (
                    delta_doc["subcounts"].get("all_access_rights", {})
                ),
                "all_languages": delta_doc["subcounts"].get("all_languages", {}),
                "all_file_types": delta_doc["subcounts"].get("all_file_types", {}),
            },
        )

        return current_totals, current_subcounts

    def _update_top_subcounts(
        self,
        current_subcounts: dict,
        delta_records: list,
    ) -> dict:
        """Update top subcounts with values from a daily delta document.

        These are the subcounts that only include the top 10 values for each field.
        (E.g. top_subjects, top_publishers, etc.) We can't just add the new deltas
        to the current subcounts because the top 10 values for each field may have
        changed.

        We need to:
        - Sum the cumulative subcounts for the whole history of the community,
          including the new delta. E.g. for top_subjects, we need to sum the
          cumulative totals for *all* subjects from *all* daily usage deltas.
        - Sort the items in each subcount list by total sum
        - Take the items with the top 10 sums as the new list for each subcount

        Args:
            current_subcounts: The current subcounts to update.
            delta_records: The daily delta records to update the subcounts with.
                These are the daily delta records for the community between
                the community's inception (not the start date) and the end date.

        Returns:
            The updated top subcounts.
        """

        top_subcount_types = {
            "top_subjects": "by_subjects",
            "top_publishers": "by_publishers",
            "top_periodicals": "by_periodicals",
            "top_funders": "by_funders",
            "top_countries": "by_countries",
            "top_user_agents": "by_user_agents",
            "top_referrers": "by_referrers",
            "top_affiliations": "by_affiliations",
            "top_licenses": "by_licenses",
        }

        all_subcount_totals = {}
        for delta in delta_records:
            for subcount_type in top_subcount_types:
                mapped_type = top_subcount_types[subcount_type]
                if mapped_type not in delta["subcounts"]:
                    continue
                for delta_item in delta["subcounts"].get(mapped_type, []):
                    # delta_item is an opensearchpy.helpers.utils.AttrDict
                    delta_item = delta_item.to_dict()
                    updated_item = all_subcount_totals.get(subcount_type, {}).get(
                        delta_item["id"], {}
                    )
                    updated_item["id"] = delta_item["id"]
                    updated_item["label"] = delta_item["label"]

                    for scope in ["view", "download"]:
                        for stat_label, stat_value in delta_item[scope].items():
                            updated_item.setdefault(scope, {})[stat_label] = (
                                updated_item.get(scope, {}).get(stat_label, 0)
                                + stat_value
                            )
                    all_subcount_totals.setdefault(subcount_type, {})[
                        delta_item["id"]
                    ] = updated_item

        # Now sort and assign top subcounts after processing all deltas
        for subcount_type in top_subcount_types:
            if subcount_type in all_subcount_totals:
                sorted_by_views = sorted(
                    all_subcount_totals[subcount_type].values(),
                    key=lambda x: x["view"]["total_events"],
                    reverse=True,
                )[:10]
                sorted_by_downloads = sorted(
                    all_subcount_totals[subcount_type].values(),
                    key=lambda x: x["download"]["total_events"],
                    reverse=True,
                )[:10]
                subcount = {
                    "by_view": [v_item for v_item in sorted_by_views],
                    "by_download": [d_item for d_item in sorted_by_downloads],
                }
                current_subcounts[subcount_type] = subcount

        return current_subcounts

    def _get_last_snapshot_document(self, community_id: str, start_date: arrow.Arrow):
        """Get the last snapshot document for a community."""
        last_snapshot_document = None
        if self.client.indices.exists(self.aggregation_index):
            last_snapshot_search = (
                Search(using=self.client, index=self.aggregation_index)
                .query(
                    Q(
                        "bool",
                        must=[
                            Q("term", community_id=community_id),
                            Q(
                                "range",
                                snapshot_date={
                                    "lt": (
                                        start_date.floor("day").format(
                                            "YYYY-MM-DDTHH:mm:ss"
                                        )
                                    )
                                },
                            ),
                        ],
                    ),
                )
                .sort({"snapshot_date": {"order": "desc"}})
                .extra(size=1)
            )  # fetch one document only
            last_snapshot_results = last_snapshot_search.execute()
            if last_snapshot_results.hits.hits:
                last_snapshot_document = last_snapshot_results.hits.hits[0]
                last_snapshot_document = last_snapshot_document.to_dict()
        return last_snapshot_document

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[dict, None, None]:
        """Create cumulative totals from daily usage deltas."""
        self.client.indices.refresh(index="*stats-community-usage-delta*")
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)

        # Find the last snapshot document for the community
        # to continue cumulative totals -- if there's a gap between the last
        # snapshot date and the start date, we need to start from the last
        # snapshot date.
        last_snapshot_document = self._get_last_snapshot_document(
            community_id, start_date
        )
        last_snapshot_date = (
            arrow.get(last_snapshot_document["_source"]["snapshot_date"])
            if last_snapshot_document
            else None
        )
        current_app.logger.error(f"Last snapshot date: {pformat(last_snapshot_date)}")
        current_app.logger.error(f"Start date: {pformat(start_date)}")
        if last_snapshot_date and last_snapshot_date < start_date.shift(days=-1):
            start_date = last_snapshot_date.shift(days=1)

        # If there's no last snapshot document, we need to start from the first
        # event date.
        elif not last_snapshot_document:
            current_app.logger.error(f"First event date: {pformat(first_event_date)}")
            if first_event_date:
                start_date = first_event_date
                current_app.logger.error(f"Start date: {pformat(start_date)}")
        # FIXME: We need to ensure there's no gap in the usage deltas before
        # we aggregate the snapshots on their basis

        # Ensure that we're not aggregating for too long a period
        # if we've adjusted the start date
        if (end_date - start_date).days > self.catchup_interval:
            end_date = start_date.shift(days=self.catchup_interval)
            current_app.logger.error(f"Adjusted end date: {pformat(end_date)}")

        prior_delta_records, period_delta_records = self._get_daily_deltas(
            community_id, start_date, end_date
        )

        # Check if we should skip aggregation due to no events since the last snapshot
        should_skip = self._should_skip_aggregation(
            start_date, last_event_date, period_delta_records, community_id, end_date
        )
        if should_skip:
            current_app.logger.error(
                f"Skipping usage snapshot aggregation for {community_id} - "
                f"no delta records with usage events after {start_date}"
            )
        else:
            current_app.logger.error(
                f"Prior delta records: {pformat(prior_delta_records)}"
            )
            current_app.logger.error(
                f"Period delta records: "
                f"{pformat([p.to_dict() for p in period_delta_records])}"
            )
            if not prior_delta_records and not period_delta_records:
                return

            # Initialize cumulative totals
            cumulative_totals, cumulative_subcounts = (
                (
                    last_snapshot_document["_source"]["totals"],
                    last_snapshot_document["_source"]["subcounts"],
                )
                if last_snapshot_document
                else ({}, {})
            )
            current_app.logger.error(f"end date: {pformat(end_date)}")
            current_app.logger.error(f"Current iteration date: {pformat(start_date)}")
            current_app.logger.error(f"cumulative totals: {pformat(cumulative_totals)}")
            current_app.logger.error(
                f"cumulative subcounts: {pformat(cumulative_subcounts)}"
            )
            if period_delta_records and len(period_delta_records) > 0:
                current_app.logger.error(
                    f"First period delta record: "
                    f"{pformat(period_delta_records[0].to_dict())}"
                )

        current_delta_index = 0
        current_iteration_date = arrow.get(start_date)
        current_app.logger.error(
            f"Current iteration date: {pformat(current_iteration_date)}"
        )
        current_app.logger.error(f"Current delta index: {pformat(current_delta_index)}")

        while current_iteration_date <= end_date:
            if should_skip:
                # When skipping, create snapshots with the same values as the last
                # snapshot (or zero if no last snapshot) for each day in the period
                if last_snapshot_document:
                    # Copy the last snapshot document but update the snapshot_date
                    source_content = last_snapshot_document["_source"].copy()
                    source_content["snapshot_date"] = current_iteration_date.ceil(
                        "day"
                    ).format("YYYY-MM-DDTHH:mm:ss")
                    source_content["timestamp"] = arrow.utcnow().format(
                        "YYYY-MM-DDTHH:mm:ss"
                    )
                else:
                    # No previous snapshot, create zero-value document
                    source_content = self._create_zero_document(
                        community_id, current_iteration_date
                    )
            elif current_delta_index >= len(period_delta_records):
                # No more delta records, create snapshot with current cumulative totals
                # NOTE: We're assuming that missing delta records have zero values.
                source_content = self._create_aggregation_doc(
                    community_id,
                    current_iteration_date,
                    cumulative_totals,
                    cumulative_subcounts,
                )
            else:
                # Check if the current delta record is for today
                current_delta = period_delta_records[current_delta_index]
                delta_date = arrow.get(current_delta.period_start)
                current_app.logger.error(f"Delta date: {pformat(delta_date)}")

                if delta_date.floor("day") == current_iteration_date.floor("day"):
                    current_app.logger.error(
                        f"Updating cumulative totals for "
                        f"{current_iteration_date.format('YYYY-MM-DD')}"
                    )
                    # Map delta document to snapshot format before updating
                    mapped_delta_doc = self._map_delta_to_snapshot_subcounts(
                        current_delta.to_dict()
                    )
                    cumulative_totals, cumulative_subcounts = (
                        self._update_cumulative_totals(
                            cumulative_totals, cumulative_subcounts, mapped_delta_doc
                        )
                    )
                    all_delta_records = list(prior_delta_records) + list(
                        period_delta_records[: current_delta_index + 1]
                    )
                    cumulative_subcounts = self._update_top_subcounts(
                        cumulative_subcounts,
                        all_delta_records,
                    )
                    current_delta_index += 1
                elif delta_date.floor("day") < current_iteration_date.floor("day"):
                    # Delta is from a previous day, skip ahead to the next delta
                    current_delta_index += 1
                    continue
                else:
                    # Delta is from a future day, create snapshot with current
                    # cumulative totals
                    pass

                source_content = self._create_aggregation_doc(
                    community_id,
                    current_iteration_date,
                    cumulative_totals,
                    cumulative_subcounts,
                )

            # Create and yield the snapshot document for the current day
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

            current_iteration_date = current_iteration_date.shift(days=1)


class CommunityUsageDeltaAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index: list[tuple[str, str]] = [
            ("view", prefix_index("events-stats-record-view")),
            ("download", prefix_index("events-stats-file-download")),
        ]
        self.aggregation_index = prefix_index("stats-community-usage-delta")
        self.event_date_field = "timestamp"
        self.event_community_query_term = lambda community_id: Q("match_all")

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
                # Get all record IDs from events in this date range
                record_search = Search(using=self.client, index=event_index)
                record_search = record_search.filter(
                    "range",
                    timestamp={
                        "gte": start_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                        "lte": start_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                    },
                )
                record_search.aggs.bucket(
                    "by_record", "terms", field="recid", size=1000
                )
                record_results = record_search.execute()

                if not record_results.aggregations.by_record.buckets:
                    continue

                # Check if any of these records are in the community on this date
                record_ids = [
                    bucket.key
                    for bucket in record_results.aggregations.by_record.buckets
                ]
                community_search = (
                    Search(
                        using=self.client, index=prefix_index("stats-community-events")
                    )
                    .filter("term", community_id=community_id)
                    .filter("terms", record_id=record_ids)
                    .filter(
                        "range",
                        event_date={
                            "lte": start_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                        },
                    )
                )

                # Add terms aggregation to get unique records
                record_agg = community_search.aggs.bucket(
                    "by_record", "terms", field="record_id"
                )
                record_agg.bucket(
                    "top_hits",
                    "top_hits",
                    size=1,
                    sort=[{"event_date": {"order": "desc"}}],
                    _source={"includes": ["event_type"]},
                )

                community_results = community_search.execute()

                # Check if any records have "added" as their last event type
                for bucket in community_results.aggregations.by_record.buckets:
                    if bucket.top_hits.hits[0]["event_type"] == "added":
                        # Found at least one record with usage events in the community
                        events_found = True
                        break

                # No records with usage events found in community
                continue
            else:
                # For global aggregator, just check if there are any events at all
                if search.count() > 0:
                    events_found = True
                    break

        return not events_found

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> dict:
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
                "by_access_rights": [],
                "by_resource_types": [],
                "by_licenses": [],
                "by_funders": [],
                "by_periodicals": [],
                "by_languages": [],
                "by_subjects": [],
                "by_publishers": [],
                "by_affiliations": [],
                "by_countries": [],
                "by_referrers": [],
                "by_file_types": [],
            },
        }

    def _create_temp_index(self, temp_index: str) -> None:
        """Create temporary index with appropriate mappings."""
        self.client.indices.create(
            index=temp_index,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "record_id": {"type": "keyword"},
                        "parent_record_id": {"type": "keyword"},
                        "community_id": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "via_api": {"type": "boolean"},
                        "is_robot": {"type": "boolean"},
                        "visitor_id": {"type": "keyword"},
                        "event_type": {"type": "keyword"},
                        "size": {"type": "long"},
                        "file_key": {"type": "keyword"},
                        "file_id": {"type": "keyword"},
                        "file_type": {"type": "keyword"},
                        "country": {"type": "keyword"},
                        "referrer": {"type": "keyword"},
                        "resource_type": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "publisher": {"type": "keyword"},
                        "access_rights": {"type": "keyword"},
                        "languages": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "subjects": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "licenses": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "affiliations": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "name": {"type": "keyword"},
                                "identifiers": {"type": "keyword"},
                            },
                        },
                        "funders": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "periodical": {"type": "keyword"},
                    }
                },
            },
            ignore=400,
        )

    def _process_event_type(
        self,
        temp_index: str,
        community_id: str,
        date: arrow.Arrow,
        event_type: str,
        event_index: str,
    ) -> None:
        """Process events of a specific type for a given date using aggregations.

        Page through the indexed events grouped by record id and enrich the results
        with metadata about the record involved in the event. (The grouping allows us
        to retrieve record metadata in batches and only once per record.) We then
        create a new document in the temporary index for each event with its enriched
        metadata.

        If the community_id is "global", we will process all events in the event
        index without restricting by community. Restriction by community is performed
        when we search for the record metadata matching the event's record id, since
        the record's communities are not stored in the event index.

        Parameters:
        - temp_index: The name of the temporary index to use for the enriched documents
        - community_id: The ID of the community to process events for or "global".
        - date: The date to process events for
        - event_type: The type of event to process
        - event_index: The name of the index to search for events

        Returns:
        - None
        """
        page = 0
        search_after = None

        # Sliding window cache for metadata in case of page edge overlaps
        metadata_cache = {}
        search_page_size = 1000
        max_cache_size = search_page_size + 1  # Only need +1 for edge case records

        while True:
            current_app.logger.error(
                f"Processing page {page} for {event_type} on "
                f"{date.format('YYYY-MM-DD')}"
            )

            search = Search(using=self.client, index=event_index)
            search = search.filter(
                "range",
                timestamp={
                    "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )

            if search_after:
                search = search.extra(search_after=search_after)

            search = search.extra(size=search_page_size)
            # Sort by record_id first to minimize cross-page duplicates
            search = search.sort("recid", "timestamp")

            current_app.logger.error(
                f"Event search found {search.count()} events for {event_type} on "
                f"{date.format('YYYY-MM-DD')}"
            )

            response = search.execute()
            hits = response.hits.hits

            if not hits:
                current_app.logger.info(
                    f"No more hits found for {event_type} on "
                    f"{date.format('YYYY-MM-DD')}"
                )
                break

            current_app.logger.error(f"Found {len(hits)} hits on page {page}")

            # Group hits by record ID
            hits_by_recid = defaultdict(list)
            for hit in hits:
                hits_by_recid[hit["_source"]["recid"]].append(hit["_source"])

            # Get unique record IDs from this page
            record_ids = set(hits_by_recid.keys())
            current_app.logger.error(f"Record IDs: {pformat(record_ids)}")

            # Filter records in the community on the date
            current_app.logger.error(f"About to filter for community {community_id}")
            if community_id != "global":
                record_ids = self._filter_for_community(record_ids, community_id, date)

            # Find record IDs that we haven't cached metadata for yet
            new_record_ids = record_ids - set(metadata_cache.keys())
            if new_record_ids:
                # Fetch metadata only for new record IDs
                new_metadata = self._get_metadata_for_records(
                    community_id, new_record_ids, date, page_size=search_page_size
                )
                # Add to cache
                metadata_cache.update(new_metadata)

                # Implement sliding window cache
                if len(metadata_cache) > max_cache_size:
                    # Remove oldest entries (simple FIFO approach)
                    # In practice, with record_id sorting, this should rarely happen
                    # as records from the same ID should be grouped together
                    excess = len(metadata_cache) - max_cache_size
                    oldest_keys = list(metadata_cache.keys())[:excess]
                    for key in oldest_keys:
                        del metadata_cache[key]
                    current_app.logger.error(
                        f"Cache limit reached. Removed {excess} oldest entries."
                    )

                current_app.logger.error(
                    f"Fetched metadata for {len(new_record_ids)} new records. "
                    f"Cache now contains {len(metadata_cache)} records."
                )

            # Filter to only records that have metadata
            record_ids_with_metadata = {i for i in record_ids if i in metadata_cache}
            current_app.logger.error(
                f"Record IDs with metadata: {pformat(record_ids_with_metadata)}"
            )

            if len(record_ids_with_metadata):
                docs = self._create_enriched_docs_from_aggs(
                    record_ids_with_metadata,
                    metadata_cache,  # Use the global cache directly
                    temp_index,
                    community_id,
                    event_type,
                    hits_by_recid,
                )

                if docs:
                    bulk(self.client, docs)
                    current_app.logger.error(f"Bulk indexed {len(docs)} documents")
                    # Force a refresh to make the documents searchable
                    self.client.indices.refresh(index=temp_index)

            # Update search_after for next page
            if len(hits) > 0:
                search_after = hits[-1]["sort"]
            else:
                break

            page += 1

    def _filter_for_community(
        self, record_ids: set[str], community_id: str, date: arrow.Arrow
    ) -> set[str]:
        """Filter record IDs to find those in the community on the date."""

        community_search = (
            Search(using=self.client, index=prefix_index("stats-community-events"))
            .filter(
                "term",
                community_id=community_id,
            )
            .filter("terms", record_id=list(record_ids))
            .filter(
                "range",
                event_date={
                    "lte": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )
        )

        # Add terms aggregation by record_id with top_hits sub-aggregation
        by_record_agg = community_search.aggs.bucket(
            "by_record", "terms", field="record_id"
        )
        by_record_agg.bucket(
            "top_hits",
            "top_hits",
            size=1,
            sort=[{"event_date": {"order": "desc"}}],
            _source={"includes": ["event_date", "event_type"]},
        )

        community_results = community_search.execute()

        # Find the records whose last event before the date was an "added" event
        community_record_ids = set()
        for bucket in community_results.aggregations.by_record.buckets:
            if bucket.top_hits.hits[0]["event_type"] == "added":
                community_record_ids.add(bucket.key)

        current_app.logger.error(
            f"Community record IDs: {pformat(community_record_ids)}"
        )
        return community_record_ids

    def _get_metadata_for_records(
        self,
        community_id: str,
        record_ids: set[str],
        date: arrow.Arrow,
        page_size: int = 1000,
    ) -> dict:
        """Get metadata for a set of record IDs."""
        meta_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        meta_search = meta_search.filter("terms", id=list(record_ids))
        meta_search = meta_search.source(
            [
                "access.status",
                "custom_fields.journal:journal.title.keyword",
                "files.types",
                "id",
                "metadata.resource_type.id",
                "metadata.resource_type.title.en",
                "metadata.languages.id",
                "metadata.languages.title.en",
                "metadata.subjects.id",
                "metadata.subjects.subject",
                "metadata.publisher",
                "metadata.rights.id",
                "metadata.rights.title.en",
                "metadata.creators.affiliations.id",
                "metadata.creators.affiliations.name.keyword",
                "metadata.contributors.affiliations.id",
                "metadata.contributors.affiliations.name.keyword",
                "metadata.funding.funder.id",
                "metadata.funding.funder.title.en",
                "parent.communities.ids",
            ]
        )
        meta_search = meta_search.extra(size=page_size)

        # NOTE: The search here should never exceed the page size from
        # _process_event_type() so we can use simple execute() instead of scan()
        # or pagination
        meta_hits = meta_search.execute().hits.hits
        results = {hit["_source"]["id"]: hit.to_dict()["_source"] for hit in meta_hits}
        return results

    def _create_enriched_docs_from_aggs(
        self,
        record_ids: set[str],
        meta_for_recids: dict,
        temp_index: str,
        community_id: str,
        event_type: str,
        hits_by_recid: dict[str, list],
    ) -> list:
        """Create enriched documents from aggregation buckets."""
        docs = []
        for recid in record_ids:
            meta = meta_for_recids.get(recid)
            if not meta:
                continue

            # Create one document per hit with the same recid
            for hit in hits_by_recid[recid]:
                doc = {
                    "_index": temp_index,
                    "_source": {
                        "record_id": recid,
                        "parent_record_id": hit["parent_recid"],
                        "community_id": community_id,
                        "timestamp": hit["timestamp"],
                        "via_api": hit["via_api"],
                        "is_robot": hit["is_robot"],
                        "visitor_id": hit["visitor_id"],
                        "event_type": event_type,
                        "resource_type": {
                            "id": meta["metadata"]["resource_type"]["id"],
                            "title": meta["metadata"]["resource_type"]["title"]["en"],
                        },
                        "publisher": meta["metadata"]["publisher"],
                        "access_rights": meta["access"]["status"],
                        "languages": [
                            {
                                "id": lang["id"],
                                "title": lang["title"]["en"],
                            }
                            for lang in meta["metadata"].get("languages", [])
                        ],
                        "subjects": [
                            {
                                "id": subject["id"],
                                "title": subject["subject"],
                            }
                            for subject in meta["metadata"].get("subjects", [])
                        ],
                        "licenses": [
                            {
                                "id": right["id"],
                                "title": right["title"]["en"],
                            }
                            for right in meta["metadata"].get("rights", [])
                        ],
                        "funders": [
                            {
                                "id": funder["id"],
                                "title": funder["title"]["en"],
                            }
                            for funder in meta["metadata"]
                            .get("funding", {})
                            .get("funder", [])
                        ],
                    },
                }

                for contributor in meta["metadata"].get("creators", []) + meta[
                    "metadata"
                ].get("contributors", []):
                    if contributor.get("affiliations"):
                        for affiliation in contributor.get("affiliations", []):
                            doc["_source"].setdefault("affiliations", []).append(
                                {
                                    "id": affiliation.get("id", ""),
                                    "name": affiliation.get("name", ""),
                                    "identifiers": affiliation.get("identifiers", []),
                                }
                            )

                if "custom_fields" in meta:
                    doc["_source"]["periodical"] = meta["custom_fields"].get(
                        "journal:journal.title.keyword", {}
                    )

                if event_type == "view":
                    file_types = meta.get("files", {}).get("types", [])
                    # Convert AttrList to regular list if needed
                    file_types = list(file_types)
                    doc["_source"]["file_type"] = file_types

                if event_type == "download":
                    doc["_source"]["referrer"] = hit["referrer"]
                    doc["_source"]["country"] = hit["country"]
                    doc["_source"]["size"] = hit["size"]
                    doc["_source"]["file_id"] = hit["file_id"]
                    doc["_source"]["file_type"] = [hit["file_key"].split(".")[-1]]

                docs.append(doc)
        return docs

    def _add_metrics_to_agg(self, agg_bucket, event_type):
        """Add common metrics to an aggregation bucket."""
        agg_bucket.metric(
            "unique_visitors",
            "cardinality",
            field="visitor_id",
        ).metric(
            "unique_records",
            "cardinality",
            field="record_id",
        ).metric(
            "unique_parents",
            "cardinality",
            field="parent_record_id",
        )

        # Only add file-related metrics for download events
        if event_type == "download":
            agg_bucket.metric(
                "unique_files",
                "cardinality",
                field="file_id",
            ).metric(
                "total_volume",
                "sum",
                field="size",
            )

        return agg_bucket

    def add_search_agg(
        self,
        agg_search: Search,
        agg_name: str,
        agg_field: str | None = None,
        title_field: str | list[str] | None = None,
        field_bucket: Bucket | None = None,
    ) -> Search:
        """Add a search aggregation to the search object."""
        # Create the field aggregation first
        if field_bucket is None:
            field_bucket = agg_search.aggs.bucket(
                agg_name,
                "terms",
                field=agg_field,
                size=1000,
            )

        # Add event type aggregation under each field value
        for event_type in ["view", "download"]:
            event_bucket = field_bucket.bucket(  # type: ignore
                event_type,
                "filter",
                term={"event_type": event_type},
            )

            # Add metrics to the event type bucket
            self._add_metrics_to_agg(event_bucket, event_type)

        # Add title field if specified
        if title_field:
            field_bucket.bucket(  # type: ignore
                "title",
                "top_hits",
                size=1,
                _source={"includes": title_field},
                sort=[{"_score": "desc"}],
            )

        return agg_search

    def _temp_index_search_query(
        self, temp_index: str, date: arrow.Arrow, community_id: str
    ) -> Search:
        """Create a search query for the temporary index."""
        agg_search = Search(using=self.client, index=temp_index)
        must_clauses = [
            Q(
                "range",
                timestamp={
                    "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )
        ]
        if community_id != "global":
            must_clauses.append(Q("term", community_id=community_id))

        agg_search = agg_search.query(Q("bool", must=must_clauses))
        current_app.logger.error(
            f"Counting {agg_search.count()} records in temp index {temp_index}"
            f" for community {community_id} on {date.format('YYYY-MM-DD')}"
        )

        self.add_search_agg(
            agg_search,
            "by_resource_types",
            "resource_type.id",
            ["resource_type.title", "resource_type.id"],
        )
        self.add_search_agg(agg_search, "by_access_rights", "access_rights", None)
        self.add_search_agg(
            agg_search,
            "by_languages",
            "languages.id",
            ["languages.title", "languages.id"],
        )
        self.add_search_agg(
            agg_search, "by_subjects", "subjects.id", ["subjects.title", "subjects.id"]
        )
        self.add_search_agg(
            agg_search, "by_licenses", "licenses.id", ["licenses.title", "licenses.id"]
        )
        self.add_search_agg(
            agg_search, "by_funders", "funders.id", ["funders.title", "funders.id"]
        )
        self.add_search_agg(agg_search, "by_periodicals", "periodical", None)
        self.add_search_agg(agg_search, "by_publishers", "publisher", None)
        self.add_search_agg(agg_search, "by_file_types", "file_type", None)
        self.add_search_agg(agg_search, "by_countries", "country", None)
        self.add_search_agg(agg_search, "by_referrers", "referrer", None)

        # Aggregate by affiliation
        affiliation_agg = agg_search.aggs.bucket(
            "by_affiliations",
            "composite",
            size=100,
            sources=[
                {"id": {"terms": {"field": "affiliations.id"}}},
                {"name": {"terms": {"field": "affiliations.name"}}},
            ],
        )
        self.add_search_agg(
            agg_search,
            "by_affiliations",
            agg_field=None,
            title_field=None,
            field_bucket=affiliation_agg,
        )

        # Add top-level metrics
        for event_type in ["view", "download"]:
            event_bucket = agg_search.aggs.bucket(
                event_type,
                "filter",
                term={"event_type": event_type},
            )

            # Add metrics to the event type bucket
            self._add_metrics_to_agg(event_bucket, event_type)

        return agg_search

    def _create_aggregation_doc(
        self, temp_index: str, community_id: str, date: arrow.Arrow
    ) -> dict:
        """Create the final aggregation document from the temporary index."""

        agg_search = self._temp_index_search_query(temp_index, date, community_id)
        results = agg_search.execute()

        # current_app.logger.error(
        #     f"Results: {pformat(results.aggregations.to_dict())}"
        # )

        # Get top-level metrics
        views_bucket = results.aggregations.view if results.aggregations.view else None
        downloads_bucket = (
            results.aggregations.download if results.aggregations.download else None
        )

        def add_subcount_to_doc(
            buckets: list, title_path: list | None | Callable = None
        ) -> list[dict]:
            """Add a subcount to the daily usage delta document."""
            subcount_list = []
            for bucket in buckets:
                field_value = bucket["key"]
                field_label = ""

                # Get title if available
                if title_path:
                    if callable(title_path):
                        field_label = title_path(bucket)
                    else:
                        title_hits = (
                            bucket.get("title", {}).get("hits", {}).get("hits", [])
                        )
                        if title_hits and title_hits[0].get("_source"):
                            source = title_hits[0]["_source"]
                            if (
                                0 in title_path
                                and title_path.index(0) != len(title_path) - 1
                            ):
                                pivot = title_path.index(0)
                                category_path, item_path = (
                                    title_path[:pivot],
                                    title_path[pivot + 1 :],  # noqa: E203
                                )
                                item = [
                                    i
                                    for i in self._get_nested_value(
                                        source, category_path
                                    )
                                    if i.get("id") == bucket.get("key")
                                ][0]
                                field_label = self._get_nested_value(item, item_path)
                            else:
                                field_label = self._get_nested_value(source, title_path)

                # Get metrics for each event type
                metrics = {}
                for event_type in ["view", "download"]:
                    if event_type in bucket:
                        event_bucket = bucket[event_type]
                        metrics[event_type] = {
                            "total_events": event_bucket["doc_count"],
                            "unique_visitors": event_bucket["unique_visitors"]["value"],
                            "unique_records": event_bucket["unique_records"]["value"],
                            "unique_parents": event_bucket["unique_parents"]["value"],
                        }
                        if event_type == "download":
                            metrics[event_type]["unique_files"] = event_bucket[
                                "unique_files"
                            ]["value"]
                            metrics[event_type]["total_volume"] = event_bucket[
                                "total_volume"
                            ]["value"]

                # Add to results
                subcount_list.append(
                    {
                        "id": (
                            field_value
                            if isinstance(field_value, str)
                            else field_value.id
                        ),
                        "label": field_label,
                        **metrics,
                    }
                )
            return subcount_list

        current_app.logger.error(
            f"period_start: {date.floor('day').format('YYYY-MM-DDTHH:mm:ss')}"
        )
        current_app.logger.error(
            f"period_end: {date.ceil('day').format('YYYY-MM-DDTHH:mm:ss')}"
        )

        final_dict = {
            "community_id": community_id,
            "period_start": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "totals": {
                "view": {
                    "total_events": views_bucket.doc_count if views_bucket else 0,
                    "unique_visitors": (
                        views_bucket.unique_visitors.value if views_bucket else 0
                    ),
                    "unique_records": (
                        views_bucket.unique_records.value if views_bucket else 0
                    ),
                    "unique_parents": (
                        views_bucket.unique_parents.value if views_bucket else 0
                    ),
                },
                "download": {
                    "total_events": (
                        downloads_bucket.doc_count if downloads_bucket else 0
                    ),
                    "unique_visitors": (
                        downloads_bucket.unique_visitors.value
                        if downloads_bucket
                        else 0
                    ),
                    "unique_records": (
                        downloads_bucket.unique_records.value if downloads_bucket else 0
                    ),
                    "unique_parents": (
                        downloads_bucket.unique_parents.value if downloads_bucket else 0
                    ),
                    "unique_files": (
                        downloads_bucket.unique_files.value if downloads_bucket else 0
                    ),
                    "total_volume": (
                        downloads_bucket.total_volume.value if downloads_bucket else 0
                    ),
                },
            },
            "subcounts": {
                "by_access_rights": add_subcount_to_doc(
                    results.aggregations.by_access_rights.buckets, None
                ),
                "by_resource_types": add_subcount_to_doc(
                    results.aggregations.by_resource_types.buckets,
                    ["resource_type", "title"],
                ),
                "by_licenses": add_subcount_to_doc(
                    results.aggregations.by_licenses.buckets,
                    ["licenses", 0, "title"],
                ),
                "by_funders": add_subcount_to_doc(
                    results.aggregations.by_funders.buckets,
                    ["funders", 0, "title"],
                ),
                "by_periodicals": add_subcount_to_doc(
                    results.aggregations.by_periodicals.buckets
                ),
                "by_languages": add_subcount_to_doc(
                    results.aggregations.by_languages.buckets,
                    [
                        "languages",
                        0,
                        "title",
                    ],  # SUBCOUNT_TYPES["language"][1].split("."),
                ),
                "by_subjects": add_subcount_to_doc(
                    results.aggregations.by_subjects.buckets,
                    ["subjects", 0, "title"],
                ),
                "by_publishers": add_subcount_to_doc(
                    results.aggregations.by_publishers.buckets
                ),
                "by_affiliations": add_subcount_to_doc(
                    results.aggregations.by_affiliations.buckets,
                    lambda aff_bucket: aff_bucket.get("key", {}).get("name"),
                ),
                "by_countries": add_subcount_to_doc(
                    results.aggregations.by_countries.buckets, None
                ),
                "by_referrers": add_subcount_to_doc(
                    results.aggregations.by_referrers.buckets
                ),
                "by_file_types": add_subcount_to_doc(
                    results.aggregations.by_file_types.buckets,
                ),
            },
        }

        return final_dict

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
            current_app.logger.error(
                f"Skipping usage delta aggregation for {community_id} - "
                f"no events after {start_date}"
            )

        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)

        if not should_skip:
            temp_index = prefix_index(
                f"temp-usage-stats-{community_id}-"
                f"{arrow.utcnow().format('YYYY-MM-DD-HH-mm-ss')}"
            )

            # Clean up any existing temporary indices for this community
            existing_indices = self.client.indices.get_alias(
                prefix_index(f"temp-usage-stats-{community_id}-*")
            )
            for index_name in existing_indices:
                self.client.indices.delete(index=index_name, ignore=[400, 404])

            self._create_temp_index(temp_index)

        current_iteration_date = start_date

        try:
            while current_iteration_date <= end_date:
                # Prepare the _source content based on whether we should skip
                # aggregation
                if should_skip:
                    source_content = self._create_zero_document(
                        community_id, current_iteration_date
                    )
                else:
                    current_app.logger.error(
                        f"Processing date: {current_iteration_date} for community "
                        f"{community_id}"
                    )
                    for event_type, event_index in self.event_index:
                        self._process_event_type(
                            temp_index,
                            community_id,
                            current_iteration_date,
                            event_type,
                            event_index,
                        )

                    source_content = self._create_aggregation_doc(
                        temp_index, community_id, current_iteration_date
                    )

                index_name = prefix_index(
                    "{0}-{1}".format(
                        self.aggregation_index, current_iteration_date.year
                    )
                )
                doc_id = f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
                if self.client.exists(index=index_name, id=doc_id):
                    self.delete_aggregation(index_name, doc_id)

                yield {
                    "_id": doc_id,
                    "_index": index_name,
                    "_source": source_content,
                }
                current_app.logger.error(
                    f"Yielding doc for index: {index_name} with id: {doc_id}"
                )

                current_iteration_date = current_iteration_date.shift(days=1)

        finally:
            # Clean up temporary index if it was created
            if not should_skip:
                self.client.indices.delete(temp_index, ignore=[400, 404])


class CommunityRecordsDeltaCreatedAggregator(CommunityAggregatorBase):
    """Aggregator for community record deltas.

    Uses the date the record was created as the initial date of the record.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-records-delta-created")

    def _should_skip_aggregation(
        self,
        start_date: arrow.Arrow,
        last_event_date: arrow.Arrow | None,
        community_id: str | None = None,
    ) -> bool:
        """Check if aggregation should be skipped due to no relevant records in date range.

        This method provides early skip logic for record delta aggregators by:
        1. Checking if there are any records that were added to the community before or on the aggregation date
        2. If no relevant records exist, we can skip the expensive processing pipeline entirely

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

        # For record delta aggregators, we need to check if there are any records
        # that were added to the community before or on the aggregation date
        if community_id == "global":
            # For global aggregator, just check if there are any records at all
            search = Search(using=self.client, index=self.event_index)
            return search.count() == 0
        else:
            # For community-specific aggregators, check if any records were added
            # to the community before or on the aggregation date
            community_search = (
                Search(using=self.client, index=prefix_index("stats-community-events"))
                .filter("term", community_id=community_id)
                .filter(
                    "range",
                    event_date={
                        "lte": start_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                    },
                )
            )

            # Add terms aggregation to get unique records
            record_agg = community_search.aggs.bucket(
                "by_record", "terms", field="record_id"
            )
            record_agg.bucket(
                "top_hits",
                "top_hits",
                size=1,
                sort=[{"event_date": {"order": "desc"}}],
                _source={"includes": ["event_type"]},
            )

            community_results = community_search.execute()

            # Check if any records have "added" as their last event type
            for bucket in community_results.aggregations.by_record.buckets:
                if bucket.top_hits.hits[0]["event_type"] == "added":
                    # Found at least one record that was added to the community
                    return False

            # No records found that were added to the community before the aggregation date
            return True

    def _create_zero_document(
        self, community_id: str, current_day: arrow.Arrow
    ) -> dict:
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
                "by_resource_type": [],
                "by_access_rights": [],
                "by_language": [],
                "by_affiliation_creator": [],
                "by_affiliation_contributor": [],
                "by_funder": [],
                "by_subject": [],
                "by_publisher": [],
                "by_periodical": [],
                "by_license": [],
                "by_file_type": [],
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    def create_agg_dict(
        self,
        community_id: str,
        current_day: arrow.Arrow,
        aggs_added: dict,
        aggs_removed: dict,
    ) -> dict:
        """Create a dictionary representing the aggregation result for indexing."""

        def make_file_type_dict():
            combined_keys = list(
                set(
                    b["key"]
                    for b in aggs_added.get("by_file_type", {}).get("buckets", [])
                    if b["key"] != "doc_count"
                )
                | set(
                    b["key"]
                    for b in aggs_removed.get("by_file_type", {}).get("buckets", [])
                    if b["key"] != "doc_count"
                )
            )
            file_type_list = []
            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        aggs_added.get("by_file_type", {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        aggs_removed.get("by_file_type", {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                file_type_list.append(
                    {
                        "id": key,
                        "label": "",
                        "added": {
                            "records": added.get("unique_records", {}).get("value", 0),
                            "parents": added.get("unique_parents", {}).get("value", 0),
                            "files": added.get("doc_count", 0),
                            "data_volume": added.get("total_bytes", {}).get("value", 0),
                        },
                        "removed": {
                            "records": (
                                removed.get("unique_records", {}).get("value", 0)
                            ),
                            "parents": (
                                removed.get("unique_parents", {}).get("value", 0)
                            ),
                            "files": removed.get("doc_count", 0),
                            "data_volume": (
                                removed.get("total_bytes", {}).get("value", 0)
                            ),
                        },
                    }
                )
            return file_type_list

        def find_item_label(added, removed, subcount_def, key):
            label = ""

            if len(subcount_def) > 1:
                label_item = added if added else removed
                label_field = subcount_def[1]
                source_path = ["label", "hits", "hits", 0, "_source"]
                label_path_stem = source_path + label_field.split(".")[:2]
                label_path_leaf = label_field.split(".")[2:]

                # We need to find the specific item that matches the key
                # Because the non-nested top-hits agg returns all items
                label_options = self._get_nested_value(label_item, label_path_stem)

                if isinstance(label_options, list) and len(label_options) > 0:
                    matching_option = next(
                        (
                            label_option
                            for label_option in label_options
                            if label_option.get("id") == key
                        ),
                        None,
                    )
                    if matching_option:
                        # Extract the label field directly from the matched object
                        if len(label_path_leaf) == 1:
                            label = matching_option.get(label_path_leaf[0], "")
                        else:
                            # For nested paths, use _get_nested_value
                            label = self._get_nested_value(
                                matching_option, label_path_leaf, key=key
                            )
                elif isinstance(label_options, dict):
                    label = self._get_nested_value(
                        label_options, label_path_leaf, key=key
                    )
            # Convert empty dict to empty string for consistency
            if isinstance(label, dict) and not label:
                label = ""
            return label

        def make_subcount_list(subcount_type):
            if subcount_type in [
                "by_affiliation_creator",
                "by_affiliation_contributor",
            ]:
                added_items = aggs_added.get(f"{subcount_type}_id", {}).get(
                    "buckets", []
                ) + aggs_added.get(f"{subcount_type}_name", {}).get("buckets", [])
                removed_items = aggs_removed.get(f"{subcount_type}_id", {}).get(
                    "buckets", []
                ) + aggs_removed.get(f"{subcount_type}_name", {}).get("buckets", [])
            else:
                added_items = aggs_added.get(subcount_type, {}).get("buckets", [])
                removed_items = aggs_removed.get(subcount_type, {}).get("buckets", [])

            combined_keys = list(
                set(b["key"] for b in added_items)
                | set(b["key"] for b in removed_items)
            )
            subcount_list = []
            for key in combined_keys:
                added_filtered = list(filter(lambda x: x["key"] == key, added_items))
                added = added_filtered[0] if added_filtered else {}
                removed_filtered = list(
                    filter(lambda x: x["key"] == key, removed_items)
                )
                removed = removed_filtered[0] if removed_filtered else {}
                label = find_item_label(
                    added, removed, SUBCOUNT_TYPES[subcount_type[3:]], key
                )
                subcount_list.append(
                    {
                        "id": key,
                        "label": label,
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
                                "file_count": (
                                    added.get("file_count", {}).get("value", 0)
                                ),
                                "data_volume": (
                                    added.get("total_bytes", {}).get("value", 0)
                                ),
                            },
                            "removed": {
                                "file_count": (
                                    removed.get("file_count", {}).get("value", 0)
                                ),
                                "data_volume": (
                                    removed.get("total_bytes", {}).get("value", 0)
                                ),
                            },
                        },
                    }
                )
            return subcount_list

        agg_dict = {
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
                    "data_volume": aggs_added.get("total_bytes", {}).get("value", 0),
                },
                "removed": {
                    "file_count": aggs_removed.get("file_count", {}).get("value", 0),
                    "data_volume": aggs_removed.get("total_bytes", {}).get("value", 0),
                },
            },
            "uploaders": aggs_added.get("uploaders", {}).get("value", 0),
            "subcounts": {
                "by_resource_type": make_subcount_list("by_resource_type"),
                "by_access_rights": make_subcount_list("by_access_rights"),
                "by_language": make_subcount_list("by_language"),
                "by_affiliation_creator": make_subcount_list("by_affiliation_creator"),
                "by_affiliation_contributor": make_subcount_list(
                    "by_affiliation_contributor"
                ),
                "by_funder": make_subcount_list("by_funder"),
                "by_subject": make_subcount_list("by_subject"),
                "by_publisher": make_subcount_list("by_publisher"),
                "by_periodical": make_subcount_list("by_periodical"),
                "by_license": make_subcount_list("by_license"),
                "by_file_type": make_file_type_dict(),
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }
        # current_app.logger.error(f"Agg dict: {pformat(agg_dict)}")
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
        should_skip = self._should_skip_aggregation(
            start_date, last_event_date, community_id
        )
        if should_skip:
            current_app.logger.error(
                f"Skipping delta aggregation for {community_id} - "
                f"no relevant records after {start_date}"
            )

        # Divide the search into years
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)
        for year in range(start_date.year, end_date.year + 1):
            year_start_date = max(arrow.get(f"{year}-01-01"), start_date)
            year_end_date = min(arrow.get(f"{year}-12-31"), end_date)

            index_name = prefix_index("{0}-{1}".format(self.aggregation_index, year))

            for day in arrow.Arrow.range("day", year_start_date, year_end_date):
                day_start_date = day.floor("day")

                # Prepare the _source content based on whether we should skip
                # aggregation
                if should_skip:
                    source_content = self._create_zero_document(
                        community_id, day_start_date
                    )
                else:
                    day_end_date = day.ceil("day")

                    year_search_added = Search(
                        using=self.client, index=self.event_index
                    )
                    year_search_added.update_from_dict(
                        daily_record_delta_query_with_events(
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
                            client=self.client,
                        )
                    )

                    day_results_added = year_search_added.execute()
                    aggs_added = day_results_added.aggregations.to_dict()

                    day_search_removed = Search(
                        using=self.client, index=self.event_index
                    )
                    day_search_removed.update_from_dict(
                        daily_record_delta_query_with_events(
                            day_start_date.format("YYYY-MM-DDTHH:mm:ss"),
                            day_end_date.format("YYYY-MM-DDTHH:mm:ss"),
                            community_id=community_id,
                            find_deleted=True,
                            client=self.client,
                        )
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


class CommunityRecordsDeltaAddedAggregator(CommunityRecordsDeltaCreatedAggregator):
    """Aggregator for community records delta added."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-delta-added")


class CommunityRecordsDeltaPublishedAggregator(CommunityRecordsDeltaCreatedAggregator):
    """Aggregator for community records delta published."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-delta-published")


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
