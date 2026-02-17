# Feature Detection API

## Overview

The **Feature Detection API** enables providers to advertise their capabilities, allowing the Auto-Code system to:
- Query providers for supported features before using them
- Gracefully degrade when features are unavailable
- Choose appropriate providers based on required capabilities
- Provide clear error messages when features are requested but unsupported

This is critical for multi-provider support because different AI providers have varying capabilities:
- **Claude SDK**: Native extended thinking, MCP servers, security hooks
- **OpenAI**: Function calling, streaming (no native MCP or extended thinking)
- **LiteLLM**: Varies by underlying model
- **OpenRouter**: Varies by underlying model

## Design Goals

1. **Explicit capability advertisement** - Providers declare what they support
2. **Type-safe feature enumeration** - Use enum, not string literals
3. **Graceful degradation** - System can fallback or skip unsupported features
4. **Performance** - Feature checks are fast (cached, no API calls)
5. **Extensibility** - New features can be added without breaking existing code

## ProviderFeature Enum

Defines all features that may vary between providers:

```python
from enum import Enum

class ProviderFeature(Enum):
    """Features that may vary between AI providers.

    Each provider implements supports_feature() to return True/False
    for each feature. This enables runtime capability detection.
    """

    # Reasoning & Context
    EXTENDED_THINKING = "extended_thinking"
    """Native support for extended thinking (Claude's thinking tokens).

    Claude SDK: Supported via max_thinking_tokens parameter
    OpenAI: Not supported (requires prompt engineering workaround)
    LiteLLM: Varies by model
    """

    # Tool & Integration Capabilities
    MCP_SERVERS = "mcp_servers"
    """Native MCP (Model Context Protocol) server integration.

    Claude SDK: Built-in MCP server support
    OpenAI: No native support (requires custom MCP client)
    LiteLLM: No native support
    """

    FUNCTION_CALLING = "function_calling"
    """Structured tool/function calling capabilities.

    Claude SDK: Tool use with input_schema
    OpenAI: Function calling with parameters
    LiteLLM: Varies by model
    """

    # Security Features
    NATIVE_SECURITY = "native_security"
    """Built-in security hooks and sandbox enforcement.

    Claude SDK: PreToolUse hooks, sandbox, file permissions
    OpenAI: No native security (requires wrapper layer)
    LiteLLM: No native security
    """

    # Communication Features
    STREAMING_RESPONSES = "streaming_responses"
    """Streaming token-by-token responses.

    Claude SDK: Supported
    OpenAI: Supported
    LiteLLM: Varies by model
    """

    # Session Management
    SESSION_MANAGEMENT = "session_management"
    """Stateful session management with conversation history.

    Claude SDK: Stateful sessions with history
    OpenAI: Stateless API (manual history management)
    LiteLLM: Stateless (manual history management)
    """

    # Advanced Features
    STRUCTURED_OUTPUT = "structured_output"
    """Native JSON/structured output generation.

    Claude SDK: Supported via output_format parameter
    OpenAI: Supported via response_format parameter
    LiteLLM: Varies by model
    """

    PARALLEL_AGENT_EXECUTION = "parallel_agent_execution"
    """Native support for spawning parallel subagents.

    Claude SDK: Supported via agents parameter
    OpenAI: Not supported (manual implementation)
    LiteLLM: Not supported
    """
```

## API Methods

### AIEngineProvider.supports_feature()

Add to the `AIEngineProvider` abstract base class:

```python
class AIEngineProvider(ABC):
    # ... existing methods ...

    def supports_feature(self, feature: ProviderFeature) -> bool:
        """Check if provider supports a specific feature.

        Default implementation returns False for all features.
        Subclasses should override to advertise their capabilities.

        Args:
            feature: ProviderFeature enum value to check

        Returns:
            True if provider supports the feature, False otherwise

        Example:
            >>> provider = create_engine_provider(config)
            >>> if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
            ...     session = provider.create_session(
            ...         config.with_extended_thinking(max_tokens=10000)
            ...     )
            ... else:
            ...     # Use alternative approach
            ...     session = provider.create_session(config)
        """
        return False  # Default: no features supported
```

### Provider Implementations

Each provider overrides `supports_feature()` to advertise its capabilities:

#### Claude Provider

