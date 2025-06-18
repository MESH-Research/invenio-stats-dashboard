from collections import defaultdict
from collections.abc import Generator
from functools import wraps
from pprint import pformat
from typing import Any, Callable

import datetime

import arrow
from flask import current_app
from invenio_access.permissions import system_identity
from opensearchpy import AttrDict, AttrList
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.bookmark import BookmarkAPI
from opensearchpy.helpers.actions import bulk
from opensearchpy.helpers.aggs import Bucket
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.search import Search
from invenio_stats.aggregations import StatAggregator
from invenio_stats.bookmark import (
    BookmarkAPI,
    SUPPORTED_INTERVALS,
)
from invenio_stats_dashboard.queries import (
    daily_record_cumulative_counts_query,
    daily_record_delta_query,
    daily_usage_delta_query,
)

SUBCOUNT_TYPES = {
    "resource_type": (
        "metadata.resource_type.id",
        "metadata.resource_type.title.en",
    ),
    "access_rights": "access.status",
    "language": ("metadata.languages.id", "metadata.languages.title.en"),
    "affiliation_creator": (
        "metadata.creators.affiliations.id",
        "metadata.creators.affiliations.name.keyword",
    ),
    "affiliation_contributor": (
        "metadata.contributors.affiliations.id",
        "metadata.contributors.affiliations.name.keyword",
    ),
    "funder": (
        "metadata.funding.funder.id",
        "metadata.funding.funder.title.en",
    ),
    "subject": ("metadata.subjects.id", "metadata.subjects.subject"),
    "publisher": "metadata.publisher.keyword",
    "periodical": "custom_fields.journal:journal.title.keyword",
    "file_type": "files.entries.ext",
    "license": ("metadata.rights.id", "metadata.rights.title.en"),
}


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


class CommunityBookmarkAPI(BookmarkAPI):
    """Bookmark API for community statistics aggregators.

    This is a copy of the BookmarkAPI class in invenio-stats, but with the
    community_id added to the index to allow separate bookmarks for each community.
    """

    MAPPINGS = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "date": {"type": "date", "format": "date_optional_time"},
                "aggregation_type": {"type": "keyword"},
                "community_id": {"type": "keyword"},
            },
        }
    }

    @staticmethod
    def _ensure_index_exists(func):
        """Decorator for ensuring the bookmarks index exists."""

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not Index(self.bookmark_index, using=self.client).exists():
                self.client.indices.create(
                    index=self.bookmark_index, body=CommunityBookmarkAPI.MAPPINGS
                )
            return func(self, *args, **kwargs)

        return wrapped

    @_ensure_index_exists
    def set_bookmark(self, community_id: str, value: str):
        """Set the bookmark for a community."""
        self.client.index(
            index=self.bookmark_index,
            body={
                "date": value,
                "aggregation_type": self.agg_type,
                "community_id": community_id,
            },
        )
        self.new_timestamp = None

    @_ensure_index_exists
    def get_bookmark(self, community_id: str, refresh_time=60):
        """Get last aggregation date."""
        # retrieve the oldest bookmark
        query_bookmark = (
            Search(using=self.client, index=self.bookmark_index)
            .query(
                Q(
                    "bool",
                    must=[
                        Q("term", aggregation_type=self.agg_type),
                        Q("term", community_id=community_id),
                    ],
                )
            )
            .sort({"date": {"order": "desc"}})
            .extra(size=1)  # fetch one document only
        )
        bookmark = next(iter(query_bookmark.execute()), None)
        if bookmark:
            my_date = arrow.get(bookmark.date)
            # By default, the bookmark returns a slightly sooner date, to make
            # sure that documents that had arrived before the previous run and
            # where not indexed by the engine are caught in this run. This means
            # that some events might be processed twice
            if refresh_time:
                my_date = my_date.shift(seconds=-refresh_time)
            return my_date


class CommunityAggregatorBase(StatAggregator):
    """Base class for community statistics aggregators."""

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = ""
        self.aggregation_field: str | None = None
        self.copy_fields: dict[str, str] = {}
        self.event_index: str | list[str] | None = None
        self.aggregation_index: str | None = None
        self.community_ids: list[str] = kwargs.get("community_ids", [])
        self.agg_interval = "day"
        self.client = kwargs.get("client") or current_search_client
        self.bookmark_api = CommunityBookmarkAPI(
            self.client, self.name, self.agg_interval
        )

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        raise NotImplementedError

    def run(
        self,
        start_date: datetime.datetime | str | None = None,
        end_date: datetime.datetime | str | None = None,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
        return_results: bool = False,
    ) -> list[tuple[int, int | list[dict]]]:
        """Perform an aggregation for community and global stats.

        This method will perform an aggregation as defined by the child class.

        It maintains a separate bookmark for each community as well as for the
        InvenioRDM instance as a whole.

        Args:
            start_date: The start date for the aggregation.
            end_date: The end date for the aggregation.
            update_bookmark: Whether to update the bookmark.
            ignore_bookmark: Whether to ignore the bookmark.
            return_results: Whether to return the error results from the bulk
                aggregation or only the error count. This is primarily used in testing.

        Returns:
            A list of tuples representing results from the bulk aggregation. If
            return_results is True, the first element of the tuple is the number of
            records indexed and the second element is the number of errors. If
            return_results is False, the first element of the tuple is the number of
            records indexed and the second element is a list of dictionaries, where
            each dictionary describes an error.
        """
        # If no records have been indexed there is nothing to aggregate
        if (
            isinstance(self.event_index, str)
            and not Index(self.event_index, using=self.client).exists()
        ):
            return [(0, [])]
        elif isinstance(self.event_index, list):
            for label, index in self.event_index:
                if not Index(index, using=self.client).exists():
                    return [(0, [])]

        if self.community_ids:
            all_communities = self.community_ids
        else:
            all_communities = [
                c["id"]
                for c in current_communities.service.read_all(system_identity, [])
            ]
        all_communities.append("global")  # Global stats are always aggregated

        results = []
        for community_id in all_communities:

            previous_bookmark = self.bookmark_api.get_bookmark(community_id)
            if not ignore_bookmark:
                if start_date:
                    lower_limit = arrow.get(start_date).naive
                elif previous_bookmark:
                    lower_limit = arrow.get(previous_bookmark).naive
                else:
                    lower_limit = arrow.utcnow().naive
            else:
                lower_limit = (
                    arrow.get(start_date).naive if start_date else arrow.utcnow().naive
                )

            end_date = arrow.get(end_date).naive if end_date else end_date
            upper_limit: datetime.datetime = self._upper_limit(end_date)

            next_bookmark = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS")
            current_app.logger.error(
                f"Lower limit: {lower_limit}, upper limit: {upper_limit}"
                f"for community {community_id}"
            )

            results.append(
                bulk(
                    self.client,
                    self.agg_iter(community_id, lower_limit, upper_limit),
                    stats_only=False if return_results else True,
                    chunk_size=50,
                )
            )
            if update_bookmark:
                self.bookmark_api.set_bookmark(community_id, next_bookmark)

        return results

    def delete_aggregation(
        self,
        index_name: str,
        document_id: str,
    ):
        """Remove the aggregation for a given community and date."""
        self.client.delete(index=index_name, id=document_id)
        self.client.indices.refresh(index=index_name)

    def _get_nested_value(
        self, data: dict | AttrDict, path: list, key: str | None = None
    ) -> Any:
        """Get a nested value from a dictionary using a list of path segments.

        Args:
            data: The dictionary to traverse
            path: List of path segments to traverse
            key: Optional key to match when traversing arrays

        Returns:
            The value at the end of the path, or an empty dict if not found
        """
        current = data
        for idx, segment in enumerate(path):
            if isinstance(current, dict) or isinstance(current, AttrDict):
                current = current.get(segment, {})
            elif isinstance(current, list) or isinstance(current, AttrList):
                # For arrays, we sometimes need to find the item that matches our key
                # This is used for fields like subjects where we need to match the specific subject
                if key is not None:
                    matching_items = [
                        item
                        for item in current
                        if isinstance(item, dict) and item.get("id") == key
                    ]
                    current = matching_items[0] if matching_items else {}
                elif isinstance(segment, int):
                    current = current[segment]
                elif isinstance(current, list):
                    current = current[0] if current else {}
            elif idx == len(path) - 1:
                return current
            else:
                return {}
        return current


class CommunityRecordsSnapshotAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-records-snapshot")

    def create_agg_dict(
        self,
        current_day: arrow.Arrow,
        community_id: str,
        added_bucket: dict,
        removed_bucket: dict,
    ) -> dict:
        """Create a dictionary representing the aggregation result for indexing."""

        def make_file_type_dict():
            combined_keys = list(
                set(
                    b.key
                    for b in added_bucket.get("by_file_type", {}).get("buckets", [])
                    if b.key != "doc_count"
                )
                | set(
                    b.key
                    for b in removed_bucket.get("by_file_type", {}).get("buckets", [])
                    if b.key != "doc_count"
                )
            )
            file_type_list = []
            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        added_bucket.get("by_file_type", {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        removed_bucket.get("by_file_type", {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                file_type_list.append(
                    {
                        "id": key,
                        "label": {},
                        "record_count": (
                            added.get("unique_records", {}).get("value", 0)
                            - removed.get("unique_records", {}).get("value", 0)
                        ),
                        "parent_count": (
                            added.get("unique_parents", {}).get("value", 0)
                            - removed.get("unique_parents", {}).get("value", 0)
                        ),
                        "file_count": (
                            added.get("doc_count", 0) - removed.get("doc_count", 0)
                        ),
                        "data_volume": (
                            added.get("total_bytes", {}).get("value", 0)
                            - removed.get("total_bytes", {}).get("value", 0)
                        ),
                    }
                )
            return file_type_list

        def make_subcount_dict(subcount_type):
            combined_keys = list(
                set(
                    b.key
                    for b in added_bucket.get(subcount_type, {}).get("buckets", [])
                    if b.key != "doc_count"
                )
                | set(
                    b.key
                    for b in removed_bucket.get(subcount_type, {}).get("buckets", [])
                    if b.key != "doc_count"
                )
            )
            subcount_list = []

            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        added_bucket.get(subcount_type, {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        removed_bucket.get(subcount_type, {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                label_field = SUBCOUNT_TYPES[subcount_type][1]
                label_path = (
                    f"label.hits.hits.0._source.{label_field}".split(".")
                    if len(SUBCOUNT_TYPES[subcount_type]) > 1
                    else None
                )
                # For subjects, we need to find the subject that matches the key
                if subcount_type == "subject" and label_path:
                    label = self._get_nested_value(
                        added,
                        ["label", "hits", "hits", 0, "_source", "metadata", "subjects"],
                        key=key,
                    ).get("subject", {})
                else:
                    label = (
                        self._get_nested_value(added, label_path) if label_path else {}
                    )
                subcount_list.append(
                    {
                        "id": key,
                        "label": label,
                        "record_count": {
                            "metadata_only": (
                                added.get("without_files", {}).get("doc_count", 0)
                                - removed.get("without_files", {}).get("doc_count", 0)
                            ),
                            "with_files": (
                                added.get("with_files", {}).get("doc_count", 0)
                                - removed.get("with_files", {}).get("doc_count", 0)
                            ),
                        },
                        "parent_count": {
                            "metadata_only": (
                                added.get("without_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                                - removed.get("without_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                            ),
                            "with_files": (
                                added.get("with_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                                - removed.get("with_files", {})
                                .get("unique_parents", {})
                                .get("value", 0)
                            ),
                        },
                        "files": {
                            "file_count": (
                                added.get("file_count", {}).get("value", 0)
                                - removed.get("file_count", {}).get("value", 0)
                            ),
                            "data_volume": (
                                added.get("total_bytes", {}).get("value", 0)
                                - removed.get("total_bytes", {}).get("value", 0)
                            ),
                        },
                    }
                )
            return subcount_list

        agg_dict = {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "snapshot_date": current_day.format("YYYY-MM-DD"),
            "total_records": {
                "metadata_only": (
                    added_bucket.get("without_files", {}).get("doc_count", 0)
                    - removed_bucket.get("without_files", {}).get("doc_count", 0)
                ),
                "with_files": (
                    added_bucket.get("with_files", {}).get("doc_count", 0)
                    - removed_bucket.get("with_files", {}).get("doc_count", 0)
                ),
            },
            "total_parents": {
                "metadata_only": (
                    added_bucket.get("without_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                    - removed_bucket.get("without_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                ),
                "with_files": (
                    added_bucket.get("with_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                    - removed_bucket.get("with_files", {})
                    .get("unique_parents", {})
                    .get("value", 0)
                ),
            },
            "total_files": {
                "file_count": (
                    added_bucket.get("file_count", {}).get("value", 0)
                    - removed_bucket.get("file_count", {}).get("value", 0)
                ),
                "data_volume": (
                    added_bucket.get("total_bytes", {}).get("value", 0)
                    - removed_bucket.get("total_bytes", {}).get("value", 0)
                ),
            },
            "total_uploaders": (
                added_bucket.get("uploaders", {}).get("value", 0)
                - removed_bucket.get("uploaders", {}).get("value", 0)
            ),
            "subcounts": {
                "all_resource_types": make_subcount_dict("by_resource_type"),
                "all_access_rights": make_subcount_dict("by_access_rights"),
                "all_languages": make_subcount_dict("by_language"),
                "top_affiliations_creator": make_subcount_dict(
                    "by_affiliation_creator"
                ),
                "top_affiliations_contributor": make_subcount_dict(
                    "by_affiliation_contributor"
                ),
                "top_funders": make_subcount_dict("by_funder"),
                "top_subjects": make_subcount_dict("by_subject"),
                "top_publishers": make_subcount_dict("by_publisher"),
                "top_periodicals": make_subcount_dict("by_periodical"),
                "all_licenses": make_subcount_dict("by_license"),
                "all_file_types": make_file_type_dict(),
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }
        return agg_dict

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing.

        Args:
            community_id: The ID of the community to aggregate.
            start_date: The start date for the aggregation.
            end_date: The end date for the aggregation.

        Returns:
            A generator of dictionaries, where each dictionary is an aggregation
            document for a single day to be indexed.
        """

        # Make sure we don't miss any old records
        earliest_date = arrow.get("1900-01-01").floor("day")
        current_iteration_date = arrow.get(start_date)

        while current_iteration_date <= arrow.get(end_date):

            snapshot_added_search = Search(using=self.client, index=self.event_index)

            snapshot_query_added = daily_record_cumulative_counts_query(
                earliest_date.format("YYYY-MM-DD"),
                current_iteration_date.format("YYYY-MM-DD"),
                community_id=community_id,
            )
            snapshot_added_search.update_from_dict(snapshot_query_added)

            snapshot_results_added = snapshot_added_search.execute()
            buckets_added = snapshot_results_added.aggregations

            snapshot_removed_search = Search(using=self.client, index=self.event_index)

            snapshot_query_removed = daily_record_cumulative_counts_query(
                earliest_date.format("YYYY-MM-DD"),
                current_iteration_date.format("YYYY-MM-DD"),
                community_id=community_id,
                find_deleted=True,
            )
            snapshot_removed_search.update_from_dict(snapshot_query_removed)

            snapshot_results_removed = snapshot_removed_search.execute()
            buckets_removed = snapshot_results_removed.aggregations

            index_name = prefix_index(
                "{0}-{1}".format(self.aggregation_index, current_iteration_date.year)
            )
            document_id = (
                f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
            )
            # Check if an aggregation already exists for this date
            # If it does, delete it (we'll re-create it below)
            if self.client.exists(index=index_name, id=document_id):
                self.delete_aggregation(index_name, document_id)

            yield {
                "_id": "{0}-{1}".format(
                    community_id, current_iteration_date.format("YYYY-MM-DD")
                ),
                "_index": index_name,
                "_source": self.create_agg_dict(
                    community_id, current_iteration_date, buckets_added, buckets_removed
                ),
            }

            current_iteration_date = current_iteration_date.shift(days=1)


class CommunityUsageSnapshotAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("stats-community-usage-delta")
        self.aggregation_index = prefix_index("stats-community-usage-snapshot")

    def _create_aggregation_doc(
        self, community_id: str, date: arrow.Arrow, cumulative_totals: dict
    ) -> dict:
        """Create the final aggregation document from cumulative totals."""
        return {
            "community_id": community_id,
            "period_start": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "totals": cumulative_totals,
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }

    def _get_daily_deltas(
        self, community_id: str, start_date: arrow.Arrow, end_date: arrow.Arrow
    ) -> list:
        """Get daily delta records for a community between start and end dates."""
        search = Search(using=self.client, index=self.event_index)
        search = search.filter("term", community_id=community_id)
        search = search.filter(
            "range",
            period_start={
                "gte": start_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            },
        )
        search = search.sort("period_start")
        return list(search.scan())

    def _update_cumulative_totals(self, current_totals: dict, delta_doc: dict) -> dict:
        """Update cumulative totals with values from a daily delta document."""
        if not current_totals:
            # Initialize totals from first delta
            return {
                "views": {
                    "total": delta_doc["totals"]["views"]["total"],
                    "unique_visitors": delta_doc["totals"]["views"]["unique_visitors"],
                    "unique_records": delta_doc["totals"]["views"]["unique_records"],
                    "unique_parents": delta_doc["totals"]["views"]["unique_parents"],
                },
                "downloads": {
                    "total": delta_doc["totals"]["downloads"]["total"],
                    "unique_visitors": delta_doc["totals"]["downloads"][
                        "unique_visitors"
                    ],
                    "unique_records": delta_doc["totals"]["downloads"][
                        "unique_records"
                    ],
                    "unique_parents": delta_doc["totals"]["downloads"][
                        "unique_parents"
                    ],
                    "unique_files": delta_doc["totals"]["downloads"]["unique_files"],
                    "total_volume": delta_doc["totals"]["downloads"]["total_volume"],
                },
            }

        # Add delta values to current totals
        current_totals["views"]["total"] += delta_doc["totals"]["views"]["total"]
        current_totals["views"]["unique_visitors"] = max(
            current_totals["views"]["unique_visitors"],
            delta_doc["totals"]["views"]["unique_visitors"],
        )
        current_totals["views"]["unique_records"] = max(
            current_totals["views"]["unique_records"],
            delta_doc["totals"]["views"]["unique_records"],
        )
        current_totals["views"]["unique_parents"] = max(
            current_totals["views"]["unique_parents"],
            delta_doc["totals"]["views"]["unique_parents"],
        )

        current_totals["downloads"]["total"] += delta_doc["totals"]["downloads"][
            "total"
        ]
        current_totals["downloads"]["unique_visitors"] = max(
            current_totals["downloads"]["unique_visitors"],
            delta_doc["totals"]["downloads"]["unique_visitors"],
        )
        current_totals["downloads"]["unique_records"] = max(
            current_totals["downloads"]["unique_records"],
            delta_doc["totals"]["downloads"]["unique_records"],
        )
        current_totals["downloads"]["unique_parents"] = max(
            current_totals["downloads"]["unique_parents"],
            delta_doc["totals"]["downloads"]["unique_parents"],
        )
        current_totals["downloads"]["unique_files"] = max(
            current_totals["downloads"]["unique_files"],
            delta_doc["totals"]["downloads"]["unique_files"],
        )
        current_totals["downloads"]["total_volume"] += delta_doc["totals"]["downloads"][
            "total_volume"
        ]

        return current_totals

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
    ) -> Generator[dict, None, None]:
        """Create cumulative totals from daily usage deltas."""
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)

        # Get last snapshot document for the community
        last_snapshot_search = (
            Search(using=self.client, index=self.aggregation_index)
            .query(
                Q(
                    "bool",
                    must=[
                        Q("term", community_id=community_id),
                        Q(
                            "range",
                            period_start={
                                "lte": (
                                    end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss")
                                )
                            },
                        ),
                    ],
                ),
            )
            .sort("period_start", order="desc")
            .extra(size=1)
        )  # fetch one document only
        last_snapshot_results = last_snapshot_search.execute()
        if not last_snapshot_results.hits.hits:
            last_snapshot_document = None
        else:
            last_snapshot_document = last_snapshot_results.hits.hits[0]
            last_snapshot_document = last_snapshot_document.to_dict()
            current_app.logger.error(
                f"Last snapshot document: {pformat(last_snapshot_document)}"
            )

        # Get all daily delta records for the community
        delta_records = self._get_daily_deltas(community_id, start_date, end_date)
        if not delta_records:
            return

        # Initialize cumulative totals
        cumulative_totals = (
            last_snapshot_document["_source"]["totals"]
            if last_snapshot_document
            else {}
        )
        current_iteration_date = start_date

        while current_iteration_date <= end_date:
            # Update cumulative totals with any delta records for the current day
            for delta in delta_records:
                delta_date = arrow.get(delta.period_start)
                if delta_date.floor("day") == current_iteration_date.floor("day"):
                    cumulative_totals = self._update_cumulative_totals(
                        cumulative_totals, delta.to_dict()
                    )

            # Create and yield the snapshot document for the current day
            index_name = prefix_index(
                f"{self.aggregation_index}-{current_iteration_date.year}"
            )
            document_id = (
                f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
            )

            # Check if an aggregation already exists for this date
            # If it does, delete it (we'll re-create it below)
            if self.client.exists(index=index_name, id=document_id):
                self.delete_aggregation(index_name, document_id)

            yield {
                "_id": document_id,
                "_index": index_name,
                "_source": self._create_aggregation_doc(
                    community_id, current_iteration_date, cumulative_totals
                ),
            }

            current_iteration_date = current_iteration_date.shift(days=1)


class CommunityUsageDeltaAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = [
            ("view", prefix_index("events-stats-record-view")),
            ("download", prefix_index("events-stats-file-download")),
        ]
        self.aggregation_index = prefix_index("stats-community-usage-delta")

    def _create_temp_index(self, temp_index: str) -> None:
        """Create temporary index with appropriate mappings."""
        self.client.indices.create(
            index=temp_index,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "record_id": {"type": "keyword"},
                        "parent_record_id": {"type": "keyword"},
                        "community_id": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "via_api": {"type": "boolean"},
                        "is_robot": {"type": "boolean"},
                        "visitor_id": {"type": "keyword"},
                        "event_type": {"type": "keyword"},
                        "size": {"type": "long"},
                        "file_key": {"type": "keyword"},
                        "file_id": {"type": "keyword"},
                        "file_type": {"type": "keyword"},
                        "country": {"type": "keyword"},
                        "referrer": {"type": "keyword"},
                        "resource_type": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "publisher": {"type": "keyword"},
                        "access_rights": {"type": "keyword"},
                        "languages": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "subjects": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "licenses": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "affiliations": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "name": {"type": "keyword"},
                                "identifiers": {"type": "keyword"},
                            },
                        },
                        "funders": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "title": {"type": "keyword"},
                            },
                        },
                        "periodical": {"type": "keyword"},
                    }
                },
            },
            ignore=400,
        )

    def _process_event_type(
        self,
        temp_index: str,
        community_id: str,
        date: arrow.Arrow,
        event_type: str,
        event_index: str,
    ) -> None:
        """Process events of a specific type for a given date using aggregations.

        Page through the indexed events grouped by record id and enrich the results
        with metadata about the record involved in the event. (The grouping allows us
        to retrieve record metadata in batches and only once per record.) We then
        create a new document in the temporary index for each event with its enriched
        metadata.

        If the community_id is "global", we will process all events in the event
        index without restricting by community. Restriction by community is performed
        when we search for the record metadata matching the event's record id, since
        the record's communities are not stored in the event index.

        Parameters:
        - temp_index: The name of the temporary index to use for the enriched documents
        - community_id: The ID of the community to process events for or "global".
        - date: The date to process events for
        - event_type: The type of event to process
        - event_index: The name of the index to search for events

        Returns:
        - None
        """
        after_key = None
        page = 0
        while True:
            current_app.logger.error(
                f"Processing page {page} for {event_type} on "
                f"{date.format('YYYY-MM-DD')}"
            )

            search = Search(using=self.client, index=event_index)
            search = search.filter(
                "range",
                timestamp={
                    "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )
            current_app.logger.error(
                f"Event search found {search.count()} events for {event_type} on "
                f"{date.format('YYYY-MM-DD')}"
            )

            # Use composite aggregation to group by recid with pagination
            composite_params = {
                "sources": [
                    {
                        "recid": {
                            "terms": {
                                "field": "recid",
                            }
                        }
                    }
                ],
                "size": 1000,
            }
            if after_key:
                composite_params["after"] = after_key

            search.aggs.bucket("by_record", "composite", **composite_params)

            response = search.execute()
            buckets = response.aggregations.by_record.buckets

            if not buckets:
                current_app.logger.info(
                    f"No more buckets found for {event_type} on "
                    f"{date.format('YYYY-MM-DD')}"
                )
                break
            current_app.logger.error(f"Bucket 0: {pformat(buckets[0].to_dict())}")

            current_app.logger.error(f"Found {len(buckets)} buckets on page {page}")

            # Get record IDs from this page of buckets
            record_ids = {bucket.key.recid for bucket in buckets}
            current_app.logger.error(f"Record IDs: {pformat(record_ids)}")

            hits_search = Search(using=self.client, index=event_index)
            hits_search = hits_search.filter(
                "range",
                timestamp={
                    "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )
            hits_search = hits_search.filter("terms", recid=list(record_ids))
            current_app.logger.error(f"Hits search count: {hits_search.count()}")

            hits_by_recid = defaultdict(list)
            for hit in hits_search.scan():
                hits_by_recid[hit["recid"]].append(hit)

            # Filter for community here if not global
            meta_for_recids = self._get_metadata_for_records(community_id, record_ids)
            record_ids = {i for i in meta_for_recids.keys()}

            if len(record_ids):
                docs = self._create_enriched_docs_from_aggs(
                    record_ids,
                    meta_for_recids,
                    temp_index,
                    community_id,
                    event_type,
                    hits_by_recid,
                )

                if docs:
                    bulk(self.client, docs)
                    current_app.logger.error(f"Bulk indexed {len(docs)} documents")
                    current_app.logger.error(f"Doc 0: {pformat(docs[0])}")
                    # Force a refresh to make the documents searchable
                    self.client.indices.refresh(index=temp_index)

            # Get the after_key for the next page of per_recid aggregation buckets
            after_key = response.aggregations.by_record.after_key if buckets else None
            if not after_key:
                current_app.logger.error(
                    f"No more after_key for {event_type} on {date.format('YYYY-MM-DD')}"
                )
                break

            page += 1

    def _get_metadata_for_records(
        self, community_id: str, record_ids: set[str]
    ) -> dict:
        """Get metadata for a set of record IDs."""
        meta_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        meta_search = meta_search.filter("terms", id=list(record_ids))
        if community_id != "global":
            meta_search = meta_search.filter(
                "term", parent__communities__ids=community_id
            )
        meta_search = meta_search.source(
            [
                "access.status",
                "custom_fields.journal:journal.title.keyword",
                "files.types",
                "id",
                "metadata.resource_type.id",
                "metadata.resource_type.title.en",
                "metadata.languages.id",
                "metadata.languages.title.en",
                "metadata.subjects.id",
                "metadata.subjects.subject",
                "metadata.publisher",
                "metadata.rights.id",
                "metadata.rights.title.en",
                "metadata.creators.affiliations.id",
                "metadata.creators.affiliations.name.keyword",
                "metadata.contributors.affiliations.id",
                "metadata.contributors.affiliations.name.keyword",
                "metadata.funding.funder.id",
                "metadata.funding.funder.title.en",
            ]
        )
        return {hit.id: hit for hit in meta_search.scan()}

    def _create_enriched_docs_from_aggs(
        self,
        record_ids: set[str],
        meta_for_recids: dict,
        temp_index: str,
        community_id: str,
        event_type: str,
        hits_by_recid: dict[str, list],
    ) -> list:
        """Create enriched documents from aggregation buckets."""
        docs = []
        for recid in record_ids:
            meta = meta_for_recids.get(recid)
            if not meta:
                continue

            # Create one document per hit with the same recid
            for hit in hits_by_recid[recid]:
                doc = {
                    "_index": temp_index,
                    "_source": {
                        "record_id": recid,
                        "parent_record_id": hit["parent_recid"],
                        "community_id": community_id,
                        "timestamp": hit["timestamp"],
                        "via_api": hit["via_api"],
                        "is_robot": hit["is_robot"],
                        "visitor_id": hit["visitor_id"],
                        "event_type": event_type,
                        "resource_type": {
                            "id": meta.metadata.resource_type.id,
                            "title": meta.metadata.resource_type.title.en,
                        },
                        "publisher": meta.metadata.publisher,
                        "access_rights": meta.access.status,
                        "languages": [
                            {
                                "id": lang.id,
                                "title": lang.title.en,
                            }
                            for lang in getattr(meta.metadata, "languages", [])
                        ],
                        "subjects": [
                            {
                                "id": subject.id,
                                "title": subject.subject,
                            }
                            for subject in getattr(meta.metadata, "subjects", [])
                        ],
                        "licenses": [
                            {
                                "id": right.id,
                                "title": right.title.en,
                            }
                            for right in getattr(meta.metadata, "rights", [])
                        ],
                        "funders": [
                            {
                                "id": funder.id,
                                "title": funder.title.en,
                            }
                            for funder in getattr(meta.metadata, "funding", {}).get(
                                "funder", []
                            )
                        ],
                    },
                }

                for contributor in list(getattr(meta.metadata, "creators", [])) + list(
                    getattr(meta.metadata, "contributors", [])
                ):
                    if contributor.get("affiliations"):
                        for affiliation in contributor.get("affiliations", []):
                            doc["_source"].setdefault("affiliations", []).append(
                                {
                                    "id": affiliation.get("id", ""),
                                    "name": affiliation.get("name", ""),
                                    "identifiers": affiliation.get("identifiers", []),
                                }
                            )

                if hasattr(meta, "custom_fields"):
                    doc["_source"]["periodical"] = meta.custom_fields.get(
                        "journal:journal.title.keyword", {}
                    )

                if event_type == "view":
                    file_types = getattr(meta, "files", {}).get("types", [])
                    # Convert AttrList to regular list if needed
                    file_types = list(file_types)
                    doc["_source"]["file_type"] = file_types

                if event_type == "download":
                    doc["_source"]["referrer"] = hit["referrer"]
                    doc["_source"]["country"] = hit["country"]
                    doc["_source"]["size"] = hit["size"]
                    doc["_source"]["file_id"] = hit["file_id"]
                    doc["_source"]["file_type"] = [hit["file_key"].split(".")[-1]]

                docs.append(doc)
        return docs

    def _add_metrics_to_agg(self, agg_bucket, event_type):
        """Add common metrics to an aggregation bucket."""
        agg_bucket.metric(
            "unique_visitors",
            "cardinality",
            field="visitor_id",
        ).metric(
            "unique_records",
            "cardinality",
            field="record_id",
        ).metric(
            "unique_parents",
            "cardinality",
            field="parent_record_id",
        )

        # Only add file-related metrics for download events
        if event_type == "download":
            agg_bucket.metric(
                "unique_files",
                "cardinality",
                field="file_id",
            ).metric(
                "total_volume",
                "sum",
                field="size",
            )

        return agg_bucket

    def add_search_agg(
        self,
        agg_search: Search,
        agg_name: str,
        agg_field: str | None = None,
        title_field: str | list[str] | None = None,
        field_bucket: Bucket | None = None,
    ):
        """Add a search aggregation to the search object."""
        # Create the field aggregation first
        field_bucket = field_bucket or agg_search.aggs.bucket(
            agg_name,
            "terms",
            field=agg_field,
            size=1000,
        )

        # Add event type aggregation under each field value
        for event_type in ["view", "download"]:
            event_bucket = field_bucket.bucket(
                event_type,
                "filter",
                term={"event_type": event_type},
            )

            # Add metrics to the event type bucket
            self._add_metrics_to_agg(event_bucket, event_type)

        # Add title field if specified
        if title_field:
            field_bucket.bucket(
                "title",
                "top_hits",
                size=1,
                _source={"includes": title_field},
                sort=[{"_score": "desc"}],
            )

        return agg_search

    def _temp_index_search_query(
        self, temp_index: str, date: arrow.Arrow, community_id: str
    ) -> Search:
        """Create a search query for the temporary index."""
        agg_search = Search(using=self.client, index=temp_index)
        must_clauses = [
            Q(
                "range",
                timestamp={
                    "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                    "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
                },
            )
        ]
        if community_id != "global":
            must_clauses.append(Q("term", community_id=community_id))

        agg_search = agg_search.query(Q("bool", must=must_clauses))
        current_app.logger.error(
            f"Counting {agg_search.count()} records in temp index {temp_index}"
        )

        self.add_search_agg(
            agg_search,
            "by_resource_type",
            "resource_type.id",
            ["resource_type.title", "resource_type.id"],
        )
        self.add_search_agg(agg_search, "by_access_rights", "access_rights", None)
        self.add_search_agg(
            agg_search,
            "by_language",
            "languages.id",
            ["languages.title", "languages.id"],
        )
        self.add_search_agg(
            agg_search, "by_subject", "subjects.id", ["subjects.title", "subjects.id"]
        )
        self.add_search_agg(
            agg_search, "by_license", "licenses.id", ["licenses.title", "licenses.id"]
        )
        self.add_search_agg(
            agg_search, "by_funder", "funders.id", ["funders.title", "funders.id"]
        )
        self.add_search_agg(agg_search, "by_periodical", "periodical", None)
        self.add_search_agg(agg_search, "by_publisher", "publisher", None)
        self.add_search_agg(agg_search, "by_file_type", "file_type", None)
        self.add_search_agg(agg_search, "by_country", "country", None)
        self.add_search_agg(agg_search, "by_referrer", "referrer", None)

        # Aggregate by affiliation
        affiliation_agg = agg_search.aggs.bucket(
            "by_affiliation",
            "composite",
            size=100,
            sources=[
                {"id": {"terms": {"field": "affiliations.id"}}},
                {"name": {"terms": {"field": "affiliations.name"}}},
            ],
        )
        self.add_search_agg(
            agg_search,
            "by_affiliation",
            agg_field=None,
            title_field=None,
            field_bucket=affiliation_agg,
        )

        # Add top-level metrics
        for event_type in ["view", "download"]:
            event_bucket = agg_search.aggs.bucket(
                event_type,
                "filter",
                term={"event_type": event_type},
            )

            # Add metrics to the event type bucket
            self._add_metrics_to_agg(event_bucket, event_type)

        return agg_search

    def _create_aggregation_doc(
        self, temp_index: str, community_id: str, date: arrow.Arrow
    ) -> dict:
        """Create the final aggregation document from the temporary index."""

        agg_search = self._temp_index_search_query(temp_index, date, community_id)
        results = agg_search.execute()

        # current_app.logger.error(f"Results: {pformat(results.aggregations.to_dict())}")

        # Get top-level metrics
        views_bucket = results.aggregations.view if results.aggregations.view else None
        downloads_bucket = (
            results.aggregations.download if results.aggregations.download else None
        )

        def add_subcount_to_doc(
            buckets: list, title_path: list | None | Callable = None
        ) -> list[dict]:
            """Add a subcount to the daily usage delta document."""
            subcount_list = []
            for bucket in buckets:
                field_value = bucket["key"]
                field_label = ""

                # Get title if available
                if title_path:
                    if callable(title_path):
                        field_label = title_path(bucket)
                    else:
                        title_hits = (
                            bucket.get("title", {}).get("hits", {}).get("hits", [])
                        )
                        if title_hits and title_hits[0].get("_source"):
                            source = title_hits[0]["_source"]
                            if (
                                0 in title_path
                                and title_path.index(0) != len(title_path) - 1
                            ):
                                pivot = title_path.index(0)
                                category_path, item_path = (
                                    title_path[:pivot],
                                    title_path[pivot + 1 :],  # noqa: E203
                                )
                                item = [
                                    i
                                    for i in self._get_nested_value(
                                        source, category_path
                                    )
                                    if i.get("id") == bucket.get("key")
                                ][0]
                                field_label = self._get_nested_value(item, item_path)
                            else:
                                field_label = self._get_nested_value(source, title_path)

                # Get metrics for each event type
                metrics = {}
                for event_type in ["view", "download"]:
                    if event_type in bucket:
                        event_bucket = bucket[event_type]
                        metrics[event_type] = {
                            "total_events": event_bucket["doc_count"],
                            "unique_visitors": event_bucket["unique_visitors"]["value"],
                            "unique_records": event_bucket["unique_records"]["value"],
                            "unique_parents": event_bucket["unique_parents"]["value"],
                        }
                        if event_type == "download":
                            metrics[event_type]["unique_files"] = event_bucket[
                                "unique_files"
                            ]["value"]
                            metrics[event_type]["total_volume"] = event_bucket[
                                "total_volume"
                            ]["value"]

                # Add to results
                subcount_list.append(
                    {
                        "id": (
                            field_value
                            if isinstance(field_value, str)
                            else field_value.id
                        ),
                        "label": field_label,
                        **metrics,
                    }
                )
            return subcount_list

        final_dict = {
            "community_id": community_id,
            "period_start": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "totals": {
                "views": {
                    "total": views_bucket.doc_count if views_bucket else 0,
                    "unique_visitors": (
                        views_bucket.unique_visitors.value if views_bucket else 0
                    ),
                    "unique_records": (
                        views_bucket.unique_records.value if views_bucket else 0
                    ),
                    "unique_parents": (
                        views_bucket.unique_parents.value if views_bucket else 0
                    ),
                },
                "downloads": {
                    "total": downloads_bucket.doc_count if downloads_bucket else 0,
                    "unique_visitors": (
                        downloads_bucket.unique_visitors.value
                        if downloads_bucket
                        else 0
                    ),
                    "unique_records": (
                        downloads_bucket.unique_records.value if downloads_bucket else 0
                    ),
                    "unique_parents": (
                        downloads_bucket.unique_parents.value if downloads_bucket else 0
                    ),
                    "unique_files": (
                        downloads_bucket.unique_files.value if downloads_bucket else 0
                    ),
                    "total_volume": (
                        downloads_bucket.total_volume.value if downloads_bucket else 0
                    ),
                },
            },
            "subcounts": {
                "by_resource_type": add_subcount_to_doc(
                    results.aggregations.by_resource_type.buckets,
                    ["resource_type", "title"],
                ),
                "by_license": add_subcount_to_doc(
                    results.aggregations.by_license.buckets,
                    ["licenses", 0, "title"],
                ),
                "by_funder": add_subcount_to_doc(
                    results.aggregations.by_funder.buckets,
                    ["funders", 0, "title"],
                ),
                "by_periodical": add_subcount_to_doc(
                    results.aggregations.by_periodical.buckets
                ),
                "by_language": add_subcount_to_doc(
                    results.aggregations.by_language.buckets,
                    [
                        "languages",
                        0,
                        "title",
                    ],  # SUBCOUNT_TYPES["language"][1].split("."),
                ),
                "by_subject": add_subcount_to_doc(
                    results.aggregations.by_subject.buckets,
                    ["subjects", 0, "title"],
                ),
                "by_publisher": add_subcount_to_doc(
                    results.aggregations.by_publisher.buckets
                ),
                "by_affiliation": add_subcount_to_doc(
                    results.aggregations.by_affiliation.buckets,
                    lambda aff_bucket: aff_bucket.get("key", {}).get("name"),
                ),
                "by_country": add_subcount_to_doc(
                    results.aggregations.by_country.buckets, None
                ),
                "by_referrer": add_subcount_to_doc(
                    results.aggregations.by_referrer.buckets
                ),
                "by_file_type": add_subcount_to_doc(
                    results.aggregations.by_file_type.buckets,
                ),
            },
        }

        return final_dict

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)
        temp_index = prefix_index(
            f"temp-usage-stats-{community_id}-"
            f"{arrow.utcnow().format('YYYY-MM-DD-HH-mm-ss')}"
        )

        # Clean up any existing temporary indices for this community
        existing_indices = self.client.indices.get_alias(
            prefix_index(f"temp-usage-stats-{community_id}-*")
        )
        for index_name in existing_indices:
            self.client.indices.delete(index=index_name, ignore=[400, 404])

        try:
            self._create_temp_index(temp_index)
            current_iteration_date = start_date

            while current_iteration_date <= end_date:
                current_app.logger.error(
                    f"Processing date: {current_iteration_date} for community {community_id}"
                )
                for event_type, event_index in self.event_index:
                    self._process_event_type(
                        temp_index,
                        community_id,
                        current_iteration_date,
                        event_type,
                        event_index,
                    )

                agg_doc = self._create_aggregation_doc(
                    temp_index, community_id, current_iteration_date
                )

                index_name = prefix_index(
                    "{0}-{1}".format(
                        self.aggregation_index, current_iteration_date.year
                    )
                )
                doc_id = f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
                if self.client.exists(index=index_name, id=doc_id):
                    self.delete_aggregation(index_name, doc_id)

                yield {
                    "_id": doc_id,
                    "_index": index_name,
                    "_source": agg_doc,
                }

                current_iteration_date = current_iteration_date.shift(days=1)

        finally:
            # Clean up temporary index
            self.client.indices.delete(index=temp_index, ignore=[400, 404])


class CommunityRecordsDeltaAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-records-delta")

    def create_agg_dict(
        self,
        community_id: str,
        current_day: arrow.Arrow,
        added_bucket: dict,
        removed_bucket: dict,
    ) -> dict:
        """Create a dictionary representing the aggregation result for indexing."""

        def make_file_type_dict():
            combined_keys = list(
                set(
                    b.key
                    for b in added_bucket.get("by_file_type", {}).get("buckets", [])
                    if b.key != "doc_count"
                )
                | set(
                    b.key
                    for b in removed_bucket.get("by_file_type", {}).get("buckets", [])
                    if b.key != "doc_count"
                )
            )
            file_type_list = []
            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        added_bucket.get("by_file_type", {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        removed_bucket.get("by_file_type", {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                file_type_list.append(
                    {
                        "id": key,
                        "label": {},
                        "added": {
                            "records": added.get("unique_records", {}).get("value", 0),
                            "parents": added.get("unique_parents", {}).get("value", 0),
                            "files": added.get("doc_count", 0),
                            "data_volume": added.get("total_bytes", {}).get("value", 0),
                        },
                        "removed": {
                            "records": (
                                removed.get("unique_records", {}).get("value", 0)
                            ),
                            "parents": (
                                removed.get("unique_parents", {}).get("value", 0)
                            ),
                            "files": removed.get("doc_count", 0),
                            "data_volume": (
                                removed.get("total_bytes", {}).get("value", 0)
                            ),
                        },
                    }
                )
            return file_type_list

        def make_subcount_dict(subcount_type):
            combined_keys = list(
                set(
                    b.key
                    for b in added_bucket.get(subcount_type, {}).get("buckets", [])
                    if b.key != "doc_count"
                )
                | set(
                    b.key
                    for b in removed_bucket.get(subcount_type, {}).get("buckets", [])
                    if b.key != "doc_count"
                )
            )
            subcount_list = []

            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        added_bucket.get(subcount_type, {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        removed_bucket.get(subcount_type, {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                label_field = SUBCOUNT_TYPES[subcount_type][1]
                label_path = (
                    f"label.hits.hits.0._source.{label_field}".split(".")
                    if len(SUBCOUNT_TYPES[subcount_type]) > 1
                    else None
                )
                # For subjects, we need to find the specific subject that matches the key
                if subcount_type == "subject" and label_path:
                    label = self._get_nested_value(
                        added,
                        ["label", "hits", "hits", 0, "_source", "metadata", "subjects"],
                        key=key,
                    ).get("subject", {})
                else:
                    label = (
                        self._get_nested_value(added, label_path) if label_path else {}
                    )
                subcount_list.append(
                    {
                        "id": key,
                        "label": label,
                        "record_count": {
                            "added": {
                                "metadata_only": (
                                    added.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    added.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": (
                                    removed.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    removed.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                        },
                        "parents": {
                            "added": {
                                "metadata_only": (
                                    added.get("without_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                                "with_files": (
                                    added.get("with_files", {})
                                    .get("unique_parents", {})
                                    .get("value", 0)
                                ),
                            },
                            "removed": {
                                "metadata_only": (
                                    removed.get("without_files", {}).get("doc_count", 0)
                                ),
                                "with_files": (
                                    removed.get("with_files", {}).get("doc_count", 0)
                                ),
                            },
                        },
                        "files": {
                            "added": {
                                "file_count": (
                                    added.get("file_count", {}).get("value", 0)
                                ),
                                "data_volume": (
                                    added.get("total_bytes", {}).get("value", 0)
                                ),
                            },
                            "removed": {
                                "file_count": (
                                    removed.get("file_count", {}).get("value", 0)
                                ),
                                "data_volume": (
                                    removed.get("total_bytes", {}).get("value", 0)
                                ),
                            },
                        },
                    }
                )
            return subcount_list

        agg_dict = {
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
            "community_id": community_id,
            "period_start": current_day.format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": current_day.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            "records": {
                "added": {
                    "metadata_only": (
                        added_bucket.get("without_files", {}).get("doc_count", 0)
                    ),
                    "with_files": (
                        added_bucket.get("with_files", {}).get("doc_count", 0)
                    ),
                },
                "removed": {
                    "metadata_only": (
                        removed_bucket.get("without_files", {}).get("doc_count", 0)
                    ),
                    "with_files": (
                        removed_bucket.get("with_files", {}).get("doc_count", 0)
                    ),
                },
            },
            "parents": {
                "added": {
                    "metadata_only": (
                        added_bucket.get("without_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                    "with_files": (
                        added_bucket.get("with_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                },
                "removed": {
                    "metadata_only": (
                        removed_bucket.get("without_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                    "with_files": (
                        removed_bucket.get("with_files", {})
                        .get("unique_parents", {})
                        .get("value", 0)
                    ),
                },
            },
            "files": {
                "added": {
                    "file_count": added_bucket.get("file_count", {}).get("value", 0),
                    "data_volume": added_bucket.get("total_bytes", {}).get("value", 0),
                },
                "removed": {
                    "file_count": removed_bucket.get("file_count", {}).get("value", 0),
                    "data_volume": (
                        removed_bucket.get("total_bytes", {}).get("value", 0)
                    ),
                },
            },
            "uploaders": added_bucket.get("uploaders", {}).get("value", 0),
            "subcounts": {
                "by_resource_type": make_subcount_dict("by_resource_type"),
                "by_access_rights": make_subcount_dict("by_access_rights"),
                "by_language": make_subcount_dict("by_language"),
                "by_affiliation_creator": make_subcount_dict("by_affiliation_creator"),
                "by_affiliation_contributor": make_subcount_dict(
                    "by_affiliation_contributor"
                ),
                "by_funder": make_subcount_dict("by_funder"),
                "by_subject": make_subcount_dict("by_subject"),
                "by_publisher": make_subcount_dict("by_publisher"),
                "by_periodical": make_subcount_dict("by_periodical"),
                "by_license": make_subcount_dict("by_license"),
                "by_file_type": make_file_type_dict(),
            },
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
        }
        app.logger.error(f"Agg dict: {pformat(agg_dict)}")
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
            year_start_date = max(arrow.get(f"{year}-01-01"), start_date)
            year_end_date = min(arrow.get(f"{year}-12-31"), end_date)

            year_search_added = Search(using=self.client, index=self.event_index)
            year_search_added.update_from_dict(
                daily_record_delta_query(
                    year_start_date.format("YYYY-MM-DD"),
                    year_end_date.format("YYYY-MM-DD"),
                    community_id=community_id,
                )
            )

            year_results_added = year_search_added.execute()
            buckets_added = year_results_added.aggregations["by_day"]["buckets"]

            year_search_removed = Search(using=self.client, index=self.event_index)
            year_search_removed.update_from_dict(
                daily_record_delta_query(
                    year_start_date.format("YYYY-MM-DD"),
                    year_end_date.format("YYYY-MM-DD"),
                    community_id=community_id,
                    find_deleted=True,
                )
            )

            year_results_removed = year_search_removed.execute()
            buckets_removed = year_results_removed.aggregations["by_day"]["buckets"]

            # We have to align uneven
            added_iteration_marker = 0
            removed_iteration_marker = 0
            next_date = min(
                (
                    arrow.get(buckets_added[0]["key_as_string"])
                    if buckets_added
                    else arrow.get(year_end_date)
                ),
                (
                    arrow.get(buckets_removed[0]["key_as_string"])
                    if buckets_removed
                    else arrow.get(year_end_date)
                ),
            )
            final_date = max(
                (
                    arrow.get(buckets_added[-1]["key_as_string"])
                    if buckets_added
                    else arrow.get(year_start_date)
                ),
                (
                    arrow.get(buckets_removed[-1]["key_as_string"])
                    if buckets_removed
                    else arrow.get(year_start_date)
                ),
            )
            current_app.logger.error(f"Final date: {pformat(final_date)}")

            while next_date <= final_date:
                current_app.logger.error(f"Next date: {pformat(next_date)}")
                added_bucket = next(
                    filter(
                        lambda x: arrow.get(x["key_as_string"]) == next_date,
                        buckets_added,
                    ),
                    {},
                )
                removed_bucket = next(
                    filter(
                        lambda x: arrow.get(x["key_as_string"]) == next_date,
                        buckets_removed,
                    ),
                    {},
                )

                # Check if an aggregation already exists for this date
                # If it does, delete it (we'll re-create it below)
                index_name = prefix_index(
                    "{0}-{1}".format(self.aggregation_index, next_date.year)
                )
                document_id = f"{community_id}-{next_date.format('YYYY-MM-DD')}"
                if self.client.exists(index=index_name, id=document_id):
                    self.delete_aggregation(index_name, document_id)

                # Process the current date even if there are no buckets
                # so that we have a record for every day in the period
                yield {
                    "_id": document_id,
                    "_index": index_name,
                    "_source": self.create_agg_dict(
                        community_id, next_date, added_bucket, removed_bucket
                    ),
                }

                # Increment markers if we found matches
                if added_bucket and added_iteration_marker < len(buckets_added):
                    added_iteration_marker += 1
                if removed_bucket and removed_iteration_marker < len(buckets_removed):
                    removed_iteration_marker += 1

                # Increment next date if we haven't reached the end of both lists
                if added_iteration_marker < len(
                    buckets_added
                ) or removed_iteration_marker < len(buckets_removed):
                    next_date = next_date.shift(days=1)
                else:
                    break
