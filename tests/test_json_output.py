#!/usr/bin/env python3
"""
Tests for JSON Output Format
=============================

Tests the json_output.py module functionality including:
- BuildStatus enum values and types
- format_build_result() JSON structure and fields
- format_qa_result() JSON structure and fields
- format_artifact_list() JSON structure and fields
- ExitCode to BuildStatus conversion
- JSON parsing and validation
- Timestamp format validation
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# sys.path is set by conftest.py (apps/backend is already on the path)
# Keep a local fallback for running this file directly using an absolute path
_BACKEND_DIR = str(
    (Path(__file__).resolve().parent.parent / "apps" / "backend")
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
from cli.exit_codes import ExitCode
from cli.json_output import (
    BuildStatus,
    format_artifact_list,
    format_build_result,
    format_qa_result,
    parse_build_result,
    print_json_output,
)


class TestBuildStatusEnum:
    """Tests for BuildStatus enum."""

    def test_success_status_value(self):
        """SUCCESS status value is 'success'."""
        assert BuildStatus.SUCCESS.value == "success"

    def test_build_failed_status_value(self):
        """BUILD_FAILED status value is 'build_failed'."""
        assert BuildStatus.BUILD_FAILED.value == "build_failed"

    def test_qa_failed_status_value(self):
        """QA_FAILED status value is 'qa_failed'."""
        assert BuildStatus.QA_FAILED.value == "qa_failed"

    def test_system_error_status_value(self):
        """SYSTEM_ERROR status value is 'system_error'."""
        assert BuildStatus.SYSTEM_ERROR.value == "system_error"

    def test_is_string_enum(self):
        """BuildStatus is a string enum."""
        assert isinstance(BuildStatus.SUCCESS, str)
        assert isinstance(BuildStatus.BUILD_FAILED, str)

    def test_all_status_values_unique(self):
        """All status values are unique."""
        statuses = [
            BuildStatus.SUCCESS,
            BuildStatus.BUILD_FAILED,
            BuildStatus.QA_FAILED,
            BuildStatus.SYSTEM_ERROR,
        ]
        assert len(set(statuses)) == len(statuses)


class TestFormatBuildResultMinimal:
    """Tests for format_build_result() with minimal parameters."""

    def test_minimal_success_result(self):
        """Format build result with only required parameters."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["exitCode"] == 0
        assert data["specName"] == "001-feature"
        assert "timestamp" in data

    def test_minimal_build_failed_result(self):
        """Format build failed result with minimal parameters."""
        result = format_build_result(
            status=BuildStatus.BUILD_FAILED,
            spec_name="002-bugfix",
            exit_code=1,
        )

        data = json.loads(result)
        assert data["status"] == "build_failed"
        assert data["exitCode"] == 1
        assert data["specName"] == "002-bugfix"

    def test_minimal_qa_failed_result(self):
        """Format QA failed result with minimal parameters."""
        result = format_build_result(
            status=BuildStatus.QA_FAILED,
            spec_name="003-refactor",
            exit_code=2,
        )

        data = json.loads(result)
        assert data["status"] == "qa_failed"
        assert data["exitCode"] == 2

    def test_minimal_system_error_result(self):
        """Format system error result with minimal parameters."""
        result = format_build_result(
            status=BuildStatus.SYSTEM_ERROR,
            spec_name="004-hotfix",
            exit_code=3,
        )

        data = json.loads(result)
        assert data["status"] == "system_error"
        assert data["exitCode"] == 3


