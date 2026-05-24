# Non-Claude Provider Full Autonomy Roadmap

Status: Draft, in active development.
Owner: runtime / provider integration track.
Audience: contributors who land code under `apps/backend/agents/runtime/`,
`apps/backend/core/providers/`, `apps/backend/cli/runtime_commands.py`,
`apps/backend/cli/provider_smoke_commands.py`, and the QA agent stack.

## Goal

Bring OpenAI, Google / Gemini, OpenRouter, LiteLLM, ZhipuAI, and Ollama (and
viable CLI runners) to the point where `full_autonomous="yes"` in
`PROVIDER_RUNTIME_COMPATIBILITY` is the truth of the runtime, not a label
chosen by policy. Today the only wired non-Claude full-autonomous path is
Codex CLI.

## Guiding Principles

1. **Capability before promotion.** A provider does not move to
   `full_autonomous="yes"` until its runtime can actually execute the full
   surface (MCP execution, mutating subagents, sandbox), not just claim it via
   a relabeled adapter.
2. **Capability is not policy.** `RuntimeCapabilities` describes what the
   runtime physically supports. Promotion to full autonomous is a separate
   policy decision, expressed via `AutonomyPolicy`, and never lies about
   capability flags.
3. **Per-provider configuration from the start.** No global threshold
   constants. Thresholds (min stable runs, history freshness, required cases)
   live in a config module with per-provider and per-phase overrides.
4. **Evidence comes from CI, not opt-in env vars.** Live fault probes and
   live task-family coverage must be reachable from a scheduled CI run, so
   readiness can be proven without a developer toggling env flags locally.
5. **qa_fixer and qa_reviewer are first-class runtime citizens.** They must
   go through `create_runtime_session`, not directly instantiate
   `ClaudeSDKClient`.
6. **Honest documentation.** Removed features and partial work are stated as
   such. The Full Autonomous Provider Roadmap Status table in
   [docs/architecture/provider-runtime-modes.md](../architecture/provider-runtime-modes.md)
   tracks reality, not aspiration.
7. **One promotion = one PR = one evidence package.** No bulk allowlist
   moves.
8. **Do not invent new runtime modes.** The four existing modes
   (`full_autonomous`, `generic_edit`, `patch_proposal`, `analysis_only`)
   stay; promotion lives in policy.

## Phase 0 — Foundation cleanup (parallelizable)

