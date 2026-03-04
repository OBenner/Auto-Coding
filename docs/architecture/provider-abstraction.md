# Provider Abstraction Layer

The **Provider Abstraction Layer** enables Auto Code to support multiple AI backends (Claude Agent SDK, LiteLLM, OpenRouter) through a unified interface. This architecture allows agent code to work with different AI providers without modification, while preserving each provider's unique capabilities.

## Overview

The provider abstraction layer solves the problem of vendor lock-in by defining a common interface for AI engine providers. Agents interact with `AIEngineProvider` instances rather than directly with specific SDKs, making it possible to swap between Claude, LiteLLM, and OpenRouter without changing agent code.

**Key benefits:**
- **Vendor independence**: Switch between AI providers by changing configuration
- **Consistent interface**: All providers implement the same `AIEngineProvider` contract
- **Feature detection**: Query providers for supported capabilities
- **Unified error handling**: Common exception hierarchy across providers
- **Extensibility**: Add new providers without modifying existing code

## Architecture

The provider system follows the **Adapter Pattern** and **Factory Pattern**:

```
core/providers/
├── __init__.py              # Public API exports (factory, exceptions)
├── base.py                  # Abstract base classes (AIEngineProvider, AgentSession)
├── config.py                # ProviderConfig dataclass with environment loading
├── factory.py               # Provider factory functions
├── exceptions.py            # Provider exception hierarchy
└── adapters/                # Provider implementations
    ├── claude.py            # Claude Agent SDK adapter
    ├── litellm.py           # LiteLLM adapter (100+ LLMs)
    └── openrouter.py        # OpenRouter adapter (400+ models)
```

**Design patterns:**
- **Abstract Factory**: `create_engine_provider()` instantiates providers based on config
- **Adapter Pattern**: Each adapter wraps a specific SDK to implement `AIEngineProvider`
- **Template Method**: Base class defines interface, adapters provide implementation
- **Strategy Pattern**: Runtime selection of provider strategy

## Core Interfaces

### AIEngineProvider (Abstract Base Class)

The `AIEngineProvider` abstract base class defines the contract that all providers must implement:

```python
class AIEngineProvider(ABC):
    """Abstract base class for AI engine providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'claude', 'litellm', 'openrouter')."""
        pass

    @abstractmethod
    def create_session(self, config: SessionConfig) -> AgentSession:
        """Create a new agent session.

        Args:
            config: Session configuration including system prompt, model, etc.

        Returns:
            AgentSession instance for interacting with the agent

        Raises:
            ProviderError: If session creation fails
            ProviderConfigError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Args:
            message: The message to send to the AI

        Yields:
            Response chunks as they are received

        Raises:
            ProviderError: If message sending fails
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Return list of supported model identifiers.

        Returns:
            List of model names/identifiers this provider supports
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration.

        Checks that all required credentials and settings are present.

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    def health_check(self) -> bool:
        """Check if provider is healthy and can accept requests.

        Default implementation just validates config.
        Subclasses can override to add connectivity checks.

        Returns:
            True if provider is healthy
        """
        return self.validate_config()

    def close(self) -> None:
        """Clean up provider resources.

        Called when provider is no longer needed.
        Default implementation does nothing.
        Subclasses should override if they need cleanup.
        """
        pass
```

**Required methods:**
- `name` - Provider identifier
- `create_session()` - Initialize agent session with configuration
- `send_message()` - Send message and stream response chunks
- `get_supported_models()` - List available models
- `validate_config()` - Check credentials and settings

**Optional overrides:**
- `get_validation_errors()` - Detailed validation messages
- `health_check()` - Connectivity and availability checks
- `close()` - Resource cleanup

### AgentSession (Base Class)

`AgentSession` represents an active session with an AI provider. Each provider implements its own session subclass:

```python
class AgentSession:
    """Base class for agent sessions.

    Represents an active session with an AI provider.
    Subclasses implement provider-specific session handling.
    """

    def __init__(self, session_id: str, provider_name: str):
        """Initialize session.

        Args:
            session_id: Unique identifier for this session
            provider_name: Name of the provider (e.g., 'claude', 'litellm')
        """
        self.session_id = session_id
        self.provider_name = provider_name
        self._is_active = True

    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self._is_active

    def close(self) -> None:
        """Close the session."""
        self._is_active = False
```

**Session lifecycle:**
1. **Creation**: Provider creates session via `create_session()`
2. **Active**: Session is used for message exchanges
3. **Closed**: Session is closed when no longer needed

### SessionConfig (Dataclass)

`SessionConfig` holds configuration for creating agent sessions:

