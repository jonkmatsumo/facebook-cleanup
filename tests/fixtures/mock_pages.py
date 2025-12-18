"""
Mock Page objects for different content scenarios.

Provides specialized mock Playwright Page objects configured for specific
testing scenarios (Activity Log, error pages, confirmation pages, etc.).
"""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_page_activity_log():
    """
    Create a mock Page object configured for Activity Log page.

    Includes:
    - URL: Activity Log URL
    - HTML content: Sample activity log structure with items
    - Locators: Configured to find activity items and "See More Posts" links

    Returns:
        Mock Page object configured for Activity Log page
    """
    page = MagicMock()
    page.url = "https://mbasic.facebook.com/testuser/allactivity"

    # Sample Activity Log HTML content
    activity_log_html = """
    <html>
        <body>
            <div class="activity-item">
                <div>You posted something</div>
                <div>November 3, 2020</div>
                <a href="/delete.php?id=123">Delete</a>
            </div>
            <div class="activity-item">
                <div>You commented on a post</div>
                <div>October 15, 2020</div>
                <a href="/delete.php?id=456">Delete</a>
            </div>
            <a href="/allactivity?page=2">See More Posts</a>
        </body>
    </html>
    """
    page.content.return_value = activity_log_html

    # Mock locator for activity items
    mock_activity_locator = MagicMock()
    mock_activity_locator.count.return_value = 2
    mock_activity_locator.all.return_value = [
        MagicMock(),  # First activity item
        MagicMock(),  # Second activity item
    ]

    # Mock locator for "See More Posts" link
    mock_see_more_locator = MagicMock()
    mock_see_more_locator.count.return_value = 1
    mock_see_more_link = MagicMock()
    mock_see_more_link.is_visible.return_value = True
    mock_see_more_link.click.return_value = None
    mock_see_more_locator.first = mock_see_more_link

    # Mock delete link locator
    mock_delete_locator = MagicMock()
    mock_delete_link = MagicMock()
    mock_delete_link.is_visible.return_value = True
    mock_delete_link.click.return_value = None
    mock_delete_link.get_attribute.return_value = "/delete.php?id=123"
    mock_delete_locator.first = mock_delete_link
    mock_delete_locator.count.return_value = 1

    # Configure page.locator to return appropriate locators based on selector
    def locator_side_effect(selector):
        if "See More" in selector or "see more" in selector.lower():
            return mock_see_more_locator
        elif "Delete" in selector or "delete" in selector.lower():
            return mock_delete_locator
        elif "activity-item" in selector or "activity" in selector.lower():
            return mock_activity_locator
        else:
            # Default locator
            default_locator = MagicMock()
            default_locator.count.return_value = 0
            return default_locator

    page.locator.side_effect = locator_side_effect
    page.goto.return_value = None
    page.wait_for_load_state.return_value = None

    return page


@pytest.fixture
def mock_page_with_error_content():
    """
    Create a mock Page object with error content.

    Includes:
    - URL: Can be error URL or normal URL with error content
    - HTML content: Contains error messages matching ErrorDetector patterns

    Returns:
        Mock Page object configured with error content
    """
    page = MagicMock()
    page.url = "https://mbasic.facebook.com/error"

    # Error page HTML content with error message
    error_html = """
    <html>
        <body>
            <div class="error-message">
                <h2>Action Blocked</h2>
                <p>You're going too fast. Please slow down.</p>
                <p>This feature is temporarily blocked.</p>
            </div>
        </body>
    </html>
    """
    page.content.return_value = error_html

    # Mock locator (no important elements on error page)
    mock_locator = MagicMock()
    mock_locator.count.return_value = 0
    page.locator.return_value = mock_locator
    page.goto.return_value = None
    page.wait_for_load_state.return_value = None

    return page


@pytest.fixture
def mock_page_confirmation():
    """
    Create a mock Page object for deletion confirmation page.

    Includes:
    - URL: Confirmation/delete page URL
    - HTML content: Contains confirmation button/form
    - Locators: Configured to find confirmation buttons

    Returns:
        Mock Page object configured for confirmation page
    """
    page = MagicMock()
    page.url = "https://mbasic.facebook.com/delete.php"

    # Confirmation page HTML content
    confirmation_html = """
    <html>
        <body>
            <form method="post">
                <h2>Confirm Deletion</h2>
                <p>Are you sure you want to delete this?</p>
                <input type="submit" value="Delete" name="confirm">
                <a href="/allactivity">Cancel</a>
            </form>
        </body>
    </html>
    """
    page.content.return_value = confirmation_html

    # Mock locator for confirmation button
    mock_confirm_locator = MagicMock()
    mock_confirm_locator.count.return_value = 1
    mock_confirm_button = MagicMock()
    mock_confirm_button.is_visible.return_value = True
    mock_confirm_button.click.return_value = None
    mock_confirm_locator.first = mock_confirm_button

    # Configure page.locator to return confirmation locator
    def locator_side_effect(selector):
        if "submit" in selector.lower() or "Delete" in selector or "confirm" in selector.lower():
            return mock_confirm_locator
        else:
            default_locator = MagicMock()
            default_locator.count.return_value = 0
            return default_locator

    page.locator.side_effect = locator_side_effect
    page.goto.return_value = None
    page.wait_for_load_state.return_value = None

    return page


@pytest.fixture
def mock_page_empty():
    """
    Create a mock Page object with minimal/no content.

    Useful for testing edge cases where page content is empty or minimal.

    Returns:
        Mock Page object with minimal content
    """
    page = MagicMock()
    page.url = "https://mbasic.facebook.com/allactivity"

    # Minimal HTML content
    page.content.return_value = "<html><body></body></html>"

    # Mock locator (no elements found)
    mock_locator = MagicMock()
    mock_locator.count.return_value = 0
    mock_locator.all.return_value = []
    mock_locator.first = MagicMock()
    mock_locator.first.is_visible.return_value = False
    page.locator.return_value = mock_locator
    page.goto.return_value = None
    page.wait_for_load_state.return_value = None

    return page
