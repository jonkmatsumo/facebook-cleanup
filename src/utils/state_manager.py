"""
Progress state manager for saving and loading operation state.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, cast

from src.utils.logging import get_logger

logger = get_logger(__name__)


class StateManager:
    """Manages progress state persistence for resumable operations."""

    def __init__(self, progress_path: Path):
        """
        Initialize StateManager.

        Args:
            progress_path: Path to progress JSON file
        """
        self.progress_path = progress_path
        self._state: Optional[Dict[str, Any]] = None

        # Ensure directory exists
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"StateManager initialized with path: {self.progress_path}")

    def get_state(self) -> Dict[str, Any]:
        """
        Get current state (loads from file if not already loaded).

        Returns:
            State dictionary
        """
        if self._state is None:
            self._state = self.load_state() or self._default_state()

        return self._state

    def save_state(self, state: Optional[Dict[str, Any]] = None) -> None:
        """
        Save progress state to JSON file.

        Args:
            state: State dictionary to save (uses current state if None)
        """
        if state is None:
            state = self.get_state()

        # Update last_updated timestamp
        state["last_updated"] = datetime.now().isoformat()

        try:
            # Create backup if file exists
            if self.progress_path.exists():
                backup_path = self.progress_path.with_suffix(".json.bak")
                shutil.copy2(self.progress_path, backup_path)
                logger.debug(f"Created backup: {backup_path}")

            # Write to temp file first (atomic write)
            temp_path = self.progress_path.with_suffix(".json.tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.progress_path)

            # Update in-memory state
            self._state = state.copy()

            logger.debug(f"State saved to {self.progress_path}")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            # Don't raise - state save failure shouldn't stop the operation

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load progress state from JSON file.

        Returns:
            State dictionary or None if file doesn't exist or is corrupted
        """
        if not self.progress_path.exists():
            logger.debug("Progress file does not exist, using default state")
            return None

        try:
            with open(self.progress_path, encoding="utf-8") as f:
                state = json.load(f)

            # Validate state structure
            if self._validate_state(state):
                self._state = state
                logger.info(f"State loaded from {self.progress_path}")
                return cast(Dict[str, Any], state)
            else:
                logger.warning("Invalid state structure, using default state")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON in progress file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None

    def update_state(self, **kwargs) -> None:
        """
        Update specific state fields.

        Args:
            **kwargs: State fields to update
        """
        state = self.get_state()
        state.update(kwargs)
        self.save_state(state)

    def clear_state(self) -> None:
        """Clear progress state (delete file)."""
        try:
            if self.progress_path.exists():
                self.progress_path.unlink()
                logger.info("Progress state cleared")

            self._state = None

        except Exception as e:
            logger.error(f"Failed to clear state: {e}")

    def _default_state(self) -> Dict[str, Any]:
        """
        Get default state structure.

        Returns:
            Default state dictionary
        """
        return {
            "last_updated": datetime.now().isoformat(),
            "current_year": None,
            "current_month": None,
            "current_category": None,
            "total_deleted": 0,
            "deleted_today": 0,
            "last_url": None,
            "errors_encountered": 0,
            "block_detected": False,
            "block_count": 0,
            "session_start": datetime.now().isoformat(),
        }

    def _validate_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate state structure.

        Args:
            state: State dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        # Check for required fields (at least some basic structure)
        if not isinstance(state, dict):
            return False

        # Check for common fields (flexible - allow additional fields)
        expected_fields = [
            "last_updated",
            "total_deleted",
            "errors_encountered",
            "block_detected",
        ]

        # At least some expected fields should be present
        has_expected = any(field in state for field in expected_fields)

        return has_expected
