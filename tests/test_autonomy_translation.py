"""Tests: AUTO_CODE_AUTONOMY level translates into build-pipeline knobs."""

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    for var in (
        "AUTO_CODE_AUTONOMY",
        "AUTO_CODE_RUNTIME_FALLBACK",
        "AUTO_CODE_RUNTIME_MODE",
        "AUTO_CLAUDE_RUNTIME_MODE",
        "AGENT_RUNTIME_MODE_CODER",
    ):
        monkeypatch.delenv(var, raising=False)


def test_safe_level_enables_runtime_fallback_without_legacy_env(
    monkeypatch: pytest.MonkeyPatch,
):
    """Live-build finding: safe alone must enable fallback for the coder path."""
    from agents.runtime.fallback import runtime_fallback_enabled

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")

    assert runtime_fallback_enabled() is True


def test_claude_level_keeps_runtime_fallback_off(monkeypatch: pytest.MonkeyPatch):
    from agents.runtime.fallback import runtime_fallback_enabled

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "claude")

    assert runtime_fallback_enabled() is False


def test_explicit_fallback_env_wins_over_safe_level(monkeypatch: pytest.MonkeyPatch):
    from agents.runtime.fallback import runtime_fallback_enabled

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.setenv("AUTO_CODE_RUNTIME_FALLBACK", "false")

    assert runtime_fallback_enabled() is False


def test_off_level_yields_analysis_only_runtime_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    from agents.runtime.modes import get_runtime_mode

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "off")

    assert get_runtime_mode("coder") == "analysis_only"


def test_per_agent_runtime_mode_wins_over_level(monkeypatch: pytest.MonkeyPatch):
    from agents.runtime.modes import get_runtime_mode

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "off")
    monkeypatch.setenv("AGENT_RUNTIME_MODE_CODER", "generic_edit")

    assert get_runtime_mode("coder") == "generic_edit"


def test_default_runtime_mode_stays_full_autonomous(
    monkeypatch: pytest.MonkeyPatch,
):
    """No level, no env: today's behavior (claude level) is preserved."""
    from agents.runtime.modes import get_runtime_mode

    assert get_runtime_mode("coder") == "full_autonomous"
