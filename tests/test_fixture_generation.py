#!/usr/bin/env python3
"""
Tests for Fixture Generation Agent
===================================

Tests the fixture generator agent functionality including:
- Fixture generation for test data
- Validation of fixture files
- Integration with code analysis
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Store original modules for cleanup
_original_modules = {}
_mocked_module_names = [
    "claude_code_sdk",
    "claude_code_sdk.types",
    "claude_agent_sdk",
    "claude_agent_sdk.types",
]

for name in _mocked_module_names:
    if name in sys.modules:
        _original_modules[name] = sys.modules[name]

# Mock Claude SDK before importing fixture generator modules
mock_code_sdk = MagicMock()
mock_code_sdk.ClaudeSDKClient = MagicMock()
mock_code_sdk.ClaudeCodeOptions = MagicMock()
mock_code_types = MagicMock()
mock_code_types.HookMatcher = MagicMock()
sys.modules["claude_code_sdk"] = mock_code_sdk
sys.modules["claude_code_sdk.types"] = mock_code_types

mock_agent_sdk = MagicMock()
mock_agent_sdk.ClaudeSDKClient = MagicMock()
mock_agent_sdk.ClaudeCodeOptions = MagicMock()
mock_agent_types = MagicMock()
mock_agent_types.HookMatcher = MagicMock()
sys.modules["claude_agent_sdk"] = mock_agent_sdk
sys.modules["claude_agent_sdk.types"] = mock_agent_types

# Import fixture generation modules
from agents.fixture_generator import generate_fixtures, validate_fixture_files


# Cleanup fixture to restore original modules after all tests
@pytest.fixture(scope="module", autouse=True)
def cleanup_mocked_modules():
    """Restore original modules after all tests in this module complete."""
    yield  # Run all tests first
    # Cleanup: restore original modules or remove mocks
    for name in _mocked_module_names:
        if name in _original_modules:
            sys.modules[name] = _original_modules[name]
        elif name in sys.modules:
            del sys.modules[name]


# =============================================================================
# FIXTURE VALIDATION TESTS
# =============================================================================


class TestFixtureValidation:
    """Tests for fixture file validation."""

    @pytest.mark.asyncio
    async def test_validate_fixture_files_valid_syntax(self, temp_dir: Path):
        """validate_fixture_files accepts syntactically correct fixtures."""
        # Create a valid conftest.py
        conftest = temp_dir / "tests" / "conftest.py"
        conftest.parent.mkdir(parents=True)
        conftest.write_text("""
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}
""")

        fixture_files = [conftest.relative_to(temp_dir)]
        result = await validate_fixture_files(fixture_files, temp_dir)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_fixture_files_invalid_syntax(self, temp_dir: Path):
        """validate_fixture_files rejects invalid syntax."""
        # Create fixture file with syntax error
        invalid_fixture = temp_dir / "tests" / "conftest.py"
        invalid_fixture.parent.mkdir(parents=True)
        invalid_fixture.write_text("""
