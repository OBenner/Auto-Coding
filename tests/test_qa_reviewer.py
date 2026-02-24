#!/usr/bin/env python3
"""
Tests for QA Reviewer Agent Session
=====================================

Tests the qa/reviewer.py module functionality including:
- Coverage validation (config load failure, pytest-cov not installed, no data)
- QA signoff update with coverage data
- Reviewer session returns "approved", "rejected", or "error"
- Memory context integration
- Previous error context for self-correction
- Coverage results in prompt and signoff

Note: This test module mocks all dependencies to avoid importing
the Claude SDK which is not available in the test environment.
Mocks are installed only during import and immediately restored.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qa_test_helpers import (
    aiter_empty,
    aiter_messages,
    create_base_mocks,
    ensure_backend_path,
    install_mocks_and_import,
    make_text_message,
    restore_backend_path,
    restore_modules,
)

# =============================================================================
# MOCK SETUP - Install mocks, import module, then immediately restore
# =============================================================================
_original_sys_path = ensure_backend_path()

_mock_session = MagicMock()
_mock_session.save_token_stats = MagicMock(return_value=True)

_mock_coverage_analyzer = MagicMock()
_mock_coverage_analyzer.CoverageAnalyzer = MagicMock
_mock_coverage_analyzer.parse_coverage_json = MagicMock()
_mock_coverage_analyzer.CoverageResult = MagicMock

_mock_spec_coverage = MagicMock()
_mock_spec_coverage.load_coverage_config = MagicMock()
_mock_spec_coverage.CoverageConfig = MagicMock
_mock_spec_coverage.CriticalPath = MagicMock
_mock_spec_coverage.get_minimum_coverage_for_file = MagicMock()
_mock_spec_coverage.matches_pattern = MagicMock()

_mocks = create_base_mocks(
    **{
        "agents.session": _mock_session,
        "analysis.coverage_analyzer": _mock_coverage_analyzer,
        "spec.coverage_config": _mock_spec_coverage,
    }
)

_saved = install_mocks_and_import(_mocks)

# Import the module under test (this triggers the full import chain)
from qa.reviewer import (  # noqa: E402
    run_coverage_validation,
    run_qa_agent_session,
    update_qa_signoff_with_coverage,
)

# Immediately restore all modules and sys.path to prevent contamination
restore_modules(_saved)
restore_backend_path(_original_sys_path)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def spec_dir(tmp_path):
    """Create a spec directory with required files."""
    spec = tmp_path / "project" / ".auto-claude" / "specs" / "001-test"
    spec.mkdir(parents=True)
    plan = {
        "spec_name": "test-spec",
        "qa_signoff": {"status": "pending", "qa_session": 0},
    }
    (spec / "implementation_plan.json").write_text(json.dumps(plan, indent=2))
    (spec / "spec.md").write_text("# Test Spec\n")
    return spec


@pytest.fixture
def project_dir(spec_dir):
    """Derive project directory from spec_dir."""
    return spec_dir.parent.parent.parent


@pytest.fixture
def mock_client():
    """Create a mock Claude SDK client."""
    client = AsyncMock()
    client.query = AsyncMock()
    client.receive_response = MagicMock(return_value=aiter_empty())
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# =============================================================================
# HELPERS (shared helpers imported from qa_test_helpers)
# =============================================================================


# =============================================================================
# TESTS: COVERAGE VALIDATION
# =============================================================================


class TestRunCoverageValidation:
    """Tests for run_coverage_validation."""

    def test_config_load_failure(self, project_dir, spec_dir):
        """Returns skipped when coverage config fails to load."""
        with patch(
            "qa.reviewer.load_coverage_config", side_effect=RuntimeError("bad config")
        ):
            success, summary, data = run_coverage_validation(project_dir, spec_dir)

        assert success is True
        assert "skipped" in summary.lower()
        assert "bad config" in summary
        assert data is None

    def test_pytest_cov_not_installed(self, project_dir, spec_dir):
        """Returns skipped when pytest-cov is not installed."""
        mock_config = MagicMock()
        mock_config.minimum_coverage = 80
        mock_config.config_source = "default"
        mock_config.critical_paths = []

        mock_analyzer = MagicMock()
        mock_analyzer.check_pytest_cov_installed.return_value = (False, "Not installed")

        with (
            patch("qa.reviewer.load_coverage_config", return_value=mock_config),
            patch("qa.reviewer.CoverageAnalyzer", return_value=mock_analyzer),
        ):
            success, summary, data = run_coverage_validation(project_dir, spec_dir)

        assert success is True
        assert "skipped" in summary.lower()
        assert "Not installed" in summary
        assert data is None

    def test_coverage_analysis_failure(self, project_dir, spec_dir):
        """Returns failure when coverage analysis fails."""
        mock_config = MagicMock()
        mock_config.minimum_coverage = 80
        mock_config.config_source = "default"
        mock_config.critical_paths = []

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Tests failed"

        mock_analyzer = MagicMock()
        mock_analyzer.check_pytest_cov_installed.return_value = (True, "5.0.0")
        mock_analyzer.run_coverage.return_value = mock_result

        with (
            patch("qa.reviewer.load_coverage_config", return_value=mock_config),
            patch("qa.reviewer.CoverageAnalyzer", return_value=mock_analyzer),
        ):
            success, summary, data = run_coverage_validation(project_dir, spec_dir)

        assert success is False
        assert "Tests failed" in summary
        assert data is None

    def test_successful_validation(self, project_dir, spec_dir):
        """Returns success and coverage_data when validation passes."""
        mock_config = MagicMock()
        mock_config.minimum_coverage = 80
        mock_config.config_source = "default"
        mock_config.critical_paths = []

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.report_path = None
        mock_result.total_coverage = 92.0
        mock_result.files = ["apps/backend/foo.py"]

        mock_analyzer = MagicMock()
        mock_analyzer.check_pytest_cov_installed.return_value = (True, "5.0.0")
        mock_analyzer.run_coverage.return_value = mock_result

        validation = MagicMock(passed=True, issues=[], critical_path_failures=0)

        with (
            patch("qa.reviewer.load_coverage_config", return_value=mock_config),
            patch("qa.reviewer.CoverageAnalyzer", return_value=mock_analyzer),
            patch("qa.reviewer.validate_coverage", return_value=validation),
            patch("qa.reviewer.format_validation_summary", return_value="Summary"),
            patch("qa.reviewer.format_coverage_report", return_value="Report"),
        ):
            success, summary, data = run_coverage_validation(project_dir, spec_dir)

        assert success is True
        assert summary == "Summary"
        assert data["passed"] is True
        assert data["total_coverage"] == 92.0
        assert data["files_analyzed"] == 1
        assert data["issues_count"] == 0
        assert data["critical_path_failures"] == 0
        assert data["minimum_required"] == 80


# =============================================================================
# TESTS: UPDATE QA SIGNOFF WITH COVERAGE
# =============================================================================


class TestUpdateQaSignoffWithCoverage:
    """Tests for update_qa_signoff_with_coverage."""

    def test_no_coverage_data(self, spec_dir):
        """Returns False when coverage_data is None."""
        result = update_qa_signoff_with_coverage(spec_dir, None)
        assert result is False

    def test_no_plan(self, tmp_path):
        """Returns False when implementation plan doesn't exist."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("qa.criteria.load_implementation_plan", return_value=None):
            result = update_qa_signoff_with_coverage(empty_dir, {"passed": True})
        assert result is False

    def test_no_signoff_in_plan(self, spec_dir):
        """Returns False when plan has no qa_signoff."""
        plan_no_signoff = {"spec_name": "test", "phases": []}

        with patch(
            "qa.criteria.load_implementation_plan", return_value=plan_no_signoff
        ):
            result = update_qa_signoff_with_coverage(spec_dir, {"passed": True})
        assert result is False

    def test_successful_update(self, spec_dir):
        """Successfully adds coverage_results to qa_signoff."""
        plan = {
            "spec_name": "test",
            "qa_signoff": {"status": "approved", "qa_session": 1},
        }
        coverage_data = {
            "passed": True,
            "total_coverage": 85.5,
            "files_analyzed": 10,
        }
        saved_plan = {}

        def fake_save(sd, p):
            saved_plan.update(p)
            return True

        with (
            patch("qa.criteria.load_implementation_plan", return_value=plan),
            patch("qa.criteria.save_implementation_plan", side_effect=fake_save),
        ):
            result = update_qa_signoff_with_coverage(spec_dir, coverage_data)

        assert result is True
        assert saved_plan["qa_signoff"]["coverage_results"] == coverage_data


