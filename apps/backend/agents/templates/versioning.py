"""
Template Versioning
===================

Version comparison and update logic for agent templates.

Provides semantic versioning utilities for comparing versions
and determining appropriate version increments based on changes.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class VersionPart:
    """
    Individual part of a semantic version.

    Attributes:
        major: Major version (breaking changes)
        minor: Minor version (new features)
        patch: Patch version (bug fixes)
        prerelease: Optional prerelease identifier (e.g., "alpha", "beta.1")
        build: Optional build metadata (e.g., "20130313144700")
    """

    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""


def parse_version(version: str) -> VersionPart:
    """
    Parse semantic version string into VersionPart.

    Args:
        version: Semantic version string (e.g., "1.2.3", "2.0.0-alpha.1")

    Returns:
        VersionPart object with parsed components

    Raises:
        ValueError: If version string is invalid
    """
    # Semantic versioning pattern: MAJOR.MINOR.PATCH(-PRERELEASE)?(+BUILD)?
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
    match = re.match(pattern, version)

    if not match:
        raise ValueError(f"Invalid semantic version: {version}")

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    prerelease = match.group(4) or ""
    build = match.group(5) or ""

    return VersionPart(
        major=major, minor=minor, patch=patch, prerelease=prerelease, build=build
    )


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic version strings.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2

    Raises:
        ValueError: If either version string is invalid
    """
    parsed_v1 = parse_version(v1)
    parsed_v2 = parse_version(v2)

    # Compare major, minor, patch
    if parsed_v1.major != parsed_v2.major:
        return -1 if parsed_v1.major < parsed_v2.major else 1
    if parsed_v1.minor != parsed_v2.minor:
        return -1 if parsed_v1.minor < parsed_v2.minor else 1
    if parsed_v1.patch != parsed_v2.patch:
        return -1 if parsed_v1.patch < parsed_v2.patch else 1

    # Compare prerelease (prerelease versions have lower precedence)
    if parsed_v1.prerelease != parsed_v2.prerelease:
        # If one has prerelease and other doesn't, the one without is greater
        if not parsed_v1.prerelease and parsed_v2.prerelease:
            return 1
        if parsed_v1.prerelease and not parsed_v2.prerelease:
            return -1

        # Both have prerelease, compare dot-separated identifiers
        v1_parts = parsed_v1.prerelease.split(".")
        v2_parts = parsed_v2.prerelease.split(".")

        for p1, p2 in zip(v1_parts, v2_parts):
            # Try numeric comparison first
            try:
                n1 = int(p1)
                n2 = int(p2)
                if n1 != n2:
                    return -1 if n1 < n2 else 1
            except ValueError:
                # String comparison
                if p1 != p2:
                    return -1 if p1 < p2 else 1

        # If all equal up to min length, shorter prerelease has lower precedence (1.0.0-alpha < 1.0.0-alpha.1)
        if len(v1_parts) != len(v2_parts):
            return -1 if len(v1_parts) < len(v2_parts) else 1

    # Build metadata does not affect precedence
    return 0


def is_newer(current: str, other: str) -> bool:
    """
    Check if other version is newer than current.

    Args:
        current: Current version string
        other: Other version to compare

    Returns:
        True if other is newer than current
    """
    return compare_versions(current, other) < 0


def get_next_version(current: str, change_type: str) -> str:
    """
    Calculate next version based on change type.

    Note: Any prerelease or build metadata on the current version is
    intentionally discarded when computing the next version.

    Args:
        current: Current version string
        change_type: Type of change - "major", "minor", or "patch"

    Returns:
        Next version string

    Raises:
        ValueError: If version is invalid or change_type is unknown
    """
    if change_type not in ("major", "minor", "patch"):
        raise ValueError(
            f"Invalid change_type: {change_type}. Must be 'major', 'minor', or 'patch'"
        )

    parsed = parse_version(current)

    if change_type == "major":
        return f"{parsed.major + 1}.0.0"
    elif change_type == "minor":
        return f"{parsed.major}.{parsed.minor + 1}.0"
    else:  # patch
        return f"{parsed.major}.{parsed.minor}.{parsed.patch + 1}"


def suggest_version_increment(
    old_template: dict[str, Any], new_template: dict[str, Any]
) -> str:
    """
    Suggest version increment based on changes between templates.

    Args:
        old_template: Old template dictionary (from to_dict())
        new_template: New template dictionary (from to_dict())

    Returns:
        Suggested increment type - "major", "minor", or "patch"

    Raises:
        ValueError: If version strings are invalid
    """
    # Check for breaking changes (major)
    breaking_changes = [
        "custom_prompt",  # Prompt changes are breaking
        "tools",  # Tool changes can break workflows
        "mcp_servers",  # MCP server changes can break integrations
        "parameters",  # Parameter changes are breaking
    ]

    for field in breaking_changes:
        if old_template.get(field) != new_template.get(field):
            return "major"

    # Check for new features (minor)
    feature_additions = ["tags"]  # Adding tags is a feature

    for field in feature_additions:
        old_value = old_template.get(field, [])
        new_value = new_template.get(field, [])
        # New tags added (not removed)
        if set(new_value) - set(old_value):
            return "minor"

    # Check for metadata updates (patch)
    metadata_changes = ["description", "author", "thinking_level"]

    for field in metadata_changes:
        if old_template.get(field) != new_template.get(field):
            return "patch"

    # Default to patch if version changed but nothing else
    if old_template.get("version") != new_template.get("version"):
        return "patch"

    # No significant changes, return patch as default
    return "patch"


def validate_version_format(version: str) -> list[str]:
    """
    Validate semantic version format.

    Args:
        version: Version string to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not version:
        errors.append("Version cannot be empty")
        return errors

    try:
        parse_version(version)
    except ValueError as e:
        errors.append(str(e))

    return errors
