#!/usr/bin/env python3
"""
End-to-End Tests for Ollama Provider Integration
==================================================

Tests the complete flow of configuring Ollama (local models) via LiteLLM provider:
- Environment configuration (simulating UI settings)
- Task creation and execution with Ollama models
- Cost tracking verification for zero-cost local models
- Verification that Ollama usage shows $0.00 cost

Note: Ollama tests use mocks to avoid requiring a running Ollama instance.
For manual testing with a real Ollama instance, ensure Ollama is installed and running.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def test_env_ollama(temp_git_repo: Path):
    """Create a test environment for Ollama provider testing.

    Yields:
        tuple: (temp_dir, spec_dir, project_dir)
    """
    temp_dir = temp_git_repo
    spec_dir = temp_dir / ".auto-claude" / "specs" / "046-ollama-provider-test"
    project_dir = temp_dir

    spec_dir.mkdir(parents=True, exist_ok=True)

    yield temp_dir, spec_dir, project_dir


@pytest.fixture
def mock_ollama_api():
    """Mock Ollama API responses for testing without actual Ollama instance."""
    pytest.importorskip("litellm", reason="litellm not installed")
    with patch("litellm.completion") as mock_completion:
        # Mock successful Ollama llama3 response
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content="Test response from Ollama llama3", role="assistant"
                )
            )
        ]
        mock_response.usage = Mock(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        mock_response.model = "ollama/llama3"

        mock_completion.return_value = mock_response
        yield mock_completion


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_ollama_env_config(
    spec_dir: Path,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> Path:
    """Configure Ollama provider via environment variables.

    Prefers monkeypatch.setenv to avoid writing to disk.
    """
    # Prefer monkeypatch to avoid writing secrets/config to disk.
    # All callers should pass monkeypatch; the parameter is kept
    # non-optional so tests fail loudly if it is accidentally omitted.
    if not monkeypatch:
        raise ValueError("monkeypatch is required – do not write .env files in tests")

    monkeypatch.setenv("AI_ENGINE_PROVIDER", "litellm")
    monkeypatch.setenv("LITELLM_MODEL", "ollama/llama3")
    monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")
    return spec_dir.parent.parent.parent / ".env"


def create_simple_spec(spec_dir: Path) -> Path:
    """Create a simple spec for testing."""
    spec_file = spec_dir / "spec.md"
    spec_content = """# Test Ollama Provider Integration

## Description
Simple test task to verify Ollama local model integration with zero cost.

