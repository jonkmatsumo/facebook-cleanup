"""
Unit tests for safety and rate limiting modules.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.safety.rate_limiter import RateLimiter
from src.safety.error_detector import ErrorDetector
from src.safety.block_manager import BlockManager
from src.utils.state_manager import StateManager
from src.stealth.behavior import human_delay, wait_before_action, micro_pause


class TestGaussianDelays:
    """Test Gaussian delay functions."""
    
    def test_human_delay_positive(self):
        """Test human_delay returns positive value."""
        delay = human_delay(mean=5.0, std_dev=1.5, min_delay=2.0)
        assert delay >= 2.0
    
    def test_human_delay_respects_min(self):
        """Test human_delay respects minimum delay."""
        # With very negative mean, should still return min_delay
        delay = human_delay(mean=-10.0, std_dev=1.0, min_delay=2.0)
        assert delay == 2.0
    
    def test_wait_before_action(self):
        """Test wait_before_action applies delay."""
        start = time.time()
        wait_before_action(mean=0.1, std_dev=0.01, min_delay=0.1)
        elapsed = time.time() - start
        assert elapsed >= 0.1
    
    def test_micro_pause(self):
        """Test micro_pause applies small delay."""
        start = time.time()
        micro_pause(min_pause=0.05, max_pause=0.1)
        elapsed = time.time() - start
        assert 0.05 <= elapsed <= 0.15  # Allow some overhead


class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_per_hour=10, mean_delay=1.0, std_dev=0.1, min_delay=0.5)
        assert limiter.max_per_hour == 10
        assert limiter.mean_delay == 1.0
        assert limiter.deleted_count == 0
    
    def test_check_rate_limit_empty(self):
        """Test check_rate_limit with no actions."""
        limiter = RateLimiter(max_per_hour=10)
        assert limiter.check_rate_limit() is True
    
    def test_check_rate_limit_under_limit(self):
        """Test check_rate_limit when under limit."""
        limiter = RateLimiter(max_per_hour=10)
        limiter.record_action()
        assert limiter.check_rate_limit() is True
    
    def test_check_rate_limit_exceeded(self):
        """Test check_rate_limit when limit exceeded."""
        limiter = RateLimiter(max_per_hour=2)
        limiter.record_action()
        limiter.record_action()
        limiter.record_action()  # Exceed limit
        assert limiter.check_rate_limit() is False
    
    def test_record_action(self):
        """Test record_action increments count."""
        limiter = RateLimiter()
        initial_count = limiter.deleted_count
        limiter.record_action()
        assert limiter.deleted_count == initial_count + 1
    
    def test_get_stats(self):
        """Test get_stats returns statistics."""
        limiter = RateLimiter(max_per_hour=50)
        limiter.record_action()
        stats = limiter.get_stats()
        
        assert 'max_per_hour' in stats
        assert 'actions_last_hour' in stats
        assert 'total_actions' in stats
        assert stats['total_actions'] == 1
    
    def test_reset(self):
        """Test reset clears actions."""
        limiter = RateLimiter()
        limiter.record_action()
        limiter.reset()
        assert limiter.deleted_count == 0
        assert len(limiter.action_times) == 0


class TestErrorDetector:
    """Test ErrorDetector class."""
    
    def test_check_url_for_errors_detected(self):
        """Test check_url_for_errors detects errors in URL."""
        detector = ErrorDetector()
        assert detector.check_url_for_errors("https://facebook.com/error") is True
        assert detector.check_url_for_errors("https://facebook.com/blocked") is True
    
    def test_check_url_for_errors_not_detected(self):
        """Test check_url_for_errors returns False for normal URLs."""
        detector = ErrorDetector()
        assert detector.check_url_for_errors("https://facebook.com/allactivity") is False
    
    def test_check_for_errors_in_content(self):
        """Test check_for_errors detects errors in page content."""
        detector = ErrorDetector()
        mock_page = Mock()
        mock_page.url = "https://facebook.com/allactivity"
        mock_page.content.return_value = "You're going too fast. Please slow down."
        
        error_detected, error_message = detector.check_for_errors(mock_page)
        assert error_detected is True
        assert "going too fast" in error_message.lower()
    
    def test_check_for_errors_no_error(self):
        """Test check_for_errors returns False when no errors."""
        detector = ErrorDetector()
        mock_page = Mock()
        mock_page.url = "https://facebook.com/allactivity"
        mock_page.content.return_value = "Welcome to Facebook"
        
        error_detected, error_message = detector.check_for_errors(mock_page)
        assert error_detected is False


class TestBlockManager:
    """Test BlockManager class."""
    
    def test_init(self):
        """Test BlockManager initialization."""
        manager = BlockManager(block_wait_hours=24, backoff_multiplier=1.5)
        assert manager.block_wait_hours == 24
        assert manager.block_detected is False
        assert manager.block_count == 0
    
    def test_check_and_handle_block_detected(self):
        """Test check_and_handle_block detects block."""
        manager = BlockManager()
        mock_page = Mock()
        mock_page.url = "https://facebook.com/allactivity"
        mock_page.content.return_value = "Action Blocked"
        
        error_detector = ErrorDetector()
        block_detected = manager.check_and_handle_block(mock_page, error_detector)
        
        assert block_detected is True
        assert manager.block_detected is True
        assert manager.block_count == 1
    
    def test_check_and_handle_block_not_detected(self):
        """Test check_and_handle_block returns False when no block."""
        manager = BlockManager()
        mock_page = Mock()
        mock_page.url = "https://facebook.com/allactivity"
        mock_page.content.return_value = "Normal page content"
        
        error_detector = ErrorDetector()
        block_detected = manager.check_and_handle_block(mock_page, error_detector)
        
        assert block_detected is False
        assert manager.block_detected is False
    
    def test_should_continue_no_block(self):
        """Test should_continue returns True when no block."""
        manager = BlockManager()
        assert manager.should_continue() is True
    
    def test_should_continue_block_recent(self):
        """Test should_continue returns False for recent block."""
        manager = BlockManager(block_wait_hours=24)
        manager.block_detected = True
        manager.last_block_time = datetime.now()  # Just now
        
        assert manager.should_continue() is False
    
    def test_should_continue_block_old(self):
        """Test should_continue returns True for old block."""
        manager = BlockManager(block_wait_hours=24)
        manager.block_detected = True
        manager.last_block_time = datetime.now() - timedelta(hours=25)  # 25 hours ago
        
        assert manager.should_continue() is True
    
    def test_apply_backoff(self):
        """Test apply_backoff increases delays."""
        manager = BlockManager(backoff_multiplier=1.5)
        manager.block_count = 1
        
        limiter = RateLimiter(mean_delay=5.0, std_dev=1.5)
        old_mean = limiter.mean_delay
        old_std_dev = limiter.std_dev
        
        manager.apply_backoff(limiter)
        
        assert limiter.mean_delay > old_mean
        assert limiter.std_dev > old_std_dev
    
    def test_get_block_info(self):
        """Test get_block_info returns block information."""
        manager = BlockManager()
        info = manager.get_block_info()
        
        assert 'block_detected' in info
        assert 'block_count' in info
        assert 'can_continue' in info


class TestStateManager:
    """Test StateManager class."""
    
    def test_init(self, tmp_path):
        """Test StateManager initialization."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)
        assert manager.progress_path == progress_path
    
    def test_get_state_default(self, tmp_path):
        """Test get_state returns default state when file doesn't exist."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)
        state = manager.get_state()
        
        assert 'total_deleted' in state
        assert 'errors_encountered' in state
        assert state['total_deleted'] == 0
    
    def test_save_and_load_state(self, tmp_path):
        """Test save_state and load_state."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)
        
        # Save state
        state = manager.get_state()
        state['total_deleted'] = 10
        manager.save_state(state)
        
        # Load state
        loaded_state = manager.load_state()
        assert loaded_state is not None
        assert loaded_state['total_deleted'] == 10
    
    def test_update_state(self, tmp_path):
        """Test update_state updates specific fields."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)
        
        manager.update_state(total_deleted=5, errors_encountered=2)
        state = manager.get_state()
        
        assert state['total_deleted'] == 5
        assert state['errors_encountered'] == 2
    
    def test_clear_state(self, tmp_path):
        """Test clear_state deletes file."""
        progress_path = tmp_path / "progress.json"
        manager = StateManager(progress_path)
        
        # Save state first
        manager.save_state(manager.get_state())
        assert progress_path.exists()
        
        # Clear state
        manager.clear_state()
        assert not progress_path.exists()
    
    def test_load_state_corrupted(self, tmp_path):
        """Test load_state handles corrupted JSON."""
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("not valid json {")
        
        manager = StateManager(progress_path)
        state = manager.load_state()
        
        # Should return None or default state
        assert state is None or isinstance(state, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

