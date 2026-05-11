import asyncio
import json
import sys
from pathlib import Path

import pytest
from agents.runtime.local_actions import local_action_tool_schemas
from core.providers.base import ProviderToolCall, ProviderToolCallResponse
from core.providers.config import ProviderConfig


def test_parse_args_with_provider_smoke():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = [
        "run.py",
        "--provider",
        "openai",
        "--model",
        "gpt-4o",
        "--provider-smoke",
        "--provider-smoke-prompt",
        "Say ok",
        "--provider-smoke-timeout",
        "12",
    ]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.provider == "openai"
    assert args.model == "gpt-4o"
    assert args.provider_smoke is True
    assert args.provider_smoke_prompt == "Say ok"
    assert args.provider_smoke_timeout == 12


def test_parse_args_with_provider_smoke_runtime():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = [
        "run.py",
        "--provider",
        "openai",
        "--provider-smoke",
        "--provider-smoke-runtime",
        "generic_edit",
    ]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.provider == "openai"
    assert args.provider_smoke is True
    assert args.provider_smoke_runtime == "generic_edit"


@pytest.mark.asyncio
async def test_run_provider_smoke_check_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeProvider:
        name = "openai"

        def __init__(self):
            self.created_session = False

        def validate_config(self):
            return True

        def create_session(self, session_config):
            self.created_session = True
            assert session_config.model == "gpt-4o"

        async def send_message(self, message: str):
            assert self.created_session is True
            assert message == "Say ok"
            yield "ok from provider"

    monkeypatch.setattr(
        "cli.provider_smoke_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="openai",
            openai_api_key="sk-test",
            openai_model="gpt-4o",
        ),
    )
    monkeypatch.setattr(
        "cli.provider_smoke_commands.create_engine_provider",
        lambda _config: FakeProvider(),
    )

    result = await run_provider_smoke_check(
        project_dir=tmp_path,
        model="gpt-4o",
        prompt="Say ok",
        timeout_seconds=1,
    )

    assert result.success is True
    assert result.provider == "openai"
    assert result.model == "gpt-4o"
    assert result.response_excerpt == "ok from provider"
    assert result.runtime_diagnostics["smoke_scope"] == "text_completion_only"
    assert result.runtime_diagnostics["validated_requirements"] == ["text_completion"]
    assert (
        "text_completion"
        in result.runtime_diagnostics["validated_runtime_capabilities"]
    )
    assert result.runtime_diagnostics["validated_runtime_missing_capabilities"] == []
    assert (
        "native_tool_loop"
        in result.runtime_diagnostics["full_autonomous_missing_capabilities"]
    )


@pytest.mark.asyncio
async def test_run_provider_smoke_check_generic_edit_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeGenericEditSession:
        provider_name = "openai"

        def __init__(self):
            self.calls = 0
            self.tool_results: list[tuple[str, str]] = []

        async def complete_with_tool_calls(self, message, tools):
            self.calls += 1
            assert any(tool["name"] == "write_file" for tool in tools)
            if self.calls == 1:
                assert "provider-smoke.txt" in message
                return ProviderToolCallResponse(
                    content="",
                    tool_calls=(
                        ProviderToolCall(
                            id="call_write",
                            name="write_file",
                            arguments={
                                "path": "provider-smoke.txt",
                                "content": "provider smoke ok\n",
                            },
                        ),
                    ),
                )
            return ProviderToolCallResponse(
                content="",
                tool_calls=(
                    ProviderToolCall(
                        id="call_finish",
                        name="finish",
                        arguments={
                            "summary": "Generic edit provider smoke passed",
                            "tests": [],
                            "risks": [],
                        },
                    ),
                ),
            )

        def add_tool_result(self, tool_call_id, name, result):
            self.tool_results.append((tool_call_id, name))

    class FakeProvider:
        name = "openai"

        def __init__(self):
            self.session = FakeGenericEditSession()

        def validate_config(self):
            return True

        def create_session(self, session_config):
            assert session_config.model == "gpt-4o"
            return self.session

        async def send_message(self, message: str):
            raise AssertionError(f"generic_edit smoke should not call {message!r}")

    fake_provider = FakeProvider()
    monkeypatch.setattr(
        "cli.provider_smoke_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="openai",
            openai_api_key="sk-test",
            openai_model="gpt-4o",
        ),
    )
    monkeypatch.setattr(
        "cli.provider_smoke_commands.create_engine_provider",
        lambda _config: fake_provider,
    )

    result = await run_provider_smoke_check(
        project_dir=tmp_path,
        model="gpt-4o",
        prompt=None,
        timeout_seconds=1,
        runtime_mode="generic_edit",
    )

    assert result.success is True
    assert result.provider == "openai"
    assert result.runtime_mode == "generic_edit"
    assert result.response_excerpt.startswith("Generic edit provider smoke passed")
    assert result.runtime_diagnostics["smoke_scope"] == "generic_edit_tool_loop"
    assert result.runtime_diagnostics["validated_runtime_mode"] == "generic_edit"
    assert "function_tools" in result.runtime_diagnostics["validated_requirements"]
    assert (
        "function_tools" in result.runtime_diagnostics["validated_runtime_capabilities"]
    )
    assert result.runtime_diagnostics["validated_runtime_missing_capabilities"] == []
    assert result.runtime_diagnostics["validated_runtime_execution"] == {
        "status": "complete",
        "stop_reason": "finish",
        "loop": "native_tool_calls",
        "action_count": 2,
        "failed_action_count": 0,
        "native_tool_fallback_count": 0,
        "native_tool_fallbacks": [],
        "tool_counts": {"finish": 1, "write_file": 1},
    }
    assert fake_provider.session.tool_results[0] == ("call_write", "write_file")


