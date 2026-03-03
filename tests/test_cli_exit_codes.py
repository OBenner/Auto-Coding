#!/usr/bin/env python3
"""
Tests for CLI Exit Codes
=========================

Tests the exit_codes.py module functionality including:
- ExitCode enum values and types
- Unix conventions for exit codes
- Exit code usage in CI/CD pipelines
- Integration with build_commands.py
"""

import sys

import pytest

# sys.path is set by conftest.py (apps/backend is already on the path)
# Keep a local fallback for running this file directly
if not any("apps/backend" in p or "apps\\backend" in p for p in sys.path):
    sys.path.insert(0, "apps/backend")
from cli.exit_codes import ExitCode


class TestExitCodeValues:
    """Tests for ExitCode enum values."""

    def test_success_exit_code(self):
        """SUCCESS exit code is 0."""
        assert ExitCode.SUCCESS == 0

    def test_build_failed_exit_code(self):
        """BUILD_FAILED exit code is 1."""
        assert ExitCode.BUILD_FAILED == 1

    def test_qa_failed_exit_code(self):
        """QA_FAILED exit code is 2."""
        assert ExitCode.QA_FAILED == 2

    def test_system_error_exit_code(self):
        """SYSTEM_ERROR exit code is 3."""
        assert ExitCode.SYSTEM_ERROR == 3


class TestExitCodeType:
    """Tests for ExitCode enum type."""

    def test_is_int_enum(self):
        """ExitCode is an IntEnum."""
        from enum import IntEnum

        assert issubclass(ExitCode, IntEnum)

    def test_members_are_integers(self):
        """All exit codes are integers."""
        assert isinstance(ExitCode.SUCCESS, int)
        assert isinstance(ExitCode.BUILD_FAILED, int)
        assert isinstance(ExitCode.QA_FAILED, int)
        assert isinstance(ExitCode.SYSTEM_ERROR, int)

    def test_enum_names(self):
        """Exit codes have correct names."""
        assert ExitCode.SUCCESS.name == "SUCCESS"
        assert ExitCode.BUILD_FAILED.name == "BUILD_FAILED"
        assert ExitCode.QA_FAILED.name == "QA_FAILED"
        assert ExitCode.SYSTEM_ERROR.name == "SYSTEM_ERROR"


class TestUnixConventions:
    """Tests for Unix exit code conventions."""

    def test_success_is_zero(self):
        """Success exit code follows Unix convention (0)."""
        assert ExitCode.SUCCESS == 0

    def test_failures_are_non_zero(self):
        """All failure exit codes are non-zero."""
        assert ExitCode.BUILD_FAILED != 0
        assert ExitCode.QA_FAILED != 0
        assert ExitCode.SYSTEM_ERROR != 0
        assert ExitCode.INTERRUPTED != 0

    def test_exit_codes_are_positive(self):
        """All exit codes are positive integers."""
        assert ExitCode.SUCCESS >= 0
        assert ExitCode.BUILD_FAILED > 0
        assert ExitCode.QA_FAILED > 0
        assert ExitCode.SYSTEM_ERROR > 0
        assert ExitCode.INTERRUPTED > 0

    def test_exit_codes_are_small(self):
        """Exit codes are in the standard range (0-255)."""
        for code in ExitCode:
            assert 0 <= code.value <= 255


class TestExitCodeUniqueness:
    """Tests for exit code uniqueness."""

    def test_all_codes_are_unique(self):
        """Each exit code has a unique value."""
        codes = [
            ExitCode.SUCCESS,
            ExitCode.BUILD_FAILED,
            ExitCode.QA_FAILED,
            ExitCode.SYSTEM_ERROR,
            ExitCode.INTERRUPTED,
        ]
        assert len(set(codes)) == len(codes)

    def test_no_duplicate_values(self):
        """No two exit codes share the same value."""
        values = [code.value for code in ExitCode]
        assert len(values) == len(set(values))