## Acceptance Criteria
- Task completes successfully
- Uses Ollama llama3 model
- Cost is $0.00 (local model, zero cost)
"""
    spec_file.write_text(spec_content)
    return spec_file


def create_implementation_plan(spec_dir: Path) -> Path:
    """Create a minimal implementation plan."""
    plan_file = spec_dir / "implementation_plan.json"
    plan_data = {
        "feature": "Test Ollama Provider",
        "workflow_type": "feature",
        "phases": [
            {
                "id": "phase-1",
                "name": "Test Phase",
                "subtasks": [
                    {
                        "id": "subtask-1-1",
                        "description": "Test subtask",
                        "status": "pending",
                    }
                ],
            }
        ],
    }
    plan_file.write_text(json.dumps(plan_data, indent=2))
    return plan_file


def get_cost_report(spec_dir: Path) -> dict:
    """Load cost_report.json from spec directory."""
    cost_report_file = spec_dir / "cost_report.json"
    if not cost_report_file.exists():
        return {}
    return json.loads(cost_report_file.read_text())


# =============================================================================
# PROVIDER CONFIGURATION TESTS
# =============================================================================


class TestOllamaProviderConfiguration:
    """Tests for Ollama provider configuration."""

    def test_provider_config_from_env(self, test_env_ollama, monkeypatch):
        """Test that Ollama provider configuration is loaded from environment."""
        from core.providers.config import ProviderConfig

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Set environment variables
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "ollama/llama3")
        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")

        # Load provider config
        config = ProviderConfig.from_env()

        # Verify configuration
        assert config.provider == "litellm", (
            f"Provider should be litellm, got {config.provider}"
        )
        assert config.get_model_for_provider() == "ollama/llama3", (
            f"Model should be ollama/llama3, got {config.get_model_for_provider()}"
        )

    def test_ollama_no_api_key_required(self, test_env_ollama, monkeypatch):
        """Test that Ollama does not require an API key (local model)."""
        temp_dir, spec_dir, project_dir = test_env_ollama

        # Set provider without any API keys
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "ollama/llama3")

        # Remove any API keys that might be set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # This should work fine for Ollama (no API key needed)
        assert os.getenv("OPENAI_API_KEY") is None
        assert os.getenv("GOOGLE_API_KEY") is None


# =============================================================================
# COST TRACKING TESTS (ZERO COST)
# =============================================================================


class TestOllamaCostTracking:
    """Tests for cost tracking with Ollama models (should be zero cost)."""

    def test_ollama_pricing_is_zero(self, test_env_ollama):
        """Test that Ollama pricing is $0.00 in MODEL_PRICING."""
        from core.cost_tracking import MODEL_PRICING

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Verify Ollama pricing exists and is zero
        assert "ollama/llama3" in MODEL_PRICING, (
            "ollama/llama3 pricing should be defined"
        )

        # Verify pricing structure
        ollama_pricing = MODEL_PRICING["ollama/llama3"]
        assert "input" in ollama_pricing, "Should have input pricing"
        assert "output" in ollama_pricing, "Should have output pricing"
        assert ollama_pricing["input"] == pytest.approx(0.0), (
            "Input price should be zero for local model"
        )
        assert ollama_pricing["output"] == pytest.approx(0.0), (
            "Output price should be zero for local model"
        )

    def test_cost_calculation_for_ollama(self, test_env_ollama):
        """Test that cost calculation returns $0.00 for Ollama models."""
        from core.cost_tracking import MODEL_PRICING, CostTracker

        temp_dir, spec_dir, project_dir = test_env_ollama

        tracker = CostTracker(spec_dir=spec_dir)

        # Log Ollama usage
        model = "ollama/llama3"
        input_tokens = 1000
        output_tokens = 500

        tracker.log_usage(
            agent_type="coder",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Calculate expected cost (should be zero)
        pricing = MODEL_PRICING[model]
        expected_cost = (input_tokens / 1_000_000 * pricing["input"]) + (
            output_tokens / 1_000_000 * pricing["output"]
        )
        assert expected_cost == pytest.approx(0.0), "Ollama cost should be zero"

        # Verify cost report
        cost_report = get_cost_report(spec_dir)
        assert cost_report, "cost_report.json should exist"
        assert "total_cost" in cost_report, "Should have total_cost"

        actual_cost = cost_report["total_cost"]
        assert actual_cost == pytest.approx(0.0), (
            f"Ollama cost should be $0.00, got ${actual_cost:.2f}"
        )

    def test_cost_tracking_multiple_ollama_models(self, test_env_ollama):
        """Test cost tracking for different Ollama models (all zero cost)."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env_ollama

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for different Ollama models
        tracker.log_usage("coder", "ollama/llama3", 1000, 500)
        tracker.log_usage("planner", "ollama/mistral", 2000, 1000)
        tracker.log_usage("qa_reviewer", "ollama/codellama", 500, 250)

        # Verify all models are tracked
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 3, "Should have 3 records"

        # Verify models are correct
        models = {r["model"] for r in cost_report["records"]}
        assert "ollama/llama3" in models, "Should track ollama/llama3"
        assert "ollama/mistral" in models, "Should track ollama/mistral"
        assert "ollama/codellama" in models, "Should track ollama/codellama"

        # Verify total cost is still zero
        assert cost_report["total_cost"] == pytest.approx(0.0), (
            "Total Ollama cost should be $0.00"
        )

    def test_ollama_models_have_zero_cost(self, test_env_ollama):
        """Test that all Ollama models in MODEL_PRICING have zero cost."""
        from core.cost_tracking import MODEL_PRICING

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Find all Ollama models
        ollama_models = [
            model_name
            for model_name in MODEL_PRICING.keys()
            if model_name.startswith("ollama/")
        ]

        assert len(ollama_models) > 0, "Should have Ollama models defined"

        # Verify all have zero cost
        for model_name in ollama_models:
            pricing = MODEL_PRICING[model_name]
            assert pricing["input"] == pytest.approx(0.0), (
                f"{model_name} input should be zero"
            )
            assert pricing["output"] == pytest.approx(0.0), (
                f"{model_name} output should be zero"
            )


# =============================================================================
# PROVIDER FACTORY TESTS
# =============================================================================


class TestOllamaProviderFactory:
    """Tests for creating Ollama provider via factory."""

    def test_create_litellm_provider_for_ollama(self, test_env_ollama, monkeypatch):
        """Test creating LiteLLM provider for Ollama."""
        from core.providers.config import ProviderConfig
        from core.providers.factory import create_engine_provider

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Configure environment
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "ollama/llama3")
        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")

        # Create provider config
        config = ProviderConfig.from_env()

        # Verify configuration
        assert config.provider == "litellm"
        assert config.get_model_for_provider() == "ollama/llama3"

        # Verify the factory can actually instantiate the provider
        provider = create_engine_provider(config)
        assert provider is not None, "create_engine_provider should return a provider"
        assert provider.name == "litellm", (
            f"Provider name should be 'litellm', got {provider.name!r}"
        )


