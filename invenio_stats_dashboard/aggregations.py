from collections import defaultdict

from invenio_search.proxies import current_search_client
from opensearchpy import OpenSearch
from invenio_stats.aggregations import StatAggregator


def register_aggregations():
    return {
        "community-records-snapshot-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_snapshot"
            ),
            "cls": CommunityRecordsSnapshotAggregator,
            "params": {
                "client": current_search_client,
                "event": None,
                "aggregation_field": None,
                "aggregation_interval": "day",
                "copy_fields": {
                    "file_key": "file_key",
                    "bucket_id": "bucket_id",
                    "file_id": "file_id",
                },
            },
        },
        "community-records-delta-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_records_delta"
            ),
            "cls": CommunityRecordsDeltaAggregator,
            "params": {
                "client": current_search_client,
                "event": "",
                "aggregation_field": "unique_id",
                "aggregation_interval": "day",
                "copy_fields": {
                    "file_key": "file_key",
                    "bucket_id": "bucket_id",
                    "file_id": "file_id",
                },
            },
        },
        "community-usage-snapshot-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_usage_snapshot"
            ),
            "cls": CommunityUsageSnapshotAggregator,
            "params": {
                "client": current_search_client,
                "event": "",
                "aggregation_field": "unique_id",
                "aggregation_interval": "day",
                "copy_fields": {
                    "file_key": "file_key",
                    "bucket_id": "bucket_id",
                    "file_id": "file_id",
                },
            },
        },
        "community-usage-delta-agg": {
            "templates": (
                "invenio_stats_dashboard.search_indices.search_templates."
                "stats_community_usage_delta"
            ),
            "cls": CommunityUsageDeltaAggregator,
            "params": {
                "client": current_search_client,
                "event": "",
            },
        },
    }


class CommunityRecordsSnapshotAggregator(StatAggregator):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = None
        self.aggregation_field = None
        self.aggregation_interval = "day"
        self.copy_fields = {
            "file_key": "file_key",
            "bucket_id": "bucket_id",
            "file_id": "file_id",
        }


class CommunityRecordsDeltaAggregator(StatAggregator):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = ""
        self.aggregation_field = "unique_id"
        self.aggregation_interval = "day"
        self.copy_fields = {
            "file_key": "file_key",
            "bucket_id": "bucket_id",
            "file_id": "file_id",
        }


class CommunityUsageSnapshotAggregator(StatAggregator):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = ""
        self.aggregation_field = "unique_id"
        self.aggregation_interval = "day"
        self.copy_fields = {
            "file_key": "file_key",
            "bucket_id": "bucket_id",
            "file_id": "file_id",
        }


class CommunityUsageDeltaAggregator(StatAggregator):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = ""
        self.aggregation_field = "unique_id"
        self.aggregation_interval = "day"
        self.copy_fields = {
            "file_key": "file_key",
            "bucket_id": "bucket_id",
            "file_id": "file_id",
        }


