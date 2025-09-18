# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Record snapshot data series transformer."""

from typing import Any

from .base import BaseDataSeriesTransformer
from .types import (
    AggregationDocumentDict,
    RecordSnapshotResultDict,
)


class RecordSnapshotDataSeriesTransformer(BaseDataSeriesTransformer):
    """Transformer for record snapshot aggregation documents."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the record snapshot transformer."""
        super().__init__(config)
        self.subcount_types = {
            "resource_types": "resourceTypes",
            "access_statuses": "accessStatuses",
            "languages": "languages",
            "affiliations_creator": "affiliations",
            "affiliations_contributor": "affiliations",
            "funders": "funders",
            "subjects": "subjects",
            "publishers": "publishers",
            "periodicals": "periodicals",
            "rights": "rights",
            "file_types": "fileTypes",
        }

    def transform(
        self, documents: list[AggregationDocumentDict]
    ) -> RecordSnapshotResultDict:
        """Transform record snapshot documents into data series.

        Args:
            documents: List of record snapshot aggregation documents

        Returns:
            Dictionary containing transformed data series
        """
        snapshot_data = self._initialize_snapshot_data_structure()

        if not documents:
            return snapshot_data

        # Create localization map from all documents
        localization_map = self.create_localization_map(documents)

        for doc in documents:
            snapshot_date = doc.get("snapshot_date")
            if snapshot_date is None:
                continue
            date = snapshot_date.split("T")[0]
            if not date:
                continue

            # Process global data
            self._process_global_data(doc, date, snapshot_data)

            # Process file presence data
            self._process_file_presence_data(doc, date, snapshot_data)

            # Process subcount data
            self._process_subcount_data(doc, date, snapshot_data, localization_map)

        # Convert data points to series
        self._convert_to_series(snapshot_data, localization_map)

        return snapshot_data

    def _initialize_snapshot_data_structure(self) -> RecordSnapshotResultDict:
        """Initialize the snapshot data structure."""
        return {
            "global": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "filePresence": {"records": [], "parents": []},
            "accessStatuses": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "languages": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "affiliations": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "funders": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "subjects": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "publishers": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "periodicals": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "rights": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "fileTypes": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
            "resourceTypes": {
                "records": [],
                "parents": [],
                "uploaders": [],
                "fileCount": [],
                "dataVolume": [],
            },
        }

    def _get_total_count(self, item: dict[str, Any]) -> int:
        """Calculate total count for a record item."""
        if not item:
            return 0
        return int(item.get("metadata_only", 0) + item.get("with_files", 0))

    def _get_total_file_count(self, item: dict[str, Any]) -> int:
        """Extract total file count from a record item."""
        if not item:
            return 0
        return int(item.get("file_count", 0))

    def _get_total_data_volume(self, item: dict[str, Any]) -> int:
        """Extract total data volume from a record item."""
        if not item:
            return 0
        return int(item.get("data_volume", 0))

    def _process_global_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        snapshot_data: RecordSnapshotResultDict,
    ) -> None:
        """Process global data points."""
        # Records
        total_records_data = doc.get("total_records")
        if total_records_data is not None:
            total_records = self._get_total_count(total_records_data)
            snapshot_data["global"]["records"].append(
                self.create_data_point(date, total_records)
            )

        # Parents
        total_parents_data = doc.get("total_parents")
        if total_parents_data is not None:
            total_parents = self._get_total_count(total_parents_data)
            snapshot_data["global"]["parents"].append(
                self.create_data_point(date, total_parents)
            )

        # Uploaders
        total_uploaders = doc.get("total_uploaders")
        if total_uploaders is not None:
            snapshot_data["global"]["uploaders"].append(
                self.create_data_point(date, total_uploaders)
            )

        # File count
        total_files_data = doc.get("total_files")
        if total_files_data is not None:
            total_file_count = self._get_total_file_count(total_files_data)
            snapshot_data["global"]["fileCount"].append(
                self.create_data_point(date, total_file_count)
            )

        # Data volume
        if total_files_data is not None:
            total_data_volume = self._get_total_data_volume(total_files_data)
            snapshot_data["global"]["dataVolume"].append(
                self.create_data_point(date, total_data_volume, "filesize")
            )

    def _process_file_presence_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        snapshot_data: RecordSnapshotResultDict,
    ) -> None:
        """Process file presence data points."""
        for key in ["records", "parents"]:
            data_point: dict[str, Any] = {"date": date}
            total_data = doc.get(f"total_{key}")
            if total_data is None:
                continue

            if isinstance(total_data, dict):
                data_point["withFiles"] = total_data.get("with_files", 0)
                data_point["metadataOnly"] = total_data.get("metadata_only", 0)
            else:
                data_point["withFiles"] = 0
                data_point["metadataOnly"] = 0

            snapshot_data["filePresence"][key].append(data_point)

    def _process_subcount_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        snapshot_data: RecordSnapshotResultDict,
        localization_map: dict[str, str],
    ) -> None:
        """Process subcount data points."""
        subcounts = doc.get("subcounts")
        if subcounts is None:
            return

        for subcount_type, target_key in self.subcount_types.items():
            subcount_series = subcounts.get(subcount_type)
            if not subcount_series:
                continue

            # Initialize data structures if needed
            if f"{target_key}DataPoints" not in snapshot_data:
                snapshot_data[f"{target_key}DataPoints"] = {
                    "records": [],
                    "parents": [],
                    "uploaders": [],
                    "fileCount": [],
                    "dataVolume": [],
                }
                snapshot_data[f"{target_key}Items"] = []

            for item in subcount_series:
                # Store item for later series creation
                if not any(
                    existing.get("id") == item.get("id")
                    for existing in snapshot_data[f"{target_key}Items"]
                ):
                    snapshot_data[f"{target_key}Items"].append(item)

                # Process each metric type
                metric_types = [
                    "records",
                    "parents",
                    "uploaders",
                    "fileCount",
                    "dataVolume",
                ]
                for metric_type in metric_types:
                    value = 0

                    if metric_type == "records":
                        records_data = item.get("records", item)
                        if isinstance(records_data, dict):
                            value = self._get_total_count(records_data)  # type: ignore[arg-type]
                        else:
                            value = 0
                    elif metric_type == "parents":
                        parents_data = item.get("parents", item)
                        if isinstance(parents_data, dict):
                            value = self._get_total_count(parents_data)  # type: ignore[arg-type]
                        else:
                            value = 0
                    elif metric_type == "uploaders":
                        uploaders_value = item.get("total_uploaders")
                        value = (
                            int(uploaders_value) if uploaders_value is not None else 0
                        )
                    elif metric_type == "fileCount":
                        files_data = item.get("files", item)
                        if isinstance(files_data, dict):
                            value = self._get_total_file_count(files_data)  # type: ignore[arg-type]
                        else:
                            value = 0
                    elif metric_type == "dataVolume":
                        files_data = item.get("files", item)
                        if isinstance(files_data, dict):
                            value = self._get_total_data_volume(files_data)  # type: ignore[arg-type]
                        else:
                            value = 0

                    # Find or create data point for this date
                    data_points = snapshot_data[f"{target_key}DataPoints"][metric_type]
                    existing_data_point = next(
                        (dp for dp in data_points if dp.get("date") == date), None
                    )
                    if not existing_data_point:
                        existing_data_point = {"date": date}
                        data_points.append(existing_data_point)

                    existing_data_point[item["id"]] = value

    def _convert_to_series(
        self, snapshot_data: RecordSnapshotResultDict, localization_map: dict[str, str]
    ) -> None:
        """Convert data points to series."""
        # Convert global data points to series
        snapshot_data["global"]["records"] = [
            self.create_global_series(
                snapshot_data["global"]["records"], "bar", "number"
            )
        ]
        snapshot_data["global"]["parents"] = [
            self.create_global_series(
                snapshot_data["global"]["parents"], "bar", "number"
            )
        ]
        snapshot_data["global"]["uploaders"] = [
            self.create_global_series(
                snapshot_data["global"]["uploaders"], "bar", "number"
            )
        ]
        snapshot_data["global"]["fileCount"] = [
            self.create_global_series(
                snapshot_data["global"]["fileCount"], "bar", "number"
            )
        ]
        snapshot_data["global"]["dataVolume"] = [
            self.create_global_series(
                snapshot_data["global"]["dataVolume"], "bar", "filesize"
            )
        ]

        # Create file presence series
        for metric_type in ["records", "parents"]:
            data_points = snapshot_data["filePresence"][metric_type]
            value_type = "filesize" if metric_type == "dataVolume" else "number"
            snapshot_data["filePresence"][metric_type] = self.create_data_series_array(
                ["withFiles", "metadataOnly"], data_points, "line", value_type
            )

        # Create subcount series
        for subcount_type, target_key in self.subcount_types.items():
            if (
                f"{target_key}Items" in snapshot_data
                and f"{target_key}DataPoints" in snapshot_data
            ):
                metric_types = [
                    "records",
                    "parents",
                    "uploaders",
                    "fileCount",
                    "dataVolume",
                ]
                for metric_type in metric_types:
                    value_type = "filesize" if metric_type == "dataVolume" else "number"
                    snapshot_data[target_key][metric_type] = (
                        self.create_data_series_from_items(
                            snapshot_data[f"{target_key}Items"],
                            snapshot_data[f"{target_key}DataPoints"][metric_type],
                            "line",
                            value_type,
                            localization_map,
                        )
                    )

                # Clean up temporary data
                del snapshot_data[f"{target_key}Items"]
                del snapshot_data[f"{target_key}DataPoints"]
