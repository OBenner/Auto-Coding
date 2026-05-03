# Environment Variable Configuration

This document describes the environment variable schema for configuring AI engine providers and runtime modes in Auto Code.

## Overview

Auto Code supports multiple AI engine providers through a unified configuration interface. Providers are selected and configured through environment variables.

Provider selection does not guarantee full autonomous coding capability. Claude
remains the default full autonomous runtime, and Codex CLI is the first wired
non-Claude full autonomous CLI runtime. Direct API providers such as OpenAI,
Google, LiteLLM, OpenRouter, ZhipuAI, and Ollama run through limited modes such
as `analysis_only`, `patch_proposal`, and `generic_edit`. See
[Provider Runtime Modes](../architecture/provider-runtime-modes.md).

## Core Configuration Variables

### `AI_ENGINE_PROVIDER`

**Description**: Selects the active AI engine provider.

**Valid Values**:
- `claude` (default) - Claude Agent SDK with full agentic capabilities
- `openai` - OpenAI direct API
- `google` - Google Gemini API
- `litellm` - LiteLLM unified API supporting multiple providers
- `openrouter` - OpenRouter cloud routing with 400+ models
- `zhipuai` - Zhipu AI GLM models
- `ollama` - Local Ollama models through an OpenAI-compatible API

**Example**:
```bash
export AI_ENGINE_PROVIDER=claude
```

**Behavior**:
- If not set, defaults to `claude`
- Invalid values fall back to `claude` with a warning
- Provider-specific credentials must be configured (see below)

**Runtime Override**:
```bash
# Override for a limited analysis command
AI_ENGINE_PROVIDER=openai python run.py --spec 001 --analyze

# Or use command-line flag
python run.py --spec 001 --provider openai --runtime-mode generic_edit
```

---

### `AUTO_CODE_RUNTIME_MODE`

**Description**: Selects the runtime behavior for provider sessions.

**Valid Values**:
- `full_autonomous` (default) - requires Claude Agent SDK-style tools, MCP, shell, filesystem edits, and workspace access
- `generic_edit` - uses Auto Code's local action loop for provider-neutral edits and validated commands
- `patch_proposal` - lets a text provider propose a unified diff that Auto Code validates and applies
- `analysis_only` - allows text-only provider responses without tools or edits

**Example**:
```bash
export AUTO_CODE_RUNTIME_MODE=full_autonomous
```

**Per-Agent Override for Limited Providers**:
```bash
export AGENT_RUNTIME_MODE_CODER=patch_proposal
```

Prefer per-agent overrides when mixing Claude with limited providers so planner
and QA phases keep the full autonomous runtime:

```bash
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=patch_proposal
OPENAI_API_KEY=sk-...
```

If a phase requires capabilities the selected runtime does not provide, Auto Code fails fast with a capability error.

### `AUTO_CODE_RUNTIME_FALLBACK`

**Description**: Enables degraded runtime fallback for incompatible provider/runtime pairs.

**Default**: `false`

When enabled, Auto Code does not fallback from Claude full autonomous coding to a
non-Claude full autonomous runtime. Instead, it resolves the provider's capability
set and degrades to the first compatible limited runtime (`generic_edit`, then
`patch_proposal`, then `analysis_only`).

**Example**:
```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_RUNTIME_FALLBACK=true
OPENAI_API_KEY=sk-...
```

This runs the selected OpenAI provider through `generic_edit` rather than
pretending it supports Claude Agent SDK external MCP tools or native Task
subagents.

### `AUTO_CODE_CLI_RUNNER_ROUTER`

**Description**: Enables opt-in routing from an incompatible direct
`full_autonomous` provider request to a wired CLI-backed runtime.

**Default**: `false`

When enabled, Auto Code can route a non-Claude direct `full_autonomous` request
to the Codex CLI runtime if the Codex provider is available. This is separate
from runtime fallback: runner routing preserves `full_autonomous` by switching
to a capable CLI runner, while runtime fallback degrades to limited modes such
as `generic_edit`.

**Example**:
```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_CLI_RUNNER_ROUTER=true
CODEX_HOME=/path/to/codex-profile
OPENAI_API_KEY=sk-...
```

Limited runtime modes remain on the configured direct provider.

---

## Provider-Specific Configuration

### Claude Agent SDK (`claude`)

The default provider with full MCP integration, native security, and agent orchestration.

#### Required Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude access | `sk-ant-...` | Yes |

