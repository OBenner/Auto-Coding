"""
File Evolution Tracker - Main Orchestration Class
==================================================

Main entry point that orchestrates the modular components:
- EvolutionStorage: File storage and persistence
- BaselineCapture: Baseline state capture
- ModificationTracker: Modification recording
- EvolutionQueries: Query and analysis methods
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..semantic_analyzer import SemanticAnalyzer
from ..types import FileEvolution, TaskSnapshot
from .baseline_capture import DEFAULT_EXTENSIONS, BaselineCapture
from .evolution_queries import EvolutionQueries
from .modification_tracker import ModificationTracker
from .storage import EvolutionStorage

# Import debug utilities
try:
    from debug import debug, debug_success
except ImportError:

    def debug(*args, **kwargs):
        """No-op fallback when debug module is unavailable."""

    def debug_success(*args, **kwargs):
        """No-op fallback when debug module is unavailable."""


logger = logging.getLogger(__name__)
MODULE = "merge.file_evolution"


@dataclass
class MergeCompletionRecord:
    """
    Record of a completed merge operation.

    Captures the outcome of a merge operation for historical tracking
    and learning from past merges.
    """

    # Unique identification
    merge_id: str  # Format: "merge_{timestamp}_{task_ids_hash}"
    timestamp: datetime

    # Tasks involved
    task_ids: list[str] = field(default_factory=list)

    # Files resolved
    resolved_files: list[str] = field(default_factory=list)

    # Merge outcome
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "merge_id": self.merge_id,
            "timestamp": self.timestamp.isoformat(),
            "task_ids": self.task_ids,
            "resolved_files": self.resolved_files,
            "success": self.success,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MergeCompletionRecord:
        """Create record from dictionary."""
        return cls(
            merge_id=data["merge_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            task_ids=data.get("task_ids", []),
            resolved_files=data.get("resolved_files", []),
            success=data.get("success", True),
            error=data.get("error"),
        )

    @property
    def files_resolved_count(self) -> int:
        """Get number of files resolved in this merge."""
        return len(self.resolved_files)

    @property
    def tasks_merged_count(self) -> int:
        """Get number of tasks merged."""
        return len(self.task_ids)


class FileEvolutionTracker:
    """
    Tracks file evolution across task modifications.

    This class manages:
    - Baseline capture when worktrees are created
    - File content snapshots in .auto-claude/baselines/
    - Task modification tracking with semantic analysis
    - Persistence of evolution data

    Usage:
        tracker = FileEvolutionTracker(project_dir)

        # When creating a worktree for a task
        tracker.capture_baselines(task_id, files_to_track)

        # When a task modifies a file
        tracker.record_modification(task_id, file_path, old_content, new_content)

        # When preparing to merge
        evolution = tracker.get_file_evolution(file_path)
    """

    # Re-export default extensions for backward compatibility
    DEFAULT_EXTENSIONS = DEFAULT_EXTENSIONS

    def __init__(
        self,
        project_dir: Path,
        storage_dir: Path | None = None,
        semantic_analyzer: SemanticAnalyzer | None = None,
    ):
        """
        Initialize the file evolution tracker.

        Args:
            project_dir: Root directory of the project
            storage_dir: Directory for evolution data (default: .auto-claude/)
            semantic_analyzer: Optional pre-configured analyzer
        """
        debug(MODULE, "Initializing FileEvolutionTracker", project_dir=str(project_dir))

        self.project_dir = Path(project_dir).resolve()
        storage_dir = storage_dir or (self.project_dir / ".auto-claude")

        # Initialize modular components
        self.storage = EvolutionStorage(self.project_dir, storage_dir)
        self.baseline_capture = BaselineCapture(
            self.storage, extensions=self.DEFAULT_EXTENSIONS
        )
        self.modification_tracker = ModificationTracker(
            self.storage,
            semantic_analyzer=semantic_analyzer,
        )
        self.queries = EvolutionQueries(self.storage)

        # Load existing evolution data
        self._evolutions: dict[str, FileEvolution] = self.storage.load_evolutions()

        debug_success(
            MODULE,
            "FileEvolutionTracker initialized",
            evolutions_loaded=len(self._evolutions),
        )

    # Expose storage_dir and baselines_dir for backward compatibility
    @property
    def storage_dir(self) -> Path:
        """Get the storage directory."""
        return self.storage.storage_dir

    @property
    def baselines_dir(self) -> Path:
        """Get the baselines directory."""
        return self.storage.baselines_dir

    @property
    def evolution_file(self) -> Path:
        """Get the evolution file path."""
        return self.storage.evolution_file

    def _save_evolutions(self) -> None:
        """Persist evolution data to disk."""
        self.storage.save_evolutions(self._evolutions)

    def capture_baselines(
        self,
        task_id: str,
        files: list[Path | str] | None = None,
        intent: str = "",
    ) -> dict[str, FileEvolution]:
        """
        Capture baseline state of files for a task.

        Call this when creating a worktree for a new task.

        Args:
            task_id: Unique identifier for the task
            files: List of files to capture. If None, discovers trackable files.
            intent: Description of what the task intends to do

        Returns:
            Dictionary mapping file paths to their FileEvolution objects
        """
        captured = self.baseline_capture.capture_baselines(
            task_id=task_id,
            files=files,
            intent=intent,
            evolutions=self._evolutions,
        )
        self._save_evolutions()
        logger.info(f"Captured baselines for {len(captured)} files for task {task_id}")
        return captured

    def record_modification(
        self,
        task_id: str,
        file_path: Path | str,
        old_content: str,
        new_content: str,
        raw_diff: str | None = None,
    ) -> TaskSnapshot | None:
        """
        Record a file modification by a task.

        Call this after a task makes changes to a file.

        Args:
            task_id: The task that made the modification
            file_path: Path to the modified file
            old_content: File content before modification
            new_content: File content after modification
            raw_diff: Optional unified diff for reference

        Returns:
            Updated TaskSnapshot, or None if file not being tracked
        """
        snapshot = self.modification_tracker.record_modification(
            task_id=task_id,
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
            evolutions=self._evolutions,
            raw_diff=raw_diff,
        )
        self._save_evolutions()
        return snapshot

    def get_file_evolution(self, file_path: Path | str) -> FileEvolution | None:
        """
        Get the complete evolution history for a file.

        Args:
            file_path: Path to the file

        Returns:
            FileEvolution object, or None if not tracked
        """
        return self.queries.get_file_evolution(file_path, self._evolutions)

    def get_baseline_content(self, file_path: Path | str) -> str | None:
        """
        Get the baseline content for a file.

        Args:
            file_path: Path to the file

        Returns:
            Original baseline content, or None if not available
        """
        return self.queries.get_baseline_content(file_path, self._evolutions)

    def get_task_modifications(
        self,
        task_id: str,
    ) -> list[tuple[str, TaskSnapshot]]:
        """
        Get all file modifications made by a specific task.

        Args:
            task_id: The task identifier

        Returns:
            List of (file_path, TaskSnapshot) tuples
        """
        return self.queries.get_task_modifications(task_id, self._evolutions)

    def get_files_modified_by_tasks(
        self,
        task_ids: list[str],
    ) -> dict[str, list[str]]:
        """
        Get files modified by specified tasks.

        Args:
            task_ids: List of task identifiers

        Returns:
            Dictionary mapping file paths to list of task IDs that modified them
        """
        return self.queries.get_files_modified_by_tasks(task_ids, self._evolutions)

    def get_conflicting_files(self, task_ids: list[str]) -> list[str]:
        """
        Get files modified by multiple tasks (potential conflicts).

        Args:
            task_ids: List of task identifiers to check

        Returns:
            List of file paths modified by 2+ tasks
        """
        return self.queries.get_conflicting_files(task_ids, self._evolutions)

    def mark_task_completed(self, task_id: str) -> None:
        """
        Mark a task as completed (set completed_at on all snapshots).

        Args:
            task_id: The task identifier
        """
        self.modification_tracker.mark_task_completed(task_id, self._evolutions)
        self._save_evolutions()

    def cleanup_task(
        self,
        task_id: str,
        remove_baselines: bool = True,
    ) -> None:
        """
        Clean up data for a completed/cancelled task.

        Args:
            task_id: The task identifier
            remove_baselines: Whether to remove stored baseline files
        """
        self._evolutions = self.queries.cleanup_task(
            task_id=task_id,
            evolutions=self._evolutions,
            remove_baselines=remove_baselines,
        )
        self._save_evolutions()

    def get_active_tasks(self) -> set[str]:
        """
        Get set of task IDs with active (non-completed) modifications.

        Returns:
            Set of task IDs
        """
        return self.queries.get_active_tasks(self._evolutions)

    def get_evolution_summary(self) -> dict:
        """
        Get a summary of tracked file evolutions.

        Returns:
            Dictionary with summary statistics
        """
        return self.queries.get_evolution_summary(self._evolutions)

    def export_for_merge(
        self,
        file_path: Path | str,
        task_ids: list[str] | None = None,
    ) -> dict | None:
        """
        Export evolution data for a file in a format suitable for merge.

        This provides the data needed by the merge system to understand
        what each task did and in what order.

        Args:
            file_path: Path to the file
            task_ids: Optional list of tasks to include (default: all)

        Returns:
            Dictionary with merge-relevant evolution data
        """
        return self.queries.export_for_merge(
            file_path=file_path,
            evolutions=self._evolutions,
            task_ids=task_ids,
        )

    def refresh_from_git(
        self,
        task_id: str,
        worktree_path: Path,
        target_branch: str | None = None,
        analyze_only_files: set[str] | None = None,
    ) -> None:
        """
        Refresh task snapshots by analyzing git diff from worktree.

        This is useful when we didn't capture real-time modifications
        and need to retroactively analyze what a task changed.

        Args:
            task_id: The task identifier
            worktree_path: Path to the task's worktree
            target_branch: Branch to compare against (default: auto-detect)
            analyze_only_files: If provided, only run full semantic analysis on
                these files. Other files will be tracked with lightweight mode
                (no semantic analysis). This optimizes performance by only
                analyzing files that have actual conflicts.
        """
        self.modification_tracker.refresh_from_git(
            task_id=task_id,
            worktree_path=worktree_path,
            evolutions=self._evolutions,
            target_branch=target_branch,
            analyze_only_files=analyze_only_files,
        )
        self._save_evolutions()

    def record_merge_completion(
        self,
        task_ids: list[str],
        resolved_files: list[str],
        success: bool = True,
        error: str | None = None,
    ) -> MergeCompletionRecord:
        """
        Record the completion of a merge operation.

        This method captures the outcome of a merge for historical tracking
        and learning from past merges.

        Args:
            task_ids: List of task IDs that were merged
            resolved_files: List of file paths that were resolved
            success: Whether the merge completed successfully
            error: Optional error message if merge failed

        Returns:
            The created MergeCompletionRecord
        """
        # Generate unique merge ID
        timestamp = datetime.now()
        task_ids_hash = hashlib.md5(
            ",".join(sorted(task_ids)).encode("utf-8")
        ).hexdigest()[:8]
        merge_id = f"merge_{int(timestamp.timestamp())}_{task_ids_hash}"

        # Create merge completion record
        record = MergeCompletionRecord(
            merge_id=merge_id,
            timestamp=timestamp,
            task_ids=task_ids,
            resolved_files=resolved_files,
            success=success,
            error=error,
        )

        # Load existing merge history
        merge_history = self.storage.load_merge_history()

        # Append new record
        merge_history.append(record.to_dict())

        # Save updated history
        self.storage.save_merge_history(merge_history)

        # Log the operation
        if success:
            debug_success(
                MODULE,
                f"Recorded successful merge {merge_id}",
                tasks_merged=len(task_ids),
                files_resolved=len(resolved_files),
            )
            logger.info(
                f"Recorded successful merge {merge_id}: "
                f"{len(task_ids)} tasks, {len(resolved_files)} files"
            )
        else:
            logger.warning(
                f"Recorded failed merge {merge_id}: {error}"
            )

        return record
