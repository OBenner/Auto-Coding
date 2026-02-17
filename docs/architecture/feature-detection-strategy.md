# Feature Detection Strategy for Unsupported Features

## Overview

This document defines strategies for detecting and handling provider features that are not universally supported across all AI providers. When Auto Code supports multiple providers (Claude, OpenAI, LiteLLM, OpenRouter), each provider has different capabilities. This strategy ensures:

1. **Graceful degradation** - System continues working even when features are unavailable
2. **Clear user communication** - Users understand what's supported and what's not
3. **Intelligent fallbacks** - Alternative approaches when primary features aren't available
4. **Provider selection guidance** - Help users choose the right provider for their needs

## Scope

### Supported Features

| Feature | Claude | OpenAI | LiteLLM | OpenRouter |
|---------|--------|--------|---------|------------|
| Extended Thinking | ✅ Native | ❌ Not supported | ❌ Not supported | ❌ Not supported |
| MCP Servers | ✅ Built-in | ⚠️ Custom required | ❌ Not supported | ❌ Not supported |
| Native Security | ✅ Built-in | ⚠️ Wrapper required | ❌ Not supported | ❌ Not supported |
| Streaming Responses | ✅ Yes | ✅ Yes | ⚠️ Varies | ⚠️ Varies |
| Function Calling | ✅ Tools | ✅ Functions | ✅ Varies | ✅ Varies |
| Session Management | ✅ Stateful | ❌ Stateless | ❌ Stateless | ❌ Stateless |
| Structured Output | ✅ Yes | ✅ Yes | ⚠️ Varies | ⚠️ Varies |
| Parallel Agents | ✅ Native | ❌ Manual | ❌ Not supported | ❌ Not supported |

**Legend:**
- ✅ **Native**: Built-in support, no adapter code needed
- ❌ **Not supported**: Feature not available, requires significant workaround or fallback
- ⚠️ **Varies**: Capability depends on underlying model or requires custom implementation

## Strategy 1: Extended Thinking Fallback

### The Problem

Claude SDK supports extended thinking via `max_thinking_tokens` parameter, which enables the model to show its reasoning process. OpenAI API has no equivalent feature.

### Impact

Extended thinking is critical for:
- **Complex architecture decisions** - Understanding trade-offs
- **Debugging complex issues** - Tracing through code paths
- **Spec creation** - Breaking down requirements thoroughly
- **Code review** - Deep analysis of code quality

### Fallback Strategies

#### Strategy 1A: Prompt Engineering Workaround

**Approach**: Modify system prompts to encourage "thinking out loud"

```python
def create_session_with_thinking(provider: AIEngineProvider, config: SessionConfig) -> AgentSession:
    """Create session, using extended thinking if available."""

    if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        # Native extended thinking (Claude)
        config.extra["max_thinking_tokens"] = 16000
        logger.info("Using native extended thinking")
    else:
        # Fallback: Prompt engineering (OpenAI, LiteLLM)
        config.system_prompt = """
You are a helpful AI assistant. When solving complex problems:

1. **Think step-by-step**: Break down the problem into smaller parts
2. **Explain your reasoning**: Before taking action, explain what you'll do and why
3. **Consider alternatives**: Discuss multiple approaches before choosing one
4. **Show your work**: Provide intermediate thoughts and analysis

This helps the user understand your decision-making process.
"""
        logger.warning(
            f"Provider {provider.name} does not support native extended thinking. "
            "Using prompt engineering workaround."
        )

    return provider.create_session(config)
```

**Pros:**
- Works with any provider
- No code changes required
- Encourages transparency

**Cons:**
- Not enforced by model (can be ignored)
- Uses output tokens for thinking (more expensive)
- No separate thinking budget
- May reduce quality vs native extended thinking

#### Strategy 1B: Multiple-Pass Reasoning

**Approach**: Break complex tasks into multiple passes

