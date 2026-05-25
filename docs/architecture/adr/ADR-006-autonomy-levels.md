# ADR-006: User-facing autonomy levels

**Date:** 2026-05-23
**Status:** Proposed
**Deciders:** Auto Code Core Team
**Tags:** autonomy, runtimes, providers, configuration, ux

---

## Context

The provider/runtime layer accumulated configuration faster than it
accumulated coherent user-facing concepts. As of today the operator has
to understand and tune a matrix of:

| Surface | Env vars | Description |
|---------|----------|-------------|
| Global runtime mode | `AUTO_CODE_RUNTIME_MODE`, `AUTO_CLAUDE_RUNTIME_MODE` (legacy) | Forces a runtime mode for the whole run |
| Per-agent runtime | `AGENT_RUNTIME_MODE_<TYPE>` | Per-agent override |
| Per-agent provider/model | `AGENT_PROVIDER_<TYPE>`, `AGENT_MODEL_<TYPE>` | Per-agent provider routing |
| Runtime fallback | `AUTO_CODE_RUNTIME_FALLBACK` | Opt-in degrade to limited mode |
| Direct API autonomy kill switch | `AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS` | Allows promoted direct providers to coder |
| CLI runner router | `AUTO_CODE_CLI_RUNNER_ROUTER` | Opt-in routing to Codex/other CLI runners |
| Per-provider autonomy policy | `AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>` (×6 knobs) + `AUTO_CODE_AUTONOMY_DEFAULT_<KNOB>` + `AUTO_CODE_AUTONOMY_POLICY_FILE` | Per-provider gate thresholds |
| Live fault probes | `AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES`, `AUTO_CODE_PROVIDER_E2E_LIVE_TASKS` | Opt-in expensive probes |
| Provider-specific keys/models | `OPENAI_API_KEY`, `OPENAI_MODEL`, `GOOGLE_API_KEY`, … (×6 providers) | Provider credentials |

Two structural problems:

1. **No user-facing concept of autonomy.** The operator wants to answer a
   single question — *"how independent should the agent be?"* — but is
   forced to set 3-5 unrelated env vars across three different prefixes
   (`AUTO_CODE_RUNTIME_*`, `AUTO_CODE_AUTONOMY_*`,
   `AUTO_CODE_DIRECT_API_*`).
2. **Every PR grows the surface.** Phases #257-#263 added 3 env vars
   each, my Phase 0.4 added 6 more (one per knob × N providers via
   templated names). Without an opinionated top-level concept the
   accretion continues PR by PR.

The matrix is internal implementation detail: provider × runtime mode ×
policy gate × runner route × fallback toggle. The user-facing question is
much smaller: *which agents should be allowed to act on their own, and
how aggressively?*

## Decision

Introduce a single user-facing concept — `AUTO_CODE_AUTONOMY` — with four
discrete levels. All existing env vars stay as low-level advanced
overrides, documented explicitly as "normally not needed". `AUTO_CODE_AUTONOMY`
becomes the only knob exposed in the quickstart docs and the default UI.

```text
AUTO_CODE_AUTONOMY=off | claude | safe | bold
```

| Level | Intent | Internally |
|-------|--------|------------|
| `off` | Agent never writes the workspace; analysis and patch suggestions only. | `AUTO_CODE_RUNTIME_MODE=analysis_only`; runtime fallback OFF; direct API gate OFF; CLI runner router OFF. |
| `claude` (default) | Claude / Codex CLI full autonomy. Direct API providers refused with a clear capability error. | `AUTO_CODE_RUNTIME_MODE=full_autonomous`; runtime fallback OFF; direct API gate OFF; CLI runner router OFF. Today's default. |
| `safe` | + direct API providers run through generic_edit, and a passed AutonomyPolicy gate promotes them to coder full_autonomous. Still fail-fast on missing capability. | `AUTO_CODE_RUNTIME_MODE=full_autonomous`; runtime fallback ON; direct API gate ON. |
| `bold` | + direct providers can run promoted-edit without waiting for the gate. Power-user mode for benchmarking and experiments. CI uses this to seed evidence. | + skip AutonomyPolicy gate; treat evidence as advisory. |

`AutonomyPolicy` thresholds simplify to three presets selected by an
optional second knob:

```text
AUTO_CODE_AUTONOMY_PRESET=strict | standard | lax
```

- `strict`: 10 stable runs / 3 days freshness / all required cases.
- `standard` (default): 3 stable runs / 7 days freshness / all required
  cases. Identical to today's defaults.
- `lax`: 1 stable run / 30 days freshness / critical cases only.

Per-knob env overrides (`AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>`) and the
JSON file remain for enterprise users who must tune one provider; they
are documented in an "advanced configuration" section and rendered in
`--runtime-modes --json` so observability stays intact.

## Rationale

The split between **policy** (operator intent) and **mechanism**
(provider/runtime matrix) is the same split that worked for ADR-005:
provider answers "which model?", runtime answers "which session
behavior?". Adding `AUTO_CODE_AUTONOMY` adds a third layer that answers
"how independent is this run?". Each layer can evolve independently:

- A new provider (Phase 1 of the roadmap) does not need a new env var to
  participate in autonomy promotion; it inherits whatever `safe`/`bold`
  already grants.
- A new runtime (CLI runner like Aider, OpenCode) likewise plugs into
  the same level enum.
- Removing env vars in a future PR no longer surprises users who never
  set them, because the level above always answers their intent.

### Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| **A. Status quo + better docs.** | Zero code change; just clarify when to set which env var. | Doesn't fix accretion; next PR adds another env var; operator still has to read 10 pages. |
| **B. Single autonomy level enum (this ADR).** | One question, one answer; existing env vars become advanced; new providers and runtimes inherit the level. | One-time refactor; needs a deprecation note on docs that still describe the matrix. |
| **C. Auto-detect everything; drop env vars.** | Smallest surface possible. | Removes operator control in non-default scenarios; CI/secrets/per-agent routing still need overrides; over-corrects. |
| **D. YAML/TOML config file as the only knob.** | Editor-friendly; structured. | Requires file in every project; env-driven CI flows lose simplicity; conflicts with project-local secrets discipline. |

Option **B** is the decision: keep env vars as the low-level interface
the codebase already speaks, add one high-level concept that maps to
them, document only the level in the quickstart.

## Consequences

### Positive

- The quickstart shrinks to *"set `AUTO_CODE_AUTONOMY=safe` and you are
  done"*; current quickstart has to enumerate the matrix.
- Future provider/runtime PRs add capability, not configuration knobs.
- `--runtime-modes` JSON output gains a top-level `autonomy_level` field
  so dashboards and the Electron control plane can show one indicator
  rather than four matrices.
- Memory of "what did I set last time" collapses to one variable; CI
  reproduction becomes trivial.
- Removes implicit pressure to add more env vars in upcoming Phase 1
  capability PRs.

### Negative

- One-time documentation update across `docs/configuration/`,
  `docs/architecture/provider-runtime-modes.md`, `guides/QUICK-START.md`,
  and the Electron settings panel.
- `AUTO_CODE_AUTONOMY` must be backward-compatible with combinations
  that explicitly set low-level env vars (precedence: explicit
  low-level value wins, level only fills the gaps).
- The Phase 0.4 per-knob env vars become "advanced" rather than primary,
  which is a small step back from the configurability they offered to
  the few users that already adopted them.
- Power users may dislike a four-bucket enumeration; the `bold` level
  plus low-level overrides give them an escape hatch but it is one
  level less granular than the per-knob matrix today.

### Neutral

- Existing env vars keep working unchanged: `AUTO_CODE_AUTONOMY` is
  additive.
- The AutonomyPolicy dataclass stays as-is; only its env var surface
  shrinks to presets in the default UX.
- Tests cover both paths: low-level overrides still tested, level
  presets get new tests.

## Implementation notes

Out of scope for this ADR; the follow-up PR ("Phase 0.6: simplify
autonomy surface") will:

1. Add `core/autonomy_level.py` with `AutonomyLevel` enum and a
   `resolve_autonomy_settings(env)` function returning a frozen
   dataclass that maps level + preset to the existing knobs.
2. Wire the resolved settings into the four current entry points:
   `agents/coder.py`, `agents/planner.py`,
   `agents/runtime/qa_phase_routing.py`, `cli/runtime_commands.py`. The
   resolver runs once per session start.
3. Update `--runtime-modes --json` payload to include
   `"autonomy_level": "...", "autonomy_preset": "..."` and a
   `low_level_overrides` map.
4. Update docs to lead with `AUTO_CODE_AUTONOMY`; move the matrix to an
   "Advanced configuration" appendix.
5. Update the autonomy roadmap to mark Phase 0.4 as superseded for
   default UX, retained for advanced configuration.

Precedence rules (highest first):

1. Explicit low-level env var (`AGENT_RUNTIME_MODE_*`,
   `AUTO_CODE_RUNTIME_MODE`, `AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS`,
   per-knob policy vars).
2. `AUTO_CODE_AUTONOMY` level mapping.
3. Module defaults (today's behavior, equivalent to `claude` level).

This keeps every existing test green: tests that set explicit env vars
exercise rule #1; the new level tests exercise rule #2; the absence of
both falls into rule #3.

The `AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS` env var is retained for one
release cycle as a deprecated escape hatch; setting it raises a warning
recommending the equivalent `AUTO_CODE_AUTONOMY=safe`. It is removed in
the release after that.

## References

- [ADR-004: Multi-provider support](./ADR-004-multi-provider-support.md)
- [ADR-005: Multi-runtime agent engine](./ADR-005-multi-runtime-agent-engine.md)
- [Provider runtime modes](../provider-runtime-modes.md)
- [Non-Claude provider autonomy roadmap](../../roadmap/non-claude-provider-autonomy.md)

---

*This ADR follows the [Auto Code ADR format](./template.md). See the [ADR index](./README.md) for all decisions.*
