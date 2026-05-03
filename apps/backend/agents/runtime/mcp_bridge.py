"""Provider-neutral bridge for local Auto Code MCP tools.

This is intentionally narrower than full MCP parity. It exposes Auto Code's
in-process ``auto-claude`` tools to limited/direct runtimes without starting a
Claude SDK agent loop. External MCP servers still require a native runtime.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from agents.tools_pkg.models import get_agent_config
from agents.tools_pkg.registry import create_all_tools, is_tools_available

from .capabilities import RuntimeCapabilities
from .local_actions import ToolActionResult, action_tool, safe_action_for_trace

MCP_AUTO_CLAUDE_PREFIX = "mcp__auto-claude__"
LOCAL_BRIDGE_SERVER = "auto-claude"
MCP_BRIDGE_AUDIT_FILENAME = "mcp_bridge_audit.jsonl"
McpSupportStrategy = Literal["native", "local_bridge", "unavailable"]
McpAuditLevel = Literal["read", "write", "command", "analysis"]
MCP_SERVER_CATALOG: dict[str, dict[str, Any]] = {
    LOCAL_BRIDGE_SERVER: {
        "display_name": "Auto Code local tools",
        "bridgeable": True,
        "notes": "In-process Auto Code tools can be exposed through local actions.",
    },
    "context7": {
        "display_name": "Context7",
        "bridgeable": False,
        "notes": "External documentation MCP server; requires native MCP runtime.",
    },
    "graphiti": {
        "display_name": "Graphiti",
        "bridgeable": False,
        "notes": "External memory MCP server; requires native MCP runtime.",
    },
    "linear": {
        "display_name": "Linear",
        "bridgeable": False,
        "notes": "External Linear MCP server; requires native MCP runtime.",
    },
    "browser": {
        "display_name": "Browser automation",
        "bridgeable": False,
        "notes": "External browser automation MCP server; requires native MCP runtime.",
    },
    "electron": {
        "display_name": "Electron",
        "bridgeable": False,
        "notes": "External Electron automation MCP server; requires native MCP runtime.",
    },
    "puppeteer": {
        "display_name": "Puppeteer",
        "bridgeable": False,
        "notes": "External browser automation MCP server; requires native MCP runtime.",
    },
}


@dataclass(frozen=True)
class RuntimeMcpToolPolicy:
    """Permission and audit policy for one bridged MCP tool."""

    permission: str
    audit_level: McpAuditLevel
    mutating: bool = False
    audit_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize tool policy metadata for reports and artifacts."""
        return {
            "permission": self.permission,
            "audit_level": self.audit_level,
            "mutating": self.mutating,
            "audit_required": self.audit_required,
        }