class TestExitCodeComparison:
    """Tests for exit code comparison."""

    def test_success_vs_failure(self):
        """Can distinguish success from failure codes."""
        assert ExitCode.SUCCESS != ExitCode.BUILD_FAILED
        assert ExitCode.SUCCESS != ExitCode.QA_FAILED
        assert ExitCode.SUCCESS != ExitCode.SYSTEM_ERROR

    def test_failure_codes_are_different(self):
        """Each failure code is distinct."""
        assert ExitCode.BUILD_FAILED != ExitCode.QA_FAILED
        assert ExitCode.BUILD_FAILED != ExitCode.SYSTEM_ERROR
        assert ExitCode.QA_FAILED != ExitCode.SYSTEM_ERROR

    def test_can_use_in_if_statements(self):
        """Exit codes work in conditional statements."""
        # SUCCESS (0) is falsy in a boolean context — check it explicitly
        assert ExitCode.SUCCESS == 0, "SUCCESS must be 0 (falsy)"
        assert not ExitCode.SUCCESS, "SUCCESS (0) should be falsy"

        # Non-zero codes are truthy
        assert ExitCode.BUILD_FAILED, "BUILD_FAILED (1) is truthy"
        assert ExitCode.QA_FAILED, "QA_FAILED (2) is truthy"
        assert ExitCode.SYSTEM_ERROR, "SYSTEM_ERROR (3) is truthy"


class TestExitCodeInBuildCommands:
    """Tests for exit code integration with build_commands.py."""

    def test_exit_codes_importable_in_build_commands(self):
        """ExitCode can be imported in build_commands."""
        # This test verifies the import works
        from cli.exit_codes import ExitCode as ExitCodeAlias

        assert ExitCodeAlias is ExitCode

    def test_exit_code_values_match_spec(self):
        """Exit code values match the CI/CD spec requirements."""
        # From spec.md: Exit codes: 0 (success), 1 (build failed), 2 (QA failed), 3 (system error)
        assert ExitCode.SUCCESS == 0
        assert ExitCode.BUILD_FAILED == 1
        assert ExitCode.QA_FAILED == 2
        assert ExitCode.SYSTEM_ERROR == 3


class TestExitCodeSemanticMeaning:
    """Tests for semantic meaning of exit codes."""

    def test_success_means_build_passed_qa(self):
        """SUCCESS code indicates build completed and passed QA."""
        # From docstring: "Build completed and passed QA"
        assert ExitCode.SUCCESS == 0
        assert ExitCode.SUCCESS.name == "SUCCESS"

    def test_build_failed_means_implementation_error(self):
        """BUILD_FAILED code indicates coder agent failed."""
        # From docstring: "Coder agent failed to implement feature"
        assert ExitCode.BUILD_FAILED == 1
        assert ExitCode.BUILD_FAILED.name == "BUILD_FAILED"

    def test_qa_failed_means_validation_rejected(self):
        """QA_FAILED code indicates build passed but QA rejected."""
        # From docstring: "Build completed but QA validation failed"
        assert ExitCode.QA_FAILED == 2
        assert ExitCode.QA_FAILED.name == "QA_FAILED"

    def test_system_error_means_unexpected_error(self):
        """SYSTEM_ERROR code indicates unexpected error."""
        # From docstring: "Unexpected system error or exception"
        assert ExitCode.SYSTEM_ERROR == 3
        assert ExitCode.SYSTEM_ERROR.name == "SYSTEM_ERROR"


