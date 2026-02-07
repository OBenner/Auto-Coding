"""
File Prioritization with Recency Scoring
=========================================

Prioritizes files based on recent modifications to focus on actively
developed code. Uses git timestamps when available, falls back to
filesystem modification times.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .models import FileMatch


class FilePrioritizer:
    """Prioritizes files based on modification recency and relevance."""

    def __init__(self, project_dir: str | Path):
        """
        Initialize the file prioritizer.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = Path(project_dir).resolve()
        self._is_git_repo = (self.project_dir / ".git").exists()
        self._recency_cache: dict[str, float] = {}

    def prioritize_matches(
        self,
        matches: list[FileMatch],
        max_results: int | None = None,
    ) -> list[FileMatch]:
        """
        Prioritize file matches by combining relevance and recency scores.

        Args:
            matches: List of FileMatch objects to prioritize
            max_results: Maximum number of results to return (None for all)

        Returns:
            Prioritized list of FileMatch objects with updated scores
        """
        if not matches:
            return []

        # Calculate recency scores for all matches
        for match in matches:
            recency_score = self._get_recency_score(match.path)
            # Combine relevance (keyword matching) with recency
            # 70% relevance, 30% recency for balanced prioritization
            combined_score = (match.relevance_score * 0.7) + (recency_score * 0.3)
            match.relevance_score = combined_score

        # Sort by combined score
        sorted_matches = sorted(
            matches, key=lambda m: m.relevance_score, reverse=True
        )

        if max_results:
            return sorted_matches[:max_results]
        return sorted_matches

    def _get_recency_score(self, file_path: str) -> float:
        """
        Calculate recency score for a file (0-10 scale).

        More recent files get higher scores. Uses exponential decay:
        - Files modified today: 10
        - Files modified this week: 7-9
        - Files modified this month: 4-6
        - Files modified this year: 1-3
        - Older files: 0-1

        Args:
            file_path: Relative path to the file

        Returns:
            Recency score from 0 to 10
        """
        # Check cache first
        if file_path in self._recency_cache:
            return self._recency_cache[file_path]

        # Get modification timestamp
        timestamp = self._get_file_timestamp(file_path)
        if timestamp is None:
            return 0.0

        # Calculate age in days
        now = datetime.now(timezone.utc)
        age_days = (now - timestamp).total_seconds() / 86400  # seconds in a day

        # Exponential decay scoring
        if age_days < 1:
            score = 10.0
        elif age_days < 7:
            score = 9.0 - (age_days - 1) / 6 * 2  # 9 to 7
        elif age_days < 30:
            score = 7.0 - (age_days - 7) / 23 * 3  # 7 to 4
        elif age_days < 365:
            score = 4.0 - (age_days - 30) / 335 * 3  # 4 to 1
        else:
            score = max(0.0, 1.0 - (age_days - 365) / 365)  # 1 to 0

        # Cache the result
        self._recency_cache[file_path] = score
        return score

    def _get_file_timestamp(self, file_path: str) -> datetime | None:
        """
        Get file modification timestamp from git or filesystem.

        Prefers git timestamps for more accurate tracking of when code
        was actually changed (ignoring checkout times).

        Args:
            file_path: Relative path to the file

        Returns:
            Datetime of last modification, or None if file doesn't exist
        """
        full_path = self.project_dir / file_path

        if not full_path.exists():
            return None

        # Try git first if available
        if self._is_git_repo:
            git_timestamp = self._get_git_timestamp(file_path)
            if git_timestamp:
                return git_timestamp

        # Fallback to filesystem mtime
        try:
            mtime = full_path.stat().st_mtime
            return datetime.fromtimestamp(mtime, tz=timezone.utc)
        except OSError:
            return None

    def _get_git_timestamp(self, file_path: str) -> datetime | None:
        """
        Get the last git commit timestamp for a file.

        Args:
            file_path: Relative path to the file

        Returns:
            Datetime of last commit, or None if not in git
        """
        try:
            # Use git log to get last commit timestamp
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "-1",
                    "--format=%ct",  # Commit timestamp (Unix epoch)
                    "--",
                    file_path,
                ],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                timestamp = int(result.stdout.strip())
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
            pass

        return None

    def get_most_recent_files(
        self, file_paths: list[str], max_results: int = 10
    ) -> list[tuple[str, float]]:
        """
        Get the most recently modified files from a list.

        Args:
            file_paths: List of relative file paths
            max_results: Maximum number of files to return

        Returns:
            List of (file_path, recency_score) tuples, sorted by recency
        """
        scored_files = [
            (path, self._get_recency_score(path)) for path in file_paths
        ]
        scored_files.sort(key=lambda x: x[1], reverse=True)
        return scored_files[:max_results]

    def clear_cache(self):
        """Clear the recency score cache."""
        self._recency_cache.clear()
