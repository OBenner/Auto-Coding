"""
Simple Claude SDK Client Factory
================================

Factory for creating minimal Claude SDK clients for single-turn utility operations
like commit message generation, merge conflict resolution, and batch analysis.

These clients don't need full security configurations, MCP servers, or hooks.
Use `create_client()` from `core.client` for full agent sessions with security.

Multi-Provider Support
----------------------
This module integrates with the provider abstraction layer (core.providers) to enable
alternative AI backends. Claude Agent SDK remains the default and recommended provider.

Available providers:
- claude: Claude Agent SDK (default) - Full SDK client with tools
- litellm: LiteLLM unified API - 100+ LLMs via single interface (simplified)
- openrouter: OpenRouter cloud routing - 400+ models with pay-per-use (simplified)

Example usage:
    from core.simple_client import create_simple_client

    # For commit message generation (text-only, no tools)
    client = create_simple_client(agent_type="commit_message")

    # For merge conflict resolution (text-only, no tools)
    client = create_simple_client(agent_type="merge_resolver")

    # For insights extraction (read tools only)
    client = create_simple_client(agent_type="insights", cwd=project_dir)

    # Provider-based client (supports alternative backends)
    from core.simple_client import create_simple_client_for_provider
    provider, session = create_simple_client_for_provider(agent_type="merge_resolver")
"""

import logging
import os
from pathlib import Path

from agents.tools_pkg import get_agent_config, get_default_thinking_level
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from core.auth import (
    get_sdk_env_vars,
    require_auth_token,
    validate_token_not_encrypted,
)
from core.platform import validate_cli_path

# Provider abstraction layer imports
# These enable multi-provider support while preserving Claude as default
from core.providers import (
    create_engine_provider,
)
from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.config import (
    DEFAULT_PROVIDER,
    ProviderConfig,
    get_provider_config,
    validate_provider_config,
)
from phase_config import get_thinking_budget

logger = logging.getLogger(__name__)


def create_simple_client(
    agent_type: str = "merge_resolver",
    model: str = "claude-haiku-4-5-20251001",
    system_prompt: str | None = None,
    cwd: Path | None = None,
    max_turns: int = 1,
    max_thinking_tokens: int | None = None,
) -> ClaudeSDKClient:
    """
    Create a minimal Claude SDK client for single-turn utility operations.

    This factory creates lightweight clients without MCP servers, security hooks,
    or full permission configurations. Use for text-only analysis tasks.

    Args:
        agent_type: Agent type from AGENT_CONFIGS. Determines available tools.
                   Common utility types:
                   - "merge_resolver" - Text-only merge conflict analysis
                   - "commit_message" - Text-only commit message generation
                   - "insights" - Read-only code insight extraction
                   - "batch_analysis" - Read-only batch issue analysis
                   - "batch_validation" - Read-only validation
        model: Claude model to use (defaults to Haiku for fast/cheap operations)
        system_prompt: Optional custom system prompt (for specialized tasks)
        cwd: Working directory for file operations (optional)
        max_turns: Maximum conversation turns (default: 1 for single-turn)
        max_thinking_tokens: Override thinking budget (None = use agent default from
                            AGENT_CONFIGS, converted using phase_config.THINKING_BUDGET_MAP)

    Returns:
        Configured ClaudeSDKClient for single-turn operations

    Raises:
        ValueError: If agent_type is not found in AGENT_CONFIGS
    """
    # Get authentication
    oauth_token = require_auth_token()

    # Validate token is not encrypted before passing to SDK
    # Encrypted tokens (enc:...) should have been decrypted by require_auth_token()
    # If we still have an encrypted token here, it means decryption failed or was skipped
    validate_token_not_encrypted(oauth_token)

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

    # Get environment variables for SDK
    sdk_env = get_sdk_env_vars()

    # Get agent configuration (raises ValueError if unknown type)
    config = get_agent_config(agent_type)

    # Get tools from config (no MCP tools for simple clients)
    allowed_tools = list(config.get("tools", []))

    # Determine thinking budget using the single source of truth (phase_config.py)
    if max_thinking_tokens is None:
        thinking_level = get_default_thinking_level(agent_type)
        max_thinking_tokens = get_thinking_budget(thinking_level)

    # Build options dict
    # Note: SDK bundles its own CLI, so no cli_path detection needed
    options_kwargs = {
        "model": model,
        "system_prompt": system_prompt,
        "allowed_tools": allowed_tools,
        "max_turns": max_turns,
        "cwd": str(cwd.resolve()) if cwd else None,
        "env": sdk_env,
    }

    # Only add max_thinking_tokens if not None (Haiku doesn't support extended thinking)
    if max_thinking_tokens is not None:
        options_kwargs["max_thinking_tokens"] = max_thinking_tokens

    # Optional: Allow CLI path override via environment variable
    env_cli_path = os.environ.get("CLAUDE_CLI_PATH")
    if env_cli_path and validate_cli_path(env_cli_path):
        options_kwargs["cli_path"] = env_cli_path
        logger.info(f"Using CLAUDE_CLI_PATH override: {env_cli_path}")

    return ClaudeSDKClient(options=ClaudeAgentOptions(**options_kwargs))


# =============================================================================
# Multi-Provider Support Functions
# =============================================================================
# These functions enable alternative AI backends while preserving Claude as default.
# Claude remains the recommended provider for full functionality.


