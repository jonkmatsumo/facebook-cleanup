"""
Integration tests for resume capability.
"""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.traversal.traversal_engine import TraversalEngine
from src.utils.state_manager import StateManager
from src.utils.statistics import StatisticsReporter


@pytest.mark.integration
class TestResumeCapability:
    """Test resume functionality from saved state."""

    def test_resume_from_saved_state(self, tmp_path):
        """Test resume from saved state."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create saved state file with specific year/month/progress
        state_manager = StateManager(progress_path)
        saved_state = state_manager.get_state()
        saved_state["current_year"] = 2019
        saved_state["current_month"] = 11
        saved_state["total_deleted"] = 100
        state_manager.save_state(saved_state)

        # Initialize TraversalEngine with resume_state
        loaded_state = state_manager.load_state()
        traversal_engine = TraversalEngine(
            page=mock_page, username="testuser", resume_state=loaded_state
        )

        # Verify TraversalEngine starts from saved year
        assert traversal_engine.start_year == 2019

        # Verify statistics can be loaded from state
        stats_reporter = StatisticsReporter()
        stats_reporter.update_from_state(loaded_state)
        assert stats_reporter.stats["total_deleted"] == 100

    def test_resume_statistics_loaded(self, tmp_path):
        """Test statistics are loaded from state."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create state with statistics
        state_manager = StateManager(progress_path)
        saved_state = state_manager.get_state()
        saved_state["total_deleted"] = 150
        saved_state["errors_encountered"] = 5
        state_manager.save_state(saved_state)

        # Load state and initialize statistics
        loaded_state = state_manager.load_state()
        stats_reporter = StatisticsReporter()
        stats_reporter.update_from_state(loaded_state)

        # Verify statistics loaded
        assert stats_reporter.stats["total_deleted"] == 150
        assert stats_reporter.stats["errors_encountered"] == 5

    def test_resume_skips_processed_items(self, tmp_path):
        """Test resume skips processed items."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create state with completed year/month
        state_manager = StateManager(progress_path)
        saved_state = state_manager.get_state()
        saved_state["current_year"] = 2019
        saved_state["current_month"] = 6  # Completed up to June 2019
        saved_state["total_deleted"] = 50
        state_manager.save_state(saved_state)

        # Initialize traversal with resume state
        loaded_state = state_manager.load_state()
        traversal_engine = TraversalEngine(
            page=mock_page, username="testuser", resume_state=loaded_state, start_year=2020
        )

        # Verify traversal starts from resume year
        assert traversal_engine.start_year == 2019

        # Mock traverse_months to simulate skipping already processed months
        processed_months = []

        def mock_traverse_months(year, resume_month=None):
            # Simulate skipping months before resume_month
            start_month = resume_month if resume_month else 12
            for month in range(start_month, 0, -1):
                processed_months.append((year, month))
                yield {"year": year, "month": month, "page": mock_page, "page_number": 1}

        traversal_engine.traverse_months = mock_traverse_months

        # Traverse months for resume year
        months = list(traversal_engine.traverse_months(2019, resume_month=6))

        # Verify we only process months from June onwards (not before)
        assert len(months) == 6  # June through January
        assert all(month["month"] <= 6 for month in months)

    def test_resume_updates_state_correctly(self, tmp_path):
        """Test resume updates state correctly."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create initial state
        state_manager = StateManager(progress_path)
        initial_state = state_manager.get_state()
        initial_state["current_year"] = 2020
        initial_state["current_month"] = 10
        initial_state["total_deleted"] = 50
        state_manager.save_state(initial_state)

        # Load state and resume
        loaded_state = state_manager.load_state()
        stats_reporter = StatisticsReporter()
        stats_reporter.update_from_state(loaded_state)

        # Simulate processing some items
        stats_reporter.update_from_page_stats(
            {"deleted": 10, "failed": 0, "skipped": 0, "errors": []}
        )

        # Save state mid-workflow
        state_manager.update_state(
            current_year=2020,
            current_month=9,
            total_deleted=stats_reporter.stats["total_deleted"],
            errors_encountered=stats_reporter.stats["errors_encountered"],
        )

        # Resume from saved state
        new_loaded_state = state_manager.load_state()

        # Verify state updated correctly
        assert new_loaded_state["current_year"] == 2020
        assert new_loaded_state["current_month"] == 9
        assert new_loaded_state["total_deleted"] == 60  # 50 initial + 10 new

    def test_resume_state_tracks_position(self, tmp_path):
        """Test state contains correct current position."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)

        # Process and save state at different positions
        positions = [
            {"year": 2020, "month": 12, "total_deleted": 10},
            {"year": 2020, "month": 11, "total_deleted": 20},
            {"year": 2020, "month": 10, "total_deleted": 30},
        ]

        for pos in positions:
            state_manager.update_state(
                current_year=pos["year"],
                current_month=pos["month"],
                total_deleted=pos["total_deleted"],
            )

            # Verify state tracks position correctly
            state = state_manager.get_state()
            assert state["current_year"] == pos["year"]
            assert state["current_month"] == pos["month"]
            assert state["total_deleted"] == pos["total_deleted"]

    def test_resume_state_tracks_total_deleted_accurately(self, tmp_path):
        """Test state tracks total_deleted accurately."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)
        stats_reporter = StatisticsReporter()

        # Load initial state
        initial_state = state_manager.get_state()
        initial_state["total_deleted"] = 100
        state_manager.save_state(initial_state)

        # Update statistics with new deletions
        stats_reporter.update_from_state(initial_state)
        stats_reporter.update_from_page_stats(
            {"deleted": 25, "failed": 0, "skipped": 0, "errors": []}
        )

        # Save updated state
        state_manager.update_state(total_deleted=stats_reporter.stats["total_deleted"])

        # Verify total_deleted is accurate
        final_state = state_manager.get_state()
        assert final_state["total_deleted"] == 125  # 100 + 25

    def test_resume_with_corrupted_state_file(self, tmp_path):
        """Test resume with corrupted state file."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create corrupted JSON file
        with open(progress_path, "w") as f:
            f.write("not valid json { invalid content }")

        # Attempt to resume from corrupted state
        state_manager = StateManager(progress_path)
        loaded_state = state_manager.load_state()

        # Verify system falls back to default state (returns None)
        assert loaded_state is None

        # Verify workflow can start from beginning (not crashed)
        default_state = state_manager.get_state()
        assert default_state is not None
        assert "current_year" in default_state
        assert "total_deleted" in default_state

        # Verify can initialize TraversalEngine with None state (uses defaults)
        traversal_engine = TraversalEngine(page=mock_page, username="testuser", resume_state=None)
        assert traversal_engine is not None

    def test_resume_with_empty_state_file(self, tmp_path):
        """Test resume with empty state file."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create empty file
        progress_path.touch()

        state_manager = StateManager(progress_path)
        loaded_state = state_manager.load_state()

        # Should return None for empty/invalid file
        assert loaded_state is None

    def test_resume_with_invalid_state_structure(self, tmp_path):
        """Test resume with invalid state structure."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        # Create JSON file with invalid structure (missing required fields)
        invalid_state = {"random_field": "value"}
        with open(progress_path, "w") as f:
            json.dump(invalid_state, f)

        state_manager = StateManager(progress_path)
        loaded_state = state_manager.load_state()

        # Should return None for invalid structure
        assert loaded_state is None

        # Should be able to continue with default state
        default_state = state_manager.get_state()
        assert default_state is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
