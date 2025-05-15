"""Queries for the stats dashboard."""

from invenio_search.proxies import current_search_client


def get_most_viewed_records(start_date, end_date, all_versions=False, size=10):
    """Get the most viewed records for a given period.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        all_versions (bool): Whether to include all versions of the records.
        size (int): The number of records to return.
    """

    id_field = "recid" if not all_versions else "parent_recid"

    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [{"range": {"timestamp": {"gte": start_date, "lte": end_date}}}]
            }
        },
        "aggs": {
            "by_recid": {
                "terms": {
                    "field": id_field,
                    "size": size,
                    "order": {"total_count": "desc"},
                },
                "aggs": {"total_count": {"sum": {"field": "count"}}},
            }
        },
    }
    result = current_search_client.search(index="stats-record-view-count", body=query)
    return result["aggregations"]["by_recid"]["buckets"]