#### Optional Variables

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `CLAUDE_MODEL` | Model identifier | `claude-sonnet-4-5-20250929` | `claude-sonnet-4-5-20250929` |

#### Supported Models

- `claude-sonnet-4-5-20250929` - Best for complex reasoning and code generation
- `claude-haiku-4-20250929` - Fast and cost-effective for simple tasks
- `claude-opus-4-20250929` - Highest quality for critical tasks

#### Configuration Example

```bash
# .env file
AI_ENGINE_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

#### Features

✅ Native MCP (Model Context Protocol) support
✅ Built-in security (sandbox, file permissions, command hooks)
✅ Agent lifecycle management
✅ Extended thinking
✅ Session management

---

### OpenAI API (`openai`)

OpenAI integration for text completion, analysis-only phases, patch proposal
mode, and the experimental generic edit local action runtime. It does not
provide full autonomous coding parity with the Claude Agent SDK.

#### Required Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` | Yes |

#### Optional Variables

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `OPENAI_MODEL` | Model identifier | `gpt-4o` | `gpt-4o` |
| `OPENAI_BASE_URL` | Custom API base URL | `https://api.openai.com/v1` | `https://api.openai.com/v1` |

#### Configuration Example

```bash
# .env file
AI_ENGINE_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o
```

#### Features

- Streaming/text completion
- Analysis-only runtime mode
- Patch proposal runtime mode
- Generic edit runtime mode with local action tools
- Local Auto Code MCP bridge for built-in tools
- Orchestrated child runtime sessions when `RuntimeSubagentOrchestrator` is
  explicitly configured

#### Limitations

- **No full Auto Code tool runtime**: External MCP servers and native Claude
  SDK Task subagents are not exposed to non-Claude providers.
- **Local action boundary**: Generic edit mode exposes only workspace-relative file actions and security-validated single commands through Auto Code.
- **No Claude-style session lifecycle**: The runtime layer treats this as a completion provider.

---

### LiteLLM (`litellm`)

Unified API supporting 100+ LLM providers through a single interface.

#### Required Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `LITELLM_MODEL` | Model identifier (provider:model format) | `gpt-4` or `claude-3-opus` | Yes |

#### Optional Variables

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `LITELLM_API_BASE` | Custom API base URL | `https://api.example.com` | (provider default) |
| `LITELLM_API_KEY` | API key for model provider | `sk-...` | (varies by model) |

#### Configuration Example

```bash
# .env file
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=gpt-4
LITELLM_API_KEY=your-openai-key
```

#### Model Format

LiteLLM uses `provider:model` format:
- `openai/gpt-4`
- `anthropic/claude-3-opus`
- `cohere/command-r`
- `palm/bison`

#### Features

⚠️ No MCP support
⚠️ No agent orchestration
✅ Unified API for multiple providers
⚠️ Requires manual security implementation

---

### OpenRouter (`openrouter`)

Cloud routing service providing access to 400+ models with pay-per-use pricing.

#### Required Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-...` | Yes |

#### Optional Variables

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `OPENROUTER_MODEL` | Model identifier | `anthropic/claude-sonnet-4` | `anthropic/claude-sonnet-4` |
| `OPENROUTER_BASE_URL` | API base URL | `https://openrouter.ai/api/v1` | `https://openrouter.ai/api/v1` |

#### Configuration Example

```bash
# .env file
AI_ENGINE_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-your-key-here
OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

#### Features

⚠️ No MCP support
⚠️ No agent orchestration
✅ Access to 400+ models
⚠️ Requires manual security implementation

---

## Model Selection Strategy

### Per-Agent Model Configuration

Different agents may use different models based on task requirements:

```bash
# Default models for each agent type
AGENT_MODEL_PLANNER=claude-sonnet-4-5-20250929
AGENT_MODEL_CODER=claude-sonnet-4-5-20250929
AGENT_MODEL_QA_REVIEWER=claude-sonnet-4-5-20250929

# Override for OpenAI provider
AI_ENGINE_PROVIDER=openai
AGENT_MODEL_PLANNER=gpt-4o
AGENT_MODEL_CODER=gpt-4o
AGENT_MODEL_QA_REVIEWER=gpt-4o
```

### Model Selection Logic

1. **Check agent-specific model** (e.g., `AGENT_MODEL_PLANNER`)
2. **Check provider default model** (e.g., `CLAUDE_MODEL`, `OPENAI_MODEL`)
3. **Fall back to provider's default model**
4. **Validate model is supported by provider**

### Capability-Based Model Selection

For providers without feature parity, models may be selected based on required capabilities:

```python
# Pseudo-code
if requires_extended_thinking:
    if provider == "claude":
        model = "claude-sonnet-4-5-20250929"
    elif provider == "openai":
        # Fallback: OpenAI doesn't support extended thinking
        model = "gpt-4o"  # Default OpenAI model, with warning
        logger.warning("Extended thinking not supported by OpenAI, using standard model")
