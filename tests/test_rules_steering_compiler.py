#!/usr/bin/env python3
"""Tests for the built-in Rules / Steering Compiler plugin."""

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
    str(
        REPO_ROOT
        / "apps"
        / "backend"
        / "plugins"
        / "system"
        / "rules-steering-compiler"
    ),
)

from plugins.base import PluginCapability, PluginMetadata
from plugins.sdk.agent import AgentContext
from rules_steering_compiler.compiler import RulesSteeringCompiler


def _load_plugin_class():
    module_path = (
        REPO_ROOT
        / "apps"
        / "backend"
        / "plugins"
        / "system"
        / "rules-steering-compiler"
        / "plugin.py"
    )
    spec = importlib.util.spec_from_file_location(
        "rules_steering_compiler_plugin_for_tests",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.RulesSteeringCompilerPlugin


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sample_rules_project(project_dir: Path) -> None:
    _write(
        project_dir / "AGENTS.md",
        "# Agent Rules\nROOT_AGENT_INSTRUCTION",
    )
    _write(
        project_dir / ".cursor" / "rules" / "backend.mdc",
        "\n".join(
            [
                "---",
                "description: Backend Python style",
                "globs: apps/backend/**/*.py",
                "phases: [coder]",
                "---",
                "CURSOR_BACKEND_RULE",
            ]
        ),
    )
    _write(
        project_dir / ".github" / "copilot-instructions.md",
        "# Copilot\nCOPILOT_REPO_RULE",
    )
    _write(
        project_dir / ".github" / "instructions" / "tests.instructions.md",
        "\n".join(
            [
                "---",
                "applyTo: tests/**/*.py",
                "phase: qa_reviewer",
                "---",
                "GITHUB_TEST_REVIEW_RULE",
            ]
        ),
    )
    _write(
        project_dir / ".windsurf" / "rules" / "tests.md",
        "\n".join(
            [
                "---",
                "trigger: glob",
                "globs: tests/**/*.py",
                "---",
                "WINDSURF_TEST_RULE",
            ]
        ),
    )
    _write(
        project_dir / ".kiro" / "steering" / "tech.md",
        "\n".join(
            [
                "---",
                "inclusion: always",
                "---",
                "KIRO_TECH_RULE",
            ]
        ),
    )


def _context(project_dir: Path, phase: str, files: list[str]) -> AgentContext:
    return AgentContext(
        project_dir=project_dir,
        spec_dir=project_dir / ".auto-claude" / "specs" / "001-test",
        phase=phase,
        metadata={"agent_type": phase, "files": files, "task": "review code"},
    )


def test_discovers_supported_rule_sources(tmp_path):
    """Compiler imports the common agent IDE steering file locations."""
    _sample_rules_project(tmp_path)

    rules = RulesSteeringCompiler(tmp_path).discover_rules()
    source_types = {rule.source_type for rule in rules}

    assert source_types == {
        "agents_md",
        "cursor_rule",
        "github_copilot",
        "github_instruction",
        "windsurf_rule",
        "kiro_steering",
    }
    assert {rule.relative_path for rule in rules} >= {
        "AGENTS.md",
        ".cursor/rules/backend.mdc",
        ".github/copilot-instructions.md",
        ".github/instructions/tests.instructions.md",
        ".windsurf/rules/tests.md",
        ".kiro/steering/tech.md",
    }


def test_compiles_rules_by_phase_and_file_scope(tmp_path):
    """Compiled context includes only global and matching phase/file rules."""
    _sample_rules_project(tmp_path)
    compiler = RulesSteeringCompiler(tmp_path)

    coder_context = compiler.compile_context(
        phase="coder",
        files=["apps/backend/core/auth.py"],
    )
    qa_context = compiler.compile_context(
        phase="qa_reviewer",
        files=["tests/test_auth.py"],
    )

    assert "ROOT_AGENT_INSTRUCTION" in coder_context.text
    assert "COPILOT_REPO_RULE" in coder_context.text
    assert "CURSOR_BACKEND_RULE" in coder_context.text
    assert "KIRO_TECH_RULE" in coder_context.text
    assert "GITHUB_TEST_REVIEW_RULE" not in coder_context.text
    assert "WINDSURF_TEST_RULE" not in coder_context.text

    assert "ROOT_AGENT_INSTRUCTION" in qa_context.text
    assert "COPILOT_REPO_RULE" in qa_context.text
    assert "GITHUB_TEST_REVIEW_RULE" in qa_context.text
    assert "WINDSURF_TEST_RULE" in qa_context.text
    assert "CURSOR_BACKEND_RULE" not in qa_context.text
    assert [rule.relative_path for rule in qa_context.rules] == [
        "AGENTS.md",
        ".github/copilot-instructions.md",
        ".github/instructions/tests.instructions.md",
        ".windsurf/rules/tests.md",
        ".kiro/steering/tech.md",
    ]


def test_plugin_prompt_augmentation_writes_trace(tmp_path):
    """System plugin emits compiled steering context and an activation trace."""
    _sample_rules_project(tmp_path)
    metadata = PluginMetadata.from_dict(
        {
            "name": "rules-steering-compiler",
            "version": "0.1.0",
            "author": "Tests",
            "description": "Rules steering compiler fixture",
            "plugin_type": "agent",
            "required_permissions": ["read_files"],
            "capabilities": ["analysis_only"],
        }
    )
    plugin = _load_plugin_class()(metadata)
    plugin._mark_enabled()

    prompt = plugin.augment_prompt(
        _context(tmp_path, "qa_reviewer", ["tests/test_auth.py"])
    )

    assert metadata.capabilities == [PluginCapability.ANALYSIS_ONLY]
    assert "Rules Steering Compiler" in prompt
    assert "GITHUB_TEST_REVIEW_RULE" in prompt
    trace_path = (
        tmp_path / ".auto-claude" / "plugin_traces" / "rules-steering-compiler.jsonl"
    )
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    assert trace["plugin"] == "rules-steering-compiler"
    assert trace["phase"] == "qa_reviewer"
    assert ".github/instructions/tests.instructions.md" in trace["matched_sources"]
