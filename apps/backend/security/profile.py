"""
Security Profile Management
============================

Manages security profiles for projects, including caching and validation.
Uses project_analyzer to create dynamic security profiles based on detected stacks.
"""

from pathlib import Path

from project_analyzer import (
    SecurityProfile,
    get_or_create_profile,
)

from .constants import ALLOWLIST_FILENAME, PROFILE_FILENAME

__all__ = [
    "get_security_profile",
    "reset_profile_cache",
]

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Cache dict to avoid re-analyzing on every command.
# Keys: profile, project_dir, spec_dir, profile_mtime, allowlist_mtime
_cache: dict = {
    "profile": None,
    "project_dir": None,
    "spec_dir": None,
    "profile_mtime": None,
    "allowlist_mtime": None,
}


def _get_profile_path(project_dir: Path) -> Path:
    """Get the security profile file path for a project."""
    return project_dir / PROFILE_FILENAME


def _get_allowlist_path(project_dir: Path) -> Path:
    """Get the allowlist file path for a project."""
    return project_dir / ALLOWLIST_FILENAME


def _get_profile_mtime(project_dir: Path) -> float | None:
    """Get the modification time of the security profile file, or None if not exists."""
    profile_path = _get_profile_path(project_dir)
    try:
        return profile_path.stat().st_mtime
    except OSError:
        return None


def _get_allowlist_mtime(project_dir: Path) -> float | None:
    """Get the modification time of the allowlist file, or None if not exists."""
    allowlist_path = _get_allowlist_path(project_dir)
    try:
        return allowlist_path.stat().st_mtime
    except OSError:
        return None


def get_security_profile(
    project_dir: Path, spec_dir: Path | None = None
) -> SecurityProfile:
    """
    Get the security profile for a project, using cache when possible.

    The cache is invalidated when:
    - The project directory changes
    - The security profile file is created (was None, now exists)
    - The security profile file is modified (mtime changed)
    - The allowlist file is created, modified, or deleted

    Args:
        project_dir: Project root directory
        spec_dir: Optional spec directory

    Returns:
        SecurityProfile for the project
    """
    project_dir = Path(project_dir).resolve()
    resolved_spec_dir = Path(spec_dir).resolve() if spec_dir else None

    # Check if cache is valid (both project_dir and spec_dir must match)
    if (
        _cache["profile"] is not None
        and _cache["project_dir"] == project_dir
        and _cache["spec_dir"] == resolved_spec_dir
    ):
        # Check if files have been created or modified since caching
        current_profile_mtime = _get_profile_mtime(project_dir)
        current_allowlist_mtime = _get_allowlist_mtime(project_dir)

        # Cache is valid if both mtimes are unchanged
        if (
            current_profile_mtime == _cache["profile_mtime"]
            and current_allowlist_mtime == _cache["allowlist_mtime"]
        ):
            return _cache["profile"]

        # File was created, modified, or deleted - invalidate cache
        # (This happens when analyzer creates the file after agent starts,
        # or when user adds/updates the allowlist)

    # Analyze and cache
    _cache["profile"] = get_or_create_profile(project_dir, spec_dir)
    _cache["project_dir"] = project_dir
    _cache["spec_dir"] = resolved_spec_dir
    _cache["profile_mtime"] = _get_profile_mtime(project_dir)
    _cache["allowlist_mtime"] = _get_allowlist_mtime(project_dir)

    return _cache["profile"]


def reset_profile_cache() -> None:
    """Reset the cached profile (useful for testing or re-analysis)."""
    _cache["profile"] = None
    _cache["project_dir"] = None
    _cache["spec_dir"] = None
    _cache["profile_mtime"] = None
    _cache["allowlist_mtime"] = None
