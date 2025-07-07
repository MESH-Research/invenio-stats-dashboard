from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_rdm_records.proxies import current_rdm_records_service as records_service
from invenio_search.utils import prefix_index
from invenio_stats_dashboard.tasks import CommunityStatsAggregationTask
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search
from .queries import CommunityStatsResultsQuery
from .components import update_community_events_index


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

    def generate_record_community_events(
        self,
        recids: list[str] | None = None,
        community_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """Create `stats-community-events` index events for one or more records.

        This method will create proper stats-community-events records for every record
        in an InvenioRDM instance (or the provided recids). If no community_ids are
        provided, it will create events for every community in the instance, and ensure
        that a "global" addition event is registered for every record in the instance
        as well. Uses the record creation date as the event date for the additions.

        Args:
            recids: The record IDs to update. If not provided, all records will be
                updated.
            community_ids: The community IDs to update. If not provided, all
                communities will be updated.
            start_date: The start date for the events. If not provided, the start date
                will be the first record creation date in the instance.
            end_date: The end date for the events. If not provided, the end date will be
                the current date.

        Returns:
            The number of records processed.
        """
        # Build search query for records
        record_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        terms = []
        if recids:
            terms.append(Q("terms", id=recids))
        if start_date:
            terms.append(Q("range", created={"gte": start_date}))
        if end_date:
            terms.append(Q("range", created={"lte": end_date}))
        if terms:
            record_search.query(Q("bool", must=terms))
        else:
            record_search.query(Q("match_all"))

        # Get all communities if not specified
        if not community_ids:
            communities = current_communities.service.read_all(system_identity, [])
            community_ids = [c["id"] for c in communities]
            community_ids.append("global")

        records_processed = 0

        # Process each record
        for result in record_search.scan():
            record_id = result["id"]
            record_data = result

            # get existing community events for this record
            # and community
            events_search = Search(
                using=self.client, index=prefix_index("stats-community-events")
            )
            events_search.query(
                Q(
                    "bool",
                    must=[
                        Q("term", record_id=record_id),
                        Q("term", community_id=community_ids),
                    ],
                )
            )
            existing_events = list(events_search.execute())

            try:
                # Get the full record to access metadata
                record_item = records_service.read(record_id)
                record_dict = record_item.to_dict()

                # Extract record dates
                record_created_date = record_data.get("created")
                record_published_date = record_dict.get("metadata", {}).get(
                    "publication_date"
                )

                # Get communities this record belongs to
                record_communities = (
                    record_data.get("parent", {}).get("communities", {}).get("ids", [])
                )

                # Create events for each community the record belongs to
                for community_id in community_ids:
                    if community_id in record_communities:
                        # Check if this community already has an event for this record
                        if any(
                            event["record_id"] == record_id
                            and event["community_id"] == community_id
                            for event in existing_events
                        ):
                            continue

                        # Create addition event for this community
                        update_community_events_index(
                            record_id=record_id,
                            community_ids_to_add=[community_id],
                            timestamp=record_created_date,
                            record_created_date=record_created_date,
                            record_published_date=record_published_date,
                            client=self.client,
                        )

                records_processed += 1

            except Exception as e:
                current_app.logger.error(f"Error processing record {record_id}: {e}")

        return records_processed

    def read_stats(self, community_id: str, start_date: str, end_date: str) -> dict:
        """Read statistics for a community."""
        query = CommunityStatsResultsQuery(
            name="community-stats",
            index="stats-community-stats",
            client=self.client,
        )
        return query.run(community_id, start_date, end_date)
