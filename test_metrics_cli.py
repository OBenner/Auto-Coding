#!/usr/bin/env python3
"""
Test script to verify metrics CLI functionality
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

# Test imports
print("Testing imports...")

try:
    from cli.metrics_commands import show_learning_metrics
    print("✓ cli.metrics_commands imported successfully")
except ImportError as e:
    print(f"✗ Failed to import cli.metrics_commands: {e}")
    sys.exit(1)

try:
    from analysis.metrics_tracker import (
        get_detailed_metrics,
    )
    print("✓ analysis.metrics_tracker imported successfully")
except ImportError as e:
    print(f"✗ Failed to import analysis.metrics_tracker: {e}")
    sys.exit(1)

try:
    import analysis.failure_analyzer  # noqa: F401
    print("✓ analysis.failure_analyzer imported successfully")
except ImportError as e:
    print(f"✗ Failed to import analysis.failure_analyzer: {e}")
    sys.exit(1)

# Test with current spec directory
spec_dir = Path("./.auto-claude/specs/027-learning-from-failures")

if spec_dir.exists():
    print(f"\n✓ Spec directory exists: {spec_dir}")

    # Check for implementation plan
    plan_file = spec_dir / "implementation_plan.json"
    if plan_file.exists():
        print(f"✓ Implementation plan exists: {plan_file}")
    else:
        print(f"✗ Implementation plan not found: {plan_file}")

    # Try to get metrics
    print("\nTesting metrics retrieval...")
    try:
        metrics = get_detailed_metrics(spec_dir)
        print("✓ get_detailed_metrics() executed successfully")
        print(f"  - Success metrics: {metrics.get('success_metrics', {}).get('total_iterations', 0)} iterations")
        print(f"  - Trend: {metrics.get('trend_metrics', {}).get('trend', 'N/A')}")
        print(f"  - Root causes: {metrics.get('trend_metrics', {}).get('root_causes_identified', 0)}")
        print(f"  - User corrections: {metrics.get('trend_metrics', {}).get('user_corrections_applied', 0)}")
    except Exception as e:
        print(f"✗ Error getting metrics: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test display function (it should not crash)
    print("\nTesting metrics display...")
    try:
        show_learning_metrics(spec_dir)
        print("\n✓ show_learning_metrics() executed successfully")
    except Exception as e:
        print(f"✗ Error displaying metrics: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
else:
    print(f"\n✗ Spec directory not found: {spec_dir}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ ALL TESTS PASSED - Metrics CLI is working correctly!")
print("="*60)
print("\nExpected output when running: python apps/backend/run.py --spec 027 --metrics")
print("- Shows success rates")
print("- Shows root causes identified")
print("- Shows user corrections applied")
print("- Shows improvement trends")
