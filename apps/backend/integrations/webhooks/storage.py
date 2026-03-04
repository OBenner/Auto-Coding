"""
Webhook Storage Layer
======================

Persistence layer for webhook configurations and logs.
Handles loading and saving webhook data to JSON files in the spec directory.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from .models import WebhookConfig, WebhookLog

logger = logging.getLogger(__name__)

# Process-wide lock so all WebhookStorage instances coordinate writes
_storage_lock = threading.Lock()


@dataclass
class WebhookStorage:
    """
    Storage manager for webhook configurations and logs.

    Handles loading and saving webhook configurations to disk.
    Uses JSON files in the spec directory for persistence.
    """

    spec_dir: Path
    config_file: str = "webhook_configs.json"
    log_file: str = "webhook_logs.json"

    def get_config_path(self) -> Path:
        """Get path to webhook configs file."""
        return self.spec_dir / self.config_file

    def get_log_path(self) -> Path:
        """Get path to webhook logs file."""
        return self.spec_dir / self.log_file

    def load_configs(self) -> list[WebhookConfig]:
        """Load all webhook configurations from disk."""
        config_path = self.get_config_path()
        if not config_path.exists():
            return []

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
                configs = []
                for cfg in data:
                    try:
                        configs.append(WebhookConfig.from_dict(cfg))
                    except Exception as e:
                        logger.warning(f"Skipping invalid webhook config entry: {e}")
                return configs
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return []

    def save_configs(self, configs: list[WebhookConfig]) -> None:
        """Save webhook configurations to disk with restricted permissions."""
        config_path = self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = [cfg.to_dict() for cfg in configs]

        # Write with restricted permissions (owner-only read/write)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(config_path.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            Path(tmp_path).replace(config_path)
            # Restrict file permissions (best-effort on Windows)
            try:
                os.chmod(config_path, 0o600)
            except OSError:
                pass
        except OSError:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def load_logs(
        self, webhook_id: str | None = None, limit: int = 100
    ) -> list[WebhookLog]:
        """
        Load webhook logs from disk.

        Args:
            webhook_id: Optional filter for specific webhook
            limit: Maximum number of logs to return (most recent first)

        Returns:
            List of webhook log entries
        """
        log_path = self.get_log_path()
        if not log_path.exists():
            return []

        try:
            with open(log_path, encoding="utf-8") as f:
                data = json.load(f)
                logs = []
                for log_entry in data:
                    try:
                        logs.append(WebhookLog.from_dict(log_entry))
                    except Exception as e:
                        logger.warning(f"Skipping invalid webhook log entry: {e}")

                # Filter by webhook_id if specified
                if webhook_id:
                    logs = [log for log in logs if log.webhook_id == webhook_id]

                # Sort by created_at descending and limit
                logs.sort(key=lambda log: log.created_at or "", reverse=True)
                return logs[:limit]

        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return []

    def save_log(self, log: WebhookLog) -> None:
        """Append a webhook log entry to disk (thread-safe with atomic write)."""
        log_path = self.get_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with _storage_lock:
            # Load existing logs
            logs = []
            if log_path.exists():
                try:
                    with open(log_path, encoding="utf-8") as f:
                        logs = json.load(f)
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    logs = []

            # Append new log
            logs.append(log.to_dict())

            # Atomic write: write to temp file then replace
            try:
                fd, tmp_path = tempfile.mkstemp(dir=str(log_path.parent), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)
                # Atomic replace (on POSIX; on Windows this is as safe as possible)
                Path(tmp_path).replace(log_path)
            except OSError:
                # Fallback to direct write if atomic replace fails
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)

    def get_config(self, webhook_id: str) -> WebhookConfig | None:
        """Get a specific webhook configuration by ID."""
        configs = self.load_configs()
        for cfg in configs:
            if cfg.id == webhook_id:
                return cfg
        return None

    def save_config(self, config: WebhookConfig) -> None:
        """Save or update a webhook configuration (thread-safe)."""
        with _storage_lock:
            configs = self.load_configs()

            # Update existing or append new
            updated = False
            for i, cfg in enumerate(configs):
                if cfg.id == config.id:
                    configs[i] = config
                    updated = True
                    break

            if not updated:
                configs.append(config)

            self.save_configs(configs)

    def delete_config(self, webhook_id: str) -> bool:
        """Delete a webhook configuration (thread-safe)."""
        with _storage_lock:
            configs = self.load_configs()
            original_count = len(configs)
            configs = [cfg for cfg in configs if cfg.id != webhook_id]

            if len(configs) < original_count:
                self.save_configs(configs)
                return True
            return False

    def clear_logs(self, webhook_id: str | None = None) -> int:
        """
        Clear webhook logs from disk (thread-safe).

        Args:
            webhook_id: Optional filter for specific webhook.
                       If None, clears all logs.

        Returns:
            Number of logs cleared
        """
        with _storage_lock:
            log_path = self.get_log_path()
            if not log_path.exists():
                return 0

            try:
                with open(log_path, encoding="utf-8") as f:
                    logs = json.load(f)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                return 0

            original_count = len(logs)

            if webhook_id:
                # Filter out logs for this webhook
                logs = [log for log in logs if log.get("webhook_id") != webhook_id]
            else:
                # Clear all logs
                logs = []

            # Atomic write
            try:
                fd, tmp_path = tempfile.mkstemp(dir=str(log_path.parent), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)
                Path(tmp_path).replace(log_path)
            except OSError:
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)

            return original_count - len(logs)
