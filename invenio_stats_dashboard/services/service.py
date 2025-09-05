"""Service for managing statistics related to communities."""

import arrow
from flask import Flask, current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search

from ..queries import CommunityStatsResultsQuery
from ..tasks import CommunityStatsAggregationTask
from .components import update_community_events_index


class CommunityStatsService:
    """Service for managing statistics related to communities."""

    def __init__(self, app: Flask):
        self.client = current_search_client
        self.app = app

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
                community_ids=community_ids,  # Pass community_ids
            )
        else:
            task_run = task.delay(
                *args,
                start_date=start_date,
                end_date=end_date,
                update_bookmark=update_bookmark,
                ignore_bookmark=ignore_bookmark,
                community_ids=community_ids,  # Pass community_ids
            )
            # Store task ID for CLI display
            task_id = task_run.id
            results = task_run.get()
            # Add task ID to results for CLI access
            if isinstance(results, dict):
                results["task_id"] = task_id

        return results

    def count_records_needing_events(
        self,
        recids: list[str] | None = None,
        community_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Count records that need community events created.

        This method analyzes records to determine how many need "added" events
        created for their communities and for the "global" community.

        Args:
            recids: The record IDs to check. If not provided, all records will be
                checked.
            community_ids: The community IDs to check. If not provided, all
                communities will be checked.
            start_date: The start date for filtering records. If not provided, the
                start date will be the first record creation date in the instance.
            end_date: The end date for filtering records. If not provided, the end
                date will be the current date.

        Returns:
            Dictionary with counts and details about records needing events.
        """
        start_date_str = (
            (arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss"))
            if start_date
            else None
        )
        end_date_str = (
            (arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss"))
            if end_date
            else None
        )

        record_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        terms = []
        if recids:
            terms.append({"terms": {"id": recids}})
        if start_date_str:
            terms.append({"range": {"created": {"gte": start_date_str}}})
        if end_date_str:
            terms.append({"range": {"created": {"lte": end_date_str}}})

        if len(terms) > 0:
            record_search = record_search.query({"bool": {"must": terms}})
        else:
            record_search = record_search.query({"match_all": {}})

        if not community_ids:
            communities = current_communities.service.read_all(system_identity, [])
            community_ids = [c["id"] for c in communities]

        total_records = 0
        records_needing_events = 0
        total_events_needed = 0
        community_breakdown = {}

        for result in record_search.scan():
            record_id = result["id"]
            record_data = result.to_dict()
            total_records += 1

            try:
                record_communities = (
                    record_data.get("parent", {}).get("communities", {}).get("ids", [])
                )

                # Always check global community, plus communities the record
                # actually belongs to
                communities_to_check = ["global"] + record_communities
                events_needed_for_record = 0

                for community_id in communities_to_check:
                    if community_id == "global" or community_id in record_communities:
                        # Check if event already exists
                        try:
                            existing_event_search = Search(
                                using=self.client,
                                index=prefix_index("stats-community-events"),
                            )
                            query_dict = {
                                "bool": {
                                    "must": [
                                        {"term": {"record_id": record_id}},
                                        {"term": {"community_id": community_id}},
                                        {"term": {"event_type": "added"}},
                                    ]
                                }
                            }
                            existing_event_search = existing_event_search.query(
                                query_dict
                            )
                            existing_events = list(existing_event_search.execute())

                            if not existing_events:
                                events_needed_for_record += 1
                                if community_id not in community_breakdown:
                                    community_breakdown[community_id] = 0
                                community_breakdown[community_id] += 1

                        except Exception as e:
                            current_app.logger.warning(
                                f"Could not search stats-community-events index for "
                                f"record {record_id}, community {community_id}: "
                                f"{e}. Assuming event needed."
                            )
                            events_needed_for_record += 1
                            if community_id not in community_breakdown:
                                community_breakdown[community_id] = 0
                            community_breakdown[community_id] += 1

                if events_needed_for_record > 0:
                    records_needing_events += 1
                    total_events_needed += events_needed_for_record

            except Exception as e:
                current_app.logger.warning(f"Error processing record {record_id}: {e}")

        return {
            "total_records": total_records,
            "records_needing_events": records_needing_events,
            "total_events_needed": total_events_needed,
            "community_breakdown": community_breakdown,
            "communities_checked": community_ids,
        }

    def generate_record_community_events(
        self,
        recids: list[str] | None = None,
        community_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[int, int, int]:
        """Create `stats-community-events` index events for one or more records.

        This method will create proper stats-community-events records for every record
        in an InvenioRDM instance (or the provided recids). For each record, it will:
        1. Create "added" events for all communities the record belongs to
        2. Ensure a "global" addition event exists for every record

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
        records_processed = 0
        new_events_created = 0
        old_events_found = 0
        start_date_str = (
            (arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss"))
            if start_date
            else None
        )
        end_date_str = (
            (arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss"))
            if end_date
            else None
        )

        record_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        terms = []
        if recids:
            terms.append({"terms": {"id": recids}})
        if start_date_str:
            terms.append({"range": {"created": {"gte": start_date_str}}})
        if end_date_str:
            terms.append({"range": {"created": {"lte": end_date_str}}})

        if len(terms) > 0:
            record_search = record_search.query({"bool": {"must": terms}})
        else:
            record_search = record_search.query({"match_all": {}})

        if not community_ids:
            communities = current_communities.service.read_all(system_identity, [])
            community_ids = [c["id"] for c in communities]

        for result in record_search.scan():
            record_id = result["id"]
            record_data = result.to_dict()

            try:
                record_created_date = record_data.get("created")
                record_published_date = record_data.get("metadata", {}).get(
                    "publication_date", None
                )

                record_communities = (
                    record_data.get("parent", {}).get("communities", {}).get("ids", [])
                )

                current_app.logger.info(f"Generating events for record: {record_id}")
                current_app.logger.info(
                    f"Record {record_id} belongs to communities: "
                    f"{record_communities}"
                )

                # Always process global community, plus communities the record
                # actually belongs to
                communities_to_process = ["global"] + record_communities

                current_app.logger.info(
                    f"Processing communities for record {record_id}: "
                    f"{communities_to_process}"
                )

                existing_events = []
                try:
                    existing_events_search = Search(
                        using=self.client, index=prefix_index("stats-community-events")
                    )

                    # Use raw query dict instead of Q objects
                    query_dict = {
                        "bool": {
                            "must": [
                                {"term": {"record_id": record_id}},
                                {"terms": {"community_id": communities_to_process}},
                                {"term": {"event_type": "added"}},
                            ]
                        }
                    }

                    existing_events_search = existing_events_search.query(query_dict)
                    existing_events = list(existing_events_search.execute())
                    old_events_found += len(existing_events)
                except Exception as e:
                    current_app.logger.warning(
                        f"Could not search stats-community-events index: {e}. "
                        f"Treating as empty."
                    )

                existing_community_ids = {
                    event["community_id"] for event in existing_events
                }

                current_app.logger.info(
                    f"Found {len(existing_events)} existing events for "
                    f"record {record_id}"
                )

                communities_to_add = [
                    community_id
                    for community_id in communities_to_process
                    if community_id not in existing_community_ids
                ]

                current_app.logger.info(
                    f"Will create events for communities: {communities_to_add}"
                )

                if communities_to_add:
                    new_events_created += len(communities_to_add)
                    update_community_events_index(
                        record_id=record_id,
                        community_ids_to_add=communities_to_add,
                        timestamp=record_created_date,
                        record_created_date=record_created_date,
                        record_published_date=record_published_date,
                        client=self.client,
                    )
                    current_app.logger.info(
                        f"Created {len(communities_to_add)} events for "
                        f"record {record_id}"
                    )

                    # Refresh the search index to ensure new events are searchable
                    try:
                        self.client.indices.refresh(
                            index=prefix_index("stats-community-events")
                        )
                    except Exception as e:
                        current_app.logger.error(
                            f"Error refreshing community events index: {e}"
                        )
                else:
                    current_app.logger.info(
                        f"No new events needed for record {record_id}"
                    )

                records_processed += 1

            except Exception as e:
                current_app.logger.error(f"Error processing record {record_id}: {e}")

        current_app.logger.info(f"Total records processed: {records_processed}")
        return records_processed, new_events_created, old_events_found

    def read_stats(self, community_id: str, start_date: str, end_date: str) -> dict:
        """Read statistics for a community."""
        query = CommunityStatsResultsQuery(
            name="community-stats",
            index="stats-community-stats",
            client=self.client._get_current_object(),
        )
        return query.run(community_id, start_date, end_date)
