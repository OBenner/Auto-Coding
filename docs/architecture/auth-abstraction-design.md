# Authentication Abstraction Design

## Overview

This document designs a unified authentication abstraction layer that supports both OAuth tokens (for Claude) and API keys (for OpenAI). The abstraction provides a consistent interface for credential management across multiple AI providers while maintaining backward compatibility with the existing Claude OAuth authentication system.

**Context**: Auto Code currently uses Claude Code OAuth tokens exclusively. Adding OpenAI support requires API key authentication. This design unifies both approaches under a single abstraction layer.

## Current Authentication Architecture

### Claude-Only Authentication (`core/auth.py`)

**Key Functions**:

```python
# From core/auth.py (lines 558-599)
def get_auth_token(config_dir: str | None = None) -> str | None:
    """
    Get authentication token from environment variables or credential store.

    Checks multiple sources in priority order:
    1. CLAUDE_CODE_OAUTH_TOKEN (env var)
    2. ANTHROPIC_AUTH_TOKEN (CCR/proxy env var for enterprise setups)
    3. Custom config directory (config_dir param or CLAUDE_CONFIG_DIR env var)
    4. System credential store (macOS Keychain, Windows Credential Manager,
       Linux Secret Service)

    NOTE: ANTHROPIC_API_KEY is intentionally NOT supported to prevent
    silent billing to user's API credits when OAuth is misconfigured.
    """

# Token priority order (lines 38-41)
AUTH_TOKEN_ENV_VARS = [
    "CLAUDE_CODE_OAUTH_TOKEN",  # OAuth token from Claude Code CLI
    "ANTHROPIC_AUTH_TOKEN",     # CCR/proxy token (for enterprise setups)
]
```

**Token Sources** (in priority order):
1. **Environment Variables** - `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`
2. **Config Directory** - Profile's custom `CLAUDE_CONFIG_DIR` with `.credentials.json`
3. **System Credential Store** - Platform-specific secure storage:
   - **macOS**: Keychain (`security find-generic-password -s "Claude Code-credentials"`)
   - **Windows**: `%USERPROFILE%\.claude\.credentials.json`
   - **Linux**: Secret Service API via DBus (`org.freedesktop.secrets`)

**Token Validation**:
```python
# From core/auth.py (lines 68-103)
def validate_token_not_encrypted(token: str) -> None:
    """
    Validate that a token is not in encrypted format.

    This function should be called before passing a token to the Claude Agent SDK
    to ensure proper error messages when decryption has failed.

    Raises:
        ValueError: If token is in encrypted format (enc:...)
    """

def is_encrypted_token(token: str | None) -> bool:
    """Check if a token is encrypted (has "enc:" prefix)."""
```

**Encrypted Token Handling**:
- Claude Code CLI stores tokens with `enc:` prefix
- Platform-specific decryption functions (`_decrypt_token_macos`, `_decrypt_token_linux`, `_decrypt_token_windows`)
- Currently **not implemented** (raises `NotImplementedError`)
- Workaround: Use plaintext tokens in `.env` file

### Provider Configuration (`core/providers/config.py`)

**Current Structure**:

```python
# From core/providers/config.py (lines 51-73)
@dataclass
class ProviderConfig:
    """Configuration for AI engine provider selection."""

    # Core settings
    provider: str = DEFAULT_PROVIDER

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
```

**Environment Variable Mapping** (lines 76-113):
```python
@classmethod
def from_env(cls) -> "ProviderConfig":
    # Claude Agent SDK settings
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # LiteLLM settings
    litellm_api_key = os.environ.get("LITELLM_API_KEY", "")

    # OpenRouter settings
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
```

**Validation** (lines 115-128):
```python
def is_valid(self) -> bool:
    """Check if config has minimum required values for the selected provider."""
    if self.provider == AIEngineProvider.CLAUDE.value:
        return bool(self.anthropic_api_key)
    elif self.provider == AIEngineProvider.OPENROUTER.value:
        return bool(self.openrouter_api_key)
    # ...
```

## Problem Statement

### Authentication Mismatch Between Providers

| Provider | Auth Method | Credential Format | Source |
|----------|-------------|-------------------|--------|
| **Claude SDK** | OAuth Token | `sk-ant-oat01-...` | Keychain, env vars, config dir |
| **OpenAI API** | API Key | `sk-proj-...` | Environment variables only |
| **LiteLLM** | API Key | Provider-specific | Environment variables |
| **OpenRouter** | API Key | `sk-or-v1-...` | Environment variables |

### Key Challenges

1. **Different Authentication Mechanisms**
   - Claude: OAuth token with encrypted storage (`enc:` prefix)
   - OpenAI: Plain API key from environment
   - No unified interface for credential retrieval

2. **Multiple Token Sources**
   - Claude tokens can come from 4+ sources (env vars, config dir, keychain)
   - OpenAI API keys only from environment
   - Each provider has different validation rules

3. **Inconsistent Error Messages**
   - Claude: "Run `claude` and authenticate with `/login`"
   - OpenAI: "Set OPENAI_API_KEY in .env"
   - No generic "authentication failed" message

4. **No Multi-Provider Credential Management**
   - `core/auth.py` is Claude-specific
   - `ProviderConfig` has separate API key fields but no unified auth logic
   - Each provider adapter must implement its own auth handling

