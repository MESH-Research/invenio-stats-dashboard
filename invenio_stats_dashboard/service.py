import arrow
import gc
import time
from typing import Any, Dict, List, Optional, Tuple
from flask import Flask, current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search
from opensearchpy.helpers.actions import bulk
from opensearchpy.exceptions import ConnectionTimeout, ConnectionError, RequestError
from .components import update_community_events_index
from .queries import CommunityStatsResultsQuery
from .tasks import CommunityStatsAggregationTask
from .aggregations import CommunityBookmarkAPI


class EventReindexingService:
    """Service for reindexing events with enriched metadata.

    This service handles the reindexing of existing events to add community_id
    and metadata fields for faster aggregation performance.
    """

    def __init__(self, app: Flask):
        self.client = current_search_client
        self.app = app

        # Configuration
        self.batch_size = 1000
        self.max_memory_percent = 85
        self.max_retries = 3
        self.retry_delay = 5  # seconds

        # Lazy-load components that require application context
        self._bookmark_api = None
        self._source_indices = None
        self._target_indices = None

    @property
    def bookmark_api(self):
        """Lazy-load bookmark API that requires application context."""
        if self._bookmark_api is None:
            self._bookmark_api = CommunityBookmarkAPI(
                self.client, "event-reindexing", "batch"
            )
        return self._bookmark_api

    @property
    def source_indices(self):
        """Lazy-load source indices that require application context."""
        if self._source_indices is None:
            self._source_indices = [
                ("view", prefix_index("events-stats-record-view")),
                ("download", prefix_index("events-stats-file-download")),
            ]
        return self._source_indices

    @property
    def target_indices(self):
        """Lazy-load target indices that require application context."""
        if self._target_indices is None:
            self._target_indices = [
                ("view", prefix_index("events-stats-record-view-enriched")),
                ("download", prefix_index("events-stats-file-download-enriched")),
            ]
        return self._target_indices

    def get_reindexing_bookmark(self, event_type: str) -> Optional[str]:
        """Get the last processed event ID for a specific event type."""
        try:
            bookmark = self.bookmark_api.get_bookmark(f"{event_type}-reindexing")
            return str(bookmark) if bookmark else None
        except Exception as e:
            current_app.logger.warning(f"Could not get bookmark for {event_type}: {e}")
            return None

    def set_reindexing_bookmark(self, event_type: str, last_event_id: str) -> None:
        """Set the bookmark for the last processed event ID."""
        try:
            self.bookmark_api.set_bookmark(f"{event_type}-reindexing", last_event_id)
            current_app.logger.info(
                f"Updated bookmark for {event_type}: {last_event_id}"
            )
        except Exception as e:
            current_app.logger.error(f"Failed to set bookmark for {event_type}: {e}")

    def get_memory_usage(self) -> float:
        """Get current memory usage as a percentage."""
        try:
            import psutil

            return psutil.virtual_memory().percent
        except ImportError:
            # Fallback if psutil is not available
            return 0.0

    def check_health_conditions(self) -> Tuple[bool, str]:
        """Check if we should continue processing or stop gracefully."""
        memory_usage = self.get_memory_usage()
        if memory_usage > self.max_memory_percent:
            return False, f"Memory usage too high: {memory_usage}%"

        # Check if OpenSearch is responsive
        try:
            self.client.cluster.health(timeout="5s")
        except (ConnectionTimeout, ConnectionError) as e:
            return False, f"OpenSearch not responsive: {e}"

        return True, "OK"

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

    def get_community_membership(self, record_ids: List[str]) -> Dict[str, List[str]]:
        """Get community membership for a batch of record IDs."""
        if not record_ids:
            return {}

        try:
            community_search = Search(
                using=self.client, index=prefix_index("stats-community-events")
            )
            community_search = community_search.filter("terms", record_id=record_ids)
            community_search = community_search.filter("term", event_type="added")

            # Add terms aggregation to get unique records with their communities
            record_agg = community_search.aggs.bucket(
                "by_record", "terms", field="record_id", size=1000
            )
            record_agg.bucket("communities", "terms", field="community_id")

            community_results = community_search.execute()

            membership = {}
            for bucket in community_results.aggregations.by_record.buckets:
                record_id = bucket.key
                communities = [c.key for c in bucket.communities.buckets]
                membership[record_id] = communities

            return membership
        except Exception as e:
            current_app.logger.error(f"Failed to fetch community membership: {e}")
            return {}

    def enrich_event(self, event: Dict, metadata: Dict, communities: List[str]) -> Dict:
        """Enrich a single event with metadata and community information."""
        enriched_event = event.copy()

        # Add community_id (use first community or "global" if none)
        enriched_event["community_id"] = communities[0] if communities else "global"

        # Add metadata fields
        if metadata:
            enriched_event["resource_type"] = {
                "id": (
                    metadata.get("metadata", {}).get("resource_type", {}).get("id", "")
                ),
                "title": (
                    metadata.get("metadata", {})
                    .get("resource_type", {})
                    .get("title", {})
                    .get("en", "")
                ),
            }
            enriched_event["publisher"] = metadata.get("metadata", {}).get(
                "publisher", ""
            )
            enriched_event["access_rights"] = metadata.get("access", {}).get(
                "status", ""
            )

            # Add languages
            languages = metadata.get("metadata", {}).get("languages", [])
            enriched_event["languages"] = [
                {
                    "id": lang.get("id", ""),
                    "title": lang.get("title", {}).get("en", ""),
                }
                for lang in languages
            ]

            # Add subjects
            subjects = metadata.get("metadata", {}).get("subjects", [])
            enriched_event["subjects"] = [
                {
                    "id": subject.get("id", ""),
                    "title": subject.get("subject", ""),
                }
                for subject in subjects
            ]

            # Add licenses
            rights = metadata.get("metadata", {}).get("rights", [])
            enriched_event["licenses"] = [
                {
                    "id": right.get("id", ""),
                    "title": right.get("title", {}).get("en", ""),
                }
                for right in rights
            ]

            # Add funders
            funders = metadata.get("metadata", {}).get("funding", {}).get("funder", [])
            enriched_event["funders"] = [
                {
                    "id": funder.get("id", ""),
                    "title": funder.get("title", {}).get("en", ""),
                }
                for funder in funders
            ]

            # Add affiliations
            affiliations = []
            for contributor_type in ["creators", "contributors"]:
                contributors = metadata.get("metadata", {}).get(contributor_type, [])
                for contributor in contributors:
                    if contributor.get("affiliations"):
                        for affiliation in contributor.get("affiliations", []):
                            affiliations.append(
                                {
                                    "id": affiliation.get("id", ""),
                                    "name": affiliation.get("name", ""),
                                    "identifiers": affiliation.get("identifiers", []),
                                }
                            )
            enriched_event["affiliations"] = affiliations

            # Add periodical
            if "custom_fields" in metadata:
                enriched_event["periodical"] = metadata["custom_fields"].get(
                    "journal:journal.title.keyword", ""
                )

        return enriched_event

    def process_event_batch(
        self,
        event_type: str,
        source_index: str,
        target_index: str,
        last_processed_id: Optional[str] = None,
    ) -> Tuple[int, Optional[str], bool]:
        """
        Process a batch of events for reindexing.

        Returns:
            Tuple of (processed_count, last_event_id, should_continue)
        """
        try:
            # Check health conditions
            is_healthy, reason = self.check_health_conditions()
            if not is_healthy:
                current_app.logger.warning(f"Health check failed: {reason}")
                return 0, last_processed_id, False

            # Build search query
            search = Search(using=self.client, index=source_index)
            search = search.extra(size=self.batch_size)
            search = search.sort("_id")

            if last_processed_id:
                search = search.extra(search_after=[last_processed_id])

            # Execute search
            response = search.execute()
            hits = response.hits.hits

            if not hits:
                current_app.logger.info(f"No more events to process for {event_type}")
                return 0, last_processed_id, True

            current_app.logger.info(f"Processing {len(hits)} events for {event_type}")

            # Extract record IDs
            record_ids = list(set(hit["_source"]["recid"] for hit in hits))

            # Fetch metadata and community membership
            metadata = self.get_metadata_for_records(record_ids)
            community_membership = self.get_community_membership(record_ids)

            # Enrich events
            enriched_docs = []
            for hit in hits:
                event = hit["_source"]
                record_id = event["recid"]

                # Get metadata and communities for this record
                record_metadata = metadata.get(record_id, {})
                record_communities = community_membership.get(record_id, [])

                # Enrich the event
                enriched_event = self.enrich_event(
                    event, record_metadata, record_communities
                )

                # Create document for bulk indexing
                enriched_docs.append(
                    {
                        "_index": target_index,
                        "_source": enriched_event,
                    }
                )

            # Bulk index enriched events
            if enriched_docs:
                success, errors = bulk(self.client, enriched_docs, stats_only=False)
                if errors:
                    current_app.logger.error(f"Bulk indexing errors: {errors}")
                    return 0, last_processed_id, False

                current_app.logger.info(
                    f"Successfully indexed {len(enriched_docs)} enriched events"
                )

            # Update bookmark
            last_event_id = hits[-1]["_id"]
            self.set_reindexing_bookmark(event_type, last_event_id)

            # Force garbage collection
            gc.collect()

            return len(hits), last_event_id, True

        except (ConnectionTimeout, ConnectionError, RequestError) as e:
            current_app.logger.error(f"OpenSearch error during batch processing: {e}")
            return 0, last_processed_id, False
        except Exception as e:
            current_app.logger.error(f"Unexpected error during batch processing: {e}")
            return 0, last_processed_id, False

    def reindex_events(
        self, event_types: Optional[List[str]] = None, max_batches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Reindex events with enriched metadata.

        Args:
            event_types: List of event types to process. If None, process all.
            max_batches: Maximum number of batches to process. If None, process all.

        Returns:
            Dictionary with reindexing results and statistics.
        """
        if event_types is None:
            event_types = ["view", "download"]

        results = {
            "total_processed": 0,
            "total_errors": 0,
            "event_types": {},
            "health_issues": [],
            "completed": False,
        }

        current_app.logger.info(f"Starting reindexing for event types: {event_types}")

        for event_type in event_types:
            if event_type not in ["view", "download"]:
                current_app.logger.warning(f"Unknown event type: {event_type}")
                continue

            source_index = next(
                idx for name, idx in self.source_indices if name == event_type
            )
            target_index = next(
                idx for name, idx in self.target_indices if name == event_type
            )

            current_app.logger.info(f"Processing {event_type} events")

            event_results = {"processed": 0, "errors": 0, "batches": 0}

            # Get last processed ID from bookmark
            last_processed_id = self.get_reindexing_bookmark(event_type)
            if last_processed_id:
                current_app.logger.info(f"Resuming from bookmark: {last_processed_id}")

            batch_count = 0
            should_continue = True

            while should_continue:
                # Check max batches limit
                if max_batches and batch_count >= max_batches:
                    current_app.logger.info(
                        f"Reached max batches limit for {event_type}"
                    )
                    break

                # Process batch
                processed_count, last_id, continue_processing = (
                    self.process_event_batch(
                        event_type, source_index, target_index, last_processed_id
                    )
                )

                if processed_count > 0:
                    event_results["processed"] += processed_count
                    event_results["batches"] += 1
                    results["total_processed"] += processed_count
                    last_processed_id = last_id
                else:
                    event_results["errors"] += 1
                    results["total_errors"] += 1

                should_continue = continue_processing and processed_count > 0
                batch_count += 1

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            results["event_types"][event_type] = event_results
            current_app.logger.info(f"Completed {event_type}: {event_results}")

        results["completed"] = True
        current_app.logger.info(f"Reindexing completed: {results}")
        return results

    def estimate_total_events(self) -> Dict[str, int]:
        """Estimate the total number of events to reindex."""
        estimates = {}

        for event_type, source_index in self.source_indices:
            try:
                search = Search(using=self.client, index=source_index)
                count = search.count()
                estimates[event_type] = count
                current_app.logger.info(f"Estimated {count} events for {event_type}")
            except Exception as e:
                current_app.logger.error(
                    f"Failed to estimate events for {event_type}: {e}"
                )
                estimates[event_type] = 0

        return estimates

    def get_reindexing_progress(self) -> Dict[str, Any]:
        """Get current reindexing progress."""
        progress = {
            "estimates": self.estimate_total_events(),
            "bookmarks": {},
            "health": {},
        }

        for event_type, _ in self.source_indices:
            bookmark = self.get_reindexing_bookmark(event_type)
            progress["bookmarks"][event_type] = bookmark

        is_healthy, reason = self.check_health_conditions()
        progress["health"] = {
            "is_healthy": is_healthy,
            "reason": reason,
            "memory_usage": self.get_memory_usage(),
        }

        return progress


class CommunityStatsService:
    """Service for managing statistics related to communities."""

    def __init__(self, app: Flask):
        self.client = current_search_client
        self.app = app

    def aggregate_stats(
        self,
        community_ids: list[str],
        start_date: str,
        end_date: str,
        eager: bool = False,
        update_bookmark: bool = True,
        ignore_bookmark: bool = False,
    ) -> dict:
        """Aggregate statistics for a community."""

        task = CommunityStatsAggregationTask["task"]
        args = CommunityStatsAggregationTask["args"]
        if eager:
            results = task(
                *args,
                start_date=start_date,
                end_date=end_date,
                update_bookmark=update_bookmark,
                ignore_bookmark=ignore_bookmark,
            )
        else:
            task_run = task.delay(
                *args,
                start_date=start_date,
                end_date=end_date,
                update_bookmark=update_bookmark,
                ignore_bookmark=ignore_bookmark,
            )
            results = task_run.get()

        return results

    def generate_record_community_events(
        self,
        recids: list[str] | None = None,
        community_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[int, int, int]:
        """Create `stats-community-events` index events for one or more records.

        This method will create proper stats-community-events records for every record
        in an InvenioRDM instance (or the provided recids). For each record, it will:
        1. Create "added" events for all communities the record belongs to
        2. Ensure a "global" addition event exists for every record

        Args:
            recids: The record IDs to update. If not provided, all records will be
                updated.
            community_ids: The community IDs to update. If not provided, all
                communities will be updated.
            start_date: The start date for the events. If not provided, the start date
                will be the first record creation date in the instance.
            end_date: The end date for the events. If not provided, the end date will be
                the current date.

        Returns:
            The number of records processed.
        """
        records_processed = 0
        new_events_created = 0
        old_events_found = 0
        start_date_str = (
            (arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss"))
            if start_date
            else None
        )
        end_date_str = (
            (arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss"))
            if end_date
            else None
        )

        record_search = Search(
            using=self.client, index=prefix_index("rdmrecords-records")
        )
        terms = []
        if recids:
            terms.append({"terms": {"id": recids}})
        if start_date_str:
            terms.append({"range": {"created": {"gte": start_date_str}}})
        if end_date_str:
            terms.append({"range": {"created": {"lte": end_date_str}}})

        if len(terms) > 0:
            record_search = record_search.query({"bool": {"must": terms}})
        else:
            record_search = record_search.query({"match_all": {}})

        if not community_ids:
            communities = current_communities.service.read_all(system_identity, [])
            community_ids = [c["id"] for c in communities]

        for result in record_search.scan():
            record_id = result["id"]
            record_data = result.to_dict()
            current_app.logger.error(f"Generating events for record: {record_id}")

            try:
                record_created_date = record_data.get("created")
                record_published_date = record_data.get("metadata", {}).get(
                    "publication_date", None
                )

                record_communities = (
                    record_data.get("parent", {}).get("communities", {}).get("ids", [])
                )
                current_app.logger.error(
                    f"Record {record_id} belongs to communities: "
                    f"{record_communities}"
                )

                communities_to_process = ["global"]
                for community_id in community_ids:
                    if community_id in record_communities:
                        communities_to_process.append(community_id)

                current_app.logger.error(
                    f"Processing communities for record {record_id}: "
                    f"{communities_to_process}"
                )

                existing_events = []
                try:
                    # Debug: Check the values being used in the query
                    current_app.logger.error(
                        f"DEBUG: record_id='{record_id}' " f"(type: {type(record_id)})"
                    )
                    current_app.logger.error(
                        f"DEBUG: communities_to_process={communities_to_process} "
                        f"(type: {type(communities_to_process)})"
                    )

                    existing_events_search = Search(
                        using=self.client, index=prefix_index("stats-community-events")
                    )

                    # Use raw query dict instead of Q objects
                    query_dict = {
                        "bool": {
                            "must": [
                                {"term": {"record_id": record_id}},
                                {"terms": {"community_id": communities_to_process}},
                                {"term": {"event_type": "added"}},
                            ]
                        }
                    }

                    existing_events_search = existing_events_search.query(query_dict)
                    current_app.logger.error(
                        f"Existing events search: {existing_events_search.to_dict()}"
                    )
                    existing_events = list(existing_events_search.execute())
                    old_events_found += len(existing_events)
                except Exception as e:
                    current_app.logger.warning(
                        f"Could not search stats-community-events index: {e}. "
                        f"Treating as empty."
                    )

                existing_community_ids = {
                    event["community_id"] for event in existing_events
                }

                current_app.logger.error(
                    f"Found {len(existing_events)} existing events for "
                    f"record {record_id}"
                )
                current_app.logger.error(
                    f"Existing events: {[e.to_dict() for e in existing_events]}"
                )

                communities_to_add = [
                    community_id
                    for community_id in communities_to_process
                    if community_id not in existing_community_ids
                ]

                current_app.logger.error(
                    f"Will create events for communities: {communities_to_add}"
                )

                if communities_to_add:
                    new_events_created += len(communities_to_add)
                    update_community_events_index(
                        record_id=record_id,
                        community_ids_to_add=communities_to_add,
                        timestamp=record_created_date,
                        record_created_date=record_created_date,
                        record_published_date=record_published_date,
                        client=self.client,
                    )
                    current_app.logger.error(
                        f"Created {len(communities_to_add)} events for "
                        f"record {record_id}"
                    )

                    # Refresh the search index to ensure new events are searchable
                    try:
                        self.client.indices.refresh(
                            index=prefix_index("stats-community-events")
                        )
                    except Exception as e:
                        current_app.logger.error(
                            f"Error refreshing community events index: {e}"
                        )
                else:
                    current_app.logger.error(
                        f"No new events needed for record {record_id}"
                    )

                records_processed += 1

            except Exception as e:
                current_app.logger.error(f"Error processing record {record_id}: {e}")

        current_app.logger.error(f"Total records processed: {records_processed}")
        return records_processed, new_events_created, old_events_found

    def read_stats(self, community_id: str, start_date: str, end_date: str) -> dict:
        """Read statistics for a community."""
        query = CommunityStatsResultsQuery(
            name="community-stats",
            index="stats-community-stats",
            client=self.client._get_current_object(),
        )
        return query.run(community_id, start_date, end_date)
