# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Configuration for Invenio Stats Dashboard."""

from typing import Any

from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.resources.stats.event_builders import (
    build_record_unique_id,
)
from invenio_stats.contrib.event_builders import build_file_unique_id
from invenio_stats.processors import (
    EventsIndexer,
    anonymize_user,
    flag_machines,
    flag_robots,
)

from ..aggregations import register_aggregations
from ..permissions import CommunityStatsPermissionFactory
from ..resources.api_queries import (
    CommunityRecordDeltaResultsQuery,
    CommunityRecordSnapshotResultsQuery,
    CommunityStatsResultsQuery,
    CommunityUsageDeltaResultsQuery,
    CommunityUsageSnapshotResultsQuery,
)
from ..resources.data_series_queries import (
    RecordDeltaCategoryQuery,
    RecordDeltaDataSeriesQuery,
    RecordSnapshotCategoryQuery,
    RecordSnapshotDataSeriesQuery,
    UsageDeltaCategoryQuery,
    UsageDeltaDataSeriesQuery,
    UsageSnapshotCategoryQuery,
    UsageSnapshotDataSeriesQuery,
)
from ..resources.serializers.wrapper_functions import (
    brotli_json_serializer_func,
    data_series_csv_serializer_func,
    data_series_excel_serializer_func,
    data_series_xml_serializer_func,
    gzip_json_serializer_func,
    json_serializer_func,
)
from ..tasks.aggregation_tasks import CommunityStatsAggregationTask
from ..tasks.cache_tasks import CachedResponsesGenerationTask
from .component_metrics import COMPONENT_METRICS_REGISTRY

COMMUNITY_STATS_ENABLED = True
COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED = False
COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED = False

STATS_DASHBOARD_ENABLED_GLOBAL = True
STATS_DASHBOARD_ENABLED_COMMUNITY = True
STATS_DASHBOARD_COMMUNITY_OPT_IN = True

STATS_DASHBOARD_OPTIMIZE_DATA_SERIES = True
"""Whether to optimize data series by default.

When True, only metrics used by components in the current dashboard layout
will be included in data series responses. This reduces payload size by
excluding unused metrics.

Can be overridden per-request via the 'optimize' parameter in API requests,
or per-call in service methods and CLI commands.
"""

COMMUNITY_STATS_CELERYBEAT_AGG_SCHEDULE = {
    "stats-aggregate-community-record-stats": {
        **CommunityStatsAggregationTask,
    },
}
COMMUNITY_STATS_CELERYBEAT_CACHE_SCHEDULE = {
    "stats-cache-hourly-generation": {
        **CachedResponsesGenerationTask,
    },
}
"""Celery beat schedule for stats aggregation and caching tasks.

Includes both aggregation and cache generation tasks:
- stats-aggregate-community-record-stats: Runs at minute 40 every hour
- stats-cache-hourly-generation: Runs at minute 50 every hour (10 minutes
  after aggregation to ensure fresh data is available)

This timing is spaced from other InvenioRDM tasks:
- minute 0: stats-aggregate-events
- minute 10: reindex-stats
- minute 25, 55: stats-process-events
- minute 40: stats-aggregate-community-record-stats
- minute 50: stats-cache-hourly-generation
"""

COMMUNITY_STATS_AGGREGATIONS = register_aggregations()

COMMUNITY_STATS_CATCHUP_INTERVAL = 365

COMMUNITY_STATS_FILTER_AGGREGATION_SIZE = 10000
"""Maximum number of buckets to return from Terms aggregation.

This setting controls the size parameter for the Terms aggregation used in
filter_communities_by_activity(). OpenSearch/Elasticsearch has a default limit
(typically 10,000) for Terms aggregations. Setting this to a higher value
ensures all communities are included when filtering by activity criteria.

If you have more than this number of communities, you may need to increase
this value or use composite aggregations for pagination.
"""

STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY = _(
    "Community managers and administrators can enable the "
    "dashboard from the community settings page"
)

STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL = (
    "The global and community statistics dashboards must be enabled "
    "by the {title} administrators."
)

