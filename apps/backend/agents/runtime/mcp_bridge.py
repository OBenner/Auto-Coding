"""Provider-neutral bridge for local Auto Code MCP tools.

This is intentionally narrower than full MCP parity. It exposes Auto Code's
in-process ``auto-claude`` tools to limited/direct runtimes without starting a
Claude SDK agent loop, and it can execute explicitly enabled external MCP tools
through a provider-neutral stdio or Streamable HTTP bridge.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
from collections.abc import Mapping
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
EXTERNAL_MCP_CLIENT_ENV = "AUTO_CODE_EXTERNAL_MCP_CLIENT"
MCP_ALLOWED_PERMISSIONS_ENV = "AUTO_CODE_MCP_ALLOWED_PERMISSIONS"
EXTERNAL_MCP_PROTOCOL_VERSION_ENV = "AUTO_CODE_MCP_PROTOCOL_VERSION"
CUSTOM_MCP_SERVERS_CONFIG_KEY = "CUSTOM_MCP_SERVERS"
DEFAULT_EXTERNAL_MCP_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_EXTERNAL_MCP_HTTP_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_EXTERNAL_MCP_TIMEOUT_SECONDS = 30.0
SUPPORTED_EXTERNAL_MCP_TRANSPORTS = ("stdio", "http")
DESCRIPTION_OPTIONAL_MAX_RESULTS = "Optional maximum number of results."
DESCRIPTION_OPTIONAL_TEAM_ID_OR_KEY = "Optional team ID or key."
McpSupportStrategy = Literal["native", "local_bridge", "unavailable"]
McpAuditLevel = Literal["read", "write", "command", "analysis"]
ExternalMcpHealthStatus = Literal[
    "not_bridgeable",
    "client_disabled",
    "server_disabled",
    "missing_configuration",
    "choose_concrete_server",
    "adapter_missing",
    "unsupported_transport",
    "ready_to_connect",
]
MCP_SERVER_CATALOG: dict[str, dict[str, Any]] = {
    LOCAL_BRIDGE_SERVER: {
        "display_name": "Auto Code local tools",
        "bridgeable": True,
        "external_bridgeable": False,
        "notes": "In-process Auto Code tools can be exposed through local actions.",
    },
    "context7": {
        "display_name": "Context7",
        "bridgeable": False,
        "external_bridgeable": True,
        "enabled_env": "CONTEXT7_ENABLED",
        "enabled_default": True,
        "transport": "stdio",
        "command": "npx",
        "args": ("-y", "@upstash/context7-mcp"),
        "tools": (
            "resolve-library-id",
            "get-library-docs",
        ),
        "notes": "External documentation MCP server.",
    },
    "graphiti": {
        "display_name": "Graphiti",
        "bridgeable": False,
        "external_bridgeable": True,
        "transport": "http",
        "url_env": "GRAPHITI_MCP_URL",
        "required_env": ("GRAPHITI_MCP_URL",),
        "notes": "External memory MCP server.",
    },
    "linear": {
        "display_name": "Linear",
        "bridgeable": False,
        "external_bridgeable": True,
        "enabled_env": "LINEAR_MCP_ENABLED",
        "enabled_default": True,
        "transport": "http",
        "url": "https://mcp.linear.app/mcp",
        "authorization_env": "LINEAR_API_KEY",
        "authorization_scheme": "Bearer",
        "required_env": ("LINEAR_API_KEY",),
        "notes": "External Linear MCP server.",
    },
    "browser": {
        "display_name": "Browser automation",
        "bridgeable": False,
        "external_bridgeable": True,
        "concrete_servers": ("electron", "puppeteer"),
        "notes": (
            "Logical browser MCP requirement; resolve to electron or puppeteer "
            "for an external client."
        ),
    },
    "electron": {
        "display_name": "Electron",
        "bridgeable": False,
        "external_bridgeable": True,
        "enabled_env": "ELECTRON_MCP_ENABLED",
        "enabled_default": False,
        "transport": "stdio",
        "command": "npm",
        "args": ("exec", "electron-mcp-server"),
        "notes": "External Electron automation MCP server.",
    },
    "puppeteer": {
        "display_name": "Puppeteer",
        "bridgeable": False,
        "external_bridgeable": True,
        "enabled_env": "PUPPETEER_MCP_ENABLED",
        "enabled_default": False,
        "transport": "stdio",
        "command": "npx",
        "args": ("puppeteer-mcp-server",),
        "notes": "External browser automation MCP server.",
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
class RuntimeMcpPermissionDecision:
    """Result of checking a bridged MCP tool policy against an allowlist."""

    allowed: bool
    reason: str
    allowed_permissions: tuple[str, ...] | None = None

    def to_audit_dict(self) -> dict[str, Any]:
        """Serialize the permission decision for audit events and observations."""
        payload: dict[str, Any] = {
            "permission_allowed": self.allowed,
            "permission_decision_reason": self.reason,
        }
        if self.allowed_permissions is not None:
            payload["allowed_permissions"] = list(self.allowed_permissions)
        return payload


@dataclass(frozen=True)
class RuntimeExternalMcpServerHealth:
    """Readiness contract for one external MCP server bridge target."""

    server: str
    display_name: str
    bridgeable: bool
    client_enabled: bool
    server_enabled: bool
    configured: bool
    status: ExternalMcpHealthStatus
    reason: str
    transport: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    enabled_env: str | None = None
    required_env: tuple[str, ...] = ()
    missing_env: tuple[str, ...] = ()
    concrete_servers: tuple[str, ...] = ()
    execution_supported: bool = False
    executable_tools: tuple[str, ...] = ()
    adapter_registered: bool = False
    adapter_name: str | None = None
    adapter_transport: str | None = None
    adapter_exposed_server: str | None = None
    transport_supported: bool = False
    supported_transports: tuple[str, ...] = SUPPORTED_EXTERNAL_MCP_TRANSPORTS

    @property
    def ready_to_connect(self) -> bool:
        """Return true when configuration is ready for a future external client."""
        return self.status == "ready_to_connect"

    def to_dict(self) -> dict[str, Any]:
        """Serialize external MCP client readiness for diagnostics and artifacts."""
        return {
            "server": self.server,
            "display_name": self.display_name,
            "bridgeable": self.bridgeable,
            "client_enabled": self.client_enabled,
            "server_enabled": self.server_enabled,
            "configured": self.configured,
            "status": self.status,
            "reason": self.reason,
            "transport": self.transport,
            "command": self.command,
            "args": list(self.args),
            "url": self.url,
            "enabled_env": self.enabled_env,
            "required_env": list(self.required_env),
            "missing_env": list(self.missing_env),
            "concrete_servers": list(self.concrete_servers),
            "execution_supported": self.execution_supported,
            "executable_tools": list(self.executable_tools),
            "executable_tool_count": len(self.executable_tools),
            "adapter_registered": self.adapter_registered,
            "adapter_name": self.adapter_name,
            "adapter_transport": self.adapter_transport,
            "adapter_exposed_server": self.adapter_exposed_server,
            "transport_supported": self.transport_supported,
            "supported_transports": list(self.supported_transports),
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
    external_bridge_required_servers: tuple[str, ...] = ()
    external_bridge_ready_servers: tuple[str, ...] = ()
    external_bridge_adapter_missing_servers: tuple[str, ...] = ()
    external_bridge_unsupported_transport_servers: tuple[str, ...] = ()
    unsupported_servers: tuple[str, ...] = ()
    bridged_servers: tuple[str, ...] = ()
    local_bridged_servers: tuple[str, ...] = ()
    external_bridged_servers: tuple[str, ...] = ()
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
            "external_bridge_required_servers": list(
                self.external_bridge_required_servers
            ),
            "external_bridge_ready_servers": list(self.external_bridge_ready_servers),
            "external_bridge_adapter_missing_servers": list(
                self.external_bridge_adapter_missing_servers
            ),
            "external_bridge_unsupported_transport_servers": list(
                self.external_bridge_unsupported_transport_servers
            ),
            "unsupported_servers": list(self.unsupported_servers),
            "bridged_servers": list(self.bridged_servers),
            "local_bridged_servers": list(self.local_bridged_servers),
            "external_bridged_servers": list(self.external_bridged_servers),
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


@dataclass(frozen=True)
class RuntimeExternalMcpToolDefinition:
    """Static provider-neutral schema for one externally bridged MCP tool."""

    name: str
    description: str
    parameters: dict[str, Any]
    policy: RuntimeMcpToolPolicy
    target_name_argument: str | None = None


@dataclass(frozen=True)
class RuntimeExternalMcpAdapter:
    """Executable adapter contract for one external MCP server."""

    server: str
    display_name: str
    tool_definitions: tuple[RuntimeExternalMcpToolDefinition, ...]
    transport: str = "stdio"
    exposed_server: str | None = None

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return registered MCP tool names for this adapter."""
        return tuple(definition.name for definition in self.tool_definitions)

    @property
    def exposed_server_name(self) -> str:
        """Return the provider-facing MCP server segment for tool names."""
        return self.exposed_server or self.server

    def execution_supported(
        self,
        *,
        transport: str | None,
        command: str | None,
        url: str | None = None,
    ) -> bool:
        """Return whether this adapter can execute the catalog transport."""
        if not self.tool_definitions or not self.transport_supported(
            transport=transport
        ):
            return False
        if self.transport == "stdio":
            return bool(command)
        if self.transport == "http":
            return bool(url)
        return False

    def transport_supported(self, *, transport: str | None) -> bool:
        """Return whether the provider-neutral client can execute this transport."""
        return (
            transport == self.transport
            and self.transport in SUPPORTED_EXTERNAL_MCP_TRANSPORTS
        )

    def load_tool_specs(
        self,
        *,
        health: RuntimeExternalMcpServerHealth,
        project_dir: Path,
        project_mcp_config: Mapping[str, Any] | None = None,
        environment: Mapping[str, str] | None = None,
        session_cache: dict[str, Any] | None = None,
    ) -> list[RuntimeMcpToolSpec]:
        """Return provider tool schemas backed by this adapter."""
        if not health.ready_to_connect or not health.execution_supported:
            return []
        return [
            RuntimeMcpToolSpec(
                server=self.server,
                name=definition.name,
                exposed_name=(f"mcp__{self.exposed_server_name}__{definition.name}"),
                description=definition.description,
                parameters=definition.parameters,
                policy=definition.policy,
                handler=external_mcp_tool_handler(
                    health=health,
                    tool_name=definition.name,
                    project_dir=project_dir,
                    target_name_argument=definition.target_name_argument,
                    project_mcp_config=project_mcp_config,
                    environment=environment,
                    session_cache=session_cache,
                ),
            )
            for definition in self.tool_definitions
        ]


