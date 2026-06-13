"""Tests for ProviderConfig.coherent_session_model (QA/coder model coherence)."""

from core.providers.config import ProviderConfig


def test_claude_family_model_replaced_for_direct_provider():
    """A claude-family phase default must not reach a non-Claude session."""
    config = ProviderConfig(provider="openai", openai_model="gpt-5.2")

    assert (
        config.coherent_session_model("claude-sonnet-4-5-20250929") == "gpt-5.2"
    )


def test_explicit_provider_model_is_preserved():
    config = ProviderConfig(provider="openai", openai_model="gpt-5.2")

    assert config.coherent_session_model("gpt-4o") == "gpt-4o"


def test_none_model_passes_through():
    config = ProviderConfig(provider="openai", openai_model="gpt-5.2")

    assert config.coherent_session_model(None) is None


def test_claude_provider_keeps_claude_model():
    config = ProviderConfig(
        provider="claude", claude_model="claude-sonnet-4-5-20250929"
    )

    assert (
        config.coherent_session_model("claude-sonnet-4-5-20250929")
        == "claude-sonnet-4-5-20250929"
    )


def test_direct_provider_without_configured_model_keeps_request():
    """If the provider has no configured model, fall back to the request
    rather than returning an empty string."""
    config = ProviderConfig(provider="openrouter", openrouter_model="")

    # openrouter_model empty -> get_model_for returns "" (falsy) -> keep request
    assert (
        config.coherent_session_model("claude-sonnet-4-5-20250929")
        == "claude-sonnet-4-5-20250929"
    )