```python
async def complex_task_with_fallback(
    provider: AIEngineProvider,
    task: str
) -> str:
    """Execute complex task with or without extended thinking."""

    if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        # Single pass with extended thinking (Claude)
        session = provider.create_session(
            SessionConfig(
                name="complex-task",
                extra={"max_thinking_tokens": 16000}
            )
        )
        return await session.send_message(task)

    else:
        # Multi-pass approach for other providers
        logger.info("Using multi-pass approach (no extended thinking)")

        # Pass 1: Analysis
        session = provider.create_session(SessionConfig(name="analysis"))
        analysis = await session.send_message(
            f"Analyze this task and break it into steps: {task}\n\n"
            "Provide a step-by-step plan. Do not implement yet."
        )

        # Pass 2: Implementation
        await session.send_message(
            f"Based on this analysis:\n{analysis}\n\n"
            f"Now implement: {task}\n\n"
            "Follow the plan you created."
        )

        # Pass 3: Review
        return await session.send_message(
            "Review your implementation. Check for:\n"
            "1. Completeness - Did you address all requirements?\n"
            "2. Correctness - Are there any bugs or issues?\n"
            "3. Edge cases - What might break?\n\n"
            "Provide a final summary."
        )
```

**Pros:**
- Works with any provider
- Encourages structured thinking
- Can improve quality for complex tasks

**Cons:**
- Slower (multiple API calls)
- More expensive (multiple requests)
- Requires custom implementation per task type
- No "hidden" thinking (user sees intermediate steps)

#### Strategy 1C: Provider Selection with Warning

**Approach**: Require Claude provider for tasks needing extended thinking

```python
def run_complex_reasoning_task(provider: AIEngineProvider, task: str) -> None:
    """Run task requiring extended thinking."""

    if not provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        raise ProviderError(
            f"Provider '{provider.name}' does not support extended thinking.\n\n"
            f"This task requires complex reasoning. Please use Claude provider:\n"
            f"  python run.py --spec XXX --provider claude\n\n"
            f"Or set DEFAULT_PROVIDER=claude in .env"
        )

    # Proceed with extended thinking
    session = provider.create_session(
        SessionConfig(
            name="reasoning",
            extra={"max_thinking_tokens": 16000}
        )
    )
    # ... execute task
```

**Pros:**
- Ensures best quality
- Clear error message
- Guides user to correct provider

**Cons:**
- Forces provider choice
- Not graceful degradation
- May frustrate users who want to use OpenAI

### Recommended Approach

**Combine Strategy 1A and 1C:**

1. **Optional features**: Use prompt engineering workaround (Strategy 1A)
2. **Critical features**: Require Claude provider (Strategy 1C)

```python
def create_session(
    provider: AIEngineProvider,
    config: SessionConfig,
    extended_thinking: str = "optional"  # "required", "optional", "disabled"
) -> AgentSession:
    """Create session with extended thinking strategy."""

    supports_thinking = provider.supports_feature(ProviderFeature.EXTENDED_THINKING)

    if extended_thinking == "required" and not supports_thinking:
        raise ProviderError(
            f"Provider '{provider.name}' does not support extended thinking. "
            f"Use --provider claude or set extended_thinking='optional'"
        )

    if supports_thinking:
        config.extra["max_thinking_tokens"] = 16000
    elif extended_thinking == "optional":
        # Add prompt engineering workaround
        config.system_prompt = config.system_prompt + THINKING_OUT_LOUD_PROMPT

    return provider.create_session(config)
```

## Strategy 2: MCP Servers Fallback

### The Problem

Claude SDK has built-in MCP (Model Context Protocol) server integration. OpenAI has no native MCP support. MCP servers provide:
- **Context7**: Documentation lookup
- **Linear**: Issue tracking integration
- **Graphiti**: Long-term memory
- **Electron**: E2E testing

### Fallback Strategies

#### Strategy 2A: Custom MCP Client for OpenAI

**Approach**: Implement MCP protocol client in `core/mcp/openai_client.py`

**Status**: See `docs/architecture/mcp-client-design.md` for full design.

**Summary**:
- Implement MCP protocol (JSON-RPC 2.0) from scratch
- Connect to same MCP servers as Claude
- Translate tool responses to OpenAI function calling format
- **Effort**: 2-3 weeks
- **Complexity**: High

#### Strategy 2B: Feature Flags with Graceful Degradation

**Approach**: Disable MCP-dependent features for non-Claude providers