def external_mcp_tool_definition(
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
    permission: str,
    audit_level: McpAuditLevel,
    mutating: bool = False,
    target_name_argument: str | None = None,
) -> RuntimeExternalMcpToolDefinition:
    """Build one external MCP tool definition with a conservative policy."""
    return RuntimeExternalMcpToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
        policy=RuntimeMcpToolPolicy(
            permission,
            audit_level,
            mutating=mutating,
        ),
        target_name_argument=target_name_argument,
    )


def object_schema(
    properties: dict[str, Any] | None = None,
    *,
    required: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return a strict object schema for external MCP tool arguments."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties or {},
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


def context7_external_mcp_adapter() -> RuntimeExternalMcpAdapter:
    """Build the Context7 external MCP execution adapter."""
    tool_definitions: tuple[RuntimeExternalMcpToolDefinition, ...] = (
        external_mcp_tool_definition(
            name="resolve-library-id",
            description=(
                "Resolve a package or library name to a Context7-compatible library ID."
            ),
            parameters=object_schema(
                {
                    "libraryName": {
                        "type": "string",
                        "description": "Package or library name to resolve.",
                    }
                },
                required=("libraryName",),
            ),
            permission="read_external_docs",
            audit_level="read",
        ),
        external_mcp_tool_definition(
            name="get-library-docs",
            description=(
                "Fetch current documentation for a Context7-compatible library ID."
            ),
            parameters=object_schema(
                {
                    "context7CompatibleLibraryID": {
                        "type": "string",
                        "description": "Library ID returned by resolve-library-id.",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional topic to focus the documentation query.",
                    },
                    "tokens": {
                        "type": "integer",
                        "description": "Optional maximum documentation token budget.",
                    },
                },
                required=("context7CompatibleLibraryID",),
            ),
            permission="read_external_docs",
            audit_level="read",
        ),
    )
    return RuntimeExternalMcpAdapter(
        server="context7",
        display_name="Context7",
        tool_definitions=tool_definitions,
    )


def graphiti_external_mcp_adapter() -> RuntimeExternalMcpAdapter:
    """Build the Graphiti Streamable HTTP MCP execution adapter."""
    return RuntimeExternalMcpAdapter(
        server="graphiti",
        display_name="Graphiti",
        transport="http",
        exposed_server="graphiti-memory",
        tool_definitions=(
            external_mcp_tool_definition(
                name="search_nodes",
                description="Search Graphiti entity summaries.",
                parameters=object_schema(
                    {
                        "query": {
                            "type": "string",
                            "description": "Natural-language entity search query.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": DESCRIPTION_OPTIONAL_MAX_RESULTS,
                        },
                    },
                    required=("query",),
                ),
                permission="read_memory",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="search_facts",
                description="Search Graphiti relationship facts.",
                parameters=object_schema(
                    {
                        "query": {
                            "type": "string",
                            "description": "Natural-language fact search query.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": DESCRIPTION_OPTIONAL_MAX_RESULTS,
                        },
                    },
                    required=("query",),
                ),
                permission="read_memory",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="add_episode",
                description="Add an episode to the Graphiti knowledge graph.",
                parameters=object_schema(
                    {
                        "name": {
                            "type": "string",
                            "description": "Episode title.",
                        },
                        "episode_body": {
                            "type": "string",
                            "description": "Episode content to store.",
                        },
                        "source": {
                            "type": "string",
                            "description": "Optional source enum or source identifier.",
                        },
                        "source_description": {
                            "type": "string",
                            "description": "Optional human-readable source description.",
                        },
                        "group_id": {
                            "type": "string",
                            "description": "Optional Graphiti group identifier.",
                        },
                    },
                    required=("name", "episode_body"),
                ),
                permission="write_memory",
                audit_level="write",
                mutating=True,
            ),
            external_mcp_tool_definition(
                name="get_episodes",
                description="Retrieve recent Graphiti episodes.",
                parameters=object_schema(
                    {
                        "group_id": {
                            "type": "string",
                            "description": "Optional Graphiti group identifier.",
                        },
                        "last_n": {
                            "type": "integer",
                            "description": "Optional number of recent episodes.",
                        },
                    }
                ),
                permission="read_memory",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="get_entity_edge",
                description="Fetch a specific Graphiti entity edge by UUID.",
                parameters=object_schema(
                    {
                        "uuid": {
                            "type": "string",
                            "description": "Entity edge UUID.",
                        }
                    },
                    required=("uuid",),
                ),
                permission="read_memory",
                audit_level="read",
            ),
        ),
    )


def linear_external_mcp_adapter() -> RuntimeExternalMcpAdapter:
    """Build the Linear Streamable HTTP MCP execution adapter."""
    read_policy = {
        "permission": "read_linear",
        "audit_level": "read",
    }
    write_policy = {
        "permission": "write_linear",
        "audit_level": "write",
        "mutating": True,
    }
    id_property = {
        "id": {
            "type": "string",
            "description": "Linear entity ID or key.",
        }
    }
    pagination_properties = {
        "limit": {
            "type": "integer",
            "description": DESCRIPTION_OPTIONAL_MAX_RESULTS,
        }
    }
    return RuntimeExternalMcpAdapter(
        server="linear",
        display_name="Linear",
        transport="http",
        exposed_server="linear-server",
        tool_definitions=(
            external_mcp_tool_definition(
                name="list_teams",
                description="List Linear teams available to the authenticated user.",
                parameters=object_schema(pagination_properties),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="get_team",
                description="Get one Linear team by ID or key.",
                parameters=object_schema(id_property, required=("id",)),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="list_projects",
                description="List Linear projects.",
                parameters=object_schema(
                    {
                        "team": {
                            "type": "string",
                            "description": DESCRIPTION_OPTIONAL_TEAM_ID_OR_KEY,
                        },
                        **pagination_properties,
                    }
                ),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="get_project",
                description="Get one Linear project by ID.",
                parameters=object_schema(id_property, required=("id",)),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="create_project",
                description="Create a Linear project.",
                parameters=object_schema(
                    {
                        "team": {
                            "type": "string",
                            "description": "Team ID or key.",
                        },
                        "name": {
                            "type": "string",
                            "description": "Project name.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional project description.",
                        },
                    },
                    required=("team", "name"),
                ),
                **write_policy,
            ),
            external_mcp_tool_definition(
                name="update_project",
                description="Update a Linear project.",
                parameters=object_schema(
                    {
                        **id_property,
                        "name": {
                            "type": "string",
                            "description": "Optional project name.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional project description.",
                        },
                        "state": {
                            "type": "string",
                            "description": "Optional project state.",
                        },
                    },
                    required=("id",),
                ),
                **write_policy,
            ),
            external_mcp_tool_definition(
                name="list_issues",
                description="List Linear issues.",
                parameters=object_schema(
                    {
                        "team": {
                            "type": "string",
                            "description": DESCRIPTION_OPTIONAL_TEAM_ID_OR_KEY,
                        },
                        "project": {
                            "type": "string",
                            "description": "Optional project ID.",
                        },
                        "query": {
                            "type": "string",
                            "description": "Optional text query.",
                        },
                        **pagination_properties,
                    }
                ),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="get_issue",
                description="Get one Linear issue by ID or key.",
                parameters=object_schema(id_property, required=("id",)),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="create_issue",
                description="Create a Linear issue.",
                parameters=object_schema(
                    {
                        "team": {
                            "type": "string",
                            "description": "Team ID or key.",
                        },
                        "project": {
                            "type": "string",
                            "description": "Optional project ID.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional issue description.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Optional Linear priority.",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional labels.",
                        },
                    },
                    required=("team", "title"),
                ),
                **write_policy,
            ),
            external_mcp_tool_definition(
                name="update_issue",
                description="Update a Linear issue.",
                parameters=object_schema(
                    {
                        **id_property,
                        "title": {
                            "type": "string",
                            "description": "Optional issue title.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional issue description.",
                        },
                        "state": {
                            "type": "string",
                            "description": "Optional issue state or state ID.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Optional Linear priority.",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Optional assignee ID.",
                        },
                    },
                    required=("id",),
                ),
                **write_policy,
            ),
            external_mcp_tool_definition(
                name="list_comments",
                description="List comments on a Linear issue.",
                parameters=object_schema(
                    {
                        "issueId": {
                            "type": "string",
                            "description": "Linear issue ID.",
                        },
                        **pagination_properties,
                    },
                    required=("issueId",),
                ),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="create_comment",
                description="Create a comment on a Linear issue.",
                parameters=object_schema(
                    {
                        "issueId": {
                            "type": "string",
                            "description": "Linear issue ID.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Comment body.",
                        },
                    },
                    required=("issueId", "body"),
                ),
                **write_policy,
            ),
            external_mcp_tool_definition(
                name="list_issue_statuses",
                description="List Linear issue statuses for a team.",
                parameters=object_schema(
                    {
                        "team": {
                            "type": "string",
                            "description": DESCRIPTION_OPTIONAL_TEAM_ID_OR_KEY,
                        }
                    }
                ),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="list_issue_labels",
                description="List Linear issue labels.",
                parameters=object_schema(
                    {
                        "team": {
                            "type": "string",
                            "description": DESCRIPTION_OPTIONAL_TEAM_ID_OR_KEY,
                        },
                        **pagination_properties,
                    }
                ),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="list_users",
                description="List Linear users.",
                parameters=object_schema(pagination_properties),
                **read_policy,
            ),
            external_mcp_tool_definition(
                name="get_user",
                description="Get one Linear user by ID.",
                parameters=object_schema(id_property, required=("id",)),
                **read_policy,
            ),
        ),
    )


def electron_external_mcp_adapter() -> RuntimeExternalMcpAdapter:
    """Build the Electron browser automation MCP execution adapter."""
    return RuntimeExternalMcpAdapter(
        server="electron",
        display_name="Electron",
        tool_definitions=(
            external_mcp_tool_definition(
                name="get_electron_window_info",
                description="Get information about running Electron windows.",
                parameters=object_schema(),
                permission="read_browser_state",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="take_screenshot",
                description="Capture a compressed screenshot of the Electron app.",
                parameters=object_schema(),
                permission="read_browser_state",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="send_command_to_electron",
                description="Send a UI automation command to the Electron app.",
                parameters=object_schema(
                    {
                        "command": {
                            "type": "string",
                            "description": "Electron automation command to run.",
                        },
                        "args": {
                            "type": "object",
                            "description": "Command-specific arguments.",
                        },
                    },
                    required=("command",),
                ),
                permission="run_browser_automation",
                audit_level="command",
                mutating=True,
            ),
            external_mcp_tool_definition(
                name="read_electron_logs",
                description="Read console logs from the Electron app.",
                parameters=object_schema(
                    {
                        "limit": {
                            "type": "integer",
                            "description": "Optional maximum log entries to return.",
                        }
                    }
                ),
                permission="read_browser_logs",
                audit_level="read",
            ),
        ),
    )


def puppeteer_external_mcp_adapter() -> RuntimeExternalMcpAdapter:
    """Build the Puppeteer browser automation MCP execution adapter."""
    browser_command_policy = {
        "permission": "run_browser_automation",
        "audit_level": "command",
        "mutating": True,
    }
    return RuntimeExternalMcpAdapter(
        server="puppeteer",
        display_name="Puppeteer",
        tool_definitions=(
            external_mcp_tool_definition(
                name="puppeteer_connect_active_tab",
                description="Connect to the active browser tab.",
                parameters=object_schema(),
                permission="read_browser_state",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="puppeteer_navigate",
                description="Navigate the browser to a URL.",
                parameters=object_schema(
                    {
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to.",
                        }
                    },
                    required=("url",),
                ),
                **browser_command_policy,
            ),
            external_mcp_tool_definition(
                name="puppeteer_screenshot",
                description="Capture a browser screenshot.",
                parameters=object_schema(
                    {
                        "name": {
                            "type": "string",
                            "description": "Optional screenshot label.",
                        },
                        "selector": {
                            "type": "string",
                            "description": "Optional CSS selector to capture.",
                        },
                    }
                ),
                permission="read_browser_state",
                audit_level="read",
            ),
            external_mcp_tool_definition(
                name="puppeteer_click",
                description="Click an element by CSS selector.",
                parameters=object_schema(
                    {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to click.",
                        }
                    },
                    required=("selector",),
                ),
                **browser_command_policy,
            ),
            external_mcp_tool_definition(
                name="puppeteer_fill",
                description="Fill an input field by CSS selector.",
                parameters=object_schema(
                    {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the input field.",
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to enter.",
                        },
                    },
                    required=("selector", "value"),
                ),
                **browser_command_policy,
            ),
            external_mcp_tool_definition(
                name="puppeteer_select",
                description="Select an option in a dropdown.",
                parameters=object_schema(
                    {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the select element.",
                        },
                        "value": {
                            "type": "string",
                            "description": "Option value to select.",
                        },
                    },
                    required=("selector", "value"),
                ),
                **browser_command_policy,
            ),
            external_mcp_tool_definition(
                name="puppeteer_hover",
                description="Hover over an element by CSS selector.",
                parameters=object_schema(
                    {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to hover.",
                        }
                    },
                    required=("selector",),
                ),
                **browser_command_policy,
            ),
            external_mcp_tool_definition(
                name="puppeteer_evaluate",
                description="Execute JavaScript in the browser page.",
                parameters=object_schema(
                    {
                        "script": {
                            "type": "string",
                            "description": "JavaScript expression or script to evaluate.",
                        }
                    },
                    required=("script",),
                ),
                permission="run_browser_script",
                audit_level="command",
                mutating=True,
            ),
        ),
    )


