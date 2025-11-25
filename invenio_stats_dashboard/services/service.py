# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service for managing statistics related to communities."""

from typing import Any, cast

import arrow
from flask import Flask, current_app
from invenio_access.permissions import system_identity
from invenio_cache import current_cache
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search

from ..aggregations import register_aggregations
from ..aggregations.bookmarks import CommunityBookmarkAPI
from ..config import COMMUNITY_STATS_QUERIES
from ..resources.api_queries import CommunityStatsResultsQuery
from ..tasks.aggregation_tasks import (
    AggregationResponse,
    CommunityStatsAggregationTask,
    aggregate_community_record_stats,
)
from .components import update_community_events_index


class CommunityStatsService:
    """Service for managing statistics related to communities."""

    def __init__(self, app: Flask):
        """Initialize the community stats service.

        Args:
            app (Flask): The Flask application instance.
        """
        self.client = current_search_client
        self.app = app

    def aggregate_stats(
        self,
        community_ids: list[str] | None = None,
        aggregation_types: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        eager: bool = True,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
        verbose: bool = False,
    ) -> AggregationResponse:
        """Aggregate statistics for a community.

        Available aggregation types are the ones configure in the
        COMMUNITY_STATS_AGGREGATIONS config variable.

        Args:
            community_ids: List of community IDs to aggregate stats for
            aggregation_types: List of configured aggregation types to run
            start_date: Start date for aggregation
            end_date: End date for aggregation
            eager: Whether to run eagerly (synchronously)
            update_bookmark: Whether to update bookmarks after aggregation
            ignore_bookmark: Whether to ignore existing bookmarks
            verbose: Whether to show detailed timing information

        Returns:
            AggregationResponse object

        Raises:
            ValueError: If invalid parameters are provided.
        """
        agg_args = CommunityStatsAggregationTask["args"]
        current_app.logger.debug(f"agg_type_args: {agg_args}")
        if aggregation_types is not None and len(aggregation_types) > 0:
            disallowed = [a for a in aggregation_types if a not in agg_args[0]]
            if len(disallowed) > 0:
                raise ValueError(
                    f"Some specified aggregation types are not configured: {disallowed}"
                )
            agg_type_args = [a for a in agg_args[0] if a in aggregation_types]
            agg_args = (agg_type_args, *agg_args[1:])

        if eager:
            current_app.logger.error(
                f"Aggregating stats eagerly for communities: {community_ids}"
            )
            try:
                # For eager execution, call the function directly
                current_app.logger.error(
                    f"Calling aggregate_community_record_stats with args: {agg_args}"
                )
                results = aggregate_community_record_stats(
                    *agg_args,
                    start_date=start_date,
                    end_date=end_date,
                    update_bookmark=update_bookmark,
                    ignore_bookmark=ignore_bookmark,
                    community_ids=community_ids,
                    verbose=verbose,
                    eager=eager,
                )
                current_app.logger.info(
                    f"Stats aggregated eagerly for communities: {community_ids}"
                )
            except Exception as e:
                current_app.logger.error(
                    f"Error during eager aggregation for communities "
                    f"{community_ids}: {e}"
                )
                raise
        else:
            current_app.logger.info(
                f"Aggregating stats asynchronously for communities: {community_ids}"
            )
            # For async execution, use the Celery task
            task_run = aggregate_community_record_stats.delay(
                *agg_args,
                start_date=start_date,
                end_date=end_date,
                update_bookmark=update_bookmark,
                ignore_bookmark=ignore_bookmark,
                community_ids=community_ids,
                verbose=verbose,
                eager=eager,
            )
            current_app.logger.info(
                f"Stats aggregation task is running asynchronously for communities: "
                f"{community_ids}"
            )
            task_id = task_run.id
            results = task_run.get()
            if isinstance(results, dict):
                results["task_id"] = task_id

        if isinstance(results, dict):
            return cast(AggregationResponse, results)
        else:
            return cast(
                AggregationResponse,
                {
                    "results": [],
                    "total_duration": "0:00:00",
                    "formatted_report": "No results available",
                    "formatted_report_verbose": "No results available",
                },
            )

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
        terms: list[dict] = []
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
            # Use scan() to get all communities without size limits
            all_communities = list(
                current_communities.service.scan(system_identity)
            )
            community_ids = [c["id"] for c in all_communities]

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
        terms: list[dict] = []
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
            # Use scan() to get all communities without size limits
            all_communities = list(
                current_communities.service.scan(system_identity)
            )
            community_ids = [c["id"] for c in all_communities]

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
                    f"Record {record_id} belongs to communities: {record_communities}"
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

    def read_stats(
        self,
        community_id: str,
        start_date: str,
        end_date: str,
        query_type: str | None = None,
    ) -> tuple[bool, dict | list]:
        """Read statistics for a community.

        Args:
            community_id: The ID of the community to read stats for
            start_date: The start date to read stats for
            end_date: The end date to read stats for
            query_type: Optional specific query type to run instead of the meta-query

        Returns:
            Tuple of (success, result) where success indicates if data was found

        Raises:
            ValueError: If invalid parameters are provided.
        """
        try:
            if query_type:
                # Run a specific query type
                if query_type not in COMMUNITY_STATS_QUERIES:
                    raise ValueError(f"Unknown query type: {query_type}")

                # Get the query class and index name from the config
                query_config: dict[str, Any] = COMMUNITY_STATS_QUERIES[query_type]
                query_class: type[CommunityStatsResultsQuery] = query_config["cls"]
                index_name: str = query_config["params"]["index"]

                # Create and run the specific query
                query: CommunityStatsResultsQuery = query_class(
                    name=query_type,
                    index=index_name,
                    client=self.client._get_current_object(),
                )
                result = query.run(community_id, start_date, end_date)
                if isinstance(result, list):
                    return True, result
                else:
                    return True, []
            else:
                # Run the meta-query
                query = CommunityStatsResultsQuery(
                    name="community-stats",
                    index="stats-community-stats",
                    client=self.client._get_current_object(),
                )
                result = query.run(community_id, start_date, end_date)
                if isinstance(result, dict):
                    return True, result
                else:
                    return True, {}
        except ValueError as e:
            if "No results found for community" in str(e):
                current_app.logger.info(
                    f"No {query_type or 'stats'} data found for community "
                    f"{community_id} from {start_date} to {end_date}"
                )
                if query_type:
                    return False, []
                else:
                    empty_response: dict[str, Any] = {}
                    for query_name in COMMUNITY_STATS_QUERIES.keys():
                        key = (
                            query_name.replace("community-record-", "")
                            .replace("community-", "")
                            .replace("-", "_")
                        )
                        empty_response[key] = []
                    return False, empty_response
            else:
                raise

    def get_aggregation_status(self, community_ids: list[str] | None = None) -> dict:
        """Get aggregation status for communities.

        Args:
            community_ids: Optional list of community IDs to check. If None, checks all
                communities.

        Returns:
            Dictionary with aggregation status information including:
            - Current bookmark dates for all aggregators
            - First and last dates of documents in each aggregation index
            - Number of documents in each aggregation index
        """
        aggregation_types = {
            k: v["templates"].split(".")[-1].replace("_", "-")
            for k, v in register_aggregations().items()
            if k != "community-events-agg"
        }

        if community_ids:
            communities = []
            for community_id in community_ids:
                try:
                    community = current_communities.service.read(
                        system_identity, community_id
                    )
                    communities.append({
                        "id": community.id,
                        "slug": community.data.get("slug", ""),
                    })
                except Exception as e:
                    return {
                        "communities": [],
                        "error": f"Community {community_id} not found: {str(e)}",
                    }
        else:
            try:
                communities_result = current_communities.service.search(
                    system_identity, size=1000
                )
                communities = [
                    {"id": comm["id"], "slug": comm.get("slug", "")}
                    for comm in communities_result.hits
                ]
            except Exception as e:
                return {
                    "communities": [],
                    "error": f"Failed to retrieve communities: {str(e)}",
                }

        result: dict[str, Any] = {"communities": []}

        for community in communities:
            comm_id = community["id"]
            comm_slug = community["slug"]

            community_status = {
                "community_id": comm_id,
                "community_slug": comm_slug,
                "aggregations": {},
            }

            for agg_type, index_pattern in aggregation_types.items():
                agg_status: dict[str, Any] = {
                    "bookmark_date": None,
                    "index_exists": False,
                    "document_count": 0,
                    "first_document_date": None,
                    "last_document_date": None,
                    "days_since_last_document": None,
                    "error": None,
                }

                try:
                    # Check if any indices exist that match the pattern
                    index_pattern_with_prefix = prefix_index(index_pattern)
                    indices_exist = self.client.indices.exists(
                        index=f"{index_pattern_with_prefix}*"
                    )
                    if indices_exist:
                        agg_status["index_exists"] = True

                        bookmark_api = CommunityBookmarkAPI(
                            self.client, agg_type, "day"
                        )
                        bookmark = bookmark_api.get_bookmark(comm_id)
                        if bookmark:
                            agg_status["bookmark_date"] = bookmark.isoformat()

                        search = Search(
                            using=self.client, index=f"{index_pattern_with_prefix}*"
                        )

                        search = search.filter("term", community_id=comm_id)

                        count_search = search.extra(size=0)
                        count_result = count_search.execute()
                        document_count = count_result.hits.total.value or 0
                        agg_status["document_count"] = document_count

                        if document_count > 0:
                            if "snapshot" in agg_type:
                                date_field = "snapshot_date"
                            else:  # delta aggregations
                                date_field = "period_start"

                            date_search = search.extra(size=0)
                            date_search.aggs.bucket("min_date", "min", field=date_field)
                            date_search.aggs.bucket("max_date", "max", field=date_field)

                            date_result = date_search.execute()
                            if date_result.aggregations.min_date.value:
                                agg_status["first_document_date"] = arrow.get(
                                    date_result.aggregations.min_date.value
                                ).isoformat()
                            if date_result.aggregations.max_date.value:
                                last_doc_date = arrow.get(
                                    date_result.aggregations.max_date.value
                                )
                                agg_status["last_document_date"] = (
                                    last_doc_date.isoformat()
                                )
                                now = arrow.utcnow()
                                agg_status["days_since_last_document"] = (
                                    now - last_doc_date
                                ).days

                except Exception as e:
                    agg_status["error"] = str(e)

                community_status["aggregations"][agg_type] = agg_status

            result["communities"].append(community_status)

        return result

    def clear_aggregation_bookmarks(
        self,
        community_ids: list[str] | None = None,
        aggregation_types: list[str] | None = None,
        all_communities: bool = False,
        all_aggregation_types: bool = False,
    ) -> dict[str, Any]:
        """Clear aggregation bookmarks for specified communities and aggregation types.

        Args:
            community_ids: List of community IDs to clear bookmarks for. If None
                and not all_communities, will clear for all communities.
            aggregation_types: List of aggregation types to clear bookmarks for. If None
                and not all_aggregation_types, will clear for all aggregation types.
            all_communities: If True, clear bookmarks for all communities
            all_aggregation_types: If True, clear bookmarks for all aggregation types

        Returns:
            Dictionary with results including number of bookmarks cleared per
                community/type
        """
        # Get available aggregation types
        available_agg_types = list(register_aggregations().keys())
        if "community-events-agg" in available_agg_types:
            # Skip community events aggregator
            available_agg_types.remove("community-events-agg")

        # Determine which aggregation types to clear
        if all_aggregation_types:
            agg_types_to_clear = available_agg_types
        elif aggregation_types:
            agg_types_to_clear = [
                t for t in aggregation_types if t in available_agg_types
            ]
            if not agg_types_to_clear:
                return {
                    "success": False,
                    "error": f"No valid aggregation types found. "
                    f"Available: {available_agg_types}",
                    "cleared": {},
                }
        else:
            agg_types_to_clear = available_agg_types

        # Get communities to clear bookmarks for
        if all_communities or not community_ids:
            try:
                communities_result = current_communities.service.search(
                    system_identity, size=1000
                )
                communities_to_clear = [
                    {"id": comm["id"], "slug": comm.get("slug", "")}
                    for comm in communities_result.hits
                ]
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to retrieve communities: {str(e)}",
                    "cleared": {},
                }
        else:
            communities_to_clear = []
            for community_id in community_ids:
                try:
                    community = current_communities.service.read(
                        system_identity, community_id
                    )
                    communities_to_clear.append({
                        "id": community.id,
                        "slug": community.data.get("slug", ""),
                    })
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Community {community_id} not found: {str(e)}",
                        "cleared": {},
                    }

        # Clear bookmarks for each community and aggregation type
        results: dict[str, Any] = {"success": True, "cleared": {}, "total_cleared": 0}

        for community in communities_to_clear:
            comm_id = community["id"]
            comm_slug = community["slug"]

            comm_entry: dict[str, Any] = {"slug": comm_slug, "aggregation_types": {}}
            agg_types_map: dict[str, int] = {}

            for agg_type in agg_types_to_clear:
                try:
                    bookmark_api = CommunityBookmarkAPI(self.client, agg_type, "day")

                    if all_communities and all_aggregation_types:
                        # Clear all bookmarks for this aggregation type
                        cleared_count = bookmark_api.clear_all_bookmarks(
                            aggregation_type=agg_type
                        )
                    else:
                        # Clear bookmarks for this specific community and aggregation
                        # type
                        cleared_count = bookmark_api.clear_bookmark(comm_id)

                    agg_types_map[agg_type] = cleared_count
                    results["total_cleared"] += cleared_count

                except Exception as e:
                    current_app.logger.warning(
                        f"Failed to clear bookmarks for community {comm_id} "
                        f"and aggregation type {agg_type}: {e}"
                    )
                    agg_types_map[agg_type] = 0

            comm_entry["aggregation_types"] = agg_types_map
            # Assign once to avoid nested indexed assignment on a dynamic type
            cleared_map = results.get("cleared")
            if isinstance(cleared_map, dict):
                cleared_map[comm_id] = comm_entry
            else:
                results["cleared"] = {comm_id: comm_entry}

        return results

    def clear_aggregation_lock(
        self, lock_name: str = "community_stats_aggregation", dry_run: bool = False
    ) -> dict[str, Any]:
        """Clear a specific lock from the cache.

        Args:
            lock_name: The name of the lock to clear (without 'lock:' prefix)
            dry_run: If True, only show what would be cleared without actually clearing

        Returns:
            Dictionary with success status and details about the operation
        """
        full_lock_key = f"lock:{lock_name}"

        try:
            # Check if the lock exists
            current_value = current_cache.get(full_lock_key)

            if current_value is None:
                return {
                    "success": True,
                    "message": (
                        f"Lock '{full_lock_key}' not found "
                        "(already cleared or never existed)"
                    ),
                    "lock_key": full_lock_key,
                    "lock_value": None,
                    "cleared": False,
                }

            if dry_run:
                return {
                    "success": True,
                    "message": f"DRY RUN: Would clear lock '{full_lock_key}'",
                    "lock_key": full_lock_key,
                    "lock_value": current_value,
                    "cleared": False,
                }

            # Clear the lock
            success = current_cache.delete(full_lock_key)

            if success:
                return {
                    "success": True,
                    "message": f"Successfully cleared lock '{full_lock_key}'",
                    "lock_key": full_lock_key,
                    "lock_value": current_value,
                    "cleared": True,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to clear lock '{full_lock_key}'",
                    "lock_key": full_lock_key,
                    "lock_value": current_value,
                    "cleared": False,
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error clearing lock '{full_lock_key}': {e}",
                "lock_key": full_lock_key,
                "lock_value": None,
                "cleared": False,
                "error": str(e),
            }

    def list_aggregation_locks(self) -> dict[str, Any]:
        """List all lock keys in the cache.

        Returns:
            Dictionary with success status and list of all lock keys
        """
        try:
            # Get all keys that start with 'lock:'
            all_keys = current_cache.cache._read_client.keys("lock:*")

            if not all_keys:
                return {
                    "success": True,
                    "message": "No lock keys found in cache",
                    "locks": [],
                    "count": 0,
                }

            locks = []
            for key in all_keys:
                # Decode bytes to string if needed
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                value = current_cache.get(key)
                locks.append({
                    "key": key,
                    "value": value,
                })

            return {
                "success": True,
                "message": f"Found {len(locks)} lock keys",
                "locks": locks,
                "count": len(locks),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error listing locks: {e}",
                "locks": [],
                "count": 0,
                "error": str(e),
            }
