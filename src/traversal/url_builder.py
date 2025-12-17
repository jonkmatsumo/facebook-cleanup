"""
URL builder for Facebook Activity Log navigation.
"""

from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Facebook mbasic base URL
MBASIC_BASE = "https://mbasic.facebook.com"


class URLBuilder:
    """Builds Activity Log URLs with year, month, and category filters."""

    def __init__(self, username: str):
        """
        Initialize URLBuilder.

        Args:
            username: Facebook username or user ID
        """
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        self.username = username.strip()
        self.base_url = f"{MBASIC_BASE}/{self.username}/allactivity"

    def build_activity_log_url(
        self, year: int, month: Optional[int] = None, category: Optional[str] = None
    ) -> str:
        """
        Build Activity Log URL with optional filters.

        Args:
            year: Target year (e.g., 2020)
            month: Optional month (1-12)
            category: Optional category filter (cluster_11, cluster_116, cluster_15)

        Returns:
            Complete URL string

        Raises:
            ValueError: If inputs are invalid
        """
        self._validate_year(year)

        params = [f"log_filter=year_{year}"]

        if month is not None:
            self._validate_month(month)
            params.append(f"month={month}")

        if category is not None:
            params.append(f"log_filter={category}")

        url = f"{self.base_url}?{'&'.join(params)}"
        logger.debug(f"Built URL: {url}")
        return url

    def build_year_url(self, year: int) -> str:
        """
        Build URL for a specific year.

        Args:
            year: Target year

        Returns:
            URL string
        """
        return self.build_activity_log_url(year)

    def build_month_url(self, year: int, month: int) -> str:
        """
        Build URL for a specific year and month.

        Args:
            year: Target year
            month: Target month (1-12)

        Returns:
            URL string
        """
        return self.build_activity_log_url(year, month=month)

    def build_category_url(self, year: int, category: str, month: Optional[int] = None) -> str:
        """
        Build URL with category filter.

        Args:
            year: Target year
            category: Category filter (cluster_11, cluster_116, cluster_15)
            month: Optional month (1-12)

        Returns:
            URL string
        """
        return self.build_activity_log_url(year, month=month, category=category)

    def _validate_year(self, year: int) -> None:
        """
        Validate year is within reasonable range.

        Args:
            year: Year to validate

        Raises:
            ValueError: If year is invalid
        """
        if not isinstance(year, int):
            raise ValueError(f"Year must be an integer, got {type(year)}")

        # Facebook was founded in 2004, reasonable range: 2004-2030
        if year < 2004 or year > 2030:
            raise ValueError(f"Year must be between 2004 and 2030, got {year}")

    def _validate_month(self, month: int) -> None:
        """
        Validate month is 1-12.

        Args:
            month: Month to validate

        Raises:
            ValueError: If month is invalid
        """
        if not isinstance(month, int):
            raise ValueError(f"Month must be an integer, got {type(month)}")

        if month < 1 or month > 12:
            raise ValueError(f"Month must be between 1 and 12, got {month}")
