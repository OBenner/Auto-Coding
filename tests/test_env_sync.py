"""
Unit Tests for Env Sync Orchestrator
======================================

Tests for apps/backend/core/env_sync.py
"""

import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from apps.backend.core.env_sync import (
    run_env_sync,
    EnvSyncResult,
    _detect_packages,
    _install_dependencies,
    _configure_environment,
    _validate_graphiti,
    _test_providers,
    _generate_report,
    _get_summary,
)


class TestEnvSyncResult:
    """Tests for EnvSyncResult class."""

    def test_env_sync_result_initialization(self):
        """Test EnvSyncResult initializes with correct defaults."""
        result = EnvSyncResult()

        assert result.success is False
        assert result.start_time > 0
        assert result.end_time is None
        assert result.issues == []
        assert result.warnings == []
        assert result.fixes == []

    def test_env_sync_result_finish(self):
        """Test finish() marks completion and sets end_time."""
        result = EnvSyncResult()
        time.sleep(0.1)  # Small delay to ensure measurable duration

        result.finish(success=True)

        assert result.success is True
        assert result.end_time is not None
        assert result.end_time > result.start_time

    def test_env_sync_result_get_duration(self):
        """Test get_duration() returns formatted duration string."""
        result = EnvSyncResult()
        time.sleep(0.1)
        result.finish()

        duration = result.get_duration()

        # Should be in format like "0s" or "1s"
        assert isinstance(duration, str)
        assert "s" in duration

    def test_env_sync_result_to_dict(self):
        """Test to_dict() converts result to dictionary."""
        result = EnvSyncResult()
        result.detection_result = {"npm": ["."], "pip": []}
        result.finish(success=True)

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert "duration" in result_dict
        assert result_dict["detection"] == {"npm": ["."], "pip": []}


