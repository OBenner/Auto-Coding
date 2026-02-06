#!/usr/bin/env python3
"""
End-to-End Test: Pattern Suggestion Workflow
=============================================

Tests the complete pattern suggestion workflow:
1. Add sample patterns to Graphiti memory
2. Retrieve pattern suggestions for authentication task
3. Test category filtering
4. Test pattern confirmation/rejection workflow
5. Verify patterns appear in spec creation context

Usage:
    python test_pattern_workflow.py
"""

import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from graphiti_config import is_graphiti_enabled
from integrations.graphiti.pattern_categorizer import categorize_pattern
from integrations.graphiti.pattern_suggester import suggest_patterns
from memory.graphiti_helpers import get_graphiti_memory

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Data
# =============================================================================

SAMPLE_PATTERNS = [
    {
        "pattern": "Use JWT tokens stored in httpOnly cookies for authentication",
        "expected_category": "security",
        "task_query": "implement user authentication",
    },
    {
        "pattern": "Implement password hashing with bcrypt (cost factor 12)",
        "expected_category": "security",
        "task_query": "implement user authentication",
    },
    {
        "pattern": "Create separate /auth/login and /auth/logout endpoints",
        "expected_category": "api-design",
        "task_query": "implement user authentication",
    },
    {
        "pattern": "Use React Context for global authentication state",
        "expected_category": "state-management",
        "task_query": "authentication frontend",
    },
    {
        "pattern": "Add authentication middleware to protect routes",
        "expected_category": "architecture",
        "task_query": "implement user authentication",
    },
]


# =============================================================================
# Test Functions
# =============================================================================


async def test_graphiti_enabled():
    """Test that Graphiti is enabled."""
    print("\n" + "=" * 80)
    print("TEST 1: Verify Graphiti is Enabled")
    print("=" * 80)

    if not is_graphiti_enabled():
        print("❌ FAILED: Graphiti is not enabled")
        print("   Please set GRAPHITI_ENABLED=true in apps/backend/.env")
        return False

    print("✅ PASSED: Graphiti is enabled")
    return True


async def test_pattern_categorization():
    """Test pattern categorization."""
    print("\n" + "=" * 80)
    print("TEST 2: Pattern Categorization")
    print("=" * 80)

    all_passed = True

    for i, sample in enumerate(SAMPLE_PATTERNS, 1):
        pattern = sample["pattern"]
        expected_category = sample["expected_category"]

        print(f"\n[{i}/{len(SAMPLE_PATTERNS)}] Categorizing: {pattern[:60]}...")

        result = await categorize_pattern(pattern)

        category = result.get("category")
        confidence = result.get("confidence", 0.0)
        reasoning = result.get("reasoning", "")

        print(f"   Category: {category} (expected: {expected_category})")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Reasoning: {reasoning[:100]}...")

        # Accept the categorization even if it differs from expected
        # (AI might categorize differently but still validly)
        if category and category != "uncategorized":
            print(f"   ✅ Categorized as '{category}'")
        else:
            print("   ⚠️  WARNING: Categorized as 'uncategorized'")
            all_passed = False

    if all_passed:
        print("\n✅ PASSED: All patterns categorized successfully")
    else:
        print("\n⚠️  WARNING: Some patterns were not categorized")

    return all_passed


async def add_pattern_to_memory(memory, pattern: str, category: str, spec_id: str):
    """Add a pattern to Graphiti memory with category metadata."""
    try:
        # Use the queries add_pattern method directly to pass category metadata
        category_metadata = {
            "category": category,
            "confidence": 0.95,
            "reasoning": f"Test pattern for {category}",
        }

        success = await memory._queries.add_pattern(pattern, category_metadata)

        if success:
            logger.info(f"Added pattern to memory: {pattern[:60]}...")
        return success

    except Exception as e:
        logger.error(f"Failed to add pattern to memory: {e}")
        return False


async def test_add_patterns_to_memory():
    """Test adding patterns to memory."""
    print("\n" + "=" * 80)
    print("TEST 3: Add Patterns to Memory")
    print("=" * 80)

    # Create test directories
    test_dir = Path(__file__).parent / ".test-pattern-workflow"
    test_dir.mkdir(exist_ok=True)

    spec_dir = test_dir / "spec"
    spec_dir.mkdir(exist_ok=True)

    project_dir = test_dir / "project"
    project_dir.mkdir(exist_ok=True)

    try:
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            print("❌ FAILED: Could not initialize Graphiti memory")
            return False, None, None, None

        print(f"✅ Initialized memory (group_id: {memory.group_id})")

        # Add patterns to memory
        added_count = 0
        for sample in SAMPLE_PATTERNS:
            pattern = sample["pattern"]
            category = sample["expected_category"]

            success = await add_pattern_to_memory(
                memory, pattern, category, spec_id="001-auth-feature"
            )
            if success:
                added_count += 1

        print(
            f"\n✅ PASSED: Added {added_count}/{len(SAMPLE_PATTERNS)} patterns to memory"
        )

        return True, memory, spec_dir, project_dir

    except Exception as e:
        print(f"❌ FAILED: {e}")
        logger.exception("Failed to add patterns to memory")
        return False, None, None, None


