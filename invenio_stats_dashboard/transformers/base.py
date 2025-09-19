# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Base classes and utilities for data series transformers."""

import json
from abc import ABC
from datetime import datetime
from typing import Any

from flask import current_app

from .types import (
    AggregationDocumentDict,
    DataPointDict,
    DataSeriesDict,
    SubcountSeriesDict,
    TransformationResult,
)


class DataPoint:
    """Represents a single data point in a time series."""

    def __init__(
        self,
        date: str | datetime,
        value: int | float,
        value_type: str = "number",
    ):
        """Initialize a data point.

        Args:
            date: Date string (YYYY-MM-DD) or datetime object
            value: Numeric value for this data point
            value_type: Type of value ('number', 'filesize', etc.)
        """
        if isinstance(date, datetime):
            self.date = date.strftime("%Y-%m-%d")
        else:
            self.date = date
        self.value = value
        self.value_type = value_type

    def to_dict(self) -> DataPointDict:
        """Convert to dictionary format matching JavaScript output."""
        return {
            "value": [self.date, self.value],
            "readableDate": self._format_readable_date(),
            "valueType": self.value_type,
        }

    def _format_readable_date(self) -> str:
        """Format date for human readability."""
        try:
            dt = datetime.strptime(self.date, "%Y-%m-%d")
            return dt.strftime("%b %d, %Y")
        except ValueError:
            return self.date


class DataSeries:
    """Represents a complete data series for charting.

    This is the primary interface for creating data series. When instantiated
    with raw data, it automatically generates data points using the appropriate
    transformer class.
    """

    def __init__(
        self,
        series_id: str,
        name: str,
        raw_documents: list[AggregationDocumentDict] | None = None,
        chart_type: str = "line",
        value_type: str = "number",
        category: str = "global",
        metric: str = "views",
        subcount_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        transformer_config: dict[str, Any] | None = None,
    ):
        """Initialize a data series.

        Args:
            series_id: Unique identifier for the series
            name: Display name for the series
            raw_documents: Raw aggregation documents to process
            chart_type: Type of chart ('line', 'bar', etc.)
            value_type: Type of values in the series
            category: Category of the series ('global', 'access_statuses', etc.)
            metric: Metric type ('views', 'downloads', 'visitors', 'dataVolume')
            subcount_id: Specific subcount item ID (for subcount series)
            start_date: Start date for filtering (YYYY-MM-DD format)
            end_date: End date for filtering (YYYY-MM-DD format)
            transformer_config: Configuration for the transformer
        """
        self.id = series_id
        self.name = name
        self.type = chart_type
        self.value_type = value_type
        self.category = category
        self.metric = metric
        self.subcount_id = subcount_id
        self.start_date = start_date
        self.end_date = end_date
        self.transformer_config = transformer_config or {}

        # Generate data points from raw documents
        if raw_documents is not None:
            self.data = self._generate_data_points(raw_documents)
        else:
            self.data = []

    def _get_transformer_class(self):
        """Get the appropriate transformer class for this data series type.

        Subclasses should override this method to return the correct transformer.
        """
        raise NotImplementedError("Subclasses must implement _get_transformer_class")

    def _generate_data_points(
        self, raw_documents: list[AggregationDocumentDict]
    ) -> list[DataPoint]:
        """Generate data points from raw documents using the appropriate transformer."""
        transformer_class = self._get_transformer_class()
        transformer = transformer_class(self.transformer_config)

        # Filter documents by date range if specified
        filtered_docs = self._filter_documents_by_date(raw_documents)

        # Extract data points using the transformer
        return transformer._extract_series_data(
            filtered_docs, self.category, self.metric, self.subcount_id
        )

    def _filter_documents_by_date(
        self, documents: list[AggregationDocumentDict]
    ) -> list[AggregationDocumentDict]:
        """Filter documents by date range if start_date/end_date are specified."""
        if not self.start_date and not self.end_date:
            return documents

        filtered = []
        for doc in documents:
            doc_date = self._extract_document_date(doc)
            if not doc_date:
                continue

            if self.start_date and doc_date < self.start_date:
                continue
            if self.end_date and doc_date > self.end_date:
                continue

            filtered.append(doc)
        return filtered

    def _extract_document_date(self, doc: AggregationDocumentDict) -> str | None:
        """Extract date from document in YYYY-MM-DD format."""
        # Try different date fields
        date_str = doc.get("snapshot_date") or doc.get("period_start")
        if not date_str:
            return None

        # Extract date part (before 'T' if present)
        return date_str.split("T")[0]

    def filter_by_date_range(self, start_date: str, end_date: str) -> "DataSeries":
        """Create a new series filtered to the specified date range."""
        # Filter the data points by date range
        filtered_data = []
        for dp in self.data:
            if start_date <= dp.date <= end_date:
                filtered_data.append(dp)

        # Create a new series with the filtered data
        new_series = self.__class__(
            series_id=self.id,
            name=self.name,
            raw_documents=None,
            chart_type=self.type,
            value_type=self.value_type,
            category=self.category,
            metric=self.metric,
            subcount_id=self.subcount_id,
            start_date=start_date,
            end_date=end_date,
            transformer_config=self.transformer_config,
        )
        new_series.data = filtered_data
        return new_series

    def get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics for the series."""
        if not self.data:
            return {"count": 0, "total": 0, "min": 0, "max": 0, "avg": 0}

        values = [dp.value for dp in self.data]
        return {
            "count": len(values),
            "total": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values) if values else 0,
        }

    def to_dict(self) -> DataSeriesDict:
        """Convert to dictionary format matching JavaScript output."""
        return {
            "id": self.id,
            "name": self.name,
            "data": [dp.to_dict() for dp in self.data],
            "type": self.type,
            "valueType": self.value_type,
        }

    def for_json(self) -> dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        result = dict(self.to_dict())

        if self.category != "global":
            result["category"] = self._to_camel_case(self.category)

        return result

    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case string to camelCase."""
        components = snake_str.split("_")
        return components[0] + "".join(word.capitalize() for word in components[1:])