class TestRunEnvSync:
    """Tests for run_env_sync() orchestrator function."""

    def test_run_env_sync_dry_run_no_modifications(self, tmp_path):
        """Test dry-run mode doesn't make file modifications."""
        # Mock all phase functions
        with patch("apps.backend.core.env_sync._detect_packages") as mock_detect:
            mock_detect.return_value = {"npm": [], "pip": [], "cargo": [], "go": []}

            with patch("apps.backend.core.env_sync._install_dependencies") as mock_install:
                mock_install_result = MagicMock()
                mock_install_result.dry_run = True
                mock_install_result.installed = []
                mock_install_result.failed = []
                mock_install_result.skipped = []
                mock_install.return_value = mock_install_result

                with patch("apps.backend.core.env_sync._configure_environment") as mock_config:
                    mock_config.return_value = {"success": True, "variables_configured": 0, "errors": []}

                    with patch("apps.backend.core.env_sync._validate_graphiti") as mock_graphiti:
                        mock_graphiti_result = MagicMock()
                        mock_graphiti_result.errors = []
                        mock_graphiti_result.warnings = []
                        mock_graphiti_result.fixes = []
                        mock_graphiti.return_value = mock_graphiti_result

                        with patch("apps.backend.core.env_sync._test_providers") as mock_providers:
                            mock_providers.return_value = {}

                            # Suppress print output
                            with patch("builtins.print"):
                                result = run_env_sync(
                                    project_dir=str(tmp_path),
                                    dry_run=True,
                                    verbose=False
                                )

                            # Verify dry-run was passed to install
                            mock_install.assert_called_once()
                            call_args = mock_install.call_args
                            assert call_args[0][2] is True  # dry_run=True

                            # Result should be successful
                            assert result["success"] is True

    def test_run_env_sync_skip_flags(self, tmp_path):
        """Test skip flags (skip_install, skip_config, skip_validation) work correctly."""
        with patch("apps.backend.core.env_sync._detect_packages") as mock_detect:
            mock_detect.return_value = {"npm": [], "pip": [], "cargo": [], "go": []}

            with patch("apps.backend.core.env_sync._install_dependencies") as mock_install:
                with patch("apps.backend.core.env_sync._configure_environment") as mock_config:
                    with patch("apps.backend.core.env_sync._validate_graphiti") as mock_graphiti:
                        with patch("apps.backend.core.env_sync._test_providers") as mock_providers:
                            with patch("builtins.print"):
                                result = run_env_sync(
                                    project_dir=str(tmp_path),
                                    skip_install=True,
                                    skip_config=True,
                                    skip_validation=True,
                                    verbose=False
                                )

                            # Verify skipped phases were not called
                            mock_install.assert_not_called()
                            mock_config.assert_not_called()
                            mock_graphiti.assert_not_called()
                            mock_providers.assert_not_called()

                            # Should still succeed
                            assert result["success"] is True

    def test_run_env_sync_result_structure(self, tmp_path):
        """Test result structure includes all phases."""
        # Mock all phases to return valid data
        with patch("apps.backend.core.env_sync._detect_packages") as mock_detect:
            mock_detect.return_value = {"npm": ["."], "pip": [], "cargo": [], "go": []}

            with patch("apps.backend.core.env_sync._install_dependencies") as mock_install:
                mock_install_result = MagicMock()
                mock_install_result.dry_run = False
                mock_install_result.installed = [("npm", ".")]
                mock_install_result.failed = []
                mock_install_result.skipped = []
                mock_install.return_value = mock_install_result

                with patch("apps.backend.core.env_sync._configure_environment") as mock_config:
                    mock_config.return_value = {"success": True, "variables_configured": 5, "errors": []}

                    with patch("apps.backend.core.env_sync._validate_graphiti") as mock_graphiti:
                        mock_graphiti_result = MagicMock()
                        mock_graphiti_result.errors = []
                        mock_graphiti_result.warnings = []
                        mock_graphiti_result.fixes = []
                        mock_graphiti_result.to_dict.return_value = {"enabled": True}
                        mock_graphiti.return_value = mock_graphiti_result

                        with patch("apps.backend.core.env_sync._test_providers") as mock_providers:
                            mock_provider_result = MagicMock()
                            mock_provider_result.success = True
                            mock_provider_result.message = "Connected"
                            mock_providers.return_value = {"openai": mock_provider_result}

                            with patch("builtins.print"):
                                result = run_env_sync(project_dir=str(tmp_path), verbose=False)

                            # Verify result has all required fields
                            assert "success" in result
                            assert "duration" in result
                            assert "detection" in result
                            assert "installation" in result
                            assert "configuration" in result
                            assert "graphiti" in result
                            assert "providers" in result
                            assert "issues" in result
                            assert "warnings" in result
                            assert "fixes" in result
                            assert "report" in result

    def test_run_env_sync_error_handling(self, tmp_path):
        """Test error handling when dependencies fail."""
        with patch("apps.backend.core.env_sync._detect_packages") as mock_detect:
            mock_detect.return_value = {"npm": ["."], "pip": [], "cargo": [], "go": []}

            with patch("apps.backend.core.env_sync._install_dependencies") as mock_install:
                # Mock installation failure
                mock_install_result = MagicMock()
                mock_install_result.dry_run = False
                mock_install_result.installed = []
                mock_install_result.failed = [("npm", ".", "Network error")]
                mock_install_result.skipped = []
                mock_install.return_value = mock_install_result

                with patch("apps.backend.core.env_sync._configure_environment") as mock_config:
                    mock_config.return_value = {"success": True, "variables_configured": 0, "errors": []}

                    with patch("apps.backend.core.env_sync._validate_graphiti") as mock_graphiti:
                        mock_graphiti_result = MagicMock()
                        mock_graphiti_result.errors = []
                        mock_graphiti_result.warnings = []
                        mock_graphiti_result.fixes = []
                        mock_graphiti.return_value = mock_graphiti_result

                        with patch("apps.backend.core.env_sync._test_providers") as mock_providers:
                            mock_providers.return_value = {}

                            with patch("builtins.print"):
                                result = run_env_sync(project_dir=str(tmp_path), verbose=False)

                            # Should have issues recorded
                            assert result["success"] is False
                            assert len(result["issues"]) > 0
                            assert any("Failed to install npm" in issue for issue in result["issues"])

    def test_run_env_sync_duration_tracking(self, tmp_path):
        """Test duration tracking and formatting."""
        with patch("apps.backend.core.env_sync._detect_packages") as mock_detect:
            mock_detect.return_value = {"npm": [], "pip": [], "cargo": [], "go": []}

            with patch("apps.backend.core.env_sync._install_dependencies"):
                with patch("apps.backend.core.env_sync._configure_environment"):
                    with patch("apps.backend.core.env_sync._validate_graphiti"):
                        with patch("apps.backend.core.env_sync._test_providers"):
                            with patch("builtins.print"):
                                result = run_env_sync(project_dir=str(tmp_path), verbose=False)

                            # Duration should be present and formatted
                            assert "duration" in result
                            assert isinstance(result["duration"], str)
                            assert "s" in result["duration"]

    def test_run_env_sync_report_generation(self, tmp_path):
        """Test report generation contains all sections."""
        with patch("apps.backend.core.env_sync._detect_packages") as mock_detect:
            mock_detect.return_value = {"npm": ["."], "pip": [], "cargo": [], "go": []}

            with patch("apps.backend.core.env_sync._install_dependencies") as mock_install:
                mock_install_result = MagicMock()
                mock_install_result.dry_run = False
                mock_install_result.installed = [("npm", ".")]
                mock_install_result.failed = []
                mock_install_result.skipped = []
                mock_install.return_value = mock_install_result

                with patch("apps.backend.core.env_sync._configure_environment") as mock_config:
                    mock_config.return_value = {"success": True, "variables_configured": 3, "errors": []}

                    with patch("apps.backend.core.env_sync._validate_graphiti") as mock_graphiti:
                        mock_graphiti_result = MagicMock()
                        mock_graphiti_result.enabled = True
                        mock_graphiti_result.config_valid = True
                        mock_graphiti_result.database_available = True
                        mock_graphiti_result.embedder_valid = True
                        mock_graphiti_result.embedder_connected = True
                        mock_graphiti_result.errors = []
                        mock_graphiti_result.warnings = []
                        mock_graphiti_result.fixes = []
                        mock_graphiti.return_value = mock_graphiti_result

                        with patch("apps.backend.core.env_sync._test_providers") as mock_providers:
                            mock_providers.return_value = {}

                            with patch("builtins.print"):
                                result = run_env_sync(project_dir=str(tmp_path), verbose=False)

                            # Report should be present
                            assert "report" in result
                            assert isinstance(result["report"], str)

                            # Report should contain key sections
                            report = result["report"]
                            assert "Auto Code Environment Setup Report" in report
                            assert "Package Managers" in report or "Environment" in report


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_detect_packages(self, tmp_path):
        """Test _detect_packages calls package detector correctly."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        detected = _detect_packages(tmp_path, verbose=False)

        assert isinstance(detected, dict)
        assert "npm" in detected
        assert "pip" in detected

    def test_get_summary_success(self):
        """Test _get_summary for successful result."""
        result = EnvSyncResult()
        result.finish(success=True)

        summary = _get_summary(result)

        assert "ready" in summary.lower()

    def test_get_summary_with_issues(self):
        """Test _get_summary with issues."""
        result = EnvSyncResult()
        result.issues = ["Error 1", "Error 2"]
        result.warnings = ["Warning 1"]
        result.finish(success=False)

        summary = _get_summary(result)

        assert "2 issue(s)" in summary
        assert "1 warning(s)" in summary

    def test_generate_report_contains_all_sections(self, tmp_path):
        """Test _generate_report includes all required sections."""
        result = EnvSyncResult()
        result.detection_result = {"npm": ["."], "pip": []}
        result.finish(success=True)

        report = _generate_report(result, tmp_path, dry_run=False)

        # Check for key sections
        assert "Auto Code Environment Setup Report" in report
        assert "Package Managers" in report
        assert "Summary" in report
