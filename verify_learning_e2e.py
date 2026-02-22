#!/usr/bin/env python3
"""
Standalone verification script for learning from failures E2E flow.
This can be run without pytest to verify the implementation.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Mock SDK modules before importing
mock_agent_sdk = MagicMock()
mock_agent_sdk.ClaudeSDKClient = MagicMock()
mock_agent_sdk.ClaudeAgentOptions = MagicMock()
sys.modules['claude_agent_sdk'] = mock_agent_sdk
sys.modules['claude_agent_sdk.types'] = MagicMock()
sys.modules['claude_code_sdk'] = mock_agent_sdk
sys.modules['claude_code_sdk.types'] = MagicMock()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from analysis.failure_analyzer import analyze_failure, format_for_graphiti
from analysis.metrics_tracker import get_success_rate, get_improvement_trends, get_detailed_metrics
from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_ROOT_CAUSE, EPISODE_TYPE_USER_CORRECTION
from qa.report import get_learning_metrics, initialize_learning_metrics, increment_learning_metric


def create_test_environment():
    """Create a temporary test environment."""
    temp_dir = Path(tempfile.mkdtemp())
    spec_dir = temp_dir / "specs" / "001-test"
    spec_dir.mkdir(parents=True)

    project_dir = temp_dir / "project"
    project_dir.mkdir(parents=True)

    # Create implementation_plan.json
    plan = {
        "feature": "Test Feature",
        "status": "in_progress",
        "qa_iteration_history": [
            {
                "iteration": 1,
                "status": "rejected",
                "timestamp": "2024-01-20T10:00:00Z",
                "issues": [
                    {
                        "type": "syntax_error",
                        "file": "src/main.py",
                        "message": "SyntaxError: invalid syntax on line 42",
                        "occurrence_count": 1
                    }
                ]
            },
            {
                "iteration": 2,
                "status": "approved",
                "timestamp": "2024-01-20T11:00:00Z"
            }
        ],
        "learning_metrics": {
            "root_causes_identified": 0,
            "user_corrections_applied": 0,
            "patterns_applied": 0
        }
    }

    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps(plan, indent=2))

    return spec_dir, project_dir


def test_step_1_failure_analysis():
    """Step 1: Failed build → Root cause extraction"""
    print("Step 1: Testing failure analysis...")

    spec_dir, project_dir = create_test_environment()

    issues = [
        {
            "type": "syntax_error",
            "file": "src/main.py",
            "message": "SyntaxError: invalid syntax - missing closing parenthesis",
            "occurrence_count": 1
        }
    ]

    result = analyze_failure(
        spec_dir=spec_dir,
        project_dir=project_dir,
        failure_type="qa_rejection",
        issues=issues,
        is_recurring=False,
        context={"qa_iteration": 1}
    )

    assert result is not None, "❌ analyze_failure returned None"
    assert "root_cause" in result, "❌ Result missing root_cause"
    assert "category" in result, "❌ Result missing category"
    assert result["category"] == "syntax_error", "❌ Wrong category detected"

    print("✅ Step 1 passed: Failure analyzer extracts root cause")
    return spec_dir, project_dir


def test_step_2_graphiti_formatting(spec_dir, project_dir):
    """Step 2: Root cause → Formatted for Graphiti storage"""
    print("\nStep 2: Testing Graphiti formatting...")

    issues = [
        {
            "type": "logic_error",
            "file": "src/auth.py",
            "message": "TypeError: 'NoneType' object is not subscriptable",
            "occurrence_count": 2
        }
    ]

    result = analyze_failure(
        spec_dir=spec_dir,
        project_dir=project_dir,
        failure_type="qa_rejection",
        issues=issues,
        is_recurring=True,
        context={"qa_iteration": 2}
    )

    formatted = format_for_graphiti(result, str(spec_dir))

    assert formatted["episode_type"] == EPISODE_TYPE_ROOT_CAUSE, "❌ Wrong episode type"
    assert "content" in formatted, "❌ Missing content"
    assert "metadata" in formatted, "❌ Missing metadata"
    assert formatted["metadata"]["is_recurring"] is True, "❌ is_recurring not set"

    print("✅ Step 2 passed: Root cause formatted for Graphiti")


def test_step_3_metrics_storage(spec_dir):
    """Step 3: Pattern stored → Metrics updated"""
    print("\nStep 3: Testing metrics storage...")

    # Initialize metrics
    initialize_learning_metrics(spec_dir)

    initial = get_learning_metrics(spec_dir)
    assert initial["root_causes_identified"] == 0, "❌ Initial metrics wrong"

    # Simulate storing root cause
    increment_learning_metric(spec_dir, "root_causes_identified")

    updated = get_learning_metrics(spec_dir)
    assert updated["root_causes_identified"] == 1, "❌ Metrics not updated"

    print("✅ Step 3 passed: Metrics track root causes")


def test_step_4_retrieval_and_trends(spec_dir):
    """Step 4: Retrieved in next session → Metrics show improvement"""
    print("\nStep 4: Testing metrics retrieval and trends...")

    # Get success rate
    success_metrics = get_success_rate(spec_dir)
    assert "overall_success_rate" in success_metrics, "❌ Missing success rate"
    assert success_metrics["overall_success_rate"] == 50.0, "❌ Wrong success rate (should be 50%)"

    # Get trends
    trends = get_improvement_trends(spec_dir)
    assert "overall_trend" in trends, "❌ Missing overall trend"
    assert trends["overall_trend"] in ["improving", "stable", "declining"], "❌ Invalid trend value"

    # Get detailed metrics
    detailed = get_detailed_metrics(spec_dir)
    assert "success_metrics" in detailed, "❌ Missing success metrics"
    assert "trends" in detailed, "❌ Missing trends"
    assert "learning_metrics" in detailed, "❌ Missing learning metrics"
    assert detailed["learning_metrics"]["root_causes_identified"] == 1, "❌ Root cause count wrong"

    print("✅ Step 4 passed: Metrics retrieved and trends calculated")


def test_step_5_user_corrections(spec_dir):
    """Step 5: User correction tracking"""
    print("\nStep 5: Testing user correction tracking...")

    # Increment user corrections
    increment_learning_metric(spec_dir, "user_corrections_applied")
    increment_learning_metric(spec_dir, "user_corrections_applied")

    metrics = get_learning_metrics(spec_dir)
    assert metrics["user_corrections_applied"] == 2, "❌ User corrections not tracked"

    print("✅ Step 5 passed: User corrections tracked")


def test_step_6_episode_types():
    """Step 6: Verify episode types exist"""
    print("\nStep 6: Testing episode type definitions...")

    assert EPISODE_TYPE_ROOT_CAUSE == "root_cause", "❌ Wrong episode type"
    assert EPISODE_TYPE_USER_CORRECTION == "user_correction", "❌ Wrong episode type"

    print("✅ Step 6 passed: Episode types defined correctly")


def main():
    """Run all end-to-end verification steps."""
    print("=" * 60)
    print("Learning from Failures - End-to-End Verification")
    print("=" * 60)

    try:
        # Step 1: Failure analysis
        spec_dir, project_dir = test_step_1_failure_analysis()

        # Step 2: Graphiti formatting
        test_step_2_graphiti_formatting(spec_dir, project_dir)

        # Step 3: Metrics storage
        test_step_3_metrics_storage(spec_dir)

        # Step 4: Retrieval and trends
        test_step_4_retrieval_and_trends(spec_dir)

        # Step 5: User corrections
        test_step_5_user_corrections(spec_dir)

        # Step 6: Episode types
        test_step_6_episode_types()

        print("\n" + "=" * 60)
        print("✅ ALL END-TO-END TESTS PASSED")
        print("=" * 60)
        print("\nVerification Summary:")
        print("1. ✅ Failed build → Root cause extraction")
        print("2. ✅ Root cause → Formatted for Graphiti storage")
        print("3. ✅ Pattern stored → Metrics updated")
        print("4. ✅ Retrieved in next session → Trends calculated")
        print("5. ✅ User corrections tracked")
        print("6. ✅ Episode types defined")

        return 0

    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
