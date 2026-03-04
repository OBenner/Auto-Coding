"""
Multi-Provider Cost Calculator
==============================

Provides cost calculation for multiple AI model providers including
Claude (Anthropic), OpenAI, Google Gemini, and Ollama.

Components:
- MODEL_PRICING: Comprehensive pricing database for all supported models
- calculate_cost(): Calculate cost for any model and token usage
- get_model_pricing(): Get pricing info for a specific model
- get_provider_models(): List all models for a provider

Usage:
    from core.providers.cost_calculator import calculate_cost, get_model_pricing

    # Calculate cost for OpenAI GPT-4o
    cost = calculate_cost(
        model="gpt-4o",
        input_tokens=10000,
        output_tokens=2000
    )
    print(f"Cost: ${cost:.4f}")

    # Get pricing info for a model
    pricing = get_model_pricing("claude-sonnet-4-5-20250929")
    print(f"Input: ${pricing['input']}/1M tokens, Output: ${pricing['output']}/1M tokens")

Pricing Sources (as of February 2026):
- Claude: https://www.anthropic.com/pricing
- OpenAI: https://openai.com/api/pricing/
- Google Gemini: https://ai.google.dev/gemini-api/docs/pricing
- Ollama: Free (local execution)
"""

from __future__ import annotations

from typing import Any

