"""
Tests for BrowserManager class.
"""
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.auth.browser_manager import BrowserManager


class TestBrowserManager:
    """Test BrowserManager class."""

    def test_init_default_path(self):
        """Test BrowserManager initialization with default cookie path."""
        with patch("src.auth.browser_manager.settings") as mock_settings:
            mock_settings.COOKIES_PATH = Path("default/cookies.json")
            manager = BrowserManager()

            assert manager.cookie_path == Path("default/cookies.json")
            assert manager.cookie_manager is not None
            assert manager.session_validator is not None
            assert manager.playwright is None
            assert manager.browser is None
            assert manager.context is None
            assert manager.page is None

    def test_init_custom_path(self):
        """Test BrowserManager initialization with custom cookie path."""
        custom_path = Path("custom/cookies.json")
        manager = BrowserManager(cookie_path=custom_path)

        assert manager.cookie_path == custom_path
        assert manager.cookie_manager is not None
        assert manager.session_validator is not None

    def test_init_custom_logger(self):
        """Test BrowserManager initialization with custom logger."""
        custom_logger = Mock()
        manager = BrowserManager(logger_instance=custom_logger)

        assert manager.logger == custom_logger

    @patch("src.auth.browser_manager.create_stealth_context")
    @patch("src.auth.browser_manager.apply_stealth_patches")
    @patch("src.auth.browser_manager.get_browser_args")
    @patch("src.auth.browser_manager.sync_playwright")
    def test_create_authenticated_browser_success(
        self, mock_playwright_class, mock_get_args, mock_stealth_patches, mock_create_context
    ):
        """Test create_authenticated_browser with valid cookies."""
        # Setup mocks
        mock_playwright_instance = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_playwright_class.return_value.start.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_get_args.return_value = ["--arg1", "--arg2"]
        mock_create_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Setup cookie manager mock
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))
        manager.cookie_manager.load_cookies = Mock()
        manager.cookie_manager.check_required_cookies = Mock(return_value=(True, []))
        manager.session_validator.validate_session = Mock(return_value=(True, "Session valid"))

        # Execute
        browser, context, page = manager.create_authenticated_browser(validate_session=True)

        # Verify
        assert browser == mock_browser
        assert context == mock_context
        assert page == mock_page
        manager.cookie_manager.load_cookies.assert_called_once()
        manager.cookie_manager.check_required_cookies.assert_called_once()
        mock_stealth_patches.assert_called_once_with(mock_page)
        manager.session_validator.validate_session.assert_called_once_with(mock_page)

    def test_create_authenticated_browser_missing_cookies(self):
        """Test create_authenticated_browser with missing cookies."""
        manager = BrowserManager(cookie_path=Path("test/nonexistent.json"))
        manager.cookie_manager.load_cookies = Mock(
            side_effect=FileNotFoundError("Cookie file not found")
        )
        manager.cleanup = Mock()  # Mock cleanup to verify it's called

        with pytest.raises(FileNotFoundError):
            manager.create_authenticated_browser()

        # Verify cleanup was called (cleanup is called in except block)
        manager.cleanup.assert_called_once()

    @patch("src.auth.browser_manager.create_stealth_context")
    @patch("src.auth.browser_manager.get_browser_args")
    @patch("src.auth.browser_manager.sync_playwright")
    def test_create_authenticated_browser_invalid_cookies(
        self, mock_playwright_class, mock_get_args, mock_create_context
    ):
        """Test create_authenticated_browser with invalid cookies."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))
        manager.cookie_manager.load_cookies = Mock()
        manager.cookie_manager.check_required_cookies = Mock(return_value=(False, ["xs"]))

        with pytest.raises(ValueError) as exc_info:
            manager.create_authenticated_browser()

        assert "missing required cookies" in str(exc_info.value).lower()
        assert "xs" in str(exc_info.value)

    @patch("src.auth.browser_manager.create_stealth_context")
    @patch("src.auth.browser_manager.apply_stealth_patches")
    @patch("src.auth.browser_manager.get_browser_args")
    @patch("src.auth.browser_manager.sync_playwright")
    def test_create_authenticated_browser_session_validation_failure(
        self, mock_playwright_class, mock_get_args, mock_stealth_patches, mock_create_context
    ):
        """Test create_authenticated_browser with session validation failure."""
        # Setup mocks
        mock_playwright_instance = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_playwright_class.return_value.start.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_get_args.return_value = []
        mock_create_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Setup cookie manager and validator mocks
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))
        manager.cookie_manager.load_cookies = Mock()
        manager.cookie_manager.check_required_cookies = Mock(return_value=(True, []))
        manager.session_validator.validate_session = Mock(return_value=(False, "Session expired"))

        # Mock cleanup to avoid actual cleanup during test
        manager.cleanup = Mock()

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            manager.create_authenticated_browser(validate_session=True)

        assert "session validation failed" in str(exc_info.value).lower()
        # Cleanup may be called multiple times (once in validation failure, once in exception handler)
        assert manager.cleanup.called

    @patch("src.auth.browser_manager.create_stealth_context")
    @patch("src.auth.browser_manager.apply_stealth_patches")
    @patch("src.auth.browser_manager.get_browser_args")
    @patch("src.auth.browser_manager.sync_playwright")
    def test_create_authenticated_browser_no_session_validation(
        self, mock_playwright_class, mock_get_args, mock_stealth_patches, mock_create_context
    ):
        """Test create_authenticated_browser without session validation."""
        # Setup mocks
        mock_playwright_instance = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_playwright_class.return_value.start.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_get_args.return_value = []
        mock_create_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Setup cookie manager mock
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))
        manager.cookie_manager.load_cookies = Mock()
        manager.cookie_manager.check_required_cookies = Mock(return_value=(True, []))
        # Mock the session validator method
        manager.session_validator.validate_session = Mock()

        # Execute
        browser, context, page = manager.create_authenticated_browser(validate_session=False)

        # Verify session validator was not called
        manager.session_validator.validate_session.assert_not_called()
        assert browser == mock_browser
        assert context == mock_context
        assert page == mock_page

    def test_cleanup_all_resources(self):
        """Test cleanup method closes all resources."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))

        # Create mock resources
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_playwright = Mock()

        manager.page = mock_page
        manager.context = mock_context
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        # Execute
        manager.cleanup()

        # Verify all resources were closed (check before cleanup sets them to None)
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

        # Verify resources are set to None
        assert manager.page is None
        assert manager.context is None
        assert manager.browser is None
        assert manager.playwright is None

    def test_cleanup_partial_resources(self):
        """Test cleanup method handles partial resource initialization."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))

        # Only page exists
        mock_page = Mock()
        manager.page = mock_page
        manager.context = None
        manager.browser = None
        manager.playwright = None

        # Should not raise exception
        manager.cleanup()

        # Verify page was closed (check before cleanup sets it to None)
        mock_page.close.assert_called_once()
        assert manager.page is None

    def test_cleanup_exception_handling(self):
        """Test cleanup method handles exceptions gracefully."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))

        # Create mock resources that raise exceptions
        manager.page = Mock()
        manager.page.close.side_effect = Exception("Close error")
        manager.context = Mock()
        manager.context.close.side_effect = Exception("Close error")
        manager.browser = Mock()
        manager.browser.close.side_effect = Exception("Close error")
        manager.playwright = Mock()
        manager.playwright.stop.side_effect = Exception("Stop error")

        # Should not raise exception, all cleanup attempts should be made
        manager.cleanup()

        # Verify all cleanup methods were called
        manager.page.close.assert_called_once()
        manager.context.close.assert_called_once()
        manager.browser.close.assert_called_once()
        manager.playwright.stop.assert_called_once()

    def test_context_manager_enter(self):
        """Test BrowserManager context manager __enter__ method."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))

        result = manager.__enter__()

        assert result == manager

    def test_context_manager_exit(self):
        """Test BrowserManager context manager __exit__ method."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))
        manager.page = Mock()
        manager.context = Mock()
        manager.browser = Mock()
        manager.playwright = Mock()

        # Mock cleanup
        manager.cleanup = Mock()

        # Execute
        result = manager.__exit__(None, None, None)

        # Verify cleanup was called
        manager.cleanup.assert_called_once()

        # Verify return value (should be False to not suppress exceptions)
        assert result is False

    def test_context_manager_exit_with_exception(self):
        """Test BrowserManager context manager __exit__ with exception."""
        manager = BrowserManager(cookie_path=Path("test/cookies.json"))
        manager.cleanup = Mock()

        # Execute with exception
        result = manager.__exit__(ValueError, ValueError("test"), None)

        # Verify cleanup was still called (even with exception)
        manager.cleanup.assert_called_once()

        # Verify return value (False means don't suppress the exception)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
