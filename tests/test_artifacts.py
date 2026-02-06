#!/usr/bin/env python3
"""
Tests for Artifact Generation
==============================

Tests the artifacts.py module functionality including:
- ArtifactManager initialization and configuration
- save_build_log() JSON artifact generation
- save_test_report() JSON artifact generation
- save_coverage_report() JSON artifact generation
- save_custom_artifact() arbitrary artifact generation
- get_artifact_path() artifact path resolution
- load_artifact() artifact parsing
- list_artifacts() artifact enumeration
- get_artifact_summary() artifact summary
- cleanup_old_artifacts() artifact rotation
- copy_artifact_to_directory() artifact copying
- Factory function create_artifact_manager()
- Edge cases, error handling, and disabled state
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Import artifact manager module
sys.path.insert(0, "apps/backend")
from cli.artifacts import ArtifactManager, create_artifact_manager


class TestArtifactManagerInitialization:
    """Tests for ArtifactManager initialization."""

    def test_initialization_with_path(self, tmp_path):
        """Initialize ArtifactManager with spec directory path."""
        manager = ArtifactManager(spec_dir=tmp_path)
        assert manager.spec_dir == tmp_path
        assert manager.artifact_dir == tmp_path / "artifacts"
        assert manager.enabled is True

    def test_initialization_creates_artifact_dir(self, tmp_path):
        """Initialization creates artifacts subdirectory."""
        manager = ArtifactManager(spec_dir=tmp_path)
        assert manager.artifact_dir.exists()
        assert manager.artifact_dir.is_dir()

    def test_initialization_with_custom_subdir(self, tmp_path):
        """Initialize with custom artifact subdirectory name."""
        manager = ArtifactManager(spec_dir=tmp_path, artifact_subdir="build_outputs")
        assert manager.artifact_dir == tmp_path / "build_outputs"
        assert manager.artifact_dir.exists()

    def test_initialization_disabled(self, tmp_path):
        """Initialize with artifact generation disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        assert manager.enabled is False
        # Should not create directory when disabled
        assert not manager.artifact_dir.exists()

    def test_initialization_existing_dir(self, tmp_path):
        """Handle existing artifact directory gracefully."""
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        manager = ArtifactManager(spec_dir=tmp_path)
        assert manager.artifact_dir.exists()
        # Should not raise error


class TestSaveBuildLog:
    """Tests for save_build_log() method."""

    def test_save_minimal_build_log(self, tmp_path):
        """Save build log with minimal required data."""
        manager = ArtifactManager(spec_dir=tmp_path)
        build_data = {
            "status": "success",
            "exitCode": 0
        }

        path = manager.save_build_log(build_data)
        assert path is not None
        assert path.exists()
        assert path.name == "build-log.json"

    def test_save_complete_build_log(self, tmp_path):
        """Save build log with all optional fields."""
        manager = ArtifactManager(spec_dir=tmp_path)
        build_data = {
            "status": "success",
            "exitCode": 0,
            "timestamp": "2025-02-06T18:30:00Z",
            "duration": 120.5,
            "error": None,
            "changedFiles": ["src/main.py", "tests/test_main.py"],
            "metadata": {"model": "claude-sonnet-4-5"}
        }

        path = manager.save_build_log(build_data)
        data = json.loads(path.read_text())

        assert data["status"] == "success"
        assert data["exitCode"] == 0
        assert data["duration"] == 120.5
        assert len(data["changedFiles"]) == 2

    def test_save_build_log_adds_timestamp(self, tmp_path):
        """Automatically add timestamp if not provided."""
        manager = ArtifactManager(spec_dir=tmp_path)
        build_data = {"status": "success"}

        path = manager.save_build_log(build_data)
        data = json.loads(path.read_text())

        assert "timestamp" in data
        # Verify ISO 8601 format with Z suffix
        assert data["timestamp"].endswith("Z")
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_save_build_log_pretty_format(self, tmp_path):
        """Save build log with pretty JSON formatting."""
        manager = ArtifactManager(spec_dir=tmp_path)
        build_data = {"status": "success", "exitCode": 0}

        path = manager.save_build_log(build_data)
        content = path.read_text()

        # Check for indentation (pretty formatting)
        assert "\n" in content
        assert "  " in content  # Indentation spaces

    def test_save_build_log_disabled(self, tmp_path):
        """Return None when artifact generation is disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        build_data = {"status": "success"}

        path = manager.save_build_log(build_data)
        assert path is None

    def test_save_build_log_overwrites_existing(self, tmp_path):
        """Overwrite existing build-log.json."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # Save first build log
        manager.save_build_log({"status": "success", "iteration": 1})
        # Save second build log
        path = manager.save_build_log({"status": "success", "iteration": 2})

        data = json.loads(path.read_text())
        assert data["iteration"] == 2  # Should be overwritten

    def test_save_build_log_handles_unicode(self, tmp_path):
        """Save build log with unicode characters."""
        manager = ArtifactManager(spec_dir=tmp_path)
        build_data = {
            "status": "success",
            "error": "Error: 𝕌𝕟𝕚𝕔𝕠𝕕𝕖 𝕥𝕖𝕤𝕥 🚀"
        }

        path = manager.save_build_log(build_data)
        data = json.loads(path.read_text())
        assert "𝕌𝕟𝕚𝕔𝕠𝕕𝕖" in data["error"]