class TestFormatBuildResultWithOptions:
    """Tests for format_build_result() with optional parameters."""

    def test_with_duration(self):
        """Format build result with duration."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=123.456,
        )

        data = json.loads(result)
        assert "duration" in data
        assert data["duration"] == pytest.approx(123.46)  # Rounded to 2 decimal places

    def test_with_error_message(self):
        """Format build result with error message."""
        result = format_build_result(
            status=BuildStatus.BUILD_FAILED,
            spec_name="001-feature",
            exit_code=1,
            error_message="Coder agent failed to implement feature",
        )

        data = json.loads(result)
        assert "error" in data
        assert data["error"] == "Coder agent failed to implement feature"

    def test_with_changed_files(self):
        """Format build result with changed files."""
        files = ["src/main.py", "tests/test_main.py", "docs/api.md"]
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            changed_files=files,
        )

        data = json.loads(result)
        assert "changedFiles" in data
        assert data["changedFiles"] == files
        assert "filesChanged" in data
        assert data["filesChanged"] == 3

    def test_with_empty_changed_files(self):
        """Format build result with empty changed files list."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            changed_files=[],
        )

        data = json.loads(result)
        assert data["changedFiles"] == []
        assert data["filesChanged"] == 0

    def test_with_artifacts(self):
        """Format build result with artifacts."""
        artifacts = {
            "build-log": "/path/to/build-log.json",
            "test-report": "/path/to/test-report.json",
        }
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            artifacts=artifacts,
        )

        data = json.loads(result)
        assert "artifacts" in data
        assert data["artifacts"] == artifacts

    def test_with_metadata(self):
        """Format build result with metadata."""
        metadata = {"model": "claude-sonnet-4-5", "iterations": 3}
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            metadata=metadata,
        )

        data = json.loads(result)
        assert "metadata" in data
        assert data["metadata"] == metadata

    def test_with_all_options(self):
        """Format build result with all optional parameters."""
        files = ["src/auth.py", "tests/test_auth.py"]
        artifacts = {"qa-report": "/path/to/qa-report.md"}
        metadata = {"agent": "coder", "version": "2.0.0"}

        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-auth",
            exit_code=0,
            duration_seconds=300.789,
            error_message=None,
            changed_files=files,
            artifacts=artifacts,
            metadata=metadata,
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["exitCode"] == 0
        assert data["specName"] == "001-auth"
        assert data["duration"] == pytest.approx(300.79)
        assert data["changedFiles"] == files
        assert data["filesChanged"] == 2
        assert data["artifacts"] == artifacts
        assert data["metadata"] == metadata
        assert "timestamp" in data


class TestFormatBuildResultExitCodeConversion:
    """Tests for ExitCode to BuildStatus conversion."""

    def test_exit_code_success_conversion(self):
        """Convert ExitCode.SUCCESS to BuildStatus."""
        result = format_build_result(
            status=ExitCode.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        assert data["status"] == "success"

    def test_exit_code_build_failed_conversion(self):
        """Convert ExitCode.BUILD_FAILED to BuildStatus."""
        result = format_build_result(
            status=ExitCode.BUILD_FAILED,
            spec_name="001-feature",
            exit_code=1,
        )

        data = json.loads(result)
        assert data["status"] == "build_failed"

    def test_exit_code_qa_failed_conversion(self):
        """Convert ExitCode.QA_FAILED to BuildStatus."""
        result = format_build_result(
            status=ExitCode.QA_FAILED,
            spec_name="001-feature",
            exit_code=2,
        )

        data = json.loads(result)
        assert data["status"] == "qa_failed"

    def test_exit_code_system_error_conversion(self):
        """Convert ExitCode.SYSTEM_ERROR to BuildStatus."""
        result = format_build_result(
            status=ExitCode.SYSTEM_ERROR,
            spec_name="001-feature",
            exit_code=3,
        )

        data = json.loads(result)
        assert data["status"] == "system_error"


class TestFormatBuildResultExitCodeTypes:
    """Tests verifying format_build_result accepts ExitCode as exit_code parameter."""

    def test_accepts_exit_code_enum_as_exit_code(self):
        """format_build_result accepts ExitCode enum for exit_code parameter."""
        # The function signature is: exit_code: ExitCode | int
        # This test verifies ExitCode instances are accepted without error
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=ExitCode.SUCCESS,
        )
        data = json.loads(result)
        assert data["exitCode"] == 0

    def test_accepts_int_as_exit_code(self):
        """format_build_result accepts plain int for exit_code parameter."""
        result = format_build_result(
            status=BuildStatus.BUILD_FAILED,
            spec_name="001-feature",
            exit_code=1,
        )
        data = json.loads(result)
        assert data["exitCode"] == 1


