#!/usr/bin/env python3
"""Tests for the built-in Skill Pack Runtime plugin."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Ensure apps/backend and plugin-local package roots are importable in tests.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))
sys.path.insert(
    0,
    str(REPO_ROOT / "apps" / "backend" / "plugins" / "system" / "skill-pack-runtime"),
)

from plugins.base import PluginCapability, PluginMetadata
from plugins.sdk.agent import AgentContext, ToolHookDecision
from skill_pack_runtime.loader import SkillPackLoader
from skill_pack_runtime.runtime import SkillPackRuntime


def _load_plugin_class():
    module_path = (
        REPO_ROOT
        / "apps"
        / "backend"
        / "plugins"
        / "system"
        / "skill-pack-runtime"
        / "plugin.py"
    )
    spec = importlib.util.spec_from_file_location(
        "skill_pack_runtime_plugin_for_tests",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.SkillPackRuntimePlugin


def _write_skill(
    project_dir: Path,
    slug: str,
    *,
    name: str,
    description: str,
    body: str,
    script_name: str | None = None,
) -> Path:
    skill_dir = project_dir / "skills" / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "---",
                "",
                body,
            ]
        ),
        encoding="utf-8",
    )
    if script_name:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / script_name).write_text(
            "#!/usr/bin/env bash\n", encoding="utf-8"
        )
    return skill_dir


def _context(project_dir: Path, task: str) -> AgentContext:
    return AgentContext(
        project_dir=project_dir,
        spec_dir=project_dir / ".auto-claude" / "specs" / "001-test",
        phase="coder",
        metadata={
            "agent_type": "coder",
            "task": task,
            "files": ["apps/backend/core/auth.py"],
        },
    )


def test_discovers_skill_catalog_without_loading_full_bodies(tmp_path):
    """Catalog discovery advertises only SKILL.md name and description."""
    _write_skill(
        tmp_path,
        "security-review",
        name="security-review",
        description="Use for authentication, authorization, and secret handling reviews.",
        body="FULL_SECURITY_BODY_SHOULD_NOT_BE_IN_CATALOG",
        script_name="scan.sh",
    )
    _write_skill(
        tmp_path,
        "frontend-polish",
        name="frontend-polish",
        description="Use for React UI polish and interaction checks.",
        body="FULL_FRONTEND_BODY_SHOULD_NOT_BE_IN_CATALOG",
    )

    catalog = SkillPackLoader(tmp_path).discover_catalog()
    payload = json.dumps([entry.to_dict() for entry in catalog])

    assert [entry.name for entry in catalog] == ["frontend-polish", "security-review"]
    assert "authentication, authorization" in payload
    assert "FULL_SECURITY_BODY_SHOULD_NOT_BE_IN_CATALOG" not in payload
    assert "FULL_FRONTEND_BODY_SHOULD_NOT_BE_IN_CATALOG" not in payload
    assert next(
        entry for entry in catalog if entry.name == "security-review"
    ).has_scripts


def test_runtime_loads_only_relevant_skill_and_blocks_scripts_without_permission(
    tmp_path,
):
    """Prompt augmentation loads only selected SKILL.md bodies and blocks scripts."""
    _write_skill(
        tmp_path,
        "security-review",
        name="security-review",
        description="Use for authentication, authorization, and secret handling reviews.",
        body="# Security Review\nFULL_SECURITY_BODY_INCLUDED_ON_MATCH",
        script_name="scan.sh",
    )
    _write_skill(
        tmp_path,
        "frontend-polish",
        name="frontend-polish",
        description="Use for React UI polish and interaction checks.",
        body="# Frontend Polish\nFULL_FRONTEND_BODY_MUST_STAY_LAZY",
    )

    runtime = SkillPackRuntime(tmp_path, granted_permissions=[])
    prompt = runtime.build_prompt(_context(tmp_path, "Review auth token handling"))

    assert "<available_skills>" in prompt
    assert "<name>security-review</name>" in prompt
    assert "<description>Use for React UI polish" in prompt
    assert "FULL_SECURITY_BODY_INCLUDED_ON_MATCH" in prompt
    assert "FULL_FRONTEND_BODY_MUST_STAY_LAZY" not in prompt
    assert "scripts/scan.sh" in prompt
    assert "blocked: plugin lacks execute_commands permission" in prompt

    trace_path = (
        tmp_path / ".auto-claude" / "plugin_traces" / "skill-pack-runtime.jsonl"
    )
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    assert trace["plugin"] == "skill-pack-runtime"
    assert trace["phase"] == "coder"
    assert trace["activated_skills"] == ["security-review"]
    assert "matched task context" in trace["reason"]


def test_runtime_can_activate_from_spec_context_when_task_metadata_is_absent(
    tmp_path,
):
    """Agent sessions can activate skills from spec files even without task metadata."""
    _write_skill(
        tmp_path,
        "plugin-building",
        name="plugin-building",
        description="Use when creating or updating Auto Code plugins.",
        body="# Plugin Building\nPLUGIN_BUILDING_BODY_INCLUDED_FROM_SPEC",
    )
    spec_dir = tmp_path / ".auto-claude" / "specs" / "123-plugin-work"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "# Build plugin runtime\nCreate a new Auto Code plugin layer.",
        encoding="utf-8",
    )

    context = AgentContext(
        project_dir=tmp_path,
        spec_dir=spec_dir,
        phase="coder",
        metadata={"agent_type": "coder"},
    )
    prompt = SkillPackRuntime(tmp_path, granted_permissions=[]).build_prompt(context)

    assert "PLUGIN_BUILDING_BODY_INCLUDED_FROM_SPEC" in prompt


def test_plugin_prompt_augmentation_is_analysis_only(tmp_path):
    """The system plugin contributes prompt context and guarded tool policy."""
    metadata = PluginMetadata.from_dict(
        {
            "name": "skill-pack-runtime",
            "version": "0.1.0",
            "author": "Tests",
            "description": "Skill pack runtime fixture",
            "plugin_type": "agent",
            "required_permissions": ["read_files"],
            "capabilities": ["analysis_only", "generic_edit"],
        }
    )
    _write_skill(
        tmp_path,
        "pytest-helper",
        name="pytest-helper",
        description="Use for pytest test writing and debugging.",
        body="# Pytest Helper\nFollow pytest idioms.",
    )
    plugin = _load_plugin_class()(metadata)
    plugin._mark_enabled()

    prompt = plugin.augment_prompt(_context(tmp_path, "Write pytest coverage"))

    assert metadata.capabilities == [
        PluginCapability.ANALYSIS_ONLY,
        PluginCapability.GENERIC_EDIT,
    ]
    assert "Skill Pack Runtime" in prompt
    assert "pytest-helper" in prompt
    assert "Follow pytest idioms." in prompt


def test_plugin_blocks_skill_scripts_without_execute_permission(tmp_path):
    """Bundled skill scripts are blocked at the tool hook without permission."""
    metadata = PluginMetadata.from_dict(
        {
            "name": "skill-pack-runtime",
            "version": "0.1.0",
            "author": "Tests",
            "description": "Skill pack runtime fixture",
            "plugin_type": "agent",
            "required_permissions": ["read_files"],
            "capabilities": ["analysis_only", "generic_edit"],
        }
    )
    plugin = _load_plugin_class()(metadata)
    context = _context(tmp_path, "Run the helper")

    decision = plugin.pre_tool(
        context,
        "Bash",
        {"command": "python skills/security-review/scripts/scan.py"},
    )

    assert decision == ToolHookDecision.block(
        "skill-pack-runtime blocks skill script execution without execute_commands permission"
    )