class BaseDataSeriesTransformer(ABC):
    """Base class for transforming indexed documents into data series."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the transformer.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.subcount_configs = current_app.config.get(
            "COMMUNITY_STATS_SUBCOUNT_CONFIGS", {}
        )
        self.ui_subcounts = current_app.config.get("STATS_DASHBOARD_UI_SUBCOUNTS", {})

    def _extract_series_data(
        self,
        documents: list[AggregationDocumentDict],
        category: str,
        metric: str,
        subcount_id: str | None = None,
    ) -> list[DataPoint]:
        """Extract data points for a specific series.

        Args:
            documents: List of aggregation documents
            category: Series category ('global', 'accessStatuses', etc.)
            metric: Metric type ('views', 'downloads', 'visitors', 'dataVolume')
            subcount_id: Specific subcount item ID (for subcount series)

        Returns:
            List of DataPoint objects
        """
        raise NotImplementedError("Subclasses must implement _extract_series_data")

    def create_data_point(
        self,
        date: str | datetime,
        value: int | float,
        value_type: str = "number",
    ) -> DataPoint:
        """Create a data point object.

        Args:
            date: Date string or datetime object
            value: Numeric value
            value_type: Type of value

        Returns:
            DataPoint object
        """
        return DataPoint(date, value, value_type)

    def create_localization_map(
        self, documents: list[AggregationDocumentDict]
    ) -> dict[str, str]:
        """Create a localization map from documents.

        Args:
            documents: List of documents containing subcount data

        Returns:
            Dictionary mapping subcount id to localized label
        """
        localization_map = {}

        # Collect all unique subcount items from all documents
        all_subcount_items: dict[str, list[SubcountSeriesDict]] = {}

        for doc in documents:
            subcounts = doc.get("subcounts")
            if subcounts is None:
                continue
            for subcount_type, subcount_series in subcounts.items():
                if isinstance(subcount_series, list):
                    if subcount_type not in all_subcount_items:
                        all_subcount_items[subcount_type] = []

                    for item in subcount_series:
                        if not any(
                            existing.get("id") == item.get("id")
                            for existing in all_subcount_items[subcount_type]
                        ):
                            all_subcount_items[subcount_type].append(item)

        # Process each subcount category to create the localization map
        for category_key, subcount_items in all_subcount_items.items():
            for item in subcount_items:
                item_id = item.get("id")
                item_label = item.get("label")

                if item_id and item_label:
                    # Handle both string and object labels
                    if isinstance(item_label, str):
                        localized_label = item_label
                    elif isinstance(item_label, dict):
                        # Use English as fallback, or first available language
                        localized_label = item_label.get(
                            "en", next(iter(item_label.values()), "")
                        )
                    else:
                        localized_label = str(item_label)

                    localization_map[item_id] = localized_label

        return localization_map

    def to_json(self, data: TransformationResult) -> str:
        """Convert data to JSON string matching JavaScript output format.

        Args:
            data: Transformed data dictionary

        Returns:
            JSON string
        """

        def convert_to_json_serializable(obj):
            """Recursively convert objects to JSON-serializable format."""
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            elif isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            else:
                return obj

        return json.dumps(convert_to_json_serializable(data), indent=2)


class UsageSnapshotDataSeries(DataSeries):
    """Data series for usage snapshot data."""

    def _get_transformer_class(self):
        """Return the usage snapshot transformer class."""
        from .usage_snapshot import UsageSnapshotDataSeriesTransformer

        return UsageSnapshotDataSeriesTransformer


class UsageDeltaDataSeries(DataSeries):
    """Data series for usage delta data."""

    def _get_transformer_class(self):
        """Return the usage delta transformer class."""
        from .usage_delta import UsageDeltaDataSeriesTransformer

        return UsageDeltaDataSeriesTransformer


class RecordSnapshotDataSeries(DataSeries):
    """Data series for record snapshot data."""

    def _get_transformer_class(self):
        """Return the record snapshot transformer class."""
        from .record_snapshot import RecordSnapshotDataSeriesTransformer

        return RecordSnapshotDataSeriesTransformer


class RecordDeltaDataSeries(DataSeries):
    """Data series for record delta data."""

    def _get_transformer_class(self):
        """Return the record delta transformer class."""
        from .record_delta import RecordDeltaDataSeriesTransformer

        return RecordDeltaDataSeriesTransformer