EXTERNAL_MCP_ADAPTERS: dict[str, RuntimeExternalMcpAdapter] = {
    adapter.server: adapter
    for adapter in (
        context7_external_mcp_adapter(),
        graphiti_external_mcp_adapter(),
        linear_external_mcp_adapter(),
        electron_external_mcp_adapter(),
        puppeteer_external_mcp_adapter(),
    )
}


def custom_external_mcp_server_configs(
    project_mcp_config: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    """Return custom MCP server configs from project-level MCP settings."""
    if not project_mcp_config:
        return ()
    raw_servers = project_mcp_config.get(CUSTOM_MCP_SERVERS_CONFIG_KEY, ())
    if isinstance(raw_servers, str):
        try:
            raw_servers = json.loads(raw_servers)
        except json.JSONDecodeError:
            return ()
    if isinstance(raw_servers, Mapping):
        raw_servers = tuple(raw_servers.values())
    if not isinstance(raw_servers, (list, tuple)):
        return ()
    return tuple(server for server in raw_servers if isinstance(server, Mapping))


def custom_external_mcp_server_config(
    server: str,
    *,
    project_mcp_config: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Return one custom MCP server config by normalized server id."""
    normalized = normalize_mcp_server_name(server)
    for custom_server in custom_external_mcp_server_configs(project_mcp_config):
        server_id = normalize_mcp_server_name(str(custom_server.get("id") or ""))
        if server_id == normalized:
            return custom_server
    return None


def custom_external_mcp_catalog_entry(
    server: str,
    *,
    project_mcp_config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a catalog-like entry for a configured custom MCP server."""
    custom_server = custom_external_mcp_server_config(
        server,
        project_mcp_config=project_mcp_config,
    )
    if custom_server is None:
        return {}

    server_type = str(custom_server.get("type") or "command")
    transport = "http" if server_type == "http" else "stdio"
    entry: dict[str, Any] = {
        "display_name": str(custom_server.get("name") or server),
        "bridgeable": False,
        "external_bridgeable": True,
        "enabled_default": True,
        "transport": transport,
        "custom": True,
        "notes": str(
            custom_server.get("description") or "User-defined custom MCP server."
        ),
    }
    if transport == "http":
        entry["url"] = str(custom_server.get("url") or "")
    else:
        entry["command"] = str(custom_server.get("command") or "")
        entry["args"] = tuple(str(arg) for arg in custom_server.get("args", ()) or ())
    return entry


def mcp_server_catalog_entry(
    server: str,
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the static or custom MCP catalog entry for a server."""
    normalized = normalize_mcp_server_name(server)
    if normalized in MCP_SERVER_CATALOG:
        return dict(MCP_SERVER_CATALOG[normalized])
    return custom_external_mcp_catalog_entry(
        normalized,
        project_mcp_config=project_mcp_config,
    )


def custom_external_mcp_tool_definitions(
    custom_server: Mapping[str, Any],
) -> tuple[RuntimeExternalMcpToolDefinition, ...]:
    """Return provider tool definitions from a cached MCP tools/list payload."""
    raw_tools = custom_server.get("tools", ())
    if not isinstance(raw_tools, (list, tuple)):
        return ()

    definitions: list[RuntimeExternalMcpToolDefinition] = []
    seen_tool_names: set[str] = set()
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, Mapping):
            continue
        name = str(raw_tool.get("name") or "").strip()
        if not name or name in seen_tool_names:
            continue
        seen_tool_names.add(name)
        definitions.append(
            external_mcp_tool_definition(
                name=name,
                description=str(
                    raw_tool.get("description") or f"Call custom MCP tool {name}."
                ),
                parameters=normalize_mcp_input_schema(raw_tool),
                permission="call_custom_mcp",
                audit_level="command",
                mutating=True,
            )
        )
    return tuple(definitions)


def custom_external_mcp_generic_tool_definition() -> RuntimeExternalMcpToolDefinition:
    """Return the fallback generic custom MCP call tool definition."""
    return external_mcp_tool_definition(
        name="call_tool",
        description=(
            "Call a named tool on the configured custom MCP server. "
            "Use tools/list smoke diagnostics to discover live tool names."
        ),
        parameters=object_schema(
            {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the MCP tool to call.",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the MCP tool.",
                },
            },
            required=("tool_name",),
        ),
        permission="call_custom_mcp",
        audit_level="command",
        mutating=True,
        target_name_argument="tool_name",
    )


def normalize_mcp_input_schema(raw_tool: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one MCP tools/list input schema for direct-provider tools."""
    raw_schema = (
        raw_tool.get("inputSchema")
        or raw_tool.get("input_schema")
        or raw_tool.get("parameters")
    )
    if not isinstance(raw_schema, Mapping):
        return object_schema()

    schema = dict(raw_schema)
    if schema.get("type") != "object":
        return object_schema()

    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        schema["properties"] = dict(properties)
    else:
        schema["properties"] = {}

    required = schema.get("required")
    if isinstance(required, (list, tuple)):
        schema["required"] = [str(name) for name in required if str(name)]
    else:
        schema.pop("required", None)
    return schema


def custom_external_mcp_adapter(
    server: str,
    *,
    project_mcp_config: Mapping[str, Any] | None,
) -> RuntimeExternalMcpAdapter | None:
    """Build a conservative generic adapter for a custom MCP server."""
    custom_server = custom_external_mcp_server_config(
        server,
        project_mcp_config=project_mcp_config,
    )
    if custom_server is None:
        return None

    server_id = normalize_mcp_server_name(str(custom_server.get("id") or server))
    server_name = str(custom_server.get("name") or server_id)
    server_type = str(custom_server.get("type") or "command")
    tool_definitions = [
        *custom_external_mcp_tool_definitions(custom_server),
        custom_external_mcp_generic_tool_definition(),
    ]
    deduped_tool_definitions: list[RuntimeExternalMcpToolDefinition] = []
    seen_tool_names: set[str] = set()
    for definition in tool_definitions:
        if definition.name in seen_tool_names:
            continue
        seen_tool_names.add(definition.name)
        deduped_tool_definitions.append(definition)
    return RuntimeExternalMcpAdapter(
        server=server_id,
        display_name=server_name,
        transport="http" if server_type == "http" else "stdio",
        exposed_server=server_id,
        tool_definitions=tuple(deduped_tool_definitions),
    )


def external_mcp_adapter_for(
    server: str,
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
) -> RuntimeExternalMcpAdapter | None:
    """Return the registered external MCP execution adapter for a server."""
    normalized = normalize_mcp_server_name(server)
    adapter = EXTERNAL_MCP_ADAPTERS.get(normalized)
    if adapter is not None:
        return adapter
    return custom_external_mcp_adapter(
        normalized,
        project_mcp_config=project_mcp_config,
    )


def registered_external_mcp_servers(
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return external MCP servers with executable bridge adapters."""
    servers = list(EXTERNAL_MCP_ADAPTERS)
    for custom_server in custom_external_mcp_server_configs(project_mcp_config):
        server_id = normalize_mcp_server_name(str(custom_server.get("id") or ""))
        if server_id and server_id not in servers:
            servers.append(server_id)
    return tuple(servers)


class RuntimeExternalMcpClientError(RuntimeError):
    """Raised when a provider-neutral external MCP call fails."""


@dataclass(frozen=True)
class RuntimeExternalMcpContractCheck:
    """Result of checking adapter schemas against a live MCP server."""

    server: str
    ok: bool
    status: str
    reason: str
    transport: str | None = None
    adapter_tools: tuple[str, ...] = ()
    server_tools: tuple[str, ...] = ()
    adapter_tools_missing_on_server: tuple[str, ...] = ()
    server_tools_missing_in_adapter: tuple[str, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the contract check for CLI/UI diagnostics."""
        return {
            "server": self.server,
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "transport": self.transport,
            "adapter_tools": list(self.adapter_tools),
            "server_tools": list(self.server_tools),
            "adapter_tools_missing_on_server": list(
                self.adapter_tools_missing_on_server
            ),
            "server_tools_missing_in_adapter": list(
                self.server_tools_missing_in_adapter
            ),
            "error": self.error,
        }


class RuntimeExternalMcpClient:
    """Minimal stdio MCP client for provider-neutral external tool calls."""

    def __init__(
        self,
        *,
        server: str,
        command: str,
        args: tuple[str, ...] = (),
        cwd: Path | None = None,
        timeout_seconds: float = DEFAULT_EXTERNAL_MCP_TIMEOUT_SECONDS,
        protocol_version: str | None = None,
    ):
        self.server = server
        self.command = command
        self.args = args
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        self.protocol_version = (
            protocol_version
            or os.environ.get(EXTERNAL_MCP_PROTOCOL_VERSION_ENV)
            or DEFAULT_EXTERNAL_MCP_PROTOCOL_VERSION
        )
        self._request_id = 0
        self._process: asyncio.subprocess.Process | None = None

    async def __aenter__(self) -> RuntimeExternalMcpClient:
        await self.open()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def open(self) -> RuntimeExternalMcpClient:
        """Open and initialize a reusable stdio MCP session."""
        if self._process is not None and self._process.returncode is None:
            return self
        self._process = await self._start_process()
        try:
            await self._initialize(self._process)
        except Exception:
            await self.close()
            raise
        return self

    async def close(self) -> None:
        """Close the reusable stdio MCP session if one is open."""
        process = self._process
        if process is None:
            return
        self._process = None
        await self._close_process(process)

    async def call_tool(
        self, *, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Start a stdio MCP server, call one tool, and shut it down."""
        if self._process is not None and self._process.returncode is None:
            return await self._request(
                self._process,
                "tools/call",
                {"name": name, "arguments": arguments},
            )
        return await self._with_process(
            method="tools/call",
            params={"name": name, "arguments": arguments},
        )

    async def list_tools(self) -> dict[str, Any]:
        """Start a stdio MCP server, list tools, and shut it down."""
        if self._process is not None and self._process.returncode is None:
            return await self._request(self._process, "tools/list", {})
        return await self._with_process(method="tools/list", params={})

    async def _with_process(
        self,
        *,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Run one initialized stdio MCP request against a short-lived process."""
        process = await self._start_process()
        try:
            await self._initialize(process)
            return await self._request(process, method, params)
        finally:
            await self._close_process(process)

    async def _start_process(self) -> asyncio.subprocess.Process:
        try:
            return await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                cwd=str(self.cwd) if self.cwd else None,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as e:
            raise RuntimeExternalMcpClientError(
                f"Failed to start MCP server {self.server}: {e}"
            ) from e

    async def _initialize(self, process: asyncio.subprocess.Process) -> None:
        await self._request(
            process,
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "auto-code-runtime-mcp-bridge",
                    "version": "0",
                },
            },
        )
        await self._notification(process, "notifications/initialized", {})

    async def _request(
        self,
        process: asyncio.subprocess.Process,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        await self._write_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
        )
        return await self._read_response(process, request_id)

    async def _notification(
        self,
        process: asyncio.subprocess.Process,
        method: str,
        params: dict[str, Any],
    ) -> None:
        await self._write_message(
            process,
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            },
        )

    async def _write_message(
        self,
        process: asyncio.subprocess.Process,
        payload: dict[str, Any],
    ) -> None:
        if process.stdin is None:
            raise RuntimeExternalMcpClientError(
                f"MCP server {self.server} stdin is unavailable."
            )
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
        process.stdin.write(data)
        await asyncio.wait_for(process.stdin.drain(), timeout=self.timeout_seconds)

    async def _read_response(
        self,
        process: asyncio.subprocess.Process,
        request_id: int,
    ) -> dict[str, Any]:
        if process.stdout is None:
            raise RuntimeExternalMcpClientError(
                f"MCP server {self.server} stdout is unavailable."
            )
        while True:
            line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=self.timeout_seconds,
            )
            if not line:
                stderr = await self._read_stderr(process)
                suffix = f": {stderr}" if stderr else ""
                raise RuntimeExternalMcpClientError(
                    f"MCP server {self.server} closed stdout before response{suffix}."
                )
            try:
                message = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                if isinstance(error, dict):
                    error_message = str(error.get("message") or error)
                else:
                    error_message = str(error)
                raise RuntimeExternalMcpClientError(
                    f"MCP server {self.server} returned error: {error_message}"
                )
            result = message.get("result", {})
            if isinstance(result, dict):
                return result
            return {"content": [{"type": "text", "text": str(result)}]}

    async def _read_stderr(self, process: asyncio.subprocess.Process) -> str:
        if process.stderr is None:
            return ""
        try:
            data = await asyncio.wait_for(process.stderr.read(), timeout=1.0)
        except TimeoutError:
            return ""
        return data.decode("utf-8", errors="replace").strip()[:1000]

    async def _close_process(self, process: asyncio.subprocess.Process) -> None:
        if process.stdin is not None and not process.stdin.is_closing():
            process.stdin.close()
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2.0)
        except TimeoutError:
            process.kill()
            await process.wait()


