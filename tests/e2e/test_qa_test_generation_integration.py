"""
Integration Test for QA Test Generation Flow
=============================================

Verifies that the test generation components integrate correctly:
1. Framework detection (pytest vs vitest)
2. Test validation routing
3. Coverage report collection
"""

import tempfile
from pathlib import Path

import pytest


def test_framework_detection_pytest():
    """Test that Python code triggers pytest framework selection."""
    from apps.backend.agents.test_generator import detect_test_framework

    py_analysis = {
        "functions": [{"name": "validate_email", "params": ["email"]}],
        "classes": [{"name": "UserValidator"}],
        "analyzed_files": ["utils.py", "auth.py"],
    }
    assert detect_test_framework(py_analysis) == "pytest"


def test_framework_detection_vitest():
    """Test that React components trigger vitest framework selection."""
    from apps.backend.agents.test_generator import detect_test_framework

    ts_analysis = {
        "components": [{"name": "LoginForm", "props": []}],
        "analyzed_files": ["LoginForm.tsx"],
    }
    assert detect_test_framework(ts_analysis) == "vitest"


def test_framework_detection_hooks():
    """Test that hooks trigger vitest framework selection."""
    from apps.backend.agents.test_generator import detect_test_framework

    hooks_analysis = {
        "hooks": [{"name": "useAuth"}],
        "analyzed_files": ["useAuth.ts"],
    }
    assert detect_test_framework(hooks_analysis) == "vitest"


def test_framework_detection_default_to_pytest():
    """Test that ambiguous code defaults to pytest."""
    from apps.backend.agents.test_generator import detect_test_framework

    ambiguous_analysis = {
        "functions": [],
        "analyzed_files": [],
    }
    assert detect_test_framework(ambiguous_analysis) == "pytest"


def test_coverage_report_collection():
    """Test that coverage reporter can collect reports from multiple frameworks."""
    from apps.backend.analysis.coverage_reporter import (
        CoverageReport,
        FileCoverage,
        format_coverage_summary,
    )

    # Create a mock coverage report
    report = CoverageReport(
        overall_coverage=85.5,
        lines_total=1000,
        lines_covered=855,
        lines_missed=145,
        framework="pytest",
        files=[
            FileCoverage(
                file_path="apps/backend/core/utils.py",
                coverage_percentage=90.0,
                lines_total=100,
                lines_covered=90,
                lines_missed=10,
            ),
            FileCoverage(
                file_path="apps/backend/services/auth.py",
                coverage_percentage=80.0,
                lines_total=50,
                lines_covered=40,
                lines_missed=10,
            ),
        ],
        uncovered_files=["apps/backend/legacy/old.py"],
    )

    # Test formatting
    summary = format_coverage_summary(report)
    assert "85.50%" in summary or "85.5%" in summary
    assert "pytest" in summary
    # Individual files not shown in summary by default
    assert "1000" in summary  # Total lines
    assert "855" in summary  # Covered lines


def test_phase_config_usage():
    """Test that test generators use correct phase config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)

        # Create minimal phase config file
        phase_config = spec_dir / "phase_config.json"
        import json

        config = {
            "phase_models": {"qa": "claude-sonnet-4"},
            "phase_thinking": {"qa": 10000},
        }
        with open(phase_config, "w") as f:
            json.dump(config, f)

        from phase_config import get_phase_model, get_phase_thinking_budget

        # Test that phase config can be loaded (uses defaults if file doesn't exist)
        model = get_phase_model(spec_dir, "qa", cli_model="claude-sonnet-4")
        assert model == "claude-sonnet-4"

        budget = get_phase_thinking_budget(spec_dir, "qa")
        assert isinstance(budget, int)


def test_test_validation_pytest():
    """Test pytest validation works for valid Python tests."""
    from unittest.mock import Mock, patch

    from apps.backend.agents.test_generator import validate_generated_tests

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        test_dir = project_dir / "tests"
        test_dir.mkdir()

        # Create a valid Python test
        test_file = test_dir / "test_example.py"
        test_file.write_text("def test_example():\n    assert True\n")

        # Mock subprocess to simulate pytest success
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Test validation
            result = validate_generated_tests(
                [Path("tests/test_example.py")], project_dir, framework="pytest"
            )
            assert result is True


def test_test_validation_vitest():
    """Test vitest validation routing."""
    from unittest.mock import patch

    from apps.backend.agents.test_generator import validate_generated_tests

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Mock vitest validation
        with patch(
            "apps.backend.agents.vitest_generator.validate_vitest_tests",
            return_value=True,
        ):
            result = validate_generated_tests(
                [Path("Button.test.tsx")], project_dir, framework="vitest"
            )
            assert result is True


def test_qa_loop_has_test_generation_integration():
    """Verify QA loop has test generation integration points."""
    from apps.backend.qa.loop import run_qa_validation_loop

    # Check that the function exists and has the right signature
    import inspect

    sig = inspect.signature(run_qa_validation_loop)
    params = list(sig.parameters.keys())

    assert "project_dir" in params
    assert "spec_dir" in params
    assert "model" in params
    assert "verbose" in params


def test_qa_loop_imports_test_generators():
    """Verify QA loop imports all test generation components."""
    import apps.backend.qa.loop as loop_module

    # Check that test generation modules are imported
    assert hasattr(loop_module, "run_test_generator_session")
    assert hasattr(loop_module, "generate_e2e_tests")
    assert hasattr(loop_module, "collect_coverage")
    assert hasattr(loop_module, "format_coverage_summary")
    assert hasattr(loop_module, "CodeAnalyzer")
    assert hasattr(loop_module, "TypeScriptAnalyzer")


def test_all_generators_use_correct_phase():
    """Verify all test generators use the 'qa' phase for configuration."""
    import ast
    from pathlib import Path

    # Get the project root (work back from test file location)
    test_file = Path(__file__).resolve()
    project_root = test_file.parent.parent.parent

    generators = [
        project_root / "apps/backend/agents/test_generator.py",
        project_root / "apps/backend/agents/vitest_generator.py",
        project_root / "apps/backend/agents/e2e_generator.py",
    ]

    for generator_file in generators:
        with open(generator_file) as f:
            tree = ast.parse(f.read())

        # Find all calls to get_phase_model and get_phase_thinking_budget
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["get_phase_model", "get_phase_thinking_budget"]:
                        # Check that it's not using "test_generation" phase
                        for arg in node.args:
                            if isinstance(arg, ast.Constant):
                                assert (
                                    arg.value != "test_generation"
                                ), f"{generator_file} uses invalid phase 'test_generation'"


if __name__ == "__main__":
    # Run the tests
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
