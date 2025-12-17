"""
Trash/Recycle Bin cleanup module for Facebook.
"""

from typing import Any, Dict

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.utils.logging import get_logger

logger = get_logger(__name__)

TRASH_URL = "https://mbasic.facebook.com/trash"


class TrashCleanup:
    """Handles cleanup of Facebook Trash/Recycle Bin."""

    def __init__(self, page: Page):
        """
        Initialize TrashCleanup.

        Args:
            page: Playwright Page object
        """
        self.page = page
        self.logger = logger

    def cleanup_trash(self) -> Dict[str, Any]:
        """
        Navigate to trash and delete all items.

        Returns:
            Dictionary with statistics: {'deleted': int, 'failed': int, 'errors': list}
        """
        stats: Dict[str, Any] = {"deleted": 0, "failed": 0, "errors": []}

        try:
            self.logger.info("Navigating to Trash...")
            self.page.goto(TRASH_URL, wait_until="networkidle", timeout=30000)

            # Check if trash is empty
            if self._is_trash_empty():
                self.logger.info("Trash is empty, nothing to clean")
                return stats

            # Select all items
            if not self._select_all():
                self.logger.warning("Could not select all items in trash")
                return stats

            # Delete selected items
            if self._delete_selected():
                self.logger.info("Successfully deleted items from trash")
                stats["deleted"] = 1  # Count as one batch operation
            else:
                self.logger.warning("Failed to delete items from trash")
                stats["failed"] = 1

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout accessing trash: {e}")
            stats["errors"].append(f"Timeout: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error cleaning trash: {e}")
            stats["errors"].append(f"Error: {str(e)}")

        return stats

    def _is_trash_empty(self) -> bool:
        """
        Check if trash is empty.

        Returns:
            True if trash is empty, False otherwise
        """
        try:
            # Look for "empty" indicators
            empty_selectors = [
                'text="No items"',
                'text="Trash is empty"',
                'text="Nothing in trash"',
            ]

            for selector in empty_selectors:
                if self.page.locator(selector).count() > 0:
                    return True

            # Check if there are any items (checkboxes or item containers)
            item_selectors = [
                'input[type="checkbox"]',
                'div[role="article"]',
                "article",
            ]

            for selector in item_selectors:
                if self.page.locator(selector).count() > 0:
                    return False

            return True

        except Exception:
            return False

    def _select_all(self) -> bool:
        """
        Select all items in trash using checkboxes.

        Returns:
            True if selection successful, False otherwise
        """
        select_selectors = [
            'input[type="checkbox"][name*="select"]',
            'input[type="checkbox"]:first-of-type',
            'a:has-text("Select All")',
            'button:has-text("Select All")',
        ]

        for selector in select_selectors:
            try:
                if selector.startswith("a:") or selector.startswith("button:"):
                    # Click "Select All" link/button
                    link = self.page.locator(selector).first
                    if link.count() > 0 and link.is_visible():
                        link.click(timeout=5000)
                        self.page.wait_for_timeout(1000)  # Wait for selection
                        return True
                else:
                    # Check all checkboxes
                    checkboxes = self.page.locator(selector).all()
                    if checkboxes:
                        for checkbox in checkboxes:
                            if checkbox.is_visible():
                                checkbox.check(timeout=2000)
                        return True
            except Exception:
                continue

        return False

    def _delete_selected(self) -> bool:
        """
        Delete selected items.

        Returns:
            True if deletion successful, False otherwise
        """
        delete_selectors = [
            'input[type="submit"][value*="Delete"]',
            'button:has-text("Delete")',
            'a:has-text("Delete")',
            'input[type="submit"]',
        ]

        for selector in delete_selectors:
            try:
                button = self.page.locator(selector).first
                if button.count() > 0 and button.is_visible():
                    button.click(timeout=5000)

                    # Wait for confirmation if needed
                    self.page.wait_for_load_state("networkidle", timeout=10000)

                    # Check if we need to confirm
                    confirm_selectors = [
                        'input[type="submit"][value*="Delete"]',
                        'button:has-text("Delete")',
                        'button:has-text("Confirm")',
                    ]

                    for confirm_selector in confirm_selectors:
                        try:
                            confirm_btn = self.page.locator(confirm_selector).first
                            if confirm_btn.count() > 0 and confirm_btn.is_visible():
                                confirm_btn.click(timeout=5000)
                                self.page.wait_for_load_state("networkidle", timeout=10000)
                                break
                        except Exception:
                            continue

                    return True
            except Exception:
                continue

        return False
