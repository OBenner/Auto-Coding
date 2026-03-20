"""
Provider Fallback Chain
=======================

Defines the provider degradation path for handling API failures or rate limits.
When a provider fails, the system will automatically retry with the next provider
in the fallback chain.

Multi-Provider Fallback Strategy:
- Each provider is tried in sequence when errors occur
- Circuit breakers prevent repeated calls to failing providers
- Final fallback to local Ollama models when available

Provider Fallback Chain:
- Claude (Anthropic) → OpenAI → Google Gemini → Ollama (local)
- Each provider has its own circuit breaker for failure tracking
- Automatic retry with exponential backoff per provider

Example:
    >>> from core.provider_fallback import retry_with_provider_fallback
    >>> def create_session(provider: str):
    ...     # Create provider-specific session
    ...     return session
    >>> result = retry_with_provider_fallback(create_session, "claude")
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from core.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# Per-provider circuit breakers
_provider_breakers: dict[str, CircuitBreaker] = {}


def reset_circuit_breakers() -> None:
    """Reset all per-provider circuit breakers. Useful for testing."""
    _provider_breakers.clear()


# Comprehensive provider fallback chain mapping
# Maps each provider identifier to its fallback sequence
PROVIDER_FALLBACK_CHAIN: dict[str, list[str]] = {
    # ==================== PRIMARY PROVIDERS ====================
    # Claude (Anthropic) - Most capable, preferred default
    "claude": ["openai", "google", "ollama"],
    # OpenAI - Strong alternative with GPT-4 family
    "openai": ["google", "ollama"],
    # Google Gemini - Good balance of capability and cost
    "google": ["ollama"],
    # Ollama - Local fallback, no external dependencies
    "ollama": [],
    # ==================== SPECIALIZED PROVIDERS ====================
    # LiteLLM - Unified interface, no specific fallback
    "litellm": ["claude", "openai", "google", "ollama"],
    # OpenRouter - Cloud routing service
    "openrouter": ["claude", "openai", "google", "ollama"],
    # ZhipuAI - Chinese language models
    "zhipuai": ["claude", "openai", "google", "ollama"],
}

# Type variable for return value
T = TypeVar("T")


def get_fallback_provider(provider: str) -> str | None:
    """
    Get the next fallback provider in the chain for a given provider.

    This function looks up the fallback chain for the specified provider
    and returns the first fallback provider, or None if no fallback exists.

    Args:
        provider: Provider identifier (e.g., "claude", "openai", "google")

    Returns:
        Next fallback provider identifier, or None if no fallback exists

    Examples:
        >>> get_fallback_provider("claude")
        'openai'

        >>> get_fallback_provider("openai")
        'google'

        >>> get_fallback_provider("google")
        'ollama'

        >>> get_fallback_provider("ollama")
        None

        >>> get_fallback_provider("unknown-provider")
        None
    """
    # Normalize provider name to lowercase
    provider_normalized = provider.lower()

    # Get fallback chain
    fallback_chain = PROVIDER_FALLBACK_CHAIN.get(provider_normalized, [])

    # Return first fallback, or None if chain is empty
    if fallback_chain:
        return fallback_chain[0]
    return None


def retry_with_provider_fallback[T](
    callable_fn: Callable[[str], T],
    provider: str,
    max_retries_per_provider: int = 1,
) -> T:
    """
    Retry an API call with fallback providers when errors occur.

    This function attempts to execute a callable with the provided provider.
    If an API error occurs (rate limit, connection error, overloaded, etc.),
    it will automatically retry with the next provider in the fallback chain.

    Args:
        callable_fn: Function that accepts a provider parameter and returns a result.
                     Example: lambda p: create_engine_provider_session(provider=p)
        provider: Initial provider to try (e.g., "claude", "openai", "google")
        max_retries_per_provider: Number of retries per provider before falling back (default: 1)

    Returns:
        Result from the callable function

    Raises:
        Exception: The final exception if all fallback providers fail

    Example:
        >>> def make_api_call(provider: str) -> dict:
        ...     return client.create_agent_session(provider=provider)
        >>> result = retry_with_provider_fallback(make_api_call, "claude")
    """
    # Normalize provider name to lowercase
    provider_normalized = provider.lower()

    # Build the full attempt sequence: [initial_provider] + fallbacks
    fallback_providers = PROVIDER_FALLBACK_CHAIN.get(provider_normalized, [])
    providers_to_try = [provider] + fallback_providers

    # Log the fallback strategy at the start for debugging and reliability analysis
    if fallback_providers:
        logger.info(
            f"Starting request with provider '{provider}' "
            f"(fallback chain: {' -> '.join(providers_to_try)})"
        )
    else:
        logger.info(f"Starting request with provider '{provider}' (no fallback available)")

    last_exception: Exception | None = None

    for attempt_num, current_provider in enumerate(providers_to_try, start=1):
        # Determine if this is the initial attempt or a fallback
        is_fallback = attempt_num > 1

        # Get or create a circuit breaker for this provider
        provider_key = current_provider.lower()
        if provider_key not in _provider_breakers:
            _provider_breakers[provider_key] = CircuitBreaker(
                name=f"provider_{provider_key}",
                failure_threshold=3,
                recovery_timeout=60.0,
            )
        breaker = _provider_breakers[provider_key]

        # Check if circuit breaker allows execution
        if not breaker.can_execute():
            logger.warning(
                f"Circuit breaker OPEN for provider '{current_provider}' — skipping"
            )
            # Skip this provider and try next in chain
            continue

        # Log fallback transition
        if is_fallback:
            logger.warning(
                f"Falling back to provider '{current_provider}' "
                f"(attempt {attempt_num}/{len(providers_to_try)})"
            )

        # Attempt the call with retry logic per provider
        for retry_num in range(max_retries_per_provider):
            try:
                # Execute the callable with current provider
                result = callable_fn(current_provider)

                # Success! Reset the circuit breaker
                breaker.record_success()

                # Log success (especially important for fallback cases)
                if is_fallback or retry_num > 0:
                    logger.info(
                        f"Request succeeded with provider '{current_provider}' "
                        f"(attempt {attempt_num}, retry {retry_num + 1})"
                    )

                return result

            except Exception as e:
                # Record the exception
                last_exception = e

                # Determine if this is a retryable error
                is_retryable = _is_retryable_error(e)

                # Log the error with context
                log_message = (
                    f"Error with provider '{current_provider}' "
                    f"(attempt {attempt_num}, retry {retry_num + 1}/{max_retries_per_provider}): "
                    f"{type(e).__name__}: {e}"
                )

                if is_retryable and retry_num < max_retries_per_provider - 1:
                    # Retryable error, will retry with same provider
                    logger.warning(f"{log_message} — retrying with same provider")
                elif is_retryable and current_provider != providers_to_try[-1]:
                    # Retryable error, exhausted retries, will try next provider
                    logger.warning(f"{log_message} — will try next provider")
                    breaker.record_failure(e)
                else:
                    # Non-retryable error or last provider failed
                    logger.error(f"{log_message} — {'no fallback available' if current_provider == providers_to_try[-1] else 'trying next provider'}")
                    breaker.record_failure(e)

                # If this is the last retry for this provider, break to try next provider
                if retry_num == max_retries_per_provider - 1:
                    break

    # All providers exhausted — raise the last exception
    providers_tried = " -> ".join(providers_to_try)
    error_message = (
        f"All providers exhausted (tried: {providers_tried}). "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    )
    logger.error(error_message)

    # Raise the last exception with additional context
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError(error_message)


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.

    Retryable errors include:
    - Rate limit errors (429)
    - Connection errors
    - Timeout errors
    - Service overloaded (503)
    - Internal server errors (500)

    Non-retryable errors include:
    - Authentication errors (401, 403)
    - Invalid request errors (400)
    - Not found errors (404)
    - Provider not installed errors

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable, False otherwise
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Rate limit errors (always retryable)
    if "rate limit" in error_str or "429" in error_str:
        return True

    # Connection/network errors (always retryable)
    if any(
        keyword in error_str
        for keyword in ["connection", "timeout", "timed out", "network"]
    ):
        return True

    # Service overloaded/unavailable (always retryable)
    if any(keyword in error_str for keyword in ["overloaded", "503", "502", "504"]):
        return True

    # Internal server errors (retryable)
    if "500" in error_str or "internal server error" in error_str:
        return True

    # Provider not installed (not retryable - missing dependency)
    if "providernotinstalled" in error_type.lower():
        return False

    # Authentication errors (not retryable - need valid credentials)
    if any(keyword in error_str for keyword in ["401", "403", "unauthorized", "forbidden", "authentication"]):
        return False

    # Invalid request errors (not retryable - bad input)
    if any(keyword in error_str for keyword in ["400", "invalid", "bad request"]):
        return False

    # Not found errors (not retryable)
    if "404" in error_str or "not found" in error_str:
        return False

    # Default: treat as retryable for safety (better to retry than fail)
    logger.debug(f"Unknown error type '{error_type}', treating as retryable: {error}")
    return True