class TestFormatBuildResultJsonStructure:
    """Tests for JSON output structure."""

    def test_returns_valid_json(self):
        """Returns valid JSON string."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        # Should not raise json.JSONDecodeError
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_json_is_pretty_printed(self):
        """JSON output is pretty-printed with indentation."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        # Check that output is formatted with newlines and indentation
        assert "\n" in result
        assert "  " in result  # 2-space indentation

    def test_has_required_fields(self):
        """JSON has all required fields."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        required_fields = ["status", "exitCode", "specName", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_timestamp_format(self):
        """Timestamp is in ISO 8601 format with Z suffix."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        timestamp = data["timestamp"]

        # Should end with Z (UTC)
        assert timestamp.endswith("Z")

        # Should be parseable as ISO 8601
        # Format: 2025-02-06T18:30:00Z
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class TestFormatQAResult:
    """Tests for format_qa_result() function."""

    def test_passed_qa_result(self):
        """Format QA result when validation passed."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=True,
            issues_found=5,
            issues_fixed=5,
            exit_code=0,
        )

        data = json.loads(result)
        assert data["status"] == "passed"
        assert data["exitCode"] == 0
        assert data["specName"] == "001-feature"
        assert data["qa"]["passed"] is True
        assert data["qa"]["issuesFound"] == 5
        assert data["qa"]["issuesFixed"] == 5
        assert data["qa"]["issuesRemaining"] == 0

    def test_failed_qa_result(self):
        """Format QA result when validation failed."""
        result = format_qa_result(
            spec_name="002-bugfix",
            passed=False,
            issues_found=3,
            issues_fixed=1,
            exit_code=2,
        )

        data = json.loads(result)
        assert data["status"] == "failed"
        assert data["exitCode"] == 2
        assert data["qa"]["passed"] is False
        assert data["qa"]["issuesFound"] == 3
        assert data["qa"]["issuesFixed"] == 1
        assert data["qa"]["issuesRemaining"] == 2

    def test_qa_result_with_report_path(self):
        """Format QA result with report path."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
            qa_report_path=".auto-claude/specs/001/qa_report.md",
        )

        data = json.loads(result)
        assert "reportPath" in data["qa"]
        assert data["qa"]["reportPath"] == ".auto-claude/specs/001/qa_report.md"

    def test_qa_result_with_error_message(self):
        """Format QA result with error message."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=False,
            issues_found=0,
            issues_fixed=0,
            exit_code=2,
            error_message="QA agent encountered unexpected error",
        )

        data = json.loads(result)
        assert "error" in data
        assert data["error"] == "QA agent encountered unexpected error"

    def test_qa_result_all_options(self):
        """Format QA result with all optional parameters."""
        result = format_qa_result(
            spec_name="001-auth",
            passed=True,
            issues_found=10,
            issues_fixed=10,
            exit_code=0,
            qa_report_path=".auto-claude/specs/001/qa_report.md",
        )

        data = json.loads(result)
        assert data["status"] == "passed"
        assert data["qa"]["passed"] is True
        assert data["qa"]["issuesFound"] == 10
        assert data["qa"]["issuesFixed"] == 10
        assert data["qa"]["issuesRemaining"] == 0
        assert data["qa"]["reportPath"] == ".auto-claude/specs/001/qa_report.md"
        assert "timestamp" in data

    def test_qa_result_json_structure(self):
        """QA result JSON has correct structure."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
        )

        data = json.loads(result)
        assert "status" in data
        assert "exitCode" in data
        assert "specName" in data
        assert "timestamp" in data
        assert "qa" in data
        assert "passed" in data["qa"]
        assert "issuesFound" in data["qa"]
        assert "issuesFixed" in data["qa"]
        assert "issuesRemaining" in data["qa"]


