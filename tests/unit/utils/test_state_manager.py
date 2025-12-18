"""
Tests for StateManager class.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from src.utils.state_manager import StateManager


@pytest.mark.unit
class TestStateManagerInit:
    """Test StateManager.__init__() method."""

    def test_init_creates_directory(self, tmp_path):
        """Test creates progress_path.parent directory if it doesn't exist."""
        progress_file = tmp_path / "subdir" / "progress.json"
        assert not progress_file.parent.exists()

        StateManager(progress_file)

        assert progress_file.parent.exists()

    def test_init_initializes_progress_path(self, tmp_path):
        """Test initializes with correct progress_path."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)

        assert manager.progress_path == progress_file

    def test_init_state_is_none(self, tmp_path):
        """Test _state is None initially."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)

        assert manager._state is None

    def test_init_existing_directory(self, tmp_path):
        """Test doesn't fail if directory already exists."""
        progress_file = tmp_path / "progress.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)

        # Should not raise
        StateManager(progress_file)

        # Verify directory still exists
        assert progress_file.parent.exists()


@pytest.mark.unit
class TestStateManagerGetState:
    """Test StateManager.get_state() method."""

    def test_get_state_no_file_default_state(self, tmp_path):
        """Test returns default state when file doesn't exist."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state = manager.get_state()

        assert isinstance(state, dict)
        assert "last_updated" in state
        assert "total_deleted" in state
        assert "errors_encountered" in state
        assert state["total_deleted"] == 0

    def test_get_state_existing_file(self, tmp_path):
        """Test returns loaded state when file exists."""
        progress_file = tmp_path / "progress.json"

        # Create state file
        saved_state = {
            "last_updated": "2024-01-01T00:00:00",
            "total_deleted": 100,
            "errors_encountered": 5,
            "block_detected": False,
        }
        with open(progress_file, "w") as f:
            json.dump(saved_state, f)

        manager = StateManager(progress_file)
        state = manager.get_state()

        assert state["total_deleted"] == 100
        assert state["errors_encountered"] == 5

    def test_get_state_caches_state(self, tmp_path):
        """Test loads from file only once (caches in _state)."""
        progress_file = tmp_path / "progress.json"

        saved_state = {
            "last_updated": "2024-01-01T00:00:00",
            "total_deleted": 50,
            "errors_encountered": 2,
            "block_detected": False,
        }
        with open(progress_file, "w") as f:
            json.dump(saved_state, f)

        manager = StateManager(progress_file)
        state1 = manager.get_state()

        # Modify file
        saved_state["total_deleted"] = 999
        with open(progress_file, "w") as f:
            json.dump(saved_state, f)

        # Should return cached state, not reloaded
        state2 = manager.get_state()
        assert state1 is state2
        assert state2["total_deleted"] == 50  # Original value, not 999

    def test_get_state_default_structure(self, tmp_path):
        """Test default state structure matches expected fields."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state = manager.get_state()

        expected_fields = [
            "last_updated",
            "current_year",
            "current_month",
            "current_category",
            "total_deleted",
            "deleted_today",
            "last_url",
            "errors_encountered",
            "block_detected",
            "block_count",
            "session_start",
        ]

        for field in expected_fields:
            assert field in state, f"Missing field: {field}"


