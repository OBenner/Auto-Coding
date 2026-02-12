#!/usr/bin/env python3
"""
Coverage Configuration Module
==============================

Loads and manages coverage thresholds for projects.
This module provides configuration for minimum coverage requirements,
critical path definitions, and project-specific coverage rules.

The coverage configuration is used by:
- QA Reviewer: To validate coverage meets project requirements
- Coverage Validator: To enforce minimum thresholds
- Test Generator: To identify areas requiring additional tests

Usage:
    from spec.coverage_config import load_coverage_config

    config = load_coverage_config(project_dir, spec_dir)
    print(f"Minimum coverage: {config.minimum_coverage}%")
    print(f"Critical paths: {config.critical_paths}")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class CriticalPath:
    """
    Represents a critical code path requiring 100% coverage.

    Attributes:
        name: Descriptive name of the critical path
        pattern: File pattern or path to match (e.g., "*/auth/*", "payment.py")
        reason: Why this path is critical (e.g., "handles authentication")
        required_coverage: Coverage percentage required (default 100%)
    """

    name: str
    pattern: str
    reason: str
    required_coverage: float = 100.0


@dataclass
class CoverageConfig:
    """
    Complete coverage configuration for a project.

    Attributes:
        minimum_coverage: Minimum overall coverage percentage (0-100)
        minimum_line_coverage: Minimum line coverage percentage
        minimum_branch_coverage: Minimum branch coverage percentage
        critical_paths: List of critical paths requiring 100% coverage
        excluded_paths: Patterns to exclude from coverage (e.g., "*/tests/*")
        enforce_on_modified_files: Whether to enforce coverage on changed files
        fail_under_threshold: Whether to fail if coverage below minimum
        config_source: Where the config was loaded from
    """

    minimum_coverage: float = 80.0
    minimum_line_coverage: float | None = None
    minimum_branch_coverage: float | None = None
    critical_paths: list[CriticalPath] = field(default_factory=list)
    excluded_paths: list[str] = field(default_factory=list)
    enforce_on_modified_files: bool = True
    fail_under_threshold: bool = True
    config_source: str = "default"


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================


def load_coverage_config(
    project_dir: str | Path,
    spec_dir: str | Path | None = None,
) -> CoverageConfig:
    """
    Load coverage configuration from project files or defaults.

    Checks for coverage config in this order:
    1. implementation_plan.json (qa_acceptance.unit_tests.minimum_coverage)
    2. pytest.ini or setup.cfg (pytest addopts --cov-fail-under)
    3. .coveragerc or pyproject.toml (coverage settings)
    4. Default values (80% minimum coverage)

    Args:
        project_dir: Root directory of the project
        spec_dir: Spec directory containing implementation_plan.json (optional)

    Returns:
        CoverageConfig with loaded or default settings

    Example:
        config = load_coverage_config("/path/to/project")
        print(f"Minimum coverage: {config.minimum_coverage}%")

        # With spec directory
        config = load_coverage_config(
            project_dir="/path/to/project",
            spec_dir=".auto-claude/specs/001-feature"
        )
    """
    project_dir = Path(project_dir).resolve()
    spec_dir_path = Path(spec_dir).resolve() if spec_dir else None

    # Try to load from implementation plan first
    if spec_dir_path:
        plan_config = _load_from_implementation_plan(spec_dir_path)
        if plan_config:
            return plan_config

    # Try to load from pytest config files
    pytest_config = _load_from_pytest_config(project_dir)
    if pytest_config:
        return pytest_config

    # Try to load from .coveragerc
    coveragerc_config = _load_from_coveragerc(project_dir)
    if coveragerc_config:
        return coveragerc_config

    # Try to load from pyproject.toml
    pyproject_config = _load_from_pyproject(project_dir)
    if pyproject_config:
        return pyproject_config

    # Return default config
    return CoverageConfig(
        minimum_coverage=80.0,
        config_source="default",
    )


def _load_from_implementation_plan(spec_dir: Path) -> CoverageConfig | None:
    """
    Load coverage config from implementation_plan.json.

    Looks for:
    - qa_acceptance.unit_tests.minimum_coverage
    - qa_acceptance.integration_tests.minimum_coverage
    - verification_strategy.acceptance_criteria (for critical paths)

    Args:
        spec_dir: Path to spec directory

    Returns:
        CoverageConfig if found, None otherwise
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return None

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    # Extract minimum coverage from qa_acceptance
    qa_acceptance = plan.get("qa_acceptance", {})
    unit_tests = qa_acceptance.get("unit_tests", {})
    minimum_coverage = unit_tests.get("minimum_coverage")

    if minimum_coverage is None:
        return None

    # Build config
    config = CoverageConfig(
        minimum_coverage=float(minimum_coverage),
        config_source="implementation_plan.json",
    )

    # Extract critical paths from acceptance criteria if available
    critical_paths = _extract_critical_paths_from_criteria(plan)
    config.critical_paths.extend(critical_paths)

    return config


