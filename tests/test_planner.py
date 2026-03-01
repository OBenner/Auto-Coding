#!/usr/bin/env python3
"""
Tests for Planner Agent
========================

Tests the planner module which handles follow-up planner sessions
for adding new subtasks to completed specs.
"""

import json

# Add apps/backend to path for imports
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents.planner import run_followup_planner

# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------

_PATCHES = [
    "agents.planner.StatusManager",
    "agents.planner.get_task_logger",
    "agents.planner.emit_phase",
    "agents.planner.print_status",
    "agents.planner.box",
]


def _make_async_client():
    """Create a MagicMock that works as an async context manager."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _make_session():
    """Create a mock session object with a .client attribute."""
    session = MagicMock()
    session.client = _make_async_client()
    return session


def _make_scanner(*, raises=None):
    """Return (scanner_instance, scanner_class_mock).

    If *raises* is set, ``scanner.scan`` will raise that exception.
    """
    scanner = MagicMock()
    if raises:
        scanner.scan.side_effect = raises
    else:
        scan_result = MagicMock()
        scan_result.should_block = False
        scan_result.should_warn = False
        scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
        scanner.scan.return_value = scan_result
        scanner.format_summary.return_value = "No issues"
    cls_mock = MagicMock(return_value=scanner)
    return scanner, cls_mock


@contextmanager
def planner_mocks(*, session_result=None, extra_patches=None):
    """Context manager that patches all common planner dependencies.

    Yields a namespace-like dict with the important mocks so tests can
    customise or assert against them.

    Parameters
    ----------
    session_result : tuple | None
        The 4-tuple returned by ``run_agent_session``.  Defaults to a
        successful session with token metadata.
    extra_patches : list[str] | None
        Additional ``agents.planner.*`` names to patch (e.g.
        ``["save_token_stats", "ImplementationPlan"]``).
    """
    if session_result is None:
        session_result = (
            "success",
            "Planning completed",
            {"input_tokens": 100, "output_tokens": 50},
            None,
        )

    extra_patches = extra_patches or []
    all_patches = _PATCHES + [f"agents.planner.{n}" for n in extra_patches]

    with (
        patch("agents.planner.create_planner_session") as mock_create_session,
        patch("agents.planner.get_followup_planner_prompt") as mock_prompt,
        patch(
            "agents.planner.run_agent_session", new_callable=AsyncMock
        ) as mock_session,
        patch("agents.planner.PreventionScanner") as mock_scanner_cls,
    ):
        # Stack extra patches
        extra_mocks = {}
        import contextlib

        stack = contextlib.ExitStack()
        for name in all_patches:
            extra_mocks[name.split(".")[-1]] = stack.enter_context(patch(name))

        with stack:
            mock_create_session.return_value = _make_session()
            mock_prompt.return_value = "Test prompt"
            mock_session.return_value = session_result

            scanner, _ = _make_scanner()
            mock_scanner_cls.return_value = scanner

            yield {
                "create_session": mock_create_session,
                "prompt": mock_prompt,
                "session": mock_session,
                "scanner_cls": mock_scanner_cls,
                "scanner": scanner,
                **extra_mocks,
            }


async def _run(tmp_path, *, plan_data=None, verbose=False, **mock_kw):
    """Scaffold directories, patch deps, and run ``run_followup_planner``.

    Returns ``(result, mocks)`` so the caller can assert on both.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir(exist_ok=True)
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir(exist_ok=True)

    if plan_data is not None:
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan_data))

    (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

    with planner_mocks(**mock_kw) as mocks:
        result = await run_followup_planner(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model="claude-3-5-sonnet-20241022",
            verbose=verbose,
        )
    return result, mocks


_EMPTY_PLAN = {"feature": "Test Feature", "status": "completed", "phases": []}
_SUCCESS_SESSION = (
    "success",
    "Planning completed",
    {"input_tokens": 100, "output_tokens": 50},
    None,
)
_ERROR_SESSION = ("error", "Error", {}, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunFollowupPlanner:
    """Test run_followup_planner function."""

    @pytest.mark.asyncio
    async def test_requires_spec_dir(self, tmp_path):
        """Test that run_followup_planner calls create_planner_session and prompt."""
        _, mocks = await _run(tmp_path, plan_data=_EMPTY_PLAN)
        assert mocks["create_session"].called
        assert mocks["prompt"].called

    @pytest.mark.asyncio
    async def test_handles_session_error(self, tmp_path):
        """Test that run_followup_planner handles session errors gracefully."""
        result, _ = await _run(
            tmp_path,
            plan_data=_EMPTY_PLAN,
            session_result=("error", "Planning failed", {}, None),
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_verifies_pending_subtasks(self, tmp_path):
        """Test that run_followup_planner verifies pending subtasks were added."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_data = {
            "feature": "Test Feature",
            "status": "completed",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Task 1",
                            "status": "completed",
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan_data))
        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        with planner_mocks(
            extra_patches=["save_token_stats", "ImplementationPlan"]
        ) as mocks:
            # Mock plan with new pending subtask
            mock_plan = MagicMock()
            mock_subtask = MagicMock()
            mock_subtask.status.value = "pending"
            mock_phase = MagicMock(subtasks=[mock_subtask])
            mock_plan.phases = [mock_phase]
            mock_plan.reset_for_followup = MagicMock()
            mock_plan.async_save = AsyncMock()
            mocks["ImplementationPlan"].load.return_value = mock_plan

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

        assert result is True
        mock_plan.reset_for_followup.assert_called_once()

    @pytest.mark.asyncio
    async def test_warns_when_no_pending_subtasks(self, tmp_path):
        """Test warning when no pending subtasks are added."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "implementation_plan.json").write_text(json.dumps(_EMPTY_PLAN))
        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        with planner_mocks(
            extra_patches=["save_token_stats", "ImplementationPlan"]
        ) as mocks:
            mock_plan = MagicMock()
            mock_subtask = MagicMock()
            mock_subtask.status.value = "completed"
            mock_plan.phases = [MagicMock(subtasks=[mock_subtask])]
            mocks["ImplementationPlan"].load.return_value = mock_plan

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_missing_plan_file(self, tmp_path):
        """Test handling of missing implementation_plan.json."""
        result, _ = await _run(tmp_path, plan_data=None)
        # No plan written → should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_runs_prevention_scanner(self, tmp_path):
        """Test that prevention scanner is run during planning."""
        _, mocks = await _run(
            tmp_path,
            plan_data=_EMPTY_PLAN,
            session_result=_ERROR_SESSION,
        )
        mocks["scanner"].scan.assert_called_once()
        mocks["scanner"].format_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_scanner_error(self, tmp_path):
        """Test that scanner errors don't block planning."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "implementation_plan.json").write_text(json.dumps(_EMPTY_PLAN))
        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add feature")

        with planner_mocks(session_result=_ERROR_SESSION) as mocks:
            # Override scanner to raise
            mocks["scanner"].scan.side_effect = Exception("Scanner error")

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

        assert isinstance(result, bool)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_with_verbose_mode(self, tmp_path):
        """Test that verbose mode is passed through correctly."""
        _, mocks = await _run(
            tmp_path,
            plan_data=_EMPTY_PLAN,
            session_result=_ERROR_SESSION,
            verbose=True,
        )
        assert mocks["session"].call_args is not None
