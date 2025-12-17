"""
Pagination handler for navigating through Activity Log pages.
"""
from typing import Optional

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.utils.logging import get_logger

logger = get_logger(__name__)


class PaginationHandler:
    """Handles pagination through Activity Log pages."""

    def __init__(self, timeout: int = 30000):
        """
        Initialize PaginationHandler.

        Args:
            timeout: Page navigation timeout in milliseconds (default: 30000)
        """
        self.timeout = timeout
        # Common selectors for "See More" links on mbasic
        self.see_more_selectors = [
            'a:has-text("See More")',
            'a:has-text("See more posts")',
            'a:has-text("See more")',
            'a[href*="allactivity"]:has-text("More")',
            'a[href*="pagination"]',
            'a[href*="next"]',
            # Generic pattern: link containing "more" in text
            'a:has-text("more")',
        ]

    def has_more_pages(self, page: Page) -> bool:
        """
        Check if there is a "See More" link on the current page.

        Args:
            page: Playwright Page object

        Returns:
            True if "See More" link exists, False otherwise
        """
        for selector in self.see_more_selectors:
            try:
                locator = page.locator(selector)
                count = locator.count()
                if count > 0:
                    # Verify it's visible and clickable
                    first_match = locator.first
                    if first_match.is_visible():
                        logger.debug(f"Found 'See More' link with selector: {selector}")
                        return True
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue

        logger.debug("No 'See More' link found on page")
        return False

    def click_see_more(self, page: Page, timeout: Optional[int] = None) -> bool:
        """
        Click the "See More" link and wait for page to load.

        Args:
            page: Playwright Page object
            timeout: Optional timeout override (uses self.timeout if None)

        Returns:
            True if successful, False otherwise
        """
        timeout = timeout or self.timeout

        # Find the "See More" link
        see_more_link = None
        for selector in self.see_more_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    first_match = locator.first
                    if first_match.is_visible():
                        see_more_link = first_match
                        logger.debug(f"Using selector: {selector}")
                        break
            except Exception:
                continue

        if see_more_link is None:
            logger.warning("Could not find 'See More' link to click")
            return False

        try:
            # Get current URL for logging
            current_url = page.url
            logger.info(f"Clicking 'See More' link (from {current_url})")

            # Click the link
            see_more_link.click(timeout=5000)  # 5 second timeout for click

            # Wait for page to load
            self.wait_for_page_load(page, timeout)

            new_url = page.url
            logger.info(f"Page loaded after 'See More' click (now at {new_url})")

            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout waiting for page load after clicking 'See More': {e}")
            return False
        except Exception as e:
            logger.error(f"Error clicking 'See More' link: {e}")
            return False

    def wait_for_page_load(self, page: Page, timeout: Optional[int] = None) -> None:
        """
        Wait for page to finish loading.

        Args:
            page: Playwright Page object
            timeout: Optional timeout override (uses self.timeout if None)

        Raises:
            PlaywrightTimeoutError: If page doesn't load within timeout
        """
        timeout = timeout or self.timeout

        try:
            # Wait for network to be idle (no requests for 500ms)
            page.wait_for_load_state("networkidle", timeout=timeout)
            logger.debug("Page load state: networkidle")
        except PlaywrightTimeoutError:
            # Fallback: wait for DOM content loaded
            try:
                page.wait_for_load_state("domcontentloaded", timeout=timeout)
                logger.debug("Page load state: domcontentloaded (fallback)")
            except PlaywrightTimeoutError as e:
                logger.warning(f"Page load timeout: {e}")
                raise

    def get_page_items(self, page: Page) -> list:
        """
        Extract activity items from current page.

        This is a placeholder for Phase 4 where items will be extracted
        and passed to deletion handlers.

        Args:
            page: Playwright Page object

        Returns:
            Empty list (to be implemented in Phase 4)
        """
        # TODO: Implement in Phase 4
        # This will extract deletable items from the page DOM
        return []