```python
@dataclass
class SessionConfig:
    """Configuration for creating an agent session."""

    name: str                                    # Session name/identifier
    system_prompt: str = ""                      # System prompt for the agent
    model: str | None = None                     # Model identifier (provider-specific)
    max_tokens: int | None = None                # Maximum tokens for responses
    temperature: float | None = None             # Temperature for generation
    tools: list[str] | None = None               # List of tools available to agent
    working_directory: str | None = None         # Working directory for file ops
    allowed_commands: list[str] | None = None    # Allowed bash commands
    extra: dict[str, Any] | None = None          # Provider-specific config
```

## Provider Adapters

### ClaudeAgentProvider

The **Claude Agent SDK adapter** wraps the existing `claude-agent-sdk` client:

```python
class ClaudeAgentProvider(AIEngineProvider):
    """Claude Agent SDK provider implementation.

    Wraps the existing create_client() function from core.client to implement
    the AIEngineProvider interface.
    """

    def __init__(self, config: ProviderConfig):
        """Initialize Claude provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._active_session: ClaudeAgentSession | None = None

    def create_session(
        self,
        config: SessionConfig,
        project_dir: Path | None = None,
        spec_dir: Path | None = None,
        agent_type: str = "coder",
        max_thinking_tokens: int | None = None,
        output_format: dict | None = None,
        agents: dict | None = None,
    ) -> ClaudeAgentSession:
        """Create a new Claude agent session.

        Uses the existing create_client() function from core.client.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)
            project_dir: Working directory for the agent (required)
            spec_dir: Spec directory for this session (required)
            agent_type: Agent type identifier (e.g., 'coder', 'planner', 'qa_reviewer')
            max_thinking_tokens: Token budget for extended thinking
            output_format: Optional structured output format
            agents: Optional dict of subagent definitions

        Returns:
            ClaudeAgentSession wrapping the SDK client
        """
        # Delegates to core.client.create_client()
        from core.client import create_client

        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=config.model,
            agent_type=agent_type,
            max_thinking_tokens=max_thinking_tokens,
            output_format=output_format,
            agents=agents,
        )

        return ClaudeAgentSession(config.name, client, project_dir, spec_dir)
```

**Key characteristics:**
- **Preserves existing functionality**: Uses `core.client.create_client()` internally
- **Full agentic capabilities**: Built-in MCP, security hooks, tool permissions
- **OAuth authentication**: Token management via `core.auth`
- **Extended thinking**: Native support for thinking blocks
- **Session management**: Handled by Claude SDK

### LiteLLMProvider

The **LiteLLM adapter** provides access to 100+ LLMs through a unified API:

```python
class LiteLLMProvider(AIEngineProvider):
    """LiteLLM provider implementation.

    Provides access to 100+ LLMs through the LiteLLM unified API.
    Supports OpenAI, Anthropic, Google, Azure, AWS Bedrock, and more.
    """

    def create_session(self, config: SessionConfig) -> LiteLLMSession:
        """Create a new LiteLLM session.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)

        Returns:
            LiteLLMSession for interacting with the LLM
        """
        # Stateful session (LiteLLM is stateless)
        session = LiteLLMSession(
            session_id=session_id,
            model=model,
            system_prompt=config.system_prompt,
            api_base=api_base,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        return session

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response."""
        async for chunk in self._active_session.complete(message, stream=True):
            yield chunk
```

**Key characteristics:**
- **Stateful sessions**: Maintains conversation history in memory
- **100+ models**: OpenAI, Anthropic, Google, Azure, Bedrock, Ollama, etc.
- **Simple API**: Unified chat completions interface
- **No built-in agentic features**: Requires external orchestration

## Factory Pattern

### Provider Factory

The `create_engine_provider()` factory function instantiates providers based on configuration:

```python
def create_engine_provider(config: ProviderConfig) -> AIEngineProvider:
    """
    Create an AI engine provider based on configuration.

    This is the main factory function for creating providers. It dispatches
    to the appropriate provider constructor based on config.provider.

    Args:
        config: ProviderConfig with provider selection and settings

    Returns:
        AIEngineProvider instance for the configured provider

    Raises:
        ProviderNotInstalled: If required packages are missing
        ProviderError: If provider creation fails or unknown provider

    Example:
        from core.providers import create_engine_provider
        from core.providers.config import ProviderConfig

        # Create provider from environment
        config = ProviderConfig.from_env()
        provider = create_engine_provider(config)

        # Create session
        session = provider.create_session(session_config)
    """
    provider = config.provider

    if provider == "claude":
        return _create_claude_provider(config)
    elif provider == "litellm":
        return _create_litellm_provider(config)
    elif provider == "openrouter":
        return _create_openrouter_provider(config)
    else:
        raise ProviderError(f"Unknown AI engine provider: {provider}")
```

