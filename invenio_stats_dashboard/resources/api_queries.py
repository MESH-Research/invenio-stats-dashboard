# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""API query classes for invenio-stats-dashboard."""

from typing import Any
import datetime
import arrow
from flask import current_app, Response
from invenio_communities.proxies import current_communities
from invenio_access.permissions import system_identity
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from .content_negotiation import ContentNegotiationMixin


class CommunityStatsResultsQueryBase(Query, ContentNegotiationMixin):
    """Base class for the stats dashboard API requests."""

    date_field: (
        str  # Type annotation to indicate this attribute will be set by child classes
    )

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)

    def run(
        self,
        community_id: str = "global",
        start_date: str | datetime.datetime | None = None,
        end_date: str | datetime.datetime | None = None,
    ) -> Response | list[dict[str, Any]] | dict[str, Any]:
        """Run the query.

        Performs content negotiation based on the query name and any
        serializers configured for the query. If no serializer is configured
        for the query, the query will return a dictionary or list of dictionaries
        which will be serialized to JSON by Flask.

        Args:
            community_id (str): The community ID (UUID or slug). If "global", the
                query will be run for the entire repository. Default is "global".
            start_date (str): The start date. Can be a date string parseable by
                arrow.get() or a datetime object.
            end_date (str): The end date. Can be a date string parseable by
                arrow.get() or a datetime object.

        Returns:
            Response | list[dict[str, Any]] | dict[str, Any]: The results of the query.
        """
        results = []
        if community_id != "global":
            try:
                community = current_communities.service.read(
                    system_identity, community_id
                )
                community_id = community.id
            except Exception as e:
                raise ValueError(f"Community {community_id} not found: {str(e)}")

        must_clauses: list[dict] = [
            {"term": {"community_id": community_id}},
        ]
        range_clauses: dict[str, dict[str, str]] = {self.date_field: {}}
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

        # The parent Query class has already applied prefix_index to self.index
        alias_name = self.index
        index_pattern = f"{alias_name}-*"

        try:
            if self.client.indices.exists_alias(name=alias_name):
                search_index = alias_name
            else:
                indices = self.client.indices.get(index_pattern)
                if not indices:
                    raise AssertionError(
                        f"No indices found for alias '{alias_name}' or pattern "
                        f"{index_pattern}'"
                    )
                search_index = index_pattern

            agg_search = (
                Search(using=self.client, index=search_index)
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

        if self.should_use_content_negotiation(self.name):
            return self.serialize_response(results, query_name=self.name)
        else:
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


class CommunityStatsResultsQuery(Query, ContentNegotiationMixin):
    """Collected query for all stats dashboard API requests."""

    client: OpenSearch | None  # Type annotation to indicate the client type

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)

    def run(
        self,
        community_id: str = "global",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Response | dict[str, Any]:
        """Run the query."""
        results = {}
        record_deltas_created = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-created",
            index="stats-community-records-delta-created",
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

        if self.should_use_content_negotiation(self.name):
            return self.serialize_response(results, query_name=self.name)
        else:
            return results
