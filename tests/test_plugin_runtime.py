#!/usr/bin/env python3
"""Tests for plugin runtime foundation hooks and capability gates."""

import asyncio
import sys
from pathlib import Path

# Ensure apps/backend is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from plugins.base import PluginCapability, PluginMetadata, PluginType
from plugins.registry import PluginRegistry
from plugins.runtime import (
    append_prompt_augmentations,
    collect_prompt_augmentations,
    plugin_capabilities,
    run_plugin_post_tool_hooks,
    run_plugin_pre_tool_hooks,
)
from plugins.sdk.agent import AgentContext, AgentPlugin, ToolHookDecision
from plugins.sdk.integration import IntegrationPlugin
from plugins.sdk.ui import UIPlugin


class RuntimeAgentPlugin(AgentPlugin):
    """Agent plugin fixture with prompt and tool runtime hooks."""

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.pre_tool_calls: list[tuple[str, dict]] = []
        self.post_tool_calls: list[tuple[str, dict, object]] = []

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def augment_prompt(self, context: AgentContext) -> str:
        return f"Use runtime guidance for {context.phase}."

    def pre_tool(
        self,
        context: AgentContext,
        tool_name: str,
        tool_input: dict,
    ) -> ToolHookDecision | None:
        self.pre_tool_calls.append((tool_name, tool_input))
        if tool_input.get("command") == "blocked":
            return ToolHookDecision.block("blocked by runtime fixture")
        return None

    def post_tool(
        self,
        context: AgentContext,
        tool_name: str,
        tool_input: dict,
        tool_result: object,
    ) -> None:
        self.post_tool_calls.append((tool_name, tool_input, tool_result))


class RuntimeIntegrationPlugin(IntegrationPlugin):
    """Integration plugin smoke fixture."""

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def create_mcp_tools(self, context):
        def smoke_tool() -> str:
            """Smoke tool for runtime contract tests."""
            return context.project_name

        return [smoke_tool]


class RuntimeUIPlugin(UIPlugin):
    """UI plugin smoke fixture."""

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass


def _metadata(
    name: str,
    plugin_type: str,
    capabilities: list[str] | None = None,
) -> PluginMetadata:
    data = {
        "name": name,
        "version": "1.0.0",
        "author": "Tests",
        "description": f"{name} fixture",
        "plugin_type": plugin_type,
        "required_permissions": [],
        "dependencies": [],
    }
    if capabilities is not None:
        data["capabilities"] = capabilities
    return PluginMetadata.from_dict(data)


def _context(tmp_path: Path) -> AgentContext:
    return AgentContext(
        project_dir=tmp_path,
        spec_dir=tmp_path / ".auto-claude" / "specs" / "001-test",
        phase="coder",
        metadata={"agent_type": "coder"},
    )


def _write_runtime_integration_plugin(project_dir: Path) -> None:
    plugin_dir = (
        project_dir / ".auto-claude" / "plugins" / "user" / "runtime-integration"
    )
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        """{
  "name": "runtime-integration",
  "version": "1.0.0",
  "author": "Tests",
  "description": "Runtime-aware integration fixture",
  "plugin_type": "integration",
  "required_permissions": ["read_files"],
  "capabilities": ["analysis_only"]
}
""",
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        '''"""Runtime-aware integration fixture."""
import plugins.sdk.integration as integration_sdk


class RuntimeAwareIntegrationPlugin(integration_sdk.IntegrationPlugin):
    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def augment_prompt(self, context):
        return f"Integration context for {context.phase}."
''',
        encoding="utf-8",
    )


def test_plugin_metadata_defaults_capabilities_by_plugin_type():
    """Plugin manifests get conservative runtime capability defaults."""
    assert _metadata("agent", "agent").capabilities == [
        PluginCapability.FULL_AGENT_RUNTIME
    ]
    assert _metadata("integration", "integration").capabilities == [
        PluginCapability.ANALYSIS_ONLY
    ]
    assert _metadata("ui", "ui").capabilities == [PluginCapability.ANALYSIS_ONLY]


def test_plugin_metadata_accepts_explicit_capabilities():
    """Manifests can opt into generic edit runtime capability explicitly."""
    metadata = _metadata(
        "workflow-pack",
        "agent",
        ["analysis_only", "generic_edit"],
    )

    assert metadata.capabilities == [
        PluginCapability.ANALYSIS_ONLY,
        PluginCapability.GENERIC_EDIT,
    ]
    assert metadata.to_dict()["capabilities"] == ["analysis_only", "generic_edit"]


