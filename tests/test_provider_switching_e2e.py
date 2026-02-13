"""
End-to-End Tests for Multi-Provider Switching
==============================================

Tests the full provider switching flow including:
- Provider configuration loading
- Provider creation and initialization
- Switching between providers
- Fallback behavior when models unavailable
- Cost calculation across providers

These tests validate the integration between provider adapters,
configuration management, and fallback logic.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from core.providers.config import ProviderConfig, AIEngineProvider
from core.providers.factory import create_engine_provider
from core.providers.cost_calculator import calculate_cost, get_model_pricing, estimate_session_cost
from core.model_fallback import get_fallback_model


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def clean_env():
    """Clean environment before and after tests."""
    # Save original env
    original_env = dict(os.environ)

    # Clear provider-related env vars
    provider_vars = [
        'AI_ENGINE_PROVIDER',
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'GOOGLE_API_KEY',
        'OPENROUTER_API_KEY',
        'OLLAMA_MODEL',
        'OLLAMA_BASE_URL',
    ]
    for var in provider_vars:
        os.environ.pop(var, None)

    yield

    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_claude_env():
    """Set up environment for Claude provider."""
    os.environ['AI_ENGINE_PROVIDER'] = 'claude'
    os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test-key-12345'
    return {
        'provider': 'claude',
        'api_key': 'sk-ant-test-key-12345',
        'model': 'claude-sonnet-4-5-20250929'
    }


@pytest.fixture
def mock_openai_env():
    """Set up environment for OpenAI provider."""
    os.environ['AI_ENGINE_PROVIDER'] = 'openai'
    os.environ['OPENAI_API_KEY'] = 'sk-test-openai-key-12345'
    os.environ['OPENAI_MODEL'] = 'gpt-4o'
    return {
        'provider': 'openai',
        'api_key': 'sk-test-openai-key-12345',
        'model': 'gpt-4o'
    }


@pytest.fixture
def mock_google_env():
    """Set up environment for Google provider."""
    os.environ['AI_ENGINE_PROVIDER'] = 'google'
    os.environ['GOOGLE_API_KEY'] = 'test-google-key-12345'
    os.environ['GOOGLE_MODEL'] = 'gemini-2.0-flash'
    return {
        'provider': 'google',
        'api_key': 'test-google-key-12345',
        'model': 'gemini-2.0-flash'
    }


@pytest.fixture
def mock_ollama_env():
    """Set up environment for Ollama provider."""
    os.environ['AI_ENGINE_PROVIDER'] = 'ollama'
    os.environ['OLLAMA_MODEL'] = 'llama3.1'
    os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434/v1'
    return {
        'provider': 'ollama',
        'model': 'llama3.1',
        'base_url': 'http://localhost:11434/v1'
    }


# ============================================================================
# Configuration Tests
# ============================================================================

def test_provider_config_from_env_claude(clean_env, mock_claude_env):
    """Test loading Claude provider configuration from environment."""
    config = ProviderConfig.from_env()

    assert config.provider == 'claude'
    assert config.anthropic_api_key == 'sk-ant-test-key-12345'
    assert config.claude_model == 'claude-sonnet-4-5-20250929'
    assert config.is_valid()


def test_provider_config_from_env_openai(clean_env, mock_openai_env):
    """Test loading OpenAI provider configuration from environment."""
    config = ProviderConfig.from_env()

    assert config.provider == 'openai'
    assert config.openai_api_key == 'sk-test-openai-key-12345'
    assert config.openai_model == 'gpt-4o'
    assert config.is_valid()


def test_provider_config_from_env_google(clean_env, mock_google_env):
    """Test loading Google provider configuration from environment."""
    config = ProviderConfig.from_env()

    assert config.provider == 'google'
    assert config.google_api_key == 'test-google-key-12345'
    assert config.google_model == 'gemini-2.0-flash'
    assert config.is_valid()


def test_provider_config_from_env_ollama(clean_env, mock_ollama_env):
    """Test loading Ollama provider configuration from environment."""
    config = ProviderConfig.from_env()

    assert config.provider == 'ollama'
    assert config.ollama_model == 'llama3.1'
    assert config.ollama_base_url == 'http://localhost:11434/v1'
    assert config.is_valid()


def test_provider_config_defaults(clean_env):
    """Test provider configuration defaults when no env vars set."""
    # Set minimal config for Claude (default provider)
    os.environ['ANTHROPIC_API_KEY'] = 'test-key'

    config = ProviderConfig.from_env()

    assert config.provider == 'claude'  # Default provider
    assert config.claude_model == 'claude-sonnet-4-5-20250929'
    assert config.is_valid()


# ============================================================================
# Provider Switching Tests
# ============================================================================

def test_switch_from_claude_to_openai(clean_env):
    """Test switching from Claude to OpenAI provider."""
    # Start with Claude
    os.environ['AI_ENGINE_PROVIDER'] = 'claude'
    os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test-key'

    config1 = ProviderConfig.from_env()
    assert config1.provider == 'claude'
    assert config1.is_valid()

    # Switch to OpenAI
    os.environ['AI_ENGINE_PROVIDER'] = 'openai'
    os.environ['OPENAI_API_KEY'] = 'sk-openai-test-key'

    config2 = ProviderConfig.from_env()
    assert config2.provider == 'openai'
    assert config2.is_valid()

    # Verify configs are different
    assert config1.provider != config2.provider


def test_switch_from_openai_to_ollama(clean_env):
    """Test switching from OpenAI to Ollama provider."""
    # Start with OpenAI
    os.environ['AI_ENGINE_PROVIDER'] = 'openai'
    os.environ['OPENAI_API_KEY'] = 'sk-openai-test-key'

    config1 = ProviderConfig.from_env()
    assert config1.provider == 'openai'

    # Switch to Ollama (no API key required)
    os.environ['AI_ENGINE_PROVIDER'] = 'ollama'
    os.environ['OLLAMA_MODEL'] = 'llama3.1'

    config2 = ProviderConfig.from_env()
    assert config2.provider == 'ollama'
    assert config2.is_valid()


def test_switch_all_providers_sequential(clean_env):
    """Test switching through all providers sequentially."""
    providers_configs = [
        ('claude', {'ANTHROPIC_API_KEY': 'test-key'}),
        ('openai', {'OPENAI_API_KEY': 'test-key'}),
        ('google', {'GOOGLE_API_KEY': 'test-key'}),
        ('ollama', {'OLLAMA_MODEL': 'llama3.1'}),
    ]

    previous_provider = None
    for provider_name, env_vars in providers_configs:
        # Set provider
        os.environ['AI_ENGINE_PROVIDER'] = provider_name
        for key, value in env_vars.items():
            os.environ[key] = value

        # Load config
        config = ProviderConfig.from_env()
        assert config.provider == provider_name
        assert config.is_valid()

        # Verify it's different from previous
        if previous_provider:
            assert config.provider != previous_provider

        previous_provider = config.provider


# ============================================================================
# Provider Creation Tests
# ============================================================================

@patch('core.providers.adapters.claude.ClaudeAgentProvider')
def test_create_claude_provider(mock_provider_class, clean_env, mock_claude_env):
    """Test creating Claude provider instance."""
    config = ProviderConfig.from_env()

    # Mock the provider class
    mock_provider = MagicMock()
    mock_provider_class.return_value = mock_provider

    provider = create_engine_provider(config)

    assert provider is not None
    mock_provider_class.assert_called_once()


@patch('core.providers.adapters.openai.OpenAIProvider')
def test_create_openai_provider(mock_provider_class, clean_env, mock_openai_env):
    """Test creating OpenAI provider instance."""
    config = ProviderConfig.from_env()

    # Mock the provider class
    mock_provider = MagicMock()
    mock_provider_class.return_value = mock_provider

    provider = create_engine_provider(config)

    assert provider is not None
    mock_provider_class.assert_called_once()


@patch('core.providers.adapters.google.GoogleProvider')
def test_create_google_provider(mock_provider_class, clean_env, mock_google_env):
    """Test creating Google provider instance."""
    config = ProviderConfig.from_env()

    # Mock the provider class
    mock_provider = MagicMock()
    mock_provider_class.return_value = mock_provider

    provider = create_engine_provider(config)

    assert provider is not None
    mock_provider_class.assert_called_once()


@patch('core.providers.adapters.ollama.OllamaProvider')
def test_create_ollama_provider(mock_provider_class, clean_env, mock_ollama_env):
    """Test creating Ollama provider instance."""
    config = ProviderConfig.from_env()

    # Mock the provider class
    mock_provider = MagicMock()
    mock_provider_class.return_value = mock_provider

    provider = create_engine_provider(config)

    assert provider is not None
    mock_provider_class.assert_called_once()


# ============================================================================
# Fallback Tests
# ============================================================================

def test_claude_model_fallback():
    """Test fallback chain for Claude models."""
    # Test Claude Opus fallback
    assert get_fallback_model('claude-opus-4-20250514') == 'claude-sonnet-4-5-20250929'
    assert get_fallback_model('claude-sonnet-4-5-20250929') == 'claude-3-5-haiku-20241022'
    assert get_fallback_model('claude-3-5-haiku-20241022') is None  # End of chain


def test_openai_model_fallback():
    """Test fallback chain for OpenAI models."""
    # Test GPT-4 fallback
    assert get_fallback_model('gpt-4') == 'gpt-4-turbo'
    assert get_fallback_model('gpt-4-turbo') == 'gpt-4o'
    assert get_fallback_model('gpt-4o') == 'gpt-4o-mini'
    assert get_fallback_model('gpt-4o-mini') == 'gpt-3.5-turbo'


def test_google_model_fallback():
    """Test fallback chain for Google Gemini models."""
    # Test Gemini fallback
    assert get_fallback_model('gemini-2.0-flash-thinking-exp') == 'gemini-2.0-flash-exp'
    assert get_fallback_model('gemini-2.0-flash-exp') == 'gemini-1.5-pro'
    assert get_fallback_model('gemini-1.5-pro') == 'gemini-1.5-flash'


def test_ollama_model_no_fallback():
    """Test that Ollama models don't have fallbacks (local, free)."""
    # Ollama models don't have fallbacks since they're local
    assert get_fallback_model('llama3.1') is None
    assert get_fallback_model('mistral') is None


