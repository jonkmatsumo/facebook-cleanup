"""
Browser manager for creating authenticated browser sessions with stealth configuration.
"""
from pathlib import Path
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from config import settings
from src.auth.cookie_manager import CookieManager
from src.auth.session_validator import SessionValidator
from src.stealth.fingerprint import create_stealth_context, apply_stealth_patches, get_browser_args
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """High-level interface for creating authenticated browser sessions."""
    
    def __init__(self, cookie_path: Optional[Path] = None, logger_instance=None):
        """
        Initialize BrowserManager.
        
        Args:
            cookie_path: Path to cookies.json file (defaults to settings.COOKIES_PATH)
            logger_instance: Optional logger instance (uses module logger if None)
        """
        self.cookie_path = cookie_path or settings.COOKIES_PATH
        self.logger = logger_instance or logger
        self.cookie_manager = CookieManager(self.cookie_path)
        self.session_validator = SessionValidator()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def create_authenticated_browser(
        self,
        headless: Optional[bool] = None,
        validate_session: bool = True
    ) -> Tuple[Browser, BrowserContext, Page]:
        """
        Create an authenticated browser session with stealth configuration.
        
        Args:
            headless: Run browser in headless mode (defaults to settings.HEADLESS)
            validate_session: Whether to validate session after creation (default: True)
            
        Returns:
            Tuple of (Browser, BrowserContext, Page)
            
        Raises:
            FileNotFoundError: If cookie file doesn't exist
            ValueError: If cookies are invalid or session validation fails
            RuntimeError: If browser creation fails
        """
        headless = headless if headless is not None else settings.HEADLESS
        
        try:
            # Step 1: Load and validate cookies
            self.logger.info("Step 1: Loading cookies...")
            cookies_data = self.cookie_manager.load_cookies()
            
            # Check required cookies
            all_present, missing = self.cookie_manager.check_required_cookies()
            if not all_present:
                raise ValueError(
                    f"Missing required cookies: {missing}\n"
                    "Please re-export your Facebook cookies. See SETUP.md for instructions."
                )
            
            self.logger.info("Cookies loaded and validated successfully")
            
            # Step 2: Launch browser
            self.logger.info("Step 2: Launching browser...")
            self.playwright = sync_playwright().start()
            
            browser_args = get_browser_args()
            self.logger.debug(f"Browser args: {browser_args}")
            
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )
            self.logger.info(f"Browser launched (headless={headless})")
            
            # Step 3: Create stealth context with cookies and resource blocking
            self.logger.info("Step 3: Creating stealth context with cookies...")
            self.context = create_stealth_context(
                self.browser,
                cookies_path=self.cookie_path,
                block_resources=True  # Block images, videos, fonts for performance
            )
            self.logger.info("Stealth context created with resource blocking")
            
            # Step 4: Create page and apply stealth patches
            self.logger.info("Step 4: Creating page and applying stealth patches...")
            self.page = self.context.new_page()
            apply_stealth_patches(self.page)
            self.logger.info("Page created and stealth patches applied")
            
            # Step 5: Validate session
            if validate_session:
                self.logger.info("Step 5: Validating session...")
                is_valid, message = self.session_validator.validate_session(self.page)
                
                if not is_valid:
                    self.logger.error(f"Session validation failed: {message}")
                    self.cleanup()
                    raise ValueError(
                        f"Session validation failed: {message}\n"
                        "Please re-export your Facebook cookies and try again."
                    )
                
                self.logger.info(f"Session validation successful: {message}")
            
            self.logger.info("Authenticated browser session created successfully")
            return self.browser, self.context, self.page
        
        except FileNotFoundError as e:
            self.logger.error(f"Cookie file not found: {e}")
            self.cleanup()
            raise
        except ValueError as e:
            self.logger.error(f"Cookie validation error: {e}")
            self.cleanup()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error creating browser: {e}")
            self.cleanup()
            raise RuntimeError(f"Failed to create authenticated browser: {e}") from e
    
    def cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                self.page.close()
                self.page = None
                self.logger.debug("Page closed")
        except Exception as e:
            self.logger.debug(f"Error closing page: {e}")
        
        try:
            if self.context:
                self.context.close()
                self.context = None
                self.logger.debug("Context closed")
        except Exception as e:
            self.logger.debug(f"Error closing context: {e}")
        
        try:
            if self.browser:
                self.browser.close()
                self.browser = None
                self.logger.debug("Browser closed")
        except Exception as e:
            self.logger.debug(f"Error closing browser: {e}")
        
        try:
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
                self.logger.debug("Playwright stopped")
        except Exception as e:
            self.logger.debug(f"Error stopping playwright: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()
        return False

