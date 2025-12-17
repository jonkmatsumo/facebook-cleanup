"""
Base deletion handler interface using Strategy pattern.
"""
from abc import ABC, abstractmethod
from typing import Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DeletionHandler(ABC):
    """Abstract base class for content-specific deletion handlers."""
    
    def __init__(self, timeout: int = 30000):
        """
        Initialize deletion handler.
        
        Args:
            timeout: Default timeout for operations in milliseconds
        """
        self.timeout = timeout
    
    @abstractmethod
    def can_handle(self, item: dict) -> bool:
        """
        Check if this handler can process the given item.
        
        Args:
            item: Item dictionary with type, date, element, etc.
        
        Returns:
            True if handler can process this item, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, page: Page, item: dict) -> tuple[bool, str]:
        """
        Execute deletion flow for the item.
        
        Args:
            page: Playwright Page object
            item: Item dictionary to delete
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    def _wait_for_confirmation(
        self,
        page: Page,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for confirmation page to load after clicking delete.
        
        Args:
            page: Playwright Page object
            timeout: Optional timeout override
        
        Returns:
            True if confirmation page detected, False otherwise
        """
        timeout = timeout or self.timeout
        
        try:
            # Wait for page to load
            page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Check if we're on a confirmation page
            current_url = page.url.lower()
            confirmation_indicators = ['delete', 'confirm', 'remove']
            
            if any(indicator in current_url for indicator in confirmation_indicators):
                logger.debug("Confirmation page detected")
                return True
            
            # Check for confirmation form/button
            confirm_selectors = [
                'input[type="submit"][value*="Delete"]',
                'input[type="submit"][value*="Confirm"]',
                'button:has-text("Delete")',
                'button:has-text("Confirm")',
                'a:has-text("Confirm")',
            ]
            
            for selector in confirm_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        logger.debug(f"Confirmation element found: {selector}")
                        return True
                except Exception:
                    continue
            
            logger.debug("No confirmation page detected (may be direct deletion)")
            return False
        
        except PlaywrightTimeoutError:
            logger.warning("Timeout waiting for confirmation page")
            return False
        except Exception as e:
            logger.debug(f"Error checking for confirmation page: {e}")
            return False
    
    def _click_confirm(
        self,
        page: Page,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Click confirmation button on confirmation page.
        
        Args:
            page: Playwright Page object
            timeout: Optional timeout override
        
        Returns:
            True if confirmation clicked successfully, False otherwise
        """
        timeout = timeout or self.timeout
        
        confirm_selectors = [
            'input[type="submit"][value*="Delete"]',
            'input[type="submit"][value*="Confirm"]',
            'button:has-text("Delete")',
            'button:has-text("Confirm")',
            'a:has-text("Confirm")',
            'a:has-text("Delete")',
            # Fallback: any submit button
            'input[type="submit"]',
        ]
        
        for selector in confirm_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    first_match = locator.first
                    if first_match.is_visible():
                        logger.debug(f"Clicking confirmation button: {selector}")
                        first_match.click(timeout=5000)
                        return True
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        
        logger.warning("Could not find confirmation button")
        return False
    
    def _wait_for_navigation(
        self,
        page: Page,
        expected_url_pattern: str = "allactivity",
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for navigation back to Activity Log after deletion.
        
        Args:
            page: Playwright Page object
            expected_url_pattern: URL pattern to wait for (default: "allactivity")
            timeout: Optional timeout override
        
        Returns:
            True if navigation successful, False otherwise
        """
        timeout = timeout or self.timeout
        
        try:
            # Wait for page to load
            page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Check if we're back on Activity Log
            current_url = page.url.lower()
            if expected_url_pattern.lower() in current_url:
                logger.debug(f"Navigation successful, back to {expected_url_pattern}")
                return True
            
            # Also check if we're still on a confirmation/delete page (error case)
            if 'delete' in current_url or 'confirm' in current_url:
                logger.warning("Still on confirmation page after clicking confirm")
                return False
            
            # May have navigated elsewhere, log but consider success
            logger.debug(f"Navigation completed, current URL: {current_url}")
            return True
        
        except PlaywrightTimeoutError:
            logger.warning("Timeout waiting for navigation")
            return False
        except Exception as e:
            logger.error(f"Error waiting for navigation: {e}")
            return False

