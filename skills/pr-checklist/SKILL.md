---
name: pr-checklist
description: Prepare Auto Code pull requests with the repo template, develop target, test evidence, screenshots for UI changes, feature-toggle notes, and cross-platform checklist. Use before creating or updating a GitHub PR.
---

# PR Checklist

Use this before `gh pr create` or `gh pr edit`.

## Inspect The Branch

```bash
git status --short --branch
git diff origin/develop...HEAD --stat
git log origin/develop..HEAD --oneline
```

If the base is not `develop`, verify the user explicitly requested a different base.

## Required PR Body Evidence

Fill every section in `.github/PULL_REQUEST_TEMPLATE.md`:

- base branch: `develop`
- description: concrete behavior, not implementation trivia
- related issue: `Closes #...` or `N/A - reason`
- type and area
- local tests run, with command names
- cross-platform risk and how it is covered
- screenshots or recording for UI changes
- feature toggle or `N/A - complete and ready`
- breaking changes and migration notes

## Extra Auto Code Checks

- Provider/runtime work: include provider smoke or why it was skipped.
- Frontend setup/auth work: include the visible progression checked after save/login.
- Plugin work: include manifest permissions and isolation notes.
- CI fixes: mention the failing job/check and the current head SHA verified.

## Gate

Do not present the PR as ready if:

- test evidence is missing for changed behavior
- UI changes lack screenshot/recording notes
- provider or plugin changes lack runtime/permission checks
- the PR accidentally includes unrelated dirty files
