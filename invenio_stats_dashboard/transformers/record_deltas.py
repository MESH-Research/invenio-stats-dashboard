# Copyright (C) 2025 Kcworks
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Record delta data series transformer classes."""

from collections.abc import Mapping
from typing import Any

from flask import current_app

from .base import (
    DataSeries,
    DataSeriesArray,
    DataSeriesSet,
)


class GlobalRecordDeltaDataSeries(DataSeries):
    """Data series for global record delta metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add global record delta data from document."""
        # Extract date
        period_start = doc.get("period_start")
        if period_start is None:
            return
        date = period_start.split("T")[0]
        if not date:
            return

        # Handle split files metrics - these come from the 'files' field
        if self.metric in ["data_volume", "file_count"]:
            files_data = doc.get("files")
            if files_data is None or not isinstance(files_data, Mapping):
                return

            added = files_data.get("added", {})
            removed = files_data.get("removed", {})

            # Get the specific sub-metric value
            added_value = added.get(self.metric, 0)
            removed_value = removed.get(self.metric, 0)
            net_value = added_value - removed_value

            # Value type is set on the DataSeriesArray constructor
            self.add_data_point(date, net_value)
            return

        # Get the metric data based on the metric name
        metric_data = doc.get(self.metric)
        if metric_data is None:
            return

        # Check if this metric has added/removed structure (delta metrics)
        if (
            isinstance(metric_data, Mapping)
            and "added" in metric_data
            and "removed" in metric_data
        ):
            # Calculate net from added/removed
            added = metric_data.get("added", {})
            removed = metric_data.get("removed", {})

            # Sum all numeric values in added and removed
            added_total = sum(v for v in added.values() if isinstance(v, (int, float)))
            removed_total = sum(
                v for v in removed.values() if isinstance(v, (int, float))
            )
            net_value = added_total - removed_total
            self.add_data_point(date, net_value)
        else:
            # Direct value (not a delta metric)
            self.add_data_point(date, metric_data)  # type: ignore[arg-type]


class SubcountRecordDeltaDataSeries(DataSeries):
    """Data series for subcount record delta metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add subcount record delta data from document."""
        # Extract date
        period_start = doc.get("period_start")
        if period_start is None:
            return
        date = period_start.split("T")[0]
        if not date:
            return

        # Handle split files metrics - these come from the 'files' field
        if self.metric in ["data_volume", "file_count"]:
            files_data = doc.get("files")
            if files_data is None or not isinstance(files_data, Mapping):
                return

            added = files_data.get("added", {})
            removed = files_data.get("removed", {})

            # Get the specific sub-metric value
            added_value = added.get(self.metric, 0)
            removed_value = removed.get(self.metric, 0)
            net_value = added_value - removed_value

            # Value type is set on the DataSeriesArray constructor
            self.add_data_point(date, net_value)
            return

        # Get the metric data based on the metric name
        metric_data = doc.get(self.metric)
        if metric_data is None:
            return

        # Check if this metric has added/removed structure (delta metrics)
        if (
            isinstance(metric_data, Mapping)
            and "added" in metric_data
            and "removed" in metric_data
        ):
            # Calculate net from added/removed
            added = metric_data.get("added", {})
            removed = metric_data.get("removed", {})

            # Sum all numeric values in added and removed
            added_total = sum(v for v in added.values() if isinstance(v, (int, float)))
            removed_total = sum(
                v for v in removed.values() if isinstance(v, (int, float))
            )
            net_value = added_total - removed_total
            self.add_data_point(date, net_value)
        else:
            # Direct value (not a delta metric)
            self.add_data_point(date, metric_data)  # type: ignore[arg-type]


class FilePresenceRecordDeltaDataSeries(DataSeries):
    """Data series for file presence record delta metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add file presence record delta data from document."""
        period_start = doc.get("period_start")
        if period_start is None:
            current_app.logger.error("No period_start in document")
            return
        date = period_start.split("T")[0]
        if not date:
            current_app.logger.error("Empty date after splitting period_start")
            return

        if self.metric in ["parents", "records"]:
            metric_data = doc.get(self.metric, {})
            if metric_data is None or not isinstance(metric_data, Mapping):
                current_app.logger.error(f"No records data in document: {metric_data}")
                return
            added_value = metric_data.get("added", {}).get(self.series_id, 0)
            removed_value = metric_data.get("removed", {}).get(self.series_id, 0)
        elif self.metric in ["file_count", "data_volume"]:
            file_data = doc.get("files", {})
            if self.series_id == "metadata_only":
                added_value = 0
                removed_value = 0
            elif self.series_id == "with_files":
                added_value = file_data.get("added", {}).get(self.metric, 0)
                removed_value = file_data.get("removed", {}).get(self.metric, 0)
        else:
            current_app.logger.error(f"Unknown metric: {self.metric}")
            return

        net_value = int(added_value) - int(removed_value)
        self.add_data_point(
            date, net_value, "number" if self.metric != "data_volume" else "filesize"
        )


class RecordDeltaDataSeriesSet(DataSeriesSet):
    """Data series set for record delta documents."""

    @property
    def config_key(self) -> str:
        """Return the configuration key for record delta data."""
        return "records"

    @property
    def special_subcounts(self) -> list[str]:
        """Get special subcounts for record deltas."""
        return ["file_presence"]

    def _get_special_subcount_metrics(self, subcount: str) -> list[str]:
        """Get the metrics for a special subcount.

        Returns:
            list[str]: List of metrics for the special subcount.
        """
        # Return empty list to fall back to regular metrics discovery
        return []

    def _create_special_series_array(
        self, subcount: str, metric: str
    ) -> DataSeriesArray:
        """Create a data series array for a special subcount and metric.

        Returns:
            DataSeriesArray: The created data series array.
        """
        if subcount == "file_presence":
            series_array = DataSeriesArray(
                "file_presence",
                FilePresenceRecordDeltaDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
                is_special=True,
            )

            series_array.series = [
                FilePresenceRecordDeltaDataSeries(
                    "metadata_only",
                    "Metadata Only",
                    metric,
                    "line",
                    "number",
                ),
                FilePresenceRecordDeltaDataSeries(
                    "with_files",
                    "With Files",
                    metric,
                    "line",
                    "number",
                ),
            ]
            series_array._initialized = True

            return series_array
        raise NotImplementedError(f"Special subcount {subcount} not implemented")

    # FIXME: Deprecated method
    def _discover_metrics_from_documents(self) -> dict[str, list[str]]:
        """Discover available metrics by examining document structures.

        For record deltas, we need to split the 'files' metric into
        'file_count' and 'data_volume' to match dataTransformer.js output.

        Returns:
            dict[str, list[str]]: Dictionary mapping category to list of metrics.
        """
        # Get the base metrics from parent class
        base_metrics = super()._discover_metrics_from_documents()

        # Split 'files' into 'file_count' and 'data_volume' for both global and subcount
        global_metrics = []
        for metric in base_metrics["global"]:
            if metric == "files":
                global_metrics.extend(["file_count", "data_volume"])
            else:
                global_metrics.append(metric)

        subcount_metrics = []
        for metric in base_metrics["subcount"]:
            if metric == "files":
                subcount_metrics.extend(["file_count", "data_volume"])
            else:
                subcount_metrics.append(metric)

        return {
            "global": global_metrics,
            "subcount": subcount_metrics,
        }

    def _get_default_metrics(self) -> dict[str, list[str]]:
        """Get default metrics for record delta data.

        Returns:
            dict[str, list[str]]: Dictionary mapping category to list of metrics.
        """
        # Standard record delta metrics that should always be available
        global_metrics = [
            "records",
            "file_count",
            "data_volume",
            "parents",
            "uploaders",
        ]
        subcount_metrics = ["records", "file_count", "data_volume", "parents"]
        return {
            "global": global_metrics,
            "subcount": subcount_metrics,
        }

    def _create_series_array(self, subcount: str, metric: str) -> DataSeriesArray:
        """Create a data series array for the given subcount and metric.

        Returns:
            DataSeriesArray: The created data series array.
        """
        # Set appropriate value type based on metric
        value_type = "filesize" if metric == "data_volume" else "number"

        if subcount == "global":
            return DataSeriesArray(
                "global",
                GlobalRecordDeltaDataSeries,
                metric,
                is_global=True,
                chart_type="line",
                value_type=value_type,
            )
        else:
            return DataSeriesArray(
                subcount,
                SubcountRecordDeltaDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type=value_type,
            )
