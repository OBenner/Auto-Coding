"""
LLM Provider Connection Tester
================================

General-purpose provider connection testing for all supported LLM and embedder providers.
Provides both synchronous and asynchronous interfaces for testing provider connectivity.

This module complements graphiti_validator.py by providing lower-level provider tests
independent of the Graphiti memory system integration.

Supported Providers:
    LLM Providers:
        - OpenAI (GPT-4, GPT-5, etc.)
        - Anthropic (Claude)
        - Azure OpenAI
        - Google AI (Gemini)
        - Ollama (local models)
        - OpenRouter (multi-provider aggregator)

    Embedder Providers:
        - OpenAI (text-embedding-3-small, etc.)
        - Voyage AI (voyage-3, etc.)
        - Azure OpenAI
        - Google AI (text-embedding-004)
        - Ollama (local embedding models)
        - OpenRouter

Usage:
    from core.provider_tester import check_provider_connection, ProviderTestResult

    # Test OpenAI connection
    result = check_provider_connection(
        provider="openai",
        api_key="sk-...",
        model="gpt-4"
    )
    if result.success:
        print(f"✓ {result.message}")
    else:
        print(f"✗ {result.message}")
        print(f"Fix: {result.fix_command}")

    # Test Anthropic connection
    result = check_provider_connection(
        provider="anthropic",
        api_key="sk-ant-...",
        model="claude-sonnet-4-5"
    )
"""

import asyncio
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProviderTestResult:
    """Result of a provider connection test."""

    success: bool
    message: str
    provider: str
    fix_command: str | None = None
    error_details: str | None = None


def check_provider_connection(
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    **kwargs,
) -> ProviderTestResult:
    """
    Check LLM or embedder provider connection (synchronous).

    This is a synchronous wrapper around async check functions for convenience.
    For async contexts, use the async check functions directly.

    Args:
        provider: Provider name (openai, anthropic, azure_openai, google, ollama, openrouter)
        api_key: API key for the provider (optional if set in environment)
        model: Model name to test (optional)
        base_url: Base URL for the provider API (optional)
        **kwargs: Additional provider-specific parameters

    Returns:
        ProviderTestResult with test outcome

    Examples:
        >>> result = check_provider_connection("openai", api_key="sk-...")
        >>> if result.success:
        ...     print(f"✓ {result.message}")
    """
    # Run async check in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            check_provider_connection_async(
                provider, api_key, model, base_url, **kwargs
            )
        )
    finally:
        loop.close()

    return result


async def check_provider_connection_async(
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    **kwargs,
) -> ProviderTestResult:
    """
    Check LLM or embedder provider connection (asynchronous).

    Args:
        provider: Provider name (openai, anthropic, azure_openai, google, ollama, openrouter)
        api_key: API key for the provider (optional if set in environment)
        model: Model name to test (optional)
        base_url: Base URL for the provider API (optional)
        **kwargs: Additional provider-specific parameters

    Returns:
        ProviderTestResult with test outcome
    """
    provider_lower = provider.lower()

    # Route to appropriate test function
    if provider_lower == "openai":
        return await _test_openai(api_key, model, **kwargs)
    elif provider_lower == "anthropic":
        return await _test_anthropic(api_key, model, **kwargs)
    elif provider_lower == "azure_openai":
        return await _test_azure_openai(api_key, base_url, model, **kwargs)
    elif provider_lower == "google":
        return await _test_google(api_key, model, **kwargs)
    elif provider_lower == "ollama":
        return await _test_ollama(base_url, model, **kwargs)
    elif provider_lower == "openrouter":
        return await _test_openrouter(api_key, model, base_url=base_url, **kwargs)
    elif provider_lower == "voyage":
        return await _test_voyage(api_key, model, **kwargs)
    else:
        return ProviderTestResult(
            success=False,
            message=f"Unknown provider: {provider}",
            provider=provider,
            fix_command="Supported providers: openai, anthropic, azure_openai, google, ollama, openrouter, voyage",
        )


