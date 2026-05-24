"""Per-server execution smoke for external MCP servers.

Phase 1.1.d of ``docs/roadmap/non-claude-provider-autonomy.md``: the
existing ``external_mcp_smoke`` validates the ``tools/list`` contract
(adapter tool names match what the live server returns). This module
extends that with a ``tools/call`` smoke against the first
non-mutating tool the adapter exposes, so the provider e2e suite has
positive evidence that a direct API provider can actually drive the
external MCP server, not just discover its catalog.

The smoke is intentionally narrow: it picks one safe, read-only tool
(``audit_level == "read"`` and ``mutating is False``), invokes it with
empty arguments, normalizes the result, and returns a structured
payload. Tools that require specific arguments are expected to surface
their requirement as a validation error rather than a connectivity or
schema failure; the smoke captures both outcomes so dashboards can tell
the difference between "server unreachable" and "server validates
input".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .mcp_bridge import (
    RuntimeExternalMcpAdapter,
    call_external_mcp_tool,
    classify_external_mcp_error,
    describe_external_mcp_server_health,
    discover_external_mcp_tools,
    external_mcp_adapter_for,
    normalize_mcp_server_name,
    normalize_mcp_tool_result,
)


@dataclass(frozen=True)
class McpExecutionSmokeResult:
    """Structured outcome of one external MCP execution smoke run."""

    server: str
    transport: str | None
    status: str
    ok: bool
    reason: str
    adapter_tools: tuple[str, ...] = field(default_factory=tuple)
    server_tools: tuple[str, ...] = field(default_factory=tuple)
    sample_tool: str | None = None
    sample_tool_audit_level: str | None = None
    normalized_result: dict[str, Any] | None = None
    failure_stage: str | None = None
    failure_kind: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe payload for diagnostics."""
        return asdict(self)


def _safe_sample_tool(
    adapter: RuntimeExternalMcpAdapter,
) -> tuple[str | None, str | None]:
    """Pick the first read-only, non-mutating tool the adapter declares.

    Returns ``(tool_name, audit_level)`` or ``(None, None)`` when no
    safe tool is registered.
    """
    for definition in adapter.tool_definitions:
        policy = definition.policy
        if policy is None:
            continue
        if getattr(policy, "mutating", True):
            continue
        audit_level = str(getattr(policy, "audit_level", "") or "")
        if audit_level == "read":
            return definition.name, audit_level
    return None, None


async def mcp_execution_smoke(
    *,
    server: str,
    project_dir: Path,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> McpExecutionSmokeResult:
    """Run a tools/list + read-only tools/call smoke for one external MCP server.

    The result is JSON-safe and can be embedded under
    ``runtime_diagnostics["mcp_execution_smoke"]`` so direct providers
    have positive end-to-end evidence rather than only schema contract
    evidence.
    """
    server_name = normalize_mcp_server_name(server)
    health = describe_external_mcp_server_health(
        server_name,
        project_mcp_config=project_mcp_config,
        environment=environment,
    )
    adapter = external_mcp_adapter_for(
        server_name,
        project_mcp_config=project_mcp_config,
    )
    adapter_tools = adapter.tool_names if adapter else ()

    if not health.ready_to_connect or not health.execution_supported:
        return McpExecutionSmokeResult(
            server=server_name,
            transport=health.transport,
            status="skipped",
            ok=False,
            reason=health.reason,
            adapter_tools=adapter_tools,
        )
    if adapter is None:
        return McpExecutionSmokeResult(
            server=server_name,
            transport=health.transport,
            status="skipped",
            ok=False,
            reason="No external MCP adapter is registered for this server.",
        )

    try:
        list_payload = await discover_external_mcp_tools(
            health=health,
            project_dir=project_dir,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
    except Exception as exc:
        failure = classify_external_mcp_error(exc, stage="tools_list")
        return McpExecutionSmokeResult(
            server=server_name,
            transport=health.transport,
            status="tools_list_failed",
            ok=False,
            reason="External MCP tools/list failed.",
            adapter_tools=adapter_tools,
            error=str(exc),
            failure_stage=failure.get("failure_stage"),
            failure_kind=failure.get("failure_kind"),
        )

    server_tools = tuple(_extract_tool_names(list_payload))
    sample_tool, sample_audit = _safe_sample_tool(adapter)
    if sample_tool is None:
        return McpExecutionSmokeResult(
            server=server_name,
            transport=health.transport,
            status="no_safe_tool",
            ok=False,
            reason=(
                "Adapter does not declare a non-mutating read tool; "
                "execution smoke needs a safe tool to invoke."
            ),
            adapter_tools=adapter_tools,
            server_tools=server_tools,
        )

    try:
        raw_result = await call_external_mcp_tool(
            health=health,
            tool_name=sample_tool,
            arguments={},
            project_dir=project_dir,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
    except Exception as exc:
        failure = classify_external_mcp_error(exc, stage="tools_call")
        return McpExecutionSmokeResult(
            server=server_name,
            transport=health.transport,
            status="tools_call_failed",
            ok=False,
            reason="External MCP tools/call failed.",
            adapter_tools=adapter_tools,
            server_tools=server_tools,
            sample_tool=sample_tool,
            sample_tool_audit_level=sample_audit,
            error=str(exc),
            failure_stage=failure.get("failure_stage"),
            failure_kind=failure.get("failure_kind"),
        )

    normalized = normalize_mcp_tool_result(raw_result)
    is_error = bool(normalized.get("is_error"))
    return McpExecutionSmokeResult(
        server=server_name,
        transport=health.transport,
        status="tool_validation_error" if is_error else "ok",
        ok=not is_error,
        reason=(
            "External MCP server validated input and reported an error "
            "for empty arguments; connectivity and schema layer are healthy."
            if is_error
            else (
                "External MCP server executed the sample tool end-to-end "
                "through the provider-neutral bridge."
            )
        ),
        adapter_tools=adapter_tools,
        server_tools=server_tools,
        sample_tool=sample_tool,
        sample_tool_audit_level=sample_audit,
        normalized_result=normalized,
    )


def _extract_tool_names(payload: Any) -> list[str]:
    """Pull tool names from a ``tools/list`` MCP response."""
    if not isinstance(payload, dict):
        return []
    tools = payload.get("tools")
    if not isinstance(tools, list):
        return []
    names: list[str] = []
    for entry in tools:
        if isinstance(entry, dict):
            name = entry.get("name")
            if isinstance(name, str) and name:
                names.append(name)
    return names
