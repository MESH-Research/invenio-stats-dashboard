# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for community statistics aggregation and event reindexing."""

import time
import uuid
from datetime import timedelta
from typing import TypedDict

from celery import shared_task
from celery.schedules import crontab
from dateutil.parser import parse as dateutil_parse  # type: ignore[import-untyped]
from flask import current_app
from invenio_cache import current_cache
from invenio_search.proxies import current_search_client
from invenio_stats.proxies import current_stats

from ..exceptions import (
    CommunityEventsNotInitializedError,
    TaskLockAcquisitionError,
    UsageEventsNotMigratedError,
)


# TypedDict definitions for aggregation response objects
class DateInfo(TypedDict, total=False):
    """Date information for a document."""

    date_type: str  # "delta" or "snapshot"
    period_start: str | None  # For delta aggregators
    period_end: str | None  # For delta aggregators
    snapshot_date: str | None  # For snapshot aggregators


class DocumentInfo(TypedDict):
    """Information about a single document generated during aggregation."""

    document_id: str
    date_info: DateInfo
    generation_time: float


class CommunityDetail(TypedDict):
    """Detailed information about a community's aggregation results."""

    community_id: str
    index_name: str
    docs_indexed: int
    errors: int
    error_details: list[int | dict]
    documents: list[DocumentInfo]
    date_range_requested: dict


class AggregatorResult(TypedDict):
    """Result information for a single aggregator."""

    aggregator: str
    duration_formatted: str
    docs_indexed: int
    errors: int
    communities_count: int
    communities_processed: list[str]
    community_details: list[CommunityDetail]
    error_details: list[int | dict]
    status: str  # Status message (e.g., "completed", "displaced by initialization")


class AggregationResponse(TypedDict):
    """Complete response object from aggregation task."""

    results: list[AggregatorResult]
    total_duration: str
    formatted_report: str
    formatted_report_verbose: str


def format_agg_startup_message(
    community_ids=None,
    aggregation_types=None,
    start_date=None,
    end_date=None,
    eager=False,
    update_bookmark=True,
    ignore_bookmark=False,
    verbose=False,
):
    """Format startup configuration into a human-readable message.

    Args:
        community_ids: List of community IDs or None for all
        aggregation_types: List of aggregation types or None for all
        start_date: Start date string or None
        end_date: End date string or None
        eager: Whether running in eager mode
        update_bookmark: Whether to update bookmarks
        ignore_bookmark: Whether to ignore bookmarks
        verbose: Whether verbose output is enabled

    Returns:
        String containing formatted startup configuration
    """
    lines = []
    lines.append("=" * 60)
    lines.append("COMMUNITY STATS AGGREGATION")
    lines.append("=" * 60)
    lines.append(f"Start date: {start_date or 'Not specified (using bookmark)'}")
    lines.append(f"End date: {end_date or 'Not specified (using current date)'}")

    communities_str = ", ".join(community_ids) if community_ids else "All communities"
    lines.append(f"Aggregation types: {communities_str}")

    communities_str = ", ".join(community_ids) if community_ids else "All communities"
    lines.append(f"Communities: {communities_str}")

    execution_mode = "Eager (synchronous)" if eager else "Asynchronous (Celery task)"
    lines.append(f"Execution mode: {execution_mode}")
    lines.append(f"Update bookmark: {update_bookmark}")
    lines.append(f"Ignore bookmark: {ignore_bookmark}")
    lines.append(f"Verbose output: {verbose}")
    lines.append("=" * 60)

    if not eager:
        lines.append("")
        lines.append("Note: This command runs asynchronously via Celery.")
        lines.append("If interrupted, the aggregation will continue in the background.")
        lines.append("Check Celery logs or OpenSearch indices to verify completion.")
        lines.append("=" * 60)

    return "\n".join(lines)


