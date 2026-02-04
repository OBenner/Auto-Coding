#!/usr/bin/env python3
"""
Quick verification script for per-agent provider selection.
Tests the core functionality without requiring full pytest setup.
"""

import json
import os
import sys
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

def test_per_agent_provider_configuration():
    """Test that per-agent provider configuration works."""
    from phase_config import get_provider_for_agent

    print("Testing per-agent provider configuration...")

    # Save original env vars
    orig_provider = os.environ.get("AI_ENGINE_PROVIDER")
    orig_planner = os.environ.get("AGENT_PROVIDER_PLANNER")
    orig_coder = os.environ.get("AGENT_PROVIDER_CODER")

    try:
        # Set test configuration
        os.environ["AI_ENGINE_PROVIDER"] = "claude"
        os.environ["AGENT_PROVIDER_PLANNER"] = "claude"
        os.environ["AGENT_MODEL_PLANNER"] = "claude-opus-4-20250514"
        os.environ["AGENT_PROVIDER_CODER"] = "litellm"
        os.environ["AGENT_MODEL_CODER"] = "gpt-4"

        # Test planner uses claude
        planner_provider = get_provider_for_agent("planner")
        assert planner_provider == "claude", f"✗ Planner should use Claude, got {planner_provider}"
        print("✓ Planner uses Claude")

        # Test coder uses litellm
        coder_provider = get_provider_for_agent("coder")
        assert coder_provider == "litellm", f"✗ Coder should use LiteLLM, got {coder_provider}"
        print("✓ Coder uses LiteLLM")

        # Test fallback to default
        os.environ.pop("AGENT_PROVIDER_QA_REVIEWER", None)
        qa_provider = get_provider_for_agent("qa_reviewer")
        assert qa_provider == "claude", f"✗ QA reviewer should fall back to Claude, got {qa_provider}"
        print("✓ QA reviewer falls back to default Claude")

    finally:
        # Restore original env vars
        if orig_provider:
            os.environ["AI_ENGINE_PROVIDER"] = orig_provider
        else:
            os.environ.pop("AI_ENGINE_PROVIDER", None)

        if orig_planner:
            os.environ["AGENT_PROVIDER_PLANNER"] = orig_planner
        else:
            os.environ.pop("AGENT_PROVIDER_PLANNER", None)

        if orig_coder:
            os.environ["AGENT_PROVIDER_CODER"] = orig_coder
        else:
            os.environ.pop("AGENT_PROVIDER_CODER", None)


def test_cost_tracking_multi_provider():
    """Test that cost tracking works with multiple providers."""
    from core.cost_tracking import CostTracker, MODEL_PRICING
    import tempfile
    import shutil

    print("\nTesting multi-provider cost tracking...")

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    spec_dir = temp_dir / "test_spec"
    spec_dir.mkdir(parents=True)

    try:
        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for both providers
        tracker.log_usage("planner", "claude-opus-4-20250514", 2000, 1000)
        tracker.log_usage("coder", "gpt-4", 1000, 500)

        # Read cost report
        cost_report_file = spec_dir / "cost_report.json"
        assert cost_report_file.exists(), "✗ cost_report.json should be created"

        with open(cost_report_file, "r") as f:
            cost_report = json.load(f)

        # Verify structure
        assert "records" in cost_report, "✗ Should have records"
        assert len(cost_report["records"]) == 2, f"✗ Should have 2 records, got {len(cost_report['records'])}"
        print("✓ Cost report has 2 records")

        # Verify both models are tracked
        models = [r["model"] for r in cost_report["records"]]
        assert any("claude" in m for m in models), "✗ Should track Claude usage"
        print("✓ Claude usage tracked")

        assert any("gpt-4" in m for m in models), "✗ Should track GPT-4 usage"
        print("✓ GPT-4 usage tracked")

        # Verify agent types
        agent_types = [r["agent_type"] for r in cost_report["records"]]
        assert "planner" in agent_types, "✗ Should track planner agent"
        assert "coder" in agent_types, "✗ Should track coder agent"
        print("✓ Both agent types tracked")

        # Verify cost calculation
        assert cost_report["total_cost"] > 0, "✗ Total cost should be positive"
        print(f"✓ Total cost calculated: ${cost_report['total_cost']:.6f}")

        # Verify individual costs
        claude_pricing = MODEL_PRICING.get("claude-opus-4-20250514", MODEL_PRICING["claude-sonnet-4-5-20250929"])
        expected_claude = (2000 / 1_000_000 * claude_pricing["input"]) + (1000 / 1_000_000 * claude_pricing["output"])

        gpt4_pricing = MODEL_PRICING["gpt-4"]
        expected_gpt4 = (1000 / 1_000_000 * gpt4_pricing["input"]) + (500 / 1_000_000 * gpt4_pricing["output"])

        expected_total = expected_claude + expected_gpt4
        actual_total = cost_report["total_cost"]

        assert abs(actual_total - expected_total) < 0.001, (
            f"✗ Cost mismatch: expected {expected_total:.6f}, got {actual_total:.6f}"
        )
        print(f"✓ Cost calculation correct (Claude: ${expected_claude:.6f}, GPT-4: ${expected_gpt4:.6f})")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_model_pricing():
    """Test that pricing exists for both Claude and OpenAI models."""
    from core.cost_tracking import MODEL_PRICING

    print("\nTesting model pricing database...")

    # Check Claude pricing
    claude_models = [k for k in MODEL_PRICING.keys() if "claude" in k]
    assert len(claude_models) > 0, "✗ Should have Claude model pricing"
    print(f"✓ Claude pricing exists ({len(claude_models)} models)")

    # Check OpenAI pricing
    assert "gpt-4" in MODEL_PRICING, "✗ Should have GPT-4 pricing"
    gpt4_pricing = MODEL_PRICING["gpt-4"]
    assert "input" in gpt4_pricing, "✗ GPT-4 should have input pricing"
    assert "output" in gpt4_pricing, "✗ GPT-4 should have output pricing"
    assert gpt4_pricing["input"] > 0, "✗ GPT-4 input price should be positive"
    assert gpt4_pricing["output"] > 0, "✗ GPT-4 output price should be positive"
    print("✓ GPT-4 pricing exists and is positive")

    # Check multiple GPT models
    gpt_models = [k for k in MODEL_PRICING.keys() if k.startswith("gpt-")]
    print(f"✓ OpenAI pricing exists ({len(gpt_models)} models)")

    # Check Ollama models (zero cost)
    ollama_models = [k for k in MODEL_PRICING.keys() if k.startswith("ollama/")]
    if ollama_models:
        print(f"✓ Ollama pricing exists ({len(ollama_models)} models, zero cost)")


def main():
    """Run all verification tests."""
    print("="*70)
    print("Per-Agent Provider Selection - Verification Tests")
    print("="*70)

    try:
        test_per_agent_provider_configuration()
        test_cost_tracking_multi_provider()
        test_model_pricing()

        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)
        print("\nVerification Summary:")
        print("✓ Per-agent provider configuration works")
        print("✓ Planner can use Claude while coder uses OpenAI")
        print("✓ Cost tracking correctly records both providers")
        print("✓ cost_report.json shows usage from both Claude and OpenAI")
        print("\nThe E2E test file has been created and follows the same patterns")
        print("as existing E2E tests (test_openai_provider_e2e.py, test_ollama_provider_e2e.py).")
        print("\nTo run the full E2E test suite:")
        print("  pytest tests/test_per_agent_provider_e2e.py -v")

        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
