# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community records snapshot aggregators for tracking cumulative record statistics."""

import arrow
from invenio_search.utils import prefix_index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from .base import CommunitySnapshotAggregatorBase
from .types import (
    RecordDeltaDocument,
    RecordSnapshotDocument,
    RecordSnapshotSubcountItem,
    RecordSnapshotTopSubcounts,
)


class CommunityRecordsSnapshotAggregatorBase(CommunitySnapshotAggregatorBase):
    """Base class for community records snapshot aggregators.

    This class provides common functionality for creating snapshot aggregations
    that track cumulative statistics about records in communities over time.
    """

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        """Initialize the records snapshot aggregator base.

        Args:
            name (str): The name of the aggregator.
            subcount_configs (dict, optional): Subcount configurations. Defaults to
                the global config.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, subcount_configs, *args, **kwargs)
        self.record_index = "rdmrecords-records"
        self.event_index = "stats-community-events"
        self.delta_index = "stats-community-records-delta-created"
        self.first_event_index = "stats-community-records-delta-created"
        self.aggregation_index = "stats-community-records-snapshot-created"
        self.event_date_field = "record_created_date"

    def _check_usage_events_migrated(self) -> None:
        """Override abstract method - checking done in usage delta aggregator."""
        pass

    def _get_latest_delta_date(self, community_id: str) -> arrow.Arrow | None:
        """Get the latest delta record date for dependency checking.
        
        Queries the records delta index directly to find the latest record.
        
        Args:
            community_id: The community ID to check
            
        Returns:
            The latest delta record date, or None if no records exist
        """
        search = (
            Search(using=self.client, index=prefix_index(self.delta_index))
            .query(Q("term", community_id=community_id))
            .extra(size=0)
        )
        search.aggs.bucket("max_date", "max", field="period_start")
        
        result = search.execute()
        
        if not result.aggregations.max_date.value:
            return None
            
        return arrow.get(result.aggregations.max_date.value_as_string)

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
            Search(using=self.client, index=prefix_index(self.event_index))
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
            Search(using=self.client, index=prefix_index(self.event_index))
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
        for subcount_key, config in self.subcount_configs.items():
            if "records" in config and config["records"].get("source_fields"):
                subcounts[subcount_key] = []

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
        """
        for subcount_key, config in self.subcount_configs.items():
            records_config = config.get("records", {})
            if records_config.get("snapshot_type") == "top":

                if subcount_key not in exhaustive_counts_cache:
                    exhaustive_counts_cache[subcount_key] = (
                        self._build_exhaustive_cache(deltas, subcount_key)
                    )
                else:
                    self._update_exhaustive_cache(
                        subcount_key, latest_delta, exhaustive_counts_cache
                    )

                new_dict["subcounts"][subcount_key] = self._select_top_n_from_cache(
                    exhaustive_counts_cache[subcount_key]
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
            """Calculate net value (added - removed) for a field.
            
            Returns:
                int: The net value (added - removed) for the field.
            """
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
        """Update cumulative totals with values from a daily delta document.
        
        Returns:
            RecordSnapshotDocument: The updated snapshot document with cumulative
                totals.
        """
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
        new_dict["total_uploaders"] = (
            new_dict.get("total_uploaders", 0) + delta_doc.get("uploaders", 0)
        )

        # Update "all" subcounts by adding latest delta onto previous snapshot
        for subcount_key, config in self.subcount_configs.items():
            records_config = config.get("records", {})
            if records_config and records_config.get("snapshot_type") == "all":

                previous_subcounts = new_dict.get("subcounts", {}).get(subcount_key, [])

                new_dict["subcounts"][subcount_key] = self._add_delta_to_subcounts(
                    previous_subcounts,
                    delta_doc,
                    subcount_key,
                )

        return new_dict

    def create_agg_dict(  # type: ignore[override]
        self,
        current_day: arrow.Arrow,
        previous_snapshot: RecordSnapshotDocument,
        latest_delta: RecordDeltaDocument,
        deltas: list,
        exhaustive_counts_cache: dict | None = None,
    ) -> RecordSnapshotDocument:
        """Create a dictionary representing the aggregation result for indexing.

        Args:
            current_day (arrow.Arrow): The current day for the snapshot
            previous_snapshot (RecordSnapshotDocument): The previous snapshot
                document to add onto
            latest_delta (RecordDeltaDocument): The latest delta document to add
            deltas (list): All delta documents for top subcounts (from earliest date)
            exhaustive_counts_cache (dict | None): The exhaustive counts cache
            
        Returns:
            RecordSnapshotDocument: The aggregation result for indexing.
        """
        if exhaustive_counts_cache is None:
            exhaustive_counts_cache = {}

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
        """Initialize the records snapshot created aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = "stats-community-records-snapshot-created"
        self.event_index = "stats-community-records-delta-created"
        self.event_date_field = "period_start"
        self.event_community_query_term = lambda community_id: Q(
            "term", community_id=community_id
        )
        self.first_event_index = "stats-community-records-delta-created"
        self.first_event_date_field = "period_start"


class CommunityRecordsSnapshotAddedAggregator(CommunityRecordsSnapshotAggregatorBase):
    """Snapshot aggregator for community records using added dates.

    This class uses the date when records were added to the community as the basis for
    community addition timing.
    """

    def __init__(self, name, *args, **kwargs):
        """Initialize the records snapshot added aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = "stats-community-records-snapshot-added"
        self.event_index = "stats-community-events"
        self.delta_index = "stats-community-records-delta-added"
        self.event_date_field = "event_date"
        self.first_event_index = "stats-community-records-delta-added"
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
        """Initialize the records snapshot published aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = "stats-community-records-snapshot-published"
        self.event_index = "stats-community-events"
        self.delta_index = "stats-community-records-delta-published"
        self.event_date_field = "record_published_date"
        self.first_event_index = "stats-community-records-delta-published"
        self.first_event_date_field = "period_start"

    @property
    def use_published_dates(self):
        """Whether to use published dates for community queries."""
        return True