## Proposed Authentication Abstraction

### Design Goals

1. **Unified Interface**: Single API for all provider authentication
2. **Provider-Specific Strategies**: OAuth for Claude, API keys for others
3. **Backward Compatibility**: Existing Claude OAuth flow unchanged
4. **Type Safety**: Clear distinction between auth types (OAuth vs API key)
5. **Extensibility**: Easy to add new providers (e.g., Google AI, Azure)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                          │
│            (agents/, spec_agents/)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ create_client(provider="openai")
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Unified Auth Provider (NEW)                    │
│                                                              │
│  class AuthProvider:                                         │
│      - get_credentials() -> Credentials                      │
│      - validate() -> bool                                    │
│      - get_source() -> str                                   │
│                                                              │
│  + OAuthAuth(Claude)     - Keychain, env vars, config dir   │
│  + APIKeyAuth(OpenAI)    - Environment variables only        │
│  + APIKeyAuth(LiteLLM)   - Environment variables only        │
│  + APIKeyAuth(OpenRouter)- Environment variables only        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Provider-specific auth strategies
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   Claude OAuth      │         │   Provider API      │
│   (existing code)   │         │   Keys (NEW)        │
│                     │         │                     │
│  - Keychain access  │         │  - OPENAI_API_KEY   │
│  - Token decrypt    │         │  - LITELLM_API_KEY  │
│  - OAuth flow       │         │  - OPENROUTER_API_  │
└─────────────────────┘         └─────────────────────┘
```

## Implementation Design

### Layer 1: Abstract Base Class

**File**: `core/auth/base.py` (NEW)

```python
"""
Authentication abstraction for multi-provider support.

Defines unified interface for credential management across all AI providers.
Each provider implements a provider-specific auth strategy (OAuth, API key, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AuthType(str, Enum):
    """Authentication type classification."""
    OAUTH = "oauth"          # OAuth token (e.g., Claude SDK)
    API_KEY = "api_key"      # API key from environment (e.g., OpenAI)
    BEARER_TOKEN = "bearer"  # Bearer token (future: Azure, Google AI)


@dataclass
class Credentials:
    """
    Unified credentials container.

    Attributes:
        auth_type: Type of authentication (OAuth, API key, etc.)
        token: The credential value (OAuth token or API key)
        source: Where the credential came from (e.g., "CLAUDE_CODE_OAUTH_TOKEN env var")
        provider: Provider identifier (claude, openai, litellm, openrouter)
        metadata: Optional provider-specific metadata (model, base URL, etc.)
    """
    auth_type: AuthType
    token: str
    source: str
    provider: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_valid(self) -> bool:
        """Basic validation: token must be non-empty string."""
        return bool(self.token and isinstance(self.token, str))

    def __str__(self) -> str:
        """Safe string representation (redacts sensitive data)."""
        if len(self.token) > 8:
            redacted = f"{self.token[:4]}...{self.token[-4:]}"
        else:
            redacted = "***"
        return f"Credentials({self.provider}, {self.auth_type.value}, {redacted}, from={self.source})"


class AuthProvider(ABC):
    """
    Abstract base class for provider-specific authentication strategies.

    Each AI provider implements a subclass that handles its unique authentication
    mechanism (OAuth tokens, API keys, bearer tokens, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'claude', 'openai')."""
        pass

    @property
    @abstractmethod
    def auth_type(self) -> AuthType:
        """Authentication type (OAuth, API key, etc.)."""
        pass

    @abstractmethod
    def get_credentials(self) -> Optional[Credentials]:
        """
        Retrieve credentials for this provider.

        Returns:
            Credentials object if found, None otherwise.

        Raises:
            ValueError: If credentials are found but invalid format
        """
        pass

    def validate_credentials(self, credentials: Credentials) -> bool:
        """
        Validate credentials format and structure.

        Default implementation checks token is non-empty.
        Subclasses can override for provider-specific validation.

        Args:
            credentials: Credentials object to validate

        Returns:
            True if valid, False otherwise
        """
        if not credentials:
            return False
        if not credentials.is_valid():
            return False
        if credentials.provider != self.provider_name:
            return False
        return True

    def get_auth_instructions(self) -> str:
        """
        Get user-friendly instructions for setting up authentication.

        Returns:
            String with setup instructions (e.g., "Run `claude` and type /login")
        """
        raise NotImplementedError(
            f"Auth instructions not implemented for {self.provider_name}"
        )

    def requires_user_interaction(self) -> bool:
        """
        Check if this auth method requires user interaction (e.g., OAuth flow).

        Returns:
            True if user must run a command or complete a flow, False otherwise
        """
        return self.auth_type == AuthType.OAUTH
```

### Layer 2: Claude OAuth Provider

**File**: `core/auth/providers/claude.py` (NEW)

```python
"""
Claude OAuth authentication provider.

