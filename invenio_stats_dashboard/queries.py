"""Queries for the stats dashboard."""

from pprint import pformat

import arrow
from flask import current_app
from invenio_search.utils import prefix_index
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

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
    "license": [
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
    client=None,
):
    """Get relevant record IDs from the events index.

    This function queries the stats-community-events index to find record IDs
    that match the given criteria.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        community_id (str): The community ID. Must not be "global" unless use_published_dates=True.
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
            "get_relevant_record_ids_from_events should not be called with community_id='global' "
            "unless use_published_dates=True. Other global queries should use record date fields directly."
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

    result = client.search(index=prefix_index("stats-community-events"), body=query)

    # Extract record IDs from the results
    record_ids = set()
    for hit in result["hits"]["hits"]:
        record_id = hit["_source"]["record_id"]
        record_ids.add(record_id)

    return record_ids


def daily_record_snapshot_query_with_events(
    start_date: str,
    end_date: str,
    community_id: str | None = None,
    find_deleted: bool = False,
    use_included_dates: bool = False,
    use_published_dates: bool = False,
    client=None,
):
    """Build the query for a snapshot of one day's cumulative record counts using events index.

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
        use_included_dates (bool, optional): Whether to use the dates when the
            record was included to the community instead of the created date.
            (Ignored for global queries)
        use_published_dates (bool, optional): Whether to use the metadata
            publication date instead of the created date.
        client: The OpenSearch client to use.

    Returns:
        dict: The query for the daily record cumulative counts.
    """
    if community_id is None:
        raise ValueError("community_id must not be None")

    # For global queries with use_published_dates=True, use the events index
    # since we now have global events with properly parsed publication dates
    if community_id == "global" and use_published_dates:
        # Get relevant record IDs from the events index
        record_ids = get_relevant_record_ids_from_events(
            start_date=start_date,
            end_date=end_date,
            community_id="global",
            find_deleted=find_deleted,
            use_included_dates=use_included_dates,
            use_published_dates=use_published_dates,
            client=client,
        )

        # If no records found, return empty query
        if not record_ids:
            # Use an impossible query that will return no results but still execute aggregations
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

        must_clauses: list[dict] = []
        if find_deleted:
            must_clauses.append(
                {
                    "bool": {
                        "must": [
                            {"range": {"tombstone.removal_date": {"lte": end_date}}},
                            {"range": {date_series_field: {"lte": end_date}}},
                            {"term": {"is_published": True}},
                        ],
                    }
                }
            )
        else:
            must_clauses.append(
                {
                    "bool": {
                        "must": [
                            {"range": {date_series_field: {"lte": end_date}}},
                            {"term": {"is_published": True}},
                        ]
                    }
                }
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
            client=client,
        )

        # If no records found, return empty query
        if not record_ids:
            # Use an impossible query that will return no results but still execute aggregations
            must_clauses = [{"term": {"_id": "no-matching-records"}}]
        else:
            # Build the query for the records index using the found record IDs
            must_clauses = [
                {"terms": {"id": list(record_ids)}},
                {"term": {"is_published": True}},
            ]

    # Build aggregations (same for both global and community queries)
    sub_aggs = {
        f"by_{subcount_label}": {
            "terms": {"field": subcount_fields[0]},
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
                                        subcount_fields[1]
                                        if len(subcount_fields) > 1
                                        else subcount_fields[0]
                                    )
                                },
                            }
                        }
                    }
                    if len(subcount_fields) > 1
                    and not subcount_label.startswith("affiliation_")
                    else {}
                ),
            },
        }
        for subcount_label, subcount_fields in NESTED_AGGREGATIONS.items()
    }

    query = {
        "size": 0,
        "query": {"bool": {"must": must_clauses}},
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
            **sub_aggs,
            "by_file_type": {
                "terms": {"field": "files.entries.ext"},
                "aggs": {
                    "unique_records": {"cardinality": {"field": "_id"}},
                    "unique_parents": {"cardinality": {"field": "parent.id"}},
                    "total_bytes": {"sum": {"field": "files.entries.size"}},
                },
            },
        },
    }

    return query


def daily_record_delta_query_with_events(
    start_date: str,
    end_date: str,
    community_id: str | None = None,
    find_deleted: bool = False,
    use_included_dates: bool = False,
    use_published_dates: bool = False,
    client=None,
):
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
            client=client,
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
            client=client,
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

    # Build aggregations (same for both global and community queries)
    sub_aggs = {
        f"by_{subcount_label}": {
            "terms": {"field": subcount_fields[0]},
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
                                        subcount_fields[1]
                                        if len(subcount_fields) > 1
                                        else subcount_fields[0]
                                    )
                                },
                            }
                        }
                    }
                    if len(subcount_fields) > 1
                    else {}
                ),
            },
        }
        for subcount_label, subcount_fields in NESTED_AGGREGATIONS.items()
    }

    return {
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
            **sub_aggs,
            "by_file_type": {
                "terms": {"field": "files.entries.ext"},
                "aggs": {
                    "unique_records": {"cardinality": {"field": "_id"}},
                    "unique_parents": {"cardinality": {"field": "parent.id"}},
                    "total_bytes": {"sum": {"field": "files.entries.size"}},
                },
            },
        },
    }


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

    def __init__(self, client=None):
        """Initialize the query builder.

        Args:
            client: The OpenSearch client to use.
        """
        if client is None:
            from invenio_search.proxies import current_search_client

            client = current_search_client
        self.client = client
        self.view_index = "events-stats-record-view"
        self.download_index = "events-stats-file-download"

    def build_view_query(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
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
        query_dict = self._build_view_query_dict(community_id, start_date, end_date)
        return Search(using=self.client, index=self.view_index).update_from_dict(
            query_dict
        )

    def build_download_query(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
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
        query_dict = self._build_download_query_dict(community_id, start_date, end_date)
        return Search(using=self.client, index=self.download_index).update_from_dict(
            query_dict
        )

    def _build_view_query_dict(
        self, community_id: str, start_date: arrow.Arrow, end_date: arrow.Arrow
    ) -> dict:
        """Build a query dictionary for view events.

        Args:
            community_id (str): The community ID to query for.
            date (arrow.Arrow): The date to aggregate for.

        Returns:
            dict: The query dictionary for view events.
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
            "aggs": self._get_view_metrics_dict(),
        }

        # Add community filter if not global
        if community_id != "global":
            query_dict["query"]["bool"]["must"].append(
                {"term": {"community_ids": community_id}}
            )

        # Add subcount aggregations
        query_dict["aggs"].update(self._get_view_subcount_aggregations_dict())

        return query_dict

    def _build_download_query_dict(
        self, community_id: str, start_date: arrow.Arrow, end_date: arrow.Arrow
    ) -> dict:
        """Build a query dictionary for download events.

        Args:
            community_id (str): The community ID to query for.
            date (arrow.Arrow): The date to aggregate for.

        Returns:
            dict: The query dictionary for download events.
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
            "aggs": self._get_download_metrics_dict(),
        }

        # Add community filter if not global
        if community_id != "global":
            query_dict["query"]["bool"]["must"].append(
                {"term": {"community_ids": community_id}}
            )

        # Add subcount aggregations
        query_dict["aggs"].update(self._get_download_subcount_aggregations_dict())

        return query_dict

    def _get_view_metrics_dict(self) -> dict:
        """Get the metrics dictionary for view events.

        Returns:
            dict: The metrics dictionary for view events.
        """
        return {
            "unique_visitors": {"cardinality": {"field": "visitor_id"}},
            "unique_records": {"cardinality": {"field": "recid"}},
            "unique_parents": {"cardinality": {"field": "parent_recid"}},
        }

    def _get_download_metrics_dict(self) -> dict:
        """Get the metrics dictionary for download events.

        Returns:
            dict: The metrics dictionary for download events.
        """
        return {
            "unique_visitors": {"cardinality": {"field": "visitor_id"}},
            "unique_records": {"cardinality": {"field": "recid"}},
            "unique_parents": {"cardinality": {"field": "parent_recid"}},
            "unique_files": {"cardinality": {"field": "file_id"}},
            "total_volume": {"sum": {"field": "size"}},
        }

    def _get_view_subcount_aggregations_dict(self) -> dict:
        """Get the subcount aggregations dictionary for view events.

        Returns:
            dict: The subcount aggregations dictionary for view events.
        """
        return {
            "by_resource_types": {
                "terms": {"field": "resource_type.id", "size": 1000},
                "aggs": {
                    **self._get_view_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": [
                                    "resource_type.title.en",
                                    "resource_type.id",
                                ]
                            },
                        }
                    },
                },
            },
            "by_access_status": {
                "terms": {"field": "access_status", "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            },
            "by_languages": {
                "terms": {"field": "languages.id", "size": 1000},
                "aggs": {
                    **self._get_view_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": ["languages.title", "languages.id"]
                            },
                        }
                    },
                },
            },
            "by_subjects": {
                "terms": {"field": "subjects.id", "size": 1000},
                "aggs": {
                    **self._get_view_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {"includes": ["subjects.title", "subjects.id"]},
                        }
                    },
                },
            },
            "by_licenses": {
                "terms": {"field": "rights.id", "size": 1000},
                "aggs": {
                    **self._get_view_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {"includes": ["rights.title", "rights.id"]},
                        }
                    },
                },
            },
            "by_funders": {
                "nested": {"path": "funders"},
                "aggs": {
                    "by_funder_combinations": {
                        "composite": {
                            "size": 1000,
                            "sources": [
                                {"funder_id": {"terms": {"field": "funders.id"}}},
                                {"funder_name": {"terms": {"field": "funders.name"}}},
                            ],
                        },
                        "aggs": {
                            **self._get_view_metrics_dict(),
                            "label": {
                                "top_hits": {
                                    "size": 1,
                                    "_source": {
                                        "includes": ["funders.name", "funders.id"]
                                    },
                                }
                            },
                        },
                    }
                },
            },
            "by_periodicals": {
                "terms": {"field": "journal_title", "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            },
            "by_publishers": {
                "terms": {"field": "publisher", "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            },
            "by_affiliations": {
                "nested": {"path": "affiliations"},
                "aggs": {
                    "by_affiliation_combinations": {
                        "composite": {
                            "size": 1000,
                            "sources": [
                                {
                                    "affiliation_id": {
                                        "terms": {"field": "affiliations.id"}
                                    }
                                },
                                {
                                    "affiliation_name": {
                                        "terms": {"field": "affiliations.name"}
                                    }
                                },
                            ],
                        },
                        "aggs": {
                            **self._get_view_metrics_dict(),
                            "label": {
                                "top_hits": {
                                    "size": 1,
                                    "_source": {
                                        "includes": [
                                            "affiliations.name",
                                            "affiliations.id",
                                        ]
                                    },
                                }
                            },
                        },
                    }
                },
            },
            "by_countries": {
                "terms": {"field": "country", "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            },
            "by_referrers": {
                "terms": {"field": "referrer", "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            },
            "by_file_types": {
                "terms": {"field": "file_types", "size": 1000},
                "aggs": self._get_view_metrics_dict(),
            },
        }

    def _get_download_subcount_aggregations_dict(self) -> dict:
        """Get the subcount aggregations dictionary for download events.

        Returns:
            dict: The subcount aggregations dictionary for download events.
        """
        return {
            "by_resource_types": {
                "terms": {"field": "resource_type.id", "size": 1000},
                "aggs": {
                    **self._get_download_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": [
                                    "resource_type.title.en",
                                    "resource_type.id",
                                ]
                            },
                        }
                    },
                },
            },
            "by_access_status": {
                "terms": {"field": "access_status", "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            },
            "by_languages": {
                "terms": {"field": "languages.id", "size": 1000},
                "aggs": {
                    **self._get_download_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": ["languages.title", "languages.id"]
                            },
                        }
                    },
                },
            },
            "by_subjects": {
                "terms": {"field": "subjects.id", "size": 1000},
                "aggs": {
                    **self._get_download_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {"includes": ["subjects.title", "subjects.id"]},
                        }
                    },
                },
            },
            "by_licenses": {
                "terms": {"field": "rights.id", "size": 1000},
                "aggs": {
                    **self._get_download_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {"includes": ["rights.title", "rights.id"]},
                        }
                    },
                },
            },
            "by_funders": {
                "composite": {
                    "size": 1000,
                    "sources": [
                        {"funder_id": {"terms": {"field": "funders.id"}}},
                        {"funder_name": {"terms": {"field": "funders.name"}}},
                    ],
                },
                "aggs": {
                    **self._get_download_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {"includes": ["funders.name", "funders.id"]},
                        }
                    },
                },
            },
            "by_periodicals": {
                "terms": {"field": "journal_title", "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            },
            "by_publishers": {
                "terms": {"field": "publisher", "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            },
            "by_affiliations": {
                "composite": {
                    "size": 1000,
                    "sources": [
                        {"affiliation_id": {"terms": {"field": "affiliations.id"}}},
                        {"affiliation_name": {"terms": {"field": "affiliations.name"}}},
                    ],
                },
                "aggs": {
                    **self._get_download_metrics_dict(),
                    "label": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": [
                                    "affiliations.name",
                                    "affiliations.id",
                                ]
                            },
                        }
                    },
                },
            },
            "by_countries": {
                "terms": {"field": "country", "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            },
            "by_referrers": {
                "terms": {"field": "referrer", "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            },
            "by_file_types": {
                "terms": {"field": "file_type", "size": 1000},
                "aggs": self._get_download_metrics_dict(),
            },
        }