@dataclass(frozen=True)
class RuntimeMcpSupport:
    """Effective MCP support for one runtime surface."""

    provider_name: str
    runtime_name: str
    strategy: McpSupportStrategy
    available: bool
    reason: str
    server: str | None = None
    tool_count: int = 0
    available_capabilities: tuple[str, ...] = ()
    requested_servers: tuple[str, ...] = ()
    available_servers: tuple[str, ...] = ()
    unavailable_servers: tuple[str, ...] = ()
    server_statuses: tuple[dict[str, Any], ...] = ()

    @property
    def bridge_plan(self) -> RuntimeMcpBridgePlan:
        """Return a normalized plan for UI, policy, and artifact consumers."""
        return build_mcp_bridge_plan(
            provider_name=self.provider_name,
            runtime_name=self.runtime_name,
            strategy=self.strategy,
            requested_servers=self.requested_servers,
            available_servers=self.available_servers,
            unavailable_servers=self.unavailable_servers,
            server_statuses=self.server_statuses,
            tool_count=self.tool_count,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize MCP support metadata for UI, CLI, and artifacts."""
        return {
            "provider": self.provider_name,
            "runtime": self.runtime_name,
            "strategy": self.strategy,
            "available": self.available,
            "reason": self.reason,
            "server": self.server,
            "tool_count": self.tool_count,
            "available_capabilities": list(self.available_capabilities),
            "requested_servers": list(self.requested_servers),
            "available_servers": list(self.available_servers),
            "unavailable_servers": list(self.unavailable_servers),
            "server_statuses": [
                dict(server_status) for server_status in self.server_statuses
            ],
            "bridge_plan": self.bridge_plan.to_dict(),
        }


@dataclass(frozen=True)
class RuntimeMcpBridgePlan:
    """Machine-readable MCP bridge plan for direct/runtime-limited providers."""

    provider_name: str
    runtime_name: str
    strategy: McpSupportStrategy
    status: str
    action_required: str
    recommended_runtime_path: str
    requested_servers: tuple[str, ...] = ()
    available_servers: tuple[str, ...] = ()
    unavailable_servers: tuple[str, ...] = ()
    native_required_servers: tuple[str, ...] = ()
    local_bridge_required_servers: tuple[str, ...] = ()
    unsupported_servers: tuple[str, ...] = ()
    bridged_servers: tuple[str, ...] = ()
    tool_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the bridge plan for artifacts, diagnostics, and UI."""
        return {
            "provider": self.provider_name,
            "runtime": self.runtime_name,
            "strategy": self.strategy,
            "status": self.status,
            "action_required": self.action_required,
            "recommended_runtime_path": self.recommended_runtime_path,
            "requested_servers": list(self.requested_servers),
            "available_servers": list(self.available_servers),
            "unavailable_servers": list(self.unavailable_servers),
            "native_required_servers": list(self.native_required_servers),
            "local_bridge_required_servers": list(self.local_bridge_required_servers),
            "unsupported_servers": list(self.unsupported_servers),
            "bridged_servers": list(self.bridged_servers),
            "tool_count": self.tool_count,
        }


@dataclass(frozen=True)
class RuntimeMcpToolSpec:
    """Provider-neutral schema for one bridged MCP tool."""

    server: str
    name: str
    exposed_name: str
    description: str
    parameters: dict[str, Any]
    policy: RuntimeMcpToolPolicy
    handler: Any

    def provider_tool_schema(self) -> dict[str, Any]:
        """Return a function/tool schema consumable by direct providers."""
        return {
            "name": self.exposed_name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def prompt_line(self) -> str:
        """Render a compact JSON-loop action example."""
        properties = self.parameters.get("properties", {})
        example = {
            "tool": self.exposed_name,
            **{key: example_value(schema) for key, schema in properties.items()},
        }
        return f"- {self.exposed_name}: {example}"

    def policy_metadata(self) -> dict[str, Any]:
        """Return audit/permission metadata for this bridged tool."""
        return {
            "server": self.server,
            "name": self.name,
            "exposed_name": self.exposed_name,
            **self.policy.to_dict(),
        }


class RuntimeMcpBridge:
    """Bridge local Auto Code MCP tools into generic runtimes."""

    def __init__(
        self,
        *,
        spec_dir: Path,
        project_dir: Path,
        allowed_tools: set[str],
        requested_servers: tuple[str, ...] = (),
    ):
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.allowed_tools = allowed_tools
        self.requested_servers = requested_servers
        self._tools = load_auto_claude_bridge_tools(
            spec_dir=spec_dir,
            project_dir=project_dir,
            allowed_tools=allowed_tools,
        )
        self._tools_by_name = {tool.exposed_name: tool for tool in self._tools} | {
            tool.name: tool for tool in self._tools
        }

    @classmethod
    def from_agent_session(
        cls,
        *,
        agent_session: Any,
        spec_dir: Path,
        project_dir: Path,
        agent_type: str | None = None,
    ) -> RuntimeMcpBridge | None:
        """Build a bridge when the agent config requests auto-claude MCP tools."""
        resolved_agent_type = str(
            agent_type or getattr(agent_session, "agent_type", "") or ""
        )
        configured_tools = getattr(agent_session, "auto_claude_tools", None)
        configured_servers = getattr(agent_session, "mcp_servers", None)
        if configured_tools is None and resolved_agent_type:
            config = get_agent_config(resolved_agent_type)
            configured_tools = config.get("auto_claude_tools", [])
            configured_servers = config.get("mcp_servers", [])
        requested_servers = normalize_mcp_server_names(configured_servers or ())
        if not configured_tools and not requested_servers:
            return None

        allowed_tools = {
            normalize_auto_claude_tool_name(str(tool_name))
            for tool_name in configured_tools or ()
        }
        bridge = cls(
            spec_dir=spec_dir,
            project_dir=project_dir,
            allowed_tools=allowed_tools,
            requested_servers=requested_servers,
        )
        return bridge if bridge.has_tools or bridge.requested_servers else None

    @property
    def has_tools(self) -> bool:
        return bool(self._tools)

    @property
    def available_servers(self) -> tuple[str, ...]:
        """Return MCP servers available through this local bridge."""
        return (LOCAL_BRIDGE_SERVER,) if self.has_tools else ()

    @property
    def unavailable_servers(self) -> tuple[str, ...]:
        """Return requested MCP servers that this local bridge cannot expose."""
        available = set(self.available_servers)
        return tuple(
            server for server in self.requested_servers if server not in available
        )

    def provider_tool_schemas(self) -> list[dict[str, Any]]:
        """Return provider-native schemas for bridged tools."""
        return [tool.provider_tool_schema() for tool in self._tools]

    def prompt_lines(self) -> list[str]:
        """Return prompt examples for JSON action runtimes."""
        return [tool.prompt_line() for tool in self._tools]

    def can_execute(self, action: dict[str, Any]) -> bool:
        """Return whether this bridge can execute the requested action."""
        return action_tool(action) in self._tools_by_name

    async def execute(self, action: dict[str, Any]) -> ToolActionResult:
        """Execute one bridged MCP tool call."""
        tool_name = action_tool(action)
        spec = self._tools_by_name.get(tool_name)
        if spec is None:
            audit_artifact = write_mcp_bridge_audit_event(
                self.spec_dir,
                {
                    "event": "mcp_tool_call",
                    "status": "denied",
                    "server": "unknown",
                    "tool": tool_name or "unknown",
                    "exposed_name": tool_name or "unknown",
                    "reason": "unknown_bridged_mcp_tool",
                    "action": safe_mcp_action_for_trace(action),
                },
            )
            return ToolActionResult(
                tool=tool_name or "unknown",
                ok=False,
                message=f"Unknown bridged MCP tool: {tool_name or '<missing>'}",
                data={"audit_artifact": audit_artifact},
            )

        args = {
            key: value
            for key, value in action.items()
            if key not in {"tool", "name", "type"}
        }
        audit_base = {
            "event": "mcp_tool_call",
            "server": spec.server,
            "tool": spec.name,
            "exposed_name": spec.exposed_name,
            **spec.policy.to_dict(),
            "action": safe_mcp_action_for_trace(action),
        }
        try:
            result = spec.handler(args)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            audit_artifact = write_mcp_bridge_audit_event(
                self.spec_dir,
                {
                    **audit_base,
                    "status": "error",
                    "message": str(e),
                },
            )
            return ToolActionResult(
                tool=spec.exposed_name,
                ok=False,
                message=f"Bridged MCP tool failed: {e}",
                data={
                    "server": spec.server,
                    "name": spec.name,
                    **spec.policy.to_dict(),
                    "audit_artifact": audit_artifact,
                },
            )

        text = extract_mcp_text(result)
        ok = not text.startswith("Error:")
        audit_artifact = write_mcp_bridge_audit_event(
            self.spec_dir,
            {
                **audit_base,
                "status": "ok" if ok else "error",
                "message": text[:1000],
            },
        )
        return ToolActionResult(
            tool=spec.exposed_name,
            ok=ok,
            message=text or f"Ran {spec.exposed_name}",
            data={
                "server": spec.server,
                "name": spec.name,
                **spec.policy.to_dict(),
                "audit_artifact": audit_artifact,
                "result": result,
            },
        )

    def report(self) -> dict[str, Any]:
        """Return compact bridge metadata for artifacts/debug output."""
        server_statuses = describe_mcp_server_statuses(
            requested_servers=self.requested_servers,
            available_servers=self.available_servers,
            native_available=False,
        )
        bridge_plan = build_mcp_bridge_plan(
            provider_name="generic",
            runtime_name="local_bridge",
            strategy="local_bridge" if self.has_tools else "unavailable",
            requested_servers=self.requested_servers,
            available_servers=self.available_servers,
            unavailable_servers=self.unavailable_servers,
            server_statuses=server_statuses,
            tool_count=len(self._tools),
        )
        return {
            "server": LOCAL_BRIDGE_SERVER,
            "available": self.has_tools,
            "tool_count": len(self._tools),
            "tools": [tool.exposed_name for tool in self._tools],
            "tool_policies": [tool.policy_metadata() for tool in self._tools],
            "requested_servers": list(self.requested_servers),
            "available_servers": list(self.available_servers),
            "unavailable_servers": list(self.unavailable_servers),
            "server_statuses": [
                dict(server_status) for server_status in server_statuses
            ],
            "bridge_plan": bridge_plan.to_dict(),
        }

    def support_for(
        self,
        *,
        provider_name: str,
        runtime_name: str,
        capabilities: RuntimeCapabilities,
    ) -> RuntimeMcpSupport:
        """Return effective MCP support with this bridge configured."""
        return resolve_runtime_mcp_support(
            provider_name=provider_name,
            runtime_name=runtime_name,
            capabilities=capabilities,
            bridge_available=self.has_tools,
            tool_count=len(self._tools),
            requested_servers=self.requested_servers,
            available_servers=self.available_servers,
        )


def resolve_runtime_mcp_support(
    *,
    provider_name: str,
    runtime_name: str,
    capabilities: RuntimeCapabilities,
    bridge_available: bool = False,
    tool_count: int = 0,
    requested_servers: tuple[str, ...] = (),
    available_servers: tuple[str, ...] = (),
) -> RuntimeMcpSupport:
    """Return native or local-bridge MCP support without claiming full parity."""
    provider = provider_name.lower()
    available_capabilities = tuple(capabilities.available())
    requested_servers = normalize_mcp_server_names(requested_servers)

    if capabilities.mcp:
        return RuntimeMcpSupport(
            provider_name=provider,
            runtime_name=runtime_name,
            strategy="native",
            available=True,
            reason=f"{provider}/{runtime_name} exposes native MCP tools.",
            server=None,
            tool_count=tool_count,
            available_capabilities=available_capabilities,
            requested_servers=requested_servers,
            available_servers=requested_servers,
            unavailable_servers=(),
            server_statuses=describe_mcp_server_statuses(
                requested_servers=requested_servers,
                available_servers=requested_servers,
                native_available=True,
            ),
        )

    if bridge_available and capabilities.function_tools:
        available_servers = normalize_mcp_server_names(
            available_servers or (LOCAL_BRIDGE_SERVER,)
        )
        unavailable_servers = tuple(
            server for server in requested_servers if server not in available_servers
        )
        return RuntimeMcpSupport(
            provider_name=provider,
            runtime_name=runtime_name,
            strategy="local_bridge",
            available=True,
            reason=(
                "Auto Code can bridge local auto-claude tools into this runtime; "
                "external MCP servers still require native runtime support."
            ),
            server=LOCAL_BRIDGE_SERVER,
            tool_count=tool_count,
            available_capabilities=available_capabilities,
            requested_servers=requested_servers,
            available_servers=available_servers,
            unavailable_servers=unavailable_servers,
            server_statuses=describe_mcp_server_statuses(
                requested_servers=requested_servers,
                available_servers=available_servers,
                native_available=False,
            ),
        )

    if bridge_available:
        reason = (
            "A local MCP bridge is configured, but the runtime cannot expose "
            "local action/function tools."
        )
    else:
        reason = (
            "MCP support requires native runtime MCP or a configured local "
            "Auto Code MCP bridge."
        )
    unavailable_servers = requested_servers
    return RuntimeMcpSupport(
        provider_name=provider,
        runtime_name=runtime_name,
        strategy="unavailable",
        available=False,
        reason=reason,
        server=LOCAL_BRIDGE_SERVER if bridge_available else None,
        tool_count=tool_count,
        available_capabilities=available_capabilities,
        requested_servers=requested_servers,
        available_servers=(),
        unavailable_servers=unavailable_servers,
        server_statuses=describe_mcp_server_statuses(
            requested_servers=requested_servers,
            available_servers=(),
            native_available=False,
        ),
    )


def describe_mcp_server_statuses(
    *,
    requested_servers: tuple[str, ...],
    available_servers: tuple[str, ...],
    native_available: bool,
) -> tuple[dict[str, Any], ...]:
    """Return per-server MCP bridge status for diagnostics and settings UI."""
    requested_servers = normalize_mcp_server_names(requested_servers)
    available = set(normalize_mcp_server_names(available_servers))
    statuses: list[dict[str, Any]] = []

    for server in requested_servers:
        catalog_entry = MCP_SERVER_CATALOG.get(server, {})
        bridgeable = bool(catalog_entry.get("bridgeable", False))
        if native_available:
            availability = "available"
            runtime_path = "native"
            reason = "Available through the selected runtime's native MCP support."
        elif server in available:
            availability = "available"
            runtime_path = "local_bridge"
            reason = "Available through Auto Code's local MCP bridge."
        elif bridgeable:
            availability = "unavailable"
            runtime_path = "local_bridge_required"
            reason = "Local bridge tools were requested but are not configured."
        elif server in MCP_SERVER_CATALOG:
            availability = "unavailable"
            runtime_path = "native_required"
            reason = "External MCP server requires native MCP runtime support."
        else:
            availability = "unavailable"
            runtime_path = "unsupported"
            reason = "No local bridge policy is registered for this MCP server."

        statuses.append(
            {
                "server": server,
                "display_name": str(catalog_entry.get("display_name", server)),
                "availability": availability,
                "runtime_path": runtime_path,
                "bridgeable": bridgeable,
                "reason": reason,
                "notes": str(catalog_entry.get("notes", "")),
            }
        )

    return tuple(statuses)


def build_mcp_bridge_plan(
    *,
    provider_name: str,
    runtime_name: str,
    strategy: McpSupportStrategy,
    requested_servers: tuple[str, ...],
    available_servers: tuple[str, ...],
    unavailable_servers: tuple[str, ...],
    server_statuses: tuple[dict[str, Any], ...],
    tool_count: int = 0,
) -> RuntimeMcpBridgePlan:
    """Build a normalized MCP bridge plan from per-server support statuses."""
    requested_servers = normalize_mcp_server_names(requested_servers)
    available_servers = normalize_mcp_server_names(available_servers)
    unavailable_servers = normalize_mcp_server_names(unavailable_servers)
    native_required_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "native_required"
    )
    local_bridge_required_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "local_bridge_required"
    )
    unsupported_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "unsupported"
    )
    bridged_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "local_bridge"
        and status.get("availability") == "available"
    )
    status = mcp_plan_status(
        requested_servers=requested_servers,
        available_servers=available_servers,
        unavailable_servers=unavailable_servers,
    )
    action_required = mcp_plan_action_required(
        status=status,
        native_required_servers=native_required_servers,
        local_bridge_required_servers=local_bridge_required_servers,
        unsupported_servers=unsupported_servers,
    )
    recommended_runtime_path = mcp_plan_recommended_runtime_path(
        action_required=action_required,
        strategy=strategy,
    )
    return RuntimeMcpBridgePlan(
        provider_name=provider_name,
        runtime_name=runtime_name,
        strategy=strategy,
        status=status,
        action_required=action_required,
        recommended_runtime_path=recommended_runtime_path,
        requested_servers=requested_servers,
        available_servers=available_servers,
        unavailable_servers=unavailable_servers,
        native_required_servers=native_required_servers,
        local_bridge_required_servers=local_bridge_required_servers,
        unsupported_servers=unsupported_servers,
        bridged_servers=bridged_servers,
        tool_count=tool_count,
    )


