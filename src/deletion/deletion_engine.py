"""
Deletion engine for orchestrating item extraction, handler selection, and deletion.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import settings
from src.deletion.handlers import DeletionHandler, get_all_handlers
from src.deletion.item_extractor import ItemExtractor
from src.safety.block_manager import BlockManager
from src.safety.error_detector import ErrorDetector
from src.safety.rate_limiter import RateLimiter
from src.utils.logging import get_logger
from src.utils.state_manager import StateManager

logger = get_logger(__name__)


class DeletionEngine:
    """Orchestrates deletion of items from Activity Log pages."""

    def __init__(
        self,
        page: Page,
        target_date: Optional[datetime] = None,
        handlers: Optional[list[DeletionHandler]] = None,
        rate_limiter: Optional[RateLimiter] = None,
        error_detector: Optional[ErrorDetector] = None,
        block_manager: Optional[BlockManager] = None,
        state_manager: Optional[StateManager] = None,
        logger_instance=None,
    ):
        """
        Initialize DeletionEngine.

        Args:
            page: Playwright Page object
            target_date: Date threshold for deletion (defaults to settings.TARGET_YEAR)
            handlers: Optional list of handlers (defaults to all registered handlers)
            rate_limiter: Optional RateLimiter instance
            error_detector: Optional ErrorDetector instance
            block_manager: Optional BlockManager instance
            state_manager: Optional StateManager instance
            logger_instance: Optional logger instance
        """
        self.page = page
        self.target_date = target_date or datetime(settings.TARGET_YEAR, 1, 1)
        self.handlers = handlers or get_all_handlers()
        self.logger = logger_instance or logger

        # Initialize safety mechanisms
        self.rate_limiter = rate_limiter or RateLimiter()
        self.error_detector = error_detector or ErrorDetector()
        self.block_manager = block_manager or BlockManager()
        self.state_manager = state_manager or StateManager(settings.PROGRESS_PATH)

        self.item_extractor = ItemExtractor(self.target_date)

        # Apply backoff if block was previously detected
        if self.block_manager.block_detected:
            self.block_manager.apply_backoff(self.rate_limiter)

        self.logger.info(
            f"DeletionEngine initialized with {len(self.handlers)} handlers, "
            f"target_date={self.target_date.date()}"
        )

    def process_page(self, page: Optional[Page] = None) -> Dict[str, Any]:
        """
        Process all deletable items on the current page.

        Args:
            page: Optional Page object (uses self.page if None)

        Returns:
            Dictionary with statistics: {'deleted': int, 'failed': int, 'skipped': int, 'errors': list}
        """
        page = page or self.page

        stats: Dict[str, Any] = {"deleted": 0, "failed": 0, "skipped": 0, "errors": []}

        # Extract items from page
        self.logger.info("Extracting items from page...")
        items = self.item_extractor.extract_items(page)

        if not items:
            self.logger.info("No deletable items found on page")
            return stats

        self.logger.info(f"Found {len(items)} deletable items, processing...")

        # Process each item
        for i, item in enumerate(items, 1):
            self.logger.debug(
                f"Processing item {i}/{len(items)}: {item.get('type')} from {item.get('date_string')}"
            )

            # Check if we should continue (block check)
            if not self.block_manager.should_continue():
                self.logger.error("Block detected, stopping deletion")
                stats["errors"].append(
                    {"item": "block", "date": "N/A", "error": "Action block detected, must wait"}
                )
                break

            # Check rate limit and apply delay
            if not self.rate_limiter.wait_before_action():
                self.logger.warning("Rate limit exceeded, stopping deletion")
                stats["errors"].append(
                    {"item": "rate_limit", "date": "N/A", "error": "Rate limit exceeded"}
                )
                break

            # Attempt deletion
            result = self.delete_item(page, item)

            # Record action (even if failed, to track attempts)
            self.rate_limiter.record_action()

            # Check for errors after deletion
            error_detected, error_message = self.error_detector.check_for_errors(page)
            if error_detected:
                block_detected = self.block_manager.check_and_handle_block(
                    page, self.error_detector
                )
                if block_detected:
                    self.logger.error(f"Block detected after deletion: {error_message}")
                    self.block_manager.apply_backoff(self.rate_limiter)
                    stats["errors"].append(
                        {
                            "item": item.get("type", "unknown"),
                            "date": item.get("date_string", "unknown"),
                            "error": f"Block detected: {error_message}",
                        }
                    )
                    break

            if result[0]:  # Success
                stats["deleted"] += 1
                self.logger.info(f"Successfully deleted item {i}/{len(items)}")
            else:
                stats["failed"] += 1
                error_msg = result[1]
                stats["errors"].append(
                    {
                        "item": item.get("type", "unknown"),
                        "date": item.get("date_string", "unknown"),
                        "error": error_msg,
                    }
                )
                self.logger.warning(f"Failed to delete item {i}/{len(items)}: {error_msg}")

        # Update state with statistics
        self._update_progress_state(stats)

        self.logger.info(
            f"Page processing complete: {stats['deleted']} deleted, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )

        return stats

    def delete_item(self, page: Page, item: dict, max_retries: int = 3) -> tuple[bool, str]:
        """
        Delete a single item using the appropriate handler with retry logic.

        Args:
            page: Playwright Page object
            item: Item dictionary to delete
            max_retries: Maximum number of retries for transient errors (default: 3)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Select appropriate handler
        handler = self._select_handler(item)

        if not handler:
            return False, f"No handler found for item type: {item.get('type')}"

        # Retry logic for transient errors
        last_error = None
        for attempt in range(max_retries):
            try:
                success, message = handler.delete(page, item)
                if success:
                    return True, message
                # If deletion failed but not due to transient error, don't retry
                if "timeout" not in message.lower() and "network" not in message.lower():
                    return False, message
                last_error = message
            except PlaywrightTimeoutError as e:
                last_error = f"Timeout: {str(e)}"
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retry {attempt + 1}/{max_retries} after timeout")
                    continue
            except Exception as e:
                # Non-transient errors don't retry
                self.logger.error(f"Unexpected error during deletion: {e}")
                return False, f"Unexpected error: {str(e)}"

        return False, last_error or "Deletion failed after retries"

    def _select_handler(self, item: dict) -> Optional[DeletionHandler]:
        """
        Select appropriate handler for item.

        Args:
            item: Item dictionary

        Returns:
            DeletionHandler instance or None if no handler found
        """
        for handler in self.handlers:
            try:
                if handler.can_handle(item):
                    self.logger.debug(f"Selected handler: {type(handler).__name__}")
                    return handler
            except Exception as e:
                self.logger.debug(f"Handler {type(handler).__name__} error in can_handle: {e}")
                continue

        return None

    def _update_progress_state(self, stats: dict) -> None:
        """
        Update progress state with current statistics.

        Args:
            stats: Statistics dictionary from process_page
        """
        try:
            state = self.state_manager.get_state()

            # Update statistics
            state["total_deleted"] += stats["deleted"]
            state["deleted_today"] += stats["deleted"]
            state["errors_encountered"] += len(stats["errors"])

            # Update block information
            state["block_detected"] = self.block_manager.block_detected
            state["block_count"] = self.block_manager.block_count

            # Save state
            self.state_manager.save_state(state)

        except Exception as e:
            self.logger.warning(f"Failed to update progress state: {e}")
            # Don't fail the operation if state save fails
