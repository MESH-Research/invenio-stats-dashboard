# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

import time
from collections.abc import Generator

import arrow
from flask import current_app
from invenio_search.utils import prefix_index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from ..queries import (
    CommunityRecordDeltaQuery,
)
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
    ) -> Generator[tuple[dict, float], None, None]:
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
        # Start timing the agg_iter method
        agg_iter_start_time = time.time()
        current_app.logger.debug(f"Record delta agg_iter {community_id}")

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

        # Time the main year loop
        year_loop_start_time = time.time()
        total_days_processed = 0
        for year in range(start_date.year, end_date.year + 1):
            year_start_time = time.time()
            year_start_date = max(arrow.get(f"{year}-01-01"), start_date)
            year_end_date = min(arrow.get(f"{year}-12-31"), end_date)

            index_name = prefix_index("{0}-{1}".format(self.aggregation_index, year))

            # Time the day loop for this year
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

                # Check if an aggregation already exists for this date
                # If it does, delete it (we'll re-create it below)
                document_id = f"{community_id}-{day_start_date.format('YYYY-MM-DD')}"
                if self.client.exists(index=index_name, id=document_id):
                    self.delete_aggregation(index_name, document_id)

                # Process the current date even if there are no buckets
                # so that we have a record for every day in the period
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

            # Log timing for this year
            year_end_time = time.time()
            year_duration = year_end_time - year_start_time
            current_app.logger.debug(
                f"Year {year}: {days_in_year} days, {year_duration:.2f}s"
            )

        # Log total timing for the year loop
        year_loop_end_time = time.time()
        year_loop_duration = year_loop_end_time - year_loop_start_time
        current_app.logger.debug(
            f"Record delta total: {total_days_processed} days, "
            f"{year_loop_duration:.2f}s"
        )

        # Log total timing for agg_iter
        agg_iter_end_time = time.time()
        agg_iter_duration = agg_iter_end_time - agg_iter_start_time
        current_app.logger.debug(
            f"Record delta agg_iter {community_id}: {agg_iter_duration:.2f}s"
        )


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