class TestExitCodeInCIPipeline:
    """Tests for exit code usage in CI/CD pipelines."""

    def test_exit_codes_work_with_sys_exit(self):
        """Exit codes can be used with sys.exit()."""
        # This test verifies the pattern from docstring works
        # We don't actually call sys.exit() in tests
        code = ExitCode.SUCCESS
        assert isinstance(code, int)
        assert code == 0

    def test_ci_can_parse_exit_codes(self):
        """CI/CD systems can parse exit codes as integers."""
        # Simulate CI checking exit code
        build_result = ExitCode.BUILD_FAILED
        assert build_result == 1

        qa_result = ExitCode.QA_FAILED
        assert qa_result == 2

        error_result = ExitCode.SYSTEM_ERROR
        assert error_result == 3

    def test_shell_script_compatibility(self):
        """Exit codes are compatible with shell script checking."""
        # Simulate shell: if [ $? -eq 0 ]; then
        exit_code = ExitCode.SUCCESS
        assert exit_code == 0

        # Simulate shell: if [ $? -ne 0 ]; then
        error_codes = [
            ExitCode.BUILD_FAILED,
            ExitCode.QA_FAILED,
            ExitCode.SYSTEM_ERROR,
            ExitCode.INTERRUPTED,
        ]
        for code in error_codes:
            assert code != 0


class TestExitCodeDocumentation:
    """Tests for exit code documentation."""

    def test_enum_has_docstring(self):
        """ExitCode enum has documentation."""
        assert ExitCode.__doc__ is not None
        assert "Standard exit codes" in ExitCode.__doc__

    def test_docstring_mentions_ci_cd(self):
        """Documentation mentions CI/CD context."""
        assert "CI/CD" in ExitCode.__doc__ or "build results" in ExitCode.__doc__

    def test_docstring_shows_usage(self):
        """Documentation shows usage examples."""
        assert "sys.exit" in ExitCode.__doc__


class TestExitCodeIteration:
    """Tests for iterating over exit codes."""

    def test_can_iterate_all_codes(self):
        """Can iterate over all exit codes."""
        codes = list(ExitCode)
        assert len(codes) == 5
        assert ExitCode.SUCCESS in codes
        assert ExitCode.BUILD_FAILED in codes
        assert ExitCode.QA_FAILED in codes
        assert ExitCode.SYSTEM_ERROR in codes
        assert ExitCode.INTERRUPTED in codes

    def test_iteration_preserves_order(self):
        """Iteration order is consistent."""
        codes1 = list(ExitCode)
        codes2 = list(ExitCode)
        assert codes1 == codes2


class TestExitCodeStringRepresentation:
    """Tests for exit code string representation."""

    def test_repr_format(self):
        """Exit code repr is informative."""
        repr_str = repr(ExitCode.SUCCESS)
        assert "SUCCESS" in repr_str
        assert "0" in repr_str

    def test_str_format(self):
        """Exit code str is informative."""
        str_str = str(ExitCode.BUILD_FAILED)
        assert "BUILD_FAILED" in str_str or "1" in str_str

    def test_name_returns_enum_name(self):
        """Exit code .name returns the enum member name."""
        assert ExitCode.SUCCESS.name == "SUCCESS"
        assert ExitCode.BUILD_FAILED.name == "BUILD_FAILED"
        assert ExitCode.QA_FAILED.name == "QA_FAILED"
        assert ExitCode.SYSTEM_ERROR.name == "SYSTEM_ERROR"

    def test_value_returns_integer(self):
        """Exit code .value returns the integer value."""
        assert ExitCode.SUCCESS.value == 0
        assert ExitCode.BUILD_FAILED.value == 1
        assert ExitCode.QA_FAILED.value == 2
        assert ExitCode.SYSTEM_ERROR.value == 3