STATS_DASHBOARD_SETTINGS_COMMUNITY_ENABLED_LABEL = _("Enable Dashboard")

STATS_DASHBOARD_SETTINGS_COMMUNITY_ENABLED_DESCRIPTION = _(
    "Enable the 'Insights' tab that displays a community statistics dashboard."
)

STATS_DASHBOARD_UI_SUBCOUNTS: dict[str, dict] = {
    "resource_types": {},
    "subjects": {},
    "languages": {},
    "rights": {},
    "funders": {},
    "periodicals": {},
    "publishers": {},
    "affiliations": {},
    "countries": {},
    # Disabled: referrers (usage events only, now disabled)
    # "referrers": {},
    "file_types": {},
    "access_statuses": {},
}

# Distributed lock configuration for stats tasks
STATS_DASHBOARD_LOCK_CONFIG = {
    "enabled": True,  # Enable/disable distributed locking globally
    "aggregation": {
        "enabled": True,  # Enable/disable locking for aggregation tasks
        "lock_timeout": 86400,  # Lock timeout in seconds (24 hours)
        "lock_name": "community_stats_aggregation",  # Lock name
    },
    "response_caching": {
        "enabled": True,  # Enable/disable locking for cache generation tasks
        "lock_timeout": 3600,  # Lock timeout in seconds (1 hour)
        "lock_name": "community_stats_cache_generation",  # Lock name
    },
}

STATS_DASHBOARD_TEMPLATES = {
    "macro": "invenio_stats_dashboard/macros/stats_dashboard_macro.html",
    "global": "invenio_stats_dashboard/stats_dashboard.html",
    "community": "invenio_communities/details/stats/index.html",
}
"""Templates for the stats dashboard."""

STATS_DASHBOARD_ROUTES = {
    "global": "/stats",
    "community": "/communities/<pid_value>/stats",
}
"""Routes for the stats dashboard."""


STATS_DASHBOARD_API_ROUTES = {
    "stats_series": "/stats-dashboard",
}
"""Routes for the stats dashboard api endpoint. ('api' prefix added automatically)"""

STATS_DASHBOARD_UI_CONFIG = {
    "global": {
        "title": _("Statistics"),
        "description": _("This is the global stats dashboard."),
        "maxHistoryYears": 10,
        "default_granularity": "week",
        "show_title": False,  # controls title at top of sidebar
        "show_description": False,
    },
    "community": {
        "title": _("Statistics"),
        "description": _("This is the community stats dashboard."),
        "maxHistoryYears": 10,
        "default_granularity": "week",
        "show_title": True,
        "show_description": False,
    },
}

STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS = {
    "day": "30days",
    "week": "yearToDate",
    "month": "yearToDate",
    "quarter": "yearToDate",
    "year": "2years",
}

# Menu configuration
STATS_DASHBOARD_MENU_ENABLED = True
"""Enable or disable the stats menu item."""

STATS_DASHBOARD_MENU_TEXT = _("Statistics")
"""Text for the stats menu item."""

STATS_DASHBOARD_MENU_ORDER = 1
"""Order of the stats menu item in the menu."""

STATS_DASHBOARD_MENU_ENDPOINT = "invenio_stats_dashboard.global_stats_dashboard"
"""Endpoint for the stats menu item."""

STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION = None
"""Custom function to register the menu item. If None, uses default registration.
Should be a callable that takes the Flask app as its only argument."""

STATS_DASHBOARD_USE_TEST_DATA = False
"""Enable or disable test data mode. When True, the dashboard will use sample data
instead of making API calls."""

