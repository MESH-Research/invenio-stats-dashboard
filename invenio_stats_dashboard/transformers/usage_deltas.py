# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Usage delta data series transformer classes."""

from typing import Any

from .base import (
    DataSeries,
    DataSeriesArray,
    DataSeriesSet,
)


class GlobalUsageDeltaDataSeries(DataSeries):
    """Data series for global usage delta metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add global usage delta data from document."""
        # Extract date
        period_start = doc.get("period_start")
        if period_start is None:
            return
        date = period_start.split("T")[0]
        if not date:
            return

        # Get totals data
        totals = doc.get("totals")
        if totals is None:
            return

        # Handle metrics using common logic
        self._add_metric_data(date, totals.get("view", {}), totals.get("download", {}))

    def _add_metric_data(self, date: str, view_data: dict, download_data: dict) -> None:
        """Add metric data using common logic for both global and subcount series."""
        # Core metric mappings
        core_metrics = {
            "views": ("view", "total_events", "number"),
            "downloads": ("download", "total_events", "number"),
            "view_visitors": ("view", "unique_visitors", "number"),
            "download_visitors": ("download", "unique_visitors", "number"),
            "data_volume": ("download", "total_volume", "filesize"),
        }

        if self.metric in core_metrics:
            source, key, value_type = core_metrics[self.metric]
            data = view_data if source == "view" else download_data
            value = data.get(key, 0)
            self.add_data_point(date, value, value_type)
        else:
            # Handle prefixed metrics (view_* and download_*)
            for prefix, data in [("view_", view_data), ("download_", download_data)]:
                if self.metric.startswith(prefix):
                    key = self.metric[len(prefix) :]  # noqa: E203
                    value = data.get(key, 0)
                    value_type = "filesize" if "volume" in key else "number"
                    self.add_data_point(date, value, value_type)
                    break


class SubcountUsageDeltaDataSeries(GlobalUsageDeltaDataSeries):
    """Data series for subcount usage delta metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add subcount usage delta data from document."""
        # Extract date
        period_start = doc.get("period_start")
        if period_start is None:
            return
        date = period_start.split("T")[0]
        if not date:
            return

        # Handle metrics using common logic (inherited from parent)
        view_data = doc.get("view", {})
        download_data = doc.get("download", {})
        if isinstance(view_data, dict) and isinstance(download_data, dict):
            self._add_metric_data(date, view_data, download_data)


class UsageDeltaDataSeriesSet(DataSeriesSet):
    """Data series set for usage delta documents."""

    @property
    def config_key(self) -> str:
        """Return the configuration key for usage delta data."""
        return "usage_events"

    def _discover_metrics_from_documents(self) -> dict[str, list[str]]:
        """Discover metrics from usage delta documents.

        Maps the actual document structure to desired output metrics:
        - view.total_events → views
        - download.total_events → downloads
        - view.unique_visitors + download.unique_visitors → visitors (max)
        - download.total_volume → data_volume
        - Plus additional metrics from view/download structures
        
        Returns:
            dict[str, list[str]]: Dictionary mapping category to list of metrics.
        """
        if not self.documents:
            return {"global": [], "subcount": []}

        # Get the first document to discover available metrics
        doc = self.documents[0]
        totals = doc.get("totals", {})
        view_data = totals.get("view", {}) if totals else {}
        download_data = totals.get("download", {}) if totals else {}

        metrics = []

        # Core metrics that map to specific output names
        if "total_events" in view_data:
            metrics.append("views")
        if "total_events" in download_data:
            metrics.append("downloads")
        if "unique_visitors" in view_data:
            metrics.append("view_visitors")
        if "unique_visitors" in download_data:
            metrics.append("download_visitors")
        if "total_volume" in download_data:
            metrics.append("data_volume")

        # Additional metrics from view data
        for key in view_data.keys():
            if key not in ["total_events", "unique_visitors"]:  # Already handled above
                metrics.append(f"view_{key}")

        # Additional metrics from download data
        for key in download_data.keys():
            if key not in ["total_events", "unique_visitors", "total_volume"]:
                # Already handled above
                metrics.append(f"download_{key}")

        return {"global": metrics, "subcount": metrics}

    def _get_default_metrics_for_empty_data(self) -> dict[str, list[str]]:
        """Get default metrics for usage delta data when no documents exist.
        
        Returns:
            dict[str, list[str]]: Dictionary mapping category to list of metrics.
        """
        # Standard usage delta metrics that should always be available
        metrics = [
            "data_volume", "download_unique_files", "download_unique_parents",
            "download_unique_records", "download_visitors", "downloads",
            "view_unique_parents", "view_unique_records", "view_visitors", "views"
        ]
        return {
            "global": metrics,
            "subcount": metrics,
        }

    def _create_series_array(self, series_key: str, metric: str) -> DataSeriesArray:
        """Create a data series array for the given series key and metric.
        
        Returns:
            DataSeriesArray: The created data series array.
        """
        if series_key == "global":
            return DataSeriesArray(
                "global",
                GlobalUsageDeltaDataSeries,
                metric,
                is_global=True,
                chart_type="line",
                value_type="number",
            )
        else:
            return DataSeriesArray(
                series_key,
                SubcountUsageDeltaDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
            )