**Factory benefits:**
- **Single entry point**: Consistent provider instantiation
- **Lazy imports**: Provider-specific packages imported only when needed
- **Error handling**: Clear error messages for missing dependencies
- **Extensibility**: Add new providers by adding factory functions

## Configuration System

### ProviderConfig

`ProviderConfig` is a dataclass that holds configuration for all providers:

```python
@dataclass
class ProviderConfig:
    """Configuration for AI engine provider selection."""

    # Core settings
    provider: str = DEFAULT_PROVIDER  # "claude", "litellm", or "openrouter"

    # Claude Agent SDK settings
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"

    # LiteLLM settings
    litellm_model: str = ""
    litellm_api_base: str = ""
    litellm_api_key: str = ""

    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        """Create config from environment variables."""
        provider = os.environ.get("AI_ENGINE_PROVIDER", DEFAULT_PROVIDER).lower()
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        claude_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
        # ... (load all settings from environment)
        return cls(provider=provider, anthropic_api_key=anthropic_api_key, ...)

    def is_valid(self) -> bool:
        """Check if config has minimum required values for selected provider."""
        if self.provider == "claude":
            return bool(self.anthropic_api_key)
        elif self.provider == "litellm":
            return bool(self.litellm_model)
        elif self.provider == "openrouter":
            return bool(self.openrouter_api_key)
        return False
```

**Environment variables:**

```bash
# Provider selection
AI_ENGINE_PROVIDER=claude  # or "litellm", "openrouter"

# Claude Agent SDK
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# LiteLLM
LITELLM_MODEL=gpt-4
LITELLM_API_BASE=https://api.openai.com/v1
LITELLM_API_KEY=sk-...

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-sonnet-4
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## Exception Hierarchy

All provider exceptions inherit from `ProviderError`:

```python
class ProviderError(Exception):
    """Base exception for all provider errors."""
    pass

class ProviderNotInstalled(ProviderError):
    """Raised when required packages for a provider are not installed."""
    pass

class ProviderConfigError(ProviderError):
    """Raised when provider configuration is invalid or missing."""
    pass
```

**Exception handling pattern:**

```python
from core.providers import create_engine_provider, ProviderError, ProviderNotInstalled

try:
    config = ProviderConfig.from_env()
    provider = create_engine_provider(config)
    session = provider.create_session(session_config)
except ProviderNotInstalled as e:
    print(f"Missing dependencies: {e}")
    print("Install required packages for this provider")
except ProviderConfigError as e:
    print(f"Configuration error: {e}")
    print("Check environment variables and credentials")
except ProviderError as e:
    print(f"Provider error: {e}")
```

## Usage Examples

### Basic Provider Usage

```python
from core.providers import create_engine_provider
from core.providers.config import ProviderConfig
from core.providers.base import SessionConfig

# Load configuration from environment
config = ProviderConfig.from_env()

# Create provider instance
provider = create_engine_provider(config)

# Validate configuration
if not provider.validate_config():
    errors = provider.get_validation_errors()
    for error in errors:
        print(f"Config error: {error}")
    exit(1)

# Create session
session_config = SessionConfig(
    name="coder-session",
    system_prompt="You are an expert Python developer.",
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
)

session = provider.create_session(session_config)

# Send message and stream response
async for chunk in provider.send_message("Write a hello world function"):
    print(chunk, end="")
```

### Provider Switching

```python
import os
from core.providers import create_engine_provider
from core.providers.config import ProviderConfig

# Switch provider via environment variable
os.environ["AI_ENGINE_PROVIDER"] = "litellm"
os.environ["LITELLM_MODEL"] = "gpt-4"

# Code remains unchanged - provider is switched by configuration
config = ProviderConfig.from_env()
provider = create_engine_provider(config)

# Same agent code works with different provider
session = provider.create_session(session_config)
```

### Custom Provider Implementation

To add a new provider, implement the `AIEngineProvider` interface:

```python
from core.providers.base import AIEngineProvider, SessionConfig, AgentSession
from collections.abc import AsyncIterator

