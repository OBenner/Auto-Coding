#!/usr/bin/env python3
"""Tests for the plugin runtime control plane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import plugins.cli as plugin_cli
import pytest
from plugins.base import PluginCapability, PluginPermission
from plugins.registry import PluginRegistry


def _write_agent_plugin(
    plugins_dir: Path,
    name: str,
    *,
    permissions: list[str] | None = None,
    capabilities: list[str] | None = None,
    prompt: str = "fixture prompt",
) -> None:
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "version": "1.0.0",
        "author": "Tests",
        "description": f"{name} fixture",
        "plugin_type": "agent",
        "required_permissions": permissions or [],
        "dependencies": [],
        "capabilities": capabilities or ["analysis_only"],
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin_dir / "plugin.py").write_text(
        f'''"""Fixture plugin."""
import plugins.sdk.agent as agent_sdk


class FixturePlugin(agent_sdk.AgentPlugin):
    def on_load(self):
        pass

    def on_unload(self):
        pass

    def on_enable(self):
        pass

    def on_disable(self):
        pass

    def augment_prompt(self, context):
        return "{prompt} for " + str(context.phase)
''',
        encoding="utf-8",
    )


def _write_integration_plugin(
    plugins_dir: Path,
    name: str,
    *,
    prompt: str = "integration fixture prompt",
) -> None:
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "version": "1.0.0",
        "author": "Tests",
        "description": f"{name} fixture",
        "plugin_type": "integration",
        "required_permissions": [],
        "dependencies": [],
        "capabilities": ["analysis_only"],
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin_dir / "plugin.py").write_text(
        f'''"""Fixture integration plugin."""
import plugins.sdk.integration as integration_sdk


class FixtureIntegrationPlugin(integration_sdk.IntegrationPlugin):
    def on_load(self):
        pass

    def on_unload(self):
        pass

    def on_enable(self):
        pass

    def on_disable(self):
        pass

    def augment_prompt(self, context):
        return "{prompt} for " + str(context.phase)
''',
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def reset_registry():
    PluginRegistry.reset_instance()
    yield
    PluginRegistry.reset_instance()


def test_registry_persists_project_scoped_enablement(tmp_path):
    """Disabling a plugin writes state and survives registry reload."""
    system_plugins = tmp_path / "system"
    project_dir = tmp_path / "project"
    _write_agent_plugin(
        system_plugins,
        "stateful-agent",
        permissions=["read_files"],
        capabilities=["analysis_only"],
    )

    registry = PluginRegistry.get_instance(
        user_plugins_dir=project_dir / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=system_plugins,
        project_dir=project_dir,
    )
    registry.load_all_plugins()
    assert registry.get_plugin("stateful-agent").is_enabled is True

    registry.disable_plugin("stateful-agent")
    state_path = project_dir / ".auto-claude" / "plugins" / "state.json"
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "plugins": {"stateful-agent": {"enabled": False}}
    }

    PluginRegistry.reset_instance()
    reloaded = PluginRegistry.get_instance(
        user_plugins_dir=project_dir / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=system_plugins,
        project_dir=project_dir,
    )
    reloaded.load_all_plugins()
    assert reloaded.get_plugin("stateful-agent").is_enabled is False

    reloaded.enable_plugin("stateful-agent")
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "plugins": {"stateful-agent": {"enabled": True}}
    }


def test_permission_diff_command_outputs_enablement_delta(tmp_path, capsys):
    """CLI exposes permission and capability diff before enabling a plugin."""
    system_plugins = tmp_path / "system"
    project_dir = tmp_path / "project"
    _write_agent_plugin(
        system_plugins,
        "guarded-agent",
        permissions=["read_files", "execute_commands"],
        capabilities=["analysis_only", "generic_edit"],
    )
    registry = PluginRegistry.get_instance(
        user_plugins_dir=project_dir / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=system_plugins,
        project_dir=project_dir,
    )
    registry.load_all_plugins()
    registry.disable_plugin("guarded-agent")

    result = plugin_cli.cmd_permission_diff(
        argparse.Namespace(plugin_name="guarded-agent", json=True)
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "success": True,
        "permission_diff": {
            "plugin_name": "guarded-agent",
            "required_permissions": ["read_files", "execute_commands"],
            "capabilities": ["analysis_only", "generic_edit"],
            "added_permissions": ["read_files", "execute_commands"],
            "added_capabilities": ["analysis_only", "generic_edit"],
            "currently_enabled": False,
            "would_enable": True,
        },
    }


def test_traces_command_reads_project_plugin_trace_events(
    tmp_path, capsys, monkeypatch
):
    """CLI exposes recent plugin trace events without invoking plugin code."""
    monkeypatch.chdir(tmp_path)
    trace_dir = tmp_path / ".auto-claude" / "plugin_traces"
    trace_dir.mkdir(parents=True)
    (trace_dir / "skill-pack-runtime.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"plugin": "skill-pack-runtime", "event": "old"}),
                json.dumps({"plugin": "skill-pack-runtime", "event": "new"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = plugin_cli.cmd_traces(
        argparse.Namespace(plugin="skill-pack-runtime", limit=1, json=True)
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["traces"] == [
        {
            "plugin": "skill-pack-runtime",
            "event": "new",
            "source": "skill-pack-runtime.jsonl",
        }
    ]


def test_traces_command_honors_zero_limit(tmp_path, capsys, monkeypatch):
    """A zero trace limit returns no events instead of slicing with -0."""
    monkeypatch.chdir(tmp_path)
    trace_dir = tmp_path / ".auto-claude" / "plugin_traces"
    trace_dir.mkdir(parents=True)
    (trace_dir / "skill-pack-runtime.jsonl").write_text(
        json.dumps({"plugin": "skill-pack-runtime", "event": "new"}) + "\n",
        encoding="utf-8",
    )

    result = plugin_cli.cmd_traces(
        argparse.Namespace(plugin="skill-pack-runtime", limit=0, json=True)
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["traces"] == []


def test_preview_context_command_returns_agent_prompt_contributions(tmp_path, capsys):
    """CLI previews enabled agent plugin prompt augmentation without an agent run."""
    system_plugins = tmp_path / "system"
    project_dir = tmp_path / "project"
    _write_agent_plugin(
        system_plugins,
        "preview-agent",
        permissions=[PluginPermission.READ_FILES.value],
        capabilities=[PluginCapability.ANALYSIS_ONLY.value],
        prompt="PREVIEW_AGENT_CONTEXT",
    )
    PluginRegistry.get_instance(
        user_plugins_dir=project_dir / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=system_plugins,
        project_dir=project_dir,
    )

    result = plugin_cli.cmd_preview_context(
        argparse.Namespace(
            agent_type="coder",
            spec_dir=str(project_dir / ".auto-claude" / "specs" / "001-preview"),
            task="inspect plugins",
            files=["apps/backend/plugins/cli.py"],
            json=True,
        )
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["agent_type"] == "coder"
    assert payload["contributions"] == [
        {
            "plugin_name": "preview-agent",
            "capabilities": ["analysis_only"],
            "text": "PREVIEW_AGENT_CONTEXT for coder",
        }
    ]
    assert "PREVIEW_AGENT_CONTEXT for coder" in payload["preview"]


def test_preview_context_command_uses_runtime_integration_plugins(tmp_path, capsys):
    """CLI preview mirrors the runtime loader, including enabled integrations."""
    system_plugins = tmp_path / "system"
    project_dir = tmp_path / "project"
    _write_integration_plugin(
        system_plugins,
        "preview-integration",
        prompt="PREVIEW_INTEGRATION_CONTEXT",
    )
    PluginRegistry.get_instance(
        user_plugins_dir=project_dir / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=system_plugins,
        project_dir=project_dir,
    )

    result = plugin_cli.cmd_preview_context(
        argparse.Namespace(
            agent_type="qa_reviewer",
            spec_dir=str(project_dir / ".auto-claude" / "specs" / "001-preview"),
            task="inspect integrations",
            files=[],
            json=True,
        )
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["contributions"] == [
        {
            "plugin_name": "preview-integration",
            "capabilities": ["analysis_only"],
            "text": "PREVIEW_INTEGRATION_CONTEXT for qa_reviewer",
        }
    ]
    assert "PREVIEW_INTEGRATION_CONTEXT for qa_reviewer" in payload["preview"]


def test_system_plugins_smoke_load_together(tmp_path):
    """The merged system plugins can be loaded together by the control plane."""
    project_root = Path(__file__).resolve().parent.parent
    registry = PluginRegistry.get_instance(
        user_plugins_dir=tmp_path / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=project_root / "apps" / "backend" / "plugins" / "system",
        project_dir=tmp_path,
    )
    registry.load_all_plugins()

    loaded_names = {plugin.name for plugin in registry.list_plugins()}

    assert {
        "codebase-intelligence",
        "skill-pack-runtime",
        "rules-steering-compiler",
    } <= loaded_names
