"""
Block manager for handling Facebook action blocks and exponential backoff.
"""

from datetime import datetime
from typing import Optional

from playwright.sync_api import Page

from config import settings
from src.safety.error_detector import ErrorDetector
from src.safety.rate_limiter import RateLimiter
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BlockManager:
    """Manages action blocks and implements exponential backoff strategy."""

    def __init__(
        self, block_wait_hours: Optional[int] = None, backoff_multiplier: Optional[float] = None
    ):
        """
        Initialize BlockManager.

        Args:
            block_wait_hours: Hours to wait after block (defaults to settings.BLOCK_WAIT_HOURS)
            backoff_multiplier: Multiplier for exponential backoff (defaults to settings.BACKOFF_MULTIPLIER)
        """
        self.block_wait_hours = block_wait_hours or settings.BLOCK_WAIT_HOURS
        self.backoff_multiplier = backoff_multiplier or settings.BACKOFF_MULTIPLIER

        self.block_detected = False
        self.last_block_time: Optional[datetime] = None
        self.block_count = 0

        logger.info(
            f"BlockManager initialized: wait_hours={self.block_wait_hours}, "
            f"backoff_multiplier={self.backoff_multiplier}"
        )

    def check_and_handle_block(
        self, page: Page, error_detector: Optional[ErrorDetector] = None
    ) -> bool:
        """
        Check for block and handle if detected.

        Args:
            page: Playwright Page object
            error_detector: Optional ErrorDetector instance (creates new if None)

        Returns:
            True if block detected, False otherwise
        """
        if error_detector is None:
            error_detector = ErrorDetector()

        error_detected, error_message = error_detector.check_for_errors(page)

        if error_detected:
            self.block_detected = True
            self.last_block_time = datetime.now()
            self.block_count += 1

            logger.error(
                f"Block detected! Count: {self.block_count}, "
                f"Message: {error_message}, "
                f"Wait period: {self.block_wait_hours} hours"
            )

            return True

        return False

    def should_continue(self) -> bool:
        """
        Determine if script should continue after a block.

        Returns:
            True if can continue, False if should wait
        """
        if not self.block_detected:
            return True

        if self.last_block_time is None:
            return True

        now = datetime.now()
        hours_since_block = (now - self.last_block_time).total_seconds() / 3600

        if hours_since_block < self.block_wait_hours:
            remaining_hours = self.block_wait_hours - hours_since_block
            logger.warning(
                f"Block still active. Wait {remaining_hours:.1f} more hours "
                f"({self.block_wait_hours} hours total)"
            )
            return False

        logger.info(f"Block wait period expired ({hours_since_block:.1f} hours)")
        return True

    def apply_backoff(self, rate_limiter: RateLimiter) -> None:
        """
        Apply exponential backoff to rate limiter delays.

        Args:
            rate_limiter: RateLimiter instance to modify
        """
        if self.block_count == 0:
            return

        # Calculate backoff multiplier
        backoff_factor = self.backoff_multiplier**self.block_count

        # Store original values for logging
        old_mean = rate_limiter.mean_delay
        old_std_dev = rate_limiter.std_dev

        # Apply backoff
        rate_limiter.mean_delay *= backoff_factor
        rate_limiter.std_dev *= 1.2  # Increase variance by 20%

        logger.warning(
            f"Applied backoff (block_count={self.block_count}, factor={backoff_factor:.2f}): "
            f"mean_delay {old_mean:.2f}s -> {rate_limiter.mean_delay:.2f}s, "
            f"std_dev {old_std_dev:.2f}s -> {rate_limiter.std_dev:.2f}s"
        )

    def reset(self) -> None:
        """Reset block status (useful for testing or after wait period)."""
        self.block_detected = False
        self.last_block_time = None
        # Keep block_count for tracking
        logger.debug("Block status reset")

    def get_block_info(self) -> dict:
        """
        Get current block information.

        Returns:
            Dictionary with block information
        """
        hours_since_block = None
        if self.last_block_time:
            hours_since_block = (datetime.now() - self.last_block_time).total_seconds() / 3600

        return {
            "block_detected": self.block_detected,
            "last_block_time": self.last_block_time.isoformat() if self.last_block_time else None,
            "hours_since_block": hours_since_block,
            "block_count": self.block_count,
            "block_wait_hours": self.block_wait_hours,
            "can_continue": self.should_continue(),
        }