class TestFormatArtifactList:
    """Tests for format_artifact_list() function."""

    def test_format_artifact_list(self):
        """Format artifact list."""
        artifacts = {
            "build-log": ".auto-claude/specs/001/artifacts/build-log.json",
            "test-report": ".auto-claude/specs/001/artifacts/test-report.json",
            "qa-report": ".auto-claude/specs/001/artifacts/qa-report.md",
        }

        result = format_artifact_list(artifacts, "001-feature")

        data = json.loads(result)
        assert data["specName"] == "001-feature"
        assert data["artifacts"] == artifacts
        assert data["artifactCount"] == 3
        assert "timestamp" in data

    def test_format_empty_artifact_list(self):
        """Format empty artifact list."""
        result = format_artifact_list({}, "001-feature")

        data = json.loads(result)
        assert data["artifacts"] == {}
        assert data["artifactCount"] == 0

    def test_format_single_artifact(self):
        """Format single artifact."""
        artifacts = {"build-log": "/path/to/build-log.json"}

        result = format_artifact_list(artifacts, "001-feature")

        data = json.loads(result)
        assert data["artifactCount"] == 1
        assert "build-log" in data["artifacts"]

    def test_artifact_list_json_structure(self):
        """Artifact list JSON has correct structure."""
        result = format_artifact_list(
            {"artifact": "/path/to/artifact.txt"},
            "001-feature",
        )

        data = json.loads(result)
        assert "specName" in data
        assert "timestamp" in data
        assert "artifacts" in data
        assert "artifactCount" in data


class TestPrintJsonOutput:
    """Tests for print_json_output() function."""

    @patch("builtins.print")
    def test_print_json_output(self, mock_print):
        """print_json_output() prints the JSON string."""
        json_str = '{"test": "data"}'

        print_json_output(json_str)

        mock_print.assert_called_once_with(json_str)

    @patch("builtins.print")
    def test_print_complex_json(self, mock_print):
        """print_json_output() prints complex JSON."""
        json_str = json.dumps({"key": "value", "nested": {"data": [1, 2, 3]}}, indent=2)

        print_json_output(json_str)

        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert json.loads(args[0]) == json.loads(json_str)


class TestParseBuildResult:
    """Tests for parse_build_result() function."""

    def test_parse_valid_json(self):
        """Parse valid JSON build result."""
        json_str = '{"status": "success", "exitCode": 0, "specName": "001"}'

        result = parse_build_result(json_str)

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["exitCode"] == 0
        assert result["specName"] == "001"

    def test_parse_complex_json(self):
        """Parse complex JSON build result."""
        json_str = json.dumps(
            {
                "status": "success",
                "exitCode": 0,
                "specName": "001-feature",
                "duration": 120.5,
                "changedFiles": ["file1.py", "file2.py"],
                "artifacts": {"build-log": "/path/to/log"},
            }
        )

        result = parse_build_result(json_str)

        assert result["changedFiles"] == ["file1.py", "file2.py"]
        assert result["artifacts"]["build-log"] == "/path/to/log"

    def test_parse_invalid_json_raises_error(self):
        """Parsing invalid JSON raises JSONDecodeError."""
        invalid_json = "{invalid json"

        with pytest.raises(json.JSONDecodeError):
            parse_build_result(invalid_json)

    def test_parse_round_trip(self):
        """Parse JSON that was created by format_build_result."""
        original = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=100.0,
            changed_files=["src/test.py"],
        )

        parsed = parse_build_result(original)

        assert parsed["status"] == "success"
        assert parsed["specName"] == "001-feature"
        assert parsed["duration"] == pytest.approx(100.0)
        assert parsed["changedFiles"] == ["src/test.py"]