STATS_DASHBOARD_LAYOUT = {
    "global_layout": {
        "tabs": [
            {
                "name": "content",
                "label": _("Content"),
                "icon": "chart pie",
                "date_range_phrase": _("Cumulative totals as of"),
                "rows": [
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatRecordCountCumulative",
                                "width": 5,
                                "props": {
                                    "title": "Total Records",
                                    "icon": "file",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatUploadersCumulative",
                                "width": 6,
                                "props": {
                                    "title": "Total Uploaders",
                                    "icon": "users",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatDataVolumeCumulative",
                                "width": 5,
                                "props": {
                                    "title": "Total Data Volume",
                                    "icon": "database",
                                    "mobile": 16,
                                },
                            },
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {
                                "component": "ContentStatsChartCumulative",
                                "width": 16,
                                "props": {
                                    "height": 300,
                                    "title": "Cumulative Content Totals",
                                    "maxSeries": 10,
                                    "display_subcounts": {
                                        "resource_types": {},
                                        "languages": {},
                                        "rights": {},
                                        "affiliations": {},
                                        "funders": {},
                                        "publishers": {},
                                        "file_types": {},
                                        "access_statuses": {},
                                    },
                                },
                            },
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {
                                "component": "ResourceTypesMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Work Types",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "FileTypesMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top File Types",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "LanguagesMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Languages",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "SubjectsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Subjects",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "AccessStatusesMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Access Statuses",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "RightsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Rights",
                                    "pageSize": 10,
                                    "available_views": ["pie", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "AffiliationsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Affiliations",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            # {
                            #     "component": "FundersMultiDisplay",
                            #     "width": 8,
                            #     "props": {
                            #         "title": "Top Funders",
                            #         "pageSize": 10,
                            #         "available_views": ["pie", "bar", "list"],
                            #         "default_view": "list",
                            #         "hideOtherInCharts": True,
                            #     },
                            # },
                            {
                                "component": "PublishersMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Publishers",
                                    "pageSize": 8,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                        ],
                    },
                ],
            },
            {
                "name": "contributions",
                "label": _("Contributions"),
                "icon": "users",
                "date_range_phrase": _("Activity during"),
                "rows": [
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatRecordCount",
                                "width": 5,
                                "props": {
                                    "title": "New Records",
                                    "icon": "file",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatUploaders",
                                "width": 6,
                                "props": {
                                    "title": "Active Uploaders",
                                    "icon": "users",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatDataVolume",
                                "width": 5,
                                "props": {
                                    "title": "New Data Uploaded",
                                    "icon": "database",
                                    "mobile": 16,
                                },
                            },
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {
                                "component": "ContentStatsChart",
                                "width": 16,
                                "props": {
                                    "height": 300,
                                    "title": "New Contribution Rates",
                                    "maxSeries": 8,
                                    "display_subcounts": {
                                        "file_presence": {},
                                        "resource_types": {},
                                        "subjects": {},
                                        "languages": {},
                                        "rights": {},
                                        "affiliations": {},
                                        # "funders": {},
                                        "periodicals": {},
                                        "publishers": {},
                                        "file_types": {},
                                        "access_statuses": {},
                                    },
                                },
                            },
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {
                                "component": "ResourceTypesMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Work Types Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "FileTypesMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "File Types Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "LanguagesMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Languages Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "SubjectsMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Subjects Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "AccessStatusesMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Access Statuses Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "pie",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "RightsMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Rights Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "AffiliationsMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Affiliations Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            # {
                            #     "component": "FundersMultiDisplayDelta",
                            #     "width": 8,
                            #     "props": {
                            #         "title": "Funders Added",
                            #         "pageSize": 10,
                            #         "available_views": ["pie", "bar", "list"],
                            #         "default_view": "list",
                            #         "hideOtherInCharts": True,
                            #     },
                            # },
                            {
                                "component": "PeriodicalsMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Periodicals Added",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "PublishersMultiDisplayDelta",
                                "width": 8,
                                "props": {
                                    "title": "Publishers Added",
                                    "pageSize": 8,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                        ],
                    },
                ],
            },
            {
                "name": "traffic",
                "label": _("Cumulative Traffic"),
                "date_range_phrase": _("Cumulative totals as of"),
                "icon": "world",
                "rows": [
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatViewsCumulative",
                                "width": 5,
                                "props": {
                                    "title": "Total Views",
                                    "icon": "eye",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatDownloadsCumulative",
                                "width": 6,
                                "props": {
                                    "title": "Total Downloads",
                                    "icon": "download",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatTrafficCumulative",
                                "width": 5,
                                "props": {
                                    "title": "Total Traffic",
                                    "icon": "chart line",
                                    "mobile": 16,
                                },
                            },
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {
                                "component": "TrafficStatsChartCumulative",
                                "width": 16,
                                "props": {
                                    "height": 300,
                                    "title": "Cumulative Traffic Totals",
                                    "maxSeries": 10,
                                    "display_subcounts": {
                                        "countries": {},
                                        # Disabled: referrers for usage events
                                        # "referrers": {},
                                        "file_presence": {},
                                        "resource_types": {},
                                        # Disabled: subjects for usage events
                                        # "subjects": {},
                                        "languages": {},
                                        "rights": {},
                                        "affiliations": {},
                                        # "funders": {},
                                        "periodicals": {},
                                        "publishers": {},
                                        "file_types": {},
                                        "access_statuses": {},
                                    },
                                },
                            },
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {
                                "component": "MostDownloadedRecordsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Most Downloaded Works",
                                    "pageSize": 6,
                                    "available_views": ["list"],
                                    "maxHeight": "300px",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "MostViewedRecordsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Most Viewed Works",
                                    "pageSize": 6,
                                    "available_views": ["list"],
                                    "maxHeight": "300px",
                                    "hideOtherInCharts": True,
                                },
                            },
                        ],
                    },
                    {
                        "name": "world-map",
                        "components": [
                            {
                                "component": "StatsMap",
                                "width": 16,
                                "props": {
                                    "title": "All Countries of Origin for Visits",
                                    "height": 400,
                                    "minHeight": 400,
                                    "zoom": 1.3,
                                    "center": [0, 20],
                                    "uniformColorMode": True,
                                },
                            },
                        ],
                    },
                    {
                        "name": "tables2",
                        "components": [
                            # {
                            #     "component": "CountriesMultiDisplayViews",
                            #     "width": 8,
                            #     "props": {
                            #         "title": "Top Countries by Visits",
                            #         "pageSize": 8,
                            #         "available_views": ["pie", "bar", "list"],
                            #         "default_view": "pie",
                            #         "hideOtherInCharts": True,
                            #     },
                            # },
                            # Disabled: referrers for usage events
                            # {
                            #     "component": "TopReferrersMultiDisplay",
                            #     "width": 8,
                            #     "props": {
                            #         "title": "Top Referrers by Visits",
                            #         "pageSize": 6,
                            #         "available_views": ["pie", "bar", "list"],
                            #         "default_view": "pie",
                            #         "hideOtherInCharts": True,
                            #     },
                            # },
                            {
                                "component": "FileTypesMultiDisplayDownloads",
                                "width": 8,
                                "props": {
                                    "title": "File Types Downloaded",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "LanguagesMultiDisplayViews",
                                "width": 8,
                                "props": {
                                    "title": "Top Languages Visited",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "ResourceTypesMultiDisplayViews",
                                "width": 8,
                                "props": {
                                    "title": "Top Work Types Visited",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "RightsMultiDisplayViews",
                                "width": 8,
                                "props": {
                                    "title": "Top Licenses by Visits",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "pie",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "PublishersMultiDisplayViews",
                                "width": 8,
                                "props": {
                                    "title": "Top Publishers by Visits",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                        ],
                    },
                ],
            },
            {
                "name": "usage",
                "label": _("Usage Rates"),
                "icon": "download",
                "date_range_phrase": _("Activity during"),
                "rows": [
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatViews",
                                "width": 5,
                                "props": {
                                    "title": "Record Views",
                                    "icon": "eye",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatDownloads",
                                "width": 6,
                                "props": {
                                    "title": "Record Downloads",
                                    "icon": "download",
                                    "mobile": 6,
                                },
                            },
                            {
                                "component": "SingleStatTraffic",
                                "width": 5,
                                "props": {
                                    "title": "Data Downloaded",
                                    "icon": "chart line",
                                    "mobile": 16,
                                },
                            },
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {
                                "component": "TrafficStatsChart",
                                "width": 16,
                                "props": {
                                    "height": 300,
                                    "title": "Usage Rates",
                                    "display_subcounts": {
                                        "countries": {},
                                        # Disabled: referrers for usage events
                                        # "referrers": {},
                                        "file_presence": {},
                                        "resource_types": {},
                                        # Disabled: subjects for usage events
                                        # "subjects": {},
                                        "languages": {},
                                        "rights": {},
                                        "affiliations": {},
                                        # "funders": {},
                                        "periodicals": {},
                                        "publishers": {},
                                        "file_types": {},
                                        "access_statuses": {},
                                    },
                                },
                            },
                        ],
                    },
                    {
                        "name": "world-map-delta",
                        "components": [
                            {
                                "component": "StatsMap",
                                "width": 16,
                                "props": {
                                    "title": "Top Countries of Origin for Visits",
                                    "height": 400,
                                    "minHeight": 400,
                                    "zoom": 1.3,
                                    "center": [0, 20],
                                    "useSnapshot": False,
                                    "uniformColorMode": True,
                                },
                            },
                        ],
                    },
                    {
                        "name": "tables2",
                        "components": [
                            # {
                            #     "component": "CountriesMultiDisplayViewsDelta",
                            #     "width": 8,
                            #     "props": {
                            #         "title": "Top Countries by Visits",
                            #         "pageSize": 10,
                            #         "available_views": ["pie", "bar", "list"],
                            #         "default_view": "pie",
                            #         "hideOtherInCharts": True,
                            #     },
                            # },
                            {
                                "component": "FileTypesMultiDisplayDownloadsDelta",
                                "width": 8,
                                "props": {
                                    "title": "File Types Downloaded",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "LanguagesMultiDisplayViewsDelta",
                                "width": 8,
                                "props": {
                                    "title": "Top Languages Visited",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "ResourceTypesMultiDisplayViewsDelta",
                                "width": 8,
                                "props": {
                                    "title": "Top Work Types Visited",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "RightsMultiDisplayViewsDelta",
                                "width": 8,
                                "props": {
                                    "title": "Top Licenses by Visits",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "pie",
                                    "hideOtherInCharts": True,
                                },
                            },
                            {
                                "component": "PublishersMultiDisplayViewsDelta",
                                "width": 8,
                                "props": {
                                    "title": "Top Publishers by Visits",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
                                    "hideOtherInCharts": True,
                                },
                            },
                        ],
                    },
                ],
            },
        ],
    },
}


COMMUNITY_STATS_QUERIES = {
    # "community-record-delta-created": {
    #     "cls": CommunityRecordDeltaResultsQuery,
    #     "permission_factory": CommunityStatsPermissionFactory,
    #     "params": {
    #         "index": "stats-community-records-delta-created",
    #         "doc_type": "community-record-delta-created-agg",
    #     },
    # },
    # "community-record-delta-published": {
    #     "cls": CommunityRecordDeltaResultsQuery,
    #     "permission_factory": CommunityStatsPermissionFactory,
    #     "params": {
    #         "index": "stats-community-records-delta-published",
    #         "doc_type": "community-record-delta-published-agg",
    #     },
    # },
    "community-record-delta-added": {
        "cls": CommunityRecordDeltaResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-delta",
            "doc_type": "community-record-delta-added-agg",
            "date_basis": "added",
        },
    },
    # "community-record-snapshot-created": {
    #     "cls": CommunityRecordSnapshotResultsQuery,
    #     "permission_factory": CommunityStatsPermissionFactory,
    #     "params": {
    #         "index": "stats-community-records-snapshot-created",
    #         "doc_type": "community-record-snapshot-created-agg",
    #     },
    # },
    "community-record-snapshot-added": {
        "cls": CommunityRecordSnapshotResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-snapshot",
            "doc_type": "community-record-snapshot-added-agg",
            "date_basis": "added",
        },
    },
    # "community-record-snapshot-published": {
    #     "cls": CommunityRecordSnapshotResultsQuery,
    #     "permission_factory": CommunityStatsPermissionFactory,
    #     "params": {
    #         "index": "stats-community-records-snapshot-published",
    #         "doc_type": "community-record-snapshot-published-agg",
    #     },
    # },
    "community-usage-delta": {
        "cls": CommunityUsageDeltaResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-usage-delta",
            "doc_type": "community-usage-delta-agg",
        },
    },
    "community-usage-snapshot": {
        "cls": CommunityUsageSnapshotResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-usage-snapshot",
            "doc_type": "community-usage-snapshot-agg",
        },
    },
    "community-stats": {
        "cls": CommunityStatsResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {  # These are actually not used
            "index": "stats-community-records-delta",
            "doc_type": "community-record-delta-added-agg",
            "date_basis": "added",
        },
    },
    "global-stats": {
        "cls": CommunityStatsResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {  # These are actually not used
            "index": "stats-community-records-delta",
            "doc_type": "community-record-delta-added-agg",
            "date_basis": "added",
        },
    },
    # Single data series queries
    "usage-snapshot-series": {
        "cls": UsageSnapshotDataSeriesQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-usage-snapshot",
            "doc_type": "community-usage-snapshot-agg",
        },
    },
    "usage-delta-series": {
        "cls": UsageDeltaDataSeriesQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-usage-delta",
            "doc_type": "community-usage-delta-agg",
        },
    },
    "record-snapshot-series": {
        "cls": RecordSnapshotDataSeriesQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-snapshot",
            "doc_type": "community-record-snapshot-agg",
        },
    },
    "record-delta-series": {
        "cls": RecordDeltaDataSeriesQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-delta",
            "doc_type": "community-record-delta-agg",
        },
    },
    # Category-wide queries
    "usage-snapshot-category": {
        "cls": UsageSnapshotCategoryQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-usage-snapshot",
            "doc_type": "community-usage-snapshot-agg",
        },
    },
    "usage-delta-category": {
        "cls": UsageDeltaCategoryQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-usage-delta",
            "doc_type": "community-usage-delta-agg",
        },
    },
    "record-snapshot-category": {
        "cls": RecordSnapshotCategoryQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-snapshot",
            "doc_type": "community-record-snapshot-agg",
        },
    },
    "record-delta-category": {
        "cls": RecordDeltaCategoryQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-delta",
            "doc_type": "community-record-delta-agg",
        },
    },
}