class CustomProvider(AIEngineProvider):
    """Custom AI provider implementation."""

    @property
    def name(self) -> str:
        return "custom"

    def create_session(self, config: SessionConfig) -> AgentSession:
        """Create custom provider session."""
        # Initialize provider-specific client
        client = CustomClient(api_key=self._config.api_key)
        return CustomSession(session_id, client)

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send message to custom provider."""
        if not self._active_session:
            raise ProviderError("No active session")

        response = await self._active_session.client.chat(message)
        for chunk in response.stream():
            yield chunk

    def get_supported_models(self) -> list[str]:
        """Return supported models."""
        return ["custom-model-1", "custom-model-2"]

    def validate_config(self) -> bool:
        """Validate configuration."""
        return bool(self._config.api_key)

# Register in factory.py
def _create_custom_provider(config: ProviderConfig) -> AIEngineProvider:
    """Create custom provider."""
    return CustomProvider(config)

# Add to create_engine_provider()
def create_engine_provider(config: ProviderConfig) -> AIEngineProvider:
    if config.provider == "custom":
        return _create_custom_provider(config)
    # ... existing providers
```

## Benefits

### 1. Separation of Concerns

The provider abstraction separates **agent logic** from **AI backend details**:
- Agents work with generic `AIEngineProvider` interface
- Provider-specific details are encapsulated in adapters
- No agent code changes when switching providers

### 2. Maintainability

- **Single responsibility**: Each adapter handles one provider
- **Clear interfaces**: Base classes define contracts explicitly
- **Easy testing**: Mock `AIEngineProvider` for unit tests
- **Isolated changes**: Adding providers doesn't modify existing code

### 3. Extensibility

Adding a new provider requires:
1. Implement `AIEngineProvider` interface
2. Add factory function in `factory.py`
3. Update `ProviderConfig` with new provider's settings
4. Add environment variable documentation

No changes to agent code or existing providers.

### 4. Vendor Independence

Switch providers by changing configuration:
```bash
# Switch from Claude to LiteLLM
export AI_ENGINE_PROVIDER=litellm
export LITELLM_MODEL=gpt-4

# No code changes required
```

### 5. Unified Error Handling

All providers raise common exceptions:
- `ProviderError` - Base exception
- `ProviderNotInstalled` - Missing dependencies
- `ProviderConfigError` - Invalid configuration

Agent code handles errors consistently across providers.

## Testing

### Unit Testing Providers

```bash
# Run all provider tests
pytest tests/test_provider_factory.py -v

# Run specific provider test
pytest tests/test_claude_provider.py -v

# Run with coverage
pytest tests/ --cov=apps/backend/core/providers --cov-report=html
```

### Mocking Providers for Tests

```python
from unittest.mock import Mock, AsyncMock
from core.providers.base import AIEngineProvider

# Mock provider for testing agents
mock_provider = Mock(spec=AIEngineProvider)
mock_provider.name = "mock"
mock_provider.validate_config.return_value = True
mock_provider.get_supported_models.return_value = ["mock-model"]

mock_session = Mock()
mock_session.is_active = True
mock_provider.create_session.return_value = mock_session

async def mock_send_message(message: str):
    yield f"Mock response to: {message}"

mock_provider.send_message = mock_send_message
```

## Configuration Examples

### Claude Agent SDK (Default)

```bash
# .env
AI_ENGINE_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

### LiteLLM (OpenAI)

```bash
# .env
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
```

### LiteLLM (Google Gemini)

```bash
# .env
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=gemini/gemini-pro
GOOGLE_API_KEY=...
```

### OpenRouter

```bash
# .env
AI_ENGINE_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

## Related Documentation

- [Provider Factory Implementation](../apps/backend/core/providers/factory.py)
- [Claude Adapter](../apps/backend/core/providers/adapters/claude.py)
- [LiteLLM Adapter](../apps/backend/core/providers/adapters/litellm.py)
- [Provider Configuration](../apps/backend/core/providers/config.py)
- [Multi-Provider LLM Support Spec](../../.auto-claude/specs/171-codex-openai-integration-concept/spec.md)

## Future Enhancements

- [ ] Add Azure OpenAI provider adapter
- [ ] Add Google AI provider adapter
- [ ] Implement provider feature detection API
- [ ] Add provider fallback mechanism
- [ ] Support for provider-specific tools
- [ ] Runtime provider switching without restart
- [ ] Provider performance metrics and benchmarking

## Troubleshooting

### Issue: ProviderNotInstalled error

**Symptom:** `ProviderNotInstalled: LiteLLM adapter not installed`

**Solution:**
```bash
# Install required provider packages
pip install litellm  # for LiteLLM provider
pip install openai   # for OpenRouter provider
```

### Issue: ProviderConfigError validation fails

**Symptom:** `ProviderConfigError: Claude provider requires ANTHROPIC_API_KEY`

**Solution:** Set required environment variables in `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> apps/backend/.env
```

### Issue: Session creation fails

**Symptom:** `ProviderError: Failed to create session`

**Solution:** Check provider-specific requirements:
- **Claude**: Ensure `project_dir` and `spec_dir` are provided
- **LiteLLM**: Ensure `LITELLM_MODEL` is set
- **OpenRouter**: Ensure `OPENROUTER_API_KEY` is valid

---

**Document Version:** 1.0
**Last Updated:** 2025-02-16
**Maintainer:** Auto Code Core Team