class TestExitCodeComparisonOperators:
    """Tests for exit code comparison operators."""

    def test_less_than_comparison(self):
        """Exit codes can be compared with <."""
        assert ExitCode.SUCCESS < ExitCode.BUILD_FAILED
        assert ExitCode.SUCCESS < ExitCode.QA_FAILED
        assert ExitCode.BUILD_FAILED < ExitCode.QA_FAILED
        assert ExitCode.QA_FAILED < ExitCode.SYSTEM_ERROR

    def test_greater_than_comparison(self):
        """Exit codes can be compared with >."""
        assert ExitCode.SYSTEM_ERROR > ExitCode.QA_FAILED
        assert ExitCode.QA_FAILED > ExitCode.BUILD_FAILED
        assert ExitCode.BUILD_FAILED > ExitCode.SUCCESS

    def test_equality_comparison(self):
        """Exit codes can be compared with ==."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.BUILD_FAILED == 1
        assert ExitCode.QA_FAILED == 2
        assert ExitCode.SYSTEM_ERROR == 3


class TestExitCodeHashable:
    """Tests for exit code hashability."""

    def test_can_use_as_dict_key(self):
        """Exit codes can be used as dictionary keys."""
        code_map = {
            ExitCode.SUCCESS: "Build passed",
            ExitCode.BUILD_FAILED: "Build failed",
            ExitCode.QA_FAILED: "QA rejected",
            ExitCode.SYSTEM_ERROR: "System error",
        }
        assert code_map[ExitCode.SUCCESS] == "Build passed"
        assert code_map[ExitCode.BUILD_FAILED] == "Build failed"

    def test_can_use_in_set(self):
        """Exit codes can be used in sets."""
        code_set = {
            ExitCode.SUCCESS,
            ExitCode.BUILD_FAILED,
            ExitCode.QA_FAILED,
            ExitCode.SYSTEM_ERROR,
        }
        assert len(code_set) == 4
        assert ExitCode.SUCCESS in code_set


class TestExitCodeImmutability:
    """Tests for exit code immutability."""

    def test_cannot_modify_value(self):
        """Exit code values cannot be modified."""
        # IntEnum values are immutable — attempting to set raises AttributeError
        with pytest.raises(AttributeError):
            ExitCode.SUCCESS.value = 99

    def test_enum_members_are_readonly(self):
        """Enum members work as readonly constants."""
        # Enum members can be accessed but their values are fixed
        initial_value = ExitCode.SUCCESS.value
        assert initial_value == 0
        # The value remains constant throughout execution
        assert ExitCode.SUCCESS.value == initial_value


class TestExitCodeBoundaryValues:
    """Tests for exit code boundary values."""

    def test_minimum_value(self):
        """Minimum exit code is 0."""
        min_code = min(ExitCode)
        assert min_code.value == 0
        assert min_code == ExitCode.SUCCESS

    def test_maximum_value(self):
        """Maximum exit code is within valid range."""
        max_code = max(ExitCode)
        assert max_code.value <= 255
        # INTERRUPTED (130) is currently the largest code; update if new codes are added
        assert max_code == ExitCode.INTERRUPTED

    def test_all_values_in_standard_range(self):
        """All exit codes are in Unix-standard range (0-255)."""
        for code in ExitCode:
            assert 0 <= code.value <= 255, (
                f"{code.name} = {code.value} is outside valid range"
            )


class TestExitCodeComprehensiveness:
    """Tests for exit code coverage of scenarios."""

    def test_covers_success_scenario(self):
        """Has code for successful build scenario."""
        assert ExitCode.SUCCESS == 0

    def test_covers_build_failure_scenario(self):
        """Has code for build failure scenario."""
        assert ExitCode.BUILD_FAILED == 1

    def test_covers_qa_failure_scenario(self):
        """Has code for QA failure scenario."""
        assert ExitCode.QA_FAILED == 2

    def test_covers_system_error_scenario(self):
        """Has code for system error scenario."""
        assert ExitCode.SYSTEM_ERROR == 3

    def test_covers_interrupted_scenario(self):
        """Has code for build interrupted/paused by user scenario."""
        assert ExitCode.INTERRUPTED == 130

    def test_all_expected_scenarios_covered(self):
        """All major build scenarios have corresponding exit codes."""
        expected_codes = {
            "SUCCESS": 0,
            "BUILD_FAILED": 1,
            "QA_FAILED": 2,
            "SYSTEM_ERROR": 3,
            "INTERRUPTED": 130,
        }
        for name, value in expected_codes.items():
            assert hasattr(ExitCode, name)
            assert ExitCode[name].value == value