def test_fallback_when_model_unavailable(clean_env):
    """Test fallback behavior when primary model is unavailable."""
    # Set up OpenAI with GPT-4
    os.environ['AI_ENGINE_PROVIDER'] = 'openai'
    os.environ['OPENAI_API_KEY'] = 'test-key'
    os.environ['OPENAI_MODEL'] = 'gpt-4'

    config = ProviderConfig.from_env()
    primary_model = config.openai_model

    # Simulate primary model unavailable, get fallback
    fallback_model = get_fallback_model(primary_model)

    assert fallback_model == 'gpt-4-turbo'
    assert fallback_model != primary_model


# ============================================================================
# Cost Calculation Tests
# ============================================================================

def test_cost_calculation_claude():
    """Test cost calculation for Claude models."""
    # Claude Sonnet: $3 per 1M input, $15 per 1M output
    cost = calculate_cost('claude-sonnet-4-5-20250929', input_tokens=100000, output_tokens=50000)
    expected_cost = (100000 / 1_000_000 * 3) + (50000 / 1_000_000 * 15)
    assert abs(cost - expected_cost) < 0.01


def test_cost_calculation_openai():
    """Test cost calculation for OpenAI models."""
    # GPT-4o: $2.50 per 1M input, $10 per 1M output
    cost = calculate_cost('gpt-4o', input_tokens=100000, output_tokens=50000)
    expected_cost = (100000 / 1_000_000 * 2.50) + (50000 / 1_000_000 * 10)
    assert abs(cost - expected_cost) < 0.01


