"""qa_reviewer on the provider-neutral runtime layer.

Covers the shared prompt builder (`build_qa_reviewer_prompt`) and the
runtime-adapter execution path (`run_qa_reviewer_via_runtime`) that lets a
direct-API provider run the read-only QA reviewer through
`run_runtime_session` instead of the Claude SDK client. The QA verdict is
file-based (`qa_signoff` in implementation_plan.json), so the same prompt
yields the same approved/rejected/error contract on any provider.
"""

from __future__ import annotations

import contextlib
import json
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qa.reviewer import build_qa_reviewer_prompt, run_qa_reviewer_via_runtime


def test_build_qa_reviewer_prompt_passed_case():
    prompt = build_qa_reviewer_prompt(
        base_prompt="BASE_PROMPT",
        qa_memory_context="MEMORY_CTX",
        coverage_summary="COVERAGE_SUMMARY",
        coverage_data={"passed": True, "total_coverage": 91.2},
        coverage_passed=True,
        spec_dir=Path("/spec"),
        qa_session=2,
        max_iterations=50,
        previous_error=None,
    )

    assert "BASE_PROMPT" in prompt
    assert "MEMORY_CTX" in prompt
    assert "COVERAGE_SUMMARY" in prompt
    assert "## Test Coverage Validation" in prompt
    assert "Coverage validation passed" in prompt
    assert "**QA Session**: 2" in prompt
    assert "**Max Iterations**: 50" in prompt
    assert "total_coverage" in prompt  # coverage_data embedded as JSON
    assert "SELF-CORRECTION" not in prompt  # no previous_error


def test_build_qa_reviewer_prompt_failure_and_retry_case():
    prompt = build_qa_reviewer_prompt(
        base_prompt="B",
        qa_memory_context=None,
        coverage_summary="CS",
        coverage_data=None,
        coverage_passed=False,
        spec_dir=Path("/spec"),
        qa_session=5,
        max_iterations=50,
        previous_error={"error_message": "no signoff written", "consecutive_errors": 2},
    )

    assert "Coverage validation failed" in prompt
    assert "SELF-CORRECTION REQUIRED" in prompt
    assert "no signoff written" in prompt
    assert "attempt 3" in prompt  # consecutive_errors + 1
    assert "MEMORY" not in prompt  # no memory context supplied


def _patch_reviewer_runtime(*, signoff: dict | None, response_text: str = "reviewed"):
    """Patch every external dependency of run_qa_reviewer_via_runtime.

    ``get_qa_signoff_status`` is patched at its source module because the
    reviewer imports it lazily (``from .criteria import ...``) to avoid a
    qa.criteria -> qa.reviewer import cycle. ``save_session_memory`` is
    patched so the verdict path's Graphiti persistence does not touch a
    real memory backend.
    """
    fake_result = MagicMock()
    fake_result.response_text = response_text
    return [
        patch("qa.reviewer.run_coverage_validation", return_value=(True, "cov", None)),
        patch("qa.reviewer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.reviewer.get_qa_reviewer_prompt", return_value="PROMPT"),
        patch("qa.reviewer.save_session_memory", new=AsyncMock(return_value=None)),
        patch(
            "agents.runtime.run_runtime_session",
            new=AsyncMock(return_value=fake_result),
        ),
        patch("qa.criteria.get_qa_signoff_status", return_value=signoff),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "signoff,expected",
    [
        ({"status": "approved"}, "approved"),
        ({"status": "rejected", "issues_found": []}, "rejected"),
        (None, "error"),
        ({"status": "weird"}, "error"),
    ],
)
async def test_run_qa_reviewer_via_runtime_verdict(tmp_path, signoff, expected):
    with contextlib.ExitStack() as stack:
        for patcher in _patch_reviewer_runtime(signoff=signoff):
            stack.enter_context(patcher)
        status, response = await run_qa_reviewer_via_runtime(
            MagicMock(),
            tmp_path,
            tmp_path,
            qa_session=1,
            max_iterations=50,
        )

    assert status == expected
    if expected in {"approved", "rejected"}:
        assert response == "reviewed"


@pytest.mark.asyncio
async def test_run_qa_reviewer_via_runtime_drives_runtime_session(tmp_path):
    """The reviewer runs through run_runtime_session, not a Claude client."""
    fake_result = MagicMock()
    fake_result.response_text = "ok"
    run_session = AsyncMock(return_value=fake_result)

    with (
        patch("qa.reviewer.run_coverage_validation", return_value=(True, "cov", None)),
        patch("qa.reviewer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.reviewer.get_qa_reviewer_prompt", return_value="PROMPT"),
        patch("qa.reviewer.save_session_memory", new=AsyncMock(return_value=None)),
        patch("agents.runtime.run_runtime_session", new=run_session),
        patch("qa.criteria.get_qa_signoff_status", return_value={"status": "approved"}),
    ):
        runtime_session = MagicMock()
        await run_qa_reviewer_via_runtime(
            runtime_session, tmp_path, tmp_path, qa_session=3, max_iterations=50
        )

    run_session.assert_awaited_once()
    args, kwargs = run_session.call_args
    assert args[0] is runtime_session
    # The reviewer drives the runtime with the fully assembled prompt
    # (base reviewer prompt + coverage + session context), not the bare base.
    assert kwargs["message"].startswith("PROMPT")
    assert "**QA Session**: 3" in kwargs["message"]
    assert kwargs["spec_dir"] == tmp_path


