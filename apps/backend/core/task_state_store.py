#!/usr/bin/env python3
"""
Task State Persistence Store
=============================

Atomic persistence layer for background task state with safe file operations.

Uses atomic write operations to prevent corruption during crashes or concurrent access.
All state updates are atomic - either fully written or not at all.

Usage:
    from core.task_state_store import TaskStateStore

    store = TaskStateStore(state_dir)
    store.save_state(task_id, {"status": "running", "output": "..."})
    state = store.load_state(task_id)
    all_tasks = store.load_all_states()
"""

import logging
from pathlib import Path
from typing import Any

from core.file_utils import write_json_atomic

logger = logging.getLogger(__name__)


class TaskStateStore:
    """
    Persistent storage for background task state.

    Features:
    - Atomic writes to prevent corruption
    - Per-task state files for isolation
    - Automatic directory management
    - Safe concurrent access

    Example:
        store = TaskStateStore(Path(".auto-claude/specs/001/.background_tasks"))
        store.save_state("task_123", {
            "status": "running",
            "command": "npm run build",
            "started_at": "2026-02-10T12:00:00Z"
        })
        state = store.load_state("task_123")
    """

    def __init__(self, state_dir: Path | str) -> None:
        """
        Initialize the task state store.

        Args:
            state_dir: Directory for storing task state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_file(self, task_id: str) -> Path:
        """
        Get the state file path for a task.

        Args:
            task_id: Task identifier

        Returns:
            Path to the task state file
        """
        return self.state_dir / f"{task_id}.json"

    def save_state(self, task_id: str, state: dict[str, Any]) -> bool:
        """
        Save task state to disk atomically.

        This operation is atomic - the state file will either be fully written
        or not changed at all. Safe to call during concurrent operations.

        Args:
            task_id: Task identifier
            state: Task state dictionary to persist

        Returns:
            True if saved successfully, False otherwise

        Example:
            success = store.save_state("task_123", {
                "status": "completed",
                "exit_code": 0
            })
        """
        if not task_id or not task_id.strip():
            logger.error("Cannot save state: task_id is empty")
            return False

        if not isinstance(state, dict):
            logger.error(f"Cannot save state for {task_id}: state must be a dict")
            return False

        try:
            state_file = self._get_state_file(task_id)
            write_json_atomic(state_file, state)
            logger.debug(f"Saved task state for {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save task state for {task_id}: {e}", exc_info=True)
            return False

    def load_state(self, task_id: str) -> dict[str, Any] | None:
        """
        Load task state from disk.

        Args:
            task_id: Task identifier

        Returns:
            Task state dict or None if not found or error occurred

        Example:
            state = store.load_state("task_123")
            if state:
                print(f"Status: {state['status']}")
        """
        if not task_id or not task_id.strip():
            logger.error("Cannot load state: task_id is empty")
            return None

        state_file = self._get_state_file(task_id)
        if not state_file.exists():
            logger.debug(f"Task state file not found: {state_file}")
            return None

        try:
            import json

            with open(state_file, encoding="utf-8") as f:
                state = json.load(f)
            logger.debug(f"Loaded task state for {task_id}")
            return state
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse task state for {task_id}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            logger.error(f"Failed to load task state for {task_id}: {e}", exc_info=True)
            return None

    def delete_state(self, task_id: str) -> bool:
        """
        Delete task state from disk.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted successfully or file didn't exist, False on error

        Example:
            store.delete_state("task_123")
        """
        if not task_id or not task_id.strip():
            logger.error("Cannot delete state: task_id is empty")
            return False

        state_file = self._get_state_file(task_id)
        if not state_file.exists():
            logger.debug(f"Task state file already deleted: {state_file}")
            return True

        try:
            state_file.unlink()
            logger.debug(f"Deleted task state for {task_id}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to delete task state for {task_id}: {e}", exc_info=True
            )
            return False

    def list_task_ids(self) -> list[str]:
        """
        List all task IDs with persisted state.

        Returns:
            List of task IDs (sorted by name)

        Example:
            task_ids = store.list_task_ids()
            for task_id in task_ids:
                state = store.load_state(task_id)
                print(f"{task_id}: {state['status']}")
        """
        try:
            task_ids = [f.stem for f in self.state_dir.glob("*.json")]
            return sorted(task_ids)
        except Exception as e:
            logger.error(f"Failed to list task IDs: {e}", exc_info=True)
            return []

    def load_all_states(self) -> dict[str, dict[str, Any]]:
        """
        Load all task states from disk.

        Returns:
            Dict mapping task_id to state dict

        Example:
            all_states = store.load_all_states()
            running_tasks = [
                tid for tid, state in all_states.items()
                if state.get("status") == "running"
            ]
        """
        states = {}
        for task_id in self.list_task_ids():
            state = self.load_state(task_id)
            if state:
                states[task_id] = state
        return states

    def clear_all_states(self) -> int:
        """
        Clear all task states from disk.

        WARNING: This deletes all persisted task data. Use with caution.

        Returns:
            Number of task states deleted

        Example:
            count = store.clear_all_states()
            print(f"Deleted {count} task states")
        """
        count = 0
        for task_id in self.list_task_ids():
            if self.delete_state(task_id):
                count += 1
        return count

    def find_orphaned_tasks(self) -> list[str]:
        """
        Find tasks that were running when app crashed/restarted.

        Orphaned tasks are those with status "running" but no active process.
        These tasks need to be recovered or marked as failed on app restart.

        Returns:
            List of task IDs for orphaned tasks

        Example:
            orphaned = store.find_orphaned_tasks()
            for task_id in orphaned:
                print(f"Task {task_id} was interrupted")
        """
        orphaned_ids = []
        try:
            all_states = self.load_all_states()
            for task_id, state in all_states.items():
                if state.get("status") == "running":
                    orphaned_ids.append(task_id)
            logger.debug(f"Found {len(orphaned_ids)} orphaned tasks")
            return orphaned_ids
        except Exception as e:
            logger.error(f"Failed to find orphaned tasks: {e}", exc_info=True)
            return []

    def mark_task_orphaned(self, task_id: str, reason: str = "App restarted") -> bool:
        """
        Mark a task as orphaned due to app restart or crash.

        Updates task state to indicate it was interrupted and cannot continue.
        Preserves existing output and metadata for debugging.

        Args:
            task_id: Task identifier
            reason: Reason why task was orphaned (default: "App restarted")

        Returns:
            True if marked successfully, False otherwise

        Example:
            store.mark_task_orphaned("task_123", "App crashed")
        """
        if not task_id or not task_id.strip():
            logger.error("Cannot mark task orphaned: task_id is empty")
            return False

        try:
            state = self.load_state(task_id)
            if not state:
                logger.warning(f"Cannot mark non-existent task as orphaned: {task_id}")
                return False

            # Update state to mark as orphaned
            state["status"] = "failed"
            state["error"] = f"Task orphaned: {reason}"
            state["orphaned"] = True

            # Save updated state
            success = self.save_state(task_id, state)
            if success:
                logger.info(f"Marked task {task_id} as orphaned: {reason}")
            return success
        except Exception as e:
            logger.error(
                f"Failed to mark task {task_id} as orphaned: {e}", exc_info=True
            )
            return False

    def recover_on_startup(self) -> dict[str, Any]:
        """
        Recover task state after app restart.

        Finds orphaned tasks and marks them as failed so they don't appear
        as still running. Preserves output and metadata for user review.

        Returns:
            Recovery statistics dict with keys:
            - orphaned_count: Number of tasks that were orphaned
            - marked_count: Number successfully marked as failed
            - failed_count: Number that failed to mark

        Example:
            stats = store.recover_on_startup()
            print(f"Recovered {stats['marked_count']} orphaned tasks")
        """
        stats = {"orphaned_count": 0, "marked_count": 0, "failed_count": 0}

        try:
            orphaned_ids = self.find_orphaned_tasks()
            stats["orphaned_count"] = len(orphaned_ids)

            if not orphaned_ids:
                logger.debug("No orphaned tasks found during startup recovery")
                return stats

            logger.info(f"Recovering {len(orphaned_ids)} orphaned tasks")

            for task_id in orphaned_ids:
                if self.mark_task_orphaned(task_id, "App restarted"):
                    stats["marked_count"] += 1
                else:
                    stats["failed_count"] += 1

            logger.info(
                f"Startup recovery complete: {stats['marked_count']} marked, "
                f"{stats['failed_count']} failed"
            )
            return stats
        except Exception as e:
            logger.error(f"Failed to recover on startup: {e}", exc_info=True)
            return stats
