"""
Unit Tests for Package Detector
=================================

Tests for apps/backend/core/package_detector.py
"""

import pytest
from pathlib import Path
from apps.backend.core.package_detector import detect_package_managers, _should_skip_directory


class TestDetectPackageManagers:
    """Tests for detect_package_managers() function."""

    def test_detect_package_managers_monorepo_with_multiple_managers(self, tmp_path):
        """Test detection in monorepo with npm, pip, cargo, and go."""
        # Create monorepo structure
        (tmp_path / "package.json").write_text('{"name": "root"}')
        (tmp_path / "apps" / "frontend").mkdir(parents=True)
        (tmp_path / "apps" / "frontend" / "package.json").write_text('{"name": "frontend"}')
        (tmp_path / "apps" / "backend").mkdir(parents=True)
        (tmp_path / "apps" / "backend" / "requirements.txt").write_text("pytest==7.0.0")
        (tmp_path / "apps" / "rust-service").mkdir(parents=True)
        (tmp_path / "apps" / "rust-service" / "Cargo.toml").write_text('[package]\nname = "rust-service"')
        (tmp_path / "apps" / "go-service").mkdir(parents=True)
        (tmp_path / "apps" / "go-service" / "go.mod").write_text('module example.com/go-service')

        # Detect package managers
        result = detect_package_managers(str(tmp_path))

        # Verify all package managers detected
        assert "." in result["npm"], "Root package.json should be detected"
        assert "apps/frontend" in result["npm"], "Frontend package.json should be detected"
        assert "apps/backend" in result["pip"], "Backend requirements.txt should be detected"
        assert "apps/rust-service" in result["cargo"], "Rust Cargo.toml should be detected"
        assert "apps/go-service" in result["go"], "Go go.mod should be detected"

    def test_detect_package_managers_empty_directory_returns_empty_dict(self, tmp_path):
        """Test detection in empty directory returns empty lists for each manager."""
        result = detect_package_managers(str(tmp_path))

        # All package manager lists should be empty
        assert result["npm"] == [], "Empty directory should have no npm packages"
        assert result["pip"] == [], "Empty directory should have no pip packages"
        assert result["cargo"] == [], "Empty directory should have no cargo packages"
        assert result["go"] == [], "Empty directory should have no go packages"

    def test_detect_package_managers_nonexistent_directory_raises_valueerror(self):
        """Test detection with non-existent directory raises ValueError."""
        with pytest.raises(ValueError, match="Project directory does not exist"):
            detect_package_managers("/nonexistent/directory/path")

    def test_detect_package_managers_ignores_common_directories(self, tmp_path):
        """Test that node_modules, .venv, .git are skipped during detection."""
        # Create package files in ignore directories
        (tmp_path / "node_modules" / "some-package").mkdir(parents=True)
        (tmp_path / "node_modules" / "some-package" / "package.json").write_text('{"name": "ignored"}')
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / ".venv" / "lib" / "requirements.txt").write_text("should-be-ignored")
        (tmp_path / ".git" / "objects").mkdir(parents=True)
        (tmp_path / ".git" / "objects" / "go.mod").write_text("should-be-ignored")

        # Create valid package file at root
        (tmp_path / "package.json").write_text('{"name": "valid"}')

        result = detect_package_managers(str(tmp_path))

        # Only root package should be detected, ignore dirs should be skipped
        assert result["npm"] == ["."], "Should only detect root package.json"
        assert result["pip"] == [], "Should skip .venv directory"
        assert result["go"] == [], "Should skip .git directory"

    def test_detect_package_managers_nested_package_managers(self, tmp_path):
        """Test detection of nested package managers in subdirectories."""
        # Create nested Python projects
        (tmp_path / "apps" / "backend").mkdir(parents=True)
        (tmp_path / "apps" / "backend" / "requirements.txt").write_text("flask==2.0.0")
        (tmp_path / "apps" / "backend" / "services" / "auth").mkdir(parents=True)
        (tmp_path / "apps" / "backend" / "services" / "auth" / "requirements.txt").write_text("jwt==1.0.0")

        result = detect_package_managers(str(tmp_path))

        # Both nested locations should be detected
        assert "apps/backend" in result["pip"], "Top-level backend should be detected"
        assert "apps/backend/services/auth" in result["pip"], "Nested auth service should be detected"

    def test_detect_package_managers_multiple_occurrences_same_type(self, tmp_path):
        """Test detection with multiple package.json files."""
        # Create multiple npm packages
        (tmp_path / "apps" / "web").mkdir(parents=True)
        (tmp_path / "apps" / "web" / "package.json").write_text('{"name": "web"}')
        (tmp_path / "apps" / "mobile").mkdir(parents=True)
        (tmp_path / "apps" / "mobile" / "package.json").write_text('{"name": "mobile"}')
        (tmp_path / "apps" / "desktop").mkdir(parents=True)
        (tmp_path / "apps" / "desktop" / "package.json").write_text('{"name": "desktop"}')

        result = detect_package_managers(str(tmp_path))

        # All three npm packages should be detected
        assert len(result["npm"]) == 3, "Should detect 3 npm packages"
        assert "apps/web" in result["npm"]
        assert "apps/mobile" in result["npm"]
        assert "apps/desktop" in result["npm"]

    def test_detect_package_managers_with_setup_py(self, tmp_path):
        """Test detection of Python projects with setup.py but no requirements.txt."""
        # Create Python project with only setup.py
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='myproject')")

        result = detect_package_managers(str(tmp_path))

        # Should detect as pip project via setup.py
        assert "." in result["pip"], "Should detect setup.py as pip project"

    def test_detect_package_managers_with_pyproject_toml(self, tmp_path):
        """Test detection of Python projects with pyproject.toml but no requirements.txt."""
        # Create Python project with only pyproject.toml
        (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]')

        result = detect_package_managers(str(tmp_path))

        # Should detect as pip project via pyproject.toml
        assert "." in result["pip"], "Should detect pyproject.toml as pip project"