Wraps existing Claude OAuth token management from core/auth.py
into the unified AuthProvider interface.
"""

import os
from typing import Optional

from core.auth.base import AuthProvider, AuthType, Credentials


class ClaudeOAuthProvider(AuthProvider):
    """
    Authentication provider for Claude SDK using OAuth tokens.

    Wraps the existing OAuth token logic from core/auth.py:
    - Environment variables (CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_AUTH_TOKEN)
    - Config directory (CLAUDE_CONFIG_DIR)
    - System credential store (macOS Keychain, Windows Credential Manager,
      Linux Secret Service)

    This provider maintains backward compatibility with the existing Claude
    authentication flow while fitting into the unified auth abstraction.
    """

    # Reuse existing auth token priority order
    AUTH_TOKEN_ENV_VARS = [
        "CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_AUTH_TOKEN",
    ]

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize Claude OAuth provider.

        Args:
            config_dir: Optional custom config directory (profile's configDir).
                       If None, checks CLAUDE_CONFIG_DIR env var, then uses
                       default locations (keychain, credential files).
        """
        self.config_dir = config_dir

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH

    def get_credentials(self) -> Optional[Credentials]:
        """
        Retrieve Claude OAuth token from multiple sources.

        Checks sources in priority order:
        1. Environment variables (CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_AUTH_TOKEN)
        2. Config directory (self.config_dir or CLAUDE_CONFIG_DIR env var)
        3. System credential store (keychain, credential manager, secret service)

        Returns:
            Credentials object if token found, None otherwise.

        Raises:
            ValueError: If token is in encrypted format (enc:...) and decryption fails
        """
        # Import existing auth functions
        from core.auth import (
            get_auth_token,
            get_auth_token_source,
            _try_decrypt_token,
        )

        # Get token using existing logic
        token = get_auth_token(self.config_dir)
        if not token:
            return None

        # Get source for better error messages
        source = get_auth_token_source(self.config_dir)
        if not source:
            source = "unknown"

        # Attempt decryption if encrypted (enc: prefix)
        decrypted_token = _try_decrypt_token(token)

        return Credentials(
            auth_type=AuthType.OAUTH,
            token=decrypted_token,
            source=source,
            provider=self.provider_name,
        )

    def validate_credentials(self, credentials: Credentials) -> bool:
        """
        Validate Claude OAuth token format.

        Claude OAuth tokens must:
        - Start with 'sk-ant-oat01-'
        - Not be in encrypted format (enc:...)

        Args:
            credentials: Credentials object to validate

        Returns:
            True if valid format, False otherwise
        """
        if not super().validate_credentials(credentials):
            return False

        token = credentials.token

        # Check for encrypted token (should be decrypted by get_credentials)
        if token.startswith("enc:"):
            return False

        # Validate token prefix (Claude OAuth tokens)
        if not token.startswith("sk-ant-oat01-"):
            return False

        # Basic length check (OAuth tokens are typically > 50 chars)
        if len(token) < 50:
            return False

        return True

    def get_auth_instructions(self) -> str:
        """
        Get platform-specific OAuth setup instructions.

        Returns:
            String with instructions for running `claude /login`
        """
        from core.platform import is_linux, is_macos, is_windows

        base_instructions = (
            "Claude OAuth authentication required.\n\n"
            "To authenticate:\n"
            "  1. Run: claude\n"
            "  2. Type: /login\n"
            "  3. Press Enter to open browser\n"
            "  4. Complete OAuth login in browser\n\n"
        )

        if is_macos():
            base_instructions += "The token will be saved to macOS Keychain automatically."
        elif is_windows():
            base_instructions += "The token will be saved to Windows Credential Manager."
        elif is_linux():
            base_instructions += "The token will be saved to system Secret Service.\n\n"
            base_instructions += "Alternatively, set CLAUDE_CODE_OAUTH_TOKEN in your .env file."

        return base_instructions
```

### Layer 3: OpenAI API Key Provider

**File**: `core/auth/providers/openai.py` (NEW)

```python
"""
OpenAI API key authentication provider.

Handles API key-based authentication for OpenAI provider.
"""

import os
from typing import Optional

from core.auth.base import AuthProvider, AuthType, Credentials


class OpenAIAPIKeyProvider(AuthProvider):
    """
    Authentication provider for OpenAI using API keys.

    OpenAI uses simple API key authentication via environment variables.
    No OAuth flow, no keychain integration.

    Environment Variables:
        OPENAI_API_KEY: API key (required, format: sk-proj-...)
    """

    # Environment variable names for OpenAI API key
    API_KEY_ENV_VARS = [
        "OPENAI_API_KEY",  # Standard OpenAI API key
    ]

    def __init__(self, env_var: Optional[str] = None):
        """
        Initialize OpenAI API key provider.

        Args:
            env_var: Optional custom environment variable name.
                    If None, uses standard OPENAI_API_KEY.
        """
        self.env_var = env_var or "OPENAI_API_KEY"

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.API_KEY

    def get_credentials(self) -> Optional[Credentials]:
        """
        Retrieve OpenAI API key from environment variable.

        Returns:
            Credentials object if API key found, None otherwise.
        """
        api_key = os.environ.get(self.env_var)
        if not api_key:
            return None

        return Credentials(
            auth_type=AuthType.API_KEY,
            token=api_key,
            source=f"{self.env_var} environment variable",
            provider=self.provider_name,
        )

    def validate_credentials(self, credentials: Credentials) -> bool:
        """
        Validate OpenAI API key format.

        OpenAI API keys must:
        - Start with 'sk-proj-' (new format) or 'sk-' (legacy format)
        - Be at least 20 characters long

        Args:
            credentials: Credentials object to validate

        Returns:
            True if valid format, False otherwise
        """
        if not super().validate_credentials(credentials):
            return False

        token = credentials.token

        # Check API key prefix
        # New format: sk-proj-...
        # Legacy format: sk-...
        if not (token.startswith("sk-proj-") or token.startswith("sk-")):
            return False

        # Basic length check (API keys are typically > 20 chars)
        if len(token) < 20:
            return False

        return True

    def get_auth_instructions(self) -> str:
        """
        Get API key setup instructions.

        Returns:
            String with instructions for setting OPENAI_API_KEY
        """
        return (
            "OpenAI API key authentication required.\n\n"
            "To authenticate:\n"
            "  1. Get API key from https://platform.openai.com/api-keys\n"
            f"  2. Set {self.env_var} in your .env file:\n"
            f"     {self.env_var}=sk-proj-...\n\n"
            "Note: Do not use the 'sk-' legacy format. Use 'sk-proj-' project keys."
        )