```

---

## Runtime Fallback Strategy

### Capability-Aware Runtime Fallback

Runtime fallback does not switch from one direct provider to another provider.
It resolves the selected provider/runtime capabilities and degrades an
incompatible request to the first compatible limited runtime mode.

#### Configuration

```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_RUNTIME_FALLBACK=true
```

#### Fallback Behavior

| Request | Fallback Behavior | Default |
|---------|-------------------|---------|
| Direct provider + `full_autonomous` | Degrade to `generic_edit`, then `patch_proposal`, then `analysis_only` if compatible | Disabled |
| Direct provider + limited mode | Stay on requested limited mode | N/A |
| Claude full autonomous | Stay on Claude Agent SDK runtime | N/A |
| Codex full autonomous | Stay on Codex CLI runtime | N/A |

#### Fallback Flow

```
Provider/runtime request
    ↓
Capability check
    ↓
Compatible?
    ↓ Yes                    ↓ No
Run requested runtime     Is AUTO_CODE_RUNTIME_FALLBACK=true?
                              ↓ Yes             ↓ No
                          Use limited mode     Fail fast
```

### CLI Runner Routing

CLI runner routing is separate from runtime fallback. It preserves
`full_autonomous` by routing an impossible direct-provider request to a wired
CLI runtime such as Codex CLI.

```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_CLI_RUNNER_ROUTER=true
CODEX_HOME=/path/to/codex-profile
```

### Retry Strategy

Before falling back, the system retries the original provider:

```bash
# Retry configuration
MAX_RETRIES=3
RETRY_BACKOFF_BASE=1  # seconds
RETRY_BACKOFF_MAX=60  # seconds
```

**Exponential Backoff Formula:**
```
delay = min(RETRY_BACKOFF_BASE * (2 ^ attempt_number), RETRY_BACKOFF_MAX)
```

**Example:**
- Attempt 1: wait 1 second
- Attempt 2: wait 2 seconds
- Attempt 3: wait 4 seconds
- Attempt 4: wait 8 seconds (capped at RETRY_BACKOFF_MAX)

### Graceful Degradation

When a provider lacks a feature, the system can:

1. **Skip the feature** - Continue without the unsupported capability
2. **Use workaround** - Implement alternative approach
3. **Fail with clear error** - Inform user of incompatibility

**Example: Extended Thinking with OpenAI**

```python
# Pseudo-code
if provider == "openai" and request.extended_thinking:
    # Option 1: Skip with warning
    logger.warning("Extended thinking not supported by OpenAI, proceeding without it")

    # Option 2: Use prompt engineering workaround
    system_prompt += "\n\nThink step-by-step before answering."

    # Option 3: Fail fast
    raise FeatureNotSupportedError("Extended thinking requires Claude provider")
```

---

## Configuration Validation

### Startup Validation

The system validates configuration at startup:

```python
from core.providers.config import validate_provider_config

is_valid, errors = validate_provider_config()

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
```

### Validation Checks

1. **Provider selection** - Valid provider name
2. **Required credentials** - API keys present for selected provider
3. **Model validity** - Model identifier supported by provider
4. **API accessibility** - Connection test (optional, with `--validate` flag)

### Configuration Commands

```bash
# Validate configuration without running
python run.py --validate-config

# Show current configuration
python run.py --show-config

# Test provider connection
python run.py --test-provider

# List available providers
python run.py --list-providers
```

---

## Security Considerations

### API Key Management

✅ **DO:**
- Store API keys in environment variables
- Use `.env` file (gitignored)
- Rotate keys regularly
- Use different keys for development/production

❌ **DON'T:**
- Hardcode API keys in source code
- Commit keys to version control
- Share keys via chat/email
- Use production keys in development

### .env File Template

```bash
# .env.example (safe to commit)

# Provider Selection
AI_ENGINE_PROVIDER=claude

# Claude Agent SDK
ANTHROPIC_API_KEY=your-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# OpenAI
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1

# LiteLLM
LITELLM_MODEL=gpt-4
LITELLM_API_KEY=your-key-here