def mcp_plan_status(
    *,
    requested_servers: tuple[str, ...],
    available_servers: tuple[str, ...],
    unavailable_servers: tuple[str, ...],
) -> str:
    """Return high-level MCP plan status."""
    if not requested_servers:
        return "not_requested"
    if not unavailable_servers:
        return "ready"
    if available_servers:
        return "partial"
    return "blocked"


def mcp_plan_action_required(
    *,
    status: str,
    native_required_servers: tuple[str, ...],
    local_bridge_required_servers: tuple[str, ...],
    unsupported_servers: tuple[str, ...],
) -> str:
    """Return the next action required to satisfy the MCP plan."""
    if status in {"not_requested", "ready"}:
        return "none"
    if unsupported_servers:
        return "register_or_remove_unsupported_servers"
    if native_required_servers:
        return "use_native_mcp_runtime"
    if local_bridge_required_servers:
        return "configure_local_bridge_tools"
    return "inspect_runtime_mcp_support"


def mcp_plan_recommended_runtime_path(
    *,
    action_required: str,
    strategy: McpSupportStrategy,
) -> str:
    """Return the recommended runtime path for the MCP plan."""
    if action_required == "use_native_mcp_runtime":
        return "native_mcp_runtime"
    if action_required == "configure_local_bridge_tools":
        return "local_bridge"
    if action_required == "register_or_remove_unsupported_servers":
        return "unsupported"
    if strategy == "native":
        return "native"
    if strategy == "local_bridge":
        return "local_bridge"
    return "none"