def test_cost_calculation_google():
    """Test cost calculation for Google Gemini models."""
    # Gemini 2.0 Flash: $0.10 per 1M input, $0.40 per 1M output
    cost = calculate_cost('gemini-2.0-flash-exp', input_tokens=100000, output_tokens=50000)
    expected_cost = (100000 / 1_000_000 * 0.10) + (50000 / 1_000_000 * 0.40)
    assert abs(cost - expected_cost) < 0.01


def test_cost_calculation_ollama():
    """Test cost calculation for Ollama models (free)."""
    # Ollama is free
    cost = calculate_cost('llama3.1', input_tokens=100000, output_tokens=50000)
    assert cost == 0.0


def test_cost_comparison_across_providers():
    """Test comparing costs across different providers."""
    tokens_in = 100000
    tokens_out = 50000

    costs = {
        'claude-opus-4-20250514': calculate_cost('claude-opus-4-20250514', tokens_in, tokens_out),
        'gpt-4': calculate_cost('gpt-4', tokens_in, tokens_out),
        'gemini-2.0-flash-exp': calculate_cost('gemini-2.0-flash-exp', tokens_in, tokens_out),
        'llama3.1': calculate_cost('llama3.1', tokens_in, tokens_out),
    }

    # Verify Ollama is cheapest (free)
    assert costs['llama3.1'] == 0.0

    # Verify Gemini is cheaper than Claude/OpenAI for these tokens
    assert costs['gemini-2.0-flash-exp'] < costs['claude-opus-4-20250514']
    assert costs['gemini-2.0-flash-exp'] < costs['gpt-4']


