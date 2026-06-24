"""Tests for model/provider attribution in token stats (P5.T1).

Verifies the persisted token_stats schema carries the model and provider per
phase, that the provider is auto-resolved when a caller omits it, and that a
known model is not clobbered by a later session that supplies none.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents import session as session_mod  # noqa: E402
from agents.session import load_token_stats, save_token_stats  # noqa: E402
from core.token_stats import PhaseTokenStats, TaskTokenStats  # noqa: E402


def test_phase_stats_to_dict_includes_model_provider():
    stats = PhaseTokenStats(
        phase="coding", input_tokens=1, output_tokens=2, model="m", provider="p"
    )
    task = TaskTokenStats(
        phases={"coding": stats},
        total_input_tokens=1,
        total_output_tokens=2,
        total_tokens=3,
        created_at=stats.updated_at,
        updated_at=stats.updated_at,
    )
    phase_dict = task.to_dict()["phases"]["coding"]
    assert phase_dict["model"] == "m"
    assert phase_dict["provider"] == "p"


def test_save_and_load_round_trips_model_provider(tmp_path):
    assert save_token_stats(
        tmp_path, "coding", 100, 50, model="claude-opus-4-8", provider="claude"
    )
    loaded = load_token_stats(tmp_path)
    assert loaded is not None
    assert loaded.phases["coding"].model == "claude-opus-4-8"
    assert loaded.phases["coding"].provider == "claude"


def test_provider_auto_resolved_when_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr(session_mod, "_resolve_active_provider", lambda: "openai")
    save_token_stats(tmp_path, "planning", 10, 5, model="gpt-x")
    loaded = load_token_stats(tmp_path)
    assert loaded.phases["planning"].provider == "openai"
    assert loaded.phases["planning"].model == "gpt-x"


def test_known_model_not_clobbered_by_later_none(tmp_path, monkeypatch):
    monkeypatch.setattr(session_mod, "_resolve_active_provider", lambda: "claude")
    save_token_stats(tmp_path, "coding", 10, 5, model="m1")
    # A later session in the same phase that doesn't supply a model.
    save_token_stats(tmp_path, "coding", 7, 3, model=None)
    loaded = load_token_stats(tmp_path)
    assert loaded.phases["coding"].model == "m1"
    assert loaded.phases["coding"].input_tokens == 17  # tokens still aggregate
