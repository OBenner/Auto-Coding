"""
Preview Store
==============

Storage and retrieval for conflict resolution previews.

This module provides file system storage for ResolutionPreview objects,
allowing users to review, approve, or reject AI-suggested merge resolutions
before applying them to the codebase.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from .types import ResolutionPreview

logger = logging.getLogger(__name__)


class PreviewStore:
    """
    File system storage for resolution previews.

    Stores AI-suggested merge resolutions with their explanations,
    enabling a preview/approval workflow before applying merges.

    Attributes:
        preview_dir: Directory where preview files are stored
        preview_file: JSON file containing all previews for a merge operation
    """

    def __init__(self, auto_claude_dir: str | Path):
        """
        Initialize the preview store.

        Args:
            auto_claude_dir: Path to .auto-claude directory
        """
        self.preview_dir = Path(auto_claude_dir) / "previews"
        self.preview_file = self.preview_dir / "resolution_previews.json"

        # Create directory if it doesn't exist
        self.preview_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Preview store initialized at {self.preview_dir}")

    def save_previews(
        self,
        previews: list[ResolutionPreview],
        merge_id: str | None = None,
    ) -> None:
        """
        Save resolution previews to disk.

        Args:
            previews: List of resolution previews to save
            merge_id: Optional merge operation ID for namespacing
        """
        try:
            # Load existing previews
            existing = self._load_all_previews()

            # Use merge_id as key, or "default" if not provided
            key = merge_id or "default"

            # Update previews for this merge operation
            existing[key] = [p.to_dict() for p in previews]

            # Atomic write: write to a temp file then rename to avoid partial writes
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=self.preview_dir, prefix=".previews_", suffix=".tmp"
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(existing, f, indent=2)
                Path(tmp_path).replace(self.preview_file)
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise

            logger.info(f"Saved {len(previews)} resolution previews for merge '{key}'")

        except Exception as e:
            logger.error(f"Failed to save previews: {e}")
            raise

    def load_previews(
        self,
        merge_id: str | None = None,
    ) -> list[ResolutionPreview]:
        """
        Load resolution previews from disk.

        Args:
            merge_id: Optional merge operation ID to load specific previews

        Returns:
            List of resolution previews
        """
        try:
            all_previews = self._load_all_previews()

            # Get previews for specific merge_id or default
            key = merge_id or "default"
            preview_data = all_previews.get(key, [])

            previews = [ResolutionPreview.from_dict(p) for p in preview_data]
            logger.debug(f"Loaded {len(previews)} resolution previews for '{key}'")
            return previews

        except Exception as e:
            logger.error(f"Failed to load previews: {e}")
            return []

    def get_preview_for_file(
        self,
        file_path: str,
        merge_id: str | None = None,
    ) -> ResolutionPreview | None:
        """
        Get the resolution preview for a specific file.

        Args:
            file_path: Path to the file
            merge_id: Optional merge operation ID

        Returns:
            ResolutionPreview if found, None otherwise
        """
        previews = self.load_previews(merge_id)

        for preview in previews:
            if preview.file_path == file_path:
                return preview

        return None

    def clear_previews(self, merge_id: str | None = None) -> None:
        """
        Clear resolution previews from storage.

        Args:
            merge_id: Optional merge operation ID to clear specific previews.
                     If None, clears all previews.
        """
        try:
            if merge_id is None:
                # Clear all previews
                if self.preview_file.exists():
                    self.preview_file.unlink()
                logger.info("Cleared all resolution previews")
            else:
                # Clear specific merge operation's previews
                all_previews = self._load_all_previews()
                if merge_id in all_previews:
                    del all_previews[merge_id]

                    tmp_fd, tmp_path = tempfile.mkstemp(
                        dir=self.preview_dir, prefix=".previews_", suffix=".tmp"
                    )
                    try:
                        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                            json.dump(all_previews, f, indent=2)
                        Path(tmp_path).replace(self.preview_file)
                    except Exception:
                        Path(tmp_path).unlink(missing_ok=True)
                        raise

                    logger.info(f"Cleared resolution previews for merge '{merge_id}'")

        except Exception as e:
            logger.error(f"Failed to clear previews: {e}")

    def list_merge_ids(self) -> list[str]:
        """
        List all merge operation IDs that have stored previews.

        Returns:
            List of merge operation IDs
        """
        try:
            all_previews = self._load_all_previews()
            return list(all_previews.keys())
        except Exception as e:
            logger.error(f"Failed to list merge IDs: {e}")
            return []

    def _load_all_previews(self) -> dict[str, list[dict[str, Any]]]:
        """
        Load all previews from disk.

        Returns:
            Dictionary mapping merge_id -> list of preview dicts
        """
        if not self.preview_file.exists():
            return {}

        try:
            with open(self.preview_file, encoding="utf-8") as f:
                data = json.load(f)

            # Handle legacy format (list of previews) by converting to dict
            if isinstance(data, list):
                logger.info("Converting legacy preview format to new format")
                return {"default": data}

            # Validate structure: must be a dict with list values
            if not isinstance(data, dict):
                logger.warning("Unexpected preview file structure; resetting to empty")
                return {}
            for k, v in list(data.items()):
                if not isinstance(v, list):
                    logger.warning("Dropping malformed preview entry '%s'", k)
                    del data[k]

            return data

        except Exception as e:
            logger.error(f"Failed to load preview file: {e}")
            return {}
