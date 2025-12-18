"""
Unit tests for fingerprint/stealth module.
"""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.stealth.fingerprint import (
    apply_stealth_patches,
    create_stealth_context,
    get_browser_args,
    get_context_options,
)


@pytest.mark.unit
class TestGetBrowserArgs:
    """Test get_browser_args() function."""

    def test_get_browser_args(self):
        """Test get_browser_args returns correct arguments."""
        args = get_browser_args()

        assert isinstance(args, list)
        assert len(args) > 0
        assert "--disable-blink-features=AutomationControlled" in args
        assert "--disable-dev-shm-usage" in args


@pytest.mark.unit
class TestGetContextOptions:
    """Test get_context_options() function."""

    def test_get_context_options_no_cookies(self):
        """Test get_context_options without cookies_path."""
        options = get_context_options()

        assert "viewport" in options
        assert "user_agent" in options
        assert "locale" in options
        assert "timezone_id" in options
        assert "permissions" in options
        assert "color_scheme" in options
        assert "storage_state" not in options

    def test_get_context_options_with_cookies(self, tmp_path):
        """Test get_context_options with cookies_path (file exists)."""
        cookie_file = tmp_path / "cookies.json"
        cookie_file.touch()

        options = get_context_options(cookies_path=cookie_file)

        assert "storage_state" in options
        assert options["storage_state"] == str(cookie_file)

    def test_get_context_options_cookies_not_exist(self, tmp_path):
        """Test get_context_options with cookies_path (file doesn't exist)."""
        cookie_file = tmp_path / "nonexistent.json"

        options = get_context_options(cookies_path=cookie_file)

        assert "storage_state" not in options

    def test_get_context_options_all_options(self):
        """Test get_context_options sets all required options."""
        options = get_context_options()

        assert options["viewport"]["width"] == 360
        assert options["viewport"]["height"] == 640
        assert options["locale"] == "en-US"
        assert options["timezone_id"] == "America/New_York"
        assert options["permissions"] == []
        assert options["color_scheme"] == "light"
        assert "user_agent" in options
        assert len(options["user_agent"]) > 0


@pytest.mark.unit
class TestCreateStealthContext:
    """Test create_stealth_context() function."""

    def test_create_stealth_context_basic(self):
        """Test basic context creation."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context

        result = create_stealth_context(mock_browser, block_resources=False)

        assert result == mock_context
        mock_browser.new_context.assert_called_once()
        # Verify context options were passed
        call_args = mock_browser.new_context.call_args[1]
        assert "viewport" in call_args
        assert "user_agent" in call_args

    def test_create_stealth_context_with_cookies(self, tmp_path):
        """Test context creation with cookies_path."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context

        cookie_file = tmp_path / "cookies.json"
        cookie_file.touch()

        result = create_stealth_context(
            mock_browser, cookies_path=cookie_file, block_resources=False
        )

        assert result == mock_context
        call_args = mock_browser.new_context.call_args[1]
        assert "storage_state" in call_args
        assert call_args["storage_state"] == str(cookie_file)

    def test_create_stealth_context_block_resources(self):
        """Test context creation with resource blocking."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context

        result = create_stealth_context(mock_browser, block_resources=True)

        assert result == mock_context
        # Verify route was set up
        mock_context.route.assert_called_once()

    def test_create_stealth_context_no_block_resources(self):
        """Test context creation without resource blocking."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context

        result = create_stealth_context(mock_browser, block_resources=False)

        assert result == mock_context
        # Verify route was not set up
        mock_context.route.assert_not_called()

    def test_create_stealth_context_extra_options(self):
        """Test context creation with extra_options."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context

        extra_options = {"locale": "fr-FR", "timezone_id": "Europe/Paris"}

        result = create_stealth_context(mock_browser, block_resources=False, **extra_options)

        assert result == mock_context
        call_args = mock_browser.new_context.call_args[1]
        # Extra options should override defaults
        assert call_args["locale"] == "fr-FR"
        assert call_args["timezone_id"] == "Europe/Paris"

    def test_create_stealth_context_resource_blocking(self):
        """Test resource blocking route handler."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context

        # Track route handler
        route_handler = None

        def capture_route(pattern, handler):
            nonlocal route_handler
            route_handler = handler

        mock_context.route.side_effect = capture_route

        result = create_stealth_context(mock_browser, block_resources=True)

        assert result == mock_context
        mock_context.route.assert_called_once()

        # Test route handler blocks images, videos, fonts
        mock_route = Mock()
        mock_route.request.resource_type = "image"
        route_handler(mock_route)
        mock_route.abort.assert_called_once()

        # Test route handler allows other resources
        mock_route2 = Mock()
        mock_route2.request.resource_type = "document"
        route_handler(mock_route2)
        mock_route2.continue_.assert_called_once()


@pytest.mark.unit
class TestApplyStealthPatches:
    """Test apply_stealth_patches() function."""

    def test_apply_stealth_patches_success(self):
        """Test successful patch application."""
        mock_page = Mock()

        with patch("src.stealth.fingerprint._stealth_instance") as mock_stealth:
            apply_stealth_patches(mock_page)

            mock_stealth.apply_stealth_sync.assert_called_once_with(mock_page)

    def test_apply_stealth_patches_exception(self):
        """Test patch application handles exceptions."""
        mock_page = Mock()

        with patch("src.stealth.fingerprint._stealth_instance") as mock_stealth:
            mock_stealth.apply_stealth_sync.side_effect = ValueError("Error")

            # Should not raise exception
            apply_stealth_patches(mock_page)

            mock_stealth.apply_stealth_sync.assert_called_once_with(mock_page)
