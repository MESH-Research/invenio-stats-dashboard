"""Queries for the stats dashboard."""

from pprint import pformat

import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from collections import defaultdict
from opensearchpy import OpenSearch
from opensearchpy.helpers.search import Search
from opensearchpy.helpers.index import Index


def get_all_subcount_ids(
    end_date=None, subcount_type=None, community_id=None, client=None
):
    """Get all unique subcount IDs in the date range.

    Args:
        end_date (str): The end date to query.
        subcount_type (str): The subcount type to query.
        community_id (str): The community ID.
        client (OpenSearch): The client to use.

    Returns:
        list: A list of unique subcount IDs.
    """
    client = client or current_search_client
    assert Index(using=client, name="stats-community-records-delta").exists()
    id_search = Search(using=client, index="stats-community-records-delta")
    id_search.aggs.bucket(
        f"all_{subcount_type}_ids",
        "terms",
        field=f"subcounts.by_{subcount_type}.id",
        size=1000,
    )
    if community_id:
        id_search.filter("term", community_id=community_id)
    if end_date:
        id_search.filter(
            "range", period_end={"gte": arrow.get("2019-01-01"), "lte": end_date}
        )
    id_search.query = {"match_all": {}}
    current_app.logger.error(f"Search count for {subcount_type}: {id_search.count()}")
    response = id_search.execute()
    current_app.logger.error(f"Response: {pformat(response['aggregations'])}")

    # Handle case where no buckets are returned
    if not response["aggregations"][f"all_{subcount_type}_ids"]["buckets"]:
        current_app.logger.warning(f"No {subcount_type} IDs found in the date range")
        return []

    return [
        bucket["key"]
        for bucket in response["aggregations"][f"all_{subcount_type}_ids"]["buckets"]
    ]


def build_subcount_filters(end_date, subcount_type, community_id=None, client=None):
    """Build the filters object for the given license IDs.

    Args:
        end_date (str): The end date to query.
        subcount_type (str): The subcount type to query. (Not "by_license" or
            "by_resource_type" but rather just "license" or "resource_type" etc.)
        community_id (str): The community ID.
        client (OpenSearch): The client to use.

    Returns:
        dict: The filters object for the given license IDs.

    We don't need the end date since we want all of the ids that
    have been used up to the end date.
    """
    subcount_ids = get_all_subcount_ids(end_date, subcount_type, community_id, client)
    current_app.logger.error(f"Subcount IDs: {subcount_ids}")

    filters = {
        f"id_{id}": {"term": {f"subcounts.by_{subcount_type}.id": id}}
        for id in subcount_ids
    }

    current_app.logger.error(f"Filters: {filters}")
    return filters


