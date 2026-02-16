# OpenAI Adapter Design

## Overview

This document describes the design of the `OpenAIProvider` adapter class that extends the `AIEngineProvider` base class. The adapter follows the same patterns as the existing `LiteLLMProvider` and `OpenRouterProvider` adapters, providing a consistent interface for using OpenAI's GPT models alongside Claude, LiteLLM, and OpenRouter providers.

**Note:** The standalone CODEX API was deprecated in March 2023. Modern code generation uses GPT models through the Chat Completions API.

## Architecture

The OpenAI adapter consists of two main classes:

1. **`OpenAISession`** - Manages individual conversation sessions with OpenAI
2. **`OpenAIProvider`** - Factory for creating sessions and managing provider-level operations

### Class Hierarchy

```
AIEngineProvider (abstract base)
└── OpenAIProvider
    └── Creates: OpenAISession instances
        └── AgentSession (base)
```

## Session Management

### OpenAISession Class

The `OpenAISession` class manages conversation history and provides the message sending interface for OpenAI. Unlike the Claude SDK (which is stateful), OpenAI's API is stateless, so we maintain conversation state in the session object.

**Key Responsibilities:**
- Maintain conversation history (messages list)
- Manage session lifecycle (active/closed state)
- Handle message addition (user/assistant)
- Provide async streaming completion
- Support optional system prompts

**Session Lifecycle:**
1. **Creation**: `OpenAIProvider.create_session()` initializes a new session
2. **Active**: Session can send/receive messages
3. **Closed**: `session.close()` marks session as inactive, clears history

**State Management:**
```python
class OpenAISession(AgentSession):
    def __init__(self, session_id, model, api_key, system_prompt="", ...):
        super().__init__(session_id, provider_name="openai")
        self._model = model              # Model identifier
        self._api_key = api_key          # OpenAI API key
        self._messages = []              # Conversation history
        self._client = None              # Lazy-loaded AsyncOpenAI client
```

**Message History:**
- Messages are stored in OpenAI Chat Completions API format:
  ```python
  [
      {"role": "system", "content": "You are an expert developer."},
      {"role": "user", "content": "Write hello world in Python"},
      {"role": "assistant", "content": "Here's the code..."}
  ]
  ```
- System prompt is added as the first message if provided
- History grows with each exchange (user message → assistant response)
- `clear_history(keep_system=True)` clears conversation while preserving system prompt

## Message Streaming

### Async Streaming Interface

The `OpenAISession.complete()` method provides async streaming responses, matching the pattern used by LiteLLM and OpenRouter adapters.

**Streaming Flow:**
```python
async def complete(self, message: str, stream: bool = True) -> AsyncIterator[str]:
    # 1. Add user message to history
    self.add_user_message(message)

    # 2. Build completion kwargs
    completion_kwargs = {
        "model": self._model,
        "messages": self._messages,
        "stream": stream,
    }

    # 3. Call OpenAI API
    response = await client.chat.completions.create(**completion_kwargs)

    # 4. Stream chunks
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

    # 5. Add full assistant response to history
    self.add_assistant_message(full_response)
```

**Streaming Implementation Details:**
- Uses `openai.AsyncOpenAI` client for async operations
- Yields text chunks as they arrive from OpenAI
- Accumulates full response for history tracking
- Supports both streaming (`stream=True`) and non-streaming modes
- Raises `ProviderError` on API failures

**Error Handling:**
- Catches OpenAI API exceptions and wraps in `ProviderError`
- Validates session is active before sending
- Returns `ProviderNotInstalled` if `openai` package not installed

## Model Listing

### Supported OpenAI Models

The adapter provides a curated list of commonly used OpenAI models for code generation and development tasks.

**Model Categories:**

| Category | Models | Use Case |
|----------|--------|----------|
| **Flagship** | `gpt-5.2`, `gpt-5` | Complex reasoning, architecture design |
| **Standard** | `gpt-4o`, `gpt-4o-mini` | General-purpose code generation |
| **Legacy** | `gpt-4-turbo`, `gpt-4` | Compatibility with existing code |

**Default Models:**
```python
DEFAULT_OPENAI_MODEL = "gpt-5.2"  # Best for complex tasks
OPENAI_MODELS = [
    # Current flagship models
    "gpt-5.2",
    "gpt-5",
    # GPT-4o family
    "gpt-4o",
    "gpt-4o-mini",
    # Legacy models
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]
```

