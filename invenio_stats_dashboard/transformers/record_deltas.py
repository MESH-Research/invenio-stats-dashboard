# Copyright (C) 2025 Kcworks
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Record delta data series transformer classes."""

from flask import current_app

from .base import (
    DataSeries,
    DataSeriesArray,
    DataSeriesSet,
)
from typing import Any


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
            if files_data is None or not isinstance(files_data, dict):
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
            isinstance(metric_data, dict)
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
            if files_data is None or not isinstance(files_data, dict):
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
            isinstance(metric_data, dict)
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
        current_app.logger.error(
            f"FilePresenceRecordDeltaDataSeries.add() called with metric={self.metric}"
        )

        # Extract date
        period_start = doc.get("period_start")
        if period_start is None:
            current_app.logger.error("No period_start in document")
            return
        date = period_start.split("T")[0]
        if not date:
            current_app.logger.error("Empty date after splitting period_start")
            return

        # Get the records data (which has metadata_only/with_files breakdown)
        records_data = doc.get("records")
        if records_data is None or not isinstance(records_data, dict):
            current_app.logger.error(f"No records data in document: {records_data}")
            return

        # Get added/removed data
        added = records_data.get("added", {})
        removed = records_data.get("removed", {})

        current_app.logger.error(f"Records data - added: {added}, removed: {removed}")

        # Calculate net values for the specific presence type
        if self.metric == "metadata_only":
            # For metadata_only, we only care about records without files
            added_value = added.get("metadata_only", 0)
            removed_value = removed.get("metadata_only", 0)
        elif self.metric == "with_files":
            # For with_files, we only care about records with files
            added_value = added.get("with_files", 0)
            removed_value = removed.get("with_files", 0)
        else:
            current_app.logger.error(f"Unknown metric: {self.metric}")
            return

        net_value = added_value - removed_value
        current_app.logger.error(
            f"Adding data point: date={date}, net_value={net_value}"
        )
        self.add_data_point(date, net_value)


class RecordDeltaDataSeriesSet(DataSeriesSet):
    """Data series set for record delta documents."""

    @property
    def config_key(self) -> str:
        """Return the configuration key for record delta data."""
        return "records"

    @property
    def special_subcounts(self) -> list[str]:
        """Get special subcounts for record deltas."""
        from flask import current_app

        current_app.logger.error(
            "special_subcounts property called, returning ['file_presence']"
        )
        return ["file_presence"]

    def _get_special_subcount_metrics(self, subcount: str) -> list[str]:
        """Get the metrics for a special subcount."""
        if subcount == "file_presence":
            return ["metadata_only", "with_files"]  # Two presence types
        return []

    def _create_special_series_array(
        self, subcount: str, metric: str
    ) -> DataSeriesArray:
        """Create a data series array for a special subcount and metric."""
        from flask import current_app

        current_app.logger.error(
            f"Creating special series array for subcount={subcount}, metric={metric}"
        )

        if subcount == "file_presence":
            series_array = DataSeriesArray(
                "file_presence",
                FilePresenceRecordDeltaDataSeries,
                metric,
                is_global=True,  # Special subcounts should be treated as global
                chart_type="line",
                value_type="number",
            )
            current_app.logger.error(
                f"Created FilePresenceRecordDeltaDataSeries for metric={metric}"
            )
            return series_array
        raise NotImplementedError(f"Special subcount {subcount} not implemented")

    def _discover_metrics_from_documents(self) -> dict[str, list[str]]:
        """Discover available metrics by examining document structures.

        For record deltas, we need to split the 'files' metric into
        'file_count' and 'data_volume' to match dataTransformer.js output.
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

    def _create_series_array(self, subcount: str, metric: str) -> DataSeriesArray:
        """Create a data series array for the given subcount and metric."""
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
