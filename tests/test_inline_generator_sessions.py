#!/usr/bin/env python3
"""
Tests for the inline agent-session call sites that used to call the phantom
``client.create_agent_session(...)`` method.

``ClaudeSDKClient`` (claude_agent_sdk) has no ``create_agent_session`` method, so
every one of these sessions raised
``AttributeError: 'ClaudeSDKClient' object has no attribute 'create_agent_session'``
at runtime. The real session API is ``run_agent_session()`` from
``agents/session.py``, driven inside ``async with client``.

The shared generator boilerplate (``agents/_generator_base``) is covered by
``tests/test_fixture_generator_session.py``. This file covers the *inline* call
sites that do not go through that boilerplate:

* ``agents/documentation_generator.run_documentation_generator_session``
* ``agents/migration_assistant.run_migration_assistant``
* ``agents/test_generator.run_test_generator_session``     (writer + improvement)
* ``agents/agent_subprocess.run_agent_session``            (subprocess wrapper)

Each test proves the session is driven through the real ``run_agent_session``
helper (an AsyncMock) inside ``async with client`` — never through the phantom
method — and that the agent role prompt leads the message.
"""

import sys
from contextlib import ExitStack
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path (mirrors tests/test_fixture_generator_session.py).
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Importing these agent modules pulls in prompts_pkg, whose package __init__
# eagerly imports the context/semantic-scoring stack (numpy). That native
# dependency is irrelevant to the session wiring under test, so stub it when
# absent — mirroring tests/test_fixture_generator_session.py and how
# tests/conftest.py pre-mocks the Claude SDK.
if "numpy" not in sys.modules:
    if find_spec("numpy") is None:
        sys.modules["numpy"] = MagicMock()


# =============================================================================
# Shared fakes
# =============================================================================


class _FakeSDKClient:
    """Stand-in for ClaudeSDKClient.

    Supports ``async with`` (the SDK client is an async context manager) but
    deliberately has NO ``create_agent_session`` attribute, mirroring the real
    SDK. If a call site ever reaches for that phantom method again, it raises
    AttributeError instead of silently passing. ``enter_count`` lets a test
    assert how many times the client was connected (the test_generator path
    drives two sequential sessions on one client).
    """

    def __init__(self):
        self.enter_count = 0
        self.exit_count = 0

    @property
    def entered(self) -> bool:
        return self.enter_count > 0

    @property
    def exited(self) -> bool:
        return self.exit_count > 0

    async def __aenter__(self):
        self.enter_count += 1
        return self

    async def __aexit__(self, *exc):
        self.exit_count += 1
        return False


def _session_result(status="continue", response="work done"):
    """A realistic 4-tuple return for run_agent_session."""
    return (status, response, {"input_tokens": 1, "output_tokens": 2}, MagicMock())


# =============================================================================
# Agent type registration (guards create_client for the inline sites)
# =============================================================================


def test_inline_generator_agent_types_are_registered():
    """create_client must resolve every agent type these sessions request."""
    from agents.tools_pkg.models import AGENT_CONFIGS

    for agent_type in (
        "documentation_generator",
        "migration_assistant",
        "test_generator",
    ):
        assert agent_type in AGENT_CONFIGS, f"{agent_type} should be registered"


# =============================================================================
# documentation_generator
# =============================================================================


@pytest.mark.asyncio
async def test_documentation_generator_drives_real_session_api(tmp_path):
    """run_documentation_generator_session must await run_agent_session()."""
    from agents import documentation_generator as docgen

    fake_client = _FakeSDKClient()
    system_prompt = "SYSTEM PROMPT: you are the Documentation Generator Agent."
    fake_run = AsyncMock(return_value=_session_result())

    with (
        patch.object(docgen, "create_client", return_value=fake_client) as mock_create,
        patch.object(docgen, "get_agent_prompt", return_value=system_prompt),
        patch.object(docgen, "get_task_logger", return_value=None),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await docgen.run_documentation_generator_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            analysis_results={"functions": [], "classes": []},
            model="claude-test-model",
            max_thinking_tokens=0,
        )

    # No docs exist under tmp_path, so generation succeeds with zero files.
    assert result["success"] is True
    assert result["error"] is None

    # create_client was asked for the documentation_generator agent type.
    assert mock_create.call_args.kwargs["agent_type"] == "documentation_generator"

    # The real session helper was driven once, inside `async with client`.
    fake_run.assert_awaited_once()
    call = fake_run.await_args
    assert call.kwargs["client"] is fake_client
    assert call.kwargs["spec_dir"] == tmp_path
    assert fake_client.entered is True
    assert fake_client.exited is True

    # The agent role prompt leads the message (the SDK client carries only the
    # generic base system prompt).
    message = call.kwargs["message"]
    assert message.startswith(system_prompt)
    assert "Documentation Generator Agent" in message


