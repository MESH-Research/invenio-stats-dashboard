# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

import time
import uuid
from datetime import timedelta

from celery import shared_task
from celery.schedules import crontab
from dateutil.parser import parse as dateutil_parse
from flask import current_app
from invenio_cache import current_cache
from invenio_search.proxies import current_search_client
from invenio_stats.proxies import current_stats

from .exceptions import TaskLockAcquisitionError
from .proxies import current_event_reindexing_service as reindexing_service


def format_agg_startup_message(
    community_ids=None,
    start_date=None,
    end_date=None,
    eager=False,
    update_bookmark=True,
    ignore_bookmark=False,
    verbose=False,
):
    """Format startup configuration into a human-readable message.

    Args:
        community_ids: List of community IDs or None for all
        start_date: Start date string or None
        end_date: End date string or None
        eager: Whether running in eager mode
        update_bookmark: Whether to update bookmarks
        ignore_bookmark: Whether to ignore bookmarks
        verbose: Whether verbose output is enabled

    Returns:
        String containing formatted startup configuration
    """
    lines = []
    lines.append("=" * 60)
    lines.append("COMMUNITY STATS AGGREGATION")
    lines.append("=" * 60)
    lines.append(f"Start date: {start_date or 'Not specified (using bookmark)'}")
    lines.append(f"End date: {end_date or 'Not specified (using current date)'}")

    communities_str = ", ".join(community_ids) if community_ids else "All communities"
    lines.append(f"Communities: {communities_str}")

    execution_mode = "Eager (synchronous)" if eager else "Asynchronous (Celery task)"
    lines.append(f"Execution mode: {execution_mode}")
    lines.append(f"Update bookmark: {update_bookmark}")
    lines.append(f"Ignore bookmark: {ignore_bookmark}")
    lines.append(f"Verbose output: {verbose}")
    lines.append("=" * 60)

    if not eager:
        lines.append("")
        lines.append("Note: This command runs asynchronously via Celery.")
        lines.append("If interrupted, the aggregation will continue in the background.")
        lines.append("Check Celery logs or OpenSearch indices to verify completion.")
        lines.append("=" * 60)

    return "\n".join(lines)


def _format_aggregation_report(result, verbose=False):
    """Format aggregation results into a human-readable report.

    Args:
        result: Dictionary containing 'timing' and 'results' keys
        verbose: Whether to include detailed timing breakdown

    Returns:
        String containing formatted report
    """
    if not isinstance(result, dict) or "timing" not in result:
        return "Aggregation completed successfully."

    timing = result["timing"]
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("AGGREGATION RESULTS")
    lines.append("=" * 60)

    # Individual aggregator results
    total_docs_indexed = 0
    total_errors = 0
    total_communities = 0

    for aggr_timing in timing["aggregators"]:
        aggr_name = aggr_timing["aggregator"]
        duration = aggr_timing["duration_formatted"]
        docs_indexed = aggr_timing.get("docs_indexed", 0)
        errors = aggr_timing.get("errors", 0)
        communities_count = aggr_timing.get("communities_count", 0)
        error_details = aggr_timing.get("error_details", [])

        lines.append(f"\n{aggr_name}")
        lines.append("-" * len(aggr_name))
        lines.append(f"Duration: {duration}")
        lines.append(f"Documents indexed: {docs_indexed:,}")
        lines.append(f"Errors: {errors:,}")
        if communities_count > 0:
            lines.append(f"Communities processed: {communities_count}")

        total_docs_indexed += docs_indexed
        total_errors += errors
        total_communities = max(total_communities, communities_count)

        # Show error details (limit to first 3 for logging)
        if error_details:
            lines.append("Error details:")
            for error in error_details[:3]:
                if isinstance(error, dict):
                    error_msg = error.get("error", {}).get("reason", str(error))
                    lines.append(f"  - {error_msg}")
            if len(error_details) > 3:
                lines.append(f"  ... and {len(error_details) - 3} more errors")

    # Summary
    lines.append("\n" + "=" * 60)
    lines.append("AGGREGATION SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total documents indexed: {total_docs_indexed:,}")
    lines.append(f"Total errors: {total_errors:,}")
    lines.append(f"Total communities processed: {total_communities}")
    lines.append(f"Total aggregation time: {timing['total_duration_formatted']}")
    lines.append("=" * 60)

    # Add verbose timing details if requested
    if verbose:
        lines.append("\nIndividual aggregator timings:")
        lines.append("-" * 50)
        for aggr_timing in timing["aggregators"]:
            lines.append(
                f"  {aggr_timing['aggregator']:<35} "
                f"{aggr_timing['duration_formatted']:>15}"
            )
        lines.append("-" * 50)
        lines.append(f"{'Total':<35} {timing['total_duration_formatted']:>15}")
        lines.append("=" * 60)

    return "\n".join(lines)


