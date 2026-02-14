"""
Model Fallback Chain
====================

Defines the model degradation path for handling API failures or rate limits.
When a model fails, the system will automatically retry with the next model
in the fallback chain.

Fallback Strategy:
- opus -> sonnet -> haiku (highest capability to lowest cost)
- sonnet -> haiku
- haiku -> (no fallback, final attempt)
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from core.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# Per-model circuit breakers
_model_breakers: dict[str, CircuitBreaker] = {}

# Model fallback chain mapping
# Maps each model shorthand to its fallback sequence
MODEL_FALLBACK_CHAIN: dict[str, list[str]] = {
    "opus": ["sonnet", "haiku"],  # If opus fails, try sonnet, then haiku
    "sonnet": ["haiku"],  # If sonnet fails, try haiku
    "haiku": [],  # No fallback for haiku (final attempt)
}

# Type variable for return value
T = TypeVar("T")


def retry_with_fallback[T](
    callable_fn: Callable[[str], T],
    model: str,
    max_retries_per_model: int = 1,
) -> T:
    """
    Retry an API call with fallback models when errors occur.

    This function attempts to execute a callable with the provided model.
    If an API error occurs (rate limit, connection error, overloaded, etc.),
    it will automatically retry with the next model in the fallback chain.

    Args:
        callable_fn: Function that accepts a model parameter and returns a result.
                     Example: lambda m: create_agent_session(model=m)
        model: Initial model to try (e.g., "opus", "sonnet", "haiku")
        max_retries_per_model: Number of retries per model before falling back (default: 1)

    Returns:
        Result from the callable function

    Raises:
        Exception: The final exception if all fallback models fail

    Example:
        >>> def make_api_call(model: str) -> dict:
        ...     return client.create_agent_session(model=model)
        >>> result = retry_with_fallback(make_api_call, "opus")
    """
    # Normalize model name (extract shorthand from full model ID)
    model_shorthand = _extract_model_shorthand(model)

    # Build the full attempt sequence: [initial_model] + fallbacks
    fallback_models = MODEL_FALLBACK_CHAIN.get(model_shorthand, [])
    models_to_try = [model] + fallback_models

    # Log the fallback strategy at the start for debugging and cost analysis
    if fallback_models:
        logger.info(
            f"Starting request with model '{model}' "
            f"(fallback chain: {' -> '.join(models_to_try)})"
        )
    else:
        logger.info(f"Starting request with model '{model}' (no fallback available)")

    last_exception: Exception | None = None

    for attempt_num, current_model in enumerate(models_to_try, start=1):
        # Determine if this is the initial attempt or a fallback
        is_fallback = attempt_num > 1

        # Get or create a circuit breaker for this model
        model_key = _extract_model_shorthand(current_model)
        if model_key not in _model_breakers:
            _model_breakers[model_key] = CircuitBreaker(
                name=f"model_{model_key}",
                failure_threshold=3,
                recovery_timeout=60.0,
            )
        breaker = _model_breakers[model_key]

        # Skip this model if its circuit breaker is open
        if not breaker.can_execute():
            logger.warning(
                f"[SKIP] Circuit breaker open for model '{current_model}' — "
                f"skipping to next fallback"
            )
            continue

        if is_fallback:
            # Log fallback transition with cost implications
            logger.warning(
                f"[FALLBACK] Switching from '{model}' to '{current_model}' "
                f"(attempt {attempt_num}/{len(models_to_try)}) - cost implications may apply"
            )
        else:
            # Log initial attempt
            logger.debug(f"Attempting request with initial model '{current_model}'")

        # Try the current model with retries
        for retry in range(max_retries_per_model):
            try:
                result = callable_fn(current_model)

                # Record success on the circuit breaker
                breaker.record_success()

                # Log success with appropriate context for cost analysis
                if is_fallback:
                    logger.info(
                        f"[SUCCESS] Request completed with fallback model '{current_model}' "
                        f"(attempt {attempt_num}/{len(models_to_try)}, retry {retry + 1}/{max_retries_per_model})"
                    )
                elif retry > 0:
                    logger.info(
                        f"[SUCCESS] Request completed with model '{current_model}' after {retry} retries"
                    )
                else:
                    logger.debug(
                        f"[SUCCESS] Request completed with initial model '{current_model}'"
                    )

                return result

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                error_msg = str(e)

                # Check if this is a retryable API error
                is_retryable = _is_retryable_error(e)

                if is_retryable:
                    breaker.record_failure(e)
                    if retry < max_retries_per_model - 1:
                        logger.warning(
                            f"[RETRY] API error with model '{current_model}' ({error_type}: {error_msg}). "
                            f"Retrying... (retry {retry + 1}/{max_retries_per_model}, attempt {attempt_num}/{len(models_to_try)})"
                        )
                        continue  # Retry with same model
                    else:
                        logger.warning(
                            f"[EXHAUSTED] Max retries reached for model '{current_model}' ({error_type}: {error_msg}). "
                            f"Moving to next model in fallback chain."
                        )
                        break  # Move to next model in fallback chain
                else:
                    # Non-retryable error - raise immediately
                    logger.error(
                        f"Non-retryable error with model '{current_model}': {error_type}: {error_msg}"
                    )
                    raise

    # All models exhausted - raise the last exception
    if last_exception:
        logger.error(
            f"[FAILED] All fallback models exhausted after trying: {' -> '.join(models_to_try)}. "
            f"Final error: {type(last_exception).__name__}: {last_exception}"
        )
        raise last_exception
    else:
        # Should never reach here, but just in case
        raise RuntimeError(
            "retry_with_fallback failed with no exception (unexpected state)"
        )


def _extract_model_shorthand(model: str) -> str:
    """
    Extract model shorthand from full model ID.

    Examples:
        "claude-opus-4-20250514" -> "opus"
        "claude-sonnet-4-5-20250929" -> "sonnet"
        "claude-haiku-4-20250514" -> "haiku"
        "opus" -> "opus"
    """
    model_lower = model.lower()
    if "opus" in model_lower:
        return "opus"
    elif "sonnet" in model_lower:
        return "sonnet"
    elif "haiku" in model_lower:
        return "haiku"
    else:
        # Unknown model - no fallback
        return model


def _is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception is retryable (e.g., rate limit, connection error).

    Args:
        exception: The exception to check

    Returns:
        True if the error should trigger a retry/fallback, False otherwise
    """
    error_type = type(exception).__name__
    error_msg = str(exception).lower()

    # Common retryable error patterns
    retryable_patterns = [
        # API rate limiting
        "ratelimit",
        "rate limit",
        "rate_limit",
        "too many requests",
        "429",
        # Connection issues
        "connection",
        "timeout",
        "timed out",
        # Server overload
        "overloaded",
        "503",
        "502",
        "500",
        # Temporary failures
        "temporarily unavailable",
        "try again",
    ]

    # Check error type
    if any(
        pattern in error_type.lower()
        for pattern in ["ratelimit", "connection", "timeout"]
    ):
        return True

    # Check error message
    if any(pattern in error_msg for pattern in retryable_patterns):
        return True

    return False
