#!/usr/bin/env python3
"""Verification script for preview workflow and explanation tracking."""

import sys
import tempfile
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from merge.ai_resolver.parsers import extract_explanation
from merge.preview_store import PreviewStore
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    MergeResult,
    ResolutionPreview,
)


def test_resolution_preview():
    """Test ResolutionPreview dataclass."""
    print("Testing ResolutionPreview dataclass...")

    # Create a test conflict region
    conflict = ConflictRegion(
        file_path="test.py",
        location="function:foo",
        tasks_involved=["task1", "task2"],
        change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.MEDIUM,
        can_auto_merge=False,
        reason="Both tasks modified the same function",
    )

    rp = ResolutionPreview(
        file_path="test.py",
        original="x = 1",
        suggested="y = 1",
        explanation="Renamed variable x to y",
        conflicts_addressed=[conflict],
    )

    assert rp.file_path == "test.py"
    assert rp.original == "x = 1"
    assert rp.suggested == "y = 1"
    assert rp.explanation == "Renamed variable x to y"
    assert len(rp.conflicts_addressed) == 1
    assert rp.conflicts_addressed[0].file_path == "test.py"

    # Test serialization
    data = rp.to_dict()
    assert data["file_path"] == "test.py"

    # Test deserialization
    rp2 = ResolutionPreview.from_dict(data)
    assert rp2.file_path == rp.file_path

    print("✓ ResolutionPreview dataclass works correctly")


def test_preview_store():
    """Test PreviewStore file system operations."""
    print("\nTesting PreviewStore...")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = PreviewStore(tmpdir)
        merge_id = "test-merge-123"

        # Create test conflict regions
        conflict1 = ConflictRegion(
            file_path="file1.py",
            location="function:bar",
            tasks_involved=["task1"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            reason="Minor change in function",
        )
        conflict2 = ConflictRegion(
            file_path="file2.py",
            location="function:baz",
            tasks_involved=["task2"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            reason="Minor change in function",
        )

        # Create test previews
        previews = [
            ResolutionPreview(
                file_path="file1.py",
                original="old code 1",
                suggested="new code 1",
                explanation="explanation 1",
                conflicts_addressed=[conflict1],
            ),
            ResolutionPreview(
                file_path="file2.py",
                original="old code 2",
                suggested="new code 2",
                explanation="explanation 2",
                conflicts_addressed=[conflict2],
            ),
        ]

        # Save previews (previews first, then merge_id)
        store.save_previews(previews, merge_id)

        # Load previews
        loaded = store.load_previews(merge_id)
        assert len(loaded) == 2
        assert loaded[0].file_path == "file1.py"
        assert loaded[1].file_path == "file2.py"

        # Clear previews
        store.clear_previews(merge_id)
        cleared = store.load_previews(merge_id)
        assert len(cleared) == 0

        print("✓ PreviewStore works correctly")


def test_explanation_extraction():
    """Test explanation parsing from AI responses."""
    print("\nTesting explanation extraction...")

    # Test with EXPLANATION prefix
    response1 = """EXPLANATION: This resolves the conflict by merging both changes.

```python
def foo():
    return 42
```"""

    explanation1 = extract_explanation(response1)
    assert "resolves the conflict" in explanation1
    assert "```" not in explanation1

    # Test without EXPLANATION
    response2 = """Here's the merged code:

```python
def bar():
    return 100
```"""

    explanation2 = extract_explanation(response2)
    # When no EXPLANATION prefix, the function returns None
    assert explanation2 is None

    print("✓ Explanation extraction works correctly")


def test_merge_result_explanation():
    """Test that MergeResult captures explanations."""
    print("\nTesting MergeResult explanation field...")

    mr = MergeResult(
        decision=MergeDecision.AI_MERGED,
        file_path="test.py",
        resolution_explanation="AI merged both changes successfully",
    )

    assert hasattr(mr, "resolution_explanation")
    assert mr.resolution_explanation == "AI merged both changes successfully"

    # Test serialization includes explanation
    data = mr.to_dict()
    assert "resolution_explanation" in data
    assert data["resolution_explanation"] == "AI merged both changes successfully"

    print("✓ MergeResult explanation tracking works correctly")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Verifying Preview Workflow and Explanation Tracking")
    print("=" * 60)

    try:
        test_resolution_preview()
        test_preview_store()
        test_explanation_extraction()
        test_merge_result_explanation()

        print("\n" + "=" * 60)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ ResolutionPreview dataclass works")
        print("  ✓ PreviewStore persists and loads previews")
        print("  ✓ Explanation extraction from AI responses works")
        print("  ✓ MergeResult tracks resolution explanations")
        return 0

    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
