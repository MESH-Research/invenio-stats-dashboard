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
from babel.dates import format_date
from flask import current_app

from .types import (
    AggregationDocumentDict,
    DataPointDict,
    DataSeriesDict,
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
        """Format date as localized human-readable string matching JavaScript output."""
        try:
            date_obj = datetime.strptime(self.date, "%Y-%m-%d")

            locale = current_app.config.get("BABEL_DEFAULT_LOCALE", "en")

            return str(format_date(date_obj, format="medium", locale=locale))
        except (ImportError, ValueError, Exception):
            return str(self.date)


class DataSeries(ABC):
    """Represents a complete data series for charting."""

    def __init__(
        self,
        series_id: str,
        series_name: str,
        metric: str,
        chart_type: str = "line",
        value_type: str = "number",
        **kwargs,
    ):
        """Initialize a data series.

        Args:
            series_id: Unique identifier for this series
            series_name: Display name for this series
            metric: Specific metric to extract (e.g., "views", "downloads", "records")
            chart_type: Type of chart ('line', 'bar', etc.)
            value_type: Type of values ('number', 'filesize', etc.)
            **kwargs: Additional parameters for subclasses
        """
        self.series_id = series_id
        self.series_name = series_name
        self.metric = metric
        self.chart_type = chart_type
        self.value_type = value_type
        self.data: list[DataPoint] = []

        # Additional attributes expected by serializers
        self.id = series_id
        self.name = series_name
        self.category = "unknown"  # Default category
        self.type = chart_type

    @abstractmethod
    def add(self, doc: dict[str, Any]) -> None:
        """Add data from a document to this series.

        Must be implemented by subclasses.
        """
        pass

    def add_data_point(
        self, date: str, value: int | float, value_type: str | None = None
    ) -> None:
        """Add a data point to this series.

        Args:
            date: Date string (YYYY-MM-DD)
            value: Numeric value for this data point
            value_type: Type of value (uses series default if None)
        """
        if value_type is None:
            value_type = self.value_type
        self.data.append(DataPoint(date, value, value_type))

    def to_dict(self) -> DataSeriesDict:
        """Convert to dictionary format matching JavaScript output."""
        return {
            "id": self.series_id,
            "name": self.series_name,
            "data": [dp.to_dict() for dp in self.data],
            "type": self.chart_type,
            "valueType": self.value_type,
        }

    def for_json(self) -> DataSeriesDict:
        """Convert to dictionary format for JSON serialization."""
        return self.to_dict()


class DataSeriesArray:
    """Manages either a single DataSeries (global) or an array of DataSeries."""

    def __init__(
        self,
        series_type: str,
        data_series_class: type[DataSeries],
        metric: str,
        is_global: bool = False,
        chart_type: str = "line",
        value_type: str = "number",
    ):
        """Initialize the data series array.

        Args:
            series_type: Type of series ('global' or subcount type
                like 'resource_types')
            data_series_class: Class to use for creating DataSeries objects
            metric: Specific metric to extract (e.g., "views", "downloads", "records")
            is_global: Whether this is a global series (single) or subcount
                series (array)
            chart_type: Chart type for subcount series ('line', 'bar', etc.)
            value_type: Value type for subcount series ('number', 'filesize', etc.)
        """
        self.series_type = series_type
        self.data_series_class = data_series_class
        self.metric = metric
        self.is_global = is_global
        self.chart_type = chart_type
        self.value_type = value_type
        self.series: DataSeries | list[DataSeries] | None = None
        self._initialized = False

    def add(self, doc: dict[str, Any]) -> None:
        """Add data from a document to the series array."""
        if not self._initialized:
            if self.is_global:
                # Create the single global DataSeries
                self.series = self.data_series_class(
                    "global", "Global", self.metric, "bar", "number"
                )
            else:
                # Initialize as empty list for subcount series
                self.series = []
            self._initialized = True

        if self.is_global:
            # For global series, add data directly to the single series
            if self.series is not None and not isinstance(self.series, list):
                self.series.add(doc)
        else:
            # Create individual DataSeries as we encounter items
            self._create_series_from_doc(doc)

            # Add data to all existing series
            if isinstance(self.series, list):
                for data_series in self.series:
                    # Get the item data for this specific series
                    item_data = self._get_item_data_for_series(doc, data_series)
                    if item_data:
                        data_series.add(item_data)

    def _create_series_from_doc(self, doc: dict[str, Any]) -> None:
        """Create individual DataSeries from document for subcount series."""
        if self.is_global:
            return

        subcounts = doc.get("subcounts")
        if subcounts is None:
            return

        # Process the specific subcount type
        if self.series_type.endswith("_by_view"):
            # For by_view series, look at subcounts[base_type]["by_view"]
            base_type = self.series_type.replace("_by_view", "")
            subcount_data = subcounts.get(base_type)
            if not isinstance(subcount_data, dict):
                return
            subcount_series = subcount_data.get("by_view", [])
        elif self.series_type.endswith("_by_download"):
            # For by_download series, look at subcounts[base_type]["by_download"]
            base_type = self.series_type.replace("_by_download", "")
            subcount_data = subcounts.get(base_type)
            if not isinstance(subcount_data, dict):
                return
            subcount_series = subcount_data.get("by_download", [])
        else:
            # For regular series, look at subcounts[series_type] (direct array)
            subcount_series = subcounts.get(self.series_type)

        if not isinstance(subcount_series, list):
            return

        for item in subcount_series:
            item_id = item.get("id", "")
            item_label = item.get("label", item_id)

            # Preserve the full label object (string or multilingual dict)
            if not isinstance(item_label, (str, dict)):
                item_label = str(item_label)

            # Create series for this item if it doesn't exist
            series_id = f"{self.series_type}_{item_id}"
            if isinstance(self.series, list) and not any(
                s.series_id == series_id for s in self.series
            ):
                # Convert label to string for series_name parameter
                series_name = (
                    str(item_label) if isinstance(item_label, dict) else item_label
                )
                self.series.append(
                    self.data_series_class(
                        series_id,
                        series_name,
                        self.metric,
                        self.chart_type,
                        self.value_type,
                    )
                )

    def _get_item_data_for_series(
        self, doc: dict[str, Any], data_series: DataSeries
    ) -> dict[str, Any] | None:
        """Get the specific item data for a DataSeries from the document."""
        if self.is_global:
            # Return global document without subcounts
            global_doc = dict(doc)
            global_doc.pop("subcounts", None)
            return global_doc

        # Parse the series_id to get subcount_type and item_id
        parts = data_series.series_id.split("_", 2)
        if len(parts) < 2:
            return None

        subcounts = doc.get("subcounts")
        if subcounts is None:
            return None

        if len(parts) == 2:
            # Regular subcount: "subcount_type_item_id"
            subcount_type = parts[0]
            item_id = parts[1]
            subcount_series = subcounts.get(subcount_type)
        else:
            # By view/download: "subcount_type_by_view_item_id"
            # or "subcount_type_by_download_item_id"
            subcount_type = parts[0]
            item_id = parts[2]
            subcount_data = subcounts.get(subcount_type)
            if not isinstance(subcount_data, dict):
                return None
            if parts[1] == "by_view":
                subcount_series = subcount_data.get("by_view", [])
            elif parts[1] == "by_download":
                subcount_series = subcount_data.get("by_download", [])
            else:
                return None

        if not isinstance(subcount_series, list):
            return None

        # Find the specific item
        for item in subcount_series:
            if item.get("id") == item_id:
                # Return only the specific metric data with the document date
                item_data = {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "period_start": doc.get("period_start"),
                    "snapshot_date": doc.get("snapshot_date"),
                    self.metric: item.get(self.metric),
                }
                return item_data

        return None

    def to_dict(self) -> list[DataSeriesDict]:
        """Convert to dictionary format."""
        if isinstance(self.series, list):
            return [s.to_dict() for s in self.series]
        elif self.series is not None:
            return [self.series.to_dict()]  # Wrap single DataSeries in array
        else:
            return []

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class DataSeriesSet(ABC):
    """Base class for creating sets of data series from aggregation documents."""

    @property
    @abstractmethod
    def config_key(self) -> str:
        """Return the configuration key for this data series set.

        Should return either "records" or "usage_events".
        Must be implemented by subclasses.
        """
        pass

    def __init__(
        self,
        documents: list[AggregationDocumentDict],
        series_keys: list[str] | None = None,
    ):
        """Initialize the data series set.

        Args:
            documents: List of aggregation documents
            series_keys: Optional list of subcount names. If None, automatically creates
                series for all available subcounts and metrics.
                Example: ["global", "countries", "institutions"]
        """
        self.documents = documents
        self.series_keys = series_keys or self._get_default_series_keys()
        self.series_arrays: dict[str, DataSeriesArray] = {}
        self._built_result: dict[str, dict[str, list[DataSeriesDict]]] | None = None

    def _get_default_series_keys(self) -> list[str]:
        """Get the default series keys for this document category."""
        from flask import current_app

        # Get subcount configurations from Flask config
        subcount_configs = current_app.config.get("COMMUNITY_STATS_SUBCOUNTS", {})

        # Create series keys - one per subcount, metrics will be generated automatically
        series_keys = []

        # Add global subcount
        series_keys.append("global")

        # Add subcount configurations
        for subcount_name, config in subcount_configs.items():
            # Check if this subcount has the appropriate configuration
            if self.config_key in config:
                subcount_config = config[self.config_key]

                # Process subcount if it has the required config
                if subcount_config:
                    # Add the main subcount
                    series_keys.append(subcount_name)

                    # For usage snapshots, add by_view and by_download
                    # series for "top" type
                    if (
                        self.config_key == "usage_events"
                        and subcount_config.get("snapshot_type") == "top"
                    ):
                        series_keys.append(f"{subcount_name}_by_view")
                        series_keys.append(f"{subcount_name}_by_download")
                else:
                    # Fall back to just the subcount key
                    series_keys.append(subcount_name)

        # Add special subcounts defined by subclasses
        series_keys.extend(self.special_subcounts)

        return series_keys

    @property
    def special_subcounts(self) -> list[str]:
        """Get special subcounts defined by subclasses.

        Override this property to add subcounts that extract data from global metrics
        or other special sources.

        Returns:
            List of special subcount names
        """
        return []

    def build(self) -> dict[str, dict[str, list[DataSeriesDict]]]:
        """Build all data series from the documents.

        Automatically discovers available metrics from document structures and creates
        series for all discovered metrics in each subcount category.

        Returns:
            Dictionary with nested structure: {subcount: {metric: [DataSeries]}}
        """
        # Return cached result if available
        if self._built_result is not None:
            return self._built_result

        # Discover available metrics from document structures
        discovered_metrics = self._discover_metrics_from_documents()

        # Create ALL DataSeriesArray objects upfront
        for subcount in self.series_keys:
            # Check if this is a special subcount
            if subcount in self.special_subcounts:
                # Handle special subcounts
                special_metrics = self._get_special_subcount_metrics(subcount)
                for metric in special_metrics:
                    series_key = f"{subcount}_{metric}"
                    self.series_arrays[series_key] = self._create_special_series_array(
                        subcount, metric
                    )
            else:
                # Get metrics for this subcount
                if subcount == "global":
                    metrics = discovered_metrics["global"]
                else:
                    metrics = discovered_metrics["subcount"]

                # Create series array for each metric
                for metric in metrics:
                    series_key = f"{subcount}_{metric}"
                    self.series_arrays[series_key] = self._create_series_array(
                        subcount, metric
                    )

        # Process each document
        for doc in self.documents:
            # Add data to ALL DataSeriesArray objects
            for series_array in self.series_arrays.values():
                series_array.add(dict(doc))

        # Convert to nested format matching dataTransformer structure
        result: dict[str, dict[str, list[DataSeriesDict]]] = {}
        for subcount in self.series_keys:
            # Initialize subcount if not exists
            if subcount not in result:
                result[subcount] = {}

            # Check if this is a special subcount
            if subcount in self.special_subcounts:
                # Handle special subcounts
                special_metrics = self._get_special_subcount_metrics(subcount)
                for metric in special_metrics:
                    series_key = f"{subcount}_{metric}"
                    series_array = self.series_arrays[series_key]

                    # Add metric data - use DataSeriesArray.to_dict()
                    result[subcount][metric] = series_array.to_dict()
            else:
                # Get metrics for this subcount
                if subcount == "global":
                    metrics = discovered_metrics["global"]
                else:
                    metrics = discovered_metrics["subcount"]

                # Add all metrics for this subcount
                for metric in metrics:
                    series_key = f"{subcount}_{metric}"
                    series_array = self.series_arrays[series_key]

                    # Add metric data - use DataSeriesArray.to_dict()
                    result[subcount][metric] = series_array.to_dict()

        # Cache the result
        self._built_result = result
        return result

    def for_json(self) -> dict[str, dict[str, list[DataSeriesDict]]]:
        """Convert to dictionary format for JSON serialization with camelCase keys."""
        result = self.build()
        return self._convert_to_camelcase(result)

    def _convert_to_camelcase(
        self, data: dict[str, dict[str, list[DataSeriesDict]]]
    ) -> dict[str, dict[str, list[DataSeriesDict]]]:
        """Convert snake_case keys to camelCase for JSON serialization."""
        result: dict[str, dict[str, list[DataSeriesDict]]] = {}
        for subcount_key, subcount_data in data.items():
            # Convert subcount key (e.g., "access_statuses" -> "accessStatuses")
            camel_subcount_key = self._to_camelcase(subcount_key)
            result[camel_subcount_key] = {}

            for metric_key, metric_data in subcount_data.items():
                # Convert metric key (e.g., "data_volume" -> "dataVolume")
                camel_metric_key = self._to_camelcase(metric_key)
                # metric_data is already a list[DataSeriesDict] with correct
                # camelCase keys
                result[camel_subcount_key][camel_metric_key] = metric_data

        return result

    def _to_camelcase(self, snake_str: str) -> str:
        """Convert snake_case string to camelCase."""
        components = snake_str.split("_")
        return components[0] + "".join(x.capitalize() for x in components[1:])

    def _discover_metrics_from_documents(self) -> dict[str, list[str]]:
        """Discover available metrics by examining document structures.

        Returns:
            Dictionary with "global" and "subcount" keys, each containing a list of
            metric names.
        """
        global_metrics = set()
        subcount_metrics = set()

        for doc in self.documents:
            # Discover global metrics - take all top-level keys except "subcounts"
            for key, value in doc.items():
                if key != "subcounts" and isinstance(value, (dict, int, float)):
                    global_metrics.add(key)

            # Discover subcount metrics - look at keys in the first available
            # subcount item
            if "subcounts" in doc:
                subcounts_data = doc["subcounts"]
                if isinstance(subcounts_data, dict):
                    for _subcount_name, subcount_data in subcounts_data.items():
                        if isinstance(subcount_data, list) and subcount_data:
                            # Look at the first item to discover available metrics
                            first_item = subcount_data[0]
                            if isinstance(first_item, dict):
                                for key, value in first_item.items():
                                    if key not in ["id", "label"] and isinstance(
                                        value, (dict, int, float)
                                    ):
                                        subcount_metrics.add(key)
                        elif isinstance(subcount_data, dict):
                            # Handle "all" type subcounts (direct metric access)
                            for key, value in subcount_data.items():
                                if key not in ["id", "label"] and isinstance(
                                    value, (dict, int, float)
                                ):
                                    subcount_metrics.add(key)

        return {
            "global": sorted(list(global_metrics)),
            "subcount": sorted(list(subcount_metrics)),
        }

    @abstractmethod
    def _create_series_array(self, subcount: str, metric: str) -> DataSeriesArray:
        """Create a data series array for the given subcount and metric.

        Must be implemented by subclasses.
        """
        pass

    def _get_special_subcount_metrics(self, subcount: str) -> list[str]:
        """Get the metrics for a special subcount.

        Override this method to define metrics for special subcounts.

        Args:
            subcount: The special subcount name

        Returns:
            List of metric names for this special subcount
        """
        return []

    def _create_special_series_array(
        self, subcount: str, metric: str
    ) -> DataSeriesArray:
        """Create a data series array for a special subcount and metric.

        Override this method to handle special subcounts.

        Args:
            subcount: The special subcount name
            metric: The metric name

        Returns:
            DataSeriesArray for the special subcount and metric
        """
        raise NotImplementedError("Special subcounts not implemented")

    def to_json(self) -> str:
        """Convert all series to JSON string."""
        return json.dumps(self.for_json(), indent=2)
