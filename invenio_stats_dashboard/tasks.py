from celery import shared_task
from celery.schedules import crontab
from dateutil.parser import parse as dateutil_parse
from invenio_stats.proxies import current_stats
from invenio_search.proxies import current_search_client
from flask import current_app
from .proxies import current_event_reindexing_service

CommunityStatsAggregationTask = {
    "task": "invenio_stats_dashboard.tasks.aggregate_community_record_stats",
    "schedule": crontab(minute="40", hour="*"),  # Run every hour at minute 40
    "args": (
        "community-usage-delta-agg",
        "community-records-delta-created-agg",
        "community-records-delta-published-agg",
        "community-records-delta-added-agg",
        "community-records-snapshot-created-agg",
        "community-records-snapshot-published-agg",
        "community-records-snapshot-added-agg",
        "community-usage-snapshot-agg",
    ),
}

EventReindexingTask = {
    "task": "invenio_stats_dashboard.tasks.reindex_events_with_metadata",
    "args": (),
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

    return results


@shared_task
def reindex_events_with_metadata(
    event_types=None,
    max_batches=None,
    batch_size=None,
    max_memory_percent=None,
):
    """
    Reindex events with enriched metadata as a Celery task.

    Args:
        event_types: List of event types to process. If None, process all.
        max_batches: Maximum number of batches to process. If None, process all.
        batch_size: Override default batch size. If None, use default.
        max_memory_percent: Override default memory limit. If None, use default.

    Returns:
        Dictionary with reindexing results and statistics.
    """
    current_app.logger.info("Starting event reindexing task")

    # Use the proxy to get the reindexing service
    reindexing_service = current_event_reindexing_service

    # Override configuration if provided
    if batch_size is not None:
        reindexing_service.batch_size = batch_size
    if max_memory_percent is not None:
        reindexing_service.max_memory_percent = max_memory_percent

    try:
        # Get initial progress estimate
        progress = reindexing_service.get_reindexing_progress()
        current_app.logger.info(f"Initial progress: {progress}")

        # Start reindexing
        results = reindexing_service.reindex_events(
            event_types=event_types, max_batches=max_batches
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
        reindexing_service = current_event_reindexing_service
        progress = reindexing_service.get_reindexing_progress()
        return progress
    except Exception as e:
        current_app.logger.error(f"Failed to get reindexing progress: {e}")
        return {"error": str(e)}
