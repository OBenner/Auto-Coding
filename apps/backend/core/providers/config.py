"""
AI Engine Provider Configuration
================================

Configuration dataclass for multi-backend AI engine selection.
Follows the same patterns as integrations/graphiti/config.py for consistency.

Supported Providers:
- claude: Claude Agent SDK (default, recommended) - Full agentic capabilities
- openai: OpenAI direct API - GPT-4, GPT-4o, o1, o3 models
- google: Google Gemini API - Gemini 2.0, Gemini 1.5 models
- litellm: LiteLLM unified API - 100+ LLMs via single interface
- openrouter: OpenRouter cloud routing - 400+ models with pay-per-use
- zhipuai: Zhipu AI GLM models - Chinese language models (e.g., glm-4, glm-4-flash)
- ollama: Ollama local models - Privacy-first local inference

Environment Variables:
    # Core
    AI_ENGINE_PROVIDER: Provider selection (claude|openai|google|litellm|openrouter|zhipuai|ollama, default: claude)

    # Claude Agent SDK (default)
    ANTHROPIC_API_KEY: Required for Claude provider

    # OpenAI
    OPENAI_API_KEY: Required for OpenAI provider
    OPENAI_MODEL: Model identifier (default: gpt-4o)
    OPENAI_BASE_URL: Optional custom API base URL

    # Google Gemini
    GOOGLE_API_KEY: Required for Google provider
    GOOGLE_MODEL: Model identifier (default: gemini-2.0-flash)

    # LiteLLM
    LITELLM_MODEL: Model identifier (e.g., gpt-4, claude-3-opus)
    LITELLM_API_BASE: Optional custom API base URL
    LITELLM_API_KEY: Optional API key (depends on model provider)

    # OpenRouter
    OPENROUTER_API_KEY: Required for OpenRouter provider
    OPENROUTER_MODEL: Model identifier (default: anthropic/claude-sonnet-4)
    OPENROUTER_BASE_URL: API base URL (default: https://openrouter.ai/api/v1)

    # Zhipu AI (GLM)
    ZHIPUAI_API_KEY: Required for ZhipuAI provider
    ZHIPUAI_MODEL: Model identifier (default: glm-4-flash)

    # Ollama
    OLLAMA_MODEL: Model identifier (e.g., llama3, deepseek-r1, codellama)
    OLLAMA_BASE_URL: API base URL (default: http://localhost:11434)
    OLLAMA_API_KEY: Optional API key for authenticated Ollama instances

    # Provider Fallback
    PROVIDER_FALLBACK_CHAIN: Comma-separated list of providers for fallback (e.g., "claude,openai,google,ollama")
"""

import os
from dataclasses import dataclass
from enum import Enum


class AIEngineProvider(str, Enum):
    """Supported AI engine providers."""

    CLAUDE = "claude"
    OPENAI = "openai"
    GOOGLE = "google"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"
    ZHIPUAI = "zhipuai"
    OLLAMA = "ollama"


