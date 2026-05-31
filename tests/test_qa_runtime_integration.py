"""QA agents are routed through the runtime layer.

These tests exercise ``qa.loop._resolve_qa_runtime`` directly. They prove
that ``AGENT_PROVIDER_<TYPE>`` and ``AGENT_RUNTIME_MODE_<TYPE>`` env
overrides actually reach a QA phase decision, that a non-Claude or
non-``full_autonomous`` request fails fast with a capability error, that
the default Claude + ``full_autonomous`` path stays unchanged, and that
the resolver always persists a ``runtime_fallback`` diagnostic artifact
for the spec.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest


def _write_passing_openai_history(project_dir: Path) -> None:
    """Write a provider-smoke-history block that satisfies the promotion gate."""
    run_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    history_path = (
        project_dir / ".auto-claude" / "runtime" / "provider-smoke-history.json"
    )
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "providers": {
                    "openai": {
                        "total_runs": 3,
                        "passed_runs": 3,
                        "recent_window": 3,
                        "consecutive_passes": 3,
                        "last_status": "passed",
                        "last_runtime_mode": "provider_e2e",
                        "last_run_at": run_at,
                        "last_reliability_status": "complete",
                        "last_provider_e2e_status": "passed",
                        "last_live_fault_probe_status": "passed",
                        "live_fault_probe_covered_cases": [
                            "unsupported_tools",
                            "gateway_model_limitations",
                        ],
                        "last_live_task_family_status": "passed",
                        "live_task_family_covered_families": [
                            "single_file_edit",
                            "multi_step_edit",
                            "recovery_resume",
                            "transaction_batching",
                        ],
                        "trend": "provider_history_stable",
                        "last_promotion_gate_status": "passed",
                        "promotion_missing_reliability_cases": [],
                        "promotion_missing_e2e_runs": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _import_resolver():
    """Import the resolver after the test fixture monkey-patches env."""
    from agents.runtime.qa_phase_routing import (
        QaRuntimeUnsupportedError,
        resolve_qa_runtime,
    )

    return resolve_qa_runtime, QaRuntimeUnsupportedError


def _clear_qa_env(monkeypatch: pytest.MonkeyPatch, agent_type: str) -> None:
    """Strip every per-agent override that would taint a test case."""
    upper = agent_type.upper()
    for key in (
        f"AGENT_PROVIDER_{upper}",
        f"AGENT_MODEL_{upper}",
        f"AGENT_RUNTIME_MODE_{upper}",
        "AUTO_CODE_RUNTIME_MODE",
        "AUTO_CLAUDE_RUNTIME_MODE",
        "AUTO_CODE_RUNTIME_FALLBACK",
        f"AUTO_CODE_AUTONOMY_{upper}_ALLOWED_PHASES",
        "AUTO_CODE_AUTONOMY_DEFAULT_ALLOWED_PHASES",
        "AUTO_CODE_QA_DIRECT_RUNTIME",
        "AUTO_CODE_AUTONOMY",
        "AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("agent_type", ["qa_reviewer", "qa_fixer"])
def test_default_claude_full_autonomous_passes_silently(
    agent_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Default config (Claude + full_autonomous) keeps existing behavior."""
    _clear_qa_env(monkeypatch, agent_type)
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    resolve_qa_runtime(agent_type=agent_type, spec_dir=tmp_path, qa_iteration=1)

    artifacts = list((tmp_path / "artifacts").glob("runtime_fallback_*.json"))
    assert artifacts, "runtime decision artifact must be persisted"


