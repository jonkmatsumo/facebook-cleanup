"""
Pytest configuration and shared fixtures for unit tests.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest  # noqa: E402

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Note: pytest_plugins is defined in the root tests/conftest.py
# to comply with pytest's requirement that it be at the top level


# Shared fixtures for unit tests
@pytest.fixture
def mock_page():
    """
    Create a mock Playwright Page object.

    Includes commonly used attributes and methods:
    - url: Page URL (default: "https://mbasic.facebook.com/allactivity")
    - content(): Returns mock HTML content
    - locator(): Returns a mock locator
    - goto(): Navigate to URL (returns None)
    - wait_for_load_state(): Wait for page load (returns None)

    Tests can override any attribute or method as needed.
    """
    page = MagicMock()
    page.url = "https://mbasic.facebook.com/allactivity"
    page.content.return_value = "<html><body>Mock page content</body></html>"

    # Mock locator chain
    mock_locator = MagicMock()
    mock_locator.count.return_value = 0
    mock_locator.first = MagicMock()
    mock_locator.first.is_visible.return_value = False
    mock_locator.first.click.return_value = None
    mock_locator.all.return_value = []
    mock_locator.is_visible.return_value = False
    mock_locator.click.return_value = None

    page.locator.return_value = mock_locator
    page.goto.return_value = None
    page.wait_for_load_state.return_value = None

    return page


@pytest.fixture
def mock_context(mock_page):
    """
    Create a mock Playwright BrowserContext object.

    Includes methods:
    - new_page(): Returns mock_page fixture
    - close(): Close context (returns None)

    Args:
        mock_page: The mock_page fixture to return from new_page()
    """
    context = MagicMock()
    context.new_page.return_value = mock_page
    context.close.return_value = None
    return context


@pytest.fixture
def mock_browser(mock_context):
    """
    Create a mock Playwright Browser object.

    Includes methods:
    - new_context(): Returns mock_context fixture
    - close(): Close browser (returns None)

    Args:
        mock_context: The mock_context fixture to return from new_context()
    """
    browser = MagicMock()
    browser.new_context.return_value = mock_context
    browser.close.return_value = None
    return browser


@pytest.fixture
def valid_cookie_data():
    """
    Valid cookie data structure for testing.

    Returns a dictionary with the structure expected by CookieManager:
    {
        "cookies": [...],
        "origins": []
    }
    """
    return {
        "cookies": [
            {"name": "c_user", "value": "123456789", "domain": ".facebook.com", "path": "/"},
            {
                "name": "xs",
                "value": "abc123def456",  # pragma: allowlist secret
                "domain": ".facebook.com",
                "path": "/",
            },
            {"name": "datr", "value": "xyz789", "domain": ".facebook.com", "path": "/"},
        ],
        "origins": [],
    }


@pytest.fixture
def temp_cookie_file(tmp_path):
    """
    Create a temporary cookie file for testing.

    Creates a cookies.json file path in a temporary directory.
    The file is not created by default - tests can write to it as needed.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path object pointing to the temporary cookie file
    """
    cookie_file = tmp_path / "cookies.json"
    return cookie_file


@pytest.fixture
def temp_progress_file(tmp_path):
    """
    Create a temporary progress file path for testing.

    Creates a progress.json file path in a temporary directory.
    The file is not created by default - tests can write to it as needed.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path object pointing to the temporary progress file
    """
    progress_file = tmp_path / "progress.json"
    return progress_file
