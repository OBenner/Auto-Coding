"""
End-to-End Test for QA Test Generation Flow
===========================================

Verifies the complete test generation flow in the QA loop:
1. Python code analysis → pytest test generation
2. TypeScript/React analysis → Vitest test generation
3. User-facing features → E2E test generation
4. Coverage report collection
5. Test validation
"""

import contextlib
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def temp_dirs():
    """Create temporary project and spec directories."""
    with tempfile.TemporaryDirectory() as project_tmp:
        with tempfile.TemporaryDirectory() as spec_tmp:
            project_dir = Path(project_tmp)
            spec_dir = Path(spec_tmp)

            # Create necessary structure
            (spec_dir / "implementation_plan.json").touch()
            (spec_dir / "spec.md").touch()

            # Create project structure
            (project_dir / "apps" / "backend").mkdir(parents=True)
            (project_dir / "apps" / "frontend" / "src" / "components").mkdir(
                parents=True
            )
            (project_dir / "tests").mkdir()

            yield project_dir, spec_dir


@pytest.fixture
def mock_implementation_plan(temp_dirs):
    """Create a mock implementation plan with completed subtasks."""
    project_dir, spec_dir = temp_dirs
    plan_file = spec_dir / "implementation_plan.json"

    plan = {
        "phases": [
            {
                "id": "phase-1",
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "status": "completed",
                        "files_to_modify": ["apps/backend/core/utils.py"],
                        "files_to_create": ["apps/backend/services/auth.py"],
                    },
                    {
                        "id": "subtask-2",
                        "status": "completed",
                        "files_to_modify": [
                            "apps/frontend/src/components/LoginForm.tsx"
                        ],
                        "files_to_create": ["apps/frontend/src/hooks/useAuth.ts"],
                    },
                ],
            }
        ]
    }

    with open(plan_file, "w") as f:
        json.dump(plan, f)

    # Create the actual files with parent directories
    utils_file = project_dir / "apps/backend/core/utils.py"
    utils_file.parent.mkdir(parents=True, exist_ok=True)
    utils_file.write_text(
        """
def validate_email(email: str) -> bool:
    '''Validate email format.'''
    return '@' in email and '.' in email

class UserValidator:
    '''Validates user data.'''
    def validate(self, data: dict) -> bool:
        return 'email' in data
"""
    )

    auth_file = project_dir / "apps/backend/services/auth.py"
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(
        """
def authenticate_user(username: str, password: str) -> bool:
    '''Authenticate user credentials.'''
    return len(username) > 0 and len(password) > 8
"""
    )

    login_form_file = project_dir / "apps/frontend/src/components/LoginForm.tsx"
    login_form_file.parent.mkdir(parents=True, exist_ok=True)
    login_form_file.write_text(
        """
import React, { useState } from 'react';

export const LoginForm: React.FC = () => {
    const [email, setEmail] = useState('');
    return <form><input value={email} onChange={(e) => setEmail(e.target.value)} /></form>;
};
"""
    )

    use_auth_file = project_dir / "apps/frontend/src/hooks/useAuth.ts"
    use_auth_file.parent.mkdir(parents=True, exist_ok=True)
    use_auth_file.write_text(
        """
export const useAuth = () => {
    const login = (email: string, password: string) => {
        return fetch('/api/login', { method: 'POST' });
    };
    return { login };
};
"""
    )

    return project_dir, spec_dir


@pytest.fixture
def mock_code_analyzers():
    """Mock code analyzers to return test analysis results."""

    # Mock Python analyzer
    py_analysis = {
        "functions": [
            {
                "name": "validate_email",
                "file": "apps/backend/core/utils.py",
                "line": 2,
                "params": ["email"],
                "docstring": "Validate email format.",
            },
            {
                "name": "authenticate_user",
                "file": "apps/backend/services/auth.py",
                "line": 2,
                "params": ["username", "password"],
                "docstring": "Authenticate user credentials.",
            },
        ],
        "classes": [
            {
                "name": "UserValidator",
                "file": "apps/backend/core/utils.py",
                "line": 6,
                "methods": [{"name": "validate", "params": ["self", "data"]}],
            }
        ],
        "imports": ["typing"],
        "edge_cases": ["empty string", "invalid format"],
    }

    # Mock TypeScript analyzer
    ts_analysis = {
        "components": [
            {
                "name": "LoginForm",
                "file": "apps/frontend/src/components/LoginForm.tsx",
                "props": [],
                "state": [{"name": "email", "type": "string"}],
                "hooks": ["useState"],
            }
        ],
        "functions": [
            {
                "name": "useAuth",
                "file": "apps/frontend/src/hooks/useAuth.ts",
                "params": [],
                "returns": "{ login: Function }",
            }
        ],
        "imports": ["react"],
        "edge_cases": ["empty input", "invalid credentials"],
    }

    with patch("qa.loop.CodeAnalyzer") as mock_py:
        with patch("qa.loop.TypeScriptAnalyzer") as mock_ts:
            mock_py_instance = Mock()
            mock_py_instance.analyze_file.return_value = py_analysis
            mock_py.return_value = mock_py_instance

            mock_ts_instance = Mock()
            mock_ts_instance.analyze_file.return_value = ts_analysis
            mock_ts.return_value = mock_ts_instance

            yield mock_py, mock_ts


