"""
Plugin Runtime Foundation
=========================

Runtime adapter that lets enabled agent plugins participate in the agent
pipeline through prompt augmentation and SDK tool hooks.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import (
    PluginBase,
    PluginCapability,
    PluginType,
    default_capabilities_for_type,
)
from .registry import PluginRegistry
from .sdk.agent import AgentContext, AgentPlugin, ToolHookDecision

logger = logging.getLogger(__name__)

TOOL_HOOK_CAPABILITIES = {
    PluginCapability.GENERIC_EDIT,
    PluginCapability.FULL_AGENT_RUNTIME,
}
PLUGIN_TOOL_HOOK_MATCHER = "*"


@dataclass(frozen=True)
class PromptContribution:
    """Prompt text contributed by one enabled plugin."""

    plugin_name: str
    capabilities: list[str]
    text: str


def plugin_capabilities(plugin: PluginBase) -> list[PluginCapability]:
    """Return declared plugin capabilities, falling back to plugin-type defaults."""
    capabilities = getattr(plugin.metadata, "capabilities", [])
    if capabilities:
        return [
            capability
            if isinstance(capability, PluginCapability)
            else PluginCapability(capability)
            for capability in capabilities
        ]
    return default_capabilities_for_type(plugin.plugin_type)


def _capability_values(plugin: PluginBase) -> list[str]:
    return [capability.value for capability in plugin_capabilities(plugin)]


def _can_use_tool_hooks(plugin: PluginBase) -> bool:
    return (
        isinstance(plugin, AgentPlugin)
        and plugin.is_enabled
        and bool(set(plugin_capabilities(plugin)) & TOOL_HOOK_CAPABILITIES)
    )


def build_agent_context(
    project_dir: Path,
    spec_dir: Path,
    agent_type: str,
    *,
    metadata: dict[str, Any] | None = None,
    client: Any | None = None,
) -> AgentContext:
    """Build the shared context object passed to agent runtime plugin hooks."""
    return AgentContext(
        project_dir=project_dir,
        spec_dir=spec_dir,
        client=client,
        phase=agent_type,
        metadata={"agent_type": agent_type, **(metadata or {})},
    )


def get_runtime_registry(project_dir: Path) -> PluginRegistry:
    """Return the registry used by runtime plugin wiring for this project."""
    return PluginRegistry.get_instance(
        user_plugins_dir=project_dir / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=Path(__file__).parent / "system",
        project_dir=project_dir,
    )


def load_enabled_agent_plugins(project_dir: Path) -> list[AgentPlugin]:
    """Load and return enabled agent plugins for runtime pipeline hooks."""
    registry = get_runtime_registry(project_dir)
    if not registry.list_plugins():
        registry.load_all_plugins()

    return [
        plugin
        for plugin in registry.list_plugins(
            plugin_type=PluginType.AGENT,
            enabled_only=True,
        )
        if isinstance(plugin, AgentPlugin)
    ]


def collect_prompt_augmentations(
    plugins: list[AgentPlugin],
    context: AgentContext,
) -> list[PromptContribution]:
    """Collect prompt augmentation blocks from enabled agent plugins."""
    contributions: list[PromptContribution] = []
    for plugin in plugins:
        if not plugin.is_enabled:
            continue
        try:
            text = plugin.augment_prompt(context)
        except Exception as exc:
            logger.warning(
                "Plugin %s failed prompt augmentation: %s",
                plugin.name,
                exc,
            )
            continue

        if not isinstance(text, str) or not text.strip():
            continue

        contributions.append(
            PromptContribution(
                plugin_name=plugin.name,
                capabilities=_capability_values(plugin),
                text=text.strip(),
            )
        )
    return contributions


def append_prompt_augmentations(
    base_prompt: str,
    contributions: list[PromptContribution],
) -> str:
    """Append plugin prompt contributions to a base agent system prompt."""
    if not contributions:
        return base_prompt

    blocks = ["# Plugin Runtime Instructions"]
    for contribution in contributions:
        capabilities = ", ".join(contribution.capabilities) or "none"
        blocks.append(
            "\n".join(
                [
                    f"## {contribution.plugin_name} (capabilities: {capabilities})",
                    contribution.text,
                ]
            )
        )
    return f"{base_prompt}\n\n" + "\n\n".join(blocks)


def apply_plugin_prompt_augmentations(
    base_prompt: str,
    project_dir: Path,
    spec_dir: Path,
    agent_type: str,
) -> str:
    """Load enabled agent plugins and append their prompt contributions."""
    plugins = load_enabled_agent_plugins(project_dir)
    context = build_agent_context(project_dir, spec_dir, agent_type)
    contributions = collect_prompt_augmentations(plugins, context)
    return append_prompt_augmentations(base_prompt, contributions)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _normalize_hook_response(plugin_name: str, response: Any) -> dict[str, Any]:
    if response is None:
        return {}

    if isinstance(response, ToolHookDecision):
        response = response.to_sdk_response()

    if not isinstance(response, dict):
        return {}

    if response.get("decision") != "block":
        return {}

    reason = response.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "blocked by plugin runtime hook"

    return {
        "decision": "block",
        "reason": f"Plugin {plugin_name} blocked tool use: {reason}",
    }


async def run_plugin_pre_tool_hooks(
    plugins: list[AgentPlugin],
    context: AgentContext,
    input_data: dict[str, Any],
    tool_use_id: str | None = None,
    sdk_context: Any | None = None,
) -> dict[str, Any]:
    """Run enabled edit/runtime agent plugin hooks before a tool executes."""
    tool_name = str(input_data.get("tool_name") or "")
    tool_input = input_data.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    for plugin in plugins:
        if not _can_use_tool_hooks(plugin):
            continue
        try:
            response = await _maybe_await(
                plugin.pre_tool(context, tool_name, tool_input)
            )
        except Exception as exc:
            logger.warning("Plugin %s failed pre_tool hook: %s", plugin.name, exc)
            continue

        normalized = _normalize_hook_response(plugin.name, response)
        if normalized.get("decision") == "block":
            return normalized

    return {}


async def run_plugin_post_tool_hooks(
    plugins: list[AgentPlugin],
    context: AgentContext,
    input_data: dict[str, Any],
    tool_use_id: str | None = None,
    sdk_context: Any | None = None,
) -> dict[str, Any]:
    """Run enabled edit/runtime agent plugin hooks after a tool executes."""
    tool_name = str(input_data.get("tool_name") or "")
    tool_input = input_data.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    tool_result = input_data.get("tool_result", input_data.get("tool_response"))

    for plugin in plugins:
        if not _can_use_tool_hooks(plugin):
            continue
        try:
            response = await _maybe_await(
                plugin.post_tool(context, tool_name, tool_input, tool_result)
            )
        except Exception as exc:
            logger.warning("Plugin %s failed post_tool hook: %s", plugin.name, exc)
            continue

        normalized = _normalize_hook_response(plugin.name, response)
        if normalized.get("decision") == "block":
            return normalized

    return {}


def build_plugin_tool_hook_matchers(
    project_dir: Path,
    spec_dir: Path,
    agent_type: str,
    hook_matcher_factory: Callable[..., Any],
) -> dict[str, list[Any]]:
    """Build Claude SDK hook matcher objects for enabled runtime-capable plugins."""
    plugins = [
        plugin
        for plugin in load_enabled_agent_plugins(project_dir)
        if _can_use_tool_hooks(plugin)
    ]
    if not plugins:
        return {"PreToolUse": [], "PostToolUse": []}

    context_obj = build_agent_context(project_dir, spec_dir, agent_type)

    async def pre_tool_hook(
        input_data: dict[str, Any],
        tool_use_id: str | None = None,
        context: Any | None = None,
    ) -> dict[str, Any]:
        return await run_plugin_pre_tool_hooks(
            plugins,
            context=context_obj,
            input_data=input_data,
            tool_use_id=tool_use_id,
            sdk_context=context,
        )

    async def post_tool_hook(
        input_data: dict[str, Any],
        tool_use_id: str | None = None,
        context: Any | None = None,
    ) -> dict[str, Any]:
        return await run_plugin_post_tool_hooks(
            plugins,
            context=context_obj,
            input_data=input_data,
            tool_use_id=tool_use_id,
            sdk_context=context,
        )

    return {
        "PreToolUse": [
            hook_matcher_factory(
                matcher=PLUGIN_TOOL_HOOK_MATCHER,
                hooks=[pre_tool_hook],
            )
        ],
        "PostToolUse": [
            hook_matcher_factory(
                matcher=PLUGIN_TOOL_HOOK_MATCHER,
                hooks=[post_tool_hook],
            )
        ],
    }
