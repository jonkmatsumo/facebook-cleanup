"""
Integration tests for complete cleanup workflow.
"""
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.deletion.deletion_engine import DeletionEngine
from src.traversal.traversal_engine import TraversalEngine
from src.utils.state_manager import StateManager
from src.utils.statistics import StatisticsReporter


@pytest.mark.integration
class TestIntegration:
    """Test complete integration workflow."""

    def test_traversal_with_resume(self):
        """Test TraversalEngine with resume state."""
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/test/allactivity"

        resume_state = {
            "current_year": 2019,
            "current_month": 11,
            "total_deleted": 100,
        }

        engine = TraversalEngine(page=mock_page, username="testuser", resume_state=resume_state)

        assert engine.start_year == 2019  # Should adjust to resume year

    def test_deletion_engine_integration(self):
        """Test DeletionEngine with all safety mechanisms."""
        mock_page = Mock()
        engine = DeletionEngine(page=mock_page)

        # Verify all safety mechanisms are initialized
        assert engine.rate_limiter is not None
        assert engine.error_detector is not None
        assert engine.block_manager is not None
        assert engine.state_manager is not None

    def test_statistics_tracking(self):
        """Test statistics reporter tracks correctly."""
        reporter = StatisticsReporter()

        # Simulate page processing
        page_stats = {"deleted": 5, "failed": 1, "skipped": 0, "errors": [{"error": "test error"}]}

        reporter.update_from_page_stats(page_stats)

        assert reporter.stats["total_deleted"] == 5
        assert reporter.stats["total_failed"] == 1
        assert reporter.stats["errors_encountered"] == 1

    def test_state_manager_save_load(self, tmp_path):
        """Test state manager save and load cycle."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)

        # Save state
        state = manager.get_state()
        state["current_year"] = 2019
        state["current_month"] = 11
        state["total_deleted"] = 100
        manager.save_state(state)

        # Load state
        loaded = manager.load_state()
        assert loaded is not None
        assert loaded["current_year"] == 2019
        assert loaded["total_deleted"] == 100


class TestResume:
    """Test resume functionality."""

    def test_resume_from_state(self, tmp_path):
        """Test resuming from saved state."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)

        # Create resume state
        state = manager.get_state()
        state["current_year"] = 2019
        state["current_month"] = 6
        state["total_deleted"] = 50
        manager.save_state(state)

        # Load and verify
        loaded = manager.load_state()
        assert loaded["current_year"] == 2019
        assert loaded["current_month"] == 6
        assert loaded["total_deleted"] == 50


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    def test_rate_limit_handling(self):
        """Test rate limit exceeded handling."""
        from src.safety.rate_limiter import RateLimiter

        limiter = RateLimiter(max_per_hour=2)
        limiter.record_action()
        limiter.record_action()
        limiter.record_action()  # Exceed limit

        assert limiter.check_rate_limit() is False

    def test_block_detection(self):
        """Test block detection and handling."""
        from src.safety.block_manager import BlockManager
        from src.safety.error_detector import ErrorDetector

        manager = BlockManager()
        detector = ErrorDetector()

        mock_page = Mock()
        mock_page.url = "https://facebook.com/error"
        mock_page.content.return_value = "Action Blocked"

        block_detected = manager.check_and_handle_block(mock_page, detector)
        assert block_detected is True
        assert manager.block_detected is True
        assert manager.should_continue() is False  # Should wait


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
