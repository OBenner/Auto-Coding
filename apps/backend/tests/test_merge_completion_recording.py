"""
Unit tests for Merge Completion Recording
===========================================

Tests the MergeCompletionRecord dataclass and FileEvolutionTracker's
merge completion recording functionality.
"""

# IMPORTANT: This sys.path manipulation must happen BEFORE importing pytest
# to ensure we import from the actual modules, not tests module
import sys
from pathlib import Path


def _configure_sys_path() -> None:
    """Configure sys.path to import from the actual modules."""
    for td in [p for p in sys.path if "tests" in p]:
        if td in sys.path:
            sys.path.remove(td)
    backend_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_root))


_configure_sys_path()

import json
import shutil
from datetime import datetime
from unittest.mock import patch

import pytest
from merge.file_evolution.tracker import (
    FileEvolutionTracker,
    MergeCompletionRecord,
)


@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for testing."""
    storage_dir = tmp_path / ".auto-claude" / "file_evolution"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@pytest.fixture
def tracker(temp_project_dir: Path, temp_storage_dir: Path) -> FileEvolutionTracker:
    """Create a FileEvolutionTracker with temporary storage."""
    return FileEvolutionTracker(
        project_dir=temp_project_dir,
        storage_dir=temp_storage_dir,
    )


class TestMergeCompletionRecord:
    """Test suite for MergeCompletionRecord dataclass."""

    def test_merge_completion_record_creation(self):
        """Test creating a MergeCompletionRecord with all fields."""
        record = MergeCompletionRecord(
            merge_id="merge_123456_abc123",
            timestamp=datetime.now(),
            task_ids=["task-001", "task-002"],
            resolved_files=["src/main.py", "src/utils.py"],
            success=True,
            error=None,
        )

        assert record.merge_id == "merge_123456_abc123"
        assert len(record.task_ids) == 2
        assert len(record.resolved_files) == 2
        assert record.success is True
        assert record.error is None

    def test_merge_completion_record_default_values(self):
        """Test MergeCompletionRecord with default values."""
        record = MergeCompletionRecord(
            merge_id="merge_test",
            timestamp=datetime.now(),
        )

        assert record.task_ids == []
        assert record.resolved_files == []
        assert record.success is True
        assert record.error is None

    def test_merge_completion_record_failed_merge(self):
        """Test MergeCompletionRecord for a failed merge."""
        record = MergeCompletionRecord(
            merge_id="merge_failed",
            timestamp=datetime.now(),
            task_ids=["task-001"],
            resolved_files=[],
            success=False,
            error="Conflict resolution failed",
        )

        assert record.success is False
        assert record.error == "Conflict resolution failed"
        assert record.resolved_files == []

    def test_to_dict(self):
        """Test converting MergeCompletionRecord to dictionary."""
        timestamp = datetime.now()
        record = MergeCompletionRecord(
            merge_id="merge_test",
            timestamp=timestamp,
            task_ids=["task-001", "task-002"],
            resolved_files=["file1.py", "file2.py"],
            success=True,
        )

        data = record.to_dict()

        assert data["merge_id"] == "merge_test"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["task_ids"] == ["task-001", "task-002"]
        assert data["resolved_files"] == ["file1.py", "file2.py"]
        assert data["success"] is True

    def test_from_dict(self):
        """Test creating MergeCompletionRecord from dictionary."""
        timestamp = datetime.now()
        data = {
            "merge_id": "merge_test",
            "timestamp": timestamp.isoformat(),
            "task_ids": ["task-001"],
            "resolved_files": ["test.py"],
            "success": True,
            "error": None,
        }

        record = MergeCompletionRecord.from_dict(data)

        assert record.merge_id == "merge_test"
        assert record.timestamp == timestamp
        assert record.task_ids == ["task-001"]
        assert record.resolved_files == ["test.py"]
        assert record.success is True

    def test_from_dict_with_missing_optional_fields(self):
        """Test from_dict handles missing optional fields."""
        timestamp = datetime.now()
        data = {
            "merge_id": "merge_test",
            "timestamp": timestamp.isoformat(),
        }

        record = MergeCompletionRecord.from_dict(data)

        assert record.merge_id == "merge_test"
        assert record.task_ids == []
        assert record.resolved_files == []
        assert record.success is True  # Default value
        assert record.error is None

    def test_files_resolved_count_property(self):
        """Test files_resolved_count property."""
        record = MergeCompletionRecord(
            merge_id="merge_test",
            timestamp=datetime.now(),
            resolved_files=["file1.py", "file2.py", "file3.py"],
        )

        assert record.files_resolved_count == 3

    def test_tasks_merged_count_property(self):
        """Test tasks_merged_count property."""
        record = MergeCompletionRecord(
            merge_id="merge_test",
            timestamp=datetime.now(),
            task_ids=["task-001", "task-002", "task-003"],
        )

        assert record.tasks_merged_count == 3

    def test_serialization_round_trip(self):
        """Test that to_dict and from_dict are inverses."""
        original = MergeCompletionRecord(
            merge_id="merge_test",
            timestamp=datetime.now(),
            task_ids=["task-001", "task-002"],
            resolved_files=["file1.py"],
            success=True,
            error="Test error",
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = MergeCompletionRecord.from_dict(data)

        assert restored.merge_id == original.merge_id
        assert restored.timestamp == original.timestamp
        assert restored.task_ids == original.task_ids
        assert restored.resolved_files == original.resolved_files
        assert restored.success == original.success
        assert restored.error == original.error


class TestRecordMergeCompletion:
    """Test suite for record_merge_completion method."""

    def test_record_successful_merge(self, tracker: FileEvolutionTracker):
        """Test recording a successful merge completion."""
        task_ids = ["task-001", "task-002"]
        resolved_files = ["src/main.py", "src/utils.py"]

        record = tracker.record_merge_completion(
            task_ids=task_ids,
            resolved_files=resolved_files,
            success=True,
        )

        assert record.success is True
        assert record.task_ids == task_ids
        assert record.resolved_files == resolved_files
        assert record.merge_id.startswith("merge_")
        assert isinstance(record.timestamp, datetime)

    def test_record_failed_merge(self, tracker: FileEvolutionTracker):
        """Test recording a failed merge completion."""
        record = tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=[],
            success=False,
            error="Merge conflict could not be resolved",
        )

        assert record.success is False
        assert record.error == "Merge conflict could not be resolved"
        assert record.resolved_files == []

    def test_merge_id_format(self, tracker: FileEvolutionTracker):
        """Test that merge_id follows expected format."""
        record = tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["test.py"],
        )

        # Format: merge_{timestamp}_{hash}
        assert record.merge_id.startswith("merge_")
        parts = record.merge_id.split("_")
        assert len(parts) >= 3  # merge, timestamp, hash

    def test_merge_id_unique(self, tracker: FileEvolutionTracker):
        """Test that each merge gets a unique ID."""
        record1 = tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["test.py"],
        )
        record2 = tracker.record_merge_completion(
            task_ids=["task-002"],
            resolved_files=["test.py"],
        )

        assert record1.merge_id != record2.merge_id

    def test_merge_with_multiple_tasks(self, tracker: FileEvolutionTracker):
        """Test recording merge with multiple tasks."""
        task_ids = [f"task-{i:03d}" for i in range(1, 6)]
        resolved_files = [f"src/file{i}.py" for i in range(3)]

        record = tracker.record_merge_completion(
            task_ids=task_ids,
            resolved_files=resolved_files,
        )

        assert len(record.task_ids) == 5
        assert len(record.resolved_files) == 3
        assert record.tasks_merged_count == 5
        assert record.files_resolved_count == 3


class TestGetMergeCompletionHistory:
    """Test suite for get_merge_completion_history method."""

    def test_empty_history(self, tracker: FileEvolutionTracker):
        """Test getting history when no merges recorded."""
        history = tracker.get_merge_completion_history()

        assert history == []

    def test_get_single_record(self, tracker: FileEvolutionTracker):
        """Test getting history with one record."""
        tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["test.py"],
        )

        history = tracker.get_merge_completion_history()

        assert len(history) == 1
        assert history[0].task_ids == ["task-001"]
        assert history[0].resolved_files == ["test.py"]

    def test_get_multiple_records(self, tracker: FileEvolutionTracker):
        """Test getting history with multiple records."""
        # Record 3 merges
        for i in range(3):
            tracker.record_merge_completion(
                task_ids=[f"task-{i:03d}"],
                resolved_files=[f"file{i}.py"],
            )

        history = tracker.get_merge_completion_history()

        assert len(history) == 3

    def test_history_ordering(self, tracker: FileEvolutionTracker):
        """Test that history maintains insertion order."""
        # Record merges with slight delays to ensure different timestamps
        import time

        records = []
        for i in range(3):
            record = tracker.record_merge_completion(
                task_ids=[f"task-{i:03d}"],
                resolved_files=[f"file{i}.py"],
            )
            records.append(record)
            if i < 2:  # Don't sleep after last one
                time.sleep(1.1)  # Sleep >1 second to ensure different timestamps

        history = tracker.get_merge_completion_history()

        # History maintains insertion order (oldest first)
        assert history[0].merge_id == records[0].merge_id
        assert history[1].merge_id == records[1].merge_id
        assert history[2].merge_id == records[2].merge_id

    def test_limit_parameter(self, tracker: FileEvolutionTracker):
        """Test limit parameter restricts number of records returned."""
        # Record 5 merges
        for i in range(5):
            tracker.record_merge_completion(
                task_ids=[f"task-{i:03d}"],
                resolved_files=[f"file{i}.py"],
            )

        # Request only 3
        history = tracker.get_merge_completion_history(limit=3)

        assert len(history) == 3

    def test_filter_by_task_id(self, tracker: FileEvolutionTracker):
        """Test filtering history by task_id."""
        # Record merges with different task combinations
        tracker.record_merge_completion(
            task_ids=["task-001", "task-002"],
            resolved_files=["file1.py"],
        )
        tracker.record_merge_completion(
            task_ids=["task-002", "task-003"],
            resolved_files=["file2.py"],
        )
        tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["file3.py"],
        )

        # Filter for task-001
        history = tracker.get_merge_completion_history(task_id="task-001")

        assert len(history) == 2
        # All returned records should involve task-001
        assert all("task-001" in r.task_ids for r in history)

    def test_filter_by_nonexistent_task_id(self, tracker: FileEvolutionTracker):
        """Test filtering by task_id that doesn't exist."""
        tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["file.py"],
        )

        history = tracker.get_merge_completion_history(task_id="task-999")

        assert len(history) == 0


