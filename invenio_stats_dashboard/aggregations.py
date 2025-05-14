from invenio_search.proxies import current_search_client as client
from datetime import datetime


def get_record_counts_for_periods(start_date, end_date):
    # Initial search query
    search_body = {
        "size": 1000,
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

    # Initial search with scroll
    response = client.search(
        index="kcworks-rdmrecord-records", body=search_body, scroll="5m"
    )

    # Store the scroll ID
    scroll_id = response["_scroll_id"]

    # Store the aggregations from the first response
    aggregations = response["aggregations"]

    # Process all hits using scroll
    while True:
        # Get the next batch of results
        scroll_response = client.scroll(scroll_id=scroll_id, scroll="5m")

        # Break if no more hits
        if not scroll_response["hits"]["hits"]:
            break

        # Process the hits here if needed
        # hits = scroll_response['hits']['hits']

        # Update scroll_id for next iteration
        scroll_id = scroll_response["_scroll_id"]

    # Clean up the scroll context
    client.clear_scroll(scroll_id=scroll_id)

    return aggregations


def get_records_created_as_of_dates(start_date, end_date):
    # Get aggregation data from helper function
    aggs = get_record_counts_for_periods(start_date, end_date)

    # Extract daily buckets
    buckets = aggs["by_day"]["buckets"]

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
        for bucket in results["by_year"]["buckets"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

        print("\nBy Month:")
        for bucket in results["by_month"]["buckets"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

        print("\nBy Week:")
        for bucket in results["by_week"]["buckets"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

        print("\nBy Day:")
        for bucket in results["by_day"]["buckets"]:
            print(f"{bucket['key']}: {bucket['doc_count']}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
