# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community records delta aggregators."""

import time
from collections.abc import Generator
from typing import Any

import arrow
from flask import current_app
from invenio_search.utils import prefix_index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from ..queries import CommunityRecordDeltaQuery
from ..config import get_subcount_field, get_subcount_combine_subfields
from .base import CommunityAggregatorBase
from .types import (
    RecordDeltaDocument,
    RecordDeltaSubcountItem,
)


class CommunityRecordsDeltaAggregatorBase(CommunityAggregatorBase):
    """Aggregator for community record deltas.

    Uses the date the record was created as the initial date of the record.
    """

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        """Initialize the records delta aggregator base.

        Args:
            name (str): The name of the aggregator.
            subcount_configs (dict, optional): Subcount configurations. Defaults to
                the global config.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.first_event_index: str = "stats-community-events"
        self.event_index: str = "stats-community-events"
        self.record_index: str = "rdmrecords-records"
        self.aggregation_index: str = "stats-community-records-delta-created"
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNTS"]
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
            search = Search(using=self.client, index=prefix_index(self.event_index))
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
                subcount_key: []
                for subcount_key, config in self.subcount_configs.items()
                if "records" in config
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

    def _make_subcount_list(self, subcount_name, aggs_added, aggs_removed):
        """Make a subcount list for a given subcount type."""
        config = self.subcount_configs.get(subcount_name, {}).get("records", {})

        if not config:
            current_app.logger.error(
                f"No configuration found for subcount type: {subcount_name}"
            )
            return []

        source_fields = config.get("source_fields", [])

        if len(source_fields) > 1:
            return self._process_multi_field_subcount(
                subcount_name, aggs_added, aggs_removed, config
            )
        else:
            return self._process_single_field_subcount(
                subcount_name, aggs_added, aggs_removed, config, 0
            )

    def _process_single_field_subcount(
        self, subcount_name, aggs_added, aggs_removed, config, field_index
    ):
        """Process subcount with single source field."""
        combine_subfields = get_subcount_combine_subfields(config, field_index)
        if combine_subfields:
            all_added_buckets = []
            all_removed_buckets = []

            for field in combine_subfields:
                field_name = field.split(".")[-1]
                if field_index > 0:
                    lookup_name = f"{subcount_name}_{field_index}_{field_name}"
                else:
                    lookup_name = f"{subcount_name}_{field_name}"
                added_buckets = aggs_added.get(lookup_name, {}).get("buckets", [])
                removed_buckets = aggs_removed.get(lookup_name, {}).get("buckets", [])
                all_added_buckets.extend(added_buckets)
                all_removed_buckets.extend(removed_buckets)

            # Deduplicate by key and merge data
            added_items = self._deduplicate_and_merge_buckets(all_added_buckets)
            removed_items = self._deduplicate_and_merge_buckets(all_removed_buckets)
        else:
            added_items = aggs_added.get(subcount_name, {}).get("buckets", [])
            removed_items = aggs_removed.get(subcount_name, {}).get("buckets", [])

        return self._process_single_field_results(
            added_items, removed_items, config, field_index
        )

    def _process_multi_field_subcount(
        self, subcount_type, aggs_added, aggs_removed, config
    ):
        """Process subcount with multiple source fields."""
        source_fields = config.get("source_fields", [])
        agg_results = []

        agg_names = []
        for field_index, source_field in enumerate(source_fields):
            field = get_subcount_field(config, "field", field_index)
            if not field:
                continue
            if field_index > 0:
                agg_names.append(f"{subcount_type}_{field_index}")
            else:
                agg_names.append(subcount_type)

        for agg_name in agg_names:
            field_added = aggs_added.get(agg_name, {}).get("buckets", [])
            field_removed = aggs_removed.get(agg_name, {}).get("buckets", [])

            agg_results.append(
                self._process_single_field_results(
                    field_added, field_removed, config, field_index
                )
            )

        combined_results = self._merge_field_results(agg_results)

        return list(combined_results.values())

    def _process_single_field_results(
        self,
        added_items: list[dict],
        removed_items: list[dict],
        config: dict,
        field_index: int,
    ) -> list[RecordDeltaSubcountItem]:
        """Process results for a single field."""
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
            field = get_subcount_field(config, "field", field_index)
            label_field = get_subcount_field(config, "label_field", field_index)
            if field:
                path_strings.append(field)
                if label_field:
                    path_strings.append(label_field)

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

    def _merge_field_results(
        self, result_lists: list[list[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Merge results from multiple fields."""
        all_result_items = [
            item for result_list in result_lists for item in result_list
        ]

        if not all_result_items:
            return {}

        merged_results: dict[str, Any] = {}
        for item in all_result_items:
            for key, value in item.items():
                if key not in merged_results:
                    merged_results[key] = value
                elif isinstance(value, dict):
                    if isinstance(merged_results[key], dict) and not merged_results[
                        key
                    ].get("label"):
                        merged_results[key]["label"] = value.get("label")
                    merged_results[key] = self._merge_field_results(
                        [[merged_results[key]], [value]]
                    )
                elif isinstance(value, int | float):
                    merged_results[key] += value

        return merged_results

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
                    name: self._make_subcount_list(
                        name,
                        aggs_added,
                        aggs_removed,
                    )
                    for name, config in self.subcount_configs.items()
                    if config.get("records", {})
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
    ) -> Generator[tuple[dict, float], None, None]:
        """Query opensearch for record counts for each day period.

        Args:
            community_id (str): The community id to query.
            start_date (arrow.Arrow): The start date to query.
            end_date (arrow.Arrow): The end date to query.
            first_event_date (arrow.Arrow | None): The first event date, or None
                if no events exist.
            last_event_date (arrow.Arrow | None): The last event date, or None
                if no events exist.

        Returns:
            Generator[tuple[dict, float], None, None]: A generator yielding tuples of
                (document, generation_time) for each day in the period.
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

        total_days_processed = 0
        for year in range(start_date.year, end_date.year + 1):
            year_start_date = max(arrow.get(f"{year}-01-01"), start_date)
            year_end_date = min(arrow.get(f"{year}-12-31"), end_date)

            index_name = prefix_index(f"{self.aggregation_index}-{year}")

            days_in_year = 0
            for day in arrow.Arrow.range("day", year_start_date, year_end_date):
                day_iteration_start_time = time.time()
                day_start_date = day.floor("day")
                days_in_year += 1
                total_days_processed += 1

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

                document_id = f"{community_id}-{day_start_date.format('YYYY-MM-DD')}"

                document = {
                    "_id": document_id,
                    "_index": index_name,
                    "_source": source_content,
                }
                # Log timing for this day iteration
                day_iteration_end_time = time.time()
                day_iteration_duration = (
                    day_iteration_end_time - day_iteration_start_time
                )
                current_app.logger.debug(
                    f"Record day {total_days_processed}: "
                    f"{day_iteration_duration:.2f}s"
                )

                yield (document, day_iteration_duration)


class CommunityRecordsDeltaCreatedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community record deltas.

    Uses the date the record was created as the initial date of the record.
    """

    def __init__(self, name, *args, **kwargs):
        """Initialize the records delta created aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = "stats-community-records-delta-created"
        self.event_date_field = "record_created_date"


class CommunityRecordsDeltaAddedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community records delta added."""

    def __init__(self, name, *args, **kwargs):
        """Initialize the records delta added aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = "stats-community-records-delta-added"
        self.event_date_field = "event_date"


class CommunityRecordsDeltaPublishedAggregator(CommunityRecordsDeltaAggregatorBase):
    """Aggregator for community records delta published."""

    def __init__(self, name, *args, **kwargs):
        """Initialize the records delta published aggregator.

        Args:
            name (str): The name of the aggregator.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        self.aggregation_index = "stats-community-records-delta-published"
        self.event_date_field = "record_published_date"
