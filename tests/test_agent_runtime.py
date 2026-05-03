import asyncio
import json
import os
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from agents.runtime import (
    LocalActionExecutor,
    RuntimeCapabilities,
    RuntimeCapabilityError,
    RuntimeMcpBridge,
    RuntimeRequirements,
    RuntimeSubagentOrchestrator,
    RuntimeSubagentResult,
    RuntimeSubagentTask,
    create_runtime_session,
    describe_mcp_server_statuses,
    get_runtime_mode,
    local_action_response_schema,
    local_action_tool_schemas,
    local_action_tool_specs,
    normalize_runtime_mode,
    render_local_action_prompt,
    requirements_for_runtime_mode,
    resolve_runtime_mcp_support,
    resolve_runtime_mode_with_fallback,
    resolve_runtime_runner_route,
    resolve_runtime_subagent_support,
    run_runtime_session,
    runtime_fallback_enabled,
    runtime_runner_router_enabled,
    save_runtime_fallback_artifact,
    save_runtime_runner_route_artifact,
    summarize_subagent_results,
)
from agents.runtime.adapters.cli_runner import CliRuntimeCommand, CliRuntimeProcess
from agents.runtime.adapters.codex_cli import (
    build_codex_command_args,
    build_codex_usage_metadata,
    codex_resume_metadata,
    extract_codex_final_message,
    parse_codex_json_events,
    summarize_codex_account,
    summarize_codex_events,
)
from agents.runtime.adapters.generic_edit import summarize_generic_edit_transactions
from agents.runtime.adapters.patch_proposal import (
    PatchProposalError,
    parse_patch_proposal,
    validate_workspace_relative_path,
)
from agents.runtime.local_actions import (
    MAX_REPLACE_COUNT,
    MAX_REPLACE_TEXT_CHARS,
    MAX_SUBAGENT_TASKS,
    MAX_TOOL_OUTPUT_CHARS,
    ToolActionResult,
    safe_action_for_trace,
    safe_result_for_trace,
)
from core.platform import run_process
from core.providers.adapters.openai_compat import (
    parse_openai_tool_calls,
    provider_message_content,
)
from core.providers.config import ProviderConfig


class FakeClaudeClient:
    def __init__(self):
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False


@pytest.mark.asyncio
async def test_claude_runtime_wraps_existing_session_runner(tmp_path: Path):
    client = FakeClaudeClient()
    agent_session = SimpleNamespace(client=client)

    async def runner(
        received_client,
        message,
        spec_dir,
        verbose,
        phase,
        subtask_id=None,
    ):
        await asyncio.sleep(0)
        assert received_client is client
        assert message == "do work"
        assert spec_dir == tmp_path
        assert verbose is True
        assert subtask_id == "1.1"
        return "complete", "done", {"input_tokens": 1, "output_tokens": 2}, "tracker"

    runtime_session = create_runtime_session(
        provider_name="claude",
        agent_session=agent_session,
        claude_session_runner=runner,
    )

    result = await run_runtime_session(
        runtime_session,
        "do work",
        tmp_path,
        verbose=True,
        requirements=RuntimeRequirements.full_coder(),
        subtask_id="1.1",
    )

    assert result.status == "complete"
    assert result.response_text == "done"
    assert result.usage_metadata == {"input_tokens": 1, "output_tokens": 2}
    assert result.decision_tracker == "tracker"
    assert client.entered is True
    assert client.exited is True


@pytest.mark.asyncio
async def test_codex_cli_runtime_uses_output_last_message(tmp_path: Path):
    fake_codex_script = tmp_path / "codex.py"
    fake_codex_script.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import pathlib
            import sys

            args = sys.argv[1:]
            assert args[0] == "exec"
            assert "--cd" in args
            assert "--sandbox" in args
            assert "--color" in args
            assert "--json" in args
            output_path = pathlib.Path(args[args.index("--output-last-message") + 1])
            message = sys.stdin.read().strip()
            output_path.write_text(f"final response: {message}", encoding="utf-8")
            print('{"type":"session.started","session_id":"codex-test-session"}')
            print('{"type":"token_usage","usage":{"input_tokens":12,"output_tokens":7,"total_tokens":19},"cost_usd":0.001}')
            """
        ),
        encoding="utf-8",
    )
    if sys.platform == "win32":
        fake_codex = tmp_path / "codex.cmd"
        fake_codex.write_text(
            textwrap.dedent(
                """\
                @echo off
                setlocal EnableExtensions
                set "OUTPUT_PATH="
                :parse
                if "%~1"=="" goto done
                if "%~1"=="--output-last-message" goto found_output
                shift
                goto parse
                :found_output
                shift
                set "OUTPUT_PATH=%~1"
                goto done
                :done
                if "%OUTPUT_PATH%"=="" exit /b 2
                > "%OUTPUT_PATH%" echo final response: do codex work
                echo codex event log
                exit /b 0
                """
            ).replace("\n", "\r\n"),
            encoding="utf-8",
        )
    else:
        fake_codex = tmp_path / "codex"
        fake_codex.write_text(
            fake_codex_script.read_text(encoding="utf-8"), encoding="utf-8"
        )
        fake_codex.chmod(0o755)

    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    session = SimpleNamespace(
        codex_command=str(fake_codex),
        codex_home=codex_home,
        model="codex-default",
    )
    runtime_session = create_runtime_session(
        provider_name="codex",
        agent_session=session,
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "do codex work",
        tmp_path,
        requirements=RuntimeRequirements.full_coder(),
    )

    assert result.status == "complete"
    assert result.response_text.rstrip("\r\n") == "final response: do codex work"
    assert result.artifacts
    assert (tmp_path / "artifacts" / "codex_cli_events.jsonl").exists()
    assert (tmp_path / "artifacts" / "codex_cli_result.json").exists()
    if sys.platform != "win32":
        result_payload = json.loads(
            (tmp_path / "artifacts" / "codex_cli_result.json").read_text(
                encoding="utf-8"
            )
        )
        assert result_payload["session_id"] == "codex-test-session"
        assert result_payload["usage"] == {
            "input_tokens": 12,
            "output_tokens": 7,
            "total_tokens": 19,
        }
        assert result_payload["cost_usd"] == 0.001
        assert result_payload["account_summary"] is None
        assert result.usage_metadata == {
            "input_tokens": 12,
            "output_tokens": 7,
            "total_tokens": 19,
            "cost_usd": 0.001,
        }


@pytest.mark.asyncio
async def test_codex_cli_runtime_uses_event_final_message_without_output_file(
    tmp_path: Path,
):
    fake_codex_script = tmp_path / "codex_events.py"
    fake_codex_script.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import sys

            message = sys.stdin.read().strip()
            print(json.dumps({
                "type": "session.started",
                "session_id": "codex-event-session",
            }))
            print(json.dumps({
                "type": "token_usage",
                "usage": {"input_tokens": 5, "output_tokens": 3},
                "text": "ignore token event text",
            }))
            print(json.dumps({
                "type": "response.completed",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "reasoning", "text": "ignore private notes"},
                        {"type": "output_text", "text": f"event final: {message}"},
                    ],
                },
            }))
            """
        ),
        encoding="utf-8",
    )
    if sys.platform == "win32":
        fake_codex = tmp_path / "codex.cmd"
        fake_codex.write_text(
            f'@echo off\r\n"{sys.executable}" "{fake_codex_script}" %*\r\n',
            encoding="utf-8",
        )
    else:
        fake_codex = tmp_path / "codex"
        fake_codex.write_text(
            fake_codex_script.read_text(encoding="utf-8"), encoding="utf-8"
        )
        fake_codex.chmod(0o755)

    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    session = SimpleNamespace(
        codex_command=str(fake_codex),
        codex_home=codex_home,
        model="codex-default",
    )
    runtime_session = create_runtime_session(
        provider_name="codex",
        agent_session=session,
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "do event work",
        tmp_path,
        requirements=RuntimeRequirements.full_coder(),
    )

    assert result.status == "complete"
    assert result.response_text == "event final: do event work"
    result_payload = json.loads(
        (tmp_path / "artifacts" / "codex_cli_result.json").read_text(encoding="utf-8")
    )
    assert result_payload["session_id"] == "codex-event-session"
    assert result_payload["event_final_message_excerpt"] == (
        "event final: do event work"
    )


def test_codex_cli_event_parser_extracts_usage_and_session():
    stdout = "\n".join(
        [
            "legacy warning",
            json.dumps(
                {
                    "type": "session.started",
                    "session_id": "codex-session-1",
                    "account": {"email": "dev@example.com", "plan": "pro"},
                }
            ),
            json.dumps(
                {
                    "type": "token_usage",
                    "usage": {
                        "prompt_tokens": 42,
                        "completion_tokens": 11,
                        "total_tokens": 53,
                    },
                    "estimated_cost_usd": "0.0042",
                }
            ),
        ]
    )

    events = parse_codex_json_events(stdout)
    summary = summarize_codex_events(events)

    assert len(events) == 2
    assert summary["session_id"] == "codex-session-1"
    assert summary["account"] == {"email": "dev@example.com", "plan": "pro"}
    assert summary["event_types"] == {"session.started": 1, "token_usage": 1}
    assert summary["usage"] == {
        "input_tokens": 42,
        "output_tokens": 11,
        "total_tokens": 53,
    }
    assert summary["cost_usd"] == pytest.approx(0.0042)
    usage_metadata = build_codex_usage_metadata(summary)
    assert usage_metadata
    assert {
        key: value for key, value in usage_metadata.items() if key != "cost_usd"
    } == {
        "input_tokens": 42,
        "output_tokens": 11,
        "total_tokens": 53,
    }
    assert usage_metadata["cost_usd"] == pytest.approx(0.0042)