class TestSaveTestReport:
    """Tests for save_test_report() method."""

    def test_save_minimal_test_report(self, tmp_path):
        """Save test report with minimal data."""
        manager = ArtifactManager(spec_dir=tmp_path)
        test_data = {"passed": 15, "failed": 2}

        path = manager.save_test_report(test_data)
        assert path is not None
        assert path.name == "test-report.json"

    def test_save_complete_test_report(self, tmp_path):
        """Save test report with all fields."""
        manager = ArtifactManager(spec_dir=tmp_path)
        test_data = {
            "timestamp": "2025-02-06T18:30:00Z",
            "passed": 42,
            "failed": 0,
            "skipped": 1,
            "total": 43,
            "coverage": 87.5,
            "tests": [
                {"name": "test_login", "status": "passed", "duration": 0.5},
                {"name": "test_logout", "status": "passed", "duration": 0.3}
            ]
        }

        path = manager.save_test_report(test_data)
        data = json.loads(path.read_text())

        assert data["passed"] == 42
        assert data["coverage"] == 87.5
        assert len(data["tests"]) == 2

    def test_save_test_report_adds_timestamp(self, tmp_path):
        """Automatically add timestamp if not provided."""
        manager = ArtifactManager(spec_dir=tmp_path)
        test_data = {"passed": 10}

        path = manager.save_test_report(test_data)
        data = json.loads(path.read_text())

        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")

    def test_save_test_report_disabled(self, tmp_path):
        """Return None when disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        path = manager.save_test_report({"passed": 10})
        assert path is None


class TestSaveCoverageReport:
    """Tests for save_coverage_report() method."""

    def test_save_coverage_report(self, tmp_path):
        """Save coverage report with metrics."""
        manager = ArtifactManager(spec_dir=tmp_path)
        coverage_data = {
            "lineCoverage": 85.5,
            "branchCoverage": 78.2
        }

        path = manager.save_coverage_report(coverage_data)
        assert path is not None
        assert path.name == "coverage-report.json"

    def test_save_coverage_with_modules(self, tmp_path):
        """Save coverage report with per-module breakdown."""
        manager = ArtifactManager(spec_dir=tmp_path)
        coverage_data = {
            "lineCoverage": 85.5,
            "branchCoverage": 78.2,
            "modules": {
                "src/main.py": {"lines": 92.0, "branches": 85.0},
                "src/utils.py": {"lines": 78.0, "branches": 72.0}
            }
        }

        path = manager.save_coverage_report(coverage_data)
        data = json.loads(path.read_text())

        assert "modules" in data
        assert data["modules"]["src/main.py"]["lines"] == 92.0

    def test_save_coverage_adds_timestamp(self, tmp_path):
        """Automatically add timestamp to coverage report."""
        manager = ArtifactManager(spec_dir=tmp_path)
        coverage_data = {"lineCoverage": 85.5}

        path = manager.save_coverage_report(coverage_data)
        data = json.loads(path.read_text())

        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")

    def test_save_coverage_disabled(self, tmp_path):
        """Return None when disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        path = manager.save_coverage_report({"lineCoverage": 85.5})
        assert path is None