```python
def create_mcp_enabled_session(
    provider: AIEngineProvider,
    config: SessionConfig,
    required_mcp_tools: list[str] = []
) -> AgentSession:
    """Create session, checking MCP availability."""

    if not provider.supports_feature(ProviderFeature.MCP_SERVERS):
        if required_mcp_tools:
            # Required MCP tools missing
            raise ProviderError(
                f"Provider '{provider.name}' does not support MCP servers.\n"
                f"Required tools: {', '.join(required_mcp_tools)}\n\n"
                f"Use --provider claude to enable MCP integration."
            )
        else:
            # Optional MCP tools - warn and continue
            logger.warning(
                f"Provider '{provider.name}' does not support MCP servers. "
                f"Features like Context7, Linear, and Graphiti will be unavailable."
            )

    return provider.create_session(config)
```

**Usage Examples:**

```python
# Example 1: Context7 documentation lookup (optional)
def lookup_documentation(
    provider: AIEngineProvider,
    query: str
) -> str | None:
    """Look up documentation via Context7 (if available)."""

    if not provider.supports_feature(ProviderFeature.MCP_SERVERS):
        logger.warning("Context7 not available - using web search")
        # Fallback to web search
        return web_search(query)

    # Use Context7 MCP server
    return context7_search(query)


# Example 2: Graphiti memory (optional)
def add_to_memory(
    provider: AIEngineProvider,
    insight: str
) -> None:
    """Add insight to memory (if available)."""

    if not provider.supports_feature(ProviderFeature.MCP_SERVERS):
        logger.warning("Graphiti memory not available - skipping")
        return

    # Use Graphiti MCP server
    graphiti.add_insight(insight)
```

#### Strategy 2C: Provider Selection by MCP Requirement

**Approach**: Route to Claude provider for MCP-dependent tasks

```python
# In configuration
agent_routing = {
    "planner": "claude",      # Requires Context7 for docs lookup
    "coder": "openai",        # Can work without MCP
    "qa_reviewer": "claude",  # Requires Electron MCP for E2E testing
    "qa_fixer": "claude",     # Requires Electron MCP for verification
}

# Or automatic routing
def select_provider_for_task(
    task_type: str,
    available_providers: dict[str, AIEngineProvider]
) -> str:
    """Select provider based on task requirements."""

    mcp_required_for = {
        "planner": True,      # Needs Context7
        "qa_reviewer": True,  # Needs Electron
        "qa_fixer": True,     # Needs Electron
    }

    if mcp_required_for.get(task_type, False):
        # Must use Claude (only provider with MCP)
        if "claude" not in available_providers:
            raise ProviderError("Task requires MCP - Claude provider required")
        return "claude"

    # Can use any provider (user's choice or default)
    return available_providers.get("default", "claude")
```

### Recommended Approach

**Combine Strategy 2B and 2C:**

1. **Agent-level routing**: Use Claude for MCP-dependent agents (planner, qa)
2. **Feature-level degradation**: Gracefully handle missing MCP for optional features
3. **Clear warnings**: Inform users when features are unavailable

```python
# Configuration example
{
  "agents": {
    "planner": {
      "provider": "claude",  # Fixed: Requires Context7
      "reason": "Documentation lookup via Context7 MCP server"
    },
    "coder": {
      "provider": "openai",  # Flexible: Can work without MCP
      "mcp_fallback": "warning"  # Warn if Graphiti unavailable
    },
    "qa_reviewer": {
      "provider": "claude",  # Fixed: Requires Electron MCP
      "reason": "E2E testing via Electron MCP server"
    }
  }
}
```

## Strategy 3: Native Security Fallback

### The Problem

Claude SDK has built-in security (sandbox, permissions, hooks). OpenAI has no native security. See `docs/architecture/security-wrapper-design.md` for full security wrapper design.

### Security Components

| Component | Claude | OpenAI | Mitigation |
|-----------|--------|--------|------------|
| **Sandbox** | ✅ OS-level isolation | ❌ Not available | ⚠️ Defer to Phase 2 |
| **File Permissions** | ✅ Native enforcement | ❌ Not available | ✅ Wrapper layer |
| **Command Allowlisting** | ✅ PreToolUse hooks | ❌ Not available | ✅ Wrapper layer |
| **Tool Filtering** | ✅ Per-agent tool lists | ❌ Not available | ✅ Wrapper layer |

### Fallback Strategy: Security Wrapper Layer

