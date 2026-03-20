"""
Graphiti setup validator for Auto Code setup wizard.

Validates that Graphiti memory system is properly configured:
- Checks provider settings in environment
- Validates API keys for selected providers
- Tests LadybugDB connection
"""

import asyncio
import logging
from typing import TypedDict

from integrations.graphiti.config import EmbedderProvider, GraphitiConfig, LLMProvider
from integrations.graphiti.providers import (
    is_graphiti_enabled,
    test_embedder_connection,
    test_llm_connection,
    test_ollama_connection,
    validate_embedding_config,
)

logger = logging.getLogger(__name__)


class GraphitiValidationResult(TypedDict):
    """Result of Graphiti configuration validation."""

    valid: bool
    enabled: bool
    llm_provider: str
    embedder_provider: str
    issues: list[str]
    warnings: list[str]
    message: str


def validate_graphiti_config() -> GraphitiValidationResult:
    """
    Validate Graphiti memory system configuration.

    Returns:
        GraphitiValidationResult: Dictionary containing:
            - valid: True if configuration is valid and usable
            - enabled: Whether Graphiti is enabled in environment
            - llm_provider: Selected LLM provider
            - embedder_provider: Selected embedder provider
            - issues: List of blocking configuration issues
            - warnings: List of non-blocking warnings
            - message: Human-readable summary message

    Example:
        >>> result = validate_graphiti_config()
        >>> if result['valid']:
        ...     print(f"Graphiti configured with {result['llm_provider']}")
        ... else:
        ...     for issue in result['issues']:
        ...         print(f"ERROR: {issue}")
    """
    issues = []
    warnings = []

    try:
        # Check if Graphiti is enabled
        enabled = is_graphiti_enabled()

        if not enabled:
            logger.info("Graphiti is disabled (GRAPHITI_ENABLED not set to true)")
            return {
                "valid": True,  # Valid to have it disabled
                "enabled": False,
                "llm_provider": "none",
                "embedder_provider": "none",
                "issues": [],
                "warnings": [
                    "Graphiti memory is disabled. Memory features will not be available."
                ],
                "message": "Graphiti is disabled. Set GRAPHITI_ENABLED=true to enable memory features.",
            }

        # Load configuration from environment
        config = GraphitiConfig.from_env()

        # Validate provider selections
        llm_provider = config.llm_provider
        embedder_provider = config.embedder_provider

        # Validate LLM provider
        if llm_provider not in [p.value for p in LLMProvider]:
            issues.append(
                f"Invalid LLM provider '{llm_provider}'. "
                f"Valid options: {', '.join(p.value for p in LLMProvider)}"
            )

        # Validate embedder provider
        if embedder_provider not in [p.value for p in EmbedderProvider]:
            issues.append(
                f"Invalid embedder provider '{embedder_provider}'. "
                f"Valid options: {', '.join(p.value for p in EmbedderProvider)}"
            )

        # Check for required API keys based on providers
        _check_provider_credentials(config, issues, warnings)

        # Validate embedding configuration
        valid_embedding, embed_msg = validate_embedding_config(config)
        if not valid_embedding:
            issues.append(f"Embedding configuration error: {embed_msg}")

        # Test connections if configuration looks valid so far
        if not issues:
            _test_provider_connections(config, issues, warnings)

        # Build result message
        if issues:
            message = (
                f"Graphiti configuration has {len(issues)} issue(s):\n"
                + "\n".join(f"  - {issue}" for issue in issues)
            )
            logger.warning(f"Graphiti validation failed: {len(issues)} issues found")
        else:
            message = (
                f"Graphiti is configured and ready\n"
                f"  LLM Provider: {llm_provider}\n"
                f"  Embedder Provider: {embedder_provider}"
            )
            logger.info(
                f"Graphiti validation passed: {llm_provider} + {embedder_provider}"
            )

        return {
            "valid": len(issues) == 0,
            "enabled": True,
            "llm_provider": llm_provider,
            "embedder_provider": embedder_provider,
            "issues": issues,
            "warnings": warnings,
            "message": message,
        }

    except Exception as e:
        error_msg = f"Failed to validate Graphiti configuration: {e}"
        logger.error(error_msg, exc_info=True)
        return {
            "valid": False,
            "enabled": False,
            "llm_provider": "unknown",
            "embedder_provider": "unknown",
            "issues": [error_msg],
            "warnings": [],
            "message": error_msg,
        }


