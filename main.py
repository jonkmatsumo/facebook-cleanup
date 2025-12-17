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
from config import settings


def main():
    """
    Main entry point for Facebook cleanup script.
    
    Phase 1: Basic setup and logging initialization.
    Future phases will implement the full deletion workflow.
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
    
    logger.info("Phase 1: Environment setup complete")
    logger.info("Next steps:")
    logger.info("  1. Export cookies from browser to data/cookies.json")
    logger.info("  2. Set FACEBOOK_USERNAME in .env file")
    logger.info("  3. Run: playwright install chromium")
    logger.info("  4. Proceed to Phase 2: Authentication & Session Management")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

