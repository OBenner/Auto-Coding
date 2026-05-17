# Provider Runtime Modes

This document describes how Auto Code runs agent sessions across Claude and
non-Claude providers after the runtime engine split. It is the current
compatibility contract for provider support.

## Summary

Auto Code remains Claude-first for full autonomous coding. The Claude Agent SDK
is still the only runtime that provides the complete agent surface Auto Code
depends on: tools, MCP servers, shell execution, filesystem edits, security
hooks, and session lifecycle behavior.

Other providers can still be useful, but they run through limited runtime modes:

- `analysis_only` for phases that only need text reasoning.
- `generic_edit` for an experimental provider-neutral JSON action loop that can
  read files, write files, apply patches, run validated single commands, inspect
  git state, and run bounded read-only runtime subagents when the caller wires a
  subagent session factory.
- `patch_proposal` for providers that return a structured unified diff proposal
  that Auto Code validates and applies locally.

The runtime engine fails fast when the selected provider cannot satisfy the
capabilities required by the current phase.

## Runtime Modes

| Runtime mode | Purpose | Required capabilities | Typical providers |
|--------------|---------|-----------------------|-------------------|
| `full_autonomous` | Full planner/coder/QA workflow with tools and filesystem access | Tools, MCP, shell, filesystem edits, workspace access, structured output | Claude Agent SDK, Codex CLI, Claude Code-compatible runners |
| `generic_edit` | Experimental local action loop for coder subtasks | Text completion, structured JSON actions, local file/patch/shell tools | OpenAI, Google, LiteLLM, OpenRouter, ZhipuAI, Ollama |
| `patch_proposal` | Model proposes a patch; Auto Code validates and applies it locally | Text completion, structured output, local patch application | OpenAI, Google, LiteLLM, OpenRouter, ZhipuAI, Ollama |
| `analysis_only` | Text-only analysis without edits or tools | Text completion or streaming | OpenAI, Google, LiteLLM, OpenRouter, ZhipuAI, Ollama |

## Provider Compatibility Matrix

The same compatibility table is available from the CLI:

```bash
python run.py --runtime-modes
python run.py --runtime-modes --json
```

| Provider | Full autonomous coding | Generic edit | Analysis-only | Patch proposal | Notes |
|----------|------------------------|--------------|---------------|----------------|-------|
| `claude` | Yes | Not needed | Yes | Not needed | Uses the Claude Agent SDK path and keeps existing behavior. |
| `openai` | No | Experimental | Limited | Limited | Direct OpenAI SDK sessions use native tool calls when available, with JSON fallback. |
| `google` | No | Experimental | Limited | Limited | Gemini can use local actions with Gemini-compatible tool schemas; MCP parity is not implemented. |
| `litellm` | No | Experimental | Limited | Limited | Gateway provider; native tools depend on routed model/gateway support. |
| `openrouter` | No | Experimental | Limited | Limited | OpenAI-compatible gateway with native tools plus JSON fallback. |
| `zhipuai` | No | Experimental | Limited | Limited | Direct ZhipuAI/Z.AI chat path is OpenAI-like and limited. Z.AI's Claude-compatible endpoint is tracked as a separate Claude Code runner profile. |
| `ollama` | No | Experimental | Limited | Limited | Local models can attempt generic edit without remote code sharing. |

`Limited` means the provider is allowed only when the selected runtime mode does
not require missing capabilities. It does not imply the provider has been
validated for every agent phase or every model.

`zhipuai` in this table means Auto Code's direct ZhipuAI/Z.AI provider adapter.
Z.AI also exposes a Claude/Anthropic-compatible endpoint for Claude Code-style
clients. Auto Code tracks that separately as the `zai_claude_code` CLI runner
profile because the full autonomous behavior comes from the Claude Code runtime
surface, not from the direct ZhipuAI chat-completions adapter.

## Configuration

### Claude Default

No runtime override is required for the default full autonomous path:

```bash
AI_ENGINE_PROVIDER=claude
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

### Per-Agent Patch Proposal Mode

Use per-agent provider routing when Claude should remain available for phases
that need full autonomy, while coder subtasks use a limited provider:

```bash
AI_ENGINE_PROVIDER=claude

AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=patch_proposal

