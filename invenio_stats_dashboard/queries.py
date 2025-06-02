"""Queries for the stats dashboard."""

from invenio_search.proxies import current_search_client
from collections import defaultdict
from opensearchpy import OpenSearch


def daily_record_cumulative_counts_query(community_id, start_date, end_date):
    return {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"term": {"community_id": community_id}},
                    {"range": {"snapshot_date": {"gte": start_date, "lte": end_date}}},
                ]
            }
        },
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


def daily_record_delta_query(community_id, start_date, end_date):
    return {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"term": {"community_id": community_id}},
                    {"range": {"created": {"gte": start_date, "lte": end_date}}},
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
                        "cardinality": {"field": "parent.access.owned_by.id"},
                    },
                    "files": {
                        "terms": {"field": "files.entries.file_id"},
                        "aggs": {
                            "count": {
                                "value_count": {"field": "files.entries.file_id"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_publisher": {
                        "terms": {"field": "metadata.publisher"},
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
                                "value_count": {"field": "files.entries.file_id"}
                            },
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                    "by_periodical": {
                        "terms": {"field": "custom_fields.journal:journal.title"},
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
                                "value_count": {"field": "files.entries.file_id"}
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
                                "value_count": {"field": "files.entries.file_id"}
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
