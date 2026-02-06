"""
Artifact Manager
================

Manages generation and storage of build artifacts for CI/CD pipelines.
Handles build logs, test reports, coverage reports, and other build outputs.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in Path(__file__).parent.parts:
    import sys

    if str(_PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(_PARENT_DIR))

logger = logging.getLogger(__name__)


class ArtifactManager:
    """
    Manages build artifacts for CI/CD pipelines.

    This class handles the creation, storage, and retrieval of build artifacts
    including build logs, test reports, and coverage reports. Artifacts are
    stored in the spec directory for later retrieval by CI/CD systems.

    Attributes:
        spec_dir: Directory where artifacts will be stored
        artifact_dir: Subdirectory within spec_dir for artifacts
        enabled: Whether artifact generation is enabled

    Example:
        >>> manager = ArtifactManager(spec_dir=Path("/path/to/spec"))
        >>> manager.save_build_log({
        ...     "status": "success",
        ...     "duration": 120.5
        ... })
        >>> artifact_path = manager.get_artifact_path("build-log.json")
    """

    def __init__(
        self,
        spec_dir: Path,
        enabled: bool = True,
        artifact_subdir: str = "artifacts",
    ):
        """
        Initialize the artifact manager.

        Args:
            spec_dir: Base spec directory where artifacts will be stored
            enabled: Whether artifact generation is enabled (for conditional use)
            artifact_subdir: Name of subdirectory for artifacts (default: "artifacts")
        """
        self.spec_dir = Path(spec_dir)
        self.enabled = enabled
        self.artifact_dir = self.spec_dir / artifact_subdir

        # Create artifact directory if enabled
        if self.enabled:
            self.artifact_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Artifact manager initialized: {self.artifact_dir}")

    def save_build_log(self, build_data: dict[str, Any]) -> Path | None:
        """
        Save build log as JSON artifact.

        Stores build execution data including status, duration, changed files,
        and other build metadata in a JSON file for CI/CD consumption.

        Args:
            build_data: Dictionary containing build information
                Required keys: status, timestamp
                Optional keys: duration, error, changedFiles, metadata

        Returns:
            Path to saved artifact file, or None if disabled

        Example:
            >>> manager.save_build_log({
            ...     "status": "success",
            ...     "timestamp": "2025-02-06T18:30:00Z",
            ...     "duration": 120.5,
            ...     "changedFiles": ["src/main.py"]
            ... })
        """
        if not self.enabled:
            return None

        artifact_path = self.artifact_dir / "build-log.json"

        try:
            # Add metadata timestamp if not present
            if "timestamp" not in build_data:
                build_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

            # Write build log with pretty formatting
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(build_data, f, indent=2)

            logger.debug(f"Build log saved: {artifact_path}")
            return artifact_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to save build log: {e}")
            return None

    def save_test_report(
        self,
        test_data: dict[str, Any],
    ) -> Path | None:
        """
        Save test report as JSON artifact.

        Stores test execution results including pass/fail status, test counts,
        coverage information, and individual test results.

        Args:
            test_data: Dictionary containing test information
                Required keys: timestamp
                Optional keys: passed, failed, skipped, total, coverage, tests

        Returns:
            Path to saved artifact file, or None if disabled

        Example:
            >>> manager.save_test_report({
            ...     "timestamp": "2025-02-06T18:30:00Z",
            ...     "passed": 15,
            ...     "failed": 2,
            ...     "skipped": 1,
            ...     "total": 18,
            ...     "coverage": 85.5
            ... })
        """
        if not self.enabled:
            return None

        artifact_path = self.artifact_dir / "test-report.json"

        try:
            # Add metadata timestamp if not present
            if "timestamp" not in test_data:
                test_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

            # Write test report with pretty formatting
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(test_data, f, indent=2)

            logger.debug(f"Test report saved: {artifact_path}")
            return artifact_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to save test report: {e}")
            return None

    def save_coverage_report(
        self,
        coverage_data: dict[str, Any],
    ) -> Path | None:
        """
        Save code coverage report as JSON artifact.

        Stores coverage metrics including line coverage, branch coverage,
        and per-module coverage breakdown.

        Args:
            coverage_data: Dictionary containing coverage information
                Required keys: timestamp
                Optional keys: lineCoverage, branchCoverage, modules

        Returns:
            Path to saved artifact file, or None if disabled

        Example:
            >>> manager.save_coverage_report({
            ...     "timestamp": "2025-02-06T18:30:00Z",
            ...     "lineCoverage": 85.5,
            ...     "branchCoverage": 78.2,
            ...     "modules": {
            ...         "src/main.py": {"lines": 92.0, "branches": 85.0}
            ...     }
            ... })
        """
        if not self.enabled:
            return None

        artifact_path = self.artifact_dir / "coverage-report.json"

        try:
            # Add metadata timestamp if not present
            if "timestamp" not in coverage_data:
                coverage_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

            # Write coverage report with pretty formatting
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f, indent=2)

            logger.debug(f"Coverage report saved: {artifact_path}")
            return artifact_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to save coverage report: {e}")
            return None

    def save_custom_artifact(
        self,
        artifact_name: str,
        data: dict[str, Any] | str,
    ) -> Path | None:
        """
        Save a custom artifact with arbitrary data.

        Allows saving custom artifacts with any JSON-serializable data.
        Useful for project-specific artifact needs.

        Args:
            artifact_name: Name of the artifact file (will be suffixed with .json)
            data: Data to save (dict for JSON, str for raw text)

        Returns:
            Path to saved artifact file, or None if disabled

        Example:
            >>> manager.save_custom_artifact("performance-metrics", {
            ...     "memoryUsage": "512MB",
            ...     "cpuTime": 45.2
            ... })
        """
        if not self.enabled:
            return None

        # Ensure artifact name ends with .json
        if not artifact_name.endswith(".json"):
            artifact_name = f"{artifact_name}.json"

        artifact_path = self.artifact_dir / artifact_name

        try:
            if isinstance(data, dict):
                # Add timestamp if not present
                if "timestamp" not in data:
                    data["timestamp"] = datetime.utcnow().isoformat() + "Z"

                # Write JSON data
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            else:
                # Write raw string data
                with open(artifact_path, "w", encoding="utf-8") as f:
                    f.write(str(data))

            logger.debug(f"Custom artifact saved: {artifact_path}")
            return artifact_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to save custom artifact '{artifact_name}': {e}")
            return None

    def get_artifact_path(self, artifact_name: str) -> Path | None:
        """
        Get the full path to an artifact file.

        Args:
            artifact_name: Name of the artifact file

        Returns:
            Full path to artifact, or None if artifact doesn't exist

        Example:
            >>> path = manager.get_artifact_path("build-log.json")
            >>> if path:
            ...     print(f"Artifact at: {path}")
        """
        artifact_path = self.artifact_dir / artifact_name
        if artifact_path.exists():
            return artifact_path
        return None

    def load_artifact(self, artifact_name: str) -> dict[str, Any] | None:
        """
        Load and parse an artifact file.

        Args:
            artifact_name: Name of the artifact file

        Returns:
            Parsed artifact data as dictionary, or None if not found/invalid

        Example:
            >>> data = manager.load_artifact("build-log.json")
            >>> if data:
            ...     print(f"Build status: {data.get('status')}")
        """
        artifact_path = self.get_artifact_path(artifact_name)
        if not artifact_path:
            return None

        try:
            with open(artifact_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def list_artifacts(self) -> list[str]:
        """
        List all artifact files in the artifact directory.

        Returns:
            List of artifact filenames

        Example:
            >>> artifacts = manager.list_artifacts()
            >>> print(f"Generated artifacts: {artifacts}")
        """
        if not self.enabled or not self.artifact_dir.exists():
            return []

        artifacts = []
        for item in self.artifact_dir.iterdir():
            if item.is_file() and not item.is_symlink():
                artifacts.append(item.name)

        return sorted(artifacts)

    def get_artifact_summary(self) -> dict[str, Any]:
        """
        Get a summary of all artifacts.

        Returns:
            Dictionary with artifact count and list of artifact paths

        Example:
            >>> summary = manager.get_artifact_summary()
            >>> print(f"Generated {summary['count']} artifacts")
        """
        artifacts = self.list_artifacts()

        return {
            "artifactDir": str(self.artifact_dir),
            "count": len(artifacts),
            "artifacts": [
                {
                    "name": name,
                    "path": str(self.artifact_dir / name),
                }
                for name in artifacts
            ],
        }

    def cleanup_old_artifacts(
        self,
        keep_count: int = 5,
    ) -> int:
        """
        Remove old artifacts, keeping only the most recent ones.

        Useful for preventing artifact directory from growing unbounded
        in long-running CI/CD pipelines.

        Args:
            keep_count: Number of most recent artifacts to keep (per file type)

        Returns:
            Number of artifacts removed

        Example:
            >>> removed = manager.cleanup_old_artifacts(keep_count=3)
            >>> print(f"Removed {removed} old artifacts")
        """
        if not self.enabled or not self.artifact_dir.exists():
            return 0

        removed_count = 0

        try:
            # Group artifacts by base name (before any timestamp/sequence suffix)
            artifact_groups: dict[str, list[Path]] = {}
            for item in self.artifact_dir.iterdir():
                if item.is_file() and not item.is_symlink():
                    # Group by file stem (name without extension)
                    base_name = item.stem
                    if base_name not in artifact_groups:
                        artifact_groups[base_name] = []
                    artifact_groups[base_name].append(item)

            # For each group, keep only the most recent files
            for base_name, artifacts in artifact_groups.items():
                if len(artifacts) > keep_count:
                    # Sort by modification time (newest first)
                    artifacts.sort(key=lambda p: p.stat().st_mtime, reverse=True)

                    # Remove oldest artifacts
                    for old_artifact in artifacts[keep_count:]:
                        old_artifact.unlink()
                        removed_count += 1
                        logger.debug(f"Removed old artifact: {old_artifact.name}")

        except OSError as e:
            logger.warning(f"Failed to cleanup old artifacts: {e}")

        return removed_count

    def copy_artifact_to_directory(
        self,
        artifact_name: str,
        target_dir: Path,
    ) -> Path | None:
        """
        Copy an artifact to a different directory.

        Useful for copying artifacts to a location accessible by CI/CD systems
        (e.g., a shared artifacts directory).

        Args:
            artifact_name: Name of the artifact file
            target_dir: Directory to copy the artifact to

        Returns:
            Path to copied artifact, or None if copy failed

        Example:
            >>> manager.copy_artifact_to_directory(
            ...     "build-log.json",
            ...     Path("/shared/artifacts")
            ... )
        """
        if not self.enabled:
            return None

        source_path = self.get_artifact_path(artifact_name)
        if not source_path:
            logger.warning(f"Artifact not found: {artifact_name}")
            return None

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / artifact_name

            shutil.copy2(source_path, target_path)
            logger.debug(f"Copied artifact to: {target_path}")
            return target_path

        except OSError as e:
            logger.warning(f"Failed to copy artifact '{artifact_name}': {e}")
            return None


def create_artifact_manager(
    spec_dir: Path,
    enabled: bool = True,
) -> ArtifactManager:
    """
    Factory function to create an ArtifactManager instance.

    This is a convenience function that follows the pattern used in other
    CLI modules for creating manager instances.

    Args:
        spec_dir: Base spec directory where artifacts will be stored
        enabled: Whether artifact generation is enabled

    Returns:
        Configured ArtifactManager instance

    Example:
        >>> manager = create_artifact_manager(
        ...     spec_dir=Path("/path/to/spec"),
        ...     enabled=True
        ... )
    """
    return ArtifactManager(spec_dir=spec_dir, enabled=enabled)
