"""
Unit tests for traversal engine modules.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.traversal.date_parser import DateParser
from src.traversal.pagination import PaginationHandler
from src.traversal.traversal_engine import TraversalEngine
from src.traversal.url_builder import URLBuilder


class TestURLBuilder:
    """Test URLBuilder class."""

    def test_init_valid_username(self):
        """Test initialization with valid username."""
        builder = URLBuilder("testuser")
        assert builder.username == "testuser"
        assert "testuser" in builder.base_url

    def test_init_empty_username(self):
        """Test initialization with empty username raises error."""
        with pytest.raises(ValueError) as exc_info:
            URLBuilder("")
        assert "empty" in str(exc_info.value).lower()

    def test_build_year_url(self):
        """Test building URL for specific year."""
        builder = URLBuilder("testuser")
        url = builder.build_year_url(2020)

        assert "mbasic.facebook.com" in url
        assert "testuser" in url
        assert "allactivity" in url
        assert "year_2020" in url

    def test_build_month_url(self):
        """Test building URL with year and month."""
        builder = URLBuilder("testuser")
        url = builder.build_month_url(2020, 11)

        assert "year_2020" in url
        assert "month=11" in url

    def test_build_category_url(self):
        """Test building URL with category filter."""
        builder = URLBuilder("testuser")
        url = builder.build_category_url(2020, "cluster_11")

        assert "year_2020" in url
        assert "cluster_11" in url

    def test_build_activity_log_url_all_filters(self):
        """Test building URL with all filters."""
        builder = URLBuilder("testuser")
        url = builder.build_activity_log_url(2020, month=11, category="cluster_11")

        assert "year_2020" in url
        assert "month=11" in url
        assert "cluster_11" in url

    def test_validate_year_too_old(self):
        """Test year validation with year before 2004."""
        builder = URLBuilder("testuser")
        with pytest.raises(ValueError) as exc_info:
            builder.build_year_url(2000)
        assert "2004" in str(exc_info.value)

    def test_validate_year_too_new(self):
        """Test year validation with year after 2030."""
        builder = URLBuilder("testuser")
        with pytest.raises(ValueError) as exc_info:
            builder.build_year_url(2031)
        assert "2030" in str(exc_info.value)

    def test_validate_month_too_low(self):
        """Test month validation with month < 1."""
        builder = URLBuilder("testuser")
        with pytest.raises(ValueError) as exc_info:
            builder.build_month_url(2020, 0)
        assert "1" in str(exc_info.value)

    def test_validate_month_too_high(self):
        """Test month validation with month > 12."""
        builder = URLBuilder("testuser")
        with pytest.raises(ValueError) as exc_info:
            builder.build_month_url(2020, 13)
        assert "12" in str(exc_info.value)


class TestDateParser:
    """Test DateParser class."""

    def test_parse_today(self):
        """Test parsing 'today'."""
        parser = DateParser()
        result = parser.parse_facebook_date("today")

        assert result is not None
        assert result.date() == datetime.now().date()

    def test_parse_yesterday(self):
        """Test parsing 'yesterday'."""
        parser = DateParser()
        result = parser.parse_facebook_date("yesterday")

        assert result is not None
        yesterday = datetime.now() - timedelta(days=1)
        assert result.date() == yesterday.date()

    def test_parse_relative_years_ago(self):
        """Test parsing '2 years ago'."""
        parser = DateParser()
        reference = datetime(2024, 1, 1)
        result = parser.parse_facebook_date("2 years ago", reference)

        assert result is not None
        # Should be approximately 2 years before reference
        assert result.year <= 2022

    def test_parse_relative_months_ago(self):
        """Test parsing '3 months ago'."""
        parser = DateParser()
        reference = datetime(2024, 6, 1)
        result = parser.parse_facebook_date("3 months ago", reference)

        assert result is not None
        # Should be approximately 3 months before reference
        assert result.month <= 3 or result.year < 2024

    def test_parse_absolute_date_with_year(self):
        """Test parsing absolute date with year."""
        parser = DateParser()
        result = parser.parse_facebook_date("November 3, 2020")

        assert result is not None
        assert result.year == 2020
        assert result.month == 11
        assert result.day == 3

    def test_parse_absolute_date_without_year(self):
        """Test parsing absolute date without year."""
        parser = DateParser()
        reference = datetime(2024, 6, 1)
        result = parser.parse_facebook_date("November 3", reference)

        assert result is not None
        assert result.month == 11
        assert result.day == 3
        # Should be in past relative to reference
        assert result.year <= 2024

    def test_parse_date_with_time(self):
        """Test parsing date with time component."""
        parser = DateParser()
        result = parser.parse_facebook_date("November 3, 2020 at 4:00pm")

        assert result is not None
        assert result.year == 2020
        assert result.month == 11
        assert result.day == 3
        assert result.hour == 16  # 4:00 PM = 16:00

    def test_parse_relative_with_time(self):
        """Test parsing relative date with time."""
        parser = DateParser()
        reference = datetime(2024, 1, 1, 12, 0, 0)
        result = parser.parse_facebook_date("2 years ago at 3:30pm", reference)

        assert result is not None
        assert result.hour == 15  # 3:30 PM = 15:30
        assert result.minute == 30

    def test_parse_invalid_date(self):
        """Test parsing invalid date string."""
        parser = DateParser()
        result = parser.parse_facebook_date("not a date")

        assert result is None

    def test_is_before_target_true(self):
        """Test is_before_target with date before target."""
        parser = DateParser()
        target = datetime(2021, 1, 1)

        assert parser.is_before_target("November 3, 2020", target) is True
        assert parser.is_before_target("2 years ago", datetime(2024, 1, 1)) is True

    def test_is_before_target_false(self):
        """Test is_before_target with date after target."""
        parser = DateParser()
        target = datetime(2020, 1, 1)

        assert parser.is_before_target("November 3, 2021", target) is False


class TestPaginationHandler:
    """Test PaginationHandler class."""

    def test_has_more_pages_found(self):
        """Test has_more_pages when link exists."""
        handler = PaginationHandler()
        mock_page = Mock()

        # Mock locator that finds a link
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_locator.first.is_visible.return_value = True
        mock_page.locator.return_value = mock_locator

        assert handler.has_more_pages(mock_page) is True

    def test_has_more_pages_not_found(self):
        """Test has_more_pages when link doesn't exist."""
        handler = PaginationHandler()
        mock_page = Mock()

        # Mock locator that finds nothing
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        assert handler.has_more_pages(mock_page) is False

    def test_click_see_more_success(self):
        """Test successful click_see_more."""
        handler = PaginationHandler()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/test"

        # Mock locator
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_link = Mock()
        mock_link.is_visible.return_value = True
        mock_link.click.return_value = None
        mock_locator.first = mock_link
        mock_page.locator.return_value = mock_locator

        # Mock wait_for_page_load
        with patch.object(handler, "wait_for_page_load", return_value=None):
            result = handler.click_see_more(mock_page)
            assert result is True
            mock_link.click.assert_called_once()

    def test_click_see_more_not_found(self):
        """Test click_see_more when link not found."""
        handler = PaginationHandler()
        mock_page = Mock()

        # Mock locator that finds nothing
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        result = handler.click_see_more(mock_page)
        assert result is False

    def test_wait_for_page_load(self):
        """Test wait_for_page_load."""
        handler = PaginationHandler()
        mock_page = Mock()

        # Should not raise exception
        handler.wait_for_page_load(mock_page)
        mock_page.wait_for_load_state.assert_called()


