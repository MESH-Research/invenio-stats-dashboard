# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Base classes for community statistics aggregators."""

import copy
import datetime
import time
from abc import abstractmethod
from collections.abc import Generator
from typing import Any, cast

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.aggregations import StatAggregator
from opensearchpy import AttrDict, AttrList
from opensearchpy.exceptions import NotFoundError, TransportError
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from ..exceptions import (
    DeltaDataGapError,
    CommunityEventsNotInitializedError,
)
from .bookmarks import CommunityBookmarkAPI
from .types import (
    RecordDeltaDocument,
    RecordSnapshotDocument,
    UsageDeltaDocument,
    UsageSnapshotDocument,
)


class CommunityAggregatorBase(StatAggregator):
    """Base class for community statistics aggregators."""

    def __init__(self, name, *args, **kwargs):
        """Initialize the base community aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments, including:
                community_ids (list[str], optional): List of community IDs to aggregate.
                client: OpenSearch client to use.
        """
        self.name = name
        self.event = ""
        self.aggregation_field: str | None = None
        self.copy_fields: dict[str, str] = {}
        self.event_index: str | list[tuple[str, str]] | None = None
        self.first_event_index: str | list[tuple[str, str]] | None = None
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
        # Adaptive chunking configuration
        self.initial_chunk_size = current_app.config.get(
            "COMMUNITY_STATS_INITIAL_CHUNK_SIZE", 50
        )
        self.min_chunk_size = current_app.config.get(
            "COMMUNITY_STATS_MIN_CHUNK_SIZE", 1
        )
        self.max_chunk_size = current_app.config.get(
            "COMMUNITY_STATS_MAX_CHUNK_SIZE", 100
        )
        self.chunk_size_reduction_factor = current_app.config.get(
            "COMMUNITY_STATS_CHUNK_REDUCTION_FACTOR", 0.7
        )
        # Current working chunk size (starts at initial, adapts during operation)
        self.current_chunk_size = self.initial_chunk_size
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
    ) -> Generator[tuple[dict, float], None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        raise NotImplementedError

    def _first_event_date_query(
        self, community_id: str, index: str
    ) -> tuple[arrow.Arrow | None, arrow.Arrow | None]:
        """Get the first event date from a specific index.

        Args:
            community_id: The community ID
            index: The index to use for the query (unprefixed)

        A min aggregation is more efficient than sorting the query.

        Returns:
            A tuple of the earliest and latest event dates. If no events are found,
            both dates are None.
        """
        current_search_client.indices.refresh(index=prefix_index(index))
        if community_id == "global":
            query = Q("match_all")
        else:
            query = self.event_community_query_term(community_id)

        search = (
            Search(using=self.client, index=prefix_index(index))
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

        def check_index_exists(index_name: str) -> bool:
            """Check if the index exists."""
            return bool(self.client.indices.exists(index=prefix_index(index_name)))

        if isinstance(self.first_event_index, str):
            if not check_index_exists(self.first_event_index):
                raise ValueError(
                    f"Required index {prefix_index(self.first_event_index)} "
                    f"does not exist. Aggregator requires this index to be available."
                )
            earliest_date, latest_date = self._first_event_date_query(
                community_id, self.first_event_index
            )
        elif isinstance(self.first_event_index, list):
            for _, index in self.first_event_index:
                if not check_index_exists(index):
                    raise ValueError(
                        f"Required index {prefix_index(index)} "
                        f"does not exist. Aggregator requires this index to be "
                        f"available."
                    )
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

    def _check_community_events_initialized(self) -> None:
        """Check if community events index exists and has records.

        Raises:
            CommunityEventsNotInitializedError: If the community events index
                doesn't exist or has no records.
        """
        try:
            # Check if the community events index exists
            if not self.client.indices.exists(
                index=prefix_index("stats-community-events")
            ):
                raise CommunityEventsNotInitializedError(
                    "Community events index does not exist. "
                    "Please run community events initialization first."
                )

            # Check if the index has any records
            search = Search(
                using=self.client, index=prefix_index("stats-community-events")
            )
            count = search.count()

            if count == 0:
                raise CommunityEventsNotInitializedError(
                    "Community events index exists but has no records. "
                    "Please run community events initialization first."
                )

        except Exception as e:
            if isinstance(e, CommunityEventsNotInitializedError):
                raise
            # If it's a different exception (e.g., connection error), wrap it
            raise CommunityEventsNotInitializedError(
                f"Failed to check community events initialization: {e}"
            ) from e

    @abstractmethod
    def _check_usage_events_migrated(self) -> None:
        """Check if usage events have been migrated to include community_ids.

        This method should be implemented by usage aggregators to verify that
        view and download events have been migrated to include community_ids fields.
        Non-usage aggregators should override this method with a pass statement.

        Raises:
            UsageEventsNotMigratedError: If usage events indices don't exist
                or events lack community_ids fields.
        """
        pass

    def run(
        self,
        start_date: arrow.Arrow | datetime.datetime | str | None = None,
        end_date: arrow.Arrow | datetime.datetime | str | None = None,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
        return_results: bool = False,
    ) -> list[tuple[int, int | list[dict], list[dict]]]:
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

        # Check if community events are initialized before proceeding
        self._check_community_events_initialized()

        # Check if usage events have been migrated (for usage aggregators)
        self._check_usage_events_migrated()

        # If no records have been indexed there is nothing to aggregate
        if (
            isinstance(self.record_index, str)
            and not Index(prefix_index(self.record_index), using=self.client).exists()
        ):
            return [(0, [], [])]
        elif isinstance(self.record_index, list):
            for _, index in self.record_index:
                if not Index(prefix_index(index), using=self.client).exists():
                    return [(0, [], [])]

        if self.community_ids:
            communities_to_aggregate = self.community_ids
        else:
            communities_to_aggregate = [
                c["id"]
                for c in current_communities.service.read_all(system_identity, [])
            ]
            communities_to_aggregate.append(
                "global"
            )  # Add global stats only when no specific communities

        results = []
        for community_id in communities_to_aggregate:
            current_app.logger.debug(f"start_date: {start_date}")
            current_app.logger.debug(f"end_date: {end_date}")
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
                # When ignoring bookmark, start from the earliest available data
                # if no start_date is provided, otherwise use the provided start_date
                if start_date:
                    lower_limit = start_date
                else:
                    lower_limit = first_event_date or arrow.utcnow()

            # Ensure we don't aggregate more than self.catchup_interval days
            upper_limit = self._get_end_date(lower_limit, end_date)

            first_event_date_safe = first_event_date or arrow.utcnow()
            last_event_date_safe = last_event_date or arrow.utcnow()

            current_app.logger.debug(f"upper_limit: {upper_limit}")
            current_app.logger.debug(f"lower_limit: {lower_limit}")

            agg_iter_generator = self.agg_iter(
                community_id,
                lower_limit,
                upper_limit,
                first_event_date_safe,
                last_event_date_safe,
            )

            community_docs_info: list[dict] = []

            # Wrapper generator that collects metadata while yielding documents
            # so that we can return the detailed information in the result
            def document_generator_with_metadata(docs_info_list):
                for doc, doc_generation_time in agg_iter_generator:  # noqa: B023
                    doc_info = {
                        "document_id": doc["_id"],
                        "index_name": doc["_index"],
                        "community_id": doc["_source"].get("community_id"),
                        "date_info": {},
                        "generation_time": doc_generation_time,
                    }

                    if (
                        "period_start" in doc["_source"]
                        and "period_end" in doc["_source"]
                    ):
                        doc_info["date_info"] = {
                            "period_start": doc["_source"]["period_start"],
                            "period_end": doc["_source"]["period_end"],
                            "date_type": "delta",
                        }
                    elif "snapshot_date" in doc["_source"]:
                        doc_info["date_info"] = {
                            "snapshot_date": doc["_source"]["snapshot_date"],
                            "date_type": "snapshot",
                        }

                    docs_info_list.append(doc_info)
                    yield doc

            current_app.logger.debug(
                f"About to begin adaptive bulk indexing for community {community_id} "
                f"with initial chunk_size={self.current_chunk_size}"
            )
            
            docs_indexed, errors = self._adaptive_bulk_index(
                document_generator_with_metadata(community_docs_info),
                stats_only=False if return_results else True,
            )
            results.append((docs_indexed, errors, community_docs_info))

            if update_bookmark:
                if errors:
                    current_app.logger.error(
                        f"Bulk indexing errors for {community_id}: "
                        f"{len(errors)} errors. Skipping bookmark update."
                    )
                    continue

                expected_days = (upper_limit - lower_limit).days + 1

                # For snapshot aggregators, we expect at least the expected number
                # of days (they may index more due to catch-up processing)
                if docs_indexed < expected_days:
                    current_app.logger.error(
                        f"Insufficient documents for {community_id}: "
                        f"expected at least {expected_days} days, indexed "
                        f"{docs_indexed} documents. Skipping bookmark update."
                    )
                    continue

                # Validate that we have document info for all indexed documents
                if len(community_docs_info) != docs_indexed:
                    current_app.logger.error(
                        f"Document info count mismatch for {community_id}: "
                        f"indexed {docs_indexed} documents, got "
                        f"{len(community_docs_info)} document info entries. "
                        f"Skipping bookmark update."
                    )
                    continue

                self._update_bookmark(community_id, community_docs_info)

        # Refresh all indices to make documents available for subsequent aggregators
        self.client.indices.refresh(index=f"{self.aggregation_index}-*")
        return results

    def _update_bookmark(
        self, community_id: str, community_docs_info: list[dict]
    ) -> bool:
        """Update the bookmark for a community based on the last processed document.

        Args:
            community_id: The community ID
            community_docs_info: List of document info dictionaries from the aggregation

        Returns:
            True if bookmark was updated successfully, False if it should be skipped
        """
        if not community_docs_info:
            current_app.logger.warning(
                f"No documents were processed for {community_id}, "
                f"skipping bookmark update"
            )
            return False

        last_doc_info = community_docs_info[-1]
        date_info = last_doc_info.get("date_info", {})
        period_start = date_info.get("period_start")
        snapshot_date = date_info.get("snapshot_date")

        latest_date = None
        try:
            if period_start:
                latest_date = arrow.get(period_start)
            elif snapshot_date:
                latest_date = arrow.get(snapshot_date)
        except (arrow.parser.ParserError, ValueError) as e:
            current_app.logger.warning(
                f"Failed to parse date for {community_id}: {e}, "
                f"skipping bookmark update"
            )
            return False

        if not latest_date:
            current_app.logger.warning(
                f"No period_start or snapshot_date found in last document for "
                f"{community_id}, skipping bookmark update"
            )
            return False

        next_bookmark = latest_date.format("YYYY-MM-DDTHH:mm:ss.SSS")
        current_app.logger.debug(
            f"Setting bookmark for {community_id} to last "
            f"processed date: {next_bookmark}"
        )

        self.bookmark_api.set_bookmark(community_id, next_bookmark)
        return True

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

    def _adaptive_bulk_index(
        self, 
        documents: Generator[dict, None, None], 
        stats_only: bool = True
    ) -> tuple[int, int | list[dict]]:
        """Perform bulk indexing with adaptive chunk size based on request size limits.

        This method automatically adjusts chunk size when encountering 413 errors
        (request too large) by gradually reducing the chunk size until it succeeds.

        Args:
            documents: Generator of documents to index
            stats_only: Whether to return only stats or detailed error information

        Returns:
            Tuple of (docs_indexed, errors)
        """
        try:
            result = bulk(
                self.client,
                documents,
                stats_only=stats_only,
                chunk_size=self.current_chunk_size,
            )
            
            if self.current_chunk_size < self.max_chunk_size:
                self.current_chunk_size = min(
                    int(self.current_chunk_size * 1.1), 
                    self.max_chunk_size
                )
                current_app.logger.debug(
                    f"Bulk indexing successful with "
                    f"chunk_size={self.current_chunk_size}"
                )
            
            return cast(tuple[int, int | list[dict]], result)
            
        except TransportError as e:
            if e.status_code == 413:  # Request too large
                if self.current_chunk_size > self.min_chunk_size:
                    # Reduce chunk size gradually
                    old_chunk_size = self.current_chunk_size
                    self.current_chunk_size = max(
                        int(self.current_chunk_size * self.chunk_size_reduction_factor),
                        self.min_chunk_size
                    )
                    
                    current_app.logger.warning(
                        f"Request too large (413) with chunk_size={old_chunk_size}, "
                        f"reducing to {self.current_chunk_size} and retrying"
                    )
                    
                    return self._adaptive_bulk_index(documents, stats_only)
                else:
                    current_app.logger.error(
                        f"Request too large even with minimum "
                        f"chunk_size={self.min_chunk_size}"
                    )
                    raise
            else:
                raise

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
        """Initialize the snapshot aggregator base.

        Args:
            name (str): The name of the aggregator.
            subcount_configs (dict, optional): Subcount configurations. Defaults to
                the global config.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNTS"]
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
        new_snapshot = copy.deepcopy(previous_snapshot)

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

        index_name = prefix_index(f"{self.aggregation_index}-{previous_date.year}")

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
        delta_search = Search(using=self.client, index=prefix_index(self.delta_index))
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

        # With unified field names, no field mapping is needed
        # Return delta documents directly
        return [doc["_source"] for doc in delta_documents]

    def _build_exhaustive_cache(self, deltas: list, category_name: str) -> dict:
        """Build exhaustive cache for a category from all delta documents.

        Args:
            deltas (list): All delta documents containing both added and removed data
            category_name (str): Name of the subcount category

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
        latest_delta: dict | None = None,
    ) -> None:
        """Update top subcounts.

        This method should be overridden by subclasses to provide the appropriate
        logic for updating top subcounts based on their specific data structures.

        Args:
            new_dict (dict): The aggregation dictionary to modify
            deltas (list): The daily delta dictionaries to update the subcounts with
            exhaustive_counts_cache (dict): The exhaustive counts cache
            latest_delta (dict | None): The latest delta document
        """
        if latest_delta is None:
            latest_delta = {}
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
        exhaustive_counts_cache: dict | None = None,
    ) -> RecordSnapshotDocument | UsageSnapshotDocument:
        """Create a dictionary representing the aggregation result for indexing.

        This method should be overridden by subclasses to provide the appropriate
        logic for creating aggregation dictionaries based on their specific data
        structures.

        Args:
            current_day (arrow.Arrow): The current day for the snapshot
            previous_snapshot (RecordSnapshotDocument | UsageSnapshotDocument):
                The previous snapshot document to add onto
            latest_delta (RecordDeltaDocument | UsageDeltaDocument):
                The latest delta document to add
            deltas (list): All delta documents for top subcounts (from earliest date)
            exhaustive_counts_cache (dict | None): The exhaustive counts cache
        """
        if exhaustive_counts_cache is None:
            exhaustive_counts_cache = {}
        raise NotImplementedError("Subclasses must override create_agg_dict")

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[tuple[dict, float], None, None]:
        """Create a dictionary representing the aggregation result for indexing.

        Args:
            community_id (str): The ID of the community to aggregate.
            start_date (arrow.Arrow): The start date for the aggregation.
            end_date (arrow.Arrow): The end date for the aggregation.
            first_event_date (arrow.Arrow | None): The first event date, or None if
                no events exist.
            last_event_date (arrow.Arrow | None): The last event date, or None if no
                events exist. In this case the events we're looking for are delta
                aggregations.

        Returns:
            A generator of tuples, where each tuple contains:
            - [0]: A dictionary representing an aggregation document for indexing
            - [1]: The time taken to generate this document (in seconds)
        """
        current_iteration_date = arrow.get(start_date)

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
            # FIXME: Add +1 to match delta aggregator's inclusive range calculation
            # Delta aggregators use _get_end_date() which creates inclusive ranges
            end_date = min(
                end_date, previous_snapshot_date.shift(days=self.catchup_interval + 1)
            )
        elif not previous_snapshot_date:  # No previous snapshot
            if first_event_date is None:
                # No events exist, return empty generator
                return
            current_iteration_date = first_event_date
            # FIXME: Add +1 to match delta aggregator's inclusive range calculation
            # Delta aggregators use _get_end_date() which creates inclusive ranges
            end_date = min(
                end_date, current_iteration_date.shift(days=self.catchup_interval + 1)
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

        exhaustive_counts_cache: dict[str, Any] = {}

        # Don't try to aggregate beyond the last delta date
        last_delta_date = arrow.get(all_delta_documents[-1]["period_start"])
        end_date = min(end_date, last_delta_date.ceil("day"))

        current_delta_index = self._get_delta_index_by_date(
            all_delta_documents, current_iteration_date
        )

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

            document = {
                "_id": document_id,
                "_index": index_name,
                "_source": source_content,
            }

            iteration_end_time = time.time()
            iteration_duration = iteration_end_time - iteration_start_time
            yield (document, iteration_duration)

            previous_snapshot = source_content
            previous_snapshot_date = current_iteration_date
            current_iteration_date = current_iteration_date.shift(days=1)
            current_delta_index += 1


class CommunityEventsIndexAggregator(CommunityAggregatorBase):
    """Dummy aggregator for registering the community events index template.

    This aggregator doesn't actually perform any aggregation - it's just used
    to register the index template with the invenio-stats system.
    """

    def __init__(self, name, *args, **kwargs):
        """Initialize the events index aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        # This aggregator doesn't need any specific configuration

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[tuple[dict, float], None, None]:
        """This aggregator doesn't perform any aggregation."""
        # Return empty generator - no aggregation needed
        return
        yield  # This line is never reached but satisfies the generator requirement
