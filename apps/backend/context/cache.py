"""
Cache management for preloaded file content.
"""

import json
import time
from pathlib import Path
from typing import Any


class ContextCache:
    """Manages caching of preloaded file contents."""

    CACHE_VALIDITY_HOURS = 24

    def __init__(self, cache_dir: Path | None):
        """
        Initialize context cache.

        Args:
            cache_dir: Directory to store cache files (None for testing)
        """
        if cache_dir is None:
            self.cache_dir = None
            self.cache_file = None
            return

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "preloaded_context.json"

    def get_cached_content(
        self, file_path: str, skip_cache: bool = False
    ) -> dict[str, Any] | None:
        """
        Retrieve cached file content if valid.

        Args:
            file_path: Path to the file to retrieve from cache
            skip_cache: If True, always return None (force reload)

        Returns:
            Cached file metadata and content or None if cache invalid/expired
        """
        if skip_cache or self.cache_file is None:
            return None

        if not self.cache_file.exists():
            return None

        try:
            cache_data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Check if this specific file is cached
        if file_path not in cache_data:
            return None

        cached_entry = cache_data[file_path]

        # Check if cache entry has expired
        cache_age = time.time() - cached_entry.get("cached_at", 0)
        hours_old = cache_age / 3600

        if hours_old >= self.CACHE_VALIDITY_HOURS:
            return None

        # Check if file has been modified since caching
        try:
            file_obj = Path(file_path)
            if not file_obj.exists():
                # File no longer exists, invalidate cache
                return None

            current_mtime = file_obj.stat().st_mtime
            cached_mtime = cached_entry.get("file_mtime", 0)

            if current_mtime != cached_mtime:
                # File has been modified, invalidate cache
                return None
        except (OSError, PermissionError):
            # Can't access file, invalidate cache
            return None

        return cached_entry

    def save_content(
        self, file_path: str, content: str, file_mtime: float
    ) -> None:
        """
        Save file content to cache.

        Args:
            file_path: Path to the file being cached
            content: File content to cache
            file_mtime: File modification time (timestamp)
        """
        if self.cache_file is None:
            return

        # Load existing cache or create new
        if self.cache_file.exists():
            try:
                cache_data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                cache_data = {}
        else:
            cache_data = {}

        # Add new entry
        cache_data[file_path] = {
            "content": content,
            "file_mtime": file_mtime,
            "cached_at": time.time(),
        }

        # Save back to disk
        self.cache_file.write_text(
            json.dumps(cache_data, indent=2), encoding="utf-8"
        )

    def clear_cache(self) -> None:
        """Clear all cached content."""
        if self.cache_file and self.cache_file.exists():
            self.cache_file.unlink()

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (file count, total size, oldest entry)
        """
        if self.cache_file is None or not self.cache_file.exists():
            return {"file_count": 0, "total_size_kb": 0, "oldest_hours": 0}

        try:
            cache_data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"file_count": 0, "total_size_kb": 0, "oldest_hours": 0}

        if not cache_data:
            return {"file_count": 0, "total_size_kb": 0, "oldest_hours": 0}

        # Calculate stats
        total_size = sum(
            len(entry.get("content", "")) for entry in cache_data.values()
        )
        oldest_time = min(
            entry.get("cached_at", time.time()) for entry in cache_data.values()
        )
        oldest_hours = (time.time() - oldest_time) / 3600

        return {
            "file_count": len(cache_data),
            "total_size_kb": total_size / 1024,
            "oldest_hours": oldest_hours,
        }
