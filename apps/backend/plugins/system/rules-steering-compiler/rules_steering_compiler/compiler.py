"""Compile project steering files into phase/file-scoped agent context."""

from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from plugins.markdown_frontmatter import split_frontmatter

from .models import CompiledSteeringContext, SteeringRule


class RulesSteeringCompiler:
    """Import common agent IDE rules and scope them to Auto Code phases."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)

    def discover_rules(self) -> list[SteeringRule]:
        """Discover all supported steering files in stable priority order."""
        rules: list[SteeringRule] = []
        root_agents = self.project_dir / "AGENTS.md"
        if root_agents.exists():
            rules.append(self._read_rule(root_agents, "agents_md"))

        rules.extend(
            self._read_rule(path, "cursor_rule")
            for path in self._iter_files(self.project_dir / ".cursor" / "rules")
        )

        github_copilot = self.project_dir / ".github" / "copilot-instructions.md"
        if github_copilot.exists():
            rules.append(self._read_rule(github_copilot, "github_copilot"))

        github_instructions = self.project_dir / ".github" / "instructions"
        rules.extend(
            self._read_rule(path, "github_instruction")
            for path in sorted(github_instructions.glob("*.instructions.md"))
        )

        rules.extend(
            self._read_rule(path, "windsurf_rule")
            for path in self._iter_files(self.project_dir / ".windsurf" / "rules")
        )
        rules.extend(
            self._read_rule(path, "kiro_steering")
            for path in self._iter_files(self.project_dir / ".kiro" / "steering")
        )
        return [rule for rule in rules if rule.content.strip()]

    def compile_context(
        self,
        phase: str,
        files: list[str] | None = None,
        task: str = "",
    ) -> CompiledSteeringContext:
        """Return steering rules that match the current phase and files."""
        normalized_files = [_normalize_file(file_path) for file_path in files or []]
        matching = [
            rule
            for rule in self.discover_rules()
            if self._matches(rule, phase, normalized_files, task)
        ]
        return CompiledSteeringContext(
            project_dir=self.project_dir,
            phase=phase,
            files=normalized_files,
            rules=matching,
        )

    def write_trace(self, compiled: CompiledSteeringContext) -> None:
        """Append one compiler trace event for diagnostics."""
        trace_dir = self.project_dir / ".auto-claude" / "plugin_traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plugin": "rules-steering-compiler",
            "phase": compiled.phase,
            "files": compiled.files,
            "matched_sources": [rule.relative_path for rule in compiled.rules],
        }
        with (trace_dir / "rules-steering-compiler.jsonl").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _read_rule(self, path: Path, source_type: str) -> SteeringRule:
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8"))
        return SteeringRule(
            source_type=source_type,
            relative_path=path.relative_to(self.project_dir).as_posix(),
            path=path,
            content=body,
            phases=_metadata_list(metadata, "phases", "phase"),
            globs=_metadata_list(
                metadata,
                "globs",
                "glob",
                "applyTo",
                "fileMatchPattern",
                "files",
            ),
            description=str(metadata.get("description") or "").strip(),
            metadata=metadata,
        )

    def _matches(
        self,
        rule: SteeringRule,
        phase: str,
        files: list[str],
        task: str,
    ) -> bool:
        if rule.phases and phase not in rule.phases:
            return False

        if not rule.globs:
            trigger = str(rule.metadata.get("trigger") or "").casefold()
            inclusion = str(rule.metadata.get("inclusion") or "").casefold()
            always_apply = bool(rule.metadata.get("alwaysApply"))
            if trigger == "model_decision" and rule.description:
                return _matches_text(rule.description, task)
            if inclusion == "manual" or trigger == "manual":
                return False
            return (
                always_apply or inclusion in {"", "always"} or trigger in {"", "always"}
            )

        if not files:
            return False
        return any(
            _matches_glob(file_path, pattern)
            for pattern in rule.globs
            for file_path in files
        )

    def _iter_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(path for path in directory.rglob("*") if path.is_file())


def _metadata_list(metadata: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw_value = metadata.get(key)
        if raw_value is None:
            continue
        if isinstance(raw_value, list):
            values.extend(
                str(value).strip() for value in raw_value if str(value).strip()
            )
        elif str(raw_value).strip():
            values.append(str(raw_value).strip())
    return values


def _normalize_file(file_path: str) -> str:
    return file_path.replace("\\", "/").lstrip("./")


def _matches_glob(file_path: str, pattern: str) -> bool:
    normalized_pattern = _normalize_file(pattern)
    normalized_file = _normalize_file(file_path)
    candidate_patterns = {
        normalized_pattern,
        normalized_pattern.replace("/**/", "/"),
    }
    return any(
        fnmatch.fnmatch(normalized_file, candidate)
        or PurePosixPath(normalized_file).match(candidate)
        for candidate in candidate_patterns
    )


def _matches_text(description: str, task: str) -> bool:
    if not task:
        return False
    task_text = task.casefold()
    return any(
        token in task_text
        for token in description.casefold().replace(",", " ").split()
        if len(token) >= 3
    )
