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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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

    def test_delete_success_direct_link(self):
        """Test delete with delete link found directly."""
        handler = CommentDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/allactivity"

        mock_delete_link = Mock()
        mock_delete_link.is_visible.return_value = True
        mock_delete_link.click.return_value = None

        item = {"type": "comment", "item_id": "123", "delete_link": mock_delete_link}

        with patch.object(handler, "_wait_for_confirmation", return_value=False):
            with patch.object(handler, "_wait_for_navigation", return_value=True):
                success, message = handler.delete(mock_page, item)
                assert success is True
                assert "success" in message.lower()
                mock_delete_link.click.assert_called_once()

    def test_delete_success_with_context(self):
        """Test delete with context navigation."""
        handler = CommentDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/allactivity"

        mock_delete_link = Mock()
        mock_delete_link.is_visible.return_value = True
        mock_delete_link.click.return_value = None

        mock_element = Mock()
        item = {"type": "comment", "item_id": "123", "element": mock_element}

        with patch.object(handler, "_find_delete_link", side_effect=[None, mock_delete_link]):
            with patch.object(handler, "_navigate_to_context", return_value=True):
                with patch.object(handler, "_wait_for_confirmation", return_value=False):
                    with patch.object(handler, "_wait_for_navigation", return_value=True):
                        success, message = handler.delete(mock_page, item)
                        assert success is True

    def test_delete_with_confirmation(self):
        """Test delete with confirmation page."""
        handler = CommentDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/allactivity"

        mock_delete_link = Mock()
        mock_delete_link.is_visible.return_value = True
        mock_delete_link.click.return_value = None

        item = {"type": "comment", "item_id": "123", "delete_link": mock_delete_link}

        with patch.object(handler, "_find_delete_link", return_value=mock_delete_link):
            with patch.object(handler, "_wait_for_confirmation", return_value=True):
                with patch.object(handler, "_click_confirm", return_value=True):
                    with patch.object(handler, "_wait_for_navigation", return_value=True):
                        success, message = handler.delete(mock_page, item)
                        assert success is True
                        handler._click_confirm.assert_called_once()

    def test_delete_navigation_back(self):
        """Test delete navigates back to Activity Log."""
        handler = CommentDeletionHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/comment/123"

        mock_delete_link = Mock()
        mock_delete_link.is_visible.return_value = True
        mock_delete_link.click.return_value = None

        item = {"type": "comment", "item_id": "123", "delete_link": mock_delete_link}

        with patch.object(handler, "_find_delete_link", return_value=mock_delete_link):
            with patch.object(handler, "_wait_for_confirmation", return_value=False):
                with patch.object(handler, "_wait_for_navigation", return_value=False):
                    # URL doesn't contain allactivity, should navigate back
                    mock_page.url = "https://mbasic.facebook.com/comment/123"
                    mock_page.goto.return_value = None
                    success, message = handler.delete(mock_page, item)
                    assert success is True
                    mock_page.goto.assert_called_once()

    def test_delete_link_not_found(self):
        """Test delete fails when delete link not found."""
        handler = CommentDeletionHandler()
        mock_page = Mock()

        item = {"type": "comment", "item_id": "123"}

        with patch.object(handler, "_find_delete_link", return_value=None):
            with patch.object(handler, "_navigate_to_context", return_value=False):
                success, message = handler.delete(mock_page, item)
                assert success is False
                assert "could not navigate" in message.lower()

    def test_delete_link_not_found_after_context(self):
        """Test delete fails when delete link not found after context navigation."""
        handler = CommentDeletionHandler()
        mock_page = Mock()

        item = {"type": "comment", "item_id": "123"}

        # First call returns None, context navigation succeeds, second call also returns None
        with patch.object(handler, "_find_delete_link", side_effect=[None, None]):
            with patch.object(handler, "_navigate_to_context", return_value=True):
                success, message = handler.delete(mock_page, item)
                assert success is False
                assert "not found after viewing context" in message.lower()

    def test_delete_timeout_error(self):
        """Test delete handles PlaywrightTimeoutError."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        handler = CommentDeletionHandler()
        mock_page = Mock()

        mock_delete_link = Mock()
        mock_delete_link.click.side_effect = PlaywrightTimeoutError("Timeout")

        item = {"type": "comment", "item_id": "123", "delete_link": mock_delete_link}

        with patch.object(handler, "_find_delete_link", return_value=mock_delete_link):
            success, message = handler.delete(mock_page, item)
            assert success is False
            assert "timeout" in message.lower()

    def test_find_delete_link_from_item(self):
        """Test _find_delete_link uses delete_link from item."""
        handler = CommentDeletionHandler()
        mock_page = Mock()

        mock_delete_link = Mock()
        mock_delete_link.is_visible.return_value = True

        item = {"type": "comment", "delete_link": mock_delete_link}

        result = handler._find_delete_link(mock_page, item)
        assert result == mock_delete_link

    def test_find_delete_link_in_element(self):
        """Test _find_delete_link finds link in element."""
        handler = CommentDeletionHandler()
        mock_page = Mock()

        mock_link = Mock()
        mock_link.count.return_value = 1
        mock_link.is_visible.return_value = True
        mock_link.first = mock_link

        mock_element = Mock()
        mock_element.locator.return_value = mock_link

        item = {"type": "comment", "element": mock_element}

        result = handler._find_delete_link(mock_page, item)
        assert result is not None

    def test_find_delete_link_on_page(self):
        """Test _find_delete_link finds link on page."""
        handler = CommentDeletionHandler()
        mock_page = Mock()

        mock_link = Mock()
        mock_link.is_visible.return_value = True
        mock_page.locator.return_value.all.return_value = [mock_link]

        item = {"type": "comment"}

        result = handler._find_delete_link(mock_page, item)
        assert result == mock_link

    def test_navigate_to_context_success(self):
        """Test _navigate_to_context successfully navigates."""
        handler = CommentDeletionHandler()
        mock_page = Mock()
        mock_page.wait_for_load_state.return_value = None

        mock_link = Mock()
        mock_link.count.return_value = 1
        mock_link.is_visible.return_value = True
        mock_link.click.return_value = None
        mock_link.first = mock_link

        mock_element = Mock()
        mock_element.locator.return_value = mock_link

        item = {"type": "comment", "element": mock_element}

        result = handler._navigate_to_context(mock_page, item)
        assert result is True
        mock_link.click.assert_called_once()

    def test_navigate_to_context_not_found(self):
        """Test _navigate_to_context returns False when no context link."""
        handler = CommentDeletionHandler()
        mock_page = Mock()

        mock_element = Mock()
        mock_element.locator.return_value.count.return_value = 0

        item = {"type": "comment", "element": mock_element}

        result = handler._navigate_to_context(mock_page, item)
        assert result is False


@pytest.mark.unit
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

    def test_delete_calls_remove_reaction(self):
        """Test delete() delegates to remove_reaction()."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()
        item = {"type": "reaction"}

        with patch.object(
            handler, "remove_reaction", return_value=(True, "Success")
        ) as mock_remove:
            success, message = handler.delete(mock_page, item)
            assert success is True
            assert message == "Success"
            mock_remove.assert_called_once_with(mock_page, item)

    def test_remove_reaction_success(self):
        """Test remove_reaction successfully removes reaction."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()
        mock_page.wait_for_timeout.return_value = None

        mock_unlike_link = Mock()
        mock_unlike_link.is_visible.side_effect = [True, False]  # Visible then disappears
        mock_unlike_link.click.return_value = None

        item = {"type": "reaction", "item_id": "123"}

        with patch.object(handler, "_find_unlike_link", return_value=mock_unlike_link):
            success, message = handler.remove_reaction(mock_page, item)
            assert success is True
            assert "success" in message.lower()
            mock_unlike_link.click.assert_called_once()

    def test_remove_reaction_link_disappears(self):
        """Test remove_reaction when link disappears after click."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()
        mock_page.wait_for_timeout.return_value = None

        mock_unlike_link = Mock()
        mock_unlike_link.is_visible.return_value = False  # Already gone
        mock_unlike_link.click.return_value = None

        item = {"type": "reaction", "item_id": "123"}

        with patch.object(handler, "_find_unlike_link", return_value=mock_unlike_link):
            success, message = handler.remove_reaction(mock_page, item)
            assert success is True

    def test_remove_reaction_network_idle(self):
        """Test remove_reaction waits for network idle."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()
        mock_page.wait_for_timeout.return_value = None
        mock_page.wait_for_load_state.return_value = None

        mock_unlike_link = Mock()
        # Still visible after first check, disappears after network idle
        mock_unlike_link.is_visible.side_effect = [True, True, False]
        mock_unlike_link.click.return_value = None

        item = {"type": "reaction", "item_id": "123"}

        with patch.object(handler, "_find_unlike_link", return_value=mock_unlike_link):
            success, message = handler.remove_reaction(mock_page, item)
            assert success is True
            mock_page.wait_for_load_state.assert_called_once()

    def test_remove_reaction_link_still_visible(self):
        """Test remove_reaction when link still visible (ambiguous case)."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()
        mock_page.wait_for_timeout.return_value = None
        mock_page.wait_for_load_state.return_value = None

        mock_unlike_link = Mock()
        mock_unlike_link.is_visible.return_value = True  # Still visible
        mock_unlike_link.click.return_value = None

        item = {"type": "reaction", "item_id": "123"}

        with patch.object(handler, "_find_unlike_link", return_value=mock_unlike_link):
            success, message = handler.remove_reaction(mock_page, item)
            assert success is True
            assert "attempted" in message.lower() or "unclear" in message.lower()

    def test_remove_reaction_link_not_found(self):
        """Test remove_reaction when unlike link not found."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()

        item = {"type": "reaction", "item_id": "123"}

        with patch.object(handler, "_find_unlike_link", return_value=None):
            success, message = handler.remove_reaction(mock_page, item)
            assert success is False
            assert "not found" in message.lower()

    def test_remove_reaction_timeout(self):
        """Test remove_reaction handles PlaywrightTimeoutError."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        handler = ReactionRemovalHandler()
        mock_page = Mock()

        mock_unlike_link = Mock()
        mock_unlike_link.click.side_effect = PlaywrightTimeoutError("Timeout")

        item = {"type": "reaction", "item_id": "123"}

        with patch.object(handler, "_find_unlike_link", return_value=mock_unlike_link):
            success, message = handler.remove_reaction(mock_page, item)
            assert success is False
            assert "timeout" in message.lower()

    def test_find_unlike_link_from_item(self):
        """Test _find_unlike_link uses delete_link from item."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()

        mock_unlike_link = Mock()
        mock_unlike_link.is_visible.return_value = True

        item = {"type": "reaction", "delete_link": mock_unlike_link}

        result = handler._find_unlike_link(mock_page, item)
        assert result == mock_unlike_link

    def test_find_unlike_link_in_element(self):
        """Test _find_unlike_link finds link in element."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()

        mock_link = Mock()
        mock_link.count.return_value = 1
        mock_link.is_visible.return_value = True
        mock_link.first = mock_link

        mock_element = Mock()
        mock_element.locator.return_value = mock_link

        item = {"type": "reaction", "element": mock_element}

        result = handler._find_unlike_link(mock_page, item)
        assert result is not None

    def test_find_unlike_link_on_page(self):
        """Test _find_unlike_link finds link on page."""
        handler = ReactionRemovalHandler()
        mock_page = Mock()

        mock_link = Mock()
        mock_link.is_visible.return_value = True
        mock_page.locator.return_value.all.return_value = [mock_link]

        item = {"type": "reaction"}

        result = handler._find_unlike_link(mock_page, item)
        assert result == mock_link


