"""
Rate limiter to enforce maximum deletion rate per hour.
"""
import time
from datetime import datetime, timedelta
from typing import Optional
from config import settings
from src.stealth.behavior import wait_before_action
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Enforces maximum deletion rate to prevent throttling."""
    
    def __init__(
        self,
        max_per_hour: Optional[int] = None,
        mean_delay: Optional[float] = None,
        std_dev: Optional[float] = None,
        min_delay: Optional[float] = None
    ):
        """
        Initialize RateLimiter.
        
        Args:
            max_per_hour: Maximum actions per hour (defaults to settings.MAX_DELETIONS_PER_HOUR)
            mean_delay: Mean delay in seconds (defaults to settings.MEAN_DELAY_SECONDS)
            std_dev: Standard deviation for delays (defaults to settings.DELAY_STD_DEV)
            min_delay: Minimum delay in seconds (defaults to settings.MIN_DELAY_SECONDS)
        """
        self.max_per_hour = max_per_hour or settings.MAX_DELETIONS_PER_HOUR
        self.mean_delay = mean_delay or settings.MEAN_DELAY_SECONDS
        self.std_dev = std_dev or settings.DELAY_STD_DEV
        self.min_delay = min_delay or settings.MIN_DELAY_SECONDS
        
        self.action_times: list[datetime] = []
        self.deleted_count = 0
        
        logger.info(
            f"RateLimiter initialized: max_per_hour={self.max_per_hour}, "
            f"mean_delay={self.mean_delay}s, std_dev={self.std_dev}s"
        )
    
    def check_rate_limit(self) -> bool:
        """
        Check if hourly rate limit has been exceeded.
        
        Returns:
            True if under limit, False if limit exceeded
        """
        now = datetime.now()
        
        # Remove actions older than 1 hour
        cutoff_time = now - timedelta(hours=1)
        self.action_times = [t for t in self.action_times if t > cutoff_time]
        
        current_count = len(self.action_times)
        
        if current_count >= self.max_per_hour:
            logger.warning(
                f"Rate limit exceeded: {current_count}/{self.max_per_hour} actions in last hour"
            )
            return False
        
        # Log warning when approaching limit (80%)
        if current_count >= int(self.max_per_hour * 0.8):
            logger.warning(
                f"Approaching rate limit: {current_count}/{self.max_per_hour} actions in last hour"
            )
        
        return True
    
    def wait_before_action(self) -> bool:
        """
        Apply delay and check rate limit before action.
        
        Returns:
            True if action can proceed, False if rate limit exceeded
        """
        # Check rate limit first
        if not self.check_rate_limit():
            return False
        
        # Apply Gaussian delay
        wait_before_action(
            mean=self.mean_delay,
            std_dev=self.std_dev,
            min_delay=self.min_delay
        )
        
        return True
    
    def record_action(self) -> None:
        """Record that an action was taken."""
        self.action_times.append(datetime.now())
        self.deleted_count += 1
        logger.debug(f"Action recorded. Total: {self.deleted_count}, Last hour: {len(self.action_times)}")
    
    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dictionary with statistics
        """
        now = datetime.now()
        cutoff_time = now - timedelta(hours=1)
        recent_actions = [t for t in self.action_times if t > cutoff_time]
        
        return {
            'max_per_hour': self.max_per_hour,
            'actions_last_hour': len(recent_actions),
            'total_actions': self.deleted_count,
            'mean_delay': self.mean_delay,
            'std_dev': self.std_dev,
            'min_delay': self.min_delay,
        }
    
    def reset(self) -> None:
        """Reset action tracking (useful for testing)."""
        self.action_times.clear()
        self.deleted_count = 0
        logger.debug("Rate limiter reset")

