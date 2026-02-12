"""
AI Engine Provider Configuration
================================

Configuration dataclass for multi-backend AI engine selection.
Follows the same patterns as integrations/graphiti/config.py for consistency.

Supported Providers:
- claude: Claude Agent SDK (default, recommended) - Full agentic capabilities
- openai: OpenAI direct API - GPT-4, GPT-4o, o1, o3 models
- litellm: LiteLLM unified API - 100+ LLMs via single interface
- openrouter: OpenRouter cloud routing - 400+ models with pay-per-use

Environment Variables:
    # Core
    AI_ENGINE_PROVIDER: Provider selection (claude|openai|litellm|openrouter, default: claude)

    # Claude Agent SDK (default)
    ANTHROPIC_API_KEY: Required for Claude provider

    # OpenAI
    OPENAI_API_KEY: Required for OpenAI provider
    OPENAI_MODEL: Model identifier (default: gpt-4o)
    OPENAI_BASE_URL: Optional custom API base URL

    # LiteLLM
    LITELLM_MODEL: Model identifier (e.g., gpt-4, claude-3-opus)
    LITELLM_API_BASE: Optional custom API base URL
    LITELLM_API_KEY: Optional API key (depends on model provider)

    # OpenRouter
    OPENROUTER_API_KEY: Required for OpenRouter provider
    OPENROUTER_MODEL: Model identifier (default: anthropic/claude-sonnet-4)
    OPENROUTER_BASE_URL: API base URL (default: https://openrouter.ai/api/v1)
"""

import os
from dataclasses import dataclass
from enum import Enum


class AIEngineProvider(str, Enum):
    """Supported AI engine providers."""

    CLAUDE = "claude"
    OPENAI = "openai"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"


# Default values
DEFAULT_PROVIDER = "claude"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4"


@dataclass
class ProviderConfig:
    """Configuration for AI engine provider selection.

    Supports multiple AI backends with Claude Agent SDK as the default.
    Configuration is loaded from environment variables.
    """

    # Core settings
    provider: str = DEFAULT_PROVIDER

    # Claude Agent SDK settings
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"

    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = ""

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
        # Provider selection (default: claude)
        provider = os.environ.get("AI_ENGINE_PROVIDER", DEFAULT_PROVIDER).lower()

        # Validate provider
        valid_providers = [p.value for p in AIEngineProvider]
        if provider not in valid_providers:
            # Fall back to default if invalid
            provider = DEFAULT_PROVIDER

        # Claude Agent SDK settings
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        claude_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

        # OpenAI settings
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        openai_base_url = os.environ.get("OPENAI_BASE_URL", "")

        # LiteLLM settings
        litellm_model = os.environ.get("LITELLM_MODEL", "")
        litellm_api_base = os.environ.get("LITELLM_API_BASE", "")
        litellm_api_key = os.environ.get("LITELLM_API_KEY", "")

        # OpenRouter settings
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        openrouter_model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        openrouter_base_url = os.environ.get(
            "OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL
        )

        return cls(
            provider=provider,
            anthropic_api_key=anthropic_api_key,
            claude_model=claude_model,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            openai_base_url=openai_base_url,
            litellm_model=litellm_model,
            litellm_api_base=litellm_api_base,
            litellm_api_key=litellm_api_key,
            openrouter_api_key=openrouter_api_key,
            openrouter_model=openrouter_model,
            openrouter_base_url=openrouter_base_url,
        )

    def is_valid(self) -> bool:
        """
        Check if config has minimum required values for the selected provider.

        Returns True if the selected provider has its required credentials.
        """
        if self.provider == AIEngineProvider.CLAUDE.value:
            return bool(self.anthropic_api_key)
        elif self.provider == AIEngineProvider.OPENAI.value:
            return bool(self.openai_api_key)
        elif self.provider == AIEngineProvider.LITELLM.value:
            # LiteLLM can work with various providers, model is required
            return bool(self.litellm_model)
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            return bool(self.openrouter_api_key)
        return False

    def get_validation_errors(self) -> list[str]:
        """Get list of validation errors for current configuration."""
        errors = []

        if self.provider == AIEngineProvider.CLAUDE.value:
            if not self.anthropic_api_key:
                errors.append(
                    "Claude provider requires ANTHROPIC_API_KEY environment variable"
                )
        elif self.provider == AIEngineProvider.OPENAI.value:
            if not self.openai_api_key:
                errors.append(
                    "OpenAI provider requires OPENAI_API_KEY environment variable"
                )
        elif self.provider == AIEngineProvider.LITELLM.value:
            if not self.litellm_model:
                errors.append(
                    "LiteLLM provider requires LITELLM_MODEL environment variable"
                )
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            if not self.openrouter_api_key:
                errors.append(
                    "OpenRouter provider requires OPENROUTER_API_KEY environment variable"
                )
        else:
            errors.append(f"Unknown provider: {self.provider}")

        return errors

    def get_provider_summary(self) -> str:
        """Get a summary of configured provider."""
        if self.provider == AIEngineProvider.CLAUDE.value:
            return f"Claude Agent SDK ({self.claude_model})"
        elif self.provider == AIEngineProvider.OPENAI.value:
            return f"OpenAI ({self.openai_model})"
        elif self.provider == AIEngineProvider.LITELLM.value:
            return f"LiteLLM ({self.litellm_model or 'no model configured'})"
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            return f"OpenRouter ({self.openrouter_model})"
        return f"Unknown ({self.provider})"

    def get_model_for_provider(self) -> str | None:
        """Get the configured model for the current provider."""
        if self.provider == AIEngineProvider.CLAUDE.value:
            return self.claude_model
        elif self.provider == AIEngineProvider.OPENAI.value:
            return self.openai_model
        elif self.provider == AIEngineProvider.LITELLM.value:
            return self.litellm_model or None
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            return self.openrouter_model
        return None


def get_provider_config() -> ProviderConfig:
    """
    Get the current provider configuration from environment.

    Returns:
        ProviderConfig instance with current settings
    """
    return ProviderConfig.from_env()


def get_available_providers() -> list[str]:
    """
    Get list of available providers based on current environment.

    Returns:
        List of provider names that have their required credentials configured
    """
    config = ProviderConfig.from_env()
    available = []

    # Check each provider's credentials
    if config.anthropic_api_key:
        available.append(AIEngineProvider.CLAUDE.value)

    if config.openai_api_key:
        available.append(AIEngineProvider.OPENAI.value)

    if config.litellm_model:
        available.append(AIEngineProvider.LITELLM.value)

    if config.openrouter_api_key:
        available.append(AIEngineProvider.OPENROUTER.value)

    return available


def validate_provider_config() -> tuple[bool, list[str]]:
    """
    Validate provider configuration from environment.

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if configuration is valid for selected provider
        - error_messages: List of validation error messages (empty if valid)
    """
    config = ProviderConfig.from_env()

    if not config.is_valid():
        errors = config.get_validation_errors()
        return False, errors

    return True, []
