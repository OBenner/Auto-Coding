"""Built-in Skill Pack Runtime agent plugin."""

from __future__ import annotations

import logging

import plugins.sdk.agent as agent_sdk
from skill_pack_runtime.runtime import SkillPackRuntime

logger = logging.getLogger(__name__)


class SkillPackRuntimePlugin(agent_sdk.AgentPlugin):
    """Expose project-local SKILL.md packs through prompt augmentation."""

    def on_load(self) -> None:
        logger.info("skill-pack-runtime: Plugin loaded")

    def on_enable(self) -> None:
        logger.info("skill-pack-runtime: Plugin enabled")

    def on_disable(self) -> None:
        logger.info("skill-pack-runtime: Plugin disabled")

    def on_unload(self) -> None:
        logger.info("skill-pack-runtime: Plugin unloaded")

    def augment_prompt(self, context: agent_sdk.AgentContext) -> str | None:
        runtime = SkillPackRuntime(
            context.project_dir,
            granted_permissions=self.metadata.required_permissions,
        )
        return runtime.build_prompt(context)

    def pre_tool(
        self,
        context: agent_sdk.AgentContext,
        tool_name: str,
        tool_input: dict,
    ) -> agent_sdk.ToolHookDecision | None:
        runtime = SkillPackRuntime(
            context.project_dir,
            granted_permissions=self.metadata.required_permissions,
        )
        if runtime.should_block_script_command(tool_name, tool_input):
            return agent_sdk.ToolHookDecision.block(
                "skill-pack-runtime blocks skill script execution without "
                "execute_commands permission"
            )
        return None
