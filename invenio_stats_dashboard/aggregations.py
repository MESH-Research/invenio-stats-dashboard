import copy
import datetime
import time
from collections.abc import Generator
from functools import wraps
from pprint import pformat
from typing import Any, Callable

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.aggregations import StatAggregator
from invenio_stats.bookmark import BookmarkAPI
from opensearchpy import AttrDict, AttrList
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from .exceptions import CommunityEventIndexingError
from .proxies import current_community_stats_service
from .queries import (
    CommunityRecordDeltaQuery,
    CommunityRecordSnapshotQuery,
    CommunityUsageDeltaQuery,
    CommunityUsageSnapshotQuery,
)

SUBCOUNT_TYPES = {
    "resource_type": [
        "metadata.resource_type.id",
        "metadata.resource_type.title.en",
    ],
    "access_status": ["access.status"],
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
    "rights": ["metadata.rights.id", "metadata.rights.title.en"],
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
        # Field name for searching community event indices - overridden by subclasses
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
            for _, index in self.event_index:
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

            # upper_limit could legitimately be < lower_limit if we spent this iteration
            # indexing prior community add/remove events. If so, skip this community
            # iteration without updating the bookmark or performing aggregations
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
        1. Checking if there are any records that were added to the community before or
           on the aggregation date
        2. If no relevant records exist, we can skip the expensive processing pipeline
           entirely

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
                "all_access_status": [],
                "all_languages": [],
                "top_affiliations_creator": [],
                "top_affiliations_contributor": [],
                "top_funders": [],
                "top_subjects": [],
                "top_publishers": [],
                "top_periodicals": [],
                "all_rights": [],
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
                "by_affiliations_creator",
                "by_affiliations_contributor",
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
                "all_access_status": make_subcount_dict("by_access_status"),
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
                "all_rights": make_subcount_dict("by_rights"),
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
                query_builder = CommunityRecordSnapshotQuery(
                    client=self.client, event_index=self.event_index
                )

                snapshot_query_added = query_builder.build_query(
                    earliest_date.format("YYYY-MM-DD"),
                    current_iteration_date.format("YYYY-MM-DD"),
                    community_id=community_id,
                    use_included_dates=self.use_included_dates,
                    use_published_dates=self.use_published_dates,
                    client=self.client,
                )
                snapshot_results_added = snapshot_query_added.execute()
                aggs_added = snapshot_results_added.aggregations.to_dict()

                snapshot_query_removed = query_builder.build_query(
                    earliest_date.format("YYYY-MM-DD"),
                    current_iteration_date.format("YYYY-MM-DD"),
                    community_id=community_id,
                    find_deleted=True,
                    use_included_dates=self.use_included_dates,
                    use_published_dates=self.use_published_dates,
                    client=self.client,
                )
                snapshot_results_removed = snapshot_query_removed.execute()
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
    """Aggregator for creating cumulative usage snapshots from daily delta documents."""

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # Use provided configs or fall back to class default
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
        )
        self.event_index = prefix_index("stats-community-usage-delta")
        self.aggregation_index = prefix_index("stats-community-usage-snapshot")
        self.event_date_field = "period_start"
        self.event_community_query_term = lambda community_id: Q(
            "term", community_id=community_id
        )
        self.query_builder = CommunityUsageSnapshotQuery(client=self.client)

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
            "subcounts": self._initialize_subcounts_structure(),
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
            search = self.query_builder.build_dependency_check_query(community_id)
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
        search = self.query_builder.build_daily_deltas_query(community_id, end_date)

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
        """Map delta document subcount field names to snapshot field names.

        This transforms the enriched aggregation field names (e.g., 'by_resource_types')
        to the snapshot field names (e.g., 'all_resource_types') for consistent
        processing throughout the aggregator.
        """
        mapped_doc = delta_doc.copy()
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
                    snapshot_field = (
                        f"{snapshot_type}_{subcount_name.replace('by_', '')}"
                    )
                    mapped_subcounts[snapshot_field] = delta_items
                    break

        mapped_doc["subcounts"] = mapped_subcounts
        return mapped_doc

    def _update_cumulative_totals(
        self,
        current_totals: dict,
        current_subcounts: dict,
        delta_doc: dict,
    ) -> tuple[dict, dict]:
        """Update cumulative totals with values from enriched daily delta documents."""

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
            # Initialize subcounts from first delta using configuration
            current_subcounts = {}
            # Get all unique subcount configurations from the central config
            seen_configs = set()
            for subcount_name, config in self.subcount_configs.items():
                usage_config = config.get("usage_events", {})
                if not usage_config:
                    continue

                snapshot_type = usage_config.get("snapshot_type", "all")
                snapshot_field = f"{snapshot_type}_{subcount_name.replace('by_', '')}"

                if snapshot_type == "all":
                    current_subcounts[snapshot_field] = []
                elif snapshot_type == "top":
                    current_subcounts[snapshot_field] = {
                        "by_view": [],
                        "by_download": [],
                    }

        update_totals(current_totals, delta_doc["totals"])

        # Update simple subcounts from mapped delta document
        # The mapping has already transformed field names to snapshot format
        update_totals(current_subcounts, delta_doc["subcounts"])

        return current_totals, current_subcounts

    def _update_top_subcounts(
        self,
        current_subcounts: dict,
        delta_records: list,
    ) -> dict:
        """Update top subcounts with full recalculation from all delta documents.

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

        # Get top metrics from configuration
        top_subcount_types = []
        for subcount_name, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Use snapshot_type to determine if this is a top subcount
            snapshot_type = usage_config.get("snapshot_type", "all")
            if snapshot_type == "top":
                delta_field = usage_config.get("delta_aggregation_name")
                if delta_field:
                    snapshot_field = (
                        f"{snapshot_type}_{subcount_name.replace('by_', '')}"
                    )
                    top_subcount_types.append(snapshot_field)

        all_subcount_totals = {}

        # Process all delta records to build cumulative totals
        for delta in delta_records:
            delta_dict = delta.to_dict() if hasattr(delta, "to_dict") else delta

            for subcount_type in top_subcount_types:
                # The delta document should already have mapped field names
                if subcount_type not in delta_dict.get("subcounts", {}):
                    continue

                # Process each bucket in the aggregation
                for bucket in delta_dict["subcounts"][subcount_type].get("buckets", []):
                    bucket_dict = (
                        bucket.to_dict() if hasattr(bucket, "to_dict") else bucket
                    )

                    # Extract the key (ID) and metrics
                    item_id = bucket_dict.get("key")
                    if not item_id:
                        continue

                    # Get or create the item in our cumulative totals
                    if subcount_type not in all_subcount_totals:
                        all_subcount_totals[subcount_type] = {}

                    if item_id not in all_subcount_totals[subcount_type]:
                        all_subcount_totals[subcount_type][item_id] = {
                            "id": item_id,
                            "label": self._extract_label_from_bucket(
                                bucket_dict, subcount_type
                            ),
                            "view": {
                                "total_events": 0,
                                "unique_visitors": 0,
                                "unique_records": 0,
                                "unique_parents": 0,
                            },
                            "download": {
                                "total_events": 0,
                                "total_volume": 0.0,
                                "unique_files": 0,
                                "unique_visitors": 0,
                                "unique_records": 0,
                                "unique_parents": 0,
                            },
                        }

                    # Update view metrics
                    view_metrics = bucket_dict.get("view", {})
                    if view_metrics:
                        for metric, value in view_metrics.items():
                            if isinstance(value, dict) and "value" in value:
                                all_subcount_totals[subcount_type][item_id]["view"][
                                    metric
                                ] += value["value"]
                            elif isinstance(value, (int, float)):
                                all_subcount_totals[subcount_type][item_id]["view"][
                                    metric
                                ] += value

                    # Update download metrics
                    download_metrics = bucket_dict.get("download", {})
                    if download_metrics:
                        for metric, value in download_metrics.items():
                            if isinstance(value, dict) and "value" in value:
                                all_subcount_totals[subcount_type][item_id]["download"][
                                    metric
                                ] += value["value"]
                            elif isinstance(value, (int, float)):
                                all_subcount_totals[subcount_type][item_id]["download"][
                                    metric
                                ] += value

        # Now sort and assign top subcounts after processing all deltas
        for subcount_type in top_subcount_types:
            if subcount_type in all_subcount_totals:
                # Sort by view total_events for top 10
                sorted_by_views = sorted(
                    all_subcount_totals[subcount_type].values(),
                    key=lambda x: x["view"]["total_events"],
                    reverse=True,
                )[:10]

                # Sort by download total_events for top 10
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

    def _initialize_subcounts_structure(self) -> dict:
        """Initialize the subcounts structure based on configuration."""
        subcounts = {}
        seen_configs = set()
        for subcount_name, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            snapshot_type = usage_config.get("snapshot_type", "all")
            snapshot_field = f"{snapshot_type}_{subcount_name.replace('by_', '')}"

            if snapshot_type == "all":
                subcounts[snapshot_field] = []
            elif snapshot_type == "top":
                subcounts[snapshot_field] = {"by_view": [], "by_download": []}
        return subcounts

    def _get_simple_metrics(self) -> list:
        """Get list of simple metrics that use incremental updates."""
        simple_metrics = []
        for subcount_name, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Use snapshot_type to determine if this is a simple metric
            snapshot_type = usage_config.get("snapshot_type", "all")
            if snapshot_type == "all":
                delta_field = usage_config.get("delta_aggregation_name")
                snapshot_field = f"{snapshot_type}_{subcount_name.replace('by_', '')}"
                simple_metrics.append(snapshot_field)
        return simple_metrics

    def _extract_label_from_bucket(self, bucket_dict: dict, metric_type: str) -> str:
        """Extract the label from a bucket based on the metric type.

        Args:
            bucket_dict: The bucket dictionary from the aggregation
            metric_type: The type of metric (e.g., 'top_subjects', 'top_affiliations')

        Returns:
            The label string, or empty string if not found
        """
        # Find the config that matches this metric type
        config = None
        for subcount_name, cfg in self.subcount_configs.items():
            usage_config = cfg.get("usage_events", {})
            if not usage_config:
                continue

            # Check if this config matches the metric type
            snapshot_type = usage_config.get("snapshot_type", "all")
            snapshot_field = f"{snapshot_type}_{subcount_name.replace('by_', '')}"
            if snapshot_field == metric_type:
                # Extract label path from the usage config
                label_path = usage_config.get("label_field")
                if label_path:
                    config = {"label_path": label_path}
                    break

        if not config or not config["label_path"]:
            return ""  # No label extraction needed

        # Check if there's a label sub-aggregation with top_hits
        if "label" in bucket_dict and "hits" in bucket_dict["label"]:
            hits = bucket_dict["label"]["hits"]
            if "hits" in hits and hits["hits"]:
                # Get the first hit and extract the label
                first_hit = hits["hits"][0]
                if "_source" in first_hit:
                    source = first_hit["_source"]
                    # Extract label using the configured path
                    label_path = config["label_path"]
                    if "." in label_path:
                        # Handle nested paths like "title.en"
                        parts = label_path.split(".")
                        value = source
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = ""
                                break
                        return value if value else ""
                    else:
                        # Simple path like "name"
                        return source.get(label_path, "")

        # Fallback: return empty string
        return ""

    def _get_last_snapshot_document(self, community_id: str, start_date: arrow.Arrow):
        """Get the last snapshot document for a community."""
        last_snapshot_document = None
        if self.client.indices.exists(self.aggregation_index):
            last_snapshot_search = self.query_builder.build_last_snapshot_query(
                community_id, start_date
            )
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
                    # Map enriched delta document to snapshot format for consistent processing
                    delta_doc = current_delta.to_dict()
                    mapped_delta_doc = self._map_delta_to_snapshot_subcounts(delta_doc)
                    cumulative_totals, cumulative_subcounts = (
                        self._update_cumulative_totals(
                            cumulative_totals, cumulative_subcounts, mapped_delta_doc
                        )
                    )
                    # Get all delta records for full recalculation of top metrics
                    # We need to map all prior delta records to use consistent field names
                    all_delta_records = list(prior_delta_records) + list(
                        period_delta_records[: current_delta_index + 1]
                    )

                    # Map all delta records to snapshot format for consistent processing
                    mapped_all_delta_records = []
                    for delta_record in all_delta_records:
                        delta_dict = (
                            delta_record.to_dict()
                            if hasattr(delta_record, "to_dict")
                            else delta_record
                        )
                        mapped_delta = self._map_delta_to_snapshot_subcounts(delta_dict)
                        mapped_all_delta_records.append(mapped_delta)

                    cumulative_subcounts = self._update_top_subcounts(
                        cumulative_subcounts,
                        mapped_all_delta_records,
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
                subcount_name: [] for subcount_name in self.subcount_configs.keys()
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

    def _combine_query_results(
        self, view_results, download_results, community_id: str, date: arrow.Arrow
    ) -> dict:
        """Combine results from separate view and download queries.

        Args:
            view_results: Results from view query (or None).
            download_results: Results from download query (or None).
            community_id (str): The community ID.
            date (arrow.Arrow): The date for the aggregation.

        Returns:
            dict: Combined aggregation document.
        """
        combined_results = {
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
            combined_results["subcounts"][subcount_name] = []

            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Handle combined aggregations (funders and affiliations)
            if (
                usage_config.get("combine_queries")
                and len(usage_config["combine_queries"]) > 1
            ):
                combined_results["subcounts"][subcount_name] = (
                    self._combine_split_aggregations(
                        view_results, download_results, usage_config, subcount_name
                    )
                )
                continue

            # Get view buckets for this subcount
            view_buckets = []
            if view_results and hasattr(view_results.aggregations, subcount_name):
                view_agg = getattr(view_results.aggregations, subcount_name)
                view_buckets = view_agg.buckets

            # Get download buckets for this subcount
            download_buckets = []
            if download_results and hasattr(
                download_results.aggregations, subcount_name
            ):
                download_agg = getattr(download_results.aggregations, subcount_name)
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
                label = str(key)
                label_field = usage_config.get("label_field")
                if label_field and view_bucket:
                    if hasattr(view_bucket, "label") and hasattr(
                        view_bucket.label, "hits"
                    ):
                        title_hits = view_bucket.label.hits.hits
                        if title_hits and title_hits[0]._source:
                            source = title_hits[0]._source
                            # Parse the label_field path to find the correct item
                            label = self._extract_label_from_source(
                                source, label_field, key
                            )

                subcount_item = {
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

                combined_results["subcounts"][subcount_name].append(subcount_item)

        return combined_results

    def _create_aggregation_doc_from_results(
        self, results, community_id: str, date: arrow.Arrow
    ) -> dict:
        """Create the final aggregation document from direct query results."""

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

        # Get top-level metrics
        # The new query structure has metrics at the top level
        view_total_events = 0
        view_unique_visitors = 0
        view_unique_records = 0
        view_unique_parents = 0

        download_total_events = 0
        download_unique_visitors = 0
        download_unique_records = 0
        download_unique_parents = 0
        download_unique_files = 0
        download_total_volume = 0

        if hasattr(results.aggregations, "unique_visitors"):
            view_unique_visitors = results.aggregations.unique_visitors.value
        if hasattr(results.aggregations, "unique_records"):
            view_unique_records = results.aggregations.unique_records.value
        if hasattr(results.aggregations, "unique_parents"):
            view_unique_parents = results.aggregations.unique_parents.value
        if hasattr(results.aggregations, "unique_files"):
            download_unique_files = results.aggregations.unique_files.value
        if hasattr(results.aggregations, "total_volume"):
            download_total_volume = results.aggregations.total_volume.value

        final_dict = {
            "community_id": community_id,
            "period_start": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "totals": {
                "view": {
                    "total_events": view_total_events,
                    "unique_visitors": view_unique_visitors,
                    "unique_records": view_unique_records,
                    "unique_parents": view_unique_parents,
                },
                "download": {
                    "total_events": download_total_events,
                    "unique_visitors": download_unique_visitors,
                    "unique_records": download_unique_records,
                    "unique_parents": download_unique_parents,
                    "unique_files": download_unique_files,
                    "total_volume": download_total_volume,
                },
            },
            "subcounts": {
                "by_access_statuses": add_subcount_to_doc(
                    results.aggregations.by_access_statuses.buckets, None
                ),
                "by_resource_types": add_subcount_to_doc(
                    results.aggregations.by_resource_types.buckets,
                    ["resource_type", "title", "en"],
                ),
                "by_rights": add_subcount_to_doc(
                    results.aggregations.by_rights.buckets,
                    ["rights", "title", "en"],
                ),
                "by_funders": add_subcount_to_doc(
                    results.aggregations.by_funders.buckets,
                    ["funders", "name"],
                ),
                "by_periodicals": add_subcount_to_doc(
                    results.aggregations.by_periodicals.buckets
                ),
                "by_languages": add_subcount_to_doc(
                    results.aggregations.by_languages.buckets,
                    ["languages", "title"],
                ),
                "by_subjects": add_subcount_to_doc(
                    results.aggregations.by_subjects.buckets,
                    ["subjects", "title"],
                ),
                "by_publishers": add_subcount_to_doc(
                    results.aggregations.by_publishers.buckets
                ),
                "by_affiliations": add_subcount_to_doc(
                    results.aggregations.by_affiliations.buckets,
                    ["affiliations", "name"],
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

        current_iteration_date = start_date

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
                combined_results = self._combine_query_results(
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
            current_app.logger.error(
                f"Yielding doc for index: {index_name} with id: {doc_id}"
            )

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
        # For the new config structure, we need to build the aggregation names
        # based on the combine_queries and delta_aggregation_name
        combine_queries = config.get("combine_queries", [])
        delta_aggregation_name = config.get("delta_aggregation_name")

        if not combine_queries or len(combine_queries) <= 1:
            return []

        # Build aggregation names for each query field
        agg_names = []
        for query_field in combine_queries:
            subfield = query_field.split(".")[-1]
            agg_name = f"{delta_aggregation_name}_{subfield}"
            agg_names.append(agg_name)

        # Use the first two aggregation names for id and name
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

        # Process all buckets
        for bucket_type, bucket, agg_type in buckets:
            item_id, name = self._extract_id_name_from_bucket(bucket, bucket_type)
            key = (item_id, name)

            if key not in combined_items:
                combined_items[key] = self._create_empty_subcount_item(item_id, name)

            # Add metrics
            if agg_type == "view":
                combined_items[key]["view"] = self._extract_view_metrics(bucket)
            else:  # download
                combined_items[key]["download"] = self._extract_download_metrics(bucket)

        return list(combined_items.values())

    def _get_id_name_buckets(
        self, view_results, download_results, id_agg_name, name_agg_name
    ):
        """Get all buckets from id and name aggregations for both view and download."""
        buckets = []

        # Helper to add buckets if they exist
        def add_buckets(results, agg_name, agg_type):
            if results and hasattr(results.aggregations, agg_name):
                agg = getattr(results.aggregations, agg_name)
                for bucket in agg.buckets:
                    buckets.append((agg_name, bucket, agg_type))

        # Add all buckets
        add_buckets(view_results, id_agg_name, "view")
        add_buckets(view_results, name_agg_name, "view")
        add_buckets(download_results, id_agg_name, "download")
        add_buckets(download_results, name_agg_name, "download")

        return buckets

    def _extract_id_name_from_bucket(self, bucket, bucket_type):
        """Extract id and name from a bucket based on its type."""
        if bucket_type.endswith("_id"):
            # ID bucket: key is id, extract name from label
            item_id = bucket.key
            name = self._extract_name_from_label(bucket)
        else:
            # Name bucket: key is name, extract id from label
            name = bucket.key
            item_id = self._extract_id_from_label(bucket)

        return item_id, name

    def _extract_name_from_label(self, bucket):
        """Extract name from bucket label aggregation."""
        if hasattr(bucket, "label") and hasattr(bucket.label, "hits"):
            title_hits = bucket.label.hits.hits
            if title_hits and title_hits[0]._source:
                source = title_hits[0]._source
                if "funders" in source and "name" in source["funders"]:
                    return source["funders"]["name"]
                elif "affiliations" in source and "name" in source["affiliations"]:
                    return source["affiliations"]["name"]
        return str(bucket.key)

    def _extract_id_from_label(self, bucket):
        """Extract id from bucket label aggregation."""
        if hasattr(bucket, "label") and hasattr(bucket.label, "hits"):
            title_hits = bucket.label.hits.hits
            if title_hits and title_hits[0]._source:
                source = title_hits[0]._source
                if "funders" in source and "id" in source["funders"]:
                    return source["funders"]["id"]
                elif "affiliations" in source and "id" in source["affiliations"]:
                    return source["affiliations"]["id"]
        return bucket.key

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

    def _extract_label_from_source(
        self, source: dict, title_field: str, bucket_key: str
    ) -> str:
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
            # Simple field like "name" - just return the value
            return source.get(title_field, str(bucket_key))

        # Parse the path (e.g., "subjects.title" -> ["subjects", "title"])
        parts = title_field.split(".")

        # The first part should be the array field (e.g., "subjects")
        array_field = parts[0]
        if array_field not in source or not isinstance(source[array_field], list):
            return str(bucket_key)

        # Find the item in the array that matches the bucket key
        for item in source[array_field]:
            if isinstance(item, dict) and "id" in item:
                if str(item["id"]) == str(bucket_key):
                    # Found the matching item, extract the label from remaining path
                    if len(parts) == 1:
                        # Just the array field, return the item itself
                        return str(item)
                    else:
                        # Extract from the nested path (e.g., "title")
                        label_path = parts[1:]
                        value = item
                        for part in label_path:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = ""
                                break
                        return str(value) if value else str(bucket_key)

        # No matching item found, return bucket key as fallback
        return str(bucket_key)


class CommunityRecordsDeltaAggregatorBase(CommunityAggregatorBase):
    """Aggregator for community record deltas.

    Uses the date the record was created as the initial date of the record.
    """

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-records-delta-created")
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
        )

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
                config["records"]["delta_aggregation_name"]: []
                for config in self.subcount_configs.values()
                if "records" in config
                and "delta_aggregation_name" in config["records"]
                and not config["records"].get("merge_aggregation_with")
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

        def make_subcount_list(subcount_type):
            # Find the config for this subcount type
            config = None
            for cfg in self.subcount_configs.values():
                if (
                    "records" in cfg
                    and cfg["records"]["delta_aggregation_name"] == subcount_type
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
                added_items = []
                removed_items = []
                for field in config["combine_queries"]:
                    field_name = field.split(".")[
                        -1
                    ]  # Get the last part of the field path
                    added_items.extend(
                        aggs_added.get(f"by_{field_name}", {}).get("buckets", [])
                    )
                    removed_items.extend(
                        aggs_removed.get(f"by_{field_name}", {}).get("buckets", [])
                    )
            else:
                added_items = aggs_added.get(subcount_type, {}).get("buckets", [])
                removed_items = aggs_removed.get(subcount_type, {}).get("buckets", [])

            combined_keys = list(
                set(b["key"] for b in added_items)
                | set(b["key"] for b in removed_items)
            )
            subcount_list = []

            # Handle case where no items found
            if not combined_keys:
                return subcount_list

            for key in combined_keys:
                # Skip None or empty keys
                if not key:
                    continue

                added_filtered = list(filter(lambda x: x["key"] == key, added_items))
                added = added_filtered[0] if added_filtered else {}
                removed_filtered = list(
                    filter(lambda x: x["key"] == key, removed_items)
                )
                removed = removed_filtered[0] if removed_filtered else {}

                # Build label configuration for find_item_label
                label_config = []
                if config.get("label_field"):
                    label_config.append(config["field"])
                    label_config.append(config["label_field"])
                else:
                    label_config.append(config["field"])

                label = find_item_label(added, removed, label_config, key)

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
                **{
                    config["records"]["delta_aggregation_name"]: make_subcount_list(
                        config["records"]["delta_aggregation_name"]
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
        # If so, we index a zero document for the community for each day
        should_skip = self._should_skip_aggregation(
            start_date, last_event_date, community_id
        )
        if should_skip:
            current_app.logger.error(
                f"Skipping delta aggregation for {community_id} - "
                f"no relevant records after {start_date}"
            )

        # Index aggregations in yearly indices
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)
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

                    query_builder = CommunityRecordDeltaQuery(
                        client=self.client, event_index=self.event_index
                    )
                    year_search_added = query_builder.build_query(
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
                    day_results_added = year_search_added.execute()
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


class CommunityRecordsDeltaAddedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community records delta added."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = prefix_index("stats-community-records-delta-added")


class CommunityRecordsDeltaPublishedAggregator(CommunityRecordsDeltaAggregatorBase):
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