def load_auto_claude_bridge_tools(
    *,
    spec_dir: Path,
    project_dir: Path,
    allowed_tools: set[str],
) -> list[RuntimeMcpToolSpec]:
    """Load SDK-declared Auto Code tools for direct invocation."""
    if not allowed_tools or not is_tools_available():
        return []

    specs: list[RuntimeMcpToolSpec] = []
    for sdk_tool in create_all_tools(spec_dir, project_dir):
        name = str(getattr(sdk_tool, "name", "") or "")
        if allowed_tools and name not in allowed_tools:
            continue
        specs.append(
            RuntimeMcpToolSpec(
                server=LOCAL_BRIDGE_SERVER,
                name=name,
                exposed_name=f"{MCP_AUTO_CLAUDE_PREFIX}{name}",
                description=str(getattr(sdk_tool, "description", "") or ""),
                parameters=input_schema_to_json_schema(
                    getattr(sdk_tool, "input_schema", {}) or {}
                ),
                policy=policy_for_auto_claude_tool(name),
                handler=sdk_tool.handler,
            )
        )
    return specs


def policy_for_auto_claude_tool(tool_name: str) -> RuntimeMcpToolPolicy:
    """Return conservative permission/audit metadata for one local MCP tool."""
    explicit: dict[str, RuntimeMcpToolPolicy] = {
        "get_build_progress": RuntimeMcpToolPolicy("read_build_state", "read"),
        "get_qa_status": RuntimeMcpToolPolicy("read_qa_state", "read"),
        "get_spec_statistics": RuntimeMcpToolPolicy("read_metrics", "read"),
        "get_quality_metrics": RuntimeMcpToolPolicy("read_metrics", "read"),
        "get_session_context": RuntimeMcpToolPolicy("read_memory", "read"),
        "list_discoveries": RuntimeMcpToolPolicy("read_memory", "read"),
        "search_team_docs": RuntimeMcpToolPolicy("read_docs", "read"),
        "get_team_docs": RuntimeMcpToolPolicy("read_docs", "read"),
        "get_task_status": RuntimeMcpToolPolicy("read_background_task", "read"),
        "get_task_output": RuntimeMcpToolPolicy("read_background_task", "read"),
        "has_critical_issues": RuntimeMcpToolPolicy("read_predictive_scan", "read"),
        "get_predictive_scan_history": RuntimeMcpToolPolicy(
            "read_predictive_scan", "read"
        ),
        "debug_error": RuntimeMcpToolPolicy("runtime_analysis", "analysis"),
        "explain_error": RuntimeMcpToolPolicy("runtime_analysis", "analysis"),
        "suggest_breakpoints": RuntimeMcpToolPolicy("runtime_analysis", "analysis"),
        "run_predictive_scan": RuntimeMcpToolPolicy(
            "run_predictive_scan", "analysis", mutating=False
        ),
        "update_subtask_status": RuntimeMcpToolPolicy(
            "write_build_state", "write", mutating=True
        ),
        "update_qa_status": RuntimeMcpToolPolicy(
            "write_qa_state", "write", mutating=True
        ),
        "record_discovery": RuntimeMcpToolPolicy(
            "write_memory", "write", mutating=True
        ),
        "record_gotcha": RuntimeMcpToolPolicy(
            "write_memory", "write", mutating=True
        ),
        "record_feedback": RuntimeMcpToolPolicy(
            "write_memory", "write", mutating=True
        ),
        "start_background_command": RuntimeMcpToolPolicy(
            "run_background_command", "command", mutating=True
        ),
        "cancel_task": RuntimeMcpToolPolicy(
            "cancel_background_task", "command", mutating=True
        ),
    }
    if tool_name in explicit:
        return explicit[tool_name]

    looks_read_only = tool_name.startswith(
        ("get_", "list_", "search_", "explain_", "suggest_", "has_")
    )
    if looks_read_only:
        return RuntimeMcpToolPolicy("read_auto_claude_tool", "read")
    return RuntimeMcpToolPolicy(
        "write_auto_claude_tool",
        "write",
        mutating=True,
    )


