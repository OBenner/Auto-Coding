---
name: test-enforcement
description: Decide which tests and quality checks are required for Auto Code changes. Use after implementing or while reviewing any feature, bug fix, provider/runtime change, plugin change, frontend change, docs change with generated content, or PR diff.
---

# Test Enforcement

Map changed files to checks. Prefer targeted checks for small changes and broaden when shared contracts, runtime paths, or user-facing flows changed.

## Step 1: Classify The Diff

Use:

```bash
git diff --name-only
git diff --cached --name-only
git diff origin/develop...HEAD --name-only
```

Use the comparison that matches the task. Do not include unrelated dirty files in the test scope.

## Step 2: Required Checks

| Path pattern | Required checks |
| --- | --- |
| `apps/backend/core/providers/`, `apps/backend/agents/runtime/` | runtime/provider pytest targets, provider smoke tests when credentials are available |
| `apps/backend/agents/`, `apps/backend/qa/`, `apps/backend/review/` | focused pytest tests plus affected agent/review tests |
| `apps/backend/cli/` | CLI command tests and direct command invocation where cheap |
| `apps/frontend/src/` | TypeScript/lint/tests, i18n locale sync for visible text, Electron/browser verification for user flows |
| `apps/web-backend/` | FastAPI import/tests and API route tests |
| `apps/web-frontend/` | frontend lint/build/tests and browser screenshot when UI changed |
| `examples/plugins/`, `apps/backend/plugins/` | plugin manifest validation, plugin load tests, permission/isolation tests |
| `docs/`, `guides/`, `site/` | docs inspection, generated site checks when site assets changed |
| `.github/workflows/`, scripts | local script syntax plus CI command parity where practical |

## Step 3: Coverage Expectations

- Bug fixes need a regression check when the behavior is testable.
- New backend behavior needs focused pytest coverage.
- New user-facing frontend behavior needs a unit or flow check and i18n coverage.
- Provider work needs capability-level validation, not just adapter import success.
- Plugin work needs manifest and permission-boundary validation.

## Step 4: Report

Return a short table:

| Area | Check | Result |
| --- | --- | --- |
| backend | `apps/backend/.venv/bin/python -m pytest ...` | pass/fail/skipped |

List skipped checks with the blocker, not as success.
