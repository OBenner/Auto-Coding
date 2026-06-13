#!/usr/bin/env python3
"""
Tests for the fixture generator path and the shared generator-session boilerplate.

Covers two regressions that silently broke fixture generation on every build:

1. ``fixture_generator`` was never registered in ``AGENT_CONFIGS``, so
   ``create_client(agent_type="fixture_generator")`` raised
   ``ValueError: Unknown agent type: 'fixture_generator'``.

2. The shared boilerplate (``agents/_generator_base.run_generator_session``)
   called ``client.create_agent_session(...)`` — a method ``ClaudeSDKClient``
   does not have. The real session API is ``run_agent_session()`` from
   ``agents/session.py``, driven inside ``async with client``.

These tests construct the fixture_generator path far enough to prove the agent
type resolves and that the boilerplate drives the session through a real method.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path (mirrors tests/test_agent_configs.py)
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Importing the generator boilerplate pulls in prompts_pkg, whose package
# __init__ eagerly imports the context/semantic-scoring stack (numpy). That
# native dependency is irrelevant to the fixture-session wiring under test, so
# stub it when absent — mirroring how tests/conftest.py pre-mocks the Claude SDK.
if "numpy" not in sys.modules:
    try:
        import numpy  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["numpy"] = MagicMock()


# =============================================================================
# (1) Agent type registration
# =============================================================================


class TestFixtureGeneratorRegistration:
    """fixture_generator (and its generator siblings) must resolve in AGENT_CONFIGS."""

    def test_fixture_generator_is_registered(self):
        """The agent type that create_client rejects must now exist in the registry."""
        from agents.tools_pkg.models import AGENT_CONFIGS

        assert "fixture_generator" in AGENT_CONFIGS

    def test_fixture_generator_config_has_required_fields(self):
        """Registry entry must be shaped like every other agent config."""
        from agents.tools_pkg.models import get_agent_config

        config = get_agent_config("fixture_generator")
        for field in ("tools", "mcp_servers", "auto_claude_tools", "thinking_default"):
            assert field in config, f"fixture_generator missing '{field}'"

    def test_fixture_generator_can_write_files(self):
        """Generating fixture files needs read + write + bash tooling."""
        from agents.tools_pkg.permissions import get_allowed_tools

        tools = get_allowed_tools("fixture_generator")
        for tool in ("Read", "Write", "Edit", "Bash"):
            assert tool in tools, f"fixture_generator should expose {tool}"

    def test_fixture_generator_mcp_servers_resolve(self):
        """get_required_mcp_servers must not raise for the new type."""
        from agents.tools_pkg.models import get_required_mcp_servers

        servers = get_required_mcp_servers("fixture_generator")
        assert isinstance(servers, list)
        # Models default to context7/graphiti/auto-claude; auto-claude is unconditional.
        assert "auto-claude" in servers

    def test_thinking_default_is_valid(self):
        """thinking_default must map to a real budget level."""
        from agents.tools_pkg.models import get_default_thinking_level
        from phase_config import THINKING_BUDGET_MAP

        assert get_default_thinking_level("fixture_generator") in THINKING_BUDGET_MAP

    def test_sibling_generators_still_registered(self):
        """Verify e2e_generator and the other generator agents remain registered."""
        from agents.tools_pkg.models import AGENT_CONFIGS

        for agent_type in (
            "test_generator",
            "e2e_generator",
            "documentation_generator",
            "migration_assistant",
        ):
            assert agent_type in AGENT_CONFIGS, f"{agent_type} should be registered"


# =============================================================================
# (2) Generator-session boilerplate drives the real session API
# =============================================================================


class _FakeSDKClient:
    """Stand-in for ClaudeSDKClient.

    Supports ``async with`` (the SDK client is an async context manager) but
    deliberately has NO ``create_agent_session`` attribute, mirroring the real
    SDK. If the boilerplate ever calls that phantom method again, it raises
    AttributeError instead of silently passing.
    """

    def __init__(self):
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *exc):
        self.exited = True
        return False


def _session_kwargs(project_dir: Path, spec_dir: Path, **overrides):
    """Build the keyword args run_generator_session expects (fixture flavour)."""
    from task_logger import LogPhase

    kwargs = dict(
        project_dir=project_dir,
        spec_dir=spec_dir,
        analysis_results={"classes": [], "functions": [], "models": []},
        session_title="FIXTURE GENERATOR SESSION",
        session_description="Generating pytest fixtures...",
        prompt_name="fixture_generator",
        agent_type="fixture_generator",
        session_name="fixture-generator-session",
        starting_message="TASK: generate fixtures for the analyzed code.",
        log_phase=LogPhase.VALIDATION,
        log_summary="Analyzing 0 classes for fixture generation",
        # Pass model + thinking explicitly so the helper skips phase-config lookups.
        model="claude-test-model",
        max_thinking_tokens=0,
        verbose=False,
    )
    kwargs.update(overrides)
    return kwargs


@pytest.mark.asyncio
async def test_run_generator_session_drives_real_session_api(tmp_path):
    """The boilerplate must await run_agent_session() — not client.create_agent_session()."""
    from agents import _generator_base

    fake_client = _FakeSDKClient()
    system_prompt = "SYSTEM PROMPT: you are the Fixture Generator Agent."
    fake_run = AsyncMock(
        return_value=("continue", "fixtures written", {"input_tokens": 1, "output_tokens": 2}, MagicMock())
    )

    with (
        patch.object(_generator_base, "create_client", return_value=fake_client) as mock_create_client,
        patch.object(_generator_base, "get_agent_prompt", return_value=system_prompt),
        patch.object(_generator_base, "get_task_logger", return_value=None),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await _generator_base.run_generator_session(
            **_session_kwargs(tmp_path, tmp_path)
        )

    # The session succeeded via the real driver.
    assert result["success"] is True
    assert result["error"] is None

    # create_client was asked for the now-registered agent type.
    assert mock_create_client.call_args.kwargs["agent_type"] == "fixture_generator"

    # The real session helper was driven exactly once...
    fake_run.assert_awaited_once()
    call = fake_run.await_args
    assert call.kwargs["client"] is fake_client
    assert call.kwargs["spec_dir"] == tmp_path

    # ...inside `async with client` (client was connected and released).
    assert fake_client.entered is True
    assert fake_client.exited is True

    # The agent role prompt is delivered as the leading message, followed by
    # the task-specific starting message (the SDK client carries only the
    # generic base system prompt).
    message = call.kwargs["message"]
    assert system_prompt in message
    assert "TASK: generate fixtures" in message
    assert message.index(system_prompt) < message.index("TASK: generate fixtures")


@pytest.mark.asyncio
async def test_run_generator_session_propagates_session_error(tmp_path):
    """An 'error' status from run_agent_session becomes a failed result."""
    from agents import _generator_base

    fake_run = AsyncMock(return_value=("error", "boom: model unavailable", None, MagicMock()))

    with (
        patch.object(_generator_base, "create_client", return_value=_FakeSDKClient()),
        patch.object(_generator_base, "get_agent_prompt", return_value="PROMPT"),
        patch.object(_generator_base, "get_task_logger", return_value=None),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await _generator_base.run_generator_session(
            **_session_kwargs(tmp_path, tmp_path)
        )

    assert result["success"] is False
    assert "boom: model unavailable" in result["error"]


@pytest.mark.asyncio
async def test_run_generator_session_reports_unknown_agent_type(tmp_path):
    """If create_client rejects the agent type, the helper returns a clean failure.

    This is the original 'Unknown agent type' symptom — guards the contract that
    a registration regression surfaces as a structured error, not a crash.
    """
    from agents import _generator_base

    with (
        patch.object(
            _generator_base,
            "create_client",
            side_effect=ValueError("Unknown agent type: 'fixture_generator'"),
        ),
        patch.object(_generator_base, "get_agent_prompt", return_value="PROMPT"),
        patch.object(_generator_base, "get_task_logger", return_value=None),
    ):
        result = await _generator_base.run_generator_session(
            **_session_kwargs(tmp_path, tmp_path)
        )

    assert result["success"] is False
    assert "Unknown agent type" in result["error"]
