# Copyright (C) 2025 Kcworks
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Record snapshot data series transformer classes."""

from pprint import pformat
from typing import Any

from flask import current_app

from .base import (
    DataSeries,
    DataSeriesArray,
    DataSeriesSet,
)


class GlobalRecordSnapshotDataSeries(DataSeries):
    """Data series for global record snapshot metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add global record snapshot data from document."""
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
        if not date:
            return

        # Handle different metric types
        if self.metric in ["records", "parents"]:
            # Map frontend metric names to document field names
            doc_field = f"total_{self.metric}"
            metric_data = doc.get(doc_field)
            if metric_data and isinstance(metric_data, dict):
                total_value = sum(
                    v for v in metric_data.values() if isinstance(v, int | float)
                )
                self.add_data_point(date, int(total_value))
        elif self.metric == "uploaders":
            # Map frontend metric name to document field name
            doc_field = "total_uploaders"
            metric_data = doc.get(doc_field)
            if metric_data is not None:
                self.add_data_point(date, metric_data)  # type: ignore[arg-type]
        elif self.metric in ["data_volume", "file_count"]:
            files_data = doc.get("total_files")
            if files_data and isinstance(files_data, dict):
                value = files_data.get(self.metric, 0)
                value_type = "filesize" if self.metric == "data_volume" else "number"
                self.add_data_point(date, value, value_type)
        else:
            # Direct numeric value (fallback for any other metrics)
            metric_data = doc.get(self.metric)
            if metric_data is not None:
                self.add_data_point(date, metric_data)  # type: ignore[arg-type]


class SubcountRecordSnapshotDataSeries(DataSeries):
    """Data series for subcount record snapshot metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add subcount record snapshot data from document."""
        # Extract date
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
        if not date:
            return

        # Handle different metric types
        if self.metric in ["records", "parents"]:
            # Sum the nested values for records and parents
            metric_data = doc.get(self.metric)
            if metric_data and isinstance(metric_data, dict):
                total_value = sum(
                    v for v in metric_data.values() if isinstance(v, int | float)
                )
                self.add_data_point(date, int(total_value))
        elif self.metric == "files":
            # For files, we need to handle data_volume and file_count separately
            # This should be handled by separate DataSeries instances
            metric_data = doc.get(self.metric)
            if metric_data and isinstance(metric_data, dict):
                # This shouldn't happen - files should be split into
                # data_volume and file_count
                pass
        elif self.metric in ["data_volume", "file_count"]:
            # These come from files structure
            files_data = doc.get("files")
            if files_data and isinstance(files_data, dict):
                value = files_data.get(self.metric, 0)
                value_type = "filesize" if self.metric == "data_volume" else "number"
                self.add_data_point(date, value, value_type)
        else:
            # Direct numeric value
            metric_data = doc.get(self.metric)
            if metric_data is not None:
                self.add_data_point(date, metric_data)  # type: ignore[arg-type]


class FilePresenceRecordSnapshotDataSeries(DataSeries):
    """Data series for file presence subcount (metadata_only vs with_files)."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add file presence data from document."""
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
        if not date:
            return

        if self.metric in ["records", "parents"]:
            # The subfields of  records  and parents  match the
            # series ids we're looking for
            metric_data = doc.get(f"total_{self.metric}")
            if isinstance(metric_data, dict):
                self.add_data_point(date, int(metric_data[self.series_id]), "number")
        elif self.metric in ["data_volume", "file_count"]:
            # These come from files structure
            files_data = doc.get("total_files", {})
            if self.series_id == "metadata_only":
                self.add_data_point(date, 0, "number")
            elif self.series_id == "with_files":
                value = files_data.get(self.metric, 0)
                value_type = "filesize" if self.metric == "data_volume" else "number"
                self.add_data_point(date, value, value_type)


class RecordSnapshotDataSeriesSet(DataSeriesSet):
    """Data series set for record snapshot documents."""

    @property
    def config_key(self) -> str:
        """Return the configuration key for record snapshot data."""
        return "records"

    @property
    def special_subcounts(self) -> list[str]:
        """Get special subcounts for record snapshots."""
        return ["file_presence"]

    def _get_special_subcount_metrics(self, subcount: str) -> list[str]:
        """Get the metrics for a special subcount."""
        # Return empty list to fall back to regular metrics discovery
        return []

    def _create_special_series_array(
        self, subcount: str, metric: str
    ) -> DataSeriesArray:
        """Create a data series array for a special subcount and metric."""
        if subcount == "file_presence":
            series_array = DataSeriesArray(
                "file_presence",
                FilePresenceRecordSnapshotDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
                is_special=True,
            )

            series_array.series = [
                FilePresenceRecordSnapshotDataSeries(
                    "metadata_only",
                    "Metadata Only",
                    metric,
                    "line",
                    "number",
                ),
                FilePresenceRecordSnapshotDataSeries(
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

    def _discover_metrics_from_documents(self) -> dict[str, list[str]]:
        """Discover metrics from record snapshot documents."""
        metrics = super()._discover_metrics_from_documents()
        assert isinstance(metrics, dict)

        # For record snapshots, map total_* metrics to frontend-expected names
        if "global" in metrics:
            metrics["global"] = [
                metric.replace("total_", "") for metric in metrics["global"] if metric != "total_files"
            ] + ["data_volume", "file_count"]

        # For subcounts, split files into data_volume and file_count
        for subcount_name in metrics:
            if subcount_name != "global" and "files" in metrics[subcount_name]:
                metrics[subcount_name] = [
                    metric for metric in metrics[subcount_name] if metric != "files"
                ] + ["data_volume", "file_count"]

        return metrics

    def _create_series_array(self, subcount: str, metric: str) -> DataSeriesArray:
        """Create a data series array for the given subcount and metric."""
        if subcount == "global":
            return DataSeriesArray(
                "global",
                GlobalRecordSnapshotDataSeries,
                metric,
                is_global=True,
                chart_type="bar",
                value_type="number",
            )
        else:
            return DataSeriesArray(
                subcount,
                SubcountRecordSnapshotDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
            )
