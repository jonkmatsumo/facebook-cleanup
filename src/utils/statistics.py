"""
Statistics and reporting utilities.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class StatisticsReporter:
    """Generates statistics and reports for cleanup operations."""

    def __init__(self, start_time: Optional[datetime] = None):
        """
        Initialize StatisticsReporter.

        Args:
            start_time: Operation start time (defaults to now)
        """
        self.start_time = start_time or datetime.now()
        self.stats = {
            "total_deleted": 0,
            "posts_deleted": 0,
            "comments_deleted": 0,
            "reactions_removed": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "errors_encountered": 0,
            "blocks_detected": 0,
        }

    def update_from_page_stats(self, page_stats: dict) -> None:
        """
        Update statistics from page processing results.

        Args:
            page_stats: Statistics dictionary from DeletionEngine.process_page()
        """
        self.stats["total_deleted"] += page_stats.get("deleted", 0)
        self.stats["total_failed"] += page_stats.get("failed", 0)
        self.stats["total_skipped"] += page_stats.get("skipped", 0)
        self.stats["errors_encountered"] += len(page_stats.get("errors", []))

    def update_from_state(self, state: dict) -> None:
        """
        Update statistics from saved state.

        Args:
            state: State dictionary from StateManager
        """
        self.stats["total_deleted"] = state.get("total_deleted", 0)
        self.stats["errors_encountered"] = state.get("errors_encountered", 0)
        self.stats["blocks_detected"] = 1 if state.get("block_detected") else 0

    def print_summary(self) -> None:
        """Print final summary statistics."""
        elapsed = datetime.now() - self.start_time
        hours = elapsed.total_seconds() / 3600

        logger.info("=" * 60)
        logger.info("CLEANUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Deleted: {self.stats['total_deleted']}")
        logger.info(f"  - Posts: {self.stats['posts_deleted']}")
        logger.info(f"  - Comments: {self.stats['comments_deleted']}")
        logger.info(f"  - Reactions: {self.stats['reactions_removed']}")
        logger.info(f"Total Failed: {self.stats['total_failed']}")
        logger.info(f"Total Skipped: {self.stats['total_skipped']}")
        logger.info(f"Errors Encountered: {self.stats['errors_encountered']}")
        logger.info(f"Blocks Detected: {self.stats['blocks_detected']}")
        logger.info(f"Time Elapsed: {elapsed}")
        logger.info(
            f"Average Rate: {self.stats['total_deleted'] / max(hours, 0.01):.1f} items/hour"
        )
        logger.info("=" * 60)

    def generate_report(self, state: Optional[dict] = None) -> str:
        """
        Generate text report.

        Args:
            state: Optional state dictionary for additional context

        Returns:
            Formatted report string
        """
        elapsed = datetime.now() - self.start_time
        hours = elapsed.total_seconds() / 3600

        report_lines = [
            "Facebook Cleanup Report",
            "=" * 60,
            f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {elapsed}",
            "",
            "Statistics:",
            f"  Total Deleted: {self.stats['total_deleted']}",
            f"    - Posts: {self.stats['posts_deleted']}",
            f"    - Comments: {self.stats['comments_deleted']}",
            f"    - Reactions: {self.stats['reactions_removed']}",
            f"  Total Failed: {self.stats['total_failed']}",
            f"  Total Skipped: {self.stats['total_skipped']}",
            f"  Errors: {self.stats['errors_encountered']}",
            f"  Blocks: {self.stats['blocks_detected']}",
            "",
            f"Average Rate: {self.stats['total_deleted'] / max(hours, 0.01):.1f} items/hour",
        ]

        if state:
            report_lines.extend(
                [
                    "",
                    "Progress State:",
                    f"  Current Year: {state.get('current_year', 'N/A')}",
                    f"  Current Month: {state.get('current_month', 'N/A')}",
                    f"  Last URL: {state.get('last_url', 'N/A')}",
                ]
            )

        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics.

        Returns:
            Statistics dictionary
        """
        elapsed = datetime.now() - self.start_time
        return {
            **self.stats,
            "start_time": self.start_time.isoformat(),
            "elapsed_time": str(elapsed),
            "elapsed_hours": elapsed.total_seconds() / 3600,
        }
