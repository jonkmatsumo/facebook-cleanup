"""
Structured logging setup for Facebook cleanup project.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Import settings with fallback for path issues
try:
    from config import settings
except ImportError:
    # Fallback if config not in path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config import settings


def setup_logging(log_level: str = None) -> logging.Logger:
    """
    Set up structured logging with file and console handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). 
                   Defaults to settings.LOG_LEVEL
    
    Returns:
        Configured logger instance
    """
    if log_level is None:
        log_level = settings.LOG_LEVEL
    
    # Create logger
    logger = logging.getLogger("facebook_cleanup")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Log format
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = settings.LOG_DIR / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # File gets all logs
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    logger.debug(f"Log level: {log_level}")
    
    return logger


def get_logger(name: str = "facebook_cleanup") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