@pytest.mark.asyncio
async def test_run_provider_smoke_check_generic_edit_reports_native_tool_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeFallbackGenericEditSession:
        provider_name = "openai"

        def __init__(self):
            self.messages: list[str] = []

        async def complete_with_tool_calls(self, message, tools):
            await asyncio.sleep(0)
            raise RuntimeError("provider does not support tools")

        async def complete(self, message: str, stream: bool = True):
            assert stream is True
            self.messages.append(message)
            yield json.dumps(
                {
                    "actions": [
                        {
                            "tool": "write_file",
                            "path": "provider-smoke.txt",
                            "content": "provider smoke ok\n",
                        },
                        {
                            "tool": "finish",
                            "summary": "JSON fallback generic edit smoke passed",
                            "tests": [],
                            "risks": [],
                        },
                    ]
                }
            )

        def add_tool_result(self, tool_call_id, name, result):
            raise AssertionError("tool results should not be added after fallback")

    class FakeProvider:
        name = "openai"

        def __init__(self):
            self.session = FakeFallbackGenericEditSession()

        def validate_config(self):
            return True

        def create_session(self, session_config):
            assert session_config.model == "gpt-4o"
            return self.session

        async def send_message(self, message: str):
            raise AssertionError(f"generic_edit smoke should not call {message!r}")

    fake_provider = FakeProvider()
    monkeypatch.setattr(
        "cli.provider_smoke_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="openai",
            openai_api_key="sk-test",
            openai_model="gpt-4o",
        ),
    )
    monkeypatch.setattr(
        "cli.provider_smoke_commands.create_engine_provider",
        lambda _config: fake_provider,
    )

    result = await run_provider_smoke_check(
        project_dir=tmp_path,
        model="gpt-4o",
        prompt=None,
        timeout_seconds=1,
        runtime_mode="generic_edit",
    )

    assert result.success is True
    assert result.response_excerpt.startswith("JSON fallback generic edit smoke passed")
    assert result.runtime_diagnostics["validated_runtime_execution"] == {
        "status": "complete",
        "stop_reason": "finish",
        "loop": "json_actions",
        "action_count": 2,
        "failed_action_count": 0,
        "native_tool_fallback_count": 1,
        "native_tool_fallbacks": [
            {
                "provider": "openai",
                "from_loop": "native_tool_calls",
                "to_loop": "json_actions",
                "reason": "native_tool_request_failed",
                "message": "provider does not support tools",
                "tool_schema_count": len(local_action_tool_schemas()),
            }
        ],
        "tool_counts": {"finish": 1, "write_file": 1},
    }
    assert "Respond with exactly one JSON object" in fake_provider.session.messages[0]


