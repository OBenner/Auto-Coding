---
name: code-review
description: "Review Auto Code changes with a two-stage process: first requirements/spec compliance, then code quality, security, tests, provider/runtime boundaries, frontend i18n, and cross-platform risks. Use for local diffs, branches, PRs, or review follow-up."
---

# Code Review

Lead with findings. Report only issues you can ground in actual code, tests, commands, or PR metadata.

## Stage 1: Requirements Compliance

1. Identify the stated goal from the user request, spec, issue, PR body, or implementation plan.
2. Inspect the diff and read the full changed files that matter.
3. Check whether every requirement has a corresponding implementation and verification path.
4. Flag scope creep, missing generated artifacts, or cross-layer gaps.

Stop after Stage 1 if the change does not implement the requested behavior.

## Stage 2: Quality Review

Check the relevant concerns:

- Backend follows existing agent, QA, provider, and review-service patterns.
- Provider/runtime changes do not assume every provider supports the Claude/Codex full-agent surface.
- Frontend user text uses i18n keys and keeps main-process filesystem work out of the renderer.
- Platform-sensitive code uses `apps/frontend/src/main/platform/` or backend platform helpers.
- Plugin changes declare only needed permissions and respect isolation boundaries.
- Security-sensitive code avoids command injection, path traversal, untrusted deserialization, and secret logging.
- Tests verify behavior rather than only mocks or imports.

## Output

Use this order:

1. Findings, ordered by severity, each with `file:line`.
2. Open questions or assumptions.
3. Brief test gaps or residual risk.
4. Short summary only after findings.

If there are no findings, say that clearly and still name any checks you did not run.
