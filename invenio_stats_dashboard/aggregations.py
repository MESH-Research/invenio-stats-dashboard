from collections import defaultdict
from collections.abc import Generator
from pprint import pformat

import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search
from opensearchpy import OpenSearch
from invenio_stats.aggregations import StatAggregator
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

    def create_agg_dict(self, community_id, community_parent_id, bucket):
        """Create a dictionary representing the aggregation result for indexing."""

        agg_dict = {
            "timestamp": arrow.now().timestamp,
            "community_id": community_id,
            "community_parent_id": community_parent_id,
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
                    "data_volume": (
                        bucket["files"].get("total_bytes", {}).get("value", 0)
                    ),
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
                    for b in bucket["by_periodical"]["buckets"]
                ],
                "by_file_type": [
                    {
                        "id": b.get("key"),
                        "label": {},
                        "added": {
                            "records": b.get("unique_records", {}).get("value", 0),
                            "parents": b.get("unique_parents", {}).get("value", 0),
                            "files": b.get("doc_count", {}).get("value", 0),
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
            "updated_timestamp": arrow.now().timestamp,
        }
        return agg_dict

    def agg_iter(
        self,
        community_id: str,
        community_parent_id: str,
        start_date: str,
        end_date: str,
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

        index_name = prefix_index("stats-community-records-delta")
        search = Search(using=current_search_client, index=index_name)
        search = search.filter("term", parent__communities__ids=community_id)
        search = search.filter(
            "range", updated_timestamp={"gte": start_date, "lte": end_date}
        )
        search.update_from_dict(
            daily_record_delta_query(community_id, start_date, end_date)
        )

        # Use scan (scroll) to allow for more than 10k records
        for set_ in search.scan():
            current_app.logger.error(
                f"Processing page {set_['_id']} "
                f"{pformat(set_['_source']['aggregations']['by_day']['buckets'][0])}"
            )

            buckets = set_["_source"]["aggregations"]["by_day"]["buckets"]
            for bucket in buckets:
                current_app.logger.error(f"Processing bucket {pformat(bucket)}")

                index_name = prefix_index(
                    "stats-community-records-delta-{0}".format(
                        bucket["key_as_string"][:4]
                    )
                )
                yield {
                    "_id": "{0}-{1}".format(community_id, bucket["key_as_string"]),
                    "_index": f"{index_name}-{bucket['key_as_string'][:4]}",
                    "_source": self.create_agg_dict(
                        community_id, community_parent_id, bucket
                    ),
                }

    def run(self, start_date, end_date, update_bookmark=True):
        """Perform the aggregation for a given community's daily records deltas."""

        # If no events have been indexed there is nothing to aggregate
        if not dsl.Index(self.event_index, using=self.client).exists():
            return

        previous_bookmark = self.bookmark_api.get_bookmark()
        lower_limit = (
            start_date or previous_bookmark or self._get_oldest_event_timestamp()
        )
        # Stop here if no bookmark could be estimated.
        if lower_limit is None:
            return

        upper_limit = self._upper_limit(end_date)
        dates = self._split_date_range(lower_limit, upper_limit)
        # Let's get the timestamp before we start the aggregation.
        # This will be used for the next iteration. Some events might be processed twice
        if not end_date:
            end_date = datetime.utcnow().isoformat()

        results = []
        for dt_key, dt in sorted(dates.items()):
            results.append(
                search.helpers.bulk(
                    self.client,
                    self.agg_iter(dt, previous_bookmark),
                    stats_only=True,
                    chunk_size=50,
                )
            )
        if update_bookmark:
            self.bookmark_api.set_bookmark(end_date)
        return results