class RuntimeExternalMcpHttpClient:
    """Minimal Streamable HTTP MCP client for provider-neutral tool calls."""

    def __init__(
        self,
        *,
        server: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = DEFAULT_EXTERNAL_MCP_TIMEOUT_SECONDS,
        protocol_version: str | None = None,
    ):
        self.server = server
        self.url = url
        self.headers = dict(headers or {})
        self.timeout_seconds = timeout_seconds
        self.protocol_version = (
            protocol_version
            or os.environ.get(EXTERNAL_MCP_PROTOCOL_VERSION_ENV)
            or DEFAULT_EXTERNAL_MCP_HTTP_PROTOCOL_VERSION
        )
        self._request_id = 0
        self._session_id: str | None = None
        self._client: Any | None = None

    async def __aenter__(self) -> RuntimeExternalMcpHttpClient:
        await self.open()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def open(self) -> RuntimeExternalMcpHttpClient:
        """Open and initialize a reusable HTTP MCP session."""
        if self._client is not None:
            return self
        try:
            import httpx
        except ImportError as e:
            raise RuntimeExternalMcpClientError(
                "httpx is required for HTTP MCP transport."
            ) from e
        self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            await self._initialize(self._client)
        except Exception:
            await self.close()
            raise
        return self

    async def close(self) -> None:
        """Close the reusable HTTP MCP session if one is open."""
        client = self._client
        if client is None:
            return
        try:
            await self._close_session(client)
        finally:
            self._client = None
            self._session_id = None
            await client.aclose()

    async def call_tool(
        self, *, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Initialize an HTTP MCP session, call one tool, and close it."""
        if self._client is not None:
            return await self._request(
                self._client,
                "tools/call",
                {"name": name, "arguments": arguments},
            )
        return await self._with_http_session(
            method="tools/call",
            params={"name": name, "arguments": arguments},
        )

    async def list_tools(self) -> dict[str, Any]:
        """Initialize an HTTP MCP session, list tools, and close it."""
        if self._client is not None:
            return await self._request(self._client, "tools/list", {})
        return await self._with_http_session(method="tools/list", params={})

    async def _with_http_session(
        self,
        *,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Run one initialized Streamable HTTP MCP request."""
        try:
            import httpx
        except ImportError as e:
            raise RuntimeExternalMcpClientError(
                "httpx is required for HTTP MCP transport."
            ) from e

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                await self._initialize(client)
                return await self._request(client, method, params)
            finally:
                await self._close_session(client)

    async def _initialize(self, client: Any) -> None:
        result = await self._request(
            client,
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "auto-code-runtime-mcp-bridge",
                    "version": "0",
                },
            },
            include_session=False,
        )
        negotiated = str(result.get("protocolVersion") or "")
        if negotiated:
            self.protocol_version = negotiated
        await self._notification(client, "notifications/initialized", {})

    async def _request(
        self,
        client: Any,
        method: str,
        params: dict[str, Any],
        *,
        include_session: bool = True,
    ) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        message = await self._post_jsonrpc(
            client,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
            request_id=request_id,
            include_session=include_session,
        )
        if "error" in message:
            error = message["error"]
            if isinstance(error, dict):
                error_message = str(error.get("message") or error)
            else:
                error_message = str(error)
            raise RuntimeExternalMcpClientError(
                f"MCP server {self.server} returned error: {error_message}"
            )
        result = message.get("result", {})
        if isinstance(result, dict):
            return result
        return {"content": [{"type": "text", "text": str(result)}]}

    async def _notification(
        self,
        client: Any,
        method: str,
        params: dict[str, Any],
    ) -> None:
        await self._post_jsonrpc(
            client,
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            },
            request_id=None,
            include_session=True,
            expect_response=False,
        )

    async def _post_jsonrpc(
        self,
        client: Any,
        payload: dict[str, Any],
        *,
        request_id: int | None,
        include_session: bool,
        expect_response: bool = True,
    ) -> dict[str, Any]:
        try:
            async with client.stream(
                "POST",
                self.url,
                json=payload,
                headers=self._request_headers(include_session=include_session),
            ) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self._session_id = session_id

                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    body = body.strip()[:1000]
                    suffix = f": {body}" if body else ""
                    raise RuntimeExternalMcpClientError(
                        f"HTTP MCP server {self.server} returned "
                        f"{response.status_code}{suffix}"
                    )

                if not expect_response or response.status_code == 202:
                    return {}

                message = await self._parse_http_message(
                    response=response,
                    request_id=request_id,
                )
        except RuntimeExternalMcpClientError:
            raise
        except Exception as e:
            raise RuntimeExternalMcpClientError(
                f"Failed to call HTTP MCP server {self.server}: {e}"
            ) from e
        if not message:
            raise RuntimeExternalMcpClientError(
                f"HTTP MCP server {self.server} returned no JSON-RPC response."
            )
        return message

    def _request_headers(self, *, include_session: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self.protocol_version,
            **self.headers,
        }
        if include_session and self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    async def _parse_http_message(
        self,
        *,
        response: Any,
        request_id: int | None,
    ) -> dict[str, Any] | None:
        content_type = str(response.headers.get("content-type", "")).lower()
        if "text/event-stream" in content_type:
            return await self._read_sse_message(response, request_id=request_id)
        data = await response.aread()
        try:
            message = json.loads(data.decode("utf-8"))
        except Exception as e:
            raise RuntimeExternalMcpClientError(
                f"HTTP MCP server {self.server} returned invalid JSON: {e}"
            ) from e
        if isinstance(message, dict):
            if request_id is not None and message.get("id") != request_id:
                raise RuntimeExternalMcpClientError(
                    f"HTTP MCP server {self.server} returned mismatched "
                    "JSON-RPC response id."
                )
            return message
        return {"result": message}

    async def _read_sse_message(
        self,
        response: Any,
        *,
        request_id: int | None,
    ) -> dict[str, Any] | None:
        data_lines: list[str] = []
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
                continue
            if line.strip():
                continue
            message = self._decode_sse_data(data_lines, request_id=request_id)
            if message is not None:
                return message
            data_lines = []
        return self._decode_sse_data(data_lines, request_id=request_id)

    def _parse_sse_message(
        self,
        text: str,
        *,
        request_id: int | None,
    ) -> dict[str, Any] | None:
        data_lines: list[str] = []
        for line in text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
                continue
            if line.strip():
                continue
            message = self._decode_sse_data(data_lines, request_id=request_id)
            if message is not None:
                return message
            data_lines = []
        return self._decode_sse_data(data_lines, request_id=request_id)

    def _decode_sse_data(
        self,
        data_lines: list[str],
        *,
        request_id: int | None,
    ) -> dict[str, Any] | None:
        if not data_lines:
            return None
        try:
            message = json.loads("\n".join(data_lines))
        except json.JSONDecodeError as e:
            raise RuntimeExternalMcpClientError(
                f"HTTP MCP server {self.server} returned invalid SSE JSON: {e}"
            ) from e
        if not isinstance(message, dict):
            return {"result": message}
        if request_id is None or message.get("id") == request_id:
            return message
        return None

    async def _close_session(self, client: Any) -> None:
        if not self._session_id:
            return
        try:
            await client.delete(
                self.url,
                headers=self._request_headers(include_session=True),
            )
        except Exception:
            return