# OpenRouter
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=anthropic/claude-sonnet-4

# Runtime Mode Configuration
AUTO_CODE_RUNTIME_MODE=full_autonomous
AGENT_RUNTIME_MODE_CODER=generic_edit
AUTO_CODE_RUNTIME_FALLBACK=false

# Retry Configuration
MAX_RETRIES=3
RETRY_BACKOFF_BASE=1
RETRY_BACKOFF_MAX=60
```

### Key Rotation

To rotate API keys without downtime:

1. Add new key as secondary variable
2. Test connection with new key
3. Update primary variable
4. Restart application
5. Revoke old key

---

## Advanced Configuration

### Per-Agent Provider Selection

Use per-agent provider and runtime variables to keep full autonomous phases on
Claude while routing selected phases to limited direct-provider runtimes:

```bash
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=generic_edit
```

### Conditional Provider Selection

```python
# Pseudo-code
def select_provider_for_task(task):
    if task.requires_extended_thinking:
        return "claude"  # Only Claude supports this
    elif task.is_cost_sensitive:
        return "openai"  # Assuming OpenAI is cheaper
    else:
        return get_default_provider()
```

### Provider Smoke Checks

```bash
python run.py --provider openai --provider-smoke
python run.py --provider openai --provider-smoke --json
```

---

## Troubleshooting

### Common Issues

#### Issue: "Provider not found"

**Cause:** Invalid `AI_ENGINE_PROVIDER` value

**Solution:**
```bash
# Check valid values
python run.py --list-providers

# Correct provider name
export AI_ENGINE_PROVIDER=claude  # Not "anthropic" or "claude-sdk"
```

#### Issue: "API key not found"

**Cause:** Required API key environment variable not set

**Solution:**
```bash
# For Claude
export ANTHROPIC_API_KEY=sk-ant-...

# For OpenAI
export OPENAI_API_KEY=sk-proj-...

# Verify it's set
echo $ANTHROPIC_API_KEY
```

#### Issue: "Model not supported"

**Cause:** Model identifier not valid for selected provider

**Solution:**
```bash
# Check available models
python run.py --list-models --provider claude

# Use correct model format
# Claude: claude-sonnet-4-5-20250929
# OpenAI: gpt-4o
# LiteLLM: openai/gpt-4
```

#### Issue: "Feature not supported by provider"

**Cause:** Requesting feature not available for selected provider

**Solution:**
```bash
# Switch to provider that supports the feature
export AI_ENGINE_PROVIDER=claude  # For extended thinking, MCP, etc.

# Or disable the feature
# (implementation-specific)
```

---

## Migration Guide

### Migrating from Claude-only to Multi-Provider

**Step 1: Add provider selection to .env**

```bash
# .env
AI_ENGINE_PROVIDER=claude  # Start with default
```

**Step 2: Add secondary provider credentials**

```bash
# .env
OPENAI_API_KEY=sk-proj-...
```

**Step 3: Test the secondary provider in a limited runtime**

```bash
python run.py --provider openai --provider-smoke
python run.py --provider openai --analyze
```

**Step 4: Enable runtime-aware fallback (optional)**

```bash
# .env
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_RUNTIME_FALLBACK=true
```

**Step 5: Update per-agent provider/runtime configuration (optional)**

```bash
# Keep Claude for full autonomous phases and use OpenAI for coder local edits
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=generic_edit
```

---

## Configuration Examples

### Development Environment

```bash
# Use Claude with fast model for development
AI_ENGINE_PROVIDER=claude
CLAUDE_MODEL=claude-haiku-4-20250929
ANTHROPIC_API_KEY=sk-ant-dev-key
```

### Production Environment

```bash
# Use Claude with premium model
AI_ENGINE_PROVIDER=claude
CLAUDE_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_API_KEY=sk-ant-prod-key

