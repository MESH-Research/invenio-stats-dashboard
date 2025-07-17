import functools
import time
from typing import Any, Callable, Type, Union
from flask import current_app


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
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
