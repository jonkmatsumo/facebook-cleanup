#!/usr/bin/env python3
"""
Facebook Cleanup - Main entry point.

Automated deletion of Facebook content created before 2021.
"""

import re
import signal
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from config import settings  # noqa: E402
from src.auth.browser_manager import BrowserManager  # noqa: E402
from src.deletion.deletion_engine import DeletionEngine  # noqa: E402
from src.deletion.trash_cleanup import TrashCleanup  # noqa: E402
from src.traversal.traversal_engine import TraversalEngine  # noqa: E402
from src.utils.logging import setup_logging  # noqa: E402
from src.utils.state_manager import StateManager  # noqa: E402
from src.utils.statistics import StatisticsReporter  # noqa: E402

# Global variables for cleanup on interrupt
browser_manager = None
state_manager = None
stats_reporter = None


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    logger = setup_logging()
    logger.warning("\nInterrupt received, saving state and cleaning up...")

    if state_manager and stats_reporter:
        try:
            # Update state with current statistics
            state = state_manager.get_state()
            state["total_deleted"] = stats_reporter.stats["total_deleted"]
            state["errors_encountered"] = stats_reporter.stats["errors_encountered"]
            state_manager.save_state(state)
            logger.info("Progress state saved")
        except Exception as e:
            logger.error(f"Failed to save state on interrupt: {e}")

    if browser_manager:
        try:
            browser_manager.cleanup()
        except Exception:
            pass

    logger.info("Exiting...")
    sys.exit(0)


def run_cleanup() -> int:
    """
    Execute the complete cleanup process.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    global browser_manager, state_manager, stats_reporter

    # Initialize logging
    logger = setup_logging()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 60)
    logger.info("Facebook Cleanup - Automated Content Deletion")
    logger.info("=" * 60)
    logger.info(f"Target Year: {settings.TARGET_YEAR}")
    logger.info(f"Start Year: {settings.START_YEAR}")
    logger.info(f"Max Deletions/Hour: {settings.MAX_DELETIONS_PER_HOUR}")
    logger.info(f"Interface: {settings.TARGET_INTERFACE}")
    logger.info("=" * 60)

    # Initialize state manager
    state_manager = StateManager(settings.PROGRESS_PATH)
    saved_state = state_manager.load_state()

    # Initialize statistics reporter
    stats_reporter = StatisticsReporter()
    if saved_state:
        stats_reporter.update_from_state(saved_state)
        logger.info(
            f"Resuming from saved state: {saved_state.get('current_year')}-{saved_state.get('current_month')}"
        )
        logger.info(f"Previously deleted: {saved_state.get('total_deleted', 0)} items")

    try:
        # Create browser manager and authenticated session
        logger.info("Creating authenticated browser session...")
        browser_manager = BrowserManager()
        browser, context, page = browser_manager.create_authenticated_browser(
            headless=settings.HEADLESS, validate_session=True
        )

        logger.info("Browser session created successfully")

        # Get username from settings or state
        username = settings.FACEBOOK_USERNAME
        if not username and saved_state:
            # Try to extract from last_url if available
            last_url = saved_state.get("last_url", "")
            if last_url:
                # Extract username from URL pattern
                match = re.search(r"mbasic\.facebook\.com/([^/]+)/", last_url)
                if match:
                    username = match.group(1)

        if not username:
            logger.error("Facebook username not configured. Set FACEBOOK_USERNAME in .env file.")
            return 1

        # Initialize TraversalEngine with resume state
        logger.info("Initializing traversal engine...")
        traversal_engine = TraversalEngine(page=page, username=username, resume_state=saved_state)

        # Initialize DeletionEngine (safety mechanisms already integrated)
        logger.info("Initializing deletion engine...")
        deletion_engine = DeletionEngine(page=page)

        # Main processing loop
        logger.info("=" * 60)
        logger.info("Starting cleanup process...")
        logger.info("=" * 60)

        pages_processed = 0
        total_deleted = 0
        total_failed = 0

        try:
            # Iterate through years and months
            for page_info in traversal_engine.traverse_years(resume_state=saved_state):
                year = page_info.get("year")
                month = page_info.get("month")
                page_num = page_info.get("page_number", 1)
                current_page = page_info.get("page", page)

                # Update state with current position
                state_manager.update_state(
                    current_year=year, current_month=month, last_url=current_page.url
                )

                logger.info(f"\nProcessing {year}-{month:02d}, page {page_num}")

                # Process page with deletion engine
                page_stats = deletion_engine.process_page(current_page)

                # Update statistics
                stats_reporter.update_from_page_stats(page_stats)
                total_deleted += page_stats["deleted"]
                total_failed += page_stats["failed"]
                pages_processed += 1

                # Check for critical errors
                if page_stats.get("errors"):
                    for error in page_stats["errors"]:
                        if "block" in error.get("error", "").lower():
                            logger.error("Block detected! Stopping cleanup.")
                            state_manager.update_state(block_detected=True)
                            return 1

                # Save progress state
                state_manager.update_state(
                    total_deleted=stats_reporter.stats["total_deleted"],
                    errors_encountered=stats_reporter.stats["errors_encountered"],
                )

                # Progress update
                logger.info(
                    f"Page complete: {page_stats['deleted']} deleted, "
                    f"{page_stats['failed']} failed. "
                    f"Total: {total_deleted} deleted, {total_failed} failed"
                )

        except KeyboardInterrupt:
            logger.warning("\nInterrupt received, saving state...")
            state_manager.update_state(
                total_deleted=stats_reporter.stats["total_deleted"],
                errors_encountered=stats_reporter.stats["errors_encountered"],
            )
            logger.info("State saved. You can resume by running the script again.")
            return 0

        # Optional: Cleanup trash
        logger.info("\n" + "=" * 60)
        logger.info("Checking Trash/Recycle Bin...")
        logger.info("=" * 60)

        try:
            trash_cleanup = TrashCleanup(page)
            trash_stats = trash_cleanup.cleanup_trash()
            if trash_stats["deleted"] > 0:
                logger.info(f"Cleaned {trash_stats['deleted']} items from trash")
        except Exception as e:
            logger.warning(f"Trash cleanup failed: {e}")

        # Final statistics
        logger.info("\n" + "=" * 60)
        stats_reporter.print_summary()

        # Save final state
        final_state = state_manager.get_state()
        final_state["total_deleted"] = stats_reporter.stats["total_deleted"]
        final_state["errors_encountered"] = stats_reporter.stats["errors_encountered"]
        state_manager.save_state(final_state)

        logger.info("Cleanup process completed successfully!")

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
        logger.error("ERROR: Unexpected error during cleanup")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("")

        # Save state on error
        if state_manager and stats_reporter:
            try:
                state_manager.update_state(
                    total_deleted=stats_reporter.stats["total_deleted"],
                    errors_encountered=stats_reporter.stats["errors_encountered"],
                )
                logger.info("Progress state saved")
            except Exception:
                pass

        return 1

    finally:
        # Cleanup browser resources
        if browser_manager:
            try:
                browser_manager.cleanup()
                logger.info("Browser session closed")
            except Exception:
                pass


def main():
    """
    Main entry point for Facebook cleanup script.

    Phase 6: Complete Integration - End-to-end cleanup workflow.
    """
    try:
        return run_cleanup()
    except KeyboardInterrupt:
        # Handle keyboard interrupt at top level
        logger = setup_logging()
        logger.warning("\nInterrupted by user")
        return 0


if __name__ == "__main__":
    sys.exit(main())
