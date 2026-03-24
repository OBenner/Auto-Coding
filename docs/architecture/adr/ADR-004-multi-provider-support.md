# ADR-004: Multi-Provider AI Engine Support via Provider Abstraction Layer

**Date:** 2024-03-01
**Status:** Accepted
**Deciders:** Auto Code Core Team
**Tags:** ai, architecture, providers, extensibility, vendor-independence

---

## Context

Auto Code initially adopted the Claude Agent SDK as its sole AI backend (see [ADR-001](./ADR-001-claude-agent-sdk.md)). While this was the right decision for the initial implementation — given Claude's superior agentic capabilities and native MCP support — it created a hard dependency on a single AI provider and a single authentication model (Claude OAuth).

Several forces motivated a reassessment:

- **Enterprise adoption barriers**: Many organisations cannot use Claude OAuth. They need support for OpenAI-compatible models, Azure-hosted models, or self-hosted LLMs accessed via API key.
- **Cost flexibility**: Different tasks warrant different cost/capability trade-offs. Routing simple classification tasks to cheaper models while reserving powerful models for complex coding reduces operational cost.
- **Compliance requirements**: Some environments mandate that AI requests remain within a private network (e.g., on-prem Ollama, Azure OpenAI with VNet integration).
- **Community contributions**: Supporting providers like LiteLLM and OpenRouter enables contributors who don't have access to Claude's OAuth flow to run and test the framework.
- **Resilience**: A single-provider dependency creates a single point of failure. Provider-level fallback improves reliability.

The challenge was to support multiple AI backends without fragmenting the codebase into provider-specific agent implementations, and without sacrificing the Claude-specific capabilities (security hooks, MCP servers, extended thinking) that the framework depends on.

## Decision

We will introduce a **Provider Abstraction Layer** in `core/providers/` that defines a unified `AIEngineProvider` interface. All provider-specific logic will be encapsulated in adapter modules. Agent code will interact exclusively with `AIEngineProvider` instances — never directly with provider SDKs.

The layer ships with three first-class adapters:
- **`claude`** — Claude Agent SDK (wraps the existing `create_client()` / `create_simple_client()` infrastructure)
- **`litellm`** — LiteLLM (100+ LLMs via a single unified API)
- **`openrouter`** — OpenRouter (400+ models via an OpenAI-compatible API)

Provider selection is driven by configuration:

```python
# Via environment variable
CLAUDE_PROVIDER=litellm
LITELLM_MODEL=gpt-4o

# Or programmatically
from core.providers import create_engine_provider, ProviderConfig

config = ProviderConfig.from_env()  # reads CLAUDE_PROVIDER and related vars
provider = create_engine_provider(config)
session = provider.create_session(SessionConfig(name="coder", system_prompt="..."))
```

The Claude provider remains the default and the reference implementation. Its adapter preserves all Claude-specific features (MCP servers, security hooks, OAuth) while conforming to the shared interface.

## Rationale

### Key factors

- **Interface stability over implementation flexibility**: Defining a narrow, stable `AIEngineProvider` interface forces us to be explicit about what agents actually need from a provider. This discipline benefits the Claude adapter too — it clarifies which Claude-specific features are load-bearing versus incidental.
- **Adapter pattern fits naturally**: Each provider SDK has a different API surface. The adapter pattern lets us normalise these differences at the boundary, keeping agent code clean.
- **Factory-based instantiation**: `create_engine_provider()` resolves provider type from `ProviderConfig`, making provider selection a configuration concern rather than a code change.
- **Capability detection**: `get_supported_models()` and `validate_config()` allow the framework to fail fast with actionable errors when a provider is misconfigured, rather than surfacing cryptic SDK errors at runtime.
- **Exception normalisation**: A common `ProviderError` hierarchy means agent error-handling code does not need to import or catch provider-specific exceptions.
- **Preserving Claude differentiation**: The Claude adapter is a full-featured implementation that retains security hooks, MCP server integration, and extended thinking. Non-Claude providers gracefully omit these features rather than failing.

### Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| **Provider Abstraction Layer** (chosen) | Vendor independence; consistent interface; feature detection; extensible without modifying agent code | Interface must be kept intentionally narrow — provider-specific features require escape hatches; additional abstraction layer to understand |
| **Keep Claude-only, add env-var model selection** | Minimal complexity; no new abstractions | Does not address enterprise auth requirements; no path to non-Anthropic models; single point of failure remains |
| **LangChain / LiteLLM as the unified layer** | Large existing ecosystem; many integrations already built | Heavy dependencies; abstractions leak provider-specific behaviour; not optimised for the agentic session model Auto Code uses; would require replacing the Claude Agent SDK entirely |
| **Provider-specific agent implementations** | Each agent can be tuned for its provider | Massive code duplication; divergence between implementations becomes inevitable; quadratic maintenance cost |
| **OpenAI Python SDK as common interface** | Widely understood API surface | Loses Claude-specific features permanently; OpenAI SDK is not a neutral abstraction — it reflects OpenAI's design choices |

## Consequences

### Positive