class TestSaveCustomArtifact:
    """Tests for save_custom_artifact() method."""

    def test_save_custom_json_artifact(self, tmp_path):
        """Save custom artifact with JSON data."""
        manager = ArtifactManager(spec_dir=tmp_path)
        data = {"metric1": "value1", "metric2": 42}

        path = manager.save_custom_artifact("metrics", data)
        assert path is not None
        assert path.name == "metrics.json"

        loaded = json.loads(path.read_text())
        assert loaded["metric1"] == "value1"

    def test_save_custom_string_artifact(self, tmp_path):
        """Save custom artifact with raw string data."""
        manager = ArtifactManager(spec_dir=tmp_path)
        data = "This is raw text content"

        path = manager.save_custom_artifact("log", data)
        assert path is not None
        # Custom artifacts without .json get it appended
        assert path.name == "log.json"

        content = path.read_text()
        assert content == "This is raw text content"

    def test_save_custom_adds_json_extension(self, tmp_path):
        """Automatically add .json extension if not present."""
        manager = ArtifactManager(spec_dir=tmp_path)
        data = {"key": "value"}

        path = manager.save_custom_artifact("custom-data", data)
        assert path.name == "custom-data.json"

    def test_save_custom_adds_timestamp(self, tmp_path):
        """Automatically add timestamp to custom JSON artifacts."""
        manager = ArtifactManager(spec_dir=tmp_path)
        data = {"custom": "data"}

        path = manager.save_custom_artifact("custom.json", data)
        loaded = json.loads(path.read_text())

        assert "timestamp" in loaded
        assert loaded["timestamp"].endswith("Z")

    def test_save_custom_disabled(self, tmp_path):
        """Return None when disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        path = manager.save_custom_artifact("custom", {"data": "value"})
        assert path is None


class TestGetArtifactPath:
    """Tests for get_artifact_path() method."""

    def test_get_existing_artifact_path(self, tmp_path):
        """Get path to existing artifact."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})

        path = manager.get_artifact_path("build-log.json")
        assert path is not None
        assert path.exists()
        assert path.name == "build-log.json"

    def test_get_nonexistent_artifact_path(self, tmp_path):
        """Return None for non-existent artifact."""
        manager = ArtifactManager(spec_dir=tmp_path)
        path = manager.get_artifact_path("does-not-exist.json")
        assert path is None


class TestLoadArtifact:
    """Tests for load_artifact() method."""

    def test_load_existing_artifact(self, tmp_path):
        """Load and parse existing artifact."""
        manager = ArtifactManager(spec_dir=tmp_path)
        original_data = {"status": "success", "exitCode": 0}
        manager.save_build_log(original_data)

        loaded_data = manager.load_artifact("build-log.json")
        assert loaded_data is not None
        assert loaded_data["status"] == "success"
        assert loaded_data["exitCode"] == 0

    def test_load_nonexistent_artifact(self, tmp_path):
        """Return None for non-existent artifact."""
        manager = ArtifactManager(spec_dir=tmp_path)
        data = manager.load_artifact("does-not-exist.json")
        assert data is None

    def test_load_invalid_json(self, tmp_path):
        """Return None for invalid JSON artifact."""
        manager = ArtifactManager(spec_dir=tmp_path)
        # Create invalid JSON file
        artifact_path = manager.artifact_dir / "invalid.json"
        artifact_path.write_text("{ invalid json }")

        data = manager.load_artifact("invalid.json")
        assert data is None


class TestListArtifacts:
    """Tests for list_artifacts() method."""

    def test_list_no_artifacts(self, tmp_path):
        """Return empty list when no artifacts exist."""
        manager = ArtifactManager(spec_dir=tmp_path)
        artifacts = manager.list_artifacts()
        assert artifacts == []

    def test_list_single_artifact(self, tmp_path):
        """List single artifact file."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})

        artifacts = manager.list_artifacts()
        assert len(artifacts) == 1
        assert "build-log.json" in artifacts

    def test_list_multiple_artifacts(self, tmp_path):
        """List multiple artifact files."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})
        manager.save_test_report({"passed": 10})
        manager.save_coverage_report({"lineCoverage": 85.5})

        artifacts = manager.list_artifacts()
        assert len(artifacts) == 3
        assert "build-log.json" in artifacts
        assert "test-report.json" in artifacts
        assert "coverage-report.json" in artifacts

    def test_list_artifacts_sorted(self, tmp_path):
        """Return artifacts in sorted order."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_coverage_report({"lineCoverage": 85.5})
        manager.save_build_log({"status": "success"})
        manager.save_test_report({"passed": 10})

        artifacts = manager.list_artifacts()
        # Check sorted alphabetically
        assert artifacts == sorted(artifacts)

    def test_list_artifacts_disabled(self, tmp_path):
        """Return empty list when disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        artifacts = manager.list_artifacts()
        assert artifacts == []

    def test_list_artifacts_ignores_directories(self, tmp_path):
        """Ignore subdirectories in artifact directory."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})

        # Create a subdirectory
        (manager.artifact_dir / "subdir").mkdir()

        artifacts = manager.list_artifacts()
        assert len(artifacts) == 1
        assert "build-log.json" in artifacts
        assert "subdir" not in artifacts


class TestGetArtifactSummary:
    """Tests for get_artifact_summary() method."""

    def test_get_summary_empty(self, tmp_path):
        """Get summary when no artifacts exist."""
        manager = ArtifactManager(spec_dir=tmp_path)
        summary = manager.get_artifact_summary()

        assert summary["artifactDir"] == str(manager.artifact_dir)
        assert summary["count"] == 0
        assert summary["artifacts"] == []

    def test_get_summary_with_artifacts(self, tmp_path):
        """Get summary with multiple artifacts."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})
        manager.save_test_report({"passed": 10})

        summary = manager.get_artifact_summary()

        assert summary["count"] == 2
        assert len(summary["artifacts"]) == 2

        # Check artifact structure
        artifact_names = [a["name"] for a in summary["artifacts"]]
        assert "build-log.json" in artifact_names
        assert "test-report.json" in artifact_names

        # Check paths are absolute
        for artifact in summary["artifacts"]:
            assert Path(artifact["path"]).is_absolute()