class TestPersistence:
    """Test suite for merge completion persistence."""

    def test_merge_completion_persists_to_disk(
        self, tracker: FileEvolutionTracker, temp_storage_dir: Path
    ):
        """Test that merge completion is saved to disk."""
        tracker.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["test.py"],
        )

        # Check that file was created
        merge_file = temp_storage_dir / "merge_history.json"
        assert merge_file.exists()

    def test_merge_completion_data_correct_on_disk(
        self, tracker: FileEvolutionTracker, temp_storage_dir: Path
    ):
        """Test that merge completion data is correctly written to disk."""
        record = tracker.record_merge_completion(
            task_ids=["task-001", "task-002"],
            resolved_files=["file1.py", "file2.py"],
            success=True,
        )

        # Read from disk
        merge_file = temp_storage_dir / "merge_history.json"
        with open(merge_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["merge_id"] == record.merge_id
        assert data[0]["task_ids"] == ["task-001", "task-002"]
        assert data[0]["resolved_files"] == ["file1.py", "file2.py"]

    def test_multiple_merges_persist_to_disk(
        self, tracker: FileEvolutionTracker, temp_storage_dir: Path
    ):
        """Test that multiple merge completions are saved to disk."""
        # Record multiple merges
        for i in range(3):
            tracker.record_merge_completion(
                task_ids=[f"task-{i:03d}"],
                resolved_files=[f"file{i}.py"],
            )

        # Read from disk
        merge_file = temp_storage_dir / "merge_history.json"
        with open(merge_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 3

    def test_history_loads_from_disk(
        self, temp_project_dir: Path, temp_storage_dir: Path
    ):
        """Test that history can be loaded from disk."""
        # Create first tracker instance and record merge
        tracker1 = FileEvolutionTracker(
            project_dir=temp_project_dir,
            storage_dir=temp_storage_dir,
        )
        tracker1.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["test.py"],
        )

        # Create second tracker instance (should load from disk)
        tracker2 = FileEvolutionTracker(
            project_dir=temp_project_dir,
            storage_dir=temp_storage_dir,
        )
        history = tracker2.get_merge_completion_history()

        assert len(history) == 1
        assert history[0].task_ids == ["task-001"]

    def test_persistence_across_sessions(
        self, temp_project_dir: Path, temp_storage_dir: Path
    ):
        """Test that merge completion persists across tracker instances."""
        # First session: record a merge
        tracker1 = FileEvolutionTracker(
            project_dir=temp_project_dir,
            storage_dir=temp_storage_dir,
        )
        record1 = tracker1.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["test.py"],
        )
        merge_id = record1.merge_id

        # Second session: verify merge is still there
        tracker2 = FileEvolutionTracker(
            project_dir=temp_project_dir,
            storage_dir=temp_storage_dir,
        )
        history = tracker2.get_merge_completion_history()

        assert len(history) == 1
        assert history[0].merge_id == merge_id

    def test_append_to_existing_history(
        self, temp_project_dir: Path, temp_storage_dir: Path
    ):
        """Test that new merges are appended to existing history."""
        # First session: record one merge
        tracker1 = FileEvolutionTracker(
            project_dir=temp_project_dir,
            storage_dir=temp_storage_dir,
        )
        tracker1.record_merge_completion(
            task_ids=["task-001"],
            resolved_files=["file1.py"],
        )

        # Second session: add another merge
        tracker2 = FileEvolutionTracker(
            project_dir=temp_project_dir,
            storage_dir=temp_storage_dir,
        )
        tracker2.record_merge_completion(
            task_ids=["task-002"],
            resolved_files=["file2.py"],
        )

        # Verify both merges are in history
        history = tracker2.get_merge_completion_history()
        assert len(history) == 2
