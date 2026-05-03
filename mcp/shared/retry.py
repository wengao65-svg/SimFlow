"""Retry with exponential backoff and error classification."""

import time
from typing import Callable, Optional, Tuple, Type

from .errors import RetryableError, SimFlowError


def is_retryable(error: Exception) -> bool:
    """Classify whether an error is retryable."""
    if isinstance(error, RetryableError):
        return True
    if isinstance(error, SimFlowError):
        return False
    # Network errors are generally retryable
    error_type = type(error).__name__
    retryable_types = (
        "ConnectionError", "TimeoutError", "ConnectionResetError",
        "ConnectionRefusedError", "BrokenPipeError",
    )
    return error_type in retryable_types


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_check: Optional[Callable[[Exception], bool]] = None,
) -> Tuple[bool, any]:
    """Execute a function with exponential backoff retry.

    Args:
        func: Callable to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        retryable_check: Custom function to check if error is retryable

    Returns:
        Tuple of (success: bool, result_or_error)

    Example:
        success, result = retry_with_backoff(lambda: api_call(query))
        if success:
            process(result)
        else:
            handle_error(result)
    """
    check = retryable_check or is_retryable
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = func()
            return (True, result)
        except Exception as e:
            last_error = e
            if attempt < max_retries and check(e):
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)
            else:
                break

    return (False, last_error)