def get_records_created_for_periods(start_date, end_date, search_domain=None):
    """Query opensearch for record counts for each time period.

    Note: Returns a dictionary with the following structure:
    {
        "by_year": [
            {"key_as_string": "2024", "key": 17207424000000, "doc_count": 100},
            {"key_as_string": "2025", "key": 17513952000000, "doc_count": 200}
        ],
        "by_month": [...],
        "by_week": [...],
        "by_day": [...],
        "by_community": {
            "community_id_1": {
                "by_year": [...],
                "by_month": [...],
                "by_week": [...],
                "by_day": [...]
            },
            "community_id_2": {
                ...
            }
        }
    }
    The "key_as_string" is the date in human readable format, and "key" is the date
    in epoch time.

    The "by_day" keys are formatted like "2024-01-01" (year-month-day).
    The "by_week" keys are formatted like "2024-W01" where "01" is the week number.
    The "by_month" keys are formatted like "2024-01" where "01" is the month number.
    The "by_year" keys are formatted like "2024" where "2024" is the year.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        search_domain (str, optional): The search domain to use. If provided,
            creates a new client instance. If None, uses the default
            current_search_client.

    Returns:
        dict: A dictionary containing lists of buckets for each time period.
    """
    # Create client instance if search_domain is provided
    if search_domain:
        client = OpenSearch(
            hosts=[{"host": search_domain, "port": 443}],
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=True,
            verify_certs=True,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
    else:
        client = current_search_client

    # Helper function to create date histogram aggregations
    def create_date_histogram_aggs():
        return {
            "by_year": {
                "date_histogram": {
                    "field": "created",
                    "calendar_interval": "year",
                    "format": "yyyy",
                }
            },
            "by_month": {
                "date_histogram": {
                    "field": "created",
                    "calendar_interval": "month",
                    "format": "yyyy-MM",
                }
            },
            "by_week": {
                "date_histogram": {
                    "field": "created",
                    "calendar_interval": "week",
                    "format": "yyyy-'W'ww",
                }
            },
            "by_day": {
                "date_histogram": {
                    "field": "created",
                    "calendar_interval": "day",
                    "format": "yyyy-MM-dd",
                }
            },
        }

    # Initial search query
    search_body = {
        "size": 10000,  # Process 10000 documents at a time
        "query": {
            "range": {
                "created": {"gte": start_date, "lte": end_date, "format": "yyyy-MM-dd"}
            }
        },
        "aggs": {
            # Global aggregations
            **create_date_histogram_aggs(),
            # Community-specific aggregations
            "by_community": {
                "nested": {"path": "parent.communities.entries"},
                "aggs": {
                    "community_ids": {
                        "terms": {
                            "field": "parent.communities.entries.id",
                            "size": (
                                1000  # Adjust based on expected number of communities
                            ),
                        },
                        "aggs": create_date_histogram_aggs(),
                    }
                },
            },
        },
    }

    # Initialize combined aggregations using defaultdict
    def create_agg_dict():
        return defaultdict(list)

    combined_aggs = {
        "by_year": [],
        "by_month": [],
        "by_week": [],
        "by_day": [],
        "by_community": defaultdict(
            lambda: {"by_year": [], "by_month": [], "by_week": [], "by_day": []}
        ),
    }

    # Helper function to merge buckets
    def merge_buckets(existing_buckets, new_buckets):
        bucket_dict = {b["key_as_string"]: b for b in existing_buckets}
        for bucket in new_buckets:
            key = bucket["key_as_string"]
            if key in bucket_dict:
                bucket_dict[key]["doc_count"] += bucket["doc_count"]
            else:
                bucket_dict[key] = bucket
        return sorted(bucket_dict.values(), key=lambda x: x["key_as_string"])

    # Initial search with scroll
    response = client.search(
        index="kcworks-rdmrecords-records", body=search_body, scroll="5m"
    )

    # Store the scroll ID
    scroll_id = response["_scroll_id"]

    # Process initial batch
    # Global aggregations
    for agg_type in ["by_year", "by_month", "by_week", "by_day"]:
        combined_aggs[agg_type] = merge_buckets(
            combined_aggs[agg_type], response["aggregations"][agg_type]["buckets"]
        )

    # Community aggregations
    for community_bucket in response["aggregations"]["by_community"]["community_ids"][
        "buckets"
    ]:
        community_id = community_bucket["key"]
        for agg_type in ["by_year", "by_month", "by_week", "by_day"]:
            combined_aggs["by_community"][community_id][agg_type] = merge_buckets(
                combined_aggs["by_community"][community_id][agg_type],
                community_bucket[agg_type]["buckets"],
            )

    # Process remaining hits using scroll
    while True:
        scroll_response = client.scroll(scroll_id=scroll_id, scroll="5m")

        # Break if no more hits
        if not scroll_response["hits"]["hits"]:
            break

        # Global aggregations
        for agg_type in ["by_year", "by_month", "by_week", "by_day"]:
            combined_aggs[agg_type] = merge_buckets(
                combined_aggs[agg_type],
                scroll_response["aggregations"][agg_type]["buckets"],
            )

        # Community aggregations
        for community_bucket in scroll_response["aggregations"]["by_community"][
            "community_ids"
        ]["buckets"]:
            community_id = community_bucket["key"]
            for agg_type in ["by_year", "by_month", "by_week", "by_day"]:
                combined_aggs["by_community"][community_id][agg_type] = merge_buckets(
                    combined_aggs["by_community"][community_id][agg_type],
                    community_bucket[agg_type]["buckets"],
                )

        # Update scroll_id for next iteration
        scroll_id = scroll_response["_scroll_id"]

    # Clean up the scroll context
    client.clear_scroll(scroll_id=scroll_id)

    # Convert defaultdict to regular dict for final output
    result = dict(combined_aggs)
    result["by_community"] = {k: dict(v) for k, v in result["by_community"].items()}

    return result


def get_record_totals_as_of_dates(start_date, end_date, search_domain=None):
    """Calculate cumulative totals of records as of each date in the period.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        search_domain (str, optional): The search domain to use. If provided,
            creates a new client instance. If None, uses the default
            current_search_client.

    Returns:
        dict: A dictionary containing cumulative totals with the following structure:
        {
            "daily_totals": {
                "2024-01-01": 100,
                "2024-01-02": 150,
                ...
            },
            "by_community": {
                "community_id_1": {
                    "daily_totals": {
                        "2024-01-01": 50,
                        "2024-01-02": 75,
                        ...
                    }
                },
                "community_id_2": {
                    "daily_totals": {
                        "2024-01-01": 30,
                        "2024-01-02": 45,
                        ...
                    }
                }
            }
        }
    """
    # Get aggregation data from helper function
    aggs = get_records_created_for_periods(start_date, end_date, search_domain)

    # Initialize result structure
    result = {
        "daily_totals": {},
        "by_community": defaultdict(lambda: {"daily_totals": {}}),
    }

    # Process global daily totals
    cumulative = 0
    for bucket in aggs["by_day"]:
        date = bucket["key_as_string"]
        count = bucket["doc_count"]
        cumulative += count
        result["daily_totals"][date] = cumulative

    # Process community-specific daily totals
    for community_id, community_aggs in aggs["by_community"].items():
        cumulative = 0
        for bucket in community_aggs["by_day"]:
            date = bucket["key_as_string"]
            count = bucket["doc_count"]
            cumulative += count
            result["by_community"][community_id]["daily_totals"][date] = cumulative

    # Convert defaultdict to regular dict for final output
    result["by_community"] = {k: dict(v) for k, v in result["by_community"].items()}

    return result


def do_get_record_counts(start_date, end_date):
    # Example usage
    start_date = start_date or "2024-01-01"
    end_date = end_date or "2024-12-31"

    try:
        results = get_record_totals_as_of_dates(start_date, end_date)

        # Print the results in a readable format
        print("\nDaily Totals:")
        for date, total in sorted(results["daily_totals"].items()):
            print(f"{date}: {total}")

        print("\nCommunity-specific Daily Totals:")
        for community_id, community_data in sorted(results["by_community"].items()):
            print(f"\nCommunity {community_id}:")
            for date, total in sorted(community_data["daily_totals"].items()):
                print(f"  {date}: {total}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