def _format_aggregation_report(
    result: AggregationResponse, verbose: bool = False
) -> str:
    """Format aggregation results into a human-readable report.

    Args:
        result: Dictionary containing 'results' and 'total_duration' keys
        verbose: Whether to include detailed timing breakdown

    Returns:
        String containing formatted report
    """
    if not isinstance(result, dict) or "results" not in result:
        return "Aggregation completed successfully."

    results = result["results"]
    total_duration = result.get("total_duration", "unknown")
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("AGGREGATION RESULTS")
    lines.append("=" * 60)

    # Individual aggregator results
    total_docs_indexed = 0
    total_errors = 0
    total_communities = 0

    for aggr_timing in results:
        aggr_name = aggr_timing["aggregator"]
        duration = aggr_timing["duration_formatted"]
        docs_indexed = aggr_timing.get("docs_indexed", 0)
        errors = aggr_timing.get("errors", 0)
        communities_count = aggr_timing.get("communities_count", 0)
        error_details = aggr_timing.get("error_details", [])
        community_details = aggr_timing.get("community_details", [])

        lines.append(f"\n{aggr_name}")
        lines.append("-" * len(aggr_name))
        lines.append(f"Duration: {duration}")
        lines.append(f"Documents indexed: {docs_indexed:,}")
        lines.append(f"Errors: {errors:,}")
        lines.append(f"Status: {aggr_timing.get('status', 'completed')}")
        if communities_count > 0:
            lines.append(f"Communities processed: {communities_count}")

        total_docs_indexed += docs_indexed
        total_errors += errors
        total_communities = max(total_communities, communities_count)

        # Show community details if available
        if community_details and verbose:
            lines.append("Community details:")
            for comm_detail in community_details:
                comm_id = comm_detail.get("community_id", "unknown")
                comm_index = comm_detail.get("index_name", "unknown")
                comm_docs = comm_detail.get("docs_indexed", 0)
                comm_errors = comm_detail.get("errors", 0)
                comm_docs_info = comm_detail.get("documents", [])

                lines.append(f"  Community {comm_id} (index: {comm_index}):")
                lines.append(f"    Documents: {comm_docs}, Errors: {comm_errors}")

                # Show document timing details if available
                if comm_docs_info and verbose:
                    total_doc_time = sum(
                        doc.get("generation_time", 0) for doc in comm_docs_info
                    )
                    avg_doc_time = (
                        total_doc_time / len(comm_docs_info) if comm_docs_info else 0
                    )
                    lines.append(
                        f"    Total doc generation time: {total_doc_time:.3f}s"
                    )
                    lines.append(
                        f"    Average doc generation time: {avg_doc_time:.3f}s"
                    )

                    # Show individual document details (limit to first 3)
                    for _i, doc_info in enumerate(comm_docs_info[:3]):
                        doc_id = doc_info.get("document_id", "unknown")
                        gen_time = doc_info.get("generation_time", 0)
                        date_info = doc_info.get("date_info", {})
                        date_type = date_info.get("date_type", "unknown")
                        lines.append(
                            f"      Doc {doc_id}: {gen_time:.3f}s ({date_type})"
                        )

                    if len(comm_docs_info) > 3:
                        remaining = len(comm_docs_info) - 3
                        lines.append(f"      ... and {remaining} more documents")

        # Show error details (limit to first 3 for logging)
        if error_details:
            lines.append("Error details:")
            for error in error_details[:3]:
                if isinstance(error, dict):
                    error_msg = error.get("error", {}).get("reason", str(error))
                    lines.append(f"  - {error_msg}")
            if len(error_details) > 3:
                lines.append(f"  ... and {len(error_details) - 3} more errors")

    # Summary
    lines.append("\n" + "=" * 60)
    lines.append("AGGREGATION SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total documents indexed: {total_docs_indexed:,}")
    lines.append(f"Total errors: {total_errors:,}")
    lines.append(f"Total communities processed: {total_communities}")
    lines.append(f"Total aggregation time: {total_duration}")
    lines.append("=" * 60)

    # Add verbose timing details if requested
    if verbose:
        lines.append("\nIndividual aggregator timings:")
        lines.append("-" * 50)
        for aggr_timing in results:
            lines.append(
                f"  {aggr_timing['aggregator']:<35} "
                f"{aggr_timing['duration_formatted']:>15}"
            )
        lines.append("-" * 50)
        lines.append(f"{'Total':<35} {total_duration:>15}")
        lines.append("=" * 60)

    return "\n".join(lines)


