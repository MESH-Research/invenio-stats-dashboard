# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utility decorators for the stats dashboard."""

import functools
import time
from collections.abc import Callable
from typing import Any

from flask import current_app


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: type[Exception] | tuple[type[Exception], ...] = Exception,
    exponential_backoff: bool = True,
    logger=None,
):
    """Retry decorator with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for the first retry
        exceptions: Exception types to retry on
        exponential_backoff: Whether to use exponential backoff
        logger: Logger instance to use (defaults to current_app.logger)

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries - 1:
                        # Last attempt failed, re-raise the exception
                        raise e

                    # Calculate delay
                    if exponential_backoff:
                        delay = base_delay * (2**attempt)
                    else:
                        delay = base_delay

                    # Log the retry attempt
                    log_func = logger or current_app.logger
                    log_func.warning(
                        f"{func.__name__} failed "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )

                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def time_operation(func):
    """Decorator to time method execution and add timing data to results.

    Expects the decorated method to return a dict with results.
    Adds timing fields: total_time_seconds, total_time_minutes, total_time_hours

    Returns:
        Callable: The wrapped function with timing functionality.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()

        try:
            # Call the original method
            results = func(self, *args, **kwargs)

            # Calculate timing
            end_time = time.time()
            total_time = end_time - start_time

            # Add timing to results if it's a dict
            if isinstance(results, dict):
                results["total_time_seconds"] = total_time
                results["total_time_minutes"] = total_time / 60
                results["total_time_hours"] = total_time / 3600

                # Log timing info
                if results.get("completed"):
                    current_app.logger.debug(
                        f"Operation completed in {total_time:.2f} seconds "
                        f"({total_time / 60:.2f} minutes)"
                    )
                elif results.get("interrupted"):
                    current_app.logger.debug(
                        f"Operation interrupted after {total_time:.2f} seconds "
                        f"({total_time / 60:.2f} minutes)"
                    )

            return results

        except Exception as e:
            # Calculate timing even for failures
            end_time = time.time()
            total_time = end_time - start_time
            current_app.logger.error(
                f"Operation failed after {total_time:.2f} seconds: {e}"
            )
            raise

    return wrapper
