# ADR-005: Multi-Runtime Agent Engine

**Date:** 2026-04-29
**Status:** Proposed
**Deciders:** Auto Code Core Team
**Tags:** ai, architecture, runtimes, providers, tools, security

---

## Context

[ADR-004](./ADR-004-multi-provider-support.md) introduced a provider abstraction
layer so Auto Code could use Claude, LiteLLM, OpenRouter, OpenAI, Google,
ZhipuAI, and Ollama through a common `AIEngineProvider` interface. That decision
is still useful, but implementation work has exposed a deeper distinction:

- A **provider** supplies model access.
- A **runtime** supplies an agent loop, tool execution, filesystem behavior,
  shell execution, MCP integration, structured output, permission handling,
  session persistence, and event streaming.

Full autonomous coding depends on runtime capabilities, not just model
completion. The current main agent path still depends on the Claude Agent SDK
shape in several places. For example:

- `agents/session.py` runs a Claude-specific `query()` / `receive_response()`
  loop.
- `agents/coder.py` expects provider sessions to expose `session.client`.
- Planner, QA, GitHub, and analysis flows still consume Claude SDK message
  shapes directly in multiple paths.

This creates an unsafe middle ground: non-Claude providers can be configured,
but the autonomous coding path may still require Claude-only runtime features
such as tool execution, MCP servers, security hooks, filesystem edits, shell
commands, and subagents.

External architecture review also supports this distinction:

- Claude Agent SDK is a managed agent runtime with built-in file, shell, tool,
  MCP, permission, session, and subagent behavior.
- OpenAI has two relevant layers: the official OpenAI API SDKs for direct model
  access, and the OpenAI Agents SDK for agent loops, tools, handoffs,
  guardrails, tracing, MCP, sandbox agents, shell, and patch application.
- Google has the same split: Google GenAI SDK is the official Gemini model API
  client, while Google ADK is an agent development framework with tools,
  sessions, memory, artifacts, events, MCP, runtimes, and deployment surfaces.
- LiteLLM, OpenRouter, Ollama, direct OpenAI-compatible APIs, and Google GenAI
  are valuable model access layers, but they do not automatically provide a safe
  coding runtime.
- Vercel AI SDK, LangChain/LangGraph, and LlamaIndex provide useful cross-model
  abstractions, but none should become Auto Code's only portability layer for
  autonomous coding. Auto Code still needs its own security, workspace, event,
  and phase-capability contract.
- Aider-like systems show that patch proposal and edit-format workflows are a
  practical way to use many models without giving them direct tool execution.

We also reviewed an unofficial public mirror of Claude Code source to identify
architecture patterns, not to copy implementation. Useful patterns include a
session-owned query engine, rich tool metadata, fail-closed tool defaults,
capability-aware permission checks, concurrency-safe tool batching, large tool
result persistence, normalized system init events, and explicit recovery and
compaction transitions.

## Decision

We will evolve Auto Code from a **provider abstraction** to a
**multi-runtime agent engine**.

The existing provider abstraction remains useful for model access, but
autonomous agent execution will be routed through a new runtime layer:

```text
AgentSessionEngine
├── RuntimeAdapter
│   ├── ClaudeAgentRuntime
│   ├── CompletionRuntime
│   ├── PatchProposalRuntime
│   ├── OpenAIAgentsRuntime
│   ├── GoogleADKRuntime
│   └── ExternalAgentRuntime
├── RuntimeCapabilities
├── RuntimeRequirements
├── ToolRegistry / ToolSpec
├── PermissionGate
├── ToolExecutor
├── ConversationStore
├── EventNormalizer
└── ResultExtractor
```

Agent phases will declare required capabilities. Runtime adapters will declare
available capabilities. The engine will decide whether to run, downgrade to a
limited mode, or fail fast with an actionable error.

Claude Agent SDK remains the default and current full autonomous coding runtime.
Other SDKs and providers are supported according to their runtime capabilities:

- Text-only planning, analysis, review, and extraction can use completion
  runtimes backed by model SDKs or gateways.
- Non-Claude coding can use patch proposal mode when direct tool execution is
  unavailable.
- OpenAI Agents SDK and Google ADK are not treated as generic completion
  providers. They are separate runtime adapters because each has its own agent
  loop, tool model, event model, and execution/deployment assumptions.
