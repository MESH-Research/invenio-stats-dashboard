"""Service for reindexing events with enriched metadata."""

import time
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

import arrow
import psutil
from flask import Flask, current_app
from invenio_search.proxies import current_search, current_search_client
from invenio_search.utils import prefix_index
from opensearchpy import AttrDict, Index, Q
from opensearchpy.exceptions import ConnectionError, ConnectionTimeout, RequestError
from opensearchpy.helpers import bulk
from opensearchpy.helpers.search import Search

from ..aggregations import CommunityBookmarkAPI
from ..utils.decorators import time_operation


class EventReindexingBookmarkAPI(CommunityBookmarkAPI):
    """Bookmark API for event reindexing progress."""

    MAPPINGS = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "task_id": {"type": "keyword"},
                "last_event_id": {"type": "keyword"},
                "last_event_timestamp": {
                    "type": "date",
                    "format": "date_optional_time",
                },
            },
        }
    }

    def __init__(self, client):
        self.client = client
        self.bookmark_index = prefix_index("stats-bookmarks-reindexing")

    @staticmethod
    def _ensure_index_exists(func):
        """Decorator for ensuring the bookmarks index exists."""

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not Index(self.bookmark_index, using=self.client).exists():
                self.client.indices.create(
                    index=self.bookmark_index, body=EventReindexingBookmarkAPI.MAPPINGS
                )
            return func(self, *args, **kwargs)

        return wrapped

    @_ensure_index_exists
    def set_bookmark(self, task_id: str, last_event_id: str, last_event_timestamp):
        """Store reindexing progress.

        Args:
            task_id: The reindexing task identifier, consisting of event_type-YYYY-MM
                (e.g. "record-view-2025-01")
            last_event_id: Last successfully processed event ID
            last_event_timestamp: Timestamp of last event. Can be:
                - arrow.Arrow object
                - ISO format string
                - datetime.datetime object
        """
        if isinstance(last_event_timestamp, str):
            timestamp = arrow.get(last_event_timestamp)
        elif hasattr(last_event_timestamp, "isoformat"):  # datetime objects
            timestamp = arrow.get(last_event_timestamp)
        elif isinstance(last_event_timestamp, arrow.Arrow):
            timestamp = last_event_timestamp
        else:
            error_msg = (
                f"last_event_timestamp must be arrow.Arrow, datetime, or ISO string, "
                f"got {type(last_event_timestamp)}"
            )
            raise ValueError(error_msg)

        self.client.index(
            index=self.bookmark_index,
            id=task_id,  # Use task_id as document ID for upsert behavior
            body={
                "task_id": task_id,  # The reindexing task identifier
                "last_event_id": last_event_id,  # Last successfully processed event ID
                "last_event_timestamp": timestamp.isoformat(),
            },
        )
        self.new_timestamp = None

    @_ensure_index_exists
    def get_bookmark(self, task_id: str, refresh_time=60):
        """Get last event_id and timestamp for a reindexing task."""
        query_bookmark = (
            Search(using=self.client, index=self.bookmark_index)
            .query(
                Q(
                    "bool",
                    must=[
                        Q("term", task_id=task_id),
                    ],
                )
            )
            .sort({"last_event_timestamp": {"order": "desc"}})
            .extra(size=1)
        )
        bookmark = next(iter(query_bookmark.execute()), None)
        if bookmark:
            return {
                "last_event_id": bookmark.last_event_id,
                "last_event_timestamp": arrow.get(bookmark.last_event_timestamp),
            }
        return None


