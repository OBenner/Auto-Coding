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
from .language_rules import LANGUAGE_SECURITY_RULES, LANGUAGE_SECURITY_SCANNERS

__all__ = [
    "get_security_profile",
    "reset_profile_cache",
    "get_security_scanners",
    "get_security_rules",
    "get_all_security_scanners",
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


# =============================================================================
# LANGUAGE SECURITY INTEGRATION
# =============================================================================


def get_security_scanners(language: str) -> set[str]:
    """
    Get security scanners for a specific language.

    Args:
        language: Programming language name (lowercase)

    Returns:
        Set of security scanner commands for the language.
        Empty set if language not found.

    Example:
        >>> scanners = get_security_scanners("go")
        >>> print(scanners)
        {'gosec', 'staticcheck', 'govulncheck'}
    """
    return LANGUAGE_SECURITY_SCANNERS.get(language.lower(), set())


def get_security_rules(language: str) -> dict[str, list[str]]:
    """
    Get security rules for a specific language.

    Args:
        language: Programming language name (lowercase)

    Returns:
        Dict containing:
        - dangerous_functions: List of functions with security risks
        - unsafe_patterns: List of unsafe code patterns
        - secure_alternatives: List of recommended secure practices
        Empty dict if language not found.

    Example:
        >>> rules = get_security_rules("php")
        >>> print(rules["dangerous_functions"])
        ['eval', 'exec', 'system', ...]
    """
    return LANGUAGE_SECURITY_RULES.get(language.lower(), {})


def get_all_security_scanners(profile: SecurityProfile) -> set[str]:
    """
    Get all security scanners for languages detected in a security profile.

    Args:
        profile: SecurityProfile with detected languages

    Returns:
        Combined set of all security scanners for detected languages

    Example:
        >>> profile = get_security_profile(project_dir)
        >>> scanners = get_all_security_scanners(profile)
        >>> print(scanners)
        {'gosec', 'cargo-audit', 'phpstan', 'bandit'}
    """
    all_scanners: set[str] = set()

    # Get scanners for each detected language
    for language in profile.detected_stack.languages:
        scanners = get_security_scanners(language)
        all_scanners.update(scanners)

    return all_scanners