@pytest.mark.parametrize("agent_type", ["qa_reviewer", "qa_fixer"])
def test_non_claude_provider_fails_fast(
    agent_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """An ``AGENT_PROVIDER_<TYPE>=openai`` override blocks the QA phase."""
    _clear_qa_env(monkeypatch, agent_type)
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv(f"AGENT_PROVIDER_{agent_type.upper()}", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    with pytest.raises(QaRuntimeUnsupportedError) as excinfo:
        resolve_qa_runtime(agent_type=agent_type, spec_dir=tmp_path, qa_iteration=2)

    message = str(excinfo.value)
    assert "openai" in message
    assert agent_type in message
    assert "Phase 1" in message
    assert "non-claude-provider-autonomy" in message
    artifacts = list((tmp_path / "artifacts").glob("runtime_fallback_*.json"))
    assert artifacts, "decision artifact must be written even when blocked"


@pytest.mark.parametrize("agent_type", ["qa_reviewer", "qa_fixer"])
def test_non_full_autonomous_runtime_mode_fails_fast(
    agent_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """A ``generic_edit`` runtime request for QA is rejected too."""
    _clear_qa_env(monkeypatch, agent_type)
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv(f"AGENT_RUNTIME_MODE_{agent_type.upper()}", "generic_edit")
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    with pytest.raises(QaRuntimeUnsupportedError) as excinfo:
        resolve_qa_runtime(agent_type=agent_type, spec_dir=tmp_path, qa_iteration=3)

    assert "generic_edit" in str(excinfo.value)


@pytest.mark.parametrize("agent_type", ["qa_reviewer", "qa_fixer"])
def test_failure_message_carries_policy_snapshot(
    agent_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Operators see the resolved AutonomyPolicy when QA is blocked."""
    _clear_qa_env(monkeypatch, agent_type)
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv(f"AGENT_PROVIDER_{agent_type.upper()}", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS", "7")
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    with pytest.raises(QaRuntimeUnsupportedError) as excinfo:
        resolve_qa_runtime(agent_type=agent_type, spec_dir=tmp_path, qa_iteration=4)

    message = str(excinfo.value)
    assert "min_stable_runs" in message
    assert "'min_stable_runs': 7" in message


@pytest.mark.parametrize("agent_type", ["qa_reviewer", "qa_fixer"])
def test_policy_allowed_phases_override_does_not_unblock_execution(
    agent_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """``AUTO_CODE_AUTONOMY_<PROVIDER>_ALLOWED_PHASES`` alone cannot bypass
    the Claude SDK requirement: capability work in Phase 1 must land first.
    """
    _clear_qa_env(monkeypatch, agent_type)
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv(f"AGENT_PROVIDER_{agent_type.upper()}", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AUTO_CODE_AUTONOMY_OPENAI_ALLOWED_PHASES", "coding,qa_fixing")
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    with pytest.raises(QaRuntimeUnsupportedError):
        resolve_qa_runtime(agent_type=agent_type, spec_dir=tmp_path, qa_iteration=5)


@pytest.mark.parametrize("agent_type", ["qa_reviewer", "qa_fixer"])
def test_direct_runtime_opt_in_without_promotion_fails_fast(
    agent_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Opt-in alone does not unblock QA: the promotion gate must pass too.

    For qa_reviewer the permit branch runs but the gate is unsatisfied (no
    history); for qa_fixer the agent is not portable at all. Both block.
    """
    _clear_qa_env(monkeypatch, agent_type)
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv(f"AGENT_PROVIDER_{agent_type.upper()}", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.setenv("AUTO_CODE_QA_DIRECT_RUNTIME", "true")
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    with pytest.raises(QaRuntimeUnsupportedError):
        resolve_qa_runtime(
            agent_type=agent_type,
            spec_dir=tmp_path,
            qa_iteration=1,
            project_dir=tmp_path,
        )


def test_qa_reviewer_promoted_opt_in_uses_runtime_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """qa_reviewer + opt-in + a promoted provider routes to the runtime layer."""
    _clear_qa_env(monkeypatch, "qa_reviewer")
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv("AGENT_PROVIDER_QA_REVIEWER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.setenv("AUTO_CODE_QA_DIRECT_RUNTIME", "true")
    _write_passing_openai_history(tmp_path)
    resolve_qa_runtime, _ = _import_resolver()

    decision = resolve_qa_runtime(
        agent_type="qa_reviewer",
        spec_dir=tmp_path,
        qa_iteration=1,
        project_dir=tmp_path,
    )

    assert decision.use_runtime_layer is True
    assert decision.provider_name == "openai"
    assert decision.runtime_mode == "generic_edit"


def test_qa_fixer_promoted_opt_in_uses_runtime_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """qa_fixer + opt-in + a promoted provider routes to the runtime layer.

    The fixer mutates source, but generic_edit confines it (mutation
    snapshots + transaction rollback + sandbox), so it is gated identically
    to the reviewer on opt-in + promotion.
    """
    _clear_qa_env(monkeypatch, "qa_fixer")
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    monkeypatch.setenv("AGENT_PROVIDER_QA_FIXER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.setenv("AUTO_CODE_QA_DIRECT_RUNTIME", "true")
    _write_passing_openai_history(tmp_path)
    resolve_qa_runtime, _ = _import_resolver()

    decision = resolve_qa_runtime(
        agent_type="qa_fixer",
        spec_dir=tmp_path,
        qa_iteration=1,
        project_dir=tmp_path,
    )

    assert decision.use_runtime_layer is True
    assert decision.provider_name == "openai"
    assert decision.runtime_mode == "generic_edit"


def test_claude_decision_does_not_use_runtime_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """The default Claude path returns a decision with use_runtime_layer=False."""
    _clear_qa_env(monkeypatch, "qa_reviewer")
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    resolve_qa_runtime, _ = _import_resolver()

    decision = resolve_qa_runtime(
        agent_type="qa_reviewer",
        spec_dir=tmp_path,
        qa_iteration=1,
        project_dir=tmp_path,
    )

    assert decision.use_runtime_layer is False
    assert decision.provider_name == "claude"