def test_codex_cli_event_parser_extracts_final_message_from_events():
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "token_usage",
                    "text": "not a final answer",
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
            ),
            json.dumps(
                {
                    "type": "response.completed",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "reasoning", "text": "private"},
                            {"type": "output_text", "text": "final from events"},
                        ],
                    },
                }
            ),
        ]
    )

    assert extract_codex_final_message(parse_codex_json_events(stdout)) == (
        "final from events"
    )


def test_codex_cli_resume_command_uses_resume_subcommand(tmp_path: Path):
    output_path = tmp_path / "last.txt"

    args = build_codex_command_args(
        project_dir=tmp_path,
        model="gpt-5.5",
        output_path=output_path,
        resume_session_id="session-123",
    )

    assert args[:2] == ["exec", "resume"]
    assert "--json" in args
    assert "--model" in args
    assert "--cd" not in args
    assert "--sandbox" not in args
    assert args[-1] == "session-123"
    assert codex_resume_metadata(args) == {
        "resumed": True,
        "last": False,
        "session_id": "session-123",
    }

    resume_last_args = build_codex_command_args(
        project_dir=tmp_path,
        model="codex-default",
        output_path=output_path,
        resume_last=True,
    )
    assert codex_resume_metadata(resume_last_args) == {
        "resumed": True,
        "last": True,
        "session_id": None,
    }


def test_codex_cli_account_summary_omits_credentials():
    summary = summarize_codex_account(
        {
            "email": "dev@example.com",
            "plan": "pro",
            "token": "secret",
            "api_key": "also-secret",
        }
    )

    assert summary == {"email": "dev@example.com", "plan": "pro"}


@pytest.mark.asyncio
async def test_cli_runtime_process_truncates_large_output(tmp_path: Path):
    script = tmp_path / "large_output.py"
    script.write_text(
        "import sys\nsys.stdout.write('x' * 1000)\n",
        encoding="utf-8",
    )
    process = CliRuntimeProcess(max_output_chars=128)

    result = await process.run(
        CliRuntimeCommand(
            executable=sys.executable,
            args=[str(script)],
            cwd=tmp_path,
            env=os.environ,
            stdin_text="",
        )
    )

    assert result.truncated is True
    assert len(result.stdout_text) == 128
    assert result.stderr_text == ""


def test_provider_tool_call_parser_handles_responses_output_blocks():
    message_obj = {
        "output": [
            {
                "type": "function_call",
                "call_id": "call_read",
                "name": "read_file",
                "arguments": json.dumps({"path": "apps/backend/run.py"}),
            }
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "call_read"
    assert tool_calls[0].name == "read_file"
    assert tool_calls[0].arguments == {"path": "apps/backend/run.py"}


def test_provider_tool_call_parser_handles_anthropic_content_blocks():
    message_obj = {
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_search",
                "name": "search_text",
                "input": {"query": "RuntimeSubagentOrchestrator"},
            }
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "toolu_search"
    assert tool_calls[0].name == "search_text"
    assert tool_calls[0].arguments == {"query": "RuntimeSubagentOrchestrator"}


def test_provider_tool_call_parser_handles_gemini_function_call_parts():
    class DumpableArgs:
        def model_dump(self):
            return {"path": "apps/backend"}

    message_obj = {
        "parts": [
            {
                "functionCall": {
                    "name": "stat_path",
                    "args": DumpableArgs(),
                }
            }
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "call_1"
    assert tool_calls[0].name == "stat_path"
    assert tool_calls[0].arguments == {"path": "apps/backend"}


def test_provider_tool_call_parser_handles_gateway_choice_envelopes():
    message_obj = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "gateway_call",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": {"path": "apps/backend/run.py"},
                            },
                        }
                    ]
                }
            }
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "gateway_call"
    assert tool_calls[0].name == "read_file"
    assert tool_calls[0].arguments == {"path": "apps/backend/run.py"}


def test_provider_tool_call_parser_handles_streaming_delta_envelopes():
    message_obj = {
        "delta": {
            "tool_calls": [
                {
                    "call_id": "delta_call",
                    "function": {
                        "name": "search_text",
                        "arguments": json.dumps({"query": "OpenRouter"}),
                    },
                }
            ]
        }
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "delta_call"
    assert tool_calls[0].name == "search_text"
    assert tool_calls[0].arguments == {"query": "OpenRouter"}


def test_provider_message_content_handles_gateway_shapes():
    assert provider_message_content({"content": "plain text"}) == "plain text"
    assert (
        provider_message_content(
            {
                "content": [
                    {"type": "text", "text": "hello "},
                    {"text": "world"},
                    {"type": "tool_call", "name": "read_file"},
                ]
            }
        )
        == "hello world"
    )
    assert provider_message_content(SimpleNamespace(content=None)) == ""


class FakeCompletionSession:
    provider_name = "openai"

    async def complete(self, message: str, stream: bool = True):
        await asyncio.sleep(0)
        assert message == "analyze"
        assert stream is True
        yield "hello"
        yield " world"


class FakeClaudeCompletionSession:
    provider_name = "claude"

    async def complete(self, message: str, stream: bool = True):
        await asyncio.sleep(0)
        assert message == "analyze"
        assert stream is True
        yield "claude limited analysis"


class FakeCancellableCompletionSession:
    provider_name = "openai"

    def __init__(self):
        self.cancelled = False

    async def complete(self, message: str, stream: bool = True):
        await asyncio.sleep(0)
        yield "should not be returned after cancellation"

    async def cancel(self):
        self.cancelled = True
        return True


class FakeClaudeQuerySession:
    provider_name = "claude"

    def __init__(self):
        self.client = FakeClaudeClient()
        self.query_message = None

    async def query(self, message: str):
        await asyncio.sleep(0)
        self.query_message = message

    async def receive_response(self):
        await asyncio.sleep(0)
        yield "query limited analysis"


class FakeSubagentRuntimeSession:
    provider_name = "openai"
    name = "fake_subagent"

    def __init__(self, response: str, status: str = "complete"):
        from agents.runtime import RuntimeCapabilities

        self.response = response
        self.status = status
        self.capabilities = RuntimeCapabilities.completion_only()
        self.prompts: list[str] = []
        self.cancelled = False

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase,
        subtask_id: str | None = None,
    ):
        del spec_dir, verbose, phase, subtask_id
        self.prompts.append(message)
        return SimpleNamespace(
            status=self.status,
            response_text=self.response,
            usage_metadata={"input_tokens": 1, "output_tokens": 2},
            artifacts=None,
        )

    async def cancel(self):
        self.cancelled = True


class SlowSubagentRuntimeSession(FakeSubagentRuntimeSession):
    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase,
        subtask_id: str | None = None,
    ):
        del message, spec_dir, verbose, phase, subtask_id
        await asyncio.sleep(10)
        return SimpleNamespace(
            status="complete",
            response_text="too late",
            usage_metadata=None,
            artifacts=None,
        )


@pytest.mark.asyncio
async def test_completion_runtime_supports_text_only(tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakeCompletionSession(),
    )

    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert result.status == "complete"
    assert result.response_text == "hello world"


@pytest.mark.asyncio
async def test_completion_runtime_cancel_forwards_to_provider(tmp_path: Path):
    session = FakeCancellableCompletionSession()
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="analysis_only",
    )

    assert await runtime_session.cancel() is True
    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert session.cancelled is True
    assert result.status == "cancelled"


@pytest.mark.asyncio
async def test_runtime_subagent_orchestrator_runs_child_sessions(tmp_path: Path):
    created_sessions: list[FakeSubagentRuntimeSession] = []

    def session_factory(task: RuntimeSubagentTask):
        session = FakeSubagentRuntimeSession(f"done {task.id}")
        created_sessions.append(session)
        return session

    orchestrator = RuntimeSubagentOrchestrator(
        session_factory=session_factory,
        spec_dir=tmp_path,
        max_concurrency=2,
    )
    support = orchestrator.support_for(
        provider_name="openai",
        runtime_name="completion",
        capabilities=RuntimeCapabilities.completion_only(),
    )
    run = await orchestrator.run(
        [
            RuntimeSubagentTask(
                id="explore-api",
                role="explorer",
                prompt="Inspect API files",
                metadata={"paths": ["apps/backend"]},
            ),
            RuntimeSubagentTask(
                id="explore-ui",
                role="explorer",
                prompt="Inspect UI files",
            ),
        ],
        support=support,
    )

    assert run.status == "complete"
    assert run.support == support
    assert [result.response_text for result in run.results] == [
        "done explore-api",
        "done explore-ui",
    ]
    assert run.artifact_path
    artifact = json.loads(Path(run.artifact_path).read_text(encoding="utf-8"))
    assert artifact["status"] == "complete"
    assert artifact["support"]["strategy"] == "orchestrated"
    assert artifact["support"]["available"] is True
    assert artifact["summary"] == {
        "result_count": 2,
        "status_counts": {"complete": 2},
        "complete_result_ids": ["explore-api", "explore-ui"],
        "continue_result_ids": [],
        "error_result_ids": [],
        "cancelled_result_ids": [],
        "artifact_result_ids": [],
        "has_errors": False,
        "has_cancelled": False,
    }
    assert artifact["results"][0]["usage_metadata"] == {
        "input_tokens": 1,
        "output_tokens": 2,
    }
    assert "Auto Code subagent `explore-api`" in created_sessions[0].prompts[0]
    assert '"paths": [' in created_sessions[0].prompts[0]