```

### Layer 4: LiteLLM and OpenRouter Providers

**File**: `core/auth/providers/litellm.py` (NEW)

```python
"""
LiteLLM API key authentication provider.

Handles API key-based authentication for LiteLLM provider.
"""

import os
from typing import Optional

from core.auth.base import AuthProvider, AuthType, Credentials


class LiteLLMAPIKeyProvider(AuthProvider):
    """
    Authentication provider for LiteLLM using API keys.

    LiteLLM supports multiple model providers, so API key requirements vary.
    Some models require API keys, others don't.

    Environment Variables:
        LITELLM_API_KEY: Optional API key (depends on model provider)
    """

    def __init__(self, env_var: Optional[str] = None):
        """
        Initialize LiteLLM API key provider.

        Args:
            env_var: Optional custom environment variable name.
                    If None, uses standard LITELLM_API_KEY.
        """
        self.env_var = env_var or "LITELLM_API_KEY"

    @property
    def provider_name(self) -> str:
        return "litellm"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.API_KEY

    def get_credentials(self) -> Optional[Credentials]:
        """
        Retrieve LiteLLM API key from environment variable.

        Note: LiteLLM can work without API key for some models (e.g., local Ollama).
        This returns None if env var is not set (not an error condition).

        Returns:
            Credentials object if API key found, None otherwise.
        """
        api_key = os.environ.get(self.env_var)
        if not api_key:
            # LiteLLM can work without API key for some providers
            return None

        return Credentials(
            auth_type=AuthType.API_KEY,
            token=api_key,
            source=f"{self.env_var} environment variable",
            provider=self.provider_name,
        )

    def get_auth_instructions(self) -> str:
        """
        Get API key setup instructions.

        Returns:
            String with instructions for setting LITELLM_API_KEY
        """
        return (
            "LiteLLM API key authentication (optional).\n\n"
            "Some LiteLLM models require API keys, others don't.\n\n"
            "To set an API key:\n"
            f"  1. Set {self.env_var} in your .env file:\n"
            f"     {self.env_var}=your-api-key-here\n\n"
            "Note: If using local models (Ollama), API key is not required."
        )
```

**File**: `core/auth/providers/openrouter.py` (NEW)

```python
"""
OpenRouter API key authentication provider.

Handles API key-based authentication for OpenRouter provider.
"""

import os
from typing import Optional

from core.auth.base import AuthProvider, AuthType, Credentials


class OpenRouterAPIKeyProvider(AuthProvider):
    """
    Authentication provider for OpenRouter using API keys.

    OpenRouter uses API key authentication via environment variables.

    Environment Variables:
        OPENROUTER_API_KEY: API key (required, format: sk-or-v1-...)
    """

    def __init__(self, env_var: Optional[str] = None):
        """
        Initialize OpenRouter API key provider.

        Args:
            env_var: Optional custom environment variable name.
                    If None, uses standard OPENROUTER_API_KEY.
        """
        self.env_var = env_var or "OPENROUTER_API_KEY"

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.API_KEY

    def get_credentials(self) -> Optional[Credentials]:
        """
        Retrieve OpenRouter API key from environment variable.

        Returns:
            Credentials object if API key found, None otherwise.
        """
        api_key = os.environ.get(self.env_var)
        if not api_key:
            return None

        return Credentials(
            auth_type=AuthType.API_KEY,
            token=api_key,
            source=f"{self.env_var} environment variable",
            provider=self.provider_name,
        )

    def validate_credentials(self, credentials: Credentials) -> bool:
        """
        Validate OpenRouter API key format.

        OpenRouter API keys must:
        - Start with 'sk-or-v1-'
        - Be at least 20 characters long

        Args:
            credentials: Credentials object to validate

        Returns:
            True if valid format, False otherwise
        """
        if not super().validate_credentials(credentials):
            return False

        token = credentials.token

        # Check API key prefix
        if not token.startswith("sk-or-v1-"):
            return False

        # Basic length check (API keys are typically > 20 chars)
        if len(token) < 20:
            return False

        return True

    def get_auth_instructions(self) -> str:
        """
        Get API key setup instructions.

        Returns:
            String with instructions for setting OPENROUTER_API_KEY
        """
        return (
            "OpenRouter API key authentication required.\n\n"
            "To authenticate:\n"
            "  1. Get API key from https://openrouter.ai/keys\n"
            f"  2. Set {self.env_var} in your .env file:\n"
            f"     {self.env_var}=sk-or-v1-...\n\n"
            "Note: OpenRouter uses pay-per-use billing."
        )
