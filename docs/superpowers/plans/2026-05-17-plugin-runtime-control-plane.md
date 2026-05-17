# Plugin Runtime Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development before production code and verify each task with focused tests. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make plugin management operational: persistent project-scoped enablement, permission preview before activation, trace inspection, runtime prompt preview, and IPC/UI surfaces for these controls.

**Architecture:** Keep plugin execution in the backend plugin substrate. Add a small project-local state file under `.auto-claude/plugins/state.json`, extend the CLI with control-plane commands, expose the commands through Electron IPC/preload APIs, and enhance the existing Plugin Manager to show permission/runtime diagnostics.

**Tech Stack:** Python 3.12, existing plugin registry/runtime, pytest, Electron IPC, React/TypeScript, Vitest.

---

### Task 1: Persistent Enablement and Backend Control Commands

**Files:**
- Modify: `apps/backend/plugins/registry.py`
- Modify: `apps/backend/plugins/cli.py`
- Modify: `tests/test_plugin_cli.py`
- Create: `tests/test_plugin_control_plane.py`

- [x] **Step 1: Add RED tests**

Cover persistent disable/enable state, `permission-diff --json`, `traces --json`, and `preview-context --json`.

- [x] **Step 2: Verify RED**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_plugin_control_plane.py tests/test_plugin_cli.py -q`

Expected: FAIL because control-plane commands and persistent state do not exist yet.

- [x] **Step 3: Implement registry state and CLI commands**

Add `.auto-claude/plugins/state.json` read/write helpers. Default valid plugins remain enabled unless explicitly disabled. Add machine-readable commands for permission diff, trace reading, and prompt augmentation preview.

- [x] **Step 4: Verify GREEN**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_plugin_control_plane.py tests/test_plugin_cli.py -q`

Expected: PASS.

### Task 2: Electron IPC and Preload Surface

**Files:**
- Modify: `apps/frontend/src/main/plugins/types.ts`
- Modify: `apps/frontend/src/main/plugins/loader.ts`
- Modify: `apps/frontend/src/main/plugins/loader.test.ts`
- Modify: `apps/frontend/src/preload/api/plugin-api.ts`
- Modify: `apps/frontend/src/shared/constants/ipc.ts`
- Modify: `apps/frontend/src/shared/types/ipc.ts`
- Modify: `apps/frontend/src/renderer/lib/browser-mock.ts`

- [x] **Step 1: Add RED IPC tests**

Cover `plugin:permissionDiff`, `plugin:traces`, and `plugin:previewContext` invoking the backend CLI with project cwd.

- [x] **Step 2: Implement IPC/preload/types**

Expose `getPluginPermissionDiff`, `getPluginTraces`, and `previewPluginContext`.

- [x] **Step 3: Verify GREEN**

Run: `npm --prefix apps/frontend test -- src/main/plugins/loader.test.ts`

Expected: PASS.

### Task 3: Plugin Manager UI

**Files:**
- Modify: `apps/frontend/src/renderer/components/plugins/PluginManager.tsx`
- Modify: `apps/frontend/src/renderer/components/plugins/PluginCard.tsx`
- Modify: `apps/frontend/src/shared/i18n/locales/en/plugins.json`
- Modify: `apps/frontend/src/shared/i18n/locales/fr/plugins.json`

- [x] **Step 1: Add visible controls**

Show permission diff before enabling, add trace and prompt-preview actions, and keep all user-facing text behind i18n keys.

- [x] **Step 2: Verify TypeScript**

Run: `npm --prefix apps/frontend run typecheck`

Expected: PASS.

### Task 4: Final Verification

**Files:**
- No extra production files.

- [x] **Step 1: Run backend focused tests**

Run: `/Users/om/PycharmProjects/Auto-Coding/.venv/bin/python -m pytest tests/test_plugin_control_plane.py tests/test_plugin_cli.py tests/test_plugin_runtime.py -q`

- [x] **Step 2: Run frontend focused tests**

Run: `npm --prefix apps/frontend test -- src/main/plugins/loader.test.ts`

- [x] **Step 3: Run format/lint checks**

Run focused Ruff and frontend typecheck.