- Full non-Claude autonomous coding requires a runtime with controlled
  filesystem edits, shell execution, tool execution, permissions, MCP handling,
  and normalized event streaming.

## Rationale

### Key factors

- **Provider is not runtime**: A model API can produce text, but autonomous
  coding needs controlled actions in a workspace.
- **Capability gates are safer than provider checks**: The system should ask
  "can this runtime edit files and run shell safely?" rather than "is this
  provider Claude?"
- **Claude remains the full path today**: The Claude Agent SDK already provides
  the managed tool loop and filesystem behavior Auto Code depends on.
- **OpenAI Agents SDK deserves a separate runtime adapter**: It should not be
  treated as a generic OpenAI-compatible completion API because it has its own
  agent loop, tool, guardrail, MCP, sandbox, and patch surfaces.
- **Google ADK deserves the same treatment**: Google GenAI SDK is a Gemini model
  client; Google ADK is a runtime framework. The latter belongs beside
  `OpenAIAgentsRuntime`, not inside `CompletionRuntime`.
- **There is no universal coding SDK to adopt wholesale**: LiteLLM,
  OpenRouter, Vercel AI SDK, LangChain, LangGraph, LlamaIndex, OpenAI Agents
  SDK, and Google ADK each solve different slices. Auto Code's portability
  boundary should be its own `AgentRuntime` contract.
- **Patch proposal mode creates an honest bridge**: Models without safe tool
  execution can still propose structured edits that Auto Code validates,
  applies, tests, and reports on.
- **Security must live above provider adapters**: MCP, shell, filesystem edits,
  hooks, and project-controlled configuration all cross trust boundaries. They
  need shared policy enforcement independent of model provider.
- **Event normalization reduces lock-in**: Agent code should consume normalized
  events, not Claude SDK message classes.

### Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Keep ADR-004 as-is | Minimal design churn; existing provider adapters remain | Conflates model access with runtime capabilities; non-Claude autonomous paths stay fragile |
| Add more provider-specific checks | Small local changes; can patch `session.client` failures | Spreads provider conditionals through agents; does not solve tools, MCP, shell, or event normalization |
| Replace Claude SDK with a generic agent framework | Single runtime abstraction from day one | High migration cost; risks losing Claude-specific capabilities that already work |
| Use LiteLLM or OpenRouter as the universal layer | Broad model coverage; useful routing and cost controls | These are model gateways, not workspace runtimes; tool execution remains Auto Code's responsibility |
| Adopt OpenAI Agents SDK or Google ADK as the universal runtime | Strong agent frameworks with tools, memory, and runtime concepts | Vendor/framework-specific event models and execution assumptions; does not cover all providers or preserve the existing Claude-first path cleanly |
| Adopt LangChain/LangGraph as the universal runtime | Broad provider support, durable execution, established agent patterns | Adds a large framework dependency while Auto Code still needs custom workspace security, permissioning, and coding-specific UX |
| Introduce a multi-runtime engine (chosen) | Capability-based execution; supports full and limited modes honestly; keeps Claude path stable | Requires new contracts, migration work, and careful tests |

## Consequences

### Positive

- Auto Code can support multiple models without pretending all models can do
  autonomous coding.
- Full autonomous coding remains reliable on Claude Agent SDK while other
  providers become useful for planning, analysis, review, extraction, and patch
  proposal workflows.
- Agents can fail fast with clear capability errors instead of late
  `AttributeError` or SDK-specific failures.
- Tool execution, permissions, logging, conversation history, result
  extraction, and usage accounting move into shared code.
- Future runtimes such as OpenAI Agents SDK, Google ADK, Gemini CLI, Codex CLI,
  or Aider can be added as runtime adapters instead of being forced into the
  completion provider interface.

### Negative

- The runtime layer adds a new abstraction alongside the existing provider
  abstraction.
- Migrating existing agent paths requires touching several modules that still
  consume Claude SDK clients or message types directly.
- Patch proposal mode requires strict validation, robust patch application, and
  careful UX so users understand it is a limited mode.
- The engine must preserve the working Claude path while introducing new
  contracts, which increases test coverage requirements.

### Neutral

- `core/providers/` remains the model provider layer.
- `core/client.py` remains the Claude-specific client factory used by the
  Claude runtime adapter.
- Existing environment configuration can remain in place, but runtime selection
  and capability validation will become explicit.
