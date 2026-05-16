---
name: auto-code-workflow
description: Route Auto Code repository work to the right skill and quality path. Use when starting any non-trivial task in this repo, especially feature work, bug fixes, frontend changes, provider/runtime work, plugin work, PR preparation, CI debugging, or code review.
---

# Auto Code Workflow

Use this as the first repo-specific routing skill. Pick the narrowest follow-on skill that matches the task, then follow that skill instead of keeping all rules in context.

## Routing

| Task | Use next |
| --- | --- |
| Feature or behavior change | `test-enforcement`, then `verification` before completion |
| Bug fix | reproduce the failure first, add or identify a regression check, then `verification` |
| Code review or PR review | `code-review` |
| Opening or updating a PR | `pr-checklist` |
| Provider, model, or runtime adapter work | `provider-building` or `provider-review` |
| Plugin or extension work | `plugin-building` or `plugin-review` |
| Frontend UI change | `test-enforcement`, with i18n and Electron checks included |
| CI failure | inspect the failing job/log first, then verify the exact fix |

## Repo Rules

- Use the Codex Agent SDK path already in the repo. Do not introduce direct Anthropic API clients.
- Target pull requests to `develop` unless the user explicitly asks for a maintainer hotfix to `main`.
- Keep optional providers and plugins outside the core path until they are explicitly enabled.
- For frontend text, use `react-i18next` keys in every supported locale file touched by the feature.
- For platform-sensitive code, use the centralized platform abstraction instead of direct path or OS assumptions.
- Treat provider readiness as layered: connection test, runtime smoke, then mini-pipeline readiness when deeper confidence is needed.
- Verify with current files and commands before saying the work is ready.

## Minimal Flow

1. Read the relevant files before proposing or editing.
2. Identify the layer: backend, frontend, web, provider/runtime, plugin, docs, CI, or PR.
3. Choose the matching skill from the routing table.
4. Make the smallest complete change that satisfies the task.
5. Run the checks selected by `test-enforcement` or the more specific skill.
6. Use `verification` before any completion, commit, push, or PR claim.