class RuntimeMcpBridge:
    """Bridge local Auto Code MCP tools into generic runtimes."""

    def __init__(
        self,
        *,
        spec_dir: Path,
        project_dir: Path,
        allowed_tools: set[str],
        allowed_mcp_permissions: set[str] | None = None,
        requested_servers: tuple[str, ...] = (),
        project_mcp_config: Mapping[str, Any] | None = None,
        environment: Mapping[str, str] | None = None,
    ):
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.allowed_tools = allowed_tools
        self.allowed_mcp_permissions = normalize_mcp_allowed_permissions(
            allowed_mcp_permissions
        )
        self.requested_servers = requested_servers
        self.project_mcp_config = project_mcp_config
        self.environment = environment
        self._external_mcp_sessions: dict[str, Any] = {}
        local_tools = load_auto_claude_bridge_tools(
            spec_dir=spec_dir,
            project_dir=project_dir,
            allowed_tools=allowed_tools,
        )
        external_tools = load_external_mcp_bridge_tools(
            requested_servers=requested_servers,
            project_dir=project_dir,
            project_mcp_config=project_mcp_config,
            environment=environment,
            session_cache=self._external_mcp_sessions,
        )
        self._tools = [*local_tools, *external_tools]
        self._tools_by_name = {tool.exposed_name: tool for tool in self._tools} | {
            tool.name: tool for tool in self._tools
        }

    async def __aenter__(self) -> RuntimeMcpBridge:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

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
        configured_permissions = configured_mcp_allowed_permissions(agent_session)
        project_mcp_config = configured_mcp_project_config(agent_session)
        if configured_tools is None and resolved_agent_type:
            config = get_agent_config(resolved_agent_type)
            configured_tools = config.get("auto_claude_tools", [])
            configured_servers = config.get("mcp_servers", [])
            if configured_permissions is None:
                configured_permissions = configured_mcp_allowed_permissions(config)
            if project_mcp_config is None:
                project_mcp_config = configured_mcp_project_config(config)
        if project_mcp_config is None:
            project_mcp_config = load_project_mcp_config_for_runtime(project_dir)
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
            allowed_mcp_permissions=configured_permissions,
            requested_servers=requested_servers,
            project_mcp_config=project_mcp_config,
        )
        return bridge if bridge.has_tools or bridge.requested_servers else None

    @property
    def has_tools(self) -> bool:
        return bool(self._tools)

    @property
    def available_servers(self) -> tuple[str, ...]:
        """Return MCP servers available through this bridge."""
        servers: list[str] = []
        for tool in self._tools:
            if tool.server not in servers:
                servers.append(tool.server)
        return tuple(servers)

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
        permission_decision = check_mcp_tool_permission(
            spec.policy,
            allowed_permissions=self.allowed_mcp_permissions,
        )
        audit_base.update(permission_decision.to_audit_dict())
        if not permission_decision.allowed:
            audit_artifact = write_mcp_bridge_audit_event(
                self.spec_dir,
                {
                    **audit_base,
                    "status": "denied",
                    "reason": permission_decision.reason,
                },
            )
            return ToolActionResult(
                tool=spec.exposed_name,
                ok=False,
                message=(
                    "Bridged MCP tool permission denied: "
                    f"{spec.policy.permission} is not allowed for {spec.exposed_name}."
                ),
                data={
                    "server": spec.server,
                    "name": spec.name,
                    **spec.policy.to_dict(),
                    "permission_allowed": False,
                    "permission_denial_reason": permission_decision.reason,
                    "allowed_permissions": (
                        list(permission_decision.allowed_permissions)
                        if permission_decision.allowed_permissions is not None
                        else None
                    ),
                    "audit_artifact": audit_artifact,
                },
            )
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
                    **permission_decision.to_audit_dict(),
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
                **permission_decision.to_audit_dict(),
                "audit_artifact": audit_artifact,
                "result": result,
            },
        )

    async def close(self) -> None:
        """Close reusable external MCP sessions opened by this bridge."""
        sessions = list(self._external_mcp_sessions.values())
        self._external_mcp_sessions.clear()
        for session in sessions:
            close = getattr(session, "close", None)
            if close is None:
                continue
            result = close()
            if inspect.isawaitable(result):
                await result

    def report(self) -> dict[str, Any]:
        """Return compact bridge metadata for artifacts/debug output."""
        server_statuses = describe_mcp_server_statuses(
            requested_servers=self.requested_servers,
            available_servers=self.available_servers,
            native_available=False,
            project_mcp_config=self.project_mcp_config,
            environment=self.environment,
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
            "permission_policy": {
                "mode": "allow_all"
                if self.allowed_mcp_permissions is None
                else "allowlist",
                "allowed_permissions": (
                    None
                    if self.allowed_mcp_permissions is None
                    else sorted(self.allowed_mcp_permissions)
                ),
            },
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
            project_mcp_config=self.project_mcp_config,
            environment=self.environment,
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
    external_client_enabled: bool | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
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
                external_client_enabled=external_client_enabled,
                project_mcp_config=project_mcp_config,
                environment=environment,
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
                "Auto Code can bridge configured MCP tools into this runtime; "
                "external MCP servers execute only when the provider-neutral "
                "external MCP client is enabled and configured."
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
                external_client_enabled=external_client_enabled,
                project_mcp_config=project_mcp_config,
                environment=environment,
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
            external_client_enabled=external_client_enabled,
            project_mcp_config=project_mcp_config,
            environment=environment,
        ),
    )