- ADR-004 is not invalidated. This ADR refines it by separating provider access
  from runtime execution.

## Implementation notes

### Runtime capabilities

Add a runtime capability contract:

```python
@dataclass(frozen=True)
class RuntimeCapabilities:
    text_completion: bool
    streaming_text: bool
    structured_output: bool
    native_tool_loop: bool
    function_tools: bool
    mcp: bool
    filesystem_read: bool
    filesystem_edit: bool
    shell: bool
    apply_patch: bool
    subagents: bool
    sandbox: bool
```

Add runtime requirements per agent phase:

| Phase or mode | Required capabilities |
|---------------|-----------------------|
| Planner | `text_completion`, `structured_output` |
| Spec writer | `text_completion`, `structured_output` |
| Text QA | `text_completion` |
| Full coder | `filesystem_edit`, `shell`, `native_tool_loop` |
| Patch coder | `text_completion`, structured patch output |
| E2E QA | `shell` plus MCP or browser/Electron tools |
| GitHub review | Connector tools or a runtime-specific GitHub capability |

### Agent session engine

Create a runtime-owned session function:

```python
async def run_runtime_session(
    session: RuntimeSession,
    message: str,
    spec_dir: Path,
    requirements: RuntimeRequirements,
    ...
) -> AgentRunResult:
    ...
```

This replaces direct calls to `run_agent_session(client, ...)` in new code. The
existing Claude-specific function can remain as a compatibility wrapper during
migration.

The engine owns:

- plugin hooks around session lifecycle;
- conversation history and resume context;
- task logging;
- decision extraction;
- usage accounting;
- normalized event handling;
- result status extraction;
- max turn, max budget, and retry status handling.

### Normalized event stream

Define provider-neutral events:

```text
SessionStarted
TextDelta
AssistantMessage
ToolCallStarted
ToolCallProgress
ToolCallFinished
FileEdited
CommandStarted
CommandFinished
PermissionDenied
UsageUpdated
CompactBoundary
Error
FinalResult
```

Claude runtime maps Claude SDK messages into these events. Completion runtimes
emit only text, usage, and result events. Patch proposal runtime emits proposal,
validation, apply, and test events.

### Runtime adapters

Initial runtime adapters:

| Runtime | Purpose | Initial capability level |
|---------|---------|--------------------------|
| `ClaudeAgentRuntime` | Wrap Claude Agent SDK | Full autonomous coding |
| `CompletionRuntime` | Wrap model SDKs and gateways such as OpenAI SDK, Google GenAI SDK, LiteLLM, OpenRouter, and Ollama | Text and structured output |
| `PatchProposalRuntime` | Use completion models to propose validated patches | Limited coding without direct tools |
| `OpenAIAgentsRuntime` | Wrap OpenAI Agents SDK agent loop, tools, MCP, sandbox, shell, and patch surfaces | Planned full or near-full runtime adapter |
| `GoogleADKRuntime` | Wrap Google ADK agents, tools, sessions, artifacts, events, MCP, and runtime/deployment surfaces | Planned full or near-full runtime adapter |
| `ExternalAgentRuntime` | Wrap tools such as Gemini CLI, Codex CLI, or Aider | Planned external process adapter |

The adapter boundaries should follow SDK responsibility:

- **Model SDK adapters** belong under `CompletionRuntime`: OpenAI SDK,
  Google GenAI SDK, OpenAI-compatible API clients, LiteLLM, OpenRouter, Ollama,
  and similar gateways.
- **Agent SDK adapters** get their own runtime adapter: Claude Agent SDK,
  OpenAI Agents SDK, Google ADK, and any future SDK that owns an agent loop,
  tool execution, state, or sandbox semantics.
- **External coding tools** get process adapters only when Auto Code can
  supervise their workspace, permissions, logs, and exit behavior.

### Coder modes

Replace the current `session.client` dependency in `agents/coder.py` with
runtime sessions:

```text
full_autonomous:
  requires filesystem_edit + shell + native_tool_loop

patch_proposal:
  requires text_completion + structured patch output
  model returns PatchProposal
  Auto Code validates and applies the patch

analysis_only:
  allows no writes and no shell execution
```

Non-Claude runtimes that do not provide full workspace capabilities should fail
fast in full autonomous mode and suggest patch proposal mode.

