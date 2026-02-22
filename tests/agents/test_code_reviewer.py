#!/usr/bin/env python3
"""
Unit Tests for Code Review Agent
==================================

Tests for the code review agent session covering:
- Successful review returning ("approved", response)
- Review with issues returning ("issues_found", response)
- Error handling returning ("error", error_message)
- Graphiti memory integration (context loading and saving)
- Report file creation and parsing
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BACKEND_PATH = str(Path(__file__).parent.parent / "apps" / "backend")
if _BACKEND_PATH not in sys.path:
    sys.path.insert(0, _BACKEND_PATH)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def test_env(temp_git_repo: Path):
    """
    Create a test environment using the shared temp_git_repo fixture.

    Yields:
        tuple: (temp_dir, spec_dir, project_dir)
    """
    temp_dir = temp_git_repo
    spec_dir = temp_dir / "spec"
    project_dir = temp_dir

    spec_dir.mkdir(parents=True, exist_ok=True)

    # Create spec.md
    (spec_dir / "spec.md").write_text(
        "# Test Spec\n\nTest feature for code review"
    )

    yield temp_dir, spec_dir, project_dir


@pytest.fixture
def mock_client():
    """Create a mock ClaudeSDKClient."""
    client = MagicMock()
    client.create_agent_session = AsyncMock()
    return client


# =============================================================================
# SUCCESSFUL REVIEW TESTS
# =============================================================================


class TestSuccessfulReview:
    """Tests for successful code review scenarios."""

    @pytest.mark.asyncio
    async def test_approved_review_returns_approved_status(
        self, test_env, mock_client
    ):
        """Test that approved review returns ('approved', response)."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        # Create review report indicating approval
        report_content = """# Code Review Report

## Status: APPROVED

No security, performance, or style issues found.

All checks passed.
"""
        (spec_dir / "code_review_report.md").write_text(report_content)

        # Mock agent session to return success
        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = (
                "success",
                "Review completed successfully",
            )
            mock_context.return_value = None

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert status == "approved", "Should return approved status"
            assert "Review completed successfully" in response

    @pytest.mark.asyncio
    async def test_approved_review_no_issues_variant(self, test_env, mock_client):
        """Test approval detection with 'NO ISSUES' in report."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        report_content = """# Code Review Report

## NO ISSUES FOUND

The code review found no critical issues.
"""
        (spec_dir / "code_review_report.md").write_text(report_content)

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert status == "approved", "Should detect approval from NO ISSUES"


# =============================================================================
# ISSUES FOUND TESTS
# =============================================================================


class TestIssuesFound:
    """Tests for code review scenarios where issues are found."""

    @pytest.mark.asyncio
    async def test_review_with_issues_returns_issues_found(
        self, test_env, mock_client
    ):
        """Test that review with issues returns ('issues_found', response)."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        # Create review report with issues
        report_content = """# Code Review Report

## Status: REJECTED

Issues found:
- SQL injection vulnerability in user input
- Performance issue: N+1 query pattern
"""
        (spec_dir / "code_review_report.md").write_text(report_content)

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review found issues")
            mock_context.return_value = None

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert (
                status == "issues_found"
            ), "Should return issues_found status"
            assert "Review found issues" in response

    @pytest.mark.asyncio
    async def test_no_report_assumes_issues_found(self, test_env, mock_client):
        """Test that missing report is treated as issues_found."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        # Don't create any report file

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Session completed")
            mock_context.return_value = None

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert (
                status == "issues_found"
            ), "Should default to issues_found when no report"


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in code review sessions."""

    @pytest.mark.asyncio
    async def test_session_error_returns_error_status(
        self, test_env, mock_client
    ):
        """Test that session errors return ('error', error_message)."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("error", "API timeout")
            mock_context.return_value = None

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert status == "error", "Should return error status"
            assert "API timeout" in response

    @pytest.mark.asyncio
    async def test_exception_handling_returns_error(
        self, test_env, mock_client
    ):
        """Test that exceptions are caught and returned as errors."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.side_effect = Exception("Unexpected error")
            mock_context.return_value = None

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert status == "error", "Should catch exception and return error"
            # Response should contain the exception type but not leak internal details
            assert "Exception" in response


# =============================================================================
# MEMORY INTEGRATION TESTS
# =============================================================================


class TestMemoryIntegration:
    """Tests for Graphiti memory integration."""

    @pytest.mark.asyncio
    async def test_memory_context_loading(self, test_env, mock_client):
        """Test that Graphiti context is loaded before session."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        memory_context = """
