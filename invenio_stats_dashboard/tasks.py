from celery import shared_task
from celery.schedules import crontab
from dateutil.parser import parse as dateutil_parse
from invenio_stats.proxies import current_stats

CommunityStatsAggregationTask = {
    "task": "invenio_stats_dashboard.tasks.aggregate_community_record_stats",
    "schedule": crontab(minute="5"),
    "args": [
        (
            "community-records-snapshot-agg",
            "community-records-delta-agg",
            "community-records-usage-snapshot-agg",
            "community-records-usage-delta-agg",
        )
    ],
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
    for aggr_name in aggregations:
        aggr_cfg = current_stats.aggregations[aggr_name]
        aggregator = aggr_cfg.cls(name=aggr_cfg.name, **aggr_cfg.params)
        results.append(aggregator.run(start_date, end_date, update_bookmark))

    return results
