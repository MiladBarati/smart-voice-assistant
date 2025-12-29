"""Throttled logging helper to reduce log spam.

This module provides a simple utility to throttle log messages based on
time intervals, preventing log flooding when the same event occurs
repeatedly in quick succession.

Example:
    logger = ThrottledLogger(interval_seconds=5.0)
    logger.log_if_ready(lambda: print("This won't spam every call"))
"""

from __future__ import annotations

import time
from typing import Callable


class ThrottledLogger:
    """Helper to throttle log messages based on time intervals.

    Prevents log spam by only allowing log messages to be emitted
    after a minimum time interval has passed since the last log.

    Example:
        logger = ThrottledLogger(interval_seconds=5.0)
        # Only logs if 5+ seconds have passed since last log
        logger.log_if_ready(lambda: print("Periodic status update"))
    """

    def __init__(self, interval_seconds: float = 5.0):
        """Initialize throttled logger.

        Args:
            interval_seconds: Minimum time between log messages.
        """
        self.interval_seconds = interval_seconds
        self._last_log_time: float = 0.0

    def should_log(self) -> bool:
        """Check if enough time has passed to log again."""
        current_time = time.time()
        if current_time - self._last_log_time >= self.interval_seconds:
            self._last_log_time = current_time
            return True
        return False

    def log_if_ready(self, log_fn: Callable[[], None]) -> None:
        """Call log function only if enough time has passed."""
        if self.should_log():
            log_fn()
