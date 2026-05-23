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

from pathlib import Path

import pytest


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
        resolve_qa_runtime(
            agent_type=agent_type, spec_dir=tmp_path, qa_iteration=2
        )

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
        resolve_qa_runtime(
            agent_type=agent_type, spec_dir=tmp_path, qa_iteration=3
        )

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
        resolve_qa_runtime(
            agent_type=agent_type, spec_dir=tmp_path, qa_iteration=4
        )

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
    monkeypatch.setenv(
        "AUTO_CODE_AUTONOMY_OPENAI_ALLOWED_PHASES", "coding,qa_fixing"
    )
    resolve_qa_runtime, QaRuntimeUnsupportedError = _import_resolver()

    with pytest.raises(QaRuntimeUnsupportedError):
        resolve_qa_runtime(
            agent_type=agent_type, spec_dir=tmp_path, qa_iteration=5
        )