def get_simple_provider_config() -> ProviderConfig:
    """
    Get the current provider configuration from environment.

    Returns:
        ProviderConfig with current provider settings

    Example:
        config = get_simple_provider_config()
        print(f"Using provider: {config.provider}")
        print(f"Model: {config.get_model_for_provider()}")
    """
    return get_provider_config()


def get_simple_provider() -> AIEngineProvider:
    """
    Create an AI engine provider instance based on current environment configuration.

    Uses the AI_ENGINE_PROVIDER environment variable to determine which provider
    to create. Defaults to Claude if not specified.

    Returns:
        AIEngineProvider instance (ClaudeAgentProvider, LiteLLMProvider, or OpenRouterProvider)

    Raises:
        ProviderNotInstalled: If required packages for the provider are missing
        ProviderError: If provider creation fails

    Example:
        provider = get_simple_provider()
        print(f"Provider: {provider.name}")
        print(f"Supported models: {provider.get_supported_models()}")
    """
    config = get_provider_config()
    return create_engine_provider(config)


def is_using_claude_provider_for_simple() -> bool:
    """
    Check if the Claude Agent SDK is the configured provider for simple clients.

    This is useful for determining whether full SDK functionality (tools, etc.)
    is available, as these features are only supported by the Claude provider.

    Returns:
        True if Claude is the configured provider (default), False otherwise
    """
    config = get_provider_config()
    return config.provider == DEFAULT_PROVIDER


def create_simple_client_for_provider(
    agent_type: str = "merge_resolver",
    model: str | None = None,
    system_prompt: str | None = None,
    cwd: Path | None = None,
    max_turns: int = 1,
    max_thinking_tokens: int | None = None,
) -> tuple[AIEngineProvider, AgentSession]:
    """
    Create a simple AI client using the provider factory.

    This function provides an alternative to create_simple_client() that uses the
    provider abstraction layer. It supports multiple AI backends based on
    the AI_ENGINE_PROVIDER environment variable.

    For Claude provider (default), this creates a simplified session without
    full security hooks or MCP servers (similar to create_simple_client).

    For non-Claude providers (LiteLLM, OpenRouter), this creates a basic
    session suitable for single-turn utility operations.

    Args:
        agent_type: Agent type identifier from AGENT_CONFIGS
                   (e.g., 'merge_resolver', 'commit_message', 'insights')
        model: Model identifier (None = use provider default from config)
        system_prompt: Optional custom system prompt (for specialized tasks)
        cwd: Working directory for file operations (optional)
        max_turns: Maximum conversation turns (default: 1 for single-turn)
        max_thinking_tokens: Token budget for extended thinking (Claude only)

    Returns:
        Tuple of (provider, session):
        - provider: AIEngineProvider instance
        - session: AgentSession instance for interacting with the AI

    Raises:
        ProviderNotInstalled: If required packages for the provider are missing
        ProviderError: If provider or session creation fails
        ValueError: If agent_type is not found in AGENT_CONFIGS

    Example:
        from core.simple_client import create_simple_client_for_provider

        provider, session = create_simple_client_for_provider(
            agent_type="merge_resolver"
        )

        # For Claude provider, get the underlying SDK client
        if provider.name == "claude":
            client = session.client  # ClaudeSDKClient instance
    """
    # Get provider configuration
    config = get_provider_config()

    # Use provider's default model if not specified
    if model is None:
        model = config.get_model_for_provider()

    logger.info(
        f"Creating simple provider-based client: provider={config.provider}, "
        f"agent_type={agent_type}, model={model}"
    )

    # Create the provider
    provider = create_engine_provider(config)

    # Get agent configuration for tools (only used by Claude provider)
    agent_config = get_agent_config(agent_type)
    allowed_tools = list(agent_config.get("tools", []))

    # Build session configuration
    session_config = SessionConfig(
        name=f"simple-{agent_type}-session",
        system_prompt=system_prompt or "",
        model=model,
        max_tokens=None,  # Use provider default
        tools=allowed_tools,
        working_directory=str(cwd.resolve()) if cwd else None,
        extra={
            "agent_type": agent_type,
            "max_turns": max_turns,
            "max_thinking_tokens": max_thinking_tokens,
            "simple_client": True,  # Flag to indicate this is a simple client
        },
    )

    # Create session using provider-specific logic
    session = provider.create_session(config=session_config)

    return provider, session


def validate_simple_provider() -> tuple[bool, list[str]]:
    """
    Validate the current provider configuration for simple clients.

    Checks that all required credentials and settings are present for
    the configured provider.

    Returns:
        Tuple of (is_valid, error_messages):
        - is_valid: True if configuration is valid
        - error_messages: List of validation errors (empty if valid)

    Example:
        is_valid, errors = validate_simple_provider()
        if not is_valid:
            print("Provider configuration errors:")
            for error in errors:
                print(f"  - {error}")
    """
    return validate_provider_config()


def get_simple_provider_summary() -> str:
    """
    Get a human-readable summary of the current provider configuration.

    Returns:
        Summary string describing the configured provider and model

    Example:
        print(f"AI Backend: {get_simple_provider_summary()}")
        # Output: "AI Backend: Claude Agent SDK (claude-haiku-4-5-20251001)"
    """
    config = get_provider_config()
    return config.get_provider_summary()