**Model Selection Strategy:**
- Models can be specified via:
  1. Environment variable: `OPENAI_MODEL`
  2. Session config: `SessionConfig(model="gpt-5.2")`
  3. Extra config: `SessionConfig(extra={"model": "gpt-4o"})`
- Provider config serves as default: `ProviderConfig.openai_model`
- Session config takes precedence over provider config

## Feature Detection

### Provider Capabilities

The OpenAI adapter implements feature detection to identify which capabilities are supported compared to Claude SDK.

**Feature Detection API:**
```python
class ProviderFeature(Enum):
    """Provider-specific features"""
    STREAMING_RESPONSES = "streaming_responses"
    FUNCTION_CALLING = "function_calling"
    SESSION_MANAGEMENT = "session_management"
    EXTENDED_THINKING = "extended_thinking"
    MCP_SERVERS = "mcp_servers"
    NATIVE_SECURITY = "native_security"
```

**OpenAI Provider Capability Matrix:**

| Feature | Supported | Notes |
|---------|-----------|-------|
| `STREAMING_RESPONSES` | ✅ Yes | Full support via Chat Completions API |
| `FUNCTION_CALLING` | ✅ Yes | Via OpenAI function calling API |
| `SESSION_MANAGEMENT` | ✅ Yes | Custom session state management (not native) |
| `EXTENDED_THINKING` | ❌ No | Requires prompt engineering workaround |
| `MCP_SERVERS` | ❌ No | Requires custom MCP client implementation |
| `NATIVE_SECURITY` | ❌ No | Requires security wrapper layer |

**Feature Detection Implementation:**
```python
class OpenAIProvider(AIEngineProvider):
    def supports_feature(self, feature: ProviderFeature) -> bool:
        """Check if provider supports a specific feature."""
        feature_map = {
            ProviderFeature.STREAMING_RESPONSES: True,
            ProviderFeature.FUNCTION_CALLING: True,
            ProviderFeature.SESSION_MANAGEMENT: True,
            ProviderFeature.EXTENDED_THINKING: False,
            ProviderFeature.MCP_SERVERS: False,
            ProviderFeature.NATIVE_SECURITY: False,
        }
        return feature_map.get(feature, False)
```

**Capability Limitations & Workarounds:**

1. **Extended Thinking** (Not Supported):
   - **Limitation**: OpenAI has no native extended thinking feature
   - **Workaround**: Add "Think step-by-step" to system prompt
   - **Mitigation**: Use higher `max_tokens` allowance for complex reasoning

2. **MCP Servers** (Not Supported):
   - **Limitation**: OpenAI SDK has no MCP protocol support
   - **Workaround**: Custom MCP client implementation required
   - **Mitigation**: Translate MCP tools to OpenAI function calling format

3. **Native Security** (Not Supported):
   - **Limitation**: OpenAI API has no security hooks or sandbox
   - **Workaround**: Security wrapper layer applies Claude's security model
   - **Mitigation**: Implement pre/post tool execution hooks in wrapper

## Configuration

### Environment Variables

The OpenAI adapter uses the following environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-5.2` | Default model to use |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | API base URL (for Azure/custom endpoints) |

### Provider Configuration

The adapter integrates with the existing `ProviderConfig` dataclass:

```python
@dataclass
class ProviderConfig:
    # ... existing providers ...
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-5.2"
    openai_base_url: str = "https://api.openai.com/v1"
```

**Loading from Environment:**
```python
# In ProviderConfig.from_env()
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
openai_model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
```

### Session Configuration

Sessions are created using the `SessionConfig` dataclass:

```python
@dataclass
class SessionConfig:
    name: str                                    # Session name
    system_prompt: str = ""                      # System prompt
    model: str | None = None                     # Model (overrides provider default)
    max_tokens: int | None = None                # Max tokens for response
    temperature: float | None = None             # Temperature for generation
    tools: list[str] | None = None               # Available tools
    working_directory: str | None = None         # Working directory
    allowed_commands: list[str] | None = None    # Allowed bash commands
    extra: dict[str, Any] | None = None          # Provider-specific config
```

**Example Usage:**
```python
from core.providers.adapters.openai import OpenAIProvider
from core.providers.config import ProviderConfig
from core.providers.base import SessionConfig

# Create provider
config = ProviderConfig.from_env()
provider = OpenAIProvider(config)

# Create session
session_config = SessionConfig(
    name="coder-session",
    system_prompt="You are an expert Python developer.",
    model="gpt-5.2",
    temperature=0.7,
    max_tokens=4096
)
session = provider.create_session(session_config)

# Send message and stream response
async for chunk in provider.send_message("Write a REST API with FastAPI"):
    print(chunk, end="")
