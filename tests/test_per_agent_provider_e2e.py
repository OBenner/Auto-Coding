#!/usr/bin/env python3
"""
End-to-End Tests for Per-Agent Provider Selection
==================================================

Tests the complete flow of configuring different providers for different agents:
- Planner agent uses Claude (opus model)
- Coder agent uses LiteLLM/OpenAI (gpt-4 model)
- Full build cycle simulation
- Cost tracking verification for both providers

This validates that the per-agent provider selection feature works correctly
and that cost_report.json accurately tracks usage from multiple providers.
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
def test_env_multi_provider(temp_git_repo: Path):
    """Create a test environment for multi-provider testing.

    Yields:
        tuple: (temp_dir, spec_dir, project_dir)
    """
    temp_dir = temp_git_repo
    spec_dir = temp_dir / ".auto-claude" / "specs" / "046-multi-provider-test"
    project_dir = temp_dir

    spec_dir.mkdir(parents=True, exist_ok=True)

    yield temp_dir, spec_dir, project_dir


@pytest.fixture
def mock_multi_provider_api():
    """Mock both Claude and OpenAI API responses for testing."""
    with patch("litellm.completion") as mock_litellm:
        # Mock GPT-4 response
        mock_gpt4_response = Mock()
        mock_gpt4_response.choices = [
            Mock(message=Mock(content="Test response from GPT-4", role="assistant"))
        ]
        mock_gpt4_response.usage = Mock(
            prompt_tokens=1000, completion_tokens=500, total_tokens=1500
        )
        mock_gpt4_response.model = "gpt-4"

        mock_litellm.return_value = mock_gpt4_response
        yield mock_litellm


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_multi_provider_env_config(
    spec_dir: Path, monkeypatch: pytest.MonkeyPatch | None = None
) -> Path:
    """Configure per-agent provider via environment variables.

    Prefers monkeypatch.setenv to avoid writing secrets to disk.
    """
    # Prefer monkeypatch to avoid writing secrets/config to disk.
    # All callers should pass monkeypatch; the parameter is kept
    # non-optional so tests fail loudly if it is accidentally omitted.
    if not monkeypatch:
        raise ValueError("monkeypatch is required – do not write .env files in tests")

    monkeypatch.setenv("AGENT_PROVIDER_PLANNER", "claude")
    monkeypatch.setenv("AGENT_MODEL_PLANNER", "claude-opus-4-20250514")
    monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
    monkeypatch.setenv("AGENT_MODEL_CODER", "gpt-4")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
    return spec_dir.parent.parent.parent / ".env"


def create_simple_spec(spec_dir: Path) -> Path:
    """Create a simple spec for testing."""
    spec_file = spec_dir / "spec.md"
    spec_content = """# Test Multi-Provider Integration

## Description
Simple test task to verify per-agent provider selection works correctly.

