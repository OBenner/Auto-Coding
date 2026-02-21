#!/usr/bin/env python3
"""
Demo script for AI Decision Explainability feature.

This script demonstrates the end-to-end decision tracking workflow:
1. Initializes decision tracking for a spec
2. Tracks multiple decisions with alternatives and reasoning
3. Logs decisions to task logs
4. Displays decision statistics
5. Shows data persistence

Usage:
    python demo_decision_tracking.py
"""

import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from agents.decision_tracker import DecisionTracker
from task_logger.decision_models import Alternative, DecisionType
from task_logger.logger import TaskLogger
from task_logger.models import LogPhase


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_decision_tracking():
    """Demonstrate the decision tracking feature end-to-end."""

    print_section("AI Decision Explainability Demo")

    # Setup
    spec_dir = Path(".auto-claude/specs/demo-decision-tracking")
    spec_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Spec directory: {spec_dir}")

    # Initialize TaskLogger
    print("\n🔧 Initializing TaskLogger...")
    task_logger = TaskLogger(spec_dir, emit_markers=False)
    task_logger.start_phase(LogPhase.PLANNING, "Demo: Planning Phase")

    # Initialize DecisionTracker
    print("🔧 Initializing DecisionTracker...")
    tracker = DecisionTracker(spec_dir, task_logger, LogPhase.PLANNING)
    tracker.set_session(1)

    # Decision 1: High confidence decision with alternatives
    print_section("Decision 1: Architecture Decision (High Confidence)")

    decision1 = tracker.track_decision(
        decision_type=DecisionType.ARCHITECTURE,
        context="Design the authentication system architecture",
        chosen_approach="JWT-based authentication with refresh tokens and HttpOnly cookies",
        reasoning=(
            "Provides stateless authentication, good security (XSS protection via HttpOnly), "
            "and enables session renewal without constant re-authentication. "
            "Widely adopted pattern with extensive tooling support."
        ),
        confidence=0.92,
        impact="Secure, scalable authentication that supports both web and mobile clients",
        reversible=False,  # Architectural decisions are hard to reverse
        dependencies=["JWT library (e.g., PyJWT)", "secure cookie handling"]
    )

    # Add alternatives
    alt1_1 = Alternative(
        description="Session-based authentication with server-side storage",
        reasoning="Traditional approach, well-understood by most developers",
        rejected_reason=(
            "Requires server-side state management, harder to scale horizontally, "
            "doesn't work well for mobile/API clients"
        ),
        tradeoffs=["Simpler initial implementation", "Harder to scale", "Server must maintain state"]
    )
    tracker.add_alternative(decision1, alt1_1)

    alt1_2 = Alternative(
        description="OAuth2 with third-party provider (e.g., Auth0, Firebase)",
        reasoning="Offloads authentication complexity to specialized service",
        rejected_reason=(
            "Adds external dependency, monthly costs, vendor lock-in, "
            "less control over auth flow customization"
        ),
        tradeoffs=["Less implementation work", "External dependency", "Monthly costs"]
    )
    tracker.add_alternative(decision1, alt1_2)

    # Add reasoning chain
    tracker.add_reasoning_step(decision1, "1. Analyzed security requirements: XSS protection, CSRF prevention, token theft mitigation")
    tracker.add_reasoning_step(decision1, "2. Evaluated three approaches: sessions, JWT, OAuth2 provider")
    tracker.add_reasoning_step(decision1, "3. Considered scalability: need horizontal scaling support")
    tracker.add_reasoning_step(decision1, "4. Assessed maintainability: team expertise with JWT patterns")
    tracker.add_reasoning_step(decision1, "5. Selected JWT + refresh tokens for security + scalability balance")

    # Log decision
    tracker.log_decision(decision1, print_to_console=True)

    print(f"\n✓ Decision tracked:")
    print(f"  • Type: {decision1.decision_type}")
    print(f"  • Confidence: {decision1.confidence:.2f} ({decision1.confidence_level})")
    print(f"  • Alternatives: {len(decision1.alternatives)}")
    print(f"  • Reasoning steps: {len(decision1.reasoning_chain)}")
    print(f"  • Requires review: {decision1.requires_review}")

    # Decision 2: Medium confidence implementation decision
    print_section("Decision 2: Implementation Decision (Medium Confidence)")

    task_logger.end_phase(LogPhase.PLANNING, success=True)
    task_logger.start_phase(LogPhase.CODING, "Demo: Coding Phase")
    tracker.set_phase(LogPhase.CODING)
    tracker.set_subtask("implement-validation")

    decision2 = tracker.track_decision(
        decision_type=DecisionType.IMPLEMENTATION,
        context="Choose data validation approach for API request payloads",
        chosen_approach="Pydantic v2 models with custom validators",
        reasoning=(
            "Type-safe validation with excellent IDE support. "
            "v2 offers significant performance improvements. "
            "Custom validators allow domain-specific rules."
        ),
        confidence=0.78,
        impact="Reduces validation errors by ~40%, improves code documentation",
        reversible=True,
        dependencies=["pydantic>=2.0"]
    )

    alt2_1 = Alternative(
        description="Marshmallow schemas",
        reasoning="Popular alternative with flexible serialization",
        rejected_reason="Less type-safe, more boilerplate, slower than Pydantic v2",
        tradeoffs=["More flexible serialization", "Less type safety", "More code"]
    )
    tracker.add_alternative(decision2, alt2_1)

    tracker.add_reasoning_step(decision2, "1. Need type-safe validation for 20+ API endpoints")
    tracker.add_reasoning_step(decision2, "2. Compared Pydantic v2 (fast, type-safe) vs Marshmallow (flexible)")
    tracker.add_reasoning_step(decision2, "3. Pydantic v2 chosen for performance + type safety benefits")

    tracker.log_decision(decision2, print_to_console=True)

    print(f"\n✓ Decision tracked:")
    print(f"  • Type: {decision2.decision_type}")
    print(f"  • Confidence: {decision2.confidence:.2f} ({decision2.confidence_level})")
    print(f"  • Alternatives: {len(decision2.alternatives)}")

    # Decision 3: Low confidence decision (flagged for review)
    print_section("Decision 3: Optimization Decision (Low Confidence)")

    decision3 = tracker.track_decision(
        decision_type=DecisionType.OPTIMIZATION,
        context="Optimize database query performance for user dashboard",
        chosen_approach="Add Redis caching layer with 5-minute TTL",
        reasoning=(
            "Should reduce database load, but impact unclear without load testing. "
            "TTL value is a guess based on typical usage patterns."
        ),
        confidence=0.52,  # Low confidence - will auto-flag for review
        impact="Potentially 30-60% faster dashboard load (needs verification)",
        reversible=True,
        dependencies=["Redis server", "redis-py client"]
    )

    alt3_1 = Alternative(
        description="Optimize SQL queries with proper indexes",
        reasoning="No new dependencies, directly addresses root cause",
        rejected_reason="Tried this first, only got 20% improvement - need more",
        tradeoffs=["No new dependencies", "Limited improvement", "Already implemented"]
    )
    tracker.add_alternative(decision3, alt3_1)

    alt3_2 = Alternative(
        description="Pre-compute dashboard data in background job",
        reasoning="Maximum performance, dashboard loads instantly",
        rejected_reason="Requires job scheduler, data might be stale, complex to implement",
        tradeoffs=["Fastest option", "Data staleness issues", "Complex implementation"]
    )
    tracker.add_alternative(decision3, alt3_2)

    tracker.add_reasoning_step(decision3, "1. Dashboard load time averages 2.5s - too slow")
    tracker.add_reasoning_step(decision3, "2. SQL optimization reduced to 2.0s - still not fast enough")
    tracker.add_reasoning_step(decision3, "3. Caching seems promising but impact uncertain")
    tracker.add_reasoning_step(decision3, "4. ⚠️ Need load testing to validate before full rollout")

    tracker.log_decision(decision3, print_to_console=True)

    print(f"\n✓ Decision tracked:")
    print(f"  • Type: {decision3.decision_type}")
    print(f"  • Confidence: {decision3.confidence:.2f} ({decision3.confidence_level})")
    print(f"  • ⚠️ Requires review: {decision3.requires_review} (auto-flagged)")

    # Show statistics
    print_section("Decision Statistics")

    stats = tracker.get_decision_stats()

    print(f"\n📊 Total decisions: {stats['total']}")

    print(f"\n📋 By type:")
    for dtype, count in stats['by_type'].items():
        print(f"   • {dtype}: {count}")

    print(f"\n🎯 By confidence level:")
    for level, count in stats['by_confidence_level'].items():
        print(f"   • {level}: {count}")

    print(f"\n📈 Average confidence: {stats['avg_confidence']:.2%}")
    print(f"⚠️ Requiring review: {stats['requiring_review']}")

    # Show review-flagged decisions
    if stats['requiring_review'] > 0:
        print(f"\n⚠️ Decisions flagged for review:")
        review_decisions = tracker.get_decisions_requiring_review()
        for i, dec in enumerate(review_decisions, 1):
            print(f"   {i}. {dec.decision_type}: {dec.chosen_approach}")
            print(f"      Confidence: {dec.confidence:.2f} ({dec.confidence_level})")

    # Verify persistence
    print_section("Data Persistence Verification")

    decisions_file = spec_dir / "decisions.json"
    task_logs_file = spec_dir / "task_logs.json"

    print(f"\n📄 Files created:")
    print(f"   • {decisions_file} ({decisions_file.stat().st_size} bytes)")
    print(f"   • {task_logs_file} ({task_logs_file.stat().st_size} bytes)")

    # Load and verify decisions.json
    with open(decisions_file, "r", encoding="utf-8") as f:
        decisions_data = json.load(f)

    print(f"\n✓ decisions.json contains {len(decisions_data['decisions'])} decisions")

    # Load and verify task_logs.json
    with open(task_logs_file, "r", encoding="utf-8") as f:
        logs_data = json.load(f)

    decision_log_count = sum(
        1 for phase_data in logs_data['phases'].values()
        for entry in phase_data.get('entries', [])
        if 'Decision:' in entry.get('content', '')
    )

    print(f"✓ task_logs.json contains {decision_log_count} decision log entries")

    # Summary
    print_section("Demo Complete")

    print("\n✅ Successfully demonstrated:")
    print("   • Decision tracking with DecisionTracker")
    print("   • Multiple decision types (architecture, implementation, optimization)")
    print("   • Confidence levels (high, medium, low)")
    print("   • Alternatives and reasoning chains")
    print("   • Automatic review flagging for low confidence")
    print("   • Persistence to decisions.json and task_logs.json")
    print("   • Decision statistics and filtering")

    print(f"\n📁 Demo data saved to: {spec_dir}")
    print("\n💡 Next steps:")
    print("   • View decisions.json to see the full decision data")
    print("   • View task_logs.json to see decision log entries")
    print("   • Open the frontend to see DecisionExplainer and DecisionTree components")
    print("   • Run tests: pytest tests/test_decision_tracking_e2e.py -v")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        demo_decision_tracking()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
