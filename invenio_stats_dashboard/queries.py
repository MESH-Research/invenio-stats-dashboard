"""Queries for the stats dashboard."""

from itertools import tee

import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from tests.services.schemas.test_publication_date import test_date

NESTED_AGGREGATIONS = {
    "resource_type": [
        "metadata.resource_type.id",
        ["metadata.resource_type.title.en", "metadata.resource_type.id"],
    ],
    "access_status": ["access.status"],
    "language": [
        "metadata.languages.id",
        ["metadata.languages.title.en", "metadata.languages.id"],
    ],
    "affiliation_creator_id": [
        "metadata.creators.affiliations.id",
        [
            "metadata.creators.affiliations.name.keyword",
            "metadata.creators.affiliations.id",
        ],
    ],
    "affiliation_creator_name": [
        "metadata.creators.affiliations.name.keyword",
        [
            "metadata.creators.affiliations.name.keyword",
            "metadata.creators.affiliations.id",
        ],
    ],
    "affiliation_contributor_id": [
        "metadata.contributors.affiliations.id",
        [
            "metadata.contributors.affiliations.name.keyword",
            "metadata.contributors.affiliations.id",
        ],
    ],
    "affiliation_contributor_name": [
        "metadata.contributors.affiliations.name.keyword",
        [
            "metadata.contributors.affiliations.name.keyword",
            "metadata.contributors.affiliations.id",
        ],
    ],
    "funder": [
        "metadata.funding.funder.id",
        ["metadata.funding.funder.title.en", "metadata.funding.funder.id"],
    ],
    "subject": [
        "metadata.subjects.id",
        [
            "metadata.subjects.subject",
            "metadata.subjects.id",
            "metadata.subjects.scheme",
        ],
    ],
    "publisher": ["metadata.publisher.keyword"],
    "periodical": ["custom_fields.journal:journal.title.keyword"],
    "file_type": ["files.entries.ext"],
    "rights": [
        "metadata.rights.id",
        ["metadata.rights.title.en", "metadata.rights.id"],
    ],
}


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
    # Global queries are only supported for published dates since we now have global events
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
    should_clauses = []

    if find_deleted:
        # For deleted records, we need to find records that were deleted in the given period
        # We look for either "removed" events OR records marked as deleted
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
        # For non-deleted records, we need to find records that were created/added/published
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


class CommunityStatsResultsQueryBase(Query):
    """Base class for the stats dashboard API requests."""

    date_field: (
        str  # Type annotation to indicate this attribute will be set by child classes
    )

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)

    def run(self, community_id="global", start_date=None, end_date=None):
        """Run the query.

        Args:
            community_id (str): The community ID. If "global", the query will be run
                for the entire repository. Default is "global".
            start_date (str): The start date.
            end_date (str): The end date.

        Returns:
            list: The results of the query.
        """
        results = []
        must_clauses: list[dict] = [
            {"term": {"community_id": community_id}},
        ]
        range_clauses = {self.date_field: {}}
        if start_date:
            range_clauses[self.date_field]["gte"] = (
                arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss")
            )
        if end_date:
            range_clauses[self.date_field]["lte"] = (
                arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss")
            )
        if range_clauses:
            must_clauses.append({"range": range_clauses})
        try:
            assert Index(using=self.client, name=self.index).exists()

            agg_search = (
                Search(using=self.client, index=self.index)
                .query(Q("bool", must=must_clauses))
                .extra(size=10_000)
            )
            agg_search.sort(self.date_field)

            count = agg_search.count()
            current_app.logger.error(f"Count: {count}")
            if count == 0:
                raise ValueError(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date}"
                )
            response = agg_search.execute()
            results = [h["_source"].to_dict() for h in response.hits.hits]
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {self.index} {e}")
        return results


class CommunityRecordDeltaResultsQuery(CommunityStatsResultsQueryBase):
    """Query for community record delta results."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"


class CommunityRecordSnapshotResultsQuery(CommunityStatsResultsQueryBase):
    """Query for community record snapshot results."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"


class CommunityUsageDeltaResultsQuery(CommunityStatsResultsQueryBase):
    """Query for community usage delta results."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"


class CommunityUsageSnapshotResultsQuery(CommunityStatsResultsQueryBase):
    """Query for community usage snapshot results."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"


