import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from agents.runtime.local_actions import local_action_tool_schemas
from core.providers.base import ProviderToolCall, ProviderToolCallResponse
from core.providers.config import ProviderConfig


class _FakeSmokeProvider:
    name = "openai"

    def __init__(self, session):
        self.session = session

    def validate_config(self):
        return True

    def create_session(self, session_config):
        assert session_config.model == "gpt-4o"
        return self.session

    async def send_message(self, message: str):
        raise AssertionError(f"generic_edit smoke should not call {message!r}")


def _install_fake_generic_edit_smoke_provider(
    monkeypatch: pytest.MonkeyPatch,
    session,
) -> _FakeSmokeProvider:
    fake_provider = _FakeSmokeProvider(session)
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
    return fake_provider


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


def test_cli_main_import_does_not_require_claude_agent_sdk():
    backend_path = Path(__file__).resolve().parents[1] / "apps" / "backend"
    code = """
import importlib.abc
import sys

class BlockClaudeSdk(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "claude_agent_sdk":
            raise ModuleNotFoundError("No module named 'claude_agent_sdk'")
        return None

sys.meta_path.insert(0, BlockClaudeSdk())
import cli.main
print("ok")
"""
    env = {
        **os.environ,
        "PYTHONPATH": str(backend_path),
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


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


def test_parse_args_with_provider_smoke_mini_pipeline_runtime():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = [
        "run.py",
        "--provider",
        "openai",
        "--provider-smoke",
        "--provider-smoke-runtime",
        "mini_pipeline",
    ]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.provider == "openai"
    assert args.provider_smoke is True
    assert args.provider_smoke_runtime == "mini_pipeline"


def test_parse_args_with_provider_smoke_provider_e2e_runtime():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = [
        "run.py",
        "--provider",
        "openai",
        "--provider-smoke",
        "--provider-smoke-runtime",
        "provider_e2e",
    ]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.provider == "openai"
    assert args.provider_smoke is True
    assert args.provider_smoke_runtime == "provider_e2e"


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
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "text_completion_ready",
        "smoke_scope": "text_completion_only",
    }
    assert (
        "native_tool_loop"
        in result.runtime_diagnostics["full_autonomous_missing_capabilities"]
    )


