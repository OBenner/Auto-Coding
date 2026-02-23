"""
AI Engine Provider Factory
==========================

Factory functions for creating AI engine providers.
Follows the same pattern as integrations/graphiti/providers_pkg/factory.py.

Usage:
    from core.providers import create_engine_provider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = create_engine_provider(config)
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.providers.base import AIEngineProvider
    from core.providers.config import ProviderConfig

from core.providers.exceptions import ProviderError, ProviderNotInstalled

logger = logging.getLogger(__name__)


def _create_claude_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create a Claude Agent SDK provider.

    Args:
        config: ProviderConfig with Claude settings

    Returns:
        ClaudeAgentProvider instance

    Raises:
        ProviderNotInstalled: If claude-agent-sdk is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.claude import ClaudeAgentProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "Claude Agent SDK adapter not installed. "
            "Ensure core.providers.adapters.claude module exists."
        ) from e

    logger.debug(f"Creating Claude provider with model: {config.claude_model}")
    return ClaudeAgentProvider(config)


def _create_litellm_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create a LiteLLM provider.

    Args:
        config: ProviderConfig with LiteLLM settings

    Returns:
        LiteLLMProvider instance

    Raises:
        ProviderNotInstalled: If litellm is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.litellm import LiteLLMProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "LiteLLM adapter not installed. Install with: pip install litellm"
        ) from e

    logger.debug(f"Creating LiteLLM provider with model: {config.litellm_model}")
    return LiteLLMProvider(config)


def _create_openrouter_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create an OpenRouter provider.

    Args:
        config: ProviderConfig with OpenRouter settings

    Returns:
        OpenRouterProvider instance

    Raises:
        ProviderNotInstalled: If openai package is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.openrouter import OpenRouterProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "OpenRouter adapter not installed. Install with: pip install openai"
        ) from e

    logger.debug(f"Creating OpenRouter provider with model: {config.openrouter_model}")
    return OpenRouterProvider(config)


def _create_openai_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create an OpenAI provider.

    Args:
        config: ProviderConfig with OpenAI settings

    Returns:
        OpenAIProvider instance

    Raises:
        ProviderNotInstalled: If openai package is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.openai import OpenAIProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "OpenAI adapter not installed. Install with: pip install openai"
        ) from e

    logger.debug(f"Creating OpenAI provider with model: {config.openai_model}")
    return OpenAIProvider(config)


def create_engine_provider(config: "ProviderConfig") -> "AIEngineProvider":
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

    logger.info(f"Creating AI engine provider: {provider}")

    if provider == "claude":
        return _create_claude_provider(config)
    elif provider == "litellm":
        return _create_litellm_provider(config)
    elif provider == "openrouter":
        return _create_openrouter_provider(config)
    elif provider == "openai":
        return _create_openai_provider(config)
    else:
        raise ProviderError(
            f"Unknown AI engine provider: {provider}. "
            f"Supported providers: claude, litellm, openrouter, openai"
        )


def get_available_provider_names() -> list[str]:
    """
    Get list of all supported provider names.

    Returns:
        List of provider name strings
    """
    return ["claude", "litellm", "openrouter", "openai"]
