"""Provider-neutral bridge for local Auto Code MCP tools.

This is intentionally narrower than full MCP parity. It exposes Auto Code's
in-process ``auto-claude`` tools to limited/direct runtimes without starting a
Claude SDK agent loop. External MCP servers still require a native runtime.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.tools_pkg.models import get_agent_config
from agents.tools_pkg.registry import create_all_tools, is_tools_available

from .local_actions import ToolActionResult, action_tool, safe_action_for_trace

MCP_AUTO_CLAUDE_PREFIX = "mcp__auto-claude__"


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
    ):
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.allowed_tools = allowed_tools
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
    ) -> RuntimeMcpBridge | None:
        """Build a bridge when the agent config requests auto-claude MCP tools."""
        agent_type = str(getattr(agent_session, "agent_type", "") or "")
        configured_tools = getattr(agent_session, "auto_claude_tools", None)
        if configured_tools is None and agent_type:
            config = get_agent_config(agent_type)
            configured_tools = config.get("auto_claude_tools", [])
        if not configured_tools:
            return None

        allowed_tools = {
            normalize_auto_claude_tool_name(str(tool_name))
            for tool_name in configured_tools
        }
        bridge = cls(
            spec_dir=spec_dir,
            project_dir=project_dir,
            allowed_tools=allowed_tools,
        )
        return bridge if bridge.has_tools else None

    @property
    def has_tools(self) -> bool:
        return bool(self._tools)

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
            "server": "auto-claude",
            "available": self.has_tools,
            "tool_count": len(self._tools),
            "tools": [tool.exposed_name for tool in self._tools],
        }


def load_auto_claude_bridge_tools(
    *,
    spec_dir: Path,
    project_dir: Path,
    allowed_tools: set[str],
) -> list[RuntimeMcpToolSpec]:
    """Load SDK-declared Auto Code tools for direct invocation."""
    if not is_tools_available():
        return []

    specs: list[RuntimeMcpToolSpec] = []
    for sdk_tool in create_all_tools(spec_dir, project_dir):
        name = str(getattr(sdk_tool, "name", "") or "")
        if allowed_tools and name not in allowed_tools:
            continue
        specs.append(
            RuntimeMcpToolSpec(
                server="auto-claude",
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