def normalize_mcp_server_names(server_names: Any) -> tuple[str, ...]:
    """Normalize configured MCP server names while preserving order."""
    if isinstance(server_names, str):
        server_iterable = (server_names,)
    else:
        server_iterable = server_names
    normalized: list[str] = []
    for server_name in server_iterable or ():
        server = normalize_mcp_server_name(str(server_name))
        if server and server not in normalized:
            normalized.append(server)
    return tuple(normalized)


def normalize_mcp_server_name(server_name: str) -> str:
    """Normalize common MCP server aliases used by agent configs."""
    server = server_name.strip()
    if server.startswith("mcp__"):
        parts = server.split("__")
        if len(parts) >= 2:
            server = parts[1]
    if server == "graphiti-memory":
        return "graphiti"
    return server


def is_mcp_action_name(tool_name: str) -> bool:
    """Return whether a local action name looks like an MCP tool call."""
    return tool_name.startswith("mcp__")


def mcp_server_from_action_name(tool_name: str) -> str | None:
    """Extract the MCP server portion from a tool name such as mcp__context7__x."""
    if not is_mcp_action_name(tool_name):
        return None
    server = normalize_mcp_server_name(tool_name)
    return server or None


def unavailable_mcp_action_result(
    action: dict[str, Any],
    *,
    support: dict[str, Any] | RuntimeMcpSupport | None,
) -> ToolActionResult:
    """Return a structured observation for MCP calls unavailable in this runtime."""
    tool_name = action_tool(action)
    server = mcp_server_from_action_name(tool_name) or "unknown"
    support_payload = (
        support.to_dict() if isinstance(support, RuntimeMcpSupport) else support or {}
    )
    status = find_mcp_server_status(support_payload, server)
    available_servers = tuple(
        str(name) for name in support_payload.get("available_servers", ())
    )

    if server in available_servers:
        reason = (
            "The MCP server is available, but this specific tool is not exposed "
            "to the selected runtime/session."
        )
        runtime_path = "tool_not_exposed"
    else:
        reason = str(status.get("reason") or support_payload.get("reason") or "")
        runtime_path = str(
            status.get("runtime_path")
            or support_payload.get("strategy")
            or "unavailable"
        )

    return ToolActionResult(
        tool=tool_name or "mcp",
        ok=False,
        message=(
            f"MCP tool {tool_name or '<missing>'} is not available in this "
            f"runtime. {reason}".strip()
        ),
        data={
            "server": server,
            "runtime_path": runtime_path,
            "support_strategy": support_payload.get("strategy"),
            "available_servers": list(available_servers),
            "unavailable_servers": list(support_payload.get("unavailable_servers", ())),
            "server_status": status,
            "bridge_plan": support_payload.get("bridge_plan"),
        },
    )


