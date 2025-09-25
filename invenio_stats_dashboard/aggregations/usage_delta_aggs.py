# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community usage delta aggregators for tracking daily usage statistics."""

import time
from collections.abc import Generator
from itertools import chain
from typing import Any

import arrow
from flask import current_app
from invenio_search.utils import prefix_index
from opensearchpy import AttrDict, AttrList
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from ..queries import CommunityUsageDeltaQuery
from ..utils.utils import (
    get_subcount_combine_subfields,
    get_subcount_field,
    get_subcount_label_includes,
)
from .base import CommunityAggregatorBase
from .types import (
    UsageDeltaDocument,
    UsageSubcountItem,
)


class CommunityUsageDeltaAggregator(CommunityAggregatorBase):
    """Community usage delta aggregator for tracking daily usage statistics.

    This class aggregates daily usage statistics (views and downloads) for communities,
    including both totals and subcounts for various metadata fields.
    """

    def __init__(self, name, subcount_configs=None, *args, **kwargs):
        """Initialize the community usage delta aggregator.

        Args:
            name (str): The name of the aggregator.
            subcount_configs (dict, optional): Subcount configurations. Defaults to
                the global config.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(name, *args, **kwargs)
        # Use provided configs or fall back to class default
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNTS"]
        )
        self.event_index: list[tuple[str, str]] = [
            ("view", "events-stats-record-view"),
            ("download", "events-stats-file-download"),
        ]
        self.first_event_index = "events-stats-record-view"
        self.first_event_date_field = "timestamp"
        self.aggregation_index = "stats-community-usage-delta"
        self.event_date_field = "timestamp"
        self.event_community_query_term = lambda community_id: Q("match_all")
        self.query_builder = CommunityUsageDeltaQuery(client=self.client)

    def _should_skip_aggregation(
        self,
        start_date: arrow.Arrow,
        last_event_date: arrow.Arrow | None,
        community_id: str | None = None,
        **kwargs,
    ) -> bool:
        """Check if aggregation should be skipped due to no usage events in date range.

        This method provides early skip logic for the usage delta aggregator by:
        1. Checking if there are any usage events in the date range for this community
        2. If no events exist, we can skip the expensive processing pipeline entirely

        Args:
            start_date: The start date for aggregation
            last_event_date: The last event date, or None if no events exist
            community_id: The community ID to check (optional, for testing)
            **kwargs: Additional arguments, including end_date

        Returns:
            True if aggregation should be skipped, False otherwise
        """
        end_date = kwargs.get("end_date", start_date)
        if last_event_date is None:
            return True
        if last_event_date < start_date:
            return True

        # For usage delta aggregator, we need to check if there are any actual
        # usage events in the date range for this community
        # This is much faster than the full processing pipeline
        events_found = False
        for _event_type, event_index in self.event_index:
            # Quick check for any events in the date range
            search = Search(using=self.client, index=prefix_index(event_index))
            search = search.filter(
                "range",
                timestamp={
                    "gte": start_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
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

            try:
                if search.count() > 0:
                    events_found = True
                    break
            except Exception:
                # If the index doesn't exist or there's an error, assume no events
                current_app.logger.debug(
                    f"Could not query index {event_index}, assuming no events"
                )
                continue

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
                subcount_name: []
                for subcount_name, config in self.subcount_configs.items()
                if config.get("usage_events", {}).get("source_fields")
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

            source_fields = usage_config.get("source_fields", [])
            if not source_fields:
                continue

            # Process each source field
            for field_index, _source_field in enumerate(source_fields):
                field = get_subcount_field(usage_config, "field", field_index)
                if not field:
                    continue  # Skip fields that don't exist

                # Handle combined subfields (like affiliations.id and affiliations.name)
                combine_subfields = get_subcount_combine_subfields(
                    usage_config, field_index
                )
                if combine_subfields:
                    for field in combine_subfields:
                        field_name = field.split(".")[-1]
                        if field_index > 0:
                            agg_name = f"{subcount_name}_{field_index}_{field_name}"
                        else:
                            agg_name = f"{subcount_name}_{field_name}"

                        # Build the base aggregation
                        agg_config = {
                            "terms": {"field": field, "size": 1000},
                            "aggs": self._get_view_metrics_dict(),
                        }

                        # Add label aggregation if label_field is specified
                        label_field = get_subcount_field(
                            usage_config, "label_field", field_index
                        )
                        if label_field:
                            label_source_includes = get_subcount_label_includes(
                                usage_config, field_index
                            ) or [field]
                            agg_config["aggs"]["label"] = {
                                "top_hits": {
                                    "size": 1,
                                    "_source": {"includes": label_source_includes},
                                }
                            }

                        aggregations[agg_name] = agg_config
                else:
                    # Standard single field aggregation
                    if field_index > 0:
                        agg_name = f"{subcount_name}_{field_index}"
                    else:
                        agg_name = subcount_name

                    # Build the base aggregation
                    agg_config = {
                        "terms": {"field": field, "size": 1000},
                        "aggs": self._get_view_metrics_dict(),
                    }

                    # Add label aggregation if label_field is specified
                    label_field = get_subcount_field(
                        usage_config, "label_field", field_index
                    )
                    if label_field:
                        label_source_includes = get_subcount_label_includes(
                            usage_config, field_index
                        ) or [field]
                        agg_config["aggs"]["label"] = {
                            "top_hits": {
                                "size": 1,
                                "_source": {"includes": label_source_includes},
                            }
                        }

                    aggregations[agg_name] = agg_config

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

            source_fields = usage_config.get("source_fields", [])
            if not source_fields:
                continue

            # Process each source field
            for field_index, _source_field in enumerate(source_fields):
                field = get_subcount_field(usage_config, "field", field_index)
                if not field:
                    continue  # Skip fields that don't exist

                # Handle combined subfields (like affiliations.id and affiliations.name)
                combine_subfields = get_subcount_combine_subfields(
                    usage_config, field_index
                )
                if combine_subfields:
                    for field in combine_subfields:
                        field_name = field.split(".")[-1]
                        if field_index > 0:
                            agg_name = f"{subcount_name}_{field_index}_{field_name}"
                        else:
                            agg_name = f"{subcount_name}_{field_name}"

                        # Build the base aggregation
                        agg_config = {
                            "terms": {"field": field, "size": 1000},
                            "aggs": self._get_download_metrics_dict(),
                        }

                        # Add label aggregation if label_field is specified
                        label_field = get_subcount_field(
                            usage_config, "label_field", field_index
                        )
                        if label_field:
                            label_source_includes = get_subcount_label_includes(
                                usage_config, field_index
                            ) or [field]
                            agg_config["aggs"]["label"] = {
                                "top_hits": {
                                    "size": 1,
                                    "_source": {"includes": label_source_includes},
                                }
                            }

                        aggregations[agg_name] = agg_config
                else:
                    # Standard single field aggregation
                    if field_index > 0:
                        agg_name = f"{subcount_name}_{field_index}"
                    else:
                        agg_name = subcount_name

                    # Build the base aggregation
                    agg_config = {
                        "terms": {"field": field, "size": 1000},
                        "aggs": self._get_download_metrics_dict(),
                    }

                    # Add label aggregation if label_field is specified
                    label_field = get_subcount_field(
                        usage_config, "label_field", field_index
                    )
                    if label_field:
                        label_source_includes = get_subcount_label_includes(
                            usage_config, field_index
                        ) or [field]
                        agg_config["aggs"]["label"] = {
                            "top_hits": {
                                "size": 1,
                                "_source": {"includes": label_source_includes},
                            }
                        }

                    aggregations[agg_name] = agg_config

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

            source_fields = usage_config.get("source_fields", [])
            if not source_fields:
                continue

            # Process each source field
            for field_index, _source_field in enumerate(source_fields):
                # Check if this source field has combine_subfields configuration
                combine_subfields = get_subcount_combine_subfields(
                    usage_config, field_index
                )
                if not combine_subfields or len(combine_subfields) <= 1:
                    continue

                # Build aggregations for each combined subfield
                for field in combine_subfields:
                    field_name = field.split(".")[-1]
                    if field_index > 0:
                        query_name = f"{subcount_name}_{field_index}_{field_name}"
                    else:
                        query_name = f"{subcount_name}_{field_name}"

                    label_source_includes = get_subcount_label_includes(
                        usage_config, field_index
                    )
                    if field not in label_source_includes:
                        label_source_includes.append(field)

                    combined_aggs[query_name] = {
                        "terms": {"field": field, "size": 1000},
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

    def _make_top_level_results(
        self,
        community_id: str,
        date: arrow.Arrow,
        view_results: AttrList | None,
        download_results: AttrList | None,
    ) -> UsageDeltaDocument:
        """Make the top level results for the usage delta document."""
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
        return combined_results

    def _assemble_subcount_items(
        self,
        view_results: AttrList | None,
        download_results: AttrList | None,
        usage_config: dict,
        subcount_name: str,
        index: int = 0,
    ) -> list[UsageSubcountItem]:
        """Assemble subcount items from view and download results."""
        assembled_results: list[UsageSubcountItem] = []

        view_buckets = []
        if view_results and hasattr(view_results.aggregations, subcount_name):
            view_agg = getattr(view_results.aggregations, subcount_name)
            view_buckets = view_agg.buckets

        download_buckets = []
        if download_results and hasattr(download_results.aggregations, subcount_name):
            download_agg = getattr(download_results.aggregations, subcount_name)
            download_buckets = download_agg.buckets

        all_keys = set()
        for view_bucket in view_buckets:
            all_keys.add(view_bucket.key)
        for download_bucket in download_buckets:
            all_keys.add(download_bucket.key)

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

            label: str | dict[str, str] = str(key)
            label_field = get_subcount_field(usage_config, "label_field", index)

            if label_field:
                for bucket in [view_bucket, download_bucket]:
                    if (
                        bucket
                        and hasattr(bucket, "label")
                        and hasattr(bucket.label, "hits")
                    ):
                        title_hits = bucket.label.hits.hits
                        if title_hits and title_hits[0]._source:
                            source: AttrDict = title_hits[0]._source
                            # Convert AttrDict to regular dict
                            if hasattr(source, "to_dict"):
                                source_dict = source.to_dict()
                            else:
                                source_dict = dict(source)
                            label_result = CommunityUsageDeltaAggregator._extract_label_from_source(  # noqa: E501
                                source_dict, label_field, key
                            )
                            if isinstance(label_result, str | dict) and label_result:
                                label = label_result
                                break  # Found valid label, stop checking

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

            if view_bucket:
                subcount_item["view"] = {
                    "total_events": view_bucket.doc_count,
                    "unique_visitors": view_bucket.unique_visitors.value,
                    "unique_records": view_bucket.unique_records.value,
                    "unique_parents": view_bucket.unique_parents.value,
                }

            if download_bucket:
                subcount_item["download"] = {
                    "total_events": download_bucket.doc_count,
                    "unique_visitors": download_bucket.unique_visitors.value,
                    "unique_records": download_bucket.unique_records.value,
                    "unique_parents": download_bucket.unique_parents.value,
                    "unique_files": download_bucket.unique_files.value,
                    "total_volume": download_bucket.total_volume.value,
                }

            assembled_results.append(subcount_item)

        return assembled_results

    def _merge_field_results(
        self, item_sets: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Merge results from multiple fields."""
        all_result_items = [item for item_set in item_sets for item in item_set]

        if not all_result_items:
            return []

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
                    merged_results[key] = self._merge_field_results([
                        [merged_results[key]],
                        [value],
                    ])
                elif isinstance(value, int | float):
                    merged_results[key] += value

        return list(merged_results.values())

    def create_agg_dict(
        self,
        view_results: AttrList | None,
        download_results: AttrList | None,
        community_id: str,
        date: arrow.Arrow,
        index: int = 0,
    ) -> UsageDeltaDocument:
        """Combine results from separate view and download queries.

        Args:
            view_results: Results from view query (or None).
            download_results: Results from download query (or None).
            community_id (str): The community ID.
            date (arrow.Arrow): The date for the aggregation.
            index (int): The index in the subcount config's source fields
                list


        Returns:
            UsageDeltaDocument: Combined aggregation document.
        """
        combined_results = self._make_top_level_results(
            community_id, date, view_results, download_results
        )

        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            source_fields = usage_config.get("source_fields", [])
            if not source_fields:
                continue
            item_sets: list[list[UsageSubcountItem]] = []

            for field_index, _source_field in enumerate(source_fields):
                if field_index > 0:
                    subcount_name = f"{subcount_key}_{field_index}"
                else:
                    subcount_name = subcount_key

                combine_subfields = get_subcount_combine_subfields(config, field_index)
                if combine_subfields:
                    item_sets.append(  # type: ignore
                        self._combine_split_aggregations(
                            view_results,
                            download_results,
                            usage_config,
                            subcount_name,
                            field_index,
                        )
                    )
                else:
                    item_sets.append(  # type: ignore
                        self._assemble_subcount_items(
                            view_results,
                            download_results,
                            usage_config,
                            subcount_name,
                            index,
                        )
                    )
            if len(item_sets) > 1:
                combined_results["subcounts"][subcount_name] = (  # type: ignore
                    self._merge_field_results(item_sets)  # type: ignore
                )
            else:
                combined_results["subcounts"][subcount_name] = item_sets[0]  # type: ignore  # noqa: E501

        return combined_results

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        first_event_date: arrow.Arrow | None,
        last_event_date: arrow.Arrow | None,
    ) -> Generator[tuple[dict, float], None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        # Check if we should skip aggregation due to no events after start_date
        should_skip = self._should_skip_aggregation(
            start_date, last_event_date, community_id, end_date=end_date
        )
        if should_skip:
            current_app.logger.warning(
                f"Skipping usage delta aggregation for {community_id} - "
                f"no events after {start_date}"
            )

        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)

        current_iteration_date = start_date

        iteration_count = 0

        while current_iteration_date <= end_date:
            iteration_start_time = time.time()
            iteration_count += 1

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
                f"{self.aggregation_index}-{current_iteration_date.year}"
            )
            doc_id = f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"

            document = {
                "_id": doc_id,
                "_index": index_name,
                "_source": source_content,
            }
            # Log timing for this iteration
            iteration_end_time = time.time()
            iteration_duration = iteration_end_time - iteration_start_time
            yield (document, iteration_duration)

            current_iteration_date = current_iteration_date.shift(days=1)

    def _combine_split_aggregations(
        self, view_results, download_results, config, subcount_name, field_index=0
    ):
        """Combine separate id and name aggregations for funders and affiliations.

        This method handles the case where we have separate aggregations for id and name
        fields (e.g., funders_id and funders_name) and need to combine them into
        a single list, deduplicating based on unique combinations of id and name.

        Args:
            view_results: Results from view query (or None).
            download_results: Results from download query (or None).
            config: Configuration for the subcount.
            subcount_name: Name of the subcount being processed.
            field_index: Index of the source_fields entry being processed.

        Returns:
            list: Combined and deduplicated subcount items.
        """
        combine_subfields = get_subcount_combine_subfields(config, field_index)

        if not combine_subfields or len(combine_subfields) <= 1:
            return []

        agg_names = []
        for subfield in combine_subfields:
            agg_name = f"{subcount_name}_{subfield.split('.')[-1]}"
            agg_names.append(agg_name)

        if len(agg_names) >= 2:
            id_agg_name = agg_names[0]
            name_agg_name = agg_names[1]
        else:
            return []
        buckets = self._get_id_name_buckets(
            view_results, download_results, id_agg_name, name_agg_name
        )
        combined_items = {}
        for bucket_type, bucket, agg_type in buckets:
            id_field_path = next(
                (
                    path
                    for path in get_subcount_label_includes(config, 0)
                    if "id" in path
                ),
                "id",
            )
            name_field_path = next(
                (
                    path
                    for path in get_subcount_label_includes(config, 0)
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
                    id_and_label["id"],
                    id_and_label["label"],  # type: ignore
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
                    isinstance(field_data, list | AttrList)
                    and field_data
                    and isinstance(field_data[0], list | AttrList)
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
                    isinstance(field_data, list | AttrList)
                    and field_data
                    and isinstance(field_data[0], list | AttrList)
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
                if isinstance(value, dict | AttrDict) and part in value:
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
            return result if isinstance(result, str | dict) else str(bucket_key)

        parts = title_field.split(".")

        # The first part should be the array field (e.g., "subjects")
        array_field = parts[0]
        if array_field not in source:
            return str(bucket_key)

        field_value = source[array_field]

        if not isinstance(field_value, list):
            if len(parts) == 1:
                return (
                    field_value
                    if isinstance(field_value, str | dict)
                    else str(field_value)
                )
            else:
                label_path = parts[1:]
                value = field_value
                for part in label_path:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = ""
                        break
                return (
                    value
                    if isinstance(value, str | dict) and value
                    else str(bucket_key)
                )

        if isinstance(field_value, list) and len(field_value) > 0:
            label_path_leaf = parts[1:] if len(parts) > 1 else []
            label = CommunityAggregatorBase._find_matching_item_by_key(
                field_value, label_path_leaf, bucket_key
            )
            if label and isinstance(label, str | dict):
                return label
            else:
                return str(bucket_key)

        return str(bucket_key)
