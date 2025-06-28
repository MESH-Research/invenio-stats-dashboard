"""Queries for the stats dashboard."""

import copy
from flask import current_app
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

NESTED_AGGREGATIONS = {
    "resource_type": [
        "metadata.resource_type.id",
        ["metadata.resource_type.title.en", "metadata.resource_type.id"],
    ],
    "access_rights": ["access.status"],
    "language": [
        "metadata.languages.id",
        ["metadata.languages.title.en", "metadata.languages.id"],
    ],
    "affiliation_creator_id": [
        "metadata.creators.affiliations.id",
        [
            "metadata.creators.affiliations.name.keyword",
            "metadata.creators.affiliations.id",
        ],
    ],
    "affiliation_creator_name": [
        "metadata.creators.affiliations.name.keyword",
        [
            "metadata.creators.affiliations.name.keyword",
            "metadata.creators.affiliations.id",
        ],
    ],
    "affiliation_contributor_id": [
        "metadata.contributors.affiliations.id",
        [
            "metadata.contributors.affiliations.name.keyword",
            "metadata.contributors.affiliations.id",
        ],
    ],
    "affiliation_contributor_name": [
        "metadata.contributors.affiliations.name.keyword",
        [
            "metadata.contributors.affiliations.name.keyword",
            "metadata.contributors.affiliations.id",
        ],
    ],
    "funder": [
        "metadata.funding.funder.id",
        ["metadata.funding.funder.title.en", "metadata.funding.funder.id"],
    ],
    "subject": [
        "metadata.subjects.id",
        [
            "metadata.subjects.subject",
            "metadata.subjects.id",
            "metadata.subjects.scheme",
        ],
    ],
    "publisher": ["metadata.publisher.keyword"],
    "periodical": ["custom_fields.journal:journal.title.keyword"],
    "file_type": ["files.entries.ext"],
    "license": [
        "metadata.rights.id",
        ["metadata.rights.title.en", "metadata.rights.id"],
    ],
}


