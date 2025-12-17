"""
Human-like behavioral simulation for delays and pauses.
"""
import random
import time
from src.utils.logging import get_logger

logger = get_logger(__name__)


def human_delay(mean: float, std_dev: float, min_delay: float) -> float:
    """
    Generate human-like delay using Gaussian distribution.
    
    Args:
        mean: Average delay in seconds
        std_dev: Standard deviation in seconds
        min_delay: Minimum delay to prevent negative values
    
    Returns:
        Delay in seconds (always >= min_delay)
    """
    delay = random.gauss(mean, std_dev)
    return max(min_delay, delay)


def wait_before_action(
    mean: float = 5.0,
    std_dev: float = 1.5,
    min_delay: float = 2.0
) -> None:
    """
    Apply human-like delay before an action.
    
    Args:
        mean: Average delay in seconds (default: 5.0)
        std_dev: Standard deviation in seconds (default: 1.5)
        min_delay: Minimum delay in seconds (default: 2.0)
    """
    delay = human_delay(mean, std_dev, min_delay)
    logger.debug(f"Waiting {delay:.2f} seconds before action (mean={mean}, std_dev={std_dev})")
    time.sleep(delay)


def micro_pause(min_pause: float = 0.1, max_pause: float = 0.3) -> None:
    """
    Apply a small random pause for human-like behavior.
    
    Args:
        min_pause: Minimum pause in seconds (default: 0.1)
        max_pause: Maximum pause in seconds (default: 0.3)
    """
    pause = random.uniform(min_pause, max_pause)
    time.sleep(pause)

