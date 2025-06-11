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
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search
from invenio_stats.aggregations import StatAggregator
from invenio_stats.bookmark import BookmarkAPI
from invenio_stats_dashboard.queries import (
    daily_record_cumulative_counts_query,
    daily_record_delta_query,
    daily_usage_delta_query,
)

SUBCOUNT_TYPES = {
    "resource_type": (
        "resource_type",
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


class CommunityAggregatorBase(StatAggregator):
    """Base class for community statistics aggregators."""

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.event = ""
        self.aggregation_field = None
        self.copy_fields = {}
        self.event_index = None
        self.aggregation_index = None
        self.community_ids = []
        self.interval = "day"
        self.client = kwargs.get("client") or current_search_client
        self.bookmark_api = BookmarkAPI(self.client, self.name, self.interval)

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

    def delete_aggregation(
        self,
        index_name: str,
        document_id: str,
    ):
        """Remove the aggregation for a given community and date."""
        self.client.delete(index=index_name, id=document_id)
        self.client.indices.refresh(index=index_name)

    def _get_nested_value(self, data: dict, path: list, key: str | None = None) -> dict:
        """Get a nested value from a dictionary using a list of path segments.

        Args:
            data: The dictionary to traverse
            path: List of path segments to traverse
            key: Optional key to match when traversing arrays

        Returns:
            The value at the end of the path, or an empty dict if not found
        """
        current = data
        for segment in path:
            if isinstance(current, dict):
                current = current.get(segment, {})
            elif isinstance(current, list):
                # For arrays, we need to find the item that matches our key
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
                else:
                    current = current[0] if current else {}
            else:
                return {}
        return current


class CommunityRecordsSnapshotAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = prefix_index("rdmrecords-records")
        self.aggregation_index = prefix_index("stats-community-usage-snapshot")
        self.delta_index = prefix_index("stats-community-usage-delta")

    def _get_daily_deltas(
        self,
        community_id: str,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
    ) -> list[dict]:
        """Get all daily delta records for a community within a date range."""
        search = Search(using=self.client, index=self.delta_index)
        search = search.filter("term", community_id=community_id)
        search = search.filter(
            "range",
            period_start={
                "gte": start_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
                "lte": end_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
            },
        )
        search = search.sort("period_start")
        return [hit.to_dict() for hit in search.scan()]

    def _calculate_cumulative_totals(
        self,
        deltas: list[dict],
        current_date: arrow.Arrow,
    ) -> dict:
        """Calculate cumulative totals up to the current date."""
        totals = {
            "views": {
                "total": 0,
                "unique_visitors": 0,
                "unique_records": 0,
                "unique_parents": 0,
            },
            "downloads": {
                "total": 0,
                "unique_visitors": 0,
                "unique_records": 0,
                "unique_parents": 0,
                "unique_files": 0,
                "total_volume": 0,
            },
            "by_resource_type": {},
            "by_access_rights": {},
            "by_language": {},
            "by_subject": {},
            "by_license": {},
            "by_affiliation": {},
            "by_funder": {},
            "by_periodical": {},
            "by_file_type": {},
            "by_country": {},
            "by_referrer": {},
        }

        for delta in deltas:
            delta_date = arrow.get(delta["period_start"])
            if delta_date > current_date:
                continue

            # Add to overall totals
            for event_type in ["views", "downloads"]:
                for metric, value in delta["totals"][event_type].items():
                    totals[event_type][metric] += value

            # Add to category totals
            for category in [
                "by_resource_type",
                "by_access_rights",
                "by_language",
                "by_subject",
                "by_license",
                "by_affiliation",
                "by_funder",
                "by_periodical",
                "by_file_type",
                "by_country",
                "by_referrer",
            ]:
                for item in delta[category]:
                    item_id = item.get("id") or item.get("name")
                    if item_id not in totals[category]:
                        totals[category][item_id] = {
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "title": item.get("title"),
                            "views": {
                                "total": 0,
                                "unique_visitors": 0,
                                "unique_records": 0,
                                "unique_parents": 0,
                            },
                            "downloads": {
                                "total": 0,
                                "unique_visitors": 0,
                                "unique_records": 0,
                                "unique_parents": 0,
                                "unique_files": 0,
                                "total_volume": 0,
                            },
                        }

                    for event_type in ["views", "downloads"]:
                        if event_type in item:
                            for metric, value in item[event_type].items():
                                totals[category][item_id][event_type][metric] += value

        return totals

    def _convert_totals_to_list(self, totals: dict) -> dict:
        """Convert the totals dictionary to the expected list format."""
        result = totals.copy()
        for category in [
            "by_resource_type",
            "by_access_rights",
            "by_language",
            "by_subject",
            "by_license",
            "by_affiliation",
            "by_funder",
            "by_periodical",
            "by_file_type",
            "by_country",
            "by_referrer",
        ]:
            result[category] = [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "title": item.get("title"),
                    "views": item["views"],
                    "downloads": item["downloads"],
                }
                for item in totals[category].values()
            ]
        return result

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
    ) -> Generator[dict, None, None]:
        """Create cumulative totals from daily usage deltas."""
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)

        # Get all daily deltas for the community
        deltas = self._get_daily_deltas(community_id, start_date, end_date)
        if not deltas:
            return

        # Process each day in the range
        current_date = start_date
        while current_date <= end_date:
            # Calculate cumulative totals up to current date
            totals = self._calculate_cumulative_totals(deltas, current_date)

            # Convert totals to expected format
            result = self._convert_totals_to_list(totals)

            # Add metadata
            result.update(
                {
                    "community_id": community_id,
                    "period_start": (
                        current_date.floor("day").format("YYYY-MM-DDTHH:mm:ss")
                    ),
                    "period_end": (
                        current_date.ceil("day")
                        .shift(seconds=-1)
                        .format("YYYY-MM-DDTHH:mm:ss")
                    ),
                    "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
                }
            )

            # Check if an aggregation already exists for this date
            index_name = prefix_index(
                "{0}-{1}".format(self.aggregation_index, current_date.year)
            )
            document_id = f"{community_id}-{current_date.format('YYYY-MM-DD')}"
            if self.client.exists(index=index_name, id=document_id):
                self.delete_aggregation(index_name, document_id)

            yield {
                "_id": document_id,
                "_index": index_name,
                "_source": result,
            }

            current_date = current_date.shift(days=1)


class CommunityUsageSnapshotAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)


class CommunityUsageDeltaAggregator(CommunityAggregatorBase):

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.event_index = [
            prefix_index("events-stats-record-view"),
            prefix_index("events-stats-file-download"),
        ]
        self.aggregation_index = prefix_index("stats-community-usage-delta")

    def _add_common_metrics(self, bucket):
        """Add common metrics to an aggregation bucket."""
        bucket.metric(
            "total_events",
            "value_count",
            field="record_id",
        ).metric(
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
        ).metric(
            "unique_files",
            "cardinality",
            field="file_id",
        ).metric(
            "total_volume",
            "sum",
            field="size",
        )
        return bucket

    def _create_event_type_bucket(self, bucket):
        """Create a bucket with event type split and common metrics."""
        return bucket.bucket(
            "by_event_type",
            "terms",
            field="event_type",
            size=2,
        )

    def _process_metrics_bucket(self, bucket, include_files=False):
        """Process a metrics bucket and return a dictionary of metrics."""
        metrics = {
            "total": bucket.total_events.value,
            "unique_visitors": bucket.unique_visitors.value,
            "unique_records": bucket.unique_records.value,
            "unique_parents": bucket.unique_parents.value,
        }
        if include_files:
            metrics.update(
                {
                    "unique_files": bucket.unique_files.value,
                    "total_volume": bucket.total_volume.value,
                }
            )
        return metrics

    def _create_aggregation_doc(
        self, temp_index: str, community_id: str, date: arrow.Arrow
    ) -> dict:
        """Create the final aggregation document from the temporary index."""
        agg_search = Search(using=self.client, index=temp_index)

        # Add top-level metrics
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_event_type", "terms", field="event_type", size=2
                )
            )
        )

        # Aggregate by resource type
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_resource_type", "terms", field="resource_type.id", size=100
                )
            )
        ).metric("title", "top_hits", size=1, _source=["resource_type.title"])

        # Aggregate by access rights
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_access_rights", "terms", field="access_rights", size=100
                )
            )
        )

        # Aggregate by language
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_language", "terms", field="languages.id", size=100
                )
            )
        ).metric("title", "top_hits", size=1, _source=["languages.title"])

        # Aggregate by subject
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_subject", "terms", field="subjects.id", size=100
                )
            )
        ).metric("title", "top_hits", size=1, _source=["subjects.title"])

        # Aggregate by license
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_license", "terms", field="licenses.id", size=100
                )
            )
        ).metric("title", "top_hits", size=1, _source=["licenses.title"])

        # Aggregate by affiliation
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_affiliation",
                    "composite",
                    size=100,
                    sources=[
                        {"id": {"terms": {"field": "affiliations.id"}}},
                        {"name": {"terms": {"field": "affiliations.name"}}},
                    ],
                )
            )
        )

        # Aggregate by funder
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_funder", "terms", field="funders.id", size=100
                )
            )
        ).metric("title", "top_hits", size=1, _source=["funders.title"])

        # Aggregate by periodical
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket(
                    "by_periodical", "terms", field="periodical", size=100
                )
            )
        )

        # Aggregate by file type (downloads only)
        self._add_common_metrics(
            agg_search.aggs.bucket("by_file_type", "terms", field="file_type", size=100)
        )

        # Aggregate by country
        self._add_common_metrics(
            self._create_event_type_bucket(
                agg_search.aggs.bucket("by_country", "terms", field="country", size=100)
            )
        )

        # Aggregate by referrer (downloads only)
        self._add_common_metrics(
            agg_search.aggs.bucket("by_referrer", "terms", field="referrer", size=100)
        )

        results = agg_search.execute()

        # Get top-level metrics
        views_bucket = next(
            (b for b in results.aggregations.by_event_type.buckets if b.key == "view"),
            None,
        )
        downloads_bucket = next(
            (
                b
                for b in results.aggregations.by_event_type.buckets
                if b.key == "download"
            ),
            None,
        )

        def process_bucket_with_title(bucket, title_path=None):
            """Process a bucket that may have a title."""
            if not bucket:
                return None
            result = {
                "id": bucket.key,
                "views": self._process_metrics_bucket(bucket.by_event_type.buckets[0]),
                "downloads": self._process_metrics_bucket(
                    bucket.by_event_type.buckets[1], include_files=True
                ),
            }
            if title_path and bucket.title.hits.hits:
                result["title"] = self._get_nested_value(
                    bucket.title.hits.hits[0]._source, title_path.split(".")
                )
            return result

        def process_bucket_without_title(bucket):
            """Process a bucket without a title."""
            if not bucket:
                return None
            return {
                "id": bucket.key,
                "views": self._process_metrics_bucket(bucket.by_event_type.buckets[0]),
                "downloads": self._process_metrics_bucket(
                    bucket.by_event_type.buckets[1], include_files=True
                ),
            }

        def process_affiliation_bucket(bucket):
            """Process an affiliation bucket."""
            if not bucket:
                return None
            return {
                "id": bucket.key.get("id"),
                "name": bucket.key.get("name"),
                "views": self._process_metrics_bucket(bucket.by_event_type.buckets[0]),
                "downloads": self._process_metrics_bucket(
                    bucket.by_event_type.buckets[1], include_files=True
                ),
            }

        def process_downloads_only_bucket(bucket):
            """Process a bucket that only has downloads metrics."""
            if not bucket:
                return None
            return {
                "id": bucket.key,
                **self._process_metrics_bucket(bucket, include_files=True),
            }

        return {
            "community_id": community_id,
            "period_start": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
            "period_end": (
                date.ceil("day").shift(seconds=-1).format("YYYY-MM-DDTHH:mm:ss")
            ),
            "totals": {
                "views": (
                    self._process_metrics_bucket(views_bucket) if views_bucket else {}
                ),
                "downloads": (
                    self._process_metrics_bucket(downloads_bucket, include_files=True)
                    if downloads_bucket
                    else {}
                ),
            },
            "by_resource_type": [
                process_bucket_with_title(b, "resource_type.title")
                for b in results.aggregations.by_resource_type.buckets
            ],
            "by_access_rights": [
                process_bucket_without_title(b)
                for b in results.aggregations.by_access_rights.buckets
            ],
            "by_language": [
                process_bucket_with_title(b, "languages.title")
                for b in results.aggregations.by_language.buckets
            ],
            "by_subject": [
                process_bucket_with_title(b, "subjects.title")
                for b in results.aggregations.by_subject.buckets
            ],
            "by_license": [
                process_bucket_with_title(b, "licenses.title")
                for b in results.aggregations.by_license.buckets
            ],
            "by_affiliation": [
                process_affiliation_bucket(b)
                for b in results.aggregations.by_affiliation.buckets
            ],
            "by_funder": [
                process_bucket_with_title(b, "funders.title")
                for b in results.aggregations.by_funder.buckets
            ],
            "by_periodical": [
                process_bucket_without_title(b)
                for b in results.aggregations.by_periodical.buckets
            ],
            "by_file_type": [
                process_downloads_only_bucket(b)
                for b in results.aggregations.by_file_type.buckets
            ],
            "by_country": [
                process_bucket_without_title(b)
                for b in results.aggregations.by_country.buckets
            ],
            "by_referrer": [
                process_downloads_only_bucket(b)
                for b in results.aggregations.by_referrer.buckets
            ],
        }

    def agg_iter(
        self,
        community_id: str,
        start_date: arrow.Arrow | datetime.datetime,
        end_date: arrow.Arrow | datetime.datetime,
    ) -> Generator[dict, None, None]:
        """Create a dictionary representing the aggregation result for indexing."""
        start_date = arrow.get(start_date)
        end_date = arrow.get(end_date)
        temp_index = (
            f"temp-usage-stats-{community_id}-{start_date.format('YYYY-MM-DD')}"
        )

        try:
            self._create_temp_index(temp_index)
            current_iteration_date = start_date

            while current_iteration_date <= end_date:
                # Process each event type (views and downloads)
                for event_type, event_index in [
                    ("view", prefix_index("events-stats-record-view")),
                    ("download", prefix_index("events-stats-file-download")),
                ]:
                    self._process_event_type(
                        temp_index,
                        community_id,
                        current_iteration_date,
                        event_type,
                        event_index,
                    )

                # Create and yield the final aggregation document
                agg_doc = self._create_aggregation_doc(
                    temp_index, community_id, current_iteration_date
                )

                yield {
                    "_id": (
                        f"{community_id}-{current_iteration_date.format('YYYY-MM-DD')}"
                    ),
                    "_index": self.aggregation_index,
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

        current_app.logger.error(f"Current day: {pformat(current_day)}")
        current_app.logger.error(
            f"Added bucket key: {pformat(added_bucket.get('key_as_string'))}"
        )
        current_app.logger.error(
            f"Removed bucket key: {pformat(removed_bucket.get('key_as_string'))}"
        )

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
            current_app.logger.error(
                f"Combined file_type keys: {pformat(combined_keys)}"
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
                current_app.logger.error(f"Added: {pformat(added)}")
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        removed_bucket.get("by_file_type", {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                current_app.logger.error(f"Removed: {pformat(removed)}")
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
            current_app.logger.error(f"Subcount type: {subcount_type}")
            current_app.logger.error(
                f"Added: {pformat(added_bucket.get(subcount_type, {}).get('buckets', []))}"
            )
            current_app.logger.error(
                f"Removed: {pformat(removed_bucket.get(subcount_type, {}).get('buckets', []))}"
            )
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
            current_app.logger.error(f"Combined keys: {pformat(combined_keys)}")
            subcount_list = []

            current_app.logger.error(
                f"Added: {pformat(added_bucket.get(subcount_type, {}).get('buckets', []))}"
            )
            current_app.logger.error(
                f"Removed: {pformat(removed_bucket.get(subcount_type, {}).get('buckets', []))}"
            )

            for key in combined_keys:
                added_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        added_bucket.get(subcount_type, {}).get("buckets", []),
                    )
                )
                added = added_list[0] if added_list else {}
                current_app.logger.error(f"Added: {pformat(added)}")
                removed_list = list(
                    filter(
                        lambda x: x["key"] == key,
                        removed_bucket.get(subcount_type, {}).get("buckets", []),
                    )
                )
                removed = removed_list[0] if removed_list else {}
                current_app.logger.error(f"Removed: {pformat(removed)}")
                label_field = SUBCOUNT_TYPES[subcount_type][2]
                label_path = (
                    f"label.hits.hits.0._source.{label_field}".split(".")
                    if len(SUBCOUNT_TYPES[subcount_type]) > 2
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
            "period_end": (
                current_day.ceil("day").shift(seconds=-1).format("YYYY-MM-DDTHH:mm:ss")
            ),
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

            current_app.logger.error(
                f"{len(buckets_removed)} buckets removed, {pformat(buckets_removed)}"
            )

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
