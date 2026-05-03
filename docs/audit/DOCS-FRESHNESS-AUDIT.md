# Documentation Freshness Audit

**Status:** Active maintenance checklist  
**Scope:** Public docs, guides, architecture docs, and the GitHub Pages portal  
**Context:** Current multi-runtime work and the new `site/` docs portal

## Executive Summary

The documentation is useful, but it has drifted from the current product shape.
The biggest issue is not missing Markdown volume. The issue is that important
entry documents still describe an older Claude-only mental model while the code
now expose a capability-aware runtime system.

This audit separates already-applied fixes from the remaining cleanup backlog.

## Already Updated In This Branch

| Area | Change |
| --- | --- |
| GitHub Pages docs | Added `site/` as a multi-language product documentation portal. |
| README quick start copy | Removed time-based onboarding claims and changed the setup phrase from "Connect Claude" to "Configure a runtime." |
| Quick Start | Reframed first-run setup around runtime choice: Claude Code OAuth, Codex CLI profile, or limited API-key providers. |
| CLI Usage | Updated Python requirement to 3.12+, added Codex CLI profile setup, and clarified limited provider modes. |
| CI/CD guide | Added a multi-runtime freshness note and clarified runtime auth paths. |
| Environment variables | Added Codex provider/runtime documentation and corrected Claude runtime auth guidance. |
| Provider abstraction | Updated provider list and runtime-layer explanation to include Codex CLI and `generic_edit`. |
| ADR-004 | Added a current implementation note so older `CLAUDE_PROVIDER` references are not mistaken for current config. |

## Stale Or Risky Docs Found

| Priority | Document | Issue | Recommended Fix |
| --- | --- | --- | --- |
| P0 | `guides/ci-cd-integration.md` | Legacy env names are still present because the current CLI uses `AUTO_CLAUDE_*`; the guide now needs a clearer compatibility note once `AUTO_CODE_*` aliases exist. | Add runtime alias guidance after the CLI supports new env names. |
| P0 | `docs/configuration/environment-vars.md` | Some provider sections still use old capability language and need runtime-mode cross-links. | Add runtime capability notes to each provider section. |
| P1 | `guides/TROUBLESHOOTING.md` | FAQ still says Auto Code cannot run without Claude Code CLI. | Update to explain Claude full runtime vs Codex CLI full runtime vs limited direct-provider modes. |
| P1 | `docs/modules/backend-architecture.md` | Backend docs still describe all AI interactions as Claude Agent SDK-only. | Reframe as provider/runtime architecture while preserving Claude SDK as the default full runtime. |
| P1 | `docs/api/backend-api.md` | Auth and provider sections still mix `ANTHROPIC_API_KEY` examples with runtime auth. | Split runtime auth, memory provider auth, and direct-provider API keys. |
| P1 | `docs/search/INDEX.md` | Search keywords still emphasize "15-minutes" and miss docs freshness/site portal. | Add docs audit, Pages portal, runtime router, Codex CLI, and `generic_edit` keywords. |
| P2 | `docs/VERIFICATION-CHECKLIST.md` | Contains old time-based onboarding acceptance criteria. | Replace with outcome-based onboarding criteria. |
| P2 | `docs/audit/FEATURE-COVERAGE-GAP.md` | Gap analysis predates the current multi-runtime docs and says multi-provider docs are still missing. | Mark as historical or refresh coverage against current runtime docs. |

## Must-Add Documentation

| Document | Why It Is Needed | Suggested Location |
| --- | --- | --- |
| Runtime Selection Guide | Users need a practical decision tree: Claude full runtime, Codex CLI full runtime, direct API limited modes, fallback, or runner router. | `guides/RUNTIME-SELECTION.md` |
| Codex CLI Runner Setup | Auto Code now has a real Codex CLI runtime path, but users need setup, `CODEX_HOME`, profile storage, smoke checks, and troubleshooting. | `guides/CODEX-CLI-RUNNER.md` |
| Provider Capability Matrix For Users | Architecture docs have the matrix, but the product docs need a less technical "what can I use this for?" view. | `guides/PROVIDER-CAPABILITY-MATRIX.md` |
| Settings And Onboarding Guide | The frontend now has separate account-login and API-key paths; this needs user-facing documentation. | `guides/SETTINGS-AND-ONBOARDING.md` |
| Runtime Artifact Guide | Users need to know where `generic_edit`, fallback, Codex CLI, analysis-only, and smoke-test artifacts are stored and how to read them. | `guides/RUNTIME-ARTIFACTS.md` |
| Documentation Freshness Policy | The repo needs a short rule for avoiding drift after runtime/provider changes. | `docs/STYLE_GUIDE.md` or `docs/audit/` |

## Recommended Cleanup Order

1. Fix authentication docs in `guides/ci-cd-integration.md`, `guides/TROUBLESHOOTING.md`, and `docs/api/backend-api.md`.
2. Add the missing runtime selection and Codex CLI runner guides.
3. Refresh backend architecture docs to match provider/runtime layering.
4. Refresh the search index and documentation portal to include the new GitHub Pages site and audit docs.
5. Mark old verification/gap documents as historical snapshots where they are no longer current.

## Documentation Rule Going Forward

When a change adds or changes provider behavior, update all three layers in the
same PR:

1. Architecture contract: `docs/architecture/`.
2. User workflow: `guides/`.
3. Public/product surface: `site/` and `docs/search/INDEX.md`.