@pytest.mark.asyncio
async def test_runtime_subagent_orchestrator_times_out_child_sessions(
    tmp_path: Path,
):
    created_sessions: list[SlowSubagentRuntimeSession] = []

    def session_factory(task: RuntimeSubagentTask):
        session = SlowSubagentRuntimeSession(f"done {task.id}")
        created_sessions.append(session)
        return session

    orchestrator = RuntimeSubagentOrchestrator(
        session_factory=session_factory,
        spec_dir=tmp_path,
        max_task_seconds=0.01,
    )
    run = await orchestrator.run(
        [
            RuntimeSubagentTask(
                id="slow-review",
                role="reviewer",
                prompt="Never finishes in time",
            ),
        ]
    )

    assert run.status == "error"
    assert run.results[0].status == "error"
    assert "timed out" in str(run.results[0].error)
    assert created_sessions[0].cancelled is True
    artifact = json.loads(Path(run.artifact_path or "").read_text(encoding="utf-8"))
    assert artifact["summary"]["error_result_ids"] == ["slow-review"]


def test_runtime_subagent_result_summary_counts_mixed_statuses():
    summary = summarize_subagent_results(
        [
            RuntimeSubagentResult(
                id="code",
                role="worker",
                status="complete",
                response_text="done",
                artifacts={"patch": "artifacts/code.patch"},
            ),
            RuntimeSubagentResult(
                id="inspect",
                role="explorer",
                status="continue",
                response_text="needs follow-up",
            ),
            RuntimeSubagentResult(
                id="test",
                role="worker",
                status="error",
                response_text="",
                error="pytest failed",
            ),
            RuntimeSubagentResult(
                id="docs",
                role="worker",
                status="cancelled",
                response_text="cancelled",
            ),
        ]
    )

    assert summary == {
        "result_count": 4,
        "status_counts": {
            "complete": 1,
            "continue": 1,
            "error": 1,
            "cancelled": 1,
        },
        "complete_result_ids": ["code"],
        "continue_result_ids": ["inspect"],
        "error_result_ids": ["test"],
        "cancelled_result_ids": ["docs"],
        "artifact_result_ids": ["code"],
        "has_errors": True,
        "has_cancelled": True,
    }


def test_runtime_subagent_support_distinguishes_native_and_orchestrated():
    native = resolve_runtime_subagent_support(
        provider_name="claude",
        runtime_name="claude_agent_sdk",
        capabilities=RuntimeCapabilities.claude_agent_sdk(),
    )
    assert native.available is True
    assert native.strategy == "native"

    unavailable = resolve_runtime_subagent_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
    )
    assert unavailable.available is False
    assert unavailable.strategy == "unavailable"
    assert "RuntimeSubagentOrchestrator" in unavailable.reason

    orchestrated = resolve_runtime_subagent_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        orchestrator_available=True,
    )
    assert orchestrated.available is True
    assert orchestrated.strategy == "orchestrated"
    assert "not Claude SDK Task tool parity" in orchestrated.reason

    unsupported_child_runtime = resolve_runtime_subagent_support(
        provider_name="custom",
        runtime_name="empty",
        capabilities=RuntimeCapabilities(),
        orchestrator_available=True,
    )
    assert unsupported_child_runtime.available is False
    assert unsupported_child_runtime.missing_capabilities == ("text_completion",)


@pytest.mark.asyncio
async def test_claude_explicit_analysis_mode_uses_limited_runtime(tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name="claude",
        agent_session=FakeClaudeCompletionSession(),
        runtime_mode="analysis_only",
    )

    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert runtime_session.name == "completion"
    assert result.status == "complete"
    assert result.response_text == "claude limited analysis"


@pytest.mark.asyncio
async def test_claude_limited_runtime_manages_query_client_context(tmp_path: Path):
    session = FakeClaudeQuerySession()
    runtime_session = create_runtime_session(
        provider_name="claude",
        agent_session=session,
        runtime_mode="analysis_only",
    )

    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert result.response_text == "query limited analysis"
    assert session.query_message == "analyze"
    assert session.client.entered is True
    assert session.client.exited is True


@pytest.mark.asyncio
async def test_completion_runtime_fails_fast_for_full_coder(tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakeCompletionSession(),
    )

    with pytest.raises(RuntimeCapabilityError) as exc:
        await run_runtime_session(
            runtime_session,
            "edit files",
            tmp_path,
            requirements=RuntimeRequirements.full_coder(),
        )

    message = str(exc.value)
    assert "provider=openai" in message
    assert "filesystem_edit" in message
    assert "native_tool_loop" in message
    assert "shell" in message


def test_create_agent_session_no_longer_requires_client(tmp_path: Path):
    from core.providers import factory

    class DummyProvider:
        name = "openai"

        def create_session(self, session_config):
            return SimpleNamespace(config=session_config, provider_name="openai")

    with (
        patch.object(
            factory.ProviderConfig,
            "from_env",
            return_value=ProviderConfig(provider="openai", openai_model="gpt-4o"),
        ),
        patch.object(factory, "create_engine_provider", return_value=DummyProvider()),
    ):
        session = factory.create_agent_session(
            agent_type="coder",
            project_dir=tmp_path,
            spec_dir=tmp_path / ".auto-claude" / "specs" / "001",
        )

    assert session.provider_name == "openai"
    assert session.config.model is None


class FakePatchProposalSession:
    provider_name = "openai"

    def __init__(self, proposal: dict):
        self.proposal = proposal

    async def complete(self, message: str, stream: bool = True):
        assert "patch proposal mode" in message
        assert stream is True
        yield json.dumps(self.proposal)


class FakeGenericEditSession:
    provider_name = "openai"

    def __init__(self, responses: list[dict]):
        self.responses = [json.dumps(response) for response in responses]
        self.messages: list[str] = []

    async def complete(self, message: str, stream: bool = True):
        assert stream is True
        self.messages.append(message)
        yield self.responses.pop(0)


class FakeBlockingGenericEditSession(FakeGenericEditSession):
    def __init__(self):
        super().__init__([{"actions": [{"tool": "finish", "summary": "done"}]}])
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = False

    async def complete(self, message: str, stream: bool = True):
        assert stream is True
        self.messages.append(message)
        self.started.set()
        await self.release.wait()
        yield self.responses.pop(0)

    async def cancel(self):
        self.cancelled = True
        self.release.set()
        return True


class FakeNativeToolCallSession:
    provider_name = "openai"

    def __init__(self, responses: list[list[dict]]):
        self.responses = responses
        self.messages: list[str | None] = []
        self.tool_schemas: list[list[dict]] = []
        self.tool_results: list[dict] = []

    async def complete_with_tool_calls(self, message: str | None, tools: list[dict]):
        await asyncio.sleep(0)
        self.messages.append(message)
        self.tool_schemas.append(tools)
        tool_calls = [
            SimpleNamespace(
                id=f"call_{len(self.messages)}_{index}",
                name=call["name"],
                arguments=call.get("arguments", {}),
            )
            for index, call in enumerate(self.responses.pop(0), start=1)
        ]
        return SimpleNamespace(content="", tool_calls=tuple(tool_calls))

    def add_tool_result(self, tool_call_id: str, name: str, result: dict):
        self.tool_results.append(
            {"tool_call_id": tool_call_id, "name": name, "result": result}
        )


class FakeNativeToolFailureSession(FakeGenericEditSession):
    async def complete_with_tool_calls(self, message: str | None, tools: list[dict]):
        await asyncio.sleep(0)
        raise RuntimeError("provider rejected tool calls")

    def add_tool_result(self, tool_call_id: str, name: str, result: dict):
        raise AssertionError("tool results should not be added after fallback")


