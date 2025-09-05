"""Configuration for Invenio Stats Dashboard."""

from typing import Any, Optional

from invenio_i18n import gettext as _
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

from .aggregations import register_aggregations
from .permissions import CommunityStatsPermissionFactory
from .queries import (
    CommunityRecordDeltaResultsQuery,
    CommunityRecordSnapshotResultsQuery,
    CommunityStatsResultsQuery,
    CommunityUsageDeltaResultsQuery,
    CommunityUsageSnapshotResultsQuery,
)
from .tasks import CommunityStatsAggregationTask

COMMUNITY_STATS_ENABLED = True
COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED = False

COMMUNITY_STATS_CELERYBEAT_SCHEDULE = {
    "stats-aggregate-community-record-stats": {
        **CommunityStatsAggregationTask,
    },
}

COMMUNITY_STATS_AGGREGATIONS = register_aggregations()

COMMUNITY_STATS_CATCHUP_INTERVAL = 365

STATS_DASHBOARD_UI_SUBCOUNTS = {
    "by_resource_types": {},
    "by_subjects": {},
    "by_languages": {},
    "by_rights": {},
    "by_funders": {},
    "by_periodicals": {},
    "by_publishers": {},
    "by_affiliations": {
        "combine": ["by_affiliations_creator", "by_affiliations_contributor"]
    },
    "by_countries": {},
    "by_referrers": {},
    "by_file_types": {},
    "by_access_statuses": {},
}

