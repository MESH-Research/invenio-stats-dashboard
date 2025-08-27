"""TypedDict types for the EventReindexingService return values."""

import types
from typing import Any, Optional, Type, TypedDict


class HealthCheckResult(TypedDict):
    """Result of a health check operation."""

    is_healthy: bool
    reason: str


class SpotCheckResult(TypedDict):
    """Result of spot-checking original fields during validation."""

    success: bool
    errors: list[str]
    details: dict[str, Any]
    documents_verified: Optional[int]
    field_mismatches: Optional[list[str]]
    document_count_mismatch: Optional[dict[str, int]]


class ValidationResult(TypedDict):
    """Result of data validation operations."""

    success: bool
    errors: list[str]
    document_counts: dict[str, int]
    missing_community_ids: int
    spot_check: SpotCheckResult


class BatchProcessingResult(TypedDict):
    """Result of processing a batch of events."""

    success: bool
    error_message: Optional[str]


class MonthlyIndexBatchResult(TypedDict):
    """Result of processing a single batch from a monthly index."""

    processed_count: int
    last_event_id: Optional[str]
    last_event_timestamp: Optional[str]
    should_continue: bool


class MigrationResult(TypedDict):
    """Result of migrating a monthly index."""

    month: str
    event_type: str
    source_index: str
    target_index: Optional[str]
    processed: int
    interrupted: bool
    batches_succeeded: int
    completed: bool
    last_processed_id: Optional[str]
    batches_attempted: int
    validation_errors: Optional[ValidationResult]
    operational_errors: list[dict[str, str]]
    start_time: str
    total_time: Optional[str]


class EventTypeResults(TypedDict):
    """Results for processing a specific event type."""

    processed: int
    errors: int
    months: dict[str, MigrationResult]


class ReindexingResults(TypedDict):
    """Results of the complete reindexing operation."""

    total_processed: int
    total_errors: int
    event_types: dict[str, EventTypeResults]
    health_issues: list[str]
    completed: bool
    error: Optional[str]


class ProgressEstimates(TypedDict):
    """Comprehensive migration progress information for events."""

    # Total events in old (source) indices
    view_old: int
    download_old: int

    # Events already migrated to new (target) indices
    view_migrated: int
    download_migrated: int

    # Remaining events to migrate (including interrupted migrations)
    view_remaining: int
    download_remaining: int

    old_indices: list[dict[str, str | int]]
    migrated_indices: list[dict[str, str | int]]

    migration_bookmarks: list[dict[str, Optional[dict[str, str]]]]

    # Mapping from old index names to migrated index names
    view_index_mapping: dict[str, Optional[str]]
    download_index_mapping: dict[str, Optional[str]]

    # Completed migrations where old indices were deleted
    view_completed_migrations: list[dict[str, str]]
    download_completed_migrations: list[dict[str, str]]


class ProgressBookmarks(TypedDict):
    """Bookmark information for tracking progress."""

    view: dict[str, Optional[dict[str, str]]]
    download: dict[str, Optional[dict[str, str]]]


class ProgressHealth(TypedDict):
    """Health information for progress tracking."""

    is_healthy: bool
    reason: str
    memory_usage: float


class ReindexingProgress(TypedDict):
    """Current reindexing progress information."""

    estimates: ProgressEstimates
    bookmarks: ProgressBookmarks
    health: ProgressHealth


def create_enriched_event_type(subcount_configs: dict[str, Any]) -> Type:
    """
    Dynamically create an EnrichedEvent TypedDict based on subcount configuration.

    This function analyzes the COMMUNITY_STATS_SUBCOUNT_CONFIGS to determine
    which enriched fields should be included in the EnrichedEvent TypedDict.

    Args:
        subcount_configs: The COMMUNITY_STATS_SUBCOUNT_CONFIGS configuration

    Returns:
        A dynamically generated TypedDict class for enriched events
    """
    fields = {
        "timestamp": str,
        "recid": str,
        "unique_id": str,
        "session_id": str,
        "visitor_id": str,
        "country": str,
        "unique_session_id": str,
        "community_ids": list[str],
        "parent_recid": Optional[str],
        "referrer": Optional[str],
        "via_api": Optional[bool],
        "is_machine": Optional[bool],
        "is_robot": Optional[bool],
        "bucket_id": Optional[str],
        "file_id": Optional[str],
        "file_key": Optional[str],
        "size": Optional[int],
    }

    # Dynamically add enriched fields based on subcount configuration
    for subcount_key, subcount_config in subcount_configs.items():
        if "usage_events" in subcount_config and subcount_config["usage_events"]:
            usage_config = subcount_config["usage_events"]
            field_name = usage_config.get("field", "").split(".")[
                0
            ]  # Get base field name

            if field_name and field_name not in fields:
                # Get the field type from configuration
                field_type_config = usage_config.get("field_type", Optional[str])

                # Use the configured field type directly
                fields[field_name] = field_type_config

    EnrichedEventTypedDict = types.new_class(
        "EnrichedEvent",
        (TypedDict,),
        {
            "total": False,
        },
    )

    return EnrichedEventTypedDict


# Will be replaced by the dynamic model when the service is initialized
# based on the subcount configuration
EnrichedEvent = create_enriched_event_type({})
