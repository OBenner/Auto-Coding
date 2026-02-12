"""
Version History System for Collaborative Spec Editing
====================================================

Manager for spec version history with diff support.
Tracks all changes, provides diff views, and supports approval workflow.
"""

from __future__ import annotations

import difflib
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from collaboration.models import Version, load_versions, save_versions

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class DiffResult:
    """Result of a diff operation between two versions."""

    def __init__(
        self,
        added: list[str],
        removed: list[str],
        unchanged: list[str],
        line_numbers: dict[str, list[tuple[int, int]]] | None = None,
    ):
        """Initialize diff result.

        Args:
            added: List of added lines
            removed: List of removed lines
            unchanged: List of unchanged lines
            line_numbers: Optional mapping of line numbers for each section
        """
        self.added = added
        self.removed = removed
        self.unchanged = unchanged
        self.line_numbers = line_numbers or {}

    def to_dict(self) -> dict:
        """Convert diff result to dictionary.

        Returns:
            Dictionary representation of the diff
        """
        return {
            "added": self.added,
            "removed": self.removed,
            "unchanged": self.unchanged,
            "line_numbers": self.line_numbers,
        }

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes.

        Returns:
            True if there are additions or deletions
        """
        return bool(self.added or self.removed)


class VersionManager:
    """Manager for spec version history with diff support.

    Provides a complete audit trail of all changes to a specification,
    including the ability to compare versions and revert changes.
    """

    def __init__(self, spec_dir: Path):
        """Initialize the version manager.

        Args:
            spec_dir: Path to the spec directory
        """
        self.spec_dir = spec_dir
        self._versions_cache: list[Version] | None = None

    def load_versions(self) -> list[Version]:
        """Load versions from disk.

        Returns:
            List of all versions for this spec
        """
        if self._versions_cache is None:
            self._versions_cache = load_versions(self.spec_dir)
            logger.debug(
                "Loaded %d versions from %s",
                len(self._versions_cache),
                self.spec_dir,
            )
        return self._versions_cache

    def save_versions(self, versions: list[Version] | None = None) -> bool:
        """Save versions to disk.

        Args:
            versions: Optional list of versions (uses cache if None)

        Returns:
            True if save was successful
        """
        versions_to_save = versions if versions is not None else self._versions_cache
        if versions_to_save is None:
            logger.warning("No versions to save")
            return False

        try:
            save_versions(self.spec_dir, versions_to_save)
            self._versions_cache = versions_to_save
            logger.debug(
                "Saved %d versions to %s",
                len(versions_to_save),
                self.spec_dir,
            )
            return True
        except Exception as e:
            logger.error("Failed to save versions: %s", e)
            return False

    def create_version(
        self,
        author: str,
        author_name: str,
        content: str,
        commit_message: str | None = None,
    ) -> Version | None:
        """Create a new version.

        Args:
            author: Author identifier
            author_name: Display name of author
            content: Full spec content
            commit_message: Optional description of changes

        Returns:
            Created version or None if creation failed
        """
        versions = self.load_versions()

        # Determine next version number
        next_version = len(versions) + 1

        # Get previous version ID
        previous_id = versions[-1].id if versions else None

        # Create new version
        version = Version(
            id=str(uuid.uuid4()),
            spec_id=self.spec_dir.name,
            version_number=next_version,
            author=author,
            author_name=author_name,
            content=content,
            commit_message=commit_message,
            previous_version_id=previous_id,
            created_at=datetime.utcnow(),
            is_approved=False,
        )

        versions.append(version)

        if self.save_versions(versions):
            logger.info(
                "Created version %d by %s for spec %s",
                next_version,
                author,
                self.spec_dir.name,
            )
            return version

        return None

    def get_version(self, version_id: str) -> Version | None:
        """Get a specific version by ID.

        Args:
            version_id: Version identifier

        Returns:
            Version or None if not found
        """
        versions = self.load_versions()
        for version in versions:
            if version.id == version_id:
                return version
        return None

    def get_version_by_number(self, version_number: int) -> Version | None:
        """Get a specific version by number.

        Args:
            version_number: Version number

        Returns:
            Version or None if not found
        """
        versions = self.load_versions()
        for version in versions:
            if version.version_number == version_number:
                return version
        return None

    def get_all_versions(self) -> list[Version]:
        """Get all versions for this spec.

        Returns:
            List of all versions, sorted by version number
        """
        versions = self.load_versions()
        return sorted(versions, key=lambda v: v.version_number)

    def get_latest_version(self) -> Version | None:
        """Get the latest version.

        Returns:
            Latest version or None if no versions exist
        """
        versions = self.get_all_versions()
        return versions[-1] if versions else None

    def get_approved_version(self) -> Version | None:
        """Get the latest approved version.

        Returns:
            Latest approved version or None if no approved version exists
        """
        versions = self.get_all_versions()
        for version in reversed(versions):
            if version.is_approved:
                return version
        return None

    def approve_version(
        self,
        version_id: str,
        approved_by: str,
    ) -> bool:
        """Mark a version as approved.

        Args:
            version_id: Version to approve
            approved_by: User approving the version

        Returns:
            True if approval was successful
        """
        versions = self.load_versions()

        for version in versions:
            if version.id == version_id:
                version.is_approved = True
                version.approved_by = approved_by
                version.approved_at = datetime.utcnow()

                if self.save_versions(versions):
                    logger.info(
                        "Approved version %s by %s",
                        version_id,
                        approved_by,
                    )
                    return True
                return False

        logger.warning("Version not found for approval: %s", version_id)
        return False

    def unapprove_version(self, version_id: str) -> bool:
        """Remove approval from a version.

        Args:
            version_id: Version to unapprove

        Returns:
            True if successful
        """
        versions = self.load_versions()

        for version in versions:
            if version.id == version_id:
                version.is_approved = False
                version.approved_by = None
                version.approved_at = None

                if self.save_versions(versions):
                    logger.info("Unapproved version %s", version_id)
                    return True
                return False

        logger.warning("Version not found for unapproval: %s", version_id)
        return False

    def diff_versions(
        self,
        version_id1: str,
        version_id2: str | None = None,
    ) -> DiffResult | None:
        """Generate a diff between two versions.

        Args:
            version_id1: First version ID (older)
            version_id2: Second version ID (newer). If None, compares with latest

        Returns:
            DiffResult or None if versions not found
        """
        version1 = self.get_version(version_id1)
        if not version1:
            logger.warning("Version not found for diff: %s", version_id1)
            return None

        # If no second version, compare with latest
        if version_id2 is None:
            version2 = self.get_latest_version()
            if not version2:
                logger.warning("No latest version found for diff")
                return None
        else:
            version2 = self.get_version(version_id2)
            if not version2:
                logger.warning("Version not found for diff: %s", version_id2)
                return None

        return self._compute_diff(version1.content, version2.content)

    def diff_with_previous(self, version_id: str) -> DiffResult | None:
        """Generate a diff between a version and its previous version.

        Args:
            version_id: Version ID

        Returns:
            DiffResult or None if versions not found
        """
        version = self.get_version(version_id)
        if not version:
            logger.warning("Version not found for diff: %s", version_id)
            return None

        if not version.previous_version_id:
            # No previous version - return empty diff
            return DiffResult(added=[], removed=[], unchanged=[])

        previous_version = self.get_version(version.previous_version_id)
        if not previous_version:
            logger.warning(
                "Previous version not found: %s",
                version.previous_version_id,
            )
            return None

        return self._compute_diff(previous_version.content, version.content)

    def _compute_diff(self, content1: str, content2: str) -> DiffResult:
        """Compute diff between two content strings.

        Args:
            content1: Original content
            content2: New content

        Returns:
            DiffResult with added, removed, and unchanged lines
        """
        lines1 = content1.splitlines(keepends=True)
        lines2 = content2.splitlines(keepends=True)

        # Use difflib to compute differences
        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))

        added = []
        removed = []
        unchanged = []

        line_num1 = 0
        line_num2 = 0
        line_numbers: dict[str, list[tuple[int, int]]] = {
            "added": [],
            "removed": [],
        }

        for line in diff:
            if line.startswith("  "):
                # Unchanged line
                unchanged.append(line[2:])
                line_num1 += 1
                line_num2 += 1
            elif line.startswith("+ "):
                # Added line
                added.append(line[2:])
                line_numbers["added"].append((line_num2, len(added) - 1))
                line_num2 += 1
            elif line.startswith("- "):
                # Removed line
                removed.append(line[2:])
                line_numbers["removed"].append((line_num1, len(removed) - 1))
                line_num1 += 1
            elif line.startswith("? "):
                # Line change indicator - skip
                pass

        return DiffResult(
            added=added,
            removed=removed,
            unchanged=unchanged,
            line_numbers=line_numbers,
        )

    def get_version_history(self, limit: int | None = None) -> list[dict]:
        """Get version history summary.

        Args:
            limit: Optional limit on number of versions to return

        Returns:
            List of version summaries
        """
        versions = self.get_all_versions()

        if limit:
            versions = versions[-limit:]

        return [
            {
                "id": v.id,
                "version_number": v.version_number,
                "author": v.author,
                "author_name": v.author_name,
                "commit_message": v.commit_message,
                "created_at": v.created_at.isoformat(),
                "is_approved": v.is_approved,
                "approved_by": v.approved_by,
                "approved_at": v.approved_at.isoformat() if v.approved_at else None,
            }
            for v in versions
        ]

    def restore_version(self, version_id: str) -> str | None:
        """Restore a version (creates a new version with restored content).

        Args:
            version_id: Version to restore

        Returns:
            Content of the restored version or None if not found
        """
        version = self.get_version(version_id)
        if not version:
            logger.warning("Version not found for restore: %s", version_id)
            return None

        logger.info(
            "Restored version %d (%s)",
            version.version_number,
            version_id,
        )

        return version.content

    def delete_version(self, version_id: str) -> bool:
        """Delete a version permanently.

        WARNING: This breaks the version chain. Use with caution.

        Args:
            version_id: Version to delete

        Returns:
            True if deletion was successful
        """
        versions = self.load_versions()

        # Find and remove version
        original_length = len(versions)
        versions = [v for v in versions if v.id != version_id]

        if len(versions) < original_length:
            if self.save_versions(versions):
                logger.info("Deleted version %s", version_id)
                return True
            return False

        logger.warning("Version not found for deletion: %s", version_id)
        return False

    def get_version_count(self) -> int:
        """Get count of versions.

        Returns:
            Number of versions
        """
        return len(self.load_versions())

    def get_versions_by_author(
        self,
        author: str,
    ) -> list[Version]:
        """Get all versions by a specific author.

        Args:
            author: Author identifier

        Returns:
            List of versions by the author
        """
        versions = self.load_versions()
        return [v for v in versions if v.author == author]

    def get_versions_since(
        self,
        since: datetime,
    ) -> list[Version]:
        """Get all versions created since a given timestamp.

        Args:
            since: Timestamp to filter from

        Returns:
            List of versions created since the timestamp
        """
        versions = self.load_versions()
        return [v for v in versions if v.created_at >= since]
