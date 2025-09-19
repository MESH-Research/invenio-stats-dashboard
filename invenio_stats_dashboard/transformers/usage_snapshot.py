# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Usage snapshot data series transformer."""

from typing import Any

from .base import BaseDataSeriesTransformer, DataPoint
from .types import (
    AggregationDocumentDict,
    SubcountSeriesDict,
    UsageSnapshotResultDict,
)


class UsageSnapshotDataSeriesTransformer(BaseDataSeriesTransformer):
    """Transformer for usage snapshot aggregation documents."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the usage snapshot transformer."""
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

        # Mapping for separate view/download properties
        self.separate_subcount_types = {
            "countries": {
                "by_view": "countriesByView",
                "by_download": "countriesByDownload",
            },
            "subjects": {
                "by_view": "subjectsByView",
                "by_download": "subjectsByDownload",
            },
            "publishers": {
                "by_view": "publishersByView",
                "by_download": "publishersByDownload",
            },
            "rights": {"by_view": "rightsByView", "by_download": "rightsByDownload"},
            "referrers": {
                "by_view": "referrersByView",
                "by_download": "referrersByDownload",
            },
            "affiliations": {
                "by_view": "affiliationsByView",
                "by_download": "affiliationsByDownload",
            },
        }

    def transform(
        self, documents: list[AggregationDocumentDict]
    ) -> UsageSnapshotResultDict:
        """Transform usage snapshot documents into data series.

        Args:
            documents: List of usage snapshot aggregation documents

        Returns:
            Dictionary containing transformed data series
        """
        snapshot_data = self._initialize_usage_snapshot_data_structure()

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

            # Process subcount data
            self._process_subcount_data(doc, date, snapshot_data, localization_map)

        # Convert data points to series
        self._convert_to_series(snapshot_data, localization_map)

        return snapshot_data

    def _initialize_usage_snapshot_data_structure(self) -> UsageSnapshotResultDict:
        """Initialize the usage snapshot data structure."""
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
            # Separate properties for view-based and download-based data
            "countriesByView": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "countriesByDownload": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "subjectsByView": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "subjectsByDownload": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "publishersByView": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "publishersByDownload": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "rightsByView": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "rightsByDownload": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "referrersByView": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "referrersByDownload": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "affiliationsByView": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
            "affiliationsByDownload": {
                "views": [],
                "downloads": [],
                "visitors": [],
                "dataVolume": [],
            },
        }

    def _get_total_view_events(
        self, item: dict[str, Any] | SubcountSeriesDict | None
    ) -> int:
        """Extract total view events count from a usage snapshot item."""
        if not item:
            return 0
        if isinstance(item, dict):
            return item.get("total_events", 0)
        return 0

    def _get_total_download_events(
        self, item: dict[str, Any] | SubcountSeriesDict | None
    ) -> int:
        """Extract total download events count from a usage snapshot item."""
        if not item:
            return 0
        if isinstance(item, dict):
            return item.get("total_events", 0)
        return 0

    def _get_total_visitors(
        self, item: dict[str, Any] | SubcountSeriesDict | None
    ) -> int:
        """Extract total unique visitors count from a usage snapshot item."""
        if not item:
            return 0
        if isinstance(item, dict):
            view_visitors = item.get("unique_visitors", 0)
            download_visitors = item.get("unique_visitors", 0)
            return int(max(view_visitors, download_visitors))
        return 0

    def _get_total_data_volume(
        self, item: dict[str, Any] | SubcountSeriesDict | None
    ) -> int:
        """Extract total data volume from a usage snapshot item."""
        if not item:
            return 0
        if isinstance(item, dict):
            return item.get("total_volume", 0)
        return 0

    def _extract_series_data(
        self,
        documents: list[AggregationDocumentDict],
        category: str,
        metric: str,
        subcount_id: str | None = None,
    ) -> list[DataPoint]:
        """Extract data points for a specific usage snapshot series.

        Args:
            documents: List of usage snapshot aggregation documents
            category: Series category ('global', 'accessStatuses', etc.)
            metric: Metric type ('views', 'downloads', 'visitors', 'dataVolume')
            subcount_id: Specific subcount item ID (for subcount series)

        Returns:
            List of DataPoint objects
        """
        data_points = []

        for doc in documents:
            snapshot_date = doc.get("snapshot_date")
            if snapshot_date is None:
                continue
            date = snapshot_date.split("T")[0]
            if not date:
                continue

            value = self._extract_value_for_series(doc, category, metric, subcount_id)
            if value is not None:
                value_type = "filesize" if metric == "dataVolume" else "number"
                data_points.append(self.create_data_point(date, value, value_type))

        return data_points

    def _extract_value_for_series(
        self,
        doc: AggregationDocumentDict,
        category: str,
        metric: str,
        subcount_id: str | None = None,
    ) -> int | float | None:
        """Extract value for a specific series from a document."""
        if category == "global":
            return self._extract_global_value(doc, metric)
        else:
            return self._extract_subcount_value(doc, category, metric, subcount_id)

    def _extract_global_value(
        self, doc: AggregationDocumentDict, metric: str
    ) -> int | float | None:
        """Extract value from global totals."""
        totals = doc.get("totals")
        if not totals:
            return None

        if metric == "views":
            view_data = totals.get("view")
            return self._get_total_view_events(view_data) if view_data else 0
        elif metric == "downloads":
            download_data = totals.get("download")
            return (
                self._get_total_download_events(download_data) if download_data else 0
            )
        elif metric == "visitors":
            view_data = totals.get("view")
            return self._get_total_visitors(view_data) if view_data else 0
        elif metric == "dataVolume":
            download_data = totals.get("download")
            return self._get_total_data_volume(download_data) if download_data else 0

        return None

    def _extract_subcount_value(
        self,
        doc: AggregationDocumentDict,
        category: str,
        metric: str,
        subcount_id: str | None = None,
    ) -> int | float | None:
        """Extract value from subcount data."""
        subcounts = doc.get("subcounts")
        if not subcounts:
            return None

        # Map category to subcount type
        subcount_type = self._get_subcount_type_for_category(category)
        if not subcount_type:
            return None

        subcount_series = subcounts.get(subcount_type)
        if not subcount_series:
            return None

        # Handle different subcount structures
        if isinstance(subcount_series, list):
            return self._extract_from_simple_subcount(
                subcount_series, metric, subcount_id
            )
        elif isinstance(subcount_series, dict):
            return self._extract_from_separate_subcount(
                subcount_series, metric, subcount_id
            )

        return None

    def _get_subcount_type_for_category(self, category: str) -> str | None:
        """Get subcount type for a category."""
        # Reverse lookup in subcount_types
        for subcount_type, target_key in self.subcount_types.items():
            if target_key == category:
                return subcount_type

        # Check separate subcount types
        for subcount_type, separate_keys in self.separate_subcount_types.items():
            for key, separate_key in separate_keys.items():
                if separate_key == category:
                    return subcount_type

        return None

    def _extract_from_simple_subcount(
        self,
        subcount_series: list[SubcountSeriesDict],
        metric: str,
        subcount_id: str | None = None,
    ) -> int | float | None:
        """Extract value from simple subcount structure."""
        if subcount_id:
            # Find specific subcount item
            for item in subcount_series:
                if item.get("id") == subcount_id:
                    return self._extract_metric_from_item(item, metric)
        else:
            # Sum all items
            total = 0
            for item in subcount_series:
                value = self._extract_metric_from_item(item, metric)
                if value is not None:
                    total += value
            return total if total > 0 else None

        return None

    def _extract_from_separate_subcount(
        self,
        subcount_series: dict[str, Any],
        metric: str,
        subcount_id: str | None = None,
    ) -> int | float | None:
        """Extract value from separate view/download subcount structure."""
        # This would need more complex logic based on the specific structure
        # For now, return None as this requires more detailed implementation
        return None

    def _extract_metric_from_item(
        self, item: SubcountSeriesDict, metric: str
    ) -> int | float | None:
        """Extract specific metric value from a subcount item."""
        if metric == "views":
            return self._get_total_view_events(item)
        elif metric == "downloads":
            return self._get_total_download_events(item)
        elif metric == "visitors":
            return self._get_total_visitors(item)
        elif metric == "dataVolume":
            return self._get_total_data_volume(item)

        return None

    def _process_global_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        snapshot_data: UsageSnapshotResultDict,
    ) -> None:
        """Process global data points."""
        totals = doc.get("totals")
        if totals is None:
            return

        # Views
        view_data = totals.get("view")
        if view_data is not None:
            views = self._get_total_view_events(view_data)
            snapshot_data["global"]["views"].append(self.create_data_point(date, views))

        # Downloads
        download_data = totals.get("download")
        if download_data is not None:
            downloads = self._get_total_download_events(download_data)
            snapshot_data["global"]["downloads"].append(
                self.create_data_point(date, downloads)
            )

        # Visitors
        if view_data is not None:
            visitors = self._get_total_visitors(view_data)
            snapshot_data["global"]["visitors"].append(
                self.create_data_point(date, visitors)
            )

        # Data volume
        if download_data is not None:
            data_volume = self._get_total_data_volume(download_data)
            snapshot_data["global"]["dataVolume"].append(
                self.create_data_point(date, data_volume, "filesize")
            )

    def _process_subcount_data(
        self,
        doc: AggregationDocumentDict,
        date: str,
        snapshot_data: UsageSnapshotResultDict,
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

            # Handle different subcount structures
            if isinstance(subcount_series, list):
                # Simple array structure (unified field names)
                if subcount_series:
                    self._process_simple_subcount(
                        subcount_series,  # type: ignore[arg-type]
                        date,
                        target_key,
                        snapshot_data,
                        localization_map,
                    )
            elif isinstance(subcount_series, dict) and subcount_series is not None:
                # Object structure with separate view/download data
                separate_keys = self.separate_subcount_types.get(subcount_type)
                if separate_keys:
                    for key, separate_key in separate_keys.items():
                        separate_series = subcount_series.get(key)
                        if separate_series:
                            self._process_simple_subcount(
                                separate_series,
                                date,
                                separate_key,
                                snapshot_data,
                                localization_map,
                                key,
                            )

    def _process_simple_subcount(
        self,
        subcount_series: list[dict[str, Any]],
        date: str,
        target_key: str,
        snapshot_data: UsageSnapshotResultDict,
        localization_map: dict[str, str],
        data_type: str | None = None,
    ) -> None:
        """Process a simple subcount series."""
        # Initialize data structures if needed
        if f"{target_key}DataPoints" not in snapshot_data:
            snapshot_data[f"{target_key}DataPoints"] = {
                "views": [],
                "downloads": [],
                "visitors": [],
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
            metric_types = ["views", "downloads", "visitors", "dataVolume"]
            for metric_type in metric_types:
                value = 0

                if metric_type == "views":
                    if data_type == "by_view":
                        view_data = item.get("view")
                        value = (
                            self._get_total_view_events(view_data)
                            if view_data is not None
                            else 0
                        )
                    else:
                        value = self._get_total_view_events(item)
                elif metric_type == "downloads":
                    if data_type == "by_download":
                        download_data = item.get("download")
                        value = (
                            self._get_total_download_events(download_data)
                            if download_data is not None
                            else 0
                        )
                    else:
                        value = self._get_total_download_events(item)
                elif metric_type == "visitors":
                    if data_type == "by_view":
                        view_data = item.get("view")
                        value = (
                            self._get_total_visitors(view_data)
                            if view_data is not None
                            else 0
                        )
                    else:
                        value = self._get_total_visitors(item)
                elif metric_type == "dataVolume":
                    if data_type == "by_download":
                        download_data = item.get("download")
                        value = (
                            self._get_total_data_volume(download_data)
                            if download_data is not None
                            else 0
                        )
                    else:
                        value = self._get_total_data_volume(item)

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
        self, snapshot_data: UsageSnapshotResultDict, localization_map: dict[str, str]
    ) -> None:
        """Convert data points to series."""
        # Convert global data points to series
        snapshot_data["global"]["views"] = [
            self.create_global_series(snapshot_data["global"]["views"], "bar", "number")
        ]
        snapshot_data["global"]["downloads"] = [
            self.create_global_series(
                snapshot_data["global"]["downloads"], "bar", "number"
            )
        ]
        snapshot_data["global"]["visitors"] = [
            self.create_global_series(
                snapshot_data["global"]["visitors"], "bar", "number"
            )
        ]
        snapshot_data["global"]["dataVolume"] = [
            self.create_global_series(
                snapshot_data["global"]["dataVolume"], "bar", "filesize"
            )
        ]

        # Create subcount series
        for subcount_type, target_key in self.subcount_types.items():
            if (
                f"{target_key}Items" in snapshot_data
                and f"{target_key}DataPoints" in snapshot_data
            ):
                metric_types = ["views", "downloads", "visitors", "dataVolume"]
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

        # Create separate subcount series
        for subcount_type, separate_keys in self.separate_subcount_types.items():
            for key, separate_key in separate_keys.items():
                if (
                    f"{separate_key}Items" in snapshot_data
                    and f"{separate_key}DataPoints" in snapshot_data
                ):
                    metric_types = ["views", "downloads", "visitors", "dataVolume"]
                    for metric_type in metric_types:
                        value_type = (
                            "filesize" if metric_type == "dataVolume" else "number"
                        )
                        snapshot_data[separate_key][metric_type] = (
                            self.create_data_series_from_items(
                                snapshot_data[f"{separate_key}Items"],
                                snapshot_data[f"{separate_key}DataPoints"][metric_type],
                                "line",
                                value_type,
                                localization_map,
                            )
                        )

                    # Clean up temporary data
                    del snapshot_data[f"{separate_key}Items"]
                    del snapshot_data[f"{separate_key}DataPoints"]