def _extract_critical_paths_from_criteria(plan: dict) -> list[CriticalPath]:
    """
    Extract critical path definitions from acceptance criteria.

    Looks for patterns like:
    - "Critical paths require 100% coverage (authentication, payment processing)"
    - "Authentication code needs 100% coverage"
    - "Payment processing must be fully tested"

    Args:
        plan: Implementation plan dictionary

    Returns:
        List of CriticalPath objects extracted from criteria
    """
    critical_paths = []

    # Get acceptance criteria from verification_strategy
    verification = plan.get("verification_strategy", {})
    acceptance_criteria = verification.get("acceptance_criteria", [])

    for criterion in acceptance_criteria:
        if not isinstance(criterion, str):
            continue

        criterion_lower = criterion.lower()

        # Look for critical path indicators
        if "critical" not in criterion_lower:
            continue

        # Check if it mentions 100% coverage requirement
        requires_full_coverage = (
            "100%" in criterion
            or "full" in criterion_lower
            or "complete" in criterion_lower
        )

        if not requires_full_coverage:
            continue

        # Extract path examples from parentheses
        # Example: "Critical paths require 100% coverage (authentication, payment processing)"
        examples = _extract_path_examples(criterion)

        if examples:
            # Create specific critical paths for each example
            for example in examples:
                # Convert example to file pattern
                # "authentication" -> "*/auth/*" or "*/authentication/*"
                # "payment processing" -> "*/payment*/*"
                patterns = _convert_to_file_patterns(example)

                for pattern in patterns:
                    critical_paths.append(
                        CriticalPath(
                            name=example.title(),
                            pattern=pattern,
                            reason=criterion,
                            required_coverage=100.0,
                        )
                    )
        else:
            # No specific examples - create generic critical path
            critical_paths.append(
                CriticalPath(
                    name="Critical paths from spec",
                    pattern="**/critical/**",
                    reason=criterion,
                    required_coverage=100.0,
                )
            )

    return critical_paths


def _extract_path_examples(criterion: str) -> list[str]:
    """
    Extract path examples from criterion text.

    Looks for:
    - Parenthetical examples: "(authentication, payment processing)"
    - Colon-separated lists: "critical: authentication, payment"

    Args:
        criterion: Acceptance criterion text

    Returns:
        List of path example strings
    """
    examples = []

    # Extract from parentheses
    paren_pattern = r"\(([^)]+)\)"
    paren_matches = re.findall(paren_pattern, criterion)

    for match in paren_matches:
        # Split on commas and clean up
        parts = [p.strip() for p in match.split(",")]
        # Filter out non-path-like items (like "etc.", numbers, etc.)
        for part in parts:
            if (
                part
                and part.lower() not in ("etc", "etc.", "e.g.", "i.e.")
                and len(part) > 2
            ):
                examples.append(part)

    # Extract from colon-separated lists if no parenthetical examples
    if not examples:
        colon_pattern = r"critical[^:]*:\s*([^.]+)"
        colon_matches = re.findall(colon_pattern, criterion, re.IGNORECASE)

        for match in colon_matches:
            parts = [p.strip() for p in match.split(",")]
            for part in parts:
                if part and len(part) > 2:
                    examples.append(part)

    return examples