@pytest.mark.asyncio
async def test_run_provider_smoke_check_provider_e2e_runtime_aggregates_suite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        _with_provider_contract_health,
        run_provider_smoke_check,
    )

    observed_runtime_modes: list[str] = []

    class FakeProvider:
        name = "openai"

        def validate_config(self):
            return True

        def create_session(self, session_config):
            return object()

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

    async def fake_generic_edit_smoke(**kwargs):
        provider = kwargs["provider"]
        observed_runtime_modes.append("generic_edit")
        return ProviderSmokeResult(
            success=True,
            provider=provider.name,
            model=kwargs["model"],
            runtime_mode="generic_edit",
            message="generic_edit passed",
            runtime_diagnostics=_with_provider_contract_health(
                {
                    "provider": provider.name,
                    "smoke_scope": "generic_edit_tool_loop",
                    "validated_runtime_execution": {
                        "tool_loop_contract": {
                            "status": "passed",
                            "tool_call_support": "native",
                            "tool_result_support": "normalized",
                            "fallback": "none",
                            "recovery_status": "not_required",
                        },
                    },
                },
                success=True,
            ),
        )

    async def fake_mini_pipeline_smoke(**kwargs):
        provider = kwargs["provider"]
        observed_runtime_modes.append("mini_pipeline")
        return ProviderSmokeResult(
            success=True,
            provider=provider.name,
            model=kwargs["model"],
            runtime_mode="mini_pipeline",
            message="mini_pipeline passed",
            runtime_diagnostics=_with_provider_contract_health(
                {
                    "provider": provider.name,
                    "smoke_scope": "mini_task_pipeline",
                    "validated_runtime_execution": {
                        "tool_loop_contract": {
                            "status": "passed",
                            "tool_call_support": "native",
                            "tool_result_support": "normalized",
                            "fallback": "none",
                            "recovery_status": "not_required",
                        },
                    },
                    "mini_pipeline": {
                        "status": "passed",
                        "recovery_loop": {
                            "status": "passed",
                            "recovery_status": "resolved",
                        },
                    },
                },
                success=True,
            ),
        )

    async def fake_transaction_batch_smoke(**kwargs):
        provider = kwargs["provider"]
        observed_runtime_modes.append("transaction_batch_probe")
        return ProviderSmokeResult(
            success=True,
            provider=provider.name,
            model=kwargs["model"],
            runtime_mode="transaction_batch_probe",
            message="transaction batch probe passed",
            runtime_diagnostics=_with_provider_contract_health(
                {
                    "provider": provider.name,
                    "smoke_scope": "transaction_batch_probe",
                    "validated_runtime_execution": {
                        "tool_loop_contract": {
                            "status": "passed",
                            "tool_call_support": "native",
                            "tool_result_support": "normalized",
                            "fallback": "none",
                            "recovery_status": "not_required",
                        },
                        "transaction_batch_contract": {
                            "status": "observed",
                            "batch_boundary_guard": "observed",
                            "transaction_batch_count": 1,
                            "open_transaction_batch_ids": [],
                            "batch_lifecycle_actions": [
                                "begin_batch",
                                "commit_batch",
                            ],
                            "batch_lifecycle_statuses": ["open", "committed"],
                        },
                    },
                },
                success=True,
            ),
        )

    monkeypatch.setattr(
        "cli.provider_smoke_commands._complete_provider_generic_edit_smoke",
        fake_generic_edit_smoke,
    )
    monkeypatch.setattr(
        "cli.provider_smoke_commands._complete_provider_mini_pipeline_smoke",
        fake_mini_pipeline_smoke,
    )
    monkeypatch.setattr(
        "cli.provider_smoke_commands._complete_provider_transaction_batch_smoke",
        fake_transaction_batch_smoke,
    )
    monkeypatch.setenv("AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES", "true")
    monkeypatch.setenv(
        "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR",
        "OpenAI returned 400 because this model does not support tools.",
    )
    monkeypatch.setenv(
        "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR",
        "OpenAI returned 502 bad gateway from the upstream provider.",
    )

    result = await run_provider_smoke_check(
        project_dir=tmp_path,
        model="gpt-4o",
        runtime_mode="provider_e2e",
    )

    assert result.success is True
    assert result.runtime_mode == "provider_e2e"
    assert observed_runtime_modes == [
        "generic_edit",
        "mini_pipeline",
        "transaction_batch_probe",
    ]
    assert result.runtime_diagnostics["smoke_scope"] == "direct_api_full_autonomy_e2e"
    assert result.runtime_diagnostics["provider_e2e_suite"] == {
        "status": "passed",
        "runs": [
            {
                "runtime_mode": "generic_edit",
                "status": "passed",
                "message": "generic_edit passed",
            },
            {
                "runtime_mode": "mini_pipeline",
                "status": "passed",
                "message": "mini_pipeline passed",
            },
            {
                "runtime_mode": "transaction_batch_probe",
                "status": "passed",
                "message": "transaction batch probe passed",
            },
            {
                "runtime_mode": "unsupported_tools_probe",
                "status": "passed",
                "message": "Unsupported tool classification probe passed",
            },
            {
                "runtime_mode": "gateway_model_probe",
                "status": "passed",
                "message": "Gateway/model limitation classification probe passed",
            },
            {
                "runtime_mode": "live_unsupported_tools_probe",
                "status": "passed",
                "message": "Live unsupported tool fault probe passed",
            },
            {
                "runtime_mode": "live_gateway_model_probe",
                "status": "passed",
                "message": "Live gateway/model fault probe passed",
            },
        ],
    }
    assert result.runtime_diagnostics["provider_e2e_live_fault_probes"] == {
        "status": "passed",
        "provider": "openai",
        "source": "provider_live_fault_fixture",
        "enabled": True,
        "required_env": [
            "AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES",
            (
                "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR "
                "or AUTO_CODE_PROVIDER_E2E_LIVE_UNSUPPORTED_TOOLS_ERROR"
            ),
            (
                "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR "
                "or AUTO_CODE_PROVIDER_E2E_LIVE_GATEWAY_MODEL_ERROR"
            ),
        ],
        "covered_cases": ["unsupported_tools", "gateway_model_limitations"],
        "probes": {
            "unsupported_tools": {
                "status": "passed",
                "source": "provider_live_fault_fixture",
                "reason": "unsupported_tools",
                "fixture_provider": "openai",
                "env_name": "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR",
            },
            "gateway_model_limitations": {
                "status": "passed",
                "source": "provider_live_fault_fixture",
                "reason": "gateway_error",
                "fixture_provider": "openai",
                "env_name": "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR",
            },
        },
    }
    assert result.runtime_diagnostics["provider_e2e_negative_probes"] == {
        "unsupported_tools": {
            "status": "passed",
            "source": "provider_adapter_negative_fixture",
            "reason": "unsupported_tools",
            "fixture_provider": "openai",
            "fixture_surface": "openai_compat",
        },
        "gateway_model_limitations": {
            "status": "passed",
            "source": "provider_adapter_negative_fixture",
            "reason": "gateway_error",
            "fixture_provider": "openai",
            "fixture_surface": "openai_compat",
        },
    }
    assert result.runtime_diagnostics["provider_e2e_negative_fixtures"] == {
        "status": "passed",
        "provider": "openai",
        "source": "provider_adapter_negative_fixture",
        "covered_cases": ["unsupported_tools", "gateway_model_limitations"],
    }
    reliability = result.runtime_diagnostics["provider_reliability"]
    assert reliability["status"] == "complete"
    assert reliability["observed_case_count"] == 8
    assert reliability["passed_case_count"] == 8
    assert reliability["required_case_count"] == 8
    assert reliability["uncovered_cases"] == []
    assert reliability["cases"][5:] == [
        {
            "case": "transaction_batches",
            "status": "passed",
            "source": "transaction_batch_contract",
        },
        {
            "case": "unsupported_tools",
            "status": "passed",
            "source": "provider_adapter_negative_fixture",
        },
        {
            "case": "gateway_model_limitations",
            "status": "passed",
            "source": "provider_adapter_negative_fixture",
        },
    ]
    assert result.runtime_diagnostics["provider_run_history"] == {
        "status": "recorded",
        "provider": "openai",
        "runtime_mode": "provider_e2e",
        "total_runs": 1,
        "passed_runs": 1,
        "failed_runs": 0,
        "last_status": "passed",
        "last_reliability_status": "complete",
        "last_provider_e2e_status": "passed",
        "trend": "provider_history_warming_up",
        "trend_reason": "single_history_run",
        "recent_window": 1,
        "recent_passed_runs": 1,
        "recent_failed_runs": 0,
        "consecutive_passes": 1,
        "consecutive_failures": 0,
        "path": ".auto-Codex/provider-smoke-history.json",
    }
    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["schema_version"] == 1
    assert len(history["runs"]) == 1
    assert history["runs"][0]["provider"] == "openai"
    assert history["runs"][0]["runtime_mode"] == "provider_e2e"
    assert history["runs"][0]["status"] == "passed"
    assert history["runs"][0]["reliability_status"] == "complete"
    assert history["runs"][0]["provider_e2e_status"] == "passed"
    assert history["providers"]["openai"]["total_runs"] == 1
    assert history["providers"]["openai"]["last_reliability_status"] == "complete"


