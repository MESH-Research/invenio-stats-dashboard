# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""API query classes for invenio-stats-dashboard."""

import datetime
from typing import Any

import arrow
from flask import Response, current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search


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

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Base implementation returns the index as-is. Child classes can override
        to append the date_basis suffix.

        Returns:
            str: Index name
        """
        return str(self.index)

    def run(
        self,
        community_id: str = "global",
        start_date: str | datetime.datetime | None = None,
        end_date: str | datetime.datetime | None = None,
        date_basis: str = "added",
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
            date_basis (str): The date basis for the query ("added", "created",
                "published"). Default is "added".

        Raises:
            ValueError: if the community can't be found.
            AssertionError: if the index doesn't exist.

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
                raise ValueError(f"Community {community_id} not found: {str(e)}") from e

        # Select the appropriate index based on date_basis
        search_index = self._get_index_for_date_basis(date_basis)

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
        index_pattern = f"{search_index}-*"

        try:
            if self.client.indices.exists_alias(name=search_index):
                final_search_index = search_index
            else:
                indices = self.client.indices.get(index_pattern)
                if not indices:
                    raise AssertionError(
                        f"No indices found for alias '{search_index}' or pattern "
                        f"{index_pattern}'"
                    )
                final_search_index = index_pattern

            agg_search = (
                Search(using=self.client, index=final_search_index)
                .query(Q("bool", must=must_clauses))
                .extra(size=10_000)
            )
            agg_search.sort(self.date_field)

            count = agg_search.count()
            if count == 0:
                raise ValueError(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date}"
                )
            response = agg_search.execute()
            results = [h["_source"].to_dict() for h in response.hits.hits]
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {self.index} {e}")

        # Return raw data only - content negotiation handled by view
        return results


class CommunityRecordDeltaResultsQuery(CommunityStatsResultsQueryBase):
    """Query for community record delta results.

    This query retrieves record delta statistics for a community, showing
    changes in record counts over time. The query supports different date
    bases (added, created, published) to filter records by different
    temporal criteria.

    Args:
        name: Query name identifier
        index: Base index name (date basis will be appended automatically)
        client: OpenSearch client instance
    """

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Returns:
            str: Full index name with date basis added.
        """
        return f"{self.index}-{date_basis}"


class CommunityRecordSnapshotResultsQuery(CommunityStatsResultsQueryBase):
    """Query for community record snapshot results."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Returns:
            str: Full index name with date basis added.
        """
        return f"{self.index}-{date_basis}"


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

    def run(
        self,
        community_id: str = "global",
        start_date: str | None = None,
        end_date: str | None = None,
        date_basis: str = "added",
    ) -> Response | dict[str, Any]:
        """Run the query.

        Args:
            community_id: The community ID (UUID or slug). If "global", the
                query will be run for the entire repository. Default is "global".
            start_date: The start date. Can be a date string parseable by
                arrow.get() or a datetime object.
            end_date: The end date. Can be a date string parseable by
                arrow.get() or a datetime object.
            date_basis: The date basis for the query ("added", "created",
                "published"). Default is "added".

        Returns:
            Dictionary containing results from all query types.
        """
        results = {}
        record_deltas = CommunityRecordDeltaResultsQuery(
            name=f"community-record-delta-{date_basis}",
            index="stats-community-records-delta",
            client=self.client,
        )
        results[f"record_deltas_{date_basis}"] = record_deltas.run(
            community_id, start_date, end_date, date_basis
        )
        record_snapshots = CommunityRecordSnapshotResultsQuery(
            name=f"community-record-snapshot-{date_basis}",
            index="stats-community-records-snapshot",
            client=self.client,
        )
        results[f"record_snapshots_{date_basis}"] = record_snapshots.run(
            community_id, start_date, end_date, date_basis
        )
        usage_deltas = CommunityUsageDeltaResultsQuery(
            name="community-usage-delta",
            index="stats-community-usage-delta",
            client=self.client,
        )
        results["usage_deltas"] = usage_deltas.run(
            community_id, start_date, end_date, date_basis
        )
        usage_snapshots = CommunityUsageSnapshotResultsQuery(
            name="community-usage-snapshot",
            index="stats-community-usage-snapshot",
            client=self.client,
        )
        results["usage_snapshots"] = usage_snapshots.run(
            community_id, start_date, end_date, date_basis
        )

        # Return raw data only - content negotiation handled by view
        return results