def daily_record_cumulative_counts_query(
    start_date: str, end_date: str, community_id: str | None = None
):
    """Build the query for the daily record cumulative counts.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        community_id (str, optional): The community ID. If None, no community filter
            is applied.

    Returns:
        dict: The query for the daily record cumulative counts.
    """
    nested_aggregations = [
        "resource_type",
        "access_rights",
        "language",
        "affiliation_creator",
        "affiliation_contributor",
        "funder",
        "subject",
        "publisher",
        "periodical",
        "file_type",
        "license",
    ]
    subcount_id_filters = {
        subcount_type: build_subcount_filters(
            end_date, subcount_type, community_id=community_id
        )
        for subcount_type in nested_aggregations
    }

    # Build the must clause conditionally
    must_clauses: list[dict] = [
        {"range": {"period_end": {"gte": start_date, "lte": end_date}}}
    ]
    if community_id:
        must_clauses.append({"term": {"community_id": community_id}})

    # Build the base aggregations
    daily_totals_aggs: dict[str, dict] = {
        "records_with_files": {"sum": {"field": "records.added.with_files"}},
        "cumulative_records_with_files": {
            "cumulative_sum": {"buckets_path": "records_with_files"}
        },
        "records_without_files": {"sum": {"field": "records.added.metadata_only"}},
        "cumulative_records_without_files": {
            "cumulative_sum": {"buckets_path": "records_without_files"}
        },
        "parents_with_files": {"sum": {"field": "parents.added.with_files"}},
        "cumulative_parents_with_files": {
            "cumulative_sum": {"buckets_path": "parents_with_files"}
        },
        "parents_without_files": {"sum": {"field": "parents.added.metadata_only"}},
        "cumulative_parents_without_files": {
            "cumulative_sum": {"buckets_path": "parents_without_files"}
        },
        "uploaders": {"sum": {"field": "uploaders"}},
        "cumulative_uploaders": {"cumulative_sum": {"buckets_path": "uploaders"}},
        "file_count": {"sum": {"field": "files.added.file_count"}},
        "cumulative_file_count": {"cumulative_sum": {"buckets_path": "file_count"}},
        "data_volume": {"sum": {"field": "files.added.data_volume"}},
        "cumulative_data_volume": {"cumulative_sum": {"buckets_path": "data_volume"}},
    }

    # Only add by_license aggregation if we have license filters
    if subcount_id_filters["license"]:
        daily_totals_aggs["by_license"] = {
            "filters": {"filters": subcount_id_filters["license"]},
            "aggs": {
                "records_with_files": {
                    "sum": {"field": "subcounts.by_license.records.added.with_files"}
                },
                "cumulative_records_with_files": {
                    "cumulative_sum": {"buckets_path": "records_with_files"}
                },
                "records_without_files": {
                    "sum": {"field": "subcounts.by_license.records.added.metadata_only"}
                },
                "cumulative_records_without_files": {
                    "cumulative_sum": {"buckets_path": "records_without_files"}
                },
                "parents_with_files": {
                    "sum": {"field": "subcounts.by_license.parents.added.with_files"}
                },
                "cumulative_parents_with_files": {
                    "cumulative_sum": {"buckets_path": "parents_with_files"}
                },
                "parents_without_files": {
                    "sum": {"field": "subcounts.by_license.parents.added.metadata_only"}
                },
                "cumulative_parents_without_files": {
                    "cumulative_sum": {"buckets_path": "parents_without_files"}
                },
                "file_count": {
                    "sum": {"field": "subcounts.by_license.files.added.file_count"}
                },
                "cumulative_file_count": {
                    "cumulative_sum": {"buckets_path": "file_count"}
                },
                "data_volume": {
                    "sum": {"field": "subcounts.by_license.files.added.data_volume"}
                },
                "cumulative_data_volume": {
                    "cumulative_sum": {"buckets_path": "data_volume"}
                },
            },
        }

    return {
        "size": 0,
        "query": {"bool": {"must": must_clauses}},
        "aggs": {
            "daily_totals": {
                "date_histogram": {
                    "field": "period_end",
                    "calendar_interval": "day",
                },
                "aggs": daily_totals_aggs,
            },
        },
    }


