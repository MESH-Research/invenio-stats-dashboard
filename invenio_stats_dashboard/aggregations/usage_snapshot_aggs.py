# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community usage snapshot aggregators for tracking cumulative usage statistics."""

import copy
import numbers
import time
from collections.abc import Generator
from pprint import pformat
from typing import Any

import arrow
import psutil
from flask import current_app
from invenio_search.utils import prefix_index
from opensearchpy import AttrDict
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


class MemoryEstimator:
    """Estimate initial memory usage components for a community run."""

    def __init__(self, client, subcount_configs: dict, top_limit: int) -> None:
        """Initialize estimator with client and configuration.

        Args:
            client: OpenSearch client.
            subcount_configs: Subcount configuration mapping.
            top_limit: Configured top-N limit for subcounts.
        """
        self.client = client
        self.subcount_configs = subcount_configs
        self.top_limit = top_limit

    @staticmethod
    def _serialize_len(obj: Any) -> int:
        """Return the byte length of a JSON-serializable object.

        Args:
            obj: Any JSON-serializable Python object.

        Returns:
            int: Number of bytes of the compact serialized representation.
        """
        try:
            import orjson  # local import to avoid import issues in some envs

            return len(orjson.dumps(obj))
        except Exception:
            return len(str(obj).encode("utf-8"))

    def _partition_keys(self) -> tuple[list[str], list[str]]:
        """Partition configured subcount keys into 'all' and 'top' groups.

        Returns:
            tuple[list[str], list[str]]: A tuple of (all_keys, top_keys).
        """
        all_keys: list[str] = []
        top_keys: list[str] = []
        for key, cfg in self.subcount_configs.items():
            stype = cfg.get("usage_events", {}).get("snapshot_type", "all")
            if stype == "all":
                all_keys.append(key)
            elif stype == "top":
                top_keys.append(key)
        return all_keys, top_keys

    def _preflight_delta_info(
        self,
        community_id: str,
        top_keys: list[str],
        all_keys: list[str],
    ) -> tuple[int, int, int, int]:
        """Inspect one delta document to refine per-doc sizes.

        Args:
            community_id: Target community identifier (or "global").
            top_keys: Subcount keys configured as 'top'.
            all_keys: Subcount keys configured as 'all'.

        Returns:
            tuple[int, int, int, int]:
                - per_doc_top_items: Count of 'top' items in the sampled delta.
                - refined_avg_top: Avg bytes per 'top' item from sampling.
                - per_doc_all_items: Count of 'all' items in the sampled delta.
                - refined_avg_all: Avg bytes per 'all' item from sampling.
        """
        try:
            index_name = prefix_index("stats-community-usage-delta")
            s = Search(using=self.client, index=index_name)
            if community_id != "global":
                s = s.query("bool", must=[{"term": {"community_id": community_id}}])
            else:
                s = s.query("match_all")
            includes = ["totals"] + [f"subcounts.{k}" for k in (top_keys + all_keys)]
            s = (
                s.sort({"period_start": {"order": "desc"}})
                .source(includes=includes)
                .extra(size=1)
            )
            hits = s.execute().to_dict().get("hits", {}).get("hits", [])
            if not hits:
                return 0, 1500, 0, 500
            src = hits[0].get("_source", {})
            delta_subcounts = src.get("subcounts", {})
            per_doc_top_items = 0
            per_doc_all_items = 0
            for k in top_keys:
                items = (
                    delta_subcounts.get(k, [])
                    if isinstance(delta_subcounts, dict)
                    else []
                )
                per_doc_top_items += len(items) if isinstance(items, list) else 0
            for k in all_keys:
                items = (
                    delta_subcounts.get(k, [])
                    if isinstance(delta_subcounts, dict)
                    else []
                )
                per_doc_all_items += len(items) if isinstance(items, list) else 0
            top_only = {k: delta_subcounts.get(k, []) for k in top_keys}
            all_only = {k: delta_subcounts.get(k, []) for k in all_keys}
            top_only_bytes = self._serialize_len(top_only)
            all_only_bytes = self._serialize_len(all_only)
            refined_avg_top = (
                int(top_only_bytes / per_doc_top_items) if per_doc_top_items else 1500
            )
            refined_avg_all = (
                int(all_only_bytes / per_doc_all_items) if per_doc_all_items else 500
            )
            return (
                per_doc_top_items,
                refined_avg_top,
                per_doc_all_items,
                refined_avg_all,
            )
        except Exception:
            return 0, 1500, 0, 500

    def estimate(
        self,
        previous_snapshot: UsageSnapshotDocument,
        first_event_date: arrow.Arrow,
        upper_limit: arrow.Arrow,
        planned_scan_page_size: int,
        planned_chunk_size: int,
        planned_delta_buffer_size: int,
    ) -> dict:
        """Compute initial memory usage estimates for the run.

        Args:
            previous_snapshot: The last stored snapshot for this community.
            first_event_date: Earliest date with any usage events.
            upper_limit: Upper bound date for the upcoming run.
            planned_scan_page_size: Planned scan page size for historical scan.
            planned_chunk_size: Planned bulk indexing chunk size.
            planned_delta_buffer_size: Planned in-memory delta buffer size.

        Returns:
            dict: Component byte estimates and predicted peaks with keys:
                - payload_bytes
                - working_all_bytes
                - working_top_bytes
                - scan_page_bytes
                - bulk_buffer_bytes
                - delta_buffer_bytes
                - build_payload_bytes
                - predicted_scan_peak_bytes
                - predicted_loop_peak_bytes
                - predicted_peak_bytes
        """
        k_ws_overhead = current_app.config.get("COMMUNITY_STATS_WS_OVERHEAD", 1.1)
        k_scan_overhead = current_app.config.get("COMMUNITY_STATS_SCAN_OVERHEAD", 1.3)
        k_bulk_overhead = current_app.config.get("COMMUNITY_STATS_BULK_OVERHEAD", 1.3)
        k_delta_overhead = current_app.config.get("COMMUNITY_STATS_DELTA_OVERHEAD", 1.2)
        safety_factor = current_app.config.get("COMMUNITY_STATS_MEM_SAFETY_FACTOR", 1.2)
        growth_factor_top = current_app.config.get(
            "COMMUNITY_STATS_TOP_GROWTH_FACTOR", 3.0
        )
        growth_floor_factor = current_app.config.get(
            "COMMUNITY_STATS_TOP_GROWTH_FLOOR_FACTOR", 5.0
        )
        hard_cap_per_key = current_app.config.get(
            "COMMUNITY_STATS_TOP_HARD_CAP_PER_KEY", 10000
        )
        decay_top = current_app.config.get("COMMUNITY_STATS_TOP_DISCOVERY_DECAY", 0.3)
        avg_delta_bytes = current_app.config.get(
            "COMMUNITY_STATS_AVG_DELTA_BYTES", 1024
        )

        payload_bytes = self._serialize_len(previous_snapshot)
        prev_subcounts = previous_snapshot.get("subcounts", {})  # type: ignore[assignment]
        all_keys, top_keys = self._partition_keys()

        all_projection = {k: prev_subcounts.get(k, []) for k in all_keys}
        all_bytes = self._serialize_len(all_projection)
        working_all_bytes = int(all_bytes * k_ws_overhead)

        top_projection = {
            k: prev_subcounts.get(k, {"by_view": [], "by_download": []})
            for k in top_keys
        }
        top_bytes = self._serialize_len(top_projection)
        total_top_items = 0
        for k in top_keys:
            sc = prev_subcounts.get(k, {})
            byv = sc.get("by_view", []) if isinstance(sc, dict) else []
            byd = sc.get("by_download", []) if isinstance(sc, dict) else []
            total_top_items += len(byv) + len(byd)
        avg_top_item_bytes = (
            int(top_bytes / total_top_items) if total_top_items > 0 else 1500
        )

        try:
            prev_date = arrow.get(previous_snapshot.get("snapshot_date", ""))
        except Exception:
            prev_date = first_event_date
        days_elapsed = max(1, (prev_date - first_event_date).days + 1)
        days_elapsed_for_rate = max(30, days_elapsed)
        days_remaining = max(0, (upper_limit - prev_date).days)

        est_total_top_ids = 0
        for k in top_keys:
            sc = prev_subcounts.get(k, {})
            ids: set[str] = set()
            if isinstance(sc, dict):
                for item in sc.get("by_view", []) or []:
                    try:
                        ids.add(item["id"])  # type: ignore[index]
                    except Exception:
                        continue
                for item in sc.get("by_download", []) or []:
                    try:
                        ids.add(item["id"])  # type: ignore[index]
                    except Exception:
                        continue
            union_count = len(ids)
            union_rate = union_count / days_elapsed_for_rate
            new_ids_est = union_rate * days_remaining * decay_top
            floor_est = self.top_limit * growth_floor_factor
            est_ids = int(
                max(floor_est, (union_count + new_ids_est) * growth_factor_top)
            )
            est_total_top_ids += min(est_ids, hard_cap_per_key)

        working_top_bytes = est_total_top_ids * avg_top_item_bytes

        scan_page_bytes = int(
            planned_scan_page_size * avg_top_item_bytes * k_scan_overhead
        )
        bulk_buffer_bytes = int(planned_chunk_size * payload_bytes * k_bulk_overhead)

        per_doc_top_items, refined_avg_top, per_doc_all_items, refined_avg_all = (
            self._preflight_delta_info(
                previous_snapshot.get("community_id", "global"),  # type: ignore[index]
                top_keys,
                all_keys,
            )
        )
        if per_doc_top_items or per_doc_all_items:
            per_doc_bytes = (
                per_doc_top_items * refined_avg_top
                + per_doc_all_items * refined_avg_all
            )
            scan_page_bytes = int(
                planned_scan_page_size * per_doc_bytes * k_scan_overhead
            )
            delta_buffer_bytes = int(
                planned_delta_buffer_size * per_doc_bytes * k_delta_overhead
            )
        else:
            delta_buffer_bytes = int(
                planned_delta_buffer_size * avg_delta_bytes * k_delta_overhead
            )

        build_payload_bytes = payload_bytes
        predicted_scan_peak = int(
            working_all_bytes + working_top_bytes + scan_page_bytes
        )
        predicted_loop_peak = int(
            bulk_buffer_bytes
            + working_top_bytes
            + working_all_bytes
            + build_payload_bytes
            + delta_buffer_bytes
        )
        predicted_peak = int(
            max(predicted_scan_peak, predicted_loop_peak) * safety_factor
        )

        return_object = {
            "payload_bytes": payload_bytes,
            "working_all_bytes": working_all_bytes,
            "working_top_bytes": working_top_bytes,
            "scan_page_bytes": scan_page_bytes,
            "bulk_buffer_bytes": bulk_buffer_bytes,
            "delta_buffer_bytes": delta_buffer_bytes,
            "build_payload_bytes": build_payload_bytes,
            "predicted_scan_peak_bytes": predicted_scan_peak,
            "predicted_loop_peak_bytes": predicted_loop_peak,
            "predicted_peak_bytes": predicted_peak,
        }
        current_app.logger.info(f"MemoryEstimator returning {pformat(return_object)}")
        return return_object

    @staticmethod
    def adjust_scan_page_size(
        mem_estimate: dict,
        rss_bytes: int,
        budget_bytes: int,
        planned_scan_page_size: int,
        scan_page_size_min: int,
        scan_page_size_max: int,
    ) -> int:
        """Adjust scan page size to fit within memory headroom.

        Uses predicted_peak_bytes from the estimate and current rss/budget to
        reduce page size proportionally when over budget. Always clamps to
        [scan_page_size_min, scan_page_size_max].
        
        Args:
            mem_estimate: Output dict from `estimate()`.
            rss_bytes: Current process RSS in bytes.
            budget_bytes: Effective memory budget in bytes.
            planned_scan_page_size: Current planned page size to consider.
            scan_page_size_min: Minimum allowed page size.
            scan_page_size_max: Maximum allowed page size.

        Returns:
            int: The adjusted page size (possibly unchanged).
        """
        page_size = planned_scan_page_size
        if budget_bytes <= 0:
            return page_size

        predicted_peak = int(mem_estimate.get("predicted_peak_bytes", 0))
        if rss_bytes + predicted_peak <= budget_bytes:
            return page_size

        scan_page_bytes = max(1, int(mem_estimate.get("scan_page_bytes", page_size)))
        if scan_page_bytes <= 0:
            return max(scan_page_size_min, min(page_size, scan_page_size_max))

        free = max(1, budget_bytes - rss_bytes)
        # Upper cap needed to fit within budget if scaling linearly with page size
        derived_cap = max(
            scan_page_size_min,
            int(page_size * (free / float(predicted_peak))),
        )
        # Softer reduction to avoid over-shrinking page size
        scale = (free / float(predicted_peak)) ** 0.5
        proposed = int(page_size * scale)
        new_page_size = max(
            scan_page_size_min,
            min(proposed, scan_page_size_max, derived_cap),
        )
        return new_page_size


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

        # Planned sizing defaults (used for preflight estimation and loop)
        cfg = current_app.config
        self.planned_scan_page_size = int(
            cfg.get("COMMUNITY_STATS_SCAN_PAGE_SIZE", 200)
        )
        # If not explicitly set, default buffer size to scan page size so both
        # phases are capped by the same batch size by default.
        self.delta_buffer_defaulted_to_scan = (
            "COMMUNITY_STATS_DELTA_BUFFER_SIZE" not in cfg
        )
        self.planned_delta_buffer_size = int(
            cfg.get("COMMUNITY_STATS_DELTA_BUFFER_SIZE", self.planned_scan_page_size)
        )
        # current_chunk_size already initialized in base; use as planned
        self.planned_chunk_size = int(self.current_chunk_size)

        # Optional memory headroom controls
        self.scan_page_size_min = int(cfg.get("COMMUNITY_STATS_SCAN_PAGE_SIZE_MIN", 50))
        self.scan_page_size_max = int(
            cfg.get("COMMUNITY_STATS_SCAN_PAGE_SIZE_MAX", 500)
        )
        self.scan_scroll = str(cfg.get("COMMUNITY_STATS_SCAN_SCROLL", "2m"))
        self.mem_budget_bytes = cfg.get("COMMUNITY_STATS_MEM_BUDGET_BYTES")
        self.mem_high_water_percent = float(
            cfg.get("COMMUNITY_STATS_MEM_HIGH_WATER_PERCENT", 0.75)
        )
        # Cache process handle and total memory once
        try:
            self.proc = psutil.Process()
        except Exception:
            self.proc = None  # type: ignore[assignment]
        try:
            self.total_mem = psutil.virtual_memory().total
        except Exception:
            self.total_mem = 0
        # Track adaptive scan page size across helper calls per run
        self._last_effective_scan_page_size: int | None = None
        # Compute effective memory budget once
        if isinstance(self.mem_budget_bytes, int) and self.mem_budget_bytes > 0:
            self.mem_budget_effective = int(self.mem_budget_bytes)
        else:
            self.mem_budget_effective = (
                int(self.total_mem * self.mem_high_water_percent)
                if self.total_mem
                else 0
            )

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
            "snapshot_date": current_day.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
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
        community_id: str,
        latest_delta: UsageDeltaDocument,
        working_state: dict,
    ) -> UsageSnapshotDocument:
        """Update working state and build the daily snapshot document.

        Args:
            current_day (arrow.Arrow): Snapshot date to emit.
            community_id (str): Target community id.
            latest_delta (UsageDeltaDocument): Day's delta to accumulate.
            working_state (dict): Compact per-community state with keys:
                - totals (dict): cumulative view/download totals
                - all (dict[str, dict[str, dict]]): "all" subcounts maps
                - top (dict): exhaustive cache for "top" subcounts

        Returns:
            UsageSnapshotDocument: Fresh document assembled from working state.
        """
        ws_totals = working_state.get("totals", {})
        ws_all = working_state.get("all", {})
        ws_top = working_state.get("top", {})

        self._update_working_totals(ws_totals, latest_delta)
        self._update_working_all(ws_all, latest_delta)
        self._update_working_top(ws_top, latest_delta)

        # Build fresh snapshot document from working state
        out_totals = copy.deepcopy(ws_totals)

        out_subcounts: dict[str, Any] = {}

        # 'all' subcounts: convert map values to lists
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type", "all") == "all":
                sub_map = ws_all.get(subcount_key, {})
                out_subcounts[subcount_key] = list(sub_map.values())

        # 'top' subcounts: select top N from exhaustive cache
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type") == "top":
                cache = ws_top.get(subcount_key, {})
                top_by_view = self._select_top_n_from_cache(cache, "view")
                top_by_download = self._select_top_n_from_cache(cache, "download")
                out_subcounts[subcount_key] = {
                    "by_view": top_by_view,
                    "by_download": top_by_download,
                }

        doc: UsageSnapshotDocument = {
            "community_id": community_id,
            "snapshot_date": current_day.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "totals": out_totals,  # type: ignore[assignment]
            "subcounts": out_subcounts,  # type: ignore[assignment]
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

        return doc

    def _accumulate_category_in_place(
        self, accumulated: dict, category_items: list
    ) -> None:
        """Accumulate category items into the existing accumulated dictionary.

        Args:
            accumulated: Dictionary to accumulate into
            category_items: List of items from a category in a delta document
        """
        for item in category_items:
            # Indexing-only access to support AttrDict without .get
            item_id = item["id"]

            if item_id not in accumulated:
                label_value = ""
                if "label" in item:
                    label_value = item["label"]

                accumulated[item_id] = {
                    "id": item_id,
                    "label": label_value,
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
                if angle in item:
                    for metric, value in item[angle].items():
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

        # Reset adaptive page size tracker for this run
        self._last_effective_scan_page_size = None  # type: ignore[assignment]

        # Preflight: compute adjusted scan page size once (used for scan and buffer)
        adjusted_scan_page_size = self.planned_scan_page_size
        try:
            adjusted_scan_page_size = self._estimate_initial_memory(
                previous_snapshot=previous_snapshot,
                first_event_date=first_event_date,
                upper_limit=end_date,
            )
        except Exception:
            pass

        try:
            # Build top-cache from historical deltas BEFORE current period
            top_cache: dict[str, Any] = {}
            self._build_exhaustive_cache_from_scan(
                top_cache,
                community_id,
                first_event_date,
                current_iteration_date,
                page_size=adjusted_scan_page_size,
            )
        except Exception as e:
            current_app.logger.error(
                "Optimized agg_iter: Failed to initialize exhaustive_counts_cache: %s",
                e,
            )
            return

        working_totals, working_all = self._init_working_state_from_snapshot(
            previous_snapshot
        )
        working_state: dict[str, Any] = {
            "totals": working_totals,
            "all": working_all,
            "top": top_cache,
        }

        daily_deltas_buffer: list[dict] = []
        last_processed_date = first_event_date.shift(
            days=-1
        )  # Start from day before first event
        # Use the same limit for scan pages and the delta buffer
        # Prefer the final adaptive scan size if available, else fall back
        last_effective = getattr(self, "_last_effective_scan_page_size", None)
        buffer_size = (
            last_effective
            if isinstance(last_effective, int)
            else adjusted_scan_page_size
        )

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

                # Use original create_agg_dict entry point for clarity
                source_content = self.create_agg_dict(
                    current_iteration_date,
                    community_id,
                    daily_delta,
                    working_state,
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

                previous_snapshot_date = current_iteration_date
                current_iteration_date = current_iteration_date.shift(days=1)

            except Exception as e:
                current_app.logger.error(
                    "Error processing date "
                    f"{current_iteration_date.format('YYYY-MM-DD')}: {e}"
                )
                current_iteration_date = current_iteration_date.shift(days=1)
                continue

    def _init_working_state_from_snapshot(
        self, previous_snapshot: UsageSnapshotDocument
    ) -> tuple[dict, dict[str, dict[str, dict]]]:
        """Create compact working state (totals + 'all' subcounts maps).

        This method initializes the working state for the portions of the aggregation
        that can be calculated from just the last snapshot and the next delta document,
        without needing to look at historical delta documents. This includes the overall
        totals and the subcounts that are the "all" type--that is, subcounts where each
        document includes all items that have ever been seen for that subcount. "Top"
        subcounts--where each document includes only the top N items to date--cannot be
        calculated without looking at historical delta documents and so are handled
        separately.

        Args:
            previous_snapshot (UsageSnapshotDocument): Last stored snapshot used to
                seed cumulative totals and the "all" subcounts maps.

        Returns:
            tuple[dict, dict[str, dict[str, dict]]]:
                - working_totals: cumulative totals (view/download)
                - working_all: "all" subcounts as maps (key → id → metrics)
        """
        prev_totals = previous_snapshot.get("totals", {})  # type: ignore[assignment]
        working_totals: dict = copy.deepcopy(prev_totals)

        # Build maps for 'all' subcounts only
        working_all: dict[str, dict[str, dict]] = {}
        prev_subcounts = previous_snapshot.get("subcounts", {})  # type: ignore[assignment]
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type", "all") != "all":
                continue
            working_all[subcount_key] = {}
            has_list = isinstance(prev_subcounts, dict) and (
                subcount_key in prev_subcounts
                and isinstance(prev_subcounts[subcount_key], list)
            )
            if has_list:
                for item in prev_subcounts[subcount_key]:
                    try:
                        item_id = item["id"]
                        working_all[subcount_key][item_id] = {
                            "id": item_id,
                            "label": item.get("label", ""),
                            "view": {
                                "total_events": item.get("view", {}).get(
                                    "total_events", 0
                                ),
                                "unique_visitors": item.get("view", {}).get(
                                    "unique_visitors", 0
                                ),
                                "unique_records": item.get("view", {}).get(
                                    "unique_records", 0
                                ),
                                "unique_parents": item.get("view", {}).get(
                                    "unique_parents", 0
                                ),
                            },
                            "download": {
                                "total_events": item.get("download", {}).get(
                                    "total_events", 0
                                ),
                                "unique_visitors": item.get("download", {}).get(
                                    "unique_visitors", 0
                                ),
                                "unique_records": item.get("download", {}).get(
                                    "unique_records", 0
                                ),
                                "unique_parents": item.get("download", {}).get(
                                    "unique_parents", 0
                                ),
                                "unique_files": item.get("download", {}).get(
                                    "unique_files", 0
                                ),
                                "total_volume": item.get("download", {}).get(
                                    "total_volume", 0
                                ),
                            },
                        }
                    except Exception:
                        continue

        return working_totals, working_all

    def _update_working_state_from_delta(
        self,
        working_totals: dict,
        working_all: dict[str, dict[str, dict]],
        working_top: dict[str, dict],
        delta_doc: UsageDeltaDocument,
    ) -> None:
        """Legacy wrapper – no longer used (split into focused helpers)."""
        self._update_working_totals(working_totals, delta_doc)
        self._update_working_all(working_all, delta_doc)
        self._update_working_top(working_top, delta_doc)

    def _update_working_totals(
        self, working_totals: dict, delta_doc: UsageDeltaDocument
    ) -> None:
        """Accumulate daily totals into the working totals dict."""
        delta_totals = delta_doc.get("totals", {})
        for angle in ("view", "download"):
            if angle in delta_totals and isinstance(delta_totals[angle], dict):
                for metric, value in delta_totals[angle].items():
                    if isinstance(value, numbers.Number):
                        working_totals[angle][metric] = (
                            working_totals[angle].get(metric, 0) + value
                        )

    def _update_working_all(
        self, working_all: dict[str, dict[str, dict]], delta_doc: UsageDeltaDocument
    ) -> None:
        """Accumulate daily 'all' subcounts into the working maps."""
        delta_subcounts = delta_doc.get("subcounts", {})
        if not isinstance(delta_subcounts, dict):
            return
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type", "all") != "all":
                continue
            if subcount_key not in delta_subcounts:
                continue
            items = delta_subcounts[subcount_key]
            if not isinstance(items, list):
                continue
            sub_map = working_all.setdefault(subcount_key, {})
            for item in items:
                try:
                    item_id = item["id"]
                except Exception:
                    continue
                entry = sub_map.get(
                    item_id,
                    {
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
                    },
                )
                if "label" in item and not entry.get("label"):
                    entry["label"] = item["label"]
                for angle in ("view", "download"):
                    if angle in item and isinstance(item[angle], dict):
                        for metric, value in item[angle].items():
                            entry[angle][metric] = entry[angle].get(metric, 0) + value
                sub_map[item_id] = entry

    def _update_working_top(
        self, working_top: dict[str, dict], delta_doc: UsageDeltaDocument
    ) -> None:
        """Accumulate daily 'top' subcounts into the exhaustive cache maps."""
        for subcount_key, config in self.subcount_configs.items():
            usage_config = config.get("usage_events", {})
            if usage_config.get("snapshot_type") == "top":
                if subcount_key not in working_top:
                    working_top[subcount_key] = {}
                self._update_exhaustive_cache(subcount_key, delta_doc, working_top)

    def _estimate_initial_memory(
        self,
        previous_snapshot: UsageSnapshotDocument,
        first_event_date: arrow.Arrow,
        upper_limit: arrow.Arrow,
    ) -> int:
        """Return adjusted scan page size based on a one-shot memory estimate."""
        estimator = MemoryEstimator(
            client=self.client,
            subcount_configs=self.subcount_configs,
            top_limit=self.top_subcount_limit,
        )
        mem_estimate = estimator.estimate(
            previous_snapshot=previous_snapshot,
            first_event_date=first_event_date,
            upper_limit=upper_limit,
            planned_scan_page_size=self.planned_scan_page_size,
            planned_chunk_size=self.planned_chunk_size,
            planned_delta_buffer_size=self.planned_delta_buffer_size,
        )

        # Cache for adaptive runtime checks during historical scan
        self._last_mem_estimate = mem_estimate

        try:
            rss = self.proc.memory_info().rss if self.proc else 0  # type: ignore[union-attr]
        except Exception:
            rss = 0
        budget = self.mem_budget_effective

        return MemoryEstimator.adjust_scan_page_size(
            mem_estimate=mem_estimate,
            rss_bytes=rss,
            budget_bytes=budget,
            planned_scan_page_size=self.planned_scan_page_size,
            scan_page_size_min=self.scan_page_size_min,
            scan_page_size_max=self.scan_page_size_max,
        )

    def _iter_deltas_with_memory_guard(
        self,
        community_id: str,
        earliest_date: arrow.Arrow,
        end_date: arrow.Arrow,
        page_size: int,
        includes: list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """Yield delta documents using search_after and adapt page size by RSS.

        Sorts by period_start asc and _id asc, and resumes via search_after.
        Between pages, checks current RSS against the effective budget and, when
        necessary, reduces page size using MemoryEstimator.adjust_scan_page_size.
        """
        index_name = prefix_index(self.delta_index)
        base = Search(using=self.client, index=index_name)
        base = base.query(
            "bool",
            must=[
                {"term": {"community_id": community_id}},
                {
                    "range": {
                        "period_start": {
                            "gte": earliest_date.format("YYYY-MM-DDTHH:mm:ss"),
                            "lt": end_date.format("YYYY-MM-DDTHH:mm:ss"),
                        }
                    }
                },
            ],
        )
        base = base.sort({"period_start": {"order": "asc"}}, {"_id": {"order": "asc"}})
        if includes:
            base = base.source(includes=includes)

        search_after_date: Any = None
        current_page_size = int(page_size)
        # Track latest effective page size for downstream buffer alignment
        self._last_effective_scan_page_size = current_page_size

        while True:
            q = base.extra(size=current_page_size)
            if search_after_date is not None:
                q = q.extra(search_after=search_after_date)

            try:
                resp = q.execute()
                hits = resp.to_dict().get("hits", {}).get("hits", [])
            except Exception as e:
                current_app.logger.error(
                    f"_iter_deltas_with_memory_guard: query failed: {e}"
                )
                return

            if not hits:
                break

            for hit in hits:
                doc = hit.get("_source", {})
                yield doc

            # Prepare resume date for next page
            # NOTE: Assumes only one document per date
            try:
                search_after_date = hits[-1]["sort"]
            except Exception:
                search_after_date = None

            # Memory guard – shrink page size when necessary
            try:
                rss = self.proc.memory_info().rss if self.proc else 0  # type: ignore[union-attr]
                current_app.logger.info(f"RSS memory usage during delta scan: {rss}")
            except Exception as e:
                rss = 0
                current_app.logger.error(
                    f"Error getting RSS memory usage during delta scan: {e}"
                )
            budget = self.mem_budget_effective
            mem_estimate = getattr(self, "_last_mem_estimate", None) or {
                "predicted_peak_bytes": 0,
                "scan_page_bytes": current_page_size,
            }
            new_page = MemoryEstimator.adjust_scan_page_size(
                mem_estimate=mem_estimate,
                rss_bytes=rss,
                budget_bytes=budget,
                planned_scan_page_size=current_page_size,
                scan_page_size_min=self.scan_page_size_min,
                scan_page_size_max=self.scan_page_size_max,
            )
            if new_page < current_page_size:
                current_app.logger.warning(
                    f"Adaptive delta scan: reducing page size from "
                    f"{current_page_size} to {new_page} due to RSS memory usage of "
                    f"{rss} (budget is {budget} bytes)"
                )
                current_page_size = new_page
                self._last_effective_scan_page_size = current_page_size
            else:
                current_app.logger.info(
                    f"RSS memory usage during delta scan: {rss} is within budget of "
                    f"{budget} bytes, no need to reduce page size"
                )

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
        page_size: int,
    ) -> None:
        """Build exhaustive cache using scan query for memory efficiency.

        Args:
            exhaustive_cache: The exhaustive counts cache to populate
            community_id: The community ID to fetch data for
            earliest_date: The earliest date to fetch
            end_date: The end date to fetch (exclusive)
            page_size: Initial page size for the adaptive scan
        """
        try:
            includes: list[str] = []
            for subcount_name, config in self.subcount_configs.items():
                usage_config = config.get("usage_events", {})
                if usage_config.get("snapshot_type", "all") == "top":
                    includes.append(f"subcounts.{subcount_name}")

            for doc in self._iter_deltas_with_memory_guard(
                community_id=community_id,
                earliest_date=earliest_date,
                end_date=end_date,
                page_size=page_size,
                includes=includes if includes else None,
            ):
                self._update_exhaustive_cache_all_subcounts(exhaustive_cache, doc)

        except Exception as e:
            current_app.logger.error(
                f"_build_exhaustive_cache_from_scan: adaptive scan failed: {e}"
            )
            raise

    def _update_exhaustive_cache_all_subcounts(
        self, exhaustive_cache: dict, delta_doc: dict | AttrDict
    ) -> None:
        """Update exhaustive cache incrementally with a single delta document.

        Args:
            exhaustive_cache: The exhaustive counts cache to update
            delta_doc: The delta document to add to the cache
        """
        # Extract subcounts without using .get on AttrDict and without copying
        subcounts = delta_doc["subcounts"] if "subcounts" in delta_doc else {}
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
