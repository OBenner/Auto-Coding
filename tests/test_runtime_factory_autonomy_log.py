"""Tests for the runtime factory autonomy logging (P3.T3).

create_runtime_session() must surface the resolved autonomy level in the
session log for every call path, and accept an injected
ResolvedAutonomySettings without re-resolving from the environment.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

import agents.runtime.adapters as adapters_mod  # noqa: E402
from agents.runtime.adapters import create_runtime_session  # noqa: E402
from core.autonomy_level import (  # noqa: E402
    AUTONOMY_LEVEL_ENV,
    resolve_autonomy_settings,
)

FACTORY_LOGGER = "agents.runtime.adapters"


def make_session(**kwargs):
    """Create the simplest runtime session (analysis_only needs no extras)."""
    return create_runtime_session(
        provider_name="openai",
        agent_session=object(),
        runtime_mode="analysis_only",
        agent_type="coder",
        **kwargs,
    )


def test_logs_level_resolved_from_env(monkeypatch, caplog):
    monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "safe")
    with caplog.at_level(logging.INFO, logger=FACTORY_LOGGER):
        session = make_session()
    assert session is not None
    assert "autonomy=safe" in caplog.text
    assert "provider=openai" in caplog.text
    assert "mode=analysis_only" in caplog.text
    assert "agent=coder" in caplog.text


def test_default_level_logged_when_env_unset(monkeypatch, caplog):
    monkeypatch.delenv(AUTONOMY_LEVEL_ENV, raising=False)
    with caplog.at_level(logging.INFO, logger=FACTORY_LOGGER):
        make_session()
    assert "autonomy=claude" in caplog.text  # default level


def test_injected_settings_skip_env_resolution(monkeypatch, caplog):
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "bold"})

    def boom():
        raise AssertionError("factory must not re-resolve injected settings")

    monkeypatch.setattr(adapters_mod, "resolve_autonomy_settings", boom)
    with caplog.at_level(logging.INFO, logger=FACTORY_LOGGER):
        session = make_session(autonomy_settings=settings)
    assert session is not None
    assert "autonomy=bold" in caplog.text


def test_level_logged_for_claude_runtime(monkeypatch, caplog):
    monkeypatch.setenv(AUTONOMY_LEVEL_ENV, "off")

    async def runner(*args, **kwargs):
        return ()

    with caplog.at_level(logging.INFO, logger=FACTORY_LOGGER):
        session = create_runtime_session(
            provider_name="claude",
            agent_session=object(),
            claude_session_runner=runner,
            runtime_mode="full_autonomous",
            agent_type="planner",
        )
    assert session is not None
    assert "autonomy=off" in caplog.text
    assert "agent=planner" in caplog.text
