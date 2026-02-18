#!/usr/bin/env python3
"""
End-to-end verification script for session replay functionality.

This script tests all aspects of the session replay feature:
1. Backend query, comparison, and export APIs
2. Session data with decision points, bookmarks, and transitions
3. Provides verification checklist for manual frontend testing
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from task_logger.comparison import (
    compare_session_metrics,
    compare_sessions,
    find_similar_sessions,
    get_session_summary,
)
from task_logger.export import (
    export_all_sessions,
    export_decision_points,
    export_session,
)
from task_logger.models import (
    LogEntry,
    LogEntryType,
    LogPhase,
)
from task_logger.query import (
    get_phase_summary,
    get_session_timeline,
    query_decision_points,
    query_entries,
    query_sessions,
    query_subtask_transitions,
    search_all,
)


def create_test_data(spec_dir: Path) -> None:
    """Create comprehensive test session data with decision points and bookmarks."""
    spec_dir.mkdir(parents=True, exist_ok=True)
    print("📝 Creating test session data...")

    # Base timestamp
    base_time = datetime.now() - timedelta(hours=2)

    # Create test logs with two sessions
    test_data = {
        "spec_id": "083-session-replay-learning",
        "spec_name": "Session Replay & Learning",
        "created_at": base_time.isoformat(),
        "sessions": [],
        "phases": {
            "planning": {
                "phase": "planning",
                "status": "completed",
                "started_at": (base_time + timedelta(minutes=5)).isoformat(),
                "completed_at": (base_time + timedelta(minutes=30)).isoformat(),
                "entries": [],
            },
            "coding": {
                "phase": "coding",
                "status": "completed",
                "started_at": (base_time + timedelta(minutes=31)).isoformat(),
                "completed_at": (base_time + timedelta(minutes=90)).isoformat(),
                "entries": [],
            },
            "validation": {
                "phase": "validation",
                "status": "completed",
                "started_at": (base_time + timedelta(minutes=91)).isoformat(),
                "completed_at": (base_time + timedelta(minutes=105)).isoformat(),
                "entries": [],
            },
        },
        "subtask_transitions": [],
        "bookmarks": [],
    }

    # Session 1: Initial implementation
    session1_start = base_time + timedelta(minutes=5)
    session1_end = base_time + timedelta(minutes=60)

    test_data["sessions"].append(
        {
            "session_id": 1,
            "started_at": session1_start.isoformat(),
            "completed_at": session1_end.isoformat(),
            "duration_seconds": 3300.0,
            "subtasks": [
                "subtask-1-1",
                "subtask-1-2",
                "subtask-1-3",
                "subtask-2-1",
                "subtask-2-2",
            ],
        }
    )

    # Session 1 entries with decision points
    entries_session1 = [
        LogEntry(
            timestamp=(session1_start + timedelta(seconds=10)).isoformat(),
            type=LogEntryType.PHASE_START.value,
            content="Starting planning phase",
            phase=LogPhase.PLANNING.value,
            session=1,
            subphase="PROJECT DISCOVERY",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(seconds=30)).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Analyzing requirements for session replay",
            phase=LogPhase.PLANNING.value,
            session=1,
            is_decision_point=True,
            reasoning="Need to decide between storing replay data in JSON files vs database. JSON files are simpler and sufficient for this use case.",
            alternatives=[
                "Use SQLite database for structured queries",
                "Use JSON files for simplicity and portability",
            ],
            decision="Use JSON files - simpler, no additional dependencies, sufficient for local replay",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=2)).isoformat(),
            type=LogEntryType.TOOL_START.value,
            content="Reading existing codebase",
            phase=LogPhase.PLANNING.value,
            session=1,
            tool_name="Read",
            tool_input="task_logger/models.py",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=2, seconds=5)).isoformat(),
            type=LogEntryType.TOOL_END.value,
            content="Successfully read models.py",
            phase=LogPhase.PLANNING.value,
            session=1,
            tool_name="Read",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=20)).isoformat(),
            type=LogEntryType.PHASE_START.value,
            content="Starting coding phase",
            phase=LogPhase.CODING.value,
            session=1,
            subphase="SUBTASK-1-1",
            subtask_id="subtask-1-1",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=25)).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Adding decision point fields to LogEntry model",
            phase=LogPhase.CODING.value,
            session=1,
            subtask_id="subtask-1-1",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=30)).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Deciding on bookmark implementation approach",
            phase=LogPhase.CODING.value,
            session=1,
            subtask_id="subtask-1-3",
            is_decision_point=True,
            reasoning="Bookmarks need to be persistent and associated with specific log entries. Need to decide how to identify and link them.",
            alternatives=[
                "Use entry index for linking",
                "Use entry timestamp for linking",
                "Store full entry data in bookmark",
            ],
            decision="Use entry timestamp - more stable and unique than index, lighter than storing full entry",
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=45)).isoformat(),
            type=LogEntryType.PHASE_START.value,
            content="Starting validation phase",
            phase=LogPhase.VALIDATION.value,
            session=1,
        ),
        LogEntry(
            timestamp=(session1_start + timedelta(minutes=50)).isoformat(),
            type=LogEntryType.SUCCESS.value,
            content="All tests passed successfully",
            phase=LogPhase.VALIDATION.value,
            session=1,
        ),
    ]

    # Add entries to phases
    for entry in entries_session1:
        entry_dict = entry.to_dict()
        if entry.phase == LogPhase.PLANNING.value:
            test_data["phases"]["planning"]["entries"].append(entry_dict)
        elif entry.phase == LogPhase.CODING.value:
            test_data["phases"]["coding"]["entries"].append(entry_dict)
        elif entry.phase == LogPhase.VALIDATION.value:
            test_data["phases"]["validation"]["entries"].append(entry_dict)

    # Session 2: Bug fix and refinement
    session2_start = base_time + timedelta(minutes=70)
    session2_end = base_time + timedelta(minutes=105)

    test_data["sessions"].append(
        {
            "session_id": 2,
            "started_at": session2_start.isoformat(),
            "completed_at": session2_end.isoformat(),
            "duration_seconds": 2100.0,
            "subtasks": ["subtask-2-3", "subtask-3-1"],
        }
    )

    entries_session2 = [
        LogEntry(
            timestamp=(session2_start + timedelta(seconds=10)).isoformat(),
            type=LogEntryType.PHASE_START.value,
            content="Starting coding phase",
            phase=LogPhase.CODING.value,
            session=2,
            subphase="SUBTASK-2-3",
            subtask_id="subtask-2-3",
        ),
        LogEntry(
            timestamp=(session2_start + timedelta(minutes=2)).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Implementing export functionality",
            phase=LogPhase.CODING.value,
            session=2,
            subtask_id="subtask-2-3",
        ),
        LogEntry(
            timestamp=(session2_start + timedelta(minutes=5)).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Choosing export format strategy",
            phase=LogPhase.CODING.value,
            session=2,
            subtask_id="subtask-2-3",
            is_decision_point=True,
            reasoning="Need to support both JSON and markdown exports. Should we create separate export functions or a unified one?",
            alternatives=[
                "Separate export_session_json() and export_session_markdown() functions",
                "Single export_session() function with format parameter",
            ],
            decision="Single function with format parameter - cleaner API, easier to maintain, consistent patterns",
        ),
        LogEntry(
            timestamp=(session2_start + timedelta(minutes=15)).isoformat(),
            type=LogEntryType.PHASE_START.value,
            content="Starting validation phase",
            phase=LogPhase.VALIDATION.value,
            session=2,
        ),
        LogEntry(
            timestamp=(session2_start + timedelta(minutes=20)).isoformat(),
            type=LogEntryType.SUCCESS.value,
            content="Export functionality verified",
            phase=LogPhase.VALIDATION.value,
            session=2,
        ),
    ]

    for entry in entries_session2:
        entry_dict = entry.to_dict()
        if entry.phase == LogPhase.CODING.value:
            test_data["phases"]["coding"]["entries"].append(entry_dict)
        elif entry.phase == LogPhase.VALIDATION.value:
            test_data["phases"]["validation"]["entries"].append(entry_dict)

    # Add subtask transitions
    test_data["subtask_transitions"] = [
        {
            "timestamp": (session1_start + timedelta(minutes=20)).isoformat(),
            "from_subtask": None,
            "to_subtask": "subtask-1-1",
            "session": 1,
        },
        {
            "timestamp": (session1_start + timedelta(minutes=30)).isoformat(),
            "from_subtask": "subtask-1-1",
            "to_subtask": "subtask-1-2",
            "session": 1,
        },
        {
            "timestamp": (session2_start + timedelta(seconds=10)).isoformat(),
            "from_subtask": None,
            "to_subtask": "subtask-2-3",
            "session": 2,
        },
        {
            "timestamp": (session2_start + timedelta(minutes=15)).isoformat(),
            "from_subtask": "subtask-2-3",
            "to_subtask": "subtask-3-1",
            "session": 2,
        },
    ]

    # Add bookmarks
    test_data["bookmarks"] = [
        {
            "id": "bookmark-1",
            "timestamp": (session1_start + timedelta(minutes=1)).isoformat(),
            "entry_timestamp": (session1_start + timedelta(seconds=30)).isoformat(),
            "phase": LogPhase.PLANNING.value,
            "label": "Storage decision - JSON vs DB",
            "note": "Important architectural decision - chose JSON for simplicity",
            "session": 1,
            "subtask_id": None,
        },
        {
            "id": "bookmark-2",
            "timestamp": (session1_start + timedelta(minutes=31)).isoformat(),
            "entry_timestamp": (session1_start + timedelta(minutes=30)).isoformat(),
            "phase": LogPhase.CODING.value,
            "label": "Bookmark linking strategy",
            "note": "Decided to use timestamps for linking bookmarks to entries",
            "session": 1,
            "subtask_id": "subtask-1-3",
        },
        {
            "id": "bookmark-3",
            "timestamp": (session2_start + timedelta(minutes=6)).isoformat(),
            "entry_timestamp": (session2_start + timedelta(minutes=5)).isoformat(),
            "phase": LogPhase.CODING.value,
            "label": "Export API design decision",
            "note": "Unified export function instead of format-specific functions",
            "session": 2,
            "subtask_id": "subtask-2-3",
        },
    ]

    # Save test data
    log_file = spec_dir / "task_logs.json"
    with open(log_file, "w") as f:
        json.dump(test_data, f, indent=2)

    print(f"✅ Created test data in {log_file}")
    print(
        f"   - 2 sessions with {len(entries_session1) + len(entries_session2)} entries"
    )
    print("   - 3 decision points")
    print("   - 3 bookmarks")
    print("   - 4 subtask transitions")


def _verify_query_apis(spec_dir: Path) -> bool:
    """Test all query API functions."""
    print("\n🔍 Testing Query APIs...")

    tests_passed = 0
    tests_total = 0

    # Test 1: query_sessions
    tests_total += 1
    try:
        sessions = query_sessions(spec_dir)
        assert len(sessions) == 2, f"Expected 2 sessions, got {len(sessions)}"
        assert sessions[0]["session_id"] == 1
        print("  ✅ query_sessions: Retrieved 2 sessions")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ query_sessions failed: {e}")

    # Test 2: query_sessions with filters
    tests_total += 1
    try:
        completed = query_sessions(spec_dir, completed=True)
        assert len(completed) == 2, (
            f"Expected 2 completed sessions, got {len(completed)}"
        )
        session1 = query_sessions(spec_dir, session_id=1)
        assert len(session1) == 1
        assert session1[0]["session_id"] == 1
        print("  ✅ query_sessions: Filters work correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ query_sessions filters failed: {e}")

    # Test 3: query_entries
    tests_total += 1
    try:
        entries = query_entries(spec_dir)
        assert len(entries) > 0, "Expected some entries"
        print(f"  ✅ query_entries: Retrieved {len(entries)} entries")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ query_entries failed: {e}")

    # Test 4: query_entries with phase filter
    tests_total += 1
    try:
        coding_entries = query_entries(spec_dir, phase="coding")
        assert len(coding_entries) > 0, "Expected some coding entries"
        print(
            f"  ✅ query_entries: Phase filter works ({len(coding_entries)} coding entries)"
        )
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ query_entries phase filter failed: {e}")

    # Test 5: query_decision_points
    tests_total += 1
    try:
        decisions = query_decision_points(spec_dir)
        assert len(decisions) == 3, f"Expected 3 decision points, got {len(decisions)}"
        assert decisions[0].get("reasoning") is not None, (
            "Decision point missing reasoning"
        )
        print(f"  ✅ query_decision_points: Found {len(decisions)} decision points")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ query_decision_points failed: {e}")

    # Test 6: query_subtask_transitions
    tests_total += 1
    try:
        transitions = query_subtask_transitions(spec_dir)
        assert len(transitions) == 4, f"Expected 4 transitions, got {len(transitions)}"
        print(f"  ✅ query_subtask_transitions: Found {len(transitions)} transitions")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ query_subtask_transitions failed: {e}")

    # Test 7: search_all
    tests_total += 1
    try:
        results = search_all(spec_dir, "decision")
        assert len(results) > 0, "Expected search results for 'decision'"
        print(f"  ✅ search_all: Found {len(results)} results for 'decision'")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ search_all failed: {e}")

    # Test 8: get_session_timeline
    tests_total += 1
    try:
        timeline = get_session_timeline(spec_dir, session_id=1)
        assert len(timeline) > 0, "Expected session 1 timeline"
        print(
            f"  ✅ get_session_timeline: Session 1 has {len(timeline)} timeline entries"
        )
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ get_session_timeline failed: {e}")

    # Test 9: get_phase_summary
    tests_total += 1
    try:
        summary = get_phase_summary(spec_dir, "coding")
        assert summary["phase"] == "coding"
        assert summary["entry_count"] > 0
        print(
            f"  ✅ get_phase_summary: Coding phase has {summary['entry_count']} entries"
        )
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ get_phase_summary failed: {e}")

    success = tests_passed == tests_total
    print(
        f"\n📊 Query API Tests: {tests_passed}/{tests_total} passed"
        + (" ✅" if success else " ❌")
    )
    return success


def _verify_comparison_apis(spec_dir: Path) -> bool:
    """Test all comparison API functions."""
    print("\n🔄 Testing Comparison APIs...")

    tests_passed = 0
    tests_total = 0

    # Test 1: compare_sessions
    tests_total += 1
    try:
        comparison = compare_sessions(spec_dir, [1, 2])
        assert "sessions" in comparison
        assert "metrics" in comparison
        assert "common_subtasks" in comparison
        assert len(comparison["sessions"]) == 2
        print("  ✅ compare_sessions: Compared 2 sessions")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ compare_sessions failed: {e}")

    # Test 2: get_session_summary
    tests_total += 1
    try:
        summary = get_session_summary(spec_dir, session_id=1)
        assert "session" in summary
        assert "tool_usage" in summary
        assert "decision_point_count" in summary
        print("  ✅ get_session_summary: Got session 1 summary")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ get_session_summary failed: {e}")

    # Test 3: compare_session_metrics
    tests_total += 1
    try:
        metrics = compare_session_metrics(spec_dir, [1, 2])
        # Returns dict with nested dicts: {duration: {1: x, 2: y}, tool_usage: {1: x, 2: y}, ...}
        assert "duration" in metrics
        assert "subtask_count" in metrics
        assert "efficiency" in metrics
        assert 1 in metrics["duration"] or 2 in metrics["duration"]
        print("  ✅ compare_session_metrics: Compared metrics across sessions")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ compare_session_metrics failed: {e}")

    # Test 4: find_similar_sessions
    tests_total += 1
    try:
        similar = find_similar_sessions(spec_dir, session_id=1)
        # Returns a list of similar sessions (may be empty if no subtask overlap)
        assert isinstance(similar, list)
        print(f"  ✅ find_similar_sessions: Found {len(similar)} similar sessions")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ find_similar_sessions failed: {e}")

    success = tests_passed == tests_total
    print(
        f"\n📊 Comparison API Tests: {tests_passed}/{tests_total} passed"
        + (" ✅" if success else " ❌")
    )
    return success


def _verify_export_apis(spec_dir: Path) -> bool:
    """Test all export API functions."""
    print("\n💾 Testing Export APIs...")

    tests_passed = 0
    tests_total = 0

    # Test 1: export_session JSON
    tests_total += 1
    try:
        json_export = export_session(spec_dir, session_id=1, format="json")
        assert "session" in json_export
        assert "entries" in json_export
        print("  ✅ export_session: JSON export works")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ export_session JSON failed: {e}")

    # Test 2: export_session Markdown
    tests_total += 1
    try:
        md_export = export_session(spec_dir, session_id=1, format="markdown")
        assert "# Session" in md_export or "## Session" in md_export
        assert len(md_export) > 100
        print("  ✅ export_session: Markdown export works")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ export_session Markdown failed: {e}")

    # Test 3: export_all_sessions
    tests_total += 1
    try:
        all_export = export_all_sessions(spec_dir, format="json")
        # export_all_sessions returns a JSON string (when format="json")
        assert isinstance(all_export, str)
        assert len(all_export) > 0
        print("  ✅ export_all_sessions: Exported all sessions")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ export_all_sessions failed: {e}")

    # Test 4: export_decision_points
    tests_total += 1
    try:
        decisions = export_decision_points(spec_dir, format="json")
        # export_decision_points returns a JSON string (may be empty "[]")
        assert isinstance(decisions, str)
        # Should be valid JSON string (array or object)
        print("  ✅ export_decision_points: Exported decision points")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ export_decision_points failed: {e}")

    # Test 5: Write actual export files to disk for manual verification
    tests_total += 1
    try:
        output_dir = spec_dir / "exports"
        output_dir.mkdir(exist_ok=True)

        # Write JSON export
        json_data = export_session(spec_dir, session_id=1, format="json")
        with open(output_dir / "session1.json", "w") as f:
            json.dump(json_data, f, indent=2)

        # Write Markdown export
        md_data = export_session(spec_dir, session_id=1, format="markdown")
        with open(output_dir / "session1.md", "w") as f:
            f.write(md_data)

        # Write all sessions
        all_data = export_all_sessions(spec_dir, format="markdown")
        with open(output_dir / "all_sessions.md", "w") as f:
            f.write(all_data)

        print(
            f"  ✅ export_files: Created export files in {output_dir}/\n"
            f"     - session1.json\n"
            f"     - session1.md\n"
            f"     - all_sessions.md"
        )
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ export_files failed: {e}")

    success = tests_passed == tests_total
    print(
        f"\n📊 Export API Tests: {tests_passed}/{tests_total} passed"
        + (" ✅" if success else " ❌")
    )
    return success


def print_frontend_checklist(spec_dir: Path):
    """Print manual verification checklist for frontend."""
    print("\n" + "=" * 70)
    print("🎨 FRONTEND MANUAL VERIFICATION CHECKLIST")
    print("=" * 70)

    print("\n📋 Setup Instructions:")
    print("1. Start the frontend app: npm run dev")
    print("2. Navigate to: http://localhost:3000")
    print("3. Press Ctrl+Shift+I to open DevTools")

    print("\n✅ Verification Steps:")
    print("\n1️⃣ VIEW SESSION LIST")
    print("   [ ] Navigate to Session Replay view (click 'Session Replay' in sidebar)")
    print("   [ ] Verify 2 sessions are displayed")
    print("   [ ] Check that sessions show: status, duration, subtask count")
    print("   [ ] Try status filter (Completed / In Progress)")

    print("\n2️⃣ SEARCH SESSIONS")
    print("   [ ] Enter '1' in search box")
    print("   [ ] Verify Session 1 appears in results")
    print("   [ ] Clear search and enter 'subtask-2'")
    print("   [ ] Verify Session 2 appears (has subtask-2-3)")

    print("\n3️⃣ PLAYBACK SESSION")
    print("   [ ] Click 'View' on Session 1")
    print("   [ ] Verify player controls appear (Play, Pause, Stop, Next, Prev)")
    print("   [ ] Click Play and verify entries display sequentially")
    print("   [ ] Try speed control (0.5x, 1x, 1.5x, 2x)")
    print("   [ ] Verify timeline shows markers for entries")
    print("   [ ] Click timeline markers to jump to entries")
    print("   [ ] Use keyboard shortcuts: Space (play/pause), Arrow keys")

    print("\n4️⃣ DECISION POINTS")
    print("   [ ] Navigate to entries with star icons (decision points)")
    print("   [ ] Verify decision point badge is displayed")
    print("   [ ] Expand decision point to see:")
    print("       [ ] Reasoning text")
    print("       [ ] Alternatives considered (numbered list)")
    print("       [ ] Chosen approach (highlighted)")

    print("\n5️⃣ BOOKMARKS")
    print("   [ ] Click bookmark icon (⭐) on any entry")
    print("   [ ] Enter label and note")
    print("   [ ] Verify bookmark appears in BookmarkPanel")
    print("   [ ] Click bookmark to navigate to that entry")
    print("   [ ] Remove bookmark and verify it disappears")

    print("\n6️⃣ EXPORT SESSION")
    print("   [ ] Click Export button")
    print("   [ ] Select JSON format")
    print("   [ ] Verify file downloads")
    print("   [ ] Open downloaded JSON file and verify structure")
    print("   [ ] Repeat with Markdown format")

    print("\n7️⃣ COMPARE SESSIONS")
    print("   [ ] Select two sessions to compare")
    print("   [ ] Verify comparison view shows:")
    print("       [ ] Session metrics side-by-side")
    print("       [ ] Common and unique subtasks")
    print("       [ ] Tool usage comparison")

    print("\n8️⃣ NAVIGATION FROM TASKS")
    print("   [ ] Go to Tasks view")
    print("   [ ] Click on any task card")
    print("   [ ] Click 'View Session Replay' button (Eye icon)")
    print("   [ ] Verify navigation to Session Replay view")
    print("   [ ] Verify sessions are filtered for that task")

    print("\n" + "=" * 70)
    print("📁 Test Data Location")
    print("=" * 70)
    print(f"Spec directory: {spec_dir}")
    print(f"Task logs: {spec_dir / 'task_logs.json'}")
    print(f"Export files: {spec_dir / 'exports' / 'session1.json'}")
    print(f"             {spec_dir / 'exports' / 'session1.md'}")
    print(f"             {spec_dir / 'exports' / 'all_sessions.md'}")

    print("\n" + "=" * 70)
    print("🐛 CONSOLE CHECKS")
    print("=" * 70)
    print("Open DevTools Console and verify:")
    print("  [ ] No errors during navigation")
    print("  [ ] No errors during session playback")
    print("  [ ] No errors during search/filter")
    print("  [ ] No errors during export")
    print("  [ ] IPC handlers successfully communicate")

    print("\n" + "=" * 70)


def main():
    """Run all E2E verification tests."""
    print("=" * 70)
    print("🧪 SESSION REPLAY E2E VERIFICATION")
    print("=" * 70)

    # Get spec directory
    spec_dir = (
        Path(__file__).parent.parent
        / ".auto-claude"
        / "specs"
        / "083-session-replay-learning"
    )
    print(f"\n📁 Spec directory: {spec_dir}")

    # Step 1: Create test data (always recreate fresh data for reliable testing)
    create_test_data(spec_dir)

    # Step 2: Test backend APIs
    query_passed = _verify_query_apis(spec_dir)
    comparison_passed = _verify_comparison_apis(spec_dir)
    export_passed = _verify_export_apis(spec_dir)
    all_passed = query_passed and comparison_passed and export_passed

    # Step 3: Print frontend checklist
    print_frontend_checklist(spec_dir)

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL BACKEND TESTS PASSED")
        print(
            "\n🎉 Backend verification complete! Follow the manual checklist above to verify the frontend."
        )
    else:
        print("❌ SOME TESTS FAILED")
        print(
            "\n⚠️  Please review the failed tests above and fix issues before proceeding."
        )

    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
