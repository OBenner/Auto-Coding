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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from core.providers.config import ProviderConfig
from core.providers.exceptions import ProviderError, ProviderNotInstalled

if TYPE_CHECKING:
    from core.providers.base import AgentSession, AIEngineProvider

logger = logging.getLogger(__name__)


def _apply_route_to_config(config: "ProviderConfig", route: object) -> "ProviderConfig":
    """
    Apply a task routing decision to a provider config.

    Args:
        config: Existing provider configuration loaded from environment.
        route: TaskRoute-like object with provider and model attributes.

    Returns:
        ProviderConfig with routed provider/model values applied.
    """
    provider = str(route.provider)
    model = str(route.model)
    routed_config = replace(config, provider=provider)

    if provider == "claude":
        routed_config.claude_model = model
    elif provider == "codex":
        routed_config.codex_model = model
    elif provider == "openai":
        routed_config.openai_model = model
    elif provider == "google":
        routed_config.google_model = model
    elif provider == "litellm":
        routed_config.litellm_model = model
    elif provider == "openrouter":
        routed_config.openrouter_model = model
    elif provider == "zhipuai":
        routed_config.zhipuai_model = model
    elif provider == "ollama":
        routed_config.ollama_model = model

    return routed_config


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


def _create_openai_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create an OpenAI direct provider.

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


def _create_codex_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create a Codex CLI account provider.

    Args:
        config: ProviderConfig with Codex CLI settings

    Returns:
        CodexCliProvider instance

    Raises:
        ProviderNotInstalled: If the adapter module is unavailable
    """
    try:
        from core.providers.adapters.codex import CodexCliProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "Codex CLI adapter not installed. "
            "Ensure core.providers.adapters.codex module exists."
        ) from e

    logger.debug(f"Creating Codex CLI provider with model: {config.codex_model}")
    return CodexCliProvider(config)


def _create_google_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create a Google Gemini provider.

    Args:
        config: ProviderConfig with Google settings

    Returns:
        GoogleProvider instance

    Raises:
        ProviderNotInstalled: If google-generativeai package is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.google import GoogleProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "Google adapter not installed. Install with: pip install google-generativeai"
        ) from e

    logger.debug(f"Creating Google provider with model: {config.google_model}")
    return GoogleProvider(config)


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


def _create_zhipuai_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create a Zhipu AI provider.

    Args:
        config: ProviderConfig with Zhipu AI settings

    Returns:
        ZhipuAIProvider instance

    Raises:
        ProviderNotInstalled: If zai-sdk package is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.zhipuai import ZhipuAIProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "ZhipuAI adapter not installed. Install with: pip install zai-sdk"
        ) from e

    logger.debug(f"Creating ZhipuAI provider with model: {config.zhipuai_model}")
    return ZhipuAIProvider(config)


def _create_ollama_provider(config: "ProviderConfig") -> "AIEngineProvider":
    """
    Create an Ollama local model provider.

    Args:
        config: ProviderConfig with Ollama settings

    Returns:
        OllamaProvider instance

    Raises:
        ProviderNotInstalled: If openai package is not installed
        ProviderError: If provider creation fails
    """
    try:
        from core.providers.adapters.ollama import OllamaProvider
    except ImportError as e:
        raise ProviderNotInstalled(
            "Ollama adapter not installed. Install with: pip install openai"
        ) from e

    logger.debug(f"Creating Ollama provider with model: {config.ollama_model}")
    return OllamaProvider(config)


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
    elif provider == "codex":
        return _create_codex_provider(config)
    elif provider == "openai":
        return _create_openai_provider(config)
    elif provider == "google":
        return _create_google_provider(config)
    elif provider == "litellm":
        return _create_litellm_provider(config)
    elif provider == "openrouter":
        return _create_openrouter_provider(config)
    elif provider == "zhipuai":
        return _create_zhipuai_provider(config)
    elif provider == "ollama":
        return _create_ollama_provider(config)
    else:
        raise ProviderError(
            f"Unknown AI engine provider: {provider}. "
            "Supported providers: claude, codex, openai, google, litellm, "
            "openrouter, zhipuai, ollama"
        )


def create_agent_session(
    agent_type: str,
    project_dir: "Path",
    spec_dir: "Path",
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    subtask: dict | None = None,
) -> "AgentSession":
    """
    Shared factory for creating agent sessions across all agent types.

    Consolidates the duplicated provider/session logic from planner.py,
    coder.py, qa/reviewer.py, and qa/fixer.py.

    Args:
        agent_type: The agent type ('planner', 'coder', 'qa_reviewer', 'qa_fixer')
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        model: Model to use (overrides provider config)
        max_thinking_tokens: Token budget for extended thinking
        subtask: Optional subtask metadata for runtime model routing. If
            provided and model is not explicitly set, the router selects a
            provider/model based on task complexity.

    Returns:
        AgentSession for the configured provider. Claude sessions expose a
        `.client` property for the SDK client; completion providers may expose
        provider-specific streaming APIs instead.

    Raises:
        ProviderError: If provider creation or session creation fails
    """
    from core.providers.base import SessionConfig

    config = ProviderConfig.from_env(agent_type=agent_type)

    if subtask is not None and not model:
        from core.providers.task_router import TaskComplexityRouter

        router = TaskComplexityRouter()
        route = router.route(subtask, agent_type, provider_config=config)
        logger.info(
            "Task routed: complexity=%s (%.2f) -> %s/%s | cost=%.4f | %s",
            route.complexity,
            route.complexity_score,
            route.provider,
            route.model,
            route.estimated_cost,
            route.reasoning,
        )
        model = route.model
        config = _apply_route_to_config(config, route)

    provider = create_engine_provider(config)

    if provider.name == "claude":
        session = provider.create_session(
            config=SessionConfig(
                name=f"{agent_type}-session",
                model=model,
            ),
            project_dir=Path(project_dir),
            spec_dir=Path(spec_dir),
            agent_type=agent_type,
            max_thinking_tokens=max_thinking_tokens,
        )
    else:
        session = provider.create_session(
            SessionConfig(
                name=f"{agent_type}-session",
                model=model,
            )
        )

    return session


def get_available_provider_names() -> list[str]:
    """
    Get list of all supported provider names.

    Returns:
        List of provider name strings
    """
    return [
        "claude",
        "codex",
        "openai",
        "google",
        "litellm",
        "openrouter",
        "zhipuai",
        "ollama",
    ]
