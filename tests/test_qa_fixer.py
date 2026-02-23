#!/usr/bin/env python3
"""
Tests for QA Fixer Agent Session
==================================

Tests the qa/fixer.py module functionality including:
- Prompt loading
- Fixer session returns "fixed" on success
- Missing QA_FIX_REQUEST.md returns error
- Circular fix detection returns "circular"
- Recovery loop exhaustion returns "stuck"
- Recovery actions (skip, escalate, rollback, continue)
- Memory context integration
- Recurring issue warnings

Note: This test module mocks all dependencies to avoid importing
the Claude SDK which is not available in the test environment.
Mocks are installed only during import and immediately restored.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# FakeRecoveryAction - used in tests (defined before mock setup)
# =============================================================================


class FakeRecoveryAction:
    def __init__(
        self,
        action="retry",
        reason="test",
        wait_seconds=0,
        use_model_fallback=False,
        should_notify=False,
        notification_message="",
        target="",
        strategy=None,
    ):
        self.action = action
        self.reason = reason
        self.wait_seconds = wait_seconds
        self.use_model_fallback = use_model_fallback
        self.should_notify = should_notify
        self.notification_message = notification_message
        self.target = target
        self.strategy = strategy


# =============================================================================
# MOCK SETUP - Install mocks, import module, then immediately restore
# =============================================================================
# qa.fixer imports from many modules. qa/__init__.py triggers qa.loop which
# imports even more. We mock everything needed for the import chain, then
# immediately restore sys.modules to prevent contamination of other tests.

_backend_path = str(Path(__file__).parent.parent / "apps" / "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Modules we need to mock for the import to succeed
_MODULES_TO_MOCK = [
    "claude_agent_sdk", "claude_agent_sdk.types",
    "ui", "progress", "task_logger", "linear_updater", "client",
    "core.client", "core.model_fallback",
    "agents", "agents.memory_manager", "agents.session", "agents.e2e_generator",
    "agents.test_generator", "agents.coder", "agents.planner", "agents.code_reviewer",
    "agents.documentation_generator", "agents.utils", "agents.base",
    "debug", "phase_config", "phase_event",
    "security.tool_input_validator", "security.constants", "services.recovery",
    "analysis.coverage_analyzer", "analysis.code_analyzer", "analysis.coverage_reporter",
    "analysis.failure_analyzer", "analysis.ts_analyzer",
    "prompts_pkg", "spec.coverage_config",
    "integrations", "integrations.graphiti", "integrations.graphiti.memory",
]

# Save original modules
_saved = {}
for _name in _MODULES_TO_MOCK:
    if _name in sys.modules:
        _saved[_name] = sys.modules[_name]

# Install mocks
_mock_recovery = MagicMock()
_mock_recovery.RecoveryAction = FakeRecoveryAction
_mock_recovery.RecoveryManager = MagicMock

_mock_agents_pkg = MagicMock()
_mock_agents_pkg.__path__ = []

_mock_mm = MagicMock()
_mock_mm.get_graphiti_context = AsyncMock(return_value=None)
_mock_mm.save_session_memory = AsyncMock(return_value=(True, "file"))
_mock_mm.save_user_correction = AsyncMock()

_mock_model_fallback = MagicMock()
_mock_model_fallback.MODEL_FALLBACK_CHAIN = {"sonnet": ["haiku"], "opus": ["sonnet"]}

_mocks = {
    "claude_agent_sdk": MagicMock(ClaudeSDKClient=MagicMock, ClaudeAgentOptions=MagicMock),
    "claude_agent_sdk.types": MagicMock(),
    "ui": MagicMock(print_status=MagicMock()),
    "progress": MagicMock(count_subtasks=MagicMock(return_value=(3, 3)), is_build_complete=MagicMock(return_value=True)),
    "task_logger": MagicMock(LogPhase=MagicMock(), LogEntryType=MagicMock(), get_task_logger=MagicMock(return_value=None)),
    "linear_updater": MagicMock(is_linear_enabled=MagicMock(return_value=False)),
    "client": MagicMock(),
    "core.client": MagicMock(create_client=MagicMock()),
    "core.model_fallback": _mock_model_fallback,
    "agents": _mock_agents_pkg,
    "agents.memory_manager": _mock_mm,
    "agents.session": MagicMock(),
    "agents.e2e_generator": MagicMock(),
    "agents.test_generator": MagicMock(),
    "agents.coder": MagicMock(),
    "agents.planner": MagicMock(),
    "agents.code_reviewer": MagicMock(),
    "agents.documentation_generator": MagicMock(),
    "agents.utils": MagicMock(),
    "agents.base": MagicMock(),
    "debug": MagicMock(),
    "phase_config": MagicMock(resolve_model_id=MagicMock(return_value="claude-haiku")),
    "phase_event": MagicMock(),
    "security.tool_input_validator": MagicMock(get_safe_tool_input=MagicMock(return_value=None)),
    "security.constants": MagicMock(),
    "services.recovery": _mock_recovery,
    "analysis.coverage_analyzer": MagicMock(),
    "analysis.code_analyzer": MagicMock(),
    "analysis.coverage_reporter": MagicMock(),
    "analysis.failure_analyzer": MagicMock(),
    "analysis.ts_analyzer": MagicMock(),
    "prompts_pkg": MagicMock(get_qa_reviewer_prompt=MagicMock(return_value="QA reviewer prompt")),
    "spec.coverage_config": MagicMock(),
    "integrations": MagicMock(),
    "integrations.graphiti": MagicMock(),
    "integrations.graphiti.memory": MagicMock(),
}

for _name, _mock in _mocks.items():
    sys.modules[_name] = _mock

# Import the module under test (this triggers the full import chain)
from qa.fixer import (  # noqa: E402
    MAX_FIXER_ITERATIONS,
    load_qa_fixer_prompt,
    run_qa_fixer_session,
)

# Immediately restore all modules to prevent contamination of other test files
for _name in _MODULES_TO_MOCK:
    if _name in _saved:
        sys.modules[_name] = _saved[_name]
    elif _name in sys.modules:
        del sys.modules[_name]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def spec_dir(tmp_path):
    """Create a spec directory with required files."""
    spec = tmp_path / "project" / ".auto-claude" / "specs" / "001-test"
    spec.mkdir(parents=True)
    (spec / "QA_FIX_REQUEST.md").write_text("## Fix these issues\n- Bug 1\n")
    plan = {
        "spec_name": "test-spec",
        "qa_signoff": {"status": "rejected", "qa_session": 1},
    }
    (spec / "implementation_plan.json").write_text(json.dumps(plan, indent=2))
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
    client.receive_response = AsyncMock(return_value=aiter_empty())
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_recovery_mgr():
    """Create a mock RecoveryManager."""
    mgr = MagicMock()
    mgr.is_circular_fix = MagicMock(return_value=False)
    mgr.get_attempt_count = MagicMock(return_value=0)
    mgr.record_attempt = MagicMock()
    mgr.record_outcome = MagicMock()
    mgr.classify_failure = MagicMock(return_value="transient")
    mgr.determine_recovery_action = MagicMock(
        return_value=FakeRecoveryAction(action="skip", reason="test skip")
    )
    mgr.record_recovery_notification = MagicMock()
    mgr.mark_subtask_stuck = MagicMock()
    mgr.rollback_to_commit = MagicMock(return_value=True)
    return mgr


# =============================================================================
# HELPERS
# =============================================================================


async def aiter_empty():
    """Empty async iterator for mock receive_response."""
    return
    yield  # noqa: RET504


def make_text_message(text):
    """Create a mock AssistantMessage with a TextBlock."""
    block = MagicMock()
    type(block).__name__ = "TextBlock"
    block.text = text
    msg = MagicMock()
    type(msg).__name__ = "AssistantMessage"
    msg.content = [block]
    return msg


async def aiter_messages(*msgs):
    """Create an async iterator from messages."""
    for m in msgs:
        yield m


# =============================================================================
# TESTS: PROMPT LOADING
# =============================================================================


class TestLoadQaFixerPrompt:
    """Tests for load_qa_fixer_prompt."""

    def test_load_prompt_success(self, tmp_path):
        """Test loading the QA fixer prompt from a file."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "qa_fixer.md").write_text("Fix the issues")

        with patch("qa.fixer.QA_PROMPTS_DIR", prompts_dir):
            result = load_qa_fixer_prompt()
            assert result == "Fix the issues"

    def test_load_prompt_file_not_found(self, tmp_path):
        """Test FileNotFoundError when prompt file doesn't exist."""
        with patch("qa.fixer.QA_PROMPTS_DIR", tmp_path / "nonexistent"):
            with pytest.raises(FileNotFoundError):
                load_qa_fixer_prompt()