def daily_record_delta_query(start_date, end_date):
    return {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    # {"term": {"parent.communities.ids": community_id}},
                    {
                        "range": {
                            "created": {
                                "gte": start_date,
                                "lte": end_date,
                                "format": "yyyy-MM-dd",
                            }
                        }
                    },
                ]
            }
        },
        "aggs": {
            "by_day": {
                "date_histogram": {
                    "field": "created",
                    "calendar_interval": "day",
                    "format": "yyyy-MM-dd",
                },
                "aggs": {
                    "total_records": {"value_count": {"field": "_id"}},
                    "with_files": {
                        "filter": {"term": {"files.enabled": True}},
                        "aggs": {
                            "unique_parents": {"cardinality": {"field": "parent.id"}}
                        },
                    },
                    "without_files": {
                        "filter": {"term": {"files.enabled": False}},
                        "aggs": {
                            "unique_parents": {"cardinality": {"field": "parent.id"}}
                        },
                    },
                    "uploaders": {
                        "cardinality": {"field": "parent.access.owned_by.user"},
                    },
                    "file_count": {
                        "value_count": {"field": "files.entries.key"},
                    },
                    "total_bytes": {"sum": {"field": "files.entries.size"}},
                    "by_resource_type": {
                        "terms": {"field": "metadata.resource_type.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_access_rights": {
                        "terms": {"field": "access.status"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_language": {
                        "terms": {"field": "metadata.languages.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_affiliation_creator": {
                        "terms": {"field": "creators.affiliations.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_affiliation_contributor": {
                        "terms": {"field": "metadata.contributors.affiliations.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_funder": {
                        "terms": {"field": "metadata.funding.funder.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_subject": {
                        "terms": {"field": "metadata.subjects.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    # FIXME: Can't perform aggregations on publisher field ('text')
                    "by_publisher": {
                        "terms": {"field": "metadata.publisher.keyword"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_periodical": {
                        "terms": {
                            "field": "custom_fields.journal:journal.title.keyword"
                        },
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_file_type": {
                        "terms": {"field": "files.entries.ext"},
                        "aggs": {
                            "unique_records": {"cardinality": {"field": "_id"}},
                            "unique_parents": {"cardinality": {"field": "parent.id"}},
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_license": {
                        "terms": {"field": "metadata.rights.id"},
                        "aggs": {
                            "with_files": {
                                "filter": {"term": {"files.enabled": True}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "without_files": {
                                "filter": {"term": {"files.enabled": False}},
                                "aggs": {
                                    "unique_parents": {
                                        "cardinality": {"field": "parent.id"}
                                    }
                                },
                            },
                            "file_count": {
                                "value_count": {"field": "files.entries.key"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                },
            }
        },
    }


DAILY_CUMULATIVE_COUNTS_QUERY = {
    "size": 0,
    "aggs": {
        "daily_totals": {
            "date_histogram": {
                "field": "snapshot_date",
                "calendar_interval": "day",
                "format": "yyyy-MM-dd",
            },
            "aggs": {
                "metadata_only": {"sum": {"field": "record_count.metadata_only"}},
                "with_files": {"sum": {"field": "record_count.with_files"}},
                "cumulative_metadata": {
                    "cumulative_sum": {"buckets_path": "metadata_only"}
                },
                "cumulative_with_files": {
                    "cumulative_sum": {"buckets_path": "with_files"}
                },
            },
        }
    },
}


def get_most_viewed_records(
    start_date, end_date, all_versions=False, size=10, search_domain=None
):
    """Get the most viewed records for a given period.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        all_versions (bool): Whether to include all versions of the records.
        size (int): The number of records to return.
        search_domain (str, optional): The OpenSearch domain URL. If provided,
            creates a new client instance. If None, uses the default
            current_search_client.

    Returns:
        list: A list of dictionaries containing record IDs and their view counts,
              sorted by view count in descending order.
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

    id_field = "recid" if not all_versions else "parent_recid"

    # Initialize scroll query with aggregations
    query = {
        "size": 10000,  # Process 10000 documents at a time
        "query": {
            "bool": {
                "must": [{"range": {"timestamp": {"gte": start_date, "lte": end_date}}}]
            }
        },
        "aggs": {
            "by_recid": {
                "terms": {
                    "field": id_field,
                    "size": size,  # Only get top size results in each batch
                    "order": {"total_count": "desc"},
                },
                "aggs": {"total_count": {"sum": {"field": "count"}}},
            }
        },
    }

    # Dictionary to store combined results
    combined_results = defaultdict(int)

    # Initial search with scroll
    response = client.search(index="stats-record-view", body=query, scroll="5m")

    # Store the scroll ID
    scroll_id = response["_scroll_id"]

    # Process initial batch aggregations
    for bucket in response["aggregations"]["by_recid"]["buckets"]:
        record_id = bucket["key"]
        count = bucket["total_count"]["value"]
        combined_results[record_id] += count

    # Process remaining hits using scroll
    while True:
        scroll_response = client.scroll(scroll_id=scroll_id, scroll="5m")

        # Break if no more hits
        if not scroll_response["hits"]["hits"]:
            break

        # Process aggregations from this batch
        for bucket in scroll_response["aggregations"]["by_recid"]["buckets"]:
            record_id = bucket["key"]
            count = bucket["total_count"]["value"]
            combined_results[record_id] += count

        # Update scroll_id for next iteration
        scroll_id = scroll_response["_scroll_id"]

    # Clean up the scroll context
    client.clear_scroll(scroll_id=scroll_id)

    # Convert to list of buckets and sort by count
    buckets = [
        {"key": record_id, "doc_count": count}
        for record_id, count in combined_results.items()
    ]

    # Sort by count in descending order and limit to requested size
    sorted_buckets = sorted(buckets, key=lambda x: x["doc_count"], reverse=True)[:size]

    return sorted_buckets