def _init_git_repo(path: Path) -> None:
    run_process(["git", "init"], cwd=path, capture_output=True, check=True)
    run_process(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    run_process(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        capture_output=True,
        check=True,
    )


@pytest.mark.asyncio
async def test_patch_proposal_runtime_applies_valid_unified_diff(tmp_path: Path):
    _init_git_repo(tmp_path)
    target = tmp_path / "hello.txt"
    target.write_text("old\n", encoding="utf-8")

    proposal = {
        "summary": "Update greeting fixture",
        "files": [
            {
                "path": "hello.txt",
                "operation": "modify",
                "patch": """diff --git a/hello.txt b/hello.txt
--- a/hello.txt
+++ b/hello.txt
@@ -1 +1 @@
-old
+new
""",
            }
        ],
        "tests": ["pytest tests/test_hello.py"],
        "risks": [],
    }

    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakePatchProposalSession(proposal),
        runtime_mode="patch_proposal",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change hello.txt",
        tmp_path,
        requirements=RuntimeRequirements.patch_proposal(),
    )

    assert result.status == "continue"
    assert "Update greeting fixture" in result.response_text
    assert "Files:" in result.response_text
    assert "modify: hello.txt" in result.response_text
    assert "patch_summary" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"

    artifact_dir = tmp_path / "artifacts"
    assert (artifact_dir / "patch_proposal.json").exists()
    assert (artifact_dir / "patch.diff").exists()
    assert (artifact_dir / "patch_result.json").exists()
    assert (artifact_dir / "patch_summary.md").exists()
    result_artifact = json.loads(
        (artifact_dir / "patch_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "applied"
    assert result_artifact["subtask_id"] is None
    assert result_artifact["files"] == [{"path": "hello.txt", "operation": "modify"}]
    assert result_artifact["file_count"] == 1
    assert result_artifact["tests"] == ["pytest tests/test_hello.py"]
    assert result_artifact["test_count"] == 1
    summary = (artifact_dir / "patch_summary.md").read_text(encoding="utf-8")
    assert "Patch Proposal Summary" in summary
    assert "`modify` `hello.txt`" in summary
    assert "`pytest tests/test_hello.py`" in summary


@pytest.mark.asyncio
async def test_patch_proposal_runtime_rejects_unsafe_paths(tmp_path: Path):
    _init_git_repo(tmp_path)
    proposal = {
        "summary": "Unsafe edit",
        "files": [
            {
                "path": "../evil.txt",
                "operation": "modify",
                "patch": """diff --git a/../evil.txt b/../evil.txt
--- a/../evil.txt
+++ b/../evil.txt
@@ -1 +1 @@
-old
+new
""",
            }
        ],
        "tests": [],
        "risks": [],
    }

    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakePatchProposalSession(proposal),
        runtime_mode="patch_proposal",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "unsafe edit",
        tmp_path,
        requirements=RuntimeRequirements.patch_proposal(),
    )

    assert result.status == "error"
    assert "unsafe segments" in result.response_text
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "patch_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "error"
    assert result_artifact["files"] == []
    assert result_artifact["file_count"] == 0


def test_patch_path_validator_rejects_sensitive_paths():
    for path in (
        ".env",
        ".env.development",
        ".ssh/id_rsa",
        ".npmrc",
        ".pypirc",
        ".zshrc",
        "secrets/api-key.txt",
    ):
        with pytest.raises(PatchProposalError):
            validate_workspace_relative_path(path)


def test_parse_patch_proposal_handles_braces_inside_strings():
    proposal = parse_patch_proposal(
        'prefix {"summary": "contains { braces }", "files": []} trailing {"ignored": true}'
    )

    assert proposal == {"summary": "contains { braces }", "files": []}


def test_parse_patch_proposal_strips_markdown_fence_without_regex():
    proposal = parse_patch_proposal(
        """```json
{"summary": "fenced", "files": []}
```"""
    )

    assert proposal == {"summary": "fenced", "files": []}


def test_parse_patch_proposal_requires_file_paths():
    with pytest.raises(PatchProposalError, match="field 'path'"):
        parse_patch_proposal(
            json.dumps(
                {
                    "summary": "missing path",
                    "files": [{"patch": "diff --git a/a.txt b/a.txt\n"}],
                }
            )
        )

    with pytest.raises(PatchProposalError, match="field 'path'"):
        parse_patch_proposal(
            json.dumps(
                {
                    "summary": "empty path",
                    "files": [{"path": "", "patch": "diff --git a/a.txt b/a.txt\n"}],
                }
            )
        )


def test_patch_mode_marks_subtask_completed(tmp_path: Path):
    from agents.coder import _mark_patch_subtask_completed

    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test"
    spec_dir.mkdir(parents=True)
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(
        json.dumps(
            {
                "feature": "Test",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "1",
                        "name": "Phase 1",
                        "status": "in_progress",
                        "subtasks": [
                            {
                                "id": "1.1",
                                "description": "Edit file",
                                "status": "pending",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert _mark_patch_subtask_completed(spec_dir, "1.1") is True

    updated = json.loads(plan_file.read_text(encoding="utf-8"))
    subtask = updated["phases"][0]["subtasks"][0]
    assert subtask["status"] == "completed"
    assert subtask["completed_by"] == "patch_proposal"
    assert updated["phases"][0]["status"] == "completed"


def test_local_action_manifest_describes_generic_edit_contract():
    expected_tools = {
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
        "read_file_range",
        "read_many_files",
        "write_file",
        "replace_text",
        "delete_file",
        "move_file",
        "apply_patch",
        "run_command",
        "git_status",
        "git_diff",
        "run_subagents",
        "finish",
    }
    specs = local_action_tool_specs()
    assert {spec.name for spec in specs} == expected_tools

    prompt = render_local_action_prompt()
    for tool_name in expected_tools:
        assert f"- {tool_name}:" in prompt

    response_schema = local_action_response_schema()
    action_schemas = response_schema["properties"]["actions"]["items"]["oneOf"]
    assert {
        schema["properties"]["tool"]["enum"][0] for schema in action_schemas
    } == expected_tools

    provider_schemas = local_action_tool_schemas()
    stat_path_schema = next(
        schema for schema in provider_schemas if schema["name"] == "stat_path"
    )
    assert "path" in stat_path_schema["parameters"]["properties"]
    list_files_schema = next(
        schema for schema in provider_schemas if schema["name"] == "list_files"
    )
    assert "max_entries" in list_files_schema["parameters"]["properties"]
    search_text_schema = next(
        schema for schema in provider_schemas if schema["name"] == "search_text"
    )
    assert search_text_schema["parameters"]["required"] == ["query"]
    assert "max_matches" in search_text_schema["parameters"]["properties"]
    read_file_range_schema = next(
        schema for schema in provider_schemas if schema["name"] == "read_file_range"
    )
    assert read_file_range_schema["parameters"]["required"] == ["path"]
    assert (
        read_file_range_schema["parameters"]["properties"]["max_lines"]["maximum"]
        == 400
    )
    read_many_schema = next(
        schema for schema in provider_schemas if schema["name"] == "read_many_files"
    )
    assert read_many_schema["parameters"]["required"] == ["paths"]
    assert read_many_schema["parameters"]["properties"]["paths"]["maxItems"] == 10
    replace_text_schema = next(
        schema for schema in provider_schemas if schema["name"] == "replace_text"
    )
    assert replace_text_schema["parameters"]["required"] == ["path", "old", "new"]
    assert (
        replace_text_schema["parameters"]["properties"]["old"]["maxLength"]
        == MAX_REPLACE_TEXT_CHARS
    )
    assert (
        replace_text_schema["parameters"]["properties"]["count"]["maximum"]
        == MAX_REPLACE_COUNT
    )
    move_file_schema = next(
        schema for schema in provider_schemas if schema["name"] == "move_file"
    )
    assert move_file_schema["parameters"]["required"] == ["source", "destination"]
    assert "overwrite" in move_file_schema["parameters"]["properties"]
    run_command_schema = next(
        schema for schema in provider_schemas if schema["name"] == "run_command"
    )
    assert run_command_schema["parameters"]["required"] == ["command"]
    assert "timeout" in run_command_schema["parameters"]["properties"]
    git_status_schema = next(
        schema for schema in provider_schemas if schema["name"] == "git_status"
    )
    assert "include_untracked" in git_status_schema["parameters"]["properties"]
    git_diff_schema = next(
        schema for schema in provider_schemas if schema["name"] == "git_diff"
    )
    assert git_diff_schema["parameters"]["properties"]["max_chars"]["maximum"] == (
        MAX_TOOL_OUTPUT_CHARS
    )
    run_subagents_schema = next(
        schema for schema in provider_schemas if schema["name"] == "run_subagents"
    )
    assert run_subagents_schema["parameters"]["required"] == ["tasks"]
    assert (
        run_subagents_schema["parameters"]["properties"]["tasks"]["maxItems"]
        == MAX_SUBAGENT_TASKS
    )


@pytest.mark.asyncio
async def test_local_actions_inspect_git_status_and_diff(tmp_path: Path):
    _init_git_repo(tmp_path)
    target = tmp_path / "hello.txt"
    target.write_text("old\n", encoding="utf-8")
    run_process(
        ["git", "add", "hello.txt"], cwd=tmp_path, capture_output=True, check=True
    )
    run_process(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    target.write_text("new\n", encoding="utf-8")

    executor = LocalActionExecutor(tmp_path)
    status = await executor.execute({"tool": "git_status"})
    diff = await executor.execute(
        {"tool": "git_diff", "path": "hello.txt", "max_chars": 1000}
    )
    stat = await executor.execute(
        {"tool": "git_diff", "path": "hello.txt", "stat": True}
    )

    assert status.ok is True
    assert "hello.txt" in status.data["changed_files"]
    assert status.data["changed_file_count"] == 1
    assert diff.ok is True
    assert "--- a/hello.txt" in diff.data["diff"]
    assert "-old" in diff.data["diff"]
    assert "+new" in diff.data["diff"]
    assert diff.data["truncated"] is False
    assert stat.ok is True
    assert "hello.txt" in stat.data["diff"]


@pytest.mark.asyncio
async def test_local_action_executor_stats_paths_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    file_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": "src/app.py",
        }
    )

    assert file_result.ok is True
    assert file_result.data["exists"] is True
    assert file_result.data["type"] == "file"
    assert file_result.data["bytes"] > 0

    dir_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": "src",
        }
    )
    assert dir_result.ok is True
    assert dir_result.data["type"] == "directory"
    assert "bytes" not in dir_result.data

    missing_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": "src/missing.py",
        }
    )
    assert missing_result.ok is True
    assert missing_result.data["exists"] is False
    assert missing_result.data["type"] == "missing"

    sensitive_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": ".env",
        }
    )
    assert sensitive_result.ok is False


@pytest.mark.asyncio
async def test_local_action_executor_lists_files_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: ci\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "list_files",
            "recursive": True,
            "max_entries": 20,
        }
    )

    assert result.ok is True
    paths = [entry["path"] for entry in result.data["entries"]]
    assert "README.md" in paths
    assert "src" in paths
    assert "src/app.py" in paths
    assert ".env" not in paths
    assert ".github" not in paths
    assert ".github/workflows/ci.yml" not in paths
    assert "node_modules" not in paths
    app_entry = next(
        entry for entry in result.data["entries"] if entry["path"] == "src/app.py"
    )
    assert app_entry["type"] == "file"
    assert app_entry["bytes"] > 0

    hidden_result = await executor.execute(
        {
            "tool": "list_files",
            "path": ".github",
            "recursive": True,
            "include_hidden": True,
        }
    )
    hidden_paths = [entry["path"] for entry in hidden_result.data["entries"]]
    assert hidden_result.ok is True
    assert ".github/workflows/ci.yml" in hidden_paths

    truncated_result = await executor.execute(
        {
            "tool": "list_files",
            "recursive": True,
            "max_entries": 1,
        }
    )
    assert truncated_result.ok is True
    assert truncated_result.data["entry_count"] == 1
    assert truncated_result.data["truncated"] is True