# =============================================================================
# TESTS: FIXER SESSION - BASIC FLOW
# =============================================================================


class TestRunQaFixerSession:
    """Tests for run_qa_fixer_session."""

    @pytest.mark.asyncio
    async def test_missing_fix_request_file(self, tmp_path, mock_client):
        """Returns error when QA_FIX_REQUEST.md is missing."""
        spec = tmp_path / "spec"
        spec.mkdir()

        status, msg = await run_qa_fixer_session(
            client=mock_client, spec_dir=spec, fix_session=1, project_dir=tmp_path,
        )
        assert status == "error"
        assert "QA_FIX_REQUEST.md not found" in msg

    @pytest.mark.asyncio
    async def test_circular_fix_detected(self, spec_dir, project_dir, mock_client):
        """Returns 'circular' when recovery manager detects circular fix."""
        mgr = MagicMock()
        mgr.is_circular_fix = MagicMock(return_value=True)
        mgr.get_attempt_count = MagicMock(return_value=3)
        mgr.record_outcome = MagicMock()

        with (
            patch("qa.fixer.RecoveryManager", return_value=mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
        ):
            status, msg = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "circular"
        assert "Circular fix" in msg
        mgr.record_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_fix_with_status_ready(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr
    ):
        """Returns 'fixed' when is_fixes_applied returns True."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Applied fix"))
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.criteria.get_qa_signoff_status", return_value={"status": "fixes_applied", "ready_for_qa_revalidation": True}),
            patch("qa.criteria.is_fixes_applied", return_value=True),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
            patch("qa.fixer.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")),
        ):
            status, response = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "fixed"
        assert "Applied fix" in response
        mock_recovery_mgr.record_outcome.assert_called_with("qa_fixer_1", success=True)

    @pytest.mark.asyncio
    async def test_successful_fix_without_status_ready(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr
    ):
        """Returns 'fixed' even when is_fixes_applied returns False (assumed applied)."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Done"))
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.criteria.get_qa_signoff_status", return_value={"status": "rejected"}),
            patch("qa.criteria.is_fixes_applied", return_value=False),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
            patch("qa.fixer.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")),
        ):
            status, _response = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "fixed"

    @pytest.mark.asyncio
    async def test_memory_context_appended_to_prompt(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr
    ):
        """Memory context is appended to the fixer prompt when available."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("ok"))
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="BASE PROMPT"),
            patch("qa.criteria.get_qa_signoff_status", return_value={"status": "fixes_applied"}),
            patch("qa.criteria.is_fixes_applied", return_value=True),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value="## Memory Context\nPrevious fix used pattern X"),
            patch("qa.fixer.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")),
        ):
            status, _ = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "fixed"
        prompt_sent = mock_client.query.call_args[0][0]
        assert "Memory Context" in prompt_sent
        assert "Previous fix used pattern X" in prompt_sent


# =============================================================================
# TESTS: RECOVERY ACTIONS
# =============================================================================


class TestRecoveryActions:
    """Tests for recovery action handling in the fixer loop."""

    @pytest.mark.asyncio
    async def test_recovery_skip_returns_stuck(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr
    ):
        """Recovery action 'skip' returns 'stuck' status."""
        mock_client.query = AsyncMock(side_effect=RuntimeError("Agent failed"))
        mock_recovery_mgr.determine_recovery_action = MagicMock(
            return_value=FakeRecoveryAction(action="skip", reason="Max retries exceeded")
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
        ):
            status, msg = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "stuck"
        assert "Max retries exceeded" in msg
        mock_recovery_mgr.mark_subtask_stuck.assert_called_once()

    @pytest.mark.asyncio
    async def test_recovery_escalate_returns_escalate(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr
    ):
        """Recovery action 'escalate' returns 'escalate' status."""
        mock_client.query = AsyncMock(side_effect=RuntimeError("Critical failure"))
        mock_recovery_mgr.determine_recovery_action = MagicMock(
            return_value=FakeRecoveryAction(action="escalate", reason="Critical: auth failed")
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
        ):
            status, msg = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "escalate"
        assert "Critical: auth failed" in msg

    @pytest.mark.asyncio
    async def test_exhausted_iterations_returns_stuck(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr
    ):
        """Exhausting MAX_FIXER_ITERATIONS returns 'stuck'."""
        mock_client.query = AsyncMock(side_effect=RuntimeError("Failed"))
        mock_recovery_mgr.determine_recovery_action = MagicMock(
            return_value=FakeRecoveryAction(action="continue", reason="Context exhausted")
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.fixer.MAX_FIXER_ITERATIONS", 2),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
        ):
            status, msg = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "stuck"
        assert "exhausting all recovery attempts" in msg

    @pytest.mark.asyncio
    async def test_recovery_retry_then_success(self, spec_dir, project_dir, mock_recovery_mgr):
        """Recovery action 'retry' retries, then succeeds on second attempt."""
        call_count = 0

        async def fake_query(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Transient error")

        client = AsyncMock()
        client.query = AsyncMock(side_effect=fake_query)
        client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Fixed it"))
        )

        mock_recovery_mgr.determine_recovery_action = MagicMock(
            return_value=FakeRecoveryAction(action="retry", reason="Transient, retrying")
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.criteria.get_qa_signoff_status", return_value={"status": "fixes_applied"}),
            patch("qa.criteria.is_fixes_applied", return_value=True),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
            patch("qa.fixer.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")),
        ):
            status, _response = await run_qa_fixer_session(
                client=client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "fixed"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_recurring_issues_warning(
        self, spec_dir, project_dir, mock_client, mock_recovery_mgr, capsys
    ):
        """Recurring issues print a warning but don't block the fixer."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("Fixed"))
        )
        (spec_dir / "qa_report.md").write_text("## QA Report\n- Bug A found\n")

        history = [
            {"iteration": 1, "status": "rejected", "issues": [{"title": "Bug A"}]},
            {"iteration": 2, "status": "rejected", "issues": [{"title": "Bug A"}]},
        ]

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=history),
            patch("qa.report.has_recurring_issues", return_value=(True, [{"title": "Bug A", "count": 3}])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.criteria.get_qa_signoff_status", return_value={"status": "fixes_applied"}),
            patch("qa.criteria.is_fixes_applied", return_value=True),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
            patch("qa.fixer.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")),
        ):
            status, _ = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=project_dir,
            )
        assert status == "fixed"
        captured = capsys.readouterr()
        assert "Recurring issues detected" in captured.out

    @pytest.mark.asyncio
    async def test_project_dir_derived_from_spec_dir(self, spec_dir, mock_client, mock_recovery_mgr):
        """When project_dir is None, it's derived from spec_dir (3 parents up)."""
        mock_client.receive_response = MagicMock(
            return_value=aiter_messages(make_text_message("ok"))
        )

        with (
            patch("qa.fixer.RecoveryManager", return_value=mock_recovery_mgr),
            patch("qa.report.get_iteration_history", return_value=[]),
            patch("qa.report.has_recurring_issues", return_value=(False, [])),
            patch("qa.report.record_iteration", return_value=True),
            patch("qa.fixer.load_qa_fixer_prompt", return_value="Fix prompt"),
            patch("qa.criteria.get_qa_signoff_status", return_value={"status": "fixes_applied"}),
            patch("qa.criteria.is_fixes_applied", return_value=True),
            patch("qa.fixer.get_graphiti_context", new_callable=AsyncMock, return_value=None),
            patch("qa.fixer.save_session_memory", new_callable=AsyncMock, return_value=(True, "file")),
        ):
            status, _ = await run_qa_fixer_session(
                client=mock_client, spec_dir=spec_dir, fix_session=1, project_dir=None,
            )
        assert status == "fixed"


# =============================================================================
# TESTS: CONSTANTS
# =============================================================================


class TestConstants:
    """Test module-level constants."""

    def test_max_fixer_iterations_value(self):
        assert MAX_FIXER_ITERATIONS == 10
