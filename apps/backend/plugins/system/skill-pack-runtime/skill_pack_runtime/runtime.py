"""Prompt contribution runtime for SKILL.md packs."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plugins.base import PluginPermission
from plugins.sdk.agent import AgentContext

from .loader import SkillPackLoader
from .models import SkillCatalogEntry, SkillDefinition


class SkillPackRuntime:
    """Build prompt context for available and activated SKILL.md packs."""

    def __init__(
        self,
        project_dir: Path,
        granted_permissions: Iterable[PluginPermission | str] | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.loader = SkillPackLoader(self.project_dir)
        self.granted_permissions = {
            permission.value if isinstance(permission, PluginPermission) else permission
            for permission in (granted_permissions or [])
        }

    def build_prompt(self, context: AgentContext) -> str | None:
        """Return catalog plus full instructions for selected skills."""
        catalog = self.loader.discover_catalog()
        if not catalog:
            return None

        query = self._context_query(context)
        selected_entries = self._select_skills(catalog, query)
        selected_skills = [
            skill
            for entry in selected_entries
            if (skill := self.loader.load_skill(entry.skill_id)) is not None
        ]

        self._write_trace(context, catalog, selected_skills, bool(query.strip()))

        blocks = [
            "# Skill Pack Runtime",
            "Available project skills are advertised by name and description only. "
            "Full SKILL.md instructions below are loaded only for activated skills.",
            self._catalog_block(catalog),
        ]
        if selected_skills:
            blocks.append(self._active_skills_block(selected_skills))

        return "\n\n".join(blocks)

    def _select_skills(
        self,
        catalog: list[SkillCatalogEntry],
        query: str,
    ) -> list[SkillCatalogEntry]:
        scored: list[tuple[int, SkillCatalogEntry]] = []
        query_tokens = _tokens(query)
        for entry in catalog:
            haystack = f"{entry.name} {entry.description}".casefold()
            score = 0
            for token in query_tokens:
                if token in haystack:
                    score += 2
                if any(term in token for term in _tokens(entry.name)):
                    score += 1
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: (-item[0], item[1].name))
        return [entry for _, entry in scored[:1]]

    def _catalog_block(self, catalog: list[SkillCatalogEntry]) -> str:
        lines = ["<available_skills>"]
        for entry in catalog:
            lines.extend(
                [
                    "  <skill>",
                    f"    <name>{entry.name}</name>",
                    f"    <description>{entry.description}</description>",
                    "  </skill>",
                ]
            )
        lines.append("</available_skills>")
        return "\n".join(lines)

    def _active_skills_block(self, skills: list[SkillDefinition]) -> str:
        blocks = ["## Activated Skills"]
        for skill in skills:
            blocks.extend(
                [
                    f"### {skill.name}",
                    skill.instructions,
                    self._resources_block(skill),
                ]
            )
        return "\n\n".join(block for block in blocks if block)

    def _resources_block(self, skill: SkillDefinition) -> str:
        if not skill.resources:
            return ""

        lines = ["Resources:"]
        can_execute = (
            PluginPermission.EXECUTE_COMMANDS.value in self.granted_permissions
        )
        for resource in skill.resources:
            if resource.kind == "script" and not can_execute:
                lines.append(
                    f"- {resource.relative_path} "
                    "(blocked: plugin lacks execute_commands permission)"
                )
            elif resource.kind == "script":
                lines.append(f"- {resource.relative_path} (script permission granted)")
            else:
                lines.append(f"- {resource.relative_path} ({resource.kind})")
        return "\n".join(lines)

    def should_block_script_command(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> bool:
        """Return true when a tool call tries to run a skill script without permission."""
        if PluginPermission.EXECUTE_COMMANDS.value in self.granted_permissions:
            return False
        if tool_name.casefold() not in {"bash", "shell"}:
            return False

        command = str(tool_input.get("command") or "").replace("\\", "/")
        return bool(
            re.search(
                r"(^|[\s'\"`])(?:\./)?skills/[^'\"`\s;]+/scripts/[^'\"`\s;]+",
                command,
            )
        )

    def _context_query(self, context: AgentContext) -> str:
        metadata = context.metadata or {}
        parts: list[str] = [str(context.phase or "")]
        for key in ("task", "prompt", "user_request", "agent_type"):
            value = metadata.get(key)
            if value:
                parts.append(str(value))
        for key in ("files", "changed_files", "target_files"):
            value = metadata.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif value:
                parts.append(str(value))
        parts.extend(self._spec_hints(context.spec_dir))
        return " ".join(parts)

    def _spec_hints(self, spec_dir: Path) -> list[str]:
        """Read small spec snippets for activation scoring, not prompt output."""
        hints: list[str] = []
        for file_name in ("spec.md", "requirements.json", "implementation_plan.json"):
            path = spec_dir / file_name
            if not path.exists():
                continue
            try:
                hints.append(path.read_text(encoding="utf-8")[:4000])
            except OSError:
                continue
        return hints

    def _write_trace(
        self,
        context: AgentContext,
        catalog: list[SkillCatalogEntry],
        selected_skills: list[SkillDefinition],
        had_context: bool,
    ) -> None:
        trace_dir = self.project_dir / ".auto-claude" / "plugin_traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        reason = (
            "matched task context"
            if selected_skills and had_context
            else "catalog advertised; no skill activation match"
        )
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plugin": "skill-pack-runtime",
            "phase": context.phase,
            "available_skills": [entry.name for entry in catalog],
            "activated_skills": [skill.name for skill in selected_skills],
            "reason": reason,
        }
        with (trace_dir / "skill-pack-runtime.jsonl").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_-]+", text.casefold())
        if len(token) >= 3
    }