class TestBuildResultFieldTypes:
    """Tests for field type validation in build results."""

    def test_status_is_string(self):
        """Status field is a string."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        assert isinstance(data["status"], str)

    def test_exit_code_is_integer(self):
        """Exit code field is an integer."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        assert isinstance(data["exitCode"], int)

    def test_spec_name_is_string(self):
        """Spec name field is a string."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
        )

        data = json.loads(result)
        assert isinstance(data["specName"], str)

    def test_duration_is_float(self):
        """Duration field is a float (or int when whole number)."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=123.456,
        )

        data = json.loads(result)
        assert isinstance(data["duration"], float)

    def test_changed_files_is_list(self):
        """Changed files field is a list."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            changed_files=["file1.py", "file2.py"],
        )

        data = json.loads(result)
        assert isinstance(data["changedFiles"], list)

    def test_files_changed_is_integer(self):
        """Files changed count field is an integer."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            changed_files=["file1.py", "file2.py"],
        )

        data = json.loads(result)
        assert isinstance(data["filesChanged"], int)

    def test_artifacts_is_dict(self):
        """Artifacts field is a dictionary."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            artifacts={"log": "/path/to/log"},
        )

        data = json.loads(result)
        assert isinstance(data["artifacts"], dict)

    def test_metadata_is_dict(self):
        """Metadata field is a dictionary."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            metadata={"key": "value"},
        )

        data = json.loads(result)
        assert isinstance(data["metadata"], dict)


class TestBuildResultEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_duration(self):
        """Build result with zero duration."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=0.0,
        )

        data = json.loads(result)
        assert data["duration"] == pytest.approx(0.0)

    def test_very_long_spec_name(self):
        """Build result with very long spec name."""
        long_name = "001-" + "a" * 1000
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name=long_name,
            exit_code=0,
        )

        data = json.loads(result)
        assert data["specName"] == long_name

    def test_special_characters_in_error_message(self):
        """Build result with special characters in error message."""
        error_msg = "Error: 'test' with \"quotes\" and \n newlines"
        result = format_build_result(
            status=BuildStatus.BUILD_FAILED,
            spec_name="001-feature",
            exit_code=1,
            error_message=error_msg,
        )

        data = json.loads(result)
        assert data["error"] == error_msg

    def test_unicode_in_spec_name(self):
        """Build result with unicode characters in spec name."""
        spec_name = "001-功能测试"
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name=spec_name,
            exit_code=0,
        )

        data = json.loads(result)
        assert data["specName"] == spec_name

    def test_large_changed_files_list(self):
        """Build result with large number of changed files."""
        files = [f"file{i}.py" for i in range(1000)]
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            changed_files=files,
        )

        data = json.loads(result)
        assert data["filesChanged"] == 1000
        assert len(data["changedFiles"]) == 1000

    def test_duration_rounding(self):
        """Duration is rounded to 2 decimal places."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=123.456789,
        )

        data = json.loads(result)
        assert data["duration"] == pytest.approx(123.46)

    def test_negative_duration_not_rounded_to_zero(self):
        """Negative duration is preserved (though unlikely in practice)."""
        # This is an edge case that shouldn't happen in practice
        # but we test that the function doesn't crash
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=-10.5,
        )

        data = json.loads(result)
        assert data["duration"] == -10.5