OPENAI_API_KEY=sk-...
```

### Per-Agent Generic Edit Mode

Use the same per-agent routing shape for the experimental local action loop:

```bash
AI_ENGINE_PROVIDER=claude

AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=generic_edit

OPENAI_API_KEY=sk-...
```

### Command-Line Runtime Override

The CLI can override the runtime mode for a run:

```bash
python run.py --spec 001 --runtime-mode patch_proposal
```

Provider selection can also be supplied on the command line:

```bash
python run.py --spec 001 --provider openai --runtime-mode analysis_only
```

For the experimental generic local action loop, use:

```bash
AGENT_PROVIDER_CODER=openai AGENT_RUNTIME_MODE_CODER=generic_edit python run.py --spec 001
```

For a non-mutating analysis pass that does not enter the coding loop, use:

```bash
python run.py --spec 001 --provider openai --analyze
python run.py --spec 001 --provider openai --analyze --analysis-prompt "Review implementation risks"
```

The analysis output is saved under `artifacts/analysis_only_analysis_*.md`.

To verify a configured provider before using it in a spec, run an opt-in smoke
check:

```bash
python run.py --provider openai --provider-smoke
python run.py --provider openai --model gpt-4o --provider-smoke --json
```

The smoke check sends a short text-only request through the provider abstraction
and reports whether the configured key/model can return a response. Its JSON
output includes `runtime_diagnostics` to make the boundary explicit: provider
smoke validates text completion only, not `generic_edit`, MCP, subagents, or
`full_autonomous` coding behavior.

For a deeper provider-readiness signal, select a runtime smoke scope:

```bash
python run.py --provider openai --provider-smoke --provider-smoke-runtime generic_edit --json
python run.py --provider openai --provider-smoke --provider-smoke-runtime mini_pipeline --json
python run.py --provider openai --provider-smoke --provider-smoke-runtime provider_e2e --json
```

`generic_edit` validates one local tool loop and reports native tool support,
JSON fallback, normalized tool results, resume policy, and transaction batch
diagnostics. `mini_pipeline` runs a temporary planner/coder/test/reviewer task
and now adds a recovery exercise: it creates a recoverable partial edit, checks
the resume preflight, resumes from the generated checkpoint, and requires the
recovery result to resolve cleanly before reporting `mini_pipeline_ready`.
`provider_e2e` runs the direct-provider e2e suite: the `generic_edit` smoke,
the mini pipeline smoke, and provider-specific negative fixtures for unsupported
tools plus gateway/model limitations are executed for the configured provider,
then merged into one `provider_e2e_suite`, `provider_e2e_negative_fixtures`, and
`provider_reliability` payload.
The JSON diagnostics also include `provider_reliability`: a direct-provider
coverage matrix for the full-autonomy e2e cases. It marks observed cases such
as text completion, generic edit tool loop, native tool calls, tool results, and
recovery loop. In `provider_e2e`, the unsupported-tool and gateway/model cases
are covered by provider adapter/gateway fixtures for OpenAI, Google/Gemini,
OpenRouter, LiteLLM, ZhipuAI, and Ollama; they prove the configured direct
provider surfaces the right fallback reason at the adapter boundary. Live
external fault-injection against real provider accounts remains optional because
it depends on credentials, model availability, and gateway behavior outside the
repository.

Use global non-Claude provider overrides carefully. A full build may still enter
planner, QA, or tool-dependent phases that require `full_autonomous`; those
phases will fail fast with a capability error instead of attempting an unsafe
fallback.

### Runtime-Aware Fallback

Runtime fallback is opt-in:

```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_RUNTIME_FALLBACK=true
OPENAI_API_KEY=sk-...
```

This does not make a direct provider a full autonomous runtime. Auto Code
resolves the provider/runtime capability set and degrades to the first
compatible limited mode, usually `generic_edit`, instead of falling back into an
impossible direct-provider full-autonomous session.

Runtime fallback artifacts also include `runner_candidates`. This is a
capability snapshot for CLI-runner routing: it records runner candidates for the
requested runtime mode, the selected runtime mode, and any compatible degraded
modes. It does not automatically switch a direct provider session to a different
CLI runner; that remains a separate runner-router decision.

The `--runtime-modes` command also exposes a `runtime_fallback_matrix` payload.
It shows the fail-fast selected mode, opt-in fallback selected mode, compatible
degraded modes, and runner candidates for each provider/runtime pair.

The same payload now includes two policy/eval contracts:

- `runtime_policy_matrix` states which runtime each provider may use for
  planner, coder, QA reviewer, and QA fixer phases, whether fallback is allowed,
  and which CLI full-runtime candidates are required when a direct provider
  cannot satisfy a full-autonomous phase.
- `runtime_eval_matrix` lists the smoke/eval cases that must stay green before a
  runtime/provider path can be treated as full autonomous: provider e2e,
  generic-edit recovery, MCP bridge contracts, subagent orchestrator artifacts,
  and CLI full-runtime artifacts.

The Electron provider settings screen consumes the same JSON payload through
the `provider:runtime:diagnostics` IPC channel. Its runtime control plane panel
shows the selected provider/runtime pair's MCP bridge status, required MCP
action, bridged servers, native-required servers, fallback-selected runtime,
runner candidates, and subagent support strategy. Treat this UI as a live view
of the backend compatibility contract rather than a separate frontend-only
matrix.

### CLI Runner Router

CLI runner routing is also opt-in:

```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_CLI_RUNNER_ROUTER=true
CODEX_HOME=/path/to/codex-profile
```

When enabled, Auto Code may route a direct non-Claude `full_autonomous` request
to a wired CLI runner instead of failing fast or degrading to a limited runtime.
The first wired route is `codex_cli`, and it is selected only when the Codex CLI
provider is available. Limited runtime modes such as `generic_edit`,
`patch_proposal`, and `analysis_only` stay on the configured direct provider.
Applied runner routes are persisted as `runtime_runner_route_*.json` artifacts.
Codex CLI runs capture JSONL events and a normalized
`codex_cli_timeline.json` artifact with bounded stdout/stderr budgets; if a CLI
exceeds the capture limit, Auto Code terminates it and records
`output_truncated` in the Codex CLI result artifact.

The shared CLI runner core now also exists independently of Codex CLI. It can
wrap a configured runner command, pass prompts through stdin or configured
prompt args, cancel the active process, parse Codex/OpenAI-style JSONL events,
and persist runner-specific `<runner>_events.jsonl`,
`<runner>_timeline.json`, `<runner>_stdout.txt`, and `<runner>_result.json`
artifacts. `cli_runner_contract_matrix` therefore distinguishes runners with a
configurable generic core (`generic_core_configurable` and
`generic_jsonl_core`) from runners that are fully wired. Runner-specific resume
and command specialization are still tracked separately, so generic core
availability does not yet make every planned CLI a production route.

### Subagent Support Matrix

The `--runtime-modes --json` payload also includes
`runtime_subagent_matrix`. It reports whether each provider/runtime pair has
native subagents, can use Auto Code's orchestrated child-session fallback, or is
blocked for subagent work. Orchestrated subagents currently use isolated child
contexts with a read-only merge policy, bounded attempts, and per-child
artifacts; this is useful for parallel exploration but is not Claude SDK Task
tool parity.

## Full Autonomous Provider Roadmap Status

Keep this table current when advancing direct-provider autonomy. It separates
what is already implemented from what still blocks OpenAI, Gemini, OpenRouter,
LiteLLM, ZhipuAI, and Ollama from being treated as full autonomous coding
providers.

Last updated: 2026-05-17.

| Area | Current status | Done | Remaining |
|------|----------------|------|-----------|
| Runtime foundation | Done | Runtime modes, capability checks, fail-fast behavior, runtime fallback diagnostics, Codex CLI as the first wired non-Claude full autonomous CLI path. | Keep compatibility metadata in sync as new CLI runners become wired. |
| Generic autonomous runtime for API providers | Partial | `generic_edit` supports JSON and native tool-call loops, local file/patch/shell actions, transaction summaries, MCP bridge calls, bounded read-only subagents, native-tool JSON fallback, and provider smoke diagnostics. | Prove direct providers across real models/gateways with e2e tool-call, tool-result, unsupported-tool, and recovery cases before marking any direct API provider full autonomous. |
| Generic Edit v2 core | Partial, strong core | Transaction groups, explicit `begin_batch` / `commit_batch` / `abort_batch`, batch-linked recovery outcomes, per-batch recovery policy, staged mutation metadata, batch boundary guards, pre-execution staged isolation guards for opaque open-batch mutations, pre-commit staged workspace drift guards, staged guard status/drift-path timeline events, mutation snapshots, rollback/repair actions, resumable session state, recovery checkpoints, drift guards, corrupt/missing/incomplete artifact preflight blockers, recovery-plan artifact health checks, artifact manifest transaction batches, manifest/checkpoint consistency checks, manifest recovery-timeline/resume-policy drift guards, trace/session/manifest counter drift checks, unified resume artifact consistency across trace, checkpoint, session state, manifest, mutation snapshots, and transaction batch state, and rich runtime events are implemented. | Harden non-happy-path recovery further for true staged apply storage/isolation and UI-driven repair/rollback workflows. |
| Provider reliability | Strong partial | `--provider-smoke --provider-smoke-runtime generic_edit` validates the live generic-edit tool loop, classifies native tool support, JSON fallback, gateway/model limitations, unsupported tools, recovery status, resume policy, transaction batch contract, boundary guards, and open transaction batches. `--provider-smoke --provider-smoke-runtime mini_pipeline` runs a planner/coder/test/reviewer flow plus a checkpoint preflight/resume recovery loop and reports `recovery_loop_status`. `--provider-smoke --provider-smoke-runtime provider_e2e` now runs the direct-provider e2e suite, adds provider-specific unsupported-tool and gateway/model negative fixtures for OpenAI, Google/Gemini, OpenRouter, LiteLLM, ZhipuAI, and Ollama, merges child results into `provider_e2e_suite`, `provider_e2e_negative_fixtures`, and `provider_reliability`, and persists compact provider run history in `.auto-Codex/provider-smoke-history.json`; the settings UI surfaces suite, fixtures, reliability, and history evidence. | Add optional live fault-injection fixtures for real external accounts/gateways when credentials are available, plus richer provider history trend views from accumulated runs. |
| MCP Bridge v1 | Strong partial | Local MCP bridge status, Context7 external execution, server health, bridge plans, unavailable-tool observations, readiness metadata for Graphiti, Linear, Electron, Puppeteer, and custom stdio/http servers, and `mcp_bridge_permission_matrix` for local/external/custom permission gates are represented. The runtime enforces `RuntimeMcpToolPolicy` before execution, writes audit artifacts, classifies mutating tools, normalizes MCP tool results into `text`, `content`, `structured_content`, and `is_error`, classifies live `tools/list` and bridged `tools/call` lifecycle failures by stage/kind, and exposes whether strict `AUTO_CODE_MCP_ALLOWED_PERMISSIONS` allowlists are configured. | Generalize live execution coverage across all registered external servers, normalize arbitrary live schemas continuously, and keep hardening external session reuse plus per-server execution smoke. |
| Subagent Orchestrator v2 | Partial | Orchestrated read-only child sessions have isolated prompt envelopes, explicit child context ids per attempt, bounded retries, cancellation, per-child artifacts, attempt history, read-only merge plans, and `runtime_subagent_mutation_policy` now exposes the gates blocking mutating children until transactional merge is ready. | Add transactional boundaries for mutating child sessions, conflict-aware merge protocol, parent-approved apply/abort, child artifact viewer polish, then move the mutation policy from blocked to enabled. |
| CLI runtimes as full runtime class | Partial, stronger core | Codex CLI is wired through a full-autonomous route with event/result artifacts and runner routing diagnostics. CLI profile discovery exists for additional runners, `cli_runner_contract_matrix` tracks `run`, `cancel`, `resume`, artifacts, event parser, and cost/account metadata for every candidate, and the generic CLI core now supplies configurable run/cancel/artifact/event parsing for planned runners. | Add runner-specific command builders, resume semantics, and live smoke/e2e coverage for Aider, OpenCode, Goose, Gemini CLI, Qwen Code, and other viable CLIs so they can move from generic-core partial to ready. |
| Frontend runtime control plane | Strong partial | Provider settings show runtime diagnostics, MCP bridge status, MCP permission gates, provider smoke results, tool-loop contract, transaction batch contract, resume policy, transaction batches in Generic Edit artifacts, recovery timeline, open-batch resume state, provider e2e negative fixtures, provider run history, runtime policy/eval rows, consolidated runtime capability readiness/blockers/warnings, runtime eval history, CLI runner contract status, and mutating-subagent gates. | Add cost estimates, trend views, deeper provider controls, and richer artifact viewers into one operator-grade surface. |
| Policy and evals | Strong partial | Runtime recommendations, compatibility diagnostics, `runtime_policy_matrix` for planner/coder/QA phase selection, `runtime_eval_matrix` for provider e2e, generic-edit recovery, MCP bridge contracts, subagent orchestrator artifacts, CLI full-runtime artifacts, `runtime_eval_history` from persisted provider smoke evidence, and `runtime_comparative_eval_matrix` for Claude/Codex/OpenAI/Gemini/Ollama quality/cost/safety comparison are implemented. | Add real cost/quality/safety metrics from live eval runs instead of mostly presence/status evidence, plus richer comparative reporting over time. |

The practical rule remains: a direct API provider is not `full_autonomous` until
it can reliably run the whole tool loop, preserve transactional recovery state,
execute the required MCP/subagent surfaces, and pass the provider reliability
suite without relying on Claude SDK semantics.

## Generic Edit Contract

`generic_edit` mode asks the model to return one JSON object per iteration. Auto
Code executes the requested local actions, sends observations back to the model,
and repeats until the model returns `finish` or the runtime reaches its
iteration limit.

When the provider session exposes native tool calls, `generic_edit` uses those
tool calls by default and falls back to the JSON action loop only when the first
native tool-call request is rejected before any local action runs.

Supported actions:

```json
{
  "thought": "short planning note",
  "actions": [
    { "tool": "stat_path", "path": "src/app.py" },
    { "tool": "list_files", "path": "src", "recursive": false, "max_entries": 100 },
    { "tool": "search_text", "query": "function_name", "path": "src", "recursive": true, "max_matches": 25 },
    { "tool": "read_file", "path": "relative/path.py", "max_chars": 12000 },
    { "tool": "read_file_range", "path": "relative/path.py", "start_line": 40, "max_lines": 120 },
    { "tool": "read_many_files", "paths": ["relative/path.py", "relative/other.py"], "max_chars_per_file": 8000 },
    { "tool": "begin_batch", "batch_id": "batch-1", "description": "Update focused files as one recovery unit." },
    { "tool": "write_file", "path": "relative/path.py", "content": "..." },
    { "tool": "replace_text", "path": "relative/path.py", "old": "old_name", "new": "new_name", "count": 1 },
    { "tool": "delete_file", "path": "relative/path.py" },
    { "tool": "move_file", "source": "relative/path.py", "destination": "relative/new-name.py", "overwrite": false },
    { "tool": "apply_patch", "patch": "unified diff" },
    { "tool": "run_command", "command": "pytest tests/test_file.py -q", "timeout": 60 },
    { "tool": "commit_batch", "batch_id": "batch-1", "summary": "Focused edits applied and ready for verification." },
    { "tool": "abort_batch", "batch_id": "batch-1", "reason": "The staged mutation is no longer needed." },
    { "tool": "rollback_transaction", "transaction_id": "json_actions-1", "snapshot_ids": ["mutation-1"] },
    { "tool": "repair_mutation", "transaction_id": "json_actions-1", "paths": ["relative/path.py"], "note": "Inspected and repaired the partial mutation." },
    { "tool": "git_status", "path": ".", "include_untracked": true },
    { "tool": "git_diff", "path": "relative/path.py", "max_chars": 8000 },
    { "tool": "run_subagents", "tasks": [{ "id": "inspect-api", "role": "explorer", "prompt": "Inspect the API layer and report relevant files." }] },
    { "tool": "finish", "summary": "what changed", "tests": ["commands run"], "risks": [] }
  ]
}
```

The action contract is defined once in
`apps/backend/agents/runtime/local_actions.py` as the local action manifest.
The JSON-loop prompt is rendered from that manifest, and future provider-native
function-calling adapters should use the same schemas instead of duplicating
tool definitions.

OpenAI-compatible sessions expose a native tool-call bridge that can send these
schemas as function tools and append tool results back to provider history.
Direct OpenAI, Ollama, OpenRouter, LiteLLM, and ZhipuAI sessions use that
bridge when the routed model/gateway supports tools; if the first native
tool-call request is rejected, `generic_edit` falls back to the JSON action
loop and records `native_tool_fallbacks` in the result and summary artifacts so
the gateway/model limitation is visible.

The native tool-call parser accepts the common gateway shapes Auto Code sees in
practice: OpenAI Chat Completions `tool_calls`, OpenAI Responses `output`
function-call blocks, Anthropic-style `tool_use` content blocks, Bedrock-style
`toolUse` blocks, Gemini `functionCall` parts, gateway `choices[].message`
envelopes, nested response/message content parts, and streaming `delta`
fragments with chunked JSON arguments.

Z.AI through Claude Code is intentionally not routed through this generic edit
contract. That path uses an Anthropic-compatible endpoint with a Claude
Code-compatible CLI runtime and is represented by the `zai_claude_code` runner
profile.

Auto Code validates and executes these actions locally:

- file paths use the same workspace-relative sensitive-path checks as
  `patch_proposal`;
- path metadata inspection is bounded and never reads file contents;
- file listings are bounded, skip sensitive/heavy directories, and return only
  path metadata;
- text search is literal, bounded, skips sensitive/heavy directories, and
  returns compact path/line excerpts;
- single-file and multi-file reads are bounded and use the same sensitive-path
  checks;
- patches use `git apply --check --whitespace=nowarn` before applying;
- commands pass the existing security allowlist/validator layer;
- commands run without a shell and do not support pipes, redirection, or command
  chaining;
- git status and diff inspection use fixed git subcommands, workspace-relative
  path scoping, and bounded output instead of arbitrary shell commands;
- runtime subagents run as bounded read-only child sessions for analysis,
  exploration, review, or comparison work; they do not receive Claude SDK Task
  tool parity or independent mutating runtime privileges, and each child
  attempt has an isolated context envelope, explicit child context id, bounded
  retry metadata, per-child result artifact, and a timeout/cancellation guard;
- JSON and native tool-call batches stop after the first failed local action, so
  later actions in the same batch do not run against a partially failed
  transaction;
- traces, summaries, safe action timelines, and per-action observations are saved
  as `generic_edit_trace.json`, `generic_edit_result.json`,
  `generic_edit_timeline.json`, `generic_edit_events.jsonl`,
  `generic_edit_observations.jsonl`, `generic_edit_artifact_manifest.json`, and
  `generic_edit_summary.md`;
- transaction summaries include tool sequences, affected/mutated paths,
  partial-failure ids, the last partial-failure path set, whether recovery was
  resolved by a later covered inspection/repair or workspace verification
  transaction, and any unresolved partial failures;
- transaction batches link batch ids to transaction ids, staged mutation ids,
  staged path metadata, mutation snapshots, transaction groups, unresolved
  groups, per-batch recovery policies, boundary errors, and recovery outcomes.
  `commit_batch` is rejected while the batch still has unresolved recovery
  groups, mutating actions after `commit_batch` / `abort_batch` in the same
  provider turn are rejected before any action in that turn mutates the
  workspace, opaque workspace commands such as `run_command` are rejected while
  a batch is open because they cannot produce staged mutation snapshots,
  `commit_batch` validates active staged postimages before closing the batch
  and blocks `staged_batch_drift` / unverifiable staged state, `finish` is
  rejected while a batch is still open, and open-batch state plus
  batch-boundary guard status, boundary reasons, staged drift status, and
  suggested recovery actions are preserved in the recovery checkpoint, artifact
  manifest timeline, provider smoke diagnostics, and the frontend runtime
  diagnostics rows. Provider smoke
  now reports the boundary preferred strategy, required action kinds, and
  resolution strategies from the manifest recovery timeline instead of only
  exposing the raw boundary reason;
- interrupted or partial runs persist `generic_edit_session_state.json`,
  `generic_edit_recovery_checkpoint.json`, `generic_edit_mutation_snapshots.json`,
  and `generic_edit_transaction_groups.json`. The read-only resume preflight
  blocks corrupt checkpoints, corrupt manifests, missing required artifacts,
  mismatched session/checkpoint/manifest policies, stale trace/session/manifest
  counters, missing checkpoint snapshot references, incomplete referenced mutation
  snapshots, trace mismatches, transaction batch drift between trace, checkpoint,
  session state, manifest, and mutation snapshots, corrupt or non-canonical required event streams, recovery-plan
  artifacts, and transaction-group artifacts, transaction-group
  count/unresolved-id drift against the checkpoint, manifest recovery-timeline
  boundary blockers whose required actions are absent from the checkpoint resume
  policy, and workspace drift before a resumed run mutates files;
- `finish` is rejected when a previous partial-failure transaction remains
  unresolved, so limited runtimes cannot report success after a partially
  applied mutating batch.

This mode is intentionally not full autonomous parity. It exposes the local
action loop, provider-native tool calls when available, bounded runtime
subagents when wired by the caller, and Auto Code's local MCP bridge for
built-in tools. It can also execute the known Context7 stdio MCP tools through
the provider-neutral external MCP client when `AUTO_CODE_EXTERNAL_MCP_CLIENT` is
enabled; Graphiti, Linear, Electron, Puppeteer, and custom external MCP servers
remain readiness-only in this layer. It does not expose Claude SDK session
lifecycle behavior. MCP support artifacts include per-server statuses
such as `local_bridge`, `external_bridge_required`, `native_required`, and
`unsupported`, so non-Claude runs can explain exactly which requested MCP
servers are available, which are ready for the provider-neutral external MCP
client, and which remain native-runtime-only. MCP support artifacts also include
a `bridge_plan` with `ready`, `partial`, or `blocked` status, native-required
servers, external-bridge-required servers, local bridged servers, external
bridged servers, unsupported servers, and the next runtime action needed.
External MCP server statuses carry a redacted `external_client` health object
with transport, command/url hints, enablement flags, missing configuration,
whether the server is `ready_to_connect`, whether this layer supports execution,
and the executable tool names when enabled. Context7 uses that health contract
to expose `mcp__context7__resolve-library-id` and
`mcp__context7__get-library-docs`; other external servers still require
tool-execution wiring before parity.
Bridged local MCP tools also carry explicit permission/audit metadata in
`tool_policies`, and each bridged call appends a redacted
`mcp_bridge_audit.jsonl` event with the tool, permission, mutation flag, action,
status, and result summary. If a provider emits an unavailable MCP tool call such as
`mcp__context7__resolve-library-id`, `generic_edit` records a structured
observation with the server name, support strategy, runtime path, and server
status instead of collapsing the failure into a generic unknown-tool error.
OpenAI-compatible tool-call parsing normalizes direct message objects, gateway
`choices[].message` envelopes, streaming `delta` envelopes, and content/part
blocks used by OpenAI, LiteLLM, OpenRouter, Gemini-like, and Anthropic-like
responses.

## Patch Proposal Contract

`patch_proposal` mode asks the model to return one JSON object with this shape:

```json
{
  "summary": "Short description of the proposed change",
  "files": [
    {
      "path": "relative/path.py",
      "operation": "modify",
      "patch": "unified diff for this file"
    }
  ],
  "tests": ["suggested verification command"],
  "risks": ["known limitation or follow-up"]
}
```

Auto Code validates and applies the proposal locally:

- rejects absolute paths and parent traversal;
- rejects sensitive paths such as `.git`, `.env`, `.env.local`,
  `.env.production`, `.mcp.json`, and `.claude`;
- runs `git apply --check --whitespace=nowarn` before applying;
- saves patch artifacts in the spec artifacts directory:
  - `patch_proposal.json` for the raw provider proposal;
  - `patch.diff` for the unified diff;
  - `patch_result.json` for structured status, file, test, and risk metadata;
  - `patch_summary.md` for a human-readable review summary;
- does not automatically run model-suggested test commands.

## Fail-Fast Behavior

Each runtime advertises capabilities such as `tools`, `mcp`, `filesystem_edits`,
`shell_commands`, `structured_output`, and `workspace_access`. Each agent phase
declares what it needs. If a provider/runtime pair cannot satisfy those
requirements, Auto Code reports a capability error before the session runs.

Examples:

- A non-Claude provider in `full_autonomous` mode fails before tool-dependent
  coding starts.
- A non-Claude provider in `analysis_only` mode is allowed only for phases that
  need text completion. During coding, Auto Code saves the text output to
  `artifacts/analysis_only_*.md`, leaves the subtask pending, and stops instead
  of pretending implementation succeeded.
- A non-Claude provider in `patch_proposal` mode can modify files only through
  a validated unified diff.
- A non-Claude provider in `generic_edit` mode can modify files through Auto
  Code's local action loop. Direct OpenAI, Ollama, OpenRouter, and LiteLLM
  sessions use provider-native tool calls when available; other sessions can use
  the JSON action loop. The mode can use the local Auto Code MCP bridge and now
  reports Context7 as an external bridged server with executable tool names when
  the provider-neutral external MCP client is explicitly enabled. Remaining
  external servers report readiness through `external_client` health metadata,
  and `mcp_bridge_permission_matrix` reports bridge permission coverage,
  mutating permissions, audit artifacts, and strict allowlist status for local,
  external, and configured custom MCP servers. MCP tool results are normalized
  into `normalized_result` in observations/audit data so UI and recovery layers
  can inspect text, typed content, structured payloads, and error state without
  reparsing raw provider output. External MCP contract smoke also records
  `failure_stage` and `failure_kind` for live `tools/list` failures so custom
  server lifecycle errors can be diagnosed without parsing free-form messages.
  Parallel read-only work can use
  `run_subagents` when the caller wires a `RuntimeSubagentOrchestrator` session
  factory. Local action batches halt after the first failed action and persist
  transaction/recovery metadata before the next provider iteration. Recovery is
  only marked resolved after a subsequent successful inspection or repair action,
  not by `finish` alone.

## Explicit Boundaries In This PR

This runtime engine is an integration boundary, not a generic replacement for
the Claude Agent SDK. Claude keeps the full native SDK surface. Codex CLI is the
first wired non-Claude full-autonomous CLI runtime. Direct providers use
`analysis_only`, `patch_proposal`, or `generic_edit`; they do not receive
general external MCP tool-execution parity or mutable subagent parity through
the direct chat adapter. The only external MCP execution path in this layer is
the explicitly enabled Context7 stdio bridge.

CLI runner profiles for Claude Code, Z.AI via Claude Code, Gemini CLI, Aider,
Cursor, CodeRabbit CLI, GitHub Copilot CLI, OpenCode, Goose, Amp, Qwen Code,
DeepV Code, and a generic CLI pool are exposed for diagnostics and routing
planning. Planned runners can use the shared generic CLI process/artifact core
when a command is explicitly configured, but runtime routing only applies to
wired runners. Profile visibility and generic-core availability do not imply
that every listed CLI already has production command mapping, resume support, or
provider-specific smoke coverage.

Non-Claude subagents are represented as orchestrated read-only child runtime
sessions, not Claude SDK Task tool parity. Their artifacts include aggregate
child-session summaries, per-child result artifacts, attempt histories, and a
read-only merge plan so status dashboards can show complete/error/cancelled
counts without re-parsing every child result.

## Related Code

- `apps/backend/agents/runtime/` - runtime capabilities, requirements, session
  engine, and adapters.
- `apps/backend/agents/runtime/local_actions.py` - reusable local action
  executor used by generic edit's JSON and provider-native tool-call loops.
- `apps/backend/agents/runtime/mcp_bridge.py` - local MCP bridge status,
  external MCP client readiness, permission policy, and audit artifacts for
  direct-provider runtimes.
- `apps/backend/agents/runtime/cli_profiles.py` - CLI runner profile registry,
  executable detection, and selection diagnostics.
- `apps/backend/agents/runtime/runner_router.py` - opt-in routing from impossible
  direct-provider full-autonomous requests to wired CLI runners.
- `apps/backend/agents/runtime/artifacts.py` - shared analysis-only artifact
  persistence.
- `apps/backend/agents/runtime/compatibility.py` - user-facing provider/runtime
  compatibility metadata.
- `apps/backend/agents/runtime/subagents.py` - provider-neutral subagent
  support policy and child-session orchestrator.
- `apps/backend/agents/coder.py` - runtime selection for planning/coding phases.
- `apps/backend/cli/analysis_commands.py` - non-mutating provider analysis CLI.
- `apps/backend/cli/runtime_commands.py` - runtime compatibility CLI.
- `apps/backend/agents/planner.py` - runtime selection for follow-up planning.
- `apps/backend/core/providers/` - provider adapters and provider factory.
- `apps/backend/cli/provider_smoke_commands.py` - opt-in live provider smoke
  checks.
- `tests/test_agent_runtime.py` - runtime capability and patch proposal tests.