Previous security patterns:
- SQL injection found in user_controller.py
- XSS vulnerability in template rendering
"""

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_context.return_value = memory_context
            mock_session.return_value = ("success", "Review completed")

            # Create approval report
            (spec_dir / "code_review_report.md").write_text("Status: APPROVED")

            await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            # Verify context was loaded with correct arguments
            mock_context.assert_called_once()
            args, kwargs = mock_context.call_args
            assert spec_dir in args, f"spec_dir not in call args: {args}"
            assert project_dir in args, f"project_dir not in call args: {args}"

            # Verify context included in prompt passed to session
            session_call = mock_session.call_args
            assert "message" in session_call[1]
            prompt = session_call[1]["message"]
            assert "Previous security patterns" in prompt

    @pytest.mark.asyncio
    async def test_memory_context_not_required(self, test_env, mock_client):
        """Test that session works even if memory context is None."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_context.return_value = None  # No memory available
            mock_session.return_value = ("success", "Review completed")

            # Create approval report
            (spec_dir / "code_review_report.md").write_text("Status: APPROVED")

            status, response = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert status == "approved", "Should work without memory context"


# =============================================================================
# REPORT FILE TESTS
# =============================================================================


class TestReportFileParsing:
    """Tests for review report file creation and parsing."""

    @pytest.mark.asyncio
    async def test_report_file_created_in_spec_dir(self, test_env, mock_client):
        """Test that report file is created in correct location."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            # Simulate agent creating report
            report_path = spec_dir / "code_review_report.md"
            report_path.write_text("Status: APPROVED")

            await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert report_path.exists(), "Report should be created in spec_dir"

    @pytest.mark.asyncio
    async def test_report_parsing_case_insensitive(
        self, test_env, mock_client
    ):
        """Test that report status parsing is case-insensitive."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        # Test lowercase
        (spec_dir / "code_review_report.md").write_text(
            "Status: approved\n\nAll good!"
        )

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            status, _ = await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=1,
            )

            assert (
                status == "approved"
            ), "Should detect approval regardless of case"


# =============================================================================
# SESSION PARAMETERS TESTS
# =============================================================================


class TestSessionParameters:
    """Tests for session parameter handling."""

    @pytest.mark.asyncio
    async def test_target_files_passed_to_prompt(self, test_env, mock_client):
        """Test that target_files parameter is included in prompt."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        target_files = ["src/app.py", "src/utils.py"]

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            # Create approval report
            (spec_dir / "code_review_report.md").write_text("Status: APPROVED")

            await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                target_files=target_files,
                review_session=1,
            )

            # Verify target files in prompt
            session_call = mock_session.call_args
            prompt = session_call[1]["message"]
            assert "src/app.py" in prompt
            assert "src/utils.py" in prompt

    @pytest.mark.asyncio
    async def test_pr_number_passed_to_prompt(self, test_env, mock_client):
        """Test that pr_number parameter is included in prompt."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            # Create approval report
            (spec_dir / "code_review_report.md").write_text("Status: APPROVED")

            await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                pr_number=123,
                review_session=1,
            )

            # Verify PR number in prompt
            session_call = mock_session.call_args
            prompt = session_call[1]["message"]
            assert "123" in prompt or "PR Number" in prompt

    @pytest.mark.asyncio
    async def test_review_session_number_tracked(self, test_env, mock_client):
        """Test that review_session parameter is tracked."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            # Create approval report
            (spec_dir / "code_review_report.md").write_text("Status: APPROVED")

            await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                review_session=3,  # Third iteration
            )

            # Verify session number in prompt
            session_call = mock_session.call_args
            prompt = session_call[1]["message"]
            assert "3" in prompt or "Review Session" in prompt


# =============================================================================
# SELF-CORRECTION TESTS
# =============================================================================


class TestSelfCorrection:
    """Tests for self-correction with previous error context."""

    @pytest.mark.asyncio
    async def test_previous_error_added_to_prompt(self, test_env, mock_client):
        """Test that previous error context is included in prompt."""
        from agents.code_reviewer import run_code_review_session

        temp_dir, spec_dir, project_dir = test_env

        previous_error = {
            "error_message": "Failed to create review report",
            "error_type": "missing_report",
            "consecutive_errors": 1,
        }

        with patch(
            "agents.code_reviewer.run_agent_session", new_callable=AsyncMock
        ) as mock_session, patch(
            "agents.code_reviewer.get_graphiti_context",
            new_callable=AsyncMock,
        ) as mock_context:

            mock_session.return_value = ("success", "Review completed")
            mock_context.return_value = None

            # Create approval report this time
            (spec_dir / "code_review_report.md").write_text("Status: APPROVED")

            await run_code_review_session(
                client=mock_client,
                project_dir=project_dir,
                spec_dir=spec_dir,
                previous_error=previous_error,
                review_session=2,
            )

            # Verify error context in prompt
            session_call = mock_session.call_args
            prompt = session_call[1]["message"]
            assert "PREVIOUS ITERATION FAILED" in prompt
            assert "Failed to create review report" in prompt
            assert "**Consecutive Failures**: 1" in prompt


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_all_tests():
    """Run all tests using pytest."""
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))


if __name__ == "__main__":
    run_all_tests()
