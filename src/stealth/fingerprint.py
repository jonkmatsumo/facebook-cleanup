"""
Stealth configuration module for browser fingerprint masking and anti-detection.
"""
from pathlib import Path
from typing import Optional
from playwright.sync_api import Browser, BrowserContext
from playwright_stealth import stealth_sync
from config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_browser_args() -> list[str]:
    """
    Get browser launch arguments for stealth mode.
    
    Returns:
        List of browser launch arguments
    """
    args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        # '--no-sandbox'  # Uncomment if needed for compatibility, but may reduce security
    ]
    return args


def get_context_options(cookies_path: Optional[Path] = None) -> dict:
    """
    Get browser context options for stealth configuration.
    
    Args:
        cookies_path: Optional path to cookies.json file for storage_state
        
    Returns:
        Dictionary of context options
    """
    options = {
        'viewport': {'width': 360, 'height': 640},  # Mobile dimensions
        'user_agent': settings.USER_AGENT,
        'locale': 'en-US',
        'timezone_id': 'America/New_York',
        'permissions': [],  # No geolocation or other permissions
        'color_scheme': 'light',
    }
    
    # Add storage_state if cookies path provided
    if cookies_path and cookies_path.exists():
        options['storage_state'] = str(cookies_path)
        logger.debug(f"Using storage_state from: {cookies_path}")
    
    return options


def create_stealth_context(
    browser: Browser,
    cookies_path: Optional[Path] = None,
    **extra_options
) -> BrowserContext:
    """
    Create a browser context with stealth configuration.
    
    Args:
        browser: Playwright Browser instance
        cookies_path: Optional path to cookies.json for storage_state
        **extra_options: Additional context options to merge
        
    Returns:
        Configured BrowserContext with stealth settings
    """
    logger.info("Creating stealth browser context...")
    
    # Get base context options
    context_options = get_context_options(cookies_path)
    
    # Merge any extra options (extra_options take precedence)
    context_options.update(extra_options)
    
    logger.debug(f"Context options: viewport={context_options['viewport']}, "
                 f"user_agent={context_options['user_agent'][:50]}...")
    
    # Create context
    context = browser.new_context(**context_options)
    
    logger.info("Stealth context created successfully")
    return context


def apply_stealth_patches(page) -> None:
    """
    Apply playwright-stealth patches to a page.
    
    Args:
        page: Playwright Page object to patch
    """
    try:
        logger.debug("Applying stealth patches to page...")
        stealth_sync(page)
        logger.debug("Stealth patches applied successfully")
    except Exception as e:
        logger.warning(f"Failed to apply stealth patches: {e}")
        # Continue anyway - stealth patches are helpful but not critical
        # The browser args and context options provide most of the protection

