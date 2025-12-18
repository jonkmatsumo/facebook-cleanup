"""
Root-level pytest configuration and shared fixtures for all tests.

This conftest.py is shared by both unit and integration tests.
It registers pytest markers and provides common fixtures.
"""
import sys
from pathlib import Path

import pytest  # noqa: E402

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Expose fixtures from test fixture modules
# Note: pytest_plugins must be defined at the top level (root conftest)
pytest_plugins = [
    "tests.unit.fixtures.mock_cookies",
    "tests.unit.fixtures.mock_pages",
]


# Configure pytest markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, with dependencies)")
    config.addinivalue_line("markers", "slow: Slow tests (may take significant time)")
    config.addinivalue_line("markers", "requires_network: Tests that require network access")
    config.addinivalue_line("markers", "requires_browser: Tests that require browser automation")
