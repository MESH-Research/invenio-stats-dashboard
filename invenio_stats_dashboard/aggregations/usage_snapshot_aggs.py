# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community usage snapshot aggregators for tracking cumulative usage statistics."""

import numbers

import arrow
from flask import current_app
from invenio_search.proxies import current_search_client

from ..queries import (
    CommunityUsageSnapshotQuery,
)
from .base import CommunitySnapshotAggregatorBase
from .bookmarks import CommunityBookmarkAPI
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
        exhaustive_counts_cache: dict | None = None,
    ) -> UsageSnapshotDocument:
        """Create the final aggregation document from cumulative totals.

        Args:
            current_day (arrow.Arrow): The current day for the snapshot
            previous_snapshot (UsageSnapshotDocument): The previous snapshot document
            latest_delta (UsageDeltaDocument): The latest delta document
            deltas (list): All delta documents for top subcounts
            exhaustive_counts_cache (dict | None): The exhaustive counts cache
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
            current_app.logger.info(
                f"Usage delta aggregator for {community_id} has not processed "
                f"data for the requested period. Delta bookmark: "
                f"{delta_bookmark_date.date()}, Snapshot start_date: "
                f"{start_date.date()}. Skipping snapshot aggregation."
            )
            return False

        return True

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
            deltas: The daily delta dictionaries to update the subcounts with.
                These are the daily delta records for the community between
                the first delta document and the current date.
            exhaustive_counts_cache: The exhaustive counts cache
            latest_delta: The latest delta document

        Returns:
            The updated aggregation dictionary with the new top subcounts.
        """
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type") == "top":
                # Use the subcount key directly
                top_subcount_name = subcount_key

                if top_subcount_name not in exhaustive_counts_cache:
                    exhaustive_counts_cache[top_subcount_name] = (
                        self._build_exhaustive_cache(deltas, top_subcount_name)
                    )
                else:
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
        """Check if a subcount is configured as 'top' type."""
        config = self.subcount_configs.get(subcount_name, {})
        usage_config = config.get("usage_events", {})
        snapshot_type = usage_config.get("snapshot_type", "all")
        return str(snapshot_type) == "top"
