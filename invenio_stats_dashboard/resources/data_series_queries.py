# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Data series API query classes for invenio-stats-dashboard."""

import arrow
from flask import Response, current_app
from invenio_communities.proxies import current_communities
from invenio_access.permissions import system_identity
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from .content_negotiation import ContentNegotiationMixin
from ..transformers.base import (
    DataSeries,
    UsageSnapshotDataSeries,
    UsageDeltaDataSeries,
    RecordSnapshotDataSeries,
    RecordDeltaDataSeries,
)


class DataSeriesQueryBase(Query, ContentNegotiationMixin):
    """Base class for data series API queries."""

    date_field: str  # Type annotation for child classes
    transformer_class: type[DataSeries]  # Type annotation for transformer class

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
        category: str = "global",
        metric: str = "views",
        subcount_id: str | None = None,
    ) -> Response | DataSeries | dict:
        """Run the query to generate a single data series.

        Args:
            community_id: The community ID (UUID or slug). If "global", the
                query will be run for the entire repository. Default is "global".
            start_date: The start date. Can be a date string parseable by
                arrow.get() or a datetime object.
            end_date: The end date. Can be a date string parseable by
                arrow.get() or a datetime object.
            category: The category of the series ('global', 'access_statuses', etc.)
            metric: The metric type ('views', 'downloads', 'visitors', 'dataVolume')
            subcount_id: Specific subcount item ID (for subcount series)

        Returns:
            DataSeries object or Response with serialized data
        """
        # Resolve community ID if not global
        if community_id != "global":
            try:
                community = current_communities.service.read(
                    system_identity, community_id
                )
                community_id = community.id
            except Exception as e:
                raise ValueError(f"Community {community_id} not found: {str(e)}")

        # Build search query
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

        # Execute search
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
            if count == 0:
                raise ValueError(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date}"
                )
            response = agg_search.execute()
            documents = [h["_source"].to_dict() for h in response.hits.hits]
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {self.index} {e}")
            documents = []

        # Create data series
        series = self.transformer_class(
            series_id=f"{community_id}_{category}_{metric}",
            name=f"{category.title()} {metric.title()}",
            raw_documents=documents,
            category=category,
            metric=metric,
            subcount_id=subcount_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Handle content negotiation
        if self.should_use_content_negotiation(self.name):
            return self.serialize_response(series.for_json(), query_name=self.name)
        else:
            return series


class UsageSnapshotDataSeriesQuery(DataSeriesQueryBase):
    """Query for usage snapshot data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = UsageSnapshotDataSeries


class UsageDeltaDataSeriesQuery(DataSeriesQueryBase):
    """Query for usage delta data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = UsageDeltaDataSeries


class RecordSnapshotDataSeriesQuery(DataSeriesQueryBase):
    """Query for record snapshot data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = RecordSnapshotDataSeries


class RecordDeltaDataSeriesQuery(DataSeriesQueryBase):
    """Query for record delta data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = RecordDeltaDataSeries


class CategoryDataSeriesQueryBase(Query, ContentNegotiationMixin):
    """Base class for category-wide data series queries."""

    date_field: str  # Type annotation for child classes
    transformer_class: type[DataSeries]  # Type annotation for transformer class

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
    ) -> Response | dict[str, DataSeries] | dict:
        """Run the query to generate all data series for a category.

        Args:
            community_id: The community ID (UUID or slug). If "global", the
                query will be run for the entire repository. Default is "global".
            start_date: The start date. Can be a date string parseable by
                arrow.get() or a datetime object.
            end_date: The end date. Can be a date string parseable by
                arrow.get() or a datetime object.

        Returns:
            Dictionary of DataSeries objects or Response with serialized data
        """
        # Resolve community ID if not global
        if community_id != "global":
            try:
                community = current_communities.service.read(
                    system_identity, community_id
                )
                community_id = community.id
            except Exception as e:
                raise ValueError(f"Community {community_id} not found: {str(e)}")

        # Build search query
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

        # Execute search
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
            if count == 0:
                raise ValueError(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date}"
                )
            response = agg_search.execute()
            documents = [h["_source"].to_dict() for h in response.hits.hits]
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {self.index} {e}")
            documents = []

        # Create data series for all metrics and categories
        series_dict = {}
        # Global series
        for metric in ["views", "downloads", "visitors", "dataVolume"]:
            series = self.transformer_class(
                series_id=f"{community_id}_global_{metric}",
                name=f"Global {metric.title()}",
                raw_documents=documents,
                category="global",
                metric=metric,
                start_date=start_date,
                end_date=end_date,
            )
            series_dict[f"global_{metric}"] = series

        # Subcount series for each category
        subcount_categories = [
            "access_statuses",
            "resource_types",
            "subjects",
            "languages",
            "rights",
            "funders",
            "affiliations",
            "countries",
            "referrers",
            "file_types",
        ]

        for category in subcount_categories:
            for metric in ["views", "downloads", "visitors", "dataVolume"]:
                series = self.transformer_class(
                    series_id=f"{community_id}_{category}_{metric}",
                    name=f"{category.title()} {metric.title()}",
                    raw_documents=documents,
                    category=category,
                    metric=metric,
                    start_date=start_date,
                    end_date=end_date,
                )
                series_dict[f"{category}_{metric}"] = series

        # Handle content negotiation
        if self.should_use_content_negotiation(self.name):
            # Convert DataSeries objects to dicts for serialization
            serializable_dict = {}
            for key, series in series_dict.items():
                serializable_dict[key] = series.for_json()
            return self.serialize_response(serializable_dict, query_name=self.name)
        else:
            return series_dict


class UsageSnapshotCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all usage snapshot data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = UsageSnapshotDataSeries


class UsageDeltaCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all usage delta data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = UsageDeltaDataSeries


class RecordSnapshotCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all record snapshot data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = RecordSnapshotDataSeries


class RecordDeltaCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all record delta data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = RecordDeltaDataSeries