STATS_EVENTS = {
    "file-download": {
        "templates": (
            "invenio_stats_dashboard.search_indices.search_templates.file_download"
        ),
        "event_builders": [
            "invenio_stats_dashboard.search_indices.event_builders."
            "file_download_event_builder",
            "invenio_rdm_records.resources.stats.check_if_via_api",
        ],
        "cls": EventsIndexer,
        "params": {
            "preprocessors": [
                flag_robots,
                flag_machines,
                anonymize_user,
                build_file_unique_id,
            ],
        },
    },
    "record-view": {
        "templates": (
            "invenio_stats_dashboard.search_indices.search_templates.record_view"
        ),
        "event_builders": [
            "invenio_stats_dashboard.search_indices.event_builders."
            "record_view_event_builder",
            "invenio_rdm_records.resources.stats.check_if_via_api",
            "invenio_rdm_records.resources.stats.drop_if_via_api",
        ],
        "cls": EventsIndexer,
        "params": {
            "preprocessors": [
                flag_robots,
                flag_machines,
                anonymize_user,
                build_record_unique_id,
            ],
        },
    },
}

STATS_DASHBOARD_REINDEXING_MAX_BATCHES = 1000
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 5000
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 85

# Number of top records to collect for "top" type subcounts
COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT = 20


