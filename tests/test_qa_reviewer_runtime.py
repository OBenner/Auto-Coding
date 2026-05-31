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
