"""qa_fixer on the provider-neutral runtime layer.

Covers the shared prompt builder (`build_qa_fixer_prompt`) and the
runtime-adapter execution path (`run_qa_fixer_via_runtime`) that lets a
direct-API provider run the QA fixer through `run_runtime_session` instead
of the Claude SDK client. The fixer mutates source, so the runtime path
relies on generic_edit's mutation snapshots + transaction rollback; success
is the file-based `is_fixes_applied` signal, matching the Claude path.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qa.fixer import build_qa_fixer_prompt, run_qa_fixer_via_runtime


def test_build_qa_fixer_prompt_full():
    prompt = build_qa_fixer_prompt(
        base_prompt="FIXER_BASE",
        fixer_memory_context="MEM",
        failure_patterns="FAILURES",
        spec_dir=Path("/proj/.auto-claude/specs/001-x"),
        fix_session=2,
    )

    assert "FIXER_BASE" in prompt
    assert "MEM" in prompt
    assert "FAILURES" in prompt
    assert "**Fix Session**: 2" in prompt
    assert "QA_FIX_REQUEST.md" in prompt
    assert "001-x" in prompt  # spec name


def test_build_qa_fixer_prompt_minimal():
    prompt = build_qa_fixer_prompt(
        base_prompt="B",
        fixer_memory_context=None,
        failure_patterns=None,
        spec_dir=Path("/proj/spec"),
        fix_session=1,
    )

    assert prompt.startswith("B")
    assert "MEM" not in prompt
    assert "**Fix Session**: 1" in prompt


def _patch_fixer_runtime(*, fixes_applied: bool, response_text: str = "fixed-text"):
    """Patch every external dependency of run_qa_fixer_via_runtime."""
    fake_result = MagicMock()
    fake_result.response_text = response_text
    return [
        patch("qa.fixer.load_qa_fixer_prompt", return_value="FIXER_PROMPT"),
        patch("qa.fixer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.fixer.get_failure_patterns", new=AsyncMock(return_value="")),
        patch("qa.fixer.save_session_memory", new=AsyncMock(return_value=None)),
        patch(
            "agents.runtime.run_runtime_session",
            new=AsyncMock(return_value=fake_result),
        ),
        patch("qa.criteria.is_fixes_applied", return_value=fixes_applied),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixes_applied,expected",
    [(True, "fixed"), (False, "error")],
)
async def test_run_qa_fixer_via_runtime_verdict(tmp_path, fixes_applied, expected):
    (tmp_path / "QA_FIX_REQUEST.md").write_text("fix these issues", encoding="utf-8")

    with contextlib.ExitStack() as stack:
        for patcher in _patch_fixer_runtime(fixes_applied=fixes_applied):
            stack.enter_context(patcher)
        status, response = await run_qa_fixer_via_runtime(
            MagicMock(), tmp_path, tmp_path, fix_session=1
        )

    assert status == expected
    if expected == "fixed":
        assert response == "fixed-text"


@pytest.mark.asyncio
async def test_run_qa_fixer_via_runtime_missing_fix_request(tmp_path):
    """No QA_FIX_REQUEST.md => error before any runtime session is built."""
    run_session = AsyncMock()
    with patch("agents.runtime.run_runtime_session", new=run_session):
        status, _ = await run_qa_fixer_via_runtime(
            MagicMock(), tmp_path, tmp_path, fix_session=1
        )

    assert status == "error"
    run_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_qa_fixer_via_runtime_drives_runtime_session(tmp_path):
    """The fixer runs through run_runtime_session with the assembled prompt."""
    (tmp_path / "QA_FIX_REQUEST.md").write_text("fix", encoding="utf-8")
    fake_result = MagicMock()
    fake_result.response_text = "ok"
    run_session = AsyncMock(return_value=fake_result)

    with (
        patch("qa.fixer.load_qa_fixer_prompt", return_value="FIXER_PROMPT"),
        patch("qa.fixer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.fixer.get_failure_patterns", new=AsyncMock(return_value="")),
        patch("qa.fixer.save_session_memory", new=AsyncMock(return_value=None)),
        patch("agents.runtime.run_runtime_session", new=run_session),
        patch("qa.criteria.is_fixes_applied", return_value=True),
    ):
        runtime_session = MagicMock()
        await run_qa_fixer_via_runtime(
            runtime_session, tmp_path, tmp_path, fix_session=4
        )

    run_session.assert_awaited_once()
    args, kwargs = run_session.call_args
    assert args[0] is runtime_session
    assert kwargs["message"].startswith("FIXER_PROMPT")
    assert "**Fix Session**: 4" in kwargs["message"]
    assert kwargs["spec_dir"] == tmp_path
