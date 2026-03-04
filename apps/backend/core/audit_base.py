"""
Shared Audit Logger Infrastructure
====================================

Base class for audit loggers providing common file management, rotation,
and singleton infrastructure. Used by both enterprise and GitHub audit loggers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseAuditLogger:
    """
    Base audit logger with shared infrastructure.

    Provides:
    - Log file management (daily JSONL files)
    - Log rotation by file size
    - Old log cleanup by retention policy
    - Singleton pattern support
    - Correlation ID generation
    """

    _instance: BaseAuditLogger | None = None

    def __init__(
        self,
        log_dir: Path,
        retention_days: int = 30,
        max_file_size_mb: int = 100,
        enabled: bool = True,
    ):
        self.log_dir = log_dir
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb
        self.enabled = enabled

        if enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._current_log_file: Path | None = None
            self._rotate_if_needed()

    @classmethod
    def get_instance(
        cls, log_dir: Path | None = None, **kwargs: Any
    ) -> BaseAuditLogger:
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(log_dir=log_dir, **kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def _get_log_file_path(self) -> Path:
        """Get path for current day's log file."""
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{date_str}.jsonl"

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds max size."""
        if not self.enabled:
            return

        log_file = self._get_log_file_path()

        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb >= self.max_file_size_mb:
                timestamp = datetime.now(UTC).strftime("%H%M%S")
                rotated = log_file.with_suffix(f".{timestamp}.jsonl")
                log_file.rename(rotated)
                logger.info(f"Rotated audit log to {rotated}")

        self._current_log_file = log_file

    def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period."""
        if not self.enabled or not self.log_dir.exists():
            return

        cutoff = datetime.now(UTC).timestamp() - (self.retention_days * 24 * 60 * 60)

        for log_file in self.log_dir.glob("audit_*.jsonl"):
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                logger.info(f"Deleted old audit log: {log_file}")

    def _write_entry(self, entry: Any) -> None:
        """Write an entry to the log file. Entry must have to_json() method."""
        if not self.enabled:
            return

        self._rotate_if_needed()

        try:
            log_file = self._get_log_file_path()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for an operation."""
        return f"audit-{uuid.uuid4().hex[:12]}"
