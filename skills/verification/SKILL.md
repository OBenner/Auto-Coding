---
name: verification
description: Verify Auto Code work before claiming completion, committing, pushing, or opening a PR. Use after any code, docs, provider, plugin, frontend, CI, or PR-prep change when fresh evidence is needed.
---

# Verification

Do not call a task done without fresh evidence. Pick the command set that matches the changed files and report only what actually ran.

## Check Selection

| Change area | Verification |
| --- | --- |
| Python backend | `apps/backend/.venv/bin/python -m pytest <tests> -q` |
| Backend lint or syntax-only docs/code | `apps/backend/.venv/bin/python -m py_compile <files>` or the relevant pytest target |
| Frontend | `cd apps/frontend && npm run lint` plus targeted tests/build when behavior changed |
| Electron UI flow | run the app with `npm run dev` and verify the flow with Electron/browser automation when available |
| Web backend | run the relevant FastAPI tests or import/syntax checks from `apps/web-backend` |
| Provider runtime | run the relevant provider/runtime pytest files and, when credentials exist, `run.py --provider-smoke --json` |
| Plugin | run plugin unit tests plus manifest/load checks where available |
| Docs-only | validate links/format when practical, otherwise inspect the rendered or changed docs directly |
| PR/CI fix | re-run the failing command or inspect the current GitHub check for the fixed head SHA |

## Required Evidence

When reporting completion, include:

- command name
- exit status or clear pass/fail signal
- important test count or relevant output line
- any skipped check and why it could not run

## Stop Conditions

- If a check fails, do not hide it behind partial successes.
- If a check needs network, credentials, Docker, or GUI access that is not available, say so and name the next best local check that was run.
- If the change touches generated artifacts, verify the generator or explain why generation was not required.
