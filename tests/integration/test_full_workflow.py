"""
Integration tests for full cleanup workflow.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.auth.browser_manager import BrowserManager
from src.deletion.deletion_engine import DeletionEngine
from src.traversal.traversal_engine import TraversalEngine
from src.utils.state_manager import StateManager
from src.utils.statistics import StatisticsReporter


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete cleanup workflow end-to-end with mocked components."""

    @pytest.fixture
    def mock_browser_components(self):
        """Create mock browser, context, and page."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        return mock_browser, mock_context, mock_page

    @pytest.fixture
    def mock_browser_manager(self, mock_browser_components):
        """Create mocked BrowserManager."""
        mock_browser, mock_context, mock_page = mock_browser_components

        with patch.object(BrowserManager, "create_authenticated_browser") as mock_create:
            mock_create.return_value = (mock_browser, mock_context, mock_page)
            manager = BrowserManager()
            yield manager, mock_browser, mock_context, mock_page

    def test_complete_workflow_mocked_browser(self, tmp_path, mock_browser_manager):
        """Test complete workflow with mocked browser."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        # Initialize components
        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()
        traversal_engine = TraversalEngine(page=mock_page, username="testuser")
        deletion_engine = DeletionEngine(page=mock_page)

        # Verify all components are initialized
        assert state_manager is not None
        assert stats_reporter is not None
        assert traversal_engine is not None
        assert deletion_engine is not None

        # Verify workflow components have required attributes
        assert deletion_engine.rate_limiter is not None
        assert deletion_engine.error_detector is not None
        assert deletion_engine.block_manager is not None

    def test_workflow_executes_without_errors(self, tmp_path, mock_browser_manager):
        """Test workflow executes without errors."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()
        traversal_engine = TraversalEngine(page=mock_page, username="testuser")
        deletion_engine = DeletionEngine(page=mock_page)

        # Mock traversal to yield one page
        def mock_traverse():
            yield {
                "year": 2020,
                "month": 11,
                "page_number": 1,
                "page": mock_page,
            }

        traversal_engine.traverse_years = mock_traverse

        # Mock deletion engine to return success stats
        deletion_engine.process_page = Mock(
            return_value={"deleted": 5, "failed": 0, "skipped": 0, "errors": []}
        )

        # Execute workflow
        for page_info in traversal_engine.traverse_years():
            page_stats = deletion_engine.process_page(page_info["page"])
            stats_reporter.update_from_page_stats(page_stats)

            # Update state
            state_manager.update_state(
                current_year=page_info["year"],
                current_month=page_info["month"],
                total_deleted=stats_reporter.stats["total_deleted"],
            )

        # Verify workflow completed
        assert stats_reporter.stats["total_deleted"] == 5
        assert stats_reporter.stats["total_failed"] == 0

    def test_state_saved_during_execution(self, tmp_path, mock_browser_manager):
        """Test state is saved during execution."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()

        # Execute workflow and save state
        stats_reporter.update_from_page_stats(
            {"deleted": 10, "failed": 1, "skipped": 0, "errors": []}
        )
        state_manager.update_state(
            current_year=2020,
            current_month=10,
            total_deleted=stats_reporter.stats["total_deleted"],
        )

        # Verify state was saved
        assert progress_path.exists()

        # Load and verify
        loaded_state = state_manager.load_state()
        assert loaded_state is not None
        assert loaded_state["current_year"] == 2020
        assert loaded_state["current_month"] == 10
        assert loaded_state["total_deleted"] == 10

    def test_statistics_collected(self, tmp_path, mock_browser_manager):
        """Test statistics are collected."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager

        stats_reporter = StatisticsReporter()

        # Process multiple pages
        page_stats1 = {"deleted": 5, "failed": 0, "skipped": 1, "errors": []}
        page_stats2 = {"deleted": 3, "failed": 1, "skipped": 0, "errors": [{"error": "test error"}]}

        stats_reporter.update_from_page_stats(page_stats1)
        stats_reporter.update_from_page_stats(page_stats2)

        # Verify statistics aggregated
        assert stats_reporter.stats["total_deleted"] == 8
        assert stats_reporter.stats["total_failed"] == 1
        assert stats_reporter.stats["total_skipped"] == 1
        assert stats_reporter.stats["errors_encountered"] == 1

    def test_workflow_multiple_pages(self, tmp_path, mock_browser_manager):
        """Test workflow with multiple pages."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()
        traversal_engine = TraversalEngine(page=mock_page, username="testuser")
        deletion_engine = DeletionEngine(page=mock_page)

        # Mock traversal to yield multiple pages
        pages_data = [
            {"year": 2020, "month": 12, "page_number": 1},
            {"year": 2020, "month": 11, "page_number": 1},
            {"year": 2019, "month": 12, "page_number": 1},
        ]

        def mock_traverse():
            for page_data in pages_data:
                yield {**page_data, "page": mock_page}

        traversal_engine.traverse_years = mock_traverse

        # Mock deletion engine with different stats for each page
        deletion_stats = [
            {"deleted": 5, "failed": 0, "skipped": 0, "errors": []},
            {"deleted": 3, "failed": 1, "skipped": 1, "errors": []},
            {"deleted": 2, "failed": 0, "skipped": 0, "errors": []},
        ]
        deletion_engine.process_page = Mock(side_effect=deletion_stats)

        # Execute workflow
        pages_processed = 0
        for page_info in traversal_engine.traverse_years():
            page_stats = deletion_engine.process_page(page_info["page"])
            stats_reporter.update_from_page_stats(page_stats)
            state_manager.update_state(
                current_year=page_info["year"],
                current_month=page_info["month"],
                total_deleted=stats_reporter.stats["total_deleted"],
            )
            pages_processed += 1

        # Verify all pages processed
        assert pages_processed == 3
        assert stats_reporter.stats["total_deleted"] == 10  # 5 + 3 + 2
        assert stats_reporter.stats["total_failed"] == 1
        assert stats_reporter.stats["total_skipped"] == 1

        # Verify state reflects last processed page
        final_state = state_manager.get_state()
        assert final_state["current_year"] == 2019
        assert final_state["current_month"] == 12

    def test_workflow_statistics_aggregate_across_pages(self, tmp_path, mock_browser_manager):
        """Test statistics aggregate correctly across pages."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager

        stats_reporter = StatisticsReporter()

        # Simulate processing multiple pages with various stats
        page_stats_list = [
            {"deleted": 10, "failed": 0, "skipped": 2, "errors": []},
            {"deleted": 5, "failed": 1, "skipped": 0, "errors": [{"error": "err1"}]},
            {
                "deleted": 7,
                "failed": 2,
                "skipped": 1,
                "errors": [{"error": "err2"}, {"error": "err3"}],
            },
        ]

        for page_stats in page_stats_list:
            stats_reporter.update_from_page_stats(page_stats)

        # Verify aggregation
        assert stats_reporter.stats["total_deleted"] == 22  # 10 + 5 + 7
        assert stats_reporter.stats["total_failed"] == 3  # 0 + 1 + 2
        assert stats_reporter.stats["total_skipped"] == 3  # 2 + 0 + 1
        assert stats_reporter.stats["errors_encountered"] == 3  # Count of all errors

    def test_workflow_with_errors_and_recovery(self, tmp_path, mock_browser_manager):
        """Test workflow with errors and recovery."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()
        traversal_engine = TraversalEngine(page=mock_page, username="testuser")
        deletion_engine = DeletionEngine(page=mock_page)

        # Mock traversal
        def mock_traverse():
            yield {"year": 2020, "month": 10, "page_number": 1, "page": mock_page}

        traversal_engine.traverse_years = mock_traverse

        # Mock deletion engine to return error stats
        deletion_engine.process_page = Mock(
            return_value={
                "deleted": 3,
                "failed": 2,
                "skipped": 1,
                "errors": [
                    {"error": "Transient error", "item": "item1"},
                    {"error": "Another error", "item": "item2"},
                ],
            }
        )

        # Execute workflow
        for page_info in traversal_engine.traverse_years():
            page_stats = deletion_engine.process_page(page_info["page"])
            stats_reporter.update_from_page_stats(page_stats)

            # Update state with errors
            state_manager.update_state(
                current_year=page_info["year"],
                current_month=page_info["month"],
                total_deleted=stats_reporter.stats["total_deleted"],
                errors_encountered=stats_reporter.stats["errors_encountered"],
            )

        # Verify errors are tracked
        assert stats_reporter.stats["total_deleted"] == 3
        assert stats_reporter.stats["total_failed"] == 2
        assert stats_reporter.stats["errors_encountered"] == 2

        # Verify state includes error information
        state = state_manager.get_state()
        assert state["errors_encountered"] == 2

    def test_workflow_state_updates_correctly(self, tmp_path, mock_browser_manager):
        """Test state updates correctly for each page."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()
        traversal_engine = TraversalEngine(page=mock_page, username="testuser")
        deletion_engine = DeletionEngine(page=mock_page)

        # Mock traversal with multiple pages
        pages_data = [
            {"year": 2020, "month": 12, "page_number": 1},
            {"year": 2020, "month": 11, "page_number": 1},
        ]

        def mock_traverse():
            for page_data in pages_data:
                yield {**page_data, "page": mock_page}

        traversal_engine.traverse_years = mock_traverse

        deletion_engine.process_page = Mock(
            return_value={"deleted": 5, "failed": 0, "skipped": 0, "errors": []}
        )

        # Process pages and verify state updates
        for idx, page_info in enumerate(traversal_engine.traverse_years()):
            page_stats = deletion_engine.process_page(page_info["page"])
            stats_reporter.update_from_page_stats(page_stats)

            state_manager.update_state(
                current_year=page_info["year"],
                current_month=page_info["month"],
                total_deleted=stats_reporter.stats["total_deleted"],
            )

            # Verify state after each page
            state = state_manager.get_state()
            assert state["current_year"] == page_info["year"]
            assert state["current_month"] == page_info["month"]
            assert state["total_deleted"] == 5 * (idx + 1)

    def test_statistics_updated_from_state_on_resume(self, tmp_path, mock_browser_manager):
        """Test stats are updated from state on resume."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager
        progress_path = tmp_path / "progress.json"

        # Create initial state with statistics
        state_manager = StateManager(progress_path)
        initial_state = state_manager.get_state()
        initial_state["total_deleted"] = 100
        initial_state["errors_encountered"] = 5
        state_manager.save_state(initial_state)

        # Create new stats reporter and load from state
        stats_reporter = StatisticsReporter()
        loaded_state = state_manager.load_state()
        stats_reporter.update_from_state(loaded_state)

        # Verify statistics loaded from state
        assert stats_reporter.stats["total_deleted"] == 100
        assert stats_reporter.stats["errors_encountered"] == 5

    def test_final_statistics_report_generated(self, tmp_path, mock_browser_manager):
        """Test final statistics report is generated correctly."""
        manager, mock_browser, mock_context, mock_page = mock_browser_manager

        stats_reporter = StatisticsReporter()

        # Update stats
        stats_reporter.update_from_page_stats(
            {"deleted": 50, "failed": 3, "skipped": 2, "errors": []}
        )

        # Generate report
        report = stats_reporter.generate_report()

        # Verify report contains key information
        assert "Facebook Cleanup Report" in report
        assert "50" in report  # total_deleted
        assert "3" in report  # total_failed
        assert "Statistics:" in report
        assert "Total Deleted" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