def find_mcp_server_status(
    support_payload: dict[str, Any],
    server: str,
) -> dict[str, Any]:
    """Return one server status from an MCP support payload when available."""
    for status in support_payload.get("server_statuses", ()) or ():
        if isinstance(status, dict) and status.get("server") == server:
            return dict(status)
    return {
        "server": server,
        "display_name": MCP_SERVER_CATALOG.get(server, {}).get("display_name", server),
        "availability": "unavailable",
        "runtime_path": "unsupported",
        "bridgeable": bool(MCP_SERVER_CATALOG.get(server, {}).get("bridgeable", False)),
        "reason": "No MCP support metadata is available for this runtime.",
        "notes": str(MCP_SERVER_CATALOG.get(server, {}).get("notes", "")),
    }


def normalize_auto_claude_tool_name(tool_name: str) -> str:
    """Normalize configured MCP names to bare SDK tool names."""
    if tool_name.startswith(MCP_AUTO_CLAUDE_PREFIX):
        return tool_name.removeprefix(MCP_AUTO_CLAUDE_PREFIX)
    return tool_name


def input_schema_to_json_schema(input_schema: dict[str, Any]) -> dict[str, Any]:
    """Convert Claude SDK tool shorthand into JSON schema."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, value in input_schema.items():
        properties[name] = python_type_to_json_schema(value)
        required.append(name)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def python_type_to_json_schema(value: Any) -> dict[str, Any]:
    """Best-effort conversion from SDK shorthand types to JSON schema."""
    if value is str:
        return {"type": "string"}
    if value is int:
        return {"type": "integer"}
    if value is float:
        return {"type": "number"}
    if value is bool:
        return {"type": "boolean"}
    if value in {list, tuple}:
        return {"type": "array"}
    if value is dict:
        return {"type": "object"}
    if isinstance(value, dict):
        return value
    return {"type": "string"}


def example_value(schema: dict[str, Any]) -> Any:
    """Return a small example value for a parameter schema."""
    schema_type = schema.get("type")
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        return []
    if schema_type == "object":
        return {}
    return "value"


def extract_mcp_text(result: Any) -> str:
    """Extract readable text from a common MCP content payload."""
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts = [
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "\n".join(part for part in parts if part)
        if isinstance(result.get("text"), str):
            return str(result["text"])
    return str(result)


def mcp_bridge_audit_path(spec_dir: Path) -> Path:
    """Return the audit artifact path for bridged MCP tool calls."""
    return spec_dir / "artifacts" / MCP_BRIDGE_AUDIT_FILENAME


def write_mcp_bridge_audit_event(spec_dir: Path, event: dict[str, Any]) -> str:
    """Append one bridged MCP audit event and return the artifact path."""
    path = mcp_bridge_audit_path(spec_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **event,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return str(path)


def safe_mcp_action_for_trace(action: dict[str, Any]) -> dict[str, Any]:
    """Reuse local redaction for MCP request traces."""
    return safe_action_for_trace(action)
