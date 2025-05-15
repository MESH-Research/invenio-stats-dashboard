from invenio_search.proxies import current_search_client
from opensearchpy import OpenSearch
from datetime import datetime


def get_record_counts_for_periods(start_date, end_date, search_domain=None):
    """Query opensearch for record counts for each time period.

    Note: Returns a dictionary with the following structure:
    {
        "by_year": [
            {"key_as_string": "2024", "key": 17207424000000, "doc_count": 100},
            {"key_as_string": "2025", "key": 17513952000000, "doc_count": 200}
        ],
        "by_month": [...],
        "by_week": [...],
        "by_day": [...]
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

    # Initial search query
    search_body = {
        "size": 1000,  # Process 1000 documents at a time
        "query": {
            "range": {
                "created": {"gte": start_date, "lte": end_date, "format": "yyyy-MM-dd"}
            }
        },
        "aggs": {
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
        },
    }

    # Initialize combined aggregations
    combined_aggs = {"by_year": [], "by_month": [], "by_week": [], "by_day": []}

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
    for agg_type in ["by_year", "by_month", "by_week", "by_day"]:
        combined_aggs[agg_type] = merge_buckets(
            combined_aggs[agg_type], response["aggregations"][agg_type]["buckets"]
        )

    # Process remaining hits using scroll
    while True:
        scroll_response = client.scroll(scroll_id=scroll_id, scroll="5m")

        # Break if no more hits
        if not scroll_response["hits"]["hits"]:
            break

        # Merge aggregations from this batch
        for agg_type in ["by_year", "by_month", "by_week", "by_day"]:
            combined_aggs[agg_type] = merge_buckets(
                combined_aggs[agg_type],
                scroll_response["aggregations"][agg_type]["buckets"],
            )

        # Update scroll_id for next iteration
        scroll_id = scroll_response["_scroll_id"]

    # Clean up the scroll context
    client.clear_scroll(scroll_id=scroll_id)

    return combined_aggs


def get_records_created_as_of_dates(start_date, end_date):
    # Get aggregation data from helper function
    aggs = get_record_counts_for_periods(start_date, end_date)

    # Extract daily buckets
    buckets = aggs["by_day"]

    # Calculate cumulative totals
    daily_totals = {}
    cumulative = 0
    for bucket in buckets:
        date = bucket["key_as_string"]
        count = bucket["doc_count"]
        cumulative += count
        daily_totals[date] = cumulative

    # Helper functions to get last day of week, month, year
    def is_last_of_period(date_str, period):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if period == "week":
            # ISO week: Sunday is the last day (weekday() == 6)
            return date.weekday() == 6
        elif period == "month":
            from calendar import monthrange

            return date.day == monthrange(date.year, date.month)[1]
        elif period == "year":
            return date.month == 12 and date.day == 31
        return False

    weekly_totals = {}
    monthly_totals = {}
    yearly_totals = {}

    for date, total in daily_totals.items():
        if is_last_of_period(date, "week"):
            weekly_totals[date] = total
        if is_last_of_period(date, "month"):
            monthly_totals[date] = total
        if is_last_of_period(date, "year"):
            yearly_totals[date] = total

    return {
        "daily_totals": daily_totals,
        "weekly_totals": weekly_totals,
        "monthly_totals": monthly_totals,
        "yearly_totals": yearly_totals,
    }


def do_get_record_counts(start_date, end_date):
    # Example usage
    start_date = start_date or "2024-01-01"
    end_date = end_date or "2024-12-31"

    try:
        results = get_records_created_as_of_dates(start_date, end_date)

        # Print the results in a readable format
        print("\nAggregations by time period:")
        print("\nBy Year:")
        for bucket in results["by_year"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

        print("\nBy Month:")
        for bucket in results["by_month"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

        print("\nBy Week:")
        for bucket in results["by_week"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

        print("\nBy Day:")
        for bucket in results["by_day"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
