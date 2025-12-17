"""
Cookie management module for loading and validating Facebook session cookies.
"""
import json
from pathlib import Path
from typing import Optional, cast

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Required cookies for Facebook authentication
REQUIRED_COOKIES = ["c_user", "xs"]


class CookieManager:
    """Manages loading and validation of Facebook session cookies."""

    def __init__(self, cookie_path: Path):
        """
        Initialize CookieManager with path to cookie file.

        Args:
            cookie_path: Path to cookies.json file
        """
        self.cookie_path = cookie_path
        self.cookies_data: Optional[dict] = None

    def load_cookies(self) -> dict:
        """
        Load cookies from JSON file.

        Returns:
            Dictionary containing cookies in Playwright format

        Raises:
            FileNotFoundError: If cookie file doesn't exist
            ValueError: If cookie file format is invalid
        """
        if not self.cookie_path.exists():
            raise FileNotFoundError(
                f"Cookie file not found: {self.cookie_path}\n"
                "Please export your Facebook cookies and save them to this location.\n"
                "See SETUP.md for instructions."
            )

        try:
            with open(self.cookie_path, encoding="utf-8") as f:
                self.cookies_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON format in cookie file: {self.cookie_path}\n"
                f"Error: {e}\n"
                'Expected format: {"cookies": [...], "origins": []}'
            ) from e

        # Validate format
        if self.cookies_data is None:
            raise ValueError(f"Cookie data is None after loading from {self.cookie_path}")

        if not self.validate_cookie_format(self.cookies_data):
            raise ValueError(
                f"Invalid cookie file format: {self.cookie_path}\n"
                'Expected structure: {"cookies": [{"name": ..., "value": ..., "domain": ..., "path": ...}], "origins": []}'
            )

        logger.info(f"Successfully loaded cookies from {self.cookie_path}")
        return self.cookies_data

    def validate_cookie_format(self, cookies: dict) -> bool:
        """
        Validate that cookies match Playwright storage state format.

        Args:
            cookies: Dictionary containing cookie data

        Returns:
            True if format is valid, False otherwise
        """
        if not isinstance(cookies, dict):
            logger.debug("Cookies data is not a dictionary")
            return False

        if "cookies" not in cookies:
            logger.debug("Missing 'cookies' key in cookie data")
            return False

        if not isinstance(cookies["cookies"], list):
            logger.debug("'cookies' is not a list")
            return False

        # Validate each cookie object
        required_fields = ["name", "value", "domain", "path"]
        for i, cookie in enumerate(cookies["cookies"]):
            if not isinstance(cookie, dict):
                logger.debug(f"Cookie at index {i} is not a dictionary")
                return False

            for field in required_fields:
                if field not in cookie:
                    logger.debug(f"Cookie at index {i} missing required field: {field}")
                    return False

            # Validate field types
            if not all(isinstance(cookie[field], str) for field in required_fields):
                logger.debug(f"Cookie at index {i} has non-string field values")
                return False

        logger.debug("Cookie format validation passed")
        return True

    def check_required_cookies(self, cookies: Optional[dict] = None) -> tuple[bool, list[str]]:
        """
        Check if all required cookies are present.

        Args:
            cookies: Cookie data dictionary (uses self.cookies_data if None)

        Returns:
            Tuple of (all_present: bool, missing_cookies: list[str])
        """
        if cookies is None:
            cookies = self.cookies_data

        if cookies is None:
            logger.warning("No cookie data available for validation")
            return False, REQUIRED_COOKIES.copy()

        if "cookies" not in cookies:
            return False, REQUIRED_COOKIES.copy()

        cookie_names = {cookie.get("name") for cookie in cookies["cookies"]}
        missing = [name for name in REQUIRED_COOKIES if name not in cookie_names]

        if missing:
            logger.warning(f"Missing required cookies: {missing}")
            return False, missing

        logger.debug("All required cookies present")
        return True, []

    def get_cookie_value(self, name: str, cookies: Optional[dict] = None) -> Optional[str]:
        """
        Extract value of a specific cookie by name.

        Args:
            name: Cookie name to look up
            cookies: Cookie data dictionary (uses self.cookies_data if None)

        Returns:
            Cookie value if found, None otherwise
        """
        if cookies is None:
            cookies = self.cookies_data

        if cookies is None or "cookies" not in cookies:
            return None

        for cookie in cookies["cookies"]:
            if cookie.get("name") == name:
                return cast(Optional[str], cookie.get("value"))

        logger.debug(f"Cookie '{name}' not found")
        return None

    def get_storage_state(self) -> dict:
        """
        Get cookies in Playwright storage_state format.

        Returns:
            Dictionary ready for Playwright context storage_state parameter

        Raises:
            ValueError: If cookies not loaded or invalid
        """
        if self.cookies_data is None:
            raise ValueError("Cookies not loaded. Call load_cookies() first.")

        # Validate required cookies are present
        all_present, missing = self.check_required_cookies()
        if not all_present:
            raise ValueError(
                f"Missing required cookies: {missing}\n" "Please re-export your Facebook cookies."
            )

        return self.cookies_data