```

### Layer 5: Unified Auth Factory

**File**: `core/auth/factory.py` (NEW)

```python
"""
Unified authentication provider factory.

Creates provider-specific auth instances based on provider name.
"""

from typing import Optional

from core.auth.base import AuthProvider, Credentials
from core.auth.providers.claude import ClaudeOAuthProvider
from core.auth.providers.openai import OpenAIAPIKeyProvider
from core.auth.providers.litellm import LiteLLMAPIKeyProvider
from core.auth.providers.openrouter import OpenRouterAPIKeyProvider


# Provider registry
AUTH_PROVIDERS = {
    "claude": ClaudeOAuthProvider,
    "openai": OpenAIAPIKeyProvider,
    "litellm": LiteLLMAPIKeyProvider,
    "openrouter": OpenRouterAPIKeyProvider,
}


def create_auth_provider(
    provider: str,
    config_dir: Optional[str] = None,
) -> AuthProvider:
    """
    Create an authentication provider for the specified AI provider.

    Args:
        provider: Provider name (claude, openai, litellm, openrouter)
        config_dir: Optional custom config directory (only for Claude OAuth)

    Returns:
        AuthProvider instance for the specified provider

    Raises:
        ValueError: If provider is not supported
    """
    provider_lower = provider.lower()

    if provider_lower not in AUTH_PROVIDERS:
        supported = ", ".join(AUTH_PROVIDERS.keys())
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {supported}"
        )

    provider_class = AUTH_PROVIDERS[provider_lower]

    # Claude OAuth provider requires config_dir parameter
    if provider_lower == "claude":
        return provider_class(config_dir=config_dir)

    # Other providers don't need special initialization
    return provider_class()


def get_provider_credentials(
    provider: str,
    config_dir: Optional[str] = None,
) -> Optional[Credentials]:
    """
    Get credentials for the specified provider.

    Convenience function that creates auth provider and retrieves credentials.

    Args:
        provider: Provider name (claude, openai, litellm, openrouter)
        config_dir: Optional custom config directory (only for Claude OAuth)

    Returns:
        Credentials object if found, None otherwise

    Raises:
        ValueError: If provider is not supported
    """
    auth_provider = create_auth_provider(provider, config_dir)
    return auth_provider.get_credentials()


def require_provider_credentials(
    provider: str,
    config_dir: Optional[str] = None,
) -> Credentials:
    """
    Get credentials for the specified provider or raise ValueError.

    Convenience function that creates auth provider, retrieves credentials,
    and raises a helpful error if not found.

    Args:
        provider: Provider name (claude, openai, litellm, openrouter)
        config_dir: Optional custom config directory (only for Claude OAuth)

    Returns:
        Credentials object

    Raises:
        ValueError: If provider is not supported or credentials not found
    """
    auth_provider = create_auth_provider(provider, config_dir)
    credentials = auth_provider.get_credentials()

    if not credentials:
        # Credentials not found - provide helpful error message
        instructions = auth_provider.get_auth_instructions()
        raise ValueError(
            f"No credentials found for provider: {provider}\n\n"
            f"{instructions}"
        )

    # Validate credentials format
    if not auth_provider.validate_credentials(credentials):
        raise ValueError(
            f"Invalid credentials format for provider: {provider}\n\n"
            f"{instructions}"
        )

    return credentials


def get_available_auth_providers() -> list[str]:
    """
    Get list of providers that have credentials configured.

    Checks each provider's auth source and returns list of providers
    that have valid credentials available.

    Returns:
        List of provider names (e.g., ["claude", "openai"])
    """
    available = []

    for provider_name in AUTH_PROVIDERS.keys():
        try:
            credentials = get_provider_credentials(provider_name)
            if credentials:
                available.append(provider_name)
        except Exception:
            # Skip providers that error during credential retrieval
            continue

    return available
```

### Layer 6: Integration with Provider Config

**File**: `core/providers/config.py` (ENHANCED)

**Changes**:

1. Add `OPENAI` to `AIEngineProvider` enum:

```python
class AIEngineProvider(str, Enum):
    """Supported AI engine providers."""

    CLAUDE = "claude"
    OPENAI = "openai"          # NEW
    LITELLM = "litellm"
    OPENROUTER = "openrouter"
```

2. Add OpenAI fields to `ProviderConfig`:

```python
@dataclass
class ProviderConfig:
    """Configuration for AI engine provider selection."""

    # Core settings
    provider: str = DEFAULT_PROVIDER

    # Claude Agent SDK settings
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"

    # OpenAI settings (NEW)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # LiteLLM settings
    litellm_model: str = ""
    litellm_api_base: str = ""
    litellm_api_key: str = ""

    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL
```

3. Add OpenAI to `from_env()` method:

```python
@classmethod
def from_env(cls) -> "ProviderConfig":
    """Create config from environment variables."""

    # Provider selection (default: claude)
    provider = os.environ.get("AI_ENGINE_PROVIDER", DEFAULT_PROVIDER).lower()

    # Validate provider
    valid_providers = [p.value for p in AIEngineProvider]
    if provider not in valid_providers:
        provider = DEFAULT_PROVIDER

    # Claude Agent SDK settings
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    claude_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

    # OpenAI settings (NEW)
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    # ... rest of implementation

    return cls(
        provider=provider,
        anthropic_api_key=anthropic_api_key,
        claude_model=claude_model,
        openai_api_key=openai_api_key,        # NEW
        openai_model=openai_model,            # NEW
        # ... other fields
    )