class TestShouldSkipDirectory:
    """Tests for _should_skip_directory() helper function."""

    def test_should_skip_directory_node_modules(self, tmp_path):
        """Test that node_modules directory is skipped."""
        root = tmp_path
        node_modules_path = root / "node_modules" / "package"
        node_modules_path.mkdir(parents=True)

        assert _should_skip_directory(node_modules_path, root) is True

    def test_should_skip_directory_venv(self, tmp_path):
        """Test that .venv and venv directories are skipped."""
        root = tmp_path
        venv_path = root / ".venv" / "lib"
        venv_path.mkdir(parents=True)

        assert _should_skip_directory(venv_path, root) is True

        venv2_path = root / "venv" / "lib"
        venv2_path.mkdir(parents=True)

        assert _should_skip_directory(venv2_path, root) is True

    def test_should_skip_directory_git(self, tmp_path):
        """Test that .git directory is skipped."""
        root = tmp_path
        git_path = root / ".git" / "objects"
        git_path.mkdir(parents=True)

        assert _should_skip_directory(git_path, root) is True

    def test_should_skip_directory_build_dirs(self, tmp_path):
        """Test that build, dist, target directories are skipped."""
        root = tmp_path

        build_path = root / "build" / "output"
        build_path.mkdir(parents=True)
        assert _should_skip_directory(build_path, root) is True

        dist_path = root / "dist" / "bundle"
        dist_path.mkdir(parents=True)
        assert _should_skip_directory(dist_path, root) is True

        target_path = root / "target" / "release"
        target_path.mkdir(parents=True)
        assert _should_skip_directory(target_path, root) is True

    def test_should_skip_directory_valid_path(self, tmp_path):
        """Test that valid project paths are not skipped."""
        root = tmp_path
        valid_path = root / "apps" / "backend" / "core"
        valid_path.mkdir(parents=True)

        assert _should_skip_directory(valid_path, root) is False

    def test_should_skip_directory_path_outside_root(self, tmp_path):
        """Test that paths outside root are skipped."""
        root = tmp_path / "project"
        root.mkdir()

        outside_path = tmp_path / "other_project" / "src"
        outside_path.mkdir(parents=True)

        assert _should_skip_directory(outside_path, root) is True