def external_mcp_client_enabled(
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Return whether the provider-neutral external MCP client is enabled."""
    value = mcp_config_or_env_value(
        EXTERNAL_MCP_CLIENT_ENV,
        project_mcp_config=project_mcp_config,
        environment=environment,
    )
    return bool_from_mcp_value(value, default=False)


def describe_external_mcp_server_health(
    server: str,
    *,
    external_client_enabled: bool | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> RuntimeExternalMcpServerHealth:
    """Return external MCP client readiness for one catalog server."""
    server = normalize_mcp_server_name(server)
    catalog_entry = mcp_server_catalog_entry(
        server,
        project_mcp_config=project_mcp_config,
    )
    adapter = external_mcp_adapter_for(
        server,
        project_mcp_config=project_mcp_config,
    )
    display_name = str(catalog_entry.get("display_name", server))
    bridgeable = bool(catalog_entry.get("external_bridgeable", False))
    client_enabled = (
        external_mcp_client_enabled(
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        if external_client_enabled is None
        else external_client_enabled
    )
    enabled_env = catalog_entry.get("enabled_env")
    enabled_default = bool(catalog_entry.get("enabled_default", True))
    server_enabled = bool(
        bool_from_mcp_value(
            mcp_config_or_env_value(
                str(enabled_env),
                project_mcp_config=project_mcp_config,
                environment=environment,
            )
            if enabled_env
            else None,
            default=enabled_default,
        )
    )
    required_env = tuple(str(name) for name in catalog_entry.get("required_env", ()))
    missing_env = tuple(
        name
        for name in required_env
        if not mcp_config_or_env_value(
            name,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
    )
    concrete_servers = tuple(
        str(name) for name in catalog_entry.get("concrete_servers", ())
    )
    transport = str(catalog_entry.get("transport") or "") or None
    command = str(catalog_entry.get("command") or "") or None
    url_env = catalog_entry.get("url_env")
    url = (
        mcp_config_or_env_value(
            str(url_env),
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        if url_env
        else catalog_entry.get("url")
    )
    transport_supported = bool(
        adapter and adapter.transport_supported(transport=transport)
    )
    execution_supported = bool(
        adapter
        and adapter.execution_supported(
            transport=transport,
            command=command,
            url=str(url or "") or None,
        )
    )
    known_tools = (
        adapter.tool_names
        if adapter
        else tuple(str(name) for name in catalog_entry.get("tools", ()))
    )
    configured = bool(
        bridgeable and server_enabled and not missing_env and not concrete_servers
    )
    if not bridgeable:
        status: ExternalMcpHealthStatus = "not_bridgeable"
        reason = "No external MCP client bridge policy is registered for this server."
    elif not server_enabled:
        status = "server_disabled"
        reason = (
            f"{enabled_env} disables this MCP server."
            if enabled_env
            else "This MCP server is disabled by configuration."
        )
    elif missing_env:
        status = "missing_configuration"
        reason = "Missing required external MCP configuration: " + ", ".join(
            missing_env
        )
    elif concrete_servers:
        status = "choose_concrete_server"
        reason = "Select a concrete external MCP server: " + ", ".join(concrete_servers)
    elif not client_enabled:
        status = "client_disabled"
        reason = (
            f"Set {EXTERNAL_MCP_CLIENT_ENV}=true to let non-native runtimes "
            "prepare external MCP connections."
        )
    elif adapter is None:
        status = "adapter_missing"
        reason = (
            "External MCP server configuration is ready, but no executable "
            "adapter is registered for this server."
        )
    elif not transport_supported:
        status = "unsupported_transport"
        reason = (
            "External MCP adapter is registered, but the provider-neutral "
            f"client supports only: {', '.join(SUPPORTED_EXTERNAL_MCP_TRANSPORTS)}."
        )
    else:
        status = "ready_to_connect"
        reason = (
            "External MCP server can execute registered tools through the "
            "provider-neutral client."
        )

    executable_tools = (
        known_tools if status == "ready_to_connect" and execution_supported else ()
    )

    return RuntimeExternalMcpServerHealth(
        server=server,
        display_name=display_name,
        bridgeable=bridgeable,
        client_enabled=client_enabled,
        server_enabled=server_enabled,
        configured=configured,
        status=status,
        reason=reason,
        transport=transport,
        command=command,
        args=tuple(str(arg) for arg in catalog_entry.get("args", ())),
        url=str(url or "") or None,
        enabled_env=str(enabled_env or "") or None,
        required_env=required_env,
        missing_env=missing_env,
        concrete_servers=concrete_servers,
        execution_supported=execution_supported,
        executable_tools=executable_tools,
        adapter_registered=adapter is not None,
        adapter_name=adapter.display_name if adapter else None,
        adapter_transport=adapter.transport if adapter else None,
        adapter_exposed_server=adapter.exposed_server_name if adapter else None,
        transport_supported=transport_supported,
        supported_transports=SUPPORTED_EXTERNAL_MCP_TRANSPORTS,
    )


def build_external_mcp_health_matrix(
    *,
    requested_servers: tuple[str, ...] | None = None,
    external_client_enabled: bool | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build external MCP client readiness diagnostics."""
    servers = normalize_mcp_server_names(requested_servers or tuple(MCP_SERVER_CATALOG))
    return [
        describe_external_mcp_server_health(
            server,
            external_client_enabled=external_client_enabled,
            project_mcp_config=project_mcp_config,
            environment=environment,
        ).to_dict()
        for server in servers
    ]


def executable_external_mcp_servers(
    *,
    requested_servers: tuple[str, ...],
    external_client_enabled: bool | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Return external MCP servers that this layer can actually execute."""
    servers: list[str] = []
    for server in normalize_mcp_server_names(requested_servers):
        health = describe_external_mcp_server_health(
            server,
            external_client_enabled=external_client_enabled,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        if health.ready_to_connect and health.execution_supported:
            servers.append(server)
    return tuple(servers)


def executable_external_mcp_tools(
    *,
    requested_servers: tuple[str, ...],
    external_client_enabled: bool | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Return exposed external MCP tool names that this layer can execute."""
    tools: list[str] = []
    for server in normalize_mcp_server_names(requested_servers):
        health = describe_external_mcp_server_health(
            server,
            external_client_enabled=external_client_enabled,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        if not health.ready_to_connect or not health.execution_supported:
            continue
        adapter = external_mcp_adapter_for(
            server,
            project_mcp_config=project_mcp_config,
        )
        exposed_server = adapter.exposed_server_name if adapter else server
        tools.extend(
            f"mcp__{exposed_server}__{tool}" for tool in health.executable_tools
        )
    return tuple(tools)


def mcp_config_or_env_value(
    key: str,
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> Any:
    """Return an MCP config value from project config, then environment."""
    if project_mcp_config and key in project_mcp_config:
        return project_mcp_config[key]
    source = os.environ if environment is None else environment
    return source.get(key)


def bool_from_mcp_value(value: Any, *, default: bool) -> bool:
    """Parse common env/config booleans with a provided default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def describe_mcp_server_statuses(
    *,
    requested_servers: tuple[str, ...],
    available_servers: tuple[str, ...],
    native_available: bool,
    external_client_enabled: bool | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return per-server MCP bridge status for diagnostics and settings UI."""
    requested_servers = normalize_mcp_server_names(requested_servers)
    available = set(normalize_mcp_server_names(available_servers))
    statuses: list[dict[str, Any]] = []

    for server in requested_servers:
        catalog_entry = mcp_server_catalog_entry(
            server,
            project_mcp_config=project_mcp_config,
        )
        bridgeable = bool(catalog_entry.get("bridgeable", False))
        external_health = describe_external_mcp_server_health(
            server,
            external_client_enabled=external_client_enabled,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        if native_available:
            availability = "available"
            runtime_path = "native"
            reason = "Available through the selected runtime's native MCP support."
        elif server in available and bridgeable:
            availability = "available"
            runtime_path = "local_bridge"
            reason = "Available through Auto Code's local MCP bridge."
        elif server in available and external_health.bridgeable:
            availability = "available"
            runtime_path = "external_bridge"
            reason = "Available through Auto Code's external MCP client bridge."
        elif external_health.bridgeable:
            availability = "unavailable"
            runtime_path = "external_bridge_required"
            reason = external_health.reason
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
                "external_client": external_health.to_dict(),
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
    external_bridge_required_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "external_bridge_required"
    )
    external_bridge_ready_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "external_bridge_required"
        and isinstance(status.get("external_client"), dict)
        and status["external_client"].get("status") == "ready_to_connect"
    )
    external_bridge_adapter_missing_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "external_bridge_required"
        and isinstance(status.get("external_client"), dict)
        and status["external_client"].get("status") == "adapter_missing"
    )
    external_bridge_unsupported_transport_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "external_bridge_required"
        and isinstance(status.get("external_client"), dict)
        and status["external_client"].get("status") == "unsupported_transport"
    )
    unsupported_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "unsupported"
    )
    local_bridged_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "local_bridge"
        and status.get("availability") == "available"
    )
    external_bridged_servers = tuple(
        str(status["server"])
        for status in server_statuses
        if status.get("runtime_path") == "external_bridge"
        and status.get("availability") == "available"
    )
    bridged_servers = (*local_bridged_servers, *external_bridged_servers)
    status = mcp_plan_status(
        requested_servers=requested_servers,
        available_servers=available_servers,
        unavailable_servers=unavailable_servers,
    )
    action_required = mcp_plan_action_required(
        status=status,
        native_required_servers=native_required_servers,
        local_bridge_required_servers=local_bridge_required_servers,
        external_bridge_required_servers=external_bridge_required_servers,
        external_bridge_ready_servers=external_bridge_ready_servers,
        external_bridge_adapter_missing_servers=(
            external_bridge_adapter_missing_servers
        ),
        external_bridge_unsupported_transport_servers=(
            external_bridge_unsupported_transport_servers
        ),
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
        external_bridge_required_servers=external_bridge_required_servers,
        external_bridge_ready_servers=external_bridge_ready_servers,
        external_bridge_adapter_missing_servers=external_bridge_adapter_missing_servers,
        external_bridge_unsupported_transport_servers=(
            external_bridge_unsupported_transport_servers
        ),
        unsupported_servers=unsupported_servers,
        bridged_servers=bridged_servers,
        local_bridged_servers=local_bridged_servers,
        external_bridged_servers=external_bridged_servers,
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
    external_bridge_required_servers: tuple[str, ...],
    external_bridge_ready_servers: tuple[str, ...],
    external_bridge_adapter_missing_servers: tuple[str, ...],
    external_bridge_unsupported_transport_servers: tuple[str, ...],
    unsupported_servers: tuple[str, ...],
) -> str:
    """Return the next action required to satisfy the MCP plan."""
    if status in {"not_requested", "ready"}:
        return "none"
    if unsupported_servers:
        return "register_or_remove_unsupported_servers"
    if external_bridge_unsupported_transport_servers:
        return "implement_external_mcp_transport"
    if external_bridge_adapter_missing_servers:
        return "register_external_mcp_adapter"
    if external_bridge_ready_servers:
        return "wire_external_mcp_tool_execution"
    if external_bridge_required_servers:
        return "configure_external_mcp_client"
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
    if action_required in {
        "configure_external_mcp_client",
        "wire_external_mcp_tool_execution",
        "register_external_mcp_adapter",
        "implement_external_mcp_transport",
    }:
        return "external_mcp_client"
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