```

4. Update `is_valid()` to check OpenAI:

```python
def is_valid(self) -> bool:
    """Check if config has minimum required values for the selected provider."""
    if self.provider == AIEngineProvider.CLAUDE.value:
        return bool(self.anthropic_api_key)
    elif self.provider == AIEngineProvider.OPENAI.value:     # NEW
        return bool(self.openai_api_key)
    elif self.provider == AIEngineProvider.LITELLM.value:
        return bool(self.litellm_model)
    elif self.provider == AIEngineProvider.OPENROUTER.value:
        return bool(self.openrouter_api_key)
    return False
```

## Environment Variables

### New Environment Variables

| Variable | Provider | Required | Format | Example |
|----------|----------|----------|--------|---------|
| `OPENAI_API_KEY` | OpenAI | Yes (if using OpenAI) | `sk-proj-...` | `sk-proj-abc123...` |
| `OPENAI_MODEL` | OpenAI | No (default: gpt-4o) | Model identifier | `gpt-4o`, `gpt-4-turbo` |

### Existing Variables (No Changes)

| Variable | Provider | Required | Format | Example |
|----------|----------|----------|--------|---------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude | Yes* | `sk-ant-oat01-...` | OAuth token |
| `ANTHROPIC_API_KEY` | Claude | No (legacy) | `sk-ant-...` | API key |
| `LITELLM_API_KEY` | LiteLLM | Conditional | Provider-specific | Varies |
| `LITELLM_MODEL` | LiteLLM | Yes | Model identifier | `gpt-4`, `claude-3-opus` |
| `OPENROUTER_API_KEY` | OpenRouter | Yes | `sk-or-v1-...` | `sk-or-v1-abc123...` |

*Note: Claude can also use keychain/config dir if env var not set.

## Usage Examples

### Example 1: Get Credentials for Provider

```python
from core.auth.factory import get_provider_credentials

# Get Claude OAuth credentials
claude_creds = get_provider_credentials("claude")
if claude_creds:
    print(f"Token: {claude_creds.token[:10]}...")
    print(f"Source: {claude_creds.source}")

# Get OpenAI API key
openai_creds = get_provider_credentials("openai")
if openai_creds:
    print(f"API Key: {openai_creds.token[:10]}...")
    print(f"Source: {openai_creds.source}")
```

### Example 2: Require Credentials (with Error Handling)

```python
from core.auth.factory import require_provider_credentials

try:
    # This will raise ValueError with helpful instructions if not found
    creds = require_provider_credentials("openai")
    print(f"Authenticated with OpenAI: {creds.token[:10]}...")
except ValueError as e:
    print(f"Authentication failed: {e}")
    # Output:
    # Authentication failed: No credentials found for provider: openai
    #
    # OpenAI API key authentication required.
    #
    # To authenticate:
    #   1. Get API key from https://platform.openai.com/api-keys
    #   2. Set OPENAI_API_KEY in your .env file:
    #      OPENAI_API_KEY=sk-proj-...
```

### Example 3: Check Available Providers

```python
from core.auth.factory import get_available_auth_providers

available = get_available_auth_providers()
print(f"Available providers: {available}")
# Output: Available providers: ['claude', 'openai']
```

### Example 4: Provider Factory Integration

```python
from core.providers.factory import create_engine_provider
from core.providers.config import ProviderConfig

# Create provider using unified auth (internal implementation)
config = ProviderConfig.from_env()
provider = create_engine_provider(config)

# Provider's __init__ will use require_provider_credentials internally
# If credentials missing, ValueError with helpful instructions is raised
```

## Error Handling

### Unified Error Messages

The abstraction provides consistent error messages across all providers:

**Claude OAuth Missing**:
```
ValueError: No credentials found for provider: claude

Claude OAuth authentication required.

To authenticate:
  1. Run: claude
  2. Type: /login
  3. Press Enter to open browser
  4. Complete OAuth login in browser

The token will be saved to macOS Keychain automatically.
```

**OpenAI API Key Missing**:
```
ValueError: No credentials found for provider: openai

OpenAI API key authentication required.

To authenticate:
  1. Get API key from https://platform.openai.com/api-keys
  2. Set OPENAI_API_KEY in your .env file:
     OPENAI_API_KEY=sk-proj-...

Note: Do not use the 'sk-' legacy format. Use 'sk-proj-' project keys.
```

**Invalid Credential Format**:
```
ValueError: Invalid credentials format for provider: openai

OpenAI API key authentication required.

To authenticate:
  1. Get API key from https://platform.openai.com/api-keys
  2. Set OPENAI_API_KEY in your .env file:
     OPENAI_API_KEY=sk-proj-...