```

## Provider Factory Integration

### AIEngineProvider Enum

The adapter integrates with the existing provider enumeration:

```python
class AIEngineProvider(str, Enum):
    """Supported AI engine providers."""
    CLAUDE = "claude"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"
    OPENAI = "openai"  # NEW
```

### Provider Factory Pattern

The `create_client()` function in `core/client.py` will be extended to support OpenAI:

```python
def create_client(project_dir: str, spec_dir: str, ...):
    """Create SDK client for specified provider."""
    config = ProviderConfig.from_env()

    if config.provider == AIEngineProvider.CLAUDE.value:
        return ClaudeSDKClient(...)
    elif config.provider == AIEngineProvider.OPENAI.value:
        return OpenAIProvider(config)
    elif config.provider == AIEngineProvider.LITELLM.value:
        return LiteLLMProvider(config)
    elif config.provider == AIEngineProvider.OPENROUTER.value:
        return OpenRouterProvider(config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
```

## Implementation Details

### OpenAISession Implementation

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `__init__()` | Initialize session with model, API key, system prompt |
| `add_user_message(content)` | Add user message to history |
| `add_assistant_message(content)` | Add assistant response to history |
| `complete(message, stream=True)` | Send message and stream response |
| `clear_history(keep_system=True)` | Clear conversation history |
| `close()` | Mark session as inactive, clear history |

**Client Lazy Loading:**
```python
def _get_client(self) -> AsyncOpenAI:
    """Get or create OpenAI client (lazy initialization)."""
    if self._client is None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
    return self._client
```

### OpenAIProvider Implementation

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `__init__(config)` | Initialize provider with configuration |
| `create_session(config)` | Create new OpenAI session |
| `send_message(message)` | Send message using active session |
| `get_supported_models()` | Return list of OpenAI models |
| `validate_config()` | Validate provider configuration |
| `health_check()` | Check if provider is available |
| `get_active_session()` | Get currently active session |
| `close()` | Clean up provider resources |

**Validation:**
```python
def validate_config(self) -> bool:
    """Validate provider configuration."""
    self._validation_errors = []

    if not self._config.openai_api_key:
        self._validation_errors.append(
            "OpenAI provider requires OPENAI_API_KEY environment variable"
        )
        return False

    return True
```

**Health Check:**
```python
def health_check(self) -> bool:
    """Check if provider is healthy."""
    if not self.validate_config():
        return False

    # Check if openai package is installed
    try:
        from openai import AsyncOpenAI
        return True
    except ImportError:
        self._validation_errors.append("openai package is not installed")
        return False
```

## Error Handling

### Exception Translation

The adapter translates OpenAI API errors to common provider exceptions:

| OpenAI Error | Translated To |
|--------------|---------------|
| `AuthenticationError` | `ProviderConfigError` |
| `RateLimitError` | `ProviderError` (with retry logic) |
| `APIConnectionError` | `ProviderError` (with retry logic) |
| `NotFoundError` | `ProviderError` |
| Generic exceptions | `ProviderError` |

**Error Handling Pattern:**
```python
try:
    response = await client.chat.completions.create(**kwargs)
    async for chunk in response:
        yield chunk.choices[0].delta.content
except AuthenticationError as e:
    raise ProviderConfigError(f"OpenAI API key invalid: {e}")
except RateLimitError as e:
    logger.warning(f"OpenAI rate limit: {e}")
    raise ProviderError(f"Rate limit exceeded: {e}")
except Exception as e:
    logger.error(f"OpenAI completion error: {e}")
    raise ProviderError(f"OpenAI completion failed: {e}") from e
```

## Dependency Requirements

### Required Packages

The OpenAI adapter requires the following package:

```
openai>=1.0.0
```

**Note:** The `openai` package is already listed in the project's `requirements.txt` for other integrations.

### Optional Dependencies

No optional dependencies required for basic functionality.

## Testing Strategy

### Unit Tests

Test coverage should include:

1. **Session Management**
   - Session creation and initialization
   - Message history management
   - Session lifecycle (active/closed)

2. **Message Streaming**
   - Async streaming responses
   - Non-streaming responses
   - Error handling

3. **Configuration**
   - Environment variable loading
   - Session config override
   - Validation

4. **Feature Detection**
   - Capability flags
   - Feature support queries

### Integration Tests

Test coverage should include:

1. **API Integration**
   - Real OpenAI API calls (with test API key)
   - Model listing
   - Message sending and streaming

2. **Error Scenarios**
   - Invalid API key
   - Rate limiting
   - Network failures

3. **Provider Interchangeability**
   - Switching between Claude and OpenAI
   - Same task, different provider
   - Output equivalence validation

## Migration Path

### From Claude to OpenAI

**For Users:**
1. Set `OPENAI_API_KEY` in `.env`
2. Set `AI_ENGINE_PROVIDER=openai`
3. Optionally set `OPENAI_MODEL=gpt-5.2`
4. Run agents normally (no code changes needed)

**For Developers:**
1. No changes required to agent code
2. Provider abstraction handles differences
3. Feature detection allows capability checks

### Backward Compatibility

- **Claude provider remains the default**
- Existing configurations continue to work
- No breaking changes to existing code
- OpenAI is opt-in via environment variable

## Security Considerations

### API Key Management

- API key stored in environment variable (never hardcoded)
- Key loaded via `ProviderConfig.from_env()`
- Key passed to OpenAI client (not logged or traced)

### Security Wrapper Integration

OpenAI provider requires security wrapper layer (designed in separate document) to provide:

1. **Filesystem Permissions** - Restrict file operations to project directory
2. **Command Allowlisting** - Filter bash commands based on project stack
3. **PreToolUse Hooks** - Validate tool calls before execution
4. **PostToolUse Hooks** - Audit tool results after execution

**Security Wrapper Application:**
```python
# Wrapper intercepts send_message calls
class SecurityWrapper:
    async def send_message(self, message: str) -> AsyncIterator[str]:
        # 1. Apply pre-execution hooks
        # 2. Enforce security policies
        # 3. Call OpenAI provider
        # 4. Validate tool calls
        # 5. Apply post-execution hooks
        async for chunk in self.provider.send_message(message):
            yield chunk
```

## Performance Considerations

### Latency Comparison

| Provider | Typical Latency | Notes |
|----------|----------------|-------|
| Claude | 2-4 seconds | Native agent orchestration |
| OpenAI | 1-3 seconds | Custom orchestration overhead |

### Token Limits

| Model | Context Window | Max Output |
|-------|---------------|------------|
| gpt-5.2 | TBD (est. 200K) | TBD (est. 8K) |
| gpt-5 | TBD (est. 128K) | TBD (est. 4K) |
| gpt-4o | 128K | 4K |

**Note:** Token limits should be verified during implementation as OpenAI's GPT-5 models may have different limits than shown here.

### Cost Optimization

**Model Selection Strategy:**
- Use `gpt-4o-mini` for simple tasks (lower cost, faster)
- Use `gpt-5` for medium complexity (balanced cost/performance)
- Use `gpt-5.2` for complex reasoning (higher cost, best quality)

**Caching Strategy:**
- Cache model list (doesn't change frequently)
- Reuse AsyncOpenAI client across requests
- Session history maintained in memory (no persistence needed)

## Future Enhancements

### Potential Improvements

1. **Custom Base URL Support**
   - Azure OpenAI endpoints
   - Custom proxy servers
   - Enterprise deployments

2. **Advanced Model Features**
   - Structured outputs (JSON mode)
   - Parallel function calling
   - Vision/multimodal capabilities

3. **Performance Optimizations**
   - Connection pooling
   - Request batching
   - Response caching

4. **Monitoring & Observability**
   - Token usage tracking
   - Cost estimation
   - Performance metrics

## Summary

The OpenAI adapter design follows the established patterns from LiteLLM and OpenRouter adapters, providing:

✅ **Consistent Interface** - Implements `AIEngineProvider` base class
✅ **Session Management** - Custom session state for stateless API
✅ **Async Streaming** - Full streaming response support
✅ **Model Listing** - Curated list of OpenAI models
✅ **Feature Detection** - Clear capability documentation
✅ **Error Handling** - Translated to common provider exceptions
✅ **Configuration** - Environment-based configuration
✅ **Factory Pattern** - Integrated with provider factory
✅ **Testing Strategy** - Unit and integration test coverage
✅ **Security Integration** - Designed for security wrapper layer

The adapter enables seamless switching between Claude and OpenAI providers without modifying agent code, while maintaining Auto Code's security model and agent orchestration features through additional layers (security wrapper, custom MCP client, tool schema translator).

## Next Steps

1. **Review** - Validate design against existing adapter patterns
2. **Implement** - Build OpenAISession and OpenAIProvider classes
3. **Test** - Unit tests for session management and streaming
4. **Integrate** - Add to provider factory and config
5. **Document** - Update user guide with OpenAI setup instructions
