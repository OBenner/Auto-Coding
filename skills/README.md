# Auto Code Skills

Repo-specific skills for working on Auto Code. The package adapts the useful structure from the OpenMetadata skills folder: a small workflow router, focused quality gates, PR prep, and domain-specific provider/plugin workflows.

## Skills

| Skill | Purpose |
| --- | --- |
| `auto-code-workflow` | Route Auto Code tasks to the right workflow. |
| `verification` | Require fresh evidence before completion claims. |
| `test-enforcement` | Map changed files to required checks. |
| `code-review` | Review requirements compliance before code quality. |
| `pr-checklist` | Prepare PRs against the repo template and `develop` target. |
| `provider-building` | Build providers and runtime adapters with readiness tiers. |
| `provider-review` | Review provider capabilities and runtime contracts. |
| `plugin-building` | Build optional plugins with manifest-first discipline. |
| `plugin-review` | Review plugin permissions, isolation, and lifecycle behavior. |

## Optional Agents

The `agents/` folder contains reviewer prompts that can be used by tools with subagent support. Metadata is provided for several clients:

- `openai.yaml` / `codex.yaml` for OpenAI/Codex-style skill UIs
- `claude.yaml` for Claude Code skill/plugin usage
- `gemini.yaml` for Gemini CLI style activation
- `generic.yaml` for Cursor, Copilot, Windsurf, and other Agent Skills compatible tools

## Hooks

`hooks/hooks.json` is a Claude Code compatible hook file. It is optional; Codex and other tools can use the skills without it.

## Attribution

This package is inspired by the public OpenMetadata `skills/` architecture, but the instructions here are written for Auto Code and its AGPL-3.0 repository conventions.
