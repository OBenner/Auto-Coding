"""Tests for the Phase 1.1 external MCP execution smoke helper.

The helper extends ``check_external_mcp_contract`` (which only verifies
``tools/list``) with a non-mutating ``tools/call`` against the first
read-only tool the adapter exposes. The result is structured so the
provider e2e suite has positive end-to-end evidence that a direct API
provider can actually drive each external MCP server, not just discover
its catalog.

These tests fully mock the underlying transport so they run without
live network/MCP processes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from agents.runtime.mcp_bridge import (
    RuntimeExternalMcpAdapter,
    RuntimeExternalMcpServerHealth,
    RuntimeExternalMcpToolDefinition,
    RuntimeMcpToolPolicy,
)
from agents.runtime.mcp_execution_smoke import mcp_execution_smoke


def _read_tool(name: str = "list_items") -> RuntimeExternalMcpToolDefinition:
    return RuntimeExternalMcpToolDefinition(
        name=name,
        description="read-only smoke tool",
        parameters={"type": "object", "properties": {}},
        policy=RuntimeMcpToolPolicy(
            permission="read_smoke",
            audit_level="read",
            mutating=False,
            audit_required=False,
        ),
    )


def _write_tool() -> RuntimeExternalMcpToolDefinition:
    return RuntimeExternalMcpToolDefinition(
        name="mutate_thing",
        description="mutating",
        parameters={"type": "object", "properties": {}},
        policy=RuntimeMcpToolPolicy(
            permission="write_smoke",
            audit_level="write",
            mutating=True,
            audit_required=True,
        ),
    )


def _adapter(*tools: RuntimeExternalMcpToolDefinition) -> RuntimeExternalMcpAdapter:
    return RuntimeExternalMcpAdapter(
        server="testserver",
        display_name="Test Server",
        tool_definitions=tools,
        transport="http",
    )


def _ready_health() -> RuntimeExternalMcpServerHealth:
    return RuntimeExternalMcpServerHealth(
        server="testserver",
        display_name="Test Server",
        bridgeable=True,
        client_enabled=True,
        server_enabled=True,
        configured=True,
        status="ready_to_connect",
        reason="ok",
        transport="http",
        url="https://example.invalid/mcp",
        execution_supported=True,
        executable_tools=("list_items",),
        adapter_registered=True,
        adapter_name="testserver",
        adapter_transport="http",
        adapter_exposed_server="testserver",
        transport_supported=True,
    )


def _skipped_health() -> RuntimeExternalMcpServerHealth:
    return RuntimeExternalMcpServerHealth(
        server="testserver",
        display_name="Test Server",
        bridgeable=True,
        client_enabled=False,
        server_enabled=True,
        configured=False,
        status="client_disabled",
        reason="External MCP client bridge disabled.",
        transport="http",
        execution_supported=False,
        adapter_registered=True,
        adapter_name="testserver",
        adapter_transport="http",
        adapter_exposed_server="testserver",
        transport_supported=True,
    )


@pytest.mark.asyncio
async def test_smoke_returns_skipped_when_server_not_ready(tmp_path: Path):
    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_skipped_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_read_tool()),
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    assert result.ok is False
    assert result.status == "skipped"
    assert "disabled" in result.reason.lower()
    assert result.adapter_tools == ("list_items",)


@pytest.mark.asyncio
async def test_smoke_returns_skipped_when_no_safe_tool_registered(tmp_path: Path):
    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_ready_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_write_tool()),
    ), patch(
        "agents.runtime.mcp_execution_smoke.discover_external_mcp_tools",
        return_value={"tools": [{"name": "mutate_thing"}]},
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    assert result.status == "no_safe_tool"
    assert result.ok is False
    assert result.sample_tool is None


@pytest.mark.asyncio
async def test_smoke_reports_tools_list_failure(tmp_path: Path):
    async def _raising_list(**_kwargs: Any) -> Any:
        raise RuntimeError("upstream down")

    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_ready_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_read_tool()),
    ), patch(
        "agents.runtime.mcp_execution_smoke.discover_external_mcp_tools",
        side_effect=_raising_list,
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    assert result.ok is False
    assert result.status == "tools_list_failed"
    assert "upstream down" in result.error
    assert result.failure_stage == "tools_list"


@pytest.mark.asyncio
async def test_smoke_reports_tools_call_failure(tmp_path: Path):
    async def _raising_call(**_kwargs: Any) -> Any:
        raise TimeoutError("call timed out")

    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_ready_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_read_tool()),
    ), patch(
        "agents.runtime.mcp_execution_smoke.discover_external_mcp_tools",
        return_value={"tools": [{"name": "list_items"}]},
    ), patch(
        "agents.runtime.mcp_execution_smoke.call_external_mcp_tool",
        side_effect=_raising_call,
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    assert result.ok is False
    assert result.status == "tools_call_failed"
    assert "call timed out" in result.error
    assert result.failure_stage == "tools_call"
    assert result.sample_tool == "list_items"
    assert result.sample_tool_audit_level == "read"


@pytest.mark.asyncio
async def test_smoke_ok_when_tool_call_returns_normalized_text(tmp_path: Path):
    async def _list(**_kwargs: Any) -> Any:
        return {"tools": [{"name": "list_items"}]}

    async def _call(**_kwargs: Any) -> Any:
        return {"content": [{"type": "text", "text": "hello"}], "isError": False}

    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_ready_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_read_tool()),
    ), patch(
        "agents.runtime.mcp_execution_smoke.discover_external_mcp_tools",
        side_effect=_list,
    ), patch(
        "agents.runtime.mcp_execution_smoke.call_external_mcp_tool",
        side_effect=_call,
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    assert result.ok is True
    assert result.status == "ok"
    assert result.sample_tool == "list_items"
    assert result.normalized_result is not None
    assert result.normalized_result.get("is_error") is False


@pytest.mark.asyncio
async def test_smoke_marks_validation_error_when_server_reports_is_error(
    tmp_path: Path,
):
    """An is_error=True response means the server validated input. Pipeline OK."""

    async def _list(**_kwargs: Any) -> Any:
        return {"tools": [{"name": "list_items"}]}

    async def _call(**_kwargs: Any) -> Any:
        return {
            "content": [{"type": "text", "text": "missing required argument: query"}],
            "isError": True,
        }

    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_ready_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_read_tool()),
    ), patch(
        "agents.runtime.mcp_execution_smoke.discover_external_mcp_tools",
        side_effect=_list,
    ), patch(
        "agents.runtime.mcp_execution_smoke.call_external_mcp_tool",
        side_effect=_call,
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    assert result.ok is False
    assert result.status == "tool_validation_error"
    # Connectivity and schema layer are healthy; the server just rejected
    # the empty-argument call. The smoke distinguishes this from a
    # transport-level failure.
    assert result.normalized_result is not None
    assert result.normalized_result["is_error"] is True


@pytest.mark.asyncio
async def test_smoke_to_dict_is_json_safe(tmp_path: Path):
    import json

    async def _list(**_kwargs: Any) -> Any:
        return {"tools": [{"name": "list_items"}]}

    async def _call(**_kwargs: Any) -> Any:
        return {"content": [{"type": "text", "text": "ok"}]}

    with patch(
        "agents.runtime.mcp_execution_smoke.describe_external_mcp_server_health",
        return_value=_ready_health(),
    ), patch(
        "agents.runtime.mcp_execution_smoke.external_mcp_adapter_for",
        return_value=_adapter(_read_tool()),
    ), patch(
        "agents.runtime.mcp_execution_smoke.discover_external_mcp_tools",
        side_effect=_list,
    ), patch(
        "agents.runtime.mcp_execution_smoke.call_external_mcp_tool",
        side_effect=_call,
    ):
        result = await mcp_execution_smoke(
            server="testserver",
            project_dir=tmp_path,
        )

    payload = result.to_dict()
    encoded = json.dumps(payload)
    assert "list_items" in encoded
    assert payload["server"] == "testserver"
    assert payload["sample_tool"] == "list_items"


def test_helper_exported_from_agents_runtime():
    """The helper is reachable through the public ``agents.runtime`` API."""
    from agents.runtime import McpExecutionSmokeResult, mcp_execution_smoke as helper

    assert callable(helper)
    assert McpExecutionSmokeResult.__name__ == "McpExecutionSmokeResult"