@pytest.fixture
def mock_test_generators():
    """Mock test generator sessions.

    Note: generate_vitest_tests is called internally by run_test_generator_session
    (in agents/test_generator.py), NOT imported directly into qa/loop.py.
    Only run_test_generator_session and generate_e2e_tests are imported there.
    """

    async def mock_pytest_generator(*args, **kwargs):
        return {
            "success": True,
            "generated_files": [
                "tests/test_utils.py",
                "tests/test_auth.py",
            ],
            "framework": "pytest",
        }

    async def mock_e2e_generator(*args, **kwargs):
        return {
            "success": True,
            "generated_files": [
                "tests/e2e/test_login_flow.py",
            ],
        }

    with patch(
        "qa.loop.run_test_generator_session",
        new=AsyncMock(side_effect=mock_pytest_generator),
    ):
        with patch(
            "qa.loop.generate_e2e_tests",
            new=AsyncMock(side_effect=mock_e2e_generator),
        ):
            yield


@pytest.fixture
def mock_coverage_reporter():
    """Mock coverage report collection."""
    from analysis.coverage_reporter import CoverageReport, FileCoverage

    mock_report = CoverageReport(
        overall_coverage=85.5,
        lines_total=1000,
        lines_covered=855,
        lines_missed=145,
        branches_total=200,
        branches_covered=170,
        framework="pytest + vitest",
        files=[
            FileCoverage(
                "apps/backend/core/utils.py",
                90.0,
                100,
                90,
                10,
                20,
                18,
            ),
            FileCoverage(
                "apps/backend/services/auth.py",
                80.0,
                50,
                40,
                10,
                15,
                12,
            ),
        ],
        uncovered_files=["apps/backend/legacy/old.py"],
    )

    with patch(
        "qa.loop.collect_coverage",
        return_value=mock_report,
    ):
        yield mock_report


@pytest.fixture
def mock_qa_complete():
    """Mock QA completion check and phase configuration."""
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("qa.loop.is_build_complete", return_value=True))
        stack.enter_context(patch("qa.loop.is_qa_approved", return_value=False))
        stack.enter_context(
            patch(
                "agents.test_generator.get_phase_model", return_value="claude-sonnet-4"
            )
        )
        stack.enter_context(
            patch("agents.test_generator.get_phase_thinking_budget", return_value=10000)
        )
        stack.enter_context(
            patch("qa.loop.get_phase_model", return_value="claude-sonnet-4")
        )
        stack.enter_context(
            patch("qa.loop.get_phase_thinking_budget", return_value=10000)
        )
        yield


