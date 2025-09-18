# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Base classes and utilities for data series transformers."""

import json
from abc import ABC, abstractmethod
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
    """Represents a complete data series for charting."""

    def __init__(
        self,
        series_id: str,
        name: str,
        data_points: list[DataPoint],
        chart_type: str = "line",
        value_type: str = "number",
    ):
        """Initialize a data series.

        Args:
            series_id: Unique identifier for the series
            name: Display name for the series
            data_points: List of data points in the series
            chart_type: Type of chart ('line', 'bar', etc.)
            value_type: Type of values in the series
        """
        self.id = series_id
        self.name = name
        self.data = data_points
        self.type = chart_type
        self.value_type = value_type

    def to_dict(self) -> DataSeriesDict:
        """Convert to dictionary format matching JavaScript output."""
        return {
            "id": self.id,
            "name": self.name,
            "data": [dp.to_dict() for dp in self.data],
            "type": self.type,
            "valueType": self.value_type,
        }


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

    @abstractmethod
    def transform(
        self, documents: list[AggregationDocumentDict]
    ) -> TransformationResult:
        """Transform documents into data series.

        Args:
            documents: List of indexed documents to transform

        Returns:
            Dictionary containing transformed data series
        """
        pass

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

    def create_global_series(
        self,
        data_points: list[DataPoint],
        chart_type: str = "line",
        value_type: str = "number",
    ) -> DataSeries:
        """Create a global data series.

        Args:
            data_points: List of data points
            chart_type: Type of chart
            value_type: Type of values

        Returns:
            DataSeries object with id "global"
        """
        return DataSeries("global", "Global", data_points, chart_type, value_type)

    def create_data_series_array(
        self,
        series_names: list[str],
        data_points_array: list[dict[str, Any]] | None = None,
        chart_type: str = "line",
        value_type: str = "number",
    ) -> list[DataSeries]:
        """Create an array of data series from named properties.

        Args:
            series_names: List of property names to extract as separate series
            data_points_array: Array of data points with named properties
            chart_type: Chart type for all series
            value_type: Value type for all series

        Returns:
            List of DataSeries objects
        """
        if data_points_array is None:
            data_points_array = []

        series_array = []
        for name in series_names:
            series = DataSeries(name, name, [], chart_type, value_type)
            series_array.append(series)

        for point_obj in data_points_array:
            date = point_obj.get("date")
            if not date:
                continue

            for name in series_names:
                if name in point_obj:
                    target_series: DataSeries | None = next(
                        (s for s in series_array if s.name == name), None
                    )
                    if target_series is not None:
                        data_point = self.create_data_point(
                            date, point_obj[name], value_type
                        )
                        target_series.data.append(data_point)

        return series_array

    def create_data_series_from_items(
        self,
        subcount_items: list[dict[str, Any]],
        data_points_array: list[dict[str, Any]] | None = None,
        chart_type: str = "line",
        value_type: str = "number",
        localization_map: dict[str, str] | None = None,
    ) -> list[DataSeries]:
        """Create data series from subcount items.

        Args:
            subcount_items: List of subcount items with id and optional label
            data_points_array: Array of data points mapping subcount id to value
            chart_type: Chart type for all series
            value_type: Value type for all series
            localization_map: Map of subcount id to localized label

        Returns:
            List of DataSeries objects
        """
        if data_points_array is None:
            data_points_array = []
        if localization_map is None:
            localization_map = {}

        series_array = []
        for item in subcount_items:
            series_id = item.get("id", "")
            series_name = localization_map.get(series_id, series_id)
            series = DataSeries(series_id, series_name, [], chart_type, value_type)
            series_array.append(series)

        for point_obj in data_points_array:
            date = point_obj.get("date")
            if not date:
                continue

            for series in series_array:
                if series.id in point_obj:
                    data_point = self.create_data_point(
                        date, point_obj[series.id], value_type
                    )
                    series.data.append(data_point)

        return series_array

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


def create_transformer(
    transformer_type: str, config: dict[str, Any] | None = None
) -> BaseDataSeriesTransformer:
    """Create a transformer instance based on type.

    Args:
        transformer_type: Type of transformer ('record_delta', 'record_snapshot',
                         'usage_delta', 'usage_snapshot')
        config: Optional configuration dictionary

    Returns:
        Appropriate transformer instance

    Raises:
        ValueError: If transformer_type is not recognized
    """
    from .record_delta import RecordDeltaDataSeriesTransformer
    from .record_snapshot import RecordSnapshotDataSeriesTransformer
    from .usage_delta import UsageDeltaDataSeriesTransformer
    from .usage_snapshot import UsageSnapshotDataSeriesTransformer

    transformers = {
        "record_delta": RecordDeltaDataSeriesTransformer,
        "record_snapshot": RecordSnapshotDataSeriesTransformer,
        "usage_delta": UsageDeltaDataSeriesTransformer,
        "usage_snapshot": UsageSnapshotDataSeriesTransformer,
    }

    if transformer_type not in transformers:
        raise ValueError(f"Unknown transformer type: {transformer_type}")

    transformer_class = transformers[transformer_type]
    # All classes in transformers dict are concrete implementations, not abstract
    return transformer_class(config)  # type: ignore[abstract]