# ---------------------------------------------------------------------------
# Runtime status-write override (build_qa_reviewer_prompt addendum)
# ---------------------------------------------------------------------------


def test_build_qa_reviewer_prompt_no_runtime_addendum_by_default():
    """Without runtime_status_relspec the prompt keeps the Claude contract."""
    prompt = build_qa_reviewer_prompt(
        base_prompt="B",
        qa_memory_context=None,
        coverage_summary="CS",
        coverage_data=None,
        coverage_passed=True,
        spec_dir=Path("/proj/.auto-claude/specs/001-x"),
        qa_session=1,
        max_iterations=50,
        previous_error=None,
    )

    assert "qa_status.json" not in prompt
    assert "RUNTIME EXECUTION OVERRIDE" not in prompt


def test_build_qa_reviewer_prompt_runtime_addendum_overrides_claude_guidance():
    """The runtime addendum redirects the verdict to qa_status.json.

    On generic_edit the Claude Write/Edit tools and absolute paths don't exist,
    so the addendum must (a) forbid the direct implementation_plan.json edit,
    (b) point at write_file with a workspace-relative path, and (c) spell out
    the richer approved/rejected + issues_found verdict the merge step reads.
    """
    prompt = build_qa_reviewer_prompt(
        base_prompt="B",
        qa_memory_context=None,
        coverage_summary="CS",
        coverage_data=None,
        coverage_passed=True,
        spec_dir=Path("/proj/.auto-claude/specs/001-x"),
        qa_session=7,
        max_iterations=50,
        previous_error=None,
        runtime_status_relspec=".auto-claude/specs/001-x",
    )

    assert "RUNTIME EXECUTION OVERRIDE" in prompt
    assert "write_file" in prompt
    # Workspace-relative status artifact path, not an absolute path.
    assert ".auto-claude/specs/001-x/qa_status.json" in prompt
    assert "/proj/.auto-claude/specs/001-x/qa_status.json" not in prompt
    # The reviewer verdict is richer than the fixer's single flag: both
    # outcomes plus the issue list the fixer reads back.
    assert '"status": "approved"' in prompt
    assert '"status": "rejected"' in prompt
    assert '"qa_session": 7' in prompt
    assert "issues_found" in prompt


def test_runtime_addendum_follows_and_overrides_self_correction_block():
    """The exact bug scenario: the addendum must come AFTER (and so win over)
    the previous_error self-correction block, which tells the model to edit
    implementation_plan.json with Claude Write/Edit and an absolute path.
    """
    prompt = build_qa_reviewer_prompt(
        base_prompt="B",
        qa_memory_context=None,
        coverage_summary="CS",
        coverage_data=None,
        coverage_passed=False,
        spec_dir=Path("/proj/.auto-claude/specs/001-x"),
        qa_session=3,
        max_iterations=50,
        previous_error={"error_message": "no signoff", "consecutive_errors": 1},
        runtime_status_relspec=".auto-claude/specs/001-x",
    )

    assert "SELF-CORRECTION REQUIRED" in prompt
    assert "RUNTIME EXECUTION OVERRIDE" in prompt
    assert prompt.index("RUNTIME EXECUTION OVERRIDE") > prompt.index(
        "SELF-CORRECTION REQUIRED"
    )
    assert ".auto-claude/specs/001-x/qa_status.json" in prompt


# ---------------------------------------------------------------------------
# qa_status.json artifact merge (the status-persistence bug fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["approved", "rejected"])
async def test_run_qa_reviewer_via_runtime_merges_qa_status_artifact(tmp_path, verdict):
    """generic_edit writes qa_status.json -> merged into qa_signoff -> verdict.

    This is the bug being fixed: on a direct-API provider the reviewer can't
    edit implementation_plan.json's qa_signoff (no Write/Edit tool, absolute
    paths rejected). It drops a workspace-relative qa_status.json instead, and
    the orchestrator folds that into qa_signoff so get_qa_signoff_status reads
    the verdict — without this, QA on e.g. OpenAI never records approved/
    rejected and returns "error". Uses the REAL get_qa_signoff_status /
    load+save implementation plan (only the runtime session, coverage, and
    memory are faked).
    """
    # Pre-review state: a signoff with no usable verdict yet.
    (tmp_path / "implementation_plan.json").write_text(
        json.dumps({"qa_signoff": {"status": "pending", "qa_session": 1}}),
        encoding="utf-8",
    )

    artifact = {"status": verdict, "qa_session": 2}
    if verdict == "rejected":
        artifact["issues_found"] = [
            {
                "type": "critical",
                "title": "boom",
                "location": "a.py:1",
                "fix_required": "fix it",
            }
        ]

    async def fake_run_session(
        runtime_session, *, message, spec_dir, verbose=False, requirements=None
    ):
        # Mirror the generic_edit reviewer: write the status artifact rather
        # than editing implementation_plan.json directly.
        (spec_dir / "qa_status.json").write_text(
            json.dumps(artifact), encoding="utf-8"
        )
        return types.SimpleNamespace(response_text="done")

    with (
        patch("qa.reviewer.run_coverage_validation", return_value=(True, "cov", None)),
        patch("qa.reviewer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.reviewer.get_qa_reviewer_prompt", return_value="PROMPT"),
        patch("qa.reviewer.save_session_memory", new=AsyncMock(return_value=None)),
        patch("agents.runtime.run_runtime_session", new=fake_run_session),
    ):
        status, response = await run_qa_reviewer_via_runtime(
            MagicMock(), tmp_path, tmp_path, qa_session=2, max_iterations=50
        )

    assert status == verdict
    assert response == "done"
    # The artifact was deterministically folded into qa_signoff.
    plan = json.loads((tmp_path / "implementation_plan.json").read_text())
    signoff = plan["qa_signoff"]
    assert signoff["status"] == verdict
    assert signoff["qa_session"] == 2  # carried forward from the artifact
    if verdict == "rejected":
        assert signoff["issues_found"][0]["title"] == "boom"


