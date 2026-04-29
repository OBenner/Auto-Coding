# Environment Variable Configuration

This document describes the environment variable schema for configuring AI engine providers and runtime modes in Auto Code.

## Overview

Auto Code supports multiple AI engine providers through a unified configuration interface. Providers are selected and configured through environment variables.

Provider selection does not guarantee full autonomous coding capability. Claude remains the full autonomous runtime. Non-Claude providers are limited to runtime modes such as `analysis_only` and `patch_proposal` unless a future runtime supplies equivalent tools, MCP, shell, filesystem, and security behavior. See [Provider Runtime Modes](../architecture/provider-runtime-modes.md).

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
# Override for single command
AI_ENGINE_PROVIDER=openai python run.py --spec 001

# Or use command-line flag
python run.py --spec 001 --provider openai
```

---

### `AUTO_CODE_RUNTIME_MODE`

**Description**: Selects the runtime behavior for provider sessions.

**Valid Values**:
- `full_autonomous` (default) - requires Claude Agent SDK-style tools, MCP, shell, filesystem edits, and workspace access
- `patch_proposal` - lets a text provider propose a unified diff that Auto Code validates and applies
- `analysis_only` - allows text-only provider responses without tools or edits

**Example**:
```bash
export AUTO_CODE_RUNTIME_MODE=patch_proposal
```

**Per-Agent Override**:
```bash
export AGENT_RUNTIME_MODE_CODER=patch_proposal
```

Prefer per-agent overrides when mixing Claude with limited providers:

```bash
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=patch_proposal
OPENAI_API_KEY=sk-...
```

If a phase requires capabilities the selected runtime does not provide, Auto Code fails fast with a capability error.

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

OpenAI integration for text completion, analysis-only phases, and patch proposal mode. It does not currently provide full autonomous coding parity with the Claude Agent SDK.

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

#### Limitations

- **No full Auto Code tool runtime**: MCP, shell, and filesystem edits are not exposed directly to the model.
- **No native Auto Code security hooks**: Patch proposal mode applies validated diffs locally instead of giving the provider direct edit access.
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

### Per-Agent Model Configuration (Proposed)

Different agents may use different models based on task requirements:

```bash
# Default models for each agent type
PLANNER_MODEL=claude-sonnet-4-5-20250929
CODER_MODEL=claude-sonnet-4-5-20250929
QA_REVIEWER_MODEL=claude-sonnet-4-5-20250929
QA_FIXER_MODEL=claude-sonnet-4-5-20250929

# Override for OpenAI provider
AI_ENGINE_PROVIDER=openai
PLANNER_MODEL=gpt-5.2
CODER_MODEL=gpt-5.2
QA_REVIEWER_MODEL=gpt-5.2
QA_FIXER_MODEL=gpt-5
```

### Model Selection Logic

1. **Check agent-specific model** (e.g., `PLANNER_MODEL`)
2. **Check provider default model** (e.g., `CLAUDE_MODEL`, `OPENAI_MODEL`)
3. **Fall back to provider's default model**
4. **Validate model is supported by provider**

### Capability-Based Model Selection (Proposed)

For providers without feature parity, models may be selected based on required capabilities:

```python
# Pseudo-code
if requires_extended_thinking:
    if provider == "claude":
        model = "claude-sonnet-4-5-20250929"
    elif provider == "openai":
        # Fallback: OpenAI doesn't support extended thinking
        model = "gpt-5.2"  # Best available, with warning
        logger.warning("Extended thinking not supported by OpenAI, using standard model")
```

---

## Fallback Strategy

### Automatic Provider Fallback (Proposed)

When a provider fails, the system can automatically fall back to an alternative provider:

#### Configuration

```bash
# Enable automatic fallback
FALLBACK_ENABLED=true

# Specify fallback provider
FALLBACK_PROVIDER=claude

# Fallback trigger conditions
FALLBACK_ON_RATE_LIMIT=true
FALLBACK_ON_AUTH_ERROR=false
FALLBACK_ON_TIMEOUT=true
FALLBACK_ON_FEATURE_UNSUPPORTED=true
```

#### Fallback Behavior

| Error Type | Fallback Behavior | Default |
|------------|-------------------|---------|
| Rate limit (429) | Retry with fallback after N attempts | Enabled |
| Authentication (401) | Fail fast, no fallback | Disabled |
| Timeout | Retry with fallback | Enabled |
| Feature not supported | Use fallback if available | Enabled |
| Network error | Retry with exponential backoff, then fallback | Enabled |

#### Fallback Flow

```
Request to Provider A
    ↓