def test_build_agent_context_preserves_runtime_metadata(tmp_path):
    """Runtime context includes task and file metadata for prompt hooks."""
    from plugins.runtime import build_agent_context

    context = build_agent_context(
        project_dir=tmp_path,
        spec_dir=tmp_path / ".auto-claude" / "specs" / "001-test",
        agent_type="coder",
        metadata={
            "task": "Refactor runtime metadata",
            "files": ["apps/backend/core/client.py"],
            "subtask_id": "task-1",
        },
    )

    assert context.phase == "coder"
    assert context.metadata == {
        "agent_type": "coder",
        "task": "Refactor runtime metadata",
        "files": ["apps/backend/core/client.py"],
        "subtask_id": "task-1",
    }


def test_smoke_contracts_for_each_plugin_type(tmp_path):
    """Agent, integration, and UI plugin classes keep distinct runtime roles."""
    agent = RuntimeAgentPlugin(_metadata("agent-smoke", "agent"))
    integration = RuntimeIntegrationPlugin(
        _metadata("integration-smoke", "integration")
    )
    ui = RuntimeUIPlugin(_metadata("ui-smoke", "ui"))

    assert plugin_capabilities(agent) == [PluginCapability.FULL_AGENT_RUNTIME]
    assert plugin_capabilities(integration) == [PluginCapability.ANALYSIS_ONLY]
    assert plugin_capabilities(ui) == [PluginCapability.ANALYSIS_ONLY]
    assert integration.create_mcp_tools(type("Ctx", (), {"project_name": "repo"})())[
        0
    ]()
    assert ui.get_ui_components(type("Ctx", (), {})()) == []


def test_prompt_augmentation_collects_enabled_agent_plugin_blocks(tmp_path):
    """Enabled agent plugins can append scoped instructions to agent prompts."""
    plugin = RuntimeAgentPlugin(_metadata("runtime-agent", "agent"))
    plugin._mark_enabled()
    context = _context(tmp_path)

    contributions = collect_prompt_augmentations([plugin], context)
    prompt = append_prompt_augmentations("Base prompt", contributions)

    assert contributions[0].plugin_name == "runtime-agent"
    assert "Use runtime guidance for coder." in prompt
    assert "runtime-agent" in prompt
    assert "full_agent_runtime" in prompt


def test_prompt_augmentation_accepts_analysis_only_integration_plugins(tmp_path):
    """Runtime prompt context can come from enabled analysis-only integrations."""
    from plugins.runtime import load_enabled_runtime_plugins

    PluginRegistry.reset_instance()
    _write_runtime_integration_plugin(tmp_path)

    plugins = load_enabled_runtime_plugins(tmp_path)
    context = _context(tmp_path)
    contributions = collect_prompt_augmentations(plugins, context)
    prompt = append_prompt_augmentations("Base prompt", contributions)
    hook_result = asyncio.run(
        run_plugin_pre_tool_hooks(
            plugins,
            context,
            {"tool_name": "Bash", "tool_input": {"command": "blocked"}},
        )
    )

    assert "runtime-integration" in {plugin.name for plugin in plugins}
    assert "Integration context for coder." in prompt
    assert "runtime-integration (capabilities: analysis_only)" in prompt
    assert hook_result == {}

    PluginRegistry.reset_instance()


def test_pre_and_post_tool_hooks_respect_capability_gates(tmp_path):
    """Only edit/runtime capable agent plugins can observe or block tool calls."""
    full_runtime = RuntimeAgentPlugin(_metadata("full-runtime", "agent"))
    analysis_only = RuntimeAgentPlugin(
        _metadata("analysis-only", "agent", ["analysis_only"])
    )
    full_runtime._mark_enabled()
    analysis_only._mark_enabled()
    context = _context(tmp_path)

    allowed = asyncio.run(
        run_plugin_pre_tool_hooks(
            [full_runtime, analysis_only],
            context,
            {"tool_name": "Bash", "tool_input": {"command": "allowed"}},
        )
    )
    blocked = asyncio.run(
        run_plugin_pre_tool_hooks(
            [full_runtime, analysis_only],
            context,
            {"tool_name": "Bash", "tool_input": {"command": "blocked"}},
        )
    )
    asyncio.run(
        run_plugin_post_tool_hooks(
            [full_runtime, analysis_only],
            context,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "allowed"},
                "tool_result": {"ok": True},
            },
        )
    )

    assert allowed == {}
    assert blocked == {
        "decision": "block",
        "reason": "Plugin full-runtime blocked tool use: blocked by runtime fixture",
    }
    assert len(full_runtime.pre_tool_calls) == 2
    assert len(full_runtime.post_tool_calls) == 1
    assert analysis_only.pre_tool_calls == []
    assert analysis_only.post_tool_calls == []
