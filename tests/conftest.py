"""
Pytest configuration and shared fixtures for all tests.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import pytest  # noqa: E402


# Configure pytest markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, with dependencies)")
    config.addinivalue_line("markers", "slow: Slow tests (may take significant time)")
    config.addinivalue_line("markers", "requires_network: Tests that require network access")
    config.addinivalue_line("markers", "requires_browser: Tests that require browser automation")