@pytest.mark.asyncio
async def test_documentation_generator_propagates_session_error(tmp_path):
    """An 'error' status from run_agent_session becomes a failed result."""
    from agents import documentation_generator as docgen

    fake_run = AsyncMock(return_value=_session_result("error", "boom: model down"))

    with (
        patch.object(docgen, "create_client", return_value=_FakeSDKClient()),
        patch.object(docgen, "get_agent_prompt", return_value="PROMPT"),
        patch.object(docgen, "get_task_logger", return_value=None),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await docgen.run_documentation_generator_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            analysis_results={"functions": [], "classes": []},
            model="claude-test-model",
            max_thinking_tokens=0,
        )

    assert result["success"] is False
    assert "boom: model down" in result["error"]


# =============================================================================
# migration_assistant
# =============================================================================


@pytest.mark.asyncio
async def test_migration_assistant_drives_real_session_api(tmp_path):
    """run_migration_assistant must await run_agent_session() inside async with."""
    from agents import migration_assistant as miga

    fake_client = _FakeSDKClient()
    system_prompt = "SYSTEM PROMPT: you are the Migration Assistant Agent."
    fake_run = AsyncMock(return_value=_session_result())

    with (
        patch.object(miga, "create_client", return_value=fake_client) as mock_create,
        patch.object(miga, "get_agent_prompt", return_value=system_prompt),
        patch.object(miga, "get_task_logger", return_value=None),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await miga.run_migration_assistant(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            migration_context={"from": "v1", "to": "v2"},
            model="claude-test-model",
            max_thinking_tokens=0,
        )

    # Success path returns the checkpoint summary (no "error" key on success).
    assert result["success"] is True
    assert result["checkpoints_created"] == 0
    assert mock_create.call_args.kwargs["agent_type"] == "migration_assistant"

    fake_run.assert_awaited_once()
    call = fake_run.await_args
    assert call.kwargs["client"] is fake_client
    assert call.kwargs["spec_dir"] == tmp_path
    assert fake_client.entered is True
    assert fake_client.exited is True

    message = call.kwargs["message"]
    assert message.startswith(system_prompt)
    assert "Migration Assistant Agent" in message


@pytest.mark.asyncio
async def test_migration_assistant_propagates_session_error(tmp_path):
    """An 'error' status from run_agent_session becomes a failed result."""
    from agents import migration_assistant as miga

    fake_run = AsyncMock(return_value=_session_result("error", "boom: migration down"))

    with (
        patch.object(miga, "create_client", return_value=_FakeSDKClient()),
        patch.object(miga, "get_agent_prompt", return_value="PROMPT"),
        patch.object(miga, "get_task_logger", return_value=None),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await miga.run_migration_assistant(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="claude-test-model",
            max_thinking_tokens=0,
        )

    assert result["success"] is False
    assert "boom: migration down" in result["error"]


# =============================================================================
# test_generator (two inline sessions: writer + coverage-improvement)
# =============================================================================


def _test_generator_patches(tg_module, fake_client, fake_run, *, total_coverage):
    """Patches that let run_test_generator_session reach its inline sessions.

    Yields the patch context managers; enter them with an ExitStack. The only
    behaviour that varies between tests is ``total_coverage`` (which decides
    whether the coverage-improvement session runs).
    """
    coverage_result = MagicMock(success=True, total_coverage=total_coverage)
    gaps_summary = {"critical_gaps": [], "files_with_gaps": []}
    return [
        patch.object(tg_module, "create_client", return_value=fake_client),
        patch.object(tg_module, "get_agent_prompt", return_value="PROMPT"),
        patch.object(tg_module, "get_task_logger", return_value=None),
        patch.object(tg_module, "detect_test_framework", return_value="pytest"),
        patch.object(tg_module, "emit_phase", MagicMock()),
        patch.object(
            tg_module,
            "load_coverage_config",
            return_value=MagicMock(minimum_coverage=80.0),
        ),
        patch.object(tg_module, "validate_generated_tests", return_value=True),
        patch.object(tg_module, "format_coverage_gaps_prompt", return_value="GAPS"),
        patch.object(
            tg_module,
            "analyze_coverage_gaps",
            return_value=(coverage_result, gaps_summary),
        ),
        patch("agents.session.run_agent_session", fake_run),
    ]


@pytest.mark.asyncio
async def test_test_generator_writer_session_uses_real_api(tmp_path):
    """The pytest writer session (was create_agent_session) drives run_agent_session.

    Coverage is above threshold, so the improvement iteration does not run and
    exactly one session is driven.
    """
    from agents import test_generator as tg

    # A test file must already exist for the post-session scan to "find" output.
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text("def test_ok():\n    assert True\n")

    fake_client = _FakeSDKClient()
    fake_run = AsyncMock(return_value=_session_result())

    with ExitStack() as stack:
        for cm in _test_generator_patches(
            tg, fake_client, fake_run, total_coverage=95.0
        ):
            stack.enter_context(cm)
        result = await tg.run_test_generator_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            analysis_results={"functions": [], "classes": []},
            model="claude-test-model",
            max_thinking_tokens=0,
            generate_fixtures_first=False,
        )

    assert result["success"] is True
    # Exactly one session (writer), driven inside `async with client`.
    fake_run.assert_awaited_once()
    call = fake_run.await_args
    assert call.kwargs["client"] is fake_client
    assert call.kwargs["spec_dir"] == tmp_path
    assert fake_client.enter_count == 1
    assert fake_client.exit_count == 1
    # Role prompt leads the writer message.
    assert call.kwargs["message"].startswith("PROMPT")
    assert "Test Generator Agent" in call.kwargs["message"]


@pytest.mark.asyncio
async def test_test_generator_runs_improvement_session(tmp_path):
    """Low coverage triggers the SECOND inline session (was create_agent_session).

    Proves both inline call sites — the writer session and the coverage
    improvement iteration — drive the real session API on the same client.
    """
    from agents import test_generator as tg

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text("def test_ok():\n    assert True\n")

    fake_client = _FakeSDKClient()
    fake_run = AsyncMock(return_value=_session_result())

    with ExitStack() as stack:
        for cm in _test_generator_patches(
            tg, fake_client, fake_run, total_coverage=50.0
        ):
            stack.enter_context(cm)
        result = await tg.run_test_generator_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            analysis_results={"functions": [], "classes": []},
            model="claude-test-model",
            max_thinking_tokens=0,
            generate_fixtures_first=False,
        )

    assert result["success"] is True
    # Two sessions: writer + improvement. Two connects on the one client.
    assert fake_run.await_count == 2
    assert fake_client.enter_count == 2
    assert fake_client.exit_count == 2
    # The improvement (second) message carries the coverage-gap prompt and still
    # leads with the role prompt.
    improvement_message = fake_run.await_args_list[1].kwargs["message"]
    assert improvement_message.startswith("PROMPT")
    assert "GAPS" in improvement_message