**Design**: Universal security wrapper applied to OpenAI provider

```python
class SecurityWrapper:
    """Apply Claude's security model to OpenAI provider."""

    def __init__(self, provider: AIEngineProvider, project_dir: str):
        self.provider = provider
        self.project_dir = project_dir
        self.security = SecurityManager(project_dir)

    async def send_message(
        self,
        session_id: str,
        message: str
    ) -> AsyncIterator[Message]:
        """Send message with security enforcement."""

        # Intercept tool calls (OpenAI function calling)
        async for msg in self.provider.send_message(session_id, message):
            if msg.type == "tool_call":
                # Validate tool call before execution
                if not self._is_tool_allowed(msg.tool_name, msg.tool_args):
                    logger.error(f"Tool call blocked: {msg.tool_name}")
                    continue

                # For file operations, validate paths
                if msg.tool_name in ["Read", "Write", "Edit"]:
                    if not self._is_path_allowed(msg.tool_args.get("path")):
                        logger.error(f"Path not allowed: {msg.tool_args.get('path')}")
                        continue

                # For Bash, validate command
                if msg.tool_name == "Bash":
                    if not self._is_command_allowed(msg.tool_args.get("command")):
                        logger.error(f"Command not allowed: {msg.tool_args.get('command')}")
                        continue

            yield msg
```

**Implementation Phases:**

1. **Phase 1** (High priority): File permissions, command allowlisting
2. **Phase 2** (Low priority): OS-level sandbox (requires containers/chroot)

### Recommended Approach

**Use security wrapper for OpenAI provider:**

```python
def create_client(
    provider: str,
    project_dir: str,
    agent_type: str
) -> AIEngineProvider:
    """Create provider client with security."""

    base_provider = ProviderFactory.create(provider, config)

    # Claude: Has native security, no wrapper needed
    if provider == "claude":
        return base_provider

    # OpenAI/LiteLLM: Apply security wrapper
    if provider in ["openai", "litellm"]:
        logger.info(f"Applying security wrapper to {provider} provider")
        return SecurityWrapper(
            provider=base_provider,
            project_dir=project_dir,
            agent_type=agent_type
        )

    return base_provider
```

## Strategy 4: Capability Flags in Practice

### Definition

Capability flags are runtime checks using the `ProviderFeature` enum:

```python
from core.providers.base import ProviderFeature

if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
    # Use extended thinking
else:
    # Use fallback
```

### Usage Patterns

#### Pattern 1: One-Time Feature Check

```python
# Check once at session creation
supports_extended_thinking = provider.supports_feature(
    ProviderFeature.EXTENDED_THINKING
)

if supports_extended_thinking:
    config.max_thinking_tokens = 16000
```

**Why**: Efficient - checks feature once, not in loops.

#### Pattern 2: Feature Validation

```python
def validate_required_features(
    provider: AIEngineProvider,
    required: list[ProviderFeature]
) -> None:
    """Validate that provider supports all required features."""

    missing = [
        f.value for f in required
        if not provider.supports_feature(f)
    ]

    if missing:
        raise ProviderError(
            f"Provider '{provider.name}' missing required features: "
            f"{', '.join(missing)}\n\n"
            f"Consider using Claude provider for full feature support."
        )
```

**Usage:**

```python
validate_required_features(
    provider,
    [
        ProviderFeature.EXTENDED_THINKING,
        ProviderFeature.MCP_SERVERS,
        ProviderFeature.NATIVE_SECURITY,
    ]
)
```

#### Pattern 3: Feature-Dependent Configuration

```python
def configure_session(
    provider: AIEngineProvider,
    agent_type: str
) -> SessionConfig:
    """Configure session based on provider capabilities."""

    config = SessionConfig(name=agent_type)

    # Extended thinking for complex agents
    if agent_type in ["planner", "qa_reviewer"]:
        if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
            config.extra["max_thinking_tokens"] = 16000
        else:
            config.system_prompt += "\n\n" + THINKING_OUT_LOUD_PROMPT

    # MCP for memory-dependent agents
    if provider.supports_feature(ProviderFeature.MCP_SERVERS):
        config.extra["enable_mcp"] = True
        config.mcp_servers = ["context7", "graphiti"]
    else:
        logger.warning("MCP not available - memory features disabled")

    return config
```

