import asyncio
import json
import os
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from agents.runtime import (
    EXTERNAL_MCP_CLIENT_ENV,
    MCP_ALLOWED_PERMISSIONS_ENV,
    LocalActionExecutor,
    RuntimeCapabilities,
    RuntimeCapabilityError,
    RuntimeExternalMcpAdapter,
    RuntimeExternalMcpClientError,
    RuntimeExternalMcpHttpClient,
    RuntimeExternalMcpToolDefinition,
    RuntimeMcpBridge,
    RuntimeMcpToolPolicy,
    RuntimeRequirements,
    RuntimeSubagentOrchestrator,
    RuntimeSubagentResult,
    RuntimeSubagentTask,
    check_external_mcp_contract,
    create_runtime_session,
    describe_external_mcp_server_health,
    describe_mcp_server_statuses,
    executable_external_mcp_tools,
    external_mcp_adapter_for,
    get_runtime_mode,
    local_action_response_schema,
    local_action_tool_schemas,
    local_action_tool_specs,
    mcp_bridge_audit_path,
    normalize_runtime_mode,
    registered_external_mcp_servers,
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
    build_codex_event_timeline,
    build_codex_usage_metadata,
    codex_resume_metadata,
    extract_codex_final_message,
    parse_codex_json_events,
    summarize_codex_account,
    summarize_codex_events,
)
from agents.runtime.adapters.generic_edit import (
    MAX_MUTATION_PREIMAGE_BYTES,
    GenericEditRuntimeError,
    bounded_subagent_attempts,
    build_generic_edit_file_preimage,
    build_generic_edit_rollback_operation,
    execute_generic_edit_transaction_rollback,
    summarize_generic_edit_transactions,
)
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
    assert (tmp_path / "artifacts" / "codex_cli_timeline.json").exists()
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
        assert result_payload["cost_usd"] == pytest.approx(0.001)
        assert result_payload["account_summary"] is None
        assert result.usage_metadata["input_tokens"] == 12
        assert result.usage_metadata["output_tokens"] == 7
        assert result.usage_metadata["total_tokens"] == 19
        assert result.usage_metadata["cost_usd"] == pytest.approx(0.001)
        timeline_payload = json.loads(
            (tmp_path / "artifacts" / "codex_cli_timeline.json").read_text(
                encoding="utf-8"
            )
        )
        assert timeline_payload["session_id"] == "codex-test-session"
        assert timeline_payload["event_count"] == 2
        assert timeline_payload["events"][0]["type"] == "session.started"
        assert timeline_payload["events"][1]["usage"] == {
            "input_tokens": 12,
            "output_tokens": 7,
            "total_tokens": 19,
        }
        assert result.artifacts["codex_cli_timeline"].endswith(
            "codex_cli_timeline.json"
        )


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


def test_codex_cli_event_timeline_summarizes_safe_fields():
    events = [
        {
            "type": "session.started",
            "session_id": "codex-session-1",
            "account": {"email": "dev@example.com", "token": "secret"},
        },
        {
            "type": "response.completed",
            "message": {
                "role": "assistant",
                "content": [{"type": "output_text", "text": "x" * 600}],
            },
            "usage": {"input_tokens": 2, "output_tokens": 3},
            "cost_usd": 0.01,
        },
    ]

    timeline = build_codex_event_timeline(events)

    assert timeline[0] == {
        "index": 1,
        "type": "session.started",
        "session_id": "codex-session-1",
    }
    assert timeline[1]["type"] == "response.completed"
    assert timeline[1]["role"] == "assistant"
    assert len(timeline[1]["text_excerpt"]) == 500
    assert timeline[1]["text_truncated"] is True
    assert timeline[1]["usage"] == {"input_tokens": 2, "output_tokens": 3}
    assert timeline[1]["cost_usd"] == pytest.approx(0.01)
    assert "account" not in timeline[0]


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


def test_provider_tool_call_parser_coalesces_streaming_delta_fragments():
    message_obj = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "chunked_call",
                            "function": {
                                "name": "write_file",
                                "arguments": '{"path":"notes.txt"',
                            },
                        }
                    ]
                }
            },
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "function": {
                                "arguments": ',"content":"hello"}',
                            },
                        }
                    ]
                }
            },
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "chunked_call"
    assert tool_calls[0].name == "write_file"
    assert tool_calls[0].arguments == {"path": "notes.txt", "content": "hello"}


def test_provider_tool_call_parser_handles_bedrock_tool_use_blocks():
    message_obj = {
        "content": [
            {
                "toolUse": {
                    "toolUseId": "bedrock_tool_use",
                    "name": "read_file",
                    "inputJson": {"path": "README.md"},
                }
            }
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "bedrock_tool_use"
    assert tool_calls[0].name == "read_file"
    assert tool_calls[0].arguments == {"path": "README.md"}


def test_provider_tool_call_parser_recurses_nested_response_content_parts():
    message_obj = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "checking"},
                    {
                        "type": "function_call",
                        "call_id": "nested_call",
                        "name": "read_file",
                        "arguments": json.dumps({"path": "nested.txt"}),
                    },
                ],
            }
        ]
    }

    tool_calls = parse_openai_tool_calls(message_obj)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "nested_call"
    assert tool_calls[0].name == "read_file"
    assert tool_calls[0].arguments == {"path": "nested.txt"}


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
        await asyncio.sleep(0)
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
        await asyncio.sleep(0)
        del spec_dir, verbose, phase, subtask_id
        self.prompts.append(message)
        return SimpleNamespace(
            status=self.status,
            response_text=self.response,
            usage_metadata={"input_tokens": 1, "output_tokens": 2},
            artifacts=None,
        )

    async def cancel(self):
        await asyncio.sleep(0)
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


class CancellableSubagentRuntimeSession(FakeSubagentRuntimeSession):
    def __init__(self, response: str):
        super().__init__(response)
        self.started = asyncio.Event()

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
        self.started.set()
        await asyncio.sleep(10)
        return SimpleNamespace(
            status="complete",
            response_text="too late",
            usage_metadata=None,
            artifacts=None,
        )


class FailingSubagentRuntimeSession(FakeSubagentRuntimeSession):
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
        raise RuntimeError("child session failed")


def assert_artifact_path_inside(
    artifact_path_value: str,
    artifact_dir: Path,
) -> Path:
    artifact_dir_resolved = artifact_dir.resolve()
    artifact_path = Path(artifact_path_value).resolve()
    assert artifact_path.is_relative_to(artifact_dir_resolved)
    assert artifact_path.exists()
    return artifact_path


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
    artifact_path = tmp_path / "artifacts" / "runtime_subagents.json"
    assert run.artifact_path == str(artifact_path)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "complete"
    assert artifact["support"]["strategy"] == "orchestrated"
    assert artifact["support"]["available"] is True
    assert artifact["merge_plan"] == {
        "strategy": "read_only",
        "requires_parent_merge": False,
        "read_only_result_ids": ["explore-api", "explore-ui"],
        "mutating_result_ids": [],
        "write_scopes": {},
        "conflict_result_ids": [],
        "has_conflicts": False,
    }
    assert artifact["summary"] == {
        "result_count": 2,
        "status_counts": {"complete": 2},
        "complete_result_ids": ["explore-api", "explore-ui"],
        "continue_result_ids": [],
        "error_result_ids": [],
        "cancelled_result_ids": [],
        "artifact_result_ids": [],
        "retried_result_ids": [],
        "max_attempts_exhausted_result_ids": [],
        "has_errors": False,
        "has_cancelled": False,
        "has_retries": False,
        "has_exhausted_retries": False,
    }
    assert artifact["results"][0]["usage_metadata"] == {
        "input_tokens": 1,
        "output_tokens": 2,
    }
    artifact_dir = tmp_path / "artifacts"
    child_artifact_path = assert_artifact_path_inside(
        artifact["results"][0]["artifact_path"],
        artifact_dir,
    )
    assert (
        child_artifact_path
        == (artifact_dir / "runtime_subagents__explore-api.json").resolve()
    )
    child_artifact = json.loads(child_artifact_path.read_text(encoding="utf-8"))
    assert child_artifact["parent_artifact"] == "runtime_subagents.json"
    assert child_artifact["merge_contract"] == {
        "merge_policy": "read_only",
        "write_scope": [],
        "requires_parent_merge": False,
    }
    assert "Auto Code subagent `explore-api`" in created_sessions[0].prompts[0]
    assert "Isolation contract:" in created_sessions[0].prompts[0]
    assert "Merge policy: read_only" in created_sessions[0].prompts[0]
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
    artifact_path = tmp_path / "artifacts" / "runtime_subagents.json"
    assert run.artifact_path == str(artifact_path)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["summary"]["error_result_ids"] == ["slow-review"]
    assert artifact["summary"]["max_attempts_exhausted_result_ids"] == ["slow-review"]


@pytest.mark.asyncio
async def test_runtime_subagent_orchestrator_cancels_child_session_on_error(
    tmp_path: Path,
):
    created_sessions: list[FailingSubagentRuntimeSession] = []

    def session_factory(task: RuntimeSubagentTask):
        session = FailingSubagentRuntimeSession(f"failed {task.id}")
        created_sessions.append(session)
        return session

    orchestrator = RuntimeSubagentOrchestrator(
        session_factory=session_factory,
        spec_dir=tmp_path,
        max_concurrency=1,
    )
    run = await orchestrator.run(
        [
            RuntimeSubagentTask(
                id="error-review",
                role="reviewer",
                prompt="Raise during child run",
            ),
        ]
    )

    assert run.status == "error"
    assert run.results[0].status == "error"
    assert run.results[0].attempt_count == 1
    assert str(run.results[0].error) == "child session failed"
    assert created_sessions[0].cancelled is True


@pytest.mark.asyncio
async def test_runtime_subagent_orchestrator_cancels_child_sessions_with_artifact(
    tmp_path: Path,
):
    created_sessions: list[CancellableSubagentRuntimeSession] = []

    def session_factory(task: RuntimeSubagentTask):
        session = CancellableSubagentRuntimeSession(f"done {task.id}")
        created_sessions.append(session)
        return session

    orchestrator = RuntimeSubagentOrchestrator(
        session_factory=session_factory,
        spec_dir=tmp_path,
        max_concurrency=1,
    )
    run_task = asyncio.create_task(
        orchestrator.run(
            [
                RuntimeSubagentTask(
                    id="cancel-running",
                    role="reviewer",
                    prompt="Start and wait",
                ),
                RuntimeSubagentTask(
                    id="cancel-queued",
                    role="reviewer",
                    prompt="Should be cancelled before session creation",
                ),
            ]
        )
    )

    for _ in range(100):
        if created_sessions:
            break
        await asyncio.sleep(0)
    assert created_sessions
    await asyncio.wait_for(created_sessions[0].started.wait(), timeout=1)

    await orchestrator.cancel()
    run = await run_task

    assert run.status == "cancelled"
    assert run.cancelled is True
    assert run.cancelled_at is not None
    assert created_sessions[0].cancelled is True
    assert [result.status for result in run.results] == ["cancelled", "cancelled"]
    assert run.results[0].attempt_count == 1
    assert run.results[0].attempts == []
    assert run.results[1].attempts == []

    artifact_path = tmp_path / "artifacts" / "runtime_subagents.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "cancelled"
    assert artifact["cancelled"] is True
    assert artifact["cancelled_at"] == run.cancelled_at
    assert artifact["summary"]["cancelled_result_ids"] == [
        "cancel-running",
        "cancel-queued",
    ]
    assert artifact["results"][0]["attempts"] == []
    assert_artifact_path_inside(
        artifact["results"][0]["artifact_path"],
        tmp_path / "artifacts",
    )


@pytest.mark.asyncio
async def test_runtime_subagent_orchestrator_retries_isolated_child_attempts(
    tmp_path: Path,
):
    created_sessions: list[FakeSubagentRuntimeSession] = []

    def session_factory(task: RuntimeSubagentTask):
        status = "error" if len(created_sessions) == 0 else "complete"
        response = f"{status} {task.id}"
        session = FakeSubagentRuntimeSession(response, status=status)
        created_sessions.append(session)
        return session

    orchestrator = RuntimeSubagentOrchestrator(
        session_factory=session_factory,
        spec_dir=tmp_path,
    )
    run = await orchestrator.run(
        [
            RuntimeSubagentTask(
                id="inspect-retry",
                role="explorer",
                prompt="Inspect flaky source",
                context={"focus": "runtime retries"},
                max_attempts=2,
            ),
        ]
    )

    assert run.status == "complete"
    assert len(created_sessions) == 2
    assert run.results[0].response_text == "complete inspect-retry"
    assert run.results[0].attempt_count == 2
    assert [attempt.status for attempt in run.results[0].attempts] == [
        "error",
        "complete",
    ]
    assert "Attempt: 1 of 2" in created_sessions[0].prompts[0]
    assert "Attempt: 2 of 2" in created_sessions[1].prompts[0]
    assert '"focus": "runtime retries"' in created_sessions[1].prompts[0]

    artifact_path = tmp_path / "artifacts" / "runtime_subagents.json"
    assert run.artifact_path == str(artifact_path)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    result_payload = artifact["results"][0]
    assert result_payload["context"] == {"focus": "runtime retries"}
    assert result_payload["attempt_count"] == 2
    assert result_payload["max_attempts"] == 2
    assert [attempt["status"] for attempt in result_payload["attempts"]] == [
        "error",
        "complete",
    ]
    assert artifact["summary"]["retried_result_ids"] == ["inspect-retry"]
    assert artifact["summary"]["max_attempts_exhausted_result_ids"] == []
    artifact_dir = tmp_path / "artifacts"
    child_artifact_path = assert_artifact_path_inside(
        result_payload["artifact_path"],
        artifact_dir,
    )
    assert (
        child_artifact_path
        == (artifact_dir / "runtime_subagents__inspect-retry.json").resolve()
    )


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
                max_attempts=2,
                attempt_count=2,
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
        "retried_result_ids": ["test"],
        "max_attempts_exhausted_result_ids": ["test"],
        "has_errors": True,
        "has_cancelled": True,
        "has_retries": True,
        "has_exhausted_retries": True,
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
        await asyncio.sleep(0)
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


