# Codebase Intelligence Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing `codebase-intelligence` integration plugin participate in the agent runtime by adding compact prompt context and activation traces while preserving its MCP tools and optional sidecar behavior.

**Architecture:** Broaden the plugin runtime adapter from "agent plugins only" to enabled runtime-aware plugins, with inert default hook methods on `PluginBase`. `codebase-intelligence` remains an `integration` plugin, keeps its MCP server contract, and contributes analysis-only prompt guidance plus a graph summary when enabled.

**Tech Stack:** Python 3.12, pytest, existing Auto Code plugin runtime substrate.

---

### Task 1: Runtime Adapter Contract

**Files:**
- Modify: `tests/test_plugin_runtime.py`
- Modify: `apps/backend/plugins/base.py`
- Modify: `apps/backend/plugins/runtime.py`

- [x] **Step 1: Write failing runtime test**

Add a test proving an enabled integration plugin with `augment_prompt()` can contribute prompt instructions through `collect_prompt_augmentations()` and `append_prompt_augmentations()`, while an `analysis_only` integration plugin still cannot observe tool hooks.

- [x] **Step 2: Run focused RED test**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_plugin_runtime.py::test_prompt_augmentation_accepts_analysis_only_integration_plugins -q`

Expected: FAIL because `load_enabled_runtime_plugins()` does not exist yet and
runtime collection only loads `AgentPlugin` instances.

- [x] **Step 3: Implement runtime-aware defaults**

Add inert `augment_prompt`, `pre_tool`, and `post_tool` methods to `PluginBase`. Introduce `load_enabled_runtime_plugins()` that loads all enabled plugin types and update prompt collection and hook matcher wiring to accept `PluginBase` instances. Keep tool hooks gated by `generic_edit` or `full_agent_runtime`.

- [x] **Step 4: Run focused GREEN test**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_plugin_runtime.py::test_prompt_augmentation_accepts_analysis_only_integration_plugins tests/test_plugin_runtime.py::test_pre_and_post_tool_hooks_respect_capability_gates -q`

Expected: PASS.

### Task 2: Codebase Intelligence Prompt Context

**Files:**
- Modify: `tests/test_codebase_intelligence.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/README.md`

- [x] **Step 1: Write failing plugin prompt test**

Add a test that calls `CodebaseIntelligencePlugin.augment_prompt()` with an `AgentContext` and asserts the prompt contains the MCP server name, index path, codebase summary, and phase-specific usage guidance.

- [x] **Step 2: Add trace assertion**

Extend the same test to assert `.auto-claude/plugin_traces/codebase-intelligence.jsonl` records the plugin name, phase, reason, index path, and summary counts.

- [x] **Step 3: Run focused RED test**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_codebase_intelligence.py::test_codebase_intelligence_prompt_augmentation_builds_summary_and_trace -q`

Expected: FAIL because the integration plugin has no prompt augmentation hook.

- [x] **Step 4: Implement prompt augmentation**

Implement `augment_prompt()` on `CodebaseIntelligencePlugin`. It should build or refresh the index through the existing sidecar path, return a compact guidance block for planner/coder/QA phases, and append a JSONL trace event explaining why the graph context was activated.

- [x] **Step 5: Run focused GREEN test**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_codebase_intelligence.py::test_codebase_intelligence_prompt_augmentation_builds_summary_and_trace -q`

Expected: PASS.

### Task 3: Integration Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-05-17-codebase-intelligence-runtime.md`

- [x] **Step 1: Run codebase/plugin runtime tests**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_codebase_intelligence.py tests/test_plugin_runtime.py -q`

Expected: PASS.

- [x] **Step 2: Run client regression smoke**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_client.py::TestClientPluginMCPWiring::test_create_client_applies_agent_plugin_prompt_and_tool_hooks tests/test_client.py::TestClientPluginMCPWiring::test_create_client_adds_enabled_integration_plugin_mcp_tools -q`

Expected: PASS.

- [x] **Step 3: Run lint and format checks**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff check apps/backend/plugins/base.py apps/backend/plugins/runtime.py apps/backend/plugins/system/codebase-intelligence/plugin.py tests/test_plugin_runtime.py tests/test_codebase_intelligence.py`

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff format --check apps/backend/plugins/base.py apps/backend/plugins/runtime.py apps/backend/plugins/system/codebase-intelligence/plugin.py tests/test_plugin_runtime.py tests/test_codebase_intelligence.py`

Expected: PASS.

- [x] **Step 4: Inspect git diff**

Run: `git diff --stat`

Expected: only plugin runtime, codebase-intelligence, tests, README, and this plan changed.