class AggregationTaskLock:
    """
    Simple distributed lock for aggregation tasks using invenio_cache.
    """

    def __init__(self, lock_name, timeout=86400):  # 24 hour timeout
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.lock_id = str(uuid.uuid4())

    def acquire(self):
        """Acquire the lock."""
        # Use cache add method which is atomic and only succeeds if key doesn't exist
        result = current_cache.add(self.lock_name, self.lock_id, timeout=self.timeout)
        return result

    def release(self):
        """Release the lock."""
        current_value = current_cache.get(self.lock_name)
        if current_value == self.lock_id:
            return current_cache.delete(self.lock_name)
        return False

    def __enter__(self):
        if not self.acquire():
            raise TaskLockAcquisitionError(
                f"Could not acquire lock: {self.lock_name}. An existing task "
                f"is probably still running."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


CommunityStatsAggregationTask = {
    "task": "invenio_stats_dashboard.tasks.aggregate_community_record_stats",
    "schedule": crontab(minute="40", hour="*"),  # Run every hour at minute 40
    "args": (
        (
            "community-usage-delta-agg",
            "community-records-delta-created-agg",
            "community-records-delta-published-agg",
            "community-records-delta-added-agg",
            "community-records-snapshot-created-agg",
            "community-records-snapshot-published-agg",
            "community-records-snapshot-added-agg",
            "community-usage-snapshot-agg",
        ),
    ),
}


@shared_task
def aggregate_community_record_stats(
    aggregations,
    start_date=None,
    end_date=None,
    update_bookmark=True,
    ignore_bookmark=False,
    community_ids=None,  # Add community_ids parameter
):
    """Aggregate community record stats from created records."""
    lock_config = current_app.config.get("STATS_DASHBOARD_LOCK_CONFIG", {})
    lock_enabled = lock_config.get("enabled", True)
    lock_timeout = lock_config.get("lock_timeout", 3600)
    lock_name = lock_config.get("lock_name", "community_stats_aggregation")

    if lock_enabled:
        lock = AggregationTaskLock(lock_name, timeout=lock_timeout)
        try:
            with lock:
                current_app.logger.info(
                    "Acquired aggregation lock, starting aggregation..."
                )
                return _run_aggregation(
                    aggregations,
                    start_date,
                    end_date,
                    update_bookmark,
                    community_ids,
                    ignore_bookmark,
                )
        except TaskLockAcquisitionError:
            # Lock acquisition failed - another task is running
            current_app.logger.warning(
                "Aggregation task skipped - another instance is already running"
            )
            return {
                "results": [],
                "timing": {
                    "total_duration_formatted": "0:00:00",
                    "aggregators": [],
                },
            }
    else:
        # Run without locking
        current_app.logger.info("Running aggregation without distributed lock...")
        return _run_aggregation(
            aggregations,
            start_date,
            end_date,
            update_bookmark,
            community_ids,
            ignore_bookmark,
        )


def _run_aggregation(
    aggregations,
    start_date,
    end_date,
    update_bookmark,
    community_ids=None,
    ignore_bookmark=False,
    verbose=False,
):
    """Run the actual aggregation logic."""
    start_date = dateutil_parse(start_date) if start_date else None
    end_date = dateutil_parse(end_date) if end_date else None
    results = []
    timing_info = []

    # Log startup configuration
    startup_config = format_agg_startup_message(
        community_ids=community_ids,
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date) if end_date else None,
        eager=False,  # This is always False when called from task
        update_bookmark=update_bookmark,
        ignore_bookmark=ignore_bookmark,
        verbose=False,
    )
    current_app.logger.info(f"Aggregation startup configuration:\n{startup_config}")

    # Refresh community events index before running aggregators
    current_search_client.indices.refresh(index="*stats-community-events*")

    total_start_time = time.time()

    for aggr_name in aggregations:
        aggr_start_time = time.time()
        current_app.logger.info(f"Starting aggregator: {aggr_name}")

        aggr_cfg = current_stats.aggregations[aggr_name]
        params = aggr_cfg.params.copy()
        if community_ids:
            params["community_ids"] = community_ids
        aggregator = aggr_cfg.cls(name=aggr_cfg.name, **params)
        result = aggregator.run(start_date, end_date, update_bookmark, ignore_bookmark)
        results.append(result)

        if hasattr(aggregator, "aggregation_index") and aggregator.aggregation_index:
            current_search_client.indices.refresh(
                index=f"*{aggregator.aggregation_index}*"
            )

        aggr_end_time = time.time()
        aggr_duration = str(timedelta(seconds=aggr_end_time - aggr_start_time))
        # Extract detailed results information
        aggr_docs_indexed = 0
        aggr_errors = 0
        aggr_communities: set[str] = set()
        aggr_error_details = []

        if isinstance(result, list):
            for community_result in result:
                if isinstance(community_result, tuple) and len(community_result) >= 2:
                    docs_indexed = community_result[0]
                    errors = community_result[1]
                    aggr_docs_indexed += docs_indexed

                    if isinstance(errors, int):
                        aggr_errors += errors
                    elif isinstance(errors, list):
                        aggr_errors += len(errors)
                        aggr_error_details.extend(errors)

        timing_info.append(
            {
                "aggregator": aggr_name,
                "duration_formatted": aggr_duration,
                "docs_indexed": aggr_docs_indexed,
                "errors": aggr_errors,
                "communities_count": len(aggr_communities),
                "error_details": (
                    aggr_error_details[:10] if aggr_error_details else []
                ),  # Limit to first 10 errors
            }
        )

        current_app.logger.info(f"Completed aggregator: {aggr_name} in {aggr_duration}")

    total_end_time = time.time()
    total_duration = str(timedelta(seconds=total_end_time - total_start_time))

    current_app.logger.info("Aggregation completed successfully")
    current_app.logger.info(f"Total aggregation time: {total_duration}")

    # Store timing info in results for CLI access
    result_dict = {
        "results": results,
        "timing": {
            "total_duration_formatted": total_duration,
            "aggregators": timing_info,
        },
    }

    # Generate formatted report for both logging and CLI display
    # Always log the non-verbose version to keep logs clean
    report = _format_aggregation_report(result_dict, verbose=verbose)
    current_app.logger.info(f"Aggregation report:\n{report}")

    # Add both verbose and non-verbose reports to result for CLI display
    result_dict["formatted_report"] = _format_aggregation_report(
        result_dict, verbose=False
    )
    result_dict["formatted_report_verbose"] = _format_aggregation_report(
        result_dict, verbose=True
    )

    return result_dict


