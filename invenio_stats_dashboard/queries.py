# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Queries for the stats dashboard."""

from typing import Any
import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from .utils.utils import (
    get_subcount_field,
    get_subcount_label_includes,
    get_subcount_combine_subfields,
)


def get_relevant_record_ids_from_events(
    start_date: str,
    end_date: str,
    community_id: str,
    find_deleted: bool = False,
    use_included_dates: bool = False,
    use_published_dates: bool = False,
    event_index: str = "stats-community-events",
    client=None,
):
    """Get relevant record IDs from the events index.

    This function queries the stats-community-events index to find record IDs
    that match the given criteria.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        community_id (str): The community ID. Must not be "global" unless
            use_published_dates=True.
        find_deleted (bool, optional): Whether to find deleted records.
        use_included_dates (bool, optional): Whether to use the dates when the record
            was added to the community instead of the created date.
        use_published_dates (bool, optional): Whether to use the metadata publication
            date instead of the created date.
        event_index (str, optional): The events index to query. Defaults to
            "stats-community-events".
        client: The OpenSearch client to use.

    Returns:
        set: A set of record IDs that match the criteria.

    Raises:
        ValueError: If community_id is "global" and use_published_dates=False.
    """
    if client is None:
        from invenio_search.proxies import current_search_client

        client = current_search_client

    # Validate that community_id is not "global" unless use_published_dates=True
    # Global queries are only supported for published dates since we now have
    # global events
    if community_id == "global" and not use_published_dates:
        raise ValueError(
            "get_relevant_record_ids_from_events should not be called with "
            "community_id='global' unless use_published_dates=True. "
            "Other global queries should use record date fields directly."
        )

    # Determine which date field to use based on the parameters
    if use_published_dates:
        date_field = "record_published_date"
    elif use_included_dates:
        date_field = "event_date"
    else:
        date_field = "record_created_date"

    # Build the query for the events index
    should_clauses: list[Any] = []

    if find_deleted:
        # For deleted records, we need to find records that were deleted in the
        # given period. We look for either "removed" events OR records marked as
        # deleted.
        removed_event_clause = {
            "bool": {
                "must": [
                    {"term": {"event_type": "removed"}},
                    {"range": {"event_date": {"gte": start_date, "lte": end_date}}},
                    {"term": {"community_id": community_id}},
                ]
            }
        }
        should_clauses.append(removed_event_clause)

        deleted_event_clause = {
            "bool": {
                "must": [
                    {"term": {"is_deleted": True}},
                    {"range": {"deleted_date": {"gte": start_date, "lte": end_date}}},
                    {"term": {"community_id": community_id}},
                ]
            }
        }
        should_clauses.append(deleted_event_clause)
    else:
        # For non-deleted records, we need to find records that were
        # created/added/published
        # in the given period and are still active (not deleted)
        must_clauses = [
            {"range": {date_field: {"gte": start_date, "lte": end_date}}},
            {"term": {"community_id": community_id}},
        ]

        # For non-deleted records, we want to exclude records that were deleted
        # before the start of our search period (but include those deleted on
        # the same day)
        must_not_clauses = [
            {
                "bool": {
                    "must": [
                        {"term": {"is_deleted": True}},
                        {"range": {"deleted_date": {"lt": start_date}}},
                    ]
                }
            }
        ]

        should_clauses.append(
            {
                "bool": {
                    "must": must_clauses,
                    "must_not": must_not_clauses,
                }
            }
        )

    # Execute the query
    query = {
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        },
        "size": 10000,  # Adjust as needed
        "_source": ["record_id"],
    }

    result = client.search(index=prefix_index(event_index), body=query)

    # Extract record IDs from the results
    record_ids = set()
    for hit in result["hits"]["hits"]:
        record_id = hit["_source"]["record_id"]
        record_ids.add(record_id)

    return record_ids


