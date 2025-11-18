# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Unit tests for memory estimator utilities in usage snapshot aggregator.

These tests validate that the estimator returns all expected keys, produces
non-negative integer byte counts, and that predicted peaks scale up when the
planned sizes (scan page, bulk chunk, delta buffer) are increased.
"""

from types import SimpleNamespace

import arrow
import orjson
import pytest

from invenio_stats_dashboard.aggregations.usage_snapshot_aggs import (
    CommunityUsageSnapshotAggregator,
    UsageSnapshotMemoryEstimator,
)


@pytest.fixture
def make_items():
    """Factory to create 'all' subcount items with simple metrics.

    Returns:
        Callable: factory function that builds item lists.
    """

    def _make_items(n: int, prefix: str) -> list[dict]:
        return [
            {
                "id": f"{prefix}{i}",
                "label": f"{prefix}_label_{i}",
                "view": {"total_events": i + 1},
                "download": {"total_events": (i % 3) + 1},
            }
            for i in range(n)
        ]

    return _make_items


@pytest.fixture
def make_top():
    """Factory to create 'top' subcount structures for view/download.

    Returns:
        Callable: factory function that builds top structures.
    """

    def _make_top(n: int, prefix: str) -> dict:
        return {
            "by_view": [
                {"id": f"{prefix}v{i}", "view": {"total_events": i + 1}}
                for i in range(n)
            ],
            "by_download": [
                {
                    "id": f"{prefix}d{i}",
                    "download": {"total_events": (i % 5) + 1},
                }
                for i in range(n)
            ],
        }

    return _make_top


@pytest.fixture
def prev_snapshot_large(make_items, make_top):
    """Realistic previous snapshot with larger subcounts for sizing.

    Returns:
        dict: snapshot document.
    """
    return {
        "community_id": "global",
        "snapshot_date": arrow.utcnow()
        .shift(days=-1)
        .floor("day")
        .format("YYYY-MM-DDTHH:mm:ss"),
        "totals": {
            "view": {
                "total_events": 10,
                "unique_visitors": 5,
                "unique_records": 4,
                "unique_parents": 3,
            },
            "download": {
                "total_events": 7,
                "unique_visitors": 5,
                "unique_records": 3,
                "unique_parents": 2,
                "unique_files": 2,
                "total_volume": 123.45,
            },
        },
        "subcounts": {
            "resource_types": make_items(44, "rt_"),
            "access_statuses": make_items(4, "as_"),
            "file_types": make_items(23, "ft_"),
            "languages": make_top(20, "lang_"),
            "countries": make_top(20, "ctry_"),
        },
    }


@pytest.fixture
def prev_snapshot_small(make_items, make_top):
    """Smaller previous snapshot used for preflight refinement tests.

    Returns:
        dict: snapshot document.
    """
    return {
        "community_id": "global",
        "snapshot_date": arrow.utcnow()
        .shift(days=-1)
        .floor("day")
        .format("YYYY-MM-DDTHH:mm:ss"),
        "totals": {
            "view": {"total_events": 1},
            "download": {"total_events": 1, "total_volume": 1.0},
        },
        "subcounts": {
            "resource_types": make_items(3, "rt_"),
            "access_statuses": make_items(2, "as_"),
            "file_types": make_items(2, "ft_"),
            "languages": make_top(5, "lang_"),
            "countries": make_top(5, "ctry_"),
        },
    }


@pytest.fixture
def fake_search_empty_class():
    """Fake Search class that returns no hits for preflight.

    Returns:
        type: fake Search class.
    """

    class FakeResultEmpty:
        def to_dict(self):
            return {"hits": {"hits": []}}

    class FakeSearchEmpty:
        def __init__(self, using=None, index=None):
            self._using = using
            self._index = index

        def query(self, *args, **kwargs):
            return self

        def sort(self, *args, **kwargs):
            return self

        def source(self, *args, **kwargs):
            return self

        def extra(self, *args, **kwargs):
            return self

        def params(self, *args, **kwargs):
            return self

        def execute(self):
            return FakeResultEmpty()

    return FakeSearchEmpty


@pytest.fixture
def preflight_delta_payload():
    """Construct a single-hit delta payload with realistic subcount counts.

    Returns:
        dict: delta subcounts payload.
    """
    # Top subcounts counts from user:
    # languages 38, subjects 1500, publishers 1200,
    # countries 128, referrers 1350
    delta_top_languages = [
        {"id": f"lang{i}", "view": {"total_events": i + 1}} for i in range(38)
    ]
    delta_top_subjects = [
        {"id": f"subj{i}", "view": {"total_events": (i % 5) + 1}} for i in range(1500)
    ]
    delta_top_publishers = [
        {
            "id": f"pub{i}",
            "download": {"total_events": (i % 7) + 1},
        }
        for i in range(1200)
    ]
    delta_top_countries = [
        {
            "id": f"ctry{i}",
            "download": {"total_events": i + 1},
        }
        for i in range(128)
    ]
    delta_top_referrers = [
        {"id": f"ref{i}", "view": {"total_events": (i % 3) + 1}} for i in range(1350)
    ]

    # All subcounts counts from user:
    # resource_types 46, access_statuses 4, file_types 29
    delta_all_resource_types = [
        {"id": f"rt{i}", "view": {"total_events": 1}} for i in range(46)
    ]
    delta_all_access = [
        {"id": f"as{i}", "download": {"total_events": 1}} for i in range(4)
    ]
    delta_all_file_types = [
        {"id": f"ft{i}", "view": {"total_events": 1}} for i in range(29)
    ]
    return {
        "languages": delta_top_languages,
        "subjects": delta_top_subjects,
        "publishers": delta_top_publishers,
        "countries": delta_top_countries,
        "referrers": delta_top_referrers,
        "resource_types": delta_all_resource_types,
        "access_statuses": delta_all_access,
        "file_types": delta_all_file_types,
    }


@pytest.fixture
def fake_search_one_class(preflight_delta_payload):
    """Fake Search class that returns one hit with controlled subcounts.

    Returns:
        type: fake Search class.
    """

    class FakeResultOne:
        def to_dict(self):
            return {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "totals": {"view": {"total_events": 1}},
                                "subcounts": preflight_delta_payload,
                            }
                        }
                    ]
                }
            }

    class FakeSearchOne:
        def __init__(self, using=None, index=None):
            self._using = using
            self._index = index

        def query(self, *args, **kwargs):
            return self

        def sort(self, *args, **kwargs):
            return self

        def source(self, *args, **kwargs):
            return self

        def extra(self, *args, **kwargs):
            return self

        def params(self, *args, **kwargs):
            return self

        def execute(self):
            return FakeResultOne()

    return FakeSearchOne


class TestMemoryEstimator:
    """Unit tests for the initial memory estimator helper."""

    def test_estimate_initial_memory_basic(self, running_app, prev_snapshot_large):
        """Basic estimator returns expected keys and scales with planned sizes."""
        app = running_app.app
        with app.app_context():
            subcfg = app.config.setdefault("COMMUNITY_STATS_SUBCOUNTS", {})
            top_limit = app.config.get("COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT", 20)
        estimator = UsageSnapshotMemoryEstimator(
            client=None,
            subcount_configs=subcfg,
            top_limit=top_limit,
        )

        first_event_date = arrow.utcnow().shift(days=-30).floor("day")
        upper_limit = arrow.utcnow().floor("day")

        est = estimator.estimate(
            previous_snapshot=prev_snapshot_large,  # type: ignore[arg-type]
            first_event_date=first_event_date,
            upper_limit=upper_limit,
            planned_scan_page_size=200,
            planned_chunk_size=50,
            planned_delta_buffer_size=50,
        )

        # Sanity checks: keys exist and values are non-negative ints
        required_keys = [
            "payload_bytes",
            "all_subcount_working_state_bytes",
            "scan_page_bytes",
            "indexing_buffer_bytes",
            "delta_buffer_bytes",
            "build_payload_bytes",
            "exhaustive_cache_bytes",
            "predicted_scan_peak_bytes",
            "predicted_loop_peak_bytes",
            "predicted_peak_bytes",
        ]
        for k in required_keys:
            assert k in est
            assert isinstance(est[k], int)
            assert est[k] >= 0

        # Peak must be at least as large as each component group
        assert est["predicted_peak_bytes"] >= est["predicted_scan_peak_bytes"]
        assert est["predicted_peak_bytes"] >= est["predicted_loop_peak_bytes"]
        
        # Verify exhaustive_cache_bytes is included in peaks
        assert est["exhaustive_cache_bytes"] >= 0
        assert est["predicted_scan_peak_bytes"] >= est["exhaustive_cache_bytes"]
        assert est["predicted_loop_peak_bytes"] >= est["exhaustive_cache_bytes"]

        # If we increase planned sizes, peaks should not decrease
        est2 = estimator.estimate(
            previous_snapshot=prev_snapshot_large,  # type: ignore[arg-type]
            first_event_date=first_event_date,
            upper_limit=upper_limit,
            planned_scan_page_size=400,
            planned_chunk_size=100,
            planned_delta_buffer_size=100,
        )
        assert est2["predicted_peak_bytes"] >= est["predicted_peak_bytes"]

    def test_estimate_initial_memory_preflight_refines_sizes(
        self,
        running_app,
        monkeypatch,
        prev_snapshot_small,
        fake_search_empty_class,
        fake_search_one_class,
        set_app_config_fn_scoped,
    ):
        """Preflight one-hit search should refine scan and delta buffer sizing."""
        app = running_app.app
        set_app_config_fn_scoped(
            # Configure subcounts to match our preflight payload keys exactly
            {
                "COMMUNITY_STATS_SUBCOUNTS": {
                    "resource_types": {"usage_events": {"snapshot_type": "all"}},
                    "access_statuses": {"usage_events": {"snapshot_type": "all"}},
                    "file_types": {"usage_events": {"snapshot_type": "all"}},
                    "languages": {"usage_events": {"snapshot_type": "top"}},
                    "subjects": {"usage_events": {"snapshot_type": "top"}},
                    "publishers": {"usage_events": {"snapshot_type": "top"}},
                    "countries": {"usage_events": {"snapshot_type": "top"}},
                    "referrers": {"usage_events": {"snapshot_type": "top"}},
                },
                "COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT": 20,
                "COMMUNITY_STATS_TOP_GROWTH_FACTOR": 1.0,
                "COMMUNITY_STATS_TOP_GROWTH_FLOOR_FACTOR": 1.0,
                "COMMUNITY_STATS_TOP_HARD_CAP_PER_KEY": 100000,
                "COMMUNITY_STATS_TOP_DISCOVERY_DECAY": 0.0,
                "COMMUNITY_STATS_WS_OVERHEAD": 1.1,
                "COMMUNITY_STATS_SCAN_OVERHEAD": 1.3,
                "COMMUNITY_STATS_BULK_OVERHEAD": 1.3,
                "COMMUNITY_STATS_DELTA_OVERHEAD": 1.2,
                "COMMUNITY_STATS_MEM_SAFETY_FACTOR": 1.2,
            }
        )
        top_limit = app.config.get("COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT", 20)
        subcfg = app.config.get("COMMUNITY_STATS_SUBCOUNTS", {})
        estimator = UsageSnapshotMemoryEstimator(
            client=None,
            subcount_configs=subcfg,
            top_limit=top_limit,
        )

        first_event_date = arrow.utcnow().shift(days=-10).floor("day")
        upper_limit = arrow.utcnow().floor("day")

        # Baseline with empty preflight (no hits)
        with app.app_context():
            monkeypatch.setattr(
                "invenio_stats_dashboard.aggregations.usage_snapshot_aggs.Search",
                fake_search_empty_class,
            )
            est_empty = estimator.estimate(
                previous_snapshot=prev_snapshot_small,  # type: ignore[arg-type]
                first_event_date=first_event_date,
                upper_limit=upper_limit,
                planned_scan_page_size=200,
                planned_chunk_size=50,
                planned_delta_buffer_size=50,
            )

        with app.app_context():
            monkeypatch.setattr(
                "invenio_stats_dashboard.aggregations.usage_snapshot_aggs.Search",
                fake_search_one_class,
            )
            planned_scan = 200
            planned_chunk = 50
            planned_delta_buf = 50
            est_refined = estimator.estimate(
                previous_snapshot=prev_snapshot_small,  # type: ignore[arg-type]
                first_event_date=first_event_date,
                upper_limit=upper_limit,
                planned_scan_page_size=planned_scan,
                planned_chunk_size=planned_chunk,
                planned_delta_buffer_size=planned_delta_buf,
            )

            # Compute expected refined averages and all components
            top_keys = [
                k
                for k, v in subcfg.items()
                if v.get("usage_events", {}).get("snapshot_type") == "top"
            ]
            all_keys = [
                k
                for k, v in subcfg.items()
                if v.get("usage_events", {}).get("snapshot_type") == "all"
            ]
            # Build top_only and all_only from the preflight payload fixture
            # used inside fake_search_one_class
            # We reconstruct it here to compute sizes identically
            preflight = {
                "languages": [
                    {"id": f"lang{i}", "view": {"total_events": i + 1}}
                    for i in range(38)
                ],
                "subjects": [
                    {
                        "id": f"subj{i}",
                        "view": {"total_events": (i % 5) + 1},
                    }
                    for i in range(1500)
                ],
                "publishers": [
                    {
                        "id": f"pub{i}",
                        "download": {"total_events": (i % 7) + 1},
                    }
                    for i in range(1200)
                ],
                "countries": [
                    {
                        "id": f"ctry{i}",
                        "download": {"total_events": i + 1},
                    }
                    for i in range(128)
                ],
                "referrers": [
                    {
                        "id": f"ref{i}",
                        "view": {"total_events": (i % 3) + 1},
                    }
                    for i in range(1350)
                ],
                "resource_types": [
                    {"id": f"rt{i}", "view": {"total_events": 1}} for i in range(46)
                ],
                "access_statuses": [
                    {"id": f"as{i}", "download": {"total_events": 1}} for i in range(4)
                ],
                "file_types": [
                    {"id": f"ft{i}", "view": {"total_events": 1}} for i in range(29)
                ],
            }
            top_only = {k: preflight[k] for k in top_keys}
            all_only = {k: preflight[k] for k in all_keys}
            per_doc_top_items = sum(len(v) for v in top_only.values())
            per_doc_all_items = sum(len(v) for v in all_only.values())
            assert per_doc_top_items == 4216
            assert per_doc_all_items == 79

            refined_avg_top = int(len(orjson.dumps(top_only)) / per_doc_top_items)
            refined_avg_all = int(len(orjson.dumps(all_only)) / per_doc_all_items)
            k_scan_overhead = app.config["COMMUNITY_STATS_SCAN_OVERHEAD"]
            k_delta_overhead = app.config["COMMUNITY_STATS_DELTA_OVERHEAD"]
            k_bulk_overhead = app.config["COMMUNITY_STATS_BULK_OVERHEAD"]
            k_ws_overhead = app.config["COMMUNITY_STATS_WS_OVERHEAD"]
            inmemory_factor = float(
                app.config.get("COMMUNITY_STATS_INMEMORY_MULTIPLIER", 4.0)
            )

            expected_per_doc_bytes_serialized = (
                per_doc_top_items * refined_avg_top
                + per_doc_all_items * refined_avg_all
            )
            # Account for inmemory_factor in per_delta_bytes calculation
            expected_per_doc_bytes = int(
                expected_per_doc_bytes_serialized * inmemory_factor
            )
            expected_scan_page_bytes = int(
                planned_scan * expected_per_doc_bytes * k_scan_overhead
            )
            expected_delta_buffer_bytes = int(
                planned_delta_buf * expected_per_doc_bytes * k_delta_overhead
            )

            # Payload and working sets from previous snapshot
            payload_bytes_serialized = len(orjson.dumps(prev_snapshot_small))
            # Account for inmemory_factor in payload_bytes
            payload_bytes = int(payload_bytes_serialized * inmemory_factor)
            all_projection = {
                k: prev_snapshot_small["subcounts"].get(k, []) for k in all_keys
            }
            working_all_bytes_serialized = int(
                len(orjson.dumps(all_projection)) * k_ws_overhead
            )
            # Account for inmemory_factor in working_all_bytes
            working_all_bytes = int(working_all_bytes_serialized * inmemory_factor)

            indexing_buffer_bytes = int(planned_chunk * payload_bytes * k_bulk_overhead)
            build_payload_bytes = payload_bytes
            
            # Compute expected exhaustive cache bytes
            # Get current unique items from previous snapshot for each top key
            prev_subcounts = prev_snapshot_small.get("subcounts", {})
            est_total_unique_items = 0
            top_limit = app.config.get("COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT", 20)
            growth_factor = app.config.get(
                "COMMUNITY_STATS_TOP_GROWTH_FACTOR", 1.0
            )
            growth_floor = app.config.get(
                "COMMUNITY_STATS_TOP_GROWTH_FLOOR_FACTOR", 1.0
            )
            decay = app.config.get("COMMUNITY_STATS_TOP_DISCOVERY_DECAY", 0.0)
            
            # Get date range info
            try:
                prev_date = arrow.get(prev_snapshot_small.get("snapshot_date", ""))
            except Exception:
                prev_date = first_event_date
            days_elapsed = max(1, (prev_date - first_event_date).days + 1)
            days_remaining = max(0, (upper_limit - prev_date).days)
            
            # Compute for each top key
            # Use the avg size from the preflight data
            avg_item_bytes = refined_avg_top
            for k in top_keys:
                sc = prev_subcounts.get(k, {})
                unique_ids = set()
                if isinstance(sc, dict):
                    for item in sc.get("by_view", []) or []:
                        try:
                            unique_ids.add(item["id"])
                        except Exception:
                            continue
                    for item in sc.get("by_download", []) or []:
                        try:
                            unique_ids.add(item["id"])
                        except Exception:
                            continue
                union_count = len(unique_ids)
                union_rate = union_count / max(30, days_elapsed)
                new_ids_est = union_rate * days_remaining * (decay * 2)
                floor_est = top_limit * growth_floor * 2
                est_unique_items = int(
                    max(
                        floor_est,
                        (union_count + new_ids_est) * growth_factor * 2,
                    )
                )
                est_total_unique_items += est_unique_items
            
            # Account for inmemory_factor in exhaustive_cache_bytes
            # (implementation multiplies the 1.3 factor result by inmemory_factor)
            expected_exhaustive_cache_bytes = int(
                est_total_unique_items * avg_item_bytes * 1.3 * inmemory_factor
            )
            
            # Assertions: tight equality for components we can verify
            assert est_refined["scan_page_bytes"] == expected_scan_page_bytes
            assert est_refined["delta_buffer_bytes"] == expected_delta_buffer_bytes
            assert est_refined["payload_bytes"] == payload_bytes
            assert est_refined["indexing_buffer_bytes"] == indexing_buffer_bytes
            assert est_refined["build_payload_bytes"] == build_payload_bytes
            assert (
                est_refined["all_subcount_working_state_bytes"]
                == working_all_bytes
            )
            assert (
                est_refined["exhaustive_cache_bytes"]
                == expected_exhaustive_cache_bytes
            )
            
            # Now verify peak calculations
            expected_scan_peak = (
                payload_bytes
                + expected_scan_page_bytes
                + expected_exhaustive_cache_bytes
            )
            expected_loop_peak = (
                expected_exhaustive_cache_bytes
                + working_all_bytes
                + indexing_buffer_bytes
                + build_payload_bytes
                + expected_delta_buffer_bytes
            )
            assert est_refined["predicted_scan_peak_bytes"] == expected_scan_peak
            assert est_refined["predicted_loop_peak_bytes"] == expected_loop_peak
            assert est_refined["predicted_peak_bytes"] == int(
                max(expected_scan_peak, expected_loop_peak)
                * app.config["COMMUNITY_STATS_MEM_SAFETY_FACTOR"]
            )
            
            # And refined path differs from empty-hit baseline for delta buffer
            assert est_refined["delta_buffer_bytes"] != est_empty["delta_buffer_bytes"]

    def test_aggregator_delegates_memory_estimation(
        self,
        running_app,
        location,
        prev_snapshot_small,
        set_app_config_fn_scoped,
        mocker,
    ):
        """Aggregator should return adjusted page size from estimator logic."""
        set_app_config_fn_scoped({
            "COMMUNITY_STATS_MEM_BUDGET_BYTES": 2_000_000_000,
            "COMMUNITY_STATS_SCAN_PAGE_SIZE": 400,
            "COMMUNITY_STATS_CHUNK_SIZE": 50,
            "COMMUNITY_STATS_DELTA_BUFFER_SIZE": 50,
        })

        mocker.patch(
            "psutil.Process"
        ).return_value.memory_info.return_value = SimpleNamespace(rss=1_500_000_000)
        mocker.patch("psutil.virtual_memory").return_value = SimpleNamespace(
            total=2_000_000_000
        )

        mock_estimator_cls = mocker.patch(
            "invenio_stats_dashboard.aggregations.usage_snapshot_aggs.UsageSnapshotMemoryEstimator"
        )
        mock_estimator_cls.adjust_scan_page_size.return_value = 123

        estimator_instance = mock_estimator_cls.return_value
        estimator_instance.estimate.return_value = {
            "scan_page_bytes": 50_000_000,
            "predicted_peak_bytes": 200_000_000,
        }

        agg = CommunityUsageSnapshotAggregator(name="community-usage-snapshot-agg")

        first_event_date = arrow.utcnow().shift(days=-10).floor("day")
        upper_limit = arrow.utcnow().floor("day")
        adjusted = agg._estimate_initial_memory(
            previous_snapshot=prev_snapshot_small,  # type: ignore[arg-type]
            first_event_date=first_event_date,
            upper_limit=upper_limit,
        )
        assert adjusted == 123
        estimator_instance.estimate.assert_called_once_with(
            previous_snapshot=prev_snapshot_small,  # type: ignore[arg-type]
            first_event_date=first_event_date,
            upper_limit=upper_limit,
            planned_scan_page_size=400,
            planned_chunk_size=50,
            planned_delta_buffer_size=50,
        )
        mock_estimator_cls.adjust_scan_page_size.assert_called_once_with(
            mem_estimate=estimator_instance.estimate.return_value,
            rss_bytes=1_500_000_000,
            budget_bytes=2_000_000_000,
            planned_scan_page_size=400,
            scan_page_size_min=agg.scan_page_size_min,
            scan_page_size_max=agg.scan_page_size_max,
        )

    def test_adjust_scan_page_size(self, running_app):
        """Adjusts page size only when over budget; clamps within min/max."""
        # Case 1: enough headroom → unchanged
        mem_est = {"predicted_peak_bytes": 1000, "scan_page_bytes": 500}
        out = UsageSnapshotMemoryEstimator.adjust_scan_page_size(
            mem_estimate=mem_est,
            rss_bytes=1_000_000,
            budget_bytes=10_000_000,
            planned_scan_page_size=200,
            scan_page_size_min=50,
            scan_page_size_max=500,
        )
        assert out == 200

        # Case 2: over budget → reduced but within min/max
        mem_est2 = {"predicted_peak_bytes": 200_000_000, "scan_page_bytes": 50_000_000}
        out2 = UsageSnapshotMemoryEstimator.adjust_scan_page_size(
            mem_estimate=mem_est2,
            rss_bytes=1_500_000_000,
            budget_bytes=1_600_000_000,
            planned_scan_page_size=400,
            scan_page_size_min=100,
            scan_page_size_max=500,
        )
        assert 100 <= out2 <= 500