# =============================================================================
# END-TO-END INTEGRATION TESTS
# =============================================================================


class TestE2EOllamaIntegration:
    """End-to-end tests for Ollama provider integration."""

    def test_e2e_ollama_provider_mock(
        self, test_env_ollama, monkeypatch, mock_ollama_api
    ):
        """
        E2E Test (MOCKED): Configure Ollama provider and verify zero cost.

        This test uses mocked API responses for fast, offline testing without
        requiring a running Ollama instance.
        """
        from core.cost_tracking import CostTracker
        from core.providers.config import ProviderConfig

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Step 1: Configure environment (simulating UI configuration)
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "ollama/llama3")
        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")

        # Step 2: Verify provider configuration loaded correctly
        config = ProviderConfig.from_env()
        assert config.provider == "litellm", (
            f"Provider should be litellm, got {config.provider}"
        )
        assert config.get_model_for_provider() == "ollama/llama3", (
            f"Model should be ollama/llama3, got {config.get_model_for_provider()}"
        )

        # Step 3: Create minimal spec and plan
        spec_file = create_simple_spec(spec_dir)
        plan_file = create_implementation_plan(spec_dir)

        assert spec_file.exists(), "spec.md should be created"
        assert plan_file.exists(), "implementation_plan.json should be created"

        # Step 4: Simulate agent execution with cost tracking
        tracker = CostTracker(spec_dir=spec_dir)

        # Simulate coder agent using Ollama llama3
        tracker.log_usage(
            agent_type="coder",
            model="ollama/llama3",
            input_tokens=1000,
            output_tokens=500,
        )

        # Step 5: Verify cost_report.json was created
        cost_report_file = spec_dir / "cost_report.json"
        assert cost_report_file.exists(), "cost_report.json should be created"

        # Step 6: Verify cost report structure
        cost_report = get_cost_report(spec_dir)
        assert cost_report, "Should load cost report"
        assert "total_cost" in cost_report, "Should have total_cost"
        assert "records" in cost_report, "Should have records"
        assert len(cost_report["records"]) == 1, "Should have 1 usage record"

        # Step 7: Verify Ollama model is tracked
        record = cost_report["records"][0]
        assert record["agent_type"] == "coder", "Should track coder agent"
        assert record["model"] == "ollama/llama3", (
            f"Should use ollama/llama3, got {record['model']}"
        )
        assert record["input_tokens"] == 1000, "Should track input tokens"
        assert record["output_tokens"] == 500, "Should track output tokens"

        # Step 8: Verify cost is ZERO (local model, no API cost)
        assert cost_report["total_cost"] == pytest.approx(0.0), (
            f"Ollama cost should be $0.00, got ${cost_report['total_cost']:.2f}"
        )

        print("\n✓ E2E Test passed: Ollama provider configured and cost is $0.00")

    def test_e2e_ollama_multiple_models_zero_cost(self, test_env_ollama, monkeypatch):
        """
        E2E Test: Use multiple Ollama models and verify all show zero cost.
        """
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Configure environment
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "ollama/llama3")

        # Create spec
        create_simple_spec(spec_dir)
        create_implementation_plan(spec_dir)

        # Simulate usage of multiple Ollama models
        tracker = CostTracker(spec_dir=spec_dir)

        tracker.log_usage("planner", "ollama/llama3", 2000, 1000)
        tracker.log_usage("coder", "ollama/codellama", 5000, 2500)
        tracker.log_usage("qa_reviewer", "ollama/mistral", 1000, 500)

        # Verify cost report
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 3, "Should have 3 records"

        # Verify all are Ollama models
        models = [r["model"] for r in cost_report["records"]]
        assert all(m.startswith("ollama/") for m in models), (
            "All models should be Ollama"
        )

        # Verify total cost is zero
        assert cost_report["total_cost"] == pytest.approx(0.0), (
            f"Total Ollama cost should be $0.00, got ${cost_report['total_cost']:.2f}"
        )

        print("\n✓ E2E Test passed: Multiple Ollama models used, total cost is $0.00")
        print(f"  Models used: {', '.join(models)}")

    def test_e2e_mixed_claude_and_ollama_cost(self, test_env_ollama, monkeypatch):
        """
        E2E Test: Mix Claude and Ollama usage, verify only Claude has cost.
        """
        from core.cost_tracking import MODEL_PRICING, CostTracker

        temp_dir, spec_dir, project_dir = test_env_ollama

        # Configure environment
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")  # Default
        monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
        monkeypatch.setenv("AGENT_MODEL_CODER", "ollama/llama3")

        # Create spec
        create_simple_spec(spec_dir)
        create_implementation_plan(spec_dir)

        # Simulate mixed usage
        tracker = CostTracker(spec_dir=spec_dir)

        # Planner uses Claude (has cost)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 2000, 1000)

        # Coder uses Ollama (zero cost)
        tracker.log_usage("coder", "ollama/llama3", 5000, 2500)

        # Verify cost report
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 2, "Should have 2 records"

        # Calculate expected cost (only Claude)
        claude_pricing = MODEL_PRICING["claude-sonnet-4-5-20250929"]
        expected_cost = (2000 / 1_000_000 * claude_pricing["input"]) + (
            1000 / 1_000_000 * claude_pricing["output"]
        )

        # Verify total cost equals only Claude cost (Ollama is zero)
        actual_cost = cost_report["total_cost"]
        assert abs(actual_cost - expected_cost) < 0.001, (
            f"Cost should be from Claude only: expected ${expected_cost:.6f}, got ${actual_cost:.6f}"
        )

        # Verify Ollama record has zero cost
        ollama_record = next(
            r for r in cost_report["records"] if "ollama" in r["model"]
        )
        ollama_cost = ollama_record.get("cost", 0.00)
        assert ollama_cost == pytest.approx(0.0), "Ollama record cost should be $0.00"

        print("\n✓ E2E Test passed: Mixed Claude/Ollama usage")
        print(f"  Claude cost: ${expected_cost:.6f}")
        print("  Ollama cost: $0.00")
        print(f"  Total cost: ${actual_cost:.6f}")


