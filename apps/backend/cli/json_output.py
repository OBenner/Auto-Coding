"""
JSON Output Formatter
=====================

Provides machine-readable JSON output for CI/CD pipelines and automation scripts.
Formats build results, QA reports, and other build data as structured JSON.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from cli.exit_codes import ExitCode


class BuildStatus(str, Enum):
    """Build status values for JSON output."""

    SUCCESS = "success"
    BUILD_FAILED = "build_failed"
    QA_FAILED = "qa_failed"
    SYSTEM_ERROR = "system_error"
    INTERRUPTED = "interrupted"


def format_build_result(
    status: BuildStatus | ExitCode,
    spec_name: str,
    exit_code: ExitCode | int,
    duration_seconds: float | None = None,
    error_message: str | None = None,
    changed_files: list[str] | None = None,
    artifacts: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """
    Format build result as JSON for CI/CD pipelines.

    This function creates a structured JSON output that can be parsed by
    automation tools and CI/CD systems to determine build status and
    extract relevant build information.

    Args:
        status: Build status (BuildStatus enum or ExitCode enum)
        spec_name: Name of the spec that was built
        exit_code: Exit code value (ExitCode enum or int; 0=success, 1=build_failed, 2=qa_failed, 3=error)
        duration_seconds: Build duration in seconds (optional)
        error_message: Error message if build failed (optional)
        changed_files: List of files changed by the build (optional)
        artifacts: Dictionary of artifact names to file paths (optional)
        metadata: Additional metadata to include in output (optional)

    Returns:
        JSON string formatted for machine parsing

    Example:
        >>> result = format_build_result(
        ...     status=BuildStatus.SUCCESS,
        ...     spec_name="001-feature",
        ...     exit_code=0,
        ...     duration_seconds=120.5,
        ...     changed_files=["src/main.py", "tests/test_main.py"]
        ... )
        >>> print(result)
        {
            "status": "success",
            "exitCode": 0,
            "specName": "001-feature",
            "timestamp": "2025-02-06T18:30:00Z",
            "duration": 120.5,
            "changedFiles": ["src/main.py", "tests/test_main.py"],
            "artifacts": {}
        }
    """
    # Convert ExitCode to BuildStatus if needed
    if isinstance(status, ExitCode):
        status_map = {
            ExitCode.SUCCESS: BuildStatus.SUCCESS,
            ExitCode.BUILD_FAILED: BuildStatus.BUILD_FAILED,
            ExitCode.QA_FAILED: BuildStatus.QA_FAILED,
            ExitCode.SYSTEM_ERROR: BuildStatus.SYSTEM_ERROR,
            ExitCode.INTERRUPTED: BuildStatus.INTERRUPTED,
        }
        status = status_map.get(status, BuildStatus.SYSTEM_ERROR)

    # Build result dictionary
    result: dict[str, Any] = {
        "status": status.value,
        "exitCode": exit_code,
        "specName": spec_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Add optional fields
    if duration_seconds is not None:
        result["duration"] = round(duration_seconds, 2)

    if error_message:
        result["error"] = error_message

    if changed_files is not None:
        result["changedFiles"] = changed_files
        result["filesChanged"] = len(changed_files)

    if artifacts is not None:
        result["artifacts"] = artifacts

    if metadata is not None:
        result["metadata"] = metadata

    # Return formatted JSON
    return json.dumps(result, indent=2)


def format_qa_result(
    spec_name: str,
    passed: bool,
    issues_found: int,
    issues_fixed: int,
    exit_code: int,
    qa_report_path: str | None = None,
    error_message: str | None = None,
) -> str:
    """
    Format QA validation result as JSON.

    Args:
        spec_name: Name of the spec
        passed: Whether QA validation passed
        issues_found: Number of issues found during QA
        issues_fixed: Number of issues fixed
        exit_code: Exit code value
        qa_report_path: Path to QA report file (optional)
        error_message: Error message if QA failed (optional)

    Returns:
        JSON string with QA results

    Example:
        >>> result = format_qa_result(
        ...     spec_name="001-feature",
        ...     passed=True,
        ...     issues_found=3,
        ...     issues_fixed=3,
        ...     exit_code=0
        ... )
    """
    result: dict[str, Any] = {
        "status": "passed" if passed else "failed",
        "exitCode": exit_code,
        "specName": spec_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "qa": {
            "passed": passed,
            "issuesFound": issues_found,
            "issuesFixed": issues_fixed,
            "issuesRemaining": max(0, issues_found - issues_fixed),
        },
    }

    if qa_report_path:
        result["qa"]["reportPath"] = qa_report_path

    if error_message:
        result["error"] = error_message

    return json.dumps(result, indent=2)


def format_artifact_list(
    artifacts: dict[str, str],
    spec_name: str,
) -> str:
    """
    Format artifact list as JSON.

    Args:
        artifacts: Dictionary mapping artifact names to file paths
        spec_name: Name of the spec

    Returns:
        JSON string with artifact information

    Example:
        >>> artifacts = {
        ...     "build-log": "/path/to/build-log.json",
        ...     "test-report": "/path/to/test-report.json"
        ... }
        >>> result = format_artifact_list(artifacts, "001-feature")
    """
    result = {
        "specName": spec_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "artifacts": artifacts,
        "artifactCount": len(artifacts),
    }

    return json.dumps(result, indent=2)


def print_json_output(data: str) -> None:
    """
    Print JSON output to stdout.

    This is a helper function for consistent JSON output across the codebase.
    In CI/CD mode, all JSON should be printed through this function to ensure
    consistent formatting and to make it easier to capture JSON output.

    Args:
        data: JSON string to print

    Example:
        >>> result = format_build_result(...)
        >>> print_json_output(result)
    """
    print(data)


def parse_build_result(json_str: str) -> dict[str, Any]:
    """
    Parse JSON build result string back into dictionary.

    This is useful for testing or for tools that need to process JSON output.

    Args:
        json_str: JSON string from format_build_result()

    Returns:
        Dictionary with build result data

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    return json.loads(json_str)
