"""Provider-neutral bridge for local Auto Code MCP tools.

This is intentionally narrower than full MCP parity. It exposes Auto Code's
in-process ``auto-claude`` tools to limited/direct runtimes without starting a
Claude SDK agent loop. External MCP servers still require a native runtime.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from agents.tools_pkg.models import get_agent_config
from agents.tools_pkg.registry import create_all_tools, is_tools_available

from .capabilities import RuntimeCapabilities
from .local_actions import ToolActionResult, action_tool, safe_action_for_trace

MCP_AUTO_CLAUDE_PREFIX = "mcp__auto-claude__"
LOCAL_BRIDGE_SERVER = "auto-claude"
McpSupportStrategy = Literal["native", "local_bridge", "unavailable"]
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
        }


@dataclass(frozen=True)
class RuntimeMcpToolSpec:
    """Provider-neutral schema for one bridged MCP tool."""

    server: str
    name: str
    exposed_name: str
    description: str
    parameters: dict[str, Any]
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
            return ToolActionResult(
                tool=tool_name or "unknown",
                ok=False,
                message=f"Unknown bridged MCP tool: {tool_name or '<missing>'}",
            )

        args = {
            key: value
            for key, value in action.items()
            if key not in {"tool", "name", "type"}
        }
        try:
            result = spec.handler(args)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            return ToolActionResult(
                tool=spec.exposed_name,
                ok=False,
                message=f"Bridged MCP tool failed: {e}",
                data={"server": spec.server, "name": spec.name},
            )

        text = extract_mcp_text(result)
        ok = not text.startswith("Error:")
        return ToolActionResult(
            tool=spec.exposed_name,
            ok=ok,
            message=text or f"Ran {spec.exposed_name}",
            data={
                "server": spec.server,
                "name": spec.name,
                "result": result,
            },
        )

    def report(self) -> dict[str, Any]:
        """Return compact bridge metadata for artifacts/debug output."""
        return {
            "server": LOCAL_BRIDGE_SERVER,
            "available": self.has_tools,
            "tool_count": len(self._tools),
            "tools": [tool.exposed_name for tool in self._tools],
            "requested_servers": list(self.requested_servers),
            "available_servers": list(self.available_servers),
            "unavailable_servers": list(self.unavailable_servers),
            "server_statuses": [
                dict(server_status)
                for server_status in describe_mcp_server_statuses(
                    requested_servers=self.requested_servers,
                    available_servers=self.available_servers,
                    native_available=False,
                )
            ],
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
                handler=sdk_tool.handler,
            )
        )
    return specs


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


def safe_mcp_action_for_trace(action: dict[str, Any]) -> dict[str, Any]:
    """Reuse local redaction for MCP request traces."""
    return safe_action_for_trace(action)
