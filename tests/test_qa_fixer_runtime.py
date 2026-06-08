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
import types
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


# ---------------------------------------------------------------------------
# Recovery / model-fallback loop (run_qa_fixer_runtime_session) — Claude parity
# ---------------------------------------------------------------------------


class _FakeRecoveryManager:
    """A RecoveryManager that hands out scripted recovery actions."""

    def __init__(self, *, action_script):
        self._script = list(action_script)
        self.outcomes: list[bool] = []

    def record_attempt(self, *a, **k):
        pass

    def record_outcome(self, *a, **k):
        self.outcomes.append(bool(k.get("success")))

    def record_recovery_notification(self, *a, **k):
        pass

    def mark_subtask_stuck(self, *a, **k):
        pass

    def rollback_to_commit(self, *a, **k):
        return True

    def classify_failure(self, *a, **k):
        return "transient_error"

    def determine_recovery_action(self, *a, **k):
        return self._script.pop(0)


def _recovery_action(
    action,
    *,
    wait_seconds=0.0,
    target=None,
    use_model_fallback=False,
    strategy=None,
    reason="reason",
):
    return types.SimpleNamespace(
        action=action,
        wait_seconds=wait_seconds,
        target=target,
        use_model_fallback=use_model_fallback,
        strategy=strategy,
        reason=reason,
    )


@pytest.mark.asyncio
async def test_runtime_fixer_recovers_via_model_fallback(tmp_path):
    """A failed attempt retries on the next model in the fallback chain."""
    from qa import fixer

    built_models: list[str] = []

    def fake_build(*, provider_name, runtime_mode, model, project_dir, fix_session):
        built_models.append(model)
        return MagicMock()

    via = AsyncMock(side_effect=[("error", "boom"), ("fixed", "done")])
    fake_rm = _FakeRecoveryManager(
        action_script=[_recovery_action("retry", use_model_fallback=True)]
    )

    with (
        patch("qa.fixer._build_qa_fixer_runtime_session", side_effect=fake_build),
        patch("qa.fixer.run_qa_fixer_via_runtime", new=via),
        patch("qa.fixer.RecoveryManager", return_value=fake_rm),
    ):
        status, response = await fixer.run_qa_fixer_runtime_session(
            provider_name="openai",
            runtime_mode="generic_edit",
            model="gpt-5.2",
            project_dir=tmp_path,
            spec_dir=tmp_path,
            fix_session=1,
        )

    assert status == "fixed"
    assert response == "done"
    # Second attempt rebuilt the session with the next model in the chain.
    assert built_models == ["gpt-5.2", "gpt-5"]
    assert via.await_count == 2
    assert fake_rm.outcomes == [True]


@pytest.mark.asyncio
async def test_runtime_fixer_threads_recovery_guidance_into_next_attempt(tmp_path):
    """Strategy guidance from a retry action is passed into the next prompt."""
    from qa import fixer

    via = AsyncMock(side_effect=[("error", "boom"), ("fixed", "done")])
    strategy = types.SimpleNamespace(guidance="TRY HARDER", description="d")
    fake_rm = _FakeRecoveryManager(
        action_script=[_recovery_action("retry", strategy=strategy)]
    )

    with (
        patch("qa.fixer._build_qa_fixer_runtime_session", return_value=MagicMock()),
        patch("qa.fixer.run_qa_fixer_via_runtime", new=via),
        patch("qa.fixer.RecoveryManager", return_value=fake_rm),
    ):
        await fixer.run_qa_fixer_runtime_session(
            provider_name="openai",
            runtime_mode="generic_edit",
            model="gpt-5.2",
            project_dir=tmp_path,
            spec_dir=tmp_path,
            fix_session=1,
        )

    # First attempt: no guidance; second attempt: guidance threaded in.
    assert via.await_args_list[0].kwargs["recovery_guidance"] is None
    assert via.await_args_list[1].kwargs["recovery_guidance"] == "TRY HARDER"


@pytest.mark.asyncio
async def test_runtime_fixer_escalates_when_recovery_exhausted(tmp_path):
    """An escalate action returns ('escalate', reason) for the dead-letter queue."""
    from qa import fixer

    via = AsyncMock(return_value=("error", "boom"))
    fake_rm = _FakeRecoveryManager(
        action_script=[_recovery_action("escalate", reason="dead-letter")]
    )

    with (
        patch("qa.fixer._build_qa_fixer_runtime_session", return_value=MagicMock()),
        patch("qa.fixer.run_qa_fixer_via_runtime", new=via),
        patch("qa.fixer.RecoveryManager", return_value=fake_rm),
    ):
        status, response = await fixer.run_qa_fixer_runtime_session(
            provider_name="openai",
            runtime_mode="generic_edit",
            model="gpt-5.2",
            project_dir=tmp_path,
            spec_dir=tmp_path,
            fix_session=1,
        )

    assert status == "escalate"
    assert response == "dead-letter"
    assert via.await_count == 1
    assert fake_rm.outcomes == [False]


@pytest.mark.asyncio
async def test_runtime_fixer_marks_stuck_on_skip(tmp_path):
    """A skip action returns ('stuck', ...) and records a failed outcome."""
    from qa import fixer

    via = AsyncMock(return_value=("error", "boom"))
    fake_rm = _FakeRecoveryManager(
        action_script=[_recovery_action("skip", reason="circular_fix")]
    )

    with (
        patch("qa.fixer._build_qa_fixer_runtime_session", return_value=MagicMock()),
        patch("qa.fixer.run_qa_fixer_via_runtime", new=via),
        patch("qa.fixer.RecoveryManager", return_value=fake_rm),
    ):
        status, response = await fixer.run_qa_fixer_runtime_session(
            provider_name="openai",
            runtime_mode="generic_edit",
            model="gpt-5.2",
            project_dir=tmp_path,
            spec_dir=tmp_path,
            fix_session=1,
        )

    assert status == "stuck"
    assert "circular_fix" in response
    assert fake_rm.outcomes == [False]