```python
class ClaudeAgentProvider(AIEngineProvider):
    # Feature capability cache (computed once)
    _FEATURES = {
        ProviderFeature.EXTENDED_THINKING: True,
        ProviderFeature.MCP_SERVERS: True,
        ProviderFeature.NATIVE_SECURITY: True,
        ProviderFeature.STREAMING_RESPONSES: True,
        ProviderFeature.FUNCTION_CALLING: True,
        ProviderFeature.SESSION_MANAGEMENT: True,
        ProviderFeature.STRUCTURED_OUTPUT: True,
        ProviderFeature.PARALLEL_AGENT_EXECUTION: True,
    }

    def supports_feature(self, feature: ProviderFeature) -> bool:
        """Claude SDK supports all features."""
        return self._FEATURES.get(feature, False)
```

#### OpenAI Provider (Future)

```python
class OpenAIAgentProvider(AIEngineProvider):
    _FEATURES = {
        ProviderFeature.EXTENDED_THINKING: False,  # Not supported
        ProviderFeature.MCP_SERVERS: False,  # Requires custom client
        ProviderFeature.NATIVE_SECURITY: False,  # Requires wrapper
        ProviderFeature.STREAMING_RESPONSES: True,
        ProviderFeature.FUNCTION_CALLING: True,
        ProviderFeature.SESSION_MANAGEMENT: False,  # Stateless API
        ProviderFeature.STRUCTURED_OUTPUT: True,  # response_format
        ProviderFeature.PARALLEL_AGENT_EXECUTION: False,  # Manual
    }

    def supports_feature(self, feature: ProviderFeature) -> bool:
        """OpenAI has limited feature support."""
        return self._FEATURES.get(feature, False)
```

#### LiteLLM Provider

```python
class LiteLLMProvider(AIEngineProvider):
    # LiteLLM capabilities vary by model
    def supports_feature(self, feature: ProviderFeature) -> bool:
        """Check feature support based on underlying model.

        LiteLLM is a proxy to 100+ models, so capabilities vary.
        We detect model type and return appropriate flags.
        """
        model = self._config.model or "unknown"

        # All LiteLLM models support streaming
        if feature == ProviderFeature.STREAMING_RESPONSES:
            return True

        # All LiteLLM models support function calling (OpenAI-compatible)
        if feature == ProviderFeature.FUNCTION_CALLING:
            return True

        # Claude models via LiteLLM support structured output
        if feature == ProviderFeature.STRUCTURED_OUTPUT:
            return model.startswith("claude-")

        # No native support for these features
        if feature in [
            ProviderFeature.EXTENDED_THINKING,
            ProviderFeature.MCP_SERVERS,
            ProviderFeature.NATIVE_SECURITY,
            ProviderFeature.SESSION_MANAGEMENT,
            ProviderFeature.PARALLEL_AGENT_EXECUTION,
        ]:
            return False

        return False
```

## Usage Patterns

### Pattern 1: Feature-Guarded Code

Execute different code paths based on feature availability:

```python
# Agent creating a session
provider = create_engine_provider(config)

if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
    # Use extended thinking for complex reasoning
    session = provider.create_session(
        SessionConfig(
            name="planner",
            extra={"max_thinking_tokens": 16000}
        )
    )
else:
    # Fallback: Use regular mode
    session = provider.create_session(
        SessionConfig(name="planner")
    )
    logger.warning(
        f"Provider {provider.name} does not support extended thinking. "
        "Using standard mode."
    )
```

### Pattern 2: Feature Requirement Validation

Validate that required features are present before proceeding:

```python
def run_complex_task(provider: AIEngineProvider) -> None:
    """Run a task requiring specific features."""
    required_features = [
        ProviderFeature.EXTENDED_THINKING,
        ProviderFeature.MCP_SERVERS,
        ProviderFeature.NATIVE_SECURITY,
    ]

    missing = [
        f.value for f in required_features
        if not provider.supports_feature(f)
    ]

    if missing:
        raise ProviderError(
            f"Provider {provider.name} does not support required features: "
            f"{', '.join(missing)}. "
            f"Consider using Claude provider for this task."
        )

    # Proceed with task
    ...
```

### Pattern 3: Provider Selection by Feature

Choose provider based on required capabilities:

```python
def select_provider_for_task(required_features: list[ProviderFeature]) -> str:
    """Select a provider that supports all required features."""
    providers_config = {
        "claude": ClaudeAgentProvider.config,
        "openai": OpenAIAgentProvider.config,
        "litellm": LiteLLMProvider.config,
    }

    for provider_name, config in providers_config.items():
        provider = create_engine_provider(config)

        if all(provider.supports_feature(f) for f in required_features):
            return provider_name

    # No provider supports all features
    raise ProviderError(
        f"No provider supports all required features: "
        f"{[f.value for f in required_features]}"
    )

# Usage
provider_name = select_provider_for_task([
    ProviderFeature.EXTENDED_THINKING,
    ProviderFeature.MCP_SERVERS,
])
# Returns: "claude" (only provider with both features)
```