class FakeNativeToolFatalFailureSession(FakeGenericEditSession):
    async def complete_with_tool_calls(self, message: str | None, tools: list[dict]):
        await asyncio.sleep(0)
        raise RuntimeError("401 Unauthorized: invalid API key")

    def add_tool_result(self, tool_call_id: str, name: str, result: dict):
        raise AssertionError("tool results should not be added after failure")


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
        "rollback_transaction",
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
    rollback_schema = next(
        schema
        for schema in provider_schemas
        if schema["name"] == "rollback_transaction"
    )
    assert rollback_schema["parameters"]["required"] == ["transaction_id"]
    assert "snapshot_ids" in rollback_schema["parameters"]["properties"]
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
    task_properties = run_subagents_schema["parameters"]["properties"]["tasks"][
        "items"
    ]["properties"]
    assert task_properties["merge_policy"]["enum"] == ["read_only"]
    assert task_properties["max_attempts"]["maximum"] >= 2


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
async def test_generic_edit_runtime_cancel_after_mutation_writes_resume_state(
    tmp_path: Path,
):
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "cancelled.txt"
    target.write_text("original\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "mutate then get cancelled",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "cancelled.txt",
                        "content": "changed\n",
                    },
                    {"tool": "read_file", "path": "cancelled.txt"},
                ],
            }
        ]
    )
    runtime_session = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=session,
        project_dir=tmp_path,
    )
    original_execute_action = runtime_session._execute_action

    async def execute_and_cancel_after_first_action(action, **kwargs):
        result = await original_execute_action(action, **kwargs)
        if kwargs["action_index"] == 1:
            runtime_session._cancel_requested = True
        return result

    runtime_session._execute_action = execute_and_cancel_after_first_action

    result = await run_runtime_session(
        runtime_session,
        "cancel after mutation",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact_dir = tmp_path / "artifacts"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    session_state = json.loads(
        (artifact_dir / "generic_edit_session_state.json").read_text(encoding="utf-8")
    )
    checkpoint = json.loads(
        (artifact_dir / "generic_edit_recovery_checkpoint.json").read_text(
            encoding="utf-8"
        )
    )
    mutation_snapshots = json.loads(
        (artifact_dir / "generic_edit_mutation_snapshots.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.status == "cancelled"
    assert target.read_text(encoding="utf-8") == "changed\n"
    assert result_artifact["status"] == "cancelled"
    assert result_artifact["stop_reason"] == "cancelled"
    assert result_artifact["recoverable"] is True
    assert result_artifact["transaction_count"] == 1
    assert result_artifact["mutation_snapshot_count"] == 1
    assert checkpoint["stop_reason"] == "cancelled"
    assert checkpoint["resume"]["strategy"] == "continue_from_trace"
    assert checkpoint["next_iteration"] == 2
    assert session_state["status"] == "cancelled"
    assert session_state["resumable"] is True
    assert session_state["resume_action"] == {
        "runtime": "generic_edit",
        "checkpoint_path": str(artifact_dir / "generic_edit_recovery_checkpoint.json"),
        "strategy": "continue_from_trace",
        "next_iteration": 2,
    }
    assert mutation_snapshots["snapshots"][0]["preimages"][0]["content"] == "original\n"


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
                                "context": {"focus": "backend"},
                                "max_attempts": 2,
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
    assert '"focus": "backend"' in created_sessions[0].prompts[0]
    assert "findings from inspect-api" in session.messages[1]
    artifact_path = tmp_path / "artifacts" / "generic_edit_subagents_1_1_1.json"
    assert artifact_path.exists()
    subagent_artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert subagent_artifact["status"] == "complete"
    assert subagent_artifact["support"]["strategy"] == "orchestrated"
    assert subagent_artifact["summary"]["result_count"] == 2
    assert subagent_artifact["merge_plan"]["strategy"] == "read_only"
    assert subagent_artifact["results"][0]["context"] == {"focus": "backend"}
    assert_artifact_path_inside(
        subagent_artifact["results"][0]["artifact_path"],
        tmp_path / "artifacts",
    )
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    subagent_observation = observation_lines[0]["result"]["data"]
    assert subagent_observation["results"][0]["attempt_count"] == 1
    assert subagent_observation["results"][0]["max_attempts"] == 2
    assert subagent_observation["results"][0]["merge_policy"] == "read_only"
    assert_artifact_path_inside(
        subagent_observation["results"][0]["artifact_path"],
        tmp_path / "artifacts",
    )

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
        await asyncio.sleep(0)
        assert args == {}
        return {"content": [{"type": "text", "text": "Build Progress: 0/1 subtasks"}]}

    monkeypatch.setattr("agents.runtime.mcp_bridge.is_tools_available", lambda: True)
    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)
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
    assert observation_lines[0]["result"]["data"]["permission"] == "read_build_state"
    assert observation_lines[0]["result"]["data"]["mutating"] is False
    assert observation_lines[0]["result"]["data"]["audit_required"] is True
    audit_path = Path(observation_lines[0]["result"]["data"]["audit_artifact"])
    assert audit_path == mcp_bridge_audit_path(tmp_path)
    assert audit_path.exists()
    audit_lines = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert audit_lines[0]["status"] == "ok"
    assert audit_lines[0]["server"] == "auto-claude"
    assert audit_lines[0]["exposed_name"] == "mcp__auto-claude__get_build_progress"
    assert audit_lines[0]["permission"] == "read_build_state"
    assert audit_lines[0]["mutating"] is False
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
    assert result_artifact["mcp_support"]["bridge"]["tool_policies"] == [
        {
            "server": "auto-claude",
            "name": "get_build_progress",
            "exposed_name": "mcp__auto-claude__get_build_progress",
            "permission": "read_build_state",
            "audit_level": "read",
            "mutating": False,
            "audit_required": True,
        }
    ]
    bridge_statuses = {
        status["server"]: status
        for status in result_artifact["mcp_support"]["bridge"]["server_statuses"]
    }
    assert bridge_statuses["auto-claude"]["runtime_path"] == "local_bridge"
    assert bridge_statuses["context7"]["runtime_path"] == "external_bridge_required"
    assert bridge_statuses["graphiti"]["runtime_path"] == "external_bridge_required"
    assert bridge_statuses["context7"]["external_client"]["status"] == (
        "client_disabled"
    )
    assert bridge_statuses["graphiti"]["external_client"]["status"] == (
        "missing_configuration"
    )
    bridge_plan = result_artifact["mcp_support"]["bridge_plan"]
    assert bridge_plan["status"] == "partial"
    assert bridge_plan["bridged_servers"] == ["auto-claude"]
    assert bridge_plan["external_bridge_required_servers"] == [
        "context7",
        "graphiti",
    ]
    assert bridge_plan["action_required"] == "configure_external_mcp_client"


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
    policy_by_tool = {
        policy["name"]: policy for policy in bridge.report()["tool_policies"]
    }
    assert policy_by_tool["update_subtask_status"]["permission"] == (
        "write_build_state"
    )
    assert policy_by_tool["update_subtask_status"]["audit_level"] == "write"
    assert policy_by_tool["update_subtask_status"]["mutating"] is True
    assert policy_by_tool["update_qa_status"]["permission"] == "write_qa_state"
    support = bridge.support_for(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
    )
    assert support.strategy == "local_bridge"
    assert support.server == "auto-claude"
    assert support.tool_count == 2


def test_runtime_mcp_bridge_reports_external_server_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from agents.runtime.adapters.generic_edit import render_mcp_bridge_prompt

    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)
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
    assert support_payload["server_statuses"][0]["runtime_path"] == (
        "external_bridge_required"
    )
    assert support_payload["server_statuses"][0]["bridgeable"] is False
    assert support_payload["server_statuses"][0]["external_client"]["status"] == (
        "client_disabled"
    )
    assert support_payload["bridge_plan"]["status"] == "blocked"
    assert support_payload["bridge_plan"]["external_bridge_required_servers"] == [
        "context7"
    ]
    assert support_payload["bridge_plan"]["action_required"] == (
        "configure_external_mcp_client"
    )


@pytest.mark.asyncio
async def test_runtime_mcp_bridge_denies_external_tool_without_permission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    called = False

    async def fake_call_external_mcp_tool(**_kwargs):
        nonlocal called
        called = True
        return {"content": [{"type": "text", "text": "should not run"}]}

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setattr(
        "agents.runtime.mcp_bridge.call_external_mcp_tool",
        fake_call_external_mcp_tool,
    )
    session = SimpleNamespace(
        agent_type="spec_researcher",
        mcp_allowed_permissions=("read_memory",),
    )

    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    result = await bridge.execute(
        {
            "tool": "mcp__context7__resolve-library-id",
            "libraryName": "pytest",
        }
    )

    assert called is False
    assert result.ok is False
    assert result.tool == "mcp__context7__resolve-library-id"
    assert "permission" in result.message.lower()
    assert result.data["server"] == "context7"
    assert result.data["permission"] == "read_external_docs"
    assert result.data["permission_allowed"] is False
    assert result.data["permission_denial_reason"] == "permission_not_allowed"
    assert result.data["allowed_permissions"] == ["read_memory"]
    audit_path = Path(result.data["audit_artifact"])
    assert audit_path == mcp_bridge_audit_path(tmp_path)
    audit_lines = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert audit_lines[0]["status"] == "denied"
    assert audit_lines[0]["server"] == "context7"
    assert audit_lines[0]["tool"] == "resolve-library-id"
    assert audit_lines[0]["permission"] == "read_external_docs"
    assert audit_lines[0]["permission_allowed"] is False
    assert audit_lines[0]["reason"] == "permission_not_allowed"
    assert audit_lines[0]["allowed_permissions"] == ["read_memory"]


@pytest.mark.asyncio
async def test_runtime_mcp_bridge_allows_external_tool_from_permission_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_call_external_mcp_tool(
        *,
        health,
        tool_name: str,
        arguments: dict,
        project_dir: Path,
    ):
        await asyncio.sleep(0)
        assert health.server == "context7"
        assert tool_name == "resolve-library-id"
        assert arguments == {"libraryName": "pytest"}
        assert project_dir == tmp_path
        return {"content": [{"type": "text", "text": "/pytest-dev/pytest"}]}

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setenv(MCP_ALLOWED_PERMISSIONS_ENV, "read_external_docs")
    monkeypatch.setattr(
        "agents.runtime.mcp_bridge.call_external_mcp_tool",
        fake_call_external_mcp_tool,
    )
    session = SimpleNamespace(agent_type="spec_researcher")

    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    result = await bridge.execute(
        {
            "tool": "mcp__context7__resolve-library-id",
            "libraryName": "pytest",
        }
    )

    assert result.ok is True
    assert result.message == "/pytest-dev/pytest"
    assert result.data["permission"] == "read_external_docs"
    assert result.data["permission_allowed"] is True
    assert result.data["permission_decision_reason"] == "permission_allowed"
    assert result.data["allowed_permissions"] == ["read_external_docs"]
    report = bridge.report()
    assert report["permission_policy"] == {
        "mode": "allowlist",
        "allowed_permissions": ["read_external_docs"],
    }
    audit_lines = [
        json.loads(line)
        for line in Path(result.data["audit_artifact"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert audit_lines[0]["status"] == "ok"
    assert audit_lines[0]["permission_allowed"] is True
    assert audit_lines[0]["permission_decision_reason"] == "permission_allowed"
    assert audit_lines[0]["allowed_permissions"] == ["read_external_docs"]


@pytest.mark.asyncio
async def test_generic_edit_runtime_executes_context7_external_mcp_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_call_external_mcp_tool(
        *,
        health,
        tool_name: str,
        arguments: dict,
        project_dir: Path,
    ):
        await asyncio.sleep(0)
        assert health.server == "context7"
        assert tool_name == "resolve-library-id"
        assert arguments == {"libraryName": "pytest"}
        assert project_dir == tmp_path
        return {"content": [{"type": "text", "text": "/pytest-dev/pytest"}]}

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setattr(
        "agents.runtime.mcp_bridge.call_external_mcp_tool",
        fake_call_external_mcp_tool,
    )
    session = FakeGenericEditSession(
        [
            {
                "thought": "resolve docs",
                "actions": [
                    {
                        "tool": "mcp__context7__resolve-library-id",
                        "libraryName": "pytest",
                    }
                ],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Resolved Context7 docs",
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
        agent_type="spec_researcher",
    )

    result = await run_runtime_session(
        runtime_session,
        "resolve docs",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert "Resolved Context7 docs" in result.response_text
    assert "mcp__context7__resolve-library-id" in session.messages[0]
    assert "/pytest-dev/pytest" in session.messages[1]
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    result_payload = observation_lines[0]["result"]
    assert result_payload["ok"] is True
    assert result_payload["tool"] == "mcp__context7__resolve-library-id"
    assert result_payload["data"]["server"] == "context7"
    assert result_payload["data"]["permission"] == "read_external_docs"
    audit_path = Path(result_payload["data"]["audit_artifact"])
    assert audit_path == mcp_bridge_audit_path(tmp_path)
    audit_lines = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert audit_lines[0]["status"] == "ok"
    assert audit_lines[0]["server"] == "context7"
    assert audit_lines[0]["tool"] == "resolve-library-id"
    artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["mcp_support"]["strategy"] == "local_bridge"
    assert artifact["mcp_support"]["available_servers"] == ["context7"]
    assert artifact["mcp_support"]["unavailable_servers"] == []
    assert artifact["mcp_support"]["bridge_plan"]["status"] == "ready"
    assert artifact["mcp_support"]["bridge_plan"]["action_required"] == "none"
    assert artifact["mcp_support"]["bridge_plan"]["external_bridged_servers"] == [
        "context7"
    ]
    assert artifact["mcp_support"]["bridge_plan"]["bridged_servers"] == ["context7"]
    assert artifact["mcp_support"]["bridge"]["tools"] == [
        "mcp__context7__resolve-library-id",
        "mcp__context7__get-library-docs",
    ]


@pytest.mark.asyncio
async def test_runtime_mcp_bridge_executes_custom_mcp_generic_call_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import agents.runtime.mcp_bridge as mcp_bridge_module

    calls: list[dict[str, Any]] = []

    async def fake_call_external_mcp_tool(
        *,
        health,
        tool_name: str,
        arguments: dict[str, Any],
        project_dir: Path,
        **_kwargs,
    ):
        await asyncio.sleep(0)
        calls.append(
            {
                "server": health.server,
                "tool_name": tool_name,
                "arguments": arguments,
                "project_dir": project_dir,
            }
        )
        return {"content": [{"type": "text", "text": "custom result"}]}

    project_mcp_config = {
        "CUSTOM_MCP_SERVERS": [
            {
                "id": "my-docs",
                "name": "My Docs",
                "type": "http",
                "url": "https://docs.example.test/mcp/",
                "headers": {"Authorization": "Bearer test-token"},
            }
        ]
    }
    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setattr(
        mcp_bridge_module,
        "call_external_mcp_tool",
        fake_call_external_mcp_tool,
    )
    session = SimpleNamespace(
        auto_claude_tools=[],
        mcp_servers=("my-docs",),
        mcp_config=project_mcp_config,
        mcp_allowed_permissions=("call_custom_mcp",),
    )
    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    assert bridge.provider_tool_schemas()[0]["name"] == "mcp__my-docs__call_tool"

    result = await bridge.execute(
        {
            "tool": "mcp__my-docs__call_tool",
            "tool_name": "search",
            "arguments": {"query": "runtime bridge"},
        }
    )

    assert result.ok is True
    assert result.message == "custom result"
    assert calls == [
        {
            "server": "my-docs",
            "tool_name": "search",
            "arguments": {"query": "runtime bridge"},
            "project_dir": tmp_path,
        }
    ]
    audit_path = Path(result.data["audit_artifact"])
    audit_event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert audit_event["server"] == "my-docs"
    assert audit_event["tool"] == "call_tool"
    assert audit_event["permission"] == "call_custom_mcp"


@pytest.mark.asyncio
async def test_runtime_mcp_bridge_exposes_discovered_custom_mcp_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import agents.runtime.mcp_bridge as mcp_bridge_module

    calls: list[dict[str, Any]] = []

    async def fake_call_external_mcp_tool(
        *,
        health,
        tool_name: str,
        arguments: dict[str, Any],
        project_dir: Path,
        **_kwargs,
    ):
        await asyncio.sleep(0)
        calls.append(
            {
                "server": health.server,
                "tool_name": tool_name,
                "arguments": arguments,
                "project_dir": project_dir,
            }
        )
        return {"content": [{"type": "text", "text": "search result"}]}

    project_mcp_config = {
        "CUSTOM_MCP_SERVERS": [
            {
                "id": "my-docs",
                "name": "My Docs",
                "type": "http",
                "url": "https://docs.example.test/mcp/",
                "headers": {"Authorization": "Bearer test-token"},
                "tools": [
                    {
                        "name": "search_docs",
                        "description": "Search private documentation.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query.",
                                },
                                "limit": {"type": "integer"},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "raw_status",
                        "description": "Schema-less status probe.",
                    },
                ],
            }
        ]
    }
    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setattr(
        mcp_bridge_module,
        "call_external_mcp_tool",
        fake_call_external_mcp_tool,
    )
    session = SimpleNamespace(
        auto_claude_tools=[],
        mcp_servers=("my-docs",),
        mcp_config=project_mcp_config,
        mcp_allowed_permissions=("call_custom_mcp",),
    )
    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    schemas = {schema["name"]: schema for schema in bridge.provider_tool_schemas()}
    assert "mcp__my-docs__search_docs" in schemas
    assert "mcp__my-docs__raw_status" in schemas
    assert "mcp__my-docs__call_tool" in schemas
    assert schemas["mcp__my-docs__search_docs"]["parameters"]["required"] == ["query"]
    assert (
        schemas["mcp__my-docs__search_docs"]["parameters"]["properties"]["query"][
            "description"
        ]
        == "Search query."
    )
    assert schemas["mcp__my-docs__raw_status"]["parameters"]["type"] == "object"

    result = await bridge.execute(
        {
            "tool": "mcp__my-docs__search_docs",
            "query": "runtime bridge",
            "limit": 3,
        }
    )

    assert result.ok is True
    assert result.message == "search result"
    assert calls == [
        {
            "server": "my-docs",
            "tool_name": "search_docs",
            "arguments": {"query": "runtime bridge", "limit": 3},
            "project_dir": tmp_path,
        }
    ]
    audit_path = Path(result.data["audit_artifact"])
    audit_event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert audit_event["server"] == "my-docs"
    assert audit_event["tool"] == "search_docs"
    assert audit_event["permission"] == "call_custom_mcp"


@pytest.mark.asyncio
async def test_generic_edit_runtime_executes_puppeteer_external_mcp_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_call_external_mcp_tool(
        *,
        health,
        tool_name: str,
        arguments: dict,
        project_dir: Path,
    ):
        await asyncio.sleep(0)
        assert health.server == "puppeteer"
        assert tool_name == "puppeteer_navigate"
        assert arguments == {"url": "http://localhost:3000"}
        assert project_dir == tmp_path
        return {"content": [{"type": "text", "text": "Navigated"}]}

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setenv("PUPPETEER_MCP_ENABLED", "true")
    monkeypatch.setattr(
        "agents.runtime.mcp_bridge.call_external_mcp_tool",
        fake_call_external_mcp_tool,
    )
    session = FakeGenericEditSession(
        [
            {
                "thought": "open app",
                "actions": [
                    {
                        "tool": "mcp__puppeteer__puppeteer_navigate",
                        "url": "http://localhost:3000",
                    }
                ],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Opened browser app",
                        "tests": [],
                        "risks": [],
                    }
                ],
            },
        ]
    )
    session.mcp_servers = ("puppeteer",)
    session.auto_claude_tools = ()
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
        agent_type="qa_reviewer",
    )

    result = await run_runtime_session(
        runtime_session,
        "open browser app",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert "Opened browser app" in result.response_text
    assert "mcp__puppeteer__puppeteer_navigate" in session.messages[0]
    assert "Navigated" in session.messages[1]
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    result_payload = observation_lines[0]["result"]
    assert result_payload["ok"] is True
    assert result_payload["data"]["server"] == "puppeteer"
    assert result_payload["data"]["permission"] == "run_browser_automation"
    assert result_payload["data"]["audit_level"] == "command"
    assert result_payload["data"]["mutating"] is True
    audit_path = Path(result_payload["data"]["audit_artifact"])
    assert audit_path == mcp_bridge_audit_path(tmp_path)
    audit_lines = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert audit_lines[0]["status"] == "ok"
    assert audit_lines[0]["server"] == "puppeteer"
    assert audit_lines[0]["tool"] == "puppeteer_navigate"
    artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["mcp_support"]["available_servers"] == ["puppeteer"]
    assert artifact["mcp_support"]["bridge_plan"]["external_bridged_servers"] == [
        "puppeteer"
    ]
    assert (
        "mcp__puppeteer__puppeteer_navigate"
        in artifact["mcp_support"]["bridge"]["tools"]
    )


@pytest.mark.asyncio
async def test_generic_edit_runtime_explains_unavailable_external_mcp_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)
    session = FakeGenericEditSession(
        [
            {
                "thought": "ask docs",
                "actions": [
                    {
                        "tool": "mcp__context7__resolve-library-id",
                        "libraryName": "pytest",
                    }
                ],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Recorded MCP gap",
                        "tests": [],
                        "risks": ["Context7 requires a native MCP runtime."],
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
        agent_type="spec_researcher",
    )

    result = await run_runtime_session(
        runtime_session,
        "resolve docs",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert "Recorded MCP gap" in result.response_text
    assert EXTERNAL_MCP_CLIENT_ENV in session.messages[1]
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    result_payload = observation_lines[0]["result"]
    assert result_payload["ok"] is False
    assert result_payload["tool"] == "mcp__context7__resolve-library-id"
    assert result_payload["data"]["server"] == "context7"
    assert result_payload["data"]["runtime_path"] == "external_bridge_required"
    assert result_payload["data"]["support_strategy"] == "unavailable"
    assert result_payload["data"]["server_status"]["bridgeable"] is False
    assert result_payload["data"]["server_status"]["external_client"]["status"] == (
        "client_disabled"
    )
    assert result_payload["data"]["bridge_plan"]["recommended_runtime_path"] == (
        "external_mcp_client"
    )
    artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["mcp_support"]["unavailable_servers"] == ["context7"]


def test_runtime_mcp_support_distinguishes_native_and_local_bridge(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)
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
    native_plan = native.to_dict()["bridge_plan"]
    assert native_plan["status"] == "ready"
    assert native_plan["action_required"] == "none"

    unavailable = resolve_runtime_mcp_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        requested_servers=("context7",),
    )
    assert unavailable.available is False
    assert unavailable.strategy == "unavailable"
    assert unavailable.unavailable_servers == ("context7",)
    assert unavailable.server_statuses[0]["runtime_path"] == "external_bridge_required"
    assert unavailable.server_statuses[0]["external_client"]["status"] == (
        "client_disabled"
    )
    unavailable_plan = unavailable.to_dict()["bridge_plan"]
    assert unavailable_plan["status"] == "blocked"
    assert unavailable_plan["recommended_runtime_path"] == "external_mcp_client"

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
        "external_bridge_required",
        "local_bridge",
    ]
    assert "external MCP servers" in local_bridge.reason
    local_bridge_plan = local_bridge.to_dict()["bridge_plan"]
    assert local_bridge_plan["status"] == "partial"
    assert local_bridge_plan["bridged_servers"] == ["auto-claude"]
    assert local_bridge_plan["external_bridge_required_servers"] == ["context7"]
    assert local_bridge_plan["recommended_runtime_path"] == "external_mcp_client"

    unsupported_bridge_runtime = resolve_runtime_mcp_support(
        provider_name="custom",
        runtime_name="completion",
        capabilities=RuntimeCapabilities.completion_only(),
        bridge_available=True,
        tool_count=1,
    )
    assert unsupported_bridge_runtime.available is False
    assert "cannot expose" in unsupported_bridge_runtime.reason
    assert unsupported_bridge_runtime.to_dict()["bridge_plan"]["status"] == (
        "not_requested"
    )


def test_runtime_mcp_server_statuses_explain_bridgeable_and_native_gaps(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)
    statuses = describe_mcp_server_statuses(
        requested_servers=("auto-claude", "context7", "browser", "custom-mcp"),
        available_servers=("auto-claude",),
        native_available=False,
    )

    status_by_server = {status["server"]: status for status in statuses}
    assert status_by_server["auto-claude"]["runtime_path"] == "local_bridge"
    assert status_by_server["auto-claude"]["bridgeable"] is True
    assert status_by_server["context7"]["runtime_path"] == ("external_bridge_required")
    assert status_by_server["context7"]["external_client"]["status"] == (
        "client_disabled"
    )
    assert status_by_server["browser"]["runtime_path"] == "external_bridge_required"
    assert status_by_server["browser"]["external_client"]["status"] == (
        "choose_concrete_server"
    )
    assert status_by_server["browser"]["display_name"] == "Browser automation"
    assert status_by_server["custom-mcp"]["runtime_path"] == "unsupported"


def test_external_mcp_adapter_registry_exposes_context7_contract():
    adapter = external_mcp_adapter_for("mcp__context7__resolve-library-id")

    assert adapter is not None
    assert "context7" in registered_external_mcp_servers()
    assert adapter.server == "context7"
    assert adapter.tool_names == ("resolve-library-id", "get-library-docs")
    assert adapter.execution_supported(transport="stdio", command="npx") is True
    assert adapter.transport_supported(transport="stdio") is True
    assert adapter.transport_supported(transport="http") is False
    assert (
        adapter.execution_supported(
            transport="http",
            command=None,
            url="http://localhost:8000/mcp/",
        )
        is False
    )
    schemas = [definition.parameters for definition in adapter.tool_definitions]
    assert schemas[0]["required"] == ["libraryName"]
    assert schemas[1]["required"] == ["context7CompatibleLibraryID"]
    assert {
        definition.policy.permission for definition in adapter.tool_definitions
    } == {"read_external_docs"}


def test_external_mcp_adapter_registry_contains_expected_static_servers():
    assert set(registered_external_mcp_servers()) == {
        "context7",
        "graphiti",
        "linear",
        "electron",
        "puppeteer",
    }


def test_external_mcp_adapter_registry_exposes_browser_contracts():
    electron = external_mcp_adapter_for("mcp__electron__take_screenshot")
    puppeteer = external_mcp_adapter_for("mcp__puppeteer__puppeteer_navigate")

    assert electron is not None
    assert puppeteer is not None
    assert electron.tool_names == (
        "get_electron_window_info",
        "take_screenshot",
        "send_command_to_electron",
        "read_electron_logs",
    )
    assert puppeteer.tool_names == (
        "puppeteer_connect_active_tab",
        "puppeteer_navigate",
        "puppeteer_screenshot",
        "puppeteer_click",
        "puppeteer_fill",
        "puppeteer_select",
        "puppeteer_hover",
        "puppeteer_evaluate",
    )
    electron_policy_by_tool = {
        definition.name: definition.policy for definition in electron.tool_definitions
    }
    puppeteer_policy_by_tool = {
        definition.name: definition.policy for definition in puppeteer.tool_definitions
    }
    assert electron_policy_by_tool["take_screenshot"].permission == (
        "read_browser_state"
    )
    assert electron_policy_by_tool["send_command_to_electron"].mutating is True
    assert puppeteer_policy_by_tool["puppeteer_screenshot"].audit_level == "read"
    assert puppeteer_policy_by_tool["puppeteer_evaluate"].mutating is True


def test_external_mcp_adapter_registry_exposes_http_contracts():
    graphiti = external_mcp_adapter_for("mcp__graphiti-memory__search_nodes")
    linear = external_mcp_adapter_for("mcp__linear-server__create_issue")

    assert graphiti is not None
    assert linear is not None
    assert graphiti.server == "graphiti"
    assert graphiti.exposed_server_name == "graphiti-memory"
    assert graphiti.transport_supported(transport="http") is True
    assert (
        graphiti.execution_supported(
            transport="http",
            command=None,
            url="http://localhost:8000/mcp/",
        )
        is True
    )
    assert graphiti.tool_names == (
        "search_nodes",
        "search_facts",
        "add_episode",
        "get_episodes",
        "get_entity_edge",
    )
    assert linear.server == "linear"
    assert linear.exposed_server_name == "linear-server"
    assert linear.transport_supported(transport="http") is True
    assert "list_teams" in linear.tool_names
    assert "create_issue" in linear.tool_names
    graphiti_policy_by_tool = {
        definition.name: definition.policy for definition in graphiti.tool_definitions
    }
    linear_policy_by_tool = {
        definition.name: definition.policy for definition in linear.tool_definitions
    }
    assert graphiti_policy_by_tool["search_nodes"].audit_level == "read"
    assert graphiti_policy_by_tool["add_episode"].mutating is True
    assert linear_policy_by_tool["list_teams"].audit_level == "read"
    assert linear_policy_by_tool["create_issue"].mutating is True


def test_external_mcp_adapter_registry_exposes_custom_server_contract():
    project_mcp_config = {
        "CUSTOM_MCP_SERVERS": [
            {
                "id": "my-docs",
                "name": "My Docs",
                "type": "command",
                "command": "uvx",
                "args": ["my-docs-mcp"],
                "description": "Private documentation server.",
                "tools": [
                    {
                        "name": "search_docs",
                        "description": "Search private documentation.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
            }
        ]
    }

    adapter = external_mcp_adapter_for(
        "mcp__my-docs__call_tool",
        project_mcp_config=project_mcp_config,
    )
    health = describe_external_mcp_server_health(
        "my-docs",
        project_mcp_config=project_mcp_config,
        environment={EXTERNAL_MCP_CLIENT_ENV: "true"},
    )

    assert adapter is not None
    assert adapter.server == "my-docs"
    assert adapter.display_name == "My Docs"
    assert adapter.transport == "stdio"
    assert adapter.tool_names == ("search_docs", "call_tool")
    assert adapter.exposed_server_name == "my-docs"
    assert {
        definition.policy.permission for definition in adapter.tool_definitions
    } == {"call_custom_mcp"}
    assert {definition.policy.mutating for definition in adapter.tool_definitions} == {
        True
    }
    assert adapter.tool_definitions[0].parameters["required"] == ["query"]
    assert adapter.tool_definitions[1].parameters["required"] == ["tool_name"]
    assert health.status == "ready_to_connect"
    assert health.command == "uvx"
    assert health.args == ("my-docs-mcp",)
    assert health.adapter_registered is True
    assert health.executable_tools == ("search_docs", "call_tool")
    assert executable_external_mcp_tools(
        requested_servers=("my-docs",),
        project_mcp_config=project_mcp_config,
        environment={EXTERNAL_MCP_CLIENT_ENV: "true"},
    ) == ("mcp__my-docs__search_docs", "mcp__my-docs__call_tool")


def test_runtime_mcp_bridge_loads_custom_mcp_config_from_project_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    mcp_config_dir = tmp_path / ".auto-claude"
    mcp_config_dir.mkdir()
    custom_servers = [
        {
            "id": "my-docs",
            "name": "My Docs",
            "type": "command",
            "command": "uvx",
            "args": ["my-docs-mcp"],
            "tools": [
                {
                    "name": "search_docs",
                    "description": "Search private documentation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                }
            ],
        }
    ]
    (mcp_config_dir / ".env").write_text(
        f"CUSTOM_MCP_SERVERS={json.dumps(custom_servers)}\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    session = SimpleNamespace(
        auto_claude_tools=[],
        mcp_servers=("my-docs",),
        mcp_allowed_permissions=("call_custom_mcp",),
    )
    bridge = RuntimeMcpBridge.from_agent_session(
        agent_session=session,
        spec_dir=tmp_path,
        project_dir=tmp_path,
    )

    assert bridge is not None
    assert bridge.available_servers == ("my-docs",)
    assert [schema["name"] for schema in bridge.provider_tool_schemas()] == [
        "mcp__my-docs__search_docs",
        "mcp__my-docs__call_tool",
    ]
    report = bridge.report()
    assert report["server_statuses"][0]["runtime_path"] == "external_bridge"
    assert report["bridge_plan"]["external_bridged_servers"] == ["my-docs"]


def test_external_mcp_health_reports_ready_context7_when_client_enabled():
    health = describe_external_mcp_server_health(
        "context7",
        environment={EXTERNAL_MCP_CLIENT_ENV: "true"},
    )

    assert health.bridgeable is True
    assert health.client_enabled is True
    assert health.configured is True
    assert health.status == "ready_to_connect"
    assert health.command == "npx"
    assert health.args == ("-y", "@upstash/context7-mcp")
    assert health.execution_supported is True
    assert health.adapter_registered is True
    assert health.adapter_name == "Context7"
    assert health.adapter_transport == "stdio"
    assert health.transport_supported is True
    assert health.supported_transports == ("stdio", "http")
    assert health.executable_tools == ("resolve-library-id", "get-library-docs")
    assert executable_external_mcp_tools(
        requested_servers=("context7",),
        environment={EXTERNAL_MCP_CLIENT_ENV: "true"},
    ) == (
        "mcp__context7__resolve-library-id",
        "mcp__context7__get-library-docs",
    )

    support = resolve_runtime_mcp_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        requested_servers=("context7",),
        external_client_enabled=True,
        environment={EXTERNAL_MCP_CLIENT_ENV: "true"},
    )
    plan = support.to_dict()["bridge_plan"]
    assert plan["external_bridge_ready_servers"] == ["context7"]
    assert plan["action_required"] == "wire_external_mcp_tool_execution"


def test_external_mcp_health_reports_ready_browser_adapters_when_enabled():
    environment = {
        EXTERNAL_MCP_CLIENT_ENV: "true",
        "ELECTRON_MCP_ENABLED": "true",
        "PUPPETEER_MCP_ENABLED": "true",
    }
    electron = describe_external_mcp_server_health(
        "electron",
        environment=environment,
    )
    puppeteer = describe_external_mcp_server_health(
        "puppeteer",
        environment=environment,
    )

    assert electron.status == "ready_to_connect"
    assert electron.execution_supported is True
    assert electron.adapter_registered is True
    assert electron.executable_tools == (
        "get_electron_window_info",
        "take_screenshot",
        "send_command_to_electron",
        "read_electron_logs",
    )
    assert puppeteer.status == "ready_to_connect"
    assert puppeteer.execution_supported is True
    assert puppeteer.adapter_registered is True
    assert "puppeteer_navigate" in puppeteer.executable_tools
    assert executable_external_mcp_tools(
        requested_servers=("electron", "puppeteer"),
        environment=environment,
    ) == (
        "mcp__electron__get_electron_window_info",
        "mcp__electron__take_screenshot",
        "mcp__electron__send_command_to_electron",
        "mcp__electron__read_electron_logs",
        "mcp__puppeteer__puppeteer_connect_active_tab",
        "mcp__puppeteer__puppeteer_navigate",
        "mcp__puppeteer__puppeteer_screenshot",
        "mcp__puppeteer__puppeteer_click",
        "mcp__puppeteer__puppeteer_fill",
        "mcp__puppeteer__puppeteer_select",
        "mcp__puppeteer__puppeteer_hover",
        "mcp__puppeteer__puppeteer_evaluate",
    )


def test_external_mcp_health_keeps_puppeteer_disabled_when_only_electron_enabled():
    environment = {
        EXTERNAL_MCP_CLIENT_ENV: "true",
        "ELECTRON_MCP_ENABLED": "true",
    }

    electron = describe_external_mcp_server_health(
        "electron",
        environment=environment,
    )
    puppeteer = describe_external_mcp_server_health(
        "puppeteer",
        environment=environment,
    )
    executable_tools = executable_external_mcp_tools(
        requested_servers=("electron", "puppeteer"),
        environment=environment,
    )

    assert electron.status == "ready_to_connect"
    assert electron.ready_to_connect is True
    assert puppeteer.status == "server_disabled"
    assert puppeteer.ready_to_connect is False
    assert puppeteer.adapter_registered is True
    assert "mcp__electron__take_screenshot" in executable_tools
    assert "mcp__puppeteer__puppeteer_navigate" not in executable_tools


def test_external_mcp_health_keeps_electron_disabled_when_only_puppeteer_enabled():
    environment = {
        EXTERNAL_MCP_CLIENT_ENV: "true",
        "PUPPETEER_MCP_ENABLED": "true",
    }

    electron = describe_external_mcp_server_health(
        "electron",
        environment=environment,
    )
    puppeteer = describe_external_mcp_server_health(
        "puppeteer",
        environment=environment,
    )
    executable_tools = executable_external_mcp_tools(
        requested_servers=("electron", "puppeteer"),
        environment=environment,
    )

    assert electron.status == "server_disabled"
    assert electron.ready_to_connect is False
    assert electron.adapter_registered is True
    assert puppeteer.status == "ready_to_connect"
    assert puppeteer.ready_to_connect is True
    assert "mcp__electron__take_screenshot" not in executable_tools
    assert "mcp__puppeteer__puppeteer_navigate" in executable_tools


def test_external_mcp_health_reports_ready_graphiti_http_adapter():
    health = describe_external_mcp_server_health(
        "graphiti",
        environment={
            EXTERNAL_MCP_CLIENT_ENV: "true",
            "GRAPHITI_MCP_URL": "http://localhost:8000/mcp/",
        },
    )

    assert health.status == "ready_to_connect"
    assert health.configured is True
    assert health.execution_supported is True
    assert health.adapter_registered is True
    assert health.adapter_name == "Graphiti"
    assert health.adapter_transport == "http"
    assert health.adapter_exposed_server == "graphiti-memory"
    assert health.transport_supported is True
    assert health.supported_transports == ("stdio", "http")
    assert health.url == "http://localhost:8000/mcp/"
    assert health.executable_tools == (
        "search_nodes",
        "search_facts",
        "add_episode",
        "get_episodes",
        "get_entity_edge",
    )
    assert executable_external_mcp_tools(
        requested_servers=("graphiti",),
        environment={
            EXTERNAL_MCP_CLIENT_ENV: "true",
            "GRAPHITI_MCP_URL": "http://localhost:8000/mcp/",
        },
    ) == (
        "mcp__graphiti-memory__search_nodes",
        "mcp__graphiti-memory__search_facts",
        "mcp__graphiti-memory__add_episode",
        "mcp__graphiti-memory__get_episodes",
        "mcp__graphiti-memory__get_entity_edge",
    )

    support = resolve_runtime_mcp_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        bridge_available=True,
        tool_count=1,
        requested_servers=("graphiti",),
        external_client_enabled=True,
        environment={
            EXTERNAL_MCP_CLIENT_ENV: "true",
            "GRAPHITI_MCP_URL": "http://localhost:8000/mcp/",
        },
    )
    plan = support.to_dict()["bridge_plan"]
    assert plan["external_bridge_ready_servers"] == ["graphiti"]
    assert plan["external_bridge_adapter_missing_servers"] == []
    assert plan["action_required"] == "wire_external_mcp_tool_execution"


def test_external_mcp_health_reports_unsupported_transport_for_registered_sse_adapter(
    monkeypatch: pytest.MonkeyPatch,
):
    import agents.runtime.mcp_bridge as mcp_bridge_module

    monkeypatch.setitem(
        mcp_bridge_module.EXTERNAL_MCP_ADAPTERS,
        "graphiti",
        RuntimeExternalMcpAdapter(
            server="graphiti",
            display_name="Graphiti",
            transport="sse",
            tool_definitions=(
                RuntimeExternalMcpToolDefinition(
                    name="search_nodes",
                    description="Search Graphiti nodes.",
                    parameters={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    policy=RuntimeMcpToolPolicy("read_memory", "read"),
                ),
            ),
        ),
    )

    health = describe_external_mcp_server_health(
        "graphiti",
        environment={
            EXTERNAL_MCP_CLIENT_ENV: "true",
            "GRAPHITI_MCP_URL": "http://localhost:8000/mcp/",
        },
    )

    assert health.status == "unsupported_transport"
    assert health.adapter_registered is True
    assert health.adapter_transport == "sse"
    assert health.transport_supported is False
    assert health.execution_supported is False
    assert health.supported_transports == ("stdio", "http")

    support = resolve_runtime_mcp_support(
        provider_name="openai",
        runtime_name="generic_edit",
        capabilities=RuntimeCapabilities.generic_edit(),
        bridge_available=True,
        tool_count=1,
        requested_servers=("graphiti",),
        external_client_enabled=True,
        environment={
            EXTERNAL_MCP_CLIENT_ENV: "true",
            "GRAPHITI_MCP_URL": "http://localhost:8000/mcp/",
        },
    )
    plan = support.to_dict()["bridge_plan"]
    assert plan["external_bridge_unsupported_transport_servers"] == ["graphiti"]
    assert plan["action_required"] == "implement_external_mcp_transport"


@pytest.mark.asyncio
async def test_external_mcp_http_client_posts_jsonrpc_with_session_and_sse(
    monkeypatch: pytest.MonkeyPatch,
):
    import httpx

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(202)

        payload = json.loads(request.content.decode("utf-8"))
        assert request.headers.get("Accept") == "application/json, text/event-stream"
        assert request.headers.get("Content-Type") == "application/json"
        assert request.headers.get("MCP-Protocol-Version") == "2025-06-18"
        assert request.headers.get("Authorization") == "Bearer test-token"

        if payload["method"] == "initialize":
            return httpx.Response(
                200,
                headers={
                    "Mcp-Session-Id": "session-1",
                    "content-type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"protocolVersion": "2025-06-18"},
                },
            )
        if payload["method"] == "notifications/initialized":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(202)
        if payload["method"] == "tools/call":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            assert payload["params"] == {
                "name": "search_nodes",
                "arguments": {"query": "runtime bridge"},
            }
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=(
                    "event: message\n"
                    'data: {"jsonrpc":"2.0","id":2,'
                    '"result":{"content":[{"type":"text","text":"found"}]}}\n\n'
                ),
            )
        return httpx.Response(500, text="unexpected request")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def fake_async_client(*, timeout: float):
        return real_async_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = RuntimeExternalMcpHttpClient(
        server="graphiti",
        url="https://graphiti.local/mcp/",
        headers={"Authorization": "Bearer test-token"},
        protocol_version="2025-06-18",
    )

    result = await client.call_tool(
        name="search_nodes",
        arguments={"query": "runtime bridge"},
    )

    assert result == {"content": [{"type": "text", "text": "found"}]}
    assert [request.method for request in requests] == [
        "POST",
        "POST",
        "POST",
        "DELETE",
    ]


@pytest.mark.asyncio
async def test_external_mcp_http_client_returns_after_matching_long_lived_sse_event(
    monkeypatch: pytest.MonkeyPatch,
):
    import httpx

    class LongLivedSseStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"event: message\n"
            yield (
                b'data: {"jsonrpc":"2.0","id":2,'
                b'"result":{"content":[{"type":"text","text":"found"}]}}\n\n'
            )
            raise AssertionError("client kept reading after matching SSE response")

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(202)

        payload = json.loads(request.content.decode("utf-8"))
        if payload["method"] == "initialize":
            return httpx.Response(
                200,
                headers={
                    "Mcp-Session-Id": "session-1",
                    "content-type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"protocolVersion": "2025-06-18"},
                },
            )
        if payload["method"] == "notifications/initialized":
            return httpx.Response(202)
        if payload["method"] == "tools/call":
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                stream=LongLivedSseStream(),
            )
        return httpx.Response(500, text="unexpected request")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def fake_async_client(*, timeout: float):
        return real_async_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = RuntimeExternalMcpHttpClient(
        server="graphiti",
        url="https://graphiti.local/mcp/",
        protocol_version="2025-06-18",
    )

    result = await client.call_tool(
        name="search_nodes",
        arguments={"query": "runtime bridge"},
    )

    assert result == {"content": [{"type": "text", "text": "found"}]}
    assert [request.method for request in requests] == [
        "POST",
        "POST",
        "POST",
        "DELETE",
    ]


@pytest.mark.asyncio
async def test_external_mcp_http_client_lists_tools_with_session_and_sse(
    monkeypatch: pytest.MonkeyPatch,
):
    import httpx

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(202)

        payload = json.loads(request.content.decode("utf-8"))
        assert request.headers.get("Accept") == "application/json, text/event-stream"
        assert request.headers.get("Content-Type") == "application/json"
        assert request.headers.get("MCP-Protocol-Version") == "2025-06-18"

        if payload["method"] == "initialize":
            return httpx.Response(
                200,
                headers={
                    "Mcp-Session-Id": "session-1",
                    "content-type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"protocolVersion": "2025-06-18"},
                },
            )
        if payload["method"] == "notifications/initialized":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(202)
        if payload["method"] == "tools/list":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            assert payload["params"] == {}
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=(
                    "event: message\n"
                    'data: {"jsonrpc":"2.0","id":2,'
                    '"result":{"tools":[{"name":"search_nodes"}]}}\n\n'
                ),
            )
        return httpx.Response(500, text="unexpected request")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def fake_async_client(*, timeout: float):
        return real_async_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = RuntimeExternalMcpHttpClient(
        server="graphiti",
        url="https://graphiti.local/mcp/",
        protocol_version="2025-06-18",
    )

    result = await client.list_tools()

    assert result == {"tools": [{"name": "search_nodes"}]}
    assert [request.method for request in requests] == [
        "POST",
        "POST",
        "POST",
        "DELETE",
    ]


@pytest.mark.asyncio
async def test_external_mcp_http_client_closes_session_when_initialize_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    import httpx

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(202)

        payload = json.loads(request.content.decode("utf-8"))
        if payload["method"] == "initialize":
            return httpx.Response(
                200,
                headers={
                    "Mcp-Session-Id": "session-1",
                    "content-type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"protocolVersion": "2025-06-18"},
                },
            )
        if payload["method"] == "notifications/initialized":
            assert request.headers.get("Mcp-Session-Id") == "session-1"
            return httpx.Response(500, text="notification failed")
        return httpx.Response(500, text="unexpected request")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def fake_async_client(*, timeout: float):
        return real_async_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = RuntimeExternalMcpHttpClient(
        server="graphiti",
        url="https://graphiti.local/mcp/",
        protocol_version="2025-06-18",
    )

    with pytest.raises(RuntimeExternalMcpClientError, match="returned 500"):
        await client.list_tools()

    assert [request.method for request in requests] == ["POST", "POST", "DELETE"]


@pytest.mark.asyncio
async def test_check_external_mcp_contract_reports_extra_and_missing_live_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import agents.runtime.mcp_bridge as mcp_bridge_module

    adapter = external_mcp_adapter_for("graphiti")
    assert adapter is not None
    live_tool_sets = [
        [*adapter.tool_names, "new_live_tool"],
        ["search_nodes"],
    ]
    calls: list[dict[str, str]] = []

    class FakeHttpClient:
        def __init__(self, *, server: str, url: str, headers: dict[str, str]):
            calls.append({"server": server, "url": url, "headers": str(headers)})

        async def list_tools(self):
            await asyncio.sleep(0)
            tool_names = live_tool_sets.pop(0)
            return {"tools": [{"name": name} for name in tool_names]}

    monkeypatch.setattr(
        mcp_bridge_module,
        "RuntimeExternalMcpHttpClient",
        FakeHttpClient,
    )
    environment = {
        EXTERNAL_MCP_CLIENT_ENV: "true",
        "GRAPHITI_MCP_URL": "https://graphiti.local/mcp/",
    }

    extra = await check_external_mcp_contract(
        server="graphiti",
        project_dir=tmp_path,
        environment=environment,
    )
    missing = await check_external_mcp_contract(
        server="graphiti",
        project_dir=tmp_path,
        environment=environment,
    )

    assert extra.ok is True
    assert extra.status == "server_has_extra_tools"
    assert extra.server_tools_missing_in_adapter == ("new_live_tool",)
    assert missing.ok is False
    assert missing.status == "adapter_tool_missing_on_server"
    assert "search_facts" in missing.adapter_tools_missing_on_server
    assert calls == [
        {
            "server": "graphiti",
            "url": "https://graphiti.local/mcp/",
            "headers": "{}",
        },
        {
            "server": "graphiti",
            "url": "https://graphiti.local/mcp/",
            "headers": "{}",
        },
    ]


@pytest.mark.asyncio
async def test_call_external_mcp_tool_dispatches_http_with_linear_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import agents.runtime.mcp_bridge as mcp_bridge_module

    calls: list[dict[str, Any]] = []

    class FakeHttpClient:
        def __init__(self, *, server: str, url: str, headers: dict[str, str]):
            calls.append({"server": server, "url": url, "headers": headers})

        async def call_tool(self, *, name: str, arguments: dict[str, Any]):
            await asyncio.sleep(0)
            calls.append({"name": name, "arguments": arguments})
            return {"content": [{"type": "text", "text": "created"}]}

    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.setattr(
        mcp_bridge_module,
        "RuntimeExternalMcpHttpClient",
        FakeHttpClient,
    )
    environment = {
        EXTERNAL_MCP_CLIENT_ENV: "true",
        "LINEAR_API_KEY": "linear-secret",
    }
    health = describe_external_mcp_server_health(
        "linear",
        environment=environment,
    )

    result = await mcp_bridge_module.call_external_mcp_tool(
        health=health,
        tool_name="create_issue",
        arguments={"team": "ENG", "title": "Wire HTTP MCP"},
        project_dir=tmp_path,
        environment=environment,
    )

    assert result["content"][0]["text"] == "created"
    assert calls == [
        {
            "server": "linear",
            "url": "https://mcp.linear.app/mcp",
            "headers": {"Authorization": "Bearer linear-secret"},
        },
        {
            "name": "create_issue",
            "arguments": {"team": "ENG", "title": "Wire HTTP MCP"},
        },
    ]


def test_external_mcp_headers_use_injected_project_config(
    monkeypatch: pytest.MonkeyPatch,
):
    import agents.runtime.mcp_bridge as mcp_bridge_module

    monkeypatch.delenv("LINEAR_API_KEY", raising=False)

    headers = mcp_bridge_module.external_mcp_headers_for_server(
        "linear",
        project_mcp_config={"LINEAR_API_KEY": "project-secret"},
        environment={"LINEAR_API_KEY": "environment-secret"},
    )

    assert headers == {"Authorization": "Bearer project-secret"}


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
    assert result_artifact["last_partial_failure_id"] == "json_actions-1"
    assert result_artifact["last_partial_failure_affected_paths"] == [
        "missing.txt",
        "partial.txt",
    ]
    assert result_artifact["last_partial_failure_mutated_paths"] == ["partial.txt"]
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


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_finish_with_unresolved_partial_failure(
    tmp_path: Path,
):
    (tmp_path / "partial.txt").write_text("original\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "mutate then fail",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "partial.txt",
                        "content": "changed\n",
                    },
                    {"tool": "read_file", "path": "missing.txt"},
                ],
            },
            {
                "thought": "finish too early",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "done without recovery",
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
    )

    result = await run_runtime_session(
        runtime_session,
        "make partial edit",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "rejected finish" in result.response_text
    assert "json_actions-1" in result.response_text
    artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    session_state_path = tmp_path / "artifacts" / "generic_edit_session_state.json"
    checkpoint_path = tmp_path / "artifacts" / "generic_edit_recovery_checkpoint.json"
    recovery_plan_path = tmp_path / "artifacts" / "generic_edit_recovery_plan.json"
    manifest_path = tmp_path / "artifacts" / "generic_edit_artifact_manifest.json"
    group_artifact_path = (
        tmp_path / "artifacts" / "generic_edit_transaction_groups.json"
    )
    mutation_snapshot_path = (
        tmp_path / "artifacts" / "generic_edit_mutation_snapshots.json"
    )
    trace_path = tmp_path / "artifacts" / "generic_edit_trace.json"
    event_path = tmp_path / "artifacts" / "generic_edit_events.jsonl"
    session_state = json.loads(session_state_path.read_text(encoding="utf-8"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    recovery_plan = json.loads(recovery_plan_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    group_artifact = json.loads(group_artifact_path.read_text(encoding="utf-8"))
    mutation_snapshots = json.loads(mutation_snapshot_path.read_text(encoding="utf-8"))
    expected_next_actions = [
        {
            "id": "inspect-json_actions-1-1",
            "kind": "inspect_diff",
            "tool": "git_diff",
            "action": {"tool": "git_diff", "path": "partial.txt", "max_chars": 8000},
            "transaction_id": "json_actions-1",
            "transaction_group_id": "transaction-group-1",
            "paths": ["partial.txt"],
            "required_before_finish": True,
        },
        {
            "id": "rollback-json_actions-1",
            "kind": "rollback_transaction",
            "tool": "rollback_transaction",
            "action": {
                "tool": "rollback_transaction",
                "transaction_id": "json_actions-1",
            },
            "transaction_id": "json_actions-1",
            "transaction_group_id": "transaction-group-1",
            "rollback_operation_id": "rollback-json_actions-1",
            "mutation_snapshot_ids": ["mutation-1"],
            "required_before_finish": True,
        },
    ]
    expected_manifest_recovery_actions = [
        {
            "id": "inspect-json_actions-1-1",
            "kind": "inspect_diff",
            "tool": "git_diff",
            "transaction_id": "json_actions-1",
            "transaction_group_id": "transaction-group-1",
            "paths": ["partial.txt"],
            "required_before_finish": True,
        },
        {
            "id": "rollback-json_actions-1",
            "kind": "rollback_transaction",
            "tool": "rollback_transaction",
            "transaction_id": "json_actions-1",
            "transaction_group_id": "transaction-group-1",
            "rollback_operation_id": "rollback-json_actions-1",
            "mutation_snapshot_ids": ["mutation-1"],
            "required_before_finish": True,
        },
    ]
    expected_group_policy = {
        "version": 1,
        "status": "requires_resolution",
        "finish_blocked": True,
        "transaction_id": "json_actions-1",
        "transaction_group_id": "transaction-group-1",
        "path_scope": ["partial.txt"],
        "resolution_strategies": ["rollback_transaction", "repair_mutation"],
        "preferred_strategy": "rollback_transaction",
        "rollback_restorable": True,
        "required_next_action_kinds": ["inspect_diff", "rollback_transaction"],
        "recommended_verification_tools": ["git_diff", "run_command"],
    }
    expected_plan_policy = {
        "version": 1,
        "status": "requires_resolution",
        "finish_blocked": True,
        "unresolved_transaction_count": 1,
        "unresolved_transaction_group_count": 1,
        "resolution_strategies": ["rollback_transaction", "repair_mutation"],
        "recommended_verification_tools": ["git_diff", "run_command"],
    }
    expected_resume_action = {
        "runtime": "generic_edit",
        "checkpoint_path": str(checkpoint_path),
        "strategy": "recover_partial_failure",
        "next_iteration": 3,
    }
    expected_resume_inputs = {
        "trace_artifact": str(trace_path),
        "event_artifact": str(event_path),
        "recovery_plan_artifact": str(recovery_plan_path),
        "mutation_snapshot_artifact": str(mutation_snapshot_path),
    }

    assert artifact["status"] == "error"
    assert artifact["stop_reason"] == "unresolved_partial_failure"
    assert artifact["unresolved_partial_failure_ids"] == ["json_actions-1"]
    assert artifact["recovery_resolved"] is False
    assert artifact["session_state_artifact"] == str(session_state_path)
    assert artifact["recovery_checkpoint_artifact"] == str(checkpoint_path)
    assert artifact["recovery_plan_artifact"] == str(recovery_plan_path)
    assert artifact["mutation_snapshot_artifact"] == str(mutation_snapshot_path)
    assert artifact["mutation_snapshot_count"] == 1
    assert artifact["transaction_group_count"] == 1
    assert artifact["unresolved_transaction_group_ids"] == ["transaction-group-1"]
    assert artifact["recovery_plan"]["strategy"] == "repair_or_rollback"
    assert artifact["recovery_plan"]["unresolved_transaction_ids"] == ["json_actions-1"]
    assert artifact["recovery_plan"]["unresolved_transaction_group_ids"] == [
        "transaction-group-1"
    ]
    assert artifact["recovery_plan"]["recovery_policy"] == expected_plan_policy
    assert artifact["recovery_plan"]["mutation_snapshot_artifact"] == str(
        mutation_snapshot_path
    )
    assert artifact["recovery_plan"]["next_actions"] == expected_next_actions
    assert manifest["recovery_summary"] == {
        "version": 1,
        "status": "requires_resolution",
        "finish_blocked": True,
        "unresolved_transaction_group_count": 1,
        "unresolved_transaction_group_ids": ["transaction-group-1"],
        "warning_count": 0,
        "warnings": [],
        "resolution_strategies": ["rollback_transaction", "repair_mutation"],
        "recommended_verification_tools": ["git_diff", "run_command"],
    }
    assert manifest["recovery_actions"] == expected_manifest_recovery_actions
    assert manifest["resume_action"] == expected_resume_action
    assert manifest["resume_inputs"] == expected_resume_inputs
    rollback_operation = recovery_plan["rollback_operations"][0]
    assert rollback_operation["tool"] == "rollback_transaction"
    assert rollback_operation["transaction_id"] == "json_actions-1"
    assert rollback_operation["mutation_snapshot_ids"] == ["mutation-1"]
    assert rollback_operation["restorable"] is True
    assert rollback_operation["action"] == {
        "tool": "rollback_transaction",
        "transaction_id": "json_actions-1",
    }
    assert rollback_operation["steps"] == [
        {"operation": "restore_file", "path": "partial.txt"}
    ]
    first_transaction = artifact["transactions"][0]
    assert first_transaction["mutation_snapshot_ids"] == ["mutation-1"]
    assert first_transaction["recovery_plan"]["rollback"]["recommended_tools"] == [
        "rollback_transaction",
        "git_diff",
        "apply_patch",
    ]
    assert first_transaction["recovery_plan"]["rollback"]["preferred_action"] == {
        "tool": "rollback_transaction",
        "transaction_id": "json_actions-1",
    }
    assert first_transaction["recovery_plan"]["rollback"]["mutation_snapshot_ids"] == [
        "mutation-1"
    ]
    assert first_transaction["recovery_plan"]["policy"] == {
        key: value
        for key, value in expected_group_policy.items()
        if key != "transaction_group_id"
    }
    assert first_transaction["recovery_plan"]["repair"]["recommended_tools"] == [
        "read_file",
        "git_diff",
        "apply_patch",
        "write_file",
        "run_command",
    ]
    assert recovery_plan["unresolved_transactions"][0]["id"] == "json_actions-1"
    assert recovery_plan["unresolved_transactions"][0]["mutated_paths"] == [
        "partial.txt"
    ]
    assert recovery_plan["unresolved_transactions"][0]["mutation_snapshot_ids"] == [
        "mutation-1"
    ]
    assert recovery_plan["recovery_policy"] == expected_plan_policy
    assert recovery_plan["next_actions"] == expected_next_actions
    group = group_artifact["transaction_groups"][0]
    assert group["status"] == "unresolved"
    assert group["next_actions"] == expected_next_actions
    assert group["recovery_policy"] == expected_group_policy
    assert mutation_snapshots["artifact_type"] == "generic_edit_mutation_snapshots"
    assert mutation_snapshots["snapshot_count"] == 1
    assert mutation_snapshots["snapshots"][0]["id"] == "mutation-1"
    assert mutation_snapshots["snapshots"][0]["transaction_id"] == "json_actions-1"
    assert mutation_snapshots["snapshots"][0]["tool"] == "write_file"
    assert mutation_snapshots["snapshots"][0]["preimages"][0]["path"] == "partial.txt"
    assert mutation_snapshots["snapshots"][0]["preimages"][0]["exists"] is True
    assert mutation_snapshots["snapshots"][0]["preimages"][0]["content"] == "original\n"
    assert session_state["artifact_type"] == "generic_edit_session_state"
    assert session_state["status"] == "error"
    assert session_state["stop_reason"] == "unresolved_partial_failure"
    assert session_state["resumable"] is True
    assert session_state["iteration_count"] == 2
    assert session_state["action_count"] == 3
    assert session_state["failed_action_count"] == 1
    assert session_state["resume_action"] == expected_resume_action
    assert session_state["resume_inputs"] == expected_resume_inputs
    assert session_state["unresolved_partial_failure_ids"] == ["json_actions-1"]
    assert session_state["unresolved_transaction_group_ids"] == ["transaction-group-1"]
    assert checkpoint["resume"]["strategy"] == "recover_partial_failure"
    assert checkpoint["recovery_plan_artifact"] == str(recovery_plan_path)
    assert checkpoint["mutation_snapshot_artifact"] == str(mutation_snapshot_path)
    assert checkpoint["recovery_plan"]["unresolved_transaction_ids"] == [
        "json_actions-1"
    ]
    assert checkpoint["unresolved_transaction_group_ids"] == ["transaction-group-1"]
    assert checkpoint["unresolved_partial_failure_ids"] == ["json_actions-1"]
    assert checkpoint["last_partial_failure_mutated_paths"] == ["partial.txt"]
    assert "repair or rollback" in checkpoint["resume"]["prompt"]
    assert "json_actions-1" in checkpoint["resume"]["prompt"]
    assert "partial.txt" in checkpoint["resume"]["prompt"]


@pytest.mark.asyncio
async def test_generic_edit_runtime_rolls_back_transaction_from_snapshots(
    tmp_path: Path,
):
    target = tmp_path / "partial.txt"
    target.write_text("original\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "mutate then fail",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "partial.txt",
                        "content": "changed\n",
                    },
                    {"tool": "read_file", "path": "missing.txt"},
                ],
            },
            {
                "thought": "rollback the partial transaction and finish",
                "actions": [
                    {
                        "tool": "rollback_transaction",
                        "transaction_id": "json_actions-1",
                    },
                    {
                        "tool": "finish",
                        "summary": "Rolled back partial transaction",
                        "tests": ["not run"],
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
        "rollback partial edit",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    trace_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )

    assert result.status == "continue"
    assert target.read_text(encoding="utf-8") == "original\n"
    assert artifact["status"] == "complete"
    assert artifact["recovery_resolved"] is True
    assert artifact["recovery_transaction_ids"] == ["json_actions-2"]
    assert artifact["transaction_status_counts"] == {
        "partial_failure": 1,
        "complete": 1,
    }
    assert artifact["transactions"][1]["mutating_tools"] == ["rollback_transaction"]
    assert artifact["transactions"][1]["mutated_paths"] == ["partial.txt"]
    rollback_result = trace_artifact["trace"][1]["actions"][0]["result"]
    assert rollback_result["ok"] is True
    assert rollback_result["data"]["transaction_id"] == "json_actions-1"
    assert rollback_result["data"]["mutation_snapshot_ids"] == ["mutation-1"]
    assert rollback_result["data"]["restored_paths"] == ["partial.txt"]


def generic_edit_text_snapshot(
    snapshot_id: str,
    path: str,
    content: str,
    *,
    transaction_id: str = "json_actions-1",
) -> dict[str, Any]:
    return {
        "id": snapshot_id,
        "transaction_id": transaction_id,
        "rollback": {"restorable": True},
        "preimages": [
            {
                "path": path,
                "restorable": True,
                "exists": True,
                "type": "file",
                "content_encoding": "utf-8",
                "content": content,
            }
        ],
    }


def block_path_write_text(monkeypatch: pytest.MonkeyPatch, blocked_name: str) -> None:
    original_write_text = Path.write_text

    def write_text_with_blocked_path(self, data, *args, **kwargs):
        if self.name == blocked_name:
            raise OSError("disk full")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write_text_with_blocked_path)


def test_generic_edit_rollback_blocks_unknown_requested_snapshot_ids():
    rollback_operation = build_generic_edit_rollback_operation(
        transaction_id="json_actions-1",
        mutation_snapshots=[
            generic_edit_text_snapshot("mutation-1", "partial.txt", "original\n")
        ],
        snapshot_ids=["mutation-1", "mutation-missing"],
    )

    assert rollback_operation["restorable"] is False
    assert rollback_operation["mutation_snapshot_ids"] == ["mutation-1"]
    assert (
        "Requested snapshot ids not found: mutation-missing"
        in rollback_operation["blocked_reasons"]
    )


def test_generic_edit_rollback_failure_reports_partial_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    mutation_snapshots = [
        generic_edit_text_snapshot("mutation-1", "blocked.txt", "blocked\n"),
        generic_edit_text_snapshot("mutation-2", "restored.txt", "restored\n"),
    ]
    block_path_write_text(monkeypatch, "blocked.txt")

    with pytest.raises(GenericEditRuntimeError) as exc_info:
        execute_generic_edit_transaction_rollback(
            action={
                "tool": "rollback_transaction",
                "transaction_id": "json_actions-1",
            },
            project_dir=tmp_path,
            mutation_snapshots=mutation_snapshots,
        )

    assert (tmp_path / "restored.txt").read_text(encoding="utf-8") == "restored\n"
    assert exc_info.value.restored_paths == ["restored.txt"]
    assert exc_info.value.deleted_paths == []
    assert "restored_paths=['restored.txt']" in str(exc_info.value)


def test_generic_edit_runtime_rollback_failure_result_reports_partial_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakeGenericEditSession([]),
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )
    runtime_session._mutation_snapshots = [
        generic_edit_text_snapshot("mutation-1", "blocked.txt", "blocked\n"),
        generic_edit_text_snapshot("mutation-2", "restored.txt", "restored\n"),
    ]
    block_path_write_text(monkeypatch, "blocked.txt")

    result = runtime_session._rollback_transaction_action(
        {"tool": "rollback_transaction", "transaction_id": "json_actions-1"}
    )

    assert result.ok is False
    assert result.data["restored_paths"] == ["restored.txt"]
    assert result.data["deleted_paths"] == []


@pytest.mark.asyncio
async def test_generic_edit_runtime_writes_transaction_recovery_groups(
    tmp_path: Path,
):
    target = tmp_path / "partial.txt"
    target.write_text("original\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "mutate then fail",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "partial.txt",
                        "content": "changed\n",
                    },
                    {"tool": "read_file", "path": "missing.txt"},
                ],
            },
            {
                "thought": "rollback the partial transaction and finish",
                "actions": [
                    {
                        "tool": "rollback_transaction",
                        "transaction_id": "json_actions-1",
                    },
                    {
                        "tool": "finish",
                        "summary": "Rolled back partial transaction",
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
        "rollback partial edit",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact_dir = tmp_path / "artifacts"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    group_artifact_path = artifact_dir / "generic_edit_transaction_groups.json"
    event_artifact_path = artifact_dir / "generic_edit_events.jsonl"
    group_artifact = json.loads(group_artifact_path.read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in event_artifact_path.read_text(encoding="utf-8").splitlines()
    ]

    assert result.status == "continue"
    assert target.read_text(encoding="utf-8") == "original\n"
    assert result_artifact["event_artifact"] == str(event_artifact_path)
    assert result_artifact["event_count"] == 7
    assert result_artifact["transaction_group_artifact"] == str(group_artifact_path)
    assert result_artifact["transaction_group_count"] == 1
    assert result_artifact["transaction_group_status_counts"] == {"resolved": 1}
    assert result_artifact["unresolved_transaction_group_count"] == 0
    assert result_artifact["unresolved_transaction_group_ids"] == []
    assert result_artifact["recovery_outcome_count"] == 1
    assert group_artifact["artifact_type"] == "generic_edit_transaction_groups"
    assert group_artifact["group_count"] == 1
    assert group_artifact["recovery_outcome_count"] == 1
    group = group_artifact["transaction_groups"][0]
    expected_outcome = {
        "transaction_group_id": "transaction-group-1",
        "partial_failure_transaction_id": "json_actions-1",
        "resolution_transaction_id": "json_actions-2",
        "strategy": "rollback_transaction",
        "tool_sequence": ["rollback_transaction", "finish"],
        "recovered_paths": ["partial.txt"],
        "mutation_snapshot_ids": ["mutation-1"],
        "recovery_attempt_count": 1,
        "failed_recovery_attempt_count": 0,
        "policy_status": {
            "version": 1,
            "status": "resolved",
            "resolution_strategy": "rollback_transaction",
            "post_recovery_verification_observed": False,
            "recommended_verification_tools": ["git_diff", "run_command"],
            "warning_count": 1,
            "warnings": [
                "Recovered transaction resolved without post-recovery verification."
            ],
        },
    }
    assert group["id"] == "transaction-group-1"
    assert group["status"] == "resolved"
    assert group["recovery_outcome"] == expected_outcome
    assert result_artifact["recovery_outcomes"] == [expected_outcome]
    assert group_artifact["recovery_outcomes"] == [expected_outcome]
    assert group["partial_failure_transaction_id"] == "json_actions-1"
    assert group["resolution_transaction_id"] == "json_actions-2"
    assert group["transaction_ids"] == ["json_actions-1", "json_actions-2"]
    assert group["recovery_transaction_ids"] == ["json_actions-2"]
    assert group["mutated_paths"] == ["partial.txt"]
    assert group["mutation_snapshot_ids"] == ["mutation-1"]
    assert group["rollback_operation"]["tool"] == "rollback_transaction"
    assert group["rollback_operation"]["action"] == {
        "tool": "rollback_transaction",
        "transaction_id": "json_actions-1",
    }
    assert "content" not in group["rollback_operation"]["steps"][0]
    assert [event["event_type"] for event in events] == [
        "action_result",
        "action_result",
        "transaction",
        "action_result",
        "action_result",
        "transaction",
        "transaction_group",
    ]
    assert events[0]["tool"] == "write_file"
    assert events[0]["transaction_id"] == "json_actions-1"
    assert events[0]["mutation_snapshot_id"] == "mutation-1"
    assert events[1]["ok"] is False
    assert events[1]["tool"] == "read_file"
    assert events[2]["transaction_id"] == "json_actions-1"
    assert events[2]["status"] == "partial_failure"
    assert events[5]["transaction_id"] == "json_actions-2"
    assert events[5]["status"] == "complete"
    assert events[6]["group_id"] == "transaction-group-1"
    assert events[6]["status"] == "resolved"
    assert events[6]["partial_failure_transaction_id"] == "json_actions-1"
    assert events[6]["resolution_transaction_id"] == "json_actions-2"
    assert events[6]["recovery_outcome"] == expected_outcome


@pytest.mark.asyncio
async def test_generic_edit_runtime_records_recovery_attempt_history(tmp_path: Path):
    target = tmp_path / "partial.txt"
    target.write_text("original\n", encoding="utf-8")
    (tmp_path / "unrelated.txt").write_text("noise\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "mutate then fail",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "partial.txt",
                        "content": "changed\n",
                    },
                    {"tool": "read_file", "path": "missing.txt"},
                ],
            },
            {
                "thought": "inspect the wrong file",
                "actions": [{"tool": "read_file", "path": "unrelated.txt"}],
            },
            {
                "thought": "inspect the mutated file and finish",
                "actions": [
                    {"tool": "read_file", "path": "partial.txt"},
                    {
                        "tool": "finish",
                        "summary": "Recovered after inspecting partial.txt",
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
        "recover partial edit",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact_dir = tmp_path / "artifacts"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    group_artifact = json.loads(
        (artifact_dir / "generic_edit_transaction_groups.json").read_text(
            encoding="utf-8"
        )
    )
    events = [
        json.loads(line)
        for line in (artifact_dir / "generic_edit_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    expected_attempts = [
        {
            "attempt_number": 1,
            "transaction_id": "json_actions-2",
            "resolved": False,
            "strategy": "path_coverage",
            "status": "complete",
            "tool_sequence": ["read_file"],
            "affected_paths": ["unrelated.txt"],
            "mutated_paths": [],
            "mutation_snapshot_ids": [],
            "post_recovery_verification_observed": False,
        },
        {
            "attempt_number": 2,
            "transaction_id": "json_actions-3",
            "resolved": True,
            "strategy": "path_coverage",
            "status": "complete",
            "tool_sequence": ["read_file", "finish"],
            "affected_paths": ["partial.txt"],
            "mutated_paths": [],
            "mutation_snapshot_ids": [],
            "post_recovery_verification_observed": False,
        },
    ]

    assert result.status == "continue"
    assert result_artifact["recovery_resolved"] is True
    assert result_artifact["recovery_attempt_count"] == 2
    assert result_artifact["failed_recovery_attempt_count"] == 1
    assert group_artifact["recovery_attempt_count"] == 2
    assert group_artifact["failed_recovery_attempt_count"] == 1
    group = group_artifact["transaction_groups"][0]
    assert group["status"] == "resolved"
    assert group["resolution_transaction_id"] == "json_actions-3"
    assert group["recovery_attempt_ids"] == ["json_actions-2", "json_actions-3"]
    assert group["recovery_attempt_count"] == 2
    assert group["failed_recovery_attempt_count"] == 1
    assert group["recovery_attempts"] == expected_attempts
    assert group["recovery_outcome"]["recovery_attempt_count"] == 2
    assert group["recovery_outcome"]["failed_recovery_attempt_count"] == 1
    assert events[-1]["recovery_attempt_count"] == 2
    assert events[-1]["failed_recovery_attempt_count"] == 1


@pytest.mark.asyncio
async def test_generic_edit_runtime_bounds_large_mutation_preimages(tmp_path: Path):
    large_content = "x" * (MAX_MUTATION_PREIMAGE_BYTES + 1)
    target = tmp_path / "large.txt"
    target.write_text(large_content, encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "mutate large file and then hit a recoverable failure",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "large.txt",
                        "content": "changed\n",
                    },
                    {"tool": "read_file", "path": "missing.txt"},
                ],
            },
            {
                "thought": "finish before recovery",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "done",
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
    )

    result = await run_runtime_session(
        runtime_session,
        "mutate large file",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    mutation_snapshot_path = (
        tmp_path / "artifacts" / "generic_edit_mutation_snapshots.json"
    )
    mutation_snapshots = json.loads(mutation_snapshot_path.read_text(encoding="utf-8"))
    preimage = mutation_snapshots["snapshots"][0]["preimages"][0]

    assert preimage["path"] == "large.txt"
    assert preimage["exists"] is True
    assert preimage["type"] == "file"
    assert preimage["bytes"] == len(large_content)
    assert preimage["content_truncated"] is True
    assert preimage["content_bytes_limit"] == MAX_MUTATION_PREIMAGE_BYTES
    assert preimage["restorable"] is False
    assert "content" not in preimage


def test_generic_edit_file_preimage_records_inspection_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    target = tmp_path / "locked.txt"
    target.write_text("before\n", encoding="utf-8")

    def raise_exists_oserror(self: Path) -> bool:
        if self == target:
            raise OSError("transient stat failure")
        return False

    monkeypatch.setattr(Path, "exists", raise_exists_oserror)

    preimage = build_generic_edit_file_preimage(
        project_dir=tmp_path,
        path="locked.txt",
    )

    assert preimage["path"] == "locked.txt"
    assert preimage["exists"] is False
    assert preimage["type"] == "unreadable"
    assert preimage["restorable"] is False
    assert "transient stat failure" in preimage["error"]


def test_generic_edit_file_preimage_records_read_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    target = tmp_path / "locked.txt"
    target.write_text("before\n", encoding="utf-8")
    original_read_text = Path.read_text

    def raise_read_oserror(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == target:
            raise PermissionError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", raise_read_oserror)

    preimage = build_generic_edit_file_preimage(
        project_dir=tmp_path,
        path="locked.txt",
    )

    assert preimage["path"] == "locked.txt"
    assert preimage["exists"] is True
    assert preimage["type"] == "file"
    assert preimage["restorable"] is False
    assert "permission denied" in preimage["error"]


@pytest.mark.asyncio
async def test_generic_edit_runtime_writes_recovery_checkpoint_on_max_iterations(
    tmp_path: Path,
):
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "todo.txt"
    target.write_text("keep going\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "inspect but do not finish yet",
                "actions": [{"tool": "read_file", "path": "todo.txt"}],
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
        "inspect todo.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact_dir = tmp_path / "artifacts"
    checkpoint_path = artifact_dir / "generic_edit_recovery_checkpoint.json"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    summary_markdown = (artifact_dir / "generic_edit_summary.md").read_text(
        encoding="utf-8"
    )

    assert result.status == "error"
    assert result_artifact["recoverable"] is True
    assert result_artifact["recovery_checkpoint_artifact"] == str(checkpoint_path)
    assert checkpoint["status"] == "error"
    assert checkpoint["stop_reason"] == "max_iterations"
    assert checkpoint["next_iteration"] == 2
    assert checkpoint["resume"]["strategy"] == "continue_from_trace"
    assert "generic_edit_trace.json" in checkpoint["resume"]["prompt"]
    assert checkpoint["recent_actions"][-1]["tool"] == "read_file"
    assert checkpoint["transaction_summary"]["transaction_count"] == 1
    assert "## Resume" in summary_markdown
    assert str(checkpoint_path) in summary_markdown


@pytest.mark.asyncio
async def test_generic_edit_runtime_writes_artifact_manifest(tmp_path: Path):
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "todo.txt"
    target.write_text("keep going\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "inspect but do not finish yet",
                "actions": [{"tool": "read_file", "path": "todo.txt"}],
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
        "inspect todo.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact_dir = tmp_path / "artifacts"
    manifest_path = artifact_dir / "generic_edit_artifact_manifest.json"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_markdown = (artifact_dir / "generic_edit_summary.md").read_text(
        encoding="utf-8"
    )
    artifacts_by_name = {
        artifact["name"]: artifact for artifact in manifest["artifacts"]
    }

    assert result.status == "error"
    assert result_artifact["artifact_manifest_artifact"] == str(manifest_path)
    assert manifest["artifact_type"] == "generic_edit_artifact_manifest"
    assert manifest["schema_version"] == 1
    assert manifest["status"] == "error"
    assert manifest["stop_reason"] == "max_iterations"
    assert manifest["flags"]["recoverable"] is True
    assert manifest["flags"]["resumable"] is True
    assert manifest["flags"]["recovery_required"] is False
    assert len(manifest["recent_events"]) == 2
    assert manifest["recent_events"][0]["sequence"] == 1
    assert manifest["recent_events"][0]["event_type"] == "action_result"
    assert manifest["recent_events"][0]["tool"] == "read_file"
    assert manifest["recent_events"][0]["ok"] is True
    assert "status" not in manifest["recent_events"][0]
    assert manifest["recent_events"][1]["event_type"] == "transaction"
    assert manifest["recent_events"][1]["transaction_id"] == "json_actions-1"
    assert manifest["entrypoints"]["result"] == str(
        artifact_dir / "generic_edit_result.json"
    )
    assert manifest["entrypoints"]["session_state"] == str(
        artifact_dir / "generic_edit_session_state.json"
    )
    assert artifacts_by_name["generic_edit_artifact_manifest"]["present"] is True
    assert artifacts_by_name["generic_edit_recovery_checkpoint"]["present"] is True
    assert artifacts_by_name["generic_edit_recovery_checkpoint"]["active"] is True
    assert artifacts_by_name["generic_edit_mutation_snapshots"]["active"] is False
    assert "## Artifact Manifest" in summary_markdown
    assert str(manifest_path) in summary_markdown


@pytest.mark.asyncio
async def test_generic_edit_runtime_resumes_from_recovery_checkpoint(tmp_path: Path):
    from agents.runtime import resume_runtime_session
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "todo.txt"
    target.write_text("keep going\n", encoding="utf-8")
    initial_session = FakeGenericEditSession(
        [
            {
                "thought": "inspect but do not finish yet",
                "actions": [{"tool": "read_file", "path": "todo.txt"}],
            }
        ]
    )
    initial_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=initial_session,
        project_dir=tmp_path,
        max_iterations=1,
    )

    first_result = await run_runtime_session(
        initial_runtime,
        "inspect todo.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    checkpoint_path = tmp_path / "artifacts" / "generic_edit_recovery_checkpoint.json"
    assert first_result.status == "error"
    assert checkpoint_path.exists()
    checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint_payload["trace_artifact"] = str(tmp_path / "untrusted-trace.json")
    checkpoint_path.write_text(
        json.dumps(checkpoint_payload, indent=2),
        encoding="utf-8",
    )

    resume_session = FakeGenericEditSession(
        [
            {
                "thought": "finish from checkpoint",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Resumed from checkpoint",
                        "tests": ["pytest tests/test_agent_runtime.py"],
                        "risks": [],
                    }
                ],
            }
        ]
    )
    resume_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=resume_session,
        project_dir=tmp_path,
        max_iterations=2,
    )

    resumed = await resume_runtime_session(
        resume_runtime,
        checkpoint_path,
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    session_state = json.loads(
        (tmp_path / "artifacts" / "generic_edit_session_state.json").read_text(
            encoding="utf-8"
        )
    )
    trace_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    summary_markdown = (tmp_path / "artifacts" / "generic_edit_summary.md").read_text(
        encoding="utf-8"
    )

    assert resumed.status == "continue"
    assert "Resume this generic_edit run" in resume_session.messages[0]
    assert "generic_edit_recovery_checkpoint.json" in resume_session.messages[0]
    assert result_artifact["status"] == "complete"
    assert result_artifact["stop_reason"] == "finish"
    assert result_artifact["recoverable"] is False
    assert session_state["status"] == "complete"
    assert session_state["resumable"] is False
    assert session_state["resume_action"] is None
    assert session_state["resume_inputs"] == {}
    assert result_artifact["transaction_count"] == 2
    assert [entry["iteration"] for entry in trace_artifact["trace"]] == [1, 2]
    assert trace_artifact["trace"][1]["transaction"]["id"] == "json_actions-2"
    assert not checkpoint_path.exists()
    assert "## Resume" not in summary_markdown


@pytest.mark.asyncio
async def test_generic_edit_runtime_records_resume_provenance(tmp_path: Path):
    from agents.runtime import resume_runtime_session
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "todo.txt"
    target.write_text("keep going\n", encoding="utf-8")
    initial_session = FakeGenericEditSession(
        [
            {
                "thought": "inspect but do not finish yet",
                "actions": [{"tool": "read_file", "path": "todo.txt"}],
            }
        ]
    )
    initial_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=initial_session,
        project_dir=tmp_path,
        max_iterations=1,
    )

    first_result = await run_runtime_session(
        initial_runtime,
        "inspect todo.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    checkpoint_path = tmp_path / "artifacts" / "generic_edit_recovery_checkpoint.json"
    assert first_result.status == "error"
    assert checkpoint_path.exists()

    resume_session = FakeGenericEditSession(
        [
            {
                "thought": "finish from checkpoint",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Resumed with provenance",
                        "tests": [],
                        "risks": [],
                    }
                ],
            }
        ]
    )
    resume_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=resume_session,
        project_dir=tmp_path,
        max_iterations=2,
    )

    resumed = await resume_runtime_session(
        resume_runtime,
        checkpoint_path,
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    artifact_dir = tmp_path / "artifacts"
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    session_state = json.loads(
        (artifact_dir / "generic_edit_session_state.json").read_text(encoding="utf-8")
    )
    events = [
        json.loads(line)
        for line in (artifact_dir / "generic_edit_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert resumed.status == "continue"
    assert result_artifact["resumed"] is True
    assert result_artifact["resume"]["checkpoint_artifact"] == str(checkpoint_path)
    assert result_artifact["resume"]["strategy"] == "continue_from_trace"
    assert result_artifact["resume"]["start_iteration"] == 2
    assert session_state["resumed"] is True
    assert session_state["resume"] == result_artifact["resume"]
    assert events[0]["event_type"] == "resume"
    assert events[0]["checkpoint_artifact"] == str(checkpoint_path)
    assert events[0]["strategy"] == "continue_from_trace"
    assert events[0]["start_iteration"] == 2


@pytest.mark.asyncio
async def test_generic_edit_runtime_resumes_from_session_state_manifest(
    tmp_path: Path,
):
    from agents.runtime import resume_runtime_session
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "todo.txt"
    target.write_text("keep going\n", encoding="utf-8")
    initial_session = FakeGenericEditSession(
        [
            {
                "thought": "inspect but do not finish yet",
                "actions": [{"tool": "read_file", "path": "todo.txt"}],
            }
        ]
    )
    initial_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=initial_session,
        project_dir=tmp_path,
        max_iterations=1,
    )

    first_result = await run_runtime_session(
        initial_runtime,
        "inspect todo.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    session_state_path = tmp_path / "artifacts" / "generic_edit_session_state.json"
    assert first_result.status == "error"
    assert session_state_path.exists()

    resume_session = FakeGenericEditSession(
        [
            {
                "thought": "finish from session state",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Resumed from session state",
                        "tests": ["pytest tests/test_agent_runtime.py"],
                        "risks": [],
                    }
                ],
            }
        ]
    )
    resume_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=resume_session,
        project_dir=tmp_path,
        max_iterations=2,
    )

    resumed = await resume_runtime_session(
        resume_runtime,
        session_state_path,
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    session_state = json.loads(session_state_path.read_text(encoding="utf-8"))

    assert resumed.status == "continue"
    assert "generic_edit_recovery_checkpoint.json" in resume_session.messages[0]
    assert result_artifact["status"] == "complete"
    assert session_state["status"] == "complete"
    assert session_state["resumable"] is False


@pytest.mark.asyncio
async def test_generic_edit_runtime_resume_preserves_mutation_snapshots(
    tmp_path: Path,
):
    from agents.runtime import resume_runtime_session
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    target = tmp_path / "todo.txt"
    target.write_text("original\n", encoding="utf-8")
    initial_session = FakeGenericEditSession(
        [
            {
                "thought": "mutate before checkpoint",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "todo.txt",
                        "content": "changed\n",
                    }
                ],
            }
        ]
    )
    initial_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=initial_session,
        project_dir=tmp_path,
        max_iterations=1,
    )

    first_result = await run_runtime_session(
        initial_runtime,
        "mutate once before checkpoint",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    checkpoint_path = tmp_path / "artifacts" / "generic_edit_recovery_checkpoint.json"
    assert first_result.status == "error"
    assert checkpoint_path.exists()

    resume_session = FakeGenericEditSession(
        [
            {
                "thought": "mutate after checkpoint and finish",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "todo.txt",
                        "content": "resumed\n",
                    },
                    {
                        "tool": "finish",
                        "summary": "Resumed with mutation",
                        "tests": [],
                        "risks": [],
                    },
                ],
            }
        ]
    )
    resume_runtime = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=resume_session,
        project_dir=tmp_path,
        max_iterations=2,
    )

    resumed = await resume_runtime_session(
        resume_runtime,
        checkpoint_path,
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    mutation_snapshots = json.loads(
        (tmp_path / "artifacts" / "generic_edit_mutation_snapshots.json").read_text(
            encoding="utf-8"
        )
    )

    assert resumed.status == "continue"
    assert target.read_text(encoding="utf-8") == "resumed\n"
    assert mutation_snapshots["snapshot_count"] == 2
    assert [snapshot["id"] for snapshot in mutation_snapshots["snapshots"]] == [
        "mutation-1",
        "mutation-2",
    ]
    assert mutation_snapshots["snapshots"][0]["transaction_id"] == "json_actions-1"
    assert mutation_snapshots["snapshots"][0]["preimages"][0]["content"] == "original\n"
    assert mutation_snapshots["snapshots"][1]["transaction_id"] == "json_actions-2"
    assert mutation_snapshots["snapshots"][1]["preimages"][0]["content"] == "changed\n"


@pytest.mark.asyncio
async def test_generic_edit_native_tools_reject_finish_with_unresolved_partial_failure(
    tmp_path: Path,
):
    session = FakeNativeToolCallSession(
        [
            [
                {
                    "name": "write_file",
                    "arguments": {"path": "partial.txt", "content": "changed\n"},
                },
                {"name": "read_file", "arguments": {"path": "missing.txt"}},
            ],
            [{"name": "finish", "arguments": {"summary": "done too early"}}],
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
        "make partial edit through native tools",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "native_tool_calls-1" in result.response_text
    artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["status"] == "error"
    assert artifact["stop_reason"] == "unresolved_partial_failure"
    assert artifact["unresolved_partial_failure_ids"] == ["native_tool_calls-1"]
    mutation_snapshot_path = (
        tmp_path / "artifacts" / "generic_edit_mutation_snapshots.json"
    )
    assert artifact["mutation_snapshot_artifact"] == str(mutation_snapshot_path)
    assert artifact["mutation_snapshot_count"] == 1
    assert session.tool_results[-1]["name"] == "finish"


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


def test_generic_edit_transaction_summary_requires_recovery_path_coverage():
    summary = summarize_generic_edit_transactions(
        [
            {
                "transaction": {
                    "id": "json_actions-1",
                    "status": "partial_failure",
                    "recovery_required": True,
                    "affected_paths": ["broken.txt", "missing.txt"],
                    "mutated_paths": ["broken.txt"],
                }
            },
            {
                "transaction": {
                    "id": "json_actions-2",
                    "status": "complete",
                    "tool_sequence": ["read_file"],
                    "affected_paths": ["unrelated.txt"],
                    "mutated_paths": [],
                    "can_resolve_partial_failure": True,
                }
            },
        ]
    )

    assert summary["partial_failure_count"] == 1
    assert summary["last_partial_failure_id"] == "json_actions-1"
    assert summary["recovery_transaction_ids"] == []
    assert summary["recovery_resolved"] is False
    assert summary["unresolved_partial_failure_ids"] == ["json_actions-1"]


def test_generic_edit_transaction_summary_allows_workspace_recovery_verification():
    summary = summarize_generic_edit_transactions(
        [
            {
                "transaction": {
                    "id": "json_actions-1",
                    "status": "partial_failure",
                    "recovery_required": True,
                    "affected_paths": ["src/broken.py"],
                    "mutated_paths": ["src/broken.py"],
                }
            },
            {
                "transaction": {
                    "id": "json_actions-2",
                    "status": "complete",
                    "tool_sequence": ["git_status"],
                    "affected_paths": ["."],
                    "mutated_paths": [],
                    "can_resolve_partial_failure": True,
                }
            },
        ]
    )

    assert summary["recovery_transaction_ids"] == ["json_actions-2"]
    assert summary["recovery_resolved"] is True
    assert summary["unresolved_partial_failure_ids"] == []


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
    assert trace["trace"][0]["loop"] == "native_tool_calls"
    assert trace["trace"][0]["native_tool_fallback"] == {
        "provider": "openai",
        "from_loop": "native_tool_calls",
        "to_loop": "json_actions",
        "reason": "native_tool_request_failed",
        "message": "provider rejected tool calls",
        "tool_schema_count": len(local_action_tool_schemas()),
    }
    assert trace["trace"][1]["loop"] == "json_actions"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["native_tool_fallback_count"] == 1
    assert result_artifact["native_tool_fallbacks"][0]["reason"] == (
        "native_tool_request_failed"
    )
    summary_markdown = (tmp_path / "artifacts" / "generic_edit_summary.md").read_text(
        encoding="utf-8"
    )
    assert "## Native Tool Fallback" in summary_markdown


@pytest.mark.asyncio
async def test_generic_edit_runtime_does_not_fallback_on_native_auth_failure(
    tmp_path: Path,
):
    target = tmp_path / "auth-failure.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolFatalFailureSession(
        [
            {
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "auth-failure.txt",
                        "content": "new\n",
                    },
                    {
                        "tool": "finish",
                        "summary": "Should not run JSON fallback",
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
        "change auth-failure.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "401 Unauthorized" in result.response_text
    assert target.read_text(encoding="utf-8") == "old\n"
    assert session.messages == []
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    assert len(trace["trace"]) == 1
    assert trace["trace"][0]["loop"] == "native_tool_calls"
    assert "native_tool_fallback" not in trace["trace"][0]


def test_bounded_subagent_attempts_rejects_bool():
    with pytest.raises(GenericEditRuntimeError, match="must be an integer"):
        bounded_subagent_attempts(True, field_name="tasks[1].max_attempts")


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
        timeout_seconds=10,
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