def test_provider_reliability_diagnostics_marks_negative_fixtures_covered():
    from cli.provider_smoke_commands import (
        _provider_e2e_negative_fixture_payload,
        _with_provider_contract_health,
    )

    diagnostics = _with_provider_contract_health(
        {
            "provider": "openai",
            "smoke_scope": "direct_api_full_autonomy_e2e",
            "provider_e2e_negative_probes": _provider_e2e_negative_fixture_payload(
                "openai"
            ),
        },
        success=True,
    )

    reliability = diagnostics["provider_reliability"]
    assert reliability["cases"][5:] == [
        {
            "case": "transaction_batches",
            "status": "not_covered",
            "source": "provider_e2e_required",
        },
        {
            "case": "unsupported_tools",
            "status": "passed",
            "source": "provider_adapter_negative_fixture",
        },
        {
            "case": "gateway_model_limitations",
            "status": "passed",
            "source": "provider_adapter_negative_fixture",
        },
    ]


def test_provider_run_history_recovers_corrupt_artifact(tmp_path: Path):
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        _with_provider_run_history,
    )

    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text("{not valid json", encoding="utf-8")

    result = _with_provider_run_history(
        tmp_path,
        ProviderSmokeResult(
            success=True,
            provider="openai",
            model="gpt-4o",
            runtime_mode="provider_e2e",
            message="Provider e2e smoke suite passed",
            runtime_diagnostics={
                "smoke_scope": "direct_api_full_autonomy_e2e",
                "provider_e2e_suite": {"status": "passed", "runs": []},
                "provider_reliability": {
                    "status": "complete",
                    "passed_case_count": 8,
                    "required_case_count": 8,
                },
            },
        ),
    )

    assert result.runtime_diagnostics["provider_run_history"]["status"] == (
        "recorded_after_repair"
    )
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["schema_version"] == 1
    assert len(history["runs"]) == 1
    assert history["runs"][0]["provider"] == "openai"