def load_external_mcp_bridge_tools(
    *,
    requested_servers: tuple[str, ...],
    project_dir: Path,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
    session_cache: dict[str, Any] | None = None,
) -> list[RuntimeMcpToolSpec]:
    """Load provider-neutral external MCP tool specs that are ready to connect."""
    specs: list[RuntimeMcpToolSpec] = []
    for server in normalize_mcp_server_names(requested_servers):
        health = describe_external_mcp_server_health(
            server,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        if not health.ready_to_connect or not health.execution_supported:
            continue
        adapter = external_mcp_adapter_for(
            server,
            project_mcp_config=project_mcp_config,
        )
        if adapter is not None:
            specs.extend(
                adapter.load_tool_specs(
                    health=health,
                    project_dir=project_dir,
                    project_mcp_config=project_mcp_config,
                    environment=environment,
                    session_cache=session_cache,
                )
            )
    return specs


def load_context7_external_mcp_tools(
    health: RuntimeExternalMcpServerHealth,
    project_dir: Path,
) -> list[RuntimeMcpToolSpec]:
    """Return known Context7 tool schemas backed by the external MCP client."""
    adapter = external_mcp_adapter_for("context7")
    if adapter is None:
        return []
    return adapter.load_tool_specs(health=health, project_dir=project_dir)


def external_mcp_tool_handler(
    *,
    health: RuntimeExternalMcpServerHealth,
    tool_name: str,
    project_dir: Path,
    target_name_argument: str | None = None,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
    session_cache: dict[str, Any] | None = None,
) -> Any:
    """Build an async handler for one external MCP tool."""

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        target_tool_name = tool_name
        target_arguments = args
        if target_name_argument:
            target_tool_name = str(args.get(target_name_argument) or "").strip()
            if not target_tool_name:
                raise RuntimeExternalMcpClientError(
                    f"Missing MCP target tool name argument: {target_name_argument}."
                )
            nested_arguments = args.get("arguments")
            target_arguments = (
                nested_arguments
                if isinstance(nested_arguments, dict)
                else {
                    key: value
                    for key, value in args.items()
                    if key != target_name_argument
                }
            )

        call_kwargs: dict[str, Any] = {
            "health": health,
            "tool_name": target_tool_name,
            "arguments": target_arguments,
            "project_dir": project_dir,
        }
        if project_mcp_config is not None:
            call_kwargs["project_mcp_config"] = project_mcp_config
        if environment is not None:
            call_kwargs["environment"] = environment
        if session_cache is not None:
            call_kwargs["session_cache"] = session_cache
        return await call_external_mcp_tool(**call_kwargs)

    return handler


async def call_external_mcp_tool(
    *,
    health: RuntimeExternalMcpServerHealth,
    tool_name: str,
    arguments: dict[str, Any],
    project_dir: Path,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
    session_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call one external MCP tool through the provider-neutral MCP client."""
    cache_key = f"{health.transport}:{health.server}"
    if health.transport == "stdio" and health.command:
        client = RuntimeExternalMcpClient(
            server=health.server,
            command=health.command,
            args=health.args,
            cwd=project_dir,
        )
        if session_cache is not None:
            client = session_cache.get(cache_key) or client
            await client.open()
            session_cache[cache_key] = client
        return await client.call_tool(name=tool_name, arguments=arguments)

    if health.transport == "http" and health.url:
        client = RuntimeExternalMcpHttpClient(
            server=health.server,
            url=health.url,
            headers=external_mcp_headers_for_server(
                health.server,
                project_mcp_config=project_mcp_config,
                environment=environment,
            ),
        )
        if session_cache is not None:
            client = session_cache.get(cache_key) or client
            await client.open()
            session_cache[cache_key] = client
        return await client.call_tool(name=tool_name, arguments=arguments)

    target = "HTTP URL" if health.transport == "http" else "stdio command"
    raise RuntimeExternalMcpClientError(
        f"External MCP server {health.server} is missing a {target}."
    )


async def discover_external_mcp_tools(
    *,
    health: RuntimeExternalMcpServerHealth,
    project_dir: Path,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return the live tools/list payload for one ready external MCP server."""
    if health.transport == "stdio" and health.command:
        client = RuntimeExternalMcpClient(
            server=health.server,
            command=health.command,
            args=health.args,
            cwd=project_dir,
        )
        return await client.list_tools()

    if health.transport == "http" and health.url:
        client = RuntimeExternalMcpHttpClient(
            server=health.server,
            url=health.url,
            headers=external_mcp_headers_for_server(
                health.server,
                project_mcp_config=project_mcp_config,
                environment=environment,
            ),
        )
        return await client.list_tools()

    target = "HTTP URL" if health.transport == "http" else "stdio command"
    raise RuntimeExternalMcpClientError(
        f"External MCP server {health.server} is missing a {target}."
    )


async def check_external_mcp_contract(
    *,
    server: str,
    project_dir: Path,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> RuntimeExternalMcpContractCheck:
    """Compare registered adapter tools with a live external MCP tools/list."""
    server = normalize_mcp_server_name(server)
    health = describe_external_mcp_server_health(
        server,
        project_mcp_config=project_mcp_config,
        environment=environment,
    )
    adapter = external_mcp_adapter_for(
        server,
        project_mcp_config=project_mcp_config,
    )
    adapter_tools = adapter.tool_names if adapter else ()

    if not health.ready_to_connect or not health.execution_supported:
        return RuntimeExternalMcpContractCheck(
            server=server,
            ok=False,
            status="skipped",
            reason=health.reason,
            transport=health.transport,
            adapter_tools=adapter_tools,
        )

    try:
        result = await discover_external_mcp_tools(
            health=health,
            project_dir=project_dir,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
    except Exception as e:
        return RuntimeExternalMcpContractCheck(
            server=server,
            ok=False,
            status="error",
            reason="External MCP tools/list failed.",
            transport=health.transport,
            adapter_tools=adapter_tools,
            error=str(e),
        )

    server_tools = extract_mcp_tool_names(result)
    adapter_missing_on_server = tuple(
        tool for tool in adapter_tools if tool not in server_tools
    )
    server_missing_in_adapter = tuple(
        tool for tool in server_tools if tool not in adapter_tools
    )
    if adapter_missing_on_server:
        return RuntimeExternalMcpContractCheck(
            server=server,
            ok=False,
            status="adapter_tool_missing_on_server",
            reason="Adapter declares tools that the live MCP server did not return.",
            transport=health.transport,
            adapter_tools=adapter_tools,
            server_tools=server_tools,
            adapter_tools_missing_on_server=adapter_missing_on_server,
            server_tools_missing_in_adapter=server_missing_in_adapter,
        )
    if server_missing_in_adapter:
        return RuntimeExternalMcpContractCheck(
            server=server,
            ok=True,
            status="server_has_extra_tools",
            reason="Live MCP server returned extra tools not yet exposed by the adapter.",
            transport=health.transport,
            adapter_tools=adapter_tools,
            server_tools=server_tools,
            server_tools_missing_in_adapter=server_missing_in_adapter,
        )
    return RuntimeExternalMcpContractCheck(
        server=server,
        ok=True,
        status="ok",
        reason="Adapter tools match the live MCP server tools/list response.",
        transport=health.transport,
        adapter_tools=adapter_tools,
        server_tools=server_tools,
    )


async def check_external_mcp_contracts(
    *,
    requested_servers: tuple[str, ...],
    project_dir: Path,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Run external MCP adapter contract checks for requested servers."""
    checks: list[dict[str, Any]] = []
    for server in normalize_mcp_server_names(requested_servers):
        check = await check_external_mcp_contract(
            server=server,
            project_dir=project_dir,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        checks.append(check.to_dict())
    return checks


def extract_mcp_tool_names(result: Mapping[str, Any]) -> tuple[str, ...]:
    """Extract ordered tool names from an MCP tools/list result."""
    tools = result.get("tools", ())
    if not isinstance(tools, (list, tuple)):
        return ()
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, Mapping):
            continue
        name = str(tool.get("name") or "")
        if name and name not in names:
            names.append(name)
    return tuple(names)


def external_mcp_headers_for_server(
    server: str,
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return HTTP headers for an external MCP server without exposing secrets."""
    server = normalize_mcp_server_name(server)
    catalog_entry = mcp_server_catalog_entry(
        server,
        project_mcp_config=project_mcp_config,
    )
    authorization_env = str(catalog_entry.get("authorization_env") or "")
    if not authorization_env:
        custom_server = custom_external_mcp_server_config(
            server,
            project_mcp_config=project_mcp_config,
        )
        headers = custom_server.get("headers") if custom_server else None
        if not isinstance(headers, Mapping):
            return {}
        return {str(key): str(value) for key, value in headers.items()}
    token = str(
        mcp_config_or_env_value(
            authorization_env,
            project_mcp_config=project_mcp_config,
            environment=environment,
        )
        or ""
    ).strip()
    if not token:
        raise RuntimeExternalMcpClientError(
            f"External MCP server {server} requires {authorization_env}."
        )
    scheme = str(catalog_entry.get("authorization_scheme") or "Bearer")
    return {"Authorization": f"{scheme} {token}"}


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
        "record_gotcha": RuntimeMcpToolPolicy("write_memory", "write", mutating=True),
        "record_feedback": RuntimeMcpToolPolicy("write_memory", "write", mutating=True),
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
    if server == "linear-server":
        return "linear"
    return server


def configured_mcp_allowed_permissions(source: Any) -> set[str] | None:
    """Return an MCP permission allowlist from a session/config object if present."""
    if isinstance(source, Mapping):
        for key in (
            "mcp_allowed_permissions",
            "allowed_mcp_permissions",
            "mcp_permissions",
        ):
            if key in source:
                return normalize_mcp_allowed_permissions(source.get(key))
        return None

    for key in (
        "mcp_allowed_permissions",
        "allowed_mcp_permissions",
        "mcp_permissions",
    ):
        if hasattr(source, key):
            return normalize_mcp_allowed_permissions(getattr(source, key))
    return None


def configured_mcp_project_config(source: Any) -> Mapping[str, Any] | None:
    """Return project-level MCP configuration from a session/config object."""
    if isinstance(source, Mapping):
        for key in ("mcp_config", "project_mcp_config"):
            value = source.get(key)
            if isinstance(value, Mapping):
                return value
        return None

    for key in ("mcp_config", "project_mcp_config"):
        value = getattr(source, key, None)
        if isinstance(value, Mapping):
            return value
    return None


def load_project_mcp_config_for_runtime(project_dir: Path) -> Mapping[str, Any] | None:
    """Load project MCP config without making runtime bridge depend on SDK setup."""
    try:
        from core.client import load_project_mcp_config
    except Exception:
        return None
    config = load_project_mcp_config(project_dir)
    if not isinstance(config, Mapping) or not config:
        return None
    return config


def normalize_mcp_allowed_permissions(permissions: Any) -> set[str] | None:
    """Normalize a bridged MCP permission allowlist.

    ``None`` keeps backward-compatible allow-all behavior. An explicit empty
    collection denies every bridged MCP tool.
    """
    if permissions is None:
        permissions = os.environ.get(MCP_ALLOWED_PERMISSIONS_ENV)
    if permissions is None:
        return None
    if isinstance(permissions, str):
        permission_iterable = permissions.split(",")
    else:
        permission_iterable = permissions
    normalized = {
        str(permission).strip()
        for permission in permission_iterable or ()
        if str(permission).strip()
    }
    return normalized


def check_mcp_tool_permission(
    policy: RuntimeMcpToolPolicy,
    *,
    allowed_permissions: set[str] | None,
) -> RuntimeMcpPermissionDecision:
    """Check whether one MCP tool policy is allowed for the current bridge."""
    if allowed_permissions is None or "*" in allowed_permissions:
        return RuntimeMcpPermissionDecision(
            allowed=True,
            reason="allow_all",
            allowed_permissions=None
            if allowed_permissions is None
            else tuple(sorted(allowed_permissions)),
        )
    if policy.permission in allowed_permissions:
        return RuntimeMcpPermissionDecision(
            allowed=True,
            reason="permission_allowed",
            allowed_permissions=tuple(sorted(allowed_permissions)),
        )
    return RuntimeMcpPermissionDecision(
        allowed=False,
        reason="permission_not_allowed",
        allowed_permissions=tuple(sorted(allowed_permissions)),
    )


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
