import uuid

from celery import shared_task
from celery.schedules import crontab
from dateutil.parser import parse as dateutil_parse
from flask import current_app
from invenio_cache import current_cache
from invenio_search.proxies import current_search_client
from invenio_stats.proxies import current_stats

from .exceptions import TaskLockAcquisitionError
from .proxies import current_event_reindexing_service as reindexing_service


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
                    aggregations, start_date, end_date, update_bookmark
                )
        except TaskLockAcquisitionError:
            # Lock acquisition failed - another task is running
            current_app.logger.warning(
                "Aggregation task skipped - another instance is already running"
            )
            return []
    else:
        # Run without locking
        current_app.logger.info("Running aggregation without distributed lock...")
        return _run_aggregation(aggregations, start_date, end_date, update_bookmark)


def _run_aggregation(aggregations, start_date, end_date, update_bookmark):
    """Run the actual aggregation logic."""
    start_date = dateutil_parse(start_date) if start_date else None
    end_date = dateutil_parse(end_date) if end_date else None
    results = []

    # Refresh community events index before running aggregators
    current_search_client.indices.refresh(index="*stats-community-events*")

    for aggr_name in aggregations:
        aggr_cfg = current_stats.aggregations[aggr_name]
        aggregator = aggr_cfg.cls(name=aggr_cfg.name, **aggr_cfg.params)
        result = aggregator.run(start_date, end_date, update_bookmark)
        results.append(result)

        if hasattr(aggregator, "aggregation_index") and aggregator.aggregation_index:
            current_search_client.indices.refresh(
                index=f"*{aggregator.aggregation_index}*"
            )

    current_app.logger.info("Aggregation completed successfully")
    return results


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
