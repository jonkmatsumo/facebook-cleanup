"""
Unit tests for deletion handlers and engine.
"""
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.deletion.deletion_engine import DeletionEngine
from src.deletion.handlers import get_all_handlers
from src.deletion.handlers.base_handler import DeletionHandler
from src.deletion.handlers.comment_handler import CommentDeletionHandler
from src.deletion.handlers.post_handler import PostDeletionHandler
from src.deletion.handlers.reaction_handler import ReactionRemovalHandler
from src.deletion.item_extractor import ItemExtractor


class TestBaseHandler:
    """Test DeletionHandler base class."""

    def test_abstract_methods(self):
        """Test that DeletionHandler is abstract."""
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            DeletionHandler()

    def test_wait_for_confirmation_detected(self):
        """Test _wait_for_confirmation detects confirmation page."""
        handler = PostDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/delete.php"
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value.count.return_value = 1

        result = handler._wait_for_confirmation(mock_page)
        assert result is True

    def test_wait_for_confirmation_not_detected(self):
        """Test _wait_for_confirmation when no confirmation page."""
        handler = PostDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/allactivity"
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value.count.return_value = 0

        result = handler._wait_for_confirmation(mock_page)
        assert result is False

    def test_click_confirm_success(self):
        """Test _click_confirm successfully clicks button."""
        handler = PostDeletionHandler()
        mock_page = Mock()

        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_button = Mock()
        mock_button.is_visible.return_value = True
        mock_button.click.return_value = None
        mock_locator.first = mock_button
        mock_page.locator.return_value = mock_locator

        result = handler._click_confirm(mock_page)
        assert result is True
        mock_button.click.assert_called_once()

    def test_wait_for_navigation_success(self):
        """Test _wait_for_navigation detects successful navigation."""
        handler = PostDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/username/allactivity"
        mock_page.wait_for_load_state.return_value = None

        result = handler._wait_for_navigation(mock_page)
        assert result is True


class TestPostDeletionHandler:
    """Test PostDeletionHandler."""

    def test_can_handle_post(self):
        """Test can_handle returns True for posts."""
        handler = PostDeletionHandler()
        item = {"type": "post"}
        assert handler.can_handle(item) is True

    def test_can_handle_non_post(self):
        """Test can_handle returns False for non-posts."""
        handler = PostDeletionHandler()
        item = {"type": "comment"}
        assert handler.can_handle(item) is False

    def test_delete_success(self):
        """Test successful post deletion."""
        handler = PostDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/allactivity"
        mock_page.wait_for_load_state.return_value = None

        # Mock delete link
        mock_delete_link = Mock()
        mock_delete_link.is_visible.return_value = True
        mock_delete_link.click.return_value = None

        item = {
            "type": "post",
            "item_id": "123",
            "delete_link": mock_delete_link,
        }

        # Mock confirmation flow
        with patch.object(handler, "_wait_for_confirmation", return_value=False):
            with patch.object(handler, "_wait_for_navigation", return_value=True):
                success, message = handler.delete(mock_page, item)
                assert success is True
                assert "success" in message.lower()


class TestCommentDeletionHandler:
    """Test CommentDeletionHandler."""

    def test_can_handle_comment(self):
        """Test can_handle returns True for comments."""
        handler = CommentDeletionHandler()
        item = {"type": "comment"}
        assert handler.can_handle(item) is True

    def test_can_handle_non_comment(self):
        """Test can_handle returns False for non-comments."""
        handler = CommentDeletionHandler()
        item = {"type": "post"}
        assert handler.can_handle(item) is False


class TestReactionRemovalHandler:
    """Test ReactionRemovalHandler."""

    def test_can_handle_reaction(self):
        """Test can_handle returns True for reactions."""
        handler = ReactionRemovalHandler()
        item = {"type": "reaction"}
        assert handler.can_handle(item) is True

    def test_can_handle_non_reaction(self):
        """Test can_handle returns False for non-reactions."""
        handler = ReactionRemovalHandler()
        item = {"type": "post"}
        assert handler.can_handle(item) is False


class TestItemExtractor:
    """Test ItemExtractor."""

    def test_init(self):
        """Test ItemExtractor initialization."""
        target_date = datetime(2021, 1, 1)
        extractor = ItemExtractor(target_date)

        assert extractor.target_date == target_date
        assert extractor.date_parser is not None

    def test_extract_items_empty_page(self):
        """Test extract_items with empty page."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_page = Mock()
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value.all.return_value = []

        items = extractor.extract_items(mock_page)
        assert items == []

    def test_determine_item_type_post(self):
        """Test _determine_item_type identifies posts."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()
        mock_element.text_content.return_value = "You posted something"

        item_type = extractor._determine_item_type(mock_element)
        assert item_type == "post"

    def test_determine_item_type_comment(self):
        """Test _determine_item_type identifies comments."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()
        mock_element.text_content.return_value = "You commented on a post"

        item_type = extractor._determine_item_type(mock_element)
        assert item_type == "comment"

    def test_determine_item_type_reaction(self):
        """Test _determine_item_type identifies reactions."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()
        mock_element.text_content.return_value = "You liked a post"

        item_type = extractor._determine_item_type(mock_element)
        assert item_type == "reaction"


class TestDeletionEngine:
    """Test DeletionEngine."""

    def test_init(self):
        """Test DeletionEngine initialization."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        assert engine.page == mock_page
        assert engine.handlers is not None
        assert len(engine.handlers) > 0
        assert engine.item_extractor is not None

    def test_select_handler_post(self):
        """Test _select_handler selects post handler."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        item = {"type": "post"}
        handler = engine._select_handler(item)

        assert handler is not None
        assert isinstance(handler, PostDeletionHandler)

    def test_select_handler_comment(self):
        """Test _select_handler selects comment handler."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        item = {"type": "comment"}
        handler = engine._select_handler(item)

        assert handler is not None
        assert isinstance(handler, CommentDeletionHandler)

    def test_select_handler_reaction(self):
        """Test _select_handler selects reaction handler."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        item = {"type": "reaction"}
        handler = engine._select_handler(item)

        assert handler is not None
        assert isinstance(handler, ReactionRemovalHandler)

    def test_select_handler_no_match(self):
        """Test _select_handler returns None for unknown type."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        item = {"type": "unknown"}
        handler = engine._select_handler(item)

        assert handler is None

    def test_delete_item_success(self):
        """Test delete_item successfully deletes item."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        mock_handler.delete.return_value = (True, "Success")
        engine.handlers = [mock_handler]

        item = {"type": "post"}
        success, message = engine.delete_item(mock_page, item)

        assert success is True
        assert message == "Success"
        mock_handler.delete.assert_called_once_with(mock_page, item)

    def test_process_page_no_items(self):
        """Test process_page with no items."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        with patch.object(engine.item_extractor, "extract_items", return_value=[]):
            stats = engine.process_page()

            assert stats["deleted"] == 0
            assert stats["failed"] == 0
            assert stats["skipped"] == 0


class TestHandlerRegistry:
    """Test handler registry."""

    def test_get_all_handlers(self):
        """Test get_all_handlers returns list of handlers."""
        handlers = get_all_handlers()

        assert len(handlers) > 0
        assert all(isinstance(h, DeletionHandler) for h in handlers)

        # Check specific handler types
        handler_types = [type(h).__name__ for h in handlers]
        assert "PostDeletionHandler" in handler_types
        assert "CommentDeletionHandler" in handler_types
        assert "ReactionRemovalHandler" in handler_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
