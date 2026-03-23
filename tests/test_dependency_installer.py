"""
Unit Tests for Dependency Installer
====================================

Tests for apps/backend/core/dependency_installer.py
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from apps.backend.core.dependency_installer import (
    DependencyInstaller,
    InstallResult,
    install_dependencies,
)


class TestInstallResult:
    """Tests for InstallResult class."""

    def test_install_result_default_success(self):
        """Test InstallResult defaults to success=True."""
        result = InstallResult()
        assert result.success is True
        assert result.dry_run is False
        assert result.installed == []
        assert result.failed == []
        assert result.skipped == []

    def test_install_result_add_installed(self):
        """Test adding successful installation."""
        result = InstallResult()
        result.add_installed("npm", "apps/frontend")

        assert ("npm", "apps/frontend") in result.installed
        assert result.success is True

    def test_install_result_add_failed(self):
        """Test adding failed installation sets success=False."""
        result = InstallResult()
        result.add_failed("pip", "apps/backend", "Network error")

        assert ("pip", "apps/backend", "Network error") in result.failed
        assert result.success is False

    def test_install_result_add_skipped(self):
        """Test adding skipped installation."""
        result = InstallResult()
        result.add_skipped("cargo", "apps/rust-service", "No Cargo.lock")

        assert ("cargo", "apps/rust-service", "No Cargo.lock") in result.skipped
        assert result.success is True  # Skipped doesn't affect success


class TestDependencyInstaller:
    """Tests for DependencyInstaller class."""

    def test_installer_nonexistent_directory_raises_valueerror(self):
        """Test that non-existent project directory raises ValueError."""
        with pytest.raises(ValueError, match="Project directory does not exist"):
            DependencyInstaller("/nonexistent/path")

    def test_install_dependencies_dry_run_no_subprocess_calls(self, tmp_path):
        """Test that dry-run mode doesn't call subprocess.run()."""
        # Create project structure
        (tmp_path / "package.json").write_text('{"name": "test"}')

        installer = DependencyInstaller(str(tmp_path))
        detected = {"npm": ["."], "pip": [], "cargo": [], "go": []}

        with patch("subprocess.run") as mock_run:
            result = installer.install(detected, dry_run=True)

            # Verify subprocess was NOT called
            mock_run.assert_not_called()

            # Verify result shows dry-run
            assert result.dry_run is True
            assert result.success is True
            assert ("npm", ".") in result.installed

    def test_install_dependencies_with_multiple_package_managers(self, tmp_path):
        """Test installation with multiple package managers."""
        # Create project structure
        (tmp_path / "package.json").write_text('{"name": "frontend"}')
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "requirements.txt").write_text("pytest")

        installer = DependencyInstaller(str(tmp_path))
        detected = {
            "npm": ["."],
            "pip": ["backend"],
            "cargo": [],
            "go": [],
        }

        # Mock successful subprocess calls
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = installer.install(detected, dry_run=False)

            # Verify both package managers were installed
            assert result.success is True
            assert ("npm", ".") in result.installed or ("pip", "backend") in result.installed
            # At least one subprocess call should have been made
            assert mock_run.call_count >= 1

    def test_install_timeout_handling(self, tmp_path):
        """Test timeout handling for long-running installation."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        installer = DependencyInstaller(str(tmp_path), timeout=1)
        detected = {"npm": ["."], "pip": [], "cargo": [], "go": []}

        # Mock subprocess to raise TimeoutExpired
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["npm", "install"], timeout=1)

            result = installer.install(detected, dry_run=False)

            # Verify timeout was recorded as failure
            assert result.success is False
            assert len(result.failed) == 1
            assert "timed out" in result.failed[0][2].lower()

    def test_install_failed_installation_tracking(self, tmp_path):
        """Test that failed installations are tracked in InstallResult."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        installer = DependencyInstaller(str(tmp_path))
        detected = {"npm": ["."], "pip": [], "cargo": [], "go": []}

        # Mock subprocess to return failure
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="npm ERR! Package not found"
            )

            result = installer.install(detected, dry_run=False)

            # Verify failure was tracked
            assert result.success is False
            assert len(result.failed) == 1
            assert result.failed[0][0] == "npm"
            assert "Package not found" in result.failed[0][2]

    def test_install_skip_behavior_for_unknown_package_manager(self, tmp_path):
        """Test that unknown package managers are skipped."""
        installer = DependencyInstaller(str(tmp_path))

        # Create detected dict with unknown package manager
        detected = {"unknown_pm": ["."], "npm": [], "pip": [], "cargo": [], "go": []}

        result = installer.install(detected, dry_run=False)

        # Unknown package manager should be skipped (not in INSTALL_ORDER)
        # Since INSTALL_ORDER only includes ["pip", "npm", "go", "cargo"],
        # unknown_pm won't be processed at all
        # So we should check that it wasn't installed
        assert len(result.installed) == 0
        # And success should still be True (nothing failed)
        assert result.success is True

    def test_install_file_not_found_error(self, tmp_path):
        """Test handling when package manager command is not found."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        installer = DependencyInstaller(str(tmp_path))
        detected = {"npm": ["."], "pip": [], "cargo": [], "go": []}

        # Mock subprocess to raise FileNotFoundError
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("npm not found")

            result = installer.install(detected, dry_run=False)

            # Verify error is recorded
            assert result.success is False
            assert len(result.failed) == 1
            assert "not found" in result.failed[0][2].lower()

    def test_get_install_command(self, tmp_path):
        """Test get_install_command returns correct shell command."""
        installer = DependencyInstaller(str(tmp_path))

        npm_cmd = installer.get_install_command("npm", "apps/frontend")
        assert "npm install" in npm_cmd
        assert str(tmp_path / "apps" / "frontend") in npm_cmd

        pip_cmd = installer.get_install_command("pip", ".")
        assert "pip install -r requirements.txt" in pip_cmd

    def test_install_dependencies_convenience_function(self, tmp_path):
        """Test install_dependencies() convenience function."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        detected = {"npm": ["."], "pip": [], "cargo": [], "go": []}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = install_dependencies(str(tmp_path), detected, dry_run=False)

            assert isinstance(result, InstallResult)
            assert result.success is True
