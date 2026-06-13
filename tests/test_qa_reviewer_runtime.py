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
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qa.reviewer import (
    build_qa_reviewer_prompt,
    merge_runtime_qa_signoff_artifact,
    run_qa_reviewer_via_runtime,
)


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


# =============================================================================
# Runtime sign-off instructions (direct-API addendum)
# =============================================================================


def test_build_qa_reviewer_prompt_runtime_addendum_uses_generic_edit_contract():
    """The runtime addendum overrides Claude tool/path guidance with the
    generic_edit contract: write_file, workspace-relative paths, qa_signoff.json.
    """
    prompt = build_qa_reviewer_prompt(
        base_prompt="BASE",
        qa_memory_context=None,
        coverage_summary="CS",
        coverage_data=None,
        coverage_passed=True,
        spec_dir=Path("/abs/spec"),
        qa_session=1,
        max_iterations=50,
        previous_error=None,
        runtime_signoff_relspec=".auto-claude/specs/001-demo",
    )

    assert "RUNTIME EXECUTION MODE" in prompt
    assert "OVERRIDE" in prompt
    assert "write_file" in prompt
    # The model is pointed at the workspace-relative verdict file, not the plan.
    assert ".auto-claude/specs/001-demo/qa_signoff.json" in prompt
    assert ".auto-claude/specs/001-demo/spec.md" in prompt
    # Absolute paths are rejected by the runtime; none must leak in.
    assert "/abs/spec/qa_signoff.json" not in prompt


def test_build_qa_reviewer_prompt_no_runtime_addendum_by_default():
    """The Claude SDK path (no relspec) is unchanged — no runtime addendum."""
    prompt = build_qa_reviewer_prompt(
        base_prompt="BASE",
        qa_memory_context=None,
        coverage_summary="CS",
        coverage_data=None,
        coverage_passed=True,
        spec_dir=Path("/abs/spec"),
        qa_session=1,
        max_iterations=50,
        previous_error=None,
    )

    assert "RUNTIME EXECUTION MODE" not in prompt
    assert "qa_signoff.json" not in prompt


# =============================================================================
# merge_runtime_qa_signoff_artifact (deterministic Python persistence)
# =============================================================================


def _write_plan(spec_dir: Path, signoff=None) -> Path:
    plan = spec_dir / "implementation_plan.json"
    plan.write_text(json.dumps({"qa_signoff": signoff}), encoding="utf-8")
    return plan


def test_merge_runtime_qa_signoff_artifact_approved(tmp_path):
    plan = _write_plan(tmp_path)
    (tmp_path / "qa_signoff.json").write_text(
        json.dumps(
            {
                "status": "approved",
                "tests_passed": {"unit": "2/2"},
                "coverage_passed": True,
            }
        ),
        encoding="utf-8",
    )

    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=7) is True

    signoff = json.loads(plan.read_text())["qa_signoff"]
    assert signoff["status"] == "approved"
    assert signoff["qa_session"] == 7
    assert signoff["tests_passed"] == {"unit": "2/2"}
    assert signoff["coverage_passed"] is True
    assert signoff["verified_by"] == "qa_agent_runtime"
    assert "timestamp" in signoff


def test_merge_runtime_qa_signoff_artifact_rejected_carries_issues(tmp_path):
    plan = _write_plan(tmp_path)
    (tmp_path / "qa_signoff.json").write_text(
        json.dumps(
            {
                "status": "rejected",
                "issues_found": [
                    {"type": "critical", "title": "bug", "location": "a.py:1"}
                ],
            }
        ),
        encoding="utf-8",
    )

    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=3) is True

    signoff = json.loads(plan.read_text())["qa_signoff"]
    assert signoff["status"] == "rejected"
    assert signoff["issues_found"][0]["title"] == "bug"
    assert signoff["fix_request_file"] == "QA_FIX_REQUEST.md"


def test_merge_runtime_qa_signoff_artifact_missing_file(tmp_path):
    _write_plan(tmp_path)
    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=1) is False


@pytest.mark.parametrize(
    "contents",
    ['{"status": "maybe"}', "{ not json", '["not", "an", "object"]'],
)
def test_merge_runtime_qa_signoff_artifact_rejects_bad_payloads(tmp_path, contents):
    plan = _write_plan(tmp_path)
    (tmp_path / "qa_signoff.json").write_text(contents, encoding="utf-8")

    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=1) is False
    # The plan's signoff is left untouched on a bad payload.
    assert json.loads(plan.read_text())["qa_signoff"] is None


