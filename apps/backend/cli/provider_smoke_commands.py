"""CLI command for opt-in provider smoke checks."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agents.runtime import (
    RuntimeRequirements,
    create_runtime_session,
    get_runtime_mode,
    normalize_runtime_mode,
    run_runtime_session,
)
from agents.runtime.adapters.completion import CompletionRuntimeSession
from agents.runtime.fallback import capabilities_for_runtime_mode
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
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
DEFAULT_PROVIDER_MINI_PIPELINE_TASK = (
    "Implement slugify(value: str) in string_tools.py."
)
DEFAULT_PROVIDER_MINI_PIPELINE_TEST_COMMAND = "python -m unittest -q"
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
PROVIDER_SMOKE_RUNTIME_MODES = ("analysis_only", "generic_edit", "mini_pipeline")


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
    diagnostics["transaction_batch_contract"] = (
        _generic_edit_transaction_batch_contract(payload)
    )
    diagnostics["tool_loop_contract"] = _generic_edit_tool_loop_contract(
        payload=payload,
        native_tool_fallbacks=native_tool_fallbacks,
        resume_policy=resume_policy,
    )
    return diagnostics


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


def _generic_edit_transaction_batch_contract(payload: dict[str, Any]) -> dict[str, Any]:
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
    if isinstance(transaction_batches, list):
        for batch in transaction_batches:
            if not isinstance(batch, dict):
                continue
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
            if not (
                isinstance(batch_error_count, int)
                and not isinstance(batch_error_count, bool)
            ):
                boundary_error_count += len(batch_error_reasons)
            boundary_error_reasons.extend(batch_error_reasons)

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
    return contract


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
    return {
        **runtime_diagnostics,
        "provider_contract_health": _provider_contract_health(
            runtime_diagnostics,
            success=success,
            error_details=error_details,
        ),
    }


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
    if status == "failed":
        health["reason"] = str(mini_pipeline.get("reason") or "mini_pipeline_failed")
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
    if runtime_mode == "mini_pipeline":
        return RuntimeRequirements(
            mode="mini_pipeline",
            required=RuntimeRequirements.generic_edit().required,
        )
    if runtime_mode == "generic_edit":
        return RuntimeRequirements.generic_edit()
    return RuntimeRequirements.text_only(mode="analysis_only")


def _provider_smoke_scope(runtime_mode: str) -> str:
    if runtime_mode == "mini_pipeline":
        return "mini_task_pipeline"
    if runtime_mode == "generic_edit":
        return "generic_edit_tool_loop"
    return "text_completion_only"


def _provider_smoke_note(runtime_mode: str) -> str:
    if runtime_mode == "mini_pipeline":
        return (
            "Provider smoke runs a temporary planner/coder/reviewer mini task. "
            "It validates the local edit loop and one unit-test command, but it "
            "does not prove full production autonomy for arbitrary repositories."
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
    if runtime_mode == "mini_pipeline":
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
        return ProviderSmokeResult(
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

    runtime_diagnostics = build_provider_smoke_runtime_diagnostics(
        provider_name=provider.name,
        requested_runtime_mode=runtime_mode,
        validated_runtime_mode=validated_runtime_mode,
    )
    validation_errors = _provider_validation_errors(provider)
    if validation_errors:
        error_details = "; ".join(validation_errors)
        return ProviderSmokeResult(
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

    session_config = SessionConfig(
        name="provider-smoke-session",
        model=model,
        system_prompt="You are running a brief Auto Code provider smoke check.",
        extra={"agent_type": "analysis"},
    )

    try:
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
        return ProviderSmokeResult(
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
        )


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