- Agent implementations in `agents/` are provider-agnostic. The same planner, coder, QA reviewer, and QA fixer code executes against Claude, LiteLLM, or OpenRouter.
- Enterprise users can deploy Auto Code without Claude OAuth by configuring a LiteLLM or OpenRouter provider with API key authentication.
- Provider health checks (`health_check()`) and validation (`validate_config()`, `get_validation_errors()`) surface configuration errors at startup rather than mid-session.
- New providers can be added by implementing `AIEngineProvider` in a new adapter module and registering it in the factory — no changes to agent code required.
- The unified `ProviderError` exception hierarchy simplifies error handling and logging across all agent types.
- `ProviderConfig.from_env()` provides a single, documented set of environment variables for provider configuration, replacing ad-hoc `os.environ` reads scattered across the codebase.

### Negative

- The `AIEngineProvider` interface is necessarily a lowest-common-denominator abstraction. Claude-specific capabilities (MCP server configuration, security hooks, extended thinking token budget) are not part of the shared interface and must be accessed through Claude-specific escape hatches or configuration.
- Introducing the abstraction layer adds indirection. Developers debugging a provider issue must trace through `create_engine_provider()` → adapter → SDK rather than going directly to the SDK call.
- Maintaining three adapter implementations means provider SDK updates may require simultaneous changes to multiple adapters. LiteLLM and OpenRouter have faster release cycles than the Claude Agent SDK.
- The `AgentSession` base class is intentionally minimal. Providers that support richer session semantics (e.g., conversation history, token counting) must expose these through provider-specific session subclasses, which agents cannot use without losing provider independence.
- Testing requires either real provider credentials or mocking at the `AIEngineProvider` interface level. The latter is preferred but means integration issues in adapters may not surface in unit tests.

### Neutral

- `core/client.py` (`create_client()`, `create_simple_client()`) is preserved as the Claude-specific entry point. The Claude adapter wraps these functions rather than replacing them, maintaining backwards compatibility.
- `ProviderConfig` is a dataclass loaded from environment variables. The provider-selection variable is `CLAUDE_PROVIDER` (defaulting to `"claude"`). This naming is intentional — it signals that Claude is the primary, supported path.
- The module structure (`core/providers/`, `core/providers/adapters/`) is separate from `core/client.py`. Existing code that imports `core.client` directly continues to work unchanged.

## Implementation notes

The provider layer lives in `apps/backend/core/providers/`:

```
core/providers/
├── __init__.py          # Exports: create_engine_provider, ProviderConfig, exceptions
├── base.py              # AIEngineProvider ABC, AgentSession, SessionConfig
├── config.py            # ProviderConfig dataclass, ProviderType enum
├── factory.py           # create_engine_provider() factory function
├── exceptions.py        # ProviderError, ProviderConfigError, ProviderAuthError, ProviderRateLimitError
└── adapters/
    ├── claude.py        # Wraps core.client / core.simple_client
    ├── litellm.py       # Wraps litellm package
    └── openrouter.py    # Wraps openai package pointed at OpenRouter endpoint
```

**Adding a new provider:**

1. Create `core/providers/adapters/my_provider.py` implementing `AIEngineProvider`.
2. Add `MY_PROVIDER = "my_provider"` to `ProviderType` in `config.py`.
3. Register the adapter in `factory.py`'s `_PROVIDER_REGISTRY`.
4. Document required environment variables in `ProviderConfig.from_env()`.
5. Add integration tests in `tests/test_providers.py`.

**Environment variables (all optional except `CLAUDE_PROVIDER` when not using Claude):**

| Variable | Default | Description |
|---|---|---|
| `CLAUDE_PROVIDER` | `claude` | Active provider: `claude`, `litellm`, `openrouter` |
| `LITELLM_MODEL` | `gpt-4o` | Model identifier passed to LiteLLM |
| `LITELLM_API_KEY` | — | API key for the underlying LLM service |
| `LITELLM_API_BASE` | — | Base URL override (e.g., for Azure or Ollama) |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-4o` | OpenRouter model identifier |

**Escape hatch for Claude-specific features:**

Agents that require Claude-specific capabilities (e.g., the coder agent which relies on MCP servers and security hooks) should check the provider type before using advanced features:

```python
from core.providers import create_engine_provider, ProviderConfig
from core.providers.adapters.claude import ClaudeProvider

config = ProviderConfig.from_env()
provider = create_engine_provider(config)

if isinstance(provider, ClaudeProvider):
    # Use Claude-specific session with MCP servers and security hooks
    session = provider.create_session_with_mcp(agent_type="coder", ...)
else:
    # Fall back to base session without MCP
    session = provider.create_session(SessionConfig(...))
```

## References

- `apps/backend/core/providers/` — Provider abstraction layer implementation
- `apps/backend/core/providers/base.py` — `AIEngineProvider` ABC and `AgentSession`
- `apps/backend/core/providers/factory.py` — `create_engine_provider()` factory
- `apps/backend/core/client.py` — Claude-specific client (wrapped by Claude adapter)
- [ADR-001: Adopt Claude Agent SDK](./ADR-001-claude-agent-sdk.md) — Original Claude SDK decision
- [Provider Abstraction Layer](../provider-abstraction.md) — Architecture overview and full interface documentation
- [ADR index](./README.md) — All architecture decisions

---

*This ADR follows the [Auto Code ADR format](./template.md). See the [ADR index](./README.md) for all decisions.*
