"""
Comment deletion handler for Facebook comments.
"""
from typing import Optional, cast

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.deletion.handlers.base_handler import DeletionHandler
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CommentDeletionHandler(DeletionHandler):
    """Handler for deleting Facebook comments."""

    def can_handle(self, item: dict) -> bool:
        """
        Check if this handler can process the item.

        Args:
            item: Item dictionary

        Returns:
            True if item is a comment, False otherwise
        """
        return item.get("type") == "comment"

    def delete(self, page: Page, item: dict) -> tuple[bool, str]:
        """
        Execute comment deletion flow.

        Args:
            page: Playwright Page object
            item: Item dictionary to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info(f"Deleting comment (ID: {item.get('item_id', 'unknown')})")

            # Save current URL to return to if needed
            original_url = page.url

            # Try to find delete link directly in Activity Log
            delete_link = self._find_delete_link(page, item)

            # If not found, may need to view context first
            if not delete_link:
                logger.debug("Delete link not found, attempting to view context")
                context_success = self._navigate_to_context(page, item)
                if not context_success:
                    return False, "Could not navigate to comment context"

                # Try to find delete link again
                delete_link = self._find_delete_link(page, item)
                if not delete_link:
                    return False, "Delete link not found after viewing context"

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

            # Wait for navigation
            nav_success = self._wait_for_navigation(page, expected_url_pattern="allactivity")

            # If we navigated to context, navigate back to Activity Log
            if "allactivity" not in page.url.lower():
                logger.debug("Navigating back to Activity Log")
                try:
                    page.goto(original_url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    logger.warning(f"Could not navigate back to Activity Log: {e}")
                    # Still consider deletion successful if we got this far
                    return True, "Comment deleted (navigation back failed)"

            if not nav_success and "allactivity" in page.url.lower():
                # Navigation check failed but we're on Activity Log, consider success
                logger.debug("Navigation check failed but on Activity Log, considering success")
                return True, "Comment deleted successfully"

            logger.info("Comment deleted successfully")
            return True, "Comment deleted successfully"

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during comment deletion: {e}")
            return False, f"Timeout: {str(e)}"
        except Exception as e:
            logger.error(f"Error deleting comment: {e}")
            return False, f"Error: {str(e)}"

    def _find_delete_link(self, page: Page, item: dict) -> Optional[Locator]:
        """
        Find delete link for the comment.

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

        # Search page for delete links (if we're in context view)
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

    def _navigate_to_context(self, page: Page, item: dict) -> bool:
        """
        Navigate to comment context (view post) if needed.

        Args:
            page: Playwright Page object
            item: Item dictionary

        Returns:
            True if navigation successful, False otherwise
        """
        element = item.get("element")
        if not element:
            return False

        # Look for "View Context" or "View Post" link
        context_selectors = [
            'a:has-text("View Context")',
            'a:has-text("View context")',
            'a:has-text("View Post")',
            'a:has-text("View post")',
            'a[href*="view"]',
        ]

        for selector in context_selectors:
            try:
                link = element.locator(selector).first
                if link.count() > 0 and link.is_visible():
                    logger.debug(f"Found context link: {selector}")
                    link.click(timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    return True
            except Exception:
                continue

        logger.debug("No context link found, comment may be deletable directly")
        return False