def daily_record_snapshot_query(
    start_date: str,
    end_date: str,
    community_id: str | None = None,
    find_deleted: bool = False,
    use_included_dates: bool = False,
    use_published_dates: bool = False,
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
    date_series_field = (
        "metadata.publication_date" if use_published_dates else "created"
    )

    community_id_field = "custom_fields.stats:community_events.community_id"
    added_field = "custom_fields.stats:community_events.added"
    removed_field = "custom_fields.stats:community_events.removed"

    must_clauses: list[dict] = []  # Build the must clause conditionally
    if find_deleted and not community_id:
        must_clauses.append(
            {
                "bool": {
                    "must": [
                        {"range": {"tombstone.removal_date": {"lte": end_date}}},
                        {"range": {date_series_field: {"lte": end_date}}},
                        {"term": {"is_published": True}},
                    ],
                }
            }
        )
    elif find_deleted and community_id and use_included_dates:
        must_clauses.append(
            {
                "nested": {
                    "path": "custom_fields.stats:community_events",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {community_id_field: community_id}},
                                {"range": {removed_field: {"lte": end_date}}},
                            ],
                            "must_not": [
                                {
                                    "nested": {
                                        "path": "custom_fields.stats:community_events",
                                        "query": {
                                            "bool": {
                                                "must": [
                                                    {
                                                        "term": {
                                                            community_id_field: (
                                                                community_id
                                                            )
                                                        }
                                                    },
                                                    {
                                                        "range": {
                                                            added_field: {
                                                                "lte": end_date
                                                            }
                                                        }
                                                    },
                                                    {
                                                        "bool": {
                                                            "should": [
                                                                {
                                                                    "bool": {
                                                                        "must_not": {
                                                                            "exists": {
                                                                                "field": (
                                                                                    removed_field
                                                                                )
                                                                            }
                                                                        }
                                                                    }
                                                                },
                                                                {
                                                                    "range": {
                                                                        removed_field: {
                                                                            "gt": (
                                                                                end_date
                                                                            )
                                                                        }
                                                                    }
                                                                },
                                                            ]
                                                        }
                                                    },
                                                ]
                                            }
                                        },
                                    }
                                }
                            ],
                        }
                    },
                },
            }
        )
        must_clauses.append({"term": {"is_published": True}})
    elif find_deleted and community_id and not use_included_dates:
        must_clauses.append(
            {
                "nested": {
                    "path": "custom_fields.stats:community_events",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {community_id_field: community_id}},
                                {"range": {removed_field: {"lte": end_date}}},
                            ],
                            "must_not": [
                                {
                                    "nested": {
                                        "path": "custom_fields.stats:community_events",
                                        "query": {
                                            "bool": {
                                                "must": [
                                                    {
                                                        "term": {
                                                            community_id_field: (
                                                                community_id
                                                            )
                                                        }
                                                    },
                                                    {
                                                        "range": {
                                                            added_field: {
                                                                "lte": end_date
                                                            }
                                                        }
                                                    },
                                                    {
                                                        "bool": {
                                                            "should": [
                                                                {
                                                                    "bool": {
                                                                        "must_not": {
                                                                            "exists": {
                                                                                "field": (
                                                                                    removed_field
                                                                                )
                                                                            }
                                                                        }
                                                                    }
                                                                },
                                                                {
                                                                    "range": {
                                                                        removed_field: {
                                                                            "gt": (
                                                                                end_date
                                                                            )
                                                                        }
                                                                    }
                                                                },
                                                            ]
                                                        }
                                                    },
                                                ]
                                            }
                                        },
                                    }
                                }
                            ],
                        }
                    },
                },
            }
        )
        must_clauses.append({"range": {date_series_field: {"lte": end_date}}})
        must_clauses.append({"term": {"is_published": True}})
    elif not find_deleted and community_id and not use_included_dates:
        must_clauses.append(
            {
                "nested": {
                    "path": "custom_fields.stats:community_events",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {community_id_field: community_id}},
                                {"range": {added_field: {"lte": end_date}}},
                                {
                                    "bool": {
                                        "should": [
                                            {
                                                "bool": {
                                                    "must_not": {
                                                        "exists": {
                                                            "field": removed_field
                                                        }
                                                    }
                                                }
                                            },
                                            {
                                                "range": {
                                                    removed_field: {"gt": end_date}
                                                }
                                            },
                                        ]
                                    }
                                },
                            ]
                        }
                    },
                }
            }
        )
        must_clauses.append({"range": {date_series_field: {"lte": end_date}}})
        must_clauses.append(
            {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "must_not": {"exists": {"field": "tombstone.deleted"}}
                            }
                        },
                        {"range": {"tombstone.deleted": {"gt": end_date}}},
                    ]
                }
            }
        )
    else:
        must_clauses.append(
            {
                "bool": {
                    "must": [
                        {"range": {date_series_field: {"lte": end_date}}},
                        {"term": {"is_published": True}},
                    ]
                }
            }
        )

    subcount_types = copy.deepcopy(NESTED_AGGREGATIONS)
    subcount_types["affiliation_creator"] = subcount_types["affiliation_creator_id"]
    subcount_types["affiliation_contributor"] = subcount_types[
        "affiliation_contributor_id"
    ]
    for type_name in [
        "affiliation_creator_id",
        "affiliation_contributor_id",
        "affiliation_creator_name",
        "affiliation_contributor_name",
    ]:
        del subcount_types[type_name]

    sub_aggs = {
        f"by_{subcount_label}": {
            **(
                {
                    "composite": {
                        "size": 1000,
                        "sources": [
                            {
                                "id": {
                                    "terms": {
                                        "field": subcount_fields[0],
                                        "missing_bucket": True,
                                    }
                                }
                            },
                            {
                                "label": {
                                    "terms": {
                                        "field": subcount_fields[1][0],
                                        "missing_bucket": True,
                                    }
                                }
                            },
                        ],
                    }
                }
                if subcount_label.startswith("affiliation_")
                else {"terms": {"field": subcount_fields[0]}}
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
                                    "includes": (
                                        subcount_fields[1]
                                        if len(subcount_fields) > 1
                                        else subcount_fields[0]
                                    )
                                },
                            }
                        }
                    }
                    if len(subcount_fields) > 1
                    and not subcount_label.startswith("affiliation_")
                    else {}
                ),
            },
        }
        for subcount_label, subcount_fields in subcount_types.items()
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
    start_date,
    end_date,
    community_id=None,
    find_deleted=False,
    use_included_dates=False,
    use_published_dates=False,
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
        use_included_dates (bool, optional): Whether to use the dates when the record
            was included to the community instead of the created date.
            (Can only be used if the community_id is not "global")
        use_published_dates (bool, optional): Whether to use the metadata publication
            date instead of the created date. (This is not the date of invenio
            publication but the date of the record's publication
            (metadata.publication_date).)
    """

    # Field to use to find the period's records
    date_series_field = "created"
    if find_deleted:
        date_series_field = "tombstone.removal_date"
    elif use_published_dates:
        date_series_field = "metadata.publication_date"

    # Field to use to find community add/remove events for the period
    event_date_field = (
        "custom_fields.stats:community_events.removed"
        if find_deleted
        else "custom_fields.stats:community_events.added"
    )

    must_clauses: list[dict] = [
        {"term": {"is_published": True}},
    ]
    community_id_field = "custom_fields.stats:community_events.community_id"
    if use_included_dates and community_id != "global":
        # Ensure we're finding records *added* during the period
        must_clauses.append(
            {
                "nested": {
                    "path": "custom_fields.stats:community_events",
                    "query": {
                        "range": {
                            event_date_field: {"gte": start_date, "lte": end_date}
                        }
                    },
                }
            }
        )
    else:
        must_clauses.append(
            {"range": {date_series_field: {"gte": start_date, "lte": end_date}}}
        )

    if find_deleted and community_id in ["global", None]:
        must_clauses.append({"term": {"is_deleted": True}})

    # Have to look at community events record in case the record has since been removed
    if community_id and community_id != "global":
        must_clauses.append(
            {
                "bool": {
                    "should": [
                        {"term": {"parent.communities.ids": community_id}},
                        {
                            "nested": {
                                "path": "custom_fields.stats:community_events",
                                "query": {
                                    "bool": {
                                        "must": [
                                            {
                                                "term": {
                                                    community_id_field: community_id
                                                }
                                            },
                                            {
                                                "range": {
                                                    event_date_field: {
                                                        "gte": start_date,
                                                        "lte": end_date,
                                                    }
                                                }
                                            },
                                        ]
                                    }
                                },
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    sub_aggs = {
        f"by_{subcount_label}": {
            "terms": {"field": subcount_fields[0]},
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
                                    "includes": (
                                        subcount_fields[1]
                                        if len(subcount_fields) > 1
                                        else subcount_fields[0]
                                    )
                                },
                            }
                        }
                    }
                    if len(subcount_fields) > 1
                    else {}
                ),
            },
        }
        for subcount_label, subcount_fields in NESTED_AGGREGATIONS.items()
    }

    return {
        "size": 0,
        "query": {
            "bool": {
                "must": must_clauses,
            }
        },
        "aggs": {
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


class CommunityStatsResultsQueryBase(Query):
    """Base class for the stats dashboard API requests."""

    date_field: (
        str  # Type annotation to indicate this attribute will be set by child classes
    )

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        # self.date_field = "snapshot_date"

    def run(self, community_id="global", start_date=None, end_date=None):
        """Run the query.

        Args:
            community_id (str): The community ID. If "global", the query will be run
                for the entire repository. Default is "global".
            start_date (str): The start date.
            end_date (str): The end date.

        Returns:
            list: The results of the query.
        """
        results = []
        must_clauses: list[dict] = [
            {"term": {"community_id": community_id}},
        ]
        range_clauses: dict[str, dict[str, str]] = {}
        if start_date:
            range_clauses[self.date_field]["gte"] = start_date
        if end_date:
            range_clauses[self.date_field]["lte"] = end_date
        if range_clauses:
            must_clauses.append({"range": range_clauses})
        try:
            assert Index(using=self.client, name=self.index).exists()
            snapshot_search = Search(using=self.client, index=self.index).query(
                Q("bool", must=must_clauses)
            )
            snapshot_search.sort(self.date_field)
            snapshot_search.extra(size=10_000)
            count = snapshot_search.count()
            if count == 0:
                raise ValueError(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date}"
                )
            response = snapshot_search.execute()
            results = [h["_source"] for h in response.hits.hits.to_dict()]
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {e}")
        return results


class CommunityRecordDeltaResultsQuery(CommunityStatsResultsQueryBase):
    """Query for the stats dashboard API requests."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "timestamp"