@pytest.fixture
def broken_fixture(
    pass  # Missing closing paren
""")

        fixture_files = [invalid_fixture.relative_to(temp_dir)]
        result = await validate_fixture_files(fixture_files, temp_dir)

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_fixture_files_empty_list(self, temp_dir: Path):
        """validate_fixture_files handles empty file list."""
        result = await validate_fixture_files([], temp_dir)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_fixture_files_missing_file(self, temp_dir: Path):
        """validate_fixture_files handles missing file."""
        missing_file = Path("tests/fixtures/missing.py")
        result = await validate_fixture_files([missing_file], temp_dir)
        assert result is False


# =============================================================================
# FIXTURE GENERATION SESSION TESTS
# =============================================================================


class TestGenerateFixtures:
    """Tests for generate_fixtures orchestration function."""

    @pytest.fixture(autouse=True)
    def _mock_fixture_generator_deps(self, monkeypatch):
        """Apply common monkeypatches for all fixture generator tests."""
        # Mock run_generator_session instead of create_client
        # (fixture_generator imports run_generator_session, not create_client directly)
        async def mock_run_session(*args, **kwargs):
            return {
                "success": True,
                "generated_files": [],
                "error": None
            }
        monkeypatch.setattr(
            "agents.fixture_generator.run_generator_session",
            mock_run_session
        )
        # Mock UI functions to suppress output
        monkeypatch.setattr(
            "agents.fixture_generator.print_status", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(
            "agents.fixture_generator.print_key_value", lambda *args, **kwargs: None
        )
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    @pytest.mark.asyncio
    async def test_successful_fixture_generation(self, temp_dir: Path, monkeypatch):
        """generate_fixtures successfully creates fixture files."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Create a conftest.py fixture file
        (tests_dir / "conftest.py").write_text("""
import pytest

@pytest.fixture
def sample_data():
    return {"test": "data"}
""")

        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=True)
        )

        analysis = {
            "classes": [{"name": "UserService"}],
            "functions": [{"name": "create_user"}],
            "models": [{"name": "User"}]
        }
        result = await generate_fixtures(
            project_dir, spec_dir, analysis, model="claude-sonnet-4"
        )

        assert result["success"] is True
        assert len(result["generated_files"]) == 1
        assert "conftest.py" in result["generated_files"][0]
        assert result["error"] is None
        assert result["framework"] == "pytest-fixtures"

    @pytest.mark.asyncio
    async def test_no_tests_directory(self, temp_dir: Path):
        """generate_fixtures handles missing tests/ directory."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        project_dir.mkdir(parents=True)

        analysis = {"classes": [], "functions": [], "models": []}
        result = await generate_fixtures(project_dir, spec_dir, analysis)

        assert result["success"] is False
        assert result["error"] == "tests/ directory not found"
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_no_fixtures_generated(self, temp_dir: Path):
        """generate_fixtures handles case where no fixture files are created."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        analysis = {"classes": [], "functions": [], "models": []}
        result = await generate_fixtures(project_dir, spec_dir, analysis)

        # Should fail since no fixture files were generated
        assert result["success"] is False
        assert result["error"] == "No fixture files were generated"
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_validation_failure(self, temp_dir: Path, monkeypatch):
        """generate_fixtures handles validation failures."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Create invalid fixture
        (tests_dir / "conftest.py").write_text("invalid syntax here")

        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=False)
        )
        # Mock log_generator_result to avoid task_logger.log_entry call
        monkeypatch.setattr(
            "agents.fixture_generator.log_generator_result",
            lambda *args, **kwargs: None
        )

        analysis = {"classes": [], "functions": [], "models": []}
        result = await generate_fixtures(project_dir, spec_dir, analysis)

        assert result["success"] is False  # Validation failure propagated
        assert "validation failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_multiple_fixture_files(self, temp_dir: Path, monkeypatch):
        """generate_fixtures handles multiple fixture files."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        fixtures_dir = tests_dir / "fixtures"
        fixtures_dir.mkdir(parents=True)

        # Create conftest.py
        (tests_dir / "conftest.py").write_text("""
import pytest

@pytest.fixture
def global_fixture():
    return "data"
""")

        # Create additional fixture files
        (fixtures_dir / "user_fixtures.py").write_text("""
import pytest

@pytest.fixture
def user_data():
    return {"id": 1}
""")
        (fixtures_dir / "api_fixtures.py").write_text("""
import pytest

@pytest.fixture
def api_client():
    return mock_client()
""")

        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=True)
        )

        analysis = {"classes": [], "functions": [], "models": []}
        result = await generate_fixtures(project_dir, spec_dir, analysis)

        assert result["success"] is True
        assert len(result["generated_files"]) == 3

    @pytest.mark.asyncio
    async def test_custom_model_and_thinking_budget(self, temp_dir: Path, monkeypatch):
        """generate_fixtures respects custom model and thinking budget."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "conftest.py").write_text("""
import pytest

@pytest.fixture
def data():
    return {}
