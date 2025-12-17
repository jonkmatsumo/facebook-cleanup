"""
Session validation module for verifying Facebook authentication status.
"""

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Facebook mbasic base URL
MBASIC_URL = "https://mbasic.facebook.com"


class SessionValidator:
    """Validates Facebook session by checking for login redirects and session indicators."""

    def __init__(self, timeout: int = 30000):
        """
        Initialize SessionValidator.

        Args:
            timeout: Page navigation timeout in milliseconds (default: 30000)
        """
        self.timeout = timeout

    def validate_session(self, page: Page) -> tuple[bool, str]:
        """
        Validate that the current session is active and authenticated.

        Args:
            page: Playwright Page object

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        try:
            logger.info("Validating Facebook session...")
            logger.debug(f"Navigating to {MBASIC_URL}")

            # Navigate to mbasic Facebook
            page.goto(MBASIC_URL, wait_until="networkidle", timeout=self.timeout)

            # Check for 2FA challenge first (most specific check)
            if self._detect_2fa_challenge(page):
                logger.warning("2FA challenge detected")
                return False, "2FA challenge detected - manual intervention required"

            # Check for login redirect
            if self._check_login_redirect(page):
                logger.warning("Session expired - redirected to login")
                return False, "Session expired - redirected to login"

            # Check for session indicators
            if self._check_session_indicators(page):
                logger.info("Session validation successful")
                return True, "Session valid"
            else:
                logger.warning("Session indicators not found")
                return False, "Session validation failed - unable to confirm authentication"

        except PlaywrightTimeoutError:
            logger.error(f"Timeout waiting for page load (>{self.timeout}ms)")
            return False, "Timeout waiting for page load"
        except Exception as e:
            logger.error(f"Unexpected error during session validation: {e}")
            return False, f"Session validation error: {str(e)}"

    def _check_login_redirect(self, page: Page) -> bool:
        """
        Detect if page was redirected to login page.

        Args:
            page: Playwright Page object

        Returns:
            True if redirected to login, False otherwise
        """
        current_url = page.url.lower()

        # Check URL for login indicators
        login_indicators = ["login", "checkpoint", "www.facebook.com/login"]
        if any(indicator in current_url for indicator in login_indicators):
            logger.debug(f"Login redirect detected in URL: {current_url}")
            return True

        # Check for login form elements
        try:
            email_input = page.locator("input[name='email']")
            pass_input = page.locator("input[name='pass']")

            if email_input.count() > 0 or pass_input.count() > 0:
                logger.debug("Login form elements detected")
                return True
        except Exception as e:
            logger.debug(f"Error checking for login form: {e}")

        return False

    def _check_session_indicators(self, page: Page) -> bool:
        """
        Look for elements indicating a valid authenticated session.

        Args:
            page: Playwright Page object

        Returns:
            True if session indicators found, False otherwise
        """
        try:
            # Check for profile link (most reliable indicator on mbasic)
            profile_selectors = [
                "a[href*='/profile.php']",
                "a[href*='/me']",
                "a[href*='/home.php']",
                # Generic profile link pattern
                "a[href^='/']:has-text('Profile')",
            ]

            for selector in profile_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        logger.debug(f"Session indicator found: {selector}")
                        return True
                except Exception:
                    continue

            # Check for news feed or home elements
            feed_selectors = [
                "a[href*='/home.php']",
                "a[href*='/feed']",
                # Check for common mbasic navigation elements
                "[role='navigation']",
            ]

            for selector in feed_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        logger.debug(f"Feed indicator found: {selector}")
                        return True
                except Exception:
                    continue

            # Check that we're NOT on login page (negative check)
            if not self._check_login_redirect(page):
                # If we're not on login and page loaded, likely authenticated
                # This is a fallback check
                logger.debug("Not on login page - assuming valid session")
                return True

            return False

        except Exception as e:
            logger.debug(f"Error checking session indicators: {e}")
            return False

    def _detect_2fa_challenge(self, page: Page) -> bool:
        """
        Detect if Facebook is requesting 2FA verification.

        Args:
            page: Playwright Page object

        Returns:
            True if 2FA challenge detected, False otherwise
        """
        current_url = page.url.lower()

        # Check URL for checkpoint/2FA indicators
        checkpoint_indicators = ["checkpoint", "two-factor", "2fa"]
        if any(indicator in current_url for indicator in checkpoint_indicators):
            logger.debug(f"2FA checkpoint detected in URL: {current_url}")
            return True

        # Check page content for 2FA-related text
        try:
            page_content = page.content().lower()
            challenge_texts = [
                "two-factor",
                "two factor",
                "security code",
                "verification code",
                "enter code",
                "checkpoint",
            ]

            if any(text in page_content for text in challenge_texts):
                logger.debug("2FA challenge text detected in page content")
                return True
        except Exception as e:
            logger.debug(f"Error checking for 2FA challenge: {e}")

        return False
