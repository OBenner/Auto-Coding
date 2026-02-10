"""
User File Priority Management
==============================

Manages user-provided file priority hints for context selection.
Allows users to override automatic file selection with explicit priorities.
"""

import fnmatch
import json
from logging import getLogger
from pathlib import Path

from .models import FileMatch

logger = getLogger(__name__)


class PriorityManager:
    """Manages user-provided file priority hints for context optimization."""

    # Priority levels (higher = more important)
    PRIORITY_LEVELS = {
        "never": -100,
        "low": -1,
        "normal": 0,
        "medium": 1,
        "high": 2,
        "always": 100,
    }

    def __init__(self, project_dir: Path):
        """
        Initialize priority manager.

        Args:
            project_dir: Root directory of the project
        """
        self.project_dir = Path(project_dir).resolve()
        self.priority_file = self.project_dir / ".auto-claude" / "context-priority.json"
        self.priorities = self._load_priorities()

    def _load_priorities(self) -> dict:
        """
        Load priority configuration from JSON file.

        Returns:
            Dictionary with priority rules, or empty dict if file doesn't exist
        """
        try:
            if self.priority_file.exists():
                with open(self.priority_file, encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Loaded priority rules from {self.priority_file}")
                    return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load priority file: {e}")

        return {}

    def get_priority(self, file_path: str) -> int:
        """
        Get priority level for a specific file.

        Args:
            file_path: Path to the file (relative to project root)

        Returns:
            Priority score (higher = more important)
        """
        # Check explicit file matches
        if file_path in self.priorities:
            level = self.priorities[file_path].get("priority", "normal")
            return self.PRIORITY_LEVELS.get(level, 0)

        # Check pattern matches
        for pattern, config in self.priorities.items():
            if fnmatch.fnmatch(file_path, pattern):
                level = config.get("priority", "normal")
                return self.PRIORITY_LEVELS.get(level, 0)

        # Default priority
        return 0

    def filter_by_priority(
        self,
        matches: list[FileMatch],
        exclude_never: bool = True,
    ) -> list[FileMatch]:
        """
        Filter matches based on user priorities.

        Args:
            matches: List of FileMatch objects to filter
            exclude_never: Whether to exclude files marked as "never" priority

        Returns:
            Filtered list of FileMatch objects
        """
        filtered = []

        for match in matches:
            priority = self.get_priority(match.path)

            # Skip files marked as "never"
            if exclude_never and priority <= -100:
                logger.debug(f"Excluding {match.path} (user priority: never)")
                continue

            # Add priority score to relevance score
            match.relevance_score += priority
            filtered.append(match)

        return filtered

    def sort_by_priority(self, matches: list[FileMatch]) -> list[FileMatch]:
        """
        Sort matches by user priority (highest first).

        Args:
            matches: List of FileMatch objects to sort

        Returns:
            Sorted list of FileMatch objects
        """
        return sorted(
            matches,
            key=lambda m: (
                self.get_priority(m.path),
                m.relevance_score,
            ),
            reverse=True,
        )

    def apply_priorities(
        self,
        matches: list[FileMatch],
        exclude_never: bool = True,
        sort: bool = True,
    ) -> list[FileMatch]:
        """
        Apply user priorities to a list of file matches.

        Args:
            matches: List of FileMatch objects
            exclude_never: Whether to exclude files marked as "never" priority
            sort: Whether to sort results by priority

        Returns:
            Filtered and sorted list of FileMatch objects
        """
        # First filter out "never" files and adjust scores
        result = self.filter_by_priority(matches, exclude_never)

        # Then sort by priority if requested
        if sort:
            result = self.sort_by_priority(result)

        return result

    def get_priority_info(self, file_path: str) -> dict | None:
        """
        Get detailed priority information for a file.

        Args:
            file_path: Path to the file (relative to project root)

        Returns:
            Dictionary with priority info, or None if no priority set
        """
        # Check explicit file matches
        if file_path in self.priorities:
            return self.priorities[file_path]

        # Check pattern matches
        for pattern, config in self.priorities.items():
            if fnmatch.fnmatch(file_path, pattern):
                return config

        return None