class AggregationTaskLock:
    """Simple distributed lock for aggregation tasks using invenio_cache."""

    def __init__(self, lock_name, timeout=86400):  # 24 hour timeout
        """Initialize the distributed lock.

        Args:
            lock_name (str): The name of the lock to acquire.
            timeout (int, optional): Lock timeout in seconds.
                Defaults to 86400 (24 hours).
        """
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.lock_id = str(uuid.uuid4())

    def acquire(self):
        """Acquire the lock."""
        # Use cache add method which is atomic and only succeeds if key doesn't exist
        result = current_cache.add(self.lock_name, self.lock_id, timeout=self.timeout)
        return result

    def release(self):
        """Release the lock."""
        current_value = current_cache.get(self.lock_name)
        if current_value == self.lock_id:
            return current_cache.delete(self.lock_name)
        return False

    def __enter__(self):
        """Enter the context manager and acquire the lock.

        Returns:
            self: The lock instance.

        Raises:
            TaskLockAcquisitionError: If the lock cannot be acquired.
        """
        if not self.acquire():
            raise TaskLockAcquisitionError(
                f"Could not acquire lock: {self.lock_name}. An existing task "
                f"is probably still running."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and release the lock.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.release()


CommunityStatsAggregationTask = {
    "task": "invenio_stats_dashboard.tasks.aggregate_community_record_stats",
    "schedule": crontab(minute="40", hour="*"),  # Run every hour at minute 40
    "args": (
        (
            "community-usage-delta-agg",
            # "community-records-delta-created-agg",
            # "community-records-delta-published-agg",
            "community-records-delta-added-agg",
            # "community-records-snapshot-created-agg",
            # "community-records-snapshot-published-agg",
            "community-records-snapshot-added-agg",
            "community-usage-snapshot-agg",
        ),
    ),
}


@shared_task
def aggregate_community_record_stats(
    aggregations: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
    update_bookmark: bool = True,
    ignore_bookmark: bool = False,
    community_ids: list[str] | None = None,
    verbose: bool = False,
    eager: bool = False,
) -> AggregationResponse:
    """Aggregate community record stats from created records.

    Returns:
        AggregationResponse
    """
    lock_config = current_app.config.get("STATS_DASHBOARD_LOCK_CONFIG", {})
    global_enabled = lock_config.get("enabled", True)
    aggregation_config = lock_config.get("aggregation", {})
    lock_enabled = global_enabled and aggregation_config.get("enabled", True)
    lock_timeout = aggregation_config.get("lock_timeout", 86400)
    lock_name = aggregation_config.get("lock_name", "community_stats_aggregation")

    if lock_enabled:
        lock = AggregationTaskLock(lock_name, timeout=lock_timeout)
        try:
            with lock:
                current_app.logger.info(
                    "Acquired aggregation lock, starting aggregation..."
                )
                return _run_aggregation(
                    aggregations,
                    start_date,
                    end_date,
                    update_bookmark,
                    community_ids,
                    ignore_bookmark,
                    verbose,
                    eager,
                )
        except TaskLockAcquisitionError:
            # Lock acquisition failed - another task is running
            current_app.logger.warning(
                "Aggregation task skipped - another instance is already running"
            )
            return {
                "results": [],
                "total_duration": "0:00:00",
                "formatted_report": "Aggregation skipped - another instance running",
                "formatted_report_verbose": (
                    "Aggregation skipped - another instance running"
                ),
            }
    else:
        # Run without locking
        current_app.logger.info("Running aggregation without distributed lock...")
        return _run_aggregation(
            aggregations,
            start_date,
            end_date,
            update_bookmark,
            community_ids,
            ignore_bookmark,
            verbose,
            eager,
        )


def _handle_community_events_error(
    aggr_name: str, aggr_duration: str, parsed_start_date, parsed_end_date
) -> AggregatorResult:
    """Handle CommunityEventsNotInitializedError by running initialization.

    Args:
        aggr_name: Name of the aggregator that failed
        aggr_duration: Duration string for the aggregator
        parsed_start_date: Parsed start date
        parsed_end_date: Parsed end date

    Returns:
        Assembled AggregatorResult for the displaced aggregator
    """
    current_app.logger.error(
        f"Community events not initialized for aggregator {aggr_name}"
    )
    current_app.logger.info(
        "Running community events initialization. This may take a while..."
    )

    # Import here to avoid circular imports
    from ..proxies import current_community_stats_service

    try:
        # Run bulk community events creation
        current_community_stats_service.generate_record_community_events()
        current_app.logger.info(
            "Community events initialization completed successfully"
        )

        # Don't retry aggregation - just log that this run was displaced
        current_app.logger.info(
            "Aggregation run displaced by community events initialization. "
            "Next scheduled run will proceed normally."
        )

        # Return assembled result for the displaced aggregator
        return _assemble_aggregation_results(
            raw_result=[],
            aggr_name=aggr_name,
            aggr_duration=aggr_duration,
            processed_communities=[],
            parsed_start_date=parsed_start_date,
            parsed_end_date=parsed_end_date,
            status="displaced by community events initialization",
        )

    except Exception as init_error:
        current_app.logger.error(f"Failed to initialize community events: {init_error}")
        current_app.logger.error(
            f"Skipping aggregator {aggr_name} due to initialization failure"
        )

        # Return assembled result for the failed aggregator
        return _assemble_aggregation_results(
            raw_result=[],
            aggr_name=aggr_name,
            aggr_duration=aggr_duration,
            processed_communities=[],
            parsed_start_date=parsed_start_date,
            parsed_end_date=parsed_end_date,
            status="failed - community events initialization error",
        )


def _handle_usage_events_error(
    aggr_name: str, aggr_duration: str, parsed_start_date, parsed_end_date
) -> AggregatorResult:
    """Handle UsageEventsNotMigratedError by running migration.

    Args:
        aggr_name: Name of the aggregator that failed
        aggr_duration: Duration string for the aggregator
        parsed_start_date: Parsed start date
        parsed_end_date: Parsed end date

    Returns:
        Assembled AggregatorResult for the displaced aggregator
    """
    current_app.logger.error(f"Usage events not migrated for aggregator {aggr_name}")
    current_app.logger.info("Running usage events migration. This may take a while...")

    # Import here to avoid circular imports
    from ..proxies import current_event_reindexing_service

    try:
        # Run usage events migration
        current_event_reindexing_service.reindex_events()
        current_app.logger.info("Usage events migration completed successfully")

        # Don't retry aggregation - just log that this run was displaced
        current_app.logger.info(
            "Aggregation run displaced by usage events migration. "
            "Next scheduled run will proceed normally."
        )

        # Return assembled result for the displaced aggregator
        return _assemble_aggregation_results(
            raw_result=[],
            aggr_name=aggr_name,
            aggr_duration=aggr_duration,
            processed_communities=[],
            parsed_start_date=parsed_start_date,
            parsed_end_date=parsed_end_date,
            status="displaced by usage events migration",
        )

    except Exception as migration_error:
        current_app.logger.error(f"Failed to migrate usage events: {migration_error}")
        current_app.logger.error(
            f"Skipping aggregator {aggr_name} due to migration failure"
        )

        # Return assembled result for the failed aggregator
        return _assemble_aggregation_results(
            raw_result=[],
            aggr_name=aggr_name,
            aggr_duration=aggr_duration,
            processed_communities=[],
            parsed_start_date=parsed_start_date,
            parsed_end_date=parsed_end_date,
            status="failed - usage events migration error",
        )


def _assemble_aggregation_results(
    raw_result: list,
    aggr_name: str,
    aggr_duration: str,
    processed_communities: list[str],
    parsed_start_date,
    parsed_end_date,
    status: str = "completed",
) -> AggregatorResult:
    """Assemble aggregation results from raw aggregator output.

    Args:
        raw_result: Raw result from aggregator.run()
        aggr_name: Name of the aggregator
        aggr_duration: Formatted duration string
        processed_communities: List of community IDs processed
        parsed_start_date: Parsed start date
        parsed_end_date: Parsed end date
        status: Status message (e.g., "completed", "displaced by initialization")

    Returns:
        Assembled AggregatorResult dictionary
    """
    # Extract detailed results information
    aggr_docs_indexed = 0
    aggr_errors = 0
    aggr_communities: set[str] = set()
    aggr_error_details: list[int | dict] = []
    community_details: list[CommunityDetail] = []

    if isinstance(raw_result, list):
        for i, community_result in enumerate(raw_result):
            response_object: CommunityDetail = {
                "community_id": "",
                "index_name": "",
                "docs_indexed": 0,
                "errors": 0,
                "error_details": [],
                "documents": [],
                "date_range_requested": {
                    "start_date": (
                        str(parsed_start_date) if parsed_start_date else None
                    ),
                    "end_date": str(parsed_end_date) if parsed_end_date else None,
                },
            }
            if isinstance(community_result, tuple) and len(community_result) >= 2:
                response_object["docs_indexed"] = community_result[0]
                response_object["errors"] = community_result[1]
                aggr_docs_indexed += community_result[0]

                # Get detailed document information if available
                docs_info = community_result[2] if len(community_result) >= 3 else []
                doc_infos: list[DocumentInfo] = [
                    {
                        "document_id": d["document_id"],
                        "date_info": d["date_info"],
                        "generation_time": d["generation_time"],
                    }
                    for d in docs_info
                ]
                response_object["documents"] = doc_infos

                if docs_info and len(docs_info) > 0:
                    response_object["community_id"] = docs_info[0].get(
                        "community_id", ""
                    )
                    response_object["index_name"] = docs_info[0].get("index_name", "")
                else:
                    if i < len(processed_communities):
                        response_object["community_id"] = processed_communities[i]
                    else:
                        response_object["community_id"] = f"community_{i}"
                    response_object["index_name"] = ""

                aggr_communities.add(response_object["community_id"])

                errors = community_result[1]
                if isinstance(errors, int):
                    response_object["errors"] = errors
                    response_object["error_details"] = []
                    aggr_errors += errors
                elif isinstance(errors, list):
                    response_object["errors"] = len(errors)
                    response_object["error_details"] = errors
                    aggr_errors += len(errors)
                    aggr_error_details.extend(errors)
                else:
                    response_object["errors"] = 0
                    response_object["error_details"] = []

                community_details.append(response_object)

    return {
        "aggregator": aggr_name,
        "duration_formatted": aggr_duration,
        "docs_indexed": aggr_docs_indexed,
        "errors": aggr_errors,
        "communities_count": len(aggr_communities),
        "communities_processed": list(aggr_communities),
        "community_details": community_details,
        "error_details": aggr_error_details,
        "status": status,
    }


def _run_aggregation(
    aggregations: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
    update_bookmark: bool = True,
    community_ids: list[str] | None = None,
    ignore_bookmark: bool = False,
    verbose: bool = False,
    eager: bool = False,
) -> AggregationResponse:
    """Run the actual aggregation logic.

    Returns:
        AggregationResponse
    """
    parsed_start_date = dateutil_parse(start_date) if start_date else None
    parsed_end_date = dateutil_parse(end_date) if end_date else None
    results: list[AggregatorResult] = []

    startup_config = format_agg_startup_message(
        community_ids=community_ids,
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date) if end_date else None,
        eager=eager,
        update_bookmark=update_bookmark,
        ignore_bookmark=ignore_bookmark,
        verbose=verbose,
    )
    current_app.logger.info(f"Aggregation startup configuration:\n{startup_config}")

    # Refresh community events index before running aggregators
    current_search_client.indices.refresh(index="*stats-community-events*")

    total_start_time = time.time()

    for aggr_name in aggregations:
        aggr_start_time = time.time()
        current_app.logger.info(f"Starting aggregator: {aggr_name}")

        aggr_cfg = current_stats.aggregations[aggr_name]
        params = aggr_cfg.params.copy()
        if community_ids:
            params["community_ids"] = community_ids
        aggregator = aggr_cfg.cls(name=aggr_cfg.name, **params)

        try:
            raw_result = aggregator.run(
                parsed_start_date, parsed_end_date, update_bookmark, ignore_bookmark
            )

            # Get the actual communities that were processed by the aggregator
            processed_communities = getattr(aggregator, "communities_to_aggregate", [])

            if (
                hasattr(aggregator, "aggregation_index")
                and aggregator.aggregation_index
            ):
                current_search_client.indices.refresh(
                    index=f"*{aggregator.aggregation_index}*"
                )

            # Calculate duration after successful run
            aggr_end_time = time.time()
            aggr_duration = str(timedelta(seconds=aggr_end_time - aggr_start_time))

            # Assemble successful result
            result = _assemble_aggregation_results(
                raw_result,
                aggr_name,
                aggr_duration,
                processed_communities,
                parsed_start_date,
                parsed_end_date,
                "completed",
            )
            results.append(result)

        except CommunityEventsNotInitializedError:
            # Calculate duration after error occurs
            aggr_end_time = time.time()
            aggr_duration = str(timedelta(seconds=aggr_end_time - aggr_start_time))

            # Handle community events error and break out of loop
            result = _handle_community_events_error(
                aggr_name, aggr_duration, parsed_start_date, parsed_end_date
            )
            results.append(result)
            current_app.logger.info(
                "Stopping aggregation run due to community events initialization"
            )
            break

        except UsageEventsNotMigratedError:
            # Calculate duration after error occurs
            aggr_end_time = time.time()
            aggr_duration = str(timedelta(seconds=aggr_end_time - aggr_start_time))

            # Handle usage events error and break out of loop
            result = _handle_usage_events_error(
                aggr_name, aggr_duration, parsed_start_date, parsed_end_date
            )
            results.append(result)
            current_app.logger.info(
                "Stopping aggregation run due to usage events migration"
            )
            break

        current_app.logger.info(f"Completed aggregator: {aggr_name} in {aggr_duration}")

    total_end_time = time.time()
    total_duration = str(timedelta(seconds=total_end_time - total_start_time))

    current_app.logger.info("Aggregation completed successfully")
    current_app.logger.info(f"Total aggregation time: {total_duration}")

    result_dict: AggregationResponse = {
        "results": results,
        "total_duration": total_duration,
        "formatted_report": "",
        "formatted_report_verbose": "",
    }

    # Generate formatted report for both logging and CLI display
    # Always log the verbose version for detailed information
    report = _format_aggregation_report(result_dict, verbose=True)
    current_app.logger.info(f"Aggregation report:\n{report}")

    # Add both verbose and non-verbose reports to result for CLI display
    result_dict["formatted_report"] = _format_aggregation_report(
        result_dict, verbose=False
    )
    result_dict["formatted_report_verbose"] = _format_aggregation_report(
        result_dict, verbose=True
    )

    return result_dict
