# Copyright (C) 2025 Kcworks
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Data series transformer classes for usage snapshot data."""

from typing import Any

from .base import (
    DataSeries,
    DataSeriesArray,
    DataSeriesSet,
)


class GlobalUsageSnapshotDataSeries(DataSeries):
    """Data series for global usage snapshot metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add global usage snapshot data from document."""
        # Extract date
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
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


class SubcountUsageSnapshotDataSeries(GlobalUsageSnapshotDataSeries):
    """Data series for subcount usage snapshot metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add subcount usage snapshot data from document."""
        # Extract date
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
        if not date:
            return

        # Check if this is a top subcount with by_view/by_download structure
        if isinstance(doc, dict) and "by_view" in doc and "by_download" in doc:
            # Top subcount: extract from by_view and by_download arrays
            by_view_data = doc.get("by_view", {})
            by_download_data = doc.get("by_download", {})
            if isinstance(by_view_data, dict) and isinstance(by_download_data, dict):
                self._add_metric_data(date, by_view_data, by_download_data)
        else:
            # Regular subcount: extract from view and download objects
            view_data = doc.get("view", {})
            download_data = doc.get("download", {})
            if isinstance(view_data, dict) and isinstance(download_data, dict):
                self._add_metric_data(date, view_data, download_data)


class UsageSnapshotDataSeriesSet(DataSeriesSet):
    """Data series set for usage snapshot documents."""

    @property
    def config_key(self) -> str:
        """Return the configuration key for usage snapshot data."""
        return "usage_events"

    def _get_default_series_keys(self) -> list[str]:
        """Get the default series keys for usage snapshot data.

        Returns:
            list[str]: List of default series keys.
        """
        from flask import current_app

        subcount_configs = current_app.config.get("COMMUNITY_STATS_SUBCOUNTS", {})

        series_keys = []
        series_keys.append("global")

        for subcount_name, config in subcount_configs.items():
            if self.config_key in config:
                subcount_config = config[self.config_key]

                if subcount_config.get("snapshot_type") == "top":
                    series_keys.append(f"{subcount_name}_by_view")
                    series_keys.append(f"{subcount_name}_by_download")
                else:
                    series_keys.append(subcount_name)

        series_keys.extend(self.special_subcounts)

        return series_keys

    @property
    def special_subcounts(self) -> list[str]:
        """Get special subcounts for usage snapshots."""
        return [
            "countries_by_view",
            "countries_by_download",
            "subjects_by_view",
            "subjects_by_download",
            "publishers_by_view",
            "publishers_by_download",
            "rights_by_view",
            "rights_by_download",
            "referrers_by_view",
            "referrers_by_download",
            "affiliations_by_view",
            "affiliations_by_download",
        ]

    def _get_special_subcount_metrics(self, subcount: str) -> list[str]:
        """Get the metrics for a special subcount.

        Returns:
            list[str]: List of metrics for the special subcount.
        """
        return [
            "views",
            "downloads",
            "view_visitors",
            "download_visitors",
            "data_volume",
        ]

    def _create_special_series_array(
        self, subcount: str, metric: str
    ) -> DataSeriesArray:
        """Create a data series array for a special subcount and metric.

        Returns:
            DataSeriesArray: The created data series array.
        """
        # All special subcounts use the same class - it auto-detects structure
        return DataSeriesArray(
            subcount,
            SubcountUsageSnapshotDataSeries,
            metric,
            is_global=False,
            chart_type="line",
            value_type="number",
        )

    # FIXME: Deprecated method
    def _discover_metrics_from_documents(self) -> dict[str, list[str]]:
        """Discover metrics from usage snapshot documents.

        Maps the actual document structure to desired output metrics:
        - view.total_events → views
        - download.total_events → downloads
        - view.unique_visitors → view_visitors
        - download.unique_visitors → download_visitors
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

    def _get_default_metrics(self) -> dict[str, list[str]]:
        """Get default metrics for usage snapshot data.

        Returns:
            dict[str, list[str]]: Dictionary mapping category to list of metrics.
        """
        metrics = [
            "data_volume",
            "download_unique_files",
            "download_unique_parents",
            "download_unique_records",
            "download_visitors",
            "downloads",
            "view_unique_parents",
            "view_unique_records",
            "view_visitors",
            "views",
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
                GlobalUsageSnapshotDataSeries,
                metric,
                is_global=True,
                chart_type="bar",
                value_type="number",
            )
        else:
            # All subcounts use the same class - it auto-detects structure
            return DataSeriesArray(
                series_key,
                SubcountUsageSnapshotDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
            )