Note: Do not use the 'sk-' legacy format. Use 'sk-proj-' project keys.
```

### Validation Rules

| Provider | Validation Rule | Error on Invalid |
|----------|----------------|------------------|
| Claude | Token starts with `sk-ant-oat01-`, not encrypted, length ≥ 50 | ValueError with OAuth instructions |
| OpenAI | Token starts with `sk-proj-` or `sk-`, length ≥ 20 | ValueError with API key instructions |
| OpenRouter | Token starts with `sk-or-v1-`, length ≥ 20 | ValueError with API key instructions |
| LiteLLM | No validation (optional, varies by model) | N/A |

## Security Considerations

### Credential Source Priority

**Claude OAuth (Secure → Less Secure)**:
1. System keychain (most secure, encrypted at rest)
2. Config directory credential file (file permissions)
3. Environment variables (least secure, visible in process list)

**OpenAI API Key**:
1. Environment variables only (standard practice for API keys)

**Recommendation**: For Claude, prefer keychain storage. For OpenAI, use `.env` file (git-ignored).

### Token Redaction

The `Credentials.__str__()` method automatically redacts sensitive data:

```python
creds = Credentials(
    auth_type=AuthType.API_KEY,
    token="sk-proj-abc123def456ghi789",
    source="OPENAI_API_KEY env var",
    provider="openai"
)

print(creds)
# Output: Credentials(openai, api_key, sk-p...789, from=OPENAI_API_KEY environment variable)
```

### Encrypted Token Handling

**Current State**:
- Claude Code CLI stores tokens with `enc:` prefix
- Decryption functions (`_decrypt_token_macos`, etc.) raise `NotImplementedError`
- `ClaudeOAuthProvider.get_credentials()` calls `_try_decrypt_token()` which returns original if decryption fails
- `validate_credentials()` rejects encrypted tokens (security measure)

**Future Enhancement**:
- Implement token decryption using Claude Code CLI as subprocess
- Fallback to prompting user to re-authenticate if decryption fails

### No Logging of Credentials

The abstraction ensures credentials are never logged:

```python
# BAD - Don't do this
logger.info(f"Using token: {credentials.token}")

# GOOD - Use redacted string representation
logger.debug(f"Using credentials: {credentials}")
```

## Migration Path

### Phase 1: Add Abstraction Layer (Non-Breaking)

1. Create `core/auth/` package with:
   - `base.py` - Abstract base classes
   - `providers/` - Provider implementations
   - `factory.py` - Factory functions

2. **Do NOT modify** existing `core/auth.py` (backward compatibility)

3. Update `core/providers/config.py` to add OpenAI fields

4. Add unit tests for new auth providers

**Impact**: No breaking changes. Existing code continues to work.

### Phase 2: Integrate with Provider Factory

1. Update `core/providers/factory.py` to use unified auth:

```python
# Before (current)
def create_engine_provider(config: ProviderConfig) -> AIEngineProvider:
    if config.provider == "claude":
        return ClaudeAdapter(
            anthropic_api_key=config.anthropic_api_key,
            model=config.claude_model,
        )

# After (with unified auth)
def create_engine_provider(config: ProviderConfig) -> AIEngineProvider:
    if config.provider == "claude":
        # Get credentials using unified auth
        creds = require_provider_credentials("claude", config_dir=None)
        return ClaudeAdapter(
            anthropic_api_key=creds.token,  # Use token from Credentials
            model=config.claude_model,
        )
```

2. Remove redundant API key fields from adapter constructors

**Impact**: Breaking change for adapter constructors. Requires updating all adapter calls.

### Phase 3: Deprecate Direct API Key Usage

1. Add deprecation warnings to direct API key usage:

```python
def create_engine_provider(config: ProviderConfig) -> AIEngineProvider:
    if config.provider == "openai":
        if config.openai_api_key:
            # Warn about using deprecated direct API key
            logger.warning(
                "Using OPENAI_API_KEY from ProviderConfig is deprecated. "
                "Use unified auth (require_provider_credentials) instead."
            )
        # Use unified auth
        creds = require_provider_credentials("openai")
        return OpenAIAdapter(
            api_key=creds.token,
            model=config.openai_model,
        )
```

2. Update documentation to recommend unified auth

**Impact**: Deprecation warnings only. Still functional.

### Phase 4: Remove Deprecated Code (Future Release)

1. Remove API key fields from `ProviderConfig` (keep `provider` and `model`)
2. Remove fallback logic in adapters
3. Make unified auth mandatory

**Impact**: Breaking change. All code must use unified auth.

## Testing Strategy

### Unit Tests

**File**: `tests/auth/test_factory.py`

```python
import pytest
from core.auth.factory import create_auth_provider, get_provider_credentials
from core.auth.base import AuthType

def test_create_claude_auth_provider():
    """Test creating Claude OAuth provider."""
    provider = create_auth_provider("claude")
    assert provider.provider_name == "claude"
    assert provider.auth_type == AuthType.OAUTH

def test_create_openai_auth_provider():
    """Test creating OpenAI API key provider."""
    provider = create_auth_provider("openai")
    assert provider.provider_name == "openai"
    assert provider.auth_type == AuthType.API_KEY

def test_create_invalid_provider():
    """Test that invalid provider raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported provider"):
        create_auth_provider("invalid_provider")

def test_get_claude_credentials_with_env(monkeypatch):
    """Test getting Claude credentials from environment variable."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test-token")
    creds = get_provider_credentials("claude")
    assert creds is not None
    assert creds.token == "sk-ant-oat01-test-token"
    assert creds.auth_type == AuthType.OAUTH