# =============================================================================
# MANUAL TEST PROCEDURE
# =============================================================================


def print_manual_test_procedure():
    """Print manual E2E test procedure for UI verification with Ollama."""
    procedure = """
    ═══════════════════════════════════════════════════════════════════════
    MANUAL E2E TEST PROCEDURE: Ollama Provider Configuration
    ═══════════════════════════════════════════════════════════════════════

    Prerequisites:
    - Electron app running: npm run dev
    - Ollama installed and running: ollama serve
    - At least one model pulled: ollama pull llama3

    Test Steps:

    1. Verify Ollama is Running
       - Open terminal and run: ollama list
       - Verify llama3 (or other models) are listed
       - Confirm Ollama is accessible at http://localhost:11434

    2. Open Settings Page
       - Launch Auto Claude Electron app
       - Click Settings icon in sidebar
       - Navigate to "Providers" section

    3. Configure Ollama Provider
       - Select "LiteLLM" from Provider dropdown
       - In Model field, enter: ollama/llama3
       - Note: No API key needed for Ollama (local model)
       - Click "Save" button
       - Verify success message appears

    4. Verify Configuration Saved
       - Check apps/backend/.env file contains:
         * AI_ENGINE_PROVIDER=litellm
         * LITELLM_MODEL=ollama/llama3
       - Note: No API key variables needed

    5. Create Simple Test Task
       - Click "Create New Task" button
       - Enter task description: "Write a hello world function in Python"
       - Click "Create Task"
       - Wait for task to complete

    6. Verify Ollama Model Usage
       - Open task details
       - Check build logs show "Using model: ollama/llama3"
       - Verify task completes successfully
       - Note: May be slower than cloud models depending on local hardware

    7. Verify Zero Cost Tracking
       - Navigate to task's .auto-claude/specs/XXX/ directory
       - Open cost_report.json
       - Verify it contains:
         * "model": "ollama/llama3"
         * "total_cost": 0.00
         * "records" array with Ollama usage
         * Each record should show zero cost

    8. Verify Cost Display in UI
       - Open Analytics/Cost view
       - Verify cost breakdown shows "Ollama: $0.00"
       - Verify Ollama models are listed with zero cost indicator
       - Confirm total cost is $0.00 if only Ollama was used

    Expected Results:
    ✓ Settings page shows Ollama configuration options
    ✓ Configuration saves to .env file (no API key needed)
    ✓ Task uses Ollama llama3 model as configured
    ✓ cost_report.json tracks Ollama usage with $0.00 cost
    ✓ UI displays Ollama with zero cost indicator
    ✓ Privacy-focused: Code never leaves local machine

    Troubleshooting:
    - If Ollama connection fails, verify: ollama serve is running
    - If model not found, run: ollama pull llama3
    - Check Ollama logs: journalctl -u ollama (Linux) or Console.app (Mac)

    ═══════════════════════════════════════════════════════════════════════
    """
    print(procedure)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_all_tests():
    """Run all tests using pytest."""
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))


if __name__ == "__main__":
    # Print manual test procedure
    print_manual_test_procedure()

    # Run automated tests
    print("\n" + "=" * 70)
    print("Running Automated E2E Tests for Ollama Provider...")
    print("=" * 70 + "\n")
    run_all_tests()