class CommunityRecordSnapshotResultsQuery(CommunityStatsResultsQueryBase):
    """Query for the stats dashboard API requests."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"


class CommunityUsageDeltaResultsQuery(CommunityStatsResultsQueryBase):
    """Query for the stats dashboard API requests."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "timestamp"


class CommunityUsageSnapshotResultsQuery(CommunityStatsResultsQueryBase):
    """Query for the stats dashboard API requests."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"


class CommunityStatsResultsQuery(Query):
    """Collected query for all stats dashboard API requests."""

    client: OpenSearch | None  # Type annotation to indicate the client type

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)

    def run(self, community_id="global", start_date=None, end_date=None):
        """Run the query."""
        results = {}
        record_deltas_created = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-created",
            index="stats-community-record-delta-created",
            client=self.client,
        )
        results["record_deltas_created"] = record_deltas_created.run(
            community_id, start_date, end_date
        )
        record_deltas_published = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-published",
            index="stats-community-record-delta-published",
            client=self.client,
        )
        results["record_deltas_published"] = record_deltas_published.run(
            community_id, start_date, end_date
        )
        record_deltas_added = CommunityRecordDeltaResultsQuery(
            name="community-record-delta-added",
            index="stats-community-record-delta-added",
            client=self.client,
        )
        results["record_deltas_added"] = record_deltas_added.run(
            community_id, start_date, end_date
        )
        record_snapshots = CommunityRecordSnapshotResultsQuery(
            name="community-record-snapshot",
            index="stats-community-record-snapshot",
            client=self.client,
        )
        results["record_snapshots"] = record_snapshots.run(
            community_id, start_date, end_date
        )
        usage_deltas = CommunityUsageDeltaResultsQuery(
            name="community-usage-delta",
            index="stats-community-usage-delta",
            client=self.client,
        )
        results["usage_deltas"] = usage_deltas.run(community_id, start_date, end_date)
        usage_snapshots = CommunityUsageSnapshotResultsQuery(
            name="community-usage-snapshot",
            index="stats-community-usage-snapshot",
            client=self.client,
        )
        results["usage_snapshots"] = usage_snapshots.run(
            community_id, start_date, end_date
        )
        return results
