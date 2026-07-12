#!/usr/bin/env python3
"""
Tests for the build_cache module.

Tests cover:
- ccache env injection for CMake projects
- sccache env injection for Cargo projects
- Respecting user-set variables
- No-op behavior when tools are missing or project is not compiled
"""

# Add auto-claude to path for imports
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from core.build_cache import get_build_cache_env


@pytest.fixture
def temp_dir(tmp_path):
    """Alias fixture for a temporary project directory."""
    return tmp_path


def _which_factory(available: set[str]):
    """Return a shutil.which stand-in knowing only the given tools."""

    def _which(name: str):
        return f"/usr/bin/{name}" if name in available else None

    return _which


class TestBuildCacheEnv:
    """Tests for get_build_cache_env."""

    def test_cmake_project_with_ccache(self, temp_dir):
        """CMake project gets compiler launcher vars when ccache exists."""
        (temp_dir / "CMakeLists.txt").write_text("project(demo)")

        with patch("core.build_cache.shutil.which", _which_factory({"ccache"})):
            env = get_build_cache_env(temp_dir)

        assert env["CMAKE_C_COMPILER_LAUNCHER"] == "ccache"
        assert env["CMAKE_CXX_COMPILER_LAUNCHER"] == "ccache"

    def test_cmake_project_without_ccache(self, temp_dir):
        """No launcher vars when ccache is not installed."""
        (temp_dir / "CMakeLists.txt").write_text("project(demo)")

        with patch("core.build_cache.shutil.which", _which_factory(set())):
            env = get_build_cache_env(temp_dir)

        assert env == {}

    def test_rust_project_with_sccache(self, temp_dir):
        """Cargo project gets RUSTC_WRAPPER when sccache exists."""
        (temp_dir / "Cargo.toml").write_text('[package]\nname = "demo"')

        with patch("core.build_cache.shutil.which", _which_factory({"sccache"})):
            env = get_build_cache_env(temp_dir)

        assert env["RUSTC_WRAPPER"] == "sccache"

    def test_user_set_vars_not_overridden(self, temp_dir):
        """Variables already present in the session env are respected."""
        (temp_dir / "CMakeLists.txt").write_text("project(demo)")
        (temp_dir / "Cargo.toml").write_text('[package]\nname = "demo"')

        existing = {
            "CMAKE_C_COMPILER_LAUNCHER": "distcc",
            "RUSTC_WRAPPER": "my-wrapper",
        }
        with patch(
            "core.build_cache.shutil.which",
            _which_factory({"ccache", "sccache"}),
        ):
            env = get_build_cache_env(temp_dir, existing)

        assert "CMAKE_C_COMPILER_LAUNCHER" not in env
        assert "RUSTC_WRAPPER" not in env
        # CXX launcher was not pre-set, so it is still added
        assert env["CMAKE_CXX_COMPILER_LAUNCHER"] == "ccache"

    def test_os_environ_vars_not_overridden(self, temp_dir):
        """Variables set in os.environ are respected."""
        (temp_dir / "CMakeLists.txt").write_text("project(demo)")

        with (
            patch("core.build_cache.shutil.which", _which_factory({"ccache"})),
            patch.dict(
                "core.build_cache.os.environ",
                {"CMAKE_C_COMPILER_LAUNCHER": "distcc"},
            ),
        ):
            env = get_build_cache_env(temp_dir)

        assert "CMAKE_C_COMPILER_LAUNCHER" not in env
        assert env["CMAKE_CXX_COMPILER_LAUNCHER"] == "ccache"

    def test_non_compiled_project_is_noop(self, temp_dir):
        """Python/JS projects get no build-cache vars."""
        (temp_dir / "package.json").write_text("{}")
        (temp_dir / "requirements.txt").write_text("flask\n")

        with patch(
            "core.build_cache.shutil.which",
            _which_factory({"ccache", "sccache"}),
        ):
            env = get_build_cache_env(temp_dir)

        assert env == {}

    def test_make_only_project_is_noop(self, temp_dir):
        """Plain Make projects are left alone (no CC/CXX override)."""
        (temp_dir / "Makefile").write_text("all:\n\tgcc main.c\n")
        (temp_dir / "main.c").write_text("int main(void) { return 0; }")

        with patch("core.build_cache.shutil.which", _which_factory({"ccache"})):
            env = get_build_cache_env(temp_dir)

        assert env == {}
