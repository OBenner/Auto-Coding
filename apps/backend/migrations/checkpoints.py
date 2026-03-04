"""
Migration Checkpoint Manager
============================

Manages migration checkpoints for safe incremental migrations with rollback capability.
Creates git-based snapshots at each migration phase for easy rollback.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

# Git commit hash pattern (40 hex chars for SHA-1, or 64 for SHA-256)
_COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


class CheckpointStatus(Enum):
    """Status of a migration checkpoint."""

    CREATED = "created"
    VALIDATED = "validated"
    ROLLED_BACK = "rolled_back"
    ACTIVE = "active"


@dataclass
class Checkpoint:
    """Represents a migration checkpoint with git snapshot."""

    id: str
    phase_id: str
    name: str
    commit_hash: str
    timestamp: str
    status: CheckpointStatus
    validation_passed: bool = False
    notes: str = ""


class CheckpointManager:
    """
    Manages migration checkpoints with git-based snapshots.

    Responsibilities:
    - Create checkpoints at each migration phase
    - Validate checkpoints with test runs
    - Rollback to previous checkpoints on failure
    - Track checkpoint history and status
    - Generate rollback scripts
    """

    def __init__(self, project_dir: Path, spec_dir: Path | None = None):
        """
        Initialize checkpoint manager.

        Args:
            project_dir: Root project directory for git operations
            spec_dir: Optional spec directory for storing checkpoint data
        """
        self.project_dir = Path(project_dir).resolve()
        self.spec_dir = Path(spec_dir).resolve() if spec_dir else None

        # Determine checkpoints directory
        if self.spec_dir:
            self.checkpoints_dir = self.spec_dir / "checkpoints"
        else:
            self.checkpoints_dir = self.project_dir / ".migration-checkpoints"

        self.checkpoints_file = self.checkpoints_dir / "checkpoints.json"
        self.rollback_scripts_dir = self.checkpoints_dir / "rollback"

        # Ensure directories exist
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.rollback_scripts_dir.mkdir(parents=True, exist_ok=True)

        # Initialize checkpoints file if it doesn't exist
        if not self.checkpoints_file.exists():
            self._init_checkpoints_file()

    def _init_checkpoints_file(self) -> None:
        """Initialize the checkpoints tracking file."""
        initial_data = {
            "checkpoints": [],
            "active_checkpoint": None,
            "baseline_commit": self._get_current_commit(),
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
        }
        with open(self.checkpoints_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)

    def _load_checkpoints(self) -> dict:
        """Load checkpoints from JSON file."""
        try:
            with open(self.checkpoints_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            self._init_checkpoints_file()
            with open(self.checkpoints_file, encoding="utf-8") as f:
                return json.load(f)

    def _save_checkpoints(self, data: dict) -> None:
        """Save checkpoints to JSON file."""
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoints_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _validate_commit_hash(commit_hash: str) -> bool:
        """Validate that a string looks like a git commit hash."""
        return bool(_COMMIT_HASH_RE.match(commit_hash))

    def _get_current_commit(self) -> str | None:
        """
        Get the current git commit hash.

        Returns:
            Commit hash or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_commit_info(self, commit_hash: str) -> dict:
        """
        Get information about a commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            Dict with commit info (message, author, date)
        """
        if not self._validate_commit_hash(commit_hash):
            return {"message": "", "author": "", "date": ""}

        try:
            result = subprocess.run(
                ["git", "show", "--no-patch", "--format=%s%n%an%n%ai", commit_hash],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            lines = result.stdout.strip().split("\n")
            return {
                "message": lines[0] if len(lines) > 0 else "",
                "author": lines[1] if len(lines) > 1 else "",
                "date": lines[2] if len(lines) > 2 else "",
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {"message": "", "author": "", "date": ""}

    def create_checkpoint(
        self, phase_id: str, name: str, notes: str = ""
    ) -> Checkpoint | None:
        """
        Create a checkpoint at the current state.

        Args:
            phase_id: ID of the migration phase
            name: Name for the checkpoint
            notes: Optional notes about the checkpoint

        Returns:
            Checkpoint object or None if failed
        """
        current_commit = self._get_current_commit()
        if not current_commit:
            return None

        data = self._load_checkpoints()

        # Generate checkpoint ID
        checkpoint_count = len(data["checkpoints"])
        checkpoint_id = f"checkpoint-{checkpoint_count + 1}"

        # Create checkpoint object
        checkpoint = Checkpoint(
            id=checkpoint_id,
            phase_id=phase_id,
            name=name,
            commit_hash=current_commit,
            timestamp=datetime.now().isoformat(),
            status=CheckpointStatus.CREATED,
            validation_passed=False,
            notes=notes,
        )

        # Add to checkpoints list
        data["checkpoints"].append(self._checkpoint_to_dict(checkpoint))
        data["active_checkpoint"] = checkpoint_id

        self._save_checkpoints(data)

        # Generate rollback script
        self._generate_rollback_script(checkpoint)

        return checkpoint

    def validate_checkpoint(self, checkpoint_id: str, validation_passed: bool) -> bool:
        """
        Mark a checkpoint as validated.

        Args:
            checkpoint_id: ID of the checkpoint
            validation_passed: Whether validation tests passed

        Returns:
            True if successful
        """
        data = self._load_checkpoints()

        # Find and update checkpoint
        for cp_dict in data["checkpoints"]:
            if cp_dict["id"] == checkpoint_id:
                cp_dict["validation_passed"] = validation_passed
                cp_dict["status"] = (
                    CheckpointStatus.VALIDATED.value
                    if validation_passed
                    else CheckpointStatus.CREATED.value
                )
                self._save_checkpoints(data)
                return True

        return False

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rollback to a specific checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to rollback to

        Returns:
            True if successful
        """
        data = self._load_checkpoints()

        # Find checkpoint
        checkpoint_dict = None
        for cp in data["checkpoints"]:
            if cp["id"] == checkpoint_id:
                checkpoint_dict = cp
                break

        if not checkpoint_dict:
            return False

        # Validate commit hash to prevent command injection
        commit_hash = checkpoint_dict["commit_hash"]
        if not self._validate_commit_hash(commit_hash):
            return False

        # Rollback to the commit
        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Update checkpoint status
            checkpoint_dict["status"] = CheckpointStatus.ROLLED_BACK.value

            # Set as active checkpoint
            data["active_checkpoint"] = checkpoint_id

            self._save_checkpoints(data)
            return True

        except subprocess.CalledProcessError:
            return False

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """
        Get a checkpoint by ID.

        Args:
            checkpoint_id: ID of the checkpoint

        Returns:
            Checkpoint object or None if not found
        """
        data = self._load_checkpoints()

        for cp_dict in data["checkpoints"]:
            if cp_dict["id"] == checkpoint_id:
                return self._dict_to_checkpoint(cp_dict)

        return None

    def list_checkpoints(self) -> list[Checkpoint]:
        """
        Get all checkpoints.

        Returns:
            List of Checkpoint objects
        """
        data = self._load_checkpoints()
        return [self._dict_to_checkpoint(cp) for cp in data["checkpoints"]]

    def get_active_checkpoint(self) -> Checkpoint | None:
        """
        Get the currently active checkpoint.

        Returns:
            Active Checkpoint or None
        """
        data = self._load_checkpoints()
        active_id = data.get("active_checkpoint")

        if not active_id:
            return None

        return self.get_checkpoint(active_id)

    def get_baseline_commit(self) -> str | None:
        """
        Get the baseline commit (before migration started).

        Returns:
            Commit hash or None
        """
        data = self._load_checkpoints()
        return data.get("baseline_commit")

    def rollback_to_baseline(self) -> bool:
        """
        Rollback to the baseline commit (before migration).

        Returns:
            True if successful
        """
        baseline = self.get_baseline_commit()
        if not baseline or not self._validate_commit_hash(baseline):
            return False

        try:
            subprocess.run(
                ["git", "reset", "--hard", baseline],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Clear active checkpoint
            data = self._load_checkpoints()
            data["active_checkpoint"] = None
            self._save_checkpoints(data)

            return True

        except subprocess.CalledProcessError:
            return False

    def _generate_rollback_script(self, checkpoint: Checkpoint) -> None:
        """
        Generate a rollback script for a checkpoint.

        Args:
            checkpoint: Checkpoint to generate script for
        """
        script_path = self.rollback_scripts_dir / f"{checkpoint.id}.sh"

        # Validate commit hash before generating script
        if not self._validate_commit_hash(checkpoint.commit_hash):
            return

        # Shell-escape all interpolated values to prevent injection
        safe_name = shlex.quote(checkpoint.name)
        safe_phase = shlex.quote(checkpoint.phase_id)
        safe_hash = shlex.quote(checkpoint.commit_hash)
        safe_timestamp = shlex.quote(checkpoint.timestamp)

        script_content = f"""#!/bin/bash
# Rollback script for checkpoint
# Generated: {safe_timestamp}

echo "Rolling back to checkpoint: "{safe_name}
echo "Phase: "{safe_phase}
echo "Commit: "{safe_hash}
echo ""

# Confirm with user
read -p "Are you sure you want to rollback? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 1
fi

# Perform rollback
git reset --hard {safe_hash}

if [ $? -eq 0 ]; then
    echo "Successfully rolled back to checkpoint "{safe_name}
    echo "Current commit: $(git rev-parse --short HEAD)"
else
    echo "Rollback failed"
    exit 1
fi
"""

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make script executable (Unix-like systems)
        try:
            script_path.chmod(0o755)
        except Exception:
            pass

    def _checkpoint_to_dict(self, checkpoint: Checkpoint) -> dict:
        """Convert Checkpoint to dictionary."""
        return {
            "id": checkpoint.id,
            "phase_id": checkpoint.phase_id,
            "name": checkpoint.name,
            "commit_hash": checkpoint.commit_hash,
            "timestamp": checkpoint.timestamp,
            "status": checkpoint.status.value,
            "validation_passed": checkpoint.validation_passed,
            "notes": checkpoint.notes,
        }

    def _dict_to_checkpoint(self, data: dict) -> Checkpoint:
        """Convert dictionary to Checkpoint."""
        return Checkpoint(
            id=data["id"],
            phase_id=data["phase_id"],
            name=data["name"],
            commit_hash=data["commit_hash"],
            timestamp=data["timestamp"],
            status=CheckpointStatus(data["status"]),
            validation_passed=data.get("validation_passed", False),
            notes=data.get("notes", ""),
        )

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to delete

        Returns:
            True if successful
        """
        data = self._load_checkpoints()

        # Remove checkpoint
        original_count = len(data["checkpoints"])
        data["checkpoints"] = [
            cp for cp in data["checkpoints"] if cp["id"] != checkpoint_id
        ]

        if len(data["checkpoints"]) == original_count:
            return False

        # Clear active checkpoint if it was deleted
        if data.get("active_checkpoint") == checkpoint_id:
            data["active_checkpoint"] = None

        self._save_checkpoints(data)

        # Delete rollback script
        script_path = self.rollback_scripts_dir / f"{checkpoint_id}.sh"
        if script_path.exists():
            script_path.unlink()

        return True

    def get_checkpoint_summary(self) -> dict:
        """
        Get a summary of all checkpoints.

        Returns:
            Dict with checkpoint statistics and status
        """
        checkpoints = self.list_checkpoints()
        active = self.get_active_checkpoint()
        baseline = self.get_baseline_commit()

        return {
            "total_checkpoints": len(checkpoints),
            "validated_checkpoints": sum(
                1 for cp in checkpoints if cp.validation_passed
            ),
            "active_checkpoint": active.id if active else None,
            "baseline_commit": baseline,
            "checkpoints": [self._checkpoint_to_dict(cp) for cp in checkpoints],
        }


# Utility functions


def create_migration_checkpoint(
    project_dir: Path, phase_id: str, name: str, spec_dir: Path | None = None
) -> Checkpoint | None:
    """
    Create a migration checkpoint (convenience function).

    Args:
        project_dir: Project directory
        phase_id: Migration phase ID
        name: Checkpoint name
        spec_dir: Optional spec directory

    Returns:
        Checkpoint object or None if failed
    """
    manager = CheckpointManager(project_dir, spec_dir)
    return manager.create_checkpoint(phase_id, name)


def rollback_migration(
    project_dir: Path, checkpoint_id: str, spec_dir: Path | None = None
) -> bool:
    """
    Rollback to a specific checkpoint (convenience function).

    Args:
        project_dir: Project directory
        checkpoint_id: Checkpoint ID to rollback to
        spec_dir: Optional spec directory

    Returns:
        True if successful
    """
    manager = CheckpointManager(project_dir, spec_dir)
    return manager.rollback_to_checkpoint(checkpoint_id)