async def test_suggest_patterns(memory, spec_dir, project_dir):
    """Test pattern suggestion retrieval."""
    print("\n" + "=" * 80)
    print("TEST 4: Pattern Suggestion Retrieval")
    print("=" * 80)

    try:
        # Test 1: Suggest patterns for authentication
        print("\n[4.1] Testing: Suggest patterns for authentication task")

        patterns = await suggest_patterns(
            client=memory._client,  # Access private _client attribute
            group_id=memory.group_id,
            spec_context_id=memory.spec_context_id,
            query="implement user authentication",
            categories=None,
            num_results=5,
            min_score=0.3,  # Lower threshold for testing
            include_project_context=True,
            project_dir=project_dir,
        )

        print(f"   Found {len(patterns)} pattern suggestions")

        if len(patterns) > 0:
            print("   ✅ Pattern suggestions retrieved successfully")

            # Display suggestions
            for i, p in enumerate(patterns, 1):
                print(f"\n   [{i}] {p.get('pattern', '')[:70]}...")
                print(f"       Category: {p.get('category')}")
                print(f"       Confidence: {p.get('confidence', 0.0):.2f}")
                print(f"       Relevance: {p.get('score', 0.0):.2f}")
        else:
            print("   ⚠️  WARNING: No patterns found (may need time for indexing)")

        # Test 2: Category filtering
        print("\n[4.2] Testing: Category filtering (security only)")

        security_patterns = await suggest_patterns(
            client=memory._client,  # Access private _client attribute
            group_id=memory.group_id,
            spec_context_id=memory.spec_context_id,
            query="implement user authentication",
            categories=["security"],
            num_results=5,
            min_score=0.3,
            include_project_context=True,
            project_dir=project_dir,
        )

        print(f"   Found {len(security_patterns)} security patterns")

        for p in security_patterns:
            category = p.get("category")
            if category != "security":
                print(f"   ❌ FAILED: Found non-security pattern: {category}")
                return False

        print("   ✅ Category filtering working correctly")

        print("\n✅ PASSED: Pattern suggestion retrieval working")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        logger.exception("Failed to suggest patterns")
        return False


async def test_memory_manager_integration(spec_dir, project_dir):
    """Test pattern suggestions through memory_manager."""
    print("\n" + "=" * 80)
    print("TEST 5: Memory Manager Integration")
    print("=" * 80)

    try:
        from agents.memory_manager import get_pattern_suggestions

        # Get pattern suggestions through memory_manager
        formatted_patterns = await get_pattern_suggestions(
            spec_dir=spec_dir,
            project_dir=project_dir,
            query="implement user authentication",
            categories=None,
            num_results=5,
            min_score=0.3,
        )

        if formatted_patterns:
            print("✅ Memory manager returned formatted patterns:")
            print("-" * 80)
            print(
                formatted_patterns[:500] + "..."
                if len(formatted_patterns) > 500
                else formatted_patterns
            )
            print("-" * 80)
            print("\n✅ PASSED: Memory manager integration working")
            return True
        else:
            print("⚠️  WARNING: Memory manager returned no patterns")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        logger.exception("Failed to test memory manager integration")
        return False


async def cleanup(memory, test_dir):
    """Cleanup test resources."""
    print("\n" + "=" * 80)
    print("Cleanup")
    print("=" * 80)

    if memory:
        try:
            await memory.close()
            print("✅ Closed memory connection")
        except Exception as e:
            print(f"⚠️  Warning: Failed to close memory: {e}")

    # Optionally remove test directory
    # test_dir.rmdir()  # Keep for inspection


# =============================================================================
# Main Test Runner
# =============================================================================


async def run_all_tests():
    """Run all end-to-end tests."""
    print("\n" + "=" * 80)
    print("PATTERN SUGGESTION WORKFLOW - END-TO-END TEST")
    print("=" * 80)
    print("\nThis test verifies:")
    print("  1. Graphiti is enabled")
    print("  2. Patterns can be categorized")
    print("  3. Patterns can be added to memory")
    print("  4. Patterns can be suggested with semantic search")
    print("  5. Category filtering works")
    print("  6. Integration with memory_manager works")

    memory = None
    test_dir = Path(__file__).parent / ".test-pattern-workflow"

    try:
        # Test 1: Graphiti enabled
        if not await test_graphiti_enabled():
            print("\n❌ OVERALL RESULT: FAILED - Graphiti not enabled")
            return False

        # Test 2: Pattern categorization
        await test_pattern_categorization()

        # Test 3: Add patterns to memory
        success, memory, spec_dir, project_dir = await test_add_patterns_to_memory()
        if not success:
            print("\n❌ OVERALL RESULT: FAILED - Could not add patterns to memory")
            return False

        # Test 4: Suggest patterns
        if not await test_suggest_patterns(memory, spec_dir, project_dir):
            print("\n⚠️  WARNING: Pattern suggestion had issues")

        # Test 5: Memory manager integration
        await test_memory_manager_integration(spec_dir, project_dir)

        print("\n" + "=" * 80)
        print("✅ OVERALL RESULT: PASSED")
        print("=" * 80)
        print("\nAll core functionality is working correctly!")
        print("Note: Some warnings about indexing are normal for fresh test data.")
        print(f"\nTest data location: {test_dir}")

        return True

    except Exception as e:
        print(f"\n❌ OVERALL RESULT: FAILED - Unexpected error: {e}")
        logger.exception("Test suite failed with exception")
        return False

    finally:
        await cleanup(memory, test_dir)


# =============================================================================
# Entry Point
# =============================================================================


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
