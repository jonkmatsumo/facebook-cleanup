"""
Reaction removal handler for Facebook likes and reactions.
"""
from typing import Optional, cast

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.deletion.handlers.base_handler import DeletionHandler
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ReactionRemovalHandler(DeletionHandler):
    """Handler for removing Facebook likes and reactions."""

    def can_handle(self, item: dict) -> bool:
        """
        Check if this handler can process the item.

        Args:
            item: Item dictionary

        Returns:
            True if item is a reaction, False otherwise
        """
        return item.get("type") == "reaction"

    def delete(self, page: Page, item: dict) -> tuple[bool, str]:
        """
        Execute reaction removal flow.

        Note: Reactions use "remove" terminology, but we implement delete()
        to match the base interface.

        Args:
            page: Playwright Page object
            item: Item dictionary to remove

        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.remove_reaction(page, item)

    def remove_reaction(self, page: Page, item: dict) -> tuple[bool, str]:
        """
        Remove a reaction (like/unlike).

        Args:
            page: Playwright Page object
            item: Item dictionary to remove

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info(f"Removing reaction (ID: {item.get('item_id', 'unknown')})")

            # Find unlike/remove link
            unlike_link = self._find_unlike_link(page, item)
            if not unlike_link:
                return False, "Unlike/Remove link not found"

            # Click unlike link (usually no confirmation needed)
            logger.debug("Clicking unlike/remove link")
            unlike_link.click(timeout=5000)

            # Wait for page update (may be AJAX, not full navigation)
            try:
                # Wait a bit for AJAX update
                page.wait_for_timeout(1000)  # 1 second

                # Check if link is gone (reaction removed)
                if not unlike_link.is_visible():
                    logger.info("Reaction removed successfully")
                    return True, "Reaction removed successfully"

                # If still visible, wait for network activity
                page.wait_for_load_state("networkidle", timeout=5000)

                # Check again
                if not unlike_link.is_visible():
                    logger.info("Reaction removed successfully (after network idle)")
                    return True, "Reaction removed successfully"

                # Still visible - may have failed or already removed
                logger.warning("Unlike link still visible after click")
                return True, "Reaction removal attempted (status unclear)"

            except Exception as e:
                logger.debug(f"Error waiting for reaction removal: {e}")
                # Still consider success if click succeeded
                return True, "Reaction removal attempted"

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during reaction removal: {e}")
            return False, f"Timeout: {str(e)}"
        except Exception as e:
            logger.error(f"Error removing reaction: {e}")
            return False, f"Error: {str(e)}"

    def _find_unlike_link(self, page: Page, item: dict) -> Optional[Locator]:
        """
        Find unlike/remove reaction link.

        Args:
            page: Playwright Page object
            item: Item dictionary

        Returns:
            Locator for unlike link or None
        """
        # First try using the delete_link from item (may be unlike link)
        if item.get("delete_link"):
            try:
                if item["delete_link"].is_visible():
                    return item["delete_link"]
            except Exception:
                pass

        # Fallback: search in the item element
        element = item.get("element")
        if element:
            unlike_selectors = [
                'a:has-text("Unlike")',
                'a:has-text("Remove reaction")',
                'a:has-text("Remove Reaction")',
                'a[href*="unlike"]',
                'a[href*="remove"]',
                'button:has-text("Unlike")',
            ]

            for selector in unlike_selectors:
                try:
                    link = element.locator(selector).first
                    if link.count() > 0 and link.is_visible():
                        return cast(Locator, link)
                except Exception:
                    continue

        # Search page for unlike links
        page_selectors = [
            'a:has-text("Unlike")',
            'a:has-text("Remove reaction")',
            'a[href*="unlike"]',
        ]

        for selector in page_selectors:
            try:
                links = page.locator(selector).all()
                for link in links:
                    if link.is_visible():
                        return cast(Locator, link)
            except Exception:
                continue

        return None