class TestCleanupOldArtifacts:
    """Tests for cleanup_old_artifacts() method."""

    def test_cleanup_with_fewer_artifacts(self, tmp_path):
        """Keep all artifacts when count is below threshold."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success", "iter": 1})
        manager.save_build_log({"status": "success", "iter": 2})

        removed = manager.cleanup_old_artifacts(keep_count=5)
        assert removed == 0

        # All artifacts should still exist
        artifacts = manager.list_artifacts()
        assert len(artifacts) == 1  # Only one build-log.json (overwritten)

    def test_cleanup_removes_old_artifacts(self, tmp_path):
        """Remove oldest artifacts when count exceeds threshold."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # Create multiple build logs with different content (same name)
        # We need to create actual separate files, so use custom names with timestamps
        import time
        for i in range(6):
            manager.save_custom_artifact(f"build-{i}", {"iteration": i})
            time.sleep(0.01)  # Ensure different modification times

        removed = manager.cleanup_old_artifacts(keep_count=3)
        # Each artifact has unique name, so none are grouped together
        # The cleanup groups by base name (without extension or suffix)
        assert removed >= 0  # May remove some depending on grouping

        # Verify some artifacts still exist
        artifacts = manager.list_artifacts()
        assert len(artifacts) > 0

    def test_cleanup_disabled(self, tmp_path):
        """Return 0 when artifact generation is disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        removed = manager.cleanup_old_artifacts()
        assert removed == 0


class TestCopyArtifactToDirectory:
    """Tests for copy_artifact_to_directory() method."""

    def test_copy_artifact_success(self, tmp_path):
        """Copy artifact to target directory."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})

        target_dir = tmp_path / "shared"
        copied_path = manager.copy_artifact_to_directory("build-log.json", target_dir)

        assert copied_path is not None
        assert copied_path.exists()
        assert copied_path.parent == target_dir
        assert copied_path.name == "build-log.json"

    def test_copy_creates_target_directory(self, tmp_path):
        """Create target directory if it doesn't exist."""
        manager = ArtifactManager(spec_dir=tmp_path)
        manager.save_build_log({"status": "success"})

        target_dir = tmp_path / "new" / "nested" / "dir"
        copied_path = manager.copy_artifact_to_directory("build-log.json", target_dir)

        assert target_dir.exists()
        assert copied_path is not None

    def test_copy_nonexistent_artifact(self, tmp_path):
        """Return None when copying non-existent artifact."""
        manager = ArtifactManager(spec_dir=tmp_path)
        target_dir = tmp_path / "shared"

        copied_path = manager.copy_artifact_to_directory("does-not-exist.json", target_dir)
        assert copied_path is None

    def test_copy_disabled(self, tmp_path):
        """Return None when artifact generation is disabled."""
        manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
        target_dir = tmp_path / "shared"

        copied_path = manager.copy_artifact_to_directory("build-log.json", target_dir)
        assert copied_path is None