@pytest.mark.unit
class TestStateManagerLoadState:
    """Test StateManager.load_state() method."""

    def test_load_state_file_not_exists(self, tmp_path):
        """Test returns None when file doesn't exist."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state = manager.load_state()

        assert state is None

    def test_load_state_valid_file(self, tmp_path):
        """Test returns state dictionary when file exists with valid JSON."""
        progress_file = tmp_path / "progress.json"

        saved_state = {
            "last_updated": "2024-01-01T00:00:00",
            "total_deleted": 42,
            "errors_encountered": 1,
            "block_detected": False,
        }
        with open(progress_file, "w") as f:
            json.dump(saved_state, f)

        manager = StateManager(progress_file)
        state = manager.load_state()

        assert state is not None
        assert state["total_deleted"] == 42

    def test_load_state_corrupted_json(self, tmp_path):
        """Test returns None when JSON is corrupted (JSONDecodeError)."""
        progress_file = tmp_path / "progress.json"

        # Write invalid JSON
        with open(progress_file, "w") as f:
            f.write("not valid json {")

        manager = StateManager(progress_file)
        state = manager.load_state()

        assert state is None

    def test_load_state_invalid_structure(self, tmp_path):
        """Test validates state structure (returns None for invalid structure)."""
        progress_file = tmp_path / "progress.json"

        # Write JSON that doesn't match expected structure
        invalid_state = {"not_a_valid_field": "value"}
        with open(progress_file, "w") as f:
            json.dump(invalid_state, f)

        manager = StateManager(progress_file)
        state = manager.load_state()

        # Should return None because no expected fields are present
        assert state is None

    def test_load_state_updates_state_attribute(self, tmp_path):
        """Test updates _state after successful load."""
        progress_file = tmp_path / "progress.json"

        saved_state = {
            "last_updated": "2024-01-01T00:00:00",
            "total_deleted": 10,
            "errors_encountered": 0,
            "block_detected": False,
        }
        with open(progress_file, "w") as f:
            json.dump(saved_state, f)

        manager = StateManager(progress_file)
        assert manager._state is None

        manager.load_state()

        assert manager._state is not None
        assert manager._state["total_deleted"] == 10


@pytest.mark.unit
class TestStateManagerSaveState:
    """Test StateManager.save_state() method."""

    def test_save_state_creates_file(self, tmp_path):
        """Test saves state to file with correct JSON format."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state = {"total_deleted": 25, "errors_encountered": 3, "block_detected": False}
        manager.save_state(state)

        assert progress_file.exists()

        with open(progress_file) as f:
            loaded = json.load(f)

        assert loaded["total_deleted"] == 25
        assert "last_updated" in loaded

    def test_save_state_creates_backup(self, tmp_path):
        """Test creates backup (.json.bak) if file exists."""
        progress_file = tmp_path / "progress.json"
        backup_file = tmp_path / "progress.json.bak"

        manager = StateManager(progress_file)

        # Save initial state
        initial_state = {"total_deleted": 10, "errors_encountered": 0, "block_detected": False}
        manager.save_state(initial_state)

        # Save updated state
        updated_state = {"total_deleted": 20, "errors_encountered": 1, "block_detected": False}
        manager.save_state(updated_state)

        assert backup_file.exists()

        # Verify backup contains original state
        with open(backup_file) as f:
            backup_state = json.load(f)

        assert backup_state["total_deleted"] == 10

    def test_save_state_atomic_write(self, tmp_path):
        """Test atomic write (uses .json.tmp then rename)."""
        progress_file = tmp_path / "progress.json"
        temp_file = tmp_path / "progress.json.tmp"

        manager = StateManager(progress_file)
        state = {"total_deleted": 15, "errors_encountered": 2, "block_detected": False}

        # Monitor file operations
        manager.save_state(state)

        # Temp file should not exist after save (it's renamed)
        assert not temp_file.exists()
        assert progress_file.exists()

    def test_save_state_updates_in_memory_state(self, tmp_path):
        """Test updates _state in memory after save."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state = {"total_deleted": 30, "errors_encountered": 4, "block_detected": False}

        manager.save_state(state)

        assert manager._state is not None
        assert manager._state["total_deleted"] == 30

    def test_save_state_updates_timestamp(self, tmp_path):
        """Test updates last_updated timestamp."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state = {"total_deleted": 5, "errors_encountered": 0, "block_detected": False}

        manager.save_state(state)

        with open(progress_file) as f:
            loaded = json.load(f)

        # Should have last_updated timestamp
        assert "last_updated" in loaded
        # Should be valid ISO format
        datetime.fromisoformat(loaded["last_updated"])

    def test_save_state_uses_current_state_if_none(self, tmp_path):
        """Test saves provided state or current state if None."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        initial_state = manager.get_state()  # Get default state
        initial_state["total_deleted"] = 40

        # Save without argument should use current state
        manager._state = initial_state
        manager.save_state()  # No argument

        with open(progress_file) as f:
            loaded = json.load(f)

        assert loaded["total_deleted"] == 40


@pytest.mark.unit
class TestStateManagerUpdateState:
    """Test StateManager.update_state() method."""

    def test_update_state_updates_fields(self, tmp_path):
        """Test updates existing state fields."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        initial_state = manager.get_state()
        initial_state["total_deleted"] = 50
        manager.save_state(initial_state)

        manager.update_state(total_deleted=100)

        updated_state = manager.get_state()
        assert updated_state["total_deleted"] == 100

    def test_update_state_adds_new_fields(self, tmp_path):
        """Test adds new fields to state."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        manager.update_state(custom_field="custom_value")

        state = manager.get_state()
        assert state["custom_field"] == "custom_value"

    def test_update_state_calls_save_state(self, tmp_path):
        """Test calls save_state() after update."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        manager.update_state(total_deleted=75)

        # Verify file was updated
        with open(progress_file) as f:
            loaded = json.load(f)

        assert loaded["total_deleted"] == 75

    def test_update_state_multiple_fields(self, tmp_path):
        """Test updates multiple fields at once."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        manager.update_state(total_deleted=200, errors_encountered=10, block_detected=True)

        state = manager.get_state()
        assert state["total_deleted"] == 200
        assert state["errors_encountered"] == 10
        assert state["block_detected"] is True


@pytest.mark.unit
class TestStateManagerClearState:
    """Test StateManager.clear_state() method."""

    def test_clear_state_deletes_file(self, tmp_path):
        """Test deletes progress file if it exists."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        manager.save_state({"total_deleted": 10, "errors_encountered": 0, "block_detected": False})
        assert progress_file.exists()

        manager.clear_state()

        assert not progress_file.exists()

    def test_clear_state_sets_state_to_none(self, tmp_path):
        """Test sets _state to None."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        manager.get_state()  # Load state
        assert manager._state is not None

        manager.clear_state()

        assert manager._state is None

    def test_clear_state_no_file_no_error(self, tmp_path):
        """Test doesn't raise error if file doesn't exist."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)

        # Should not raise
        manager.clear_state()
        assert manager._state is None