def test_get_openai_credentials_with_env(monkeypatch):
    """Test getting OpenAI credentials from environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test-key")
    creds = get_provider_credentials("openai")
    assert creds is not None
    assert creds.token == "sk-proj-test-key"
    assert creds.auth_type == AuthType.API_KEY

def test_require_credentials_missing(monkeypatch):
    """Test that require_provider_credentials raises when credentials missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="No credentials found"):
        require_provider_credentials("openai")
```

### Integration Tests

**File**: `tests/auth/test_integration.py`

```python
import pytest
from core.auth.factory import require_provider_credentials
from core.providers.config import ProviderConfig
from core.providers.factory import create_engine_provider

@pytest.mark.skipif(
    os.environ.get("OPENAI_API_KEY") is None,
    reason="OPENAI_API_KEY not set"
)
def test_openai_provider_with_unified_auth():
    """Test OpenAI provider creation using unified auth."""
    # Get credentials using unified auth
    creds = require_provider_credentials("openai")

    # Create provider config
    config = ProviderConfig.from_env()

    # Create provider (should use unified auth internally)
    provider = create_engine_provider(config)

    assert provider is not None
    assert isinstance(provider, OpenAIProvider)
```

### Validation Tests

**File**: `tests/auth/test_validation.py`

```python
import pytest
from core.auth.providers.openai import OpenAIAPIKeyProvider
from core.auth.base import Credentials

def test_openai_validates_good_key():
    """Test that valid OpenAI API key passes validation."""
    provider = OpenAIAPIKeyProvider()
    creds = Credentials(
        auth_type=AuthType.API_KEY,
        token="sk-proj-abc123def456",
        source="test",
        provider="openai"
    )
    assert provider.validate_credentials(creds) is True

def test_openai_rejects_bad_prefix():
    """Test that API key with wrong prefix fails validation."""
    provider = OpenAIAPIKeyProvider()
    creds = Credentials(
        auth_type=AuthType.API_KEY,
        token="bad-prefix-abc123",
        source="test",
        provider="openai"
    )
    assert provider.validate_credentials(creds) is False

def test_claude_rejects_encrypted_token():
    """Test that encrypted Claude tokens are rejected."""
    provider = ClaudeOAuthProvider()
    creds = Credentials(
        auth_type=AuthType.OAUTH,
        token="enc:encrypted-data-here",
        source="test",
        provider="claude"
    )
    assert provider.validate_credentials(creds) is False
```

## Summary

### What This Design Provides

1. **Unified Interface**: Single API for all provider authentication
2. **Type Safety**: Clear distinction between OAuth and API key auth
3. **Provider-Specific Strategies**: OAuth for Claude, API keys for others
4. **Backward Compatibility**: Existing Claude OAuth flow unchanged
5. **Better Error Messages**: Consistent, actionable error messages
6. **Extensibility**: Easy to add new providers (Google AI, Azure)

### Files to Create

| File | Purpose |
|------|---------|
| `core/auth/__init__.py` | Auth package initialization |
| `core/auth/base.py` | Abstract base classes (`AuthProvider`, `Credentials`) |
| `core/auth/providers/__init__.py` | Providers package initialization |
| `core/auth/providers/claude.py` | Claude OAuth provider (wraps existing auth.py) |
| `core/auth/providers/openai.py` | OpenAI API key provider |
| `core/auth/providers/litellm.py` | LiteLLM API key provider |
| `core/auth/providers/openrouter.py` | OpenRouter API key provider |
| `core/auth/factory.py` | Factory functions for creating providers |

### Files to Modify

| File | Changes |
|------|---------|
| `core/providers/config.py` | Add `OPENAI` to enum, add OpenAI fields to `ProviderConfig` |
| `core/providers/factory.py` | Use unified auth when creating provider instances |
| `tests/auth/test_factory.py` | (NEW) Unit tests for factory |
| `tests/auth/test_validation.py` | (NEW) Validation tests |

### Backward Compatibility

✅ **Phase 1**: No breaking changes
- Existing `core/auth.py` functions unchanged
- New auth layer is additive only
- Existing tests continue to pass

⚠️ **Phase 2**: Adapter constructor changes
- Adapters use unified auth instead of direct API key parameters
- Requires updating adapter factory logic

⚠️ **Phase 3**: Deprecation warnings
- Direct API key usage still works but warns
- Prepares for future removal

❌ **Phase 4**: Breaking changes
- API key fields removed from `ProviderConfig`
- Unified auth mandatory
- Requires code updates across codebase

### Next Steps

1. **Implement Phase 1**: Create auth abstraction layer (non-breaking)
2. **Write Tests**: Unit tests for all auth providers
3. **Update Provider Factory**: Integrate unified auth (Phase 2)
4. **Add Deprecation Warnings**: Phase 3
5. **Document Migration**: User guide for updating code
6. **Remove Deprecated Code**: Phase 4 (future release)

### Verification

✅ Verify that unified auth provider supports both `CLAUDE_CODE_OAUTH_TOKEN` and `OPENAI_API_KEY`:

```bash
# Test Claude OAuth
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-test"
python -c "from core.auth.factory import get_provider_credentials; print(get_provider_credentials('claude'))"

# Test OpenAI API key
export OPENAI_API_KEY="sk-proj-test"
python -c "from core.auth.factory import get_provider_credentials; print(get_provider_credentials('openai'))"
```

Both should return `Credentials` objects with correct `auth_type` and `source`.