# Distributed lock configuration for aggregation tasks
STATS_DASHBOARD_LOCK_CONFIG = {
    "enabled": True,  # Enable/disable distributed locking
    "lock_timeout": 86400,  # Lock timeout in seconds (24 hours)
    "lock_name": "community_stats_aggregation",  # Lock name
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

STATS_DASHBOARD_USE_TEST_DATA = True
"""Enable or disable test data mode. When True, the dashboard will use sample data
instead of making API calls."""

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
                                    "display_subcounts": [
                                        "by_resource_types",
                                        "by_subjects",
                                        "by_languages",
                                        "by_rights",
                                    ],
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
                                "component": "SubjectsMultiDisplay",
                                "width": 8,
                                "props": {
                                    "title": "Top Subjects",
                                    "pageSize": 10,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "pie",
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
                                "component": "SingleStatViewsCumulative",
                                "width": 5,
                                "props": {"title": "Total Views", "icon": "eye"},
                            },
                            {
                                "component": "SingleStatDownloadsCumulative",
                                "width": 6,
                                "props": {
                                    "title": "Total Downloads",
                                    "icon": "download",
                                },
                            },
                            {
                                "component": "SingleStatTrafficCumulative",
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
                                "component": "TopReferrersMultiDisplay",
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
    "community-record-snapshot-created": {
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

STATS_EVENTS = {
    "file-download": {
        "templates": (
            "invenio_stats_dashboard.search_indices.search_templates.file_download"
        ),
        "event_builders": [
            "invenio_stats_dashboard.search_indices.event_builders.file_download_event_builder",
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
            "invenio_stats_dashboard.search_indices.event_builders.record_view_event_builder",
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
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 1000
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 75

# Number of top records to collect for "top" type subcounts
COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT = 20

COMMUNITY_STATS_SUBCOUNT_CONFIGS = {
    "by_resource_types": {
        "records": {
            "delta_aggregation_name": "by_resource_types",
            "field": "metadata.resource_type.id",
            "label_field": "metadata.resource_type.title",
            "label_source_includes": [
                "metadata.resource_type.title",
                "metadata.resource_type.id",
            ],
            "snapshot_type": "all",
        },
        "usage_events": {
            "delta_aggregation_name": "by_resource_types",
            "field": "resource_type.id",
            "field_type": Optional[dict[str, Any]],
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "label_field": "resource_type.title",
            "label_source_includes": ["resource_type.title", "resource_type.id"],
            "snapshot_type": "all",
        },
    },
    "by_access_statuses": {
        "records": {
            "delta_aggregation_name": "by_access_statuses",
            "field": "access.status",
            "label_field": None,
            "snapshot_type": "all",
        },
        "usage_events": {
            "delta_aggregation_name": "by_access_statuses",
            "field": "access_status",
            "field_type": Optional[str],
            "event_field": "access_status",
            "extraction_path_for_event": "access.status",
            "label_field": None,
            "snapshot_type": "all",
        },
    },
    "by_languages": {
        "records": {
            "delta_aggregation_name": "by_languages",
            "field": "metadata.languages.id",
            "label_field": "metadata.languages.title",
            "label_source_includes": [
                "metadata.languages.title",
                "metadata.languages.id",
            ],
            "snapshot_type": "top",
        },
        "usage_events": {
            "delta_aggregation_name": "by_languages",
            "field": "languages.id",
            "field_type": Optional[list[str]],
            "event_field": "languages",
            "extraction_path_for_event": "metadata.languages",
            "label_field": "languages.title",
            "label_source_includes": ["languages.title", "languages.id"],
            "snapshot_type": "top",
        },
    },
    "by_subjects": {
        "records": {
            "delta_aggregation_name": "by_subjects",
            "field": "metadata.subjects.id",
            "label_field": "metadata.subjects.subject",
            "label_source_includes": [
                "metadata.subjects.subject",
                "metadata.subjects.scheme",
                "metadata.subjects.id",
            ],
            "snapshot_type": "top",
        },
        "usage_events": {
            "delta_aggregation_name": "by_subjects",
            "field": "subjects.id",
            "field_type": Optional[list[str]],
            "event_field": "subjects",
            "extraction_path_for_event": "metadata.subjects",
            "label_field": "subjects.subject",
            "label_source_includes": ["subjects.subject", "subjects.id"],
            "snapshot_type": "top",
        },
    },
    "by_rights": {
        "records": {
            "delta_aggregation_name": "by_rights",
            "field": "metadata.rights.id",
            "label_field": "metadata.rights.title",
            "label_source_includes": ["metadata.rights.title", "metadata.rights.id"],
            "snapshot_type": "top",
        },
        "usage_events": {
            "delta_aggregation_name": "by_rights",
            "field": "rights.id",
            "field_type": Optional[list[str]],
            "event_field": "rights",
            "extraction_path_for_event": "metadata.rights",
            "label_field": "rights.title",
            "label_source_includes": ["rights.title", "rights.id"],
            "snapshot_type": "top",
        },
    },
    "by_funders": {
        "records": {
            "delta_aggregation_name": "by_funders",
            "field": "metadata.funding.funder.id",
            "label_field": "metadata.funding.funder.name.keyword",
            "label_source_includes": [
                "metadata.funding.funder.name.keyword",
                "metadata.funding.funder.id",
            ],
            "combine_queries": [
                "metadata.funding.funder.id",
                "metadata.funding.funder.name.keyword",
            ],
            "snapshot_type": "top",
        },
        "usage_events": {
            "delta_aggregation_name": "by_funders",
            "field": "funders.id",
            "field_type": "list",
            "event_field": "funders",
            "extraction_path_for_event": lambda metadata: [
                item["funder"]
                for item in metadata.get("funding", [])
                if isinstance(item, dict) and "funder" in item
            ],
            "label_field": "funders.name",
            "combine_queries": ["funders.id", "funders.name"],
            "label_source_includes": ["funders.id", "funders.name"],
            "snapshot_type": "top",
        },
    },
    "by_periodicals": {
        "records": {
            "delta_aggregation_name": "by_periodicals",
            "field": "custom_fields.journal:journal.title.keyword",
            "label_field": None,
            "snapshot_type": "top",
        },
        "usage_events": {
            "delta_aggregation_name": "by_periodicals",
            "field": "journal_title",
            "field_type": Optional[str],
            "event_field": "journal_title",
            "extraction_path_for_event": "custom_fields.journal:journal.title.keyword",
            "label_field": None,
            "snapshot_type": "top",
        },
    },
    "by_publishers": {
        "records": {
            "delta_aggregation_name": "by_publishers",
            "field": "metadata.publisher.keyword",
            "label_field": None,
            "snapshot_type": "top",
        },
        "usage_events": {
            "delta_aggregation_name": "by_publishers",
            "field": "publisher",
            "field_type": Optional[str],
            "event_field": "publisher",
            "extraction_path_for_event": "metadata.publisher",
            "label_field": None,
            "snapshot_type": "top",
        },
    },
    "by_affiliations_creator": {
        "records": {
            "delta_aggregation_name": "by_affiliations_creator",
            "field": "metadata.creators.affiliations.id",
            "label_field": "metadata.creators.affiliations.name.keyword",
            "label_source_includes": [
                "metadata.creators.affiliations.name.keyword",
                "metadata.creators.affiliations.id",
            ],
            "snapshot_type": "top",
            "combine_queries": [
                "metadata.creators.affiliations.id",
                "metadata.creators.affiliations.name.keyword",
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "by_affiliations_creator",
            "field": "affiliations.id",
            "field_type": Optional[list[str]],
            "event_field": "affiliations",
            "extraction_path_for_event": lambda metadata: [
                item["affiliations"]
                for item in metadata.get("creators", [])
                + metadata.get("contributors", [])
                if "affiliations" in item
            ],
            "label_field": "affiliations.name",
            "combine_queries": ["affiliations.id", "affiliations.name"],
            "label_source_includes": ["affiliations.name", "affiliations.id"],
            "snapshot_type": "top",
        },
    },
    "by_affiliations_contributor": {
        "records": {
            "delta_aggregation_name": "by_affiliations_contributor",
            "field": "metadata.contributors.affiliations.id",
            "label_field": "metadata.contributors.affiliations.name.keyword",
            "label_source_includes": [
                "metadata.contributors.affiliations.name.keyword",
                "metadata.contributors.affiliations.id",
            ],
            "snapshot_type": "top",
            "combine_queries": [
                "metadata.contributors.affiliations.id",
                "metadata.contributors.affiliations.name.keyword",
            ],
        },
        "usage_events": {
            "delta_aggregation_name": "by_affiliations_contributor",
            "field": "affiliations.id",
            "field_type": Optional[list[str]],
            "event_field": "affiliations",
            "extraction_path_for_event": lambda metadata: [
                item["affiliations"]
                for item in metadata.get("contributors", [])
                if "affiliations" in item
            ],
            "label_field": "affiliations.name",
            "label_source_includes": ["affiliations.name", "affiliations.id"],
            "snapshot_type": "top",
        },
    },
    "by_countries": {
        "records": {},
        "usage_events": {
            "delta_aggregation_name": "by_countries",
            "field": "country",
            "field_type": Optional[str],
            "event_field": None,
            "label_field": None,
            "snapshot_type": "top",
        },
    },
    "by_referrers": {
        "records": {},
        "usage_events": {
            "delta_aggregation_name": "by_referrers",
            "field": "referrer",
            "field_type": Optional[str],
            "event_field": None,
            "label_field": None,
            "snapshot_type": "top",
        },
    },
    "by_file_types": {
        "records": {
            "delta_aggregation_name": "by_file_types",
            "field": "files.entries.ext",
            "label_field": None,
            "snapshot_type": "all",
            "with_files_only": True,
        },
        "usage_events": {
            "delta_aggregation_name": "by_file_types",
            "field": "file_types",
            "field_type": Optional[list[str]],
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
            "label_field": None,
            "snapshot_type": "all",
        },
    },
}
