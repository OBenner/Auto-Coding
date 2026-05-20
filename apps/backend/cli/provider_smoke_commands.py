"""CLI command for opt-in provider smoke checks."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.runtime import (
    RuntimeRequirements,
    create_runtime_session,
    get_runtime_mode,
    normalize_runtime_mode,
    resume_runtime_session,
    run_runtime_session,
)
from agents.runtime.adapters.completion import CompletionRuntimeSession
from agents.runtime.adapters.generic_edit import inspect_generic_edit_resume_artifacts
from agents.runtime.fallback import capabilities_for_runtime_mode
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
from core.providers.cost_calculator import (
    MODEL_PRICING,
    calculate_cost,
    format_cost,
    get_model_pricing,
)
from core.providers.factory import create_engine_provider
from task_logger import LogPhase
from ui import print_key_value, print_status

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_SMOKE_PROMPT = (
    "Reply with one short sentence confirming the provider smoke check works."
)
DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_CONTENT = "provider smoke ok\n"
DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_PROMPT = (
    "Use the available local tools to overwrite provider-smoke.txt with exactly "
    f"{DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_CONTENT!r}, then finish with a short "
    "summary. Do not edit any other file."
)
DEFAULT_PROVIDER_TRANSACTION_BATCH_SMOKE_PROMPT = (
    "Open a transaction batch with begin_batch using batch_id "
    "`provider-batch-smoke`, overwrite provider-smoke.txt with exactly "
    f"{DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_CONTENT!r}, commit the batch with "
    "commit_batch, then finish with a short summary. Do not edit any other file."
)
DEFAULT_PROVIDER_MINI_PIPELINE_TASK = (
    "Implement slugify(value: str) in string_tools.py."
)
DEFAULT_PROVIDER_MINI_PIPELINE_TEST_COMMAND = "python -m unittest -q"
PROVIDER_SMOKE_COST_ESTIMATE_INPUT_TOKENS = 10_000
PROVIDER_SMOKE_COST_ESTIMATE_OUTPUT_TOKENS = 2_000
DEFAULT_PROVIDER_MINI_PIPELINE_PLANNER_PROMPT = (
    "Plan a tiny Auto Code readiness task for a provider pipeline smoke check.\n\n"
    "Task: {task}\n\n"
    "Reply with a concise implementation plan. Do not edit files."
)
DEFAULT_PROVIDER_MINI_PIPELINE_CODER_PROMPT = (
    "Mini coding readiness task.\n\n"
    "Project files:\n"
    "- string_tools.py currently has normalize_space(value: str).\n"
    "- test_string_tools.py already contains unittest coverage for slugify.\n\n"
    "Task: {task}\n\n"
    "Acceptance criteria:\n"
    "- Add slugify(value: str) to string_tools.py.\n"
    "- It lowercases text, trims surrounding whitespace, replaces every run of "
    "non-alphanumeric characters with one hyphen, and trims leading/trailing "
    "hyphens.\n"
    f"- {DEFAULT_PROVIDER_MINI_PIPELINE_TEST_COMMAND} passes.\n\n"
    "Planner notes:\n{planner_response}\n\n"
    "Use the available local tools to edit the temporary project, then finish "
    "with a short summary and tests run."
)
DEFAULT_PROVIDER_MINI_PIPELINE_REVIEW_PROMPT = (
    "Review this completed mini Auto Code readiness task.\n\n"
    "Task: {task}\n"
    f"Verification command: {DEFAULT_PROVIDER_MINI_PIPELINE_TEST_COMMAND}\n"
    "Verification exit code: {test_exit_code}\n"
    "Verification output:\n{test_output}\n\n"
    "Final string_tools.py:\n{implementation}\n\n"
    "Reply with one short sentence stating whether the mini task is ready."
)
DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_CONTENT = "provider recovery ok\n"
DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_INITIAL_CONTENT = "pending recovery\n"
DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_PROMPT = (
    "Generic Edit recovery readiness exercise.\n\n"
    "Use the available local tools to create an intentional recoverable partial "
    "failure:\n"
    "- Overwrite recovery-target.txt with exactly "
    f"{DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_CONTENT!r}.\n"
    "- Then try to read missing-recovery.txt so the transaction records a "
    "partial failure.\n"
    "- After the observation reports the missing file, attempt to finish. The "
    "runtime should block finish and create a recovery checkpoint.\n"
)
MINI_PIPELINE_INITIAL_STRING_TOOLS = (
    'def normalize_space(value: str) -> str:\n    return " ".join(value.split())\n'
)
MINI_PIPELINE_TEST_FILE = (
    "import unittest\n\n"
    "from string_tools import slugify\n\n\n"
    "class SlugifyTests(unittest.TestCase):\n"
    "    def test_slugifies_mixed_text(self):\n"
    '        self.assertEqual(slugify("  Hello, Auto Code!  "), "hello-auto-code")\n\n'
    "    def test_trims_repeated_separators(self):\n"
    '        self.assertEqual(slugify("---Already  Sluggy---"), "already-sluggy")\n\n\n'
    'if __name__ == "__main__":\n'
    "    unittest.main()\n"
)
DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS = 30.0
PROVIDER_SMOKE_RUNTIME_MODES = (
    "analysis_only",
    "generic_edit",
    "mini_pipeline",
    "transaction_batch_probe",
    "provider_e2e",
)
PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS = (
    "openai",
    "google",
    "openrouter",
    "litellm",
    "zhipuai",
    "ollama",
)
PROVIDER_RELIABILITY_CASE_ORDER = (
    "text_completion",
    "generic_edit_tool_loop",
    "native_tool_calls",
    "tool_results",
    "recovery_loop",
    "transaction_batches",
    "unsupported_tools",
    "gateway_model_limitations",
)
PROVIDER_RELIABILITY_NEGATIVE_FIXTURES = {
    "openai": {
        "surface": "openai_compat",
        "unsupported_tools_error": (
            "OpenAI tool-call completion failed: Error code: 400 - "
            "This model does not support tools."
        ),
        "gateway_model_error": (
            "OpenAI tool-call completion failed: Error code: 502 - "
            "Bad gateway from upstream model provider."
        ),
    },
    "google": {
        "surface": "google_gemini",
        "unsupported_tools_error": (
            "Google tool-call completion failed: 400 function calling is not "
            "supported for this model."
        ),
        "gateway_model_error": (
            "Google tool-call completion failed: 503 upstream gateway timeout."
        ),
    },
    "openrouter": {
        "surface": "openrouter_openai_compat",
        "unsupported_tools_error": (
            "OpenRouter tool-call completion failed: Provider returned 400 "
            "unsupported tool_choice for selected model."
        ),
        "gateway_model_error": (
            "OpenRouter tool-call completion failed: 502 bad gateway from "
            "upstream provider."
        ),
    },
    "litellm": {
        "surface": "litellm_gateway",
        "unsupported_tools_error": (
            "LiteLLM tool-call completion failed: UnsupportedParamsError: "
            "function calling tools are not supported for this model."
        ),
        "gateway_model_error": (
            "LiteLLM tool-call completion failed: upstream gateway 504 timeout."
        ),
    },
    "zhipuai": {
        "surface": "zhipuai_glm",
        "unsupported_tools_error": (
            "ZhipuAI tool-call completion failed: function calling is not "
            "supported by this model."
        ),
        "gateway_model_error": (
            "ZhipuAI tool-call completion failed: 503 upstream connection timeout."
        ),
    },
    "ollama": {
        "surface": "ollama_openai_compat",
        "unsupported_tools_error": (
            "Ollama tool-call completion failed: local model does not support tools."
        ),
        "gateway_model_error": (
            "Ollama tool-call completion failed: connection refused by local "
            "Ollama gateway."
        ),
    },
}
PROVIDER_RELIABILITY_STATUS_RANK = {
    "not_covered": 0,
    "blocked": 1,
    "limited": 2,
    "passed": 3,
}
PROVIDER_SMOKE_HISTORY_RELATIVE_PATH = Path(
    ".auto-Codex",
    "provider-smoke-history.json",
)
PROVIDER_SMOKE_HISTORY_MAX_RUNS = 100
PROVIDER_SMOKE_HISTORY_TREND_WINDOW = 5
PROVIDER_E2E_LIVE_FAULT_PROBES_ENV = "AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES"
PROVIDER_E2E_LIVE_FAULT_CASES = {
    "unsupported_tools": {
        "suffix": "UNSUPPORTED_TOOLS_ERROR",
        "expected_statuses": ("unsupported_tools",),
        "runtime_mode": "live_unsupported_tools_probe",
        "passed_message": "Live unsupported tool fault probe passed",
        "skipped_message": "Live unsupported tool fault probe skipped",
        "failed_message": "Live unsupported tool fault probe failed",
    },
    "gateway_model_limitations": {
        "suffix": "GATEWAY_MODEL_ERROR",
        "expected_statuses": ("gateway_blocked", "model_blocked"),
        "runtime_mode": "live_gateway_model_probe",
        "passed_message": "Live gateway/model fault probe passed",
        "skipped_message": "Live gateway/model fault probe skipped",
        "failed_message": "Live gateway/model fault probe failed",
    },
}
PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS = 3
PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES = tuple(
    PROVIDER_E2E_LIVE_FAULT_CASES
)
PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL = {
    "provider_e2e_failed": "provider_e2e_failed",
    "provider_reliability_incomplete": "provider_reliability_incomplete",
    "provider_history_latest_failed": "latest_provider_smoke_failed",
    "provider_history_unknown": "history_missing",
    "provider_history_warming_up": "history_warming_up",
    "provider_history_flaky": "history_flaky",
    "provider_history_recovering": "history_recovering",
    "provider_history_degraded": "history_degraded",
    "provider_history_insufficient_runs": "history_insufficient_runs",
    "live_fault_probe_evidence_missing": "live_fault_probe_missing",
    "live_fault_probe_coverage_incomplete": "live_fault_coverage_incomplete",
}


@dataclass(frozen=True)
class ProviderSmokeResult:
    """Structured result for one provider smoke check."""

    success: bool
    provider: str
    model: str | None
    runtime_mode: str
    message: str
    response_excerpt: str | None = None
    error_details: str | None = None
    runtime_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result for JSON output."""
        return asdict(self)


class ProviderSendMessageSession:
    """Expose provider.send_message() as a completion session."""

    def __init__(self, provider: Any):
        self.provider_name = provider.name
        self._provider = provider

    async def complete(self, message: str, stream: bool = True):
        del stream
        async for chunk in self._provider.send_message(message):
            yield chunk


def _utc_timestamp() -> str:
    """Return a compact UTC timestamp for provider evidence artifacts."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _provider_smoke_history_path(project_dir: Path) -> Path:
    """Return the project-local provider smoke history path."""
    return project_dir / PROVIDER_SMOKE_HISTORY_RELATIVE_PATH


def _provider_smoke_history_record(
    result: ProviderSmokeResult,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a compact persisted provider smoke evidence record."""
    runtime_diagnostics = result.runtime_diagnostics
    reliability = runtime_diagnostics.get("provider_reliability")
    reliability = reliability if isinstance(reliability, dict) else {}
    provider_e2e_suite = runtime_diagnostics.get("provider_e2e_suite")
    provider_e2e_suite = (
        provider_e2e_suite if isinstance(provider_e2e_suite, dict) else {}
    )
    suite_runs = provider_e2e_suite.get("runs")
    e2e_case_counts = _provider_e2e_suite_case_counts(suite_runs)
    failed_suite_runs = (
        [
            str(run.get("runtime_mode") or "unknown")
            for run in suite_runs
            if isinstance(run, dict) and run.get("status") != "passed"
        ]
        if isinstance(suite_runs, list)
        else []
    )
    reliability_case_counts = _provider_reliability_case_counts(reliability)
    live_fault_probes = runtime_diagnostics.get("provider_e2e_live_fault_probes")
    live_fault_probes = live_fault_probes if isinstance(live_fault_probes, dict) else {}
    live_fault_probe_status = live_fault_probes.get("status")
    live_fault_probe_enabled = live_fault_probes.get("enabled")
    live_fault_probe_covered_cases = _string_list_payload(
        live_fault_probes.get("covered_cases")
    )
    live_fault_probe_missing_env = _string_list_payload(
        live_fault_probes.get("missing_env")
    )
    record: dict[str, Any] = {
        "timestamp": timestamp or _utc_timestamp(),
        "provider": result.provider,
        "model": result.model,
        "runtime_mode": result.runtime_mode,
        "status": "passed" if result.success else "failed",
        "message": result.message,
        "smoke_scope": runtime_diagnostics.get("smoke_scope"),
        "reliability_status": reliability.get("status"),
        "passed_case_count": reliability.get("passed_case_count"),
        "required_case_count": reliability.get("required_case_count"),
        "provider_e2e_status": provider_e2e_suite.get("status"),
        **e2e_case_counts,
        **reliability_case_counts,
        "failed_suite_runs": failed_suite_runs,
    }
    if isinstance(live_fault_probe_status, str) and live_fault_probe_status:
        record["live_fault_probe_status"] = live_fault_probe_status
    if isinstance(live_fault_probe_enabled, bool):
        record["live_fault_probe_enabled"] = live_fault_probe_enabled
    if live_fault_probe_covered_cases:
        record["live_fault_probe_covered_cases"] = live_fault_probe_covered_cases
    if live_fault_probe_missing_env:
        record["live_fault_probe_missing_env_count"] = len(live_fault_probe_missing_env)
    cost_record = _provider_smoke_cost_record(result)
    if cost_record:
        record.update(cost_record)
    if result.error_details:
        record["error_details"] = _response_excerpt(result.error_details, max_chars=240)
    return record


def _provider_e2e_suite_case_counts(suite_runs: Any) -> dict[str, int]:
    """Return per-run e2e case counters from a provider e2e suite."""
    if not isinstance(suite_runs, list):
        return {}
    case_count = 0
    passed_case_count = 0
    failed_case_count = 0
    for run in suite_runs:
        if not isinstance(run, dict):
            continue
        case_count += 1
        if run.get("status") == "passed":
            passed_case_count += 1
        else:
            failed_case_count += 1
    return {
        "e2e_case_count": case_count,
        "e2e_passed_case_count": passed_case_count,
        "e2e_failed_case_count": failed_case_count,
    }


def _provider_reliability_case_counts(reliability: dict[str, Any]) -> dict[str, int]:
    """Return direct-provider reliability case counters from diagnostics."""
    return {
        "reliability_observed_case_count": _int_payload_value(
            reliability,
            "observed_case_count",
        ),
        "reliability_passed_case_count": _int_payload_value(
            reliability,
            "passed_case_count",
        ),
        "reliability_required_case_count": _int_payload_value(
            reliability,
            "required_case_count",
        ),
    }


def _provider_smoke_cost_record(result: ProviderSmokeResult) -> dict[str, Any]:
    """Return actual token/cost evidence for a provider smoke run when available."""
    pricing_model = _provider_smoke_cost_pricing_model(result.model)
    if not pricing_model:
        return {}

    token_usage = _provider_smoke_token_usage_payload(result.runtime_diagnostics)
    if token_usage is None:
        input_tokens = PROVIDER_SMOKE_COST_ESTIMATE_INPUT_TOKENS
        output_tokens = PROVIDER_SMOKE_COST_ESTIMATE_OUTPUT_TOKENS
        cost_source = "fixed_token_estimate"
        cost_status = "estimated"
    else:
        input_tokens = token_usage["input_tokens"]
        output_tokens = token_usage["output_tokens"]
        cost_source = token_usage["source"]
        cost_status = "recorded"
    cost_usd = calculate_cost(pricing_model, input_tokens, output_tokens)
    pricing = get_model_pricing(pricing_model)
    return {
        "cost_status": cost_status,
        "cost_source": cost_source,
        "cost_input_tokens": input_tokens,
        "cost_output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "cost_formatted": format_cost(cost_usd),
        "cost_pricing_model": pricing_model,
        "cost_pricing_provider": pricing.get("provider"),
    }


def _provider_smoke_cost_pricing_model(model: Any) -> str | None:
    """Return a known pricing model from provider smoke evidence."""
    if not isinstance(model, str):
        return None
    trimmed = model.strip()
    if not trimmed:
        return None
    if trimmed in MODEL_PRICING and trimmed != "default":
        return trimmed
    for segment in reversed(trimmed.split("/")):
        if segment in MODEL_PRICING and segment != "default":
            return segment
    return None


