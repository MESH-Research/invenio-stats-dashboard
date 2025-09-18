# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Record delta data series transformer."""

from typing import Any

from .base import BaseDataSeriesTransformer
from .types import (
    AggregationDocumentDict,
    RecordDeltaResultDict,
)


class RecordDeltaDataSeriesTransformer(BaseDataSeriesTransformer):
    """Transformer for record delta aggregation documents."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the record delta transformer."""
        super().__init__(config)
        self.subcount_types = {
            "resource_types": "resourceTypes",
            "access_statuses": "accessStatuses",
            "languages": "languages",
            "affiliations_creators": "affiliations",
            "affiliations_contributors": "affiliations",
            "funders": "funders",
            "subjects": "subjects",
            "publishers": "publishers",
            "periodicals": "periodicals",
            "rights": "rights",
            "file_types": "fileTypes",
        }

    def transform(
        self, documents: list[AggregationDocumentDict]
    ) -> RecordDeltaResultDict:
        """Transform record delta documents into data series.

        Args:
            documents: List of record delta aggregation documents

        Returns:
            Dictionary containing transformed data series
        """
        delta_data = self._initialize_delta_data_structure()

        if not documents:
            return delta_data

        # Create localization map from all documents
        localization_map = self.create_localization_map(documents)

        for doc in documents:
            period_start = doc.get("period_start")
            if period_start is None:
                continue
            date = period_start.split("T")[0]
            if not date:
                continue

            # Process global data
            self._process_global_data(doc, date, delta_data)

            # Process file presence data
            self._process_file_presence_data(doc, date, delta_data)

            # Process subcount data
            self._process_subcount_data(doc, date, delta_data, localization_map)

        # Convert data points to series
        self._convert_to_series(delta_data, localization_map)

        return delta_data

    def _initialize_delta_data_structure(self) -> RecordDeltaResultDict:
        """Initialize the delta data structure."""
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

    def _get_net_count(self, item: dict[str, Any]) -> int:
        """Calculate net count change for a subcount item."""
        if "added" in item and "removed" in item:
            added = int(item["added"].get("metadata_only", 0)) + int(
                item["added"].get("with_files", 0)
            )
            removed = int(item["removed"].get("metadata_only", 0)) + int(
                item["removed"].get("with_files", 0)
            )
            return added - removed
        return 0

    def _get_net_file_count(self, item: dict[str, Any]) -> int:
        """Calculate net file count change for a subcount item."""
        if "added" in item and "removed" in item:
            return int(item["added"].get("file_count", 0)) - int(
                item["removed"].get("file_count", 0)
            )
        elif "files" in item:
            files = item["files"]
            return int(files.get("added", {}).get("file_count", 0)) - int(
                files.get("removed", {}).get("file_count", 0)
            )
        return 0

    def _get_net_data_volume(self, item: dict[str, Any]) -> int:
        """Calculate net data volume change for a subcount item."""
        if "added" in item and "removed" in item:
            return int(item["added"].get("data_volume", 0)) - int(
                item["removed"].get("data_volume", 0)
            )
        elif "files" in item:
            files = item["files"]
            return int(files.get("added", {}).get("data_volume", 0)) - int(
                files.get("removed", {}).get("data_volume", 0)
            )
        return 0

    def _process_global_data(
        self, doc: AggregationDocumentDict, date: str, delta_data: RecordDeltaResultDict
    ) -> None:
        """Process global data points."""
        # Records
        records_data = doc.get("records")
        if records_data is not None:
            records_net = self._get_net_count(records_data)
            delta_data["global"]["records"].append(
                self.create_data_point(date, records_net)
            )

        # Parents
        parents_data = doc.get("parents")
        if parents_data is not None:
            parents_net = self._get_net_count(parents_data)
            delta_data["global"]["parents"].append(
                self.create_data_point(date, parents_net)
            )

        # Uploaders
        uploaders = doc.get("uploaders")
        if uploaders is not None:
            delta_data["global"]["uploaders"].append(
                self.create_data_point(date, uploaders)
            )

        # File count
        files_data = doc.get("files")
        if files_data is not None:
            file_count_net = self._get_net_file_count(files_data)
            delta_data["global"]["fileCount"].append(
                self.create_data_point(date, file_count_net)
            )

        # Data volume
        if files_data is not None:
            data_volume_net = self._get_net_data_volume(files_data)
            delta_data["global"]["dataVolume"].append(
                self.create_data_point(date, data_volume_net, "filesize")
            )

    def _process_file_presence_data(
        self, doc: AggregationDocumentDict, date: str, delta_data: RecordDeltaResultDict
    ) -> None:
        """Process file presence data points."""
        for key in ["records", "parents"]:
            data_point = {"date": date}

            # Calculate net change for delta data
            key_data = doc.get(key)
            if key_data is None or not isinstance(key_data, dict):
                continue
            added_data = key_data.get("added", {})
            removed_data = key_data.get("removed", {})

            data_point["withFiles"] = added_data.get(
                "with_files", 0
            ) - removed_data.get("with_files", 0)
            data_point["metadataOnly"] = added_data.get(
                "metadata_only", 0
            ) - removed_data.get("metadata_only", 0)

            delta_data["filePresence"][key].append(data_point)

    def _process_subcount_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        delta_data: RecordDeltaResultDict,
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
            if f"{target_key}DataPoints" not in delta_data:
                delta_data[f"{target_key}DataPoints"] = {
                    "records": [],
                    "parents": [],
                    "uploaders": [],
                    "fileCount": [],
                    "dataVolume": [],
                }
                delta_data[f"{target_key}Items"] = []

            for item in subcount_series:
                # Store item for later series creation
                if not any(
                    existing.get("id") == item.get("id")
                    for existing in delta_data[f"{target_key}Items"]
                ):
                    delta_data[f"{target_key}Items"].append(item)

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
                            value = self._get_net_count(records_data)  # type: ignore[arg-type]
                        else:
                            value = 0
                    elif metric_type == "parents":
                        parents_data = item.get("parents", item)
                        if isinstance(parents_data, dict):
                            value = self._get_net_count(parents_data)  # type: ignore[arg-type]
                        else:
                            value = 0
                    elif metric_type == "uploaders":
                        uploaders_value = item.get("uploaders")
                        value = (
                            int(uploaders_value) if uploaders_value is not None else 0
                        )
                    elif metric_type == "fileCount":
                        files_data = item.get("files", item)
                        if isinstance(files_data, dict):
                            value = self._get_net_file_count(files_data)  # type: ignore[arg-type]
                        else:
                            value = 0
                    elif metric_type == "dataVolume":
                        files_data = item.get("files", item)
                        if isinstance(files_data, dict):
                            value = self._get_net_data_volume(files_data)  # type: ignore[arg-type]
                        else:
                            value = 0

                    # Find or create data point for this date
                    data_points = delta_data[f"{target_key}DataPoints"][metric_type]
                    existing_data_point = next(
                        (dp for dp in data_points if dp.get("date") == date), None
                    )
                    if not existing_data_point:
                        existing_data_point = {"date": date}
                        data_points.append(existing_data_point)

                    existing_data_point[item["id"]] = value

    def _convert_to_series(
        self, delta_data: RecordDeltaResultDict, localization_map: dict[str, str]
    ) -> None:
        """Convert data points to series."""
        # Convert global data points to series
        delta_data["global"]["records"] = [
            self.create_global_series(delta_data["global"]["records"], "line", "number")
        ]
        delta_data["global"]["parents"] = [
            self.create_global_series(delta_data["global"]["parents"], "line", "number")
        ]
        delta_data["global"]["uploaders"] = [
            self.create_global_series(
                delta_data["global"]["uploaders"], "line", "number"
            )
        ]
        delta_data["global"]["fileCount"] = [
            self.create_global_series(
                delta_data["global"]["fileCount"], "line", "number"
            )
        ]
        delta_data["global"]["dataVolume"] = [
            self.create_global_series(
                delta_data["global"]["dataVolume"], "line", "filesize"
            )
        ]

        # Create file presence series
        for metric_type in ["records", "parents"]:
            data_points = delta_data["filePresence"][metric_type]
            value_type = "filesize" if metric_type == "dataVolume" else "number"
            delta_data["filePresence"][metric_type] = self.create_data_series_array(
                ["withFiles", "metadataOnly"], data_points, "line", value_type
            )

        # Create subcount series
        for subcount_type, target_key in self.subcount_types.items():
            if (
                f"{target_key}Items" in delta_data
                and f"{target_key}DataPoints" in delta_data
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
                    delta_data[target_key][metric_type] = (
                        self.create_data_series_from_items(
                            delta_data[f"{target_key}Items"],
                            delta_data[f"{target_key}DataPoints"][metric_type],
                            "line",
                            value_type,
                            localization_map,
                        )
                    )

                # Clean up temporary data
                del delta_data[f"{target_key}Items"]
                del delta_data[f"{target_key}DataPoints"]