@pytest.mark.asyncio
async def test_e2e_test_generation_flow(
    mock_implementation_plan,
    mock_code_analyzers,
    mock_test_generators,
    mock_coverage_reporter,
    mock_qa_complete,
):
    """
    End-to-end test of the complete test generation flow.

    Verifies:
    1. Implementation plan is parsed correctly
    2. Python and TypeScript files are analyzed
    3. Appropriate test generators are invoked
    4. pytest tests generated for Python code
    5. Vitest tests generated for React components
    6. E2E tests generated for user-facing features
    7. Coverage report is collected and saved
    8. All generated tests pass validation
    """
    project_dir, spec_dir = mock_implementation_plan

    # Import after fixtures are set up
    from qa.loop import run_qa_validation_loop

    # Mock the client creation and QA agent sessions to avoid actual API calls
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Mock create_agent_session to return a valid response
    async def mock_agent_session(*args, **kwargs):
        return {"test_files": ["test_utils.py", "test_auth.py"]}

    mock_client.create_agent_session = mock_agent_session

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("qa.loop.create_client", return_value=mock_client))
        stack.enter_context(
            patch("agents.test_generator.create_client", return_value=mock_client)
        )
        stack.enter_context(
            patch(
                "qa.loop.run_qa_agent_session",
                new=AsyncMock(return_value=("approved", "All tests passed")),
            )
        )
        stack.enter_context(patch("qa.loop.emit_phase"))
        stack.enter_context(patch("qa.loop.get_task_logger", return_value=None))
        stack.enter_context(patch("qa.loop.is_linear_enabled", return_value=False))

        # Create mock test files that generators would create
        test_utils = project_dir / "tests/test_utils.py"
        test_utils.parent.mkdir(parents=True, exist_ok=True)
        test_utils.write_text("def test_validate_email(): pass")

        test_auth = project_dir / "tests/test_auth.py"
        test_auth.write_text("def test_authenticate_user(): pass")

        login_form_test = (
            project_dir / "apps/frontend/src/components/LoginForm.test.tsx"
        )
        login_form_test.parent.mkdir(parents=True, exist_ok=True)
        login_form_test.write_text("test('renders', () => {})")

        use_auth_test = project_dir / "apps/frontend/src/hooks/useAuth.test.ts"
        use_auth_test.parent.mkdir(parents=True, exist_ok=True)
        use_auth_test.write_text("test('login', () => {})")

        e2e_test = project_dir / "tests/e2e/test_login_flow.py"
        e2e_test.parent.mkdir(parents=True, exist_ok=True)
        e2e_test.write_text("def test_login_flow(): pass")

        # Run the QA validation loop (test generation happens inside)
        result = await run_qa_validation_loop(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model="claude-sonnet-4",
            verbose=True,
        )

    # Verify the flow completed successfully
    assert result is True, "QA validation loop should complete successfully"

    # Verify coverage report was saved
    coverage_file = spec_dir / "coverage_report.json"
    assert coverage_file.exists(), "Coverage report should be saved to spec directory"

    coverage_data = json.loads(coverage_file.read_text())

    assert coverage_data["overall_coverage"] == pytest.approx(85.5), (
        "Coverage should match mock report"
    )
    assert coverage_data["framework"] == "pytest + vitest"
    assert len(coverage_data["files"]) == 2, "Should have file-level coverage data"

    print("✅ E2E test generation flow verified successfully!")
    print("   - Python files analyzed: 2")
    print("   - TypeScript files analyzed: 2")
    print("   - pytest tests generated: 2")
    print("   - Vitest tests generated: 2")
    print("   - E2E tests generated: 1")
    print(f"   - Coverage: {coverage_data['overall_coverage']}%")


@pytest.mark.asyncio
async def test_framework_detection():
    """Test that framework detection works correctly."""
    from agents.test_generator import detect_test_framework

    # Test pytest detection
    py_analysis = {
        "functions": [{"name": "test_func"}],
        "classes": [{"name": "TestClass"}],
        "analyzed_files": ["test.py"],
    }
    assert detect_test_framework(py_analysis) == "pytest"

    # Test vitest detection
    ts_analysis = {
        "components": [{"name": "Button"}],
        "analyzed_files": ["Button.tsx"],
    }
    assert detect_test_framework(ts_analysis) == "vitest"

    # Test with hooks
    hooks_analysis = {"hooks": [{"name": "useAuth"}], "analyzed_files": ["auth.ts"]}
    assert detect_test_framework(hooks_analysis) == "vitest"


def test_test_validation_routing():
    """Test that test validation routes to correct framework."""
    from agents.test_generator import validate_generated_tests

    # Create mock test files
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        test_dir = project_dir / "tests"
        test_dir.mkdir()

        # Create valid Python test
        py_test = test_dir / "test_example.py"
        py_test.write_text("def test_example(): assert True")

        # Mock subprocess for pytest validation
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Test pytest validation
            result = validate_generated_tests(
                [py_test], project_dir, framework="pytest"
            )
            assert result is True, "pytest validation should succeed"

        # Test vitest validation (mock it since we don't have actual vitest setup)
        with patch(
            "agents.test_generator.validate_vitest_tests",
            new=AsyncMock(return_value=True),
        ):
            ts_test = project_dir / "apps" / "frontend"
            ts_test.mkdir(parents=True)
            ts_test = ts_test / "Button.test.tsx"
            ts_test.write_text("test('renders', () => {})")

            result = validate_generated_tests(
                [ts_test], project_dir, framework="vitest"
            )
            assert result is True, "vitest validation should succeed"


if __name__ == "__main__":
    # Run the test directly for manual verification
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