def test_session_cost_estimation():
    """Test estimating total session cost."""
    # Estimate 10-message session with GPT-4o
    messages = [
        {'role': 'user', 'content': 'Tell me about Python'},  # ~5 tokens
        {'role': 'assistant', 'content': 'Python is a high-level programming language...'},  # ~50 tokens
    ]

    # Rough estimate: 10 exchanges = ~550 tokens total
    estimated_input = 250
    estimated_output = 300

    cost = estimate_session_cost('gpt-4o', num_messages=10, avg_input_tokens=estimated_input, avg_output_tokens=estimated_output)

    # Should be small cost for this session
    assert cost > 0
    assert cost < 1.0  # Less than $1


# ============================================================================
# Integration Tests
# ============================================================================

@patch('core.providers.adapters.openai.OpenAIProvider')
def test_full_provider_switch_flow(mock_provider_class, clean_env):
    """
    Test complete flow:
    1. Start with Claude
    2. Switch to OpenAI
    3. Calculate cost difference
    4. Use fallback if needed
    """
    # Step 1: Start with Claude
    os.environ['AI_ENGINE_PROVIDER'] = 'claude'
    os.environ['ANTHROPIC_API_KEY'] = 'test-claude-key'

    config_claude = ProviderConfig.from_env()
    assert config_claude.provider == 'claude'

    # Calculate cost for Claude
    claude_cost = calculate_cost('claude-sonnet-4-5-20250929', 100000, 50000)

    # Step 2: Switch to OpenAI
    os.environ['AI_ENGINE_PROVIDER'] = 'openai'
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    os.environ['OPENAI_MODEL'] = 'gpt-4o'

    config_openai = ProviderConfig.from_env()
    assert config_openai.provider == 'openai'
    assert config_openai.openai_model == 'gpt-4o'

    # Step 3: Calculate cost for OpenAI
    openai_cost = calculate_cost('gpt-4o', 100000, 50000)

    # Verify cost difference
    assert openai_cost != claude_cost

    # Step 4: Test fallback for OpenAI
    fallback = get_fallback_model('gpt-4o')
    assert fallback == 'gpt-4o-mini'

    # Calculate fallback cost
    fallback_cost = calculate_cost('gpt-4o-mini', 100000, 50000)
    assert fallback_cost < openai_cost  # Fallback should be cheaper


def test_provider_validation_all_providers(clean_env):
    """Test that all providers validate correctly with proper credentials."""
    test_cases = [
        ('claude', {'ANTHROPIC_API_KEY': 'test-key'}),
        ('openai', {'OPENAI_API_KEY': 'test-key'}),
        ('google', {'GOOGLE_API_KEY': 'test-key'}),
        ('ollama', {'OLLAMA_MODEL': 'llama3.1'}),  # Ollama doesn't need API key
    ]

    for provider_name, env_vars in test_cases:
        # Clean and set environment
        os.environ.clear()
        os.environ['AI_ENGINE_PROVIDER'] = provider_name
        for key, value in env_vars.items():
            os.environ[key] = value

        # Load and validate config
        config = ProviderConfig.from_env()
        assert config.provider == provider_name
        assert config.is_valid(), f"Provider {provider_name} should be valid with credentials"