#### Pattern 4: Graceful Degradation

```python
def execute_with_optional_features(
    provider: AIEngineProvider,
    task: str,
    optional_features: dict[ProviderFeature, Callable]
) -> str:
    """Execute task, using optional features if available."""

    result = task

    for feature, handler in optional_features.items():
        if provider.supports_feature(feature):
            logger.info(f"Using feature: {feature.value}")
            result = handler(result)
        else:
            logger.info(f"Skipping feature: {feature.value}")

    return result

# Usage
result = execute_with_optional_features(
    provider,
    initial_task,
    {
        ProviderFeature.EXTENDED_THINKING: lambda t: t.with_thinking(),
        ProviderFeature.MCP_SERVERS: lambda t: t.with_memory(),
    }
)
```

### Best Practices

✅ **DO:**
- Check features once, cache the result
- Use `ProviderFeature` enum, not string literals
- Provide clear fallbacks for unsupported features
- Log warnings when features are unavailable
- Document which features are required vs optional

❌ **DON'T:**
- Check features in loops (performance issue)
- Silently skip required features
- Use string literals like "extended_thinking"
- Throw errors for optional features (use degradation)
- Assume all providers support the same features

## Strategy 5: Graceful Degradation Hierarchy

### Hierarchy Levels

Define feature requirement levels:

```python
class FeatureRequirement(Enum):
    """How critical is a feature to task success?"""

    REQUIRED = "required"
    """Task cannot succeed without this feature. Fail if unavailable."""

    RECOMMENDED = "recommended"
    """Task works better with this feature. Warn if unavailable."""

    OPTIONAL = "optional"
    """Nice-to-have feature. Silent skip if unavailable."""
```

### Implementation

```python
def create_session_with_requirements(
    provider: AIEngineProvider,
    config: SessionConfig,
    feature_requirements: dict[ProviderFeature, FeatureRequirement]
) -> AgentSession:
    """Create session, handling feature requirements appropriately."""

    for feature, requirement in feature_requirements.items():
        supported = provider.supports_feature(feature)

        if not supported:
            if requirement == FeatureRequirement.REQUIRED:
                raise ProviderError(
                    f"Provider '{provider.name}' does not support required feature: "
                    f"{feature.value}\n\nUse --provider claude or choose a different task."
                )

            elif requirement == FeatureRequirement.RECOMMENDED:
                logger.warning(
                    f"Provider '{provider.name}' does not support recommended feature: "
                    f"{feature.value}\n\nTask quality may be reduced. "
                    f"Consider using Claude provider."
                )

            elif requirement == FeatureRequirement.OPTIONAL:
                logger.info(f"Skipping optional feature: {feature.value}")

    return provider.create_session(config)
```

### Usage Examples

#### Example 1: Spec Creation (Planner Agent)

```python
def create_planner_session(provider: AIEngineProvider) -> AgentSession:
    """Create planner session with feature requirements."""

    return create_session_with_requirements(
        provider,
        SessionConfig(name="planner"),
        {
            # Critical for spec quality
            ProviderFeature.EXTENDED_THINKING: FeatureRequirement.REQUIRED,

            # Important for documentation lookup
            ProviderFeature.MCP_SERVERS: FeatureRequirement.RECOMMENDED,

            # Nice to have, but not critical
            ProviderFeature.PARALLEL_AGENT_EXECUTION: FeatureRequirement.OPTIONAL,
        }
    )
```

**Outcome:**
- OpenAI provider: Fails (missing REQUIRED extended thinking)
- LiteLLM + Claude model: Warns about MCP (missing RECOMMENDED feature)
- Claude provider: All features available

#### Example 2: Code Implementation (Coder Agent)

```python
def create_coder_session(provider: AIEngineProvider) -> AgentSession:
    """Create coder session with feature requirements."""

    return create_session_with_requirements(
        provider,
        SessionConfig(name="coder"),
        {
            # Critical for code generation
            ProviderFeature.FUNCTION_CALLING: FeatureRequirement.REQUIRED,

            # Useful for file operations
            ProviderFeature.NATIVE_SECURITY: FeatureRequirement.RECOMMENDED,

            # Helpful but not required
            ProviderFeature.MCP_SERVERS: FeatureRequirement.OPTIONAL,

            # Not needed for coding
            ProviderFeature.EXTENDED_THINKING: FeatureRequirement.OPTIONAL,
        }
    )
```

