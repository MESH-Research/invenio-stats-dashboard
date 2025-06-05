from collections.abc import Generator
import math
from pprint import pformat

import datetime

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.search import Search
from invenio_stats.aggregations import StatAggregator
from invenio_stats.bookmark import BookmarkAPI
from invenio_stats_dashboard.queries import daily_record_delta_query


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


class CommunityRecordsDeltaAggregator(StatAggregator):

    def __init__(self, name, community_ids=None, *args, **kwargs):
        self.name = name
        self.event = ""  # Not used
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-records-delta")
        self.aggregation_field = ""  # Not used
        self.client = kwargs.get("client") or current_search_client
        self.interval = "day"
        self.community_ids = community_ids
        # Create client instance if search_domain is provided
        # self.client = OpenSearch(
        #     hosts=[{"host": kwargs.get("search_domain"), "port": 443}],
        #     http_compress=True,  # enables gzip compression for request bodies
        #     use_ssl=True,
        #     verify_certs=True,
        #     ssl_assert_hostname=False,
        #     ssl_show_warn=False,
        # )
        self.bookmark_api = BookmarkAPI(self.client, self.name, self.interval)

    def create_agg_dict(self, community_id, bucket):
        """Create a dictionary representing the aggregation result for indexing."""

        agg_dict = {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "period_start": bucket["key_as_string"],
            "period_end": bucket["key_as_string"],
            "records": {
                "added": {
                    "metadata_only": bucket["without_files"].get("doc_count", 0),
                    "with_files": bucket["with_files"].get("doc_count", 0),
                },
                "removed": {
                    "metadata_only": 0,
                    "with_files": 0,
                },
            },
            "parents": {
                "added": {
                    "metadata_only": (
                        bucket["without_files"]
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                    "with_files": (
                        bucket["with_files"].get("unique_parents", {}).get("value", 0)
                    ),
                },
                "removed": {
                    "metadata_only": 0,
                    "with_files": 0,
                },
            },
            "files": {
                "added": {
                    "file_count": bucket["file_count"].get("value", 0),
                    "data_volume": bucket["total_bytes"].get("value", 0),
                },
                "removed": {
                    "file_count": 0,
                    "data_volume": 0,
                },
            },
            "uploaders": bucket["uploaders"].get("value", 0),
            "subcounts": {
                "by_resource_type": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_resource_type"]["buckets"]
                ],
                "by_access_rights": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_access_rights"]["buckets"]
                ],
                "by_language": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                        },
                    }
                    for b in bucket["by_language"]["buckets"]
                ],
                "by_affiliation_creator": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_affiliation_creator"]["buckets"]
                ],
                "by_affiliation_contributor": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_affiliation_contributor"]["buckets"]
                ],
                "by_funder": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                            },
                            "with_files": b.get("with_files", {}).get("doc_count", 0),
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_funder"]["buckets"]
                ],
                "by_subject": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_subject"]["buckets"]
                ],
                "by_publisher": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_publisher"]["buckets"]
                ],
                "by_periodical": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_periodical"]["buckets"]
                ],
                "by_file_type": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "added": {
                            "records": b.get("unique_records", {}).get("value", 0),
                            "parents": b.get("unique_parents", {}).get("value", 0),
                            "files": b.get("doc_count", 0),
                            "data_volume": b.get("data_volume", {}).get("value", 0),
                        },
                        "removed": {
                            "records": 0,
                            "parents": 0,
                            "files": 0,
                            "data_volume": 0,
                        },
                    }
                    for b in bucket["by_file_type"]["buckets"]
                ],
                "by_license": [
                    {
                        "id": b.get("key"),
                        "records": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    b.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    b.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": 0,
                                "with_files": 0,
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": b.get("file_count", {}).get("value", 0),
                                "data_volume": b.get("total_bytes", {}).get("value", 0),
                            },
                            "removed": {
                                "file_count": 0,
                                "data_volume": 0,
                            },
                        },
                    }
                    for b in bucket["by_license"]["buckets"]
                ],
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }
        return agg_dict

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
        search_domain: str | None = None,
    ) -> Generator[dict, None, None]:
        """Query opensearch for record counts for each day period.

        Args:
            community_id (str): The community id to query.
            community_parent_id (str): The community parent id to query.
            start_date (str): The start date to query.
            end_date (str): The end date to query.
            search_domain (str, optional): The search domain to use. If provided,
                creates a new client instance. If None, uses the default
                current_search_client.

        Returns:
            dict: A dictionary containing lists of buckets for each time period.
        """
        # Divide the search into years
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)
        for year in range(start_date.year, end_date.year + 1):
            current_app.logger.error(f"Year: {year}")
            year_start_date = arrow.get(f"{year}-01-01")
            year_end_date = arrow.get(f"{year}-12-31")

            year_search = Search(using=self.client, index=self.event_index)
            if community_id:
                year_search = year_search.filter(
                    "term", parent__communities__ids=community_id
                )
            year_search = year_search.filter(
                "range",
                created={
                    "gte": year_start_date.format("YYYY-MM-DD"),
                    "lte": year_end_date.format("YYYY-MM-DD"),
                },
            )
            year_search.update_from_dict(
                daily_record_delta_query(
                    community_id,
                    year_start_date.format("YYYY-MM-DD"),
                    year_end_date.format("YYYY-MM-DD"),
                )
            )

            current_app.logger.error(
                f"Processing year {year_start_date} to {year_end_date}"
            )

            year_results = year_search.execute()
            buckets = year_results.aggregations["by_day"]["buckets"]
            for bucket in buckets:
                current_app.logger.error(f"Processing bucket {pformat(bucket)}")

                index_name = prefix_index(
                    "{0}-{1}".format(
                        self.aggregation_index, bucket["key_as_string"][:4]
                    )
                )
                yield {
                    "_id": "{0}-{1}".format(community_id, bucket["key_as_string"]),
                    "_index": index_name,
                    "_source": self.create_agg_dict(community_id, bucket),
                }

    def run(
        self,
        start_date: datetime.datetime | str | None = None,
        end_date: datetime.datetime | str | None = None,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
    ):
        """Perform the aggregation for a given community's daily records deltas."""
        # If no records have been indexed there is nothing to aggregate
        if not Index(self.event_index, using=self.client).exists():
            return

        previous_bookmark = self.bookmark_api.get_bookmark()
        if not ignore_bookmark:
            lower_limit = (
                arrow.get(start_date).naive if start_date else previous_bookmark
            )
            # Stop here if no bookmark could be estimated.
            if lower_limit is None:
                return
        else:
            lower_limit = (
                arrow.get(start_date).naive if start_date else arrow.utcnow().naive
            )

        end_date = arrow.get(end_date).naive if end_date else end_date
        upper_limit: datetime.datetime = self._upper_limit(end_date)

        next_bookmark = arrow.utcnow().isoformat()

        if self.community_ids:
            all_communities = self.community_ids
        else:
            all_communities = [
                c["id"]
                for c in current_communities.service.read_all(system_identity, [])
            ]

        results = []
        for community_id in all_communities:
            results.append(
                bulk(
                    self.client,
                    self.agg_iter(community_id, lower_limit, upper_limit),
                    stats_only=True,
                    chunk_size=50,
                )
            )
        if update_bookmark:
            self.bookmark_api.set_bookmark(next_bookmark)
        return results
