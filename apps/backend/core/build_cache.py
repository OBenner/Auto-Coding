"""
Build Cache Environment
=======================

Compiler-cache environment variables for compiled-language projects.

Fresh worktrees always cold-build, which makes every coder -> QA -> fixer
iteration expensive for C/C++ and Rust projects. ccache and sccache keep
their caches outside the worktree, so pointing the build at them lets a
brand-new worktree reuse object files from previous builds.

Only opt-in mechanisms are used:
- CMake honors CMAKE_<LANG>_COMPILER_LAUNCHER environment variables
- Cargo honors RUSTC_WRAPPER

Plain Make projects are deliberately left alone: overriding CC/CXX can
break builds that expect a bare compiler path.
"""

import os
import shutil
from pathlib import Path


def _is_cmake_project(project_dir: Path) -> bool:
    """Check if the project builds with CMake."""
    return (project_dir / "CMakeLists.txt").exists()


def _is_rust_project(project_dir: Path) -> bool:
    """Check if the project builds with Cargo."""
    return (project_dir / "Cargo.toml").exists()


def get_build_cache_env(
    project_dir: Path, existing_env: dict[str, str] | None = None
) -> dict[str, str]:
    """
    Get compiler-cache env vars for the agent session.

    Args:
        project_dir: Root directory of the project being built
        existing_env: Env vars already collected for the SDK subprocess;
            variables present there (or in os.environ) are never overridden

    Returns:
        Dict of env vars to add (empty when no cache tool applies)
    """
    project_dir = Path(project_dir)
    existing = {**os.environ, **(existing_env or {})}
    env: dict[str, str] = {}

    if _is_cmake_project(project_dir) and shutil.which("ccache"):
        for var in ("CMAKE_C_COMPILER_LAUNCHER", "CMAKE_CXX_COMPILER_LAUNCHER"):
            if var not in existing:
                env[var] = "ccache"

    if _is_rust_project(project_dir) and shutil.which("sccache"):
        if "RUSTC_WRAPPER" not in existing:
            env["RUSTC_WRAPPER"] = "sccache"

    return env


__all__ = ["get_build_cache_env"]