@pytest.mark.asyncio
async def test_local_action_executor_searches_text_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "def target_handler():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("TARGET_HANDLER docs\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TARGET_HANDLER_SECRET=1\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: target_handler\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text(
        "target_handler\n",
        encoding="utf-8",
    )
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "search_text",
            "query": "target_handler",
            "path": ".",
            "max_matches": 20,
        }
    )

    assert result.ok is True
    paths = [match["path"] for match in result.data["matches"]]
    assert "README.md" in paths
    assert "src/app.py" in paths
    assert ".env" not in paths
    assert ".github/workflows/ci.yml" not in paths
    assert "node_modules/pkg.js" not in paths
    app_match = next(
        match for match in result.data["matches"] if match["path"] == "src/app.py"
    )
    assert app_match["line"] == 1
    assert "target_handler" in app_match["excerpt"]

    hidden_result = await executor.execute(
        {
            "tool": "search_text",
            "query": "target_handler",
            "path": ".github",
            "include_hidden": True,
        }
    )
    hidden_paths = [match["path"] for match in hidden_result.data["matches"]]
    assert hidden_result.ok is True
    assert ".github/workflows/ci.yml" in hidden_paths

    truncated_result = await executor.execute(
        {
            "tool": "search_text",
            "query": "target_handler",
            "max_matches": 1,
        }
    )
    assert truncated_result.ok is True
    assert truncated_result.data["match_count"] == 1
    assert truncated_result.data["truncated"] is True


def test_search_text_trace_redacts_query_and_excerpts():
    request = safe_action_for_trace(
        {
            "tool": "search_text",
            "query": "SECRET_NEEDLE",
            "path": ".",
        }
    )
    result = safe_result_for_trace(
        ToolActionResult(
            tool="search_text",
            ok=True,
            message="Found 1 line match under .",
            data={
                "matches": [
                    {
                        "path": "src/app.py",
                        "line": 1,
                        "excerpt": "const token = 'SECRET_NEEDLE'",
                    }
                ],
            },
        )
    )

    assert request["query_redacted"] is True
    assert request["query_bytes"] == len("SECRET_NEEDLE")
    assert "query" not in request
    excerpt = result["data"]["matches"][0]["excerpt_redacted"]
    assert excerpt is True
    assert "SECRET_NEEDLE" not in json.dumps(result)


@pytest.mark.asyncio
async def test_local_action_executor_reads_file_ranges_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "\n".join(
            [
                "line one",
                "line two",
                "line three",
                "line four",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "read_file_range",
            "path": "src/app.py",
            "start_line": 2,
            "max_lines": 2,
        }
    )

    assert result.ok is True
    assert result.data["start_line"] == 2
    assert result.data["end_line"] == 3
    assert result.data["line_count"] == 2
    assert result.data["truncated"] is True
    assert result.data["content"] == "2: line two\n3: line three"
    assert result.data["lines"] == [
        {"line": 2, "text": "line two"},
        {"line": 3, "text": "line three"},
    ]
    assert safe_result_for_trace(result)["data"]["lines"][0]["text_redacted"] is True

    missing_result = await executor.execute(
        {
            "tool": "read_file_range",
            "path": "src/missing.py",
        }
    )
    assert missing_result.ok is False


@pytest.mark.asyncio
async def test_local_action_executor_reads_many_files_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "src" / "two.py").write_text("two line\n", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "read_many_files",
            "paths": ["src/one.py", "src/two.py", "src/missing.py"],
            "max_chars_per_file": 3,
        }
    )

    assert result.ok is False
    assert result.data["file_count"] == 3
    assert result.data["read_count"] == 2
    files_by_path = {file["path"]: file for file in result.data["files"]}
    assert files_by_path["src/one.py"]["content"] == "one"
    assert files_by_path["src/one.py"]["truncated"] is True
    assert files_by_path["src/two.py"]["content"] == "two"
    assert files_by_path["src/missing.py"]["ok"] is False
    assert "content" not in files_by_path["src/missing.py"]


