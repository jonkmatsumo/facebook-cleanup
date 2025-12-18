"""
Unit tests for TrashCleanup module.
"""
from unittest.mock import Mock, patch

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.deletion.trash_cleanup import TRASH_URL, TrashCleanup


@pytest.mark.unit
class TestTrashCleanup:
    """Test TrashCleanup class."""

    def test_init(self):
        """Test TrashCleanup initialization."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        assert cleanup.page == mock_page
        assert cleanup.logger is not None

    def test_cleanup_trash_success(self):
        """Test successful trash cleanup."""
        mock_page = Mock()
        mock_page.goto.return_value = None
        cleanup = TrashCleanup(mock_page)

        with patch.object(cleanup, "_is_trash_empty", return_value=False):
            with patch.object(cleanup, "_select_all", return_value=True):
                with patch.object(cleanup, "_delete_selected", return_value=True):
                    stats = cleanup.cleanup_trash()

                    assert stats["deleted"] == 1
                    assert stats["failed"] == 0
                    assert len(stats["errors"]) == 0
                    mock_page.goto.assert_called_once_with(
                        TRASH_URL, wait_until="networkidle", timeout=30000
                    )

    def test_cleanup_trash_empty(self):
        """Test cleanup when trash is empty."""
        mock_page = Mock()
        mock_page.goto.return_value = None
        cleanup = TrashCleanup(mock_page)

        with patch.object(cleanup, "_is_trash_empty", return_value=True):
            stats = cleanup.cleanup_trash()

            assert stats["deleted"] == 0
            assert stats["failed"] == 0
            assert len(stats["errors"]) == 0

    def test_cleanup_trash_select_all_failure(self):
        """Test cleanup when select_all fails."""
        mock_page = Mock()
        mock_page.goto.return_value = None
        cleanup = TrashCleanup(mock_page)

        with patch.object(cleanup, "_is_trash_empty", return_value=False):
            with patch.object(cleanup, "_select_all", return_value=False):
                stats = cleanup.cleanup_trash()

                assert stats["deleted"] == 0
                assert stats["failed"] == 0

    def test_cleanup_trash_delete_failure(self):
        """Test cleanup when delete_selected fails."""
        mock_page = Mock()
        mock_page.goto.return_value = None
        cleanup = TrashCleanup(mock_page)

        with patch.object(cleanup, "_is_trash_empty", return_value=False):
            with patch.object(cleanup, "_select_all", return_value=True):
                with patch.object(cleanup, "_delete_selected", return_value=False):
                    stats = cleanup.cleanup_trash()

                    assert stats["deleted"] == 0
                    assert stats["failed"] == 1

    def test_cleanup_trash_timeout(self):
        """Test cleanup handles PlaywrightTimeoutError."""
        mock_page = Mock()
        mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")
        cleanup = TrashCleanup(mock_page)

        stats = cleanup.cleanup_trash()

        assert stats["deleted"] == 0
        assert stats["failed"] == 0
        assert len(stats["errors"]) == 1
        assert "timeout" in stats["errors"][0].lower()

    def test_cleanup_trash_exception(self):
        """Test cleanup handles general exceptions."""
        mock_page = Mock()
        mock_page.goto.side_effect = ValueError("Error")
        cleanup = TrashCleanup(mock_page)

        stats = cleanup.cleanup_trash()

        assert stats["deleted"] == 0
        assert stats["failed"] == 0
        assert len(stats["errors"]) == 1
        assert "error" in stats["errors"][0].lower()

    def test_is_trash_empty_indicators(self):
        """Test _is_trash_empty detects empty indicators."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        # Mock locator to find empty indicator
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_page.locator.return_value = mock_locator

        result = cleanup._is_trash_empty()
        assert result is True

    def test_is_trash_empty_items_found(self):
        """Test _is_trash_empty detects items."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        # Mock locator: first 3 calls for empty selectors return 0, 4th call (first item selector) returns 1
        mock_empty_locator = Mock()
        mock_empty_locator.count.return_value = 0

        mock_item_locator = Mock()
        mock_item_locator.count.return_value = 1

        # Function checks 3 empty selectors, then 3 item selectors
        # We need to mock all 6 calls, but the 4th one (first item selector) should find items
        mock_page.locator.side_effect = [
            mock_empty_locator,  # First empty selector
            mock_empty_locator,  # Second empty selector
            mock_empty_locator,  # Third empty selector
            mock_item_locator,  # First item selector (finds items)
        ]

        result = cleanup._is_trash_empty()
        assert result is False

    def test_is_trash_empty_no_indicators_no_items(self):
        """Test _is_trash_empty returns True when no indicators and no items."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        # Mock all locators to return 0
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        result = cleanup._is_trash_empty()
        assert result is True

    def test_is_trash_empty_exception(self):
        """Test _is_trash_empty handles exceptions."""
        mock_page = Mock()
        mock_page.locator.side_effect = ValueError("Error")
        cleanup = TrashCleanup(mock_page)

        result = cleanup._is_trash_empty()
        assert result is False  # Returns False on error

    def test_select_all_via_link(self):
        """Test _select_all via 'Select All' link/button."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        mock_link = Mock()
        mock_link.count.return_value = 1
        mock_link.is_visible.return_value = True
        mock_link.click.return_value = None
        mock_link.first = mock_link

        mock_page.locator.return_value = mock_link
        mock_page.wait_for_timeout.return_value = None

        result = cleanup._select_all()
        assert result is True
        mock_link.click.assert_called_once()

    def test_select_all_via_checkboxes(self):
        """Test _select_all via checkboxes."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        # Mock checkbox locator
        mock_checkbox1 = Mock()
        mock_checkbox1.is_visible.return_value = True
        mock_checkbox1.check.return_value = None

        mock_checkbox2 = Mock()
        mock_checkbox2.is_visible.return_value = True
        mock_checkbox2.check.return_value = None

        mock_checkbox_locator = Mock()
        mock_checkbox_locator.all.return_value = [mock_checkbox1, mock_checkbox2]

        # First call for link returns 0, second for checkbox returns checkboxes
        mock_page.locator.side_effect = [
            Mock(count=Mock(return_value=0)),  # Link not found
            mock_checkbox_locator,  # Checkboxes found
        ]

        result = cleanup._select_all()
        assert result is True
        mock_checkbox1.check.assert_called_once()
        mock_checkbox2.check.assert_called_once()

    def test_select_all_failure(self):
        """Test _select_all returns False when no selectors work."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        # All locators return 0 or raise exceptions
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_locator.all.return_value = []
        mock_page.locator.return_value = mock_locator

        result = cleanup._select_all()
        assert result is False

    def test_delete_selected_success(self):
        """Test _delete_selected successfully deletes."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        mock_button = Mock()
        mock_button.count.return_value = 1
        mock_button.is_visible.return_value = True
        mock_button.click.return_value = None
        mock_button.first = mock_button

        mock_page.locator.return_value = mock_button
        mock_page.wait_for_load_state.return_value = None

        # Mock confirmation check (no confirmation needed)
        mock_confirm_locator = Mock()
        mock_confirm_locator.count.return_value = 0
        mock_page.locator.side_effect = [mock_button, mock_confirm_locator]

        result = cleanup._delete_selected()
        assert result is True
        mock_button.click.assert_called_once()

    def test_delete_selected_with_confirmation(self):
        """Test _delete_selected with confirmation."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        mock_button = Mock()
        mock_button.count.return_value = 1
        mock_button.is_visible.return_value = True
        mock_button.click.return_value = None
        mock_button.first = mock_button

        mock_confirm_button = Mock()
        mock_confirm_button.count.return_value = 1
        mock_confirm_button.is_visible.return_value = True
        mock_confirm_button.click.return_value = None
        mock_confirm_button.first = mock_confirm_button

        # First call returns delete button, second returns confirm button
        mock_page.locator.side_effect = [mock_button, mock_confirm_button]
        mock_page.wait_for_load_state.return_value = None

        result = cleanup._delete_selected()
        assert result is True
        mock_button.click.assert_called_once()
        mock_confirm_button.click.assert_called_once()

    def test_delete_selected_failure(self):
        """Test _delete_selected returns False when no delete button found."""
        mock_page = Mock()
        cleanup = TrashCleanup(mock_page)

        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        result = cleanup._delete_selected()
        assert result is False
