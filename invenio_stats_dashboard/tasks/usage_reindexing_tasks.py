# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for community statistics aggregation and event reindexing."""

from celery import shared_task
from flask import current_app

from ..proxies import current_event_reindexing_service as reindexing_service


@shared_task
def reindex_usage_events_with_metadata(
    event_types=None,
    max_batches=None,
    batch_size=None,
    max_memory_percent=None,
    delete_old_indices=False,
):
    """Reindex view and download events with enriched metadata as a Celery task.

    Args:
        event_types: List of event types to process. If None, process all.
        max_batches: Maximum number of batches to process. If None, process all.
        batch_size: Override default batch size. If None, use default.
        max_memory_percent: Override default memory limit. If None, use default.
        delete_old_indices: Whether to delete old indices after migration.

    Returns:
        Dictionary with reindexing results and statistics.
    """
    current_app.logger.info("Starting event reindexing task")

    if batch_size is not None:
        reindexing_service.batch_size = batch_size
    if max_memory_percent is not None:
        reindexing_service.max_memory_percent = max_memory_percent

    try:
        progress = reindexing_service.get_reindexing_progress()
        current_app.logger.info(f"Initial progress: {progress}")

        results = reindexing_service.reindex_events(
            event_types=event_types,
            max_batches=max_batches,
            delete_old_indices=delete_old_indices,
        )

        current_app.logger.info(f"Reindexing task completed: {results}")
        return results

    except Exception as e:
        current_app.logger.error(f"Reindexing task failed: {e}")
        return {
            "error": str(e),
            "completed": False,
            "total_processed": 0,
            "total_errors": 1,
        }


@shared_task
def get_reindexing_progress():
    """Get current reindexing progress as a Celery task.
    
    Returns:
        dict: Progress information or error details.
    """
    try:
        from .proxies import current_event_reindexing_service

        progress = current_event_reindexing_service.get_reindexing_progress()
        return progress
    except Exception as e:
        current_app.logger.error(f"Failed to get reindexing progress: {e}")
        return {"error": str(e)}
