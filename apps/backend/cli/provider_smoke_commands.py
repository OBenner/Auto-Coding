"""CLI command for opt-in provider smoke checks."""

from __future__ import annotations

import asyncio
import json
import logging
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
DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS = 30.0
PROVIDER_SMOKE_RUNTIME_MODES = ("analysis_only", "generic_edit")


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

    tool_counts = payload.get("tool_counts")
    normalized_tool_counts = {
        str(tool): count
        for tool, count in (
            tool_counts.items() if isinstance(tool_counts, dict) else ()
        )
        if isinstance(count, int) and not isinstance(count, bool)
    }
    return {
        "status": str(payload.get("status") or "unknown"),
        "stop_reason": str(payload.get("stop_reason") or "unknown"),
        "loop": str(payload.get("loop") or "unknown"),
        "action_count": _int_payload_value(payload, "action_count"),
        "failed_action_count": _int_payload_value(payload, "failed_action_count"),
        "native_tool_fallback_count": _int_payload_value(
            payload,
            "native_tool_fallback_count",
        ),
        "tool_counts": normalized_tool_counts,
    }


def _int_payload_value(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


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
    mode = normalize_runtime_mode(value)
    if mode not in PROVIDER_SMOKE_RUNTIME_MODES:
        allowed = ", ".join(PROVIDER_SMOKE_RUNTIME_MODES)
        raise ValueError(
            f"Invalid provider smoke runtime '{value}'. Must be one of: {allowed}"
        )
    return mode


def _provider_smoke_requirements(runtime_mode: str) -> RuntimeRequirements:
    if runtime_mode == "generic_edit":
        return RuntimeRequirements.generic_edit()
    return RuntimeRequirements.text_only(mode="analysis_only")


def _provider_smoke_scope(runtime_mode: str) -> str:
    if runtime_mode == "generic_edit":
        return "generic_edit_tool_loop"
    return "text_completion_only"


def _provider_smoke_note(runtime_mode: str) -> str:
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
    requested_capabilities = capabilities_for_runtime_mode(
        provider_name,
        requested_mode,
    )
    validated_capabilities = capabilities_for_runtime_mode(
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
            runtime_diagnostics=runtime_diagnostics,
        )

    runtime_diagnostics = build_provider_smoke_runtime_diagnostics(
        provider_name=provider.name,
        requested_runtime_mode=runtime_mode,
        validated_runtime_mode=validated_runtime_mode,
    )
    validation_errors = _provider_validation_errors(provider)
    if validation_errors:
        return ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=resolved_model,
            runtime_mode="analysis_only",
            message="Provider configuration is incomplete",
            error_details="; ".join(validation_errors),
            runtime_diagnostics=runtime_diagnostics,
        )

    session_config = SessionConfig(
        name="provider-smoke-session",
        model=model,
        system_prompt="You are running a brief Auto Code provider smoke check.",
        extra={"agent_type": "analysis"},
    )

    try:
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
            runtime_diagnostics=runtime_diagnostics,
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
            runtime_diagnostics=runtime_diagnostics,
        )

    return ProviderSmokeResult(
        success=True,
        provider=provider.name,
        model=model,
        runtime_mode="analysis_only",
        message="Provider smoke check passed",
        response_excerpt=_response_excerpt(response_text),
        runtime_diagnostics=runtime_diagnostics,
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
            return ProviderSmokeResult(
                success=False,
                provider=provider.name,
                model=model,
                runtime_mode="generic_edit",
                message="Provider generic_edit smoke did not update the test file",
                response_excerpt=_response_excerpt(result.response_text),
                error_details=(
                    "Expected provider-smoke.txt to contain "
                    f"{DEFAULT_PROVIDER_GENERIC_EDIT_SMOKE_CONTENT!r}; got "
                    f"{smoke_content!r}"
                ),
                runtime_diagnostics=runtime_diagnostics,
            )

    response_text = result.response_text.strip()
    if not response_text:
        return ProviderSmokeResult(
            success=False,
            provider=provider.name,
            model=model,
            runtime_mode="generic_edit",
            message="Provider generic_edit smoke returned an empty response",
            runtime_diagnostics=runtime_diagnostics,
        )

    return ProviderSmokeResult(
        success=True,
        provider=provider.name,
        model=model,
        runtime_mode="generic_edit",
        message="Provider generic_edit smoke passed",
        response_excerpt=_response_excerpt(response_text),
        runtime_diagnostics=runtime_diagnostics,
    )


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
        print_status(
            result.message,
            "success" if result.success else "error",
        )
        print_key_value("Provider", result.provider)
        print_key_value("Model", result.model or "default")
        print_key_value("Runtime mode", result.runtime_mode)
        if result.runtime_diagnostics:
            print_key_value(
                "Smoke scope",
                str(result.runtime_diagnostics.get("smoke_scope", "unknown")),
            )
            execution = result.runtime_diagnostics.get("validated_runtime_execution")
            if isinstance(execution, dict):
                print_key_value("Execution loop", str(execution.get("loop", "unknown")))
                print_key_value(
                    "Execution actions",
                    str(execution.get("action_count", 0)),
                )
                print_key_value(
                    "Native tool fallbacks",
                    str(execution.get("native_tool_fallback_count", 0)),
                )
        if result.response_excerpt:
            print_key_value("Response", result.response_excerpt)
        if result.error_details:
            print_key_value("Details", result.error_details)

    return result
