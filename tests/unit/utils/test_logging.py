"""
Tests for logging utility module.
"""
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.logging import get_logger, setup_logging


@pytest.mark.unit
class TestSetupLogging:
    """Test setup_logging() function."""

    def test_setup_logging_default_log_level(self, tmp_path):
        """Test setup_logging() with default log level."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            assert logger.name == "facebook_cleanup"
            assert logger.level == logging.INFO

    def test_setup_logging_custom_log_level_debug(self, tmp_path):
        """Test setup_logging() with custom DEBUG log level."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging(log_level="DEBUG")

            assert logger.level == logging.DEBUG

    def test_setup_logging_custom_log_level_warning(self, tmp_path):
        """Test setup_logging() with custom WARNING log level."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging(log_level="WARNING")

            assert logger.level == logging.WARNING

    def test_setup_logging_custom_log_level_error(self, tmp_path):
        """Test setup_logging() with custom ERROR log level."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging(log_level="ERROR")

            assert logger.level == logging.ERROR

    def test_setup_logging_logger_name(self, tmp_path):
        """Test logger name is 'facebook_cleanup'."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            assert logger.name == "facebook_cleanup"

    def test_setup_logging_console_handler(self, tmp_path):
        """Test logger has console handler configured."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            # Check console handler exists (FileHandler is also a StreamHandler, so exclude it)
            console_handlers = [
                h
                for h in logger.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
            ]
            assert len(console_handlers) == 1

            console_handler = console_handlers[0]
            assert console_handler.level == logging.INFO
            assert console_handler.formatter is not None

    def test_setup_logging_file_handler(self, tmp_path):
        """Test logger has file handler configured."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            # Check file handler exists
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) == 1

            file_handler = file_handlers[0]
            assert file_handler.level == logging.DEBUG
            assert file_handler.formatter is not None

    def test_setup_logging_file_handler_level(self, tmp_path):
        """Test file handler level is DEBUG."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            file_handler = file_handlers[0]
            assert file_handler.level == logging.DEBUG

    def test_setup_logging_console_handler_level(self, tmp_path):
        """Test console handler level is INFO."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "DEBUG"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            console_handler = console_handlers[0]
            assert console_handler.level == logging.INFO

    def test_setup_logging_format(self, tmp_path):
        """Test log format is correct."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            # Check formatter
            handler = logger.handlers[0]
            formatter = handler.formatter
            assert formatter is not None
            assert "[%(asctime)s] %(levelname)s: %(message)s" in formatter._fmt
            assert "%Y-%m-%d %H:%M:%S" in formatter.datefmt

    def test_setup_logging_handlers_cleared(self, tmp_path):
        """Test handlers are cleared before adding new ones (no duplicates)."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger1 = setup_logging()
            handler_count_1 = len(logger1.handlers)

            logger2 = setup_logging()
            handler_count_2 = len(logger2.handlers)

            # Should have same number of handlers (not doubled)
            assert handler_count_1 == handler_count_2
            # Should have 2 handlers (console + file)
            assert handler_count_2 == 2

    def test_setup_logging_log_file_created(self, tmp_path):
        """Test log file is created in correct directory."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            # Find the file handler and check its path
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            file_handler = file_handlers[0]
            log_file_path = Path(file_handler.baseFilename)

            assert log_file_path.parent == tmp_path
            assert log_file_path.exists()

    def test_setup_logging_log_file_naming_pattern(self, tmp_path):
        """Test log file naming pattern (cleanup_YYYYMMDD_HHMMSS.log)."""
        with patch("src.utils.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_DIR = tmp_path

            logger = setup_logging()

            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            file_handler = file_handlers[0]
            log_file_path = Path(file_handler.baseFilename)

            assert log_file_path.name.startswith("cleanup_")
            assert log_file_path.suffix == ".log"
            # Check format: cleanup_YYYYMMDD_HHMMSS.log
            name_part = log_file_path.stem.replace("cleanup_", "")
            assert len(name_part) == 15  # YYYYMMDD_HHMMSS


@pytest.mark.unit
class TestGetLogger:
    """Test get_logger() function."""

    def test_get_logger_returns_logger_instance(self):
        """Test returns logger instance."""
        logger = get_logger()

        assert isinstance(logger, logging.Logger)

    def test_get_logger_default_name(self):
        """Test with default name ('facebook_cleanup')."""
        logger = get_logger()

        assert logger.name == "facebook_cleanup"

    def test_get_logger_custom_name(self):
        """Test with custom name."""
        custom_name = "test_logger"
        logger = get_logger(custom_name)

        assert logger.name == custom_name

    def test_get_logger_singleton_behavior(self):
        """Test logger is the same instance for same name (singleton behavior)."""
        logger1 = get_logger("test_singleton")
        logger2 = get_logger("test_singleton")

        # Same name should return same logger instance
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test different names return different logger instances."""
        logger1 = get_logger("logger_one")
        logger2 = get_logger("logger_two")

        assert logger1 is not logger2
        assert logger1.name != logger2.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
