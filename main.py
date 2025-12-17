#!/usr/bin/env python3
"""
Facebook Cleanup - Main entry point.

Automated deletion of Facebook content created before 2021.
"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.utils.logging import setup_logging
from src.auth.browser_manager import BrowserManager
from config import settings


def main():
    """
    Main entry point for Facebook cleanup script.
    
    Phase 2: Authentication & Session Management.
    Tests the full authentication flow.
    """
    # Initialize logging
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Facebook Cleanup - Automated Content Deletion")
    logger.info("=" * 60)
    logger.info(f"Target Year: {settings.TARGET_YEAR}")
    logger.info(f"Start Year: {settings.START_YEAR}")
    logger.info(f"Max Deletions/Hour: {settings.MAX_DELETIONS_PER_HOUR}")
    logger.info(f"Interface: {settings.TARGET_INTERFACE}")
    logger.info("=" * 60)
    
    # Phase 2: Authentication & Session Management
    logger.info("Phase 2: Testing Authentication & Session Management")
    logger.info("-" * 60)
    
    try:
        # Create browser manager
        browser_manager = BrowserManager()
        
        # Create authenticated browser session
        logger.info("Creating authenticated browser session...")
        browser, context, page = browser_manager.create_authenticated_browser(
            headless=settings.HEADLESS,
            validate_session=True
        )
        
        logger.info("=" * 60)
        logger.info("SUCCESS: Authenticated browser session created!")
        logger.info("=" * 60)
        logger.info("Browser is ready for Phase 3: Traversal Engine")
        logger.info("")
        logger.info("Current page URL: " + page.url)
        logger.info("")
        logger.info("To test manually, the browser window should be open.")
        logger.info("Press Enter to close the browser and exit...")
        
        # Keep browser open for manual inspection (if not headless)
        if not settings.HEADLESS:
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                logger.info("Exiting...")
        
        # Cleanup
        browser_manager.cleanup()
        logger.info("Browser session closed")
        
        return 0
    
    except FileNotFoundError as e:
        logger.error("=" * 60)
        logger.error("ERROR: Cookie file not found")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("")
        logger.error("Please:")
        logger.error("  1. Log into Facebook in your browser")
        logger.error("  2. Export cookies to data/cookies.json")
        logger.error("  3. See SETUP.md for detailed instructions")
        return 1
    
    except ValueError as e:
        logger.error("=" * 60)
        logger.error("ERROR: Cookie validation failed")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("")
        logger.error("Please re-export your Facebook cookies.")
        return 1
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error("ERROR: Failed to create authenticated browser")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error("")
        logger.error("Please check:")
        logger.error("  1. Playwright is installed: playwright install chromium")
        logger.error("  2. Dependencies are installed: pip install -r requirements.txt")
        logger.error("  3. Cookies file exists and is valid")
        return 1


if __name__ == "__main__":
    sys.exit(main())