# Default values
DEFAULT_PROVIDER = "claude"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4"
DEFAULT_ZHIPUAI_MODEL = "glm-4-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


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
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_base_url: str = ""

    # Google Gemini settings
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # LiteLLM settings
    litellm_model: str = ""
    litellm_api_base: str = ""
    litellm_api_key: str = ""

    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL

    # Zhipu AI settings
    zhipuai_api_key: str = ""
    zhipuai_model: str = DEFAULT_ZHIPUAI_MODEL

    # Ollama settings
    ollama_model: str = ""
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    ollama_api_key: str = ""

    # Provider fallback chain
    provider_fallback_chain: list[str] | None = None

    @classmethod
    def from_env(cls, agent_type: str | None = None) -> "ProviderConfig":
        """Create config from environment variables.

        Args:
            agent_type: Optional agent type for per-agent provider/model overrides.
                        If provided, checks AGENT_PROVIDER_<TYPE> and AGENT_MODEL_<TYPE>
                        env vars before falling back to global settings.
        """
        # Per-agent provider override (e.g. AGENT_PROVIDER_PLANNER=litellm)
        provider = None
        if agent_type:
            provider = os.environ.get(f"AGENT_PROVIDER_{agent_type.upper()}")
        if not provider:
            provider = os.environ.get("AI_ENGINE_PROVIDER", DEFAULT_PROVIDER)
        provider = provider.lower()

        # Validate provider
        valid_providers = [p.value for p in AIEngineProvider]
        if provider not in valid_providers:
            # Fall back to default if invalid
            provider = DEFAULT_PROVIDER

        # Per-agent model override (e.g. AGENT_MODEL_PLANNER=claude-opus-4-20250514)
        agent_model = None
        if agent_type:
            agent_model = os.environ.get(f"AGENT_MODEL_{agent_type.upper()}")

        # Claude Agent SDK settings
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        claude_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

        # OpenAI settings
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        openai_model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        openai_base_url = os.environ.get("OPENAI_BASE_URL", "")

        # Google Gemini settings
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        google_model = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")

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

        # Zhipu AI settings
        zhipuai_api_key = os.environ.get("ZHIPUAI_API_KEY", "")
        zhipuai_model = os.environ.get("ZHIPUAI_MODEL", DEFAULT_ZHIPUAI_MODEL)

        # Ollama settings
        ollama_model = os.environ.get("OLLAMA_MODEL", "")
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        ollama_api_key = os.environ.get("OLLAMA_API_KEY", "")

        # Provider fallback chain (comma-separated list, e.g., "claude,openai,google,ollama")
        provider_fallback_chain_str = os.environ.get("PROVIDER_FALLBACK_CHAIN", "")
        provider_fallback_chain = None
        if provider_fallback_chain_str:
            # Parse comma-separated list and normalize provider names
            provider_fallback_chain = [
                p.strip().lower() for p in provider_fallback_chain_str.split(",") if p.strip()
            ]
            # Validate providers in chain
            valid_providers = [p.value for p in AIEngineProvider]
            provider_fallback_chain = [
                p for p in provider_fallback_chain if p in valid_providers
            ]
            # Set to None if empty after validation
            if not provider_fallback_chain:
                provider_fallback_chain = None

        # Apply per-agent model override to the selected provider's model field
        if agent_model:
            if provider == AIEngineProvider.CLAUDE.value:
                claude_model = agent_model
            elif provider == AIEngineProvider.OPENAI.value:
                openai_model = agent_model
            elif provider == AIEngineProvider.GOOGLE.value:
                google_model = agent_model
            elif provider == AIEngineProvider.LITELLM.value:
                litellm_model = agent_model
            elif provider == AIEngineProvider.OPENROUTER.value:
                openrouter_model = agent_model
            elif provider == AIEngineProvider.ZHIPUAI.value:
                zhipuai_model = agent_model
            elif provider == AIEngineProvider.OLLAMA.value:
                ollama_model = agent_model

        return cls(
            provider=provider,
            anthropic_api_key=anthropic_api_key,
            claude_model=claude_model,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            openai_base_url=openai_base_url,
            google_api_key=google_api_key,
            google_model=google_model,
            litellm_model=litellm_model,
            litellm_api_base=litellm_api_base,
            litellm_api_key=litellm_api_key,
            openrouter_api_key=openrouter_api_key,
            openrouter_model=openrouter_model,
            openrouter_base_url=openrouter_base_url,
            zhipuai_api_key=zhipuai_api_key,
            zhipuai_model=zhipuai_model,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
            ollama_api_key=ollama_api_key,
            provider_fallback_chain=provider_fallback_chain,
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
        elif self.provider == AIEngineProvider.GOOGLE.value:
            return bool(self.google_api_key)
        elif self.provider == AIEngineProvider.LITELLM.value:
            # LiteLLM can work with various providers, model is required
            return bool(self.litellm_model)
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            return bool(self.openrouter_api_key)
        elif self.provider == AIEngineProvider.ZHIPUAI.value:
            return bool(self.zhipuai_api_key)
        elif self.provider == AIEngineProvider.OLLAMA.value:
            return bool(self.ollama_model)
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
        elif self.provider == AIEngineProvider.GOOGLE.value:
            if not self.google_api_key:
                errors.append(
                    "Google provider requires GOOGLE_API_KEY environment variable"
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
        elif self.provider == AIEngineProvider.ZHIPUAI.value:
            if not self.zhipuai_api_key:
                errors.append(
                    "ZhipuAI provider requires ZHIPUAI_API_KEY environment variable"
                )
        elif self.provider == AIEngineProvider.OLLAMA.value:
            if not self.ollama_model:
                errors.append(
                    "Ollama provider requires OLLAMA_MODEL environment variable"
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
        elif self.provider == AIEngineProvider.GOOGLE.value:
            return f"Google Gemini ({self.google_model})"
        elif self.provider == AIEngineProvider.LITELLM.value:
            return f"LiteLLM ({self.litellm_model or 'no model configured'})"
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            return f"OpenRouter ({self.openrouter_model})"
        elif self.provider == AIEngineProvider.ZHIPUAI.value:
            return f"ZhipuAI ({self.zhipuai_model})"
        elif self.provider == AIEngineProvider.OLLAMA.value:
            return f"Ollama ({self.ollama_model or 'no model configured'})"
        return f"Unknown ({self.provider})"

    def get_model_for_provider(self) -> str | None:
        """Get the configured model for the current provider."""
        if self.provider == AIEngineProvider.CLAUDE.value:
            return self.claude_model
        elif self.provider == AIEngineProvider.OPENAI.value:
            return self.openai_model
        elif self.provider == AIEngineProvider.GOOGLE.value:
            return self.google_model
        elif self.provider == AIEngineProvider.LITELLM.value:
            return self.litellm_model or None
        elif self.provider == AIEngineProvider.OPENROUTER.value:
            return self.openrouter_model
        elif self.provider == AIEngineProvider.ZHIPUAI.value:
            return self.zhipuai_model
        elif self.provider == AIEngineProvider.OLLAMA.value:
            return self.ollama_model or None
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

    if config.google_api_key:
        available.append(AIEngineProvider.GOOGLE.value)

    if config.litellm_model:
        available.append(AIEngineProvider.LITELLM.value)

    if config.openrouter_api_key:
        available.append(AIEngineProvider.OPENROUTER.value)

    if config.zhipuai_api_key:
        available.append(AIEngineProvider.ZHIPUAI.value)

    if config.ollama_model:
        available.append(AIEngineProvider.OLLAMA.value)

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