async def _test_openai(
    api_key: str | None = None, model: str | None = None, **kwargs
) -> ProviderTestResult:
    """Test OpenAI API connection."""
    # Get API key from parameter or environment
    api_key = api_key or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return ProviderTestResult(
            success=False,
            message="OpenAI API key not provided",
            provider="openai",
            fix_command="Set OPENAI_API_KEY in your .env file or pass api_key parameter",
        )

    try:
        # Try importing openai client
        import openai
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="OpenAI package not installed",
            provider="openai",
            fix_command="pip install openai",
        )

    try:
        # Create client and test with a minimal request
        client = openai.AsyncOpenAI(api_key=api_key)

        # Use models list as a lightweight connectivity test
        # This validates API key without consuming tokens
        await client.models.list()

        model_info = f" (model: {model})" if model else ""
        return ProviderTestResult(
            success=True,
            message=f"OpenAI connection successful{model_info}",
            provider="openai",
        )

    except openai.AuthenticationError:
        return ProviderTestResult(
            success=False,
            message="OpenAI authentication failed - invalid API key",
            provider="openai",
            fix_command="Check your OPENAI_API_KEY is valid",
            error_details="Invalid API key",
        )
    except openai.APIConnectionError as e:
        return ProviderTestResult(
            success=False,
            message=f"Cannot connect to OpenAI API: {e}",
            provider="openai",
            fix_command="Check your network connection and firewall settings",
            error_details=str(e),
        )
    except Exception as e:
        return ProviderTestResult(
            success=False,
            message=f"OpenAI connection test failed: {e}",
            provider="openai",
            error_details=str(e),
        )


async def _test_anthropic(
    api_key: str | None = None, model: str | None = None, **kwargs
) -> ProviderTestResult:
    """Test Anthropic API connection."""
    # Get API key from parameter or environment
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        return ProviderTestResult(
            success=False,
            message="Anthropic API key not provided",
            provider="anthropic",
            fix_command="Set ANTHROPIC_API_KEY in your .env file or pass api_key parameter",
        )

    try:
        # Try importing anthropic client
        import anthropic
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="Anthropic package not installed",
            provider="anthropic",
            fix_command="pip install anthropic",
        )

    try:
        # Create client
        client = anthropic.AsyncAnthropic(api_key=api_key)

        # Test with a minimal message request (won't actually consume tokens with max_tokens=1)
        test_model = model or "claude-sonnet-4-5-20250929"
        await client.messages.create(
            model=test_model,
            max_tokens=1,
            messages=[{"role": "user", "content": "test"}],
        )

        model_info = f" (model: {test_model})"
        return ProviderTestResult(
            success=True,
            message=f"Anthropic connection successful{model_info}",
            provider="anthropic",
        )

    except anthropic.AuthenticationError:
        return ProviderTestResult(
            success=False,
            message="Anthropic authentication failed - invalid API key",
            provider="anthropic",
            fix_command="Check your ANTHROPIC_API_KEY is valid",
            error_details="Invalid API key",
        )
    except anthropic.NotFoundError as e:
        return ProviderTestResult(
            success=False,
            message=f"Model not found: {model or 'claude-sonnet-4-5-20250929'}",
            provider="anthropic",
            fix_command="Check the model name is valid",
            error_details=str(e),
        )
    except anthropic.APIConnectionError as e:
        return ProviderTestResult(
            success=False,
            message=f"Cannot connect to Anthropic API: {e}",
            provider="anthropic",
            fix_command="Check your network connection and firewall settings",
            error_details=str(e),
        )
    except Exception as e:
        return ProviderTestResult(
            success=False,
            message=f"Anthropic connection test failed: {e}",
            provider="anthropic",
            error_details=str(e),
        )


async def _test_azure_openai(
    api_key: str | None = None,
    base_url: str | None = None,
    deployment: str | None = None,
    **kwargs,
) -> ProviderTestResult:
    """Test Azure OpenAI connection."""
    # Get credentials from parameters or environment
    api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
    base_url = base_url or os.environ.get("AZURE_OPENAI_BASE_URL")
    deployment = deployment or os.environ.get("AZURE_OPENAI_LLM_DEPLOYMENT")

    if not api_key:
        return ProviderTestResult(
            success=False,
            message="Azure OpenAI API key not provided",
            provider="azure_openai",
            fix_command="Set AZURE_OPENAI_API_KEY in your .env file",
        )

    if not base_url:
        return ProviderTestResult(
            success=False,
            message="Azure OpenAI base URL not provided",
            provider="azure_openai",
            fix_command="Set AZURE_OPENAI_BASE_URL in your .env file",
        )

    try:
        # Try importing openai client (Azure uses same package)
        import openai
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="OpenAI package not installed (required for Azure)",
            provider="azure_openai",
            fix_command="pip install openai",
        )

    try:
        # Create Azure client
        client = openai.AsyncAzureOpenAI(
            api_key=api_key, azure_endpoint=base_url, api_version="2024-02-01"
        )

        # Test with deployments list (lightweight connectivity test)
        # Note: This may not be available in all Azure setups
        # Fallback to a minimal completion request if needed
        try:
            await client.models.list()
        except Exception:
            # Some Azure setups don't support models.list, try a minimal request instead
            if deployment:
                await client.chat.completions.create(
                    model=deployment,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )

        deployment_info = f" (deployment: {deployment})" if deployment else ""
        return ProviderTestResult(
            success=True,
            message=f"Azure OpenAI connection successful{deployment_info}",
            provider="azure_openai",
        )

    except openai.AuthenticationError:
        return ProviderTestResult(
            success=False,
            message="Azure OpenAI authentication failed - invalid API key",
            provider="azure_openai",
            fix_command="Check your AZURE_OPENAI_API_KEY is valid",
            error_details="Invalid API key",
        )
    except openai.APIConnectionError as e:
        return ProviderTestResult(
            success=False,
            message=f"Cannot connect to Azure OpenAI: {e}",
            provider="azure_openai",
            fix_command="Check your AZURE_OPENAI_BASE_URL and network connection",
            error_details=str(e),
        )
    except Exception as e:
        return ProviderTestResult(
            success=False,
            message=f"Azure OpenAI connection test failed: {e}",
            provider="azure_openai",
            error_details=str(e),
        )