class TestTraversalEngine:
    """Test TraversalEngine class."""

    def test_init(self):
        """Test TraversalEngine initialization."""
        mock_page = Mock()
        engine = TraversalEngine(mock_page, "testuser", target_year=2021, start_year=2020)

        assert engine.username == "testuser"
        assert engine.target_year == 2021
        assert engine.start_year == 2020
        assert engine.url_builder is not None
        assert engine.pagination_handler is not None
        assert engine.date_parser is not None

    def test_traverse_page_builds_url(self):
        """Test traverse_page builds correct URL."""
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.url = "https://mbasic.facebook.com/test"
        mock_page.wait_for_load_state.return_value = None

        engine = TraversalEngine(mock_page, "testuser")

        # Mock pagination handler
        engine.pagination_handler.has_more_pages = Mock(return_value=False)
        engine.pagination_handler.wait_for_page_load = Mock()

        # Get first item from generator
        page_info = next(engine.traverse_page(2020, month=11), None)

        assert page_info is not None
        assert page_info["year"] == 2020
        assert page_info["month"] == 11
        assert page_info["is_pagination"] is False
        mock_page.goto.assert_called_once()

    def test_traverse_page_handles_pagination(self):
        """Test traverse_page handles pagination."""
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.url = "https://mbasic.facebook.com/test"

        engine = TraversalEngine(mock_page, "testuser")

        # Mock pagination: first call returns True, second returns False
        engine.pagination_handler.has_more_pages = Mock(side_effect=[True, False])
        engine.pagination_handler.click_see_more = Mock(return_value=True)
        engine.pagination_handler.wait_for_page_load = Mock()

        # Collect all pages
        pages = list(engine.traverse_page(2020, month=11))

        assert len(pages) == 2  # Initial page + one paginated page
        assert pages[0]["is_pagination"] is False
        assert pages[1]["is_pagination"] is True
        assert pages[1]["page_number"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
