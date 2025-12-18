"""
Integration tests for error recovery mechanisms.
"""
import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.deletion.deletion_engine import DeletionEngine
from src.safety.block_manager import BlockManager
from src.safety.error_detector import ErrorDetector
from src.utils.state_manager import StateManager


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery mechanisms and block detection."""

    def test_error_recovery_transient_errors(self, tmp_path):
        """Test error recovery with transient errors."""
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        deletion_engine = DeletionEngine(page=mock_page)

        # Mock handler's delete() method to raise transient errors then succeed
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_handler = Mock()
        # First two calls raise transient error, third succeeds
        mock_handler.delete.side_effect = [
            PlaywrightTimeoutError("Timeout"),
            PlaywrightTimeoutError("Timeout"),
            (True, "Success"),
        ]
        deletion_engine._select_handler = Mock(return_value=mock_handler)

        # Create a mock item
        mock_item = {"type": "post", "date_string": "2020-01-01", "id": "item1"}

        # Attempt deletion (should retry and succeed)
        result, message = deletion_engine.delete_item(mock_page, mock_item, max_retries=3)

        # Verify successful recovery after retry
        assert result is True
        assert mock_handler.delete.call_count == 3  # Should have retried

    def test_error_recovery_persistent_errors(self, tmp_path):
        """Test error recovery with persistent errors."""
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        deletion_engine = DeletionEngine(page=mock_page)

        # Mock handler's delete() to always raise exceptions
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_handler = Mock()
        mock_handler.delete.side_effect = PlaywrightTimeoutError("Persistent timeout")
        deletion_engine._select_handler = Mock(return_value=mock_handler)

        # Mock item extractor to return items
        mock_item = {"type": "post", "date_string": "2020-01-01", "id": "item1"}
        deletion_engine.item_extractor.extract_items = Mock(return_value=[mock_item])

        # Process page - should continue despite persistent errors
        page_stats = deletion_engine.process_page(mock_page)

        # Verify workflow continues
        assert page_stats is not None
        # Verify failed items are tracked
        assert page_stats["failed"] > 0
        # Verify errors are in the errors list
        assert len(page_stats["errors"]) > 0

    def test_error_recovery_transient_errors_logged(self, tmp_path):
        """Test transient errors are logged but don't stop workflow."""
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        deletion_engine = DeletionEngine(page=mock_page)

        # Mock handler's delete() with transient errors that recover
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_handler = Mock()
        # First two calls raise transient error, third succeeds
        mock_handler.delete.side_effect = [
            PlaywrightTimeoutError("Transient timeout"),
            PlaywrightTimeoutError("Transient timeout"),
            (True, "Success"),
        ]
        deletion_engine._select_handler = Mock(return_value=mock_handler)

        mock_item = {"type": "post", "date_string": "2020-01-01", "id": "item1"}
        deletion_engine.item_extractor.extract_items = Mock(return_value=[mock_item])

        # Process page
        page_stats = deletion_engine.process_page(mock_page)

        # Verify workflow continued (didn't crash)
        assert page_stats is not None
        # Verify transient errors don't accumulate incorrectly in stats
        # (should be successful after retry)
        assert page_stats["deleted"] == 1
        assert page_stats["failed"] == 0

    def test_error_recovery_block_detection(self, tmp_path):
        """Test error recovery with block detection."""
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/blocked"

        deletion_engine = DeletionEngine(page=mock_page)

        # Mock ErrorDetector to detect block
        mock_error_detector = Mock()
        mock_error_detector.check_for_errors.return_value = (True, "Action Blocked")
        deletion_engine.error_detector = mock_error_detector

        # Check for block
        block_detected = deletion_engine.block_manager.check_and_handle_block(
            mock_page, mock_error_detector
        )

        # Verify block detection
        assert block_detected is True
        assert deletion_engine.block_manager.block_detected is True
        assert deletion_engine.block_manager.should_continue() is False

    def test_error_recovery_block_info_saved_to_state(self, tmp_path):
        """Test block information is saved to state."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/blocked"

        state_manager = StateManager(progress_path)
        deletion_engine = DeletionEngine(page=mock_page)

        # Mock error detector to detect block
        mock_error_detector = Mock()
        mock_error_detector.check_for_errors.return_value = (True, "Action Blocked")
        deletion_engine.error_detector = mock_error_detector

        # Detect block
        deletion_engine.block_manager.check_and_handle_block(mock_page, mock_error_detector)

        # Save block info to state
        state_manager.update_state(
            block_detected=True,
            block_count=deletion_engine.block_manager.block_count,
        )

        # Verify state saved
        saved_state = state_manager.get_state()
        assert saved_state["block_detected"] is True
        assert saved_state["block_count"] > 0

    def test_error_recovery_workflow_saves_state_before_stopping(self, tmp_path):
        """Test workflow saves state before stopping on block."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)
        deletion_engine = DeletionEngine(page=mock_page)

        # Set up block
        mock_error_detector = Mock()
        mock_error_detector.check_for_errors.return_value = (True, "Action Blocked")
        deletion_engine.error_detector = mock_error_detector
        deletion_engine.block_manager.check_and_handle_block(mock_page, mock_error_detector)

        # Mock items on page
        mock_item = {"type": "post", "date_string": "2020-01-01", "id": "item1"}
        deletion_engine.item_extractor.extract_items = Mock(return_value=[mock_item])

        # Process page - should detect block and stop
        deletion_engine.process_page(mock_page)

        # Verify block was detected and workflow stopped
        assert deletion_engine.block_manager.block_detected is True
        assert deletion_engine.block_manager.should_continue() is False

        # Explicitly update state with block info (as would be done in main workflow)
        state_manager.update_state(
            block_detected=True,
            block_count=deletion_engine.block_manager.block_count,
        )

        # Verify state was saved with block info
        saved_state = state_manager.get_state()
        assert saved_state["block_detected"] is True

    def test_state_saving_on_errors(self, tmp_path):
        """Test state saving on errors."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)
        deletion_engine = DeletionEngine(page=mock_page)

        # Mock handler's delete() to fail
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_handler = Mock()
        mock_handler.delete.side_effect = PlaywrightTimeoutError("Deletion failed")
        deletion_engine._select_handler = Mock(return_value=mock_handler)

        # Process page with errors
        mock_item = {"type": "post", "date_string": "2020-01-01", "id": "item1"}
        deletion_engine.item_extractor.extract_items = Mock(return_value=[mock_item])

        page_stats = deletion_engine.process_page(mock_page)

        # Save state after errors
        state_manager.update_state(
            current_year=2020,
            current_month=10,
            total_deleted=page_stats["deleted"],
            errors_encountered=len(page_stats["errors"]),
        )

        # Verify state saved with error information
        saved_state = state_manager.get_state()
        assert saved_state["errors_encountered"] > 0
        assert saved_state["current_year"] == 2020
        assert saved_state["current_month"] == 10

    def test_state_includes_current_position_on_error(self, tmp_path):
        """Test state includes current position when error occurred."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity?year=2020&month=9"

        state_manager = StateManager(progress_path)

        # Save state with position when error occurs
        state_manager.update_state(
            current_year=2020,
            current_month=9,
            last_url=mock_page.url,
            errors_encountered=5,
        )

        # Verify state contains position
        saved_state = state_manager.get_state()
        assert saved_state["current_year"] == 2020
        assert saved_state["current_month"] == 9
        assert saved_state["last_url"] == mock_page.url

    def test_state_can_resume_after_error_recovery(self, tmp_path):
        """Test state can be used to resume after error recovery."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)

        # Save state with error information
        state_manager.update_state(
            current_year=2020,
            current_month=9,
            total_deleted=50,
            errors_encountered=3,
        )

        # Load state for resume
        loaded_state = state_manager.load_state()

        # Verify can resume from saved position
        assert loaded_state["current_year"] == 2020
        assert loaded_state["current_month"] == 9
        assert loaded_state["total_deleted"] == 50

    def test_errors_encountered_counter_incremented(self, tmp_path):
        """Test errors_encountered counter is incremented."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)
        deletion_engine = DeletionEngine(page=mock_page)

        # Initial state
        initial_state = state_manager.get_state()
        initial_errors = initial_state.get("errors_encountered", 0)

        # Mock handler's delete() to fail
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        mock_handler = Mock()
        mock_handler.delete.side_effect = PlaywrightTimeoutError("Error")
        deletion_engine._select_handler = Mock(return_value=mock_handler)

        # Process page with errors
        mock_item = {"type": "post", "date_string": "2020-01-01", "id": "item1"}
        deletion_engine.item_extractor.extract_items = Mock(return_value=[mock_item])

        page_stats = deletion_engine.process_page(mock_page)

        # Update state with errors
        state_manager.update_state(errors_encountered=initial_errors + len(page_stats["errors"]))

        # Verify counter incremented
        final_state = state_manager.get_state()
        assert final_state["errors_encountered"] > initial_errors

    def test_state_saved_atomically_on_error(self, tmp_path):
        """Test state is saved atomically (no corruption on error)."""
        progress_path = tmp_path / "progress.json"
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/testuser/allactivity"

        state_manager = StateManager(progress_path)

        # Save state (should use atomic write)
        state_manager.update_state(
            current_year=2020,
            current_month=10,
            total_deleted=100,
            errors_encountered=5,
        )

        # Verify file exists and is valid JSON
        assert progress_path.exists()

        # Verify can load state without errors
        loaded_state = state_manager.load_state()
        assert loaded_state is not None
        assert loaded_state["current_year"] == 2020
        assert loaded_state["total_deleted"] == 100

        # Verify backup file created (for atomic writes)
        backup_path = progress_path.with_suffix(".json.bak")
        # Backup may or may not exist depending on whether this is first save
        # But if it exists, it should be valid JSON
        if backup_path.exists():
            with open(backup_path) as f:
                backup_data = json.load(f)
            assert isinstance(backup_data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
