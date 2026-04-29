import json
import sys
from pathlib import Path

import pytest
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