Small independent PRs that pay down debt introduced by the
direct-API-autonomy series (PRs #257 - #263). Must land before Phase 1.

### 0.1 Split capability from policy
[apps/backend/agents/runtime/capabilities.py](../../apps/backend/agents/runtime/capabilities.py)

- Drop `RuntimeCapabilities.direct_api_autonomous()` in its current form
  (it sets `native_tool_loop=True` while wrapping a runtime that may use the
  JSON fallback loop).
- Add `RuntimeCapabilities.promoted_edit()` that is byte-identical to
  `generic_edit()` (no `native_tool_loop=True`).
- Introduce a separate `AutonomyPolicy` (see 0.4) that carries
  `promoted_to_full_autonomous: bool`.
- `DirectApiAutonomousRuntimeSession` keeps its name but advertises honest
  capabilities and consults the policy for promotion.

### 0.2 Route qa_fixer and qa_reviewer through the runtime layer
Landed via
[apps/backend/agents/runtime/qa_phase_routing.py](../../apps/backend/agents/runtime/qa_phase_routing.py)
plus call sites in
[apps/backend/qa/loop.py](../../apps/backend/qa/loop.py). The qa_fixer
and qa_reviewer session objects themselves still receive a
`ClaudeSDKClient` because the runtime path remains Claude-only; what
changed is that the loop now resolves the runtime contract via
`resolve_qa_runtime(...)` BEFORE building the session, so:

- Replace direct `claude_agent_sdk.ClaudeSDKClient` instantiation with
  `create_runtime_session(...).context_client`, mirroring
  [planner.py:231](../../apps/backend/agents/planner.py) — DONE in
  spirit: the resolver enforces the contract, then the loop hands off
  to the SDK client as before until Phase 1 capability wiring lands.
- Treat MCP-tool-requiring QA fixtures (Electron E2E) as a
  `RuntimeRequirements` constraint; non-Claude providers fail fast for QA
  phases that require MCP execution until 1.1 is done.
- New test: `tests/test_qa_runtime_integration.py` proves coder and qa_fixer
  honor the same runtime-modes contract.

### 0.3 Unify artifact path
- Pick `.auto-claude/runtime/` as the canonical location for runtime
  artifacts (currently split across `.auto-Codex/` and `.auto-claude/`).
- New module `apps/backend/core/paths.py` with `AUTO_CODE_RUNTIME_DIR`.
- Read code accepts both legacy `.auto-Codex/` and new path; write code uses
  the new path only.
- Migration script `scripts/migrate_auto_codex_dir.py` moves existing data.
- Update callers:
  [cli/provider_smoke_commands.py:217-220](../../apps/backend/cli/provider_smoke_commands.py),
  [cli/runtime_commands.py](../../apps/backend/cli/runtime_commands.py), and
  the gate module introduced by PR #263 once it lands.

### 0.4 Per-provider autonomy policy config
[apps/backend/cli/provider_smoke_commands.py:273-287](../../apps/backend/cli/provider_smoke_commands.py)

- New module `apps/backend/core/autonomy_policy.py` exposing a frozen
  `AutonomyPolicy` dataclass with defaults that match today's constants:
  - `min_stable_runs = 3`
  - `max_history_age_days = 7`
  - `required_e2e_runs = (...)`
  - `required_live_fault_cases = (...)`
  - `required_live_task_families = (...)`
  - `allowed_phases = ("coding",)`
- Per-provider overrides via env vars
  (`AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>=value`) and an optional
  `apps/backend/config/autonomy_policy.json` file.
- All current threshold constants in `provider_smoke_commands.py` and the
  gate module become lookups via `AutonomyPolicy.for_provider(name)`.
- The `--runtime-modes --json` payload includes the resolved policy for
  every provider so the frontend can render it.

### 0.5 PR #263 follow-ups
- Symmetrize `_append_missing` usage in the gate module.
- `DirectApiAutonomousGate.history_path` returns an absolute path.
- `runtime_decision.reason` stops claiming "fallback disabled" when the
  direct-API gate overrode the request.
- Rename `direct_api_autonomy.py` to
  `agents/runtime/gates/direct_api_autonomous_gate.py`.
- Cache `_load_provider_stats` within a single CLI invocation.

## Phase 1 — Real capability parity

This is the hard work. Each subsystem closes one of the gaps that today keep
direct-API providers below Claude SDK in real terms.

### 1.1 MCP execution for direct-API providers
[apps/backend/agents/runtime/mcp_bridge.py](../../apps/backend/agents/runtime/mcp_bridge.py)

- Generalize `RuntimeMcpBridge` execution wiring to all registered external
  servers (Graphiti, Linear, Electron, Puppeteer, custom), not only
  Context7.
- Add per-server smoke `mcp_execution_smoke_<server>` to the `provider_e2e`
  suite.
- Session reuse and connection pooling so one provider session reuses one
  MCP transport.
- Continue normalizing live schemas into `text` / `content` /
  `structured_content` / `is_error`.
- Promote `RuntimeCapabilities.promoted_edit()` to set `mcp=True` once a
  provider's MCP execution smoke is green.
- Acceptance: an OpenAI session can call `mcp__graphiti__add_episode` and
  receive a normalized result.

### 1.2 Mutating subagents with transactional merge
[apps/backend/agents/runtime/subagents.py](../../apps/backend/agents/runtime/subagents.py)

- Transactional child boundary: each child enters a staged workspace clone
  and exits with a patch relative to the parent baseline.
- Conflict-aware 3-way merge protocol; abort on conflict, surface a
  resolution artifact.
- Parent-approved apply / abort gate: preview before merge.
- `runtime_subagent_mutation_policy` flips from `blocked` to `enabled` only
  when 1.2.a-c are wired.
- Tests covering two parallel coder children that conflict on the same
  file.

### 1.3 Sandbox for direct providers
- Unify the sandbox interface across macOS Seatbelt, Linux bubblewrap, and
  Windows AppContainer.
- Generic Edit shell actions go through this layer rather than relying on
  the `core/security.py` allowlist alone.
- `RuntimeCapabilities.sandbox=True` becomes legal on `promoted_edit()`
  once the platform layer is in place.

### 1.4 Native tool loop per provider
[apps/backend/core/providers/adapters/](../../apps/backend/core/providers/adapters/)

| Provider   | Today                            | To do                                              |
|------------|----------------------------------|----------------------------------------------------|
| openai     | function calling, ok             | parallel_tool_calls, strict mode                   |
| openrouter | OpenAI-compat, ok                | per-model capability detection                     |
| litellm    | depends on routed model          | per-routed-model capability check                  |
| google     | Gemini schema, ok                | FunctionDeclaration parity vs OpenAI               |
| zhipuai    | mixed direct / OpenAI-compat     | branch-aware capability flag                       |
| ollama     | depends on local model           | model capability detection (llama3.1+, qwen2.5+)   |

Each adapter exposes `supports_native_tools(model: str) -> bool`. The
provider e2e suite stops silently downgrading to JSON fallback; it reports
the downgrade explicitly so promotion gates can flag it.

## Phase 2 — Evidence without opt-in

### 2.1 Scheduled live probes
- `scripts/nightly_provider_e2e.py` runs the full provider-e2e suite for
  each direct provider against real keys (CI secrets), then writes results
  to `.auto-claude/runtime/provider-smoke-history.json` via a bot PR.
- README badges per provider summarize last-7-day pass rate and freshness.

### 2.2 Per-provider cost calibration
[apps/backend/cli/provider_smoke_commands.py:62-63](../../apps/backend/cli/provider_smoke_commands.py)

- Replace fixed 10k input + 2k output benchmark with rolling per-model
  calibration persisted at `.auto-claude/runtime/cost-calibration.json`.
- `runtime_comparative_eval_matrix` uses measured cost when available, fixed
  benchmark only as fallback.

### 2.3 Quality and safety evals
- Add mini-SWE-bench style suite (5 - 10 small tasks, mixed fix / feature /
  refactor / test) callable from CI.
- Per-provider pass rate feeds the honest quality score that the comparative
  matrix exposes today.

## Phase 3 — Provider promotion (one at a time)

No bulk allowlist moves. Each promotion is its own PR with an evidence
package.

### 3.1 Pilot: OpenAI
Acceptance checklist for the "promote openai" PR:
- Phase 1.1 - 1.4 green for OpenAI.
- 10+ stable consecutive provider_e2e runs within the last 7 days.
- Mini-SWE-bench pass rate >= 60% on the configured model.
- Live probes cover all required cases.
- Cost calibration within +/-15% of the fixed estimate (or new estimate
  documented).

Code change: flip `full_autonomous="no"` -> `"yes"` for openai in
[apps/backend/agents/runtime/compatibility.py:157-166](../../apps/backend/agents/runtime/compatibility.py)
and remove openai from `DIRECT_API_AUTONOMOUS_PROVIDERS`, since the
promotion no longer needs to flow through the gate.

### 3.2 Subsequent order
By decreasing readiness:
1. OpenRouter (OpenAI-compat wrapper, trivial after OpenAI).
2. Google / Gemini (schema diffs from 1.4 resolved).
3. LiteLLM (per-routed-model capability check resolved).
4. ZhipuAI (direct branch only; Claude-compat path stays on the CLI runner
   profile).
5. Ollama (local; stricter per-model capability filter).

## Phase 4 — CLI runner class (parallel track)

Alternative full-autonomous path: wrap a ready CLI rather than promote a
direct provider. Codex CLI is the only wired runner today.

| Runner     | Priority | What is needed                                       |
|------------|----------|------------------------------------------------------|
| Gemini CLI | high     | command builder, resume semantics                    |
| Aider      | high     | git-aware mode, event parser                         |
| OpenCode   | mid      | event parser, artifact contract                      |
| Qwen Code  | mid      | command spec, capability check                       |
| Goose      | mid      | session model adaptation                             |

Per-runner tasks: command builder in
[apps/backend/agents/runtime/cli_profiles.py](../../apps/backend/agents/runtime/cli_profiles.py),
resume semantics, event parser in
`apps/backend/agents/runtime/adapters/<runner>_cli.py`, smoke wired into
`provider-smoke --runner <runner>`, contract entry in
`cli_runner_contract_matrix`.

## Phase 5 — Frontend control plane completion

### 5.1 Provider readiness dashboard
- Real-time grid (provider x phase), drill-down into trace, checkpoint,
  artifacts.
- Promote and demote actions surfaced behind explicit confirmation.

### 5.2 Live history charts
- Quality, cost, stability, safety trend lines over 30 days per provider.
- Anomaly highlight when a metric regresses beyond 2 sigma.

### 5.3 Artifact viewer
- Recovery checkpoint diff viewer.
- Mutation snapshot rollback UI.
- Subagent merge conflict resolver.

## Phase 6 — Recovery and edge case hardening

### 6.1 Generic Edit non-happy-path
- Repair flow UI: one-button repair or rollback against a concrete blocker.
- Auto-rollback when drift exceeds threshold.
- Idempotent batch retry with deduplication.

### 6.2 Staged overlay edge cases
- Symlinks, binary files, files > 10 MB, concurrent mutations within one
  transaction.
- Property-based tests (hypothesis) on trace consistency.

## Dependency layering

```text
Phase 0 -> Phase 1 -> Phase 3
        \-> Phase 2 -/
Phase 4 runs independently in parallel.
Phase 5 follows Phase 1 + 2.
Phase 6 is ongoing background work.
```

Minimum critical path to the first truly full-autonomous direct provider:
`0.1 -> 0.2 -> 0.4 -> 1.1 -> 1.4 (openai only) -> 2.1 -> 3.1`.

## First batch of PRs (in flight)

- **PR 1: Roadmap doc + Phase 0.4 per-provider autonomy policy.** Adds
  `apps/backend/core/autonomy_policy.py` with the `AutonomyPolicy`
  dataclass, env / file precedence, and refactors current thresholds to
  consume it. Defaults match today's constants so behavior is unchanged.
- **PR 2: Phase 0.3 path migration.** Introduces
  `apps/backend/core/paths.py`, makes reads tolerant of both legacy and new
  paths, makes writes use the new path, ships
  `scripts/migrate_auto_codex_dir.py`.
- **PR 3: Phase 0.2 QA runtime wiring.** Routes qa_fixer and qa_reviewer
  through `create_runtime_session`, adds the QA runtime integration test.
