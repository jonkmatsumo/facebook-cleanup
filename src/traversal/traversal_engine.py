"""
Traversal engine for navigating Facebook Activity Log by year and month.
"""
from datetime import datetime
from typing import Generator, Optional

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import settings
from src.traversal.date_parser import DateParser
from src.traversal.pagination import PaginationHandler
from src.traversal.url_builder import URLBuilder
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TraversalEngine:
    """Orchestrates navigation through Activity Log by year and month."""

    def __init__(
        self,
        page: Page,
        username: str,
        target_year: Optional[int] = None,
        start_year: Optional[int] = None,
        min_year: int = 2004,
        resume_state: Optional[dict] = None,
        logger_instance=None,
    ):
        """
        Initialize TraversalEngine.

        Args:
            page: Playwright Page object (from BrowserManager)
            username: Facebook username or user ID
            target_year: Year threshold - delete everything before this (defaults to settings.TARGET_YEAR)
            start_year: Starting year for traversal (defaults to settings.START_YEAR)
            min_year: Minimum year to traverse to (default: 2004, Facebook founding year)
            resume_state: Optional state dictionary to resume from
            logger_instance: Optional logger instance
        """
        self.page = page
        self.username = username
        self.target_year = target_year or settings.TARGET_YEAR
        self.start_year = start_year or settings.START_YEAR
        self.min_year = min_year

        self.logger = logger_instance or logger

        # Initialize components
        self.url_builder = URLBuilder(username)
        self.pagination_handler = PaginationHandler()
        self.date_parser = DateParser()

        # Target date for comparison (January 1 of target_year)
        self.target_date = datetime(self.target_year, 1, 1)

        # Resume from state if provided
        if resume_state:
            self._apply_resume_state(resume_state)

        self.logger.info(
            f"TraversalEngine initialized: username={username}, "
            f"start_year={self.start_year}, target_year={self.target_year}, min_year={self.min_year}"
        )

    def _apply_resume_state(self, state: dict) -> None:
        """
        Apply resume state to adjust traversal starting point.

        Args:
            state: State dictionary with current_year, current_month
        """
        if state.get("current_year") and state.get("current_month"):
            resume_year = state["current_year"]
            resume_month = state["current_month"]

            # Adjust start_year to resume position
            if resume_year <= self.start_year:
                self.start_year = resume_year
                self.logger.info(f"Resuming from {resume_year}-{resume_month:02d}")
            else:
                self.logger.warning(
                    f"Resume year {resume_year} is after start_year {self.start_year}, "
                    "starting from configured start_year"
                )

    def traverse_years(self, resume_state: Optional[dict] = None) -> Generator[dict, None, None]:
        """
        Generator that yields pages for each year from start_year down to min_year.

        Args:
            resume_state: Optional state dictionary for resume position

        Yields:
            Dictionary with keys: year, month, page, url, is_pagination, page_number
        """
        self.logger.info(f"Starting year traversal: {self.start_year} -> {self.min_year}")

        # Determine resume position
        resume_year = None
        resume_month = None
        if resume_state:
            resume_year = resume_state.get("current_year")
            resume_month = resume_state.get("current_month")

        for year in range(self.start_year, self.min_year - 1, -1):
            self.logger.info(f"Processing year: {year}")

            try:
                # If resuming, only use resume_month for the resume year
                month_to_resume = resume_month if year == resume_year else None

                # Traverse all months for this year
                yield from self.traverse_months(year, resume_month=month_to_resume)

                # Clear resume_month after first year (only applies once)
                if year == resume_year:
                    resume_month = None

            except Exception as e:
                self.logger.error(f"Error traversing year {year}: {e}")
                # Continue to next year
                continue

    def traverse_months(
        self, year: int, resume_month: Optional[int] = None
    ) -> Generator[dict, None, None]:
        """
        Generator that yields pages for each month in a year (December to January).

        Args:
            year: Year to traverse
            resume_month: Optional month to resume from (skip months after this)

        Yields:
            Dictionary with keys: year, month, page, url, is_pagination
        """
        self.logger.info(f"Starting month traversal for year {year}")

        # Determine starting month (resume from specific month if provided)
        start_month = resume_month if resume_month else 12

        for month in range(start_month, 0, -1):  # From start_month down to January (1)
            self.logger.info(f"Processing {year}-{month:02d}")

            try:
                # Traverse this month (handles pagination)
                yield from self.traverse_page(year, month=month)
            except Exception as e:
                self.logger.error(f"Error traversing {year}-{month:02d}: {e}")
                # Continue to next month
                continue

    def traverse_page(
        self, year: int, month: Optional[int] = None, category: Optional[str] = None
    ) -> Generator[dict, None, None]:
        """
        Handle pagination for a single year/month page.

        Args:
            year: Target year
            month: Optional month (1-12)
            category: Optional category filter

        Yields:
            Dictionary with keys: year, month, page, url, is_pagination, page_number
        """
        # Build URL
        url = self.url_builder.build_activity_log_url(year=year, month=month, category=category)

        self.logger.info(f"Navigating to: {url}")

        try:
            # Navigate to URL
            self.page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for page to fully load
            self.pagination_handler.wait_for_page_load(self.page)

            # Yield first page
            page_number = 1
            yield {
                "year": year,
                "month": month,
                "category": category,
                "page": self.page,
                "url": self.page.url,
                "is_pagination": False,
                "page_number": page_number,
            }

            # Handle pagination
            while self.pagination_handler.has_more_pages(self.page):
                page_number += 1
                self.logger.info(f"Found more pages, clicking 'See More' (page {page_number})")

                success = self.pagination_handler.click_see_more(self.page)

                if not success:
                    self.logger.warning("Failed to click 'See More', stopping pagination")
                    break

                # Yield paginated page
                yield {
                    "year": year,
                    "month": month,
                    "category": category,
                    "page": self.page,
                    "url": self.page.url,
                    "is_pagination": True,
                    "page_number": page_number,
                }

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout navigating to {url}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            raise

    def get_activity_items(self, page: Page) -> list[dict]:
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
        # This will:
        # 1. Find all activity items on the page
        # 2. Extract date information for each
        # 3. Filter items before target_date
        # 4. Return list of items with metadata
        return []

    def traverse_by_category(
        self, category: str, year: Optional[int] = None, month: Optional[int] = None
    ) -> Generator[dict, None, None]:
        """
        Traverse Activity Log filtered by category.

        Args:
            category: Category filter (cluster_11, cluster_116, cluster_15)
            year: Optional specific year (traverses all years if None)
            month: Optional specific month (traverses all months if None)

        Yields:
            Dictionary with page information
        """
        if year is not None:
            # Traverse specific year
            if month is not None:
                # Specific year and month
                for page_info in self.traverse_page(year, month=month, category=category):
                    yield page_info
            else:
                # All months in year
                for month_num in range(12, 0, -1):
                    for page_info in self.traverse_page(year, month=month_num, category=category):
                        yield page_info
        else:
            # Traverse all years
            for year_num in range(self.start_year, self.min_year - 1, -1):
                for month_num in range(12, 0, -1):
                    for page_info in self.traverse_page(
                        year_num, month=month_num, category=category
                    ):
                        yield page_info