class CommunityUsageDeltaQuery:
    """Query builder for community usage delta aggregation.

    This class encapsulates the logic for building aggregation queries
    on the enriched event indices
    """

    def __init__(
        self,
        client=None,
        view_index="events-stats-record-view",
        download_index="events-stats-file-download",
    ):
        """Initialize the query builder.

        Args:
            client: The OpenSearch client to use.
            view_index (str, optional): The view events index name. Defaults to
                "events-stats-record-view".
            download_index (str, optional): The download events index name. Defaults to
                "events-stats-file-download".
        """
        if client is None:
            client = current_search_client
        self.client = client
        self.view_index = view_index
        self.download_index = download_index

    def build_view_query(
        self,
        community_id: str,
        start_date: arrow.Arrow | str,
        end_date: arrow.Arrow | str,
    ) -> Search:
        """Build a query for view events.

        Args:
            community_id (str): The community ID to query for.
            start_date (arrow.Arrow | str): The start date to aggregate for.
            end_date (arrow.Arrow | str): The end date to aggregate for.

        Returns:
            Search: The search object for view events.
        """
        if isinstance(start_date, str):
            start_date = arrow.get(start_date)
        if isinstance(end_date, str):
            end_date = arrow.get(end_date)
        query_dict = self._build_query_dict(community_id, start_date, end_date, "view")
        view_search = (
            Search(using=self.client, index=prefix_index(self.view_index))
            .update_from_dict(query_dict)
            .extra(size=1)
        )
        return view_search

    def build_download_query(
        self,
        community_id: str,
        start_date: arrow.Arrow | str,
        end_date: arrow.Arrow | str,
    ) -> Search:
        """Build a query for download events.

        Args:
            community_id (str): The community ID to query for.
            start_date (arrow.Arrow | str): The start date to aggregate for.
            end_date (arrow.Arrow | str): The end date to aggregate for.

        Returns:
            Search: The search object for download events.
        """
        if isinstance(start_date, str):
            start_date = arrow.get(start_date)
        if isinstance(end_date, str):
            end_date = arrow.get(end_date)
        query_dict = self._build_query_dict(
            community_id, start_date, end_date, "download"
        )
        download_search = (
            Search(using=self.client, index=prefix_index(self.download_index))
            .update_from_dict(query_dict)
            .extra(size=1)
        )
        return download_search

    def _build_query_dict(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        event_type: str,
    ) -> dict:
        """Build a query dictionary for view or download events.

        Args:
            community_id (str): The community ID to query for.
            start_date (arrow.Arrow): The start date to aggregate for.
            end_date (arrow.Arrow): The end date to aggregate for.
            event_type (str): The type of event (view or download).

        Returns:
            dict: The query dictionary for view or download events.
        """
        query_dict = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": (
                                        start_date.floor("day").format(
                                            "YYYY-MM-DDTHH:mm:ss"
                                        )
                                    ),
                                    "lt": (
                                        end_date.ceil("day").format(
                                            "YYYY-MM-DDTHH:mm:ss"
                                        )
                                    ),
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": self._make_metrics_dict(event_type),
        }

        # Add community filter if not global
        if community_id != "global":
            query_dict["query"]["bool"]["must"].append(
                {"term": {"community_ids": community_id}}
            )

        # Add subcount aggregations
        query_dict["aggs"].update(self._make_subcount_aggregations_dict(event_type))

        return query_dict

    def _make_metrics_dict(self, event_type: str) -> dict:
        """Get the metrics dictionary for view events.

        Returns:
            dict: The metrics dictionary for view events.
        """
        metrics_dict = {
            "total_events": {"value_count": {"field": "_id"}},
            "unique_visitors": {"cardinality": {"field": "visitor_id"}},
            "unique_records": {"cardinality": {"field": "recid"}},
            "unique_parents": {"cardinality": {"field": "parent_recid"}},
        }
        if event_type == "download":
            metrics_dict["unique_files"] = {"cardinality": {"field": "file_id"}}
            metrics_dict["total_volume"] = {"sum": {"field": "size"}}
        return metrics_dict

    def _make_simple_subcount_aggregation(self, field: str, event_type: str) -> dict:
        """Make a simple subcount aggregation.

        Args:
            field (str): The field to aggregate on.
            event_type (str): The type of event (view or download).
        """
        return {
            "terms": {"field": field, "size": 1000},
            "aggs": {
                **self._make_metrics_dict(event_type),
            },
        }

    def _make_labeled_subcount_aggregation(
        self, field: str, label_source_includes: list[str], event_type: str
    ) -> dict:
        """Make a labeled subcount aggregation.

        Args:
            field (str): The field to aggregate on.
            label_source_includes (list[str]): The fields to include in the label.
            event_type (str): The type of event (view or download).
        """
        agg = self._make_simple_subcount_aggregation(field, event_type)
        agg["aggs"]["label"] = {
            "top_hits": {
                "size": 1,
                "_source": {"includes": label_source_includes},
            }
        }
        return agg

    def _make_subcount_aggregations_dict(self, event_type: str, index: int = 0) -> dict:
        """Get the subcount aggregations dictionary for view events.

        Returns:
            dict: The subcount aggregations dictionary for view events.
        """
        subcount_configs = current_app.config["COMMUNITY_STATS_SUBCOUNTS"]
        subcounts = {}
        for subcount_key, config in subcount_configs.items():
            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            # Iterate over source_fields
            source_fields = usage_config.get("source_fields", [])
            for field_index, _source_field in enumerate(source_fields):
                combine_subfields = get_subcount_combine_subfields(
                    usage_config, field_index
                )

                if combine_subfields and len(combine_subfields) > 1:
                    # Handle combined subfields (e.g., id and name.keyword)
                    for subfield in combine_subfields:
                        if len(source_fields) > 1:
                            query_name = f"{subcount_key}_{field_index}_{subfield.split('.')[-1]}"
                        else:
                            query_name = f"{subcount_key}_{subfield.split('.')[-1]}"
                        subcounts[query_name] = self._make_labeled_subcount_aggregation(
                            subfield,
                            get_subcount_label_includes(usage_config, field_index),
                            event_type,
                        )
                elif get_subcount_field(usage_config, "label_field", field_index):
                    # Handle single field with label
                    field = get_subcount_field(usage_config, "field", field_index)
                    if field:
                        if len(source_fields) > 1:
                            query_name = f"{subcount_key}_{field_index}"
                        else:
                            query_name = subcount_key
                        subcounts[query_name] = self._make_labeled_subcount_aggregation(
                            field,
                            get_subcount_label_includes(usage_config, field_index),
                            event_type,
                        )
                else:
                    # Handle simple field without label
                    field = get_subcount_field(usage_config, "field", field_index)
                    if field:
                        if len(source_fields) > 1:
                            query_name = f"{subcount_key}_{field_index}"
                        else:
                            query_name = subcount_key
                        subcounts[query_name] = self._make_simple_subcount_aggregation(
                            field, event_type
                        )
        return subcounts