@pytest.mark.asyncio
async def test_run_qa_reviewer_via_runtime_no_artifact_stays_error(tmp_path):
    """No qa_status.json and no plan verdict => still 'error' (loop must not pass)."""
    (tmp_path / "implementation_plan.json").write_text(
        json.dumps({"qa_signoff": {"status": "pending"}}), encoding="utf-8"
    )

    async def fake_run_session(runtime_session, **kwargs):
        return types.SimpleNamespace(response_text="did nothing")

    with (
        patch("qa.reviewer.run_coverage_validation", return_value=(True, "cov", None)),
        patch("qa.reviewer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.reviewer.get_qa_reviewer_prompt", return_value="PROMPT"),
        patch("qa.reviewer.save_session_memory", new=AsyncMock(return_value=None)),
        patch("agents.runtime.run_runtime_session", new=fake_run_session),
    ):
        status, _ = await run_qa_reviewer_via_runtime(
            MagicMock(), tmp_path, tmp_path, qa_session=1, max_iterations=50
        )

    assert status == "error"
    plan = json.loads((tmp_path / "implementation_plan.json").read_text())
    assert plan["qa_signoff"]["status"] == "pending"  # untouched


# ---------------------------------------------------------------------------
# Same-loop async session close (no leaked AsyncOpenAI connection pools)
# ---------------------------------------------------------------------------


class _AsyncClosableSession:
    def __init__(self):
        self.aclose_calls = 0

    async def aclose(self):
        self.aclose_calls += 1


class _RuntimeWithSession:
    def __init__(self):
        self.agent_session = _AsyncClosableSession()


@pytest.mark.asyncio
async def test_run_qa_reviewer_runtime_session_acloses_session(tmp_path):
    """The reviewer's single-pass runtime session is async-closed in the loop."""
    from qa import reviewer

    runtime = _RuntimeWithSession()
    fake_config = MagicMock()
    fake_config.provider = "openai"
    fake_config.coherent_session_model.return_value = "gpt-5.2"
    fake_provider = MagicMock()
    fake_provider.create_session.return_value = MagicMock()
    via = AsyncMock(return_value=("approved", "ok"))

    with (
        patch("qa.reviewer.ProviderConfig.from_env", return_value=fake_config),
        patch("qa.reviewer.create_engine_provider", return_value=fake_provider),
        patch("agents.runtime.create_runtime_session", return_value=runtime),
        patch("qa.reviewer.run_qa_reviewer_via_runtime", new=via),
    ):
        status, response = await reviewer.run_qa_reviewer_runtime_session(
            provider_name="openai",
            runtime_mode="generic_edit",
            model="gpt-5.2",
            project_dir=tmp_path,
            spec_dir=tmp_path,
            qa_session=1,
            max_iterations=50,
        )

    assert status == "approved"
    assert response == "ok"
    via.assert_awaited_once()
    # The provider session was async-closed exactly once (the finally runs even
    # though run_qa_reviewer_via_runtime returned successfully).
    assert runtime.agent_session.aclose_calls == 1


@pytest.mark.asyncio
async def test_aclose_agent_session_falls_back_to_sync_close():
    """A session exposing only a sync close() is still closed."""
    from qa.reviewer import _aclose_agent_session

    class _SyncOnlySession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class _Runtime:
        def __init__(self):
            self.agent_session = _SyncOnlySession()

    runtime = _Runtime()
    await _aclose_agent_session(runtime)
    assert runtime.agent_session.closed is True


@pytest.mark.asyncio
async def test_aclose_agent_session_swallows_errors():
    """Cleanup must never raise — a failing aclose is logged and absorbed."""
    from qa.reviewer import _aclose_agent_session

    class _BoomSession:
        async def aclose(self):
            raise RuntimeError("close exploded")

    class _Runtime:
        def __init__(self):
            self.agent_session = _BoomSession()

    # Must not raise.
    await _aclose_agent_session(_Runtime())
