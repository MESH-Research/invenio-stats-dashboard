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
import os
import json


class EventReindexingService:
    """Service for reindexing events with enriched metadata.

    This service handles the reindexing of existing events to add community_id
    and metadata fields for faster aggregation performance. It works with monthly
    indices and manages aliases properly to ensure zero downtime.
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
        self._source_index_patterns = None
        self._target_index_patterns = None

    @property
    def bookmark_api(self):
        """Lazy-load bookmark API that requires application context."""
        if self._bookmark_api is None:
            self._bookmark_api = CommunityBookmarkAPI(
                self.client, "event-reindexing", "monthly"
            )
        return self._bookmark_api

    @property
    def source_index_patterns(self):
        """Lazy-load source index patterns that require application context."""
        if self._source_index_patterns is None:
            self._source_index_patterns = [
                ("view", prefix_index("events-stats-record-view")),
                ("download", prefix_index("events-stats-file-download")),
            ]
        return self._source_index_patterns

    @property
    def target_index_patterns(self):
        """Lazy-load target index patterns that require application context."""
        if self._target_index_patterns is None:
            self._target_index_patterns = [
                ("view", prefix_index("events-stats-record-view-enriched")),
                ("download", prefix_index("events-stats-file-download-enriched")),
            ]
        return self._target_index_patterns

    def get_monthly_indices(self, event_type: str) -> List[str]:
        """Get all monthly indices for a given event type."""
        try:
            pattern = next(
                pattern
                for name, pattern in self.source_index_patterns
                if name == event_type
            )
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

    def get_reindexing_bookmark(self, event_type: str, month: str) -> Optional[str]:
        """Get the last processed event ID for a specific event type and month."""
        try:
            bookmark = self.bookmark_api.get_bookmark(
                f"{event_type}-{month}-reindexing"
            )
            return str(bookmark) if bookmark else None
        except Exception as e:
            current_app.logger.warning(
                f"Could not get bookmark for {event_type}-{month}: {e}"
            )
            return None

    def set_reindexing_bookmark(
        self, event_type: str, month: str, last_event_id: str
    ) -> None:
        """Set the bookmark for the last processed event ID."""
        try:
            self.bookmark_api.set_bookmark(
                f"{event_type}-{month}-reindexing", last_event_id
            )
            current_app.logger.info(
                f"Updated bookmark for {event_type}-{month}: {last_event_id}"
            )
        except Exception as e:
            current_app.logger.error(
                f"Failed to set bookmark for {event_type}-{month}: {e}"
            )

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

    def create_enriched_index(self, event_type: str, month: str) -> str:
        """Create a new enriched index for the given month."""
        try:
            # Get the target pattern
            target_pattern = next(
                pattern
                for name, pattern in self.target_index_patterns
                if name == event_type
            )
            # Add a differentiator to avoid naming conflicts
            new_index_name = f"{target_pattern}-{month}-v2"

            # Create the index with the same settings as the template
            # The template will automatically apply the correct mappings
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
            # Check document counts
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
                "bool", must_not=[{"exists": {"field": "community_id"}}]
            )
            missing_community = search.count()

            if missing_community > 0:
                current_app.logger.error(
                    f"Found {missing_community} documents without community_id "
                    f"in {target_index}"
                )
                return False

            current_app.logger.info(f"Validation passed for {target_index}")
            return True
        except Exception as e:
            current_app.logger.error(f"Validation failed for {target_index}: {e}")
            return False

    def update_aliases(
        self, event_type: str, month: str, old_index: str, new_index: str
    ) -> bool:
        """Update aliases to point to the new enriched index."""
        try:
            # Get the alias pattern
            alias_pattern = next(
                pattern
                for name, pattern in self.source_index_patterns
                if name == event_type
            )

            # Remove old index from alias and add new index
            actions = [
                {"remove": {"index": old_index, "alias": alias_pattern}},
                {"add": {"index": new_index, "alias": alias_pattern}},
            ]

            self.client.indices.update_aliases(body={"actions": actions})
            current_app.logger.info(
                f"Updated alias {alias_pattern} to point to {new_index}"
            )
            return True
        except Exception as e:
            current_app.logger.error(
                f"Failed to update aliases for {event_type}-{month}: {e}"
            )
            return False

    def setup_write_alias_for_current_month(
        self, event_type: str, month: str, old_index: str, new_index: str
    ) -> bool:
        """
        Set up write alias for current month to ensure new writes go to the new index.
        """
        try:
            # Create a write alias that points to the new index
            # The write alias should have the same name as the old index
            # so that new writes go to the new enriched index
            write_alias = old_index

            actions = [{"add": {"index": new_index, "alias": write_alias}}]

            self.client.indices.update_aliases(body={"actions": actions})
            msg = "Created write alias %s " "pointing to %s"
            current_app.logger.info(
                msg,
                write_alias,
                new_index,
            )
            return True
        except Exception as e:
            current_app.logger.error(
                f"Failed to create write alias for {event_type}-{month}: " f"{e}"
            )
            return False

    def check_for_new_records(
        self, index: str, last_processed_id: Optional[str] = None
    ) -> int:
        """Check if new records were written to an index after a certain point."""
        try:
            search = Search(using=self.client, index=index)
            search = search.sort("_id")

            if last_processed_id:
                search = search.extra(search_after=[last_processed_id])

            response = search.execute()
            return len(response.hits.hits)
        except Exception as e:
            current_app.logger.error(f"Failed to check for new records in {index}: {e}")
            return 0

    def migrate_new_records(
        self, source_index: str, target_index: str, last_processed_id: Optional[str]
    ) -> bool:
        """Migrate any new records that were written after the initial migration."""
        try:
            search = Search(using=self.client, index=source_index)
            search = search.sort("_id")
            if last_processed_id:
                search = search.extra(search_after=[last_processed_id])
            search = search.extra(size=self.batch_size)

            response = search.execute()
            hits = response.hits.hits

            if not hits:
                current_app.logger.info(
                    f"No new records to migrate from {source_index}"
                )
                return True

            current_app.logger.info(
                f"Migrating {len(hits)} new records from {source_index}"
            )

            # Extract record IDs and enrich events
            record_ids = list(set(hit["_source"]["recid"] for hit in hits))
            metadata = self.get_metadata_for_records(record_ids)
            community_membership = self.get_community_membership(record_ids)

            # Enrich and bulk index
            enriched_docs = []
            for hit in hits:
                event = hit["_source"]
                record_id = event["recid"]
                record_metadata = metadata.get(record_id, {})
                record_communities = community_membership.get(record_id, [])

                enriched_event = self.enrich_event(
                    event, record_metadata, record_communities
                )
                enriched_docs.append(
                    {
                        "_index": target_index,
                        "_source": enriched_event,
                    }
                )

            if enriched_docs:
                success, errors = bulk(self.client, enriched_docs, stats_only=False)
                if errors:
                    current_app.logger.error(
                        f"Bulk indexing errors for new records: {errors}"
                    )
                    return False

                current_app.logger.info(
                    f"Successfully migrated {len(enriched_docs)} new records"
                )

            return True
        except Exception as e:
            current_app.logger.error(f"Failed to migrate new records: {e}")
            return False

    def delete_old_index(self, index: str) -> bool:
        """Delete the old index after successful migration."""
        try:
            self.client.indices.delete(index=index)
            current_app.logger.info(f"Deleted old index: {index}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to delete old index {index}: {e}")
            return False

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

    def process_monthly_index(
        self,
        event_type: str,
        source_index: str,
        target_index: str,
        month: str,
        last_processed_id: Optional[str] = None,
    ) -> Tuple[int, Optional[str], bool]:
        """
        Process a monthly index for reindexing.

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
                current_app.logger.info(
                    f"No more events to process for {event_type}-{month}"
                )
                return 0, last_processed_id, True

            current_app.logger.info(
                f"Processing {len(hits)} events for {event_type}-{month}"
            )

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
            self.set_reindexing_bookmark(event_type, month, last_event_id)

            # Force garbage collection
            gc.collect()

            return len(hits), last_event_id, True

        except (ConnectionTimeout, ConnectionError, RequestError) as e:
            current_app.logger.error(f"OpenSearch error during batch processing: {e}")
            return 0, last_processed_id, False
        except Exception as e:
            current_app.logger.error(f"Unexpected error during batch processing: {e}")
            return 0, last_processed_id, False

    def migrate_monthly_index(
        self,
        event_type: str,
        source_index: str,
        month: str,
        max_batches: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Migrate a single monthly index to enriched format.

        Args:
            event_type: The type of event (view or download)
            source_index: The source monthly index name
            month: The month being migrated (YYYY-MM format)
            max_batches: Maximum number of batches to process

        Returns:
            Dictionary with migration results and statistics.
        """
        results = {
            "month": month,
            "event_type": event_type,
            "source_index": source_index,
            "processed": 0,
            "errors": 0,
            "batches": 0,
            "completed": False,
            "target_index": None,
        }

        current_app.logger.info(f"Starting migration for {event_type}-{month}")

        try:
            # Step 1: Create new enriched index
            target_index = self.create_enriched_index(event_type, month)
            results["target_index"] = target_index

            # Step 2: Migrate data
            last_processed_id = self.get_reindexing_bookmark(event_type, month)
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

                # Process batch
                processed_count, last_id, continue_processing = (
                    self.process_monthly_index(
                        event_type, source_index, target_index, month, last_processed_id
                    )
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

            # Step 3: Validate the migrated data
            if not self.validate_enriched_data(source_index, target_index):
                current_app.logger.error(f"Validation failed for {event_type}-{month}")
                results["completed"] = False
                return results

            # Step 4: Update aliases
            if not self.update_aliases(event_type, month, source_index, target_index):
                current_app.logger.error(
                    f"Failed to update aliases for {event_type}-{month}"
                )
                results["completed"] = False
                return results

            # Step 5: Handle current month write alias
            is_current_month = self.is_current_month_index(source_index)
            if is_current_month:
                if not self.setup_write_alias_for_current_month(
                    event_type, month, source_index, target_index
                ):
                    current_app.logger.error(
                        f"Failed to setup write alias for {event_type}-{month}"
                    )
                    results["completed"] = False
                    return results

                # Check for new records written during migration
                new_records_count = self.check_for_new_records(
                    source_index, last_processed_id
                )
                if new_records_count > 0:
                    current_app.logger.info(
                        f"Found {new_records_count} new records, migrating them"
                    )
                    if not self.migrate_new_records(
                        source_index, target_index, last_processed_id
                    ):
                        current_app.logger.error(
                            f"Failed to migrate new records for {event_type}-{month}"
                        )
                        results["completed"] = False
                        return results

            # Step 6: Delete old index (only if not current month or after
            # write alias is set)
            if not is_current_month:
                if not self.delete_old_index(source_index):
                    msg = "Failed to delete old index %s"
                    current_app.logger.warning(
                        msg,
                        source_index,
                    )

            results["completed"] = True
            current_app.logger.info(
                f"Migration completed for {event_type}-{month}: {results}"
            )

        except Exception as e:
            current_app.logger.error(f"Migration failed for {event_type}-{month}: {e}")
            results["completed"] = False

        return results

    def update_and_verify_templates(self):
        """Update and verify the enriched event index templates before reindexing."""
        # Template file paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        view_template_path = os.path.join(
            base_dir,
            "search_indices/search_templates/stats_events_record_view_enriched/os-v2/"
            "stats-events-record-view-enriched-v1.0.0.json",
        )
        download_template_path = os.path.join(
            base_dir,
            "search_indices/search_templates/stats_events_file_download_enriched/os-v2/"
            "stats-events-file-download-enriched-v1.0.0.json",
        )
        # Template names (must match invenio-stats exactly)
        view_template_name = "stats_events_record_view"
        download_template_name = "stats_events_file_download"
        # Patterns (must match existing invenio-stats patterns exactly)
        view_pattern = "__SEARCH_INDEX_PREFIX__events-stats-record-view-*"
        download_pattern = "__SEARCH_INDEX_PREFIX__events-stats-file-download-*"
        # Aliases (must match existing invenio-stats aliases exactly)
        view_alias = "__SEARCH_INDEX_PREFIX__events-stats-record-view"
        download_alias = "__SEARCH_INDEX_PREFIX__events-stats-file-download"
        # Fields to check
        required_fields = [
            "community_id",
            "resource_type",
            "access_rights",
            "publisher",
            "languages",
            "subjects",
            "licenses",
            "affiliations",
            "funders",
            "periodical",
        ]

        # Helper to load, patch, and update a template
        def update_template(template_path, template_name, pattern, alias):
            with open(template_path, "r") as f:
                template = json.load(f)
            # Patch index_patterns to match existing invenio-stats patterns
            template["index_patterns"] = [pattern]
            # Patch aliases to match existing invenio-stats aliases
            template["template"]["aliases"] = {alias: {}}
            # Patch any __SEARCH_INDEX_PREFIX__ (if present)
            template = json.loads(
                json.dumps(template).replace("__SEARCH_INDEX_PREFIX__", "")
            )
            # Update template
            self.client.indices.put_index_template(name=template_name, body=template)
            # Fetch and verify
            result = self.client.indices.get_index_template(name=template_name)
            mappings = result["index_templates"][0]["index_template"]["template"][
                "mappings"
            ]
            for field in required_fields:
                if field not in mappings.get("properties", {}):
                    raise RuntimeError(
                        f"Field '{field}' missing in template '{template_name}' "
                        f"after update."
                    )

        # Update both templates
        update_template(
            view_template_path, view_template_name, view_pattern, view_alias
        )
        update_template(
            download_template_path,
            download_template_name,
            download_pattern,
            download_alias,
        )
        current_app.logger.info("Updated and verified enriched event index templates.")

    def reindex_events(
        self, event_types: Optional[List[str]] = None, max_batches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Reindex events with enriched metadata for all monthly indices.

        Args:
            event_types: List of event types to process. If None, process all.
            max_batches: Maximum number of batches to process per month. If None,
            process all.

        Returns:
            Dictionary with reindexing results and statistics.
        """
        # Update and verify templates before starting
        self.update_and_verify_templates()
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

            current_app.logger.info(f"Processing {event_type} events")

            # Get all monthly indices for this event type
            monthly_indices = self.get_monthly_indices(event_type)
            if not monthly_indices:
                current_app.logger.warning(f"No monthly indices found for {event_type}")
                continue

            event_results = {"processed": 0, "errors": 0, "months": {}}

            for source_index in monthly_indices:
                # Extract month from index name
                month = source_index.split("-")[-1]  # Get YYYY-MM part

                current_app.logger.info(
                    f"Processing {event_type} events for month {month}"
                )

                month_results = self.migrate_monthly_index(
                    event_type, source_index, month, max_batches
                )

                event_results["months"][month] = month_results
                event_results["processed"] += month_results.get("processed", 0)
                event_results["errors"] += month_results.get("errors", 0)

                if month_results.get("completed", False):
                    results["total_processed"] += month_results.get("processed", 0)
                else:
                    results["total_errors"] += 1

            results["event_types"][event_type] = event_results
            current_app.logger.info(f"Completed {event_type}: {event_results}")

        results["completed"] = True
        current_app.logger.info(f"Reindexing completed: {results}")
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
                bookmark = self.get_reindexing_bookmark(event_type, month)
                progress["bookmarks"][event_type][month] = bookmark

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
                    msg = "DEBUG: record_id='%s' (type: %s)"
                    current_app.logger.error(
                        msg,
                        record_id,
                        type(record_id),
                    )
                    msg2 = "DEBUG: communities_to_process=%s (type: %s)"
                    current_app.logger.error(
                        msg2,
                        communities_to_process,
                        type(communities_to_process),
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
