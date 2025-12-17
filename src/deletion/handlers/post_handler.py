"""
Post deletion handler for standard Facebook posts.
"""

from typing import Optional, cast

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.deletion.handlers.base_handler import DeletionHandler
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PostDeletionHandler(DeletionHandler):
    """Handler for deleting standard Facebook posts."""

    def can_handle(self, item: dict) -> bool:
        """
        Check if this handler can process the item.

        Args:
            item: Item dictionary

        Returns:
            True if item is a post, False otherwise
        """
        return item.get("type") == "post"

    def delete(self, page: Page, item: dict) -> tuple[bool, str]:
        """
        Execute post deletion flow.

        Args:
            page: Playwright Page object
            item: Item dictionary to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info(f"Deleting post (ID: {item.get('item_id', 'unknown')})")

            # Find delete link
            delete_link = self._find_delete_link(page, item)
            if not delete_link:
                return False, "Delete link not found"

            # Click delete link
            logger.debug("Clicking delete link")
            delete_link.click(timeout=5000)

            # Wait for confirmation page (if applicable)
            has_confirmation = self._wait_for_confirmation(page)

            if has_confirmation:
                logger.debug("Confirmation page detected, clicking confirm")
                confirm_success = self._click_confirm(page)
                if not confirm_success:
                    return False, "Could not click confirmation button"

            # Wait for navigation back to Activity Log
            nav_success = self._wait_for_navigation(page, expected_url_pattern="allactivity")
            if not nav_success:
                # Still consider success if we're not on an error page
                current_url = page.url.lower()
                if "error" not in current_url and "login" not in current_url:
                    logger.debug(
                        "Navigation check failed but not on error page, considering success"
                    )
                    return True, "Deletion completed (navigation check inconclusive)"
                return False, "Navigation failed after deletion"

            logger.info("Post deleted successfully")
            return True, "Post deleted successfully"

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during post deletion: {e}")
            return False, f"Timeout: {str(e)}"
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return False, f"Error: {str(e)}"

    def _find_delete_link(self, page: Page, item: dict) -> Optional[Locator]:
        """
        Find delete link for the post.

        Args:
            page: Playwright Page object
            item: Item dictionary

        Returns:
            Locator for delete link or None
        """
        # First try using the delete_link from item
        if item.get("delete_link"):
            try:
                if item["delete_link"].is_visible():
                    return item["delete_link"]
            except Exception:
                pass

        # Fallback: search in the item element
        element = item.get("element")
        if element:
            delete_selectors = [
                'a:has-text("Delete")',
                'a:has-text("Remove")',
                'a[href*="delete"]',
                'a[href*="remove"]',
                'button:has-text("Delete")',
            ]

            for selector in delete_selectors:
                try:
                    link = element.locator(selector).first
                    if link.count() > 0 and link.is_visible():
                        return cast(Locator, link)
                except Exception:
                    continue

        # Last resort: search entire page (less reliable)
        page_selectors = [
            'a:has-text("Delete")',
            'a[href*="delete"]',
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
