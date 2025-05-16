"""Configuration for Invenio Stats Dashboard."""

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
        "title": "Statistics Dashboard",
        "description": "This is the global stats dashboard.",
        "maxHistoryYears": 15,
    },
    "community": {
        "title": "Community Statistics Dashboard",
        "description": "This is the community stats dashboard.",
        "maxHistoryYears": 15,
    },
}

STATS_DASHBOARD_LAYOUT = {
    "global": {
        "tabs": [
            {
                "name": "content",
                "label": "Content",
                "rows": [
                    {
                        "name": "date-range-selector",
                        "components": [
                            {
                                "component": "DateRangeSelector",
                                "width": 16,
                                "props": {
                                    "maxHistoryYears": 15,
                                    "defaultRange": "last30days",
                                },
                            },
                        ],
                    },
                    {
                        "name": "single-stats",
                        "components": [
                            {
                                "component": "SingleStatRecordCount",
                                "width": 5,
                                "props": {"title": "Total Records", "icon": "file"},
                            },
                            {
                                "component": "SingleStatUploaders",
                                "width": 6,
                                "props": {"title": "Total Uploaders", "icon": "users"},
                            },
                            {
                                "component": "SingleStatDataVolume",
                                "width": 5,
                                "props": {"title": "Data Volume", "icon": "database"},
                            },
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {
                                "component": "ContentStatsChart",
                                "width": 16,
                                "props": {"title": "Content Statistics", "height": 400},
                            },
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {
                                "component": "ResourceTypesTable",
                                "width": 8,
                                "props": {"title": "Resource Types", "pageSize": 10},
                            },
                            {
                                "component": "AccessRightsTable",
                                "width": 8,
                                "props": {"title": "Access Rights", "pageSize": 10},
                            },
                            {
                                "component": "LicensesTable",
                                "width": 8,
                                "props": {"title": "Licenses", "pageSize": 10},
                            },
                            {
                                "component": "AffiliationsTable",
                                "width": 8,
                                "props": {"title": "Affiliations", "pageSize": 10},
                            },
                            {
                                "component": "FundersTable",
                                "width": 8,
                                "props": {"title": "Funders", "pageSize": 10},
                            },
                        ],
                    },
                ],
            },
            {
                "name": "traffic",
                "label": "Traffic",
                "rows": [
                    {
                        "name": "date-range-selector",
                        "components": [
                            {
                                "component": "DateRangeSelector",
                                "width": 16,
                                "props": {
                                    "maxHistoryYears": 15,
                                    "defaultRange": "last30days",
                                },
                            },
                        ],
                    },
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
                                "component": "TrafficStatsChart",
                                "width": 16,
                                "props": {"title": "Traffic Statistics", "height": 400},
                            },
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {
                                "component": "MostDownloadedRecordsTable",
                                "width": 8,
                                "props": {
                                    "title": "Most Downloaded Records",
                                    "pageSize": 10,
                                },
                            },
                            {
                                "component": "MostViewedRecordsTable",
                                "width": 8,
                                "props": {
                                    "title": "Most Viewed Records",
                                    "pageSize": 10,
                                },
                            },
                            {
                                "component": "TopCountriesTable",
                                "width": 8,
                                "props": {"title": "Top Countries", "pageSize": 10},
                            },
                            {
                                "component": "TopReferrerDomainsTable",
                                "width": 8,
                                "props": {
                                    "title": "Top Referrer Domains",
                                    "pageSize": 10,
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
                                    "title": "World Map of Site Visits",
                                    "height": 500,
                                    "minHeight": 400,
                                },
                            },
                        ],
                    },
                ],
            },
        ],
    },
}
