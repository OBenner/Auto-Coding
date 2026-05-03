"""CLI command for opt-in provider smoke checks."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agents.runtime import RuntimeRequirements, run_runtime_session
from agents.runtime.adapters.completion import CompletionRuntimeSession
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
from core.providers.factory import create_engine_provider
from task_logger import LogPhase
from ui import print_key_value, print_status

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_SMOKE_PROMPT = (
    "Reply with one short sentence confirming the provider smoke check works."
)
DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS = 30.0


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


async def run_provider_smoke_check(
    *,
    project_dir: Path,
    model: str | None = None,
    prompt: str | None = None,
    timeout_seconds: float = DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS,
) -> ProviderSmokeResult:
    """Run a real text-only smoke check against the configured provider."""
    provider_config = ProviderConfig.from_env(agent_type="analysis")
    provider_name = provider_config.provider
    resolved_model = model or provider_config.get_model_for_provider()

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
        )

    session_config = SessionConfig(
        name="provider-smoke-session",
        model=model,
        system_prompt="You are running a brief Auto Code provider smoke check.",
        extra={"agent_type": "analysis"},
    )

    try:
        if provider.name == "claude":
            with tempfile.TemporaryDirectory(
                prefix="auto-code-provider-smoke-"
            ) as temp_dir:
                spec_dir = Path(temp_dir) / "spec"
                spec_dir.mkdir(parents=True, exist_ok=True)
                provider.create_session(
                    session_config,
                    project_dir=project_dir,
                    spec_dir=spec_dir,
                    agent_type="planner",
                )
                return await _complete_provider_smoke(
                    provider=provider,
                    prompt=prompt,
                    timeout_seconds=timeout_seconds,
                    model=resolved_model,
                )

        provider.create_session(session_config)
        return await _complete_provider_smoke(
            provider=provider,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            model=resolved_model,
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
        )


async def _complete_provider_smoke(
    *,
    provider: Any,
    prompt: str | None,
    timeout_seconds: float,
    model: str | None,
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
        )

    return ProviderSmokeResult(
        success=True,
        provider=provider.name,
        model=model,
        runtime_mode="analysis_only",
        message="Provider smoke check passed",
        response_excerpt=_response_excerpt(response_text),
    )


def handle_provider_smoke_command(
    *,
    project_dir: Path,
    model: str | None,
    prompt: str | None,
    timeout_seconds: float = DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS,
    output_json: bool = False,
) -> ProviderSmokeResult:
    """Run and print one provider smoke check."""
    result = asyncio.run(
        run_provider_smoke_check(
            project_dir=project_dir,
            model=model,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
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
        if result.response_excerpt:
            print_key_value("Response", result.response_excerpt)
        if result.error_details:
            print_key_value("Details", result.error_details)

    return result
