# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Registry mapping UI components to their required metrics per subcount.

This registry serves as the single source of truth for which metrics
each component needs. When optimization is enabled, transformers will
only generate series for metrics listed here.

Structure:
{
    "category": {
        "subcount": {
            "metric": ["component1", "component2", ...]
        }
    }
}

Note: Both subcount names and metric names use snake_case to match the
transformer internal format. Transformers use snake_case internally
(e.g., "resource_types", "data_volume", "view_unique_records",
"publishers_by_view") and only convert to camelCase when outputting JSON.
"""

from typing import Any

from flask import current_app

# Registry mapping components to their required metrics per subcount
COMPONENT_METRICS_REGISTRY = {
    "record_deltas": {
        "global": {
            "records": ["ContentStatsChart", "SingleStatRecordCount"],
            "uploaders": ["ContentStatsChart", "SingleStatUploaders"],
            "data_volume": ["ContentStatsChart", "SingleStatDataVolume"],
        },
        # All record delta subcounts use only "records" metric
        "publishers": {
            "records": ["PublishersMultiDisplayDelta"],
        },
        "resource_types": {
            "records": ["ResourceTypesMultiDisplayDelta"],
        },
        "file_types": {
            "records": ["FileTypesMultiDisplayDelta"],
        },
        "rights": {
            "records": ["RightsMultiDisplayDelta"],
        },
        "access_statuses": {
            "records": ["AccessStatusesMultiDisplayDelta"],
        },
        "funders": {
            "records": ["FundersMultiDisplayDelta"],
        },
        "languages": {
            "records": ["LanguagesMultiDisplayDelta"],
        },
        "affiliations": {
            "records": ["AffiliationsMultiDisplayDelta"],
        },
        "subjects": {
            "records": ["SubjectsMultiDisplayDelta"],
        },
        "periodicals": {
            "records": ["PeriodicalsMultiDisplayDelta"],
        },
    },
    "record_snapshots": {
        "global": {
            "records": [
                "ContentStatsChartCumulative",
                "SingleStatRecordCountCumulative",
            ],
            "uploaders": [
                "ContentStatsChartCumulative",
                "SingleStatUploadersCumulative",
            ],
            "data_volume": [
                "ContentStatsChartCumulative",
                "SingleStatDataVolumeCumulative",
            ],
            "file_count": ["ContentStatsChartCumulative"],
        },
        # All record snapshot subcounts use only "records" metric
        "publishers": {
            "records": ["PublishersMultiDisplay"],
        },
        "resource_types": {
            "records": ["ResourceTypesMultiDisplay"],
        },
        "file_types": {
            "records": ["FileTypesMultiDisplay"],
        },
        "rights": {
            "records": ["RightsMultiDisplay"],
        },
        "access_statuses": {
            "records": ["AccessStatusesMultiDisplay"],
        },
        "funders": {
            "records": ["FundersMultiDisplay"],
        },
        "languages": {
            "records": ["LanguagesMultiDisplay"],
        },
        "affiliations": {
            "records": ["AffiliationsMultiDisplay"],
        },
        "subjects": {
            "records": ["SubjectsMultiDisplay"],
        },
        "periodicals": {
            "records": ["PeriodicalsMultiDisplay"],
        },
    },
    "usage_deltas": {
        "global": {
            "views": ["TrafficStatsChart", "SingleStatViews"],
            "downloads": ["TrafficStatsChart", "SingleStatDownloads"],
            "data_volume": ["TrafficStatsChart", "SingleStatTraffic"],
        },
        "countries": {
            "views": ["CountriesMultiDisplayViewsDelta", "StatsMap"],
        },
        "referrers": {
            "views": ["ReferrersMultiDisplayViewsDelta"],
        },
        # Views breakdowns use view_unique_records
        "publishers": {
            "view_unique_records": ["PublishersMultiDisplayViewsDelta"],
            "download_unique_files": ["PublishersMultiDisplayDownloadsDelta"],
        },
        "affiliations": {
            "view_unique_records": ["AffiliationsMultiDisplayViewsDelta"],
            "download_unique_files": ["AffiliationsMultiDisplayDownloadsDelta"],
        },
        "funders": {
            "view_unique_records": ["FundersMultiDisplayViewsDelta"],
            "download_unique_files": ["FundersMultiDisplayDownloadsDelta"],
        },
        "periodicals": {
            "view_unique_records": ["PeriodicalsMultiDisplayViewsDelta"],
            "download_unique_files": ["PeriodicalsMultiDisplayDownloadsDelta"],
        },
        "rights": {
            "view_unique_records": ["RightsMultiDisplayViewsDelta"],
            "download_unique_files": ["RightsMultiDisplayDownloadsDelta"],
        },
        "languages": {
            "view_unique_records": ["LanguagesMultiDisplayViewsDelta"],
            "download_unique_files": ["LanguagesMultiDisplayDownloadsDelta"],
        },
        "subjects": {
            "view_unique_records": ["SubjectsMultiDisplayViewsDelta"],
            "download_unique_files": ["SubjectsMultiDisplayDownloadsDelta"],
        },
        "access_statuses": {
            "view_unique_records": ["AccessStatusesMultiDisplayViewsDelta"],
            "download_unique_files": ["AccessStatusesMultiDisplayDownloadsDelta"],
        },
        "resource_types": {
            "view_unique_records": ["ResourceTypesMultiDisplayViewsDelta"],
            "download_unique_files": ["ResourceTypesMultiDisplayDownloadsDelta"],
        },
        "file_types": {
            "view_unique_records": ["FileTypesMultiDisplayViewsDelta"],
            "download_unique_files": ["FileTypesMultiDisplayDownloadsDelta"],
        },
    },
    "usage_snapshots": {
        "global": {
            "views": [
                "TrafficStatsChartCumulative",
                "SingleStatViewsCumulative",
            ],
            "downloads": [
                "TrafficStatsChartCumulative",
                "SingleStatDownloadsCumulative",
            ],
            "data_volume": [
                "TrafficStatsChartCumulative",
                "SingleStatTrafficCumulative",
            ],
        },
        "countries_by_view": {
            "views": ["CountriesMultiDisplayViews", "StatsMap"],
        },
        "countries_by_download": {
            "downloads": ["StatsMap"],
        },
        # Views breakdowns use view_unique_records
        "publishers_by_view": {
            "view_unique_records": ["PublishersMultiDisplayViews"],
        },
        "affiliations_by_view": {
            "view_unique_records": ["AffiliationsMultiDisplayViews"],
        },
        "funders_by_view": {
            "view_unique_records": ["FundersMultiDisplayViews"],
        },
        "periodicals_by_view": {
            "view_unique_records": ["PeriodicalsMultiDisplayViews"],
        },
        "rights_by_view": {
            "view_unique_records": ["RightsMultiDisplayViews"],
        },
        "languages_by_view": {
            "view_unique_records": ["LanguagesMultiDisplayViews"],
        },
        "subjects_by_view": {
            "view_unique_records": ["SubjectsMultiDisplayViews"],
        },
        "access_statuses_by_view": {
            "view_unique_records": ["AccessStatusesMultiDisplayViews"],
        },
        "resource_types_by_view": {
            "view_unique_records": ["ResourceTypesMultiDisplayViews"],
        },
        "file_types_by_view": {
            "view_unique_records": ["FileTypesMultiDisplayViews"],
        },
        # Downloads breakdowns use download_unique_files
        "publishers_by_download": {
            "download_unique_files": ["PublishersMultiDisplayDownloads"],
        },
        "affiliations_by_download": {
            "download_unique_files": ["AffiliationsMultiDisplayDownloads"],
        },
        "funders_by_download": {
            "download_unique_files": ["FundersMultiDisplayDownloads"],
        },
        "periodicals_by_download": {
            "download_unique_files": ["PeriodicalsMultiDisplayDownloads"],
        },
        "rights_by_download": {
            "download_unique_files": ["RightsMultiDisplayDownloads"],
        },
        "languages_by_download": {
            "download_unique_files": ["LanguagesMultiDisplayDownloads"],
        },
        "subjects_by_download": {
            "download_unique_files": ["SubjectsMultiDisplayDownloads"],
        },
        "access_statuses_by_download": {
            "download_unique_files": ["AccessStatusesMultiDisplayDownloads"],
        },
        "resource_types_by_download": {
            "download_unique_files": ["ResourceTypesMultiDisplayDownloads"],
        },
        "file_types_by_download": {
            "download_unique_files": ["FileTypesMultiDisplayDownloads"],
        },
    },
}


def extract_component_names_from_layout(
    layout: dict[str, Any],
) -> set[str]:
    """Extract all component names from a dashboard layout configuration.

    Args:
        layout: Dashboard layout configuration dictionary with structure:
            {"tabs": [{"rows": [{"components": [{"component": "Name", ...}]}]}]}
            or {"rows": [{"components": [{"component": "Name", ...}]}]}

    Returns:
        Set of component names found in the layout.
    """
    component_names: set[str] = set()

    for tab in layout.get("tabs", []):
        for row in tab.get("rows", []):
            for component in row.get("components", []):
                if component_name := component.get("component"):
                    component_names.add(component_name)

    for row in layout.get("rows", []):
        for component in row.get("components", []):
            if component_name := component.get("component"):
                component_names.add(component_name)

    return component_names


def get_required_metrics_for_category(
    category: str,
    optimize: bool = False,
    subcounts: list[str] | None = None,
    component_names: list[str] | set[str] | None = None,
) -> dict[str, set[str]] | None:
    """Get required metrics per subcount for a given category.

    Args:
        category: One of "record_deltas", "record_snapshots",
                  "usage_deltas", "usage_snapshots"
        optimize: If True, return only metrics used by components.
                  If False, return None (use all metrics).
        subcounts: Optional list of subcount names to include. If None,
                   returns metrics for all subcounts in the registry.
        component_names: Optional list or set of component names to filter by.
                        If provided, only metrics used by these components
                        will be included. If None, includes metrics for all
                        components in the registry.

    Returns:
        Dictionary mapping subcount names to sets of required metric names.
        Returns None if optimize=False (indicating all metrics should be included).
    """
    if not optimize:
        return None

    if category not in COMPONENT_METRICS_REGISTRY:
        if current_app:
            current_app.logger.warning(
                f"Category {category} not found in component metrics registry. "
                "Falling back to all metrics."
            )
        return None

    # Convert component_names to set for efficient membership testing
    component_names_set: set[str] | None = None
    if component_names:
        component_names_set = (
            set(component_names)
            if isinstance(component_names, list)
            else component_names
        )

    required_metrics: dict[str, set[str]] = {}
    category_registry = COMPONENT_METRICS_REGISTRY[category]

    subcounts_to_check = (
        subcounts if subcounts is not None else category_registry.keys()
    )

    for subcount in subcounts_to_check:
        if subcount in category_registry:
            metrics_dict = category_registry[subcount]
            if component_names_set:
                # Filter metrics to only those used by the specified components
                filtered_metrics = set()
                for metric, components_using_metric in metrics_dict.items():
                    if any(
                        comp in component_names_set
                        for comp in components_using_metric
                    ):
                        filtered_metrics.add(metric)
                required_metrics[subcount] = filtered_metrics
            else:
                # Include all metrics in registry for this subcount
                required_metrics[subcount] = set(metrics_dict.keys())

    return required_metrics


def get_components_for_metric(
    category: str,
    subcount: str,
    metric: str,
) -> list[str]:
    """Get list of components that use a specific metric.

    Args:
        category: One of "record_deltas", "record_snapshots",
                  "usage_deltas", "usage_snapshots"
        subcount: Subcount name (e.g., "publishers", "global")
        metric: Metric name (e.g., "records", "views")

    Returns:
        List of component names that use this metric, or empty list if not found.
    """
    if category not in COMPONENT_METRICS_REGISTRY:
        return []

    category_registry = COMPONENT_METRICS_REGISTRY[category]
    if subcount not in category_registry:
        return []

    subcount_registry = category_registry[subcount]
    if metric not in subcount_registry:
        return []

    return subcount_registry[metric]


def validate_registry() -> dict[str, list[str]]:
    """Validate the registry for consistency and completeness.

    Returns:
        Dictionary with validation results:
        - "errors": List of error messages
        - "warnings": List of warning messages
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check that all categories are present
    expected_categories = [
        "record_deltas",
        "record_snapshots",
        "usage_deltas",
        "usage_snapshots",
    ]

    for category in expected_categories:
        if category not in COMPONENT_METRICS_REGISTRY:
            errors.append(f"Missing category: {category}")

    # Check for empty subcounts
    for category, subcounts in COMPONENT_METRICS_REGISTRY.items():
        for subcount, metrics in subcounts.items():
            if not metrics:
                warnings.append(
                    f"Empty metrics dict for {category}.{subcount}"
                )
            for metric, components in metrics.items():
                if not components:
                    warnings.append(
                        f"No components listed for {category}.{subcount}.{metric}"
                    )

    return {
        "errors": errors,
        "warnings": warnings,
    }