# Comprehensive model pricing database (per 1M tokens)
# Updated February 2026
MODEL_PRICING: dict[str, dict[str, float]] = {
    # ==================== ANTHROPIC (CLAUDE) ====================
    # Claude 4.5 Opus - Most capable model
    "claude-opus-4-5-20251101": {
        "input": 15.00,
        "output": 75.00,
        "provider": "anthropic",
    },
    # Claude 4.5 Sonnet - Balanced performance and cost
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,
        "output": 15.00,
        "provider": "anthropic",
    },
    # Claude 4.5 Haiku - Fast and cost-effective
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.00,
        "provider": "anthropic",
    },
    # Extended thinking variants (same pricing as base models)
    "claude-sonnet-4-5-20250929-thinking": {
        "input": 3.00,
        "output": 15.00,
        "provider": "anthropic",
    },
    "claude-opus-4-5-20251101-thinking": {
        "input": 15.00,
        "output": 75.00,
        "provider": "anthropic",
    },
    # ==================== OPENAI ====================
    # GPT-4o - Latest GPT-4 optimized model
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
        "provider": "openai",
    },
    # GPT-4o Mini - Cost-effective variant
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
        "provider": "openai",
    },
    # GPT-4 Turbo - High performance
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00,
        "provider": "openai",
    },
    # GPT-4 - Original GPT-4
    "gpt-4": {
        "input": 30.00,
        "output": 60.00,
        "provider": "openai",
    },
    # GPT-3.5 Turbo - Fast and affordable
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50,
        "provider": "openai",
    },
    # o1 - Advanced reasoning model
    "o1": {
        "input": 15.00,
        "output": 60.00,
        "provider": "openai",
    },
    # o1-mini - Smaller reasoning model
    "o1-mini": {
        "input": 3.00,
        "output": 12.00,
        "provider": "openai",
    },
    # o3-mini - Latest mini reasoning model
    "o3-mini": {
        "input": 3.00,
        "output": 12.00,
        "provider": "openai",
    },
    # ==================== GOOGLE GEMINI ====================
    # Gemini 2.0 Flash - Latest fast model
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
        "provider": "google",
    },
    # Gemini 2.0 Flash Thinking - Advanced reasoning
    "gemini-2.0-flash-thinking": {
        "input": 0.10,
        "output": 0.40,
        "provider": "google",
    },
    # Gemini 1.5 Pro - High capability
    "gemini-1.5-pro": {
        "input": 0.15,
        "output": 0.60,
        "provider": "google",
    },
    # Gemini 1.5 Flash - Balanced performance
    "gemini-1.5-flash": {
        "input": 0.075,
        "output": 0.30,
        "provider": "google",
    },
    # ==================== OLLAMA (LOCAL) ====================
    # All Ollama models are free (local execution)
    "llama2": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "llama3": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "mistral": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "codellama": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "phi": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "gemma": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "qwen": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    "deepseek-coder": {
        "input": 0.00,
        "output": 0.00,
        "provider": "ollama",
    },
    # ==================== FALLBACK ====================
    # Default pricing for unknown models (use Sonnet pricing)
    "default": {
        "input": 3.00,
        "output": 15.00,
        "provider": "unknown",
    },
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate cost for a model operation across any provider.

    Supports Claude (Anthropic), OpenAI, Google Gemini, and Ollama models.
    If model is not found, falls back to default pricing (Claude Sonnet rates).

    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in dollars (USD)

    Examples:
        >>> calculate_cost("gpt-4o", 10000, 2000)
        0.045  # (10000/1M * $2.50) + (2000/1M * $10.00)

        >>> calculate_cost("claude-sonnet-4-5-20250929", 5000, 1000)
        0.03  # (5000/1M * $3.00) + (1000/1M * $15.00)

        >>> calculate_cost("llama2", 10000, 2000)
        0.0  # Ollama models are free
    """
    # Get pricing for model (fallback to default if not found)
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

    # Calculate cost (pricing is per 1M tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def get_model_pricing(model: str) -> dict[str, Any]:
    """
    Get pricing information for a specific model.

    Args:
        model: Model identifier

    Returns:
        Dictionary with pricing info (input, output, provider)

    Examples:
        >>> pricing = get_model_pricing("gpt-4o")
        >>> print(pricing)
        {'input': 2.50, 'output': 10.00, 'provider': 'openai'}
    """
    return MODEL_PRICING.get(model, MODEL_PRICING["default"]).copy()


def get_provider_models(provider: str) -> list[str]:
    """
    Get all models for a specific provider.

    Args:
        provider: Provider name ("anthropic", "openai", "google", "ollama")

    Returns:
        List of model identifiers for the provider

    Examples:
        >>> models = get_provider_models("openai")
        >>> print(models)
        ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', ...]
    """
    return [
        model
        for model, pricing in MODEL_PRICING.items()
        if pricing.get("provider") == provider and model != "default"
    ]


def get_all_providers() -> list[str]:
    """
    Get list of all supported providers.

    Returns:
        List of provider names

    Examples:
        >>> providers = get_all_providers()
        >>> print(providers)
        ['anthropic', 'openai', 'google', 'ollama']
    """
    providers = set()
    for pricing in MODEL_PRICING.values():
        provider = pricing.get("provider")
        if provider and provider != "unknown":
            providers.add(provider)
    return sorted(providers)


def format_cost(cost: float) -> str:
    """
    Format cost for display.

    Args:
        cost: Cost in dollars

    Returns:
        Formatted string (e.g., "$0.0450")

    Examples:
        >>> format_cost(0.045)
        '$0.0450'

        >>> format_cost(1.234)
        '$1.2340'
    """
    return f"${cost:.4f}"


def estimate_session_cost(
    model: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
) -> dict[str, Any]:
    """
    Estimate cost for a session with estimated token usage.

    Useful for showing cost previews before running agents.

    Args:
        model: Model identifier
        estimated_input_tokens: Estimated input tokens
        estimated_output_tokens: Estimated output tokens

    Returns:
        Dictionary with cost estimate and breakdown

    Examples:
        >>> estimate = estimate_session_cost("gpt-4o", 10000, 2000)
        >>> print(estimate)
        {
            'model': 'gpt-4o',
            'estimated_cost': 0.045,
            'input_tokens': 10000,
            'output_tokens': 2000,
            'input_cost': 0.025,
            'output_cost': 0.020,
            'formatted': '$0.0450'
        }
    """
    pricing = get_model_pricing(model)
    cost = calculate_cost(model, estimated_input_tokens, estimated_output_tokens)

    input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
    output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]

    return {
        "model": model,
        "provider": pricing.get("provider", "unknown"),
        "estimated_cost": cost,
        "input_tokens": estimated_input_tokens,
        "output_tokens": estimated_output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "formatted": format_cost(cost),
        "pricing": {
            "input_per_million": pricing["input"],
            "output_per_million": pricing["output"],
        },
    }
