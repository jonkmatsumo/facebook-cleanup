"""
Tests for StatisticsReporter class.
"""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.utils.statistics import StatisticsReporter


@pytest.mark.unit
class TestStatisticsReporterInit:
    """Test StatisticsReporter.__init__() method."""

    def test_init_default_start_time(self):
        """Test initializes with default start_time (datetime.now())."""
        before_init = datetime.now()
        reporter = StatisticsReporter()
        after_init = datetime.now()

        assert reporter.start_time >= before_init
        assert reporter.start_time <= after_init

    def test_init_custom_start_time(self):
        """Test initializes with custom start_time."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        reporter = StatisticsReporter(start_time=custom_time)

        assert reporter.start_time == custom_time

    def test_init_empty_stats(self):
        """Test initializes with empty stats dictionary."""
        reporter = StatisticsReporter()

        assert isinstance(reporter.stats, dict)
        assert reporter.stats["total_deleted"] == 0
        assert reporter.stats["total_failed"] == 0
        assert reporter.stats["total_skipped"] == 0

    def test_init_counters_start_at_zero(self):
        """Test all counters start at 0."""
        reporter = StatisticsReporter()

        assert reporter.stats["total_deleted"] == 0
        assert reporter.stats["posts_deleted"] == 0
        assert reporter.stats["comments_deleted"] == 0
        assert reporter.stats["reactions_removed"] == 0
        assert reporter.stats["total_failed"] == 0
        assert reporter.stats["total_skipped"] == 0
        assert reporter.stats["errors_encountered"] == 0
        assert reporter.stats["blocks_detected"] == 0


@pytest.mark.unit
class TestStatisticsReporterUpdateFromPageStats:
    """Test StatisticsReporter.update_from_page_stats() method."""

    def test_update_from_page_stats_deleted(self):
        """Test updates deleted count."""
        reporter = StatisticsReporter()
        initial_deleted = reporter.stats["total_deleted"]

        page_stats = {"deleted": 5}
        reporter.update_from_page_stats(page_stats)

        assert reporter.stats["total_deleted"] == initial_deleted + 5

    def test_update_from_page_stats_failed(self):
        """Test updates failed count."""
        reporter = StatisticsReporter()

        page_stats = {"failed": 3}
        reporter.update_from_page_stats(page_stats)

        assert reporter.stats["total_failed"] == 3

    def test_update_from_page_stats_skipped(self):
        """Test updates skipped count."""
        reporter = StatisticsReporter()

        page_stats = {"skipped": 2}
        reporter.update_from_page_stats(page_stats)

        assert reporter.stats["total_skipped"] == 2

    def test_update_from_page_stats_errors(self):
        """Test appends errors to errors_encountered count."""
        reporter = StatisticsReporter()
        initial_errors = reporter.stats["errors_encountered"]

        page_stats = {"errors": ["error1", "error2", "error3"]}
        reporter.update_from_page_stats(page_stats)

        assert reporter.stats["errors_encountered"] == initial_errors + 3

    def test_update_from_page_stats_empty_dict(self):
        """Test handles empty stats dictionary."""
        reporter = StatisticsReporter()
        initial_stats = reporter.stats.copy()

        page_stats = {}
        reporter.update_from_page_stats(page_stats)

        # Should not change stats
        assert reporter.stats == initial_stats

    def test_update_from_page_stats_aggregates(self):
        """Test aggregates multiple updates correctly."""
        reporter = StatisticsReporter()

        page_stats1 = {"deleted": 10, "failed": 2, "errors": ["err1"]}
        reporter.update_from_page_stats(page_stats1)

        page_stats2 = {"deleted": 5, "skipped": 1, "errors": ["err2", "err3"]}
        reporter.update_from_page_stats(page_stats2)

        assert reporter.stats["total_deleted"] == 15
        assert reporter.stats["total_failed"] == 2
        assert reporter.stats["total_skipped"] == 1
        assert reporter.stats["errors_encountered"] == 3


@pytest.mark.unit
class TestStatisticsReporterUpdateFromState:
    """Test StatisticsReporter.update_from_state() method."""

    def test_update_from_state_total_deleted(self):
        """Test updates total_deleted from state."""
        reporter = StatisticsReporter()

        state = {"total_deleted": 100}
        reporter.update_from_state(state)

        assert reporter.stats["total_deleted"] == 100

    def test_update_from_state_errors_encountered(self):
        """Test updates errors_encountered from state."""
        reporter = StatisticsReporter()

        state = {"errors_encountered": 5}
        reporter.update_from_state(state)

        assert reporter.stats["errors_encountered"] == 5

    def test_update_from_state_blocks_detected_true(self):
        """Test updates blocks_detected when True."""
        reporter = StatisticsReporter()

        state = {"block_detected": True}
        reporter.update_from_state(state)

        assert reporter.stats["blocks_detected"] == 1

    def test_update_from_state_blocks_detected_false(self):
        """Test updates blocks_detected when False."""
        reporter = StatisticsReporter()

        state = {"block_detected": False}
        reporter.update_from_state(state)

        assert reporter.stats["blocks_detected"] == 0

    def test_update_from_state_missing_fields(self):
        """Test handles missing fields gracefully."""
        reporter = StatisticsReporter()
        initial_stats = reporter.stats.copy()

        state = {}  # Empty state
        reporter.update_from_state(state)

        # Should use existing stats for missing fields
        assert reporter.stats["total_deleted"] == initial_stats["total_deleted"]
        assert reporter.stats["errors_encountered"] == initial_stats["errors_encountered"]

    def test_update_from_state_multiple_fields(self):
        """Test updates multiple fields from state."""
        reporter = StatisticsReporter()

        state = {"total_deleted": 200, "errors_encountered": 10, "block_detected": True}
        reporter.update_from_state(state)

        assert reporter.stats["total_deleted"] == 200
        assert reporter.stats["errors_encountered"] == 10
        assert reporter.stats["blocks_detected"] == 1


@pytest.mark.unit
class TestStatisticsReporterGetStats:
    """Test StatisticsReporter.get_stats() method."""

    def test_get_stats_returns_dict(self):
        """Test returns current statistics dictionary."""
        reporter = StatisticsReporter()
        stats = reporter.get_stats()

        assert isinstance(stats, dict)

    def test_get_stats_includes_expected_fields(self):
        """Test includes all expected fields."""
        reporter = StatisticsReporter()
        stats = reporter.get_stats()

        expected_fields = [
            "total_deleted",
            "posts_deleted",
            "comments_deleted",
            "reactions_removed",
            "total_failed",
            "total_skipped",
            "errors_encountered",
            "blocks_detected",
            "start_time",
            "elapsed_time",
            "elapsed_hours",
        ]

        for field in expected_fields:
            assert field in stats, f"Missing field: {field}"

    def test_get_stats_includes_elapsed_time(self):
        """Test includes elapsed_time calculation."""
        start_time = datetime.now() - timedelta(hours=2)
        reporter = StatisticsReporter(start_time=start_time)
        stats = reporter.get_stats()

        assert "elapsed_time" in stats
        assert "elapsed_hours" in stats
        assert stats["elapsed_hours"] > 0

    def test_get_stats_start_time_format(self):
        """Test start_time is ISO format."""
        reporter = StatisticsReporter()
        stats = reporter.get_stats()

        # Should be ISO format string
        datetime.fromisoformat(stats["start_time"])


@pytest.mark.unit
class TestStatisticsReporterPrintSummary:
    """Test StatisticsReporter.print_summary() method."""

    @patch("src.utils.statistics.logger")
    def test_print_summary_calls_logger(self, mock_logger):
        """Test prints summary using logger."""
        reporter = StatisticsReporter()
        reporter.stats["total_deleted"] = 50

        reporter.print_summary()

        # Verify logger.info was called multiple times
        assert mock_logger.info.call_count >= 5

    @patch("src.utils.statistics.logger")
    def test_print_summary_includes_key_statistics(self, mock_logger):
        """Test includes key statistics."""
        reporter = StatisticsReporter()
        reporter.stats["total_deleted"] = 100
        reporter.stats["total_failed"] = 5

        reporter.print_summary()

        # Check that key stats are in the log calls
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        log_text = " ".join(log_calls)

        assert "100" in log_text  # total_deleted
        assert "5" in log_text  # total_failed

    @patch("src.utils.statistics.logger")
    def test_print_summary_empty_statistics(self, mock_logger):
        """Test handles empty statistics gracefully."""
        reporter = StatisticsReporter()

        # Should not raise
        reporter.print_summary()

        assert mock_logger.info.called


@pytest.mark.unit
class TestStatisticsReporterGenerateReport:
    """Test StatisticsReporter.generate_report() method."""

    def test_generate_report_returns_string(self):
        """Test generates formatted report string."""
        reporter = StatisticsReporter()

        report = reporter.generate_report()

        assert isinstance(report, str)
        assert len(report) > 0

    def test_generate_report_includes_statistics(self):
        """Test includes all statistics."""
        reporter = StatisticsReporter()
        reporter.stats["total_deleted"] = 75
        reporter.stats["total_failed"] = 3

        report = reporter.generate_report()

        assert "75" in report  # total_deleted
        assert "3" in report  # total_failed
        assert "Total Deleted" in report
        assert "Total Failed" in report

    def test_generate_report_includes_elapsed_time(self):
        """Test includes elapsed time."""
        start_time = datetime.now() - timedelta(hours=1)
        reporter = StatisticsReporter(start_time=start_time)

        report = reporter.generate_report()

        assert "Duration" in report
        assert "hour" in report.lower() or "1:" in report

    def test_generate_report_format(self):
        """Test format is correct."""
        reporter = StatisticsReporter()

        report = reporter.generate_report()

        assert "Facebook Cleanup Report" in report
        assert "=" in report  # Separator line
        assert "Start Time" in report
        assert "End Time" in report
        assert "Statistics:" in report

    def test_generate_report_with_state(self):
        """Test includes state information when provided."""
        reporter = StatisticsReporter()
        state = {"current_year": 2020, "current_month": 5, "last_url": "http://example.com"}

        report = reporter.generate_report(state=state)

        assert "Progress State" in report
        assert "2020" in report
        assert "5" in report
        assert "example.com" in report

    def test_generate_report_zero_stats(self):
        """Test handles edge cases (zero stats)."""
        reporter = StatisticsReporter()

        report = reporter.generate_report()

        assert "0" in report
        assert "items/hour" in report

    def test_generate_report_without_state(self):
        """Test works without state parameter."""
        reporter = StatisticsReporter()

        report = reporter.generate_report()

        assert "Progress State" not in report


@pytest.mark.unit
class TestStatisticsReporterAggregation:
    """Test statistics aggregation."""

    def test_multiple_update_from_page_stats(self):
        """Test multiple update_from_page_stats calls aggregate correctly."""
        reporter = StatisticsReporter()

        for i in range(5):
            page_stats = {"deleted": 10, "failed": 1, "errors": [f"err{i}"]}
            reporter.update_from_page_stats(page_stats)

        assert reporter.stats["total_deleted"] == 50
        assert reporter.stats["total_failed"] == 5
        assert reporter.stats["errors_encountered"] == 5

    def test_combining_page_stats_and_state(self):
        """Test combining page stats and state stats."""
        reporter = StatisticsReporter()

        # Update from page stats
        page_stats = {"deleted": 20, "failed": 2}
        reporter.update_from_page_stats(page_stats)

        # Update from state (should overwrite, not add)
        state = {"total_deleted": 100, "errors_encountered": 5}
        reporter.update_from_state(state)

        # State values should be used (not added to page stats)
        assert reporter.stats["total_deleted"] == 100
        assert reporter.stats["errors_encountered"] == 5
        # Failed should remain from page stats (not in state)
        assert reporter.stats["total_failed"] == 2

    def test_counters_increment_correctly(self):
        """Test counters increment correctly."""
        reporter = StatisticsReporter()

        # Initial state
        assert reporter.stats["total_deleted"] == 0

        # First update
        reporter.update_from_page_stats({"deleted": 10})
        assert reporter.stats["total_deleted"] == 10

        # Second update
        reporter.update_from_page_stats({"deleted": 15})
        assert reporter.stats["total_deleted"] == 25

        # Third update
        reporter.update_from_page_stats({"deleted": 5})
        assert reporter.stats["total_deleted"] == 30

    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation is accurate."""
        start_time = datetime.now() - timedelta(hours=2, minutes=30)
        reporter = StatisticsReporter(start_time=start_time)

        stats = reporter.get_stats()

        # Should be approximately 2.5 hours
        assert 2.4 <= stats["elapsed_hours"] <= 2.6

    def test_complex_aggregation_scenario(self):
        """Test complex aggregation scenario with multiple updates."""
        reporter = StatisticsReporter()

        # Multiple page stats updates
        reporter.update_from_page_stats({"deleted": 10, "failed": 1, "skipped": 2})
        reporter.update_from_page_stats({"deleted": 5, "failed": 0, "errors": ["err1"]})
        reporter.update_from_page_stats({"deleted": 15, "skipped": 1, "errors": ["err2", "err3"]})

        # Verify page stats aggregation before state update
        assert reporter.stats["total_deleted"] == 30  # Sum of all deleted
        assert reporter.stats["total_failed"] == 1  # Sum of all failed
        assert reporter.stats["total_skipped"] == 3  # Sum of all skipped
        assert reporter.stats["errors_encountered"] == 3  # Count of all errors

        # Update from state (update_from_state overwrites values, so include them to preserve aggregated values)
        state = {
            "block_detected": True,
            "total_deleted": 30,  # Preserve aggregated total_deleted
            "errors_encountered": 3,  # Preserve aggregated errors_encountered
        }
        reporter.update_from_state(state)

        # Verify final aggregated results
        assert reporter.stats["total_deleted"] == 30  # From state
        assert reporter.stats["total_failed"] == 1  # Preserved from page stats (not in state)
        assert reporter.stats["total_skipped"] == 3  # Preserved from page stats (not in state)
        assert reporter.stats["errors_encountered"] == 3  # From state
        assert reporter.stats["blocks_detected"] == 1  # From state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
