from pprint import pformat

from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_rdm_records.proxies import current_rdm_records_service as records_service
from invenio_search.utils import prefix_index
from invenio_records_resources.services.uow import (
    unit_of_work,
    RecordCommitOp,
    UnitOfWork,
)
from invenio_stats_dashboard.tasks import CommunityStatsAggregationTask
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search


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

    @unit_of_work()
    def generate_record_community_events(
        self,
        recids: list[str] | None = None,
        community_ids: list[str] | None = None,
        uow: UnitOfWork | None = None,
    ):
        """Update the `stats:community_events` custom field for one or more records.

        The `stats:community_events` custom field is used to store the date when
        the record was added to or removed from each of its communities.
        This helps in generating community record statistics.

        This method will look at the `parent.communities` field to find any
        communities that the record is a part of. If the `stats:community_events`
        custom field is not present, it will be created. If it is present, and
        the `parent.communities.ids` field lists ids that are not present in any
        of the `stats:community_events` custom field dictionaries (`custom_fields.stats:community_events.community_id`), then a new dictionary for this community will be added to the custom field. The record's created date will be used for the `added` subfield, and the `removed` subfield will be left unset.

        Args:
            recid: The record IDs to update. If not provided, all records will be
                updated.
            community_id: The community IDs to update. If not provided, all
                communities will be updated.

        Returns:
            The number of records updated.
        """
        record_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        if recids:
            record_search.query(Q("terms", id=recids))
        else:
            record_search.query(Q("match_all"))

        if not community_ids:
            community_ids = [
                c["id"]
                for c in current_communities.service.read_all(system_identity, [])
            ]
        for community_id in community_ids:
            record_search.filter(Q("term", parent__communities__ids=community_id))

            for result in record_search.scan():
                record_item = records_service.read(result["_source"]["id"])
                data = record_item.to_dict()
                event_list = [
                    f
                    for f in data.get("custom_fields", {}).get(
                        "stats:community_events", []
                    )
                    if f.get("community_id") == community_id
                ]
                event_obj = event_list[0] if event_list else None
                if not event_obj:
                    model = record_item._record.model
                    custom_fields = model.custom_fields
                    custom_fields["stats:community_events"] = [
                        {
                            "community_id": community_id,
                            "added": result["_source"]["created"],
                        }
                    ]
                    model.custom_fields = custom_fields
                    assert uow
                    uow.register(RecordCommitOp(model))

    def get_community_stats(self, community_id: str) -> dict:
        """Get statistics for a community."""
        daily_record_deltas = (
            Search(
                using=self.client, index=prefix_index("stats-community-record-delta")
            )
            .query(Q("term", community_id=community_id))
            .sort("period_start")
            .extra(size=10_000)
            .execute()
        )
        daily_record_snapshots = (
            Search(
                using=self.client,
                index=prefix_index("stats-community-record-snapshot"),
            )
            .query(Q("term", community_id=community_id))
            .sort("snapshot_date")
            .extra(size=10_000)
            .execute()
        )
        daily_usage_deltas = (
            Search(using=self.client, index=prefix_index("stats-community-usage-delta"))
            .query(Q("term", community_id=community_id))
            .sort("period_start")
            .extra(size=10_000)
            .execute()
        )
        daily_usage_snapshots = (
            Search(
                using=self.client, index=prefix_index("stats-community-usage-snapshot")
            )
            .query(Q("term", community_id=community_id))
            .sort("snapshot_date")
            .extra(size=10_000)
            .execute()
        )
        return {
            "daily_record_deltas": daily_record_deltas.hits.hits.to_dict(),
            "daily_record_snapshots": daily_record_snapshots.hits.hits.to_dict(),
            "daily_usage_deltas": daily_usage_deltas.hits.hits.to_dict(),
            "daily_usage_snapshots": daily_usage_snapshots.hits.hits.to_dict(),
        }
