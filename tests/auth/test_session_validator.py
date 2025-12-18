"""
Tests for SessionValidator class.
"""
from unittest.mock import Mock, patch

import pytest

from src.auth.session_validator import SessionValidator


class TestSessionValidator:
    """Test SessionValidator class."""

    def test_init_default_timeout(self):
        """Test SessionValidator initialization with default timeout."""
        validator = SessionValidator()

        assert validator.timeout == 30000

    def test_init_custom_timeout(self):
        """Test SessionValidator initialization with custom timeout."""
        validator = SessionValidator(timeout=60000)

        assert validator.timeout == 60000

    def test_check_login_redirect_url_contains_login(self):
        """Test detecting login redirect in URL."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/login.php"

        assert validator._check_login_redirect(mock_page) is True

    def test_check_login_redirect_url_contains_checkpoint(self):
        """Test detecting checkpoint in URL."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/checkpoint"

        assert validator._check_login_redirect(mock_page) is True

    def test_check_login_redirect_no_redirect(self):
        """Test when not redirected to login."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        mock_page.locator.return_value.count.return_value = 0

        assert validator._check_login_redirect(mock_page) is False

    def test_check_login_redirect_login_form_present(self):
        """Test detecting login form elements."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        # Mock locator to return element count > 0
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_page.locator.return_value = mock_locator

        assert validator._check_login_redirect(mock_page) is True

    def test_check_session_indicators_profile_link(self):
        """Test _check_session_indicators with profile link present."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        # Mock locator to find profile link
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_page.locator.return_value = mock_locator

        # Mock _check_login_redirect to return False
        with patch.object(validator, "_check_login_redirect", return_value=False):
            result = validator._check_session_indicators(mock_page)

            assert result is True

    def test_check_session_indicators_feed_link(self):
        """Test _check_session_indicators with feed/home link present."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        # First selector returns 0, second returns 1 (feed link)
        mock_profile_locator = Mock()
        mock_profile_locator.count.return_value = 0

        mock_feed_locator = Mock()
        mock_feed_locator.count.return_value = 1

        # Configure locator to return different values for different selectors
        def locator_side_effect(selector):
            if "profile" in selector.lower():
                return mock_profile_locator
            elif "home" in selector.lower() or "feed" in selector.lower():
                return mock_feed_locator
            else:
                default_locator = Mock()
                default_locator.count.return_value = 0
                return default_locator

        mock_page.locator.side_effect = locator_side_effect

        # Mock _check_login_redirect to return False
        with patch.object(validator, "_check_login_redirect", return_value=False):
            result = validator._check_session_indicators(mock_page)

            assert result is True

    def test_check_session_indicators_no_indicators(self):
        """Test _check_session_indicators with no indicators present."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        # All locators return 0
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        # Mock _check_login_redirect to return True (on login page)
        with patch.object(validator, "_check_login_redirect", return_value=True):
            result = validator._check_session_indicators(mock_page)

            assert result is False

    def test_check_session_indicators_fallback_not_on_login(self):
        """Test _check_session_indicators fallback when not on login page."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        # All selectors return 0 (no indicators found)
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        # Mock _check_login_redirect to return False (not on login)
        # This triggers the fallback check
        with patch.object(validator, "_check_login_redirect", return_value=False):
            result = validator._check_session_indicators(mock_page)

            # Fallback should return True if not on login page
            assert result is True

    def test_check_session_indicators_exception_handling(self):
        """Test _check_session_indicators handles exceptions gracefully."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        # Mock locator to raise exception - this will be caught by inner try-except
        # To test the outer exception handler, we need an exception that escapes
        # The _check_login_redirect call is not in a try-except, so if it raises,
        # it will be caught by the outer handler
        mock_page.locator.return_value.count.return_value = 0  # All selectors return 0
        # Mock _check_login_redirect to raise exception to trigger outer exception handler
        with patch.object(
            validator, "_check_login_redirect", side_effect=Exception("Check redirect error")
        ):
            # Should return False on exception
            result = validator._check_session_indicators(mock_page)

            assert result is False

    def test_detect_2fa_challenge_url(self):
        """Test detecting 2FA challenge in URL."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/checkpoint"

        assert validator._detect_2fa_challenge(mock_page) is True

    def test_detect_2fa_challenge_content(self):
        """Test detecting 2FA challenge in page content."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        mock_page.content.return_value = "Enter your two-factor authentication code"

        assert validator._detect_2fa_challenge(mock_page) is True

    def test_detect_2fa_challenge_no_challenge(self):
        """Test when no 2FA challenge present."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        mock_page.content.return_value = "Welcome to Facebook"

        assert validator._detect_2fa_challenge(mock_page) is False

    @patch("src.auth.session_validator.SessionValidator._check_login_redirect")
    @patch("src.auth.session_validator.SessionValidator._detect_2fa_challenge")
    def test_validate_session_success(self, mock_2fa, mock_login):
        """Test successful session validation."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        mock_2fa.return_value = False
        mock_login.return_value = False

        # Mock session indicators check
        with patch.object(validator, "_check_session_indicators", return_value=True):
            is_valid, message = validator.validate_session(mock_page)

            assert is_valid is True
            assert "valid" in message.lower()

    @patch("src.auth.session_validator.SessionValidator._detect_2fa_challenge")
    def test_validate_session_2fa_challenge(self, mock_2fa):
        """Test session validation with 2FA challenge."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        mock_2fa.return_value = True

        is_valid, message = validator.validate_session(mock_page)

        assert is_valid is False
        assert "2fa" in message.lower() or "challenge" in message.lower()

    @patch("src.auth.session_validator.SessionValidator._detect_2fa_challenge")
    @patch("src.auth.session_validator.SessionValidator._check_login_redirect")
    def test_validate_session_expired(self, mock_login, mock_2fa):
        """Test session validation with expired session."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"

        mock_2fa.return_value = False
        mock_login.return_value = True

        is_valid, message = validator.validate_session(mock_page)

        assert is_valid is False
        assert "expired" in message.lower() or "login" in message.lower()

    def test_validate_session_timeout(self):
        """Test session validation with timeout."""
        validator = SessionValidator()
        mock_page = Mock()

        # Mock goto to raise TimeoutError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")

        is_valid, message = validator.validate_session(mock_page)

        assert is_valid is False
        assert "timeout" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
