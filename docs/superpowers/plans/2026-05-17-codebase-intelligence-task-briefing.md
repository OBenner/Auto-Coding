# Codebase Intelligence Task Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pass task/file metadata into plugin runtime hooks and let `codebase-intelligence` generate a compact task briefing from target files before agents act.

**Architecture:** Add optional `runtime_metadata` to `create_client()` and the Claude provider adapter, then pass it into `plugins.runtime.build_agent_context()`. Keep metadata optional and bounded. Extend the analyzer prompt augmentation to summarize dependencies, dependents, impact, and test candidates for provided `files`, `changed_files`, or `target_files`.

**Tech Stack:** Python 3.12, pytest, existing Auto Code plugin runtime and codebase-intelligence index.

---

## Task 1: Runtime Metadata Contract

**Files:**
- Modify: `tests/test_plugin_runtime.py`
- Modify: `tests/test_client.py`
- Modify: `apps/backend/plugins/runtime.py`
- Modify: `apps/backend/core/client.py`
- Modify: `apps/backend/core/providers/adapters/claude.py`

- [x] **Step 1: Add RED tests**

Add tests proving `build_agent_context(..., metadata={...})` preserves task/file metadata, and `create_client(..., runtime_metadata={...})` passes that metadata into plugin prompt augmentation.

- [x] **Step 2: Run RED tests**

Run: `python -m pytest tests/test_plugin_runtime.py::test_build_agent_context_preserves_runtime_metadata tests/test_client.py::TestClientPluginMCPWiring::test_create_client_passes_runtime_metadata_to_plugin_prompt -q`

Expected: FAIL because `create_client()` does not accept `runtime_metadata`.

- [x] **Step 3: Implement metadata plumbing**

Add `runtime_metadata: dict | None = None` to `create_client()`, pass it to `apply_plugin_prompt_augmentations()` and `build_plugin_tool_hook_matchers()`, and let the Claude provider adapter forward `config.extra["runtime_metadata"]`.

- [x] **Step 4: Run GREEN tests**

Run: `python -m pytest tests/test_plugin_runtime.py::test_build_agent_context_preserves_runtime_metadata tests/test_client.py::TestClientPluginMCPWiring::test_create_client_passes_runtime_metadata_to_plugin_prompt -q`

Expected: PASS.

## Task 2: Agent Flow Metadata

**Files:**
- Modify: `apps/backend/agents/coder.py`
- Modify: `apps/backend/qa/loop.py`

- [x] **Step 1: Pass planner/coder metadata**

For planner sessions, pass a compact task label. For coder sessions, pass `subtask_id`, `task`, `phase_name`, and `files` from `files_to_modify`.

- [x] **Step 2: Pass QA metadata**

For QA reviewer/fixer sessions, pass phase labels and issue context when available, keeping file lists bounded and project-relative.

## Task 3: Codebase Task Briefing

**Files:**
- Modify: `tests/test_codebase_intelligence.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/README.md`

- [x] **Step 1: Add RED briefing test**

Add a test proving `augment_prompt()` with `metadata.files=["apps/backend/core/client.py"]` includes a `Task Briefing`, dependencies/dependents, impacted files, and test candidates.

- [x] **Step 2: Run RED test**

Run: `python -m pytest tests/test_codebase_intelligence.py::test_codebase_intelligence_task_briefing_uses_runtime_metadata_files -q`

Expected: FAIL because the prompt currently only includes global summary guidance.

- [x] **Step 3: Implement briefing generation**

Add bounded helpers that normalize metadata files, inspect index facts, and emit a compact briefing block. Include briefing files in the trace event.

- [x] **Step 4: Run GREEN test**

Run: `python -m pytest tests/test_codebase_intelligence.py::test_codebase_intelligence_task_briefing_uses_runtime_metadata_files -q`

Expected: PASS.

## Task 4: Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-05-17-codebase-intelligence-task-briefing.md`

- [x] **Step 1: Run focused tests**

Run: `python -m pytest tests/test_codebase_intelligence.py tests/test_plugin_runtime.py tests/test_client.py::TestClientPluginMCPWiring -q`

Expected: PASS.

- [x] **Step 2: Run lint and format checks**

Run: `ruff check apps/backend/plugins/runtime.py apps/backend/core/client.py apps/backend/core/providers/adapters/claude.py apps/backend/agents/coder.py apps/backend/qa/loop.py apps/backend/plugins/system/codebase-intelligence/plugin.py tests/test_plugin_runtime.py tests/test_client.py tests/test_codebase_intelligence.py`

Run: `ruff format --check apps/backend/plugins/runtime.py apps/backend/core/client.py apps/backend/core/providers/adapters/claude.py apps/backend/agents/coder.py apps/backend/qa/loop.py apps/backend/plugins/system/codebase-intelligence/plugin.py tests/test_plugin_runtime.py tests/test_client.py tests/test_codebase_intelligence.py`

Expected: PASS.