@pytest.mark.asyncio
async def test_local_action_executor_mutates_files_with_bounded_actions(
    tmp_path: Path,
):
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "app.py"
    target.write_text("old_name = 1\nold_name = 2\n", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    replace_result = await executor.execute(
        {
            "tool": "replace_text",
            "path": "src/app.py",
            "old": "old_name",
            "new": "new_name",
            "count": 1,
        }
    )

    assert replace_result.ok is True
    assert replace_result.data["replacements"] == 1
    assert replace_result.data["remaining_occurrences"] == 1
    assert target.read_text(encoding="utf-8") == "new_name = 1\nold_name = 2\n"
    safe_request = safe_action_for_trace(
        {
            "tool": "replace_text",
            "path": "src/app.py",
            "old": "old_name",
            "new": "new_name",
        }
    )
    assert safe_request["old_redacted"] is True
    assert safe_request["new_redacted"] is True
    assert "old_name" not in json.dumps(safe_request)

    move_result = await executor.execute(
        {
            "tool": "move_file",
            "source": "src/app.py",
            "destination": "src/renamed.py",
        }
    )

    assert move_result.ok is True
    assert not target.exists()
    moved = tmp_path / "src" / "renamed.py"
    assert moved.read_text(encoding="utf-8").startswith("new_name")

    delete_result = await executor.execute(
        {
            "tool": "delete_file",
            "path": "src/renamed.py",
        }
    )

    assert delete_result.ok is True
    assert not moved.exists()


@pytest.mark.asyncio
async def test_local_action_executor_rejects_unsafe_file_mutations(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("hello\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    replace_missing = await executor.execute(
        {
            "tool": "replace_text",
            "path": "src/app.py",
            "old": "missing",
            "new": "",
        }
    )
    delete_sensitive = await executor.execute(
        {
            "tool": "delete_file",
            "path": ".env",
        }
    )
    move_over_existing = await executor.execute(
        {
            "tool": "move_file",
            "source": "src/app.py",
            "destination": ".env",
        }
    )

    assert replace_missing.ok is False
    assert "not found" in replace_missing.message
    assert delete_sensitive.ok is False
    assert move_over_existing.ok is False
    assert (tmp_path / "src" / "app.py").exists()
    assert (tmp_path / ".env").exists()


@pytest.mark.asyncio
async def test_generic_edit_runtime_runs_local_action_loop(tmp_path: Path):
    target = tmp_path / "hello.txt"
    trace_marker = "TRACE_REDACTION_MARKER"
    target.write_text(f"old\n{trace_marker}\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "inspect target",
                "actions": [{"tool": "read_file", "path": "hello.txt"}],
            },
            {
                "thought": "replace content",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "hello.txt",
                        "content": "new\n",
                    }
                ],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Updated greeting through generic edit",
                        "tests": ["not run"],
                        "risks": [],
                    }
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change hello.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.1",
    )

    assert result.status == "continue"
    assert "Updated greeting through generic edit" in result.response_text
    assert "generic_edit_summary" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(session.messages) == 3
    assert "generic_edit mode" in session.messages[0]
    assert render_local_action_prompt() in session.messages[0]
    assert "observations" in session.messages[1]
    assert "generic_edit mode" in session.messages[1]
    assert "change hello.txt" in session.messages[1]

    artifact_dir = tmp_path / "artifacts"
    assert (artifact_dir / "generic_edit_trace.json").exists()
    assert (artifact_dir / "generic_edit_timeline.json").exists()
    assert (artifact_dir / "generic_edit_result.json").exists()
    assert (artifact_dir / "generic_edit_summary.md").exists()
    assert (artifact_dir / "generic_edit_observations.jsonl").exists()
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["stop_reason"] == "finish"
    assert result_artifact["subtask_id"] == "1.1"
    assert result_artifact["iteration_count"] == 3
    assert result_artifact["loop"] == "json_actions"
    assert result_artifact["action_count"] == 3
    assert result_artifact["failed_action_count"] == 0
    assert result_artifact["tool_counts"] == {
        "read_file": 1,
        "write_file": 1,
        "finish": 1,
    }
    assert result_artifact["failed_tools"] == {}
    assert result_artifact["mcp_support"]["strategy"] == "unavailable"
    assert result_artifact["observation_artifact"].endswith(
        "generic_edit_observations.jsonl"
    )
    assert result_artifact["action_timeline"] == [
        {
            "iteration": 1,
            "tool": "read_file",
            "ok": True,
            "message": "Read hello.txt",
            "path": "hello.txt",
            "truncated": False,
        },
        {
            "iteration": 2,
            "tool": "write_file",
            "ok": True,
            "message": "Wrote hello.txt",
            "path": "hello.txt",
        },
        {
            "iteration": 3,
            "tool": "finish",
            "ok": True,
            "message": "Updated greeting through generic edit",
        },
    ]
    assert result_artifact["tests"] == ["not run"]

    trace_text = (artifact_dir / "generic_edit_trace.json").read_text(encoding="utf-8")
    assert trace_marker not in trace_text
    trace = json.loads(trace_text)
    read_result = trace["trace"][0]["actions"][0]["result"]
    assert read_result["data"]["content_redacted"] is True
    assert read_result["data"]["content_bytes"] > 0
    assert "response_excerpt" in trace["trace"][0]
    assert "response" not in trace["trace"][0]
    timeline = json.loads(
        (artifact_dir / "generic_edit_timeline.json").read_text(encoding="utf-8")
    )
    assert timeline["stop_reason"] == "finish"
    assert timeline["timeline"] == result_artifact["action_timeline"]
    observation_lines = [
        json.loads(line)
        for line in (artifact_dir / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [line["result"]["tool"] for line in observation_lines] == [
        "read_file",
        "write_file",
        "finish",
    ]
    assert observation_lines[0]["loop"] == "json_actions"
    assert observation_lines[0]["result"]["data"]["content_redacted"] is True
    assert trace_marker not in (
        artifact_dir / "generic_edit_observations.jsonl"
    ).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_generic_edit_runtime_cancel_stops_action_loop(tmp_path: Path):
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    session = FakeBlockingGenericEditSession()
    runtime_session = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=session,
        project_dir=tmp_path,
    )

    run_task = asyncio.create_task(
        run_runtime_session(
            runtime_session,
            "cancel generic edit",
            tmp_path,
            requirements=RuntimeRequirements.generic_edit(),
        )
    )
    await session.started.wait()

    assert await runtime_session.cancel() is True
    result = await run_task

    assert session.cancelled is True
    assert result.status == "cancelled"
    assert not (tmp_path / "artifacts" / "generic_edit_trace.json").exists()


@pytest.mark.asyncio
async def test_generic_edit_runtime_runs_orchestrated_subagents(tmp_path: Path):
    created_sessions: list[FakeSubagentRuntimeSession] = []

    def session_factory(task: RuntimeSubagentTask):
        session = FakeSubagentRuntimeSession(f"findings from {task.id}")
        created_sessions.append(session)
        return session

    session = FakeGenericEditSession(
        [
            {
                "thought": "parallel analysis",
                "actions": [
                    {
                        "tool": "run_subagents",
                        "tasks": [
                            {
                                "id": "inspect-api",
                                "role": "explorer",
                                "prompt": "Inspect API files",
                                "metadata": {"paths": ["apps/backend"]},
                            },
                            {
                                "id": "inspect-ui",
                                "role": "reviewer",
                                "prompt": "Review UI settings",
                            },
                        ],
                    }
                ],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Used runtime subagents",
                        "tests": [],
                        "risks": [],
                    }
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
        subagent_session_factory=session_factory,
    )

    result = await run_runtime_session(
        runtime_session,
        "inspect independently",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.1",
    )

    assert result.status == "continue"
    assert len(created_sessions) == 2
    assert "Auto Code subagent `inspect-api`" in created_sessions[0].prompts[0]
    assert "findings from inspect-api" in session.messages[1]
    artifact_path = tmp_path / "artifacts" / "generic_edit_subagents_1_1_1.json"
    assert artifact_path.exists()
    subagent_artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert subagent_artifact["status"] == "complete"
    assert subagent_artifact["support"]["strategy"] == "orchestrated"
    assert subagent_artifact["summary"]["result_count"] == 2

    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    request = trace["trace"][0]["actions"][0]["request"]
    assert request["tool"] == "run_subagents"
    assert request["tasks_redacted"] is True
    assert request["task_count"] == 2


@pytest.mark.asyncio
async def test_generic_edit_runtime_bridges_auto_claude_mcp_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    async def get_build_progress(args):
        assert args == {}
        return {"content": [{"type": "text", "text": "Build Progress: 0/1 subtasks"}]}

    monkeypatch.setattr("agents.runtime.mcp_bridge.is_tools_available", lambda: True)
    monkeypatch.setattr(
        "agents.runtime.mcp_bridge.create_all_tools",
        lambda spec_dir, project_dir: [
            SimpleNamespace(
                name="get_build_progress",
                description="Get build progress",
                input_schema={},
                handler=get_build_progress,
            )
        ],
    )
    session = FakeGenericEditSession(
        [
            {
                "thought": "check progress",
                "actions": [{"tool": "mcp__auto-claude__get_build_progress"}],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Checked bridged MCP progress",
                        "tests": [],
                        "risks": [],
                    }
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
        agent_type="coder",
    )

    result = await run_runtime_session(
        runtime_session,
        "check build progress",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert "Checked bridged MCP progress" in result.response_text
    assert "mcp__auto-claude__get_build_progress" in session.messages[0]
    assert "Build Progress: 0/1 subtasks" in session.messages[1]
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert observation_lines[0]["result"]["tool"] == (
        "mcp__auto-claude__get_build_progress"
    )
    assert observation_lines[0]["result"]["data"]["server"] == "auto-claude"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["mcp_support"]["strategy"] == "local_bridge"
    assert result_artifact["mcp_support"]["server"] == "auto-claude"
    assert result_artifact["mcp_support"]["tool_count"] == 1
    assert result_artifact["mcp_support"]["bridge"]["tools"] == [
        "mcp__auto-claude__get_build_progress"
    ]
    bridge_statuses = {
        status["server"]: status
        for status in result_artifact["mcp_support"]["bridge"]["server_statuses"]
    }
    assert bridge_statuses["auto-claude"]["runtime_path"] == "local_bridge"
    assert bridge_statuses["context7"]["runtime_path"] == "native_required"
    assert bridge_statuses["graphiti"]["runtime_path"] == "native_required"


def test_runtime_mcp_bridge_filters_agent_allowed_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("agents.runtime.mcp_bridge.is_tools_available", lambda: True)
    monkeypatch.setattr(
        "agents.runtime.mcp_bridge.create_all_tools",
        lambda spec_dir, project_dir: [
            SimpleNamespace(
                name="update_subtask_status",
                description="Update subtask",
                input_schema={"subtask_id": str, "status": str},
                handler=lambda args: {},
            ),
            SimpleNamespace(
                name="update_qa_status",
                description="Update QA",
                input_schema={"status": str},
                handler=lambda args: {},
            ),
            SimpleNamespace(
                name="search_team_docs",
                description="Search docs",
                input_schema={"query": str},
                handler=lambda args: {},
            ),
        ],
    )
    session = SimpleNamespace(agent_type="qa_fixer")

    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    schemas = bridge.provider_tool_schemas()
    schema_names = {schema["name"] for schema in schemas}
    assert "mcp__auto-claude__update_subtask_status" in schema_names
    assert "mcp__auto-claude__update_qa_status" in schema_names
    assert "mcp__auto-claude__search_team_docs" not in schema_names
    support = bridge.support_for(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
    )
    assert support.strategy == "local_bridge"
    assert support.server == "auto-claude"
    assert support.tool_count == 2


def test_runtime_mcp_bridge_reports_external_server_gaps(tmp_path: Path):
    from agents.runtime.adapters.generic_edit import render_mcp_bridge_prompt

    session = SimpleNamespace(agent_type="spec_researcher")

    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    assert bridge.has_tools is False
    assert bridge.requested_servers == ("context7",)
    assert bridge.available_servers == ()
    assert bridge.unavailable_servers == ("context7",)
    assert "context7" in render_mcp_bridge_prompt(bridge)

    support = bridge.support_for(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
    )
    support_payload = support.to_dict()
    assert support.strategy == "unavailable"
    assert support_payload["requested_servers"] == ["context7"]
    assert support_payload["available_servers"] == []
    assert support_payload["unavailable_servers"] == ["context7"]
    assert support_payload["server_statuses"][0]["server"] == "context7"
    assert support_payload["server_statuses"][0]["runtime_path"] == "native_required"
    assert support_payload["server_statuses"][0]["bridgeable"] is False


def test_runtime_mcp_support_distinguishes_native_and_local_bridge():
    native = resolve_runtime_mcp_support(
        provider_name="claude",
        runtime_name="claude_agent_sdk",
        capabilities=RuntimeCapabilities.claude_agent_sdk(),
        requested_servers=("context7", "graphiti-memory"),
    )
    assert native.available is True
    assert native.strategy == "native"
    assert native.available_servers == ("context7", "graphiti")
    assert [status["runtime_path"] for status in native.server_statuses] == [
        "native",
        "native",
    ]

    unavailable = resolve_runtime_mcp_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        requested_servers=("context7",),
    )
    assert unavailable.available is False
    assert unavailable.strategy == "unavailable"
    assert unavailable.unavailable_servers == ("context7",)
    assert unavailable.server_statuses[0]["runtime_path"] == "native_required"

    local_bridge = resolve_runtime_mcp_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        bridge_available=True,
        tool_count=3,
        requested_servers=("context7", "auto-claude"),
        available_servers=("auto-claude",),
    )
    assert local_bridge.available is True
    assert local_bridge.strategy == "local_bridge"
    assert local_bridge.tool_count == 3
    assert local_bridge.available_servers == ("auto-claude",)
    assert local_bridge.unavailable_servers == ("context7",)
    assert [status["runtime_path"] for status in local_bridge.server_statuses] == [
        "native_required",
        "local_bridge",
    ]
    assert "external MCP servers" in local_bridge.reason

    unsupported_bridge_runtime = resolve_runtime_mcp_support(
        provider_name="custom",
        runtime_name="completion",
        capabilities=RuntimeCapabilities.completion_only(),
        bridge_available=True,
        tool_count=1,
    )
    assert unsupported_bridge_runtime.available is False
    assert "cannot expose" in unsupported_bridge_runtime.reason


def test_runtime_mcp_server_statuses_explain_bridgeable_and_native_gaps():
    statuses = describe_mcp_server_statuses(
        requested_servers=("auto-claude", "context7", "browser", "custom-mcp"),
        available_servers=("auto-claude",),
        native_available=False,
    )

    status_by_server = {status["server"]: status for status in statuses}
    assert status_by_server["auto-claude"]["runtime_path"] == "local_bridge"
    assert status_by_server["auto-claude"]["bridgeable"] is True
    assert status_by_server["context7"]["runtime_path"] == "native_required"
    assert status_by_server["browser"]["runtime_path"] == "native_required"
    assert status_by_server["browser"]["display_name"] == "Browser automation"
    assert status_by_server["custom-mcp"]["runtime_path"] == "unsupported"


@pytest.mark.asyncio
async def test_generic_edit_runtime_records_partial_transactions_for_recovery(
    tmp_path: Path,
):
    target = tmp_path / "partial.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "edit then inspect missing file",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "partial.txt",
                        "content": "new\n",
                    },
                    {
                        "tool": "read_file",
                        "path": "missing.txt",
                    },
                ],
            },
            {
                "thought": "partial state is acceptable",
                "actions": [
                    {
                        "tool": "read_file",
                        "path": "partial.txt",
                    },
                    {
                        "tool": "finish",
                        "summary": "Recovered after partial action failure",
                        "tests": [],
                        "risks": [],
                    },
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change partial.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert target.read_text(encoding="utf-8") == "new\n"
    assert "partial_failure" in session.messages[1]
    assert "workspace is consistent" in session.messages[1]

    artifact_dir = tmp_path / "artifacts"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["transaction_count"] == 2
    assert result_artifact["partial_failure_count"] == 1
    assert result_artifact["recovery_required"] is True
    assert result_artifact["transaction_status_counts"] == {
        "partial_failure": 1,
        "complete": 1,
    }
    assert result_artifact["partial_failure_transaction_ids"] == ["json_actions-1"]
    assert result_artifact["recovery_transaction_ids"] == ["json_actions-2"]
    assert result_artifact["recovery_resolved"] is True
    assert result_artifact["unresolved_partial_failure_count"] == 0
    first_transaction = result_artifact["transactions"][0]
    assert first_transaction["status"] == "partial_failure"
    assert first_transaction["failed_at_action_index"] == 2
    assert first_transaction["failed_tool"] == "read_file"
    assert first_transaction["mutating_tools"] == ["write_file"]
    assert first_transaction["tool_sequence"] == ["write_file", "read_file"]
    assert first_transaction["affected_paths"] == ["missing.txt", "partial.txt"]
    assert first_transaction["mutated_paths"] == ["partial.txt"]
    assert first_transaction["can_resolve_partial_failure"] is False
    second_transaction = result_artifact["transactions"][1]
    assert second_transaction["tool_sequence"] == ["read_file", "finish"]
    assert second_transaction["can_resolve_partial_failure"] is True
    transaction_lines = [
        json.loads(line)
        for line in (artifact_dir / "generic_edit_transactions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [line["status"] for line in transaction_lines] == [
        "partial_failure",
        "complete",
    ]
    summary_markdown = (artifact_dir / "generic_edit_summary.md").read_text(
        encoding="utf-8"
    )
    assert "## Recovery" in summary_markdown
    assert "Recovery state: resolved" in summary_markdown


def test_generic_edit_transaction_summary_marks_unresolved_partial_failure():
    summary = summarize_generic_edit_transactions(
        [
            {
                "transaction": {
                    "id": "json_actions-1",
                    "status": "partial_failure",
                    "recovery_required": True,
                }
            }
        ]
    )

    assert summary["partial_failure_count"] == 1
    assert summary["partial_failure_transaction_ids"] == ["json_actions-1"]
    assert summary["recovery_required"] is True
    assert summary["recovery_resolved"] is False
    assert summary["unresolved_partial_failure_count"] == 1
    assert summary["unresolved_partial_failure_ids"] == ["json_actions-1"]


def test_generic_edit_transaction_summary_does_not_treat_finish_as_recovery():
    summary = summarize_generic_edit_transactions(
        [
            {
                "transaction": {
                    "id": "json_actions-1",
                    "status": "partial_failure",
                    "recovery_required": True,
                }
            },
            {
                "transaction": {
                    "id": "json_actions-2",
                    "status": "complete",
                    "tool_sequence": ["finish"],
                    "can_resolve_partial_failure": False,
                }
            },
        ]
    )

    assert summary["partial_failure_count"] == 1
    assert summary["recovery_transaction_ids"] == []
    assert summary["recovery_resolved"] is False
    assert summary["unresolved_partial_failure_ids"] == ["json_actions-1"]


@pytest.mark.asyncio
async def test_generic_edit_runtime_prefers_native_tool_call_loop(tmp_path: Path):
    target = tmp_path / "native.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolCallSession(
        [
            [{"name": "read_file", "arguments": {"path": "native.txt"}}],
            [
                {
                    "name": "write_file",
                    "arguments": {
                        "path": "native.txt",
                        "content": "new\n",
                    },
                }
            ],
            [
                {
                    "name": "finish",
                    "arguments": {
                        "summary": "Updated through native tool calls",
                        "tests": ["not run"],
                        "risks": [],
                    },
                }
            ],
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change native.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.3",
    )

    assert result.status == "continue"
    assert "Updated through native tool calls" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert session.messages[0] is not None
    assert "function calls" in session.messages[0]
    assert session.messages[1:] == [None, None]
    assert [schema["name"] for schema in session.tool_schemas[0]][:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert [result["name"] for result in session.tool_results] == [
        "read_file",
        "write_file",
        "finish",
    ]

    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    assert trace["trace"][0]["loop"] == "native_tool_calls"
    assert trace["trace"][0]["actions"][0]["request"]["tool"] == "read_file"
    assert trace["trace"][0]["actions"][0]["result"]["data"]["content_redacted"]
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["subtask_id"] == "1.3"
    assert result_artifact["stop_reason"] == "finish"
    assert result_artifact["iteration_count"] == 3
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 3
    assert result_artifact["tool_counts"]["finish"] == 1
    assert result_artifact["action_timeline"][0]["tool_call_id"] == "call_1_1"
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert observation_lines[0]["loop"] == "native_tool_calls"
    assert observation_lines[0]["request"]["tool_call_id"] == "call_1_1"
    assert [line["result"]["tool"] for line in observation_lines] == [
        "read_file",
        "write_file",
        "finish",
    ]


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_non_terminal_json_finish(tmp_path: Path):
    target = tmp_path / "after-finish.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "done too early",
                    },
                    {
                        "tool": "write_file",
                        "path": "after-finish.txt",
                        "content": "new\n",
                    },
                ],
            }
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "reject non-terminal finish",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "finish" in result.response_text
    assert target.read_text(encoding="utf-8") == "old\n"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["stop_reason"] == "non_terminal_finish"


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_non_terminal_native_finish(
    tmp_path: Path,
):
    target = tmp_path / "after-native-finish.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolCallSession(
        [
            [
                {
                    "name": "finish",
                    "arguments": {"summary": "done too early"},
                },
                {
                    "name": "write_file",
                    "arguments": {
                        "path": "after-native-finish.txt",
                        "content": "new\n",
                    },
                },
            ]
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "reject native non-terminal finish",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "finish" in result.response_text
    assert target.read_text(encoding="utf-8") == "old\n"
    assert session.tool_results == []
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["stop_reason"] == "non_terminal_finish"


@pytest.mark.asyncio
async def test_generic_edit_runtime_falls_back_when_native_tools_rejected(
    tmp_path: Path,
):
    target = tmp_path / "fallback.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolFailureSession(
        [
            {
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "fallback.txt",
                        "content": "new\n",
                    },
                    {
                        "tool": "finish",
                        "summary": "Fallback JSON loop completed",
                        "tests": [],
                    },
                ],
            }
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change fallback.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert "Fallback JSON loop completed" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(session.messages) == 1
    assert "Respond with exactly one JSON object" in session.messages[0]
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    assert "loop" not in trace["trace"][0]


@pytest.mark.asyncio
async def test_local_action_executor_rejects_command_chaining(tmp_path: Path):
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "run_command",
            "command": "git status --short && git status --short",
        }
    )

    assert result.ok is False
    assert result.tool == "run_command"
    assert "one command at a time" in result.message


