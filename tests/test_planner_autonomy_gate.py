"""Tests for the planner autonomy gate (P3.T2).

``AUTO_CODE_AUTONOMY=off`` must block non-Claude planner sessions before the
session exists; Claude keeps working at every level, and claude/safe/bold
keep non-Claude planners available.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

import agents.planner as planner_mod  # noqa: E402
from agents.planner import (  # noqa: E402
    _assert_planner_autonomy_allows,
    create_planner_session,
)
from core.autonomy_level import AUTONOMY_LEVEL_ENV  # noqa: E402
from core.providers.exceptions import ProviderError  # noqa: E402


class TestAutonomyGateHelper:
    def test_off_blocks_non_claude(self, monkeypatch):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "off")
        with pytest.raises(ProviderError, match="AUTO_CODE_AUTONOMY=off"):
            _assert_planner_autonomy_allows("openai")

    def test_off_keeps_claude_available(self, monkeypatch):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "off")
        _assert_planner_autonomy_allows("claude")  # must not raise

    @pytest.mark.parametrize("level", ["claude", "safe", "bold"])
    def test_other_levels_allow_non_claude(self, monkeypatch, level):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, level)
        _assert_planner_autonomy_allows("openai")  # must not raise

    def test_default_level_allows_non_claude(self, monkeypatch):
        monkeypatch.delenv(AUTONOMY_LEVEL_ENV, raising=False)
        _assert_planner_autonomy_allows("openai")  # default is claude, not off

    def test_error_names_the_provider(self, monkeypatch):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "off")
        with pytest.raises(ProviderError, match="'ollama'"):
            _assert_planner_autonomy_allows("ollama")


class _FakeProvider:
    """Provider stub: session creation must never be reached when gated."""

    def __init__(self, name: str):
        self.name = name
        self.create_session_calls = 0

    def create_session(self, *args, **kwargs):
        self.create_session_calls += 1
        return object()


class TestCreatePlannerSessionGate:
    def test_off_blocks_before_session_creation(self, monkeypatch, tmp_path):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "off")
        fake = _FakeProvider("openai")
        monkeypatch.setattr(planner_mod, "create_engine_provider", lambda config: fake)

        with pytest.raises(ProviderError, match="AUTO_CODE_AUTONOMY=off"):
            create_planner_session(tmp_path, tmp_path / "spec")

        assert fake.create_session_calls == 0

    def test_safe_level_creates_non_claude_session(self, monkeypatch, tmp_path):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "safe")
        fake = _FakeProvider("openai")
        monkeypatch.setattr(planner_mod, "create_engine_provider", lambda config: fake)

        session = create_planner_session(tmp_path, tmp_path / "spec")

        assert session is not None
        assert fake.create_session_calls == 1

    def test_off_still_creates_claude_session(self, monkeypatch, tmp_path):
        monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "off")
        fake = _FakeProvider("claude")
        monkeypatch.setattr(planner_mod, "create_engine_provider", lambda config: fake)

        session = create_planner_session(tmp_path, tmp_path / "spec")

        assert session is not None
        assert fake.create_session_calls == 1