def _convert_to_file_patterns(example: str) -> list[str]:
    """
    Convert an example name to file patterns.

    Args:
        example: Example name (e.g., "authentication", "payment processing")

    Returns:
        List of file patterns that might match this example

    Examples:
        "authentication" -> ["**/auth/**", "**/authentication/**"]
        "payment processing" -> ["**/payment*/**", "**/payments/**"]
    """
    patterns = []
    example_lower = example.lower().strip()

    # Remove common words
    example_lower = example_lower.replace(" processing", "")
    example_lower = example_lower.replace(" handling", "")
    example_lower = example_lower.replace(" code", "")

    # Handle multi-word examples
    words = example_lower.split()

    for word in words:
        if len(word) < 3:  # Skip short words like "of", "to"
            continue

        # Add patterns for common abbreviations and variations
        if word == "authentication" or word == "auth":
            patterns.extend(["**/auth/**", "**/authentication/**"])
        elif word == "payment" or word == "payments":
            patterns.extend(["**/payment/**", "**/payments/**", "**/payment*/**"])
        elif word == "security":
            patterns.extend(["**/security/**", "**/secure/**"])
        elif word == "authorization":
            patterns.extend(["**/authorization/**", "**/authz/**"])
        else:
            # Generic pattern: exact match and plural
            patterns.append(f"**/{word}/**")
            if not word.endswith("s"):
                patterns.append(f"**/{word}s/**")
            # Also add wildcard pattern for variations
            patterns.append(f"**/{word}*/**")

    # If no patterns generated, use the full example
    if not patterns:
        patterns.append(f"**/{example_lower.replace(' ', '_')}/**")

    return patterns


def _load_from_pytest_config(project_dir: Path) -> CoverageConfig | None:
    """
    Load coverage config from pytest.ini or setup.cfg.

    Looks for:
    - addopts = --cov-fail-under=X
    - addopts = --cov-branch

    Args:
        project_dir: Path to project directory

    Returns:
        CoverageConfig if found, None otherwise
    """
    # Check pytest.ini
    pytest_ini = project_dir / "pytest.ini"
    if pytest_ini.exists():
        try:
            content = pytest_ini.read_text(encoding="utf-8")
            min_cov = _extract_fail_under_from_pytest(content)
            if min_cov is not None:
                return CoverageConfig(
                    minimum_coverage=min_cov,
                    config_source="pytest.ini",
                )
        except (OSError, UnicodeDecodeError):
            pass  # Gracefully ignore unreadable pytest.ini files

    # Check setup.cfg
    setup_cfg = project_dir / "setup.cfg"
    if setup_cfg.exists():
        try:
            content = setup_cfg.read_text(encoding="utf-8")
            min_cov = _extract_fail_under_from_pytest(content)
            if min_cov is not None:
                return CoverageConfig(
                    minimum_coverage=min_cov,
                    config_source="setup.cfg",
                )
        except (OSError, UnicodeDecodeError):
            pass  # Gracefully ignore unreadable setup.cfg files

    return None


def _extract_fail_under_from_pytest(content: str) -> float | None:
    """
    Extract --cov-fail-under value from pytest config.

    Args:
        content: Content of pytest config file

    Returns:
        Minimum coverage threshold or None
    """
    # Look for --cov-fail-under=80 or --cov-fail-under 80
    pattern = r"--cov-fail-under[=\s]+(\d+(?:\.\d+)?)"
    match = re.search(pattern, content)
    if match:
        return float(match.group(1))
    return None


