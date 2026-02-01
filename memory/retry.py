"""Retry utilities for memory operations."""

import asyncio
import time
from typing import Callable, TypeVar, Optional, List
from functools import wraps
from memory.logger import get_logger
from memory.errors import MemoryError

logger = get_logger()

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 2.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Optional[tuple] = None
    ):
        """Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            retryable_exceptions: Tuple of exception types to retry on
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or (
            ConnectionError,
            TimeoutError,
            redis.ConnectionError,
            redis.TimeoutError,
        )


def retry_async(
    config: Optional[RetryConfig] = None,
    operation_name: Optional[str] = None
):
    """Decorator for async functions with retry logic.
    
    Args:
        config: Retry configuration
        operation_name: Name of operation for logging
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation = operation_name or func.__name__
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if exception is retryable
                    if not isinstance(e, config.retryable_exceptions):
                        logger.error(
                            f"{operation} failed with non-retryable error: {e}",
                            extra={"operation": operation, "attempt": attempt}
                        )
                        raise
                    
                    # Don't retry on last attempt
                    if attempt >= config.max_attempts:
                        logger.error(
                            f"{operation} failed after {attempt} attempts: {e}",
                            extra={"operation": operation, "attempt": attempt}
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )
                    
                    logger.warning(
                        f"{operation} failed (attempt {attempt}/{config.max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}",
                        extra={"operation": operation, "attempt": attempt, "delay": delay}
                    )
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{operation} failed after {config.max_attempts} attempts")
        
        return wrapper
    return decorator