# Optional limited fallback path for direct provider runs
AUTO_CODE_RUNTIME_FALLBACK=true
OPENAI_API_KEY=sk-proj-prod-key
```

### Cost-Optimized Environment

```bash
# Keep full autonomous phases on Claude and route coder to generic_edit
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=generic_edit
OPENAI_API_KEY=sk-proj-...
```

### Codex CLI Full Autonomous Environment

```bash
# Use Codex CLI account runtime through an isolated CODEX_HOME
AI_ENGINE_PROVIDER=codex
AUTO_CODE_RUNTIME_MODE=full_autonomous
CODEX_HOME=/path/to/codex-profile
CODEX_MODEL=codex-default
```

### Testing Environment

```bash
# Use LiteLLM with test model
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=openai/gpt-3.5-turbo
LITELLM_API_KEY=sk-test-...
```

---

## Appendix

### Environment Variable Reference

Complete list of all environment variables:

#### Core Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_ENGINE_PROVIDER` | string | `claude` | Selected AI provider |
| `AUTO_CODE_RUNTIME_MODE` | string | `full_autonomous` | Default runtime mode |
| `AGENT_RUNTIME_MODE_PLANNER` | string | unset | Planner runtime override |
| `AGENT_RUNTIME_MODE_CODER` | string | unset | Coder runtime override |
| `AGENT_RUNTIME_MODE_QA_REVIEWER` | string | unset | QA reviewer runtime override |
| `AGENT_RUNTIME_MODE_QA_FIXER` | string | unset | QA fixer runtime override |
| `AUTO_CODE_RUNTIME_FALLBACK` | boolean | `false` | Enable capability-aware limited runtime fallback |
| `AUTO_CODE_CLI_RUNNER_ROUTER` | boolean | `false` | Route impossible direct full-autonomous requests to wired CLI runners |
| `MAX_RETRIES` | integer | `3` | Maximum retry attempts |
| `RETRY_BACKOFF_BASE` | integer | `1` | Base backoff time (seconds) |
| `RETRY_BACKOFF_MAX` | integer | `60` | Maximum backoff time (seconds) |

#### Claude Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ANTHROPIC_API_KEY` | string | (required) | Anthropic API key |
| `CLAUDE_MODEL` | string | `claude-sonnet-4-5-20250929` | Default model |

#### Codex CLI Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CODEX_HOME` | string | user profile | Codex CLI account/profile directory |
| `CODEX_MODEL` | string | `codex-default` | Codex CLI model override |

#### OpenAI Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_API_KEY` | string | (required) | OpenAI API key |
| `OPENAI_MODEL` | string | `gpt-4o` | Default model |
| `OPENAI_BASE_URL` | string | `https://api.openai.com/v1` | API base URL |

#### LiteLLM Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LITELLM_MODEL` | string | (required) | Model identifier |
| `LITELLM_API_BASE` | string | (provider default) | Custom API base URL |
| `LITELLM_API_KEY` | string | (varies) | API key for model provider |

#### OpenRouter Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENROUTER_API_KEY` | string | (required) | OpenRouter API key |
| `OPENROUTER_MODEL` | string | `anthropic/claude-sonnet-4` | Default model |
| `OPENROUTER_BASE_URL` | string | `https://openrouter.ai/api/v1` | API base URL |

#### Google Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GOOGLE_API_KEY` | string | (required) | Google Gemini API key |
| `GOOGLE_MODEL` | string | `gemini-2.0-flash` | Default Gemini model |

#### ZhipuAI Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ZHIPUAI_API_KEY` | string | (required) | ZhipuAI/Z.AI API key |
| `ZHIPUAI_MODEL` | string | provider default | Default GLM model |

#### Ollama Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OLLAMA_BASE_URL` | string | `http://localhost:11434/v1` | Ollama OpenAI-compatible endpoint |
| `OLLAMA_MODEL` | string | provider default | Ollama model |

### Provider Feature Matrix

| Feature | Claude | Codex CLI | OpenAI | Google | LiteLLM | OpenRouter | ZhipuAI | Ollama |
|---------|--------|-----------|--------|--------|---------|------------|---------|--------|
| Full autonomous runtime | Yes | Yes | No | No | No | No | No | No |
| `generic_edit` local actions | Not needed | Not needed | Experimental | Experimental | Experimental | Experimental | Experimental | Experimental |
| External MCP parity | Yes | CLI-dependent | No | No | No | No | No | No |
| Local MCP bridge diagnostics | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Runtime subagents | Claude SDK Task | CLI-dependent | Read-only orchestrated | Read-only orchestrated | Read-only orchestrated | Read-only orchestrated | Read-only orchestrated | Read-only orchestrated |
| Streaming/text completion | Yes | CLI events | Yes | Yes | Yes | Yes | Yes | Yes |
| Provider-native function tools | Yes | CLI-dependent | Yes | Yes | Gateway-dependent | Gateway-dependent | Yes | Model-dependent |

---

**Document Version:** 1.0
**Last Updated:** 2026-05-03
**Status:** Active limited multi-provider support