def _check_provider_credentials(
    config: GraphitiConfig, issues: list[str], warnings: list[str]
) -> None:
    """
    Check that required API keys are present for selected providers.

    Args:
        config: GraphitiConfig to validate
        issues: List to append blocking issues to
        warnings: List to append warnings to
    """
    llm_provider = config.llm_provider
    embedder_provider = config.embedder_provider

    # Check LLM provider credentials
    if llm_provider == "openai" and not config.openai_api_key:
        issues.append(
            "OpenAI LLM provider requires OPENAI_API_KEY environment variable"
        )
    elif llm_provider == "anthropic" and not config.anthropic_api_key:
        issues.append(
            "Anthropic LLM provider requires ANTHROPIC_API_KEY environment variable"
        )
    elif llm_provider == "azure_openai":
        if not config.azure_openai_api_key:
            issues.append(
                "Azure OpenAI requires AZURE_OPENAI_API_KEY environment variable"
            )
        if not config.azure_openai_base_url:
            issues.append(
                "Azure OpenAI requires AZURE_OPENAI_BASE_URL environment variable"
            )
        if not config.azure_openai_llm_deployment:
            issues.append(
                "Azure OpenAI requires AZURE_OPENAI_LLM_DEPLOYMENT environment variable"
            )
    elif llm_provider == "google" and not config.google_api_key:
        issues.append("Google AI provider requires GOOGLE_API_KEY environment variable")
    elif llm_provider == "openrouter" and not config.openrouter_api_key:
        issues.append(
            "OpenRouter provider requires OPENROUTER_API_KEY environment variable"
        )
    elif llm_provider == "ollama":
        if not config.ollama_llm_model:
            issues.append(
                "Ollama LLM provider requires OLLAMA_LLM_MODEL environment variable"
            )
        # Ollama runs locally, so we'll test connection instead of API key

    # Check embedder provider credentials
    if embedder_provider == "openai" and not config.openai_api_key:
        issues.append("OpenAI embedder requires OPENAI_API_KEY environment variable")
    elif embedder_provider == "voyage" and not config.voyage_api_key:
        issues.append("Voyage AI embedder requires VOYAGE_API_KEY environment variable")
    elif embedder_provider == "azure_openai":
        if not config.azure_openai_api_key:
            issues.append(
                "Azure OpenAI requires AZURE_OPENAI_API_KEY environment variable"
            )
        if not config.azure_openai_base_url:
            issues.append(
                "Azure OpenAI requires AZURE_OPENAI_BASE_URL environment variable"
            )
        if not config.azure_openai_embedding_deployment:
            issues.append(
                "Azure OpenAI requires AZURE_OPENAI_EMBEDDING_DEPLOYMENT environment variable"
            )
    elif embedder_provider == "google" and not config.google_api_key:
        issues.append("Google AI embedder requires GOOGLE_API_KEY environment variable")
    elif embedder_provider == "openrouter" and not config.openrouter_api_key:
        issues.append(
            "OpenRouter embedder requires OPENROUTER_API_KEY environment variable"
        )
    elif embedder_provider == "ollama":
        if not config.ollama_embedding_model:
            issues.append(
                "Ollama embedder requires OLLAMA_EMBEDDING_MODEL environment variable"
            )
        if not config.ollama_embedding_dim:
            warnings.append(
                "Ollama embedder should specify OLLAMA_EMBEDDING_DIM for best results"
            )

    # Warn if using Anthropic for LLM without a proper embedder
    if llm_provider == "anthropic" and embedder_provider == "anthropic":
        warnings.append(
            "Anthropic does not provide embeddings. "
            "Consider using Voyage AI (GRAPHITI_EMBEDDER_PROVIDER=voyage) "
            "or OpenAI embeddings."
        )


def _test_provider_connections(
    config: GraphitiConfig, issues: list[str], warnings: list[str]
) -> None:
    """
    Test connections to configured providers.

    Args:
        config: GraphitiConfig to test
        issues: List to append blocking issues to
        warnings: List to append warnings to
    """
    # Test Ollama connection if using Ollama
    if config.llm_provider == "ollama" or config.embedder_provider == "ollama":
        success, msg = asyncio.run(test_ollama_connection(config.ollama_base_url))
        if not success:
            issues.append(f"Ollama connection test failed: {msg}")
        else:
            logger.debug(msg)

    # Test LLM connection
    try:
        success, msg = asyncio.run(test_llm_connection(config))
        if not success:
            issues.append(f"LLM connection test failed: {msg}")
        else:
            logger.debug(msg)
    except Exception as e:
        issues.append(f"LLM connection test error: {e}")

    # Test embedder connection
    try:
        success, msg = asyncio.run(test_embedder_connection(config))
        if not success:
            issues.append(f"Embedder connection test failed: {msg}")
        else:
            logger.debug(msg)
    except Exception as e:
        issues.append(f"Embedder connection test error: {e}")


def get_graphiti_status() -> dict[str, str | bool]:
    """
    Get current Graphiti configuration status.

    Returns:
        dict: Dictionary containing:
            - enabled: Whether Graphiti is enabled
            - llm_provider: Current LLM provider
            - embedder_provider: Current embedder provider
            - database: Database name
            - db_path: Database storage path

    Useful for displaying current configuration in setup wizard.
    """
    try:
        enabled = is_graphiti_enabled()
        if not enabled:
            return {
                "enabled": False,
                "llm_provider": "none",
                "embedder_provider": "none",
                "database": "none",
                "db_path": "none",
            }

        config = GraphitiConfig.from_env()
        return {
            "enabled": True,
            "llm_provider": config.llm_provider,
            "embedder_provider": config.embedder_provider,
            "database": config.database,
            "db_path": config.db_path,
        }
    except Exception as e:
        logger.error(f"Failed to get Graphiti status: {e}")
        return {
            "enabled": False,
            "llm_provider": "error",
            "embedder_provider": "error",
            "database": "error",
            "db_path": str(e),
        }