Error occurs
    ↓
Is error retryable?
    ↓ Yes                    ↓ No
Retry Provider A          Check fallback enabled
    ↓                           ↓ Yes    ↓ No
Max retries reached?      Use Fallback B    Fail
    ↓ Yes    ↓ No
Provider A failed       Success with B
    ↓
Check fallback enabled
    ↓ Yes
Use Fallback Provider B
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

# OpenAI (proposed)
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-5.2

# LiteLLM
LITELLM_MODEL=gpt-4
LITELLM_API_KEY=your-key-here

# OpenRouter
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=anthropic/claude-sonnet-4

# Fallback Configuration
FALLBACK_ENABLED=true
FALLBACK_PROVIDER=claude

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

### Provider Switching at Runtime (Proposed)

Agents can switch providers mid-execution based on task requirements:

```python
# Pseudo-code
if task.requires_native_mcp and current_provider != "claude":
    switch_to_provider("claude")
    logger.info("Switched to Claude for MCP support")
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

### Provider Health Monitoring (Proposed)

```bash
# Health check configuration
PROVIDER_HEALTH_CHECK_ENABLED=true
PROVIDER_HEALTH_CHECK_INTERVAL=300  # seconds
PROVIDER_HEALTH_CHECK_TIMEOUT=10    # seconds

# Unhealthy provider handling
PROVIDER_AUTO_DISABLE_ON_FAILURE=true
PROVIDER_AUTO_REENABLE_INTERVAL=600  # seconds
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
# OpenAI: gpt-5.2
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

**Step 3: Test secondary provider**

```bash
AI_ENGINE_PROVIDER=openai python run.py --spec 001
```

**Step 4: Enable fallback (optional)**

```bash
# .env
FALLBACK_ENABLED=true
FALLBACK_PROVIDER=claude
```

**Step 5: Update agent configurations (optional)**

```bash
# Use different providers for different agents
PLANNER_PROVIDER=claude
CODER_PROVIDER=openai
QA_REVIEWER_PROVIDER=claude
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

# Enable fallback for resilience
FALLBACK_ENABLED=true
FALLBACK_PROVIDER=openai
OPENAI_API_KEY=sk-proj-prod-key
```

### Cost-Optimized Environment

```bash
# Use OpenAI for cost savings (assuming lower pricing)
AI_ENGINE_PROVIDER=openai
OPENAI_MODEL=gpt-5
OPENAI_API_KEY=sk-proj-...

# Fallback to Claude for complex tasks
FALLBACK_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
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
| `FALLBACK_ENABLED` | boolean | `false` | Enable automatic fallback |
| `FALLBACK_PROVIDER` | string | `claude` | Fallback provider |
| `MAX_RETRIES` | integer | `3` | Maximum retry attempts |
| `RETRY_BACKOFF_BASE` | integer | `1` | Base backoff time (seconds) |
| `RETRY_BACKOFF_MAX` | integer | `60` | Maximum backoff time (seconds) |

#### Claude Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ANTHROPIC_API_KEY` | string | (required) | Anthropic API key |
| `CLAUDE_MODEL` | string | `claude-sonnet-4-5-20250929` | Default model |

#### OpenAI Variables (Proposed)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_API_KEY` | string | (required) | OpenAI API key |
| `OPENAI_MODEL` | string | `gpt-5.2` | Default model |
| `OPENAI_BASE_URL` | string | `https://api.openai.com/v1` | API base URL |
| `OPENAI_CUSTOM_MCP_ENABLED` | boolean | `true` | Enable custom MCP client |
| `OPENAI_SECURITY_WRAPPER_ENABLED` | boolean | `true` | Enable security wrapper |

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

### Provider Feature Matrix

| Feature | Claude | OpenAI | LiteLLM | OpenRouter |
|---------|--------|--------|---------|------------|
| Native MCP | ✅ | ⚠️* | ❌ | ❌ |
| Security Hooks | ✅ | ⚠️* | ❌ | ❌ |
| Agent Orchestration | ✅ | ⚠️* | ❌ | ❌ |
| Extended Thinking | ✅ | ❌ | ❌ | ❌ |
| Streaming | ✅ | ✅ | ✅ | ✅ |
| Function Calling | ✅ | ✅ | ✅ | ✅ |
| Session Management | ✅ | ⚠️* | ❌ | ❌ |

*Requires custom implementation

---

**Document Version:** 1.0
**Last Updated:** 2025-02-16
**Status:** Concept (for OpenAI integration)