class EventReindexingService:
    """Service for reindexing events with enriched metadata.

    This service handles the reindexing of existing events to add community_id
    and metadata fields for faster aggregation performance. It works with monthly
    indices and manages aliases properly to ensure zero downtime.
    """

    def __init__(self, app: Flask):
        self.client = current_search_client
        self.app = app

        self.max_batches = app.config.get(
            "STATS_DASHBOARD_REINDEXING_MAX_BATCHES", 1000
        )
        self.batch_size = app.config.get("STATS_DASHBOARD_REINDEXING_BATCH_SIZE", 1000)
        self.max_memory_percent = app.config.get(
            "STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT", 75
        )

        # Lazy-load components that require application context
        self._reindexing_bookmark_api = None
        self._index_patterns = None
        self._community_events_index_exists = None

    @property
    def reindexing_bookmark_api(self):
        """Lazy-load reindexing bookmark API that requires application context."""
        if (
            not hasattr(self, "_reindexing_bookmark_api")
            or self._reindexing_bookmark_api is None
        ):
            self._reindexing_bookmark_api = EventReindexingBookmarkAPI(self.client)
        return self._reindexing_bookmark_api

    @property
    def index_patterns(self):
        """Lazy-load index patterns that require application context."""
        return {
            "view": prefix_index("events-stats-record-view"),
            "download": prefix_index("events-stats-file-download"),
        }

    @property
    def community_events_index_exists(self):
        """Check if the stats-community-events index exists."""
        if self._community_events_index_exists is None:
            try:
                self.client.indices.get(index=prefix_index("stats-community-events"))
                self._community_events_index_exists = True
                current_app.logger.debug("stats-community-events index exists")
            except Exception:
                self._community_events_index_exists = False
                current_app.logger.info(
                    "stats-community-events index does not exist, "
                    "will use fallback mechanism"
                )
        return self._community_events_index_exists

    def get_monthly_indices(self, event_type: str) -> List[str]:
        """Get all monthly indices for a given event type."""
        try:
            pattern = self.index_patterns[event_type]
            indices = self.client.indices.get(index=f"{pattern}-*")
            return sorted(indices.keys())
        except Exception as e:
            current_app.logger.error(
                f"Failed to get monthly indices for {event_type}: {e}"
            )
            return []

    def get_current_month(self) -> str:
        """Get the current month in YYYY-MM format."""
        return arrow.utcnow().format("YYYY-MM")

    def is_current_month_index(self, index_name: str) -> bool:
        """Check if an index is for the current month."""
        current_month = self.get_current_month()
        return index_name.endswith(f"-{current_month}")

    def check_health_conditions(self) -> Tuple[bool, str]:
        """Check if we should continue processing or stop gracefully.

        We check if the memory usage is too high, and if the OpenSearch cluster is
        responsive.
        """
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > self.max_memory_percent:
            return False, f"Memory usage too high: {memory_usage}%"

        try:
            self.client.cluster.health(timeout=5)
        except (ConnectionTimeout, ConnectionError) as e:
            return False, f"OpenSearch not responsive: {e}"

        return True, "OK"

    def create_enriched_index(self, event_type: str, month: str) -> str:
        """Create a new enriched index for the given month."""
        try:
            target_pattern = self.index_patterns[event_type]
            # Add a differentiator to avoid naming conflicts
            new_index_name = f"{target_pattern}-{month}-v2.0.0"

            self.client.indices.create(index=new_index_name)
            current_app.logger.info(f"Created enriched index: {new_index_name}")

            return new_index_name
        except Exception as e:
            current_app.logger.error(
                f"Failed to create enriched index for {event_type}-{month}: {e}"
            )
            raise

    def validate_enriched_data(self, source_index: str, target_index: str) -> bool:
        """Validate that the enriched data matches the source data."""
        try:
            source_count = self.client.count(index=source_index)["count"]
            target_count = self.client.count(index=target_index)["count"]

            if source_count != target_count:
                current_app.logger.error(
                    f"Document count mismatch: {source_index}={source_count}, "
                    f"{target_index}={target_count}"
                )
                return False

            # Check that all documents have the required enriched fields
            search = Search(using=self.client, index=target_index)
            search = search.filter(
                "bool",
                must_not=[
                    {"exists": {"field": "community_ids"}},
                ],
            )
            missing_community = search.count()

            if missing_community > 0:
                current_app.logger.error(
                    f"Found {missing_community} documents without community_ids "
                    f"in {target_index}"
                )
                return False

            if not self._spot_check_original_fields(source_index, target_index):
                current_app.logger.error(
                    f"Spot-check validation failed for {target_index}"
                )
                return False

            current_app.logger.info(f"Validation passed for {target_index}")
            return True
        except Exception as e:
            current_app.logger.error(f"Validation failed for {target_index}: {e}")
            return False

    def _spot_check_original_fields(self, source_index: str, target_index: str) -> bool:
        """Spot-check a sample of records to ensure original fields are unchanged.

        Args:
            source_index: The source index name
            target_index: The target index name

        Returns:
            True if spot-check passes, False otherwise
        """
        try:
            sample_size = min(100, self.client.count(index=source_index)["count"])
            if sample_size == 0:
                current_app.logger.warning("No documents to spot-check")
                return True

            source_search = Search(using=self.client, index=source_index)
            source_search = source_search.extra(size=sample_size)
            source_search = source_search.sort("_score")  # Random sort for sampling
            source_hits = source_search.execute().hits.hits

            if not source_hits:
                current_app.logger.warning("No source documents found for spot-check")
                return True

            doc_ids = [hit["_id"] for hit in source_hits]
            target_search = Search(using=self.client, index=target_index)
            target_search = target_search.filter("terms", _id=doc_ids)
            target_search = target_search.extra(size=len(doc_ids))
            target_hits = target_search.execute().hits.hits

            if len(target_hits) != len(source_hits):
                current_app.logger.error(
                    f"Spot-check failed: found {len(target_hits)} target docs "
                    f"but {len(source_hits)} source docs"
                )
                return False

            source_docs = {
                hit["_id"]: (
                    hit["_source"].to_dict()
                    if hasattr(hit["_source"], "to_dict")
                    else hit["_source"]
                )
                for hit in source_hits
            }
            target_docs = {
                hit["_id"]: (
                    hit["_source"].to_dict()
                    if hasattr(hit["_source"], "to_dict")
                    else hit["_source"]
                )
                for hit in target_hits
            }

            core_fields = [
                "timestamp",
                "recid",
                "parent_recid",
                "unique_id",
                "session_id",
                "visitor_id",
                "country",
                "unique_session_id",
                "referrer",
                "via_api",
                "is_machine",
                "is_robot",
                "bucket_id",
                "file_id",
                "file_key",
                "size",
            ]

            mismatches = []
            for doc_id in source_docs.keys():
                source_doc = source_docs.get(doc_id, {})
                target_doc = target_docs.get(doc_id, {})
                original_fields = list(set(core_fields) & set(source_doc.keys()))

                if not target_doc:
                    mismatches.append(f"Document {doc_id} missing from target")
                    continue

                for field in original_fields:
                    source_value = source_doc.get(field)
                    target_value = target_doc.get(field)

                    if source_value != target_value:
                        mismatches.append(
                            f"Document {doc_id} field '{field}' mismatch: "
                            f"source={source_value}, target={target_value}"
                        )

            if mismatches:
                current_app.logger.error(
                    f"Spot-check found {len(mismatches)} mismatches: {mismatches[:5]}"
                )
                return False

            current_app.logger.info(
                f"Spot-check passed: verified {len(source_docs)} documents "
                f"have unchanged original fields"
            )
            return True

        except Exception as e:
            current_app.logger.error(f"Spot-check validation failed: {e}")
            return False

    def update_alias(
        self, event_type: str, month: str, old_index: str, new_index: str
    ) -> bool:
        """Update the alias to point to the new enriched index for this month."""
        try:
            alias_pattern = self.index_patterns[event_type]
            current_app.logger.error(
                f"Starting alias update for {event_type}-{month}: "
                f"alias={alias_pattern}, old_index={old_index}, new_index={new_index}"
            )

            # First, add the alias to the new index (ensuring continuity)
            current_app.logger.error(
                f"Adding alias {alias_pattern} to new index {new_index}"
            )
            self.client.indices.put_alias(index=new_index, name=alias_pattern)
            current_app.logger.error(
                f"Successfully added alias {alias_pattern} to {new_index}"
            )

            # Then remove the alias from the old index (safe to do now)
            current_app.logger.error(
                f"Removing alias {alias_pattern} from old index {old_index}"
            )
            try:
                self.client.indices.delete_alias(index=old_index, name=alias_pattern)
                current_app.logger.error(
                    f"Successfully removed alias {alias_pattern} from {old_index}"
                )
            except Exception as e:
                current_app.logger.info(
                    f"Alias {alias_pattern} not found on {old_index} (expected): {e}"
                )

            # Verify the alias was created correctly
            try:
                alias_info = self.client.indices.get_alias(
                    index=new_index, name=alias_pattern
                )
                current_app.logger.error(
                    f"Verification: alias {alias_pattern} exists on "
                    f"{new_index}: {alias_info}"
                )
            except Exception as e:
                current_app.logger.error(
                    f"Verification failed: alias {alias_pattern} not found on "
                    f"{new_index}: {e}"
                )

            current_app.logger.error(
                f"Successfully updated alias {alias_pattern} to include {new_index}"
            )
            return True
        except Exception as e:
            current_app.logger.error(
                f"Failed to update alias for {event_type}-{month}: {e}"
            )
            return False

    def _create_backup_index(self, old_index: str, backup_index: str) -> bool:
        """Step 1 of current month switchover: Create a backup copy of the old index.

        Args:
            old_index: Name of the index to backup
            backup_index: Name for the backup index

        Returns:
            bool: True if successful, False otherwise
        """
        current_app.logger.info(
            f"Creating backup copy of {old_index} to {backup_index}"
        )
        backup_task = self.client.reindex(
            body={"source": {"index": old_index}, "dest": {"index": backup_index}},
            wait_for_completion=False,
        )

        # Wait for backup reindex to complete
        current_app.logger.info("Waiting for backup reindex to complete...")
        while True:
            task_status = self.client.tasks.get(task_id=backup_task["task"])
            if task_status["completed"]:
                if task_status.get("error"):
                    current_app.logger.error(
                        f"Backup reindex failed: {task_status['error']}"
                    )
                    return False
                break
            time.sleep(1)

        current_app.logger.info("Backup reindex completed successfully")
        return True

    def _capture_events_during_backup(self, old_index: str, backup_index: str) -> None:
        """Step 2 of current month switchover: Ensure backup index is complete.

        This method runs AFTER backup creation but BEFORE alias swap. It finds any
        events that arrived in the old index during the backup creation process
        and adds them to the backup index to ensure it's truly complete.

        Args:
            old_index: The old index where new events are still arriving
            backup_index: The backup index to add any missing recent events to
        """
        current_app.logger.info(f"Checking for recent documents in {old_index}")

        last_backup_timestamp = self._get_last_event_timestamp(backup_index)
        if last_backup_timestamp:
            current_app.logger.info(
                f"Last event timestamp in backup index: {last_backup_timestamp}"
            )

            recent_events = self._get_events_after_timestamp(
                old_index, last_backup_timestamp
            )
            if recent_events:
                current_app.logger.info(
                    f"Found {len(recent_events)} recent events to backup"
                )

                # Index these recent events to the backup index
                actions = []
                for event in recent_events:
                    actions.append(
                        {
                            "_index": backup_index,
                            "_id": event["_id"],
                            "_source": event["_source"],
                        }
                    )

                if actions:
                    from opensearchpy.helpers import bulk

                    success, failed = bulk(self.client, actions, refresh=True)
                    current_app.logger.info(
                        f"Indexed {success} recent events to backup, {failed} failed"
                    )
            else:
                current_app.logger.info("No recent events found to backup")
        else:
            current_app.logger.info(
                "No events found in backup index, skipping recent event check"
            )

    def _perform_alias_swap(self, old_index: str, new_index: str) -> None:
        """Step 3 of current month switchover: Quick alias swap.

        This method runs AFTER ensuring backup completeness. It quickly deletes the
        old index and creates a write alias pointing to the new enriched index.

        This is the risky operation - we can only do this safely because we have
        a complete backup. The alias swap must be fast to minimize the gap in
        search index availability. It should be quick enough that the OpenSearch
        cluster's retry mechanism can recover from any errors.

        Args:
            old_index: Name of the old index to delete (now safe to delete)
            new_index: Name of the new enriched index to alias to
        """
        self.client.indices.delete(index=old_index)
        self.client.indices.put_alias(index=new_index, name=old_index)

    def _recover_missing_events(self, backup_index: str, new_index: str) -> None:
        """Step 4 of current month switchover: Recover events from backup.

        This method runs AFTER the alias swap. It finds any events in the backup
        that are newer than what's currently in the enriched index and moves them
        there. These are events that arrived since the original enriched index
        creation.

        This ensures the enriched index contains ALL events that existed in the
        old index, including ones that arrived during the entire migration.

        Args:
            backup_index: The backup index containing events to recover
            new_index: The new enriched index to recover events to
        """
        # Get the most recent event from the new enriched index to know where to start
        # This represents the state after the alias swap, so any newer events in the
        # backup index occurred during the alias swap process
        current_last_timestamp = self._get_last_event_timestamp(new_index)
        if current_last_timestamp:
            missing_events = self._get_events_after_timestamp(
                backup_index, current_last_timestamp
            )
            if missing_events:
                record_ids = list(
                    set(
                        event["_source"].get("recid")
                        for event in missing_events
                        if event["_source"].get("recid")
                    )
                )
                if record_ids:
                    metadata_by_recid = self.get_metadata_for_records(record_ids)
                    communities_by_recid = self.get_community_membership(
                        record_ids, metadata_by_recid
                    )
                else:
                    metadata_by_recid = {}
                    communities_by_recid = {}

                enriched_actions = []
                for event in missing_events:
                    try:
                        event_source = event["_source"]
                        record_id = event_source.get("recid")

                        enriched_event = event_source
                        if record_id:
                            record_metadata = metadata_by_recid.get(record_id, {})
                            record_communities = communities_by_recid.get(record_id, [])
                            enriched_event = self.enrich_event(
                                event_source, record_metadata, record_communities
                            )

                        enriched_actions.append(
                            {
                                "_index": new_index,
                                "_id": event["_id"],
                                "_source": enriched_event,
                            }
                        )
                    except Exception as e:
                        current_app.logger.error(
                            f"Failed to enrich event {event['_id']}: {e}"
                        )

                if enriched_actions:
                    success, failed = bulk(self.client, enriched_actions, refresh=True)
                    current_app.logger.info(
                        f"Recovered {success} missing events, {failed} failed"
                    )
            else:
                pass

    def switch_over_current_month_index(
        self, old_index: str, new_index: str, delete_old_indices: bool = False
    ) -> bool:
        """Setup write alias for current month and add recent events to the new index.

        This method implements a 5-step process to ensure (nearly) zero data loss during
        alias swap for current month indices (which are still receiving new events):

        Step 1: Create backup copy of old index using reindex
        Step 2: Ensure backup is complete by adding any events that arrived during
            backup creation to the backup index
        Step 3: Quickly delete old index and create write alias to new enriched index
        Step 4: Recover any events that arrived since the original enriched index
            creation from the backup index to the new enriched index
        Step 5: Validate the enriched index integrity before (optionally) deleting
            backup index

        This is necessary because OpenSearch does not allow us to create aliases with
        the same name as an existing index. So we can't alias the new index to the old
        index name until the old index is deleted.

        Args:
            old_index: Name of the old index to replace with an alias
            new_index: Name of the new enriched index to alias to
            delete_old_indices: Whether to delete the backup index after validation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            backup_index = f"{old_index}-backup"

            # Step 1: Create backup copy of old index using reindex
            if not self._create_backup_index(old_index, backup_index):
                return False

            # Step 2: Check for any more recent documents and copy them to backup
            self._capture_events_during_backup(old_index, backup_index)

            # Step 3: Quickly delete old index and create write alias
            self._perform_alias_swap(old_index, new_index)

            # Step 4: Copy any missing recent events from backup to new enriched index
            self._recover_missing_events(backup_index, new_index)

            # Step 4.5: Validate the enriched index integrity before deleting backup
            current_app.logger.info("Step 4.5: Validating enriched index integrity")
            if not self.validate_enriched_data(old_index, new_index):
                current_app.logger.error(
                    f"Validation failed for {new_index}, keeping backup for safety"
                )
                return False

            # Step 5: Clean up backup index (only if validation passes and deletion
            # is enabled)
            if delete_old_indices:
                current_app.logger.info("Step 5: Cleaning up backup index")
                self.client.indices.delete(index=backup_index)
                current_app.logger.info(f"Backup index {backup_index} deleted")
            else:
                current_app.logger.info(
                    f"Step 5: Keeping backup index {backup_index} "
                    f"(delete_old_indices=False)"
                )

            current_app.logger.info(
                f"Write alias setup completed successfully for {old_index}"
            )
            return True

        except Exception as e:
            current_app.logger.error(
                f"Failed to setup write alias for {old_index}: {e}"
            )
            return False

    def _get_events_after_timestamp(
        self, index_name: str, after_timestamp: str
    ) -> List[dict]:
        """Get events from an index that are newer than the specified timestamp.

        Args:
            index_name: Name of the index to search
            after_timestamp: Timestamp string - get events after this time

        Returns:
            List of events with _id and _source
        """
        try:
            search_query = Search(using=self.client, index=index_name)
            search_query = search_query.filter(
                "range", timestamp={"gt": after_timestamp}
            )
            search_query = search_query.sort("timestamp")

            response = search_query.execute()
            events = []
            for hit in response.hits:
                events.append({"_id": hit.meta.id, "_source": hit.to_dict()})

            return events
        except Exception as e:
            current_app.logger.error(
                f"Failed to get recent events after {after_timestamp} "
                f"from {index_name}: {e}"
            )
            return []

    def get_metadata_for_records(self, record_ids: List[str]) -> Dict[str, Dict]:
        """Get metadata for a batch of record IDs."""
        if not record_ids:
            return {}

        try:
            meta_search = Search(
                using=self.client, index=prefix_index("rdmrecords-records")
            )
            meta_search = meta_search.filter("terms", id=record_ids)
            meta_search = meta_search.source(
                [
                    "access.status",
                    "custom_fields.journal:journal.title.keyword",
                    "files.types",
                    "id",
                    "metadata.resource_type",
                    "metadata.languages",
                    "metadata.subjects",
                    "metadata.publisher",
                    "metadata.rights",
                    "metadata.creators.affiliations",
                    "metadata.contributors.affiliations",
                    "metadata.funding.funder",
                    "parent.communities.ids",
                ]
            )
            meta_search = meta_search.extra(size=len(record_ids))

            meta_hits = meta_search.execute().hits.hits
            results = {
                hit["_source"]["id"]: hit.to_dict()["_source"] for hit in meta_hits
            }
            return results
        except Exception as e:
            current_app.logger.error(f"Failed to fetch metadata: {e}")
            return {}

    def get_community_membership(
        self, record_ids: List[str], metadata_by_recid: Dict[str, Dict]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """Get community membership for a batch of record IDs.

        Generally we assume that the stats-community-events index will not yet exist,
        since this reindexing should happen before the aggregator classes trigger
        community events creation. However, if the index does exist, we use it to get
        the community membership. Otherwise, we use a fallback mechanism to infer a
        plausible membership based on the record creation date and community creation
        date.

        Note that the effective date is the date on which the record was added to the
        community (or best guess based on record creation date and community creation
        date).

        Args:
            record_ids: List of record IDs to get community membership for
            metadata_by_recid: Pre-fetched metadata to avoid duplicate searches

        Returns:
            Dictionary of record IDs to lists of (community_id, effective_date) tuples
        """
        if not record_ids:
            return {}

        # If community events index doesn't exist, use fallback immediately
        if not self.community_events_index_exists:
            return self._get_community_membership_fallback(metadata_by_recid)

        try:
            community_search = Search(
                using=self.client, index=prefix_index("stats-community-events")
            )
            community_search = community_search.query(
                {"terms": {"record_id": record_ids}}
            )

            # Aggregate by record_id, then by community_id, getting the most
            # recent event by timestamp
            record_agg = community_search.aggs.bucket(
                "by_record", "terms", field="record_id", size=1000
            )
            community_agg = record_agg.bucket(
                "by_community", "terms", field="community_id", size=100
            )
            community_agg.bucket(
                "top_hit", "top_hits", size=1, sort=[{"timestamp": {"order": "desc"}}]
            )

            community_results = community_search.execute()

            membership = {}
            for record_bucket in community_results.aggregations.by_record.buckets:
                record_id = record_bucket.key
                membership[record_id] = []

                for community_bucket in record_bucket.by_community.buckets:
                    community_id = community_bucket.key
                    # Get the most recent event for this record-community pair
                    if community_bucket.top_hit.hits.hits:
                        top_hit = community_bucket.top_hit.hits.hits[0]
                        event_type = top_hit["_source"]["event_type"]
                        timestamp = top_hit["_source"]["timestamp"]

                        # Only include if the most recent event was an "added" event
                        if event_type == "added":
                            membership[record_id].append((community_id, timestamp))

            # Fallback for records without community event index records
            missing_records = [rid for rid in record_ids if rid not in membership]
            if missing_records:
                current_app.logger.info(
                    f"Found {len(missing_records)} records without community event "
                    f"index records, using fallback mechanism"
                )
                fallback_membership = self._get_community_membership_fallback(
                    metadata_by_recid
                )
                membership.update(fallback_membership)

            return membership
        except Exception as e:
            current_app.logger.error(f"Failed to fetch community membership: {e}")
            # If the main method fails, try the fallback for all records
            return self._get_community_membership_fallback(metadata_by_recid)

    def _get_community_membership_fallback(
        self, metadata_by_recid: Dict[str, Dict]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """Fallback method to get community membership from record metadata.

        This method is used when stats-community-events index records are not available.
        It gets community membership from record.parent.communities.ids and considers
        the event timestamp and community creation dates to determine which communities
        should be included.

        Args:
            metadata_by_recid: Pre-fetched metadata to avoid duplicate searches

        Returns:
            Dictionary of record IDs to lists of (community_id, effective_date) tuples
        """
        try:
            # Get community creation dates
            community_ids = set()
            for record_data in metadata_by_recid.values():
                if record_data.get("parent", {}).get("communities", {}).get("ids"):
                    community_ids.update(record_data["parent"]["communities"]["ids"])

            community_creation_dates = {}
            if community_ids:
                community_search = Search(
                    using=self.client, index=prefix_index("communities-communities")
                )
                community_search = community_search.filter(
                    "terms", id=list(community_ids)
                )
                community_search = community_search.source(["id", "created"])
                community_search = community_search.extra(size=len(community_ids))

                community_hits = community_search.execute().hits.hits
                for hit in community_hits:
                    community_data = hit["_source"]
                    community_creation_dates[community_data["id"]] = community_data[
                        "created"
                    ]

            membership = {}
            for record_id, record_data in metadata_by_recid.items():
                record_created = record_data.get("created")
                record_communities = (
                    record_data.get("parent", {}).get("communities", {}).get("ids", [])
                )

                valid_communities = []
                for community_id in record_communities:
                    community_created = community_creation_dates.get(community_id)
                    if community_created and record_created:
                        effective_date = max(record_created, community_created)
                        valid_communities.append((community_id, effective_date))
                    elif record_created:
                        # If we can't find community creation date, assume it existed
                        # before the record
                        valid_communities.append((community_id, record_created))
                    else:
                        continue

                # Return tuples of (community_id, effective_date) for later filtering
                membership[record_id] = valid_communities

            current_app.logger.info(
                f"Fallback community membership found for {len(membership)} records"
            )
            return membership

        except Exception as e:
            current_app.logger.error(
                f"Failed to get fallback community membership: {e}"
            )
            return {}

    def _process_and_index_events_batch(
        self, hits: List[Dict], target_index: str, context: str = "events"
    ) -> Tuple[bool, Optional[str]]:
        """Process a batch of events and bulk index them with error handling.

        Args:
            hits: List of search hits from OpenSearch
            target_index: Target index name for the enriched documents
            context: Context for logging (e.g., "new records", "events")

        Returns:
            Tuple of (success, error_message)
        """
        if not hits:
            return True, None

        # Process events into enriched documents
        record_ids = list(set(hit["_source"]["recid"] for hit in hits))
        current_app.logger.error(
            f"Extracted {len(record_ids)} unique record IDs: {record_ids[:5]}..."
        )

        # Debug: Check what records exist in the index
        try:
            all_records = self.client.search(
                index=prefix_index("rdmrecords-records"),
                body={"query": {"match_all": {}}, "size": 10},
            )
            existing_record_ids = [
                hit["_source"]["id"] for hit in all_records["hits"]["hits"]
            ]
            current_app.logger.error(
                f"Existing record IDs in index: {existing_record_ids}"
            )
        except Exception as e:
            current_app.logger.error(f"Error checking existing records: {e}")

        metadata_by_recid = self.get_metadata_for_records(record_ids)
        current_app.logger.error(f"Found metadata for {len(metadata_by_recid)} records")

        communities_by_recid = self.get_community_membership(
            record_ids, metadata_by_recid
        )
        current_app.logger.info(
            f"Found community membership for {len(communities_by_recid)} records"
        )

        enriched_docs = []
        for hit in hits:
            event = hit["_source"]
            record_id = event["recid"]

            record_metadata = metadata_by_recid.get(record_id, {})
            record_communities_with_dates = communities_by_recid.get(record_id, [])

            enriched_event = self.enrich_event(
                event, record_metadata, record_communities_with_dates
            )

            enriched_docs.append(
                {
                    "_index": target_index,
                    "_id": hit["_id"],  # Preserve the original document ID
                    "_source": enriched_event,
                }
            )

        # Bulk index the enriched documents
        if not enriched_docs:
            current_app.logger.warning("No enriched documents to index")
            return True, None

        # Log the first enriched document structure before indexing
        if enriched_docs:
            first_doc = enriched_docs[0]
            current_app.logger.error(f"First enriched doc structure: {first_doc}")
            current_app.logger.error(f"First doc _id: {first_doc.get('_id')}")
            current_app.logger.error(f"First doc _index: {first_doc.get('_index')}")
            current_app.logger.error(
                f"First doc _source keys: {list(first_doc.get('_source', {}).keys())}"
            )
            current_app.logger.error(
                f"First doc _source values: {first_doc.get('_source', {})}"
            )

        current_app.logger.info(
            f"Attempting to bulk index {len(enriched_docs)} enriched documents"
        )
        current_app.logger.error(f"Client type: {type(self.client)}")
        current_app.logger.error(
            f"Client bulk method: {getattr(self.client, 'bulk', 'No bulk method')}"
        )

        try:
            bulk_result = bulk(self.client, enriched_docs, refresh=True)
            current_app.logger.error(
                f"Bulk result type: {type(bulk_result)}, value: {bulk_result}"
            )

            success, failed = bulk_result
            current_app.logger.error(
                f"Unpacked - success type: {type(success)}, value: {success}"
            )
            current_app.logger.error(
                f"Unpacked - failed type: {type(failed)}, value: {failed}"
            )

            # Handle different return types from bulk function
            if isinstance(failed, list):
                failed_count = len(failed)
                current_app.logger.error(
                    f"Failed is a list, converting to count: {failed_count}"
                )
            else:
                failed_count = failed

            if failed_count > 0:
                current_app.logger.error(
                    f"Bulk indexing failed for {failed_count} out of "
                    f"{len(enriched_docs)} documents"
                )

                # Find the last successfully indexed document for accurate bookmark
                # positioning. (Bulk indexing stops on first failure.)
                if success > 0:
                    # Get the last successful document from this batch
                    last_successful_doc = enriched_docs[success - 1]
                    last_successful_id = last_successful_doc["_id"]
                    current_app.logger.info(
                        f"Last successful document: {last_successful_id} "
                        f"(position {success} in batch)"
                    )
                    return (
                        False,
                        f"Bulk indexing failed after {success} documents. "
                        f"Last successful: {last_successful_id}",
                    )
                else:
                    return False, "Bulk indexing failed - no documents were indexed"

            current_app.logger.info(
                f"Successfully indexed {success} enriched {context}"
            )
            return True, None

        except Exception as e:
            error_msg = f"Failed to bulk index {context}: {e}"
            current_app.logger.error(error_msg)
            return False, error_msg

    def enrich_event(
        self, event: Dict | AttrDict, metadata: Dict, communities: List[Tuple[str, str]]
    ) -> Dict:
        """Enrich a single event with metadata and community information.

        Args:
            event: The event to enrich
            metadata: The metadata for the record
            communities: The communities that the record belongs to. This is a list of
                tuples of (community_id, effective_date). The effective date is the
                date on which the record was added to the community (or best guess).

        Returns:
            The enriched event
        """
        # Convert AttrDict to regular dict if needed
        if hasattr(event, "to_dict"):
            enriched_event = event.to_dict().copy()
        else:
            enriched_event = event.copy()

        # Log the original event structure
        current_app.logger.error(f"Original event keys: {list(enriched_event.keys())}")
        current_app.logger.error(f"Original event structure: {enriched_event}")

        event_timestamp = event.get("timestamp")
        if event_timestamp and communities:
            active_communities = self._get_active_communities_for_event(
                communities, event_timestamp, metadata
            )
            enriched_event["community_ids"] = active_communities
        else:
            enriched_event["community_ids"] = (
                [c for c, _ in communities] if communities else None
            )

        if metadata:
            metadata_dict = metadata.get("metadata", {})
            enriched_event.update(
                {
                    "resource_type": metadata_dict.get("resource_type", {}),
                    "publisher": metadata_dict.get("publisher", ""),
                    "access_status": metadata.get("access", {}).get("status", ""),
                    "languages": metadata_dict.get("languages", []),
                    "subjects": metadata_dict.get("subjects", []),
                    "rights": metadata_dict.get("rights", []),
                    "funders": [
                        item["funder"]
                        for item in metadata_dict.get("funding", [])
                        if isinstance(item, dict) and "funder" in item
                    ],
                    "journal_title": (
                        metadata.get("custom_fields", {}).get(
                            "journal:journal.title.keyword", ""
                        )
                    ),
                }
            )

            affiliations = []
            for contributor_type in ["creators", "contributors"]:
                for contributor in metadata_dict.get(contributor_type, []):
                    if contributor.get("affiliations"):
                        affiliations.extend(contributor["affiliations"])
            enriched_event["affiliations"] = affiliations

            if "file_key" in enriched_event and metadata:
                files_entries = metadata.get("files", {}).get("entries", {})
                downloaded_file_type = None

                for file_info in files_entries.values():
                    if isinstance(file_info, dict) and "key" in file_info:
                        if file_info["key"] == enriched_event["file_key"]:
                            if "ext" in file_info:
                                downloaded_file_type = file_info["ext"]
                            else:
                                key = file_info["key"]
                                if key and "." in key:
                                    downloaded_file_type = key.split(".")[-1].lower()
                            break

                enriched_event["file_types"] = (
                    [downloaded_file_type] if downloaded_file_type else []
                )

            elif metadata and "files" in metadata:
                files_entries = metadata.get("files", {}).get("entries", {})
                file_types = []

                for file_info in files_entries.values():
                    if isinstance(file_info, dict) and "ext" in file_info:
                        file_types.append(file_info["ext"])
                    elif isinstance(file_info, dict) and "key" in file_info:
                        key = file_info["key"]
                        if key and "." in key:
                            file_types.append(key.split(".")[-1].lower())

                enriched_event["file_types"] = file_types

            elif "file_types" in enriched_event:
                if not isinstance(enriched_event["file_types"], list):
                    enriched_event["file_types"] = [enriched_event["file_types"]]

        # Log the final enriched event structure
        current_app.logger.error(
            f"Final enriched event keys: {list(enriched_event.keys())}"
        )
        current_app.logger.error(f"Final enriched event structure: {enriched_event}")

        return enriched_event

    def _get_active_communities_for_event(
        self, communities: List[Tuple[str, str]], event_timestamp: str, metadata: Dict
    ) -> List[str]:
        """Get all communities that were active at the time of the event.

        This method determines which communities should be included for an event
        based on the event timestamp and pre-calculated effective dates.

        Args:
            communities: List of (community_id, effective_date) tuples
            event_timestamp: The timestamp of the usage event
            metadata: Record metadata including creation date

        Returns:
            List of community IDs that were active at the event time
        """
        if not communities:
            return []

        try:
            event_time = arrow.get(event_timestamp)

            # Find all communities that were active at the time of the event
            active_communities = []
            for community_id, effective_date in communities:
                # Use the pre-calculated effective date
                effective_time = arrow.get(effective_date)
                if event_time >= effective_time:
                    active_communities.append(community_id)

            return active_communities

        except Exception as e:
            current_app.logger.warning(
                f"Error getting active communities for event: {e}, "
                f"returning all communities"
            )
            return [c for c, _ in communities]

    def process_monthly_index_batch(
        self,
        event_type: str,
        source_index: str,
        target_index: str,
        month: str,
        last_processed_id: Optional[str] = None,
    ) -> Tuple[int, Optional[str], bool]:
        """
        Process a single batch of events from a monthly event index.

        Processes one batch of events from the monthly index, returning after
        each batch and keeping track of the progress with a bookmark and the
        last processed event ID.

        Args:
            event_type: The type of event (view or download)
            source_index: The source monthly index name
            target_index: The target enriched index name
            month: The month being migrated (YYYY-MM format)
            last_processed_id: The last processed event ID

        Returns:
            Tuple of (processed_count, last_event_id, should_continue)

        Raises:
            ConnectionTimeout: If the connection to OpenSearch times out
            ConnectionError: If there is a connection error to OpenSearch
            RequestError: If there is a request error to OpenSearch
        """
        try:
            current_app.logger.error(
                f"Entering process_monthly_index_batch for {event_type}-{month}"
            )

            # Check health conditions
            is_healthy, reason = self.check_health_conditions()
            current_app.logger.error(
                f"Health check result: {is_healthy}, reason: {reason}"
            )
            if not is_healthy:
                current_app.logger.error(f"Health check failed: {reason}")
                return 0, last_processed_id, False

            # Debug: Check if source index exists and has documents
            source_count = self.client.count(index=source_index)["count"]
            current_app.logger.info(
                f"Source index {source_index} has {source_count} documents"
            )

            # Debug: Check what events are in the source index
            try:
                sample_events = self.client.search(
                    index=source_index, body={"query": {"match_all": {}}, "size": 5}
                )
                sample_recids = [
                    hit["_source"].get("recid") for hit in sample_events["hits"]["hits"]
                ]
                current_app.logger.info(
                    f"Sample recids from source index: {sample_recids}"
                )
            except Exception as e:
                current_app.logger.error(f"Error checking sample events: {e}")

            search = Search(using=self.client, index=source_index)
            search = search.extra(size=self.batch_size)
            search = search.sort("_id")

            current_app.logger.error(
                f"Search query before search_after: {search.to_dict()}"
            )

            if last_processed_id:
                search = search.extra(search_after=[last_processed_id])
                current_app.logger.error(
                    f"Using search_after with last_processed_id: {last_processed_id}"
                )
            else:
                current_app.logger.error(
                    "No last_processed_id, starting from beginning"
                )

            current_app.logger.error(f"Final search query: {search.to_dict()}")

            response = search.execute()
            hits = response.hits.hits

            current_app.logger.info(
                f"Search query returned {len(hits)} hits from {source_index}"
            )

            # Debug: Check if we're getting any hits at all
            if not hits:
                current_app.logger.error(
                    f"No hits returned from search on {source_index}"
                )
                current_app.logger.error(f"Search query: {search.to_dict()}")
            else:
                current_app.logger.error(f"First hit ID: {hits[0]['_id']}")
                current_app.logger.error(
                    f"First hit source keys: "
                    f"{list(hits[0]['_source'].to_dict().keys())}"
                )

            if not hits:
                current_app.logger.info(
                    f"No more events to process for {event_type}-{month}"
                )
                return 0, last_processed_id, False

            current_app.logger.info(
                f"Processing {len(hits)} events for {event_type}-{month}"
            )

            # Debug: Check first few hits to see what we're working with
            if hits:
                first_hit = hits[0]
                current_app.logger.info(f"First hit ID: {first_hit['_id']}")
                current_app.logger.info(
                    f"First hit source keys: "
                    f"{list(first_hit['_source'].to_dict().keys())}"
                )
                if "recid" in first_hit["_source"]:
                    current_app.logger.info(
                        f"First hit recid: {first_hit['_source']['recid']}"
                    )

            success, error_msg = self._process_and_index_events_batch(
                hits, target_index, "events"
            )
            if not success:
                current_app.logger.error(f"Failed to process batch: {error_msg}")
                return 0, last_processed_id, False

            last_event_id = hits[-1]["_id"]
            last_event_timestamp = hits[-1]["_source"]["timestamp"]
            self.reindexing_bookmark_api.set_bookmark(
                f"{event_type}-{month}-reindexing", last_event_id, last_event_timestamp
            )

            # Check if there are more documents available after this batch
            # Only continue if we got a full batch AND there are more docs
            batch_was_full = len(hits) == self.batch_size
            if batch_was_full:
                # Use count() to efficiently check if there are more docs after this batch
                try:
                    count_query = {"query": {"match_all": {}}}
                    count_response = self.client.count(
                        index=source_index,
                        body=count_query,
                        search_after=[last_event_id],
                    )
                    has_more_docs = count_response["count"] > 0
                    current_app.logger.info(
                        f"Batch was full ({len(hits)} docs), count after shows {count_response['count']} more docs"
                    )
                    return len(hits), last_event_id, has_more_docs
                except Exception as e:
                    current_app.logger.error(f"Error checking count for more docs: {e}")
                    # If we can't check, assume there are more to be safe
                    return len(hits), last_event_id, True
            else:
                # Partial batch means we're at the end
                current_app.logger.info(
                    f"Partial batch ({len(hits)} docs), no more documents available"
                )
                return len(hits), last_event_id, False

        except (ConnectionTimeout, ConnectionError, RequestError) as e:
            current_app.logger.error(f"OpenSearch error during batch processing: {e}")
            return 0, last_processed_id, False
        except Exception as e:
            current_app.logger.error(f"Unexpected error during batch processing: {e}")
            return 0, last_processed_id, False

    @time_operation
    def migrate_monthly_index(
        self,
        event_type: str,
        source_index: str,
        month: str,
        max_batches: Optional[int] = None,
        delete_old_indices: bool = False,
    ) -> Dict[str, Any]:
        """
        Migrate a single monthly index to enriched format.

        Args:
            event_type: The type of event (view or download)
            source_index: The source monthly index name
            month: The month being migrated (YYYY-MM format)
            max_batches: Maximum number of batches to process
            delete_old_indices: Whether to delete old indices after migration

        Returns:
            Dictionary with migration results and statistics.
        """
        results = {
            "month": month,
            "event_type": event_type,
            "source_index": source_index,
            "processed": 0,
            "interrupted": False,
            "errors": 0,
            "batches": 0,
            "completed": False,
            "target_index": None,
        }

        current_app.logger.error(f"Starting migration for {event_type}-{month}")

        try:
            # Step 1: Create new enriched index
            target_index = self.create_enriched_index(event_type, month)
            results["target_index"] = target_index

            # Debug: Check source index before migration
            try:
                source_count = self.client.count(index=source_index)["count"]
                current_app.logger.error(
                    f"Source index {source_index} has {source_count} documents"
                )

                # Check a sample of events
                sample_events = self.client.search(
                    index=source_index, body={"query": {"match_all": {}}, "size": 3}
                )
                sample_recids = [
                    hit["_source"].get("recid") for hit in sample_events["hits"]["hits"]
                ]
                current_app.logger.error(
                    f"Sample recids from {source_index}: {sample_recids}"
                )
            except Exception as e:
                current_app.logger.error(f"Error checking source index: {e}")

            # Step 2: Migrate data
            bookmark = self.reindexing_bookmark_api.get_bookmark(
                f"{event_type}-{month}-reindexing"
            )
            last_processed_id = str(bookmark) if bookmark else None
            if last_processed_id:
                current_app.logger.info(f"Resuming from bookmark: {last_processed_id}")

            batch_count = 0
            should_continue = True

            while should_continue:
                # Check max batches limit
                if max_batches and batch_count >= max_batches:
                    current_app.logger.info(
                        f"Reached max batches limit for {event_type}-{month}"
                    )
                    break

                current_app.logger.info(
                    f"Processing batch {batch_count + 1} for {event_type}-{month}"
                )

                # Debug: Check if we're about to process a batch
                current_app.logger.error(
                    f"About to call process_monthly_index_batch for "
                    f"{event_type}-{month}"
                )

                # Process batch
                processed_count, last_id, continue_processing = (
                    self.process_monthly_index_batch(
                        event_type, source_index, target_index, month, last_processed_id
                    )
                )

                current_app.logger.error(
                    f"Batch processing result: processed={processed_count}, "
                    f"continue={continue_processing}"
                )

                current_app.logger.info(
                    f"Batch {batch_count + 1} result: processed={processed_count}, "
                    f"continue_processing={continue_processing}, last_id={last_id}"
                )

                if processed_count > 0:
                    results["processed"] += processed_count
                    results["batches"] += 1
                    last_processed_id = last_id
                else:
                    results["errors"] += 1

                should_continue = continue_processing and processed_count > 0
                batch_count += 1

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            if should_continue:
                reason = (
                    "max_batches limit"
                    if max_batches and batch_count >= max_batches
                    else "incomplete"
                )

                current_app.logger.info(
                    f"Migration interrupted ({reason}) for {event_type}-{month}. "
                    f"Processed {results['processed']} records in "
                    f"{batch_count} batches. "
                    f"Last processed ID: {last_processed_id}"
                )
                results["completed"] = False
                results["interrupted"] = True
                results["last_processed_id"] = last_processed_id
                results["batches_processed"] = batch_count
                return results

            # Step 3: Validate the migrated data (only if migration completed)
            if not self.validate_enriched_data(source_index, target_index):
                current_app.logger.error(f"Validation failed for {event_type}-{month}")
                results["completed"] = False
                return results

            # Step 4: Update alias
            if not self.update_alias(event_type, month, source_index, target_index):
                current_app.logger.error(
                    f"Failed to update alias for {event_type}-{month}"
                )
                results["completed"] = False
                return results

            # Step 5: Set up write alias for current month
            is_current_month = self.is_current_month_index(source_index)
            if is_current_month:
                if not self.switch_over_current_month_index(
                    source_index, target_index, delete_old_indices
                ):
                    current_app.logger.error(
                        f"Failed to setup write alias for {event_type}-{month}"
                    )
                    results["completed"] = False
                    return results

                # Note: New records that arrived during migration will be automatically
                # captured and migrated by the _recover_missing_events method during
                # the write alias setup, so no separate check is needed here.

            # Step 6: Delete old index (if enabled)
            # Safe to delete now that aliases are updated and any new records
            # have been migrated
            if delete_old_indices:
                if not self.delete_old_index(source_index):
                    current_app.logger.warning(
                        f"Failed to delete old index {source_index}"
                    )
            else:
                current_app.logger.info(
                    f"Skipping deletion of old index {source_index} "
                    f"(delete_old_indices=False)"
                )

            results["completed"] = True
            current_app.logger.info(
                f"Migration completed for {event_type}-{month}: {results}"
            )

        except Exception as e:
            current_app.logger.error(f"Migration failed for {event_type}-{month}: {e}")
            results["completed"] = False

        return results

    def _get_templates_to_update(self, stats_events) -> list:
        """
        Check which templates need to be updated (do not exist or are missing
        'community_ids'). Returns a list of template names to update.
        """
        templates_to_update = []
        for event_type, event_config in stats_events.items():
            template_path = event_config.get("templates")
            if not template_path:
                continue
            template_name = template_path.split(".")[-1]
            try:
                template_exists = self.client.indices.get_index_template(
                    name=template_name, ignore=[404]
                )
                if template_exists:
                    mappings = template_exists["index_templates"][0]["index_template"][
                        "template"
                    ]["mappings"]
                    properties = mappings.get("properties", {})
                    if "community_ids" in properties:
                        current_app.logger.info(
                            f"Template {template_name} already has enriched fields - "
                            f"skipping update"
                        )
                        continue
                    else:
                        current_app.logger.info(
                            f"Template {template_name} exists but needs enrichment - "
                            f"will update"
                        )
                        templates_to_update.append(template_name)
                else:
                    current_app.logger.info(
                        f"Template {template_name} does not exist - will create"
                    )
                    templates_to_update.append(template_name)
            except Exception as e:
                current_app.logger.warning(
                    f"Could not check template {template_name}: {e} - "
                    f"will attempt update"
                )
                templates_to_update.append(template_name)
        return templates_to_update

    def update_and_verify_templates(self) -> bool:
        """Update and verify the enriched event index templates before reindexing.

        Returns:
            True if templates were successfully updated or already up-to-date,
            False otherwise.
        """
        stats_events = current_app.config["STATS_EVENTS"]
        templates = {}

        templates_to_update = self._get_templates_to_update(stats_events)

        if not templates_to_update:
            current_app.logger.info(
                "All templates are already up-to-date with enriched fields"
            )
            return True

        # Register and process templates that need updating
        templates = {}
        for event_type, event_config in stats_events.items():
            template_path = event_config.get("templates", "")
            template_name = template_path.split(".")[-1]
            if template_name in templates_to_update:
                try:
                    result = current_search.register_templates(template_path)
                    if isinstance(result, dict):
                        for index_name, index_template in result.items():
                            current_app.logger.info(
                                f"Registered template for index: {index_name}"
                            )
                            templates[index_name] = index_template
                    else:
                        current_app.logger.error(
                            f"Unexpected result from register_templates: {result}"
                            f"Cannot proceed with reindexing."
                        )
                        return False
                except Exception as e:
                    current_app.logger.error(
                        f"Failed to register index template {template_path}: {e}"
                        f"Cannot proceed with reindexing."
                    )
                    return False

        index_template_count = 0
        failed_templates = []
        for index_name, index_template in templates.items():
            try:
                current_search._put_template(
                    index_name,
                    index_template,
                    current_search_client.indices.put_index_template,
                    ignore=None,  # Don't ignore errors - update existing templates
                )
                index_template_count += 1
            except Exception as e:
                current_app.logger.error(f"Failed to put template {index_name}: {e}")
                failed_templates.append(index_name)

        if failed_templates:
            current_app.logger.error(
                f"Failed to update templates: {failed_templates}. "
                f"Cannot proceed with reindexing."
            )
            return False
        elif index_template_count == 0:
            current_app.logger.error(
                "No enriched view/download event index templates were put to OpenSearch"
            )
            return False
        else:
            current_app.logger.info(
                f"Successfully put {index_template_count} enriched view/download "
                f"event index templates to OpenSearch"
            )

        return True

    def reindex_events(
        self,
        event_types: Optional[List[str]] = None,
        max_batches: Optional[int] = None,
        delete_old_indices: bool = False,
    ) -> Dict[str, Any]:
        """
        Reindex events with enriched metadata for all monthly indices.

        Begins by verifying and (if necessary) updating the enriched view/download
        event index templates before reindexing.

        Args:
            event_types: List of event types to process. If None, process all.
            max_batches: Maximum number of batches to process per month. If None,
            process all.

        Returns:
            Dictionary with reindexing results and statistics.
        """
        max_batches = max_batches or self.max_batches
        results = {
            "total_processed": 0,
            "total_errors": 0,
            "event_types": {},
            "health_issues": [],
            "completed": False,
        }

        if not self.update_and_verify_templates():
            current_app.logger.error(
                "Template update failed - stopping reindexing process"
            )
            results["total_errors"] = 1
            results["health_issues"] = ["Template update failed"]
            results["completed"] = False
            results["error"] = "Template update failed - cannot proceed with reindexing"
            return results

        if event_types is None:
            event_types = ["view", "download"]

        current_app.logger.error(f"Starting reindexing for event types: {event_types}")

        for event_type in event_types:
            if event_type not in ["view", "download"]:
                current_app.logger.warning(f"Unknown event type: {event_type}")
                continue

            current_app.logger.info(f"Processing {event_type} events")

            monthly_indices = self.get_monthly_indices(event_type)
            if not monthly_indices:
                current_app.logger.warning(f"No monthly indices found for {event_type}")
                continue

            event_results = {"processed": 0, "errors": 0, "months": {}}

            for source_index in monthly_indices:
                year, month = source_index.split("-")[-2:]
                current_app.logger.info(
                    f"Processing {event_type} events for {year}-{month}"
                )

                month_results = self.migrate_monthly_index(
                    event_type,
                    source_index,
                    f"{year}-{month}",
                    max_batches,
                    delete_old_indices,
                )

                event_results["months"][f"{year}-{month}"] = month_results
                event_results["processed"] += month_results.get("processed", 0)
                event_results["errors"] += month_results.get("errors", 0)

                # Always add processed count
                results["total_processed"] += month_results.get("processed", 0)

                # Track incomplete migrations (both interrupted and failed)
                if not month_results.get("completed", False):
                    if "interrupted_migrations" not in results:
                        results["interrupted_migrations"] = []
                    results["interrupted_migrations"].append(
                        {
                            "event_type": event_type,
                            "month": f"{year}-{month}",
                            "processed": month_results.get("processed", 0),
                            "batches": month_results.get("batches_processed", 0),
                            "last_processed_id": month_results.get("last_processed_id"),
                            "source_index": month_results.get("source_index"),
                            "target_index": month_results.get("target_index"),
                            "reason": (
                                "interrupted"
                                if month_results.get("interrupted", False)
                                else "failed"
                            ),
                        }
                    )

            results["event_types"][event_type] = event_results
            current_app.logger.info(f"Completed {event_type}: {event_results}")

        # Check if any migrations were incomplete
        if results.get("interrupted_migrations"):
            results["completed"] = False
            current_app.logger.warning(
                f"Reindexing completed with {len(results['interrupted_migrations'])} "
                f"incomplete migrations. Use --max-batches to limit processing "
                f"and resume later."
            )
        else:
            results["completed"] = True
            current_app.logger.info(f"Reindexing completed successfully: {results}")

        return results

    def estimate_total_events(self) -> Dict[str, int]:
        """Estimate the total number of events to reindex across all monthly indices."""
        estimates = {}

        for event_type in ["view", "download"]:
            monthly_indices = self.get_monthly_indices(event_type)
            total_count = 0

            for index in monthly_indices:
                try:
                    count = self.client.count(index=index)["count"]
                    total_count += count
                    msg = "Estimated %d events for %s"
                    current_app.logger.info(
                        msg,
                        count,
                        index,
                    )
                except Exception as e:
                    msg = "Failed to estimate events for %s: %s"
                    current_app.logger.error(
                        msg,
                        index,
                        e,
                    )

            estimates[event_type] = total_count

        return estimates

    def get_reindexing_progress(self) -> Dict[str, Any]:
        """Get current reindexing progress across all monthly indices."""
        progress = {
            "estimates": self.estimate_total_events(),
            "bookmarks": {},
            "health": {},
        }

        for event_type in ["view", "download"]:
            monthly_indices = self.get_monthly_indices(event_type)
            progress["bookmarks"][event_type] = {}

            for index in monthly_indices:
                month = index.split("-")[-1]
                bookmark = self.reindexing_bookmark_api.get_bookmark(
                    f"{event_type}-{month}-reindexing"
                )
                progress["bookmarks"][event_type][month] = bookmark

        is_healthy, reason = self.check_health_conditions()
        progress["health"] = {
            "is_healthy": is_healthy,
            "reason": reason,
            "memory_usage": psutil.virtual_memory().percent,
        }

        return progress

    def _get_last_event_timestamp(self, index_name: str) -> Optional[str]:
        """Get the timestamp of the last event in an index, sorted by timestamp."""
        try:
            search_query = Search(using=self.client, index=index_name)
            search_query = search_query.sort({"timestamp": {"order": "desc"}})
            search_query = search_query.extra(size=1)
            response = search_query.execute()
            if response.hits:
                return response.hits[0].timestamp
            return None
        except Exception as e:
            current_app.logger.error(
                f"Failed to get last event timestamp from {index_name}: {e}"
            )
            return None

    def delete_old_index(self, index_name: str) -> bool:
        """Delete an old index if it exists."""
        try:
            # Check if any aliases point to this index (and remove them first)
            aliases_pointing_to_index = self.client.indices.get_alias(
                index=index_name, ignore=[404]
            )
            if aliases_pointing_to_index and index_name in aliases_pointing_to_index:
                for alias_name in aliases_pointing_to_index[index_name][
                    "aliases"
                ].keys():
                    self.client.indices.delete_alias(index=index_name, name=alias_name)
                    current_app.logger.info(
                        f"Removed alias {alias_name} from {index_name}"
                    )

            if self.client.indices.exists(index=index_name):
                self.client.indices.delete(index=index_name)
                current_app.logger.info(f"Deleted old index: {index_name}")
            else:
                current_app.logger.info(f"Index {index_name} no longer exists")

            return True
        except Exception as e:
            current_app.logger.error(f"Failed to delete old index {index_name}: {e}")
            return False