""")

        # Track call arguments to run_generator_session
        call_kwargs = {}

        async def mock_run_session(**kwargs):
            call_kwargs.update(kwargs)
            return {
                "success": True,
                "generated_files": [],
                "error": None
            }

        monkeypatch.setattr(
            "agents.fixture_generator.run_generator_session",
            mock_run_session
        )
        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=True)
        )

        analysis = {"classes": [], "functions": [], "models": []}
        result = await generate_fixtures(
            project_dir,
            spec_dir,
            analysis,
            model="claude-opus-4",
            max_thinking_tokens=10000,
        )

        assert result["success"] is True
        assert call_kwargs["model"] == "claude-opus-4"
        assert call_kwargs["max_thinking_tokens"] == 10000

    @pytest.mark.asyncio
    async def test_analysis_results_in_starting_message(self, temp_dir: Path, monkeypatch):
        """generate_fixtures includes analysis results in starting message."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "conftest.py").write_text("""
import pytest

@pytest.fixture
def data():
    return {}
""")

        captured_message = None

        async def mock_run_session_with_capture(*args, **kwargs):
            nonlocal captured_message
            captured_message = kwargs.get("starting_message", "")
            return {
                "success": True,
                "generated_files": [],
                "error": None
            }

        monkeypatch.setattr(
            "agents.fixture_generator.run_generator_session",
            mock_run_session_with_capture
        )
        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=True)
        )

        analysis = {
            "classes": [
                {"name": "UserService"},
                {"name": "ProductService"}
            ],
            "functions": [
                {"name": "create_user"},
                {"name": "delete_user"}
            ],
            "models": [
                {"name": "User"}
            ]
        }

        result = await generate_fixtures(project_dir, spec_dir, analysis)

        assert result["success"] is True
        assert captured_message is not None
        assert "Code Analysis Results" in captured_message
        assert "UserService" in captured_message

    @pytest.mark.asyncio
    async def test_fixtures_in_fixtures_subdirectory(self, temp_dir: Path, monkeypatch):
        """generate_fixtures scans tests/fixtures/ subdirectory."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        fixtures_dir = tests_dir / "fixtures"
        fixtures_dir.mkdir(parents=True)

        # Create fixture files in subdirectory
        (fixtures_dir / "data_fixtures.py").write_text("""
import pytest

@pytest.fixture
def test_data():
    return {}
""")
        (fixtures_dir / "__init__.py").write_text("")  # Should be ignored

        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=True)
        )

        analysis = {"classes": [], "functions": [], "models": []}
        result = await generate_fixtures(project_dir, spec_dir, analysis)

        assert result["success"] is True
        assert len(result["generated_files"]) == 1
        assert "data_fixtures.py" in result["generated_files"][0]
        assert "__init__.py" not in str(result["generated_files"])


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestFixtureGenerationPipeline:
    """Integration tests for fixture generation pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_fixture_generation(self, temp_dir: Path, monkeypatch):
        """Complete pipeline: code analysis -> fixture generation -> validation."""
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Simulate agent creating fixtures
        (tests_dir / "conftest.py").write_text("""
import pytest

@pytest.fixture
def sample_fixture():
    return {"key": "value"}
""")

        # Mock run_generator_session to avoid actual agent call
        async def mock_run_session(*args, **kwargs):
            return {
                "success": True,
                "generated_files": [],
                "error": None
            }
        monkeypatch.setattr(
            "agents.fixture_generator.run_generator_session",
            mock_run_session
        )
        monkeypatch.setattr(
            "agents.fixture_generator.validate_fixture_files",
            AsyncMock(return_value=True)
        )
        # Mock log_generator_result to avoid task_logger.log_entry call
        monkeypatch.setattr(
            "agents.fixture_generator.log_generator_result",
            lambda *args, **kwargs: None
        )

        # Step 1: Code analysis (simulated)
        analysis = {
            "classes": [{"name": "Calculator", "methods": 5}],
            "functions": [{"name": "add"}, {"name": "subtract"}],
            "models": []
        }

        # Step 2: Generate fixtures
        result = await generate_fixtures(project_dir, spec_dir, analysis)

        # Verify results
        assert result["success"] is True
        assert len(result["generated_files"]) > 0
        assert result["framework"] == "pytest-fixtures"
