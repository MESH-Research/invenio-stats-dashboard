from celery import shared_task
from celery.schedules import crontab
from dateutil.parser import parse as dateutil_parse
from invenio_stats.proxies import current_stats
from invenio_search.proxies import current_search_client

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