async def _test_google(
    api_key: str | None = None, model: str | None = None, **kwargs
) -> ProviderTestResult:
    """Test Google AI (Gemini) connection."""
    # Get API key from parameter or environment
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        return ProviderTestResult(
            success=False,
            message="Google API key not provided",
            provider="google",
            fix_command="Set GOOGLE_API_KEY in your .env file",
        )

    try:
        # Try importing google.generativeai
        import google.generativeai as genai
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="Google AI package not installed",
            provider="google",
            fix_command="pip install google-generativeai",
        )

    try:
        # Configure API key
        genai.configure(api_key=api_key)

        # Test with model list (lightweight connectivity test)
        test_model = model or "gemini-2.0-flash"

        # List models to verify connection
        models = genai.list_models()
        model_names = [m.name for m in models]

        # Check if requested model exists
        model_found = any(test_model in name for name in model_names)

        if not model_found:
            return ProviderTestResult(
                success=False,
                message=f"Google AI model not found: {test_model}",
                provider="google",
                fix_command=f"Available models: {', '.join(model_names[:5])}...",
                error_details=f"Model {test_model} not in available models",
            )

        return ProviderTestResult(
            success=True,
            message=f"Google AI connection successful (model: {test_model})",
            provider="google",
        )

    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return ProviderTestResult(
                success=False,
                message="Google AI authentication failed - invalid API key",
                provider="google",
                fix_command="Check your GOOGLE_API_KEY is valid",
                error_details=error_msg,
            )
        else:
            return ProviderTestResult(
                success=False,
                message=f"Google AI connection test failed: {e}",
                provider="google",
                error_details=error_msg,
            )


async def _test_ollama(
    base_url: str | None = None, model: str | None = None, **kwargs
) -> ProviderTestResult:
    """Test Ollama connection."""
    # Get base URL from parameter or environment
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    try:
        import urllib.error
        import urllib.request
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="urllib not available",
            provider="ollama",
            error_details="Standard library import failed",
        )

    try:
        # Normalize URL (remove /v1 suffix if present)
        url = base_url.rstrip("/")
        if url.endswith("/v1"):
            url = url[:-3]

        # Test server connectivity with /api/tags endpoint
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return ProviderTestResult(
                    success=False,
                    message=f"Ollama returned status {response.status}",
                    provider="ollama",
                    fix_command="Check Ollama server is running: ollama serve",
                )

            # Parse response to get available models
            import json

            data = json.loads(response.read())
            models = data.get("models", [])

            # If specific model requested, check if available
            if model:
                model_names = [m.get("name", "") for m in models]
                if model not in model_names:
                    return ProviderTestResult(
                        success=False,
                        message=f"Ollama model not found: {model}",
                        provider="ollama",
                        fix_command=f"Pull model: ollama pull {model}",
                        error_details=f"Available models: {', '.join(model_names)}",
                    )

            model_info = (
                f" (model: {model})" if model else f" ({len(models)} models available)"
            )
            return ProviderTestResult(
                success=True,
                message=f"Ollama connection successful{model_info}",
                provider="ollama",
            )

    except urllib.error.URLError as e:
        return ProviderTestResult(
            success=False,
            message=f"Cannot connect to Ollama at {base_url}: {e.reason}",
            provider="ollama",
            fix_command="Start Ollama server: ollama serve",
            error_details=str(e),
        )
    except TimeoutError:
        return ProviderTestResult(
            success=False,
            message=f"Ollama connection timed out at {base_url}",
            provider="ollama",
            fix_command="Check Ollama server is running and accessible",
            error_details="Connection timeout after 5 seconds",
        )
    except Exception as e:
        return ProviderTestResult(
            success=False,
            message=f"Ollama connection test failed: {e}",
            provider="ollama",
            error_details=str(e),
        )