@shared_task
def reindex_usage_events_with_metadata(
    event_types=None,
    max_batches=None,
    batch_size=None,
    max_memory_percent=None,
    delete_old_indices=False,
):
    """
    Reindex view and download events with enriched metadata as a Celery task.

    Args:
        event_types: List of event types to process. If None, process all.
        max_batches: Maximum number of batches to process. If None, process all.
        batch_size: Override default batch size. If None, use default.
        max_memory_percent: Override default memory limit. If None, use default.
        delete_old_indices: Whether to delete old indices after migration.

    Returns:
        Dictionary with reindexing results and statistics.
    """
    current_app.logger.info("Starting event reindexing task")

    if batch_size is not None:
        reindexing_service.batch_size = batch_size
    if max_memory_percent is not None:
        reindexing_service.max_memory_percent = max_memory_percent

    try:
        progress = reindexing_service.get_reindexing_progress()
        current_app.logger.info(f"Initial progress: {progress}")

        results = reindexing_service.reindex_events(
            event_types=event_types,
            max_batches=max_batches,
            delete_old_indices=delete_old_indices,
        )

        current_app.logger.info(f"Reindexing task completed: {results}")
        return results

    except Exception as e:
        current_app.logger.error(f"Reindexing task failed: {e}")
        return {
            "error": str(e),
            "completed": False,
            "total_processed": 0,
            "total_errors": 1,
        }


@shared_task
def get_reindexing_progress():
    """Get current reindexing progress as a Celery task."""
    try:
        from .proxies import current_event_reindexing_service

        progress = current_event_reindexing_service.get_reindexing_progress()
        return progress
    except Exception as e:
        current_app.logger.error(f"Failed to get reindexing progress: {e}")
        return {"error": str(e)}
