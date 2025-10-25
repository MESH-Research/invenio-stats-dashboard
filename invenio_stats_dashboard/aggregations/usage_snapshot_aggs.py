# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community usage snapshot aggregators for tracking cumulative usage statistics."""

import numbers
import time
from collections.abc import Generator
from typing import Any

import arrow
from flask import current_app
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search

from ..queries import (
    CommunityUsageSnapshotQuery,
)
from .base import CommunitySnapshotAggregatorBase
from .types import (
    UsageDeltaDocument,
    UsageSnapshotDocument,
    UsageSnapshotTopCategories,
    UsageSubcountItem,
)


class CommunityUsageSnapshotAggregator(CommunitySnapshotAggregatorBase):
    """Aggregator for creating cumulative usage snapshots from daily delta documents."""

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        """Initialize the community usage snapshot aggregator.

        Args:
            name (str): The name of the aggregator.
            subcount_configs (dict, optional): Subcount configurations. Defaults to
                the global config.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, subcount_configs, *args, **kwargs)
        self.event_index = "stats-community-usage-delta"
        self.delta_index = "stats-community-usage-delta"
        self.first_event_index = "stats-community-usage-delta"
        self.aggregation_index = "stats-community-usage-snapshot"
        self.event_date_field = "period_start"
        self.query_builder = CommunityUsageSnapshotQuery(client=self.client)

    def _check_usage_events_migrated(self) -> None:
        """Override abstract method - checking done in usage delta aggregator."""
        pass

    def _get_latest_delta_date(self, community_id: str) -> arrow.Arrow | None:
        """Get the latest delta record date for dependency checking.

        Uses the query builder to find the latest usage delta record.

        Args:
            community_id: The community ID to check

        Returns:
            The latest delta record date, or None if no records exist
        """
        search = self.query_builder.build_dependency_check_query(community_id)
        result = search.execute()

        if not result.aggregations.max_date.value:
            return None

        return arrow.get(result.aggregations.max_date.value_as_string)

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
        exhaustive_counts_cache: dict | None = None,
    ) -> UsageSnapshotDocument:
        """Create the final aggregation document from cumulative totals.

        Args:
            current_day (arrow.Arrow): The current day for the snapshot
            previous_snapshot (UsageSnapshotDocument): The previous snapshot document
            latest_delta (UsageDeltaDocument): The latest delta document
            exhaustive_counts_cache (dict | None): The exhaustive counts cache

        Returns:
            UsageSnapshotDocument: The final aggregation document.
        """
        if exhaustive_counts_cache is None:
            exhaustive_counts_cache = {}

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

        self._update_top_subcounts(new_dict, exhaustive_counts_cache, latest_delta)

        return new_dict

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

        Returns:
            list: List of top N items sorted by the specified angle.
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
        """Update cumulative totals with values from enriched daily delta documents.

        Returns:
            UsageSnapshotDocument: The updated snapshot document with cumulative totals.
        """

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
                # Skip "top" type subcounts - they're handled by _update_top_subcounts
                if key == "subcounts" and self._is_top_subcount(k):
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
        # Only process "all" type subcounts to avoid double-counting with
        # "top" type subcounts
        filtered_subcounts = {}
        delta_subcounts = delta_doc.get("subcounts", {})

        for subcount_name, subcount_data in delta_subcounts.items():
            config = self.subcount_configs.get(subcount_name, {})
            usage_config = config.get("usage_events", {})
            if usage_config and usage_config.get("snapshot_type", "all") == "all":
                filtered_subcounts[subcount_name] = subcount_data

        if filtered_subcounts:
            # Create a temporary delta doc with only "all" type subcounts
            temp_delta_doc = delta_doc.copy()
            temp_delta_doc["subcounts"] = filtered_subcounts
            update_totals(new_dict, temp_delta_doc, "subcounts")

        return new_dict

    def _update_top_subcounts(  # type: ignore[override]
        self,
        new_dict: UsageSnapshotDocument,
        exhaustive_counts_cache: dict,
        latest_delta: UsageDeltaDocument,
    ) -> None:
        """Update top subcounts.

        These are the subcounts that only include the top N values for each field
        (where N is configured by COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).
        (E.g. subjects, publishers, etc.) We can't just add the new deltas
        to the current subcounts because the top N values for each field may have
        changed. We avoid performing a full recalculation from all delta documents
        for every delta document by using an exhaustive counts cache. This builds
        a cumulative set of subcount totals that includes *all* existing items that
        have been seen for each subcount since the first delta document. This way
        we can simply update the cache with the latest delta document and then select
        the top N items from the cache for each subcount.

        Args:
            new_dict: The aggregation dictionary to modify
            exhaustive_counts_cache: The exhaustive counts cache
            latest_delta: The latest delta document
        """
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type") == "top":
                # Use the subcount key directly
                top_subcount_name = subcount_key

                # exhaustive_counts_cache should already be populated by our scan query
                # Just update it with the latest delta
                if top_subcount_name not in exhaustive_counts_cache:
                    exhaustive_counts_cache[top_subcount_name] = {}
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
        """Initialize the subcounts structure based on configuration.

        Returns:
            dict[str, list[UsageSubcountItem] | UsageSnapshotTopCategories]: Initialized
                subcounts structure.
        """
        subcounts: dict[str, list[UsageSubcountItem] | UsageSnapshotTopCategories] = {}
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            snapshot_type = usage_config.get("snapshot_type", "all")
            if snapshot_type == "all":
                subcounts[subcount_key] = []
            elif snapshot_type == "top":
                subcounts[subcount_key] = {"by_view": [], "by_download": []}
        return subcounts

    def _is_top_subcount(self, subcount_name: str) -> bool:
        """Check if a subcount is configured as 'top' type.

        Returns:
            bool: True if the subcount is configured as 'top' type, False otherwise.
        """
        config = self.subcount_configs.get(subcount_name, {})
        usage_config = config.get("usage_events", {})
        snapshot_type = usage_config.get("snapshot_type", "all")
        return str(snapshot_type) == "top"

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

        Yields:
            tuple[dict, float]: A tuple containing:
                - [0]: A dictionary representing an aggregation document for indexing
                - [1]: The time taken to generate this document (in seconds)
        """
        # Check if delta aggregator has processed data for the requested period
        if not self._check_delta_dependency(community_id, start_date, end_date):
            current_app.logger.info(
                f"Skipping snapshot aggregation for {community_id} "
                f"from {start_date.date()} to {end_date.date()} - "
                f"delta aggregator has not processed data for this period"
            )
            return

        current_iteration_date = arrow.get(start_date)
        previous_snapshot, is_zero_placeholder = self._get_previous_snapshot(
            community_id, current_iteration_date
        )
        previous_snapshot_date = (
            arrow.get(previous_snapshot["snapshot_date"])  # type: ignore
            if previous_snapshot and not is_zero_placeholder
            else None
        )

        if previous_snapshot_date and previous_snapshot_date <= end_date:
            current_iteration_date = previous_snapshot_date
            # Apply catchup limit to prevent processing too many days at once
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

        try:
            # Build exhaustive_counts_cache from all historical
            # deltas BEFORE current period
            exhaustive_counts_cache: dict[str, Any] = {}
            self._build_exhaustive_cache_from_scan(
                exhaustive_counts_cache,
                community_id,
                first_event_date,
                current_iteration_date,
            )
        except Exception as e:
            current_app.logger.error(
                "Optimized agg_iter: Failed to initialize "
                "exhaustive_counts_cache: "
                f"{e}"
            )
            return

        # Initialize streaming for daily deltas
        daily_deltas_buffer: list[dict] = []
        last_processed_date = first_event_date.shift(
            days=-1
        )  # Start from day before first event
        buffer_size = 50  # Small buffer of daily deltas

        iteration_count = 0
        while current_iteration_date <= end_date:
            iteration_start_time = time.time()
            iteration_count += 1

            try:
                # Get the delta document for this specific date
                daily_delta, daily_deltas_buffer, last_processed_date = (
                    self._get_delta_from_buffer(
                        daily_deltas_buffer,
                        current_iteration_date,
                        community_id,
                        end_date,
                        last_processed_date,
                        buffer_size,
                    )
                )
                if not daily_delta:
                    current_app.logger.warning(
                        "No delta document found for date "
                        f"{current_iteration_date.format('YYYY-MM-DD')} - "
                        "stopping aggregation"
                    )
                    break

                # Create the aggregation document using original method
                source_content = self.create_agg_dict(
                    current_iteration_date,
                    previous_snapshot,
                    daily_delta,
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

            except Exception as e:
                current_app.logger.error(
                    "Error processing date "
                    f"{current_iteration_date.format('YYYY-MM-DD')}: {e}"
                )
                current_iteration_date = current_iteration_date.shift(days=1)
                continue

    def _fetch_daily_deltas_page(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        page_size: int,
    ) -> list[dict]:
        """Fetch a page of daily delta documents starting from start_date.

        Args:
            community_id: The community ID to fetch data for
            start_date: The start date to fetch from
            end_date: The end date to fetch to
            page_size: Number of documents to fetch per page

        Returns:
            List of delta documents
        """
        index_name = prefix_index(self.delta_index)
        delta_search = Search(using=self.client, index=index_name)
        delta_search = delta_search.query(
            "bool",
            must=[
                {"term": {"community_id": community_id}},
                {
                    "range": {
                        "period_start": {
                            "gte": start_date.format("YYYY-MM-DDTHH:mm:ss"),
                            "lte": end_date.format("YYYY-MM-DDTHH:mm:ss"),
                        }
                    }
                },
            ],
        )

        delta_search = delta_search.sort({"period_start": {"order": "asc"}})

        # Build query for this page
        page_search = delta_search.extra(size=page_size)

        # Set timeout
        timeout_value = "120s"
        page_search = page_search.extra(timeout=timeout_value)

        try:
            results = page_search.execute()
            hits = results.to_dict()["hits"]["hits"]

            # Convert hits to documents
            documents = [hit["_source"] for hit in hits]

            return documents

        except Exception as e:
            current_app.logger.error(f"_fetch_daily_deltas_page: Query failed: {e}")
            return []

    def _get_delta_from_buffer(
        self,
        buffer: list,
        target_date: arrow.Arrow,
        community_id: str,
        end_date: arrow.Arrow,
        last_processed_date: arrow.Arrow,
        buffer_size: int,
    ) -> tuple[dict | None, list, arrow.Arrow]:
        """Get the delta document for a specific date from the buffer.

        Args:
            buffer: List of delta documents (sorted by date)
            target_date: The target date to find
            community_id: Community ID for fetching more documents
            end_date: End date for fetching more documents
            last_processed_date: Last date we successfully processed
            buffer_size: Size of buffer to fetch

        Returns:
            Tuple of (delta_document, updated_buffer, updated_last_processed_date)
        """
        target_date_str = target_date.format("YYYY-MM-DD")

        # If buffer is empty, try to fetch more documents from
        # last_processed_date + 1 day
        if not buffer:
            next_date = last_processed_date.shift(days=1)
            buffer = self._fetch_daily_deltas_page(
                community_id, next_date, end_date, buffer_size
            )
            last_processed_date = next_date
            if not buffer:
                return None, buffer, last_processed_date

        # Check the first document in the buffer
        first_doc = buffer[0]
        first_doc_date_str = arrow.get(first_doc["period_start"]).format("YYYY-MM-DD")

        if first_doc_date_str == target_date_str:
            # Found the target date - remove it from buffer and return it
            return first_doc, buffer[1:], last_processed_date
        elif first_doc_date_str < target_date_str:
            # First document is earlier - remove it and recurse
            return self._get_delta_from_buffer(
                buffer[1:],
                target_date,
                community_id,
                end_date,
                last_processed_date,
                buffer_size,
            )
        else:
            # First document is later - target date doesn't exist
            return None, buffer, last_processed_date

    def _build_exhaustive_cache_from_scan(
        self,
        exhaustive_cache: dict,
        community_id: str,
        earliest_date: arrow.Arrow,
        end_date: arrow.Arrow,
    ) -> None:
        """Build exhaustive cache using scan query for memory efficiency.

        Args:
            exhaustive_cache: The exhaustive counts cache to populate
            community_id: The community ID to fetch data for
            earliest_date: The earliest date to fetch
            end_date: The end date to fetch (exclusive)
        """
        index_name = prefix_index(self.delta_index)
        delta_search = Search(using=self.client, index=index_name)
        delta_search = delta_search.query(
            "bool",
            must=[
                {"term": {"community_id": community_id}},
                {
                    "range": {
                        "period_start": {
                            "gte": earliest_date.format("YYYY-MM-DDTHH:mm:ss"),
                            "lt": end_date.format(
                                "YYYY-MM-DDTHH:mm:ss"
                            ),  # Use lt (less than) to exclude end_date
                        }
                    }
                },
            ],
        )

        delta_search = delta_search.sort({"period_start": {"order": "asc"}})

        try:
            # Use scan to process all documents efficiently without loading into memory
            for hit in delta_search.scan():
                doc = hit.to_dict()
                self._update_exhaustive_cache_all_subcounts(exhaustive_cache, doc)

        except Exception as e:
            current_app.logger.error(
                f"_build_exhaustive_cache_from_scan: Scan query failed: {e}"
            )
            raise

    def _update_exhaustive_cache_all_subcounts(
        self, exhaustive_cache: dict, delta_doc: dict
    ) -> None:
        """Update exhaustive cache incrementally with a single delta document.

        Args:
            exhaustive_cache: The exhaustive counts cache to update
            delta_doc: The delta document to add to the cache
        """
        subcounts = delta_doc.get("subcounts", {})
        for subcount_name, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Only process "top" type subcounts in exhaustive cache
            if usage_config.get("snapshot_type", "all") != "top":
                continue

            if subcount_name not in exhaustive_cache:
                exhaustive_cache[subcount_name] = {}

            if subcounts and subcount_name in subcounts:
                self._accumulate_category_in_place(
                    exhaustive_cache[subcount_name], subcounts[subcount_name]
                )
