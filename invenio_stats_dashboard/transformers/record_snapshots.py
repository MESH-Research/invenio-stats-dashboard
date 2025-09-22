# Copyright (C) 2025 Kcworks
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Record snapshot data series transformer classes."""

from .base import (
    DataSeries,
    DataSeriesArray,
    DataSeriesSet,
)
from typing import Any


class GlobalRecordSnapshotDataSeries(DataSeries):
    """Data series for global record snapshot metrics."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add global record snapshot data from document."""
        # Extract date
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
        if not date:
            return

        # Get the metric data based on the metric name
        metric_data = doc.get(self.metric)
        if metric_data is None:
            return

        # Handle different metric types
        if self.metric in ["total_records", "total_parents"]:
            # Sum the nested values for records and parents
            if isinstance(metric_data, dict):
                total_value = sum(
                    v for v in metric_data.values() if isinstance(v, (int, float))
                )
                self.add_data_point(date, int(total_value))
        elif self.metric == "total_files":
            # For files, we need to handle data_volume and file_count separately
            # This should be handled by separate DataSeries instances
            if isinstance(metric_data, dict):
                # This shouldn't happen - total_files should be split into
                # data_volume and file_count
                pass
        elif self.metric in ["data_volume", "file_count"]:
            # These come from total_files structure
            files_data = doc.get("total_files")
            if files_data and isinstance(files_data, dict):
                value = files_data.get(self.metric, 0)
                value_type = "filesize" if self.metric == "data_volume" else "number"
                self.add_data_point(date, value, value_type)
        else:
            # Direct numeric value (like total_uploaders)
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

        # Get the metric data based on the metric name
        metric_data = doc.get(self.metric)
        if metric_data is None:
            return

        # Handle different metric types
        if self.metric in ["records", "parents"]:
            # Sum the nested values for records and parents
            if isinstance(metric_data, dict):
                total_value = sum(
                    v for v in metric_data.values() if isinstance(v, (int, float))
                )
                self.add_data_point(date, int(total_value))
        elif self.metric == "files":
            # For files, we need to handle data_volume and file_count separately
            # This should be handled by separate DataSeries instances
            if isinstance(metric_data, dict):
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
            self.add_data_point(date, metric_data)  # type: ignore[arg-type]


class FilePresenceRecordSnapshotDataSeries(DataSeries):
    """Data series for file presence subcount (metadata_only vs with_files)."""

    def add(self, doc: dict[str, Any]) -> None:
        """Add file presence data from document."""
        # Extract date
        snapshot_date = doc.get("snapshot_date")
        if snapshot_date is None:
            return
        date = snapshot_date.split("T")[0]
        if not date:
            return

        # Get total_records data
        total_records = doc.get("total_records")
        if not isinstance(total_records, dict):
            return

        # The metric should be the presence type (metadata_only or with_files)
        if self.metric in total_records:
            value = total_records[self.metric]
            self.add_data_point(date, value)


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
        if subcount == "file_presence":
            return ["metadata_only", "with_files"]  # Two presence types
        return []

    def _create_special_series_array(
        self, subcount: str, metric: str
    ) -> DataSeriesArray:
        """Create a data series array for a special subcount and metric."""
        if subcount == "file_presence":
            return DataSeriesArray(
                "file_presence",
                FilePresenceRecordSnapshotDataSeries,
                metric,
                is_global=False,
                chart_type="line",
                value_type="number",
            )
        raise NotImplementedError(f"Special subcount {subcount} not implemented")

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
