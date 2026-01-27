#!/usr/bin/env python3
"""
Standalone E2E Verification Script for Multi-Model Agent Orchestration
=======================================================================

This script verifies the complete multi-model orchestration flow:
1. Create task_metadata.json with agentModels configuration
2. Verify correct models are resolved for each agent
3. Log usage and verify cost_report.json is created
4. Verify logs show model selection process

Run from project root:
    python verify_multi_model_orchestration.py
"""

import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

# Setup logging to see model selection process
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

def main():
    """Run E2E verification."""
    print("=" * 70)
    print("Multi-Model Agent Orchestration - E2E Verification")
    print("=" * 70)
    print()

    # Use the current spec directory
    spec_dir = Path(".auto-claude/specs/024-multi-model-agent-orchestration")
    spec_dir.mkdir(parents=True, exist_ok=True)

    # Clean up old cost report for clean test run
    cost_report_file = spec_dir / "cost_report.json"
    if cost_report_file.exists():
        print("Cleaning up old cost_report.json for fresh test run...")
        cost_report_file.unlink()
        print()

    # =========================================================================
    # STEP 1: Create task_metadata.json with agentModels configuration
    # =========================================================================
    print("STEP 1: Creating task_metadata.json with custom agent models...")

    custom_agent_models = {
        "planner": "opus",      # Most capable model for planning
        "coder": "sonnet",      # Balanced model for coding
        "qa_reviewer": "haiku", # Fast model for QA
    }

    task_metadata = {
        "taskDescription": "Multi-model orchestration E2E test",
        "timestamp": "2026-01-27T00:00:00.000Z",
        "agentModels": custom_agent_models
    }

    metadata_file = spec_dir / "task_metadata.json"
    metadata_file.write_text(json.dumps(task_metadata, indent=2))
    print(f"✓ Created {metadata_file}")
    print(f"  Agent models: {json.dumps(custom_agent_models, indent=4)}")
    print()

    # =========================================================================
    # STEP 2: Verify correct models are used for each agent
    # =========================================================================
    print("STEP 2: Verifying correct models are resolved for each agent...")

    from phase_config import get_agent_model

    # Test planner model (should be opus)
    planner_model = get_agent_model(spec_dir, "planner")
    print(f"  Planner model: {planner_model}")
    assert "opus" in planner_model, f"Expected opus, got {planner_model}"
    print(f"    ✓ Planner correctly uses opus")

    # Test coder model (should be sonnet)
    coder_model = get_agent_model(spec_dir, "coder")
    print(f"  Coder model: {coder_model}")
    assert "sonnet" in coder_model, f"Expected sonnet, got {coder_model}"
    print(f"    ✓ Coder correctly uses sonnet")

    # Test QA model (should be haiku)
    qa_model = get_agent_model(spec_dir, "qa_reviewer")
    print(f"  QA Reviewer model: {qa_model}")
    assert "haiku" in qa_model, f"Expected haiku, got {qa_model}"
    print(f"    ✓ QA Reviewer correctly uses haiku")
    print()

    # =========================================================================
    # STEP 3: Simulate agent sessions and verify cost tracking
    # =========================================================================
    print("STEP 3: Simulating agent sessions and tracking costs...")

    from core.cost_tracking import CostTracker

    tracker = CostTracker(spec_dir=spec_dir)

    # Simulate planner agent session (opus - expensive)
    print(f"  Logging planner usage (opus): 5000 input, 2000 output tokens")
    tracker.log_usage(
        agent_type="planner",
        model=planner_model,
        input_tokens=5000,
        output_tokens=2000
    )

    # Simulate coder agent session (sonnet - balanced)
    print(f"  Logging coder usage (sonnet): 10000 input, 5000 output tokens")
    tracker.log_usage(
        agent_type="coder",
        model=coder_model,
        input_tokens=10000,
        output_tokens=5000
    )

    # Simulate QA agent session (haiku - cheap)
    print(f"  Logging qa_reviewer usage (haiku): 3000 input, 1000 output tokens")
    tracker.log_usage(
        agent_type="qa_reviewer",
        model=qa_model,
        input_tokens=3000,
        output_tokens=1000
    )
    print()

    # =========================================================================
    # STEP 4: Verify cost_report.json was created with correct data
    # =========================================================================
    print("STEP 4: Verifying cost_report.json...")

    cost_report_file = spec_dir / "cost_report.json"
    assert cost_report_file.exists(), "cost_report.json should exist"
    print(f"✓ {cost_report_file} exists")

    cost_report = json.loads(cost_report_file.read_text())

    # Verify structure
    assert "total_cost" in cost_report, "Should have total_cost"
    assert "records" in cost_report, "Should have records"
    assert len(cost_report["records"]) == 3, f"Should have 3 records, got {len(cost_report['records'])}"
    print(f"  ✓ Has correct structure with {len(cost_report['records'])} records")

    # Verify all agents are tracked
    agent_types = {r["agent_type"] for r in cost_report["records"]}
    expected_agents = {"planner", "coder", "qa_reviewer"}
    assert agent_types == expected_agents, f"Expected {expected_agents}, got {agent_types}"
    print(f"  ✓ All agent types tracked: {agent_types}")

    # Verify all models are tracked
    models = {r["model"] for r in cost_report["records"]}
    assert any("opus" in m for m in models), "Should track opus"
    assert any("sonnet" in m for m in models), "Should track sonnet"
    assert any("haiku" in m for m in models), "Should track haiku"
    print(f"  ✓ All model types tracked")

    # Verify total cost is positive
    total_cost = cost_report["total_cost"]
    assert total_cost > 0, "Total cost should be positive"
    print(f"  ✓ Total cost calculated: ${total_cost:.6f}")
    print()

    # =========================================================================
    # STEP 5: Display cost summary
    # =========================================================================
    print("STEP 5: Generating cost summary...")
    print()

    summary = tracker.get_cost_summary()
    print(summary)
    print()

    # =========================================================================
    # VERIFICATION COMPLETE
    # =========================================================================
    print("=" * 70)
    print("✓ ALL VERIFICATION STEPS PASSED")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  • task_metadata.json created with custom agent models")
    print(f"  • Model resolution working (opus/sonnet/haiku)")
    print(f"  • Cost tracking functional with {len(cost_report['records'])} records")
    print(f"  • Total cost: ${total_cost:.6f}")
    print(f"  • cost_report.json: {cost_report_file}")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
