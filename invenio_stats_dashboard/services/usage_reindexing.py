# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service for reindexing events with enriched metadata."""

import random
import time
from functools import wraps

import arrow
import psutil
from flask import Flask, current_app
from glom import Spec, glom
from invenio_search.proxies import current_search, current_search_client
from invenio_search.utils import prefix_index
from opensearchpy import Index, Q
from opensearchpy.exceptions import (
    ConnectionError,
    ConnectionTimeout,
    NotFoundError,
    RequestError,
)
from opensearchpy.helpers import bulk
from opensearchpy.helpers.search import Search

from ..aggregations.bookmarks import CommunityBookmarkAPI
from ..exceptions import MissingCommunityEventsError
from ..utils.decorators import time_operation
from .types import (
    BatchProcessingResult,
    EventTypeResults,
    HealthCheckResult,
    MigratedMonthCounts,
    MigrationResult,
    MonthlyIndexBatchResult,
    OldMonthCounts,
    ProgressCounts,
    ReindexingProgress,
    ReindexingResults,
    SpotCheckResult,
    ValidationResult,
)


class MetadataExtractor:
    """High-performance metadata field extractor using pre-compiled glom specs.

    This class pre-compiles all extraction paths from the subcount configuration
    for maximum performance during event enrichment. It also caches extracted
    values by record ID to avoid repeated extraction for the same record.

    Requires the glom library to be installed.
    """

    def __init__(self, subcount_configs: dict):
        """Initialize the enricher with pre-compiled specs.

        Args:
            subcount_configs: The COMMUNITY_STATS_SUBCOUNTS
        """
        self.subcount_configs = subcount_configs
        self.compiled_specs: dict[str, Spec] = {}
        self._compile_specs()

        # Cache for extracted values by record ID
        self._extraction_cache: dict[str, dict] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _compile_specs(self):
        """Pre-compile all extraction specs for maximum performance."""
        for subcount_config in self.subcount_configs.values():
            if (
                "usage_events" in subcount_config
                and subcount_config["usage_events"]
                and subcount_config["usage_events"].get("event_field") is not None
            ):
                usage_config = subcount_config["usage_events"]
                event_field = usage_config["event_field"]
                extraction_path = usage_config.get("extraction_path_for_event")

                if extraction_path is not None:
                    # Store the compiled spec for this field
                    if isinstance(extraction_path, str):
                        self.compiled_specs[event_field] = Spec(extraction_path)
                    else:
                        # For lambda functions, store the function directly
                        self.compiled_specs[event_field] = extraction_path

    def extract_fields(self, metadata: dict, record_id: str | None = None) -> dict:
        """Extract all configured fields from metadata using pre-compiled specs.

        Args:
            metadata: The metadata dictionary to extract from
            record_id: Optional record ID for caching. If provided, results are cached.

        Returns:
            Dictionary of extracted field values
        """
        # If we have a record ID, check the cache first
        if record_id and record_id in self._extraction_cache:
            self._cache_hits += 1
            cached_result = self._extraction_cache[record_id]
            return cached_result.copy() if isinstance(cached_result, dict) else {}

        # Cache miss - extract the fields
        self._cache_misses += 1
        enrichment = {}

        for event_field, spec in self.compiled_specs.items():
            try:
                if callable(spec):
                    # Lambda function - call directly
                    field_value = spec(metadata)
                else:
                    # Pre-compiled glom spec - use for maximum performance
                    field_value = glom(metadata, spec)

                enrichment[event_field] = field_value
            except Exception:
                # If extraction fails, set to None
                enrichment[event_field] = None

        # Cache the result if we have a record ID
        if record_id:
            self._extraction_cache[record_id] = enrichment.copy()

        return enrichment

    def clear_cache(self):
        """Clear the extraction cache to free memory."""
        self._extraction_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cache_stats(self) -> dict:
        """Get cache performance statistics.

        Returns:
            Dictionary with cache hit rate and memory usage info
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_records": len(self._extraction_cache),
            "total_requests": total_requests,
        }


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
        """Initialize the usage reindexing service.

        Args:
            client: The OpenSearch client instance.
        """
        self.client = client
        self.bookmark_index = "stats-bookmarks-reindexing"

    @staticmethod
    def _ensure_index_exists(func):
        """Decorator for ensuring the bookmarks index exists."""

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not Index(prefix_index(self.bookmark_index), using=self.client).exists():
                self.client.indices.create(
                    index=prefix_index(self.bookmark_index),
                    body=EventReindexingBookmarkAPI.MAPPINGS,
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
            index=prefix_index(self.bookmark_index),
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
            Search(using=self.client, index=prefix_index(self.bookmark_index))
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
                "task_id": bookmark.task_id,
                "last_event_id": bookmark.last_event_id,
                "last_event_timestamp": arrow.get(bookmark.last_event_timestamp),
            }
        return None

    @_ensure_index_exists
    def delete_bookmark(self, task_id: str):
        """Delete a bookmark for a given task."""
        try:
            self.client.delete(index=prefix_index(self.bookmark_index), id=task_id)
        except Exception as e:
            current_app.logger.warning(f"Failed to delete bookmark {task_id}: {e}")

    @_ensure_index_exists
    def reset_bookmark_to_beginning(self, task_id: str, source_index: str):
        """Reset a bookmark by deleting it, allowing migration to start fresh.

        This is used when a migration fails to preserve failure information
        while indicating that the enriched index data is unreliable.
        Deleting the bookmark ensures we start from the very beginning.
        """
        try:
            self.delete_bookmark(task_id)
            current_app.logger.info(
                f"Reset bookmark for {task_id} by deletion - will start from beginning"
            )
        except Exception as e:
            current_app.logger.warning(
                f"Failed to reset bookmark {task_id} by deletion: {e}"
            )


class EventReindexingService:
    """Service for reindexing events with enriched metadata.

    This service provides configurable event enrichment based on the
    COMMUNITY_STATS_SUBCOUNTS configuration. It will always at minimum
    add a community_ids field. Which additional fields are added are determined
    by the COMMUNITY_STATS_SUBCOUNTS configuration.
    """

    def __init__(self, app: Flask):
        """Initialize the EventReindexingService.

        Args:
            app: The Flask application instance
        """
        self.client = current_search_client
        self.app = app

        self.max_batches = app.config.get(
            "STATS_DASHBOARD_REINDEXING_MAX_BATCHES", 1000
        )
        self.batch_size = app.config.get("STATS_DASHBOARD_REINDEXING_BATCH_SIZE", 1000)
        # IMPORTANT: OpenSearch has a hard limit of 10,000 documents for search results
        # This means batch_size cannot exceed 10,000, and any attempt to count documents
        # after a search_after position will be limited to 10,000 results maximum.

        # Validate batch_size doesn't exceed OpenSearch limit for search_after
        # query results, required by batch pagination.
        if self.batch_size > 10000:
            current_app.logger.warning(
                f"Batch size {self.batch_size} exceeds OpenSearch limit of 10,000. "
                f"Setting to 10,000."
            )
            self.batch_size = 10000
        self.max_memory_percent = app.config.get(
            "STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT", 75
        )
        self.max_spot_check_sample_size = app.config.get(
            "STATS_DASHBOARD_REINDEXING_MAX_SPOT_CHECK_SAMPLE_SIZE", 100
        )
        self.subcount_configs = app.config.get("COMMUNITY_STATS_SUBCOUNTS", {})

        # Lazy-load components that require application context
        self._reindexing_bookmark_api: EventReindexingBookmarkAPI | None = None
        self._index_patterns: dict | None = None
        self._metadata_extractor: MetadataExtractor | None = None
        self._month_count_without_communities = 0

    @property
    def metadata_extractor(self):
        """Lazy-load the metadata extractor with pre-compiled specs."""
        if self._metadata_extractor is None:
            self._metadata_extractor = MetadataExtractor(self.subcount_configs)
        return self._metadata_extractor

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
        """Check if any stats-community-events indices exist and have documents."""
        try:
            # Check if index has any documents by doing a match_all query
            index_pattern = f"{prefix_index('stats-community-events')}*"
            search = Search(using=self.client, index=index_pattern)
            search = search.query("match_all")
            count = search.count()
            return count > 0
        except (
            ConnectionError,
            ConnectionTimeout,
            RequestError,
            NotFoundError,
        ) as e:
            current_app.logger.info(f"Community events index check failed: {e}")
            return False

    def get_monthly_indices(
        self, event_type: str, month_filter: str | list[str] | tuple | None = None
    ) -> list[str]:
        """Get monthly indices for a given event type, optionally filtered by month.

        Args:
            event_type: The type of event (view or download)
            month_filter: Optional filter for specific months. Can be:
                - Single month: "2024-01"
                - Range: "2024-01:2024-03"
                - Multiple months: ("2024-01", "2024-02", "2024-03")
                - None: return all months
        """
        try:
            pattern = self.index_patterns[event_type]
            indices = self.client.indices.get(index=f"{pattern}-*")
            all_indices = sorted(indices.keys())

            old_indices = [
                idx
                for idx in all_indices
                if not idx.endswith("-v2.0.0") and not idx.endswith("-backup")
            ]

            if not month_filter:
                return old_indices

            # Parse the month filter and filter indices
            months_to_process = self._parse_month_filter(month_filter)
            if not months_to_process:
                return []

            filtered_indices = []
            for index in old_indices:
                year, month = index.split("-")[-2:]
                month_key = f"{year}-{month}"
                if month_key in months_to_process:
                    filtered_indices.append(index)

            return filtered_indices

        except Exception as e:
            error_msg = (
                f"Failed to get monthly indices for {event_type}: "
                f"{type(e).__name__}: {e}"
            )
            current_app.logger.error(error_msg)
            if month_filter:
                current_app.logger.info(
                    f"No {event_type} indices match the month filter: "
                    f"{month_filter}"
                )
            else:
                current_app.logger.warning(f"No monthly indices found for {event_type}")
            return []

    def get_current_month(self) -> str:
        """Get the current month in YYYY-MM format."""
        result = arrow.utcnow().format("YYYY-MM")
        return str(result)

    def is_current_month_index(self, index_name: str) -> bool:
        """Check if an index is for the current month."""
        current_month = self.get_current_month()
        return index_name.endswith(f"-{current_month}")

    def check_health_conditions(self) -> HealthCheckResult:
        """Check if we should continue processing or stop gracefully.

        We check if the memory usage is too high, and if the OpenSearch cluster is
        responsive.
        """
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > self.max_memory_percent:
            return HealthCheckResult(
                is_healthy=False, reason=f"Memory usage too high: {memory_usage}%"
            )

        try:
            self.client.cluster.health(timeout=5)
        except (ConnectionTimeout, ConnectionError) as e:
            return HealthCheckResult(
                is_healthy=False, reason=f"OpenSearch not responsive: {e}"
            )

        return HealthCheckResult(is_healthy=True, reason="OK")

    def create_enriched_index(
        self, event_type: str, month: str, fresh_start: bool = False
    ) -> str:
        """Create a new enriched index for the given month.

        Args:
            event_type: The type of event (view or download)
            month: The month in YYYY-MM format
            fresh_start: If True, delete existing target index before creating new one
        """
        try:
            target_pattern = self.index_patterns[event_type]
            # Add a differentiator to avoid naming conflicts
            new_index_name = f"{target_pattern}-{month}-v2.0.0"

            # Check if the index already exists
            if self.client.indices.exists(index=new_index_name):
                if fresh_start:
                    # Fresh start: clean up existing index and create new one
                    if not self._cleanup_existing_target_index(
                        new_index_name, event_type, month
                    ):
                        current_app.logger.warning(
                            f"Failed to clean up existing target index "
                            f"{new_index_name}, but continuing with creation attempt"
                        )
                    # Create new index after cleanup
                    self.client.indices.create(index=new_index_name)
                    current_app.logger.info(
                        f"Created new enriched index: {new_index_name}"
                    )
                else:
                    # Not fresh start: just use the existing index
                    current_app.logger.info(
                        f"Using existing enriched index: " f"{new_index_name}"
                    )
                return new_index_name
            else:
                # Index doesn't exist, create it
                self.client.indices.create(index=new_index_name)
                current_app.logger.info(f"Created enriched index: {new_index_name}")
                return new_index_name

        except Exception as e:
            current_app.logger.error(
                f"Failed to create enriched index for {event_type}-{month}: {e}"
            )
            raise

    def _cleanup_existing_target_index(
        self, target_index: str, event_type: str, month: str
    ) -> bool:
        """Clean up an existing target index and its aliases for fresh start.

        Args:
            target_index: The name of the target index to clean up
            event_type: The type of event (view or download)
            month: The month in YYYY-MM format

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Check if the index exists
            if not self.client.indices.exists(index=target_index):
                return True  # Nothing to clean up

            current_app.logger.info(
                f"Cleaning up existing target index: {target_index}"
            )

            # Remove any aliases that might point to this index
            try:
                aliases = self.client.indices.get_alias(index=target_index)
                for index_name, index_aliases in aliases.items():
                    if index_aliases.get("aliases"):
                        for alias_name in index_aliases["aliases"].keys():
                            self.client.indices.delete_alias(
                                index=index_name, name=alias_name
                            )
                            current_app.logger.info(
                                f"Removed alias {alias_name} from {index_name}"
                            )
            except Exception as e:
                current_app.logger.warning(
                    f"Failed to clean up aliases for {target_index}: {e}"
                )

            # Delete the index itself
            self.client.indices.delete(index=target_index)
            current_app.logger.info(
                f"Successfully deleted target index: {target_index}"
            )

            return True

        except Exception as e:
            current_app.logger.error(
                f"Failed to clean up target index {target_index}: {e}"
            )
            return False

    def _cleanup_existing_aliases_for_month(self, event_type: str, month: str) -> None:
        """Clean up any existing aliases that might point to old target indices.

        Args:
            event_type: The type of event (view or download)
            month: The month in YYYY-MM format
        """
        try:
            # Get the alias pattern for this event type
            alias_pattern = self.index_patterns[event_type]

            # Check if there are any existing aliases for this month
            try:
                aliases = self.client.indices.get_alias(name=f"{alias_pattern}-{month}")
                for index_name, index_aliases in aliases.items():
                    if index_aliases.get("aliases"):
                        for alias_name in index_aliases["aliases"].keys():
                            # Only remove aliases that point to v2.0.0 indices
                            # (our target indices)
                            if index_name.endswith("-v2.0.0"):
                                try:
                                    self.client.indices.delete_alias(
                                        index=index_name, name=alias_name
                                    )
                                    current_app.logger.info(
                                        f"Removed alias {alias_name} from {index_name} "
                                        f"for fresh start"
                                    )
                                except Exception as e:
                                    current_app.logger.warning(
                                        f"Failed to remove alias {alias_name} from "
                                        f"{index_name}: {e}"
                                    )
            except Exception as e:
                # No aliases found or other error - this is fine
                current_app.logger.debug(
                    f"No existing aliases found for {event_type}-{month}: {str(e)}"
                )

        except Exception as e:
            current_app.logger.warning(
                f"Failed to clean up aliases for {event_type}-{month}: {e}"
            )

    def validate_enriched_data(
        self,
        source_index: str,
        target_index: str,
        batch_document_ids: list[str] | None = None,
        last_processed_id: str | None = None,
        last_processed_timestamp: str | None = None,
        max_batches: int | None = None,
        fresh_start: bool = False,
        batches_attempted: int = 0,
        processed_count: int = 0,
    ) -> ValidationResult:
        """Validate that the enriched data matches the source data.

        Returns:
            ValidationResult with validation results including success status and
            detailed error information.
        """
        validation_results: ValidationResult = {
            "success": False,
            "errors": [],
            "document_counts": {},
            "missing_community_ids": 0,
            "spot_check": {
                "success": False,
                "errors": [],
                "details": {},
                "documents_verified": None,
                "field_mismatches": None,
                "document_count_mismatch": None,
            },
        }

        try:
            source_count = self.client.count(index=source_index)["count"]
            target_count = self.client.count(index=target_index)["count"]

            validation_results["document_counts"] = {
                "source": source_count,
                "target": target_count,
            }

            expected_records = self._get_expected_record_count(
                source_index,
                source_count,
                max_batches,
                fresh_start,
                last_processed_id,
                last_processed_timestamp,
            )

            # Validate document counts
            expected = expected_records
            if target_count != expected:
                error_msg = (
                    f"Document count mismatch: expected {expected}, "
                    f"found {target_count} in {target_index}"
                )
                current_app.logger.error(error_msg)
                validation_results["errors"].append(error_msg)
            else:
                validation_results["document_counts"]["match"] = True
                if expected_records:
                    validation_results["document_counts"]["expected"] = expected_records

            # Check that all documents have the required enriched fields
            # OpenSearch doesn't distinguish between absent field and []
            # for empty arrays, so we keep count of documents without community_ids
            search = Search(using=self.client, index=target_index)
            search = search.filter(
                "bool",
                must_not=[
                    {"exists": {"field": "community_ids"}},
                ],
            )
            hits_without_community = search.count()
            hits_missing_communities = hits_without_community - target_count

            validation_results["missing_community_ids"] = hits_missing_communities

            if hits_missing_communities > 0:
                error_msg = (
                    f"Found {hits_missing_communities} documents without community_ids "
                    f"in {target_index}"
                )
                current_app.logger.error(error_msg)
                validation_results["errors"].append(error_msg)
            else:
                pass

            spot_check_results = self._spot_check_original_fields(
                source_index, target_index, batch_document_ids or []
            )
            validation_results["spot_check"] = spot_check_results

            if not spot_check_results["success"]:
                error_msg = f"Spot-check validation failed for {target_index}"
                current_app.logger.error(error_msg)
                validation_results["errors"].extend(spot_check_results["errors"])
            else:
                # Spot-check passed (success is already True)
                pass

            # Determine overall success
            validation_results["success"] = len(validation_results["errors"]) == 0

            if validation_results["success"]:
                current_app.logger.info(f"Validation passed for {target_index}")
            else:
                current_app.logger.error(
                    f"Validation failed for {target_index} with "
                    f"{len(validation_results['errors'])} errors"
                )

        except Exception as e:
            error_msg = f"Validation failed for {target_index}: {type(e).__name__}: {e}"
            current_app.logger.error(error_msg)
            validation_results["errors"].append(error_msg)

        return validation_results

    def _spot_check_original_fields(
        self,
        source_index: str,
        target_index: str,
        batch_document_ids: list[str],
    ) -> SpotCheckResult:
        """Spot-check a sample of records to ensure original fields are unchanged.

        This method samples documents from the batch we just processed and compares
        them with the corresponding documents in the source index to ensure data
        integrity.

        Args:
            source_index: The source index name
            target_index: The target index name
            batch_document_ids: List of document IDs from the batch we just processed

        Returns:
            SpotCheckResult with spot-check results including success status and
            error details.
        """
        spot_check_results: SpotCheckResult = {
            "success": False,
            "errors": [],
            "details": {},
            "documents_verified": None,
            "field_mismatches": None,
            "document_count_mismatch": None,
        }

        try:
            if not batch_document_ids:
                current_app.logger.info("No documents in batch to spot-check")
                spot_check_results["success"] = True
                return spot_check_results

            # Sample documents for spot-check
            sample_size = min(self.max_spot_check_sample_size, len(batch_document_ids))
            sample_ids = batch_document_ids[:sample_size]

            # Get the sampled documents from both indices
            source_search = Search(using=self.client, index=source_index)
            source_search = source_search.filter("terms", _id=sample_ids)
            source_search = source_search.extra(size=len(sample_ids))
            source_hits = source_search.execute().hits.hits

            target_search = Search(using=self.client, index=target_index)
            target_search = target_search.filter("terms", _id=sample_ids)
            target_search = target_search.extra(size=len(sample_ids))
            target_hits = target_search.execute().hits.hits

            if len(target_hits) != len(source_hits):
                error_msg = (
                    f"Spot-check failed: found {len(target_hits)} target docs "
                    f"but {len(source_hits)} source docs"
                )
                current_app.logger.error(error_msg)
                spot_check_results["errors"].append(error_msg)
                spot_check_results["details"]["document_count_mismatch"] = {
                    "source": len(source_hits),
                    "target": len(target_hits),
                }
                return spot_check_results

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
                    f"Spot-check found {len(mismatches)} mismatches: "
                    f"{mismatches[:5]}"
                )
                spot_check_results["errors"].extend(mismatches)
                spot_check_results["details"]["field_mismatches"] = mismatches
                return spot_check_results

            current_app.logger.info(
                f"Spot-check passed: verified {len(source_docs)} documents "
                f"have unchanged original fields"
            )
            spot_check_results["success"] = True
            spot_check_results["details"]["documents_verified"] = len(source_docs)
            return spot_check_results

        except Exception as e:
            error_msg = f"Spot-check validation failed: {type(e).__name__}: {e}"
            current_app.logger.error(error_msg)
            spot_check_results["errors"].append(error_msg)
            return spot_check_results

    def _get_expected_record_count(
        self,
        source_index: str,
        source_count: int,
        max_batches: int | None,
        fresh_start: bool,
        last_processed_id: str | None,
        last_processed_timestamp: str | None,
    ) -> int:
        """Calculate the expected number of records based on migration context.

        Args:
            source_index: The source index name
            source_count: Total number of documents in source index
            max_batches: Maximum number of batches to process (None for unlimited)
            fresh_start: Whether this is a fresh start migration
            last_processed_id: ID of last processed event (None if starting from
                beginning)
            last_processed_timestamp: Timestamp of last processed event (None if
                starting from beginning)

        Returns:
            Expected number of records that should exist in target index
        """
        if fresh_start or (not last_processed_id and not last_processed_timestamp):
            if max_batches:
                result = min(max_batches * self.batch_size, source_count)
                return int(result)
            else:
                return int(source_count)
        else:
            if last_processed_id and last_processed_timestamp:
                docs_after_bookmark = self.count_remaining_after_bookmark(
                    source_index, last_processed_timestamp, last_processed_id
                )

                already_processed_before_bookmark = source_count - docs_after_bookmark

                if max_batches:
                    new_docs_expected = min(
                        max_batches * self.batch_size,
                        source_count - already_processed_before_bookmark,
                    )
                    result = already_processed_before_bookmark + new_docs_expected
                    return int(result)
                else:
                    return int(source_count)
            else:
                # No bookmark info - fallback to source count
                return source_count

    def update_alias(
        self, event_type: str, month: str, old_index: str, new_index: str
    ) -> bool:
        """Update the alias to point to the new enriched index for this month."""
        try:
            alias_pattern = self.index_patterns[event_type]
            current_app.logger.info(
                f"Starting alias update for {event_type}-{month}: "
                f"alias={alias_pattern}, old_index={old_index}, new_index={new_index}"
            )

            # First, add the alias to the new index (ensuring continuity)
            current_app.logger.info(
                f"Adding alias {alias_pattern} to new index {new_index}"
            )
            self.client.indices.put_alias(index=new_index, name=alias_pattern)
            current_app.logger.info(
                f"Successfully added alias {alias_pattern} to {new_index}"
            )

            # Then remove the alias from the old index (safe to do now)
            current_app.logger.info(
                f"Removing alias {alias_pattern} from old index {old_index}"
            )
            try:
                self.client.indices.delete_alias(index=old_index, name=alias_pattern)
                current_app.logger.info(
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
                current_app.logger.info(
                    f"Verification: alias {alias_pattern} exists on "
                    f"{new_index}: {alias_info}"
                )
            except Exception as e:
                current_app.logger.error(
                    f"Verification failed: alias {alias_pattern} not found on "
                    f"{new_index}: {e}"
                )

            current_app.logger.info(
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

    def _recover_missing_events(
        self, backup_index: str, new_index: str
    ) -> dict[str, bool | str | None]:
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

        Returns:
            Dict with success status and error message if applicable
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
                try:
                    enriched_actions = self._bulk_enrich_events(
                        missing_events,
                        new_index,
                    )

                    if enriched_actions:
                        success, failed = bulk(
                            self.client, enriched_actions, refresh=True
                        )
                        current_app.logger.info(
                            f"Recovered {success} missing events, {failed} failed"
                        )

                        # Check if bulk indexing had any failures
                        if failed > 0:
                            error_msg = (
                                f"Bulk indexing failed for {failed} out of "
                                f"{len(enriched_actions)} missing events during "
                                "recovery"
                            )
                            current_app.logger.error(error_msg)
                            return {"success": False, "error_message": error_msg}

                        # Return success if we successfully indexed all events
                        return {"success": True, "error_message": None}
                    else:
                        error_msg = (
                            "Missing events found but enrichment failed"
                            f"for events {[event['_id'] for event in missing_events]}"
                        )
                        current_app.logger.error(error_msg)
                        return {"success": False, "error_message": error_msg}

                except Exception as e:
                    error_msg = f"Failed to bulk enrich missing events: {e}"
                    current_app.logger.error(error_msg)
                    # Return failure - this will prevent backup deletion
                    return {"success": False, "error_message": error_msg}

            else:
                # No missing events to recover
                return {"success": True, "error_message": None}
        else:
            # No timestamp found, nothing to recover
            return {"success": True, "error_message": None}

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
            recovery_results = self._recover_missing_events(backup_index, new_index)
            if not recovery_results["success"]:
                current_app.logger.error(
                    f"Event recovery failed: {recovery_results['error_message']}, "
                    f"keeping backup for safety"
                )
                return False

            # Step 4.5: Validate the enriched index integrity before deleting backup
            current_app.logger.info("Step 4.5: Validating enriched index integrity")
            validation_results = self.validate_enriched_data(
                old_index, new_index, None, None
            )
            if not validation_results["success"]:
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
    ) -> list[dict]:
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

    def get_metadata_for_records(self, record_ids: list[str]) -> dict[str, dict]:
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
                    "created",
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
        self, record_ids: list[str], metadata_by_recid: dict[str, dict]
    ) -> dict[str, list[tuple[str, str]]]:
        """Get community membership for a batch of record IDs.

        We assume that the stats-community-events index will exist and be complete.

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

        try:
            search_pattern = f"{prefix_index('stats-community-events')}*"
            current_app.logger.info(
                f"Searching for community events using pattern: {search_pattern}"
            )
            community_search = Search(using=self.client, index=search_pattern)
            community_search = community_search.query(
                {"terms": {"record_id": record_ids}}
            )

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

            if hasattr(community_results, "aggregations") and hasattr(
                community_results.aggregations, "by_record"
            ):
                current_app.logger.error(
                    f"Found {len(community_results.aggregations.by_record.buckets)} "
                    f"record buckets in aggregations"
                )
            else:
                current_app.logger.warning("No aggregations found in search results")

            membership: dict[str, list] = {}
            for record_bucket in community_results.aggregations.by_record.buckets:
                record_id = record_bucket.key
                membership[record_id] = []

                for community_bucket in record_bucket.by_community.buckets:
                    community_id = community_bucket.key
                    if community_bucket.top_hit.hits.hits:
                        top_hit = community_bucket.top_hit.hits.hits[0]
                        event_type = top_hit["_source"]["event_type"]
                        event_date = top_hit["_source"]["event_date"]

                        if event_type == "added":
                            membership[record_id].append((community_id, event_date))

            # Fallback for records without community event index records
            missing_records = [rid for rid in record_ids if rid not in membership]
            if missing_records:
                raise MissingCommunityEventsError(
                    f"Found {len(missing_records)} records without community event "
                    f"index records, cannot get community membership for event "
                    "migration"
                )

            return membership
        except Exception as e:
            current_app.logger.error(f"Failed to fetch community membership: {e}")
            current_app.logger.error(f"Exception details: {str(e)}")
            # If the main method fails, try the fallback for all records
            current_app.logger.info("Using fallback for all records due to exception")
            fallback_result = self._get_community_membership_fallback(metadata_by_recid)
            current_app.logger.info(f"Fallback result: {fallback_result}")
            return fallback_result

    def _get_community_membership_fallback(
        self, metadata_by_recid: dict[str, dict]
    ) -> dict[str, list[tuple[str, str]]]:
        """Fallback method to get community membership from record metadata.

        DEPRECATED: This method is deprecated because we now require the
        stats-community-events index to exist.
        FIXME: Remove this method

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
                    using=self.client, index=prefix_index("communities")
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

            return membership

        except Exception as e:
            current_app.logger.error(
                f"Failed to get fallback community membership: {e}"
            )
            current_app.logger.error(f"Exception details: {str(e)}")
            return {}

    def _process_and_index_events_batch(
        self, hits: list[dict], target_index: str, context: str = "events"
    ) -> BatchProcessingResult:
        """Process a batch of events and bulk index them with error handling.

        Args:
            hits: List of search hits from OpenSearch
            target_index: Target index name for the enriched documents
            context: Context for logging (e.g., "new records", "events")

        Returns:
            BatchProcessingResult, which is a dictionary with the following keys:
            - success: bool
            - error_message: Optional[str]
        """
        if not hits:
            return {"success": True, "error_message": None}

        # Process events into enriched documents
        enriched_docs = self._bulk_enrich_events(hits, target_index)

        # Verify that we didn't lose any documents during enrichment
        if len(enriched_docs) != len(hits):
            current_app.logger.error(
                f"Document count mismatch during enrichment: "
                f"input hits: {len(hits)}, enriched docs: {len(enriched_docs)}"
            )
            return {
                "success": False,
                "error_message": (
                    f"Enrichment process lost documents: "
                    f"input {len(hits)} -> output {len(enriched_docs)}"
                ),
            }

        # Bulk index the enriched documents
        if not enriched_docs:
            current_app.logger.warning("No enriched documents to index")
            return {"success": True, "error_message": None}

        current_app.logger.info(
            f"Attempting to bulk index {len(enriched_docs)} enriched documents"
        )

        try:
            bulk_result = bulk(self.client, enriched_docs, refresh=True)
            success, failed = bulk_result

            # Handle different return types from bulk function
            if isinstance(failed, list):
                failed_count = len(failed)
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
                    return {
                        "success": False,
                        "error_message": (
                            f"Bulk indexing failed after {success} documents. "
                            f"Last successful: {last_successful_id}"
                        ),
                    }
                else:
                    return {
                        "success": False,
                        "error_message": (
                            "Bulk indexing failed - no documents were indexed"
                        ),
                    }

            current_app.logger.info(
                f"Successfully indexed {success} enriched {context}"
            )
            return {
                "success": True,
                "error_message": None,
            }

        except Exception as e:
            error_msg = f"Failed to bulk index {context}: {e}"
            current_app.logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg,
            }

    def _bulk_enrich_events(
        self,
        hits: list[dict],
        target_index: str,
    ) -> list[dict]:
        """Bulk enrich events using pre-computed enrichment data.

        Args:
            hits: List of event search hits from OpenSearch
            enrichment_lookup: Pre-computed enrichment data by record ID
            communities_by_recid: Community membership by record ID
            target_index: Target index name for the enriched documents

        Returns:
            List of enriched documents ready for bulk indexing (dicts)
        """
        enriched_docs = []

        record_ids = list(set(hit["_source"]["recid"] for hit in hits))
        metadata_by_recid = self.get_metadata_for_records(record_ids)
        communities_by_recid = self.get_community_membership(
            record_ids, metadata_by_recid
        )

        enrichment_lookup = {}
        for record_id in record_ids:
            metadata = metadata_by_recid.get(record_id, {})

            enrichment_lookup[record_id] = self.metadata_extractor.extract_fields(
                metadata, record_id
            )

        for hit in hits:
            event = hit["_source"]
            record_id = event["recid"]

            enrichment_data = enrichment_lookup.get(record_id, {}).copy()

            # Calculate community_ids based on event timestamp
            event_timestamp = event.get("timestamp")
            # Get the end of the event day to include communities added on same day
            event_date = arrow.get(event_timestamp)
            end_of_event_day = event_date.ceil("day").format("YYYY-MM-DDTHH:mm:ss.SSS")

            effective_communities = [
                c
                for c, effective_date in communities_by_recid.get(record_id, [])
                if effective_date <= end_of_event_day and c != "global"
            ]
            enrichment_data["community_ids"] = effective_communities
            if not effective_communities:
                self._month_count_without_communities += 1

            # Merge event with enrichment data (fast dictionary merge)
            enriched_event = {**event, **enrichment_data}

            enriched_docs.append(
                {
                    "_index": target_index,
                    "_id": hit["_id"],  # Preserve the original document ID
                    "_source": enriched_event,
                }
            )

        return enriched_docs

    def _get_active_communities_for_event(
        self, communities: list[tuple[str, str]], event_timestamp: str, metadata: dict
    ) -> list[str]:
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

            active_communities = []
            for community_id, event_date in communities:
                # Filter out "global" as it's not a real community
                if community_id == "global":
                    continue
                community_added_time = arrow.get(event_date)
                if event_time >= community_added_time:
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
        last_processed_id: str | None = None,
        last_processed_timestamp: str | None = None,
        previous_batch_ids: set | None = None,
        search_after_point: list | None = None,
    ) -> MonthlyIndexBatchResult:
        """Process a single batch of events from a monthly event index.

        Processes one batch of events from the monthly index, returning after
        each batch and keeping track of the progress with a bookmark and the
        last processed event ID.

        Args:
            event_type: The type of event (view or download)
            source_index: The source monthly index name
            target_index: The target enriched index name
            month: The month being migrated (YYYY-MM format)
            last_processed_id: The last processed event ID
            last_processed_timestamp: The timestamp of the last processed event

        Returns:
            Tuple of (processed_count, last_event_id, should_continue)

        Raises:
            ConnectionTimeout: If the connection to OpenSearch times out
            ConnectionError: If there is a connection error to OpenSearch
            RequestError: If there is a request error to OpenSearch
        """
        try:
            # Check health conditions
            health_check = self.check_health_conditions()
            if not health_check["is_healthy"]:
                current_app.logger.error(
                    f"Health check failed: {health_check['reason']}"
                )
                return {
                    "processed_count": 0,
                    "last_event_id": last_processed_id,
                    "last_event_timestamp": last_processed_timestamp,
                    "should_continue": False,
                    "batch_document_ids": [],
                    "previous_batch_ids": set(),
                    "search_after_point": None,
                }

            # Check if source index exists and has documents
            source_count = self.client.count(index=source_index)["count"]
            current_app.logger.info(
                f"Source index {source_index} has {source_count} documents"
            )

            search = Search(using=self.client, index=source_index)
            search = search.extra(size=self.batch_size)
            # Sort by timestamp first, then by _id to ensure consistent ordering
            # when multiple documents have the same timestamp
            search = search.sort("timestamp", "_id")

            if search_after_point:
                # Use the search_after_point from the previous batch to avoid missing
                # documents
                search = search.extra(search_after=search_after_point)

            response = search.execute()
            hits = response.to_dict()["hits"]["hits"]
            original_hits_count = len(hits)

            # Filter out already-processed IDs if we have them from the previous batch
            if previous_batch_ids:
                hits_before_filter = len(hits)
                hits = [hit for hit in hits if hit["_id"] not in previous_batch_ids]
                filtered_count = hits_before_filter - len(hits)
                current_app.logger.info(
                    f"Filtered out {filtered_count} already-processed IDs, "
                    f"remaining: {len(hits)} documents"
                )

            if not hits:
                current_app.logger.info(
                    f"No more events to process for {event_type}-{month}"
                )
                return {
                    "processed_count": 0,
                    "last_event_id": last_processed_id,
                    "last_event_timestamp": last_processed_timestamp,
                    "should_continue": False,
                    "batch_document_ids": [],
                    "previous_batch_ids": set(),
                    "search_after_point": None,
                }

            current_app.logger.info(
                f"Processing {len(hits)} events for {event_type}-{month}"
            )

            # Collect document IDs from this batch for spot-check validation
            batch_document_ids = [hit["_id"] for hit in hits]

            batch_result = self._process_and_index_events_batch(
                hits, target_index, "events"
            )
            if not batch_result["success"]:
                current_app.logger.error(
                    f"Failed to process batch: {batch_result['error_message']}"
                )
                return {
                    "processed_count": 0,
                    "last_event_id": last_processed_id,
                    "last_event_timestamp": last_processed_timestamp,
                    "should_continue": False,
                    "batch_document_ids": [],
                    "previous_batch_ids": set(),
                    "search_after_point": None,
                }

            last_event_id = hits[-1]["_id"]
            last_event_timestamp = hits[-1]["_source"]["timestamp"]

            # Collect all IDs that share the last timestamp to avoid lexicographic
            # ordering issues
            last_timestamp = last_event_timestamp
            same_timestamp_ids = set()
            for hit in hits:
                if hit["_source"]["timestamp"] == last_timestamp:
                    same_timestamp_ids.add(hit["_id"])

            # Use second-to-last timestamp for search_after to avoid missing
            # documents
            if len(hits) >= 2:
                second_to_last_timestamp = hits[-2]["_source"]["timestamp"]
                second_to_last_id = hits[-2]["_id"]
                search_after_point = [second_to_last_timestamp, second_to_last_id]
            else:
                # Handle edge case where batch has only one document
                search_after_point = [last_event_timestamp, last_event_id]

            # Set the bookmark with current position
            self.reindexing_bookmark_api.set_bookmark(
                f"{event_type}-{month}-reindexing", last_event_id, last_event_timestamp
            )
            # Check if there are more documents available after this batch
            # Only continue if we got a full batch AND there are more docs
            # Use original_hits_count to determine if this was a full batch before
            # filtering
            batch_was_full = original_hits_count == self.batch_size
            if batch_was_full:
                try:
                    count_search = Search(using=self.client, index=source_index)
                    count_search = count_search.sort("timestamp", "_id")
                    count_search = count_search.extra(
                        size=2, search_after=search_after_point
                    )
                    # Use execute() instead of count() to allow search_after
                    response = count_search.execute()
                    # Filter out already-processed IDs to avoid overlap issues
                    if previous_batch_ids:
                        filtered_hits = [
                            hit
                            for hit in response.hits
                            if hit["_id"] not in previous_batch_ids
                        ]
                        has_more_docs = len(filtered_hits) > 0
                    else:
                        has_more_docs = len(response.hits) > 0

                    timestamp_for_log = (
                        second_to_last_timestamp
                        if len(hits) >= 2
                        else last_event_timestamp
                    )
                    current_app.logger.info(
                        f"Batch was full ({len(hits)} docs), count after timestamp "
                        f"{timestamp_for_log} shows more documents"
                    )
                    return {
                        "processed_count": len(hits),
                        "last_event_id": last_event_id,
                        "last_event_timestamp": last_event_timestamp,
                        "should_continue": has_more_docs,
                        "batch_document_ids": batch_document_ids,
                        "previous_batch_ids": same_timestamp_ids,
                        "search_after_point": search_after_point,
                    }
                except Exception as e:
                    current_app.logger.error(f"Error checking count for more docs: {e}")
                    # If we can't check, assume there are more to be safe
                    return {
                        "processed_count": len(hits),
                        "last_event_id": last_event_id,
                        "last_event_timestamp": last_event_timestamp,
                        "should_continue": True,
                        "batch_document_ids": batch_document_ids,
                        "previous_batch_ids": same_timestamp_ids,
                        "search_after_point": search_after_point,
                    }
            else:
                # Partial batch means we're at the end
                current_app.logger.info(
                    f"Partial batch ({len(hits)} docs), no more documents available"
                )
                return {
                    "processed_count": len(hits),
                    "last_event_id": last_event_id,
                    "last_event_timestamp": last_event_timestamp,
                    "should_continue": False,
                    "batch_document_ids": batch_document_ids,
                    "previous_batch_ids": same_timestamp_ids,
                    "search_after_point": search_after_point,
                }

        except (ConnectionTimeout, ConnectionError, RequestError) as e:
            current_app.logger.error(f"OpenSearch error during batch processing: {e}")
            return {
                "processed_count": 0,
                "last_event_id": last_processed_id,
                "last_event_timestamp": last_processed_timestamp,
                "should_continue": False,
                "batch_document_ids": [],
                "previous_batch_ids": set(),
                "search_after_point": None,
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error during batch processing: {e}")
            return {
                "processed_count": 0,
                "last_event_id": last_processed_id,
                "last_event_timestamp": last_processed_timestamp,
                "should_continue": False,
                "batch_document_ids": [],
                "previous_batch_ids": set(),
                "search_after_point": None,
            }

    @time_operation
    def migrate_monthly_index(
        self,
        event_type: str,
        source_index: str,
        month: str,
        max_batches: int | None = None,
        delete_old_indices: bool = False,
        fresh_start: bool = False,
    ) -> MigrationResult:
        """Migrate a single monthly index to enriched format.

        Args:
            event_type: The type of event (view or download)
            source_index: The source monthly index name
            month: The month being migrated (YYYY-MM format)
            max_batches: Maximum number of batches to process
            delete_old_indices: Whether to delete old indices after migration
            fresh_start: Whether to start fresh (ignore existing bookmarks)

        Returns:
            Dictionary with migration results and statistics.
        """
        results: MigrationResult = {
            "month": month,
            "event_type": event_type,
            "source_index": source_index,
            "processed": 0,
            "interrupted": False,
            "batches_succeeded": 0,
            "completed": False,
            "target_index": None,
            "last_processed_id": None,
            "batches_attempted": 0,
            "validation_errors": None,
            "operational_errors": [],
            "start_time": arrow.utcnow().isoformat(),
            "total_time": None,
            "all_sample_document_ids": [],
        }
        # Reset count without communities for each migration
        self._month_count_without_communities = 0

        current_app.logger.info(f"Starting migration for {event_type}-{month}")

        def add_operational_error(error_type: str, error_message: str):
            """Helper to add operational errors to the results."""
            results["operational_errors"].append(
                {
                    "type": error_type,
                    "message": error_message,
                    "timestamp": arrow.utcnow().isoformat(),
                }
            )

        # Store initial bookmark for potential rollback
        initial_bookmark = self.reindexing_bookmark_api.get_bookmark(
            f"{event_type}-{month}-reindexing"
        )
        bookmark_was_set = initial_bookmark is not None

        # If fresh_start is enabled, clean up existing state
        if fresh_start:
            task_id = f"{event_type}-{month}-reindexing"

            # Delete existing bookmark
            try:
                self.reindexing_bookmark_api.delete_bookmark(task_id)
                current_app.logger.info(
                    f"Fresh start enabled - deleted existing bookmark for "
                    f"{event_type}-{month}"
                )
            except Exception as e:
                current_app.logger.warning(
                    f"Failed to delete bookmark for {event_type}-{month}: {e}"
                )

            # Reset bookmark tracking since we're starting fresh
            initial_bookmark = None
            bookmark_was_set = False

            # Also clean up any existing aliases that might point to old target indices
            self._cleanup_existing_aliases_for_month(event_type, month)

        try:
            # Step 1: Create new enriched index
            target_index = self.create_enriched_index(event_type, month, fresh_start)
            results["target_index"] = target_index

            # Get source count for better batch estimation
            source_count = self.client.count(index=source_index)["count"]
            current_app.logger.info(
                f"Source index {source_index} has {source_count} documents"
            )

            # Step 2: Migrate data
            if fresh_start:
                last_processed_id, last_processed_timestamp = None, None
                current_app.logger.info(
                    f"Fresh start enabled - starting migration from beginning for "
                    f"{event_type}-{month}"
                )
            else:
                bookmark = self.reindexing_bookmark_api.get_bookmark(
                    f"{event_type}-{month}-reindexing"
                )
                last_processed_id = str(bookmark["last_event_id"]) if bookmark else None
                last_processed_timestamp = (
                    bookmark["last_event_timestamp"].naive.strftime("%Y-%m-%dT%H:%M:%S")
                    if bookmark
                    else None
                )
                if last_processed_id and last_processed_timestamp:
                    current_app.logger.info(
                        f"Resuming from bookmark: {last_processed_id} "
                        f"at timestamp: {last_processed_timestamp}"
                    )
                else:
                    current_app.logger.info(
                        "No valid bookmark data found - starting from beginning"
                    )

            batch_count = 0
            should_continue = True
            previous_batch_ids: set[str] = set()
            search_after_point = None

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

                # Process batch
                batch_result = self.process_monthly_index_batch(
                    event_type,
                    source_index,
                    target_index,
                    month,
                    last_processed_id,
                    last_processed_timestamp,
                    previous_batch_ids,
                    search_after_point,
                )
                processed_count = batch_result["processed_count"]
                last_id = batch_result["last_event_id"]
                last_timestamp = batch_result["last_event_timestamp"]
                continue_processing = batch_result["should_continue"]
                batch_document_ids = batch_result.get("batch_document_ids", [])
                previous_batch_ids = (
                    batch_result.get("previous_batch_ids", set()) or set()
                )
                search_after_point = batch_result.get("search_after_point", None)

                current_app.logger.info(
                    f"Batch {batch_count + 1} result: processed={processed_count}, "
                    f"continue_processing={continue_processing}, last_id={last_id}"
                )

                # Log cumulative progress
                current_app.logger.info(
                    f"Total processed so far: {results['processed']} documents"
                )

                if processed_count > 0:
                    results["processed"] += processed_count
                    results["batches_succeeded"] += 1
                    # Always use the actual last document from the batch for bookmarking
                    # search_after_point is for pagination, not for bookmarking
                    last_processed_id = last_id
                    last_processed_timestamp = last_timestamp

                    # Collect a sample of document IDs from each batch for validation
                    total_batches = (source_count // self.batch_size) + (
                        1 if source_count % self.batch_size > 0 else 0
                    )
                    samples_per_batch = max(
                        1, self.max_spot_check_sample_size // total_batches
                    )
                    # Ensure we don't try to sample more documents than are available
                    # in this batch
                    actual_samples = min(samples_per_batch, len(batch_document_ids))
                    results["all_sample_document_ids"] += random.sample(
                        batch_document_ids, actual_samples
                    )
                else:
                    # Only treat as error if we're not at the end of the data
                    if continue_processing:
                        add_operational_error(
                            "batch_failure",
                            f"Batch {batch_count + 1} processed 0 events",
                        )
                    else:
                        current_app.logger.info(
                            f"Batch {batch_count + 1}: No more events to process "
                            f"for {event_type}-{month}"
                        )

                should_continue = continue_processing and processed_count > 0

                # Only increment batch count if we actually processed documents
                # This prevents counting "checking for more data" as an attempted batch
                if processed_count > 0:
                    batch_count += 1

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            # Always set batches_attempted to the actual number of batches
            # processed
            results["batches_attempted"] = batch_count

            # Check if migration was limited by max_batches
            # (even if should_continue is False)
            max_batches_limit_reached = max_batches and batch_count >= max_batches

            # Only mark as interrupted if we hit max_batches AND there's more data
            if should_continue or (max_batches_limit_reached and should_continue):
                reason = (
                    "max_batches limit" if max_batches_limit_reached else "incomplete"
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

                results["total_time"] = str(
                    arrow.utcnow() - arrow.get(results["start_time"])
                )

                # Set bookmark for interrupted migrations so they can be resumed
                # This ensures we can resume from the last successful batch
                if last_processed_id and last_processed_timestamp:
                    self.reindexing_bookmark_api.set_bookmark(
                        f"{event_type}-{month}-reindexing",
                        last_processed_id,
                        last_processed_timestamp,
                    )

                current_app.logger.info(
                    f"Migration interrupted for {event_type}-{month} after "
                    f"{results['total_time']}"
                )
                return results

            # Step 3: Validate the migrated data (only if migration completed)
            # Check if any new records were actually processed in this run
            if results["batches_attempted"] == 0:
                # No batches were processed - this means we're already at the end
                # or there was no data to process. Skip validation since no new
                # data was added.
                current_app.logger.info(
                    f"No new batches processed for {event_type}-{month} - "
                    "skipping validation (bookmark already at end)"
                )
                validation_results: ValidationResult = {
                    "success": True,
                    "errors": [],
                    "document_counts": {"match": True, "source": 0, "target": 0},
                    "missing_community_ids": 0,
                    "spot_check": {
                        "success": True,
                        "errors": [],
                        "details": {},
                        "documents_verified": None,
                        "field_mismatches": None,
                        "document_count_mismatch": None,
                    },
                }
            else:
                # Normal case: validate the migrated data
                validation_results = self.validate_enriched_data(
                    source_index,
                    target_index,
                    results.get("all_sample_document_ids", []),
                    last_processed_id,
                    last_processed_timestamp,
                    max_batches=max_batches,
                    fresh_start=fresh_start,
                    batches_attempted=results["batches_attempted"],
                    processed_count=results["processed"],
                )
            if not validation_results["success"]:
                current_app.logger.error(f"Validation failed for {event_type}-{month}")

                # Reset bookmark to beginning on validation failure
                self.reindexing_bookmark_api.reset_bookmark_to_beginning(
                    f"{event_type}-{month}-reindexing", source_index
                )
                current_app.logger.info(
                    f"Reset bookmark for {event_type}-{month} to beginning due to "
                    f"validation failure"
                )

                results["completed"] = False
                results["validation_errors"] = validation_results
                return results

            # Step 4: Update alias
            if not self.update_alias(event_type, month, source_index, target_index):
                current_app.logger.error(
                    f"Failed to update alias for {event_type}-{month}"
                )

                # Reset bookmark to beginning on alias update failure
                self.reindexing_bookmark_api.reset_bookmark_to_beginning(
                    f"{event_type}-{month}-reindexing", source_index
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

                    # Reset bookmark to beginning on write alias setup failure
                    self.reindexing_bookmark_api.reset_bookmark_to_beginning(
                        f"{event_type}-{month}-reindexing", source_index
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

            # Step 7: Set final bookmark after successful completion
            # This ensures the bookmark points to the end of the last successful batch
            if last_processed_id and last_processed_timestamp:
                self.reindexing_bookmark_api.set_bookmark(
                    f"{event_type}-{month}-reindexing",
                    last_processed_id,
                    last_processed_timestamp,
                )
                current_app.logger.info(
                    f"Set final bookmark for {event_type}-{month} to "
                    f"{last_processed_id}"
                )

                # Calculate timing information
                results["total_time"] = str(
                    arrow.utcnow() - arrow.get(results["start_time"])
                )

            results["completed"] = True
            current_app.logger.info(
                f"Migration completed for {event_type}-{month} in "
                f"{results['total_time']}: {results}"
            )

        except Exception as e:
            current_app.logger.error(f"Migration failed for {event_type}-{month}: {e}")

            # Collect unexpected error information
            add_operational_error("unexpected_error", f"{type(e).__name__}: {e}")

            # Rollback bookmark on any unexpected error
            if bookmark_was_set and initial_bookmark:
                last_event_id = initial_bookmark.get("last_event_id")
                if last_event_id:
                    self.reindexing_bookmark_api.set_bookmark(
                        f"{event_type}-{month}-reindexing",
                        last_event_id,
                        initial_bookmark.get("last_event_timestamp"),
                    )
                    current_app.logger.info(
                        f"Rolled back bookmark for {event_type}-{month} to "
                        f"{last_event_id} due to unexpected error"
                    )
            elif not bookmark_was_set:
                task_id = f"{event_type}-{month}-reindexing"
                self.reindexing_bookmark_api.delete_bookmark(task_id)

                # Calculate timing for failed migrations
                results["total_time"] = str(
                    arrow.utcnow() - arrow.get(results["start_time"])
                )

            current_app.logger.error(
                f"Migration failed for {event_type}-{month} after "
                f"{results['total_time']}"
            )

        return results

    def _get_templates_to_update(self, stats_events) -> list:
        """Check which templates need to be updated.

        Check which templates need to be updated (do not exist or are missing
        'community_ids'). Returns a list of template names to update.
        """
        templates_to_update = []
        for _event_type, event_config in stats_events.items():
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
        templates: dict[str, dict] = {}

        templates_to_update = self._get_templates_to_update(stats_events)

        if not templates_to_update:
            current_app.logger.info(
                "All templates are already up-to-date with enriched fields"
            )
            return True

        # Register and process templates that need updating
        templates = {}
        for _event_type, event_config in stats_events.items():
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
        event_types: list[str] | None = None,
        max_batches: int | None = None,
        delete_old_indices: bool = False,
        fresh_start: bool = False,
        month_filter: str | list[str] | tuple | None = None,
    ) -> ReindexingResults:
        """Reindex events with enriched metadata for monthly indices.

        Begins by verifying and (if necessary) updating the enriched view/download
        event index templates before reindexing.

        Args:
            event_types: List of event types to process. If None, process all.
            max_batches: Maximum number of batches to process per month. If None,
                process all.
            delete_old_indices: Whether to delete old indices after migration
            fresh_start: Whether to start fresh (ignore existing bookmarks)
            month_filter: If specified, only process the specified month(s). Can be:
                - Single month: "2024-01"
                - List of specific months: ["2024-01", "2024-02", "2024-03"]
                - Month range: "2024-01:2024-03" (inclusive range)
                - Tuple of months: ("2024-01", "2024-02", "2024-03")
                If None, process all months.

                Note: The CLI can provide multiple --months options which
                get passed as a tuple, or a single --months with range syntax.

        Returns:
            Dictionary with reindexing results and statistics.
        """
        max_batches = max_batches or self.max_batches
        results: ReindexingResults = {
            "total_processed": 0,
            "total_errors": 0,
            "event_types": {},
            "health_issues": [],
            "completed": False,
            "error": None,
        }

        if not self.community_events_index_exists:
            current_app.logger.error(
                "Community events index does not exist - stopping reindexing process"
            )
            results["total_errors"] = 1
            results["health_issues"] = ["Community events index does not exist"]
            results["completed"] = False
            results["error"] = (
                "Community events index does not exist - cannot proceed with reindexing"
            )
            return results

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

        current_app.logger.info(f"Starting reindexing for event types: {event_types}")

        for event_type in event_types:
            if event_type not in ["view", "download"]:
                current_app.logger.warning(f"Unknown event type: {event_type}")
                continue

            current_app.logger.info(f"Processing {event_type} events")

            monthly_indices = self.get_monthly_indices(event_type, month_filter)
            if not monthly_indices:
                continue

            event_results: EventTypeResults = {
                "processed": 0,
                "errors": 0,
                "months": {},
            }

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
                    fresh_start,
                )

                event_results["months"][f"{year}-{month}"] = month_results
                event_results["processed"] += month_results.get("processed", 0)
                # Count operational and validation errors
                op_error_count = len(month_results.get("operational_errors", []))
                val_error_count = 1 if month_results.get("validation_errors") else 0
                event_results["errors"] += op_error_count + val_error_count

                # Always add processed count
                results["total_processed"] += month_results.get("processed", 0)

                # Note: All migration details are stored in month_results
                # No need to duplicate them at the top level

            results["event_types"][event_type] = event_results
            current_app.logger.info(
                f"Completed {event_type}: processed {event_results.get('processed', 0)}"
                f" events across {len(event_results.get('months', {}))} months."
            )

        # Check completion status and count failures from the nested structure
        total_failures = 0
        total_interruptions = 0
        failed_months = []

        for event_type, event_results in results["event_types"].items():
            for month, month_results in event_results["months"].items():
                if not month_results.get("completed", False):
                    if month_results.get("interrupted", False):
                        total_interruptions += 1
                    else:
                        total_failures += 1
                        failed_months.append(f"{event_type}-{month}")

        if total_failures > 0:
            results["completed"] = False
            results["error"] = (
                f"Migration failed for months: {', '.join(failed_months)}"
            )
            current_app.logger.error(
                f"Reindexing failed for {total_failures} months: {failed_months}"
            )
        elif total_interruptions > 0:
            results["completed"] = False
            current_app.logger.warning(
                f"Reindexing completed with {total_interruptions} "
                "interrupted migrations. "
                "Use --max-batches to limit processing and resume later."
            )
        else:
            results["completed"] = True
            current_app.logger.info("Reindexing completed successfully")

        total_errors = 0
        for _event_type, event_results in results["event_types"].items():
            for _month, month_results in event_results["months"].items():
                # Count operational and validation errors
                op_error_count = len(month_results.get("operational_errors", []))
                val_error_count = 1 if month_results.get("validation_errors") else 0
                total_errors += op_error_count + val_error_count

        results["total_errors"] = total_errors

        return results

    def count_total_events(self) -> ProgressCounts:
        """Get comprehensive migration progress information for events.

        Returns:
            ProgressCounts with total events in old indices, already migrated
            events in new indices, and remaining events to migrate (including
            interrupted migrations from bookmarks).
        """
        counts: ProgressCounts = {
            "view_old": 0,
            "download_old": 0,
            "view_migrated": 0,
            "download_migrated": 0,
            "view_remaining": 0,
            "download_remaining": 0,
            "old_indices": [],
            "migrations_in_progress": [],
            "migrations_old_deleted": [],
            "view_completed_migrations": [],
            "download_completed_migrations": [],
        }

        for event_type in ["view", "download"]:
            # Get all indices (both old and new) for this event type
            pattern = self.index_patterns[event_type]
            indices = self.client.indices.get(index=f"{pattern}-*")
            all_monthly_indices = sorted(indices.keys())
            # Filter out the -v2.0.0 indices and backup indices to get only old indices
            old_monthly_indices = [
                idx
                for idx in all_monthly_indices
                if not idx.endswith("-v2.0.0") and not idx.endswith("-backup")
            ]

            event_type_old_count = 0
            event_type_migrated_count = 0
            event_type_remaining_count = 0

            for source_index in old_monthly_indices:
                try:
                    source_count = self.client.count(index=source_index)["count"] or 0

                    old_idx: OldMonthCounts = {
                        "index": source_index,
                        "count": source_count,
                        "enriched_index": None,
                    }
                    new_idx: MigratedMonthCounts = {
                        "source_index": source_index,
                        "index": None,
                        "old_count": source_count,
                        "migrated_count": None,
                        "remaining_count": None,
                        "completed": False,
                        "interrupted": False,
                        "bookmark": None,
                    }

                    year, month = source_index.split("-")[-2:]
                    enriched_index = f"{source_index}-v2.0.0"

                    if self.client.indices.exists(index=enriched_index):
                        old_idx["enriched_index"] = enriched_index
                        new_idx["index"] = enriched_index
                        enriched_count = self.client.count(index=enriched_index)[
                            "count"
                        ]

                        bookmark = self.reindexing_bookmark_api.get_bookmark(
                            f"{event_type}-{year}-{month}-reindexing"
                        )
                        if bookmark and bookmark.get("last_event_id"):
                            try:
                                bookmark_remaining = (
                                    self.count_remaining_after_bookmark(
                                        source_index,
                                        bookmark["last_event_timestamp"],
                                        bookmark["last_event_id"],
                                    )
                                )

                                new_idx["remaining_count"] = bookmark_remaining
                                new_idx["migrated_count"] = (
                                    source_count - bookmark_remaining
                                )
                            except Exception as e:
                                current_app.logger.warning(
                                    f"Could not count remaining events for "
                                    f"{source_index} "
                                    f"from bookmark {bookmark}: {e}"
                                )
                                new_idx["migrated_count"] = enriched_count
                                new_idx["remaining_count"] = max(
                                    0, source_count - enriched_count
                                )
                        else:
                            new_idx["migrated_count"] = enriched_count
                            new_idx["remaining_count"] = max(
                                0, source_count - enriched_count
                            )
                        new_idx["completed"] = (
                            new_idx["migrated_count"] == new_idx["old_count"]
                            and new_idx["remaining_count"] == 0
                        )
                        new_idx["interrupted"] = (
                            new_idx["old_count"] > (new_idx["migrated_count"] or 0)
                            and (new_idx["remaining_count"] or 0) > 0
                        )
                        new_idx["bookmark"] = bookmark

                    else:
                        pass

                    event_type_migrated_count += new_idx["migrated_count"] or 0
                    event_type_remaining_count += new_idx["remaining_count"] or 0
                    event_type_old_count += source_count

                    counts["old_indices"].append(old_idx)
                    if self.client.indices.exists(index=enriched_index):
                        counts["migrations_in_progress"].append(new_idx)

                except Exception as e:
                    current_app.logger.error(
                        f"Failed to count events for {source_index}: {e}"
                    )

            # Find completed migrations (enriched indices without old indices)
            new_indices = set(
                [i for i in all_monthly_indices if i not in old_monthly_indices]
            )
            matched_indices = set([i["enriched_index"] for i in counts["old_indices"]])

            for index in new_indices - matched_indices:
                completed_idx: MigratedMonthCounts = {
                    "source_index": f"[{index.replace("-v2.0.0", "")}] (deleted)",
                    "index": index,
                    "old_count": 0,
                    "migrated_count": 0,
                    "remaining_count": 0,
                    "completed": True,
                    "interrupted": False,
                    "bookmark": None,
                }
                index_count = self.client.count(index=index)["count"]
                completed_idx["old_count"] = index_count
                completed_idx["migrated_count"] = index_count
                completed_idx["bookmark"] = self.reindexing_bookmark_api.get_bookmark(
                    f"{event_type}-{index.split('-')[-2]}-"
                    f"{index.split('-')[-1]}-reindexing"
                )
                counts["migrations_old_deleted"].append(completed_idx)

            # Update counts based on event type
            if event_type == "view":
                counts["view_old"] = event_type_old_count
                counts["view_migrated"] = event_type_migrated_count
                counts["view_remaining"] = event_type_remaining_count
            else:  # download
                counts["download_old"] = event_type_old_count
                counts["download_migrated"] = event_type_migrated_count
                counts["download_remaining"] = event_type_remaining_count

        # Add counts from migrations_old_deleted to migrated counts after processing
        # all event types
        for completed_idx in counts["migrations_old_deleted"]:
            if (
                completed_idx["completed"]
                and not completed_idx["interrupted"]
                and completed_idx["index"]
            ):
                event_type = "view" if "view" in completed_idx["index"] else "download"
                migrated_count = completed_idx["migrated_count"] or 0

                # Add to migrated counts
                if event_type == "view":
                    counts["view_migrated"] += migrated_count
                else:
                    counts["download_migrated"] += migrated_count

                # Add to completed_migrations for CLI display
                year_month = (
                    completed_idx["index"].split("-")[-2]
                    + "-"
                    + completed_idx["index"].split("-")[-1].replace("-v2.0.0", "")
                )
                migration_entry = {
                    "year_month": year_month,
                    "old_index": completed_idx["source_index"],
                    "enriched_index": completed_idx["index"],
                }

                if event_type == "view":
                    counts["view_completed_migrations"].append(migration_entry)
                else:
                    counts["download_completed_migrations"].append(migration_entry)

        return counts

    def get_reindexing_progress(self) -> ReindexingProgress:
        """Get current reindexing progress across all monthly indices.

        Returns:
            Dictionary with reindexing progress information based on the current
            counts and health check.
        """
        progress: ReindexingProgress = {
            "counts": self.count_total_events(),
            "health": {
                "is_healthy": False,
                "reason": "",
                "memory_usage": 0.0,
            },
        }

        health_check = self.check_health_conditions()
        progress["health"] = {
            "is_healthy": health_check["is_healthy"],
            "reason": health_check["reason"],
            "memory_usage": psutil.virtual_memory().percent,
        }

        return progress

    def _get_last_event_timestamp(self, index_name: str) -> str | None:
        """Get the timestamp of the last event in an index, sorted by timestamp."""
        try:
            search_query = Search(using=self.client, index=index_name)
            search_query = search_query.sort({"timestamp": {"order": "desc"}})
            search_query = search_query.extra(size=1)
            response = search_query.execute()
            if response.hits:
                timestamp = response.hits[0].timestamp
                return str(timestamp) if timestamp is not None else None
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

    def _parse_month_filter(
        self, month_filter: str | list[str] | tuple | None
    ) -> list[str]:
        """Parse month filter to handle different formats.

        Args:
            month_filter: String, list, or tuple that can be:
                - Single month: "2024-01"
                - Range: "2024-01:2024-03"
                - Multiple values: ("2024-01", "2024-02", "2024-03")
                - Already a list: ["2024-01", "2024-02"]

        Returns:
            List of month strings in YYYY-MM format
        """
        if not month_filter:
            return []

        if isinstance(month_filter, list | tuple):
            valid_months = []
            for month in month_filter:
                try:
                    arrow.get(month + "-01")
                    valid_months.append(month)
                except arrow.parser.ParserError:
                    current_app.logger.warning(
                        f"Invalid month format: {month}. Skipping."
                    )
            return list(valid_months)

        if ":" in month_filter:
            try:
                start_month, end_month = month_filter.split(":")
                months = []
                current = arrow.get(start_month + "-01")
                end = arrow.get(end_month + "-01")

                while current <= end:
                    months.append(current.format("YYYY-MM"))
                    current = current.shift(months=1)
                return months
            except arrow.parser.ParserError:
                current_app.logger.warning(
                    f"Invalid month range format: {month_filter}. "
                    "Expected format: YYYY-MM:YYYY-MM"
                )
                return []

        else:
            try:
                arrow.get(month_filter + "-01")
                return [month_filter]
            except arrow.parser.ParserError:
                current_app.logger.warning(f"Invalid month format: {month_filter}")
                return []

    def count_remaining_after_bookmark(
        self, source_index: str, last_timestamp: arrow.Arrow | str, last_id: str
    ) -> int:
        """Count remaining documents after a bookmark position.

        This method handles the OpenSearch 10k limit by making multiple
        paginated requests until all remaining documents are counted.
        FIXME: This is a hack and should be replaced with a more
        efficient method.

        Args:
            source_index: The source index to search
            last_timestamp: Timestamp of the last processed document (Arrow object
                or string)
            last_id: ID of the last processed document

        Returns:
            Total number of documents remaining after the bookmark position
        """
        total_remaining = 0
        current_id = last_id

        if hasattr(last_timestamp, "format"):
            current_timestamp = last_timestamp.format("YYYY-MM-DDTHH:mm:ss")
        else:
            current_timestamp = last_timestamp

        while True:
            search = Search(using=self.client, index=source_index)
            search = search.sort("timestamp", "_id")
            search = search.extra(
                size=10000,  # OpenSearch 10k limit
                search_after=[current_timestamp, current_id],
            )

            try:
                response = search.execute()
                hits = response.hits
                if not hits:
                    break

                batch_count = len(hits)
                total_remaining += batch_count
                if batch_count < 10000:
                    break

                last_hit = hits[-1]
                current_timestamp = last_hit.timestamp
                current_id = last_hit.meta.id

            except Exception as e:
                current_app.logger.error(f"Error counting remaining documents: {e}")
                break

        return total_remaining