def _load_from_coveragerc(project_dir: Path) -> CoverageConfig | None:
    """
    Load coverage config from .coveragerc file.

    Looks for:
    [report]
    fail_under = X
    exclude_lines = ...

    Args:
        project_dir: Path to project directory

    Returns:
        CoverageConfig if found, None otherwise
    """
    coveragerc = project_dir / ".coveragerc"
    if not coveragerc.exists():
        return None

    try:
        content = coveragerc.read_text(encoding="utf-8")

        # Extract fail_under from [report] section
        min_cov = None
        in_report_section = False

        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("[report]"):
                in_report_section = True
                continue
            elif line.startswith("["):
                in_report_section = False
                continue

            if in_report_section and line.startswith("fail_under"):
                # Parse: fail_under = 80
                parts = line.split("=")
                if len(parts) == 2:
                    try:
                        min_cov = float(parts[1].strip())
                    except ValueError:
                        pass  # Ignore non-numeric fail_under values

        if min_cov is not None:
            return CoverageConfig(
                minimum_coverage=min_cov,
                config_source=".coveragerc",
            )

    except (OSError, UnicodeDecodeError):
        pass  # Gracefully ignore unreadable .coveragerc files

    return None


def _load_from_pyproject(project_dir: Path) -> CoverageConfig | None:
    """
    Load coverage config from pyproject.toml.

    Looks for:
    [tool.coverage.report]
    fail_under = X

    Args:
        project_dir: Path to project directory

    Returns:
        CoverageConfig if found, None otherwise
    """
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return None

    try:
        content = pyproject.read_text(encoding="utf-8")

        # Simple regex-based parsing (avoid dependency on toml library)
        # Look for fail_under in [tool.coverage.report] section
        pattern = r"\[tool\.coverage\.report\].*?fail_under\s*=\s*(\d+(?:\.\d+)?)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            min_cov = float(match.group(1))
            return CoverageConfig(
                minimum_coverage=min_cov,
                config_source="pyproject.toml",
            )

    except (OSError, UnicodeDecodeError):
        pass  # Gracefully ignore unreadable pyproject.toml files

    return None


# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================


def validate_coverage_config(config: CoverageConfig) -> tuple[bool, list[str]]:
    """
    Validate coverage configuration for correctness.

    Checks:
    - minimum_coverage is between 0 and 100
    - critical path patterns are valid
    - no conflicting settings

    Args:
        config: Coverage configuration to validate

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        valid, errors = validate_coverage_config(config)
        if not valid:
            for error in errors:
                print(f"Config error: {error}")
    """
    errors = []

    # Validate minimum coverage
    if config.minimum_coverage < 0 or config.minimum_coverage > 100:
        errors.append(
            f"minimum_coverage must be between 0 and 100, got {config.minimum_coverage}"
        )

    # Validate line coverage if set
    if config.minimum_line_coverage is not None:
        if config.minimum_line_coverage < 0 or config.minimum_line_coverage > 100:
            errors.append(
                f"minimum_line_coverage must be between 0 and 100, got {config.minimum_line_coverage}"
            )

    # Validate branch coverage if set
    if config.minimum_branch_coverage is not None:
        if config.minimum_branch_coverage < 0 or config.minimum_branch_coverage > 100:
            errors.append(
                f"minimum_branch_coverage must be between 0 and 100, got {config.minimum_branch_coverage}"
            )

    # Validate critical paths
    for critical_path in config.critical_paths:
        if critical_path.required_coverage < 0 or critical_path.required_coverage > 100:
            errors.append(
                f"Critical path '{critical_path.name}' has invalid required_coverage: {critical_path.required_coverage}"
            )

    return len(errors) == 0, errors


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_critical_paths(
    spec_dir: str | Path,
) -> list[CriticalPath]:
    """
    Get list of critical paths from spec acceptance criteria.

    Args:
        spec_dir: Path to spec directory

    Returns:
        List of CriticalPath objects requiring high coverage

    Example:
        critical_paths = get_critical_paths(".auto-claude/specs/001-feature")
        for path in critical_paths:
            print(f"{path.name}: {path.pattern} - {path.reason}")
    """
    spec_dir_path = Path(spec_dir).resolve()

    plan_file = spec_dir_path / "implementation_plan.json"
    if not plan_file.exists():
        return []

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []

    return _extract_critical_paths_from_criteria(plan)