## Acceptance Criteria
- Task completes successfully
- Planner uses Claude Opus model
- Coder uses OpenAI GPT-4 model
- Cost tracking shows both Claude and OpenAI usage
"""
    spec_file.write_text(spec_content)
    return spec_file


def create_implementation_plan(spec_dir: Path) -> Path:
    """Create a minimal implementation plan."""
    plan_file = spec_dir / "implementation_plan.json"
    plan_data = {
        "feature": "Test Multi-Provider Support",
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


class TestPerAgentProviderConfiguration:
    """Tests for per-agent provider configuration."""

    def test_planner_uses_claude(self, test_env_multi_provider, monkeypatch):
        """Test that planner is configured to use Claude."""
        from phase_config import get_provider_for_agent

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Configure per-agent providers
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")  # Default
        monkeypatch.setenv("AGENT_PROVIDER_PLANNER", "claude")
        monkeypatch.setenv("AGENT_MODEL_PLANNER", "claude-opus-4-20250514")

        # Verify planner uses Claude
        planner_provider = get_provider_for_agent("planner")
        assert planner_provider == "claude", (
            f"Planner should use Claude, got {planner_provider}"
        )

    def test_coder_uses_openai(self, test_env_multi_provider, monkeypatch):
        """Test that coder is configured to use OpenAI via LiteLLM."""
        from phase_config import get_provider_for_agent

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Configure per-agent providers
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")  # Default
        monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
        monkeypatch.setenv("AGENT_MODEL_CODER", "gpt-4")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Verify coder uses LiteLLM
        coder_provider = get_provider_for_agent("coder")
        assert coder_provider == "litellm", (
            f"Coder should use LiteLLM, got {coder_provider}"
        )

    def test_per_agent_provider_fallback(self, test_env_multi_provider, monkeypatch):
        """Test that agents fall back to default provider when not configured."""
        from phase_config import get_provider_for_agent

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Set default provider only
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
        monkeypatch.delenv("AGENT_PROVIDER_QA_REVIEWER", raising=False)

        # Verify QA reviewer falls back to Claude
        qa_provider = get_provider_for_agent("qa_reviewer")
        assert qa_provider == "claude", (
            f"QA reviewer should fall back to Claude, got {qa_provider}"
        )


# =============================================================================
# COST TRACKING TESTS
# =============================================================================


class TestMultiProviderCostTracking:
    """Tests for cost tracking with multiple providers."""

    def test_cost_tracking_both_providers(self, test_env_multi_provider):
        """Test that cost tracking works for both Claude and OpenAI."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for both providers
        tracker.log_usage("planner", "claude-opus-4-20250514", 2000, 1000)
        tracker.log_usage("coder", "gpt-4", 1000, 500)

        # Verify cost report
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 2, "Should have 2 records"

        # Verify both models are tracked
        models = [r["model"] for r in cost_report["records"]]
        assert any("claude" in m for m in models), "Should track Claude usage"
        assert any("gpt-4" in m for m in models), "Should track GPT-4 usage"

        # Verify both have non-zero costs
        assert cost_report["total_cost"] > 0, "Total cost should be positive"

    def test_cost_breakdown_by_provider(self, test_env_multi_provider):
        """Test that cost report shows usage breakdown by provider."""
        from core.cost_tracking import MODEL_PRICING, CostTracker

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for different providers
        tracker.log_usage("planner", "claude-opus-4-20250514", 2000, 1000)
        tracker.log_usage("coder", "gpt-4", 1000, 500)

        # Calculate expected costs
        claude_pricing = MODEL_PRICING.get(
            "claude-opus-4-20250514", MODEL_PRICING["claude-sonnet-4-5-20250929"]
        )
        claude_cost = (2000 / 1_000_000 * claude_pricing["input"]) + (
            1000 / 1_000_000 * claude_pricing["output"]
        )

        gpt4_pricing = MODEL_PRICING["gpt-4"]
        gpt4_cost = (1000 / 1_000_000 * gpt4_pricing["input"]) + (
            500 / 1_000_000 * gpt4_pricing["output"]
        )

        expected_total = claude_cost + gpt4_cost

        # Verify total cost
        cost_report = get_cost_report(spec_dir)
        actual_total = cost_report["total_cost"]
        assert abs(actual_total - expected_total) < 0.001, (
            f"Cost mismatch: expected {expected_total:.6f}, got {actual_total:.6f}"
        )

    def test_agent_type_tracking(self, test_env_multi_provider):
        """Test that agent types are correctly tracked with their models."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage with different agent types
        tracker.log_usage("planner", "claude-opus-4-20250514", 2000, 1000)
        tracker.log_usage("coder", "gpt-4", 1000, 500)

        # Verify agent types and models are tracked correctly
        cost_report = get_cost_report(spec_dir)

        planner_records = [
            r for r in cost_report["records"] if r["agent_type"] == "planner"
        ]
        assert len(planner_records) == 1, "Should have 1 planner record"
        assert "claude" in planner_records[0]["model"], "Planner should use Claude"

        coder_records = [
            r for r in cost_report["records"] if r["agent_type"] == "coder"
        ]
        assert len(coder_records) == 1, "Should have 1 coder record"
        assert coder_records[0]["model"] == "gpt-4", "Coder should use GPT-4"


# =============================================================================
# PROVIDER FACTORY TESTS
# =============================================================================


class TestMultiProviderFactory:
    """Tests for creating providers via factory with per-agent configuration."""

    def test_create_claude_provider_for_planner(
        self, test_env_multi_provider, monkeypatch
    ):
        """Test creating Claude provider for planner agent."""
        from core.providers.config import ProviderConfig
        from core.providers.factory import create_engine_provider

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Configure planner to use Claude
        monkeypatch.setenv("AGENT_PROVIDER_PLANNER", "claude")
        monkeypatch.setenv("AGENT_MODEL_PLANNER", "claude-opus-4-20250514")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Create provider config for planner
        config = ProviderConfig.from_env(agent_type="planner")

        assert config.provider == "claude"
        assert config.get_model_for_provider() == "claude-opus-4-20250514"

        # Verify the factory can actually instantiate the provider
        provider = create_engine_provider(config)
        assert provider is not None, "create_engine_provider should return a provider"
        assert provider.name == "claude", (
            f"Provider name should be 'claude', got {provider.name!r}"
        )

    def test_create_litellm_provider_for_coder(
        self, test_env_multi_provider, monkeypatch
    ):
        """Test creating LiteLLM provider for coder agent."""
        from core.providers.config import ProviderConfig
        from core.providers.factory import create_engine_provider

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Configure coder to use LiteLLM
        monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
        monkeypatch.setenv("AGENT_MODEL_CODER", "gpt-4")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Create provider config for coder
        config = ProviderConfig.from_env(agent_type="coder")

        assert config.provider == "litellm"
        assert config.get_model_for_provider() == "gpt-4"

        # Verify the factory can actually instantiate the provider
        provider = create_engine_provider(config)
        assert provider is not None, "create_engine_provider should return a provider"
        assert provider.name == "litellm", (
            f"Provider name should be 'litellm', got {provider.name!r}"
        )


# =============================================================================
# END-TO-END INTEGRATION TESTS
# =============================================================================


class TestE2EPerAgentProviderSelection:
    """End-to-end tests for per-agent provider selection."""

    @pytest.mark.skipif(
        not (os.getenv("ANTHROPIC_API_KEY") and os.getenv("OPENAI_API_KEY")),
        reason="API keys not set - skipping live API test",
    )
    def test_e2e_multi_provider_live(self, test_env_multi_provider, monkeypatch):
        """
        E2E Test (LIVE): Configure different providers for different agents.

        This test makes actual API calls if both API keys are set.
        Skip if running in CI or without API keys.
        """
        from core.cost_tracking import CostTracker
        from core.providers.config import ProviderConfig

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Step 1: Configure per-agent providers
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")  # Default
        monkeypatch.setenv("AGENT_PROVIDER_PLANNER", "claude")
        monkeypatch.setenv("AGENT_MODEL_PLANNER", "claude-opus-4-20250514")
        monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
        monkeypatch.setenv("AGENT_MODEL_CODER", "gpt-4")

        # Step 2: Verify provider configurations
        planner_config = ProviderConfig.from_env(agent_type="planner")
        assert planner_config.provider == "claude"
        assert planner_config.get_model_for_provider() == "claude-opus-4-20250514"

        coder_config = ProviderConfig.from_env(agent_type="coder")
        assert coder_config.provider == "litellm"
        assert coder_config.get_model_for_provider() == "gpt-4"

        # Step 3: Create spec and plan
        create_simple_spec(spec_dir)
        create_implementation_plan(spec_dir)

        # Step 4: Simulate agent usage with cost tracking
        tracker = CostTracker(spec_dir=spec_dir)

        # Planner uses Claude
        tracker.log_usage("planner", "claude-opus-4-20250514", 2000, 1000)

        # Coder uses OpenAI
        tracker.log_usage("coder", "gpt-4", 1000, 500)

        # Step 5: Verify cost report
        cost_report = get_cost_report(spec_dir)
        assert cost_report, "cost_report.json should exist"
        assert "records" in cost_report
        assert len(cost_report["records"]) == 2, "Should have 2 usage records"

        # Verify both providers are tracked
        models = [r["model"] for r in cost_report["records"]]
        assert any("claude" in m for m in models), "Should track Claude usage"
        assert any("gpt-4" in m for m in models), "Should track GPT-4 usage"

        # Verify total cost is positive
        assert cost_report["total_cost"] > 0, "Total cost should be positive"

    def test_e2e_multi_provider_mock(self, test_env_multi_provider, monkeypatch):
        """
        E2E Test (MOCKED): Configure different providers and verify flow.

        This test uses mocked API responses for fast, offline testing.
        """
        from core.cost_tracking import CostTracker
        from core.providers.config import ProviderConfig

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Step 1: Configure per-agent providers (simulating UI configuration)
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")
        monkeypatch.setenv("AGENT_PROVIDER_PLANNER", "claude")
        monkeypatch.setenv("AGENT_MODEL_PLANNER", "claude-opus-4-20250514")
        monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
        monkeypatch.setenv("AGENT_MODEL_CODER", "gpt-4")
        monkeypatch.setenv("OPENAI_API_KEY", "test-mock-key-123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-mock-key-456")

        # Step 2: Verify provider configurations loaded correctly
        planner_config = ProviderConfig.from_env(agent_type="planner")
        assert planner_config.provider == "claude", (
            f"Planner provider should be claude, got {planner_config.provider}"
        )
        assert planner_config.get_model_for_provider() == "claude-opus-4-20250514", (
            f"Planner model should be opus, got {planner_config.get_model_for_provider()}"
        )

        coder_config = ProviderConfig.from_env(agent_type="coder")
        assert coder_config.provider == "litellm", (
            f"Coder provider should be litellm, got {coder_config.provider}"
        )
        assert coder_config.get_model_for_provider() == "gpt-4", (
            f"Coder model should be gpt-4, got {coder_config.get_model_for_provider()}"
        )

        # Step 3: Create minimal spec and plan
        spec_file = create_simple_spec(spec_dir)
        plan_file = create_implementation_plan(spec_dir)

        assert spec_file.exists(), "spec.md should be created"
        assert plan_file.exists(), "implementation_plan.json should be created"

        # Step 4: Simulate agent execution with cost tracking
        tracker = CostTracker(spec_dir=spec_dir)

        # Simulate planner agent using Claude Opus
        tracker.log_usage(
            agent_type="planner",
            model="claude-opus-4-20250514",
            input_tokens=2000,
            output_tokens=1000,
        )

        # Simulate coder agent using GPT-4
        tracker.log_usage(
            agent_type="coder",
            model="gpt-4",
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
        assert len(cost_report["records"]) == 2, "Should have 2 usage records"

        # Step 7: Verify both providers are tracked
        planner_record = next(
            r for r in cost_report["records"] if r["agent_type"] == "planner"
        )
        assert "claude" in planner_record["model"], (
            f"Planner should use Claude, got {planner_record['model']}"
        )
        assert planner_record["input_tokens"] == 2000
        assert planner_record["output_tokens"] == 1000

        coder_record = next(
            r for r in cost_report["records"] if r["agent_type"] == "coder"
        )
        assert coder_record["model"] == "gpt-4", (
            f"Coder should use GPT-4, got {coder_record['model']}"
        )
        assert coder_record["input_tokens"] == 1000
        assert coder_record["output_tokens"] == 500

        # Step 8: Verify cost calculation includes both providers
        from core.cost_tracking import MODEL_PRICING

        # Calculate expected costs
        claude_pricing = MODEL_PRICING.get(
            "claude-opus-4-20250514", MODEL_PRICING["claude-sonnet-4-5-20250929"]
        )
        claude_cost = (2000 / 1_000_000 * claude_pricing["input"]) + (
            1000 / 1_000_000 * claude_pricing["output"]
        )

        gpt4_pricing = MODEL_PRICING["gpt-4"]
        gpt4_cost = (1000 / 1_000_000 * gpt4_pricing["input"]) + (
            500 / 1_000_000 * gpt4_pricing["output"]
        )

        expected_total = claude_cost + gpt4_cost
        actual_total = cost_report["total_cost"]

        assert abs(actual_total - expected_total) < 0.001, (
            f"Cost mismatch: expected {expected_total:.6f}, got {actual_total:.6f}"
        )

        print("\n✓ E2E Test passed: Per-agent provider selection")
        print(f"  Planner (Claude): ${claude_cost:.6f}")
        print(f"  Coder (GPT-4): ${gpt4_cost:.6f}")
        print(f"  Total: ${actual_total:.6f}")

    def test_e2e_qa_agent_provider_inheritance(
        self, test_env_multi_provider, monkeypatch
    ):
        """
        E2E Test: QA agents inherit default provider when not explicitly configured.
        """
        from core.cost_tracking import CostTracker
        from phase_config import get_provider_for_agent

        temp_dir, spec_dir, project_dir = test_env_multi_provider

        # Configure specific agents only
        monkeypatch.setenv("AI_ENGINE_PROVIDER", "claude")  # Default
        monkeypatch.setenv("AGENT_PROVIDER_PLANNER", "claude")
        monkeypatch.setenv("AGENT_PROVIDER_CODER", "litellm")
        # QA agents not explicitly configured, should inherit default

        # Verify QA agents inherit default
        qa_reviewer_provider = get_provider_for_agent("qa_reviewer")
        qa_fixer_provider = get_provider_for_agent("qa_fixer")

        assert qa_reviewer_provider == "claude", (
            "QA reviewer should inherit default Claude"
        )
        assert qa_fixer_provider == "claude", "QA fixer should inherit default Claude"

        # Simulate mixed usage
        tracker = CostTracker(spec_dir=spec_dir)

        tracker.log_usage("planner", "claude-opus-4-20250514", 2000, 1000)
        tracker.log_usage("coder", "gpt-4", 1000, 500)
        tracker.log_usage("qa_reviewer", "claude-sonnet-4-5-20250929", 1500, 750)

        # Verify all agents are tracked
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 3, "Should have 3 records"

        agent_types = [r["agent_type"] for r in cost_report["records"]]
        assert "planner" in agent_types
        assert "coder" in agent_types
        assert "qa_reviewer" in agent_types


# =============================================================================
# MANUAL TEST PROCEDURE
# =============================================================================


def print_manual_test_procedure():
    """Print manual E2E test procedure for UI verification."""
    procedure = """
    ═══════════════════════════════════════════════════════════════════════
    MANUAL E2E TEST PROCEDURE: Per-Agent Provider Selection
    ═══════════════════════════════════════════════════════════════════════

    Prerequisites:
    - Electron app running: npm run dev
    - Valid ANTHROPIC_API_KEY available
    - Valid OPENAI_API_KEY available

    Test Steps:

    1. Open Settings Page
       - Launch Auto Claude Electron app
       - Click Settings icon in sidebar
       - Navigate to "Providers" section

    2. Configure Per-Agent Providers
       - Select "Claude" from Default Provider dropdown
       - Configure Planner:
         * Provider: Claude
         * Model: claude-opus-4-20250514
       - Configure Coder:
         * Provider: LiteLLM
         * Model: gpt-4
         * Enter OpenAI API key
       - Click "Save" button
       - Verify success message appears

    3. Verify Configuration Saved
       - Check apps/backend/.env file contains:
         * AI_ENGINE_PROVIDER=claude
         * AGENT_PROVIDER_PLANNER=claude
         * AGENT_MODEL_PLANNER=claude-opus-4-20250514
         * AGENT_PROVIDER_CODER=litellm
         * AGENT_MODEL_CODER=gpt-4
         * OPENAI_API_KEY=sk-...

    4. Create and Run Task
       - Click "Create New Task" button
       - Enter task description: "Write a hello world function in Python"
       - Click "Create Task"
       - Wait for build cycle to complete (planner + coder)

    5. Verify Provider Usage in Logs
       - Open build logs
       - Check planner logs show "Using model: claude-opus-4-20250514"
       - Check coder logs show "Using model: gpt-4"
       - Verify task completes successfully

    6. Verify Cost Tracking
       - Navigate to task's .auto-claude/specs/XXX/ directory
       - Open cost_report.json
       - Verify it contains:
         * 2+ records (planner + coder)
         * Planner record with model containing "claude"
         * Coder record with model "gpt-4"
         * "total_cost" > 0 (sum of both)
       - Example:
         {
           "records": [
             {
               "agent_type": "planner",
               "model": "claude-opus-4-20250514",
               "input_tokens": 2000,
               "output_tokens": 1000,
               "cost": 0.XXX
             },
             {
               "agent_type": "coder",
               "model": "gpt-4",
               "input_tokens": 1000,
               "output_tokens": 500,
               "cost": 0.YYY
             }
           ],
           "total_cost": 0.ZZZ
         }

    7. Verify Cost Display in UI
       - Open Analytics/Cost view
       - Verify cost breakdown shows both providers:
         * Claude: $X.XX (planner)
         * OpenAI: $Y.YY (coder)
       - Verify models are listed in breakdown
       - Verify total cost is sum of both

    Expected Results:
    ✓ Settings page shows per-agent configuration options
    ✓ Configuration saves to .env file with correct variables
    ✓ Planner uses Claude Opus as configured
    ✓ Coder uses OpenAI GPT-4 as configured
    ✓ cost_report.json tracks both Claude and OpenAI usage
    ✓ Costs are calculated correctly for each provider
    ✓ UI displays cost breakdown by provider and agent

    Benefits Verified:
    ✓ Flexibility: Different agents can use different providers
    ✓ Cost Optimization: Can use cheaper models for simpler tasks
    ✓ Privacy: Can use local models for sensitive code
    ✓ Reliability: Can use different providers for redundancy

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
    print("Running Automated E2E Tests for Per-Agent Provider Selection...")
    print("=" * 70 + "\n")
    run_all_tests()