class CommunityStatsResultsQuery(Query):
    """Collected query for all stats dashboard API requests."""

    client: OpenSearch | None  # Type annotation to indicate the client type

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)

    def run(self, community_id="global", start_date=None, end_date=None):
        """Run the query."""
        results = {}
        record_deltas_created = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-created",
            index=prefix_index("stats-community-records-delta-created"),
            client=self.client,
        )
        results["record_deltas_created"] = record_deltas_created.run(
            community_id, start_date, end_date
        )
        record_deltas_published = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-published",
            index="stats-community-records-delta-published",
            client=self.client,
        )
        results["record_deltas_published"] = record_deltas_published.run(
            community_id, start_date, end_date
        )
        record_deltas_added = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-added",
            index="stats-community-records-delta-added",
            client=self.client,
        )
        results["record_deltas_added"] = record_deltas_added.run(
            community_id, start_date, end_date
        )
        record_snapshots_created = CommunityRecordSnapshotResultsQuery(
            name="community-record-snapshot-created",
            index="stats-community-records-snapshot-created",
            client=self.client,
        )
        results["record_snapshots_created"] = record_snapshots_created.run(
            community_id, start_date, end_date
        )
        record_snapshots_published = CommunityRecordSnapshotResultsQuery(
            name="community-record-snapshot-published",
            index="stats-community-records-snapshot-published",
            client=self.client,
        )
        results["record_snapshots_published"] = record_snapshots_published.run(
            community_id, start_date, end_date
        )
        record_snapshots_added = CommunityRecordSnapshotResultsQuery(
            name="community-record-snapshot-added",
            index="stats-community-records-snapshot-added",
            client=self.client,
        )
        results["record_snapshots_added"] = record_snapshots_added.run(
            community_id, start_date, end_date
        )
        usage_deltas = CommunityUsageDeltaResultsQuery(
            name="community-usage-delta",
            index="stats-community-usage-delta",
            client=self.client,
        )
        results["usage_deltas"] = usage_deltas.run(community_id, start_date, end_date)
        usage_snapshots = CommunityUsageSnapshotResultsQuery(
            name="community-usage-snapshot",
            index="stats-community-usage-snapshot",
            client=self.client,
        )
        results["usage_snapshots"] = usage_snapshots.run(
            community_id, start_date, end_date
        )
        return results


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
            date (arrow.Arrow): The date to aggregate for.

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
            date (arrow.Arrow): The date to aggregate for.

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
            date (arrow.Arrow): The date to aggregate for.

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
            label_source_includes (list[str]): The fields to include in the label.
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

    def _make_subcount_aggregations_dict(self, event_type: str) -> dict:
        """Get the subcount aggregations dictionary for view events.

        Returns:
            dict: The subcount aggregations dictionary for view events.
        """
        subcount_configs = current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
        subcounts = {}
        for config in subcount_configs.values():
            # Get the usage_events configuration for this subcount
            usage_config = config.get("usage_events", {})
            if not usage_config:
                continue

            if (
                usage_config.get("combine_queries")
                and len(usage_config["combine_queries"]) > 1
            ):
                for query_field in usage_config["combine_queries"]:
                    subfield = query_field.split(".")[-1]
                    query_name = f"{usage_config['delta_aggregation_name']}_{subfield}"
                    subcounts[query_name] = self._make_labeled_subcount_aggregation(
                        query_field,
                        usage_config["label_source_includes"],
                        event_type,
                    )
            elif usage_config.get("label_field"):
                subcounts[usage_config["delta_aggregation_name"]] = (
                    self._make_labeled_subcount_aggregation(
                        usage_config["field"],
                        usage_config["label_source_includes"],
                        event_type,
                    )
                )
            else:
                subcounts[usage_config["delta_aggregation_name"]] = (
                    self._make_simple_subcount_aggregation(
                        usage_config["field"], event_type
                    )
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
            client: The OpenSearch client to use.
        """
        if client is None:
            client = current_search_client
        self.client = client
        self.event_index = event_index or prefix_index("stats-community-events")
        self.record_index = record_index or prefix_index("rdmrecords-records")
        self.subcount_configs = (
            subcount_configs or current_app.config["COMMUNITY_STATS_SUBCOUNT_CONFIGS"]
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
            community_id (str, optional): The community ID. If "global", uses events index
                when use_published_dates=True, otherwise uses record date fields directly.
            find_deleted (bool, optional): Whether to find deleted records.

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
            # For global queries without use_published_dates, use record date fields directly
            # Field to use to find the period's records
            date_series_field = "created"
            if find_deleted:
                date_series_field = "tombstone.removal_date"

            must_clauses: list[dict] = [
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

        Args:
            start_date (str): The start date to query.
            end_date (str): The end date to query.
            community_id (str, optional): The community ID. If "global", uses events index
                when use_published_dates=True, otherwise uses record date fields directly.
            find_deleted (bool, optional): Whether to find deleted records.
            use_included_dates (bool, optional): Whether to use the dates when the record
                was included to the community instead of the created date.
            use_published_dates (bool, optional): Whether to use the metadata publication
                date instead of the created date.

        Returns:
            dict: The sub aggregations for the query.
        """
        sub_aggs: dict = {}

        for config in self.subcount_configs.values():
            if (
                "records" in config.keys()
                and "delta_aggregation_name" in config["records"].keys()
            ):
                records_config = config["records"]
                subcount_key = records_config["delta_aggregation_name"]

                # Handle combined queries (like affiliations)
                if records_config.get("combine_queries"):
                    current_app.logger.error(
                        f"Creating combine_queries aggregations for {subcount_key}: {records_config['combine_queries']}"
                    )
                    # For combined queries, we need to create separate aggregations
                    for field in records_config["combine_queries"]:
                        field_name = field.split(".")[-1]
                        agg_name = (
                            f"{records_config['delta_aggregation_name']}_{field_name}"
                        )
                        current_app.logger.error(
                            f"Creating aggregation '{agg_name}' for field '{field}'"
                        )
                        sub_aggs[agg_name] = {
                            "terms": {"field": field},
                            "aggs": {
                                "with_files": {
                                    "filter": {"term": {"files.enabled": True}},
                                    "aggs": {
                                        "unique_parents": {
                                            "cardinality": {"field": "parent.id"}
                                        }
                                    },
                                },
                                "without_files": {
                                    "filter": {"term": {"files.enabled": False}},
                                    "aggs": {
                                        "unique_parents": {
                                            "cardinality": {"field": "parent.id"}
                                        }
                                    },
                                },
                                "file_count": {
                                    "value_count": {"field": "files.entries.key"}
                                },
                                "total_bytes": {"sum": {"field": "files.entries.size"}},
                                **(
                                    {
                                        "label": {
                                            "top_hits": {
                                                "size": 1,
                                                "_source": {
                                                    "includes": (
                                                        records_config[
                                                            "label_source_includes"
                                                        ]
                                                        if records_config.get(
                                                            "label_source_includes"
                                                        )
                                                        else [field]
                                                    )
                                                },
                                            }
                                        }
                                    }
                                    if records_config.get("label_field")
                                    else {}
                                ),
                            },
                        }
                else:
                    # Standard single field aggregation
                    sub_aggs[subcount_key] = {
                        "terms": {"field": records_config["field"]},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                            **(
                                {
                                    "label": {
                                        "top_hits": {
                                            "size": 1,
                                            "_source": {
                                                "includes": (
                                                    records_config[
                                                        "label_source_includes"
                                                    ]
                                                    if records_config.get(
                                                        "label_source_includes"
                                                    )
                                                    else [records_config["field"]]
                                                )
                                            },
                                        }
                                    }
                                }
                                if records_config.get("label_field")
                                else {}
                            ),
                        },
                    }

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
        events with parsed publication dates), otherwise uses record date fields directly.

        Args:
            start_date (str): The start date to query.
            end_date (str): The end date to query.
            community_id (str, optional): The community ID. If "global", uses events index
                when use_published_dates=True, otherwise uses record date fields directly.
            find_deleted (bool, optional): Whether to find deleted records.
            use_included_dates (bool, optional): Whether to use the dates when the record
                was included to the community instead of the created date.
                (Ignored for global queries)
            use_published_dates (bool, optional): Whether to use the metadata publication
                date instead of the created date.
            client: The OpenSearch client to use.

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

        search = Search(using=self.client, index=self.record_index)
        search.update_from_dict(query)

        return search
