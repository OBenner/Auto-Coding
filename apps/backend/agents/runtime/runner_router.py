"""Runtime-aware CLI runner routing policy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from core.providers.config import ProviderConfig

from .cli_profiles import CliRunnerSelection, select_cli_runner_profiles
from .modes import RuntimeMode, normalize_runtime_mode

RUNNER_ROUTER_ENV = "AUTO_CODE_CLI_RUNNER_ROUTER"
_TRUTHY = {"1", "true", "yes", "on"}
RunnerRouteStatus = Literal["native", "disabled", "routed", "unavailable"]


@dataclass(frozen=True)
class RuntimeRunnerRoute:
    """Decision for switching a provider request to a CLI-backed runtime."""

    requested_provider: str
    selected_provider: str
    requested_mode: RuntimeMode
    selected_mode: RuntimeMode
    status: RunnerRouteStatus
    route_applied: bool
    reason: str
    runner_id: str | None = None
    runner_selection: CliRunnerSelection | None = None

    def to_dict(self, *, include_detection: bool = False) -> dict[str, Any]:
        """Serialize the route for logs, artifacts, and settings diagnostics."""
        payload: dict[str, Any] = {
            "requested_provider": self.requested_provider,
            "selected_provider": self.selected_provider,
            "requested_mode": self.requested_mode,
            "selected_mode": self.selected_mode,
            "status": self.status,
            "route_applied": self.route_applied,
            "reason": self.reason,
            "runner_id": self.runner_id,
        }
        if self.runner_selection is not None:
            payload["runner_selection"] = self.runner_selection.to_dict(
                include_detection=include_detection,
            )
        return payload


def runtime_runner_router_enabled() -> bool:
    """Return true when CLI runner routing is explicitly enabled."""
    return os.environ.get(RUNNER_ROUTER_ENV, "").strip().lower() in _TRUTHY


def resolve_runtime_runner_route(
    *,
    provider_config: ProviderConfig,
    provider_name: str,
    requested_mode: str | None,
    phase: str,
    allow_router: bool | None = None,
) -> RuntimeRunnerRoute:
    """Resolve whether a request should move from a direct provider to a CLI runner."""
    del phase

    requested_provider = provider_name.lower()
    requested = normalize_runtime_mode(requested_mode)
    allow = runtime_runner_router_enabled() if allow_router is None else allow_router
    runner_selection = select_cli_runner_profiles(runtime_mode=requested)

    if requested_provider == "claude":
        return RuntimeRunnerRoute(
            requested_provider=requested_provider,
            selected_provider=requested_provider,
            requested_mode=requested,
            selected_mode=requested,
            status="native",
            route_applied=False,
            reason="Claude uses the native Claude Agent SDK runtime path.",
            runner_id="claude_agent_sdk" if requested == "full_autonomous" else None,
            runner_selection=runner_selection,
        )

    if requested_provider == "codex":
        return RuntimeRunnerRoute(
            requested_provider=requested_provider,
            selected_provider=requested_provider,
            requested_mode=requested,
            selected_mode=requested,
            status="native",
            route_applied=False,
            reason="Codex provider already uses the Codex CLI runtime path.",
            runner_id="codex_cli" if requested == "full_autonomous" else None,
            runner_selection=runner_selection,
        )

    if requested != "full_autonomous":
        return RuntimeRunnerRoute(
            requested_provider=requested_provider,
            selected_provider=requested_provider,
            requested_mode=requested,
            selected_mode=requested,
            status="native",
            route_applied=False,
            reason="Limited runtimes stay on the configured direct provider.",
            runner_selection=runner_selection,
        )

    if not allow:
        return RuntimeRunnerRoute(
            requested_provider=requested_provider,
            selected_provider=requested_provider,
            requested_mode=requested,
            selected_mode=requested,
            status="disabled",
            route_applied=False,
            reason=f"{RUNNER_ROUTER_ENV} is disabled.",
            runner_selection=runner_selection,
        )

    if provider_config.is_provider_available("codex"):
        return RuntimeRunnerRoute(
            requested_provider=requested_provider,
            selected_provider="codex",
            requested_mode=requested,
            selected_mode="full_autonomous",
            status="routed",
            route_applied=True,
            reason=(
                "Direct provider cannot supply full_autonomous runtime; routing "
                "to the wired Codex CLI runner."
            ),
            runner_id="codex_cli",
            runner_selection=runner_selection,
        )

    return RuntimeRunnerRoute(
        requested_provider=requested_provider,
        selected_provider=requested_provider,
        requested_mode=requested,
        selected_mode=requested,
        status="unavailable",
        route_applied=False,
        reason=(
            "No wired full_autonomous CLI runner is available; configure Codex CLI "
            "or use a limited runtime mode."
        ),
        runner_selection=runner_selection,
    )