COMMUNITY_STATS_SUBCOUNTS = {
    "resource_types": {
        "records": {
            "delta_aggregation_name": "resource_types",
            "snapshot_type": "all",
            "source_fields": [
                {
                    "field": "metadata.resource_type.id",
                    "label_field": "metadata.resource_type.title",
                    "label_source_includes": [
                        "metadata.resource_type.title",
                        "metadata.resource_type.id",
                    ],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "resource_types",
            "field_type": dict[str, Any] | None,
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "snapshot_type": "all",
            "source_fields": [
                {
                    "field": "resource_type.id",
                    "label_field": "resource_type.title",
                    "label_source_includes": [
                        "resource_type.title",
                        "resource_type.id",
                    ],
                },
            ],
        },
    },
    "access_statuses": {
        "records": {
            "delta_aggregation_name": "access_statuses",
            "snapshot_type": "all",
            "source_fields": [
                {
                    "field": "access.status",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "access_statuses",
            "field_type": str | None,
            "event_field": "access_status",
            "extraction_path_for_event": "access.status",
            "snapshot_type": "all",
            "source_fields": [
                {
                    "field": "access_status",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
    },
    "languages": {
        "records": {
            "delta_aggregation_name": "languages",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "metadata.languages.id",
                    "label_field": "metadata.languages.title",
                    "label_source_includes": [
                        "metadata.languages.title",
                        "metadata.languages.id",
                    ],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "languages",
            "field_type": list[str] | None,
            "event_field": "languages",
            "extraction_path_for_event": "metadata.languages",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "languages.id",
                    "label_field": "languages.title",
                    "label_source_includes": ["languages.title", "languages.id"],
                },
            ],
        },
    },
    "subjects": {
        "records": {
            "delta_aggregation_name": "subjects",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "metadata.subjects.id",
                    "label_field": "metadata.subjects.subject",
                    "label_source_includes": [
                        "metadata.subjects.subject",
                        "metadata.subjects.scheme",
                        "metadata.subjects.id",
                    ],
                },
            ],
        },
        # Disabled: usage_events for subjects
        # "usage_events": {
        #     "delta_aggregation_name": "subjects",
        #     "field_type": list[str] | None,
        #     "event_field": "subjects",
        #     "extraction_path_for_event": "metadata.subjects",
        #     "snapshot_type": "top",
        #     "source_fields": [
        #         {
        #             "field": "subjects.id",
        #             "label_field": "subjects.subject",
        #             "label_source_includes": ["subjects.subject", "subjects.id"],
        #         },
        #     ],
        # },
        "usage_events": {},
    },
    "rights": {
        "records": {
            "delta_aggregation_name": "rights",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "metadata.rights.id",
                    "label_field": "metadata.rights.title",
                    "label_source_includes": [
                        "metadata.rights.title",
                        "metadata.rights.id",
                    ],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "rights",
            "field_type": list[str] | None,
            "event_field": "rights",
            "extraction_path_for_event": "metadata.rights",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "rights.id",
                    "label_field": "rights.title",
                    "label_source_includes": ["rights.title", "rights.id"],
                },
            ],
        },
    },
    "funders": {
        "records": {
            "delta_aggregation_name": "funders",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "metadata.funding.funder.id",
                    "label_field": "metadata.funding.funder.name.keyword",
                    "label_source_includes": [
                        "metadata.funding.funder.name.keyword",
                        "metadata.funding.funder.id",
                    ],
                    "combine_subfields": [
                        "metadata.funding.funder.id",
                        "metadata.funding.funder.name.keyword",
                    ],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "funders",
            "field_type": "list",
            "event_field": "funders",
            "extraction_path_for_event": lambda metadata: [
                item["funder"]
                for item in metadata.get("funding", [])
                if isinstance(item, dict) and "funder" in item
            ],
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "funders.id",
                    "label_field": "funders.name",
                    "label_source_includes": ["funders.id", "funders.name"],
                    "combine_subfields": [
                        "funders.id",
                        "funders.name",
                    ],
                },
            ],
        },
    },
    "periodicals": {
        "records": {
            "delta_aggregation_name": "periodicals",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "custom_fields.journal:journal.title.keyword",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "periodicals",
            "field_type": str | None,
            "event_field": "journal_title",
            "extraction_path_for_event": "custom_fields.journal:journal.title.keyword",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "journal_title",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
    },
    "publishers": {
        "records": {
            "delta_aggregation_name": "publishers",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "metadata.publisher.keyword",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "publishers",
            "field_type": str | None,
            "event_field": "publisher",
            "extraction_path_for_event": "metadata.publisher",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "publisher",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
    },
    "affiliations": {
        "records": {
            "delta_aggregation_name": "affiliations",
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "metadata.creators.affiliations.id",
                    "label_field": "metadata.creators.affiliations.name",
                    "label_source_includes": [
                        "metadata.creators.affiliations.name",
                        "metadata.creators.affiliations.id",
                    ],
                },
                {
                    "field": "metadata.contributors.affiliations.id",
                    "label_field": "metadata.contributors.affiliations.name",
                    "label_source_includes": [
                        "metadata.contributors.affiliations.name",
                        "metadata.contributors.affiliations.id",
                    ],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "affiliations",
            "field_type": list[str] | None,
            "event_field": "affiliations",
            "extraction_path_for_event": lambda metadata: [
                affiliation
                for item in metadata.get("creators", [])
                + metadata.get("contributors", [])
                if "affiliations" in item
                for affiliation in item["affiliations"]
            ],
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "affiliations.id",
                    "label_field": "affiliations.name",
                    "label_source_includes": ["affiliations.name", "affiliations.id"],
                },
            ],
        },
    },
    "countries": {
        "records": {},
        "usage_events": {
            "delta_aggregation_name": "countries",
            "field_type": str | None,
            "event_field": None,
            "snapshot_type": "top",
            "source_fields": [
                {
                    "field": "country",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
    },
    "referrers": {
        "records": {},
        # Disabled: usage_events for referrers
        # "usage_events": {
        #     "delta_aggregation_name": "referrers",
        #     "field_type": str | None,
        #     "event_field": None,
        #     "snapshot_type": "top",
        #     "source_fields": [
        #         {
        #             "field": "referrer",
        #             "label_field": None,
        #             "label_source_includes": [],
        #         },
        #     ],
        # },
        "usage_events": {},
    },
    "file_types": {
        "records": {
            "delta_aggregation_name": "file_types",
            "snapshot_type": "all",
            "with_files_only": True,
            "source_fields": [
                {
                    "field": "files.entries.ext",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "file_types",
            "field_type": list[str] | None,
            "event_field": "file_types",
            "extraction_path_for_event": lambda metadata: (
                metadata.get("files", {}).get("types", [])
                if metadata.get("files", {}).get("types", [])
                else [
                    item["ext"]
                    for item in metadata.get("files", {}).get("entries", [])
                    if "ext" in item
                ]
            ),
            "snapshot_type": "all",
            "source_fields": [
                {
                    "field": "file_types",
                    "label_field": None,
                    "label_source_includes": [],
                },
            ],
        },
    },
}

# JSON compression configuration
# When True: Frontend requests compressed JSON (application/json+gzip) from the API
# When False: Frontend requests plain JSON (application/json) and lets server
#   handle compression
# Set to False when server-level compression (nginx, Apache) is enabled to avoid
#   double compression
STATS_DASHBOARD_COMPRESS_JSON = False

# Client-side IndexedDB cache compression configuration
# When True: Cached data in IndexedDB is compressed using gzip (via pako library)
#   before storage, reducing storage requirements (typically 70-90% reduction)
# When False: Cached data is stored as JavaScript objects directly (no compression)
#   providing faster read/write operations without serialization or compression
#   overhead
STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED = False

# Content negotiation configuration for community stats API requests
COMMUNITY_STATS_SERIALIZERS = {
    "application/json": json_serializer_func,
    "application/json+br": brotli_json_serializer_func,
    "application/json+gzip": gzip_json_serializer_func,
    "text/csv": data_series_csv_serializer_func,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        data_series_excel_serializer_func
    ),
    "application/xml": data_series_xml_serializer_func,
}

# will default to instance cache url with unique db number
STATS_CACHE_REDIS_URL = None
STATS_CACHE_REDIS_DB = 7
STATS_CACHE_PREFIX = "stats_dashboard"
STATS_CACHE_DEFAULT_TTL = 365  # 1 year in days (allows age measurement)
STATS_CACHE_COMPRESSION_METHOD = "gzip"

STATS_AGG_REGISTRY_PREFIX = "stats_agg_registry"
STATS_AGG_REGISTRY_REDIS_DB = 8

STATS_DASHBOARD_COMPONENT_METRICS_REGISTRY = COMPONENT_METRICS_REGISTRY
"""Registry mapping UI components to their required metrics per subcount.

This registry serves as the single source of truth for which metrics
each component needs. When optimization is enabled, data series transformers
will only generate series for metrics used by the components listed in the
registry for the components in the current configured dashboard layout.
"""
