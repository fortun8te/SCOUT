"""Retry logic with exponential backoff for resilient cloud operation"""

import asyncio
import logging
import random
from typing import Callable, Any

logger = logging.getLogger(__name__)


class RetryHandler:
    """Handle retries with exponential backoff for API failures"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize retry handler

        Args:
            max_retries: Max number of attempts (including initial)
            base_delay: Starting delay in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with exponential backoff retry

        Args:
            func: Async function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result or None if all retries fail
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"[RETRY] {func.__name__} succeeded on attempt {attempt}")
                return result

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    # Calculate backoff: 1s, 2s, 4s (+ jitter)
                    delay = self.base_delay * (2 ** (attempt - 1))
                    jitter = random.uniform(0, 0.1 * delay)  # 10% jitter
                    wait_time = delay + jitter

                    logger.warning(
                        f"[RETRY] {func.__name__} failed attempt {attempt}/{self.max_retries}: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"[RETRY] {func.__name__} failed all {self.max_retries} attempts. "
                        f"Last error: {e}"
                    )

        return None

    def execute_sync_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Synchronous version of retry for non-async functions"""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"[RETRY] {func.__name__} succeeded on attempt {attempt}")
                return result

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    jitter = random.uniform(0, 0.1 * delay)
                    wait_time = delay + jitter

                    logger.warning(
                        f"[RETRY] {func.__name__} failed attempt {attempt}/{self.max_retries}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    asyncio.run(asyncio.sleep(wait_time))
                else:
                    logger.error(
                        f"[RETRY] {func.__name__} failed all {self.max_retries} attempts"
                    )

        return None
