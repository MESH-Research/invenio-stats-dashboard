# Copyright (C) 2025 Kcworks
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Record delta data series transformer classes."""

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

            # Use filesize value type for data_volume metric
            value_type = "filesize" if self.metric == "data_volume" else "number"
            self.add_data_point(date, int(net_value), value_type)
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

            # Use filesize value type for data_volume metric
            value_type = "filesize" if self.metric == "data_volume" else "number"
            self.add_data_point(date, int(net_value), value_type)
        else:
            # Direct value (not a delta metric)
            self.add_data_point(date, metric_data)  # type: ignore[arg-type]


class RecordDeltaDataSeriesSet(DataSeriesSet):
    """Data series set for record delta documents."""

    @property
    def config_key(self) -> str:
        """Return the configuration key for record delta data."""
        return "records"

    def _create_series_array(self, subcount: str, metric: str) -> DataSeriesArray:
        """Create a data series array for the given subcount and metric."""
        if subcount == "global":
            return DataSeriesArray(
                "global",
                GlobalRecordDeltaDataSeries,
                metric,
                is_global=True,
                chart_type="line",
                value_type="number",
            )
        else:
            return DataSeriesArray(
                subcount,
                SubcountRecordDeltaDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
            )