@pytest.mark.asyncio
async def test_local_action_executor_bounds_read_before_returning(tmp_path: Path):
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "read_file",
            "path": "large.txt",
            "max_chars": 3,
        }
    )

    assert result.ok is True
    assert result.data["content"] == "abc"
    assert result.data["truncated"] is True


@pytest.mark.asyncio
async def test_local_action_executor_rejects_zero_limits(tmp_path: Path):
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    read_result = await executor.execute(
        {
            "tool": "read_file",
            "path": "large.txt",
            "max_chars": 0,
        }
    )
    command_result = await executor.execute(
        {
            "tool": "run_command",
            "command": "git status --short",
            "timeout": 0,
        }
    )

    assert read_result.ok is False
    assert "greater than 0" in read_result.message
    assert command_result.ok is False
    assert "greater than 0" in command_result.message


@pytest.mark.asyncio
async def test_local_action_executor_bounds_command_output(tmp_path: Path):
    executor = LocalActionExecutor(tmp_path)

    completed = await executor._run_subprocess_bounded(
        [sys.executable, "-c", "print('x' * 20000)"],
        timeout=10,
    )

    assert completed.truncated is True
    assert len(completed.output) <= MAX_TOOL_OUTPUT_CHARS


@pytest.mark.asyncio
async def test_generic_edit_runtime_runs_validated_single_command(tmp_path: Path):
    _init_git_repo(tmp_path)
    session = FakeGenericEditSession(
        [
            {
                "actions": [
                    {
                        "tool": "run_command",
                        "command": "git status --short",
                        "timeout": 10,
                    }
                ],
            },
            {
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Validated command completed",
                        "tests": ["git status --short"],
                    }
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "check repository",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    command_result = trace["trace"][0]["actions"][0]["result"]
    assert command_result["ok"] is True
    assert command_result["data"]["exit_code"] == 0


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_unsafe_write_path(tmp_path: Path):
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    session = FakeGenericEditSession(
        [
            {
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "../evil.txt",
                        "content": "bad\n",
                    },
                    {
                        "tool": "finish",
                        "summary": "should not finish while action failed",
                    },
                ],
            }
        ]
    )
    runtime_session = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=session,
        project_dir=tmp_path,
        max_iterations=1,
    )

    result = await run_runtime_session(
        runtime_session,
        "unsafe write",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "max iterations" in result.response_text
    assert not (tmp_path.parent / "evil.txt").exists()
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    assert len(trace["trace"][0]["actions"]) == 1
    first_result = trace["trace"][0]["actions"][0]["result"]
    assert first_result["ok"] is False
    assert "unsafe segments" in first_result["message"]


def test_runtime_mode_env_resolution(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTO_CODE_RUNTIME_MODE", "patch-proposal")
    assert get_runtime_mode("coder") == "patch_proposal"
    monkeypatch.setenv("AGENT_RUNTIME_MODE_CODER", "analysis-only")
    assert get_runtime_mode("coder") == "analysis_only"
    assert normalize_runtime_mode("full-autonomous") == "full_autonomous"
    assert normalize_runtime_mode("generic-edit") == "generic_edit"


def test_runtime_fallback_is_explicit_and_capability_aware(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AUTO_CODE_RUNTIME_FALLBACK", raising=False)
    assert runtime_fallback_enabled() is False

    fail_fast = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )
    assert fail_fast.selected_mode == "full_autonomous"
    assert fail_fast.fallback_applied is False
    assert "disabled" in fail_fast.reason
    assert fail_fast.missing_capabilities == (
        "native_tool_loop",
        "filesystem_edit",
        "shell",
    )
    assert fail_fast.compatible_fallbacks == (
        "generic_edit",
        "patch_proposal",
        "analysis_only",
    )
    fail_fast_payload = fail_fast.to_dict()
    assert fail_fast_payload["runner_candidates"]["selected_runner_id"] is None
    assert fail_fast_payload["runner_candidates"]["selected_mode"] == (
        "full_autonomous"
    )
    assert fail_fast_payload["runner_candidates"]["modes"]["full_autonomous"][
        "selected_runner_ids"
    ] == ["codex_cli", "claude_code", "zai_claude_code"]
    assert fail_fast_payload["runner_candidates"]["modes"]["generic_edit"][
        "selected_runner_ids"
    ] == ["aider", "cursor_cli", "opencode", "goose", "amp", "qwen_code"]

    monkeypatch.setenv("AUTO_CODE_RUNTIME_FALLBACK", "true")
    degraded = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )
    assert degraded.selected_mode == "generic_edit"
    assert degraded.fallback_applied is True
    assert "using generic_edit" in degraded.reason
    assert degraded.to_dict()["compatible_fallbacks"] == [
        "generic_edit",
        "patch_proposal",
        "analysis_only",
    ]
    degraded_payload = degraded.to_dict()
    assert degraded_payload["runner_candidates"]["selected_mode"] == "generic_edit"
    assert degraded_payload["runner_candidates"]["selected_mode_runner_candidates"] == [
        "aider",
        "cursor_cli",
        "opencode",
        "goose",
        "amp",
        "qwen_code",
    ]

    claude = resolve_runtime_mode_with_fallback(
        provider_name="claude",
        requested_mode="full_autonomous",
        phase="coding",
    )
    assert claude.selected_mode == "full_autonomous"
    assert claude.fallback_applied is False

    analysis = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="analysis",
    )
    assert analysis.selected_mode == "full_autonomous"
    assert analysis.fallback_applied is False


