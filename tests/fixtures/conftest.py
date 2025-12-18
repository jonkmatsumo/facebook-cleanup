"""
Conftest for tests/fixtures directory.

Exposes fixtures from mock_cookies.py and mock_pages.py using pytest_plugins.
"""
# Make fixtures from these modules discoverable by pytest
pytest_plugins = [
    "tests.fixtures.mock_cookies",
    "tests.fixtures.mock_pages",
]