def test_generic_edit_execution_diagnostics_includes_safe_resume_policy(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "error",
                "stop_reason": "unresolved_partial_failure",
                "loop": "json_actions",
                "action_count": 3,
                "failed_action_count": 1,
                "native_tool_fallback_count": 1,
                "tool_counts": {"finish": 1, "read_file": 1, "write_file": 1},
                "resume_policy": {
                    "status": "requires_resolution",
                    "strategy": "recover_partial_failure",
                    "can_resume": True,
                    "finish_blocked": True,
                    "next_iteration": 4,
                    "checkpoint_path": str(tmp_path / "checkpoint.json"),
                    "required_artifacts": {
                        "checkpoint": str(tmp_path / "checkpoint.json")
                    },
                    "required_resolution_action_kinds": [
                        "inspect_diff",
                        "rollback_transaction",
                    ],
                    "unresolved_partial_failure_ids": ["partial-failure-1"],
                    "unresolved_transaction_group_ids": ["transaction-group-1"],
                },
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["resume_policy"] == {
        "status": "requires_resolution",
        "strategy": "recover_partial_failure",
        "can_resume": True,
        "finish_blocked": True,
        "next_iteration": 4,
        "required_resolution_action_kinds": [
            "inspect_diff",
            "rollback_transaction",
        ],
        "unresolved_partial_failure_ids": ["partial-failure-1"],
        "unresolved_transaction_group_ids": ["transaction-group-1"],
    }


@pytest.mark.asyncio
async def test_run_provider_smoke_check_reports_validation_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeProvider:
        name = "openai"

        def validate_config(self):
            return False

        def get_validation_errors(self):
            return ["OpenAI provider requires OPENAI_API_KEY environment variable"]

    monkeypatch.setattr(
        "cli.provider_smoke_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="openai",
            openai_model="gpt-4o",
        ),
    )
    monkeypatch.setattr(
        "cli.provider_smoke_commands.create_engine_provider",
        lambda _config: FakeProvider(),
    )

    result = await run_provider_smoke_check(
        project_dir=tmp_path,
        model=None,
        prompt=None,
        timeout_seconds=1,
    )

    assert result.success is False
    assert result.provider == "openai"
    assert "incomplete" in result.message
    assert "OPENAI_API_KEY" in result.error_details
    assert result.runtime_diagnostics["validated_runtime_mode"] == "analysis_only"


def test_handle_provider_smoke_command_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        handle_provider_smoke_command,
    )

    async def fake_run_provider_smoke_check(**_kwargs):
        await asyncio.sleep(0)
        return ProviderSmokeResult(
            success=True,
            provider="openai",
            model="gpt-4o",
            runtime_mode="analysis_only",
            message="Provider smoke check passed",
            response_excerpt="ok",
        )

    monkeypatch.setattr(
        "cli.provider_smoke_commands.run_provider_smoke_check",
        fake_run_provider_smoke_check,
    )

    result = handle_provider_smoke_command(
        project_dir=tmp_path,
        model="gpt-4o",
        prompt=None,
        timeout_seconds=1,
        output_json=True,
    )
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert result.success is True
    assert payload["success"] is True
    assert payload["provider"] == "openai"
    assert payload["response_excerpt"] == "ok"
    assert payload["runtime_diagnostics"] == {}


def test_handle_provider_smoke_command_prints_generic_edit_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        handle_provider_smoke_command,
    )

    async def fake_run_provider_smoke_check(**_kwargs):
        await asyncio.sleep(0)
        return ProviderSmokeResult(
            success=True,
            provider="openai",
            model="gpt-4o",
            runtime_mode="generic_edit",
            message="Provider generic_edit smoke passed",
            runtime_diagnostics={
                "smoke_scope": "generic_edit_tool_loop",
                "validated_runtime_execution": {
                    "loop": "json_actions",
                    "action_count": 2,
                    "native_tool_fallback_count": 1,
                    "native_tool_fallbacks": [
                        {
                            "reason": "native_tool_request_failed",
                            "message": "provider does not support tools",
                        }
                    ],
                    "resume_policy": {
                        "status": "requires_resolution",
                        "strategy": "recover_partial_failure",
                        "required_resolution_action_kinds": [
                            "inspect_diff",
                            "rollback_transaction",
                        ],
                    },
                },
            },
        )

    monkeypatch.setattr(
        "cli.provider_smoke_commands.run_provider_smoke_check",
        fake_run_provider_smoke_check,
    )

    handle_provider_smoke_command(
        project_dir=tmp_path,
        model="gpt-4o",
        prompt=None,
        timeout_seconds=1,
        output_json=False,
    )
    output = capsys.readouterr().out

    assert "Execution loop" in output
    assert "json_actions" in output
    assert "Execution actions" in output
    assert "Native tool fallbacks" in output
    assert "Native fallback reason" in output
    assert "native_tool_request_failed" in output
    assert "Resume policy" in output
    assert "requires_resolution" in output
    assert "Resume required actions" in output
    assert "inspect_diff, rollback_transaction" in output