def test_runtime_fallback_artifact_records_capability_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AUTO_CODE_RUNTIME_FALLBACK", "true")
    decision = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )

    artifact_path = save_runtime_fallback_artifact(
        spec_dir=tmp_path,
        decision=decision,
        phase="coding",
        session_num=2,
        subtask_id="1.2",
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "coding"
    assert payload["session"] == 2
    assert payload["subtask_id"] == "1.2"
    assert payload["decision"]["provider"] == "openai"
    assert payload["decision"]["requested_mode"] == "full_autonomous"
    assert payload["decision"]["selected_mode"] == "generic_edit"
    assert payload["decision"]["fallback_applied"] is True
    assert payload["decision"]["missing_capabilities"] == [
        "native_tool_loop",
        "filesystem_edit",
        "shell",
    ]
    assert payload["decision"]["runner_candidates"]["selected_mode"] == ("generic_edit")
    assert payload["decision"]["runner_candidates"][
        "selected_mode_runner_candidates"
    ] == ["aider", "cursor_cli", "opencode", "goose", "amp", "qwen_code"]


def test_runtime_runner_router_is_explicit_for_direct_full_autonomous(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AUTO_CODE_CLI_RUNNER_ROUTER", raising=False)
    assert runtime_runner_router_enabled() is False

    route = resolve_runtime_runner_route(
        provider_config=ProviderConfig(provider="openai"),
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )

    assert route.route_applied is False
    assert route.status == "disabled"
    assert route.selected_provider == "openai"
    assert route.runner_selection
    assert route.runner_selection.selected_runner_ids[:1] == ("codex_cli",)


def test_runtime_runner_router_routes_to_wired_codex_cli(tmp_path: Path):
    codex_bin = tmp_path / "codex"
    codex_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text("{}", encoding="utf-8")
    config = ProviderConfig(
        provider="openai",
        codex_cli_path=str(codex_bin),
        codex_home=str(codex_home),
    )

    route = resolve_runtime_runner_route(
        provider_config=config,
        provider_name="openai",
        requested_mode="full-autonomous",
        phase="coding",
        allow_router=True,
    )

    assert route.route_applied is True
    assert route.status == "routed"
    assert route.selected_provider == "codex"
    assert route.selected_mode == "full_autonomous"
    assert route.runner_id == "codex_cli"


def test_runtime_runner_route_artifact_records_route_decision(tmp_path: Path):
    route = resolve_runtime_runner_route(
        provider_config=ProviderConfig(provider="openai"),
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
        allow_router=False,
    )

    artifact_path = save_runtime_runner_route_artifact(
        spec_dir=tmp_path,
        route=route,
        phase="coding",
        session_num=3,
        subtask_id="2.1",
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "coding"
    assert payload["session"] == 3
    assert payload["subtask_id"] == "2.1"
    assert payload["route"]["requested_provider"] == "openai"
    assert payload["route"]["selected_provider"] == "openai"
    assert payload["route"]["status"] == "disabled"
    assert payload["route"]["runner_selection"]["selected_runner_ids"] == [
        "codex_cli",
        "claude_code",
        "zai_claude_code",
    ]


def test_runtime_runner_router_keeps_limited_runtimes_direct():
    route = resolve_runtime_runner_route(
        provider_config=ProviderConfig(provider="openai"),
        provider_name="openai",
        requested_mode="generic_edit",
        phase="coding",
        allow_router=True,
    )

    assert route.route_applied is False
    assert route.status == "native"
    assert route.selected_provider == "openai"


def test_runtime_requirements_follow_selected_runtime_mode():
    assert (
        requirements_for_runtime_mode(
            "full_autonomous",
            phase="planning",
        )
        == RuntimeRequirements.planner()
    )
    assert (
        requirements_for_runtime_mode(
            "generic_edit",
            phase="planning",
        )
        == RuntimeRequirements.generic_edit()
    )
    assert (
        requirements_for_runtime_mode(
            "patch_proposal",
            phase="coding",
        )
        == RuntimeRequirements.patch_proposal()
    )
    assert (
        requirements_for_runtime_mode(
            "analysis_only",
            phase="coding",
        )
        == RuntimeRequirements.text_only()
    )


@pytest.mark.asyncio
async def test_analysis_only_coding_saves_artifact_without_post_processing(
    temp_git_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from agents.coder import run_autonomous_agent

    spec_dir = temp_git_repo / ".auto-claude" / "specs" / "001-analysis"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Analyze only\n", encoding="utf-8")
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(
        json.dumps(
            {
                "feature": "Analyze only",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "1",
                        "name": "Phase 1",
                        "subtasks": [
                            {
                                "id": "1.1",
                                "description": "Explain the likely edit path",
                                "status": "pending",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    class FakeAnalysisSession:
        provider_name = "openai"

        async def complete(self, message: str, stream: bool = True):
            await asyncio.sleep(0)
            assert "Explain the likely edit path" in message
            assert stream is True
            yield "Inspect src/app.py before proposing edits."

    class FakeProvider:
        name = "openai"

        def create_session(self, _session_config):
            return FakeAnalysisSession()

    async def fake_get_graphiti_context(*_args, **_kwargs):
        await asyncio.sleep(0)
        return None

    async def fake_get_pattern_suggestions(*_args, **_kwargs):
        await asyncio.sleep(0)
        return None

    async def fail_post_session_processing(*_args, **_kwargs):
        await asyncio.sleep(0)
        raise AssertionError("analysis_only coding must not run post processing")

    monkeypatch.setenv("AI_ENGINE_PROVIDER", "openai")
    monkeypatch.setenv("AGENT_RUNTIME_MODE_CODER", "analysis_only")
    monkeypatch.setattr(
        "agents.coder.create_engine_provider", lambda *_a: FakeProvider()
    )
    monkeypatch.setattr("agents.coder.is_linear_enabled", lambda: False)
    monkeypatch.setattr("agents.coder.get_graphiti_context", fake_get_graphiti_context)
    monkeypatch.setattr(
        "agents.coder.get_pattern_suggestions",
        fake_get_pattern_suggestions,
    )
    monkeypatch.setattr("agents.coder.load_subtask_context", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "agents.coder.post_session_processing",
        fail_post_session_processing,
    )
    monkeypatch.setattr("agents.coder.AUTO_CONTINUE_DELAY_SECONDS", 0)

    await run_autonomous_agent(
        project_dir=temp_git_repo,
        spec_dir=spec_dir,
        model="gpt-4o",
        max_iterations=1,
        verbose=False,
    )

    artifact_path = next(
        (spec_dir / "artifacts").glob("analysis_only_coding_session-1_1.1_openai_*.md")
    )
    metadata_path = artifact_path.with_suffix(".json")
    assert artifact_path.exists()
    assert metadata_path.exists()
    assert "Inspect src/app.py" in artifact_path.read_text(encoding="utf-8")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "analysis_only"
    assert metadata["provider"] == "openai"
    assert metadata["subtask_id"] == "1.1"

    updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
    subtask = updated_plan["phases"][0]["subtasks"][0]
    assert subtask["status"] == "pending"
