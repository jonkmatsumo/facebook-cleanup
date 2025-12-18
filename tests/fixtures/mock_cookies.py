"""
Cookie-related test fixtures.

Provides various cookie data structures and cookie file fixtures for testing.
"""
import json
from pathlib import Path

import pytest


@pytest.fixture
def valid_cookie_data_full():
    """
    Complete cookie data with all required cookies for testing.

    Returns a dictionary with the structure expected by CookieManager:
    {
        "cookies": [...],
        "origins": []
    }

    Includes: c_user, xs, datr (all required cookies).
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
def minimal_cookie_data():
    """
    Minimal valid cookie data with only required cookies.

    Useful for testing scenarios where minimal valid data is needed.
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
def expired_cookie_data():
    """
    Cookie data structure with potentially expired/invalid values.

    Useful for testing cookie validation and expiration scenarios.
    """
    return {
        "cookies": [
            {"name": "c_user", "value": "expired123", "domain": ".facebook.com", "path": "/"},
            {
                "name": "xs",
                "value": "expired456",  # pragma: allowlist secret
                "domain": ".facebook.com",
                "path": "/",
            },
            {"name": "datr", "value": "expired789", "domain": ".facebook.com", "path": "/"},
        ],
        "origins": [],
    }


@pytest.fixture
def invalid_cookie_data():
    """
    Invalid cookie data with cookies missing required fields (domain, path).

    This is the main invalid cookie data fixture (moved from test_auth.py).
    Useful for testing cookie validation logic.
    """
    return {
        "cookies": [
            {
                "name": "c_user",
                "value": "123456789",
                # Missing domain and path
            }
        ],
        "origins": [],
    }


@pytest.fixture
def invalid_cookie_data_missing_fields():
    """
    Invalid cookie data with cookies missing required fields (domain, path).

    Alias for invalid_cookie_data for backwards compatibility.
    Useful for testing cookie validation logic.
    """
    return {
        "cookies": [
            {
                "name": "c_user",
                "value": "123456789",
                # Missing domain and path
            }
        ],
        "origins": [],
    }


@pytest.fixture
def invalid_cookie_data_wrong_structure():
    """
    Invalid cookie data with wrong top-level structure.

    Useful for testing error handling when cookie file structure is invalid.
    """
    return {
        # Missing "cookies" key
        "origins": [],
    }


@pytest.fixture
def invalid_cookie_data_empty():
    """
    Invalid cookie data with empty cookies list.

    Useful for testing validation when no cookies are provided.
    """
    return {
        "cookies": [],
        "origins": [],
    }


@pytest.fixture
def cookie_file_with_data(tmp_path, valid_cookie_data_full):
    """
    Create a temporary cookie file with valid cookie data written to it.

    Args:
        tmp_path: Pytest's temporary directory fixture
        valid_cookie_data_full: The valid_cookie_data_full fixture

    Returns:
        Path object pointing to the cookie file with data
    """
    cookie_file = tmp_path / "cookies.json"
    with open(cookie_file, "w") as f:
        json.dump(valid_cookie_data_full, f)
    return cookie_file


@pytest.fixture
def cookie_file_empty(tmp_path):
    """
    Create an empty temporary cookie file.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path object pointing to an empty cookie file
    """
    cookie_file = tmp_path / "cookies_empty.json"
    cookie_file.touch()  # Create empty file
    return cookie_file


@pytest.fixture
def cookie_file_invalid_json(tmp_path):
    """
    Create a temporary cookie file with invalid JSON content.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path object pointing to the cookie file with invalid JSON
    """
    cookie_file = tmp_path / "cookies_invalid.json"
    cookie_file.write_text("not valid json {")
    return cookie_file