def test_invalid_provider_configuration(clean_env):
    """Test that invalid configurations are detected."""
    # Claude without API key
    os.environ['AI_ENGINE_PROVIDER'] = 'claude'
    # No ANTHROPIC_API_KEY set

    config = ProviderConfig.from_env()
    assert not config.is_valid()  # Should be invalid without API key


# ============================================================================
# E2E Manual Test Documentation
# ============================================================================

def test_print_e2e_manual_test_plan():
    """
    Print manual E2E test plan for frontend UI testing.
    This documents the steps to manually verify provider switching in the UI.
    """
    manual_test_plan = """

    =============================================================
    MANUAL E2E TEST PLAN: Provider Switching in UI
    =============================================================

    Prerequisites:
    1. Build frontend: cd apps/frontend && npm run build
    2. Start app: npm run dev
    3. Have API keys ready for testing:
       - Anthropic API key
       - OpenAI API key
       - Google API key (optional)
       - Ollama running locally (optional)

    Test Flow:

    STEP 1: Navigate to Settings
    ✓ Start the application
    ✓ Click on Settings icon in sidebar
    ✓ Verify settings page loads
    ✓ Locate "Provider" section with Sparkles icon

    STEP 2: Configure OpenAI Provider
    ✓ In Provider section, select "OpenAI" from dropdown
    ✓ Enter OpenAI API key in the API key field
    ✓ Select model (e.g., gpt-4o) from model dropdown
    ✓ Click Save/Apply
    ✓ Verify success notification

    STEP 3: View Cost Comparison
    ✓ Scroll to "Cost Comparison" section (DollarSign icon)
    ✓ Verify pricing shown for OpenAI models
    ✓ Verify cheapest model is highlighted
    ✓ Note the per-1M-token pricing

    STEP 4: Configure Fallback Model
    ✓ In Provider section, locate "Fallback Model" dropdown
    ✓ Select a fallback model (e.g., gpt-4o-mini)
    ✓ Verify info box explains fallback behavior
    ✓ Click Save/Apply

    STEP 5: Create Test Spec with OpenAI
    ✓ Navigate to "Create Spec" page
    ✓ Enter task description: "Create a simple hello world script"
    ✓ Click "Create Spec"
    ✓ Verify spec is created successfully
    ✓ Check backend logs to confirm OpenAI provider is used

    STEP 6: Switch to Ollama Provider
    ✓ Return to Settings > Provider section
    ✓ Select "Ollama" from provider dropdown
    ✓ Enter model name: llama3.1 (or your installed model)
    ✓ Verify base URL: http://localhost:11434/v1
    ✓ Click Save/Apply
    ✓ Verify success notification

    STEP 7: Verify Ollama in Cost Comparison
    ✓ Scroll to Cost Comparison section
    ✓ Verify Ollama shows $0.00 for input/output
    ✓ Verify "Free Local Model" badge is shown

    STEP 8: Create Test Spec with Ollama
    ✓ Navigate to "Create Spec" page
    ✓ Enter task description: "Create a README file"
    ✓ Click "Create Spec"
    ✓ Verify spec is created successfully
    ✓ Check backend logs to confirm Ollama provider is used

    STEP 9: Test Fallback Behavior
    ✓ In Settings, select a model that doesn't exist (e.g., "gpt-5")
    ✓ Configure a valid fallback model (e.g., gpt-4o)
    ✓ Try to create a spec
    ✓ Verify system falls back to gpt-4o
    ✓ Check logs for fallback message

    STEP 10: Verify Provider Persistence
    ✓ Close the application
    ✓ Reopen the application
    ✓ Navigate to Settings > Provider
    ✓ Verify last selected provider is still selected
    ✓ Verify API keys are still configured

    Expected Results:
    ✅ All providers can be selected and configured
    ✅ Cost comparison updates when switching providers
    ✅ Fallback configuration works correctly
    ✅ Specs can be created with different providers
    ✅ Settings persist across app restarts
    ✅ Backend logs show correct provider being used

    =============================================================
    """

    print(manual_test_plan)
    # This test always passes - it's just documentation
    assert True


if __name__ == '__main__':
    # Run with: python -m pytest tests/test_provider_switching_e2e.py -v
    pytest.main([__file__, '-v', '-s'])
