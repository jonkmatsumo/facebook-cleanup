"""
Error detector for Facebook error messages indicating blocks or throttling.
"""
from typing import Optional
from playwright.sync_api import Page
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ErrorDetector:
    """Detects Facebook error messages indicating blocks or throttling."""
    
    ERROR_INDICATORS = [
        "You're going too fast",
        "This feature is temporarily blocked",
        "Action Blocked",
        "Too many requests",
        "Please slow down",
        "Temporarily unavailable",
        "Try again later",
        "Something went wrong",
        "We're having trouble",
        "Unable to complete",
    ]
    
    def __init__(self, additional_indicators: Optional[list] = None):
        """
        Initialize ErrorDetector.
        
        Args:
            additional_indicators: Optional list of additional error indicators
        """
        self.indicators = self.ERROR_INDICATORS.copy()
        if additional_indicators:
            self.indicators.extend(additional_indicators)
    
    def check_for_errors(self, page: Page) -> tuple[bool, Optional[str]]:
        """
        Check page for error messages.
        
        Args:
            page: Playwright Page object
        
        Returns:
            Tuple of (error_detected: bool, error_message: str or None)
        """
        # Check URL first (faster)
        url_has_error = self.check_url_for_errors(page.url)
        if url_has_error:
            logger.warning(f"Error detected in URL: {page.url}")
            return True, f"Error URL detected: {page.url}"
        
        # Check page content
        try:
            content = page.content().lower()
            
            for indicator in self.indicators:
                if indicator.lower() in content:
                    logger.warning(f"Error detected in page content: '{indicator}'")
                    return True, f"Error message detected: '{indicator}'"
        
        except Exception as e:
            logger.debug(f"Error checking page content: {e}")
            # If we can't check content, assume no error (don't want false positives)
            return False, None
        
        return False, None
    
    def check_url_for_errors(self, url: str) -> bool:
        """
        Check URL for error indicators.
        
        Args:
            url: URL string to check
        
        Returns:
            True if error indicators found in URL, False otherwise
        """
        url_lower = url.lower()
        
        error_url_patterns = [
            'error',
            'blocked',
            'unavailable',
            'restricted',
            'checkpoint',
            'security',
        ]
        
        for pattern in error_url_patterns:
            if pattern in url_lower:
                return True
        
        return False