**Outcome:**
- OpenAI provider: Succeeds (has function calling)
- OpenAI provider: Warns about security (missing RECOMMENDED feature)
- LiteLLM (GPT model): Succeeds (has function calling)
- All providers: Skip optional features

## Strategy 6: Error Handling for Unsupported Features

### Error Types

```python
class FeatureNotSupportedError(ProviderError):
    """Raised when attempting to use an unsupported feature."""

    def __init__(
        self,
        provider_name: str,
        feature: ProviderFeature,
        suggestion: str | None = None
    ):
        self.provider_name = provider_name
        self.feature = feature
        self.suggestion = suggestion

        message = (
            f"Provider '{provider_name}' does not support feature: {feature.value}"
        )

        if suggestion:
            message += f"\n\n{suggestion}"

        super().__init__(message)


class FeatureNotRecommendedWarning(Warning):
    """Warning when using a provider without recommended features."""

    def __init__(
        self,
        provider_name: str,
        missing_features: list[ProviderFeature]
    ):
        self.provider_name = provider_name
        self.missing_features = missing_features

        message = (
            f"Provider '{provider_name}' is missing recommended features:\n"
            f"{', '.join(f.value for f in missing_features)}\n\n"
            f"Task quality may be reduced. Consider using Claude provider."
        )

        super().__init__(message)
```

### Usage Examples

#### Example 1: Required Feature Missing

```python
def run_complex_task(provider: AIEngineProvider) -> None:
    """Run task requiring extended thinking."""

    if not provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        raise FeatureNotSupportedError(
            provider_name=provider.name,
            feature=ProviderFeature.EXTENDED_THINKING,
            suggestion=(
                "This task requires complex reasoning. "
                "Use Claude provider:\n"
                "  python run.py --spec XXX --provider claude\n"
                "Or set DEFAULT_PROVIDER=claude in .env"
            )
        )

    # Proceed with task
    ...
```

#### Example 2: Recommended Features Missing

```python
def run_task_with_warnings(provider: AIEngineProvider) -> None:
    """Run task, warning if recommended features missing."""

    missing_recommended = [
        f for f in [
            ProviderFeature.EXTENDED_THINKING,
            ProviderFeature.MCP_SERVERS,
        ]
        if not provider.supports_feature(f)
    ]

    if missing_recommended:
        warnings.warn(
            FeatureNotRecommendedWarning(
                provider_name=provider.name,
                missing_features=missing_recommended
            )
        )

    # Proceed with task (quality may be reduced)
    ...
```

## Strategy 7: Provider Selection Guidance

### Decision Tree

```text
User wants to run a task
    │
    ├─→ Does task require extended thinking?
    │   ├─ Yes → Use Claude provider
    │   └─ No  → Continue
    │
    ├─→ Does task require MCP servers?
    │   ├─ Yes → Use Claude provider
    │   └─ No  → Continue
    │
    ├─→ Does task require E2E testing?
    │   ├─ Yes → Use Claude provider (Electron MCP)
    │   └─ No  → Continue
    │
    ├─→ User has API key for which provider?
    │   ├─ Both → Recommend Claude (better feature support)
    │   ├─ OpenAI only → Use OpenAI (warn about missing features)
    │   └─ Claude only → Use Claude
    │
    └─→ Default: Claude (full feature support)
```

### Configuration-Based Selection

```json
{
  "providers": {
    "claude": {
      "enabled": true,
      "api_key_required": true,
      "features": {
        "extended_thinking": true,
        "mcp_servers": true,
        "native_security": true,
        "parallel_agents": true
      }
    },
    "openai": {
      "enabled": true,
      "api_key_required": true,
      "features": {
        "extended_thinking": false,
        "mcp_servers": false,
        "native_security": false,
        "parallel_agents": false
      },
      "warnings": [
        "Extended thinking not supported - quality may be reduced for complex tasks",
        "MCP servers not supported - Context7, Graphiti, Linear unavailable",
        "No native security - using wrapper layer (may be less robust)"
      ]
    }
  },
  "routing": {
    "default_provider": "claude",
    "agent_routing": {
      "planner": "claude",
      "coder": "openai",
      "qa_reviewer": "claude",
      "qa_fixer": "claude"
    },
    "feature_requirements": {
      "planner": {
        "required_features": ["extended_thinking"],
        "recommended_features": ["mcp_servers"]
      },
      "coder": {
        "required_features": ["function_calling"],
        "recommended_features": ["native_security"]
      }
    }
  }
}
```