### Pattern 4: Graceful Degradation

Skip optional features if unsupported:

```python
def create_session_with_optional_features(
    provider: AIEngineProvider,
    required_config: SessionConfig,
    optional_thinking: bool = False,
    optional_mcp: bool = False,
) -> AgentSession:
    """Create session, using optional features if available."""

    # Optional: Extended thinking
    if optional_thinking and provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        required_config.extra["max_thinking_tokens"] = 10000
        logger.info("Extended thinking enabled")
    else:
        logger.info("Extended thinking not supported or not requested")

    # Optional: MCP servers
    if optional_mcp and provider.supports_feature(ProviderFeature.MCP_SERVERS):
        required_config.extra["enable_mcp"] = True
        logger.info("MCP servers enabled")
    else:
        logger.info("MCP servers not supported or not requested")

    return provider.create_session(required_config)
```

## Feature Compatibility Matrix

| Feature | Claude | OpenAI | LiteLLM | OpenRouter |
|---------|--------|--------|---------|------------|
| `EXTENDED_THINKING` | ✅ Native | ❌ None | ❌ None | ❌ None |
| `MCP_SERVERS` | ✅ Built-in | ❌ Custom | ❌ None | ❌ None |
| `NATIVE_SECURITY` | ✅ Built-in | ❌ Wrapper | ❌ None | ❌ None |
| `STREAMING_RESPONSES` | ✅ Yes | ✅ Yes | ✅ Most | ✅ Most |
| `FUNCTION_CALLING` | ✅ Tools | ✅ Functions | ✅ Varies | ✅ Varies |
| `SESSION_MANAGEMENT` | ✅ Stateful | ❌ Stateless | ❌ Stateless | ❌ Stateless |
| `STRUCTURED_OUTPUT` | ✅ Yes | ✅ Yes | ✅ Claude only | ✅ Claude only |
| `PARALLEL_AGENT_EXECUTION` | ✅ Native | ❌ Manual | ❌ None | ❌ None |

**Legend:**
- ✅ Native: Built-in support, no adapter code needed
- ❌ None: Not supported, requires significant workaround
- ✅ Custom: Supported but requires custom implementation
- ✅ Varies: Depends on underlying model
- ❌ Wrapper: Can be added via security wrapper layer
- ❌ Manual: Must be implemented in application code

## Implementation Checklist

For the feature detection API to be complete:

- [ ] Add `ProviderFeature` enum to `core/providers/base.py`
- [ ] Add `supports_feature()` method to `AIEngineProvider` base class
- [ ] Implement `supports_feature()` in `ClaudeAgentProvider`
- [ ] Implement `supports_feature()` in `OpenAIAgentProvider` (when created)
- [ ] Implement `supports_feature()` in `LiteLLMProvider` (model-dependent)
- [ ] Add feature detection tests to provider test suite
- [ ] Update documentation with provider-specific feature support
- [ ] Add feature validation to provider factory

## Testing

### Unit Tests

```python
def test_claude_feature_support():
    """Claude provider should support all features."""
    provider = ClaudeAgentProvider(config)
    assert provider.supports_feature(ProviderFeature.EXTENDED_THINKING)
    assert provider.supports_feature(ProviderFeature.MCP_SERVERS)
    assert provider.supports_feature(ProviderFeature.NATIVE_SECURITY)
    assert provider.supports_feature(ProviderFeature.STREAMING_RESPONSES)
    assert provider.supports_feature(ProviderFeature.FUNCTION_CALLING)
    assert provider.supports_feature(ProviderFeature.SESSION_MANAGEMENT)

def test_openai_feature_support():
    """OpenAI provider should have limited feature support."""
    provider = OpenAIAgentProvider(config)
    assert not provider.supports_feature(ProviderFeature.EXTENDED_THINKING)
    assert not provider.supports_feature(ProviderFeature.MCP_SERVERS)
    assert not provider.supports_feature(ProviderFeature.NATIVE_SECURITY)
    assert provider.supports_feature(ProviderFeature.STREAMING_RESPONSES)
    assert provider.supports_feature(ProviderFeature.FUNCTION_CALLING)
    assert not provider.supports_feature(ProviderFeature.SESSION_MANAGEMENT)

def test_feature_guarded_code():
    """Test feature-guarde d code paths."""
    provider = create_engine_provider(config)

    if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        # Should execute for Claude
        assert provider.name == "claude"
    else:
        # Should execute for OpenAI/LiteLLM
        assert provider.name in ["openai", "litellm"]
```