# =============================================================================
# agent_subprocess (the isolated-subprocess session wrapper)
# =============================================================================


@pytest.mark.asyncio
async def test_agent_subprocess_drives_real_session_api(tmp_path):
    """agent_subprocess.run_agent_session must drive the shared session helper.

    Its own wrapper is named run_agent_session, so the real helper is imported
    under an alias; patching agents.session.run_agent_session covers it.
    """
    from agents import agent_subprocess

    fake_client = _FakeSDKClient()
    fake_run = AsyncMock(return_value=_session_result(response="coder finished"))

    with (
        patch("core.client.create_client", return_value=fake_client) as mock_create,
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await agent_subprocess.run_agent_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            agent_type="coder",
            model="claude-test-model",
            starting_message="Implement the feature.",
            system_prompt=None,
            session_name="coder-session",
        )

    assert result["success"] is True
    assert result["error"] is None
    # Output shape preserved for run_agent_session_isolated's parser.
    assert result["output"]["response"] == "coder finished"
    assert result["output"]["agent_type"] == "coder"
    assert result["output"]["session_name"] == "coder-session"

    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["agent_type"] == "coder"

    fake_run.assert_awaited_once()
    call = fake_run.await_args
    assert call.kwargs["client"] is fake_client
    assert call.kwargs["spec_dir"] == tmp_path
    assert fake_client.entered is True
    assert fake_client.exited is True
    # No system_prompt → message is the starting message verbatim.
    assert call.kwargs["message"] == "Implement the feature."


@pytest.mark.asyncio
async def test_agent_subprocess_prepends_system_prompt(tmp_path):
    """When a system_prompt is supplied it leads the message."""
    from agents import agent_subprocess

    fake_run = AsyncMock(return_value=_session_result())

    with (
        patch("core.client.create_client", return_value=_FakeSDKClient()),
        patch("agents.session.run_agent_session", fake_run),
    ):
        await agent_subprocess.run_agent_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            agent_type="qa_fixer",
            model="claude-test-model",
            starting_message="Fix the failing test.",
            system_prompt="ROLE: QA fixer.",
            session_name="qa-session",
        )

    message = fake_run.await_args.kwargs["message"]
    assert message.startswith("ROLE: QA fixer.")
    assert "Fix the failing test." in message


@pytest.mark.asyncio
async def test_agent_subprocess_propagates_session_error(tmp_path):
    """An 'error' status becomes a failed subprocess result (no exception)."""
    from agents import agent_subprocess

    fake_run = AsyncMock(return_value=_session_result("error", "boom: auth failed"))

    with (
        patch("core.client.create_client", return_value=_FakeSDKClient()),
        patch("agents.session.run_agent_session", fake_run),
    ):
        result = await agent_subprocess.run_agent_session(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            agent_type="coder",
            model="claude-test-model",
            starting_message="Implement the feature.",
            session_name="coder-session",
        )

    assert result["success"] is False
    assert result["output"] is None
    assert "boom: auth failed" in result["error"]