@pytest.mark.unit
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

    def test_extract_items_with_items(self):
        """Test extract_items with items found."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_page = Mock()
        mock_page.wait_for_load_state.return_value = None

        # Mock elements
        mock_element1 = Mock()
        mock_element1.text_content.return_value = "You posted something. November 3, 2020"
        mock_element1.get_attribute.return_value = None
        mock_element1.locator.return_value.count.return_value = 0

        mock_element2 = Mock()
        mock_element2.text_content.return_value = "You commented. 2 years ago"
        mock_element2.get_attribute.return_value = None
        mock_element2.locator.return_value.count.return_value = 0

        mock_locator = Mock()
        mock_locator.all.return_value = [mock_element1, mock_element2]
        mock_page.locator.return_value = mock_locator

        with patch.object(extractor, "_parse_activity_item") as mock_parse:
            mock_parse.side_effect = [
                {
                    "type": "post",
                    "date_string": "November 3, 2020",
                    "date_parsed": datetime(2020, 11, 3),
                    "delete_link": Mock(),
                    "item_id": "1",
                    "element": mock_element1,
                },
                {
                    "type": "comment",
                    "date_string": "2 years ago",
                    "date_parsed": datetime(2019, 1, 1),
                    "delete_link": Mock(),
                    "item_id": "2",
                    "element": mock_element2,
                },
            ]
            items = extractor.extract_items(mock_page)
            assert len(items) == 2

    def test_extract_items_date_filtering(self):
        """Test extract_items filters items by target_date."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_page = Mock()
        mock_page.wait_for_load_state.return_value = None

        mock_element = Mock()
        mock_element.text_content.return_value = "You posted something. November 3, 2022"
        mock_element.get_attribute.return_value = None
        mock_element.locator.return_value.count.return_value = 0

        mock_locator = Mock()
        mock_locator.all.return_value = [mock_element]
        mock_page.locator.return_value = mock_locator

        with patch.object(extractor, "_parse_activity_item") as mock_parse:
            mock_parse.return_value = {
                "type": "post",
                "date_string": "November 3, 2022",
                "date_parsed": datetime(2022, 11, 3),  # After target_date
                "delete_link": Mock(),
                "item_id": "1",
                "element": mock_element,
            }
            items = extractor.extract_items(mock_page)
            assert len(items) == 0  # Should be filtered out

    def test_extract_items_unparseable_date(self):
        """Test extract_items includes items with unparseable dates."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_page = Mock()
        mock_page.wait_for_load_state.return_value = None

        mock_element = Mock()
        mock_element.text_content.return_value = "You posted something"
        mock_element.get_attribute.return_value = None
        mock_element.locator.return_value.count.return_value = 0

        mock_locator = Mock()
        mock_locator.all.return_value = [mock_element]
        mock_page.locator.return_value = mock_locator

        with patch.object(extractor, "_parse_activity_item") as mock_parse:
            mock_parse.return_value = {
                "type": "post",
                "date_string": "unknown date",
                "date_parsed": None,  # Unparseable
                "delete_link": Mock(),
                "item_id": "1",
                "element": mock_element,
            }
            items = extractor.extract_items(mock_page)
            assert len(items) == 1  # Should be included

    def test_extract_items_multiple_selectors(self):
        """Test extract_items tries multiple selectors."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_page = Mock()
        mock_page.wait_for_load_state.return_value = None

        # First selector returns empty, second returns elements
        mock_locator1 = Mock()
        mock_locator1.all.return_value = []
        mock_locator2 = Mock()
        mock_locator2.all.return_value = [Mock()]

        mock_page.locator.side_effect = [mock_locator1, mock_locator2]

        with patch.object(extractor, "_parse_activity_item", return_value=None):
            extractor.extract_items(mock_page)
            # Should try multiple selectors
            assert mock_page.locator.call_count >= 2

    def test_parse_activity_item_success(self):
        """Test _parse_activity_item successfully parses item."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        with patch.object(extractor, "_extract_date", return_value="November 3, 2020"):
            with patch.object(
                extractor.date_parser, "parse_facebook_date", return_value=datetime(2020, 11, 3)
            ):
                with patch.object(extractor, "_determine_item_type", return_value="post"):
                    with patch.object(extractor, "_find_delete_link", return_value=Mock()):
                        with patch.object(extractor, "_extract_item_id", return_value="123"):
                            item = extractor._parse_activity_item(mock_element)
                            assert item is not None
                            assert item["type"] == "post"
                            assert item["date_string"] == "November 3, 2020"
                            assert item["date_parsed"] == datetime(2020, 11, 3)
                            assert item["item_id"] == "123"

    def test_parse_activity_item_missing_type(self):
        """Test _parse_activity_item returns None when type missing."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        with patch.object(extractor, "_extract_date", return_value="November 3, 2020"):
            with patch.object(
                extractor.date_parser, "parse_facebook_date", return_value=datetime(2020, 11, 3)
            ):
                with patch.object(extractor, "_determine_item_type", return_value=None):
                    item = extractor._parse_activity_item(mock_element)
                    assert item is None

    def test_extract_date_from_abbr_title(self):
        """Test _extract_date from abbr title attribute."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        mock_date_elem = Mock()
        mock_date_elem.count.return_value = 1
        mock_date_elem.get_attribute.return_value = "November 3, 2020"
        mock_date_elem.first = mock_date_elem

        mock_element.locator.return_value = mock_date_elem

        date_string = extractor._extract_date(mock_element)
        assert date_string == "November 3, 2020"

    def test_extract_date_from_text_pattern(self):
        """Test _extract_date from text patterns."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        # Mock locator to return empty for structured selectors
        mock_date_elem = Mock()
        mock_date_elem.count.return_value = 0
        mock_element.locator.return_value = mock_date_elem

        # Mock text_content to contain date pattern
        mock_element.text_content.return_value = "You posted something on November 3, 2020"

        date_string = extractor._extract_date(mock_element)
        assert date_string is not None
        assert "November" in date_string or "2020" in date_string

    def test_extract_date_not_found(self):
        """Test _extract_date returns None when no date found."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        mock_date_elem = Mock()
        mock_date_elem.count.return_value = 0
        mock_element.locator.return_value = mock_date_elem
        mock_element.text_content.return_value = "No date here"

        date_string = extractor._extract_date(mock_element)
        assert date_string is None

    def test_find_delete_link_various_selectors(self):
        """Test _find_delete_link tries various selectors."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        # First selector fails, second succeeds
        mock_link1 = Mock()
        mock_link1.count.return_value = 0
        mock_link2 = Mock()
        mock_link2.count.return_value = 1
        mock_link2.is_visible.return_value = True
        mock_link2.first = mock_link2

        mock_element.locator.side_effect = [mock_link1, mock_link2]

        result = extractor._find_delete_link(mock_element)
        assert result is not None

    def test_extract_item_id_from_attributes(self):
        """Test _extract_item_id from id and data-id attributes."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        # Test id attribute
        mock_element.get_attribute.side_effect = lambda name: "item123" if name == "id" else None
        item_id = extractor._extract_item_id(mock_element)
        assert item_id == "item123"

        # Test data-id attribute
        mock_element.get_attribute.side_effect = (
            lambda name: "data456" if name == "data-id" else None
        )
        item_id = extractor._extract_item_id(mock_element)
        assert item_id == "data456"

    def test_extract_item_id_from_href(self):
        """Test _extract_item_id from href URL parameter."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        mock_element = Mock()

        # Mock delete link with href
        mock_delete_link = Mock()
        mock_delete_link.get_attribute.return_value = (
            "https://mbasic.facebook.com/delete.php?id=789"
        )
        mock_element.get_attribute.return_value = None
        mock_element.locator.return_value.first.count.return_value = 1
        mock_element.locator.return_value.first.is_visible.return_value = True

        with patch.object(extractor, "_find_delete_link", return_value=mock_delete_link):
            item_id = extractor._extract_item_id(mock_element)
            assert item_id == "789"

    def test_is_deletable_reaction(self):
        """Test _is_deletable for reaction (no delete link needed)."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        item = {"type": "reaction"}  # No delete_link
        assert extractor._is_deletable(item) is True

    def test_is_deletable_requires_link(self):
        """Test _is_deletable requires delete link for non-reactions."""
        extractor = ItemExtractor(datetime(2021, 1, 1))
        # Post without delete link
        item = {"type": "post"}
        assert extractor._is_deletable(item) is False

        # Post with delete link
        item = {"type": "post", "delete_link": Mock()}
        assert extractor._is_deletable(item) is True

        # No type
        item = {}
        assert extractor._is_deletable(item) is False


@pytest.mark.unit
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

    def test_process_page_with_items(self):
        """Test process_page with items found."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        # Mock items
        mock_item1 = {"type": "post", "date_string": "2020-01-01", "item_id": "1"}
        mock_item2 = {"type": "comment", "date_string": "2020-01-02", "item_id": "2"}

        # Mock handler
        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        mock_handler.delete.return_value = (True, "Success")
        engine.handlers = [mock_handler]

        # Mock item extractor
        with patch.object(
            engine.item_extractor, "extract_items", return_value=[mock_item1, mock_item2]
        ):
            # Mock rate limiter and block manager
            engine.rate_limiter.wait_before_action = Mock(return_value=True)
            engine.block_manager.should_continue = Mock(return_value=True)
            engine.error_detector.check_for_errors = Mock(return_value=(False, None))

            # Mock state manager
            engine.state_manager.get_state = Mock(
                return_value={
                    "total_deleted": 0,
                    "deleted_today": 0,
                    "errors_encountered": 0,
                    "block_detected": False,
                    "block_count": 0,
                }
            )
            engine.state_manager.save_state = Mock()

            # Mock delete_item to return success
            with patch.object(engine, "delete_item", return_value=(True, "Success")):
                stats = engine.process_page()

                assert stats["deleted"] == 2
                assert stats["failed"] == 0
                assert len(stats["errors"]) == 0

    def test_process_page_block_detected(self):
        """Test process_page stops when block detected."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_item = {"type": "post", "date_string": "2020-01-01", "item_id": "1"}

        with patch.object(engine.item_extractor, "extract_items", return_value=[mock_item]):
            engine.block_manager.should_continue = Mock(return_value=False)

            stats = engine.process_page()

            assert stats["deleted"] == 0
            assert len(stats["errors"]) == 1
            assert "block" in stats["errors"][0]["error"].lower()

    def test_process_page_rate_limit_exceeded(self):
        """Test process_page stops when rate limit exceeded."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_item = {"type": "post", "date_string": "2020-01-01", "item_id": "1"}

        with patch.object(engine.item_extractor, "extract_items", return_value=[mock_item]):
            engine.block_manager.should_continue = Mock(return_value=True)
            engine.rate_limiter.wait_before_action = Mock(return_value=False)

            stats = engine.process_page()

            assert stats["deleted"] == 0
            assert len(stats["errors"]) == 1
            assert "rate limit" in stats["errors"][0]["error"].lower()

    def test_process_page_error_detection(self):
        """Test process_page detects errors after deletion."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_item = {"type": "post", "date_string": "2020-01-01", "item_id": "1"}

        with patch.object(engine.item_extractor, "extract_items", return_value=[mock_item]):
            engine.block_manager.should_continue = Mock(return_value=True)
            engine.rate_limiter.wait_before_action = Mock(return_value=True)
            engine.error_detector.check_for_errors = Mock(return_value=(True, "Action Blocked"))
            engine.block_manager.check_and_handle_block = Mock(return_value=True)
            engine.block_manager.apply_backoff = Mock()

            # Mock state manager
            engine.state_manager.get_state = Mock(
                return_value={
                    "total_deleted": 0,
                    "deleted_today": 0,
                    "errors_encountered": 0,
                    "block_detected": False,
                    "block_count": 0,
                }
            )
            engine.state_manager.save_state = Mock()

            with patch.object(engine, "delete_item", return_value=(True, "Success")):
                stats = engine.process_page()

                assert len(stats["errors"]) == 1
                assert "block" in stats["errors"][0]["error"].lower()
                engine.block_manager.apply_backoff.assert_called_once()

    def test_process_page_failed_deletions(self):
        """Test process_page tracks failed deletions."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_item = {"type": "post", "date_string": "2020-01-01", "item_id": "1"}

        with patch.object(engine.item_extractor, "extract_items", return_value=[mock_item]):
            engine.block_manager.should_continue = Mock(return_value=True)
            engine.rate_limiter.wait_before_action = Mock(return_value=True)
            engine.error_detector.check_for_errors = Mock(return_value=(False, None))

            # Mock state manager
            engine.state_manager.get_state = Mock(
                return_value={
                    "total_deleted": 0,
                    "deleted_today": 0,
                    "errors_encountered": 0,
                    "block_detected": False,
                    "block_count": 0,
                }
            )
            engine.state_manager.save_state = Mock()

            with patch.object(engine, "delete_item", return_value=(False, "Deletion failed")):
                stats = engine.process_page()

                assert stats["deleted"] == 0
                assert stats["failed"] == 1
                assert len(stats["errors"]) == 1
                assert "failed" in stats["errors"][0]["error"].lower()

    def test_delete_item_retry_logic(self):
        """Test delete_item retries on transient errors."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        # First two calls fail with timeout, third succeeds
        mock_handler.delete.side_effect = [
            (False, "Timeout error"),
            (False, "Timeout error"),
            (True, "Success"),
        ]
        engine.handlers = [mock_handler]

        item = {"type": "post"}
        success, message = engine.delete_item(mock_page, item, max_retries=3)

        assert success is True
        assert message == "Success"
        assert mock_handler.delete.call_count == 3

    def test_delete_item_max_retries(self):
        """Test delete_item stops after max retries."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        mock_handler.delete.return_value = (False, "Timeout error")
        engine.handlers = [mock_handler]

        item = {"type": "post"}
        success, message = engine.delete_item(mock_page, item, max_retries=3)

        assert success is False
        assert "retries" in message.lower() or "timeout" in message.lower()
        assert mock_handler.delete.call_count == 3

    def test_delete_item_non_transient_error(self):
        """Test delete_item doesn't retry on non-transient errors."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        mock_handler.delete.return_value = (False, "Permission denied")
        engine.handlers = [mock_handler]

        item = {"type": "post"}
        success, message = engine.delete_item(mock_page, item, max_retries=3)

        assert success is False
        assert "permission" in message.lower()
        assert mock_handler.delete.call_count == 1  # No retry

    def test_delete_item_playwright_timeout(self):
        """Test delete_item handles PlaywrightTimeoutError."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        mock_handler.delete.side_effect = PlaywrightTimeoutError("Timeout")
        engine.handlers = [mock_handler]

        item = {"type": "post"}
        success, message = engine.delete_item(mock_page, item, max_retries=2)

        assert success is False
        assert "timeout" in message.lower()
        assert mock_handler.delete.call_count == 2  # Retried once

    def test_delete_item_handler_not_found(self):
        """Test delete_item when no handler matches."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        # Empty handlers list
        engine.handlers = []

        item = {"type": "unknown"}
        success, message = engine.delete_item(mock_page, item)

        assert success is False
        assert "no handler" in message.lower()

    def test_delete_item_exception_handling(self):
        """Test delete_item handles general exceptions."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        mock_handler = Mock()
        mock_handler.can_handle.return_value = True
        mock_handler.delete.side_effect = ValueError("Unexpected error")
        engine.handlers = [mock_handler]

        item = {"type": "post"}
        success, message = engine.delete_item(mock_page, item)

        assert success is False
        assert "unexpected" in message.lower()
        assert mock_handler.delete.call_count == 1  # No retry for non-transient errors

    def test_select_handler_exception_in_can_handle(self):
        """Test _select_handler continues when handler raises exception."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        # First handler raises exception, second succeeds
        mock_handler1 = Mock()
        mock_handler1.can_handle.side_effect = ValueError("Error in can_handle")
        mock_handler2 = Mock()
        mock_handler2.can_handle.return_value = True
        engine.handlers = [mock_handler1, mock_handler2]

        item = {"type": "post"}
        handler = engine._select_handler(item)

        assert handler == mock_handler2
        assert mock_handler1.can_handle.called
        assert mock_handler2.can_handle.called

    def test_update_progress_state(self):
        """Test _update_progress_state updates state correctly."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        # Mock state manager
        mock_state = {
            "total_deleted": 10,
            "deleted_today": 5,
            "errors_encountered": 2,
            "block_detected": False,
            "block_count": 0,
        }
        engine.state_manager.get_state = Mock(return_value=mock_state)
        engine.state_manager.save_state = Mock()
        engine.block_manager.block_detected = False
        engine.block_manager.block_count = 0

        stats = {"deleted": 3, "failed": 1, "errors": [{"error": "test"}]}
        engine._update_progress_state(stats)

        # Verify state was updated
        engine.state_manager.save_state.assert_called_once()
        saved_state = engine.state_manager.save_state.call_args[0][0]
        assert saved_state["total_deleted"] == 13  # 10 + 3
        assert saved_state["deleted_today"] == 8  # 5 + 3
        assert saved_state["errors_encountered"] == 3  # 2 + 1

    def test_update_progress_state_failure(self):
        """Test _update_progress_state doesn't fail operation on error."""
        mock_page = Mock()
        engine = DeletionEngine(mock_page)

        # Mock state manager to raise exception
        engine.state_manager.get_state = Mock(side_effect=ValueError("State error"))
        engine.state_manager.save_state = Mock()

        stats = {"deleted": 1, "failed": 0, "errors": []}
        # Should not raise exception
        engine._update_progress_state(stats)

    def test_init_with_custom_components(self):
        """Test DeletionEngine initialization with custom components."""
        mock_page = Mock()
        mock_rate_limiter = Mock()
        mock_error_detector = Mock()
        mock_block_manager = Mock()
        mock_state_manager = Mock()
        mock_handlers = [Mock()]

        engine = DeletionEngine(
            mock_page,
            target_date=datetime(2020, 1, 1),
            handlers=mock_handlers,
            rate_limiter=mock_rate_limiter,
            error_detector=mock_error_detector,
            block_manager=mock_block_manager,
            state_manager=mock_state_manager,
        )

        assert engine.page == mock_page
        assert engine.target_date == datetime(2020, 1, 1)
        assert engine.handlers == mock_handlers
        assert engine.rate_limiter == mock_rate_limiter
        assert engine.error_detector == mock_error_detector
        assert engine.block_manager == mock_block_manager
        assert engine.state_manager == mock_state_manager

    def test_init_with_block_detected(self):
        """Test DeletionEngine applies backoff when block detected."""
        mock_page = Mock()
        mock_block_manager = Mock()
        mock_block_manager.block_detected = True
        mock_rate_limiter = Mock()

        DeletionEngine(mock_page, block_manager=mock_block_manager, rate_limiter=mock_rate_limiter)

        # Verify backoff was applied
        mock_block_manager.apply_backoff.assert_called_once_with(mock_rate_limiter)


@pytest.mark.unit
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