class TestQAResultCalculations:
    """Tests for QA result calculations."""

    def test_issues_remaining_calculation_with_none_remaining(self):
        """Issues remaining is zero when all fixed."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=True,
            issues_found=5,
            issues_fixed=5,
            exit_code=0,
        )

        data = json.loads(result)
        assert data["qa"]["issuesRemaining"] == 0

    def test_issues_remaining_calculation_with_some_remaining(self):
        """Issues remaining is correct when some unfixed."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=False,
            issues_found=10,
            issues_fixed=7,
            exit_code=2,
        )

        data = json.loads(result)
        assert data["qa"]["issuesRemaining"] == 3

    def test_issues_remaining_with_zero_issues(self):
        """Issues remaining is zero when no issues found."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
        )

        data = json.loads(result)
        assert data["qa"]["issuesRemaining"] == 0


class TestJsonOutputIntegration:
    """Integration tests for JSON output functions."""

    def test_format_and_parse_round_trip(self):
        """Format and parse build result maintains data integrity."""
        original_data = {
            "status": BuildStatus.SUCCESS,
            "spec_name": "001-integration-test",
            "exit_code": 0,
            "duration_seconds": 250.75,
            "error_message": None,
            "changed_files": ["src/integration.py", "tests/test_integration.py"],
            "artifacts": {"log": "/path/to/log.json"},
            "metadata": {"test": "integration"},
        }

        json_str = format_build_result(**original_data)
        parsed_data = parse_build_result(json_str)

        assert parsed_data["status"] == "success"
        assert parsed_data["specName"] == "001-integration-test"
        assert parsed_data["exitCode"] == 0
        assert parsed_data["duration"] == pytest.approx(250.75)
        assert parsed_data["changedFiles"] == original_data["changed_files"]
        assert parsed_data["artifacts"] == original_data["artifacts"]
        assert parsed_data["metadata"] == original_data["metadata"]

    def test_qa_format_and_parse_round_trip(self):
        """Format and parse QA result maintains data integrity."""
        json_str = format_qa_result(
            spec_name="001-qa-test",
            passed=True,
            issues_found=8,
            issues_fixed=8,
            exit_code=0,
            qa_report_path="/path/to/qa.md",
        )

        parsed = json.loads(json_str)

        assert parsed["status"] == "passed"
        assert parsed["specName"] == "001-qa-test"
        assert parsed["qa"]["passed"] is True
        assert parsed["qa"]["issuesFound"] == 8
        assert parsed["qa"]["issuesFixed"] == 8
        assert parsed["qa"]["issuesRemaining"] == 0
        assert parsed["qa"]["reportPath"] == "/path/to/qa.md"

    def test_all_format_functions_produce_valid_json(self):
        """All format functions produce valid JSON strings."""
        # format_build_result
        build_json = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001",
            exit_code=0,
        )
        assert json.loads(build_json)

        # format_qa_result
        qa_json = format_qa_result(
            spec_name="001",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
        )
        assert json.loads(qa_json)

        # format_artifact_list
        artifact_json = format_artifact_list({}, "001")
        assert json.loads(artifact_json)


class TestBuildStatusValueMapping:
    """Tests for BuildStatus and ExitCode value mapping."""

    def test_all_exit_codes_have_build_status_mapping(self):
        """All ExitCode values have corresponding BuildStatus mapping."""
        mappings = {
            ExitCode.SUCCESS: BuildStatus.SUCCESS,
            ExitCode.BUILD_FAILED: BuildStatus.BUILD_FAILED,
            ExitCode.QA_FAILED: BuildStatus.QA_FAILED,
            ExitCode.SYSTEM_ERROR: BuildStatus.SYSTEM_ERROR,
            ExitCode.INTERRUPTED: BuildStatus.INTERRUPTED,
        }

        for exit_code, expected_status in mappings.items():
            result = format_build_result(
                status=exit_code,
                spec_name="001",
                exit_code=exit_code.value,
            )
            data = json.loads(result)
            assert data["status"] == expected_status.value

    def test_status_value_matches_exit_code(self):
        """Status value matches expected exit code."""
        test_cases = [
            (BuildStatus.SUCCESS, 0),
            (BuildStatus.BUILD_FAILED, 1),
            (BuildStatus.QA_FAILED, 2),
            (BuildStatus.SYSTEM_ERROR, 3),
        ]

        for status, expected_exit_code in test_cases:
            result = format_build_result(
                status=status,
                spec_name="001",
                exit_code=expected_exit_code,
            )
            data = json.loads(result)
            assert data["exitCode"] == expected_exit_code


class TestTimestampGeneration:
    """Tests for timestamp generation in JSON output."""

    def test_timestamp_is_present(self):
        """Timestamp field is present in all outputs."""
        # Build result
        build_json = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001",
            exit_code=0,
        )
        assert "timestamp" in json.loads(build_json)

        # QA result
        qa_json = format_qa_result(
            spec_name="001",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
        )
        assert "timestamp" in json.loads(qa_json)

        # Artifact list
        artifact_json = format_artifact_list({}, "001")
        assert "timestamp" in json.loads(artifact_json)

    def test_timestamp_format_consistency(self):
        """Timestamp format is consistent across all outputs."""
        build_json = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001",
            exit_code=0,
        )
        qa_json = format_qa_result(
            spec_name="001",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
        )
        artifact_json = format_artifact_list({}, "001")

        build_ts = json.loads(build_json)["timestamp"]
        qa_ts = json.loads(qa_json)["timestamp"]
        artifact_ts = json.loads(artifact_json)["timestamp"]

        # All should have Z suffix
        assert build_ts.endswith("Z")
        assert qa_ts.endswith("Z")
        assert artifact_ts.endswith("Z")

        # All should be parseable
        for ts in [build_ts, qa_ts, artifact_ts]:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))


class TestJsonOutputForCIPipelines:
    """Tests specific to CI/CD pipeline usage."""

    def test_build_result_has_machine_parseable_structure(self):
        """Build result can be parsed by automation tools."""
        result = format_build_result(
            status=BuildStatus.SUCCESS,
            spec_name="001-feature",
            exit_code=0,
            duration_seconds=120.5,
            changed_files=["src/main.py"],
            artifacts={"log": "/path/to/log"},
        )

        data = json.loads(result)

        # CI tools need to check status
        assert "status" in data

        # CI tools need to check exit code
        assert "exitCode" in data

        # CI tools need to identify the build
        assert "specName" in data

        # CI tools need to track timing
        assert "timestamp" in data
        assert "duration" in data

        # CI tools need to find artifacts
        assert "artifacts" in data

        # CI tools need to track changes
        assert "changedFiles" in data
        assert "filesChanged" in data

    def test_qa_result_has_machine_parseable_structure(self):
        """QA result can be parsed by automation tools."""
        result = format_qa_result(
            spec_name="001-feature",
            passed=True,
            issues_found=0,
            issues_fixed=0,
            exit_code=0,
        )

        data = json.loads(result)

        # CI tools need to check status
        assert "status" in data

        # CI tools need to check exit code
        assert "exitCode" in data

        # CI tools need QA metrics
        assert "qa" in data
        assert "passed" in data["qa"]
        assert "issuesFound" in data["qa"]
        assert "issuesFixed" in data["qa"]
        assert "issuesRemaining" in data["qa"]

    def test_error_messages_available_in_ci(self):
        """Error messages are available for CI reporting."""
        result = format_build_result(
            status=BuildStatus.BUILD_FAILED,
            spec_name="001-feature",
            exit_code=1,
            error_message="Build failed: authentication not implemented",
        )

        data = json.loads(result)
        assert "error" in data
        assert "authentication" in data["error"]

    def test_exit_codes_match_ci_conventions(self):
        """Exit codes follow Unix conventions for CI."""
        test_cases = [
            (BuildStatus.SUCCESS, 0),  # Success = 0
            (BuildStatus.BUILD_FAILED, 1),  # Error = non-zero
            (BuildStatus.QA_FAILED, 2),  # Different error = different code
            (BuildStatus.SYSTEM_ERROR, 3),  # System error = different code
        ]

        for status, exit_code in test_cases:
            result = format_build_result(
                status=status,
                spec_name="001",
                exit_code=exit_code,
            )
            data = json.loads(result)
            assert data["exitCode"] == exit_code

            # Non-zero for errors, zero for success
            if status == BuildStatus.SUCCESS:
                assert data["exitCode"] == 0
            else:
                assert data["exitCode"] != 0