### User-Facing Messages

#### Message 1: Provider Selection Hint

```text
🤖 Auto-Code Provider Recommendation

Task "spec-creation" requires:
  ✅ Extended thinking (complex reasoning)
  ✅ MCP servers (documentation lookup)

Recommended provider: Claude
  - Supports all required features
  - Best quality for spec creation

Current provider: OpenAI
  ⚠️  Missing: extended_thinking, mcp_servers
  ⚠️  Task quality may be significantly reduced

Options:
  1. Switch to Claude: --provider claude
  2. Continue with OpenAI (not recommended)
  3. Set default: DEFAULT_PROVIDER=claude in .env

Your choice: [1/2/3]
```

#### Message 2: Feature Unavailable Warning

```text
⚠️  Feature Unavailable Warning

Provider 'OpenAI' does not support MCP servers.

The following features will be unavailable:
  - Context7 (documentation lookup)
  - Graphiti (long-term memory)
  - Linear (issue tracking)

This task will proceed but may have reduced quality.

For full feature support, use Claude provider:
  python run.py --spec XXX --provider claude
```

## Strategy 8: Testing Feature Detection

### Unit Tests

```python
def test_feature_detection_claude():
    """Claude provider should support all features."""
    provider = ClaudeAgentProvider(config)

    # All features should be supported
    assert provider.supports_feature(ProviderFeature.EXTENDED_THINKING)
    assert provider.supports_feature(ProviderFeature.MCP_SERVERS)
    assert provider.supports_feature(ProviderFeature.NATIVE_SECURITY)
    assert provider.supports_feature(ProviderFeature.STREAMING_RESPONSES)
    assert provider.supports_feature(ProviderFeature.FUNCTION_CALLING)
    assert provider.supports_feature(ProviderFeature.SESSION_MANAGEMENT)

def test_feature_detection_openai():
    """OpenAI provider should have limited feature support."""
    provider = OpenAIAgentProvider(config)

    # Supported features
    assert provider.supports_feature(ProviderFeature.STREAMING_RESPONSES)
    assert provider.supports_feature(ProviderFeature.FUNCTION_CALLING)

    # Unsupported features
    assert not provider.supports_feature(ProviderFeature.EXTENDED_THINKING)
    assert not provider.supports_feature(ProviderFeature.MCP_SERVERS)
    assert not provider.supports_feature(ProviderFeature.NATIVE_SECURITY)
    assert not provider.supports_feature(ProviderFeature.SESSION_MANAGEMENT)

def test_feature_validation():
    """Test feature requirement validation."""
    claude = ClaudeAgentProvider(config)
    openai = OpenAIAgentProvider(config)

    # Should pass for Claude, fail for OpenAI
    validate_required_features(claude, [
        ProviderFeature.EXTENDED_THINKING,
        ProviderFeature.MCP_SERVERS,
    ])  # OK

    with pytest.raises(ProviderError):
        validate_required_features(openai, [
            ProviderFeature.EXTENDED_THINKING,
        ])  # Fails
```

### Integration Tests

```python
def test_session_creation_with_extended_thinking():
    """Test session creation with extended thinking fallback."""
    openai = OpenAIAgentProvider(config)

    # Should not raise error, should use prompt engineering fallback
    session = create_session_with_thinking(openai, SessionConfig(name="test"))

    # Verify prompt engineering workaround was added
    assert "Think step-by-step" in session.config.system_prompt

def test_graceful_degradation():
    """Test graceful degradation for optional features."""
    openai = OpenAIAgentProvider(config)

    # Should not raise error for optional features
    session = create_session_with_optional_features(
        openai,
        SessionConfig(name="test"),
        optional_thinking=True,
        optional_mcp=True,
    )

    # Session should be created successfully
    assert session is not None

def test_required_feature_error():
    """Test that required features raise errors."""
    openai = OpenAIAgentProvider(config)

    with pytest.raises(FeatureNotSupportedError) as exc:
        create_session_with_requirements(
            openai,
            SessionConfig(name="test"),
            {
                ProviderFeature.EXTENDED_THINKING: FeatureRequirement.REQUIRED,
            }
        )

    # Verify error message
    assert "does not support required feature" in str(exc.value)
    assert "extended_thinking" in str(exc.value)
```