### Patch proposal mode

Patch proposal mode uses structured model output:

```json
{
  "summary": "Describe the intended change",
  "files": [
    {
      "path": "apps/backend/example.py",
      "operation": "modify",
      "patch": "unified diff or search-replace blocks"
    }
  ],
  "tests": ["apps/backend/.venv/bin/pytest tests/test_example.py -v"],
  "risks": ["Potential behavioral risk"]
}
```

Auto Code then:

1. validates paths are inside the workspace;
1. rejects unsafe or unsupported operations;
1. validates patch structure;
1. applies the patch locally;
1. runs permitted verification commands;
1. reports results back to the user and, when useful, back to the model.

### ToolSpec and ToolRegistry

Introduce provider-neutral tool metadata:

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    input_schema: dict[str, Any]
    read_only: bool
    destructive: bool
    concurrency_safe: bool
    requires_permission: bool
    requires_mcp: bool
    max_result_size_chars: int
    exposure: Literal["native", "function", "runtime_only", "disabled"]
```

Tool defaults should fail closed:

- tools are not concurrency-safe unless explicitly marked;
- tools are not read-only unless explicitly marked;
- destructive behavior must be explicitly declared;
- deny rules filter tools before the model sees them;
- large tool results are persisted as artifacts with model-visible previews;
- empty tool results are replaced with a short completion marker.

### PermissionGate

Add a shared permission pipeline:

```text
1. Deny rules
2. Ask rules
3. Tool-specific validation
4. Safety checks
5. Mode policy
6. Runtime capability check
7. Allow, deny, or ask decision
```

Safety checks are bypass-immune. They apply even when an agent is in an
auto-approval mode. Sensitive targets include:

- `.git/`;
- `.claude/`;
- `.mcp.json`;
- project settings;
- shell configuration files;
- credentials;
- files outside the workspace;
- destructive git operations;
- local MCP stdio commands.

### Tool execution

Move tool execution into a shared `ToolExecutor`.

Execution rules:

- read-only and concurrency-safe tools may run in bounded parallel batches;
- write, shell, git, and destructive tools run serially unless explicitly safe;
- shell failures can cancel related sibling shell commands;
- user interruption uses each tool's declared interrupt behavior;
- tool progress is emitted as normalized events;
- context modifiers are applied only in safe order.

### Fail-fast UX

Capability errors should name both required and available capabilities:

```text
Cannot run coder in full autonomous mode with provider=openrouter.

Required capabilities:
- filesystem_edit
- shell
- native_tool_loop

Available capabilities:
- text_completion
- structured_output

Use Claude Agent SDK for full autonomous coding, or run this task in
patch proposal mode with the configured provider.
```

### Migration sequence

Create new runtime modules:

```text
apps/backend/agents/runtime/
├── capabilities.py
├── requirements.py
├── events.py
├── result.py
├── session_engine.py
└── adapters/
    ├── claude.py
    ├── completion.py
    └── patch_proposal.py
```

Migrate in vertical slices:

1. Add `RuntimeCapabilities`, `RuntimeRequirements`, normalized events, and
   `AgentRunResult`.
1. Wrap the existing Claude path in `ClaudeAgentRuntime`.
1. Implement `run_runtime_session()` and keep `run_agent_session()` as a
   compatibility wrapper.
1. Migrate `agents/coder.py` away from `session.client`.
1. Add fail-fast capability checks for full coder mode.
1. Add patch proposal mode for non-Claude completion runtimes.
1. Migrate planner and spec flows to text-capable runtimes.
1. Split QA into text QA and E2E/tool-dependent QA requirements.
1. Migrate GitHub and analysis runners where they only need text or structured
   output.
1. Add OpenAI Agents SDK runtime as a separate adapter when local tool harnesses
   and sandbox/permission mapping are ready.
1. Add Google ADK runtime as a separate adapter after the same capability and
   permission mapping is understood.
1. Evaluate optional LangChain/LangGraph or Vercel AI SDK integration only as a
   bridge for specific use cases, not as the core Auto Code runtime contract.

### Test plan

Add tests for:

- capability matching and failure messages;
- Claude runtime event normalization;
- completion runtime text and structured output;
- model SDK adapters staying text-only unless explicitly upgraded;
- patch proposal validation and application;
- workspace path restrictions;
- deny rules removing tools before exposure;
- safety checks overriding bypass modes;
- tool batching for concurrency-safe and serial tools;
- large tool result persistence;
- coder full mode requiring workspace capabilities;
- coder patch mode succeeding without direct tool execution;
- OpenAI Agents SDK and Google ADK adapters refusing full coding until their
  shell, filesystem, MCP, sandbox, and permission capabilities are mapped.

## Documentation updates

Update provider documentation to say:

```text
Claude Agent SDK is required for full autonomous coding today.

