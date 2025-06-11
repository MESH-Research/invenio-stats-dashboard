"""Queries for the stats dashboard."""

from pprint import pformat

import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy import OpenSearch
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

nested_aggregations = [
    (
        "resource_type",
        "metadata.resource_type.id",
        "metadata.resource_type.title.en",
    ),
    ("access_rights", "access.status"),
    ("language", "metadata.languages.id", "metadata.languages.title.en"),
    (
        "affiliation_creator",
        "metadata.creators.affiliations.id",
        "metadata.creators.affiliations.name.keyword",
    ),
    (
        "affiliation_contributor",
        "metadata.contributors.affiliations.id",
        "metadata.contributors.affiliations.name.keyword",
    ),
    (
        "funder",
        "metadata.funding.funder.id",
        "metadata.funding.funder.title.en",
    ),
    ("subject", "metadata.subjects.id", "metadata.subjects.subject"),
    ("publisher", "metadata.publisher.keyword"),
    ("periodical", "custom_fields.journal:journal.title.keyword"),
    ("file_type", "files.entries.ext"),
    ("license", "metadata.rights.id", "metadata.rights.title.en"),
]


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

    # Create a nested aggregation since the fields are mapped as nested
    id_search.aggs.bucket(
        f"all_{subcount_type}_ids",
        "nested",
        path=f"subcounts.by_{subcount_type}",
    ).bucket(
        "filtered_ids",
        "filter",
        {"bool": {"must": []}},
    ).bucket(
        "ids",
        "terms",
        field=f"subcounts.by_{subcount_type}.id",
        size=1000,
    )

    # Add filters to the bool query
    if community_id:
        id_search.filter("term", community_id=community_id)
    if end_date:
        id_search.filter(
            "range",
            period_end={"gte": arrow.get("2019-01-01").isoformat(), "lte": end_date},
        )
    id_search.query = {"match_all": {}}
    current_app.logger.error(f"Search count for {subcount_type}: {id_search.count()}")
    response = id_search.execute()
    current_app.logger.error(f"Response: {pformat(response.hits[0].to_dict())}")
    current_app.logger.error(f"Response: {pformat(response.aggregations)}")

    # Handle case where no buckets are returned
    if not response["aggregations"][f"all_{subcount_type}_ids"]["filtered_ids"]["ids"][
        "buckets"
    ]:
        current_app.logger.warning(f"No {subcount_type} IDs found in the date range")
        return []

    return [
        bucket["key"]
        for bucket in response["aggregations"][f"all_{subcount_type}_ids"][
            "filtered_ids"
        ]["ids"]["buckets"]
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
    start_date: str,
    end_date: str,
    community_id: str | None = None,
    find_deleted: bool = False,
):
    """Build the query for a snapshot of one day's cumulative record counts.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        community_id (str, optional): The community ID. If None, no community filter
            is applied.
        find_deleted (bool, optional): Whether to find deleted records. If True,
            the query will find deleted records. Instead of finding currently published
            records based on their created date, it will find deleted records based
            on their removal date.

    Returns:
        dict: The query for the daily record cumulative counts.
    """
    date_series_field = "tombstone.removal_date" if find_deleted else "created"

    # Build the must clause conditionally
    must_clauses: list[dict] = [
        {
            "range": {
                date_series_field: {
                    "gte": (
                        arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss")
                    ),
                    "lte": (
                        arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss")
                    ),
                }
            }
        }
    ]
    if community_id:
        must_clauses.append({"term": {"parent.communities.ids": community_id}})

    # Only add by_license aggregation if we have license filters
    sub_aggs = {
        f"by_{subcount_type[0]}": {
            **(
                {
                    "composite": {
                        "size": 1000,
                        "sources": [
                            {
                                "id": {
                                    "terms": {
                                        "field": subcount_type[1],
                                        "missing_bucket": True,
                                    }
                                }
                            },
                            {
                                "label": {
                                    "terms": {
                                        "field": subcount_type[2],
                                        "missing_bucket": True,
                                    }
                                }
                            },
                        ],
                    }
                }
                if subcount_type[0]
                in ["affiliation_creator", "affiliation_contributor"]
                else {"terms": {"field": subcount_type[1]}}
            ),
            "aggs": {
                "with_files": {
                    "filter": {"term": {"files.enabled": True}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "without_files": {
                    "filter": {"term": {"files.enabled": False}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "file_count": {"value_count": {"field": "files.entries.key"}},
                "total_bytes": {"sum": {"field": "files.entries.size"}},
                **(
                    {
                        "label": {
                            "top_hits": {
                                "size": 1,
                                "_source": {
                                    "includes": [
                                        (
                                            "metadata.subjects"
                                            if subcount_type[0] == "subject"
                                            else subcount_type[2]
                                        )
                                    ]
                                },
                            }
                        }
                    }
                    if len(subcount_type) > 2
                    and subcount_type[0]
                    not in [
                        "affiliation_creator",
                        "affiliation_contributor",
                    ]
                    else {}
                ),
            },
        }
        for subcount_type in nested_aggregations
    }

    return {
        "size": 0,
        "query": {"bool": {"must": must_clauses}},
        "aggs": {
            "date_field_min": {
                "min": {"field": date_series_field, "format": "yyyy-MM-dd'T'HH:mm:ss"}
            },
            "date_field_max": {
                "max": {"field": date_series_field, "format": "yyyy-MM-dd'T'HH:mm:ss"}
            },
            "total_records": {"value_count": {"field": "_id"}},
            "with_files": {
                "filter": {"term": {"files.enabled": True}},
                "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
            },
            "without_files": {
                "filter": {"term": {"files.enabled": False}},
                "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
            },
            "uploaders": {
                "cardinality": {"field": "parent.access.owned_by.user"},
            },
            "file_count": {
                "value_count": {"field": "files.entries.key"},
            },
            "total_bytes": {"sum": {"field": "files.entries.size"}},
            **sub_aggs,
            "by_file_type": {
                "terms": {"field": "files.entries.ext"},
                "aggs": {
                    "unique_records": {"cardinality": {"field": "_id"}},
                    "unique_parents": {"cardinality": {"field": "parent.id"}},
                    "total_bytes": {"sum": {"field": "files.entries.size"}},
                },
            },
        },
    }


def daily_record_delta_query(
    start_date, end_date, community_id=None, find_deleted=False
):
    """Build the query for a delta of records created or deleted between two dates.

    Args:
        start_date (str): The start date to query.
        end_date (str): The end date to query.
        community_id (str, optional): The community ID. If None, no community filter
            is applied.
        find_deleted (bool, optional): Whether to find deleted records. If True,
            the query will find deleted records. Instead of finding currently published
            records based on their created date, it will find deleted records based
            on their removal date.
    """

    date_series_field = "tombstone.removal_date" if find_deleted else "created"
    must_clauses: list[dict] = [
        {"term": {"is_published": True}},
        {"range": {date_series_field: {"gte": start_date, "lte": end_date}}},
    ]

    if find_deleted:
        must_clauses.append({"term": {"is_deleted": True}})
    if community_id:
        must_clauses.append({"term": {"parent.communities.ids": community_id}})

    sub_aggs = {
        f"by_{subcount_type[0]}": {
            **(
                {
                    "composite": {
                        "size": 1000,
                        "sources": [
                            {
                                "id": {
                                    "terms": {
                                        "field": subcount_type[1],
                                        "missing_bucket": True,
                                    }
                                }
                            },
                            {
                                "label": {
                                    "terms": {
                                        "field": subcount_type[2],
                                        "missing_bucket": True,
                                    }
                                }
                            },
                        ],
                    }
                }
                if subcount_type[0]
                in ["affiliation_creator", "affiliation_contributor"]
                else {"terms": {"field": subcount_type[1]}}
            ),
            "aggs": {
                "with_files": {
                    "filter": {"term": {"files.enabled": True}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "without_files": {
                    "filter": {"term": {"files.enabled": False}},
                    "aggs": {"unique_parents": {"cardinality": {"field": "parent.id"}}},
                },
                "file_count": {"value_count": {"field": "files.entries.key"}},
                "total_bytes": {"sum": {"field": "files.entries.size"}},
                **(
                    {
                        "label": {
                            "top_hits": {
                                "size": 1,
                                "_source": {
                                    "includes": [
                                        (
                                            "metadata.subjects"
                                            if subcount_type[0] == "subject"
                                            else subcount_type[2]
                                        )
                                    ]
                                },
                            }
                        }
                    }
                    if len(subcount_type) > 2
                    and subcount_type[0]
                    not in [
                        "affiliation_creator",
                        "affiliation_contributor",
                    ]
                    else {}
                ),
            },
        }
        for subcount_type in nested_aggregations
    }

    return {
        "size": 0,
        "query": {
            "bool": {
                "must": must_clauses,
            }
        },
        "aggs": {
            "by_day": {
                "date_histogram": {
                    "field": date_series_field,
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
                    **sub_aggs,
                    "by_file_type": {
                        "terms": {"field": "files.entries.ext"},
                        "aggs": {
                            "unique_records": {"cardinality": {"field": "_id"}},
                            "unique_parents": {"cardinality": {"field": "parent.id"}},
                            "total_bytes": {"sum": {"field": "files.entries.size"}},
                        },
                    },
                },
            }
        },
    }


def daily_usage_delta_query(
    current_date: arrow.Arrow,
    community_id: str | None = None,
    client: OpenSearch | None = None,
    after_key: dict | None = None,
):
    """Build the query for a delta of usage between two dates."""

    daily_activity_search = Search(
        using=client or current_search_client,
        index=prefix_index("events-stats-record-view"),
    )
    daily_activity_search.query(
        Q(
            "range",
            timestamp={
                "gte": current_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                "lte": current_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            },
        )
        & Q("term", is_robot=False)
    )
    daily_activity_search.aggs.bucket(
        "recid_count",
        "cardinality",
        field="recid",
    )
    daily_activity_search.aggs.bucket(
        "parent_count",
        "cardinality",
        field="parent_recid",
    )
    daily_activity_search.aggs.bucket(
        "by_country",
        "terms",
        field="country",
        size=20,
    )
    daily_activity_search.aggs.bucket(
        "by_referrer",
        "terms",
        field="referrer",
        size=20,
    )
    daily_activity_search.aggs.bucket(
        "all_recids",
        "composite",
        sources=[{"recid": {"terms": {"field": "recid"}}}],
        size=1000,
        after=after_key,
    )