# =============================================================================
# End-to-end: a scripted runtime session writes a verdict, the reviewer reads it
# =============================================================================


def _patch_reviewer_io():
    """Patch the reviewer's side-effecting deps but NOT get_qa_signoff_status,
    so the verdict is read back from the real implementation_plan.json.
    """
    return [
        patch("qa.reviewer.run_coverage_validation", return_value=(True, "cov", None)),
        patch("qa.reviewer.get_graphiti_context", new=AsyncMock(return_value="")),
        patch("qa.reviewer.get_qa_reviewer_prompt", return_value="PROMPT"),
        patch("qa.reviewer.save_session_memory", new=AsyncMock(return_value=None)),
    ]


def _scripted_runtime_session(write_fn):
    """An AsyncMock for run_runtime_session whose side effect simulates the
    model's writes (into the spec_dir it is handed), then returns a result.
    """

    async def _run(*args, **kwargs):
        write_fn(kwargs["spec_dir"])
        result = MagicMock()
        result.response_text = "reviewed"
        return result

    return AsyncMock(side_effect=_run)


@pytest.mark.asyncio
async def test_runtime_reviewer_reads_back_direct_plan_signoff(tmp_path):
    """A model that edits implementation_plan.json directly is honored."""
    _write_plan(tmp_path)

    def write_plan(spec_dir: Path) -> None:
        plan_file = spec_dir / "implementation_plan.json"
        plan = json.loads(plan_file.read_text())
        plan["qa_signoff"] = {"status": "approved", "tests_passed": {"unit": "3/3"}}
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

    with contextlib.ExitStack() as stack:
        for patcher in _patch_reviewer_io():
            stack.enter_context(patcher)
        stack.enter_context(
            patch(
                "agents.runtime.run_runtime_session",
                new=_scripted_runtime_session(write_plan),
            )
        )
        status, response = await run_qa_reviewer_via_runtime(
            MagicMock(), tmp_path, tmp_path, qa_session=1, max_iterations=50
        )

    assert status == "approved"
    assert response == "reviewed"


@pytest.mark.asyncio
async def test_runtime_reviewer_merges_side_file_signoff(tmp_path):
    """A direct-API model that drops qa_signoff.json gets it merged into the
    plan and read back as the official verdict.
    """
    plan = _write_plan(tmp_path)

    def write_side_file(spec_dir: Path) -> None:
        (spec_dir / "qa_signoff.json").write_text(
            json.dumps(
                {
                    "status": "rejected",
                    "issues_found": [
                        {
                            "type": "critical",
                            "title": "missing validation",
                            "location": "auth.py:42",
                            "fix_required": "validate input",
                        }
                    ],
                    "coverage_passed": False,
                }
            ),
            encoding="utf-8",
        )

    with contextlib.ExitStack() as stack:
        for patcher in _patch_reviewer_io():
            stack.enter_context(patcher)
        stack.enter_context(
            patch(
                "agents.runtime.run_runtime_session",
                new=_scripted_runtime_session(write_side_file),
            )
        )
        status, _ = await run_qa_reviewer_via_runtime(
            MagicMock(), tmp_path, tmp_path, qa_session=4, max_iterations=50
        )

    assert status == "rejected"
    merged = json.loads(plan.read_text())["qa_signoff"]
    assert merged["status"] == "rejected"
    assert merged["qa_session"] == 4
    assert merged["issues_found"][0]["location"] == "auth.py:42"
    assert merged["fix_request_file"] == "QA_FIX_REQUEST.md"


@pytest.mark.asyncio
async def test_runtime_reviewer_errors_when_no_verdict_written(tmp_path):
    """No plan edit and no qa_signoff.json -> the reviewer reports an error so
    the QA loop retries with self-correction context.
    """
    _write_plan(tmp_path)

    with contextlib.ExitStack() as stack:
        for patcher in _patch_reviewer_io():
            stack.enter_context(patcher)
        stack.enter_context(
            patch(
                "agents.runtime.run_runtime_session",
                new=_scripted_runtime_session(lambda spec_dir: None),
            )
        )
        status, _ = await run_qa_reviewer_via_runtime(
            MagicMock(), tmp_path, tmp_path, qa_session=1, max_iterations=50
        )

    assert status == "error"
