"""
Artifact Manager
================

Manages generation and storage of build artifacts for CI/CD pipelines.
Handles build logs, test reports, coverage reports, and other build outputs.
"""

import json
import logging
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

logger = logging.getLogger(__name__)

# Trust Layer verification report (P1) — see docs/strategy/roadmap.md
VERIFICATION_REPORT_FILENAME = "verification-report.json"
VERIFICATION_REPORT_SCHEMA_VERSION = 1
_ALLOWED_VERDICTS = ("approved", "rejected", "error")


def _utc_timestamp() -> str:
    """Timezone-aware UTC timestamp in ISO-8601 with a trailing ``Z``."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
                Optional keys: duration, error, changed_files, metadata

        Returns:
            Path to saved artifact file, or None if disabled

        Example:
            >>> manager.save_build_log({
            ...     "status": "success",
            ...     "timestamp": "2025-02-06T18:30:00Z",
            ...     "duration": 120.5,
            ...     "changed_files": ["src/main.py"]
            ... })
        """
        if not self.enabled:
            return None

        artifact_path = self.artifact_dir / "build-log.json"

        try:
            # Add metadata timestamp if not present (use a copy to avoid mutating caller's dict)
            if "timestamp" not in build_data:
                build_data = dict(build_data)
                build_data["timestamp"] = _utc_timestamp()

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
            # Add metadata timestamp if not present (use a copy to avoid mutating caller's dict)
            if "timestamp" not in test_data:
                test_data = dict(test_data)
                test_data["timestamp"] = _utc_timestamp()

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
            # Add metadata timestamp if not present (use a copy to avoid mutating caller's dict)
            if "timestamp" not in coverage_data:
                coverage_data = dict(coverage_data)
                coverage_data["timestamp"] = _utc_timestamp()

            # Write coverage report with pretty formatting
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f, indent=2)

            logger.debug(f"Coverage report saved: {artifact_path}")
            return artifact_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to save coverage report: {e}")
            return None

    def save_verification_report(
        self,
        verification_data: dict[str, Any],
    ) -> Path | None:
        """
        Save the Trust Layer verification report as a JSON artifact.

        Persists the structured QA verdict that the desktop UI and GitHub PR
        comments surface as a "what was verified" report: verdict, confidence,
        tests run, diff summary, the agent's uncertainty list, and any
        out-of-scope edits. Use :func:`build_verification_report` to assemble
        ``verification_data`` from the QA loop's existing signals.

        Args:
            verification_data: Verification report dict (see
                build_verification_report). A ``timestamp`` is added if absent.

        Returns:
            Path to saved artifact file, or None if disabled.

        Example:
            >>> report = build_verification_report(verdict="approved")
            >>> manager.save_verification_report(report)
        """
        if not self.enabled:
            return None

        artifact_path = self.artifact_dir / VERIFICATION_REPORT_FILENAME

        try:
            # Add timestamp if not present (copy to avoid mutating caller's dict)
            if "timestamp" not in verification_data:
                verification_data = dict(verification_data)
                verification_data["timestamp"] = _utc_timestamp()

            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(verification_data, f, indent=2)

            logger.debug(f"Verification report saved: {artifact_path}")
            return artifact_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to save verification report: {e}")
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

        # Sanitize artifact_name: reject paths with separators or parent components
        sanitized = Path(artifact_name)
        if (
            sanitized.is_absolute()
            or any(part in ("..", "") for part in sanitized.parts[:-1])
            or len(sanitized.parts) > 1
        ):
            raise ValueError(
                f"Invalid artifact name '{artifact_name}': must be a plain filename, "
                "not a path with directories or '..' components"
            )

        # Ensure artifact name ends with .json
        artifact_name = sanitized.name
        if not artifact_name.endswith(".json"):
            artifact_name = f"{artifact_name}.json"

        artifact_path = (self.artifact_dir / artifact_name).resolve()
        if not artifact_path.is_relative_to(self.artifact_dir.resolve()):
            raise ValueError(
                f"Resolved artifact path escapes artifact directory: {artifact_path}"
            )

        try:
            if isinstance(data, dict):
                # Add timestamp if not present (use a copy to avoid mutating caller's dict)
                if "timestamp" not in data:
                    data = dict(data)
                    data["timestamp"] = _utc_timestamp()

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
        artifact_path = (self.artifact_dir / Path(artifact_name).name).resolve()
        if not artifact_path.is_relative_to(self.artifact_dir.resolve()):
            return None
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
            target_path = target_dir / Path(artifact_name).name

            shutil.copy2(source_path, target_path)
            logger.debug(f"Copied artifact to: {target_path}")
            return target_path

        except OSError as e:
            logger.warning(f"Failed to copy artifact '{artifact_name}': {e}")
            return None


def build_verification_report(
    *,
    verdict: str | None,
    qa_session: int | None = None,
    iteration: int | None = None,
    confidence: float | None = None,
    tests_run: dict[str, Any] | None = None,
    diff_summary: dict[str, Any] | None = None,
    issues: list[dict[str, Any]] | None = None,
    uncertainty: list[dict[str, Any]] | None = None,
    out_of_scope_edits: list[dict[str, Any]] | None = None,
    duration_seconds: float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Assemble a normalized Trust Layer verification report (no I/O).

    Pure helper so the schema can be unit-tested and reused by the QA reviewer
    and fixer. ``verdict`` is normalized to one of ``approved``/``rejected``/
    ``error`` and ``confidence`` is clamped to ``[0, 1]``. The ``uncertainty``
    and ``out_of_scope_edits`` lists are part of the contract today and stay
    empty until P1·T2 (out-of-scope detection) and P1·T3 (confidence /
    uncertainty extraction) populate them — see docs/strategy/roadmap.md.

    Args:
        verdict: QA outcome; ``None`` or unknown values map to ``"error"``.
        qa_session: QA session/pass index, if known.
        iteration: QA loop iteration number, if known.
        confidence: Optional 0..1 confidence signal (clamped).
        tests_run: Test/coverage summary (e.g. passed/failed/total/coverage).
        diff_summary: Change summary (e.g. files_changed, files).
        issues: Issues found (reuses the ``qa_signoff`` issue shape).
        uncertainty: Areas the agent is unsure about.
        out_of_scope_edits: Edits made outside the planned files.
        duration_seconds: Optional duration of the QA pass.
        notes: Free-form notes.

    Returns:
        A JSON-serializable verification report dict (no timestamp — the
        timestamp is stamped by :meth:`ArtifactManager.save_verification_report`).
    """
    normalized_verdict = (verdict or "error").strip().lower()
    if normalized_verdict not in _ALLOWED_VERDICTS:
        normalized_verdict = "error"

    clamped_confidence: float | None = None
    if confidence is not None:
        try:
            clamped_confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            clamped_confidence = None

    report: dict[str, Any] = {
        "schema_version": VERIFICATION_REPORT_SCHEMA_VERSION,
        "verdict": normalized_verdict,
        "qa_session": qa_session,
        "iteration": iteration,
        "confidence": clamped_confidence,
        "tests_run": dict(tests_run) if tests_run else {},
        "diff_summary": dict(diff_summary) if diff_summary else {},
        "issues": list(issues) if issues else [],
        "uncertainty": list(uncertainty) if uncertainty else [],
        "out_of_scope_edits": list(out_of_scope_edits) if out_of_scope_edits else [],
        "notes": notes,
    }
    if duration_seconds is not None:
        try:
            report["duration_seconds"] = round(float(duration_seconds), 2)
        except (TypeError, ValueError):
            # Non-numeric duration is dropped rather than failing the report.
            pass
    return report


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
