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

from ..config.component_metrics import get_required_metrics_for_category
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
        """Convert to dictionary format matching JavaScript output.

        Returns:
            DataPointDict: Dictionary representation of the data point.
        """
        return {
            "value": [self.date, self.value],
            "readableDate": self._format_readable_date(),
            "valueType": self.value_type,
        }

    def _format_readable_date(self) -> str:
        """Format date as localized human-readable string matching JavaScript output.

        Returns:
            str: Formatted date string.
        """
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
        series_name: str | dict,
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
        """Convert to dictionary format matching JavaScript output.

        Returns:
            DataSeriesDict: Dictionary representation of the data series.
        """
        # Handle multilingual labels - preserve as object for JavaScript processing
        name = self.series_name
        if isinstance(name, dict):
            # Convert AttrDict to plain dict if needed for JSON serialization
            # Keep as object for proper multilingual handling on frontend
            name = dict(name)
        else:
            # Ensure it's a string
            name = str(name)

        return {
            "id": self.series_id,
            "name": name,
            "data": [dp.to_dict() for dp in self.data],
            "type": self.chart_type,
            "valueType": self.value_type,
        }

    def for_json(self) -> DataSeriesDict:
        """Convert to dictionary format for JSON serialization.

        Returns:
            DataSeriesDict: Dictionary representation for JSON serialization.
        """
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
        is_special: bool = False,
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
            is_special: Whether this is a special subcount (pre-populated series)
        """
        self.series_type = series_type
        self.data_series_class = data_series_class
        self.metric = metric
        self.is_global = is_global
        self.chart_type = chart_type
        self.value_type = value_type
        self.is_special = is_special
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
            # Check if this is a special subcount (pre-populated series)
            if self.is_special:
                # For special subcounts, add data directly to existing series
                if isinstance(self.series, list):
                    for data_series in self.series:
                        data_series.add(doc)
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
            if not isinstance(item_label, str | dict):
                item_label = str(item_label)

            # Create series for this item if it doesn't exist
            if isinstance(self.series, list) and not any(
                s.series_id == item_id for s in self.series
            ):
                # Preserve the original label object for proper multilingual handling
                # The JavaScript side will handle localization
                series_name = item_label
                self.series.append(
                    self.data_series_class(
                        item_id,
                        series_name,
                        self.metric,
                        self.chart_type,
                        self.value_type,
                    )
                )

    def _get_item_data_for_series(
        self, doc: dict[str, Any], data_series: DataSeries
    ) -> dict[str, Any] | None:
        """Get the specific item data for a DataSeries from the document.

        Returns:
            dict[str, Any] | None: Item data dictionary, or None if not found.
        """
        if self.is_global:
            # Return global document without subcounts
            global_doc = dict(doc)
            global_doc.pop("subcounts", None)
            return global_doc

        # Get the item_id directly from series_id and subcount_type from series_type
        item_id = data_series.series_id
        subcount_type = self.series_type

        subcounts = doc.get("subcounts")
        if subcounts is None:
            return None

        # Handle different subcount types
        if subcount_type.endswith("_by_view"):
            # For by_view series, look at subcounts[base_type]["by_view"]
            base_type = subcount_type.replace("_by_view", "")
            subcount_data = subcounts.get(base_type)
            if not isinstance(subcount_data, dict):
                return None
            subcount_series = subcount_data.get("by_view", [])
        elif subcount_type.endswith("_by_download"):
            # For by_download series, look at subcounts[base_type]["by_download"]
            base_type = subcount_type.replace("_by_download", "")
            subcount_data = subcounts.get(base_type)
            if not isinstance(subcount_data, dict):
                return None
            subcount_series = subcount_data.get("by_download", [])
        else:
            # For regular series, look at subcounts[series_type] (direct array)
            subcount_series = subcounts.get(subcount_type)

        if not isinstance(subcount_series, list):
            return None

        # Find the specific item
        for item in subcount_series:
            if item.get("id") == item_id:
                # Return the full item data with the document date
                item_data = dict(item)
                item_data["snapshot_date"] = doc.get("snapshot_date")
                item_data["period_start"] = doc.get("period_start")
                return item_data

        return None

    def to_dict(self) -> list[DataSeriesDict]:
        """Convert to dictionary format.

        Returns:
            list[DataSeriesDict]: List of data series dictionaries.
        """
        if isinstance(self.series, list):
            return [s.to_dict() for s in self.series]
        elif self.series is not None:
            return [self.series.to_dict()]  # Wrap single DataSeries in array
        else:
            return []

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            str: JSON string representation.
        """
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
        optimize: bool = False,
        category: str | None = None,
        component_names: set[str] | None = None,
    ):
        """Initialize the data series set.

        Args:
            documents: List of aggregation documents
            series_keys: Optional list of subcount names. If None, automatically creates
                series for all available subcounts and metrics.
                Example: ["global", "countries", "institutions"]
            optimize: If True, only include metrics used by UI components.
            category: Category name for registry lookup (e.g., "record_deltas").
                      Required if optimize=True.
            component_names: Optional set of component names to filter metrics by.
                            If provided, only metrics used by these components will
                            be included. If None and optimize=True, includes metrics
                            for all components in the registry.
        """
        self.documents = documents or []
        self.subcount_configs = current_app.config.get("COMMUNITY_STATS_SUBCOUNTS", {})
        self.series_keys = series_keys or self._get_default_series_keys()
        self.series_arrays: dict[str, DataSeriesArray] = {}
        self._built_result: dict[str, dict[str, list[DataSeriesDict]]] | None = None
        self._initialized = False

        # Optimization support
        self.optimize = optimize
        self.category = category
        self._required_metrics: dict[str, set[str]] | None = None

        if optimize:
            if not category:
                current_app.logger.warning(
                    "optimize=True but category not provided. "
                    "Falling back to all metrics."
                )
                self.optimize = False
            else:
                self._required_metrics = get_required_metrics_for_category(
                    category,
                    optimize=True,
                    subcounts=list(series_keys) if series_keys is not None else None,
                    component_names=component_names,
                )
                if self._required_metrics is None:
                    current_app.logger.warning(
                        f"Failed to get required metrics for category {category}. "
                        "Falling back to all metrics."
                    )
                    self.optimize = False

    def _get_default_series_keys(self) -> list[str]:
        """Get the default series keys for this document category.

        Returns:
            list[str]: List of default series keys.
        """
        series_keys = ["global"]
        for subcount_name, config in self.subcount_configs.items():
            # Only add subcount if it has actual configuration (not just empty dict)
            config_value = config.get(self.config_key)
            if (
                config_value
                and isinstance(config_value, dict)
                and len(config_value) > 0
            ):
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

    def _should_include_metric(self, subcount: str, metric: str) -> bool:
        """Determine if a metric should be included based on optimization settings.

        Args:
            subcount: Subcount name (e.g., "publishers", "global")
            metric: Metric name (e.g., "records", "views")

        Returns:
            True if metric should be included, False otherwise.
        """
        if not (self.optimize and self._required_metrics) \
                or subcount not in self._required_metrics:
            return True

        required = self._required_metrics.get(subcount, set())
        return metric in required

    def _initialize_series_arrays(self) -> None:
        """Initialize all series arrays and populate them with existing documents.

        This creates all DataSeriesArray objects and processes all documents
        currently in self.documents. Should only be called once.

        When optimization is enabled, only creates series for metrics that are
        required by UI components according to the registry and the current
        configured dashboard layout.
        """
        default_metrics = self._get_default_metrics()

        for subcount in self.series_keys:
            if subcount in self.special_subcounts:
                special_metrics = self._get_special_subcount_metrics(subcount)
                metrics_to_use = special_metrics or default_metrics["subcount"]

                for metric in metrics_to_use:
                    if not self._should_include_metric(subcount, metric):
                        continue  # Skip this metric

                    series_key = f"{subcount}_{metric}"
                    self.series_arrays[series_key] = (
                        self._create_special_series_array(subcount, metric)
                    )
            else:
                if subcount == "global":
                    available_metrics = default_metrics["global"]
                else:
                    available_metrics = default_metrics["subcount"]

                for metric in available_metrics:
                    if not self._should_include_metric(subcount, metric):
                        continue  # Skip this metric

                    series_key = f"{subcount}_{metric}"
                    self.series_arrays[series_key] = self._create_series_array(
                        subcount, metric
                    )

        # Add data to all created DataSeriesArray objects
        for doc in self.documents:
            for series_array in self.series_arrays.values():
                series_array.add(doc)

        # Clear documents from memory after processing
        # (GC will be triggered by the query pagination loop after processing)
        self.documents = []

        self._initialized = True

    def _build_result_dict(self) -> dict[str, dict[str, list[DataSeriesDict]]]:
        """Build the result dictionary from current series arrays.

        Returns:
            Dictionary with nested structure: {subcount: {metric: [DataSeries]}}

        Note: Only includes series arrays that were actually created (which may
            be filtered by optimization).
        """
        result: dict[str, dict[str, list[DataSeriesDict]]] = {}
        for subcount in self.series_keys:
            if subcount not in result:
                result[subcount] = {}

            prefix = f"{subcount}_"
            for series_key, series_array in self.series_arrays.items():
                if series_key.startswith(prefix):
                    # Extract metric name (everything after "{subcount}_")
                    metric = series_key[len(prefix):]
                    result[subcount][metric] = series_array.to_dict()

        return result

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

        # Initialize series arrays if not already initialized
        if not self._initialized:
            self._initialize_series_arrays()

        # Build and cache the result
        result = self._build_result_dict()
        self._built_result = result
        return result

    def for_json(self) -> dict[str, dict[str, list[DataSeriesDict]]]:
        """Convert to dictionary format for JSON serialization with camelCase keys.

        Returns:
            dict[str, dict[str, list[DataSeriesDict]]]: Dictionary with camelCase keys.
        """
        result = self.build()
        return self._convert_to_camelcase(result)

    def add(self, documents: list[AggregationDocumentDict]) -> None:
        """Add additional documents to a data series set.

        This method allows incrementally adding documents to the series set.
        If the series set hasn't been initialized yet (via build() or a previous
        add() call), it will initialize the series arrays before processing the
        new documents.
        It will then update all existing series arrays with data from the new documents.

        Args:
            documents: List of additional aggregation documents to add
        """
        if not self._initialized:
            self._initialize_series_arrays()

        for doc in documents:
            for series_array in self.series_arrays.values():
                series_array.add(doc)

        # Invalidate cached result so it will be rebuilt lazily the next time
        # build()/for_json() is called. This avoids constructing a full
        # dictionary representation after each page of query results, which
        # previously doubled memory usage during large backfills.
        self._built_result = None

    def _convert_to_camelcase(
        self, data: dict[str, dict[str, list[DataSeriesDict]]]
    ) -> dict[str, dict[str, list[DataSeriesDict]]]:
        """Convert snake_case keys to camelCase for JSON serialization.

        Returns:
            dict[str, dict[str, list[DataSeriesDict]]]: Dictionary with camelCase keys.
        """
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
        """Convert snake_case string to camelCase.

        Returns:
            str: camelCase string.
        """
        components = snake_str.split("_")
        return components[0] + "".join(x.capitalize() for x in components[1:])

    # FIXME: Deprecated method
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
                if key != "subcounts" and isinstance(value, dict | int | float):
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
                                        value, dict | int | float
                                    ):
                                        subcount_metrics.add(key)
                        elif isinstance(subcount_data, dict):
                            # Handle "all" type subcounts (direct metric access)
                            for key, value in subcount_data.items():
                                if key not in ["id", "label"] and isinstance(
                                    value, dict | int | float
                                ):
                                    subcount_metrics.add(key)

        return {
            "global": sorted(list(global_metrics)),
            "subcount": sorted(list(subcount_metrics)),
        }

    @abstractmethod
    def _get_default_metrics(self) -> dict[str, list[str]]:
        """Get default metrics for data series.

        Returns:
            Dictionary with "global" and "subcount" keys containing standard metrics
        """
        raise NotImplementedError(
            "Subclasses must implement _get_default_metrics_for_empty_data"
        )

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
        """Convert all series to JSON string.

        Returns:
            str: JSON string representation.
        """
        return json.dumps(self.for_json(), indent=2)
