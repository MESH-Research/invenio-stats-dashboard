# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

import datetime
import time
from collections.abc import Generator
from typing import Any

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.aggregations import StatAggregator
from opensearchpy import AttrDict, AttrList
from opensearchpy.exceptions import NotFoundError
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from ..exceptions import CommunityEventIndexingError, DeltaDataGapError
from ..proxies import current_community_stats_service
from .bookmarks import CommunityBookmarkAPI, CommunityEventBookmarkAPI
from .types import (
    RecordSnapshotDocument,
    RecordDeltaDocument,
    UsageSnapshotDocument,
    UsageDeltaDocument,
)


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
        # Start timing the entire run method
        run_start_time = time.time()
        current_app.logger.debug(f"Starting {self.name}")
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
            community_start_time = time.time()
            current_app.logger.debug(f"Community {community_id}")
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

            # Time the agg_iter call
            agg_iter_start_time = time.time()
            current_app.logger.debug(f"agg_iter {community_id}")
            agg_iter_generator = self.agg_iter(
                community_id,
                lower_limit,
                upper_limit,
                first_event_date_safe,
                last_event_date_safe,
            )

            agg_iter_end_time = time.time()
            agg_iter_duration = agg_iter_end_time - agg_iter_start_time
            current_app.logger.debug(
                f"agg_iter {community_id}: {agg_iter_duration:.2f}s"
            )

            # Time the bulk indexing
            bulk_start_time = time.time()
            current_app.logger.debug(f"bulk {community_id}")
            results.append(
                bulk(
                    self.client,
                    agg_iter_generator,
                    stats_only=False if return_results else True,
                    chunk_size=50,
                )
            )

            bulk_end_time = time.time()
            bulk_duration = bulk_end_time - bulk_start_time
            current_app.logger.debug(f"bulk {community_id}: {bulk_duration:.2f}s")
            if update_bookmark:
                self.bookmark_api.set_bookmark(community_id, next_bookmark)

            # Log total time for this community
            community_end_time = time.time()
            community_duration = community_end_time - community_start_time
            current_app.logger.debug(
                f"Community {community_id}: {community_duration:.2f}s"
            )

        # Log total time for the entire run method
        run_end_time = time.time()
        run_duration = run_end_time - run_start_time
        current_app.logger.debug(f"Completed {self.name}: {run_duration:.2f}s")
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
        # Start timing the agg_iter method
        agg_iter_start_time = time.time()
        current_app.logger.debug(f"Snapshot agg_iter {community_id}")
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

        # Time the main aggregation loop
        loop_start_time = time.time()
        iteration_count = 0
        while current_iteration_date <= end_date:
            iteration_start_time = time.time()
            iteration_count += 1
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

            # Time the create_agg_dict call
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

            # Log timing for this iteration
            iteration_end_time = time.time()
            iteration_duration = iteration_end_time - iteration_start_time
            current_app.logger.debug(
                f"Day {iteration_count}: {iteration_duration:.2f}s"
            )
        # Log total timing for the main loop
        loop_end_time = time.time()
        loop_duration = loop_end_time - loop_start_time
        current_app.logger.debug(
            f"Snapshot loop: {iteration_count} days, {loop_duration:.2f}s"
        )

        # Log total timing for agg_iter
        agg_iter_end_time = time.time()
        agg_iter_duration = agg_iter_end_time - agg_iter_start_time
        current_app.logger.debug(
            f"Snapshot agg_iter {community_id}: {agg_iter_duration:.2f}s"
        )


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