def test_provider_run_history_reports_recent_trend(tmp_path: Path):
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        _with_provider_run_history,
    )

    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "timestamp": "2026-05-18T09:00:00Z",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "runtime_mode": "provider_e2e",
                        "status": "failed",
                    },
                    {
                        "timestamp": "2026-05-18T09:05:00Z",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "runtime_mode": "provider_e2e",
                        "status": "failed",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _with_provider_run_history(
        tmp_path,
        ProviderSmokeResult(
            success=True,
            provider="openai",
            model="gpt-4o",
            runtime_mode="provider_e2e",
            message="Provider e2e smoke suite passed",
            runtime_diagnostics={
                "provider_e2e_suite": {"status": "passed", "runs": []},
                "provider_reliability": {"status": "complete"},
            },
        ),
    )

    history_summary = result.runtime_diagnostics["provider_run_history"]
    assert history_summary["trend"] == "provider_history_recovering"
    assert history_summary["trend_reason"] == "latest_run_passed_after_failures"
    assert history_summary["recent_window"] == 3
    assert history_summary["recent_passed_runs"] == 1
    assert history_summary["recent_failed_runs"] == 2
    assert history_summary["consecutive_passes"] == 1
    assert history_summary["consecutive_failures"] == 0

    history = json.loads(history_path.read_text(encoding="utf-8"))
    provider_stats = history["providers"]["openai"]
    assert provider_stats["trend"] == "provider_history_recovering"
    assert provider_stats["recent_failed_runs"] == 2
    assert provider_stats["consecutive_passes"] == 1


def test_provider_e2e_negative_fixtures_cover_all_direct_api_providers():
    from cli.provider_smoke_commands import (
        PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS,
        _provider_e2e_negative_fixture_payload,
    )

    for provider_name in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        probes = _provider_e2e_negative_fixture_payload(provider_name)

        assert probes == {
            "unsupported_tools": {
                "status": "passed",
                "source": "provider_adapter_negative_fixture",
                "reason": "unsupported_tools",
                "fixture_provider": provider_name,
                "fixture_surface": probes["unsupported_tools"]["fixture_surface"],
            },
            "gateway_model_limitations": {
                "status": "passed",
                "source": "provider_adapter_negative_fixture",
                "reason": "gateway_error",
                "fixture_provider": provider_name,
                "fixture_surface": probes["gateway_model_limitations"][
                    "fixture_surface"
                ],
            },
        }


def test_provider_e2e_live_fault_probes_are_opt_in(monkeypatch: pytest.MonkeyPatch):
    from cli.provider_smoke_commands import _provider_e2e_live_fault_probe_payload

    monkeypatch.delenv("AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES", raising=False)

    probes = _provider_e2e_live_fault_probe_payload("openai")

    assert probes == {
        "status": "not_configured",
        "provider": "openai",
        "source": "provider_live_fault_fixture",
        "enabled": False,
        "required_env": [
            "AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES",
            (
                "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR "
                "or AUTO_CODE_PROVIDER_E2E_LIVE_UNSUPPORTED_TOOLS_ERROR"
            ),
            (
                "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR "
                "or AUTO_CODE_PROVIDER_E2E_LIVE_GATEWAY_MODEL_ERROR"
            ),
        ],
        "covered_cases": [],
    }


def test_provider_e2e_live_fault_probes_classify_opt_in_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import _provider_e2e_live_fault_probe_payload

    monkeypatch.setenv("AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES", "true")
    monkeypatch.setenv(
        "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR",
        "OpenAI returned 400 because this model does not support tools.",
    )
    monkeypatch.setenv(
        "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR",
        "OpenAI returned 502 bad gateway from the upstream provider.",
    )

    probes = _provider_e2e_live_fault_probe_payload("openai")

    assert probes == {
        "status": "passed",
        "provider": "openai",
        "source": "provider_live_fault_fixture",
        "enabled": True,
        "required_env": [
            "AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES",
            (
                "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR "
                "or AUTO_CODE_PROVIDER_E2E_LIVE_UNSUPPORTED_TOOLS_ERROR"
            ),
            (
                "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR "
                "or AUTO_CODE_PROVIDER_E2E_LIVE_GATEWAY_MODEL_ERROR"
            ),
        ],
        "covered_cases": ["unsupported_tools", "gateway_model_limitations"],
        "probes": {
            "unsupported_tools": {
                "status": "passed",
                "source": "provider_live_fault_fixture",
                "reason": "unsupported_tools",
                "fixture_provider": "openai",
                "env_name": "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR",
            },
            "gateway_model_limitations": {
                "status": "passed",
                "source": "provider_live_fault_fixture",
                "reason": "gateway_error",
                "fixture_provider": "openai",
                "env_name": "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR",
            },
        },
    }


def test_provider_e2e_live_fault_probes_accept_model_limitations(
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import _provider_e2e_live_fault_probe_payload

    monkeypatch.setenv("AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES", "true")
    monkeypatch.setenv(
        "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR",
        "OpenAI returned 400 because this model does not support tools.",
    )
    monkeypatch.setenv(
        "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR",
        "OpenAI returned model_not_found for this deployment.",
    )

    probes = _provider_e2e_live_fault_probe_payload("openai")

    assert probes["status"] == "passed"
    assert probes["covered_cases"] == [
        "unsupported_tools",
        "gateway_model_limitations",
    ]
    assert probes["probes"]["gateway_model_limitations"] == {
        "status": "passed",
        "source": "provider_live_fault_fixture",
        "reason": "model_unavailable",
        "fixture_provider": "openai",
        "env_name": "AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR",
    }


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

    fake_provider = _install_fake_generic_edit_smoke_provider(
        monkeypatch,
        FakeGenericEditSession(),
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
        "transaction_batch_contract": {
            "status": "not_observed",
            "batch_boundary_guard": "not_observed",
            "transaction_batch_count": 0,
            "open_transaction_batch_ids": [],
        },
        "tool_loop_contract": {
            "status": "passed",
            "tool_call_support": "native",
            "tool_result_support": "normalized",
            "fallback": "none",
            "recovery_status": "not_required",
        },
    }
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "tool_loop_ready",
        "smoke_scope": "generic_edit_tool_loop",
        "tool_call_support": "native",
        "tool_result_support": "normalized",
        "fallback": "none",
        "recovery_status": "not_required",
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

    fake_provider = _install_fake_generic_edit_smoke_provider(
        monkeypatch,
        FakeFallbackGenericEditSession(),
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
        "transaction_batch_contract": {
            "status": "not_observed",
            "batch_boundary_guard": "not_observed",
            "transaction_batch_count": 0,
            "open_transaction_batch_ids": [],
        },
        "tool_loop_contract": {
            "status": "passed",
            "tool_call_support": "json_fallback",
            "tool_result_support": "normalized",
            "fallback": "json_actions",
            "fallback_reason": "native_tool_request_failed",
            "recovery_status": "not_required",
        },
    }
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "tool_loop_limited",
        "smoke_scope": "generic_edit_tool_loop",
        "reason": "native_tool_request_failed",
        "tool_call_support": "json_fallback",
        "tool_result_support": "normalized",
        "fallback": "json_actions",
        "fallback_reason": "native_tool_request_failed",
        "recovery_status": "not_required",
    }
    assert "Respond with exactly one JSON object" in fake_provider.session.messages[0]


@pytest.mark.asyncio
async def test_run_provider_smoke_check_mini_pipeline_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeMiniPipelineGenericEditSession:
        provider_name = "openai"

        def __init__(self, scenario: str):
            self.scenario = scenario
            self.calls = 0
            self.tool_results: list[tuple[str, str]] = []

        async def complete_with_tool_calls(self, message, tools):
            self.calls += 1
            assert any(tool["name"] == "write_file" for tool in tools)
            if self.scenario == "coder":
                return self._complete_coder(message)
            if self.scenario == "recovery_initial":
                return self._complete_recovery_initial(message)
            if self.scenario == "recovery_resume":
                return self._complete_recovery_resume(message)
            raise AssertionError(f"unknown scenario: {self.scenario}")

        async def complete(self, message: str, stream: bool = True):
            assert stream is True
            self.calls += 1
            if self.scenario != "recovery_resume":
                raise AssertionError(
                    f"json resume should only use recovery_resume, got {self.scenario}"
                )
            assert "Required recovery actions" in message
            yield json.dumps(
                {
                    "actions": [
                        {
                            "tool": "repair_mutation",
                            "transaction_id": "native_tool_calls-1",
                            "paths": ["recovery-target.txt"],
                            "summary": "Accepted provider recovery target.",
                        },
                        {
                            "tool": "finish",
                            "summary": "Recovered the mini pipeline partial edit.",
                            "tests": ["python -m unittest -q"],
                            "risks": [],
                        },
                    ]
                }
            )

        def _complete_coder(self, message):
            assert "slugify" in message
            if self.calls == 1:
                return ProviderToolCallResponse(
                    content="",
                    tool_calls=(
                        ProviderToolCall(
                            id="call_write_slugify",
                            name="write_file",
                            arguments={
                                "path": "string_tools.py",
                                "content": (
                                    "import re\n\n\n"
                                    "def normalize_space(value: str) -> str:\n"
                                    '    return " ".join(value.split())\n\n\n'
                                    "def slugify(value: str) -> str:\n"
                                    "    slug = re.sub(\n"
                                    '        r"[^a-z0-9]+", "-", value.strip().lower()\n'
                                    "    )\n"
                                    '    return slug.strip("-")\n'
                                ),
                            },
                        ),
                    ),
                )
            return ProviderToolCallResponse(
                content="",
                tool_calls=(
                    ProviderToolCall(
                        id="call_finish_pipeline",
                        name="finish",
                        arguments={
                            "summary": "Implemented slugify and kept unittest coverage.",
                            "tests": ["python -m unittest -q"],
                            "risks": [],
                        },
                    ),
                ),
            )

        def _complete_recovery_initial(self, message):
            assert "recovery-target.txt" in message
            if self.calls == 1:
                return ProviderToolCallResponse(
                    content="",
                    tool_calls=(
                        ProviderToolCall(
                            id="call_recovery_write",
                            name="write_file",
                            arguments={
                                "path": "recovery-target.txt",
                                "content": "provider recovery ok\n",
                            },
                        ),
                        ProviderToolCall(
                            id="call_recovery_missing_read",
                            name="read_file",
                            arguments={"path": "missing-recovery.txt"},
                        ),
                    ),
                )
            return ProviderToolCallResponse(
                content="",
                tool_calls=(
                    ProviderToolCall(
                        id="call_recovery_blocked_finish",
                        name="finish",
                        arguments={
                            "summary": "Tried to finish before recovery",
                            "tests": [],
                            "risks": [],
                        },
                    ),
                ),
            )

        def _complete_recovery_resume(self, message):
            assert "Required recovery actions" in message
            return ProviderToolCallResponse(
                content="",
                tool_calls=(
                    ProviderToolCall(
                        id="call_repair_recovery",
                        name="repair_mutation",
                        arguments={
                            "transaction_id": "native_tool_calls-1",
                            "paths": ["recovery-target.txt"],
                            "summary": "Accepted provider recovery target.",
                        },
                    ),
                    ProviderToolCall(
                        id="call_finish_recovery",
                        name="finish",
                        arguments={
                            "summary": "Recovered the mini pipeline partial edit.",
                            "tests": ["python -m unittest -q"],
                            "risks": [],
                        },
                    ),
                ),
            )

        def add_tool_result(self, tool_call_id, name, result):
            self.tool_results.append((tool_call_id, name))

    class FakeMiniPipelineProvider:
        name = "openai"

        def __init__(self):
            self.sessions = [
                FakeMiniPipelineGenericEditSession("coder"),
                FakeMiniPipelineGenericEditSession("recovery_initial"),
                FakeMiniPipelineGenericEditSession("recovery_resume"),
            ]
            self.messages: list[str] = []

        def validate_config(self):
            return True

        def create_session(self, session_config):
            assert session_config.model == "gpt-4o"
            return self.sessions.pop(0)

        async def send_message(self, message: str):
            self.messages.append(message)
            if len(self.messages) == 1:
                yield "Plan: implement slugify, run unittest, review results."
            else:
                assert "python -m unittest -q" in message
                yield "Review passed: implementation satisfies the mini task."

    fake_provider = FakeMiniPipelineProvider()
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

    async def fake_run_mini_pipeline_tests(_project_dir, *, timeout_seconds):
        return 0, "OK"

    monkeypatch.setattr(
        "cli.provider_smoke_commands._run_mini_pipeline_tests",
        fake_run_mini_pipeline_tests,
    )

    result = await run_provider_smoke_check(
        project_dir=tmp_path,
        model="gpt-4o",
        prompt=None,
        timeout_seconds=3,
        runtime_mode="mini_pipeline",
    )

    assert result.success is True
    assert result.provider == "openai"
    assert result.runtime_mode == "mini_pipeline"
    assert result.response_excerpt.startswith("Review passed")
    assert result.runtime_diagnostics["smoke_scope"] == "mini_task_pipeline"
    assert result.runtime_diagnostics["validated_runtime_mode"] == "mini_pipeline"
    assert "function_tools" in result.runtime_diagnostics["validated_requirements"]
    assert result.runtime_diagnostics["validated_runtime_missing_capabilities"] == []
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "mini_pipeline_ready",
        "smoke_scope": "mini_task_pipeline",
        "tool_call_support": "native",
        "tool_result_support": "normalized",
        "fallback": "none",
        "recovery_status": "resolved",
        "recovery_loop_status": "passed",
    }
    assert result.runtime_diagnostics["mini_pipeline"] == {
        "status": "passed",
        "task": "Implement slugify(value: str) in string_tools.py.",
        "test_command": "python -m unittest -q",
        "test_exit_code": 0,
        "changed_files": ["string_tools.py"],
        "phases": [
            {"name": "planner", "status": "passed"},
            {"name": "coder", "status": "passed"},
            {"name": "tests", "status": "passed"},
            {"name": "recovery", "status": "passed"},
            {"name": "reviewer", "status": "passed"},
        ],
        "recovery_loop": {
            "status": "passed",
            "preflight_status": "ready",
            "resume_policy_status": "requires_resolution",
            "required_resolution_action_kinds": [
                "inspect_diff",
                "rollback_transaction",
            ],
            "resume_result_status": "continue",
            "recovery_status": "resolved",
            "workspace_guard_status": "clean",
            "changed_files": ["recovery-target.txt"],
        },
    }
    assert result.runtime_diagnostics["validated_runtime_execution"]["tool_counts"] == {
        "write_file": 1
    }
    assert fake_provider.messages[0].startswith("Plan a tiny Auto Code readiness task")
    assert fake_provider.sessions == []


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
                    "required_artifacts": [
                        "trace_artifact",
                        "recovery_plan_artifact",
                    ],
                    "required_resolution_action_kinds": [
                        "inspect_diff",
                        "rollback_transaction",
                    ],
                    "unresolved_partial_failure_ids": ["partial-failure-1"],
                    "unresolved_transaction_group_ids": ["transaction-group-1"],
                    "open_transaction_batch_ids": ["batch-1"],
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
        "required_artifacts": [
            "trace_artifact",
            "recovery_plan_artifact",
        ],
        "unresolved_partial_failure_ids": ["partial-failure-1"],
        "unresolved_transaction_group_ids": ["transaction-group-1"],
        "open_transaction_batch_ids": ["batch-1"],
    }