def _provider_smoke_token_usage_payload(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, int | str] | None:
    """Return normalized token usage evidence from smoke diagnostics."""
    candidates: list[tuple[str, Any]] = [
        ("token_usage", runtime_diagnostics.get("token_usage")),
        ("usage", runtime_diagnostics.get("usage")),
    ]
    execution = runtime_diagnostics.get("validated_runtime_execution")
    if isinstance(execution, dict):
        candidates.extend(
            [
                (
                    "validated_runtime_execution.token_usage",
                    execution.get("token_usage"),
                ),
                ("validated_runtime_execution.usage", execution.get("usage")),
            ]
        )

    for source, payload in candidates:
        if not isinstance(payload, dict):
            continue
        input_tokens = _int_payload_value_from_keys(
            payload,
            ("input_tokens", "prompt_tokens"),
        )
        output_tokens = _int_payload_value_from_keys(
            payload,
            ("output_tokens", "completion_tokens"),
        )
        if input_tokens is None or output_tokens is None:
            continue
        return {
            "source": source,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    return None


def _int_payload_value_from_keys(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> int | None:
    """Return the first non-negative integer value from any candidate key."""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None


def _load_provider_smoke_history(
    history_path: Path,
) -> tuple[list[dict[str, Any]], bool]:
    """Load provider smoke history records, returning whether repair was needed."""
    if not history_path.exists():
        return [], False
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        return [], True
    if not isinstance(payload, dict):
        return [], True
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return [], True
    return [run for run in runs if isinstance(run, dict)], False


def _provider_smoke_history_streak(
    statuses: list[str],
    *,
    status: str,
) -> int:
    """Return the trailing streak length for a status."""
    streak = 0
    for run_status in reversed(statuses):
        if run_status != status:
            break
        streak += 1
    return streak


def _provider_smoke_history_trend(
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return compact recent-run trend diagnostics for one provider."""
    recent_runs = runs[-PROVIDER_SMOKE_HISTORY_TREND_WINDOW:]
    statuses = [str(run.get("status") or "unknown") for run in recent_runs]
    recent_passed_runs = statuses.count("passed")
    recent_failed_runs = statuses.count("failed")
    consecutive_passes = _provider_smoke_history_streak(
        statuses,
        status="passed",
    )
    consecutive_failures = _provider_smoke_history_streak(
        statuses,
        status="failed",
    )
    latest_status = statuses[-1] if statuses else "unknown"
    if not statuses:
        trend = "provider_history_unknown"
        trend_reason = "no_history_runs"
    elif len(statuses) == 1:
        trend = "provider_history_warming_up"
        trend_reason = "single_history_run"
    elif recent_failed_runs == 0 and recent_passed_runs == len(statuses):
        trend = "provider_history_stable"
        trend_reason = "recent_runs_all_passed"
    elif latest_status == "failed" and consecutive_failures >= 2:
        trend = "provider_history_degraded"
        trend_reason = "consecutive_recent_failures"
    elif latest_status == "passed" and recent_failed_runs > 0:
        trend = "provider_history_recovering"
        trend_reason = "latest_run_passed_after_failures"
    else:
        trend = "provider_history_flaky"
        trend_reason = "mixed_recent_results"
    return {
        "trend": trend,
        "trend_reason": trend_reason,
        "recent_window": len(recent_runs),
        "recent_passed_runs": recent_passed_runs,
        "recent_failed_runs": recent_failed_runs,
        "consecutive_passes": consecutive_passes,
        "consecutive_failures": consecutive_failures,
        "recent_runs": _provider_smoke_history_recent_runs(recent_runs),
        **_provider_smoke_history_eval_trends(recent_runs),
    }


def _provider_smoke_history_recent_runs(
    runs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return a compact normalized timeline for the latest provider runs."""
    timeline: list[dict[str, str]] = []
    fields = (
        "timestamp",
        "status",
        "runtime_mode",
        "model",
        "reliability_status",
        "provider_e2e_status",
        "live_fault_probe_status",
    )
    for run in runs:
        item = {
            field: value
            for field in fields
            if isinstance((value := run.get(field)), str) and value
        }
        if item:
            timeline.append(item)
    return timeline


def _provider_smoke_history_provider_stats(
    runs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return per-provider aggregate history stats from persisted records."""
    providers: dict[str, dict[str, Any]] = {}
    provider_runs: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        provider = str(run.get("provider") or "unknown")
        status = str(run.get("status") or "unknown")
        provider_runs.setdefault(provider, []).append(run)
        stats = providers.setdefault(provider, _provider_smoke_empty_provider_stats())
        _provider_smoke_history_apply_run_stats(stats, run, status=status)
    for provider, stats in providers.items():
        stats["live_fault_probe_covered_cases"] = sorted(
            stats["live_fault_probe_covered_cases"]
        )
        stats.update(_provider_smoke_history_trend(provider_runs.get(provider, [])))
        stats.update(_provider_smoke_history_metrics(stats))
    return providers


def _provider_smoke_empty_provider_stats() -> dict[str, Any]:
    """Return a fresh provider history stats accumulator."""
    return {
        "total_runs": 0,
        "passed_runs": 0,
        "failed_runs": 0,
        "last_status": "unknown",
        "last_runtime_mode": "unknown",
        "last_model": None,
        "last_run_at": None,
        "last_reliability_status": None,
        "last_provider_e2e_status": None,
        "e2e_case_count": 0,
        "e2e_passed_case_count": 0,
        "e2e_failed_case_count": 0,
        "reliability_observed_case_count": 0,
        "reliability_passed_case_count": 0,
        "reliability_required_case_count": 0,
        "last_live_fault_probe_status": None,
        "live_fault_probe_enabled_runs": 0,
        "live_fault_probe_passed_runs": 0,
        "live_fault_probe_covered_cases": [],
    }


def _provider_smoke_history_apply_run_stats(
    stats: dict[str, Any],
    run: dict[str, Any],
    *,
    status: str,
) -> None:
    """Apply one persisted provider-smoke run to aggregate provider stats."""
    stats["total_runs"] += 1
    if status == "passed":
        stats["passed_runs"] += 1
    elif status == "failed":
        stats["failed_runs"] += 1
    stats["last_status"] = status
    stats["last_runtime_mode"] = run.get("runtime_mode")
    stats["last_model"] = run.get("model")
    stats["last_run_at"] = run.get("timestamp")
    stats["last_reliability_status"] = run.get("reliability_status")
    stats["last_provider_e2e_status"] = run.get("provider_e2e_status")
    _provider_smoke_history_apply_case_stats(stats, run)
    _provider_smoke_history_apply_live_fault_stats(stats, run)
    _provider_smoke_history_apply_cost_stats(stats, run)


def _provider_smoke_history_apply_case_stats(
    stats: dict[str, Any],
    run: dict[str, Any],
) -> None:
    """Apply granular e2e and reliability case counters from one run."""
    for key in (
        "e2e_case_count",
        "e2e_passed_case_count",
        "e2e_failed_case_count",
        "reliability_observed_case_count",
        "reliability_passed_case_count",
        "reliability_required_case_count",
    ):
        stats[key] = _int_payload_value(stats, key) + _int_payload_value(run, key)


def _provider_smoke_history_apply_live_fault_stats(
    stats: dict[str, Any],
    run: dict[str, Any],
) -> None:
    """Apply live-fault probe evidence from one persisted run."""
    live_fault_probe_status = run.get("live_fault_probe_status")
    stats["last_live_fault_probe_status"] = (
        live_fault_probe_status
        if isinstance(live_fault_probe_status, str) and live_fault_probe_status
        else None
    )
    if run.get("live_fault_probe_enabled") is True:
        stats["live_fault_probe_enabled_runs"] += 1
    if live_fault_probe_status == "passed":
        stats["live_fault_probe_passed_runs"] += 1

    existing_cases = stats["live_fault_probe_covered_cases"]
    for covered_case in _string_list_payload(run.get("live_fault_probe_covered_cases")):
        if covered_case not in existing_cases:
            existing_cases.append(covered_case)


def _provider_smoke_history_apply_cost_stats(
    stats: dict[str, Any],
    run: dict[str, Any],
) -> None:
    """Apply token/cost evidence from one persisted run."""
    cost_status = run.get("cost_status")
    if cost_status not in {"recorded", "estimated"}:
        return
    input_tokens = _int_payload_value(run, "cost_input_tokens")
    output_tokens = _int_payload_value(run, "cost_output_tokens")
    cost_usd = _float_payload_value(run, "cost_usd")
    if cost_usd is None:
        return

    if cost_status == "estimated" and stats.get("cost_status") == "recorded":
        _provider_smoke_history_apply_latest_cost_stats(
            stats,
            run,
            cost_status=cost_status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        return
    if cost_status == "recorded" and stats.get("cost_status") == "estimated":
        _provider_smoke_history_reset_cost_stats(stats)

    if stats.get("cost_status") != "recorded":
        stats["cost_status"] = cost_status
    stats["cost_observed_run_count"] = (
        _int_payload_value(stats, "cost_observed_run_count") + 1
    )
    stats["cost_total_input_tokens"] = (
        _int_payload_value(stats, "cost_total_input_tokens") + input_tokens
    )
    stats["cost_total_output_tokens"] = (
        _int_payload_value(stats, "cost_total_output_tokens") + output_tokens
    )
    stats["cost_total_usd"] = round(
        float(stats.get("cost_total_usd") or 0.0) + cost_usd,
        10,
    )
    stats["cost_total_formatted"] = format_cost(stats["cost_total_usd"])
    _provider_smoke_history_apply_latest_cost_stats(
        stats,
        run,
        cost_status=cost_status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
    stats["cost_pricing_model"] = run.get("cost_pricing_model")
    stats["cost_pricing_provider"] = run.get("cost_pricing_provider")


def _provider_smoke_history_apply_latest_cost_stats(
    stats: dict[str, Any],
    run: dict[str, Any],
    *,
    cost_status: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    """Apply latest-run cost evidence without necessarily changing totals."""
    stats["cost_last_status"] = cost_status
    stats["cost_last_source"] = run.get("cost_source")
    stats["cost_last_input_tokens"] = input_tokens
    stats["cost_last_output_tokens"] = output_tokens
    stats["cost_last_usd"] = cost_usd
    stats["cost_last_formatted"] = format_cost(cost_usd)
    stats["cost_last_pricing_model"] = run.get("cost_pricing_model")
    stats["cost_last_pricing_provider"] = run.get("cost_pricing_provider")


def _provider_smoke_history_reset_cost_stats(stats: dict[str, Any]) -> None:
    """Clear estimated cost totals before recorded usage takes precedence."""
    for key in (
        "cost_status",
        "cost_observed_run_count",
        "cost_total_input_tokens",
        "cost_total_output_tokens",
        "cost_total_usd",
        "cost_total_formatted",
        "cost_last_status",
        "cost_last_source",
        "cost_last_input_tokens",
        "cost_last_output_tokens",
        "cost_last_usd",
        "cost_last_formatted",
        "cost_last_pricing_model",
        "cost_last_pricing_provider",
        "cost_pricing_model",
        "cost_pricing_provider",
    ):
        stats.pop(key, None)


def _provider_smoke_percent_metric(
    numerator: int,
    denominator: int,
) -> int | None:
    """Return a rounded percentage metric when a denominator is available."""
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100)


def _provider_smoke_history_eval_trends(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return score and cost trend deltas from the two latest usable runs."""
    quality_trend, quality_delta = _provider_smoke_history_score_trend(
        runs,
        _provider_smoke_run_quality_score,
    )
    stability_trend, stability_delta = _provider_smoke_history_score_trend(
        runs,
        _provider_smoke_run_stability_score,
    )
    safety_trend, safety_delta = _provider_smoke_history_score_trend(
        runs,
        _provider_smoke_run_safety_score,
    )
    cost_trend, cost_delta = _provider_smoke_history_cost_trend(runs)
    cost_delta_formatted = _provider_smoke_signed_cost_delta(cost_delta)
    return {
        "quality_trend": quality_trend,
        "quality_delta_percent": quality_delta,
        "stability_trend": stability_trend,
        "stability_delta_percent": stability_delta,
        "safety_trend": safety_trend,
        "safety_delta_percent": safety_delta,
        "cost_trend": cost_trend,
        "cost_delta_usd": cost_delta,
        "cost_delta_formatted": cost_delta_formatted,
    }


def _provider_smoke_history_score_trend(
    runs: list[dict[str, Any]],
    score_getter: Callable[[dict[str, Any]], int | None],
) -> tuple[str, int | None]:
    """Return improving/degrading/stable trend from the latest two score values."""
    scores = [score for run in runs if (score := score_getter(run)) is not None]
    if len(scores) < 2:
        return "trend_insufficient_data", None
    delta = scores[-1] - scores[-2]
    if delta > 0:
        return "score_improving", delta
    if delta < 0:
        return "score_degrading", delta
    return "score_stable", 0


def _provider_smoke_run_quality_score(run: dict[str, Any]) -> int | None:
    """Return a per-run quality score from e2e cases or pass/fail status."""
    e2e_score = _provider_smoke_percent_metric(
        _int_payload_value(run, "e2e_passed_case_count"),
        _int_payload_value(run, "e2e_case_count"),
    )
    if e2e_score is not None:
        return e2e_score
    return _provider_smoke_run_status_score(run)


def _provider_smoke_run_stability_score(run: dict[str, Any]) -> int | None:
    """Return a per-run stability score from the latest run status."""
    return _provider_smoke_run_status_score(run)


def _provider_smoke_run_status_score(run: dict[str, Any]) -> int | None:
    """Return a simple pass/fail score for one persisted run."""
    status = run.get("status")
    if status == "passed":
        return 100
    if status == "failed":
        return 0
    return None


def _provider_smoke_run_safety_score(run: dict[str, Any]) -> int | None:
    """Return the strictest per-run safety score from reliability/live-fault data."""
    reliability_score = _provider_smoke_percent_metric(
        _int_payload_value(run, "reliability_passed_case_count"),
        _int_payload_value(run, "reliability_required_case_count"),
    )
    live_fault_score = _provider_smoke_percent_metric(
        len(set(_string_list_payload(run.get("live_fault_probe_covered_cases")))),
        len(PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES),
    )
    scores = [
        score for score in (reliability_score, live_fault_score) if score is not None
    ]
    return min(scores) if scores else None


def _provider_smoke_history_cost_trend(
    runs: list[dict[str, Any]],
) -> tuple[str, float | None]:
    """Return cost trend from the latest two per-run cost values."""
    costs = [
        cost
        for run in runs
        if (cost := _float_payload_value(run, "cost_usd")) is not None
    ]
    if len(costs) < 2:
        return "cost_insufficient_data", None
    delta = round(costs[-1] - costs[-2], 10)
    if delta > 0:
        return "cost_increasing", delta
    if delta < 0:
        return "cost_decreasing", delta
    return "cost_stable", 0.0


def _provider_smoke_signed_cost_delta(delta: float | None) -> str | None:
    """Return a signed human-readable cost delta."""
    if delta is None:
        return None
    sign = ""
    if delta > 0:
        sign = "+"
    elif delta < 0:
        sign = "-"
    return f"{sign}{format_cost(abs(delta))}"


def _provider_smoke_history_metrics(stats: dict[str, Any]) -> dict[str, Any]:
    """Return quality and live-safety metrics from provider smoke history."""
    total_runs = int(stats.get("total_runs") or 0)
    passed_runs = int(stats.get("passed_runs") or 0)
    recent_window = int(stats.get("recent_window") or 0)
    recent_passed_runs = int(stats.get("recent_passed_runs") or 0)
    e2e_case_count = _int_payload_value(stats, "e2e_case_count")
    e2e_passed_case_count = _int_payload_value(stats, "e2e_passed_case_count")
    reliability_required_case_count = _int_payload_value(
        stats,
        "reliability_required_case_count",
    )
    reliability_passed_case_count = _int_payload_value(
        stats,
        "reliability_passed_case_count",
    )
    required_live_fault_case_count = len(
        PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
    )
    observed_live_fault_case_count = len(
        _string_list_payload(stats.get("live_fault_probe_covered_cases"))
    )
    return {
        "pass_rate_percent": _provider_smoke_percent_metric(
            passed_runs,
            total_runs,
        ),
        "recent_pass_rate_percent": _provider_smoke_percent_metric(
            recent_passed_runs,
            recent_window,
        ),
        "e2e_case_pass_rate_percent": _provider_smoke_percent_metric(
            e2e_passed_case_count,
            e2e_case_count,
        ),
        "reliability_case_pass_rate_percent": _provider_smoke_percent_metric(
            reliability_passed_case_count,
            reliability_required_case_count,
        ),
        "observed_live_fault_case_count": observed_live_fault_case_count,
        "required_live_fault_case_count": required_live_fault_case_count,
        "live_fault_probe_case_coverage_percent": _provider_smoke_percent_metric(
            observed_live_fault_case_count,
            required_live_fault_case_count,
        ),
    }


def _provider_smoke_history_payload(
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the persisted provider smoke history artifact payload."""
    bounded_runs = runs[-PROVIDER_SMOKE_HISTORY_MAX_RUNS:]
    return {
        "schema_version": 1,
        "runs": bounded_runs,
        "providers": _provider_smoke_history_provider_stats(bounded_runs),
    }


def _provider_autonomous_readiness_diagnostics(
    result: ProviderSmokeResult,
    history_summary: dict[str, Any],
) -> dict[str, Any]:
    """Return provider autonomous-readiness recommendation from e2e evidence."""
    runtime_diagnostics = result.runtime_diagnostics
    provider = result.provider
    if provider.lower() not in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        return {
            "status": "not_required",
            "provider": provider,
            "source": "provider_autonomous_readiness",
            "recommendation": "not_required",
            "recommendation_reasons": [],
            "blockers": [],
            "warnings": [],
            "next_actions": [],
            "requirements": {},
            "missing_requirements": [],
            "evidence": [],
        }

    blockers: list[str] = []
    warnings: list[str] = []
    evidence: list[str] = []

    _provider_readiness_suite_evidence(runtime_diagnostics, blockers, evidence)
    _provider_readiness_reliability_evidence(runtime_diagnostics, blockers, evidence)
    history_warning_offset = len(warnings)
    _provider_readiness_history_evidence(history_summary, blockers, warnings, evidence)
    history_warnings = warnings[history_warning_offset:]
    del warnings[history_warning_offset:]
    _provider_readiness_live_fault_evidence(history_summary, warnings, evidence)
    warnings.extend(history_warnings)

    status, recommendation = _provider_readiness_status(blockers, warnings)
    requirements = _provider_readiness_requirements(history_summary)
    return {
        "status": status,
        "provider": provider,
        "source": "provider_autonomous_readiness",
        "recommendation": recommendation,
        "recommendation_reasons": _provider_readiness_recommendation_reasons(
            status,
            blockers,
            warnings,
        ),
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": _provider_readiness_next_actions(blockers, warnings),
        "requirements": requirements,
        "missing_requirements": _provider_readiness_missing_requirements(
            blockers,
            requirements,
        ),
        "evidence": evidence,
    }


def _provider_readiness_suite_evidence(
    runtime_diagnostics: dict[str, Any],
    blockers: list[str],
    evidence: list[str],
) -> None:
    """Apply provider e2e suite evidence to readiness lists."""
    provider_e2e_suite = runtime_diagnostics.get("provider_e2e_suite")
    provider_e2e_suite = (
        provider_e2e_suite if isinstance(provider_e2e_suite, dict) else {}
    )
    if provider_e2e_suite.get("status") == "passed":
        evidence.append("provider_e2e_passed")
    else:
        blockers.append("provider_e2e_failed")


def _provider_readiness_reliability_evidence(
    runtime_diagnostics: dict[str, Any],
    blockers: list[str],
    evidence: list[str],
) -> None:
    """Apply reliability coverage evidence to readiness lists."""
    reliability = runtime_diagnostics.get("provider_reliability")
    reliability = reliability if isinstance(reliability, dict) else {}
    if reliability.get("status") == "complete":
        evidence.append("provider_reliability_complete")
    else:
        blockers.append("provider_reliability_incomplete")


def _provider_readiness_history_evidence(
    history_summary: dict[str, Any],
    blockers: list[str],
    warnings: list[str],
    evidence: list[str],
) -> None:
    """Apply provider history trend evidence to readiness lists."""
    if (
        history_summary.get("status") == "record_failed"
        or "last_status" not in history_summary
        or history_summary.get("last_status") is None
    ):
        warnings.append("provider_history_unknown")
        return

    if history_summary.get("last_status") != "passed":
        blockers.append("provider_history_latest_failed")

    trend = history_summary.get("trend")
    if trend == "provider_history_stable":
        if _provider_readiness_history_is_stable_enough(history_summary):
            evidence.append("provider_history_stable")
        else:
            warnings.append("provider_history_insufficient_runs")
    elif isinstance(trend, str) and trend:
        warnings.append(trend)


def _provider_readiness_history_is_stable_enough(
    history_summary: dict[str, Any],
) -> bool:
    """Return whether persisted history has enough stable runs for promotion."""
    return (
        _provider_readiness_recent_window(history_summary)
        >= PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS
        and _provider_readiness_consecutive_passes(history_summary)
        >= PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS
    )


def _provider_readiness_live_fault_evidence(
    history_summary: dict[str, Any],
    warnings: list[str],
    evidence: list[str],
) -> None:
    """Apply live fault probe evidence to readiness lists."""
    if history_summary.get("last_live_fault_probe_status") == "passed":
        evidence.append("live_fault_probes_passed")
        if not _provider_readiness_live_fault_coverage_complete(history_summary):
            warnings.append("live_fault_probe_coverage_incomplete")
    else:
        warnings.append("live_fault_probe_evidence_missing")


def _provider_readiness_live_fault_coverage_complete(
    history_summary: dict[str, Any],
) -> bool:
    """Return whether live fault probes covered every required provider fault."""
    covered_cases = set(
        _string_list_payload(history_summary.get("live_fault_probe_covered_cases"))
    )
    return all(
        required_case in covered_cases
        for required_case in PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
    )


def _provider_readiness_requirements(
    history_summary: dict[str, Any],
) -> dict[str, Any]:
    """Return structured readiness requirement evidence for operators."""
    recent_window = _provider_readiness_recent_window(history_summary)
    consecutive_passes = _provider_readiness_consecutive_passes(history_summary)
    required_live_fault_cases = sorted(
        PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
    )
    live_fault_covered_cases = sorted(
        _string_list_payload(history_summary.get("live_fault_probe_covered_cases"))
    )
    live_fault_missing_cases = [
        required_case
        for required_case in required_live_fault_cases
        if required_case not in live_fault_covered_cases
    ]
    live_fault_coverage_complete = (
        history_summary.get("last_live_fault_probe_status") == "passed"
        and not live_fault_missing_cases
    )
    return {
        "min_stable_runs": PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS,
        "observed_recent_window": recent_window,
        "observed_consecutive_passes": consecutive_passes,
        "history_stability_complete": _provider_readiness_history_is_stable_enough(
            history_summary,
        ),
        "required_live_fault_cases": required_live_fault_cases,
        "live_fault_covered_cases": live_fault_covered_cases,
        "live_fault_missing_cases": live_fault_missing_cases,
        "live_fault_coverage_complete": live_fault_coverage_complete,
    }


def _provider_readiness_recent_window(history_summary: dict[str, Any]) -> int:
    """Return observed recent-window count from provider history."""
    recent_window = _int_payload_value(history_summary, "recent_window")
    if recent_window == 0:
        recent_window = _int_payload_value(history_summary, "total_runs")
    return recent_window


def _provider_readiness_consecutive_passes(history_summary: dict[str, Any]) -> int:
    """Return observed consecutive-pass count from provider history."""
    consecutive_passes = _int_payload_value(history_summary, "consecutive_passes")
    if consecutive_passes == 0:
        consecutive_passes = _int_payload_value(history_summary, "passed_runs")
    return consecutive_passes


def _provider_readiness_missing_requirements(
    blockers: list[str],
    requirements: dict[str, Any],
) -> list[str]:
    """Return stable missing requirement ids for readiness automation."""
    missing: list[str] = []
    if "provider_e2e_failed" in blockers:
        missing.append("provider_e2e")
    if "provider_reliability_incomplete" in blockers:
        missing.append("provider_reliability")
    if "provider_history_latest_failed" in blockers:
        missing.append("latest_provider_e2e_pass")
    if requirements.get("history_stability_complete") is not True:
        missing.append("stable_history_runs")
    if requirements.get("live_fault_coverage_complete") is not True:
        missing.append("live_fault_case_coverage")
    return missing


def _provider_readiness_status(
    blockers: list[str],
    warnings: list[str],
) -> tuple[str, str]:
    """Return readiness status and recommendation."""
    if blockers:
        return "blocked", "provider_e2e_required"
    if (
        "live_fault_probe_evidence_missing" in warnings
        or "live_fault_probe_coverage_incomplete" in warnings
    ):
        return "needs_live_fault_evidence", "limited_autonomous_until_live_faults"
    if warnings:
        return "warming_up", "limited_autonomous_until_evidence_stable"
    return "full_autonomous_candidate", "api_runtime_full_autonomous_candidate"


def _provider_readiness_recommendation_reasons(
    status: str,
    blockers: list[str],
    warnings: list[str],
) -> list[str]:
    """Return stable, UI-facing reason ids behind the readiness recommendation."""
    if status == "full_autonomous_candidate":
        return ["full_autonomy_candidate"]

    reasons: list[str] = []
    for signal in [*blockers, *warnings]:
        reason = PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL.get(
            signal
        )
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _provider_readiness_next_actions(
    blockers: list[str],
    warnings: list[str],
) -> list[str]:
    """Return ordered next actions for readiness blockers and warnings."""
    action_by_reason = {
        "provider_e2e_failed": "rerun_provider_e2e",
        "provider_reliability_incomplete": "inspect_uncovered_cases",
        "provider_history_latest_failed": "rerun_provider_e2e",
        "provider_history_unknown": "collect_provider_history_runs",
        "live_fault_probe_evidence_missing": "enable_live_fault_probes",
        "live_fault_probe_coverage_incomplete": "enable_live_fault_probes",
        "provider_history_insufficient_runs": "collect_provider_history_runs",
        "provider_history_warming_up": "collect_provider_history_runs",
        "provider_history_flaky": "stabilize_provider_history",
        "provider_history_recovering": "collect_provider_history_runs",
        "provider_history_degraded": "stabilize_provider_history",
    }
    actions: list[str] = []
    for reason in [*blockers, *warnings]:
        action = action_by_reason.get(reason)
        if action and action not in actions:
            actions.append(action)
    return actions


def _with_provider_run_history(
    project_dir: Path,
    result: ProviderSmokeResult,
) -> ProviderSmokeResult:
    """Persist provider e2e history and attach a compact diagnostics summary."""
    history_path = _provider_smoke_history_path(project_dir)
    try:
        runs, repaired = _load_provider_smoke_history(history_path)
        record = _provider_smoke_history_record(result)
        payload = _provider_smoke_history_payload([*runs, record])
        history_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = history_path.with_name(f"{history_path.name}.tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(history_path)
        provider_stats = payload["providers"].get(result.provider, {})
        history_summary = {
            "status": "recorded_after_repair" if repaired else "recorded",
            "provider": result.provider,
            "runtime_mode": result.runtime_mode,
            "total_runs": provider_stats.get("total_runs", 0),
            "passed_runs": provider_stats.get("passed_runs", 0),
            "failed_runs": provider_stats.get("failed_runs", 0),
            "last_status": provider_stats.get("last_status", "unknown"),
            "last_reliability_status": provider_stats.get("last_reliability_status"),
            "last_provider_e2e_status": provider_stats.get("last_provider_e2e_status"),
            "e2e_case_count": provider_stats.get("e2e_case_count", 0),
            "e2e_passed_case_count": provider_stats.get("e2e_passed_case_count", 0),
            "e2e_failed_case_count": provider_stats.get("e2e_failed_case_count", 0),
            "reliability_observed_case_count": provider_stats.get(
                "reliability_observed_case_count",
                0,
            ),
            "reliability_passed_case_count": provider_stats.get(
                "reliability_passed_case_count",
                0,
            ),
            "reliability_required_case_count": provider_stats.get(
                "reliability_required_case_count",
                0,
            ),
            "last_live_fault_probe_status": provider_stats.get(
                "last_live_fault_probe_status"
            ),
            "live_fault_probe_enabled_runs": provider_stats.get(
                "live_fault_probe_enabled_runs",
                0,
            ),
            "live_fault_probe_passed_runs": provider_stats.get(
                "live_fault_probe_passed_runs",
                0,
            ),
            "live_fault_probe_covered_cases": provider_stats.get(
                "live_fault_probe_covered_cases",
                [],
            ),
            "trend": provider_stats.get("trend"),
            "trend_reason": provider_stats.get("trend_reason"),
            "recent_window": provider_stats.get("recent_window"),
            "recent_passed_runs": provider_stats.get("recent_passed_runs"),
            "recent_failed_runs": provider_stats.get("recent_failed_runs"),
            "consecutive_passes": provider_stats.get("consecutive_passes"),
            "consecutive_failures": provider_stats.get("consecutive_failures"),
            "pass_rate_percent": provider_stats.get("pass_rate_percent"),
            "recent_pass_rate_percent": provider_stats.get("recent_pass_rate_percent"),
            "e2e_case_pass_rate_percent": provider_stats.get(
                "e2e_case_pass_rate_percent"
            ),
            "reliability_case_pass_rate_percent": provider_stats.get(
                "reliability_case_pass_rate_percent"
            ),
            "observed_live_fault_case_count": provider_stats.get(
                "observed_live_fault_case_count",
            ),
            "required_live_fault_case_count": provider_stats.get(
                "required_live_fault_case_count",
            ),
            "live_fault_probe_case_coverage_percent": provider_stats.get(
                "live_fault_probe_case_coverage_percent",
            ),
            "quality_trend": provider_stats.get("quality_trend"),
            "quality_delta_percent": provider_stats.get("quality_delta_percent"),
            "stability_trend": provider_stats.get("stability_trend"),
            "stability_delta_percent": provider_stats.get("stability_delta_percent"),
            "safety_trend": provider_stats.get("safety_trend"),
            "safety_delta_percent": provider_stats.get("safety_delta_percent"),
            "cost_trend": provider_stats.get("cost_trend"),
            "cost_delta_usd": provider_stats.get("cost_delta_usd"),
            "cost_delta_formatted": provider_stats.get("cost_delta_formatted"),
            "recent_runs": provider_stats.get("recent_runs", []),
            "path": PROVIDER_SMOKE_HISTORY_RELATIVE_PATH.as_posix(),
        }
        for cost_key in (
            "cost_status",
            "cost_observed_run_count",
            "cost_total_input_tokens",
            "cost_total_output_tokens",
            "cost_total_usd",
            "cost_total_formatted",
            "cost_last_status",
            "cost_last_source",
            "cost_last_input_tokens",
            "cost_last_output_tokens",
            "cost_last_usd",
            "cost_last_formatted",
            "cost_last_pricing_model",
            "cost_last_pricing_provider",
            "cost_pricing_model",
            "cost_pricing_provider",
        ):
            if cost_key in provider_stats:
                history_summary[cost_key] = provider_stats[cost_key]
    except Exception as e:
        logger.debug("Provider smoke history persistence failed", exc_info=True)
        live_fault_probes = result.runtime_diagnostics.get(
            "provider_e2e_live_fault_probes"
        )
        live_fault_probes = (
            live_fault_probes if isinstance(live_fault_probes, dict) else {}
        )
        live_fault_probe_status = live_fault_probes.get("status")
        history_summary = {
            "status": "record_failed",
            "provider": result.provider,
            "runtime_mode": result.runtime_mode,
            "reason": str(e),
            "last_live_fault_probe_status": live_fault_probe_status
            if isinstance(live_fault_probe_status, str) and live_fault_probe_status
            else None,
            "live_fault_probe_covered_cases": _string_list_payload(
                live_fault_probes.get("covered_cases")
            ),
            "path": PROVIDER_SMOKE_HISTORY_RELATIVE_PATH.as_posix(),
        }
    return replace(
        result,
        runtime_diagnostics={
            **result.runtime_diagnostics,
            "provider_run_history": history_summary,
            "provider_autonomous_readiness": _provider_autonomous_readiness_diagnostics(
                result,
                history_summary,
            ),
        },
    )


def _response_excerpt(response_text: str, max_chars: int = 500) -> str:
    response = " ".join(response_text.split())
    if len(response) <= max_chars:
        return response
    return response[:max_chars].rstrip() + "..."


def _generic_edit_execution_diagnostics(artifact_dir: Path) -> dict[str, Any] | None:
    """Return the generic_edit execution summary created by the smoke run."""
    result_path = artifact_dir / "generic_edit_result.json"
    if not result_path.exists():
        return None

    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "status": "artifact_unreadable",
            "error": str(e),
        }

    normalized_tool_counts = _number_record_payload(payload.get("tool_counts"))
    failed_tools = _number_record_payload(payload.get("failed_tools"))
    native_tool_fallbacks = _native_tool_fallbacks_payload(
        payload.get("native_tool_fallbacks")
    )
    diagnostics = {
        "status": str(payload.get("status") or "unknown"),
        "stop_reason": str(payload.get("stop_reason") or "unknown"),
        "loop": str(payload.get("loop") or "unknown"),
        "action_count": _int_payload_value(payload, "action_count"),
        "failed_action_count": _int_payload_value(payload, "failed_action_count"),
        "native_tool_fallback_count": _int_payload_value(
            payload,
            "native_tool_fallback_count",
        ),
        "native_tool_fallbacks": native_tool_fallbacks,
        "tool_counts": normalized_tool_counts,
    }
    if failed_tools:
        diagnostics["failed_tools"] = failed_tools
    resume_policy = _resume_policy_payload(payload.get("resume_policy"))
    if resume_policy is not None:
        diagnostics["resume_policy"] = resume_policy
    artifact_manifest = _generic_edit_artifact_manifest_payload(artifact_dir)
    mutation_snapshots = _generic_edit_mutation_snapshots_payload(artifact_dir)
    diagnostics["transaction_batch_contract"] = (
        _generic_edit_transaction_batch_contract(
            payload,
            artifact_manifest=artifact_manifest,
            mutation_snapshots=mutation_snapshots,
        )
    )
    diagnostics["tool_loop_contract"] = _generic_edit_tool_loop_contract(
        payload=payload,
        native_tool_fallbacks=native_tool_fallbacks,
        resume_policy=resume_policy,
    )
    return diagnostics


def _generic_edit_artifact_manifest_payload(
    artifact_dir: Path,
) -> dict[str, Any] | None:
    """Return the adjacent generic_edit artifact manifest when it is readable."""
    manifest_path = artifact_dir / "generic_edit_artifact_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _generic_edit_mutation_snapshots_payload(
    artifact_dir: Path,
) -> list[dict[str, Any]]:
    """Return compact mutation snapshot entries when the artifact is readable."""
    snapshot_path = artifact_dir / "generic_edit_mutation_snapshots.json"
    if not snapshot_path.exists():
        return []
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, list):
        return []
    return [snapshot for snapshot in snapshots if isinstance(snapshot, dict)]


def _generic_edit_tool_loop_contract(
    *,
    payload: dict[str, Any],
    native_tool_fallbacks: list[dict[str, Any]],
    resume_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact provider contract summary for UI/CLI diagnostics."""
    status = str(payload.get("status") or "unknown")
    stop_reason = str(payload.get("stop_reason") or "unknown")
    loop = str(payload.get("loop") or "unknown")
    action_count = _int_payload_value(payload, "action_count")
    failed_action_count = _int_payload_value(payload, "failed_action_count")
    fallback_count = _int_payload_value(payload, "native_tool_fallback_count")
    failed_tools = _number_record_payload(payload.get("failed_tools"))

    first_fallback = native_tool_fallbacks[0] if native_tool_fallbacks else {}
    fallback_reason = first_fallback.get("reason")
    fallback_target = first_fallback.get("to_loop") or "json_actions"
    blocking_reason = next(iter(failed_tools), stop_reason) if failed_tools else None

    contract: dict[str, Any] = {
        "status": _generic_edit_contract_status(
            status=status,
            stop_reason=stop_reason,
            failed_action_count=failed_action_count,
            resume_policy=resume_policy,
            failed_tools=failed_tools,
        ),
        "tool_call_support": _generic_edit_tool_call_support(
            loop=loop,
            fallback_count=fallback_count,
        ),
        "tool_result_support": _generic_edit_tool_result_support(
            action_count=action_count,
            failed_action_count=failed_action_count,
            resume_policy=resume_policy,
        ),
        "fallback": fallback_target if fallback_count > 0 else "none",
        "recovery_status": _generic_edit_recovery_status(
            failed_action_count=failed_action_count,
            resume_policy=resume_policy,
        ),
    }
    if fallback_reason:
        contract["fallback_reason"] = fallback_reason
    if contract["status"] in {"blocked", "needs_recovery", "unsupported_tools"}:
        contract["blocking_reason"] = blocking_reason or stop_reason
    return contract


def _generic_edit_contract_status(
    *,
    status: str,
    stop_reason: str,
    failed_action_count: int,
    resume_policy: dict[str, Any] | None,
    failed_tools: dict[str, int],
) -> str:
    if failed_tools:
        return "unsupported_tools"
    if resume_policy and resume_policy.get("status") == "requires_resolution":
        return "needs_recovery"
    if status == "complete" and stop_reason == "finish" and failed_action_count == 0:
        return "passed"
    if status == "complete":
        return "recovered" if failed_action_count else "passed"
    if status == "error":
        return "blocked"
    return "incomplete"


def _generic_edit_tool_call_support(*, loop: str, fallback_count: int) -> str:
    if loop == "native_tool_calls" and fallback_count == 0:
        return "native"
    if fallback_count > 0:
        return "json_fallback"
    if loop == "json_actions":
        return "json_actions"
    return "unknown"


def _generic_edit_tool_result_support(
    *,
    action_count: int,
    failed_action_count: int,
    resume_policy: dict[str, Any] | None,
) -> str:
    if action_count <= 0:
        return "not_observed"
    if failed_action_count <= 0:
        return "normalized"
    if resume_policy and resume_policy.get("status") == "requires_resolution":
        return "partial_failure"
    return "failed"


def _generic_edit_recovery_status(
    *,
    failed_action_count: int,
    resume_policy: dict[str, Any] | None,
) -> str:
    if resume_policy and resume_policy.get("status") == "requires_resolution":
        return "requires_resolution"
    if failed_action_count > 0:
        return "unresolved"
    return "not_required"


def _generic_edit_transaction_batch_contract(
    payload: dict[str, Any],
    *,
    artifact_manifest: dict[str, Any] | None = None,
    mutation_snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return safe batch-boundary diagnostics for provider smoke results."""
    stop_reason = str(payload.get("stop_reason") or "unknown")
    transaction_batch_count = _int_payload_value(payload, "transaction_batch_count")
    transaction_batches = payload.get("transaction_batches")
    if isinstance(transaction_batches, list):
        transaction_batch_count = max(
            transaction_batch_count,
            len([batch for batch in transaction_batches if isinstance(batch, dict)]),
        )

    open_batches = _string_list_payload(payload.get("open_transaction_batch_ids"))
    boundary_error_count = 0
    boundary_error_reasons: list[str] = []
    boundary_required_action_kinds: list[str] = []
    boundary_resolution_strategies: list[str] = []
    boundary_preferred_strategy: str | None = None
    staged_workspace_guard_statuses: list[str] = []
    staged_drift_paths: list[str] = []
    batch_lifecycle_actions: list[str] = []
    batch_lifecycle_statuses: list[str] = []
    committed_mutation_snapshot_ids: list[str] = []
    commit_operation_ids: list[str] = []
    staged_isolation_statuses: list[str] = []
    staged_workspace_restore_statuses: list[str] = []
    staged_baseline_paths: list[str] = []
    if isinstance(transaction_batches, list):
        for batch in transaction_batches:
            if not isinstance(batch, dict):
                continue
            actions, statuses = _generic_edit_batch_lifecycle_values(batch)
            batch_lifecycle_actions.extend(actions)
            batch_lifecycle_statuses.extend(statuses)
            commit_operation_ids.extend(
                _string_list_payload(batch.get("commit_operation_ids"))
            )
            batch_error_reasons = _string_list_payload(
                batch.get("boundary_error_reasons")
            )
            batch_error_count = batch.get("boundary_error_count")
            if isinstance(batch_error_count, int) and not isinstance(
                batch_error_count, bool
            ):
                boundary_error_count += batch_error_count
            boundary_errors = batch.get("boundary_errors")
            if isinstance(boundary_errors, list):
                batch_error_reasons.extend(
                    str(error.get("reason"))
                    for error in boundary_errors
                    if isinstance(error, dict)
                    and isinstance(error.get("reason"), str)
                    and error.get("reason")
                )
                for error in boundary_errors:
                    if not isinstance(error, dict):
                        continue
                    boundary_preferred_strategy = (
                        boundary_preferred_strategy
                        or _string_payload_value(error.get("preferred_strategy"))
                    )
                    boundary_required_action_kinds.extend(
                        _string_list_payload(error.get("required_next_action_kinds"))
                    )
                    boundary_resolution_strategies.extend(
                        _string_list_payload(error.get("resolution_strategies"))
                    )
            if not (
                isinstance(batch_error_count, int)
                and not isinstance(batch_error_count, bool)
            ):
                boundary_error_count += len(batch_error_reasons)
            boundary_error_reasons.extend(batch_error_reasons)

    for event in _generic_edit_batch_boundary_manifest_events(artifact_manifest):
        reason = _string_payload_value(event.get("batch_boundary_error_reason"))
        if reason:
            boundary_error_reasons.append(reason)
        staged_guard_status = _string_payload_value(
            event.get("staged_workspace_guard_status")
        )
        if staged_guard_status:
            staged_workspace_guard_statuses.append(staged_guard_status)
        staged_drift_paths.extend(_string_list_payload(event.get("drift_paths")))
        boundary_preferred_strategy = (
            boundary_preferred_strategy
            or _string_payload_value(event.get("preferred_strategy"))
        )
        boundary_required_action_kinds.extend(
            _string_list_payload(event.get("required_next_action_kinds"))
        )
        boundary_resolution_strategies.extend(
            _string_list_payload(event.get("resolution_strategies"))
        )
    for batch in _generic_edit_manifest_transaction_batches(artifact_manifest):
        actions, statuses = _generic_edit_batch_lifecycle_values(batch)
        batch_lifecycle_actions.extend(actions)
        batch_lifecycle_statuses.extend(statuses)
        commit_operation_ids.extend(
            _string_list_payload(batch.get("commit_operation_ids"))
        )
    for event in _generic_edit_manifest_committed_batch_events(artifact_manifest):
        committed_mutation_snapshot_ids.extend(
            _string_list_payload(event.get("committed_mutation_snapshot_ids"))
        )
        commit_operation_id = _string_payload_value(event.get("commit_operation_id"))
        if commit_operation_id:
            commit_operation_ids.append(commit_operation_id)
        commit_operation_ids.extend(
            _string_list_payload(event.get("commit_operation_ids"))
        )
    for snapshot in mutation_snapshots or []:
        isolation = snapshot.get("staged_isolation")
        if not isinstance(isolation, dict):
            continue
        isolation_status = _string_payload_value(isolation.get("status"))
        if isolation_status:
            staged_isolation_statuses.append(isolation_status)
        if isolation.get("workspace_restored") is True:
            staged_workspace_restore_statuses.append("restored")
        elif isolation.get("workspace_restored") is False:
            staged_workspace_restore_statuses.append("not_restored")
        staged_baseline_paths.extend(
            _string_list_payload(isolation.get("baseline_paths"))
        )
    if boundary_error_reasons:
        boundary_error_count = max(
            boundary_error_count,
            len(set(boundary_error_reasons)),
        )

    if stop_reason == "batch_boundary_violation":
        boundary_error_count = max(boundary_error_count, 1)
        boundary_error_reasons.append("batch_boundary_violation")
        status = "boundary_guarded"
        boundary_guard = "pre_execution_blocked"
    elif boundary_error_count > 0:
        status = "boundary_guarded"
        boundary_guard = "runtime_blocked"
    elif open_batches:
        status = "requires_resolution"
        boundary_guard = "open_batch"
    elif transaction_batch_count > 0:
        status = "observed"
        boundary_guard = "observed"
    else:
        status = "not_observed"
        boundary_guard = "not_observed"

    contract: dict[str, Any] = {
        "status": status,
        "batch_boundary_guard": boundary_guard,
        "transaction_batch_count": transaction_batch_count,
        "open_transaction_batch_ids": open_batches,
    }
    if boundary_error_count > 0:
        contract["boundary_error_count"] = boundary_error_count
        contract["boundary_error_reasons"] = sorted(
            dict.fromkeys(boundary_error_reasons)
        )
    if boundary_preferred_strategy:
        contract["boundary_preferred_strategy"] = boundary_preferred_strategy
    if boundary_required_action_kinds:
        contract["boundary_required_action_kinds"] = list(
            dict.fromkeys(boundary_required_action_kinds)
        )
    if boundary_resolution_strategies:
        contract["boundary_resolution_strategies"] = list(
            dict.fromkeys(boundary_resolution_strategies)
        )
    if staged_workspace_guard_statuses:
        contract["staged_workspace_guard_statuses"] = list(
            dict.fromkeys(staged_workspace_guard_statuses)
        )
    if staged_drift_paths:
        contract["staged_drift_paths"] = list(dict.fromkeys(staged_drift_paths))
    if batch_lifecycle_actions:
        contract["batch_lifecycle_actions"] = list(
            dict.fromkeys(batch_lifecycle_actions)
        )
    if batch_lifecycle_statuses:
        contract["batch_lifecycle_statuses"] = list(
            dict.fromkeys(batch_lifecycle_statuses)
        )
    if committed_mutation_snapshot_ids:
        contract["committed_mutation_snapshot_ids"] = list(
            dict.fromkeys(committed_mutation_snapshot_ids)
        )
    if commit_operation_ids:
        contract["commit_operation_ids"] = list(dict.fromkeys(commit_operation_ids))
    if staged_isolation_statuses:
        contract["staged_isolation_statuses"] = list(
            dict.fromkeys(staged_isolation_statuses)
        )
    if staged_workspace_restore_statuses:
        contract["staged_workspace_restore_statuses"] = list(
            dict.fromkeys(staged_workspace_restore_statuses)
        )
    if staged_baseline_paths:
        contract["staged_baseline_paths"] = list(dict.fromkeys(staged_baseline_paths))
    return contract


def _generic_edit_batch_lifecycle_values(
    batch: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return safe lifecycle action/status lists from a batch summary."""
    events = batch.get("lifecycle_events")
    if not isinstance(events, list):
        return [], []
    actions: list[str] = []
    statuses: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        action = _string_payload_value(event.get("action"))
        status = _string_payload_value(event.get("status"))
        if action:
            actions.append(action)
        if status:
            statuses.append(status)
    return actions, statuses


def _generic_edit_manifest_transaction_batches(
    artifact_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return manifest transaction batch summaries when available."""
    if not isinstance(artifact_manifest, dict):
        return []
    transaction_batches = artifact_manifest.get("transaction_batches")
    if not isinstance(transaction_batches, list):
        return []
    return [batch for batch in transaction_batches if isinstance(batch, dict)]


def _generic_edit_manifest_committed_batch_events(
    artifact_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return manifest timeline events that describe committed batches."""
    if not isinstance(artifact_manifest, dict):
        return []
    recovery_timeline = artifact_manifest.get("recovery_timeline")
    if not isinstance(recovery_timeline, list):
        return []
    events: list[dict[str, Any]] = []
    for event in recovery_timeline:
        if not isinstance(event, dict):
            continue
        if event.get("timeline_stage") == "batch_committed":
            events.append(event)
    return events


def _generic_edit_batch_boundary_manifest_events(
    artifact_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return manifest timeline events that describe batch-boundary recovery."""
    if not isinstance(artifact_manifest, dict):
        return []
    recovery_timeline = artifact_manifest.get("recovery_timeline")
    if not isinstance(recovery_timeline, list):
        return []
    events: list[dict[str, Any]] = []
    for event in recovery_timeline:
        if not isinstance(event, dict):
            continue
        has_boundary_reason = bool(
            _string_payload_value(event.get("batch_boundary_error_reason"))
        )
        has_boundary_stage = event.get("timeline_stage") == "batch_boundary_blocked"
        if has_boundary_reason or has_boundary_stage:
            events.append(event)
    return events


def _string_payload_value(value: Any) -> str | None:
    """Return a non-empty string payload value."""
    return value if isinstance(value, str) and value else None


def _native_tool_fallbacks_payload(value: Any) -> list[dict[str, Any]]:
    """Return safe native tool fallback records for provider smoke diagnostics."""
    if not isinstance(value, list):
        return []

    fallbacks: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        fallback = {
            key: str(item[key])
            for key in ("provider", "from_loop", "to_loop", "reason", "message")
            if isinstance(item.get(key), str)
        }
        tool_schema_count = item.get("tool_schema_count")
        if isinstance(tool_schema_count, int) and not isinstance(
            tool_schema_count, bool
        ):
            fallback["tool_schema_count"] = tool_schema_count
        if fallback:
            fallbacks.append(fallback)
    return fallbacks


def _resume_policy_payload(value: Any) -> dict[str, Any] | None:
    """Return safe generic_edit resume policy fields for smoke diagnostics."""
    if not isinstance(value, dict):
        return None
    policy: dict[str, Any] = {}
    for key in ("status", "strategy"):
        field_value = value.get(key)
        if isinstance(field_value, str) and field_value:
            policy[key] = field_value
    for key in ("can_resume", "finish_blocked"):
        field_value = value.get(key)
        if isinstance(field_value, bool):
            policy[key] = field_value
    next_iteration = value.get("next_iteration")
    if isinstance(next_iteration, int) and not isinstance(next_iteration, bool):
        policy["next_iteration"] = next_iteration
    action_kinds = _string_list_payload(value.get("required_resolution_action_kinds"))
    if action_kinds:
        policy["required_resolution_action_kinds"] = action_kinds
    required_artifacts = _string_list_payload(value.get("required_artifacts"))
    if required_artifacts:
        policy["required_artifacts"] = required_artifacts
    unresolved_groups = _string_list_payload(
        value.get("unresolved_transaction_group_ids")
    )
    if unresolved_groups:
        policy["unresolved_transaction_group_ids"] = unresolved_groups
    unresolved_failures = _string_list_payload(
        value.get("unresolved_partial_failure_ids")
    )
    if unresolved_failures:
        policy["unresolved_partial_failure_ids"] = unresolved_failures
    open_batches = _string_list_payload(value.get("open_transaction_batch_ids"))
    if open_batches:
        policy["open_transaction_batch_ids"] = open_batches
    return policy or None


def _string_list_payload(value: Any) -> list[str]:
    """Return a safe bounded string list for smoke diagnostics."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:20] if isinstance(item, str) and item]


def _int_payload_value(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _float_payload_value(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _number_record_payload(value: Any) -> dict[str, int]:
    """Return a safe string->int record for smoke diagnostics."""
    if not isinstance(value, dict):
        return {}
    return {
        str(key): count
        for key, count in value.items()
        if isinstance(count, int) and not isinstance(count, bool)
    }


def _provider_contract_health(
    runtime_diagnostics: dict[str, Any],
    *,
    success: bool | None = None,
    error_details: str | None = None,
) -> dict[str, Any]:
    """Return a compact provider health classification for UI/automation."""
    smoke_scope = str(runtime_diagnostics.get("smoke_scope") or "unknown")
    mini_pipeline = runtime_diagnostics.get("mini_pipeline")
    if isinstance(mini_pipeline, dict):
        health = _provider_health_from_mini_pipeline(
            mini_pipeline,
            runtime_diagnostics=runtime_diagnostics,
            smoke_scope=smoke_scope,
        )
        if health:
            return health

    provider_e2e_suite = runtime_diagnostics.get("provider_e2e_suite")
    if isinstance(provider_e2e_suite, dict):
        health = _provider_health_from_e2e_suite(
            provider_e2e_suite,
            smoke_scope=smoke_scope,
        )
        if health:
            return health

    if error_details:
        issue = _provider_issue_from_error(error_details)
        return {
            "status": issue["status"],
            "smoke_scope": smoke_scope,
            "reason": issue["reason"],
            "message": _response_excerpt(error_details, max_chars=240),
        }

    execution = runtime_diagnostics.get("validated_runtime_execution")
    if isinstance(execution, dict):
        contract = execution.get("tool_loop_contract")
        if isinstance(contract, dict):
            health = _provider_health_from_tool_loop_contract(
                contract,
                smoke_scope=smoke_scope,
            )
            if health:
                return health

    if success is True and smoke_scope == "text_completion_only":
        return {
            "status": "text_completion_ready",
            "smoke_scope": smoke_scope,
        }
    if success is True:
        return {
            "status": "provider_smoke_ready",
            "smoke_scope": smoke_scope,
        }
    return {
        "status": "not_observed",
        "smoke_scope": smoke_scope,
        "reason": "smoke_not_completed",
    }


def _with_provider_contract_health(
    runtime_diagnostics: dict[str, Any],
    *,
    success: bool | None = None,
    error_details: str | None = None,
) -> dict[str, Any]:
    """Attach provider health classification without mutating caller payloads."""
    provider_contract_health = _provider_contract_health(
        runtime_diagnostics,
        success=success,
        error_details=error_details,
    )
    diagnostics = {
        **runtime_diagnostics,
        "provider_contract_health": provider_contract_health,
    }
    existing_reliability = runtime_diagnostics.get("provider_reliability")
    provider_reliability = (
        existing_reliability
        if isinstance(existing_reliability, dict)
        else _provider_reliability_diagnostics(
            diagnostics,
            provider_contract_health=provider_contract_health,
            success=success,
        )
    )
    if provider_reliability is not None:
        diagnostics["provider_reliability"] = provider_reliability
    return diagnostics


def _provider_reliability_diagnostics(
    runtime_diagnostics: dict[str, Any],
    *,
    provider_contract_health: dict[str, Any],
    success: bool | None,
) -> dict[str, Any] | None:
    """Return direct-provider e2e coverage status from one smoke run."""
    provider = str(runtime_diagnostics.get("provider") or "").lower()
    if provider not in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        return None

    cases = [
        _provider_text_completion_case(runtime_diagnostics, success=success),
        _provider_generic_edit_case(runtime_diagnostics),
        _provider_native_tool_case(runtime_diagnostics),
        _provider_tool_result_case(runtime_diagnostics),
        _provider_recovery_loop_case(runtime_diagnostics),
        _provider_transaction_batch_case(runtime_diagnostics),
        _provider_unsupported_tools_case(
            runtime_diagnostics,
            provider_contract_health=provider_contract_health,
        ),
        _provider_gateway_model_case(
            runtime_diagnostics,
            provider_contract_health=provider_contract_health,
        ),
    ]
    return _provider_reliability_payload(provider, cases)


def _provider_reliability_payload(
    provider: str,
    cases: list[dict[str, str]],
) -> dict[str, Any]:
    """Return direct-provider reliability counters for ordered case results."""
    observed_cases = [case for case in cases if case.get("status") != "not_covered"]
    passed_cases = [case for case in cases if case.get("status") == "passed"]
    uncovered_cases = [
        str(case["case"]) for case in cases if case.get("status") == "not_covered"
    ]
    return {
        "provider": provider,
        "suite": "direct_api_full_autonomy",
        "status": "complete" if len(passed_cases) == len(cases) else "partial_coverage",
        "observed_case_count": len(observed_cases),
        "passed_case_count": len(passed_cases),
        "required_case_count": len(cases),
        "uncovered_cases": uncovered_cases,
        "cases": cases,
    }


def _merge_provider_reliability_diagnostics(
    provider: str,
    reliabilities: list[Any],
) -> dict[str, Any] | None:
    """Merge per-smoke reliability payloads into one provider e2e suite view."""
    normalized_provider = provider.lower()
    if normalized_provider not in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        return None

    cases_by_name: dict[str, dict[str, str]] = {
        case_name: {
            "case": case_name,
            "status": "not_covered",
            "source": "provider_e2e_required",
        }
        for case_name in PROVIDER_RELIABILITY_CASE_ORDER
    }
    observed = False
    for reliability in reliabilities:
        if not isinstance(reliability, dict):
            continue
        cases = reliability.get("cases")
        if not isinstance(cases, list):
            continue
        for candidate in cases:
            if not isinstance(candidate, dict):
                continue
            case_name = str(candidate.get("case") or "")
            if case_name not in cases_by_name:
                continue
            status = str(candidate.get("status") or "not_covered")
            current_status = cases_by_name[case_name]["status"]
            if PROVIDER_RELIABILITY_STATUS_RANK.get(
                status,
                0,
            ) > PROVIDER_RELIABILITY_STATUS_RANK.get(current_status, 0):
                source = str(candidate.get("source") or "provider_e2e_suite")
                cases_by_name[case_name] = {
                    "case": case_name,
                    "status": status,
                    "source": source,
                }
                observed = True

    if not observed:
        return None
    return _provider_reliability_payload(
        normalized_provider,
        [cases_by_name[case_name] for case_name in PROVIDER_RELIABILITY_CASE_ORDER],
    )


def _provider_text_completion_case(
    runtime_diagnostics: dict[str, Any],
    *,
    success: bool | None,
) -> dict[str, str]:
    smoke_scope = str(runtime_diagnostics.get("smoke_scope") or "unknown")
    if success is True:
        return {
            "case": "text_completion",
            "status": "passed",
            "source": "mini_pipeline"
            if smoke_scope == "mini_task_pipeline"
            else smoke_scope,
        }
    if smoke_scope != "unknown":
        return {
            "case": "text_completion",
            "status": "blocked",
            "source": smoke_scope,
        }
    return {
        "case": "text_completion",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_generic_edit_case(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, str]:
    contract = _provider_tool_loop_contract(runtime_diagnostics)
    status = str(contract.get("status") or "") if isinstance(contract, dict) else ""
    if status in {"passed", "recovered"}:
        return {
            "case": "generic_edit_tool_loop",
            "status": "passed",
            "source": "tool_loop_contract",
        }
    if status in {"needs_recovery", "unsupported_tools", "blocked"}:
        return {
            "case": "generic_edit_tool_loop",
            "status": "blocked",
            "source": "tool_loop_contract",
        }
    return {
        "case": "generic_edit_tool_loop",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_native_tool_case(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, str]:
    contract = _provider_tool_loop_contract(runtime_diagnostics)
    support = (
        str(contract.get("tool_call_support") or "")
        if isinstance(contract, dict)
        else ""
    )
    if support == "native":
        return {
            "case": "native_tool_calls",
            "status": "passed",
            "source": "tool_loop_contract",
        }
    if support in {"json_fallback", "json_actions"}:
        return {
            "case": "native_tool_calls",
            "status": "limited",
            "source": "tool_loop_contract",
        }
    return {
        "case": "native_tool_calls",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_tool_result_case(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, str]:
    contract = _provider_tool_loop_contract(runtime_diagnostics)
    support = (
        str(contract.get("tool_result_support") or "")
        if isinstance(contract, dict)
        else ""
    )
    if support == "normalized":
        return {
            "case": "tool_results",
            "status": "passed",
            "source": "tool_loop_contract",
        }
    if support == "partial_failure":
        return {
            "case": "tool_results",
            "status": "limited",
            "source": "tool_loop_contract",
        }
    if support == "failed":
        return {
            "case": "tool_results",
            "status": "blocked",
            "source": "tool_loop_contract",
        }
    return {
        "case": "tool_results",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_recovery_loop_case(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, str]:
    mini_pipeline = runtime_diagnostics.get("mini_pipeline")
    recovery_loop = (
        mini_pipeline.get("recovery_loop") if isinstance(mini_pipeline, dict) else None
    )
    if isinstance(recovery_loop, dict):
        status = str(recovery_loop.get("status") or "")
        if status == "passed":
            return {
                "case": "recovery_loop",
                "status": "passed",
                "source": "mini_pipeline",
            }
        if status:
            return {
                "case": "recovery_loop",
                "status": "blocked",
                "source": "mini_pipeline",
            }
    return {
        "case": "recovery_loop",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_transaction_batch_case(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, str]:
    execution = runtime_diagnostics.get("validated_runtime_execution")
    contract = (
        execution.get("transaction_batch_contract")
        if isinstance(execution, dict)
        else None
    )
    if not isinstance(contract, dict):
        return {
            "case": "transaction_batches",
            "status": "not_covered",
            "source": "provider_e2e_required",
        }

    status = str(contract.get("status") or "")
    lifecycle_actions = set(
        _string_list_payload(contract.get("batch_lifecycle_actions"))
    )
    lifecycle_statuses = set(
        _string_list_payload(contract.get("batch_lifecycle_statuses"))
    )
    transaction_batch_count = _int_payload_value(contract, "transaction_batch_count")
    if (
        status == "observed"
        and transaction_batch_count > 0
        and {"begin_batch", "commit_batch"}.issubset(lifecycle_actions)
        and "committed" in lifecycle_statuses
    ):
        return {
            "case": "transaction_batches",
            "status": "passed",
            "source": "transaction_batch_contract",
        }
    if status in {"boundary_guarded", "requires_resolution"}:
        return {
            "case": "transaction_batches",
            "status": "blocked",
            "source": "transaction_batch_contract",
        }
    if status and status != "not_observed":
        return {
            "case": "transaction_batches",
            "status": "limited",
            "source": "transaction_batch_contract",
        }
    return {
        "case": "transaction_batches",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_unsupported_tools_case(
    runtime_diagnostics: dict[str, Any],
    *,
    provider_contract_health: dict[str, Any],
) -> dict[str, str]:
    negative_probe_case = _provider_negative_probe_case(
        runtime_diagnostics,
        "unsupported_tools",
    )
    if negative_probe_case is not None:
        return negative_probe_case

    contract = _provider_tool_loop_contract(runtime_diagnostics)
    contract_status = (
        str(contract.get("status") or "") if isinstance(contract, dict) else ""
    )
    health_status = str(provider_contract_health.get("status") or "")
    if contract_status == "unsupported_tools" or health_status == "unsupported_tools":
        return {
            "case": "unsupported_tools",
            "status": "blocked",
            "source": "tool_loop_contract",
        }
    return {
        "case": "unsupported_tools",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_gateway_model_case(
    runtime_diagnostics: dict[str, Any],
    *,
    provider_contract_health: dict[str, Any],
) -> dict[str, str]:
    negative_probe_case = _provider_negative_probe_case(
        runtime_diagnostics,
        "gateway_model_limitations",
    )
    if negative_probe_case is not None:
        return negative_probe_case

    health_status = str(provider_contract_health.get("status") or "")
    if health_status in {"gateway_blocked", "model_blocked"}:
        return {
            "case": "gateway_model_limitations",
            "status": "blocked",
            "source": "provider_contract_health",
        }
    return {
        "case": "gateway_model_limitations",
        "status": "not_covered",
        "source": "provider_e2e_required",
    }


def _provider_negative_probe_case(
    runtime_diagnostics: dict[str, Any],
    case_name: str,
) -> dict[str, str] | None:
    probes = runtime_diagnostics.get("provider_e2e_negative_probes")
    if not isinstance(probes, dict):
        return None
    probe = probes.get(case_name)
    if not isinstance(probe, dict):
        return None
    status = str(probe.get("status") or "")
    source = str(probe.get("source") or "provider_e2e_negative_probe")
    if status == "passed":
        return {
            "case": case_name,
            "status": "passed",
            "source": source,
        }
    if status:
        return {
            "case": case_name,
            "status": "blocked",
            "source": source,
        }
    return None


def _provider_tool_loop_contract(
    runtime_diagnostics: dict[str, Any],
) -> dict[str, Any] | None:
    execution = runtime_diagnostics.get("validated_runtime_execution")
    if not isinstance(execution, dict):
        return None
    contract = execution.get("tool_loop_contract")
    return contract if isinstance(contract, dict) else None


def _provider_health_from_tool_loop_contract(
    contract: dict[str, Any],
    *,
    smoke_scope: str,
) -> dict[str, Any]:
    status = str(contract.get("status") or "unknown")
    fallback = str(contract.get("fallback") or "none")
    fallback_reason = str(contract.get("fallback_reason") or "")
    blocking_reason = str(contract.get("blocking_reason") or "")
    health_status = {
        "passed": "tool_loop_limited" if fallback != "none" else "tool_loop_ready",
        "needs_recovery": "tool_loop_needs_recovery",
        "unsupported_tools": "unsupported_tools",
        "blocked": "tool_loop_blocked",
    }.get(status, "tool_loop_blocked")
    health: dict[str, Any] = {
        "status": health_status,
        "smoke_scope": smoke_scope,
        "tool_call_support": str(contract.get("tool_call_support") or "unknown"),
        "tool_result_support": str(contract.get("tool_result_support") or "unknown"),
        "fallback": fallback,
        "recovery_status": str(contract.get("recovery_status") or "unknown"),
    }
    if fallback_reason:
        health["fallback_reason"] = fallback_reason
    if health_status == "tool_loop_limited":
        health["reason"] = fallback_reason or "fallback_active"
    elif blocking_reason:
        health["reason"] = blocking_reason
    return health


def _provider_health_from_mini_pipeline(
    mini_pipeline: dict[str, Any],
    *,
    runtime_diagnostics: dict[str, Any],
    smoke_scope: str,
) -> dict[str, Any] | None:
    """Return provider health for the end-to-end mini pipeline smoke."""
    status = str(mini_pipeline.get("status") or "unknown")
    if status not in {"passed", "failed"}:
        return None

    health: dict[str, Any] = {
        "status": "mini_pipeline_ready"
        if status == "passed"
        else "mini_pipeline_blocked",
        "smoke_scope": smoke_scope,
    }
    execution = runtime_diagnostics.get("validated_runtime_execution")
    contract = (
        execution.get("tool_loop_contract") if isinstance(execution, dict) else None
    )
    if isinstance(contract, dict):
        for source_key, target_key in (
            ("tool_call_support", "tool_call_support"),
            ("tool_result_support", "tool_result_support"),
            ("fallback", "fallback"),
            ("fallback_reason", "fallback_reason"),
            ("recovery_status", "recovery_status"),
        ):
            value = contract.get(source_key)
            if isinstance(value, str) and value:
                health[target_key] = value
    recovery_loop = mini_pipeline.get("recovery_loop")
    if isinstance(recovery_loop, dict):
        recovery_loop_status = recovery_loop.get("status")
        if isinstance(recovery_loop_status, str) and recovery_loop_status:
            health["recovery_loop_status"] = recovery_loop_status
        recovery_status = recovery_loop.get("recovery_status")
        if isinstance(recovery_status, str) and recovery_status:
            health["recovery_status"] = recovery_status
        if status == "failed":
            reason = recovery_loop.get("reason")
            if isinstance(reason, str) and reason:
                health["reason"] = reason
    if status == "failed":
        health.setdefault(
            "reason",
            str(mini_pipeline.get("reason") or "mini_pipeline_failed"),
        )
    return health


def _provider_health_from_e2e_suite(
    provider_e2e_suite: dict[str, Any],
    *,
    smoke_scope: str,
) -> dict[str, Any] | None:
    """Return provider health for the direct-provider e2e suite."""
    status = str(provider_e2e_suite.get("status") or "unknown")
    if status not in {"passed", "failed"}:
        return None

    runs = provider_e2e_suite.get("runs")
    run_payloads = (
        [run for run in runs if isinstance(run, dict)] if isinstance(runs, list) else []
    )
    failed_runs = [
        str(run.get("runtime_mode") or "unknown")
        for run in run_payloads
        if str(run.get("status") or "") != "passed"
    ]
    health: dict[str, Any] = {
        "status": "provider_e2e_ready"
        if status == "passed"
        else "provider_e2e_blocked",
        "smoke_scope": smoke_scope,
        "passed_run_count": len(run_payloads) - len(failed_runs),
        "required_run_count": len(run_payloads),
    }
    if failed_runs:
        health["reason"] = "provider_e2e_failed"
        health["failed_runs"] = failed_runs
    return health


def _provider_issue_from_error(error_details: str) -> dict[str, str]:
    error_text = error_details.lower()
    if any(
        marker in error_text
        for marker in (
            "api key",
            "api_key",
            "authentication",
            "invalid key",
            "unauthorized",
            "forbidden",
            "permission denied",
        )
    ):
        return {"status": "configuration_blocked", "reason": "configuration_error"}
    if any(
        marker in error_text
        for marker in (
            "model not found",
            "model_not_found",
            "unknown model",
            "invalid model",
            "does not exist",
        )
    ):
        return {"status": "model_blocked", "reason": "model_unavailable"}
    if any(
        marker in error_text
        for marker in (
            "bad gateway",
            "gateway",
            "upstream",
            "proxy",
            "502",
            "503",
            "504",
            "connection",
            "timed out",
            "timeout",
            "rate limit",
        )
    ):
        return {"status": "gateway_blocked", "reason": "gateway_error"}
    if any(
        marker in error_text
        for marker in (
            "does not support tools",
            "function calling",
            "tool_choice",
            "unsupported tool",
        )
    ):
        return {"status": "unsupported_tools", "reason": "unsupported_tools"}
    return {"status": "provider_smoke_blocked", "reason": "provider_error"}


def _provider_validation_errors(provider: Any) -> list[str]:
    if not hasattr(provider, "validate_config"):
        return []

    try:
        if provider.validate_config():
            return []
    except Exception as e:
        return [f"Provider validation failed: {e}"]

    if hasattr(provider, "get_validation_errors"):
        try:
            errors = provider.get_validation_errors()
            return [str(error) for error in errors]
        except Exception as e:
            return [f"Could not read provider validation errors: {e}"]

    return ["Provider configuration is invalid"]


def normalize_provider_smoke_runtime_mode(value: str | None) -> str:
    """Normalize the runtime surface that the provider smoke command validates."""
    if value is None:
        return "analysis_only"
    mode = value.strip().lower().replace("-", "_")
    if mode not in PROVIDER_SMOKE_RUNTIME_MODES:
        allowed = ", ".join(PROVIDER_SMOKE_RUNTIME_MODES)
        raise ValueError(
            f"Invalid provider smoke runtime '{value}'. Must be one of: {allowed}"
        )
    return mode


def _provider_smoke_requirements(runtime_mode: str) -> RuntimeRequirements:
    if runtime_mode == "provider_e2e":
        return RuntimeRequirements(
            mode="provider_e2e",
            required=RuntimeRequirements.generic_edit().required,
        )
    if runtime_mode in {"mini_pipeline", "transaction_batch_probe"}:
        return RuntimeRequirements(
            mode=runtime_mode,
            required=RuntimeRequirements.generic_edit().required,
        )
    if runtime_mode == "generic_edit":
        return RuntimeRequirements.generic_edit()
    return RuntimeRequirements.text_only(mode="analysis_only")


def _provider_smoke_scope(runtime_mode: str) -> str:
    if runtime_mode == "provider_e2e":
        return "direct_api_full_autonomy_e2e"
    if runtime_mode == "mini_pipeline":
        return "mini_task_pipeline"
    if runtime_mode == "transaction_batch_probe":
        return "transaction_batch_probe"
    if runtime_mode == "generic_edit":
        return "generic_edit_tool_loop"
    return "text_completion_only"


def _provider_smoke_note(runtime_mode: str) -> str:
    if runtime_mode == "provider_e2e":
        return (
            "Provider e2e smoke runs the direct-provider generic_edit tool-loop "
            "check and the mini planner/coder/tests/reviewer pipeline. It "
            "aggregates full-autonomy coverage cases, but unsupported-tool and "
            "gateway/model limitation probes still require explicit negative "
            "provider runs."
        )
    if runtime_mode == "mini_pipeline":
        return (
            "Provider smoke runs a temporary planner/coder/reviewer mini task. "
            "It validates the local edit loop, one unit-test command, and a "
            "generic_edit recovery/resume loop, but it does not prove full "
            "production autonomy for arbitrary repositories."
        )
    if runtime_mode == "transaction_batch_probe":
        return (
            "Provider smoke validates a temporary generic_edit transaction batch "
            "with begin_batch, commit_batch, and committed batch diagnostics."
        )
    if runtime_mode == "generic_edit":
        return (
            "Provider smoke validates a temporary generic_edit tool loop; full "
            "autonomous coding still depends on MCP, subagents, recovery, and "
            "project-specific commands."
        )
    return (
        "Provider smoke validates text completion only; run runtime-specific "
        "tests before treating a provider as autonomous."
    )


def _provider_smoke_capability_mode(runtime_mode: str) -> str:
    """Map smoke-only scopes to the runtime mode that supplies capabilities."""
    if runtime_mode == "provider_e2e":
        return "generic_edit"
    if runtime_mode in {"mini_pipeline", "transaction_batch_probe"}:
        return "generic_edit"
    return runtime_mode


def _provider_smoke_capabilities(provider_name: str, runtime_mode: str):
    """Return runtime capabilities for a smoke validation mode."""
    return capabilities_for_runtime_mode(
        provider_name,
        normalize_runtime_mode(_provider_smoke_capability_mode(runtime_mode)),
    )


def build_provider_smoke_runtime_diagnostics(
    *,
    provider_name: str,
    requested_runtime_mode: str | None = None,
    validated_runtime_mode: str = "analysis_only",
) -> dict[str, Any]:
    """Return the runtime scope covered by a provider smoke check."""
    requested_mode = requested_runtime_mode or get_runtime_mode("analysis")
    validated_mode = normalize_provider_smoke_runtime_mode(validated_runtime_mode)
    smoke_requirements = _provider_smoke_requirements(validated_mode)
    requested_capabilities = _provider_smoke_capabilities(
        provider_name,
        requested_mode
        if requested_mode in PROVIDER_SMOKE_RUNTIME_MODES
        else normalize_runtime_mode(requested_mode),
    )
    validated_capabilities = _provider_smoke_capabilities(
        provider_name,
        validated_mode,
    )
    full_autonomous_capabilities = capabilities_for_runtime_mode(
        provider_name,
        "full_autonomous",
    )
    full_autonomous_requirements = RuntimeRequirements.full_coder()
    return {
        "provider": provider_name,
        "smoke_scope": _provider_smoke_scope(validated_mode),
        "requested_runtime_mode": requested_mode,
        "validated_runtime_mode": smoke_requirements.mode,
        "validated_requirements": list(smoke_requirements.required),
        "requested_runtime_capabilities": requested_capabilities.available(),
        "validated_runtime_capabilities": validated_capabilities.available(),
        "validated_runtime_missing_capabilities": validated_capabilities.missing(
            smoke_requirements,
        ),
        "full_autonomous_missing_capabilities": full_autonomous_capabilities.missing(
            full_autonomous_requirements,
        ),
        "note": _provider_smoke_note(validated_mode),
    }


async def run_provider_smoke_check(
    *,
    project_dir: Path,
    model: str | None = None,
    prompt: str | None = None,
    timeout_seconds: float = DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS,
    runtime_mode: str | None = None,
) -> ProviderSmokeResult:
    """Run a real smoke check against the configured provider/runtime surface."""
    provider_config = ProviderConfig.from_env(agent_type="analysis")
    provider_name = provider_config.provider
    resolved_model = model or provider_config.get_model_for_provider()
    validated_runtime_mode = normalize_provider_smoke_runtime_mode(runtime_mode)
    runtime_diagnostics = build_provider_smoke_runtime_diagnostics(
        provider_name=provider_name,
        requested_runtime_mode=runtime_mode,
        validated_runtime_mode=validated_runtime_mode,
    )

    try:
        provider = create_engine_provider(provider_config)
    except Exception as e:
        logger.debug("Provider creation failed for smoke check", exc_info=True)
        result = ProviderSmokeResult(
            success=False,
            provider=provider_name,
            model=resolved_model,
            runtime_mode="analysis_only",
            message=f"Could not create provider {provider_name}: {e}",
            error_details=str(e),
            runtime_diagnostics=_with_provider_contract_health(
                runtime_diagnostics,
                error_details=str(e),
            ),
        )
        if validated_runtime_mode == "provider_e2e":
            return _with_provider_run_history(project_dir, result)
        return result

    runtime_diagnostics = build_provider_smoke_runtime_diagnostics(
        provider_name=provider.name,
        requested_runtime_mode=runtime_mode,
        validated_runtime_mode=validated_runtime_mode,
    )
    validation_errors = _provider_validation_errors(provider)
    if validation_errors:
        error_details = "; ".join(validation_errors)
        result = ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=resolved_model,
            runtime_mode="analysis_only",
            message="Provider configuration is incomplete",
            error_details=error_details,
            runtime_diagnostics=_with_provider_contract_health(
                runtime_diagnostics,
                error_details=error_details,
            ),
        )
        if validated_runtime_mode == "provider_e2e":
            return _with_provider_run_history(project_dir, result)
        return result

    session_config = SessionConfig(
        name="provider-smoke-session",
        model=model,
        system_prompt="You are running a brief Auto Code provider smoke check.",
        extra={"agent_type": "analysis"},
    )

    try:
        if validated_runtime_mode == "provider_e2e":
            result = await _complete_provider_e2e_smoke_suite(
                provider=provider,
                session_config=session_config,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                model=resolved_model,
                runtime_diagnostics=runtime_diagnostics,
            )
            return _with_provider_run_history(project_dir, result)

        if validated_runtime_mode == "mini_pipeline":
            return await _complete_provider_mini_pipeline_smoke(
                provider=provider,
                session_config=session_config,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                model=resolved_model,
                runtime_diagnostics=runtime_diagnostics,
            )

        if validated_runtime_mode == "generic_edit":
            return await _complete_provider_generic_edit_smoke(
                provider=provider,
                session_config=session_config,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                model=resolved_model,
                runtime_diagnostics=runtime_diagnostics,
            )

        if provider.name == "claude":
            with tempfile.TemporaryDirectory(
                prefix="auto-code-provider-smoke-"
            ) as temp_dir:
                smoke_spec_dir = Path(temp_dir) / "spec"
                smoke_spec_dir.mkdir(parents=True, exist_ok=True)
                _create_provider_session(
                    provider=provider,
                    session_config=session_config,
                    project_dir=project_dir,
                    spec_dir=smoke_spec_dir,
                    agent_type="planner",
                )
                return await _complete_provider_smoke(
                    provider=provider,
                    prompt=prompt,
                    timeout_seconds=timeout_seconds,
                    model=resolved_model,
                    runtime_diagnostics=runtime_diagnostics,
                )

        _create_provider_session(
            provider=provider,
            session_config=session_config,
            project_dir=project_dir,
            agent_type="planner",
        )
        return await _complete_provider_smoke(
            provider=provider,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            model=resolved_model,
            runtime_diagnostics=runtime_diagnostics,
        )
    except Exception as e:
        logger.debug("Provider smoke check failed", exc_info=True)
        result = ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=resolved_model,
            runtime_mode="analysis_only",
            message=f"Provider smoke check failed: {e}",
            error_details=str(e),
            runtime_diagnostics=_with_provider_contract_health(
                runtime_diagnostics,
                error_details=str(e),
            ),
        )
        if validated_runtime_mode == "provider_e2e":
            return _with_provider_run_history(project_dir, result)
        return result


def _create_provider_session(
    *,
    provider: Any,
    session_config: SessionConfig,
    project_dir: Path,
    spec_dir: Path | None = None,
    agent_type: str = "analysis",
) -> Any:
    """Create a provider session while preserving Claude's required directories."""
    if provider.name == "claude":
        if spec_dir is None:
            raise ValueError("spec_dir is required for Claude provider smoke sessions")
        return provider.create_session(
            session_config,
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type=agent_type,
        )
    return provider.create_session(session_config)


async def _complete_provider_smoke(
    *,
    provider: Any,
    prompt: str | None,
    timeout_seconds: float,
    model: str | None,
    runtime_diagnostics: dict[str, Any],
) -> ProviderSmokeResult:
    smoke_prompt = prompt or DEFAULT_PROVIDER_SMOKE_PROMPT
    runtime_session = CompletionRuntimeSession(
        provider_name=provider.name,
        agent_session=ProviderSendMessageSession(provider),
    )
    result = await asyncio.wait_for(
        run_runtime_session(
            runtime_session,
            smoke_prompt,
            Path.cwd(),
            verbose=False,
            phase=LogPhase.PLANNING,
            requirements=RuntimeRequirements.text_only(mode="provider_smoke"),
        ),
        timeout=timeout_seconds,
    )
    response_text = result.response_text.strip()
    if not response_text:
        return ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=model,
            runtime_mode="analysis_only",
            message="Provider returned an empty response",
            runtime_diagnostics=_with_provider_contract_health(
                runtime_diagnostics,
                error_details="Provider returned an empty response",
            ),
        )

    return ProviderSmokeResult(
        success=True,
        provider=provider.name,
        model=model,
        runtime_mode="analysis_only",
        message="Provider smoke check passed",
        response_excerpt=_response_excerpt(response_text),
        runtime_diagnostics=_with_provider_contract_health(
            runtime_diagnostics,
            success=True,
        ),
    )


def _provider_e2e_negative_probe_payload() -> dict[str, dict[str, str]]:
    """Return deterministic negative classification probes for provider e2e."""
    unsupported_issue = _provider_issue_from_error(
        "The selected model does not support tools."
    )
    gateway_issue = _provider_issue_from_error(
        "502 Bad gateway from the upstream model gateway."
    )
    return {
        "unsupported_tools": {
            "status": "passed"
            if unsupported_issue["status"] == "unsupported_tools"
            else "failed",
            "source": "provider_e2e_negative_probe",
            "reason": unsupported_issue["reason"],
        },
        "gateway_model_limitations": {
            "status": "passed"
            if gateway_issue["status"] == "gateway_blocked"
            else "failed",
            "source": "provider_e2e_negative_probe",
            "reason": gateway_issue["reason"],
        },
    }


def _provider_e2e_negative_fixture_payload(provider: str) -> dict[str, dict[str, str]]:
    """Return provider-specific negative fixtures for direct-provider e2e."""
    normalized_provider = provider.lower()
    fixture = PROVIDER_RELIABILITY_NEGATIVE_FIXTURES.get(normalized_provider)
    if fixture is None:
        return _provider_e2e_negative_probe_payload()

    surface = str(fixture["surface"])
    unsupported_issue = _provider_issue_from_error(
        str(fixture["unsupported_tools_error"])
    )
    gateway_issue = _provider_issue_from_error(str(fixture["gateway_model_error"]))
    return {
        "unsupported_tools": {
            "status": "passed"
            if unsupported_issue["status"] == "unsupported_tools"
            else "failed",
            "source": "provider_adapter_negative_fixture",
            "reason": unsupported_issue["reason"],
            "fixture_provider": normalized_provider,
            "fixture_surface": surface,
        },
        "gateway_model_limitations": {
            "status": "passed"
            if gateway_issue["status"] == "gateway_blocked"
            else "failed",
            "source": "provider_adapter_negative_fixture",
            "reason": gateway_issue["reason"],
            "fixture_provider": normalized_provider,
            "fixture_surface": surface,
        },
    }


def _provider_e2e_negative_fixture_summary(
    *,
    provider: str,
    probes: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Return provider e2e fixture coverage summary for diagnostics/UI."""
    covered_cases = [
        case_name
        for case_name, probe in probes.items()
        if isinstance(probe, dict) and probe.get("status") == "passed"
    ]
    source = next(
        (
            str(probe.get("source"))
            for probe in probes.values()
            if isinstance(probe, dict) and probe.get("source")
        ),
        "provider_e2e_negative_probe",
    )
    return {
        "status": "passed"
        if len(covered_cases) == len(probes) and bool(probes)
        else "failed",
        "provider": provider.lower(),
        "source": source,
        "covered_cases": covered_cases,
    }


def _provider_e2e_negative_probe_runs(
    probes: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    """Return e2e suite child-run summaries for deterministic negative probes."""
    return [
        {
            "runtime_mode": "unsupported_tools_probe",
            "status": str(probes["unsupported_tools"].get("status") or "failed"),
            "message": "Unsupported tool classification probe passed"
            if probes["unsupported_tools"].get("status") == "passed"
            else "Unsupported tool classification probe failed",
        },
        {
            "runtime_mode": "gateway_model_probe",
            "status": str(
                probes["gateway_model_limitations"].get("status") or "failed"
            ),
            "message": "Gateway/model limitation classification probe passed"
            if probes["gateway_model_limitations"].get("status") == "passed"
            else "Gateway/model limitation classification probe failed",
        },
    ]


def _provider_e2e_negative_probe_reliability(
    provider: str,
    probes: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    """Return a provider reliability payload covering e2e negative probes."""
    normalized_provider = provider.lower()
    if normalized_provider not in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        return None
    probe_diagnostics = {
        "provider": normalized_provider,
        "provider_e2e_negative_probes": probes,
    }
    cases = [
        {
            "case": case_name,
            "status": "not_covered",
            "source": "provider_e2e_required",
        }
        for case_name in PROVIDER_RELIABILITY_CASE_ORDER
    ]
    for index, case_name in enumerate(PROVIDER_RELIABILITY_CASE_ORDER):
        probe_case = _provider_negative_probe_case(probe_diagnostics, case_name)
        if probe_case is not None:
            cases[index] = probe_case
    return _provider_reliability_payload(normalized_provider, cases)


def _provider_live_fault_env_provider(provider: str) -> str:
    """Return an env-safe provider token for live fault fixtures."""
    return "".join(
        character.upper() if character.isalnum() else "_" for character in provider
    ).strip("_")


def _provider_live_fault_required_env(provider: str) -> list[str]:
    """Return the opt-in env contract for provider live fault fixtures."""
    provider_token = _provider_live_fault_env_provider(provider)
    return [
        PROVIDER_E2E_LIVE_FAULT_PROBES_ENV,
        (
            f"AUTO_CODE_PROVIDER_E2E_LIVE_{provider_token}_UNSUPPORTED_TOOLS_ERROR "
            "or AUTO_CODE_PROVIDER_E2E_LIVE_UNSUPPORTED_TOOLS_ERROR"
        ),
        (
            f"AUTO_CODE_PROVIDER_E2E_LIVE_{provider_token}_GATEWAY_MODEL_ERROR "
            "or AUTO_CODE_PROVIDER_E2E_LIVE_GATEWAY_MODEL_ERROR"
        ),
    ]


def _provider_live_fault_error_env_names(
    provider: str,
    suffix: str,
) -> list[str]:
    """Return provider-specific then generic live fault env names."""
    provider_token = _provider_live_fault_env_provider(provider)
    return [
        f"AUTO_CODE_PROVIDER_E2E_LIVE_{provider_token}_{suffix}",
        f"AUTO_CODE_PROVIDER_E2E_LIVE_{suffix}",
    ]


def _provider_live_fault_error_from_env(
    env: Mapping[str, str],
    *,
    provider: str,
    suffix: str,
) -> tuple[str | None, str | None, str]:
    """Return the configured live fault error, source env, and required label."""
    env_names = _provider_live_fault_error_env_names(provider, suffix)
    for env_name in env_names:
        value = env.get(env_name)
        if isinstance(value, str) and value.strip():
            return value.strip(), env_name, " or ".join(env_names)
    return None, None, " or ".join(env_names)


def _provider_live_fault_enabled(env: Mapping[str, str]) -> bool:
    """Return whether live fault fixtures are explicitly enabled."""
    value = env.get(PROVIDER_E2E_LIVE_FAULT_PROBES_ENV)
    return isinstance(value, str) and value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _provider_e2e_live_fault_probe_payload(
    provider: str,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return opt-in live fault probe diagnostics for provider e2e."""
    normalized_provider = provider.lower()
    live_env = os.environ if env is None else env
    required_env = _provider_live_fault_required_env(normalized_provider)
    if not _provider_live_fault_enabled(live_env):
        return {
            "status": "not_configured",
            "provider": normalized_provider,
            "source": "provider_live_fault_fixture",
            "enabled": False,
            "required_env": required_env,
            "covered_cases": [],
        }

    probes: dict[str, dict[str, str]] = {}
    missing_env: list[str] = []
    covered_cases: list[str] = []
    for case_name, case_config in PROVIDER_E2E_LIVE_FAULT_CASES.items():
        case_result = _provider_e2e_live_fault_probe_case(
            provider=normalized_provider,
            case_config=case_config,
            suffix=str(case_config["suffix"]),
            env=live_env,
        )
        probes[case_name] = case_result["probe"]
        if case_result["missing_env"]:
            missing_env.append(str(case_result["missing_env"]))
        if case_result["covered"]:
            covered_cases.append(case_name)

    payload: dict[str, Any] = {
        "status": _provider_e2e_live_fault_status(
            missing_env=missing_env,
            covered_cases=covered_cases,
        ),
        "provider": normalized_provider,
        "source": "provider_live_fault_fixture",
        "enabled": True,
        "required_env": required_env,
        "covered_cases": covered_cases,
        "probes": probes,
    }
    if missing_env:
        payload["missing_env"] = missing_env
    return payload


def _provider_e2e_live_fault_probe_case(
    *,
    provider: str,
    case_config: Mapping[str, Any],
    suffix: str,
    env: Mapping[str, str],
) -> dict[str, Any]:
    """Return one live-fault probe case outcome."""
    error_text, env_name, required_label = _provider_live_fault_error_from_env(
        env,
        provider=provider,
        suffix=suffix,
    )
    if error_text is None:
        return {
            "covered": False,
            "missing_env": required_label,
            "probe": {
                "status": "skipped",
                "source": "provider_live_fault_fixture",
                "reason": "missing_live_fault_fixture",
                "fixture_provider": provider,
            },
        }

    issue = _provider_issue_from_error(error_text)
    passed = issue["status"] in _provider_live_fault_expected_statuses(case_config)
    return {
        "covered": passed,
        "missing_env": None,
        "probe": {
            "status": "passed" if passed else "failed",
            "source": "provider_live_fault_fixture",
            "reason": str(issue["reason"]),
            "fixture_provider": provider,
            "env_name": str(env_name),
        },
    }


def _provider_live_fault_expected_statuses(
    case_config: Mapping[str, Any],
) -> set[str]:
    """Return normalized expected issue statuses for one live-fault case."""
    expected_statuses = case_config["expected_statuses"]
    if isinstance(expected_statuses, str):
        return {expected_statuses}
    return {str(status) for status in expected_statuses}


def _provider_e2e_live_fault_status(
    *,
    missing_env: list[str],
    covered_cases: list[str],
) -> str:
    """Return aggregate live-fault probe status from case outcomes."""
    if missing_env:
        return "configuration_blocked"
    if len(covered_cases) == len(PROVIDER_E2E_LIVE_FAULT_CASES):
        return "passed"
    return "failed"


def _provider_e2e_live_fault_probe_runs(
    live_fault_probes: dict[str, Any],
) -> list[dict[str, str]]:
    """Return provider e2e child-run summaries for live fault probes."""
    if live_fault_probes.get("status") == "not_configured":
        return []
    probes = live_fault_probes.get("probes")
    if not isinstance(probes, dict):
        return []
    runs: list[dict[str, str]] = []
    for case_name, case_config in PROVIDER_E2E_LIVE_FAULT_CASES.items():
        probe = probes.get(case_name)
        if not isinstance(probe, dict):
            continue
        probe_status = str(probe.get("status") or "failed")
        passed = probe_status == "passed"
        if passed:
            message = str(case_config["passed_message"])
        elif probe_status == "skipped":
            message = str(case_config["skipped_message"])
        else:
            message = str(case_config["failed_message"])
        run_payload = {
            "runtime_mode": str(case_config["runtime_mode"]),
            "status": probe_status,
            "message": message,
        }
        reason = probe.get("reason")
        if not passed and isinstance(reason, str) and reason:
            run_payload["reason"] = reason
        runs.append(run_payload)
    return runs


async def _complete_provider_e2e_smoke_suite(
    *,
    provider: Any,
    session_config: SessionConfig,
    prompt: str | None,
    timeout_seconds: float,
    model: str | None,
    runtime_diagnostics: dict[str, Any],
) -> ProviderSmokeResult:
    """Run the provider-specific e2e suite over live direct-provider surfaces."""
    child_results: list[ProviderSmokeResult] = []
    suite_runs: list[dict[str, str]] = []
    for child_runtime_mode, runner, child_prompt in (
        ("generic_edit", _complete_provider_generic_edit_smoke, None),
        ("mini_pipeline", _complete_provider_mini_pipeline_smoke, prompt),
        (
            "transaction_batch_probe",
            _complete_provider_transaction_batch_smoke,
            None,
        ),
    ):
        child_diagnostics = build_provider_smoke_runtime_diagnostics(
            provider_name=provider.name,
            requested_runtime_mode=child_runtime_mode,
            validated_runtime_mode=child_runtime_mode,
        )
        try:
            child_result = await runner(
                provider=provider,
                session_config=session_config,
                prompt=child_prompt,
                timeout_seconds=timeout_seconds,
                model=model,
                runtime_diagnostics=child_diagnostics,
            )
        except Exception as e:
            logger.debug(
                "Provider e2e smoke child run failed",
                exc_info=True,
                extra={"runtime_mode": child_runtime_mode},
            )
            child_result = ProviderSmokeResult(
                success=False,
                provider=provider.name,
                model=model,
                runtime_mode=child_runtime_mode,
                message=f"Provider {child_runtime_mode} smoke failed: {e}",
                error_details=str(e),
                runtime_diagnostics=_with_provider_contract_health(
                    child_diagnostics,
                    error_details=str(e),
                ),
            )
        child_results.append(child_result)
        run_payload = {
            "runtime_mode": child_result.runtime_mode,
            "status": "passed" if child_result.success else "failed",
            "message": child_result.message,
        }
        if child_result.error_details:
            run_payload["reason"] = _response_excerpt(
                child_result.error_details,
                max_chars=160,
            )
        suite_runs.append(run_payload)

    negative_probes = _provider_e2e_negative_fixture_payload(provider.name)
    negative_fixture_summary = _provider_e2e_negative_fixture_summary(
        provider=provider.name,
        probes=negative_probes,
    )
    negative_probe_runs = _provider_e2e_negative_probe_runs(negative_probes)
    live_fault_probes = _provider_e2e_live_fault_probe_payload(provider.name)
    live_fault_probe_runs = _provider_e2e_live_fault_probe_runs(live_fault_probes)
    suite_runs.extend(negative_probe_runs)
    suite_runs.extend(live_fault_probe_runs)
    negative_probe_success = all(
        run.get("status") == "passed" for run in negative_probe_runs
    )
    live_fault_probe_success = live_fault_probes.get("status") in {
        "not_configured",
        "passed",
    }
    success = (
        all(child.success for child in child_results)
        and negative_probe_success
        and live_fault_probe_success
    )
    suite_status = "passed" if success else "failed"
    reliability = _merge_provider_reliability_diagnostics(
        provider.name,
        [
            child.runtime_diagnostics.get("provider_reliability")
            for child in child_results
        ]
        + [_provider_e2e_negative_probe_reliability(provider.name, negative_probes)],
    )
    next_diagnostics: dict[str, Any] = {
        **runtime_diagnostics,
        "provider_e2e_suite": {
            "status": suite_status,
            "runs": suite_runs,
        },
        "provider_e2e_negative_probes": negative_probes,
        "provider_e2e_negative_fixtures": negative_fixture_summary,
        "provider_e2e_live_fault_probes": live_fault_probes,
    }
    if reliability is not None:
        next_diagnostics["provider_reliability"] = reliability

    response_excerpt = _response_excerpt(
        "; ".join(
            child.response_excerpt or child.message
            for child in child_results
            if child.response_excerpt or child.message
        )
    )
    error_details = (
        "; ".join(
            child.error_details or child.message
            for child in child_results
            if not child.success
        )
        or None
    )
    return ProviderSmokeResult(
        success=success,
        provider=provider.name,
        model=model,
        runtime_mode="provider_e2e",
        message=(
            "Provider e2e smoke suite passed"
            if success
            else "Provider e2e smoke suite failed"
        ),
        response_excerpt=response_excerpt if success else None,
        error_details=error_details,
        runtime_diagnostics=_with_provider_contract_health(
            next_diagnostics,
            success=success,
            error_details=error_details,
        ),
    )


async def _complete_provider_generic_edit_smoke(
    *,
    provider: Any,
    session_config: SessionConfig,
    prompt: str | None,
    timeout_seconds: float,
    model: str | None,
    runtime_diagnostics: dict[str, Any],
) -> ProviderSmokeResult:
    smoke_prompt = prompt or DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_PROMPT
    with tempfile.TemporaryDirectory(prefix="auto-code-provider-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        smoke_project_dir = temp_root / "project"
        smoke_spec_dir = temp_root / "spec"
        smoke_project_dir.mkdir(parents=True, exist_ok=True)
        smoke_spec_dir.mkdir(parents=True, exist_ok=True)
        smoke_file = smoke_project_dir / "provider-smoke.txt"
        smoke_file.write_text("pending\n", encoding="utf-8")
        session = _create_provider_session(
            provider=provider,
            session_config=session_config,
            project_dir=smoke_project_dir,
            spec_dir=smoke_spec_dir,
            agent_type="coder",
        )
        runtime_session = create_runtime_session(
            provider_name=provider.name,
            agent_session=session,
            runtime_mode="generic_edit",
            project_dir=smoke_project_dir,
            agent_type="coder",
        )
        result = await asyncio.wait_for(
            run_runtime_session(
                runtime_session,
                smoke_prompt,
                smoke_spec_dir,
                verbose=False,
                phase=LogPhase.PLANNING,
                requirements=RuntimeRequirements.generic_edit(),
            ),
            timeout=timeout_seconds,
        )
        execution_diagnostics = _generic_edit_execution_diagnostics(
            smoke_spec_dir / "artifacts",
        )
        if execution_diagnostics is not None:
            runtime_diagnostics = {
                **runtime_diagnostics,
                "validated_runtime_execution": execution_diagnostics,
            }

        smoke_content = smoke_file.read_text(encoding="utf-8")
        if smoke_content != DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_CONTENT:
            error_details = (
                "Expected provider-smoke.txt to contain "
                f"{DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_CONTENT!r}; got "
                f"{smoke_content!r}"
            )
            return ProviderSmokeResult(
                success=False,
                provider=provider.name,
                model=model,
                runtime_mode="generic_edit",
                message="Provider generic_edit smoke did not update the test file",
                response_excerpt=_response_excerpt(result.response_text),
                error_details=error_details,
                runtime_diagnostics=_with_provider_contract_health(
                    runtime_diagnostics,
                    error_details=error_details,
                ),
            )

    response_text = result.response_text.strip()
    if not response_text:
        return ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=model,
            runtime_mode="generic_edit",
            message="Provider generic_edit smoke returned an empty response",
            runtime_diagnostics=_with_provider_contract_health(
                runtime_diagnostics,
                error_details="Provider generic_edit smoke returned an empty response",
            ),
        )

    return ProviderSmokeResult(
        success=True,
        provider=provider.name,
        model=model,
        runtime_mode="generic_edit",
        message="Provider generic_edit smoke passed",
        response_excerpt=_response_excerpt(response_text),
        runtime_diagnostics=_with_provider_contract_health(
            runtime_diagnostics,
            success=True,
        ),
    )


async def _complete_provider_transaction_batch_smoke(
    *,
    provider: Any,
    session_config: SessionConfig,
    prompt: str | None,
    timeout_seconds: float,
    model: str | None,
    runtime_diagnostics: dict[str, Any],
) -> ProviderSmokeResult:
    """Run a generic_edit smoke that must exercise begin/commit batch semantics."""
    del prompt
    result = await _complete_provider_generic_edit_smoke(
        provider=provider,
        session_config=session_config,
        prompt=DEFAULT_PROVIDER_TRANSACTION_BATCH_SMOKE_PROMPT,
        timeout_seconds=timeout_seconds,
        model=model,
        runtime_diagnostics={
            **runtime_diagnostics,
            "smoke_scope": "transaction_batch_probe",
        },
    )
    execution = result.runtime_diagnostics.get("validated_runtime_execution")
    contract = (
        execution.get("transaction_batch_contract")
        if isinstance(execution, dict)
        else None
    )
    case = _provider_transaction_batch_case(result.runtime_diagnostics)
    if case.get("status") != "passed":
        error_details = (
            "Provider transaction batch smoke did not observe a committed batch."
        )
        return ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=model,
            runtime_mode="transaction_batch_probe",
            message="Provider transaction batch smoke failed",
            response_excerpt=result.response_excerpt,
            error_details=error_details,
            runtime_diagnostics=_with_provider_contract_health(
                {
                    **result.runtime_diagnostics,
                    "smoke_scope": "transaction_batch_probe",
                    "transaction_batch_contract": contract,
                },
                error_details=error_details,
            ),
        )

    return ProviderSmokeResult(
        success=True,
        provider=provider.name,
        model=model,
        runtime_mode="transaction_batch_probe",
        message="Provider transaction batch smoke passed",
        response_excerpt=result.response_excerpt,
        runtime_diagnostics=_with_provider_contract_health(
            {
                **result.runtime_diagnostics,
                "smoke_scope": "transaction_batch_probe",
            },
            success=True,
        ),
    )


async def _complete_provider_mini_pipeline_smoke(
    *,
    provider: Any,
    session_config: SessionConfig,
    prompt: str | None,
    timeout_seconds: float,
    model: str | None,
    runtime_diagnostics: dict[str, Any],
) -> ProviderSmokeResult:
    """Run a tiny planner/coder/tests/reviewer pipeline in a temp project."""
    task = prompt or DEFAULT_PROVIDER_MINI_PIPELINE_TASK
    phases: list[dict[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="auto-code-provider-pipeline-") as temp_dir:
        temp_root = Path(temp_dir)
        smoke_project_dir = temp_root / "project"
        smoke_spec_dir = temp_root / "spec"
        smoke_project_dir.mkdir(parents=True, exist_ok=True)
        smoke_spec_dir.mkdir(parents=True, exist_ok=True)
        string_tools_path = smoke_project_dir / "string_tools.py"
        string_tools_path.write_text(
            MINI_PIPELINE_INITIAL_STRING_TOOLS,
            encoding="utf-8",
        )
        (smoke_project_dir / "test_string_tools.py").write_text(
            MINI_PIPELINE_TEST_FILE,
            encoding="utf-8",
        )

        planner_response = await _complete_provider_text_phase(
            provider=provider,
            message=DEFAULT_PROVIDER_MINI_PIPELINE_PLANNER_PROMPT.format(task=task),
            spec_dir=smoke_spec_dir,
            timeout_seconds=timeout_seconds,
            mode="mini_pipeline_planner",
        )
        phases.append({"name": "planner", "status": "passed"})

        session = _create_provider_session(
            provider=provider,
            session_config=session_config,
            project_dir=smoke_project_dir,
            spec_dir=smoke_spec_dir,
            agent_type="coder",
        )
        runtime_session = create_runtime_session(
            provider_name=provider.name,
            agent_session=session,
            runtime_mode="generic_edit",
            project_dir=smoke_project_dir,
            agent_type="coder",
        )
        coder_result = await asyncio.wait_for(
            run_runtime_session(
                runtime_session,
                DEFAULT_PROVIDER_MINI_PIPELINE_CODER_PROMPT.format(
                    task=task,
                    planner_response=planner_response.strip(),
                ),
                smoke_spec_dir,
                verbose=False,
                phase=LogPhase.PLANNING,
                requirements=RuntimeRequirements.generic_edit(),
            ),
            timeout=timeout_seconds,
        )
        del coder_result
        phases.append({"name": "coder", "status": "passed"})

        execution_diagnostics = _generic_edit_execution_diagnostics(
            smoke_spec_dir / "artifacts",
        )
        if execution_diagnostics is not None:
            runtime_diagnostics = {
                **runtime_diagnostics,
                "validated_runtime_execution": execution_diagnostics,
            }

        test_exit_code, test_output = await _run_mini_pipeline_tests(
            smoke_project_dir,
            timeout_seconds=timeout_seconds,
        )
        if test_exit_code != 0:
            phases.append({"name": "tests", "status": "failed"})
            return _mini_pipeline_result(
                provider=provider,
                model=model,
                runtime_diagnostics=runtime_diagnostics,
                task=task,
                phases=phases,
                changed_files=_mini_pipeline_changed_files(string_tools_path),
                success=False,
                message="Provider mini pipeline failed unit tests",
                response_excerpt=None,
                error_details=test_output,
                test_exit_code=test_exit_code,
                reason="unit_tests_failed",
            )
        phases.append({"name": "tests", "status": "passed"})

        recovery_spec_dir = smoke_spec_dir / "recovery"
        recovery_spec_dir.mkdir(parents=True, exist_ok=True)
        (
            recovery_loop,
            recovery_execution,
        ) = await _complete_provider_mini_pipeline_recovery_loop(
            provider=provider,
            session_config=session_config,
            project_dir=smoke_project_dir,
            spec_dir=recovery_spec_dir,
            timeout_seconds=timeout_seconds,
        )
        if recovery_execution is not None:
            runtime_diagnostics = {
                **runtime_diagnostics,
                "validated_recovery_execution": recovery_execution,
            }
        if recovery_loop.get("status") != "passed":
            phases.append({"name": "recovery", "status": "failed"})
            return _mini_pipeline_result(
                provider=provider,
                model=model,
                runtime_diagnostics=runtime_diagnostics,
                task=task,
                phases=phases,
                changed_files=_mini_pipeline_changed_files(string_tools_path),
                success=False,
                message="Provider mini pipeline recovery loop failed",
                response_excerpt=None,
                error_details=str(recovery_loop.get("reason") or "recovery_failed"),
                test_exit_code=test_exit_code,
                reason="recovery_loop_failed",
                recovery_loop=recovery_loop,
            )
        phases.append({"name": "recovery", "status": "passed"})

        implementation = string_tools_path.read_text(encoding="utf-8")
        reviewer_response = await _complete_provider_text_phase(
            provider=provider,
            message=DEFAULT_PROVIDER_MINI_PIPELINE_REVIEW_PROMPT.format(
                task=task,
                test_exit_code=test_exit_code,
                test_output=test_output or "(no output)",
                implementation=implementation,
            ),
            spec_dir=smoke_spec_dir,
            timeout_seconds=timeout_seconds,
            mode="mini_pipeline_reviewer",
        )
        if not reviewer_response.strip():
            phases.append({"name": "reviewer", "status": "failed"})
            return _mini_pipeline_result(
                provider=provider,
                model=model,
                runtime_diagnostics=runtime_diagnostics,
                task=task,
                phases=phases,
                changed_files=_mini_pipeline_changed_files(string_tools_path),
                success=False,
                message="Provider mini pipeline reviewer returned an empty response",
                response_excerpt=None,
                error_details="Provider mini pipeline reviewer returned an empty response",
                test_exit_code=test_exit_code,
                reason="reviewer_empty_response",
                recovery_loop=recovery_loop,
            )
        phases.append({"name": "reviewer", "status": "passed"})

        return _mini_pipeline_result(
            provider=provider,
            model=model,
            runtime_diagnostics=runtime_diagnostics,
            task=task,
            phases=phases,
            changed_files=_mini_pipeline_changed_files(string_tools_path),
            success=True,
            message="Provider mini pipeline smoke passed",
            response_excerpt=_response_excerpt(reviewer_response),
            error_details=None,
            test_exit_code=test_exit_code,
            recovery_loop=recovery_loop,
        )


async def _complete_provider_mini_pipeline_recovery_loop(
    *,
    provider: Any,
    session_config: SessionConfig,
    project_dir: Path,
    spec_dir: Path,
    timeout_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Run a recoverable generic_edit failure and resume it to completion."""
    target_path = project_dir / "recovery-target.txt"
    target_path.write_text(
        DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_INITIAL_CONTENT,
        encoding="utf-8",
    )
    checkpoint_path = spec_dir / "artifacts" / "generic_edit_recovery_checkpoint.json"

    try:
        initial_session = _create_provider_session(
            provider=provider,
            session_config=session_config,
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type="coder",
        )
        initial_runtime = create_runtime_session(
            provider_name=provider.name,
            agent_session=initial_session,
            runtime_mode="generic_edit",
            project_dir=project_dir,
            agent_type="coder",
        )
        first_result = await asyncio.wait_for(
            run_runtime_session(
                initial_runtime,
                DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_PROMPT,
                spec_dir,
                verbose=False,
                phase=LogPhase.PLANNING,
                requirements=RuntimeRequirements.generic_edit(),
            ),
            timeout=timeout_seconds,
        )
        if first_result.status != "error" or not checkpoint_path.exists():
            return (
                {
                    "status": "failed",
                    "reason": "recovery_checkpoint_not_created",
                    "initial_result_status": first_result.status,
                },
                _generic_edit_execution_diagnostics(spec_dir / "artifacts"),
            )

        preflight = inspect_generic_edit_resume_artifacts(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
        )
        if preflight.get("status") != "ready":
            return (
                _mini_pipeline_recovery_loop_failure(
                    reason="resume_preflight_blocked",
                    preflight=preflight,
                ),
                _generic_edit_execution_diagnostics(spec_dir / "artifacts"),
            )

        resume_session = _create_provider_session(
            provider=provider,
            session_config=session_config,
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type="coder",
        )
        resume_runtime = create_runtime_session(
            provider_name=provider.name,
            agent_session=resume_session,
            runtime_mode="generic_edit",
            project_dir=project_dir,
            agent_type="coder",
        )
        resumed = await asyncio.wait_for(
            resume_runtime_session(
                resume_runtime,
                checkpoint_path,
                spec_dir,
                verbose=False,
                phase=LogPhase.PLANNING,
                requirements=RuntimeRequirements.generic_edit(),
            ),
            timeout=timeout_seconds,
        )

        artifact_dir = spec_dir / "artifacts"
        execution_diagnostics = _generic_edit_execution_diagnostics(artifact_dir)
        result_payload = _load_json_file(artifact_dir / "generic_edit_result.json")
        if not isinstance(result_payload, dict):
            return (
                {
                    "status": "failed",
                    "reason": "result_artifact_unreadable",
                    "resume_result_status": resumed.status,
                },
                execution_diagnostics,
            )

        final_content = target_path.read_text(encoding="utf-8")
        workspace_guard = (
            result_payload.get("resume", {}).get("workspace_guard")
            if isinstance(result_payload.get("resume"), dict)
            else {}
        )
        workspace_guard_status = (
            workspace_guard.get("status")
            if isinstance(workspace_guard, dict)
            else "unknown"
        )
        recovery_resolved = result_payload.get("recovery_resolved") is True
        if (
            resumed.status != "continue"
            or final_content != DEFAULT_PROVIDER_MINI_PIPELINE_RECOVERY_CONTENT
            or not recovery_resolved
            or workspace_guard_status != "clean"
        ):
            return (
                {
                    "status": "failed",
                    "reason": "resume_recovery_not_clean",
                    "resume_result_status": resumed.status,
                    "recovery_status": "resolved"
                    if recovery_resolved
                    else "requires_resolution",
                    "workspace_guard_status": str(workspace_guard_status),
                },
                execution_diagnostics,
            )

        resume_policy = preflight.get("resume_policy")
        if not isinstance(resume_policy, dict):
            resume_policy = {}
        return (
            {
                "status": "passed",
                "preflight_status": str(preflight.get("status") or "unknown"),
                "resume_policy_status": str(resume_policy.get("status") or "unknown"),
                "required_resolution_action_kinds": _string_list_payload(
                    resume_policy.get("required_resolution_action_kinds")
                ),
                "resume_result_status": resumed.status,
                "recovery_status": "resolved",
                "workspace_guard_status": str(workspace_guard_status),
                "changed_files": ["recovery-target.txt"],
            },
            execution_diagnostics,
        )
    except Exception as e:
        logger.debug("Provider mini pipeline recovery loop failed", exc_info=True)
        return (
            {
                "status": "failed",
                "reason": "recovery_loop_exception",
                "message": _response_excerpt(str(e), max_chars=240),
            },
            _generic_edit_execution_diagnostics(spec_dir / "artifacts"),
        )


def _mini_pipeline_recovery_loop_failure(
    *,
    reason: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    resume_policy = preflight.get("resume_policy")
    if not isinstance(resume_policy, dict):
        resume_policy = {}
    return {
        "status": "failed",
        "reason": reason,
        "preflight_status": str(preflight.get("status") or "unknown"),
        "resume_policy_status": str(resume_policy.get("status") or "unknown"),
        "required_resolution_action_kinds": _string_list_payload(
            resume_policy.get("required_resolution_action_kinds")
        ),
        "blockers": preflight.get("blockers", []),
    }


def _load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


async def _complete_provider_text_phase(
    *,
    provider: Any,
    message: str,
    spec_dir: Path,
    timeout_seconds: float,
    mode: str,
) -> str:
    """Run one text-only provider phase and return its response."""
    runtime_session = CompletionRuntimeSession(
        provider_name=provider.name,
        agent_session=ProviderSendMessageSession(provider),
    )
    result = await asyncio.wait_for(
        run_runtime_session(
            runtime_session,
            message,
            spec_dir,
            verbose=False,
            phase=LogPhase.PLANNING,
            requirements=RuntimeRequirements.text_only(mode=mode),
        ),
        timeout=timeout_seconds,
    )
    return result.response_text.strip()


async def _run_mini_pipeline_tests(
    project_dir: Path,
    *,
    timeout_seconds: float,
) -> tuple[int, str]:
    """Run the mini pipeline unittest command in the temporary project."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "unittest",
        "-q",
        cwd=project_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=max(1.0, min(timeout_seconds, 15.0)),
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        return 124, "Mini pipeline unit tests timed out."

    output = "\n".join(
        part.decode("utf-8", errors="replace").strip()
        for part in (stdout, stderr)
        if part
    ).strip()
    return process.returncode or 0, output


def _mini_pipeline_changed_files(string_tools_path: Path) -> list[str]:
    if (
        string_tools_path.read_text(encoding="utf-8")
        == MINI_PIPELINE_INITIAL_STRING_TOOLS
    ):
        return []
    return ["string_tools.py"]


def _mini_pipeline_result(
    *,
    provider: Any,
    model: str | None,
    runtime_diagnostics: dict[str, Any],
    task: str,
    phases: list[dict[str, str]],
    changed_files: list[str],
    success: bool,
    message: str,
    response_excerpt: str | None,
    error_details: str | None,
    test_exit_code: int,
    reason: str | None = None,
    recovery_loop: dict[str, Any] | None = None,
) -> ProviderSmokeResult:
    mini_pipeline: dict[str, Any] = {
        "status": "passed" if success else "failed",
        "task": task,
        "test_command": DEFAULT_PROVIDER_MINI_PIPELINE_TEST_COMMAND,
        "test_exit_code": test_exit_code,
        "changed_files": changed_files,
        "phases": phases,
    }
    if reason:
        mini_pipeline["reason"] = reason
    if recovery_loop is not None:
        mini_pipeline["recovery_loop"] = recovery_loop
    next_diagnostics = {
        **runtime_diagnostics,
        "mini_pipeline": mini_pipeline,
    }
    return ProviderSmokeResult(
        success=success,
        provider=provider.name,
        model=model,
        runtime_mode="mini_pipeline",
        message=message,
        response_excerpt=response_excerpt,
        error_details=error_details,
        runtime_diagnostics=_with_provider_contract_health(
            next_diagnostics,
            success=success,
        ),
    )


def _print_provider_smoke_result(result: ProviderSmokeResult) -> None:
    """Print the human-readable provider smoke result."""
    print_status(
        result.message,
        "success" if result.success else "error",
    )
    print_key_value("Provider", result.provider)
    print_key_value("Model", result.model or "default")
    print_key_value("Runtime mode", result.runtime_mode)
    _print_provider_runtime_diagnostics(result.runtime_diagnostics)
    if result.response_excerpt:
        print_key_value("Response", result.response_excerpt)
    if result.error_details:
        print_key_value("Details", result.error_details)


def _print_provider_runtime_diagnostics(
    runtime_diagnostics: dict[str, Any],
) -> None:
    """Print provider runtime diagnostics when the smoke result includes them."""
    if not runtime_diagnostics:
        return
    print_key_value(
        "Smoke scope",
        str(runtime_diagnostics.get("smoke_scope", "unknown")),
    )
    _print_provider_contract_health(runtime_diagnostics.get("provider_contract_health"))
    _print_provider_reliability(runtime_diagnostics.get("provider_reliability"))
    _print_provider_e2e_suite(runtime_diagnostics.get("provider_e2e_suite"))
    _print_provider_run_history(runtime_diagnostics.get("provider_run_history"))
    _print_provider_autonomous_readiness(
        runtime_diagnostics.get("provider_autonomous_readiness")
    )
    _print_provider_execution_diagnostics(
        runtime_diagnostics.get("validated_runtime_execution")
    )


def _print_provider_contract_health(health: Any) -> None:
    """Print the provider contract health summary."""
    if not isinstance(health, dict):
        return
    print_key_value(
        "Provider health",
        str(health.get("status", "unknown")),
    )
    reason = health.get("reason")
    if isinstance(reason, str) and reason:
        print_key_value("Provider health reason", reason)


def _print_provider_reliability(reliability: Any) -> None:
    """Print direct-provider reliability coverage diagnostics."""
    if not isinstance(reliability, dict):
        return
    status = reliability.get("status")
    if isinstance(status, str) and status:
        print_key_value("Provider reliability", status)
    coverage_parts = [
        (
            f"{reliability['passed_case_count']}/"
            f"{reliability['required_case_count']} passed"
        )
        if isinstance(reliability.get("passed_case_count"), int)
        and not isinstance(reliability.get("passed_case_count"), bool)
        and isinstance(reliability.get("required_case_count"), int)
        and not isinstance(reliability.get("required_case_count"), bool)
        else "",
        f"{reliability['observed_case_count']} observed"
        if isinstance(reliability.get("observed_case_count"), int)
        and not isinstance(reliability.get("observed_case_count"), bool)
        else "",
    ]
    coverage = ", ".join(part for part in coverage_parts if part)
    if coverage:
        print_key_value("Reliability coverage", coverage)
    _print_string_list_line("Reliability uncovered", reliability.get("uncovered_cases"))


def _print_provider_e2e_suite(provider_e2e_suite: Any) -> None:
    """Print provider e2e suite run diagnostics."""
    if not isinstance(provider_e2e_suite, dict):
        return
    status = provider_e2e_suite.get("status")
    if isinstance(status, str) and status:
        print_key_value("Provider e2e suite", status)
    runs = provider_e2e_suite.get("runs")
    if not isinstance(runs, list):
        return
    run_parts = [
        f"{run.get('runtime_mode', 'unknown')}={run.get('status', 'unknown')}"
        for run in runs
        if isinstance(run, dict)
    ]
    if run_parts:
        print_key_value("Provider e2e runs", ", ".join(run_parts))


def _print_provider_run_history(provider_run_history: Any) -> None:
    """Print persisted provider run history diagnostics."""
    if not isinstance(provider_run_history, dict):
        return
    status = provider_run_history.get("status")
    if isinstance(status, str) and status:
        print_key_value("Provider run history", status)
    total_runs = provider_run_history.get("total_runs")
    passed_runs = provider_run_history.get("passed_runs")
    failed_runs = provider_run_history.get("failed_runs")
    run_parts = [
        f"{total_runs} total"
        if isinstance(total_runs, int) and not isinstance(total_runs, bool)
        else "",
        f"{passed_runs} passed"
        if isinstance(passed_runs, int) and not isinstance(passed_runs, bool)
        else "",
        f"{failed_runs} failed"
        if isinstance(failed_runs, int) and not isinstance(failed_runs, bool)
        else "",
    ]
    runs = ", ".join(part for part in run_parts if part)
    if runs:
        print_key_value("Provider history runs", runs)
    trend = provider_run_history.get("trend")
    recent_window = provider_run_history.get("recent_window")
    recent_passed_runs = provider_run_history.get("recent_passed_runs")
    recent_failed_runs = provider_run_history.get("recent_failed_runs")
    trend_parts = [
        str(trend) if isinstance(trend, str) and trend else "",
        f"{recent_window} run window"
        if isinstance(recent_window, int) and not isinstance(recent_window, bool)
        else "",
        (f"{recent_passed_runs} passed, {recent_failed_runs} failed")
        if isinstance(recent_passed_runs, int)
        and not isinstance(recent_passed_runs, bool)
        and isinstance(recent_failed_runs, int)
        and not isinstance(recent_failed_runs, bool)
        else "",
    ]
    trend_summary = ", ".join(part for part in trend_parts if part)
    if trend_summary:
        print_key_value("Provider history trend", trend_summary)
    pass_rate_percent = provider_run_history.get("pass_rate_percent")
    if isinstance(pass_rate_percent, int) and not isinstance(pass_rate_percent, bool):
        print_key_value("Provider history pass rate", f"{pass_rate_percent}%")
    recent_pass_rate_percent = provider_run_history.get("recent_pass_rate_percent")
    if isinstance(recent_pass_rate_percent, int) and not isinstance(
        recent_pass_rate_percent,
        bool,
    ):
        print_key_value(
            "Provider history recent pass rate",
            f"{recent_pass_rate_percent}%",
        )
    _print_provider_history_case_coverage(
        provider_run_history,
        label="Provider history e2e case pass rate",
        percent_key="e2e_case_pass_rate_percent",
        passed_key="e2e_passed_case_count",
        required_key="e2e_case_count",
    )
    _print_provider_history_case_coverage(
        provider_run_history,
        label="Provider history reliability case pass rate",
        percent_key="reliability_case_pass_rate_percent",
        passed_key="reliability_passed_case_count",
        required_key="reliability_required_case_count",
    )
    live_fault_coverage_percent = provider_run_history.get(
        "live_fault_probe_case_coverage_percent"
    )
    observed_live_fault_cases = provider_run_history.get(
        "observed_live_fault_case_count"
    )
    required_live_fault_cases = provider_run_history.get(
        "required_live_fault_case_count"
    )
    if (
        isinstance(live_fault_coverage_percent, int)
        and not isinstance(live_fault_coverage_percent, bool)
        and isinstance(observed_live_fault_cases, int)
        and not isinstance(observed_live_fault_cases, bool)
        and isinstance(required_live_fault_cases, int)
        and not isinstance(required_live_fault_cases, bool)
    ):
        print_key_value(
            "Provider history live-fault coverage",
            f"{live_fault_coverage_percent}% "
            f"({observed_live_fault_cases}/{required_live_fault_cases})",
        )
    cost_status = provider_run_history.get("cost_status")
    cost_run_label = "estimated runs" if cost_status == "estimated" else "recorded runs"
    cost_parts = [
        f"{provider_run_history['cost_total_formatted']} total"
        if isinstance(provider_run_history.get("cost_total_formatted"), str)
        and provider_run_history.get("cost_total_formatted")
        else "",
        f"{provider_run_history['cost_last_formatted']} latest"
        if isinstance(provider_run_history.get("cost_last_formatted"), str)
        and provider_run_history.get("cost_last_formatted")
        else "",
        f"{provider_run_history['cost_observed_run_count']} {cost_run_label}"
        if isinstance(provider_run_history.get("cost_observed_run_count"), int)
        and not isinstance(provider_run_history.get("cost_observed_run_count"), bool)
        else "",
        f"{provider_run_history['cost_total_input_tokens']} input"
        if isinstance(provider_run_history.get("cost_total_input_tokens"), int)
        and not isinstance(provider_run_history.get("cost_total_input_tokens"), bool)
        else "",
        f"{provider_run_history['cost_total_output_tokens']} output"
        if isinstance(provider_run_history.get("cost_total_output_tokens"), int)
        and not isinstance(provider_run_history.get("cost_total_output_tokens"), bool)
        else "",
        str(provider_run_history.get("cost_pricing_model"))
        if isinstance(provider_run_history.get("cost_pricing_model"), str)
        and provider_run_history.get("cost_pricing_model")
        else "",
    ]
    cost_summary = ", ".join(part for part in cost_parts if part)
    if cost_summary:
        print_key_value("Provider history cost", cost_summary)
    recent_runs = provider_run_history.get("recent_runs")
    recent_run_parts = (
        [
            _provider_run_history_recent_run_summary(run)
            for run in recent_runs
            if isinstance(run, dict)
        ]
        if isinstance(recent_runs, list)
        else []
    )
    recent_run_summary = " -> ".join(part for part in recent_run_parts if part)
    if recent_run_summary:
        print_key_value("Provider history recent runs", recent_run_summary)
    path = provider_run_history.get("path")
    if isinstance(path, str) and path:
        print_key_value("Provider history artifact", path)


def _print_provider_history_case_coverage(
    provider_run_history: dict[str, Any],
    *,
    label: str,
    percent_key: str,
    passed_key: str,
    required_key: str,
) -> None:
    """Print a provider history case-rate metric when all fields exist."""
    percent = provider_run_history.get(percent_key)
    passed = provider_run_history.get(passed_key)
    required = provider_run_history.get(required_key)
    if (
        isinstance(percent, int)
        and not isinstance(percent, bool)
        and isinstance(passed, int)
        and not isinstance(passed, bool)
        and isinstance(required, int)
        and not isinstance(required, bool)
    ):
        print_key_value(label, f"{percent}% ({passed}/{required})")


def _provider_run_history_recent_run_summary(run: dict[str, Any]) -> str:
    """Return one compact provider history run summary for CLI output."""
    timestamp = run.get("timestamp")
    prefix = f"{timestamp}: " if isinstance(timestamp, str) and timestamp else ""
    parts = [
        str(run.get(field))
        for field in (
            "status",
            "runtime_mode",
            "model",
            "reliability_status",
            "provider_e2e_status",
            "live_fault_probe_status",
        )
        if isinstance(run.get(field), str) and run.get(field)
    ]
    return f"{prefix}{' / '.join(parts)}" if parts else prefix.rstrip(": ")


def _print_provider_autonomous_readiness(readiness: Any) -> None:
    """Print the aggregate direct-provider autonomous readiness scorecard."""
    if not isinstance(readiness, dict):
        return
    status = readiness.get("status")
    if isinstance(status, str) and status:
        print_key_value("Provider autonomous readiness", status)
    recommendation = readiness.get("recommendation")
    if isinstance(recommendation, str) and recommendation:
        print_key_value("Autonomous recommendation", recommendation)
    _print_string_list_line(
        "Autonomous recommendation reasons",
        readiness.get("recommendation_reasons"),
    )
    _print_string_list_line("Autonomous blockers", readiness.get("blockers"))
    _print_string_list_line("Autonomous warnings", readiness.get("warnings"))
    _print_string_list_line(
        "Autonomous missing requirements",
        readiness.get("missing_requirements"),
    )
    _print_string_list_line("Autonomous evidence", readiness.get("evidence"))
    _print_string_list_line("Autonomous next actions", readiness.get("next_actions"))


def _print_provider_execution_diagnostics(execution: Any) -> None:
    """Print validated generic_edit execution diagnostics."""
    if not isinstance(execution, dict):
        return
    print_key_value("Execution loop", str(execution.get("loop", "unknown")))
    _print_tool_loop_contract(execution.get("tool_loop_contract"))
    print_key_value(
        "Execution actions",
        str(execution.get("action_count", 0)),
    )
    print_key_value(
        "Native tool fallbacks",
        str(execution.get("native_tool_fallback_count", 0)),
    )
    _print_first_native_tool_fallback(execution.get("native_tool_fallbacks"))
    _print_provider_resume_policy(execution.get("resume_policy"))
    _print_transaction_batch_contract(execution.get("transaction_batch_contract"))


def _print_tool_loop_contract(contract: Any) -> None:
    """Print the compact provider tool-loop contract line."""
    if not isinstance(contract, dict):
        return
    contract_parts = [
        str(contract[field])
        for field in (
            "status",
            "tool_call_support",
            "tool_result_support",
            "recovery_status",
        )
        if isinstance(contract.get(field), str) and str(contract[field])
    ]
    if contract_parts:
        print_key_value(
            "Tool-loop contract",
            ", ".join(contract_parts),
        )


def _print_first_native_tool_fallback(fallbacks: Any) -> None:
    """Print the first native-tool fallback reason for quick CLI diagnosis."""
    if not isinstance(fallbacks, list) or not fallbacks:
        return
    first_fallback = fallbacks[0]
    if isinstance(first_fallback, dict):
        print_key_value(
            "Native fallback reason",
            str(first_fallback.get("reason", "unknown")),
        )


def _print_provider_resume_policy(resume_policy: Any) -> None:
    """Print the generic_edit resume policy summary."""
    if not isinstance(resume_policy, dict):
        return
    print_key_value(
        "Resume policy",
        str(resume_policy.get("status", "unknown")),
    )
    _print_string_list_line(
        "Resume required actions",
        resume_policy.get("required_resolution_action_kinds"),
    )
    _print_string_list_line(
        "Resume required artifacts",
        resume_policy.get("required_artifacts"),
    )
    _print_string_list_line(
        "Resume unresolved failures",
        resume_policy.get("unresolved_partial_failure_ids"),
    )
    _print_string_list_line(
        "Resume unresolved groups",
        resume_policy.get("unresolved_transaction_group_ids"),
    )
    _print_string_list_line(
        "Resume open batches",
        resume_policy.get("open_transaction_batch_ids"),
    )


def _print_transaction_batch_contract(contract: Any) -> None:
    """Print batch-boundary diagnostics for provider smoke output."""
    if not isinstance(contract, dict):
        return
    contract_parts = [
        str(contract[field])
        for field in ("status", "batch_boundary_guard")
        if isinstance(contract.get(field), str) and str(contract[field])
    ]
    if contract_parts:
        print_key_value(
            "Batch contract",
            ", ".join(contract_parts),
        )
    _print_string_list_line(
        "Batch boundary reasons",
        contract.get("boundary_error_reasons"),
    )
    preferred_strategy = contract.get("boundary_preferred_strategy")
    if isinstance(preferred_strategy, str) and preferred_strategy:
        print_key_value("Batch preferred strategy", preferred_strategy)
    _print_string_list_line(
        "Batch required actions",
        contract.get("boundary_required_action_kinds"),
    )
    _print_string_list_line(
        "Batch resolution strategies",
        contract.get("boundary_resolution_strategies"),
    )
    _print_string_list_line(
        "Batch lifecycle actions",
        contract.get("batch_lifecycle_actions"),
    )
    _print_string_list_line(
        "Batch lifecycle statuses",
        contract.get("batch_lifecycle_statuses"),
    )
    _print_string_list_line(
        "Committed mutation snapshots",
        contract.get("committed_mutation_snapshot_ids"),
    )
    _print_string_list_line(
        "Batch commit operations",
        contract.get("commit_operation_ids"),
    )
    _print_string_list_line(
        "Open transaction batches",
        contract.get("open_transaction_batch_ids"),
    )


def _print_string_list_line(label: str, value: Any) -> None:
    """Print a comma-separated list value when present."""
    if isinstance(value, list) and value:
        print_key_value(label, ", ".join(str(item) for item in value))


def handle_provider_smoke_command(
    *,
    project_dir: Path,
    model: str | None,
    prompt: str | None,
    timeout_seconds: float = DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS,
    runtime_mode: str | None = None,
    output_json: bool = False,
) -> ProviderSmokeResult:
    """Run and print one provider smoke check."""
    result = asyncio.run(
        run_provider_smoke_check(
            project_dir=project_dir,
            model=model,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            runtime_mode=runtime_mode,
        )
    )

    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print_provider_smoke_result(result)

    return result
