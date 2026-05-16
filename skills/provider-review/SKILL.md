---
name: provider-review
description: Review Auto Code provider, model-routing, auth, and runtime adapter changes for capability correctness, smoke coverage, fallback safety, and Claude/Codex-shaped assumptions. Use for provider PRs, runtime refactors, setup-flow changes, and readiness validation.
---

# Provider Review

Review provider work at the runtime contract level.

## Required Checks

1. Identify which provider, runtime mode, and auth path changed.
2. Read the full changed files and nearby provider/runtime implementations.
3. Check capability claims against actual implementation.
4. Look for hidden full-agent assumptions:
   - direct `.client` access
   - hard-coded `query()` or `receive_response()` expectations
   - tool-call support implied without tool-result handling
   - auth copy that blends OAuth/account login with API-key providers
5. Check fallback behavior and diagnostics for unsupported modes.
6. Verify tests or smoke checks cover the changed path.

## Output Categories

- **Blocker:** false capability claim, broken auth/config path, unsafe fallback, missing regression for a runtime contract.
- **Warning:** weak diagnostics, partial smoke coverage, unclear setup progression.
- **Suggestion:** docs/UI wording or matrix clarity.

## Evidence

Every finding needs:

- file and line
- the capability claim or runtime contract being violated
- the concrete check that would catch it

When no issues are found, still list smoke/test gaps.