### Integration Tests

```python
def test_session_creation_with_extended_thinking():
    """Create session with extended thinking if supported."""
    provider = create_engine_provider(config)

    if provider.supports_feature(ProviderFeature.EXTENDED_THINKING):
        session = provider.create_session(
            SessionConfig(
                name="test",
                extra={"max_thinking_tokens": 5000}
            )
        )
        assert session is not None
    else:
        # Should not raise error, just skip feature
        session = provider.create_session(SessionConfig(name="test"))
        assert session is not None
```

## Error Handling

### FeatureNotSupportedError

Raised when code attempts to use an unsupported feature:

```python
class FeatureNotSupportedError(ProviderError):
    """Raised when attempting to use an unsupported feature."""

    def __init__(self, provider_name: str, feature: ProviderFeature):
        self.provider_name = provider_name
        self.feature = feature
        super().__init__(
            f"Provider '{provider_name}' does not support feature: {feature.value}. "
            f"Consider using a different provider or disabling this feature."
        )
```

### Usage Example

```python
def require_feature(provider: AIEngineProvider, feature: ProviderFeature) -> None:
    """Raise error if feature not supported."""
    if not provider.supports_feature(feature):
        raise FeatureNotSupportedError(provider.name, feature)

# Usage
provider = create_engine_provider(config)
require_feature(provider, ProviderFeature.MCP_SERVERS)
# Proceed with MCP-specific code
```

## Migration Path

### Phase 1: Add Feature Detection (This Task)

1. Add `ProviderFeature` enum to `base.py`
2. Add `supports_feature()` method to `AIEngineProvider`
3. Implement in existing providers (Claude, LiteLLM)
4. Add unit tests

### Phase 2: Use Feature Detection in Agent Code

1. Update agent code to check features before using them
2. Add feature-guarde d code paths
3. Update error messages to suggest alternative providers

### Phase 3: OpenAI Provider Integration

1. Implement OpenAI provider with accurate feature flags
2. Add security wrapper to provide NATIVE_SECURITY feature
3. Implement custom MCP client for MCP_SERVERS feature

## Best Practices

### DO

✅ Check features before using them
✅ Provide clear fallbacks for unsupported features
✅ Log warnings when features are unavailable
✅ Document which features are required vs. optional
✅ Use feature constants (ProviderFeature enum), not strings

### DON'T

❌ Assume all providers support the same features
❌ Silently skip required features without logging
❌ Use string literals for feature names
❌ Check features multiple times (cache the result)
❌ Throw errors for optional features (use graceful degradation)

## Performance Considerations

1. **Feature checks are fast** - No API calls, just dictionary lookup
2. **Cache feature support** - Providers use `_FEATURES` dict for O(1) lookup
3. **Check once, use many times** - Don't check in loops
4. **Lazy evaluation** - Only check features when actually needed

Example:

```python
# ❌ BAD: Checks feature in loop
for i in range(100):
    if provider.supports_feature(ProviderFeature.STREAMING):
        process_streaming()

# ✅ GOOD: Check once before loop
supports_streaming = provider.supports_feature(ProviderFeature.STREAMING)
if supports_streaming:
    for i in range(100):
        process_streaming()
```

## Future Extensions

### Version-Dependent Features

Future versions may need to check feature versions:

```python
class ProviderFeature(Enum):
    EXTENDED_THINKING = "extended_thinking"
    EXTENDED_THINKING_V2 = "extended_thinking_v2"  # Future

def supports_feature_version(
    self,
    feature: ProviderFeature,
    min_version: str | None = None
) -> bool:
    """Check feature support with optional version requirement."""
    if not self.supports_feature(feature):
        return False

    if min_version:
        return self._get_feature_version(feature) >= min_version

    return True
```

### Dynamic Feature Detection

Some features may require runtime detection (API calls):

```python
async def detect_model_capabilities(self, model: str) -> set[ProviderFeature]:
    """Detect model capabilities via API call to provider."""
    # Call provider's models API to get capabilities
    # Cache result for future use
    pass
```

## Summary

The Feature Detection API provides:
- **Type-safe feature enumeration** via `ProviderFeature` enum
- **Runtime capability checking** via `supports_feature()` method
- **Graceful degradation** for unsupported features
- **Clear error messages** when features are required but unavailable
- **Performance** via cached feature support (O(1) lookup)
- **Extensibility** for new features and providers

This enables Auto-Code to work seamlessly across different AI providers while taking advantage of each provider's unique capabilities.