class CommunityUsageSnapshotQuery:
    """Query builder for community usage snapshot aggregation.

    This class encapsulates the logic for building queries needed by the
    CommunityUsageSnapshotAggregator, including queries for last snapshot
    documents, daily deltas, and dependency checking.
    """

    def __init__(
        self,
        client=None,
        delta_index="stats-community-usage-delta",
        snapshot_index="stats-community-usage-snapshot",
    ):
        """Initialize the query builder.

        Args:
            client: The OpenSearch client to use.
            delta_index: The index containing usage delta records.
            snapshot_index: The index containing usage snapshot records.
        """
        if client is None:
            client = current_search_client
        self.client = client
        self.delta_index = delta_index
        self.snapshot_index = snapshot_index

    def build_last_snapshot_query(
        self,
        community_id: str,
        start_date: arrow.Arrow,
    ) -> Search:
        """Build a query for the last snapshot document.

        Args:
            community_id (str): The community ID to query for.
            start_date (arrow.Arrow): The start date to find snapshots before.

        Returns:
            Search: The search object for the last snapshot.
        """
        if isinstance(start_date, str):
            start_date = arrow.get(start_date)

        search = (
            Search(using=self.client, index=prefix_index(self.snapshot_index))
            .query(
                Q(
                    "bool",
                    must=[
                        Q("term", community_id=community_id),
                        Q(
                            "range",
                            snapshot_date={
                                "lt": (
                                    start_date.floor("day").format(
                                        "YYYY-MM-DDTHH:mm:ss"
                                    )
                                ),
                            },
                        ),
                    ],
                )
            )
            .sort({"snapshot_date": {"order": "desc"}})
            .extra(size=1)
        )
        return search

    def build_daily_deltas_query(
        self,
        community_id: str,
        end_date: arrow.Arrow,
    ) -> Search:
        """Build a query for daily delta records.

        Args:
            community_id (str): The community ID to query for.
            end_date (arrow.Arrow): The end date for delta records.

        Returns:
            Search: The search object for daily deltas.
        """
        if isinstance(end_date, str):
            end_date = arrow.get(end_date)

        search = (
            Search(using=self.client, index=prefix_index(self.delta_index))
            .query(
                "bool",
                must=[
                    Q("term", community_id=community_id),
                    Q(
                        "range",
                        period_start={
                            "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                        },
                    ),
                ],
            )
            .sort({"period_start": {"order": "asc"}})
        )
        return search

    def build_dependency_check_query(
        self,
        community_id: str,
    ) -> Search:
        """Build a query for checking usage delta dependency.

        Args:
            community_id (str): The community ID to query for.

        Returns:
            Search: The search object for dependency checking.
        """
        search = (
            Search(using=self.client, index=prefix_index(self.delta_index))
            .query(Q("term", community_id=community_id))
            .extra(size=0)
        )
        search.aggs.bucket("max_date", "max", field="period_start")
        return search


class CommunityRecordDeltaQuery:
    """Query builder for community record delta aggregation.

    This class encapsulates the logic for building queries needed by the
    CommunityRecordDeltaAggregator, including queries for last snapshot
    documents, daily deltas, and dependency checking.
    """

    def __init__(
        self,
        client: OpenSearch | None = None,
        event_index: str | None = None,
        record_index: str | None = None,
        subcount_configs: dict | None = None,
    ):
        """Initialize the query builder.

        Args:
            client (OpenSearch | None, optional): The OpenSearch client to use.
            event_index (str | None, optional): The events index name. Defaults to
                "stats-community-events".
            record_index (str | None, optional): The records index name. Defaults to
                "rdmrecords-records".
            subcount_configs (dict | None, optional): The subcount configurations.
                Defaults to the global config.
        """
        if client is None:
            client = current_search_client  # type: ignore
        self.client = client
        self.event_index = event_index or "stats-community-events"
        self.record_index = record_index or "rdmrecords-records"
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNTS"]
        )

    def _get_must_clauses(
        self,
        start_date: str,
        end_date: str,
        community_id: str,
        find_deleted: bool,
        use_included_dates: bool,
        use_published_dates: bool,
    ) -> list[dict]:
        """Get the must clauses for the query.

        Args:
            start_date (str): The start date to query.
            end_date (str): The end date to query.
            community_id (str): The community ID. If "global", uses events index
                when use_published_dates=True, otherwise uses record date
                fields directly.
            find_deleted (bool): Whether to find deleted records.
            use_included_dates (bool): Whether to use the dates when the record
                was included to the community instead of the created date.
            use_published_dates (bool): Whether to use the metadata publication
                date instead of the created date.

        Returns:
            list: The must clauses for the query.
        """
        must_clauses: list[dict] = []

        # For global queries with use_published_dates=True, use the events index
        if community_id == "global" and use_published_dates:
            # Get relevant record IDs from the events index
            record_ids = get_relevant_record_ids_from_events(
                start_date=start_date,
                end_date=end_date,
                community_id="global",
                find_deleted=find_deleted,
                use_included_dates=use_included_dates,
                use_published_dates=use_published_dates,
                event_index=self.event_index,
                client=self.client,
            )

            # If no records found, return empty query
            if not record_ids:
                must_clauses = [{"term": {"_id": "no-matching-records"}}]
            else:
                # Build the query for the records index using the found record IDs
                must_clauses = [
                    {"terms": {"id": list(record_ids)}},
                    {"term": {"is_published": True}},
                ]
        elif community_id == "global":
            # For global queries without use_published_dates, use record date
            # fields directly
            date_series_field = "created"
            if find_deleted:
                date_series_field = "tombstone.removal_date"

            must_clauses = [
                {"term": {"is_published": True}},
            ]

            if find_deleted:
                must_clauses.append({"term": {"is_deleted": True}})
                must_clauses.append(
                    {"range": {date_series_field: {"gte": start_date, "lte": end_date}}}
                )
            else:
                must_clauses.append(
                    {"range": {date_series_field: {"gte": start_date, "lte": end_date}}}
                )
        else:
            # Get relevant record IDs from the events index
            record_ids = get_relevant_record_ids_from_events(
                start_date=start_date,
                end_date=end_date,
                community_id=community_id,
                find_deleted=find_deleted,
                use_included_dates=use_included_dates,
                use_published_dates=use_published_dates,
                client=self.client,
            )

            # If no records found, return empty query
            if not record_ids:
                must_clauses = [{"term": {"_id": "no-matching-records"}}]
            else:
                # Build the query for the records index using the found record IDs
                must_clauses = [
                    {"terms": {"id": list(record_ids)}},
                    {"term": {"is_published": True}},
                ]

        return must_clauses

    def _get_sub_aggregations(self) -> dict:
        """Get the sub aggregations for the query.

        Returns:
            dict: The sub aggregations for the query.
        """
        sub_aggs: dict = {}

        for subcount_key, config in self.subcount_configs.items():
            if (
                "records" in config.keys()
                and "source_fields" in config["records"].keys()
            ):
                records_config = config["records"]
                source_fields = records_config.get("source_fields", [])

                for field_index, _source_field in enumerate(source_fields):
                    sub_aggs = self._build_single_field_aggregation(
                        sub_aggs, records_config, subcount_key, field_index
                    )
        return sub_aggs

    def _make_subcount_agg_dict(self, field, label_field, label_includes):
        """Make a subcount aggregation dictionary."""
        return {
            "terms": {"field": field, "size": 1000},
            "aggs": {
                "with_files": {
                    "filter": {"term": {"files.enabled": True}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "without_files": {
                    "filter": {"term": {"files.enabled": False}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "file_count": {"value_count": {"field": "files.entries.key"}},
                "total_bytes": {"sum": {"field": "files.entries.size"}},
                **(
                    {
                        "label": {
                            "top_hits": {
                                "size": 1,
                                "_source": {
                                    "includes": (
                                        label_includes if label_includes else [field]
                                    )
                                },
                            }
                        }
                    }
                    if label_field
                    else {}
                ),
            },
        }

    def _build_single_field_aggregation(
        self, sub_aggs, records_config, subcount_key, field_index
    ):
        """Build a single aggregations for a single subcount's field/subfields."""
        field = get_subcount_field(records_config, "field", field_index)
        label_field = get_subcount_field(records_config, "label_field", field_index)
        label_includes = get_subcount_label_includes(records_config, field_index)

        if field_index > 0:
            agg_name = f"{subcount_key}_{field_index}"
        else:
            agg_name = subcount_key

        # Handle combined subfields (like affiliations.id and affiliations.name)
        combine_subfields = get_subcount_combine_subfields(records_config, field_index)
        if combine_subfields:
            current_app.logger.error(
                f"Creating combine_subfields aggregations for {subcount_key}: "
                f"{combine_subfields}"
            )
            for field in combine_subfields:
                field_name = field.split(".")[-1]
                if field_index > 0:
                    agg_name = f"{subcount_key}_{field_index}_{field_name}"
                else:
                    agg_name = f"{subcount_key}_{field_name}"
                current_app.logger.error(
                    f"Creating aggregation '{agg_name}' for field '{field}'"
                )
                sub_aggs[agg_name] = self._make_subcount_agg_dict(
                    field, label_field, label_includes
                )
        else:
            # Standard single field aggregation
            sub_aggs[agg_name] = self._make_subcount_agg_dict(
                field, label_field, label_includes
            )

        return sub_aggs

    def build_query(
        self,
        start_date: str,
        end_date: str,
        community_id: str | None = None,
        find_deleted: bool = False,
        use_included_dates: bool = False,
        use_published_dates: bool = False,
    ) -> Search:
        """Build the query for a delta of records using events index.

        This function first queries the events index to find relevant record IDs,
        then builds a query for the records index using those IDs.

        For global community queries (community_id="global"), this function uses
        the events index when use_published_dates=True (since we now have global
        events with parsed publication dates), otherwise uses record date fields
        directly.

        Args:
            start_date (str): The start date to query.
            end_date (str): The end date to query.
            community_id (str, optional): The community ID. If "global", uses
                events index when use_published_dates=True, otherwise uses record date
                fields directly.
                (Ignored for global queries)
            find_deleted (bool, optional): Whether to find deleted records.
            use_included_dates (bool, optional): Whether to use the dates when
                the record was included to the community instead of the created date.
                (Ignored for global queries)
            use_published_dates (bool, optional): Whether to use the metadata
                publication date instead of the created date.

        Returns:
            dict: The query for the daily record delta counts.
        """
        if community_id is None:
            raise ValueError("community_id must not be None")

        must_clauses = self._get_must_clauses(
            start_date,
            end_date,
            community_id,
            find_deleted,
            use_included_dates,
            use_published_dates,
        )

        sub_aggregations = self._get_sub_aggregations()

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": must_clauses,
                }
            },
            "aggs": {
                "total_records": {"value_count": {"field": "_id"}},
                "with_files": {
                    "filter": {"term": {"files.enabled": True}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "without_files": {
                    "filter": {"term": {"files.enabled": False}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "uploaders": {
                    "cardinality": {"field": "parent.access.owned_by.user"},
                },
                "file_count": {
                    "value_count": {"field": "files.entries.key"},
                },
                "total_bytes": {"sum": {"field": "files.entries.size"}},
                **sub_aggregations,
            },
        }

        search = Search(using=self.client, index=prefix_index(self.record_index))
        search.update_from_dict(query)

        return search
