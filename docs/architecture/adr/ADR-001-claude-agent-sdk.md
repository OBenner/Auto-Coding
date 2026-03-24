# ADR-001: Adopt Claude Agent SDK for All AI Interactions

**Date:** 2024-01-15
**Status:** Accepted
**Deciders:** Auto Code Core Team
**Tags:** ai, sdk, architecture, integration

---

## Context

Auto Code is a multi-agent autonomous coding framework that coordinates multiple AI agent sessions to build software. Early in the project's development, a decision was required about how to interface with Anthropic's Claude models.

Two primary approaches were available:
1. **Direct Anthropic API** — Use the `anthropic` Python package to call the API directly with raw HTTP requests and manage sessions, authentication, and tool configuration manually.
2. **Claude Agent SDK** — Use the `claude-agent-sdk` package, which provides a higher-level abstraction over the Anthropic API, purpose-built for agentic use cases.

The framework requires:
- Multi-session agent coordination (planner, coder, QA reviewer, QA fixer)
- Secure sandboxed execution of agent-generated commands
- Dynamic tool and MCP server configuration per agent role
- OAuth-based authentication (not API key)
- Integration with external MCP servers (Context7, Linear, Graphiti, Electron, Puppeteer)
- Security hooks for bash command validation before execution

Managing all of these concerns manually against the raw API would introduce significant complexity and maintenance burden.

## Decision

We will use the **Claude Agent SDK** (`claude-agent-sdk` package) for **all** AI interactions in Auto Code. Direct use of `anthropic.Anthropic()` is explicitly prohibited throughout the codebase.

All agent sessions must be created via `create_client()` from `core.client`, which returns a configured `ClaudeSDKClient` instance.

```python
# ✅ CORRECT
from core.client import create_client

client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model="claude-sonnet-4-5-20250929",
    agent_type="coder",
)
response = client.create_agent_session(
    name="coder-agent-session",
    starting_message="Implement the authentication feature"
)

# ❌ WRONG — never use directly
import anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
```

## Rationale

The Claude Agent SDK was chosen because it directly solves the challenges of agentic AI orchestration without requiring us to reimplement foundational infrastructure.

### Key factors

- **Security hooks** — The SDK supports `HookMatcher`-based pre-execution hooks, enabling `bash_security_hook` to validate every shell command before it runs. Implementing equivalent intercept logic against the raw API would require wrapping every tool call.
- **OAuth authentication** — The SDK natively supports the Claude OAuth flow used by `claude auth login`. This avoids distributing raw API keys and aligns with the project's security model. The raw API requires `ANTHROPIC_API_KEY`, which is not supported.
- **MCP server integration** — The SDK has first-class support for configuring MCP servers per session. Manually proxying MCP protocols over the raw API is not practical.
- **Tool permission scoping** — Agent roles (planner, coder, qa_reviewer, qa_fixer) have different allowed tools. The SDK's `ClaudeAgentOptions` makes this straightforward to configure per session.
- **Agent session management** — The SDK manages the full agent loop (tool calls, results, follow-up messages) automatically. This eliminates hundreds of lines of orchestration boilerplate.
- **Caching and performance** — `core/client.py` implements a thread-safe project index cache (`_PROJECT_INDEX_CACHE`) with a 5-minute TTL, reducing repeated filesystem reads when creating many agent sessions.

### Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| **Claude Agent SDK** (chosen) | Purpose-built for agents; OAuth support; MCP integration; security hooks; session management built-in | Additional dependency; SDK updates may introduce breaking changes |
| **Anthropic API directly** | Full control; minimal dependency | Must manually implement: tool call loops, security intercepts, MCP proxying, OAuth flow, session recovery; high maintenance burden |
| **LangChain / LlamaIndex** | Large ecosystem; many integrations | Not optimised for Claude; abstractions often leak; adds heavy dependency; no native Claude OAuth support |
| **OpenAI-compatible endpoint** | Familiar API surface | Loses Claude-specific features (extended thinking, computer use, native MCP); not the right abstraction level |

## Consequences

### Positive

- Security is enforced at the SDK level — `bash_security_hook` intercepts all shell commands before execution, providing a consistent defence layer across all agent types.
- OAuth authentication means no plaintext API keys need to be stored or rotated.
- MCP servers (Context7, Linear, Graphiti, Electron, Puppeteer) are configured declaratively per agent role via `get_required_mcp_servers()`.
- Agent session recovery and retry logic is handled by the SDK, reducing failure modes.
- New agent types can be added by defining a configuration in `AGENT_CONFIGS` (single source of truth) without changing session management code.
- The `ClaudeAgentOptions` abstraction makes it straightforward to vary model, thinking tokens, and tool permissions per agent.

### Negative

- The project is tightly coupled to the Claude Agent SDK's API surface. Breaking changes in the SDK require updates to `core/client.py` and potentially all agent implementations.
- Developers cannot use the Anthropic API directly even for simple one-off queries; they must use `create_simple_client()` from `core.simple_client` or the full `create_client()`.
- Debugging agent behaviour requires understanding both the SDK's internal loop and the project's security hooks.
- The SDK is not publicly available as an open-source package in the standard PyPI ecosystem, which may complicate onboarding new contributors.

### Neutral

- All new AI feature work must go through `core/client.py`. This is enforced by convention and documented in `CLAUDE.md`.
- The `create_client()` factory accepts an `agent_type` parameter that maps to `AGENT_CONFIGS` in `agents/tools_pkg/models.py`. Adding new agent types requires updating that registry.
- Windows environments require special handling due to the 32,768-character command-line limit (`WINDOWS_MAX_SYSTEM_PROMPT_CHARS = 20000`), which is managed transparently by `create_client()`.

## Implementation notes

The client factory lives in `apps/backend/core/client.py`. Key entry points:

- **`create_client()`** — Full client for agent sessions with security hooks, MCP servers, and tool permissions. Use this for planner, coder, QA reviewer, and QA fixer agents.
- **`create_simple_client()`** (`core.simple_client`) — Lightweight client for single-turn message calls that don't require the full agent loop. Use for spec agents and simple prompts.

The security hook is registered via `ClaudeAgentOptions`:

```python
options = ClaudeAgentOptions(
    ...
    hooks=[HookMatcher(event="pre_tool_use", tool="bash", callback=bash_security_hook)],
)
```

MCP server selection is dynamic based on project capabilities detected by `detect_project_capabilities()`. This means a project without Electron will not spin up the Electron MCP server, keeping agent sessions lean.

Authentication is handled via `require_auth_token()` and `get_sdk_env_vars()` from `core.auth`. The OAuth token is read from the system keychain and passed to the SDK via environment variables — never hardcoded.

## References

- `apps/backend/core/client.py` — Client factory implementation
- `apps/backend/core/auth.py` — OAuth token management
- `apps/backend/core/security.py` — Command allowlist and bash security hook
- `apps/backend/agents/tools_pkg/models.py` — `AGENT_CONFIGS` registry
- `apps/backend/agents/planner.py` — Example agent using `create_client()`
- [CLAUDE.md](../../../CLAUDE.md) — Project-level guidance prohibiting direct API use

---

*This ADR follows the [Auto Code ADR format](./template.md). See the [ADR index](./README.md) for all decisions.*