def get_minimum_coverage_for_file(
    file_path: str | Path,
    config: CoverageConfig,
) -> float:
    """
    Get the minimum coverage required for a specific file.

    Checks if the file matches any critical path patterns, otherwise
    returns the default minimum coverage.

    Args:
        file_path: Path to the file to check
        config: Coverage configuration

    Returns:
        Minimum coverage percentage required (0-100)

    Example:
        min_cov = get_minimum_coverage_for_file("auth/login.py", config)
        if min_cov == 100.0:
            print("This is a critical path requiring 100% coverage")
    """
    file_path = Path(file_path)

    # Check if file matches any critical path pattern
    for critical_path in config.critical_paths:
        if _matches_pattern(str(file_path), critical_path.pattern):
            return critical_path.required_coverage

    # Return default minimum coverage
    return config.minimum_coverage


def _matches_pattern(file_path: str, pattern: str) -> bool:
    """
    Check if a file path matches a pattern.

    Supports:
    - Exact matches: "auth/login.py"
    - Wildcards: "*/auth/*", "*.py"
    - Glob patterns: "**/auth/**/*.py"

    Args:
        file_path: File path to check
        pattern: Pattern to match against

    Returns:
        True if file matches pattern
    """
    # Normalize to POSIX-style paths for cross-platform matching
    normalized_path = Path(file_path).as_posix()

    # Convert pattern to regex
    # Replace ** with .* (match any characters including /)
    # Replace * with [^/]* (match any characters except /)
    regex_pattern = pattern.replace("**", "__DOUBLE_STAR__")
    regex_pattern = regex_pattern.replace("*", r"[^/]*")
    regex_pattern = regex_pattern.replace("__DOUBLE_STAR__", ".*")
    regex_pattern = f"^{regex_pattern}$"

    return bool(re.match(regex_pattern, normalized_path))


def matches_pattern(file_path: str, pattern: str) -> bool:
    """Public API for checking if a file path matches a glob-like pattern.

    See _matches_pattern for details.
    """
    return _matches_pattern(file_path, pattern)


def merge_coverage_configs(
    base_config: CoverageConfig,
    override_config: CoverageConfig,
) -> CoverageConfig:
    """
    Merge two coverage configurations, with override taking precedence.

    Args:
        base_config: Base configuration
        override_config: Override configuration

    Returns:
        Merged configuration

    Example:
        default = load_coverage_config(project_dir)
        custom = CoverageConfig(minimum_coverage=90.0)
        merged = merge_coverage_configs(default, custom)
    """
    return CoverageConfig(
        minimum_coverage=(
            override_config.minimum_coverage
            if override_config.minimum_coverage is not None
            else base_config.minimum_coverage
        ),
        minimum_line_coverage=(
            override_config.minimum_line_coverage
            if override_config.minimum_line_coverage is not None
            else base_config.minimum_line_coverage
        ),
        minimum_branch_coverage=(
            override_config.minimum_branch_coverage
            if override_config.minimum_branch_coverage is not None
            else base_config.minimum_branch_coverage
        ),
        critical_paths=(
            override_config.critical_paths
            if override_config.critical_paths is not None
            else base_config.critical_paths
        ),
        excluded_paths=(
            override_config.excluded_paths
            if override_config.excluded_paths is not None
            else base_config.excluded_paths
        ),
        enforce_on_modified_files=override_config.enforce_on_modified_files,
        fail_under_threshold=override_config.fail_under_threshold,
        config_source=f"{base_config.config_source} + {override_config.config_source}",
    )
