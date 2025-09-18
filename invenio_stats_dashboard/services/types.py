# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""TypedDict types for the EventReindexingService return values."""

import types
from typing import Any, TypedDict


class HealthCheckResult(TypedDict):
    """Result of a health check operation."""

    is_healthy: bool
    reason: str


class SpotCheckResult(TypedDict):
    """Result of spot-checking original fields during validation."""

    success: bool
    errors: list[str]
    details: dict[str, Any]
    documents_verified: int | None
    field_mismatches: list[str] | None
    document_count_mismatch: dict[str, int] | None


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
    error_message: str | None


class MonthlyIndexBatchResult(TypedDict):
    """Result of processing a single batch from a monthly index."""

    processed_count: int
    last_event_id: str | None
    last_event_timestamp: str | None
    should_continue: bool
    batch_document_ids: list[str]
    previous_batch_ids: set[str] | None
    search_after_point: list[str] | None


class MigrationResult(TypedDict):
    """Result of migrating a monthly index."""

    month: str
    event_type: str
    source_index: str
    target_index: str | None
    processed: int
    interrupted: bool
    batches_succeeded: int
    completed: bool
    last_processed_id: str | None
    batches_attempted: int
    validation_errors: ValidationResult | None
    operational_errors: list[dict[str, str]]
    start_time: str
    total_time: str | None
    all_sample_document_ids: list[str]


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
    error: str | None


class OldMonthCounts(TypedDict):
    """Information about an old monthly index."""

    index: str
    count: int
    enriched_index: str | None


class MigratedMonthCounts(TypedDict):
    """Information about a migrated monthly index."""

    source_index: str
    index: str | None  # enriched index name
    old_count: int
    migrated_count: int | None
    remaining_count: int | None
    completed: bool
    interrupted: bool
    bookmark: dict[str, Any] | None


class ProgressCounts(TypedDict):
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

    # Detailed index information
    old_indices: list[OldMonthCounts]
    migrations_in_progress: list[MigratedMonthCounts]
    migrations_old_deleted: list[MigratedMonthCounts]

    # Completed migrations for CLI display
    view_completed_migrations: list[dict[str, str]]
    download_completed_migrations: list[dict[str, str]]


class ProgressHealth(TypedDict):
    """Health information for progress tracking."""

    is_healthy: bool
    reason: str
    memory_usage: float


class ReindexingProgress(TypedDict):
    """Current reindexing progress information."""

    counts: ProgressCounts
    health: ProgressHealth


def create_enriched_event_type(subcount_configs: dict[str, Any]) -> type:
    """Dynamically create an EnrichedEvent TypedDict based on subcount configuration.

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
        "parent_recid": str | None,
        "referrer": str | None,
        "via_api": bool | None,
        "is_machine": bool | None,
        "is_robot": bool | None,
        "bucket_id": str | None,
        "file_id": str | None,
        "file_key": str | None,
        "size": int | None,
    }

    # Dynamically add enriched fields based on subcount configuration
    for _subcount_key, subcount_config in subcount_configs.items():
        if "usage_events" in subcount_config and subcount_config["usage_events"]:
            usage_config = subcount_config["usage_events"]
            field_name = usage_config.get("field", "").split(".")[
                0
            ]  # Get base field name

            if field_name and field_name not in fields:
                # Get the field type from configuration
                field_type_config = usage_config.get("field_type", str | None)

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
