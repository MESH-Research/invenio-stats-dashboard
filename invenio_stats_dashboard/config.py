"""Configuration for Invenio Stats Dashboard."""

from invenio_i18n import gettext as _

from .aggregations import register_aggregations
from .queries import (
    CommunityRecordDeltaResultsQuery,
    CommunityRecordSnapshotResultsQuery,
    CommunityUsageDeltaResultsQuery,
    CommunityUsageSnapshotResultsQuery,
    CommunityStatsResultsQuery,
)
from .permissions import CommunityStatsPermissionFactory
from .tasks import CommunityStatsAggregationTask

COMMUNITY_STATS_CELERYBEAT_SCHEDULE = {
    "stats-aggregate-community-record-stats": {
        **CommunityStatsAggregationTask,
    },
}

COMMUNITY_STATS_AGGREGATIONS = register_aggregations()

COMMUNITY_STATS_CATCHUP_INTERVAL = 365

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

STATS_DASHBOARD_UI_CONFIG = {
    "global": {
        "title": _("Statistics"),
        "description": _("This is the global stats dashboard."),
        "maxHistoryYears": 15,
        "default_granularity": "month",
        "show_title": True,
        "show_description": False,
    },
    "community": {
        "title": _("Statistics"),
        "description": _("This is the community stats dashboard."),
        "maxHistoryYears": 15,
        "default_granularity": "month",
        "show_title": True,
        "show_description": False,
    },
}

STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS = {
    "day": "30days",
    "week": "12weeks",
    "month": "12months",
    "quarter": "4quarters",
    "year": "5years",
}

STATS_DASHBOARD_LAYOUT = {
    "global": {
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
                                "props": {"title": "Total Records", "icon": "file"},
                            },
                            {
                                "component": "SingleStatUploadersCumulative",
                                "width": 6,
                                "props": {"title": "Total Uploaders", "icon": "users"},
                            },
                            {
                                "component": "SingleStatDataVolumeCumulative",
                                "width": 5,
                                "props": {
                                    "title": "Total Data Volume",
                                    "icon": "database",
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
                                },
                            },
                            {
                                "component": "AccessRightsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Access Rights",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                },
                            },
                            {
                                "component": "LicensesMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Licenses",
                                    "pageSize": 10,
                                    "available_views": ["pie", "list"],
                                    "default_view": "list",
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
                                },
                            },
                            {
                                "component": "FundersMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Funders",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "list",
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
                                "props": {"title": "New Records", "icon": "file"},
                            },
                            {
                                "component": "SingleStatUploaders",
                                "width": 6,
                                "props": {"title": "Active Uploaders", "icon": "users"},
                            },
                            {
                                "component": "SingleStatDataVolume",
                                "width": 5,
                                "props": {
                                    "title": "New Data Uploaded",
                                    "icon": "database",
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
                                },
                            },
                        ],
                    },
                ],
            },
            {
                "name": "traffic",
                "label": _("Traffic"),
                "date_range_phrase": _("Cumulative totals as of"),
                "icon": "world",
                "rows": [
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatViews",
                                "width": 5,
                                "props": {"title": "Total Views", "icon": "eye"},
                            },
                            {
                                "component": "SingleStatDownloads",
                                "width": 6,
                                "props": {
                                    "title": "Total Downloads",
                                    "icon": "download",
                                },
                            },
                            {
                                "component": "SingleStatTraffic",
                                "width": 5,
                                "props": {
                                    "title": "Total Traffic",
                                    "icon": "chart line",
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
                                },
                            },
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {
                                "component": "TopCountriesMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Countries",
                                    "pageSize": 6,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "bar",
                                },
                            },
                            {
                                "component": "TopReferrerDomainsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Referrer Domains",
                                    "pageSize": 6,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "pie",
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
                                    "title": "Top Countries by Visits",
                                    "height": 400,
                                    "minHeight": 400,
                                    "zoom": 1.3,
                                    "center": [0, 20],
                                },
                            },
                        ],
                    },
                ],
            },
            {
                "name": "usage",
                "label": _("Usage"),
                "icon": "download",
                "date_range_phrase": _("Activity during"),
                "rows": [
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatViews",
                                "width": 5,
                                "props": {"title": "Record Views", "icon": "eye"},
                            },
                            {
                                "component": "SingleStatDownloads",
                                "width": 6,
                                "props": {
                                    "title": "Record Downloads",
                                    "icon": "download",
                                },
                            },
                            {
                                "component": "SingleStatTraffic",
                                "width": 5,
                                "props": {
                                    "title": "Data Downloaded",
                                    "icon": "chart line",
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
                                },
                            },
                            {
                                "component": "MostViewedRecordsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Most Viewed Works",
                                    "pageSize": 6,
                                    "available_views": ["list"],
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
    "community-record-delta-created": {
        "cls": CommunityRecordDeltaResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-delta-created",
            "doc_type": "community-record-delta-created-agg",
        },
    },
    "community-record-delta-published": {
        "cls": CommunityRecordDeltaResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-delta-published",
            "doc_type": "community-record-delta-published-agg",
        },
    },
    "community-record-delta-added": {
        "cls": CommunityRecordDeltaResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-delta-added",
            "doc_type": "community-record-delta-added-agg",
        },
    },
    "community-record-snapshot": {
        "cls": CommunityRecordSnapshotResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-snapshot-created",
            "doc_type": "community-record-snapshot-created-agg",
        },
    },
    "community-record-snapshot-added": {
        "cls": CommunityRecordSnapshotResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-snapshot-added",
            "doc_type": "community-record-snapshot-added-agg",
        },
    },
    "community-record-snapshot-published": {
        "cls": CommunityRecordSnapshotResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {
            "index": "stats-community-records-snapshot-published",
            "doc_type": "community-record-snapshot-published-agg",
        },
    },
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
            "doc_type": "community-record-delta-agg",
        },
    },
    "global-stats": {
        "cls": CommunityStatsResultsQuery,
        "permission_factory": CommunityStatsPermissionFactory,
        "params": {  # These are actually not used
            "index": "stats-community-records-delta",
            "doc_type": "community-record-delta-agg",
        },
    },
}