@pytest.mark.unit
class TestStateManagerDefaultState:
    """Test StateManager._default_state() method."""

    def test_default_state_returns_dict(self, tmp_path):
        """Test returns dictionary with all expected fields."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        default_state = manager._default_state()

        assert isinstance(default_state, dict)
        assert "last_updated" in default_state
        assert "total_deleted" in default_state
        assert default_state["total_deleted"] == 0

    def test_default_state_correct_defaults(self, tmp_path):
        """Test fields have correct default values."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        default_state = manager._default_state()

        assert default_state["total_deleted"] == 0
        assert default_state["errors_encountered"] == 0
        assert default_state["block_detected"] is False
        assert default_state["block_count"] == 0
        assert default_state["current_year"] is None
        assert default_state["current_month"] is None

    def test_default_state_last_updated_format(self, tmp_path):
        """Test last_updated is ISO format timestamp."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        default_state = manager._default_state()

        # Should be valid ISO format
        datetime.fromisoformat(default_state["last_updated"])

    def test_default_state_session_start_format(self, tmp_path):
        """Test session_start is ISO format timestamp."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        default_state = manager._default_state()

        # Should be valid ISO format
        datetime.fromisoformat(default_state["session_start"])


@pytest.mark.unit
class TestStateManagerValidateState:
    """Test StateManager._validate_state() method."""

    def test_validate_state_valid_dict(self, tmp_path):
        """Test returns True for valid state dictionary."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        valid_state = {
            "last_updated": "2024-01-01T00:00:00",
            "total_deleted": 10,
            "errors_encountered": 0,
            "block_detected": False,
        }

        assert manager._validate_state(valid_state) is True

    def test_validate_state_non_dict(self, tmp_path):
        """Test returns False for non-dictionary input."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)

        assert manager._validate_state("not a dict") is False
        assert manager._validate_state([]) is False
        assert manager._validate_state(123) is False
        assert manager._validate_state(None) is False

    def test_validate_state_no_expected_fields(self, tmp_path):
        """Test returns False when no expected fields present."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        invalid_state = {"random_field": "value"}

        assert manager._validate_state(invalid_state) is False

    def test_validate_state_some_expected_fields(self, tmp_path):
        """Test returns True when at least some expected fields present."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)

        # Should pass with just one expected field
        state_with_one = {"last_updated": "2024-01-01T00:00:00"}
        assert manager._validate_state(state_with_one) is True

        state_with_another = {"total_deleted": 10}
        assert manager._validate_state(state_with_another) is True

    def test_validate_state_allows_additional_fields(self, tmp_path):
        """Test is flexible (allows additional fields)."""
        progress_file = tmp_path / "progress.json"

        manager = StateManager(progress_file)
        state_with_extras = {
            "last_updated": "2024-01-01T00:00:00",
            "total_deleted": 10,
            "custom_field": "custom_value",
            "another_field": 123,
        }

        assert manager._validate_state(state_with_extras) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