# =============================================================================
# TESTS: QA REVIEWER SESSION
# =============================================================================


class TestRunQaAgentSession:
    """Tests for run_qa_agent_session."""

    @pytest.mark.asyncio
    async def test_approved_status(self, spec_dir, project_dir, mock_client):
        """Returns 'approved' when agent sets approved status."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("All criteria pass"))
        )

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status",
                return_value={"status": "approved", "qa_session": 1},
            ),
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            status, response = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "approved"
        assert "All criteria pass" in response

    @pytest.mark.asyncio
    async def test_rejected_status(self, spec_dir, project_dir, mock_client):
        """Returns 'rejected' when agent finds issues."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Found issues"))
        )

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status",
                return_value={
                    "status": "rejected",
                    "issues_found": [
                        {"type": "critical", "title": "Bug", "location": "test.py:10"}
                    ],
                },
            ),
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            status, response = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "rejected"
        assert "Found issues" in response

    @pytest.mark.asyncio
    async def test_error_no_signoff_update(self, spec_dir, project_dir, mock_client):
        """Returns 'error' when agent doesn't update plan."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Did nothing"))
        )

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch("qa.criteria.get_qa_signoff_status", return_value=None),
        ):
            status, msg = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "error"
        assert "did not update" in msg

    @pytest.mark.asyncio
    async def test_exception_handling(self, spec_dir, project_dir, mock_client):
        """Returns 'error' when client raises exception."""
        mock_client.query = AsyncMock(side_effect=RuntimeError("Connection lost"))

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
        ):
            status, msg = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "error"
        assert "Connection lost" in msg

    @pytest.mark.asyncio
    async def test_memory_context_in_prompt(self, spec_dir, project_dir, mock_client):
        """Memory context is appended to the QA reviewer prompt."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("ok"))
        )

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="BASE PROMPT"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value="## Memory\nUse pattern Y for validation",
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status", return_value={"status": "approved"}
            ),
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            status, _ = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "approved"
        prompt_sent = mock_client.query.call_args[0][0]
        assert "Memory" in prompt_sent
        assert "Use pattern Y for validation" in prompt_sent

    @pytest.mark.asyncio
    async def test_previous_error_context_in_prompt(
        self, spec_dir, project_dir, mock_client
    ):
        """Previous error context is added to the prompt for self-correction."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Fixed"))
        )
        prev_error = {
            "error_type": "no_signoff",
            "error_message": "Agent did not update implementation_plan.json",
            "consecutive_errors": 1,
        }

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status", return_value={"status": "approved"}
            ),
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            status, _ = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=2,
                max_iterations=3,
                previous_error=prev_error,
            )

        assert status == "approved"
        prompt_sent = mock_client.query.call_args[0][0]
        assert "PREVIOUS ITERATION FAILED" in prompt_sent
        assert "Agent did not update" in prompt_sent

    @pytest.mark.asyncio
    async def test_coverage_data_added_to_signoff(
        self, spec_dir, project_dir, mock_client
    ):
        """Coverage data is added to signoff via update_qa_signoff_with_coverage."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("approved"))
        )
        coverage_data = {"passed": True, "total_coverage": 90.0}

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", coverage_data),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status", return_value={"status": "approved"}
            ),
            patch("qa.reviewer.update_qa_signoff_with_coverage") as mock_update,
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            status, _ = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "approved"
        mock_update.assert_called_once_with(spec_dir, coverage_data)

    @pytest.mark.asyncio
    async def test_error_details_empty_response(
        self, spec_dir, project_dir, mock_client
    ):
        """Error message includes details when agent produces no output."""
        mock_client.receive_response = MagicMock(return_value=aiter_empty())

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage OK", None),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch("qa.criteria.get_qa_signoff_status", return_value=None),
        ):
            status, msg = await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        assert status == "error"
        assert "did not update" in msg
        assert "No tools were used" in msg

    @pytest.mark.asyncio
    async def test_coverage_results_in_prompt(self, spec_dir, project_dir, mock_client):
        """Coverage results JSON is included in the prompt text."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("ok"))
        )
        coverage_data = {"passed": True, "total_coverage": 88.5, "files_analyzed": 5}

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(True, "Coverage passed", coverage_data),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status", return_value={"status": "approved"}
            ),
            patch("qa.reviewer.update_qa_signoff_with_coverage"),
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        prompt_sent = mock_client.query.call_args[0][0]
        assert "Coverage Results" in prompt_sent
        assert "88.5" in prompt_sent

    @pytest.mark.asyncio
    async def test_failed_coverage_warning_in_prompt(
        self, spec_dir, project_dir, mock_client
    ):
        """Failed coverage adds warning to prompt."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("reviewed"))
        )

        with (
            patch(
                "qa.reviewer.run_coverage_validation",
                return_value=(False, "Coverage failed", {"passed": False}),
            ),
            patch("qa.reviewer.get_qa_reviewer_prompt", return_value="Review prompt"),
            patch(
                "qa.reviewer.get_graphiti_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("qa.reviewer.get_task_logger", return_value=None),
            patch(
                "qa.criteria.get_qa_signoff_status", return_value={"status": "rejected"}
            ),
            patch("qa.reviewer.update_qa_signoff_with_coverage"),
            patch(
                "qa.reviewer.save_session_memory",
                new_callable=AsyncMock,
                return_value=(True, "f"),
            ),
        ):
            await run_qa_agent_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                qa_session=1,
                max_iterations=3,
            )

        prompt_sent = mock_client.query.call_args[0][0]
        assert "IMPORTANT" in prompt_sent
        assert "Coverage validation failed" in prompt_sent