Other providers are supported for planning, analysis, spec generation, review
summaries, structured extraction, and patch proposal mode.

OpenAI Agents SDK and Google ADK should be documented as agent runtimes, not as
generic model providers.

Full support for additional coding runtimes requires controlled filesystem
edits, shell execution, permissioning, MCP/tool loop support, and event
streaming.
```

Add SDK taxonomy:

| Layer | Examples | Auto Code role |
|-------|----------|----------------|
| Model SDK | OpenAI SDK, Google GenAI SDK, Anthropic API SDK | Back `CompletionRuntime`; no direct workspace actions |
| Model gateway | LiteLLM, OpenRouter, Ollama OpenAI-compatible API | Back `CompletionRuntime`; routing, cost, local models, structured output where supported |
| Agent SDK/runtime | Claude Agent SDK, OpenAI Agents SDK, Google ADK | Dedicated runtime adapters with capability mapping |
| Cross-provider app framework | Vercel AI SDK, LangChain/LangGraph, LlamaIndex | Optional integration layer for specific use cases, not the core Auto Code runtime contract |
| Protocol | MCP | Tool/data/workflow connectivity that still requires Auto Code permission and security gates |
| External coding tool | Gemini CLI, Codex CLI, Aider | External process adapter when supervisable |

Add a runtime matrix:

| Runtime | Full coding | Patch mode | Planning | MCP | Shell |
|---------|-------------|------------|----------|-----|-------|
| Claude Agent SDK | Yes | Yes | Yes | Yes | Yes |
| OpenAI SDK / OpenAI-compatible API | No | Yes | Yes | No | No |
| Google GenAI SDK | No | Yes | Yes | No | No |
| LiteLLM | No | Yes | Yes | No | No |
| OpenRouter | No | Yes | Yes | Partial | No |
| Ollama | No | Yes | Yes | No | No |
| OpenAI Agents SDK | Planned | Yes | Yes | Yes | Planned |
| Google ADK | Planned | Yes | Yes | Yes | Planned |
| Gemini CLI | Possible external runtime | Possible | Possible | Possible | Possible |
| Aider | Possible patch/edit runtime | Yes | Limited | No | Limited |

## References

- [ADR-001: Claude Agent SDK Adoption](./ADR-001-claude-agent-sdk.md)
- [ADR-004: Multi-Provider AI Engine Support](./ADR-004-multi-provider-support.md)
- [Provider Abstraction Layer](../provider-abstraction.md)
- `apps/backend/core/providers/base.py`
- `apps/backend/agents/session.py`
- `apps/backend/agents/coder.py`
- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [OpenAI API libraries](https://developers.openai.com/api/docs/libraries)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [OpenAI Agents SDK runtime update](https://openai.com/index/the-next-evolution-of-the-agents-sdk/)
- [OpenAI Agents SDK tools](https://openai.github.io/openai-agents-python/tools/)
- [OpenAI Agents SDK sandbox agents](https://openai.github.io/openai-agents-python/sandbox/guide/)
- [Google GenAI SDK libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Google ADK](https://adk.dev/)
- [Google ADK on Gemini Enterprise Agent Platform](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk)
- [Gemini CLI](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
- [Vercel AI SDK](https://ai-sdk.dev/docs/introduction)
- [LangChain models and agents](https://docs.langchain.com/oss/python/langchain/models)
- [LiteLLM documentation](https://docs.litellm.ai/)
- [OpenRouter structured outputs](https://openrouter.ai/docs/features/structured-outputs)
- [Aider edit formats](https://aider.chat/docs/more/edit-formats.html)
- [Model Context Protocol intro](https://modelcontextprotocol.io/docs/getting-started/intro)
- [MCP security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)

---

*This ADR follows the [Auto Code ADR format](./template.md). See the [ADR index](./README.md) for all decisions.*
