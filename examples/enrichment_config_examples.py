"""Example configurations for configurable event enrichment.

This file demonstrates different ways to configure the event enrichment system
by modifying the existing COMMUNITY_STATS_SUBCOUNT_CONFIGS.
"""

from typing import Optional, Any

# Example 1: Enable all enrichment fields (default configuration)
SUBCOUNT_CONFIG_ALL_ENABLED = {
    "by_resource_types": {
        "usage_events": {
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "field_type": "dict",
        }
    },
    "by_subjects": {
        "usage_events": {
            "event_field": "subjects",
            "extraction_path_for_event": "metadata.subjects",
            "field_type": "list",
        }
    },
    "by_languages": {
        "usage_events": {
            "event_field": "languages",
            "extraction_path_for_event": "metadata.languages",
            "field_type": "list",
        }
    },
    "by_rights": {
        "usage_events": {
            "event_field": "rights",
            "extraction_path_for_event": "metadata.rights",
            "field_type": "list",
        }
    },
    "by_funders": {
        "usage_events": {
            "event_field": "funders",
            "extraction_path_for_event": lambda metadata: [
                item["funder"]
                for item in metadata.get("funding", [])
                if isinstance(item, dict) and "funder" in item
            ],
            "field_type": "list",
        }
    },
    "by_periodicals": {
        "usage_events": {
            "event_field": "journal_title",
            "extraction_path_for_event": "custom_fields.journal:journal.title.keyword",
            "field_type": "str",
        }
    },
    "by_affiliations": {
        "usage_events": {
            "event_field": "affiliations",
            "extraction_path_for_event": lambda metadata: [
                item["affiliations"]
                for item in metadata.get("creators", [])
                + metadata.get("contributors", [])
                if "affiliations" in item
            ],
            "field_type": "list",
        }
    },
    "by_file_types": {
        "usage_events": {
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
            "field_type": "list",
        }
    },
    "by_publishers": {
        "usage_events": {
            "event_field": "publisher",
            "extraction_path_for_event": "metadata.publisher",
            "field_type": "str",
        }
    },
    "by_access_statuses": {
        "usage_events": {
            "event_field": "access_status",
            "extraction_path_for_event": "access.status",
            "field_type": "str",
        }
    },
}