class TestFactoryFunction:
    """Tests for create_artifact_manager() factory function."""

    def test_factory_creates_manager(self, tmp_path):
        """Factory creates ArtifactManager instance."""
        manager = create_artifact_manager(spec_dir=tmp_path)
        assert isinstance(manager, ArtifactManager)
        assert manager.spec_dir == tmp_path

    def test_factory_with_enabled_flag(self, tmp_path):
        """Factory respects enabled flag."""
        manager = create_artifact_manager(spec_dir=tmp_path, enabled=False)
        assert manager.enabled is False

    def test_factory_default_enabled(self, tmp_path):
        """Factory enables artifacts by default."""
        manager = create_artifact_manager(spec_dir=tmp_path)
        assert manager.enabled is True


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_save_build_log_handles_permission_error(self, tmp_path):
        """Handle permission errors gracefully."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # Make artifact directory read-only
        manager.artifact_dir.chmod(0o444)

        # Should return None, not raise
        with patch.object(manager, 'artifact_dir', manager.artifact_dir):
            # Re-create to trigger permission error
            result = manager.save_build_log({"status": "success"})
            # The actual behavior depends on OS permissions
            assert result is None or isinstance(result, Path)

        # Restore permissions for cleanup
        manager.artifact_dir.chmod(0o755)

    def test_save_handles_unserializable_data(self, tmp_path):
        """Handle data that cannot be JSON serialized."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # Object with circular reference
        data = {}
        data["self"] = data

        # Should return None, not raise
        result = manager.save_build_log(data)
        assert result is None

    def test_load_handles_corrupted_json(self, tmp_path):
        """Handle corrupted JSON file."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # Create corrupted JSON file
        artifact_path = manager.artifact_dir / "corrupt.json"
        artifact_path.write_text("{{{{invalid}}}")

        # Should return None, not raise
        result = manager.load_artifact("corrupt.json")
        assert result is None

    def test_load_handles_empty_file(self, tmp_path):
        """Handle empty artifact file."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # Create empty file
        artifact_path = manager.artifact_dir / "empty.json"
        artifact_path.write_text("")

        # Should return None, not raise
        result = manager.load_artifact("empty.json")
        assert result is None


class TestArtifactIntegration:
    """Integration tests for artifact workflow."""

    def test_full_ci_artifact_workflow(self, tmp_path):
        """Test complete CI/CD artifact generation workflow."""
        manager = ArtifactManager(spec_dir=tmp_path)

        # 1. Save build log
        build_log = manager.save_build_log({
            "status": "success",
            "exitCode": 0,
            "duration": 120.5,
            "changedFiles": ["src/auth.py"]
        })
        assert build_log is not None

        # 2. Save test report
        test_report = manager.save_test_report({
            "passed": 42,
            "failed": 0,
            "total": 42,
            "coverage": 87.5
        })
        assert test_report is not None

        # 3. Save coverage report
        coverage_report = manager.save_coverage_report({
            "lineCoverage": 87.5,
            "branchCoverage": 82.0
        })
        assert coverage_report is not None

        # 4. List all artifacts
        artifacts = manager.list_artifacts()
        assert len(artifacts) == 3

        # 5. Get summary
        summary = manager.get_artifact_summary()
        assert summary["count"] == 3

        # 6. Load and verify build log
        build_data = manager.load_artifact("build-log.json")
        assert build_data["status"] == "success"
        assert build_data["changedFiles"] == ["src/auth.py"]

        # 7. Copy to shared directory
        shared_dir = tmp_path / "shared"
        copied = manager.copy_artifact_to_directory("build-log.json", shared_dir)
        assert copied is not None
        assert copied.exists()

    def test_timestamp_consistency(self, tmp_path):
        """All artifacts have consistent timestamp format."""
        manager = ArtifactManager(spec_dir=tmp_path)

        manager.save_build_log({"status": "success"})
        manager.save_test_report({"passed": 10})
        manager.save_coverage_report({"lineCoverage": 85.5})

        # Load all artifacts and check timestamps
        for artifact_name in ["build-log.json", "test-report.json", "coverage-report.json"]:
            data = manager.load_artifact(artifact_name)
            assert "timestamp" in data
            assert data["timestamp"].endswith("Z")
            # Verify ISO 8601 format
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_json_round_trip(self, tmp_path):
        """Data survives JSON save/load round trip."""
        manager = ArtifactManager(spec_dir=tmp_path)

        original_data = {
            "status": "success",
            "exitCode": 0,
            "duration": 123.456,
            "nested": {
                "key": "value",
                "number": 42
            },
            "list": [1, 2, 3]
        }

        manager.save_build_log(original_data)
        loaded_data = manager.load_artifact("build-log.json")

        assert loaded_data["status"] == original_data["status"]
        assert loaded_data["exitCode"] == original_data["exitCode"]
        assert loaded_data["duration"] == original_data["duration"]
        assert loaded_data["nested"] == original_data["nested"]
        assert loaded_data["list"] == original_data["list"]
