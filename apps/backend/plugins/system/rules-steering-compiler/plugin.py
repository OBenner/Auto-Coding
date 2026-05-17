"""Built-in Rules / Steering Compiler agent plugin."""

from __future__ import annotations

import logging

import plugins.sdk.agent as agent_sdk
from rules_steering_compiler.compiler import RulesSteeringCompiler

logger = logging.getLogger(__name__)


class RulesSteeringCompilerPlugin(agent_sdk.AgentPlugin):
    """Expose project-local steering rules through prompt augmentation."""

    def on_load(self) -> None:
        logger.info("rules-steering-compiler: Plugin loaded")

    def on_enable(self) -> None:
        logger.info("rules-steering-compiler: Plugin enabled")

    def on_disable(self) -> None:
        logger.info("rules-steering-compiler: Plugin disabled")

    def on_unload(self) -> None:
        logger.info("rules-steering-compiler: Plugin unloaded")

    def augment_prompt(self, context: agent_sdk.AgentContext) -> str | None:
        metadata = context.metadata or {}
        files = metadata.get("files") or metadata.get("changed_files") or []
        if isinstance(files, str):
            files = [files]
        compiler = RulesSteeringCompiler(context.project_dir)
        compiled = compiler.compile_context(
            phase=str(context.phase or metadata.get("agent_type") or ""),
            files=[str(path) for path in files],
            task=str(metadata.get("task") or metadata.get("prompt") or ""),
        )
        if not compiled.rules:
            return None
        compiler.write_trace(compiled)
        return compiled.text