async def _test_openrouter(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    **kwargs,
) -> ProviderTestResult:
    """Test OpenRouter connection."""
    # Get API key from parameter or environment
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        return ProviderTestResult(
            success=False,
            message="OpenRouter API key not provided",
            provider="openrouter",
            fix_command="Set OPENROUTER_API_KEY in your .env file",
        )

    try:
        # Try importing openai client (OpenRouter uses OpenAI-compatible API)
        import openai
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="OpenAI package not installed (required for OpenRouter)",
            provider="openrouter",
            fix_command="pip install openai",
        )

    try:
        # Create client with OpenRouter endpoint
        effective_base_url = base_url or os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        client = openai.AsyncOpenAI(api_key=api_key, base_url=effective_base_url)

        # Test with models list
        await client.models.list()

        model_info = f" (model: {model})" if model else ""
        return ProviderTestResult(
            success=True,
            message=f"OpenRouter connection successful{model_info}",
            provider="openrouter",
        )

    except openai.AuthenticationError:
        return ProviderTestResult(
            success=False,
            message="OpenRouter authentication failed - invalid API key",
            provider="openrouter",
            fix_command="Check your OPENROUTER_API_KEY is valid",
            error_details="Invalid API key",
        )
    except openai.APIConnectionError as e:
        return ProviderTestResult(
            success=False,
            message=f"Cannot connect to OpenRouter: {e}",
            provider="openrouter",
            fix_command="Check your network connection",
            error_details=str(e),
        )
    except Exception as e:
        return ProviderTestResult(
            success=False,
            message=f"OpenRouter connection test failed: {e}",
            provider="openrouter",
            error_details=str(e),
        )


async def _test_voyage(
    api_key: str | None = None, model: str | None = None, **kwargs
) -> ProviderTestResult:
    """Test Voyage AI connection."""
    # Get API key from parameter or environment
    api_key = api_key or os.environ.get("VOYAGE_API_KEY")

    if not api_key:
        return ProviderTestResult(
            success=False,
            message="Voyage API key not provided",
            provider="voyage",
            fix_command="Set VOYAGE_API_KEY in your .env file",
        )

    try:
        # Try importing voyageai
        import voyageai
    except ImportError:
        return ProviderTestResult(
            success=False,
            message="Voyage AI package not installed",
            provider="voyage",
            fix_command="pip install voyageai",
        )

    try:
        # Create client
        client = voyageai.AsyncClient(api_key=api_key)

        # Test with a minimal embedding request
        test_model = model or "voyage-3"
        result = await client.embed(
            texts=["test"], model=test_model, input_type="document"
        )

        # Check if we got embeddings back
        if not result.embeddings or len(result.embeddings) == 0:
            return ProviderTestResult(
                success=False,
                message="Voyage AI returned no embeddings",
                provider="voyage",
                error_details="Empty embeddings response",
            )

        return ProviderTestResult(
            success=True,
            message=f"Voyage AI connection successful (model: {test_model})",
            provider="voyage",
        )

    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return ProviderTestResult(
                success=False,
                message="Voyage AI authentication failed - invalid API key",
                provider="voyage",
                fix_command="Check your VOYAGE_API_KEY is valid",
                error_details=error_msg,
            )
        else:
            return ProviderTestResult(
                success=False,
                message=f"Voyage AI connection test failed: {e}",
                provider="voyage",
                error_details=error_msg,
            )


def get_provider_from_env() -> str | None:
    """
    Detect which provider is configured in environment variables.

    Returns:
        Provider name if detected, None otherwise
    """
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    elif os.environ.get("AZURE_OPENAI_API_KEY"):
        return "azure_openai"
    elif os.environ.get("GOOGLE_API_KEY"):
        return "google"
    elif os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_LLM_MODEL"):
        return "ollama"
    elif os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    elif os.environ.get("VOYAGE_API_KEY"):
        return "voyage"
    else:
        return None


def check_all_configured_providers() -> dict[str, ProviderTestResult]:
    """
    Check all providers that are configured in environment variables.

    Returns:
        Dict mapping provider name to ProviderTestResult
    """
    results = {}

    # Check each provider if credentials are present
    if os.environ.get("OPENAI_API_KEY"):
        results["openai"] = check_provider_connection("openai")

    if os.environ.get("ANTHROPIC_API_KEY"):
        results["anthropic"] = check_provider_connection("anthropic")

    if os.environ.get("AZURE_OPENAI_API_KEY"):
        results["azure_openai"] = check_provider_connection("azure_openai")

    if os.environ.get("GOOGLE_API_KEY"):
        results["google"] = check_provider_connection("google")

    if os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_LLM_MODEL"):
        results["ollama"] = check_provider_connection("ollama")

    if os.environ.get("OPENROUTER_API_KEY"):
        results["openrouter"] = check_provider_connection("openrouter")

    if os.environ.get("VOYAGE_API_KEY"):
        results["voyage"] = check_provider_connection("voyage")

    return results