## Strategy 9: Documentation and User Guidance

### Provider Comparison Table

Include in user documentation:

```text
# Provider Comparison

| Feature | Claude | OpenAI | Notes |
|---------|--------|--------|-------|
| **Reasoning** |
| Extended Thinking | ✅ Yes | ❌ No | Claude shows reasoning process |
| **Integrations** |
| MCP Servers | ✅ Built-in | ❌ No | Context7, Graphiti, Linear, Electron |
| **Security** |
| Native Security | ✅ Yes | ⚠️ Wrapper | Claude has OS-level sandbox |
| File Permissions | ✅ Yes | ✅ Wrapper | Both restrict file operations |
| Command Allowlisting | ✅ Yes | ✅ Wrapper | Both validate commands |
| **Performance** |
| Streaming | ✅ Yes | ✅ Yes | Both support streaming |
| Speed | Fast | Fast | Similar latency |
| **Cost** |
| Pricing | $3/M input | TBD | Check provider pricing |

**Recommendation**: Use Claude provider for best experience and full feature support.
```

### Feature Availability by Agent

```text
# Agent Feature Requirements

| Agent | Extended Thinking | MCP Servers | Native Security | Recommended Provider |
|-------|-------------------|-------------|-----------------|---------------------|
| **Planner** | Required | Recommended | Optional | Claude |
| **Coder** | Optional | Optional | Recommended | Any |
| **QA Reviewer** | Recommended | Required (Electron) | Optional | Claude |
| **QA Fixer** | Recommended | Required (Electron) | Optional | Claude |
```

## Implementation Checklist

For feature detection strategy to be complete:

- [x] Feature Detection API designed (`docs/architecture/feature-detection-api.md`)
- [x] Feature Detection Strategy designed (this document)
- [ ] Implement `ProviderFeature` enum in `core/providers/base.py`
- [ ] Implement `supports_feature()` in all providers
- [ ] Add feature validation to `core/client.py`
- [ ] Implement extended thinking fallback (prompt engineering)
- [ ] Implement MCP graceful degradation
- [ ] Implement security wrapper for OpenAI
- [ ] Add feature requirement levels (REQUIRED/RECOMMENDED/OPTIONAL)
- [ ] Add error handling (`FeatureNotSupportedError`)
- [ ] Add provider selection guidance
- [ ] Write unit tests for feature detection
- [ ] Write integration tests for graceful degradation
- [ ] Update user documentation with provider comparison
- [ ] Add warning messages for missing recommended features

## Summary

The feature detection strategy provides:

1. **Extended Thinking Fallback**
   - Prompt engineering workaround (reduced quality, works everywhere)
   - Multi-pass reasoning (slower, more expensive)
   - Provider requirement (best quality, forces Claude)

2. **MCP Servers Fallback**
   - Custom MCP client for OpenAI (2-3 weeks effort)
   - Feature flags with graceful degradation (warn and continue)
   - Provider routing by MCP requirement (use Claude for MCP-dependent agents)

3. **Native Security Fallback**
   - Security wrapper layer for OpenAI (replicates Claude's security)
   - Phased implementation (file permissions first, sandbox later)

4. **Capability Flags**
   - Runtime feature checking via `supports_feature()`
   - Feature requirement levels (REQUIRED/RECOMMENDED/OPTIONAL)
   - Clear error messages and warnings

5. **Graceful Degradation**
   - Optional features: Silent skip or warning
   - Recommended features: Warn but continue
   - Required features: Fail with clear error message

6. **Provider Selection Guidance**
   - Decision tree for choosing providers
   - Configuration-based routing by agent type
   - User-facing recommendations and warnings

This ensures Auto Code works seamlessly across multiple providers while taking advantage of each provider's unique capabilities and providing clear guidance to users.