def test_generic_edit_execution_diagnostics_reports_batch_boundary_guard(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "error",
                "stop_reason": "batch_boundary_violation",
                "loop": "json_actions",
                "action_count": 0,
                "failed_action_count": 0,
                "native_tool_fallback_count": 0,
                "tool_counts": {},
                "transaction_batch_count": 0,
                "open_transaction_batch_ids": [],
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["transaction_batch_contract"] == {
        "status": "boundary_guarded",
        "batch_boundary_guard": "pre_execution_blocked",
        "transaction_batch_count": 0,
        "open_transaction_batch_ids": [],
        "boundary_error_count": 1,
        "boundary_error_reasons": ["batch_boundary_violation"],
    }


def test_generic_edit_execution_diagnostics_reports_batch_runtime_boundary_errors(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "stop_reason": "finish",
                "loop": "json_actions",
                "action_count": 4,
                "failed_action_count": 1,
                "native_tool_fallback_count": 0,
                "tool_counts": {
                    "begin_batch": 1,
                    "write_file": 1,
                    "commit_batch": 1,
                    "abort_batch": 1,
                },
                "transaction_batch_count": 1,
                "open_transaction_batch_ids": [],
                "transaction_batches": [
                    {
                        "id": "batch-1",
                        "status": "aborted",
                        "boundary_errors": [{"reason": "unresolved_batch_recovery"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["transaction_batch_contract"] == {
        "status": "boundary_guarded",
        "batch_boundary_guard": "runtime_blocked",
        "transaction_batch_count": 1,
        "open_transaction_batch_ids": [],
        "boundary_error_count": 1,
        "boundary_error_reasons": ["unresolved_batch_recovery"],
    }


def test_generic_edit_execution_diagnostics_reports_batch_recovery_actions(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    manifest_path = tmp_path / "generic_edit_artifact_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_type": "generic_edit_artifact_manifest",
                "recovery_timeline": [
                    {
                        "event_type": "action_result",
                        "tool": "run_command",
                        "timeline_stage": "batch_boundary_blocked",
                        "batch_boundary_error_reason": "opaque_batch_mutation",
                        "preferred_strategy": "abort_batch",
                        "required_next_action_kinds": [
                            "abort_batch",
                            "repair_mutation",
                        ],
                        "resolution_strategies": [
                            "abort_batch",
                            "repair_mutation",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "stop_reason": "finish",
                "loop": "json_actions",
                "action_count": 4,
                "failed_action_count": 1,
                "native_tool_fallback_count": 0,
                "tool_counts": {
                    "begin_batch": 1,
                    "write_file": 1,
                    "run_command": 1,
                    "abort_batch": 1,
                },
                "transaction_batch_count": 1,
                "open_transaction_batch_ids": [],
                "artifact_manifest_artifact": str(manifest_path),
                "transaction_batches": [
                    {
                        "id": "batch-1",
                        "status": "aborted",
                        "boundary_errors": [{"reason": "opaque_batch_mutation"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["transaction_batch_contract"] == {
        "status": "boundary_guarded",
        "batch_boundary_guard": "runtime_blocked",
        "transaction_batch_count": 1,
        "open_transaction_batch_ids": [],
        "boundary_error_count": 1,
        "boundary_error_reasons": ["opaque_batch_mutation"],
        "boundary_preferred_strategy": "abort_batch",
        "boundary_required_action_kinds": ["abort_batch", "repair_mutation"],
        "boundary_resolution_strategies": ["abort_batch", "repair_mutation"],
    }


def test_generic_edit_execution_diagnostics_reports_staged_batch_drift(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    manifest_path = tmp_path / "generic_edit_artifact_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_type": "generic_edit_artifact_manifest",
                "recovery_timeline": [
                    {
                        "event_type": "action_result",
                        "tool": "commit_batch",
                        "timeline_stage": "batch_boundary_blocked",
                        "batch_boundary_error_reason": "staged_batch_drift",
                        "staged_workspace_guard_status": "drifted",
                        "drift_paths": ["batched.txt"],
                        "preferred_strategy": "abort_batch",
                        "required_next_action_kinds": [
                            "abort_batch",
                            "repair_mutation",
                        ],
                        "resolution_strategies": [
                            "abort_batch",
                            "repair_mutation",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "stop_reason": "finish",
                "loop": "json_actions",
                "action_count": 4,
                "failed_action_count": 1,
                "native_tool_fallback_count": 0,
                "tool_counts": {
                    "begin_batch": 1,
                    "write_file": 1,
                    "commit_batch": 1,
                    "abort_batch": 1,
                },
                "transaction_batch_count": 1,
                "open_transaction_batch_ids": [],
                "artifact_manifest_artifact": str(manifest_path),
                "transaction_batches": [
                    {
                        "id": "batch-1",
                        "status": "aborted",
                        "lifecycle_events": [
                            {
                                "action": "begin_batch",
                                "transaction_id": "json_actions-1",
                                "status": "open",
                            },
                            {
                                "action": "commit_batch",
                                "transaction_id": "json_actions-1",
                                "status": "blocked",
                                "reason": "staged_batch_drift",
                            },
                            {
                                "action": "abort_batch",
                                "transaction_id": "json_actions-2",
                                "status": "aborted",
                            },
                        ],
                        "boundary_errors": [{"reason": "staged_batch_drift"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["transaction_batch_contract"] == {
        "status": "boundary_guarded",
        "batch_boundary_guard": "runtime_blocked",
        "transaction_batch_count": 1,
        "open_transaction_batch_ids": [],
        "boundary_error_count": 1,
        "boundary_error_reasons": ["staged_batch_drift"],
        "boundary_preferred_strategy": "abort_batch",
        "boundary_required_action_kinds": ["abort_batch", "repair_mutation"],
        "boundary_resolution_strategies": ["abort_batch", "repair_mutation"],
        "staged_workspace_guard_statuses": ["drifted"],
        "staged_drift_paths": ["batched.txt"],
        "batch_lifecycle_actions": ["begin_batch", "commit_batch", "abort_batch"],
        "batch_lifecycle_statuses": ["open", "blocked", "aborted"],
    }


def test_generic_edit_execution_diagnostics_reports_committed_batch_snapshots(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    manifest_path = tmp_path / "generic_edit_artifact_manifest.json"
    mutation_snapshot_path = tmp_path / "generic_edit_mutation_snapshots.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_type": "generic_edit_artifact_manifest",
                "recovery_timeline": [
                    {
                        "event_type": "action_result",
                        "tool": "commit_batch",
                        "ok": True,
                        "timeline_stage": "batch_committed",
                        "batch_id": "batch-1",
                        "batch_status": "committed",
                        "commit_operation_id": "batch-1:commit",
                        "committed_mutation_snapshot_ids": ["mutation-1", 2],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    mutation_snapshot_path.write_text(
        json.dumps(
            {
                "artifact_type": "generic_edit_mutation_snapshots",
                "snapshot_count": 1,
                "snapshots": [
                    {
                        "id": "mutation-1",
                        "batch_id": "batch-1",
                        "staged_status": "committed",
                        "staged_isolation": {
                            "status": "isolated",
                            "workspace_restored": True,
                            "baseline_paths": ["batched.txt", 7],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "stop_reason": "finish",
                "loop": "json_actions",
                "action_count": 3,
                "failed_action_count": 0,
                "native_tool_fallback_count": 0,
                "tool_counts": {
                    "begin_batch": 1,
                    "write_file": 1,
                    "commit_batch": 1,
                },
                "transaction_batch_count": 1,
                "open_transaction_batch_ids": [],
                "artifact_manifest_artifact": str(manifest_path),
                "transaction_batches": [
                    {
                        "id": "batch-1",
                        "status": "committed",
                        "commit_operation_ids": ["batch-1:commit", 9],
                        "lifecycle_events": [
                            {
                                "action": "begin_batch",
                                "transaction_id": "json_actions-1",
                                "status": "open",
                            },
                            {
                                "action": "commit_batch",
                                "transaction_id": "json_actions-1",
                                "status": "committed",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["transaction_batch_contract"] == {
        "status": "observed",
        "batch_boundary_guard": "observed",
        "transaction_batch_count": 1,
        "open_transaction_batch_ids": [],
        "batch_lifecycle_actions": ["begin_batch", "commit_batch"],
        "batch_lifecycle_statuses": ["open", "committed"],
        "committed_mutation_snapshot_ids": ["mutation-1"],
        "commit_operation_ids": ["batch-1:commit"],
        "staged_isolation_statuses": ["isolated"],
        "staged_workspace_restore_statuses": ["restored"],
        "staged_baseline_paths": ["batched.txt"],
    }


def test_generic_edit_execution_diagnostics_classifies_native_tool_contract(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "stop_reason": "finish",
                "loop": "native_tool_calls",
                "action_count": 2,
                "failed_action_count": 0,
                "native_tool_fallback_count": 0,
                "native_tool_fallbacks": [],
                "tool_counts": {"finish": 1, "write_file": 1},
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["tool_loop_contract"] == {
        "status": "passed",
        "tool_call_support": "native",
        "tool_result_support": "normalized",
        "fallback": "none",
        "recovery_status": "not_required",
    }


def test_generic_edit_execution_diagnostics_classifies_fallback_recovery_contract(
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
                "native_tool_fallbacks": [
                    {
                        "provider": "openai",
                        "from_loop": "native_tool_calls",
                        "to_loop": "json_actions",
                        "reason": "native_tool_request_failed",
                        "message": "provider does not support tools",
                    }
                ],
                "tool_counts": {"finish": 1, "read_file": 1, "write_file": 1},
                "resume_policy": {
                    "status": "requires_resolution",
                    "strategy": "recover_partial_failure",
                    "can_resume": True,
                    "finish_blocked": True,
                    "required_resolution_action_kinds": [
                        "inspect_diff",
                        "rollback_transaction",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["tool_loop_contract"] == {
        "status": "needs_recovery",
        "tool_call_support": "json_fallback",
        "tool_result_support": "partial_failure",
        "fallback": "json_actions",
        "fallback_reason": "native_tool_request_failed",
        "recovery_status": "requires_resolution",
        "blocking_reason": "unresolved_partial_failure",
    }


def test_generic_edit_execution_diagnostics_classifies_unsupported_tool_contract(
    tmp_path: Path,
):
    from cli.provider_smoke_commands import _generic_edit_execution_diagnostics

    result_path = tmp_path / "generic_edit_result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "stop_reason": "finish",
                "loop": "native_tool_calls",
                "action_count": 2,
                "failed_action_count": 1,
                "native_tool_fallback_count": 0,
                "native_tool_fallbacks": [],
                "tool_counts": {"finish": 1, "unsupported_local_tool": 1},
                "failed_tools": {"unsupported_local_tool": 1},
            }
        ),
        encoding="utf-8",
    )

    diagnostics = _generic_edit_execution_diagnostics(tmp_path)

    assert diagnostics is not None
    assert diagnostics["failed_tools"] == {"unsupported_local_tool": 1}
    assert diagnostics["tool_loop_contract"] == {
        "status": "unsupported_tools",
        "tool_call_support": "native",
        "tool_result_support": "failed",
        "fallback": "none",
        "recovery_status": "unresolved",
        "blocking_reason": "unsupported_local_tool",
    }


def test_provider_reliability_diagnostics_tracks_mini_pipeline_coverage():
    from cli.provider_smoke_commands import _with_provider_contract_health

    diagnostics = _with_provider_contract_health(
        {
            "provider": "openai",
            "smoke_scope": "mini_task_pipeline",
            "validated_runtime_execution": {
                "tool_loop_contract": {
                    "status": "passed",
                    "tool_call_support": "native",
                    "tool_result_support": "normalized",
                    "fallback": "none",
                    "recovery_status": "not_required",
                },
            },
            "mini_pipeline": {
                "status": "passed",
                "recovery_loop": {
                    "status": "passed",
                    "recovery_status": "resolved",
                },
            },
        },
        success=True,
    )

    assert diagnostics["provider_reliability"] == {
        "provider": "openai",
        "suite": "direct_api_full_autonomy",
        "status": "partial_coverage",
        "observed_case_count": 5,
        "passed_case_count": 5,
        "required_case_count": 8,
        "uncovered_cases": [
            "transaction_batches",
            "unsupported_tools",
            "gateway_model_limitations",
        ],
        "cases": [
            {
                "case": "text_completion",
                "status": "passed",
                "source": "mini_pipeline",
            },
            {
                "case": "generic_edit_tool_loop",
                "status": "passed",
                "source": "tool_loop_contract",
            },
            {
                "case": "native_tool_calls",
                "status": "passed",
                "source": "tool_loop_contract",
            },
            {
                "case": "tool_results",
                "status": "passed",
                "source": "tool_loop_contract",
            },
            {
                "case": "recovery_loop",
                "status": "passed",
                "source": "mini_pipeline",
            },
            {
                "case": "transaction_batches",
                "status": "not_covered",
                "source": "provider_e2e_required",
            },
            {
                "case": "unsupported_tools",
                "status": "not_covered",
                "source": "provider_e2e_required",
            },
            {
                "case": "gateway_model_limitations",
                "status": "not_covered",
                "source": "provider_e2e_required",
            },
        ],
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
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "configuration_blocked",
        "smoke_scope": "text_completion_only",
        "reason": "configuration_error",
        "message": "OpenAI provider requires OPENAI_API_KEY environment variable",
    }


@pytest.mark.asyncio
async def test_run_provider_smoke_check_classifies_gateway_limitations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeProvider:
        name = "litellm"

        def validate_config(self):
            return True

        def create_session(self, session_config):
            raise RuntimeError("502 Bad gateway from LiteLLM upstream")

    monkeypatch.setattr(
        "cli.provider_smoke_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="litellm",
            litellm_api_key="sk-test",
            litellm_model="openai/gpt-4o",
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
        runtime_mode="generic_edit",
    )

    assert result.success is False
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "gateway_blocked",
        "smoke_scope": "generic_edit_tool_loop",
        "reason": "gateway_error",
        "message": "502 Bad gateway from LiteLLM upstream",
    }


@pytest.mark.asyncio
async def test_run_provider_smoke_check_classifies_model_limitations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.provider_smoke_commands import run_provider_smoke_check

    class FakeProvider:
        name = "openrouter"

        def validate_config(self):
            return True

        def create_session(self, session_config):
            raise RuntimeError("Model not found: provider/model-without-tools")

    monkeypatch.setattr(
        "cli.provider_smoke_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="openrouter",
            openrouter_api_key="sk-test",
            openrouter_model="provider/model-without-tools",
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
        runtime_mode="generic_edit",
    )

    assert result.success is False
    assert result.runtime_diagnostics["provider_contract_health"] == {
        "status": "model_blocked",
        "smoke_scope": "generic_edit_tool_loop",
        "reason": "model_unavailable",
        "message": "Model not found: provider/model-without-tools",
    }


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
                "provider_contract_health": {
                    "status": "tool_loop_limited",
                    "reason": "native_tool_request_failed",
                },
                "provider_reliability": {
                    "status": "partial_coverage",
                    "observed_case_count": 4,
                    "passed_case_count": 3,
                    "required_case_count": 8,
                    "uncovered_cases": [
                        "transaction_batches",
                        "recovery_loop",
                        "unsupported_tools",
                    ],
                },
                "validated_runtime_execution": {
                    "loop": "json_actions",
                    "action_count": 2,
                    "native_tool_fallback_count": 1,
                    "tool_loop_contract": {
                        "status": "passed",
                        "tool_call_support": "json_fallback",
                        "tool_result_support": "normalized",
                        "fallback": "json_actions",
                        "fallback_reason": "native_tool_request_failed",
                        "recovery_status": "not_required",
                    },
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
                        "required_artifacts": [
                            "trace_artifact",
                            "recovery_plan_artifact",
                        ],
                        "unresolved_partial_failure_ids": ["json_actions-1"],
                        "unresolved_transaction_group_ids": ["transaction-group-1"],
                        "open_transaction_batch_ids": ["batch-1"],
                    },
                    "transaction_batch_contract": {
                        "status": "boundary_guarded",
                        "batch_boundary_guard": "runtime_blocked",
                        "boundary_error_reasons": ["opaque_batch_mutation"],
                        "boundary_preferred_strategy": "abort_batch",
                        "boundary_required_action_kinds": [
                            "abort_batch",
                            "repair_mutation",
                        ],
                        "boundary_resolution_strategies": [
                            "abort_batch",
                            "repair_mutation",
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
    assert "Provider health" in output
    assert "tool_loop_limited" in output
    assert "Provider health reason" in output
    assert "Provider reliability" in output
    assert "partial_coverage" in output
    assert "Reliability coverage" in output
    assert "3/8 passed, 4 observed" in output
    assert "Reliability uncovered" in output
    assert "transaction_batches, recovery_loop, unsupported_tools" in output
    assert "json_actions" in output
    assert "Tool-loop contract" in output
    assert "json_fallback" in output
    assert "Execution actions" in output
    assert "Native tool fallbacks" in output
    assert "Native fallback reason" in output
    assert "native_tool_request_failed" in output
    assert "Resume policy" in output
    assert "requires_resolution" in output
    assert "Resume required actions" in output
    assert "inspect_diff, rollback_transaction" in output
    assert "Resume required artifacts" in output
    assert "trace_artifact, recovery_plan_artifact" in output
    assert "Resume unresolved failures" in output
    assert "json_actions-1" in output
    assert "Resume unresolved groups" in output
    assert "transaction-group-1" in output
    assert "Resume open batches" in output
    assert "batch-1" in output
    assert "Batch contract" in output
    assert "boundary_guarded, runtime_blocked" in output
    assert "Batch boundary reasons" in output
    assert "opaque_batch_mutation" in output
    assert "Batch preferred strategy" in output
    assert "abort_batch" in output
    assert "Batch required actions" in output
    assert "abort_batch, repair_mutation" in output
    assert "Batch resolution strategies" in output
