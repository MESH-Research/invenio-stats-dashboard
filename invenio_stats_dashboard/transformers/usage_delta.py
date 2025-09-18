# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Usage delta data series transformer."""

from typing import Any

from .base import BaseDataSeriesTransformer
from .types import (
    AggregationDocumentDict,
    UsageDeltaResultDict,
)


class UsageDeltaDataSeriesTransformer(BaseDataSeriesTransformer):
    """Transformer for usage delta aggregation documents."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the usage delta transformer."""
        super().__init__(config)
        self.subcount_types = {
            "access_statuses": "accessStatuses",
            "file_types": "fileTypes",
            "languages": "languages",
            "resource_types": "resourceTypes",
            "subjects": "subjects",
            "publishers": "publishers",
            "rights": "rights",
            "countries": "countries",
            "referrers": "referrers",
            "affiliations": "affiliations",
        }

    def transform(
        self, documents: list[AggregationDocumentDict]
    ) -> UsageDeltaResultDict:
        """Transform usage delta documents into data series.

        Args:
            documents: List of usage delta aggregation documents

        Returns:
            Dictionary containing transformed data series
        """
        delta_data = self._initialize_usage_delta_data_structure()

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

    def _initialize_usage_delta_data_structure(self) -> UsageDeltaResultDict:
        """Initialize the usage delta data structure."""
        return {
            "global": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "filePresence": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "accessStatuses": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "fileTypes": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "languages": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "resourceTypes": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "subjects": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "publishers": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "rights": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "countries": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "referrers": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "affiliations": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
        }

    def _get_net_view_events(self, item: dict[str, Any]) -> int:
        """Extract net view events count from a usage item."""
        return item.get("view", {}).get("total_events", 0) if item else 0

    def _get_net_download_events(self, item: dict[str, Any]) -> int:
        """Extract net download events count from a usage item."""
        return item.get("download", {}).get("total_events", 0) if item else 0

    def _get_net_visitors(self, item: dict[str, Any]) -> int:
        """Extract net unique visitors count from a usage item."""
        if not item:
            return 0
        view_data = item.get("view", {})
        download_data = item.get("download", {})
        view_visitors = view_data.get("unique_visitors", 0)
        download_visitors = download_data.get("unique_visitors", 0)
        return int(max(view_visitors, download_visitors))

    def _get_net_data_volume(self, item: dict[str, Any]) -> int:
        """Extract net data volume from a usage item."""
        return item.get("download", {}).get("total_volume", 0) if item else 0

    def _process_global_data(
        self, doc: AggregationDocumentDict, date: str, delta_data: UsageDeltaResultDict
    ) -> None:
        """Process global data points."""
        totals = doc.get("totals")
        if totals is None:
            return

        # Views
        views = self._get_net_view_events(totals)
        delta_data["global"]["views"].append(self.create_data_point(date, views))

        # Downloads
        downloads = self._get_net_download_events(totals)
        delta_data["global"]["downloads"].append(
            self.create_data_point(date, downloads)
        )

        # Visitors
        visitors = self._get_net_visitors(totals)
        delta_data["global"]["visitors"].append(self.create_data_point(date, visitors))

        # Data volume
        data_volume = self._get_net_data_volume(totals)
        delta_data["global"]["dataVolume"].append(
            self.create_data_point(date, data_volume, "filesize")
        )

    def _process_file_presence_data(
        self, doc: AggregationDocumentDict, date: str, delta_data: UsageDeltaResultDict
    ) -> None:
        """Process file presence data points."""
        totals = doc.get("totals")
        if totals is None:
            return

        view_data = totals.get("view", {})
        download_data = totals.get("download", {})
        data_point = {
            "date": date,
            "withFiles": self._get_net_view_events(view_data),
            "withoutFiles": self._get_net_download_events(download_data),
        }

        for metric_type in ["views", "downloads", "visitors", "dataVolume"]:
            delta_data["filePresence"][metric_type].append(data_point)

    def _process_subcount_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        delta_data: UsageDeltaResultDict,
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
                    "views": [],
                    "downloads": [],
                    "visitors": [],
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
                metric_types = ["views", "downloads", "visitors", "dataVolume"]
                for metric_type in metric_types:
                    value = 0

                    if metric_type == "views":
                        value = self._get_net_view_events(item)  # type: ignore[arg-type]
                    elif metric_type == "downloads":
                        value = self._get_net_download_events(item)  # type: ignore[arg-type]
                    elif metric_type == "visitors":
                        value = self._get_net_visitors(item)  # type: ignore[arg-type]
                    elif metric_type == "dataVolume":
                        value = self._get_net_data_volume(item)  # type: ignore[arg-type]

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
        self, delta_data: UsageDeltaResultDict, localization_map: dict[str, str]
    ) -> None:
        """Convert data points to series."""
        # Convert global data points to series
        delta_data["global"]["views"] = [
            self.create_global_series(delta_data["global"]["views"], "line", "number")
        ]
        delta_data["global"]["downloads"] = [
            self.create_global_series(
                delta_data["global"]["downloads"], "line", "number"
            )
        ]
        delta_data["global"]["visitors"] = [
            self.create_global_series(
                delta_data["global"]["visitors"], "line", "number"
            )
        ]
        delta_data["global"]["dataVolume"] = [
            self.create_global_series(
                delta_data["global"]["dataVolume"], "line", "filesize"
            )
        ]

        # Create file presence series
        for metric_type in ["views", "downloads", "visitors", "dataVolume"]:
            data_points = delta_data["filePresence"][metric_type]
            delta_data["filePresence"][metric_type] = self.create_data_series_array(
                ["withFiles", "withoutFiles"], data_points
            )

        # Create subcount series
        for subcount_type, target_key in self.subcount_types.items():
            if (
                f"{target_key}Items" in delta_data
                and f"{target_key}DataPoints" in delta_data
            ):
                metric_types = ["views", "downloads", "visitors", "dataVolume"]
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
