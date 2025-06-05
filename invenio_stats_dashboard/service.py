from invenio_search.proxies import current_search_client
from invenio_stats_dashboard.tasks import CommunityStatsAggregationTask
from opensearchpy import OpenSearch


class CommunityStatsService:
    """Service for managing statistics related to communities."""

    def __init__(self, client: OpenSearch):
        self.client = client

    def aggregate_stats(
        self,
        community_ids: list[str],
        start_date: str,
        end_date: str,
        eager: bool = False,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
    ) -> dict:
        """Aggregate statistics for a community."""

        task = CommunityStatsAggregationTask["task"]
        args = CommunityStatsAggregationTask["args"]
        if eager:
            results = task(
                *args,
                start_date=start_date,
                end_date=end_date,
                update_bookmark=update_bookmark,
                ignore_bookmark=ignore_bookmark,
            )
        else:
            task_run = task.delay(
                *args,
                start_date=start_date,
                end_date=end_date,
                update_bookmark=update_bookmark,
                ignore_bookmark=ignore_bookmark,
            )
            results = task_run.get()

        return results
