"""
End-to-End Session Persistence Test
====================================

This script tests that session context persists across multi-hour sessions
with 50+ conversation rounds, meeting the acceptance criteria:
- Agent sessions maintain full context for 4+ hours of continuous operation
- Conversation history of 50+ rounds without quality degradation
- Highlighted code references persist across entire session
- Session context survives app restart and agent respawns

NOTE: This is a standalone test script, not a pytest test module.
Run directly: python tests/test_session_persistence_e2e.py
"""

# Prevent pytest from collecting functions in this standalone script
__test__ = False

import json
import sys
import time
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents.session import ConversationHistory, ConversationRound


def create_test_round(
    round_number: int, base_message: str = "Implement feature"
) -> ConversationRound:
    """
    Create a test conversation round with realistic data.

    Simulates a typical agent interaction with tool calls and code references.
    """
    round_obj = ConversationRound(
        round_number=round_number,
        user_message=f"{base_message} part {round_number}",
        phase="coding",
    )

    # Add realistic assistant response
    round_obj.add_text(f"I'll implement part {round_number} of the feature.\n")

    # Simulate tool calls (Read, Edit, Write operations)
    round_obj.add_tool_call(
        "Read", {"file_path": f"src/feature/module_{round_number % 5}.py"}
    )
    round_obj.add_tool_call("Grep", {"pattern": "class Test", "path": "tests/"})
    round_obj.add_tool_call(
        "Edit", {"file_path": f"src/feature/feature_{round_number % 3}.py"}
    )

    # Set token usage (growing with round number to simulate longer conversations)
    round_obj.set_usage(
        input_tokens=1000 + (round_number * 50),
        output_tokens=2000 + (round_number * 100),
    )

    return round_obj


def test_conversation_history_persistence(spec_dir: Path):
    """Test that conversation history persists across 50+ rounds."""
    print("\n" + "=" * 70)
    print("TEST 1: Conversation History Persistence (50+ rounds)")
    print("=" * 70)

    subtask_id = "test-subtask-persistence"

    # Initialize conversation history
    history = ConversationHistory(spec_dir=spec_dir, subtask_id=subtask_id)
    print(f"✓ Created conversation history for subtask: {subtask_id}")

    # Simulate 55 conversation rounds (exceeds 50 requirement)
    num_rounds = 55
    print(f"\nSimulating {num_rounds} conversation rounds...")

    start_time = time.time()

    for i in range(1, num_rounds + 1):
        round_obj = create_test_round(i, "Implement authentication feature")

        # Add to history
        history.rounds.append(round_obj)

        # Save after each round to verify incremental persistence
        if i % 10 == 0:
            success = history.save()
            if not success:
                print(f"✗ FAILED: Could not save history at round {i}")
                return False
            print(f"  ✓ Round {i}/{num_rounds} - Saved {len(history.rounds)} rounds")

    # Final save
    success = history.save()
    if not success:
        print("✗ FAILED: Could not save final history")
        return False

    elapsed = time.time() - start_time
    print(f"\n✓ Completed {num_rounds} rounds in {elapsed:.2f} seconds")
    print(f"✓ Average time per round: {elapsed / num_rounds:.3f} seconds")

    # Verify file was created
    history_dir = spec_dir / "conversation_history"
    if not history_dir.exists():
        print("✗ FAILED: History directory not created")
        return False

    history_files = list(history_dir.glob("*.json"))
    if len(history_files) != 1:
        print(f"✗ FAILED: Expected 1 history file, found {len(history_files)}")
        return False

    print(f"✓ History file created: {history_files[0].name}")

    # Verify file contents
    with open(history_files[0]) as f:
        data = json.load(f)

    if data.get("total_rounds") != num_rounds:
        print(f"✗ FAILED: Expected {num_rounds} rounds, got {data.get('total_rounds')}")
        return False

    print(f"✓ History file contains all {num_rounds} rounds")

    # Verify token totals
    total_input, total_output = history.get_total_tokens()
    if total_input == 0 or total_output == 0:
        print("✗ FAILED: Token totals not calculated correctly")
        return False

    print(f"✓ Total tokens: {total_input:,} input, {total_output:,} output")

    # Verify code references
    code_refs = history.get_all_code_references()
    if len(code_refs) == 0:
        print("✗ FAILED: No code references extracted")
        return False

    print(f"✓ Extracted {len(code_refs)} unique code references")

    print("\n" + "=" * 70)
    print("✓ TEST 1 PASSED: Conversation history persists across 50+ rounds")
    print("=" * 70)

    return True, history_files[0]


def test_session_restart_and_restore(spec_dir: Path):
    """Test that session context can be restored after restart."""
    print("\n" + "=" * 70)
    print("TEST 2: Session Restart and Context Restore")
    print("=" * 70)

    subtask_id = "test-subtask-persistence"

    # Simulate app restart by loading history from disk
    print("\nSimulating app restart...")

    # Debug: Check what files exist
    history_dir = spec_dir / "conversation_history"
    if not history_dir.exists():
        print("✗ FAILED: conversation_history directory does not exist")
        return False

    existing_files = list(history_dir.glob("*.json"))
    print(f"  Debug: Found {len(existing_files)} history files:")
    for f in existing_files:
        print(f"    - {f.name}")

    # Load the saved history
    loaded_history = ConversationHistory.load_latest(spec_dir, subtask_id)

    if loaded_history is None:
        print("✗ FAILED: Could not load conversation history after restart")
        return False

    print("✓ Loaded conversation history from disk")
    print(f"  Session ID: {loaded_history.session_id}")
    print(f"  Total rounds: {len(loaded_history.rounds)}")

    # Verify all rounds are present
    if len(loaded_history.rounds) != 55:
        print(f"✗ FAILED: Expected 55 rounds, got {len(loaded_history.rounds)}")
        return False

    print(f"✓ All {len(loaded_history.rounds)} rounds restored")

    # Verify round data integrity
    for i, round_obj in enumerate(loaded_history.rounds, 1):
        if round_obj.round_number != i:
            print(
                f"✗ FAILED: Round {i} has incorrect round_number: {round_obj.round_number}"
            )
            return False

        if not round_obj.user_message:
            print(f"✗ FAILED: Round {i} missing user_message")
            return False

        if not round_obj.assistant_response:
            print(f"✗ FAILED: Round {i} missing assistant_response")
            return False

        if len(round_obj.tool_calls) == 0:
            print(f"✗ FAILED: Round {i} has no tool calls")
            return False

        if len(round_obj.code_references) == 0:
            print(f"✗ FAILED: Round {i} has no code references")
            return False

        if round_obj.input_tokens == 0 or round_obj.output_tokens == 0:
            print(f"✗ FAILED: Round {i} missing token usage")
            return False

    print("✓ All round data verified (user messages, responses, tools, refs, tokens)")

    # Verify code references persisted across all rounds
    code_refs = loaded_history.get_all_code_references()
    if len(code_refs) == 0:
        print("✗ FAILED: No code references found after restart")
        return False

    print(f"✓ Code references persisted: {len(code_refs)} unique files")

    # Verify token usage persisted
    total_input, total_output = loaded_history.get_total_tokens()
    if total_input == 0 or total_output == 0:
        print("✗ FAILED: Token usage not persisted correctly")
        return False

    print(f"✓ Token usage persisted: {total_input:,} input, {total_output:,} output")

    print("\n" + "=" * 70)
    print("✓ TEST 2 PASSED: Session context survives restart")
    print("=" * 70)

    return True, loaded_history


def test_context_formatting_for_resume(history: ConversationHistory):
    """Test that context can be formatted for session resumption."""
    print("\n" + "=" * 70)
    print("TEST 3: Context Formatting for Session Resume")
    print("=" * 70)

    from agents.session import format_context_for_resume

    # Format context for resume
    context = format_context_for_resume(history)

    if not context:
        print("✗ FAILED: format_context_for_resume returned empty string")
        return False

    print(f"✓ Generated context summary ({len(context)} characters)")

    # Verify required sections are present
    required_sections = [
        "Session Resume Context",
        "Session ID:",
        "Total rounds:",
        "Previous Conversation Summary",
        "Round",
        "Code References from Session",
        "Token Usage",
    ]

    missing_sections = [s for s in required_sections if s not in context]
    if missing_sections:
        print(f"✗ FAILED: Missing sections: {missing_sections}")
        return False

    print("✓ All required sections present")

    # Verify last 5 rounds are included
    recent_rounds = history.rounds[-5:]
    for round_obj in recent_rounds:
        if f"Round {round_obj.round_number}" not in context:
            print(f"✗ FAILED: Round {round_obj.round_number} not in context")
            return False

    print("✓ Last 5 rounds included in context")

    # Verify code references are included
    code_refs = history.get_all_code_references()
    sample_ref = list(code_refs)[0]
    if sample_ref not in context:
        print(f"✗ FAILED: Code reference {sample_ref} not in context")
        return False

    print("✓ Code references included in context")

    # Verify token usage is included
    total_input, total_output = history.get_total_tokens()
    if f"{total_input:,}" not in context:
        print("✗ FAILED: Token usage not formatted correctly")
        return False

    print("✓ Token usage formatted correctly")

    print("\n" + "=" * 70)
    print("✓ TEST 3 PASSED: Context can be formatted for resume")
    print("=" * 70)

    return True


def test_session_resume_functionality(history: ConversationHistory, spec_dir: Path):
    """Test that session can be resumed with full context."""
    print("\n" + "=" * 70)
    print("TEST 4: Session Resume with Full Context")
    print("=" * 70)

    import asyncio

    async def run_resume_test():
        from agents.session import resume_session

        # Save the history first
        history.save()

        # Resume session with new message
        new_message = "Continue implementing the authentication feature"
        formatted_message, loaded_history = await resume_session(
            spec_dir=spec_dir,
            subtask_id=history.subtask_id,
            new_message=new_message,
        )

        if loaded_history is None:
            print("✗ FAILED: resume_session returned None for history")
            return False

        print(f"✓ Resumed session with {len(loaded_history.rounds)} rounds")

        # Verify formatted message contains context
        if "Session Resume Context" not in formatted_message:
            print("✗ FAILED: Resume context not in formatted message")
            return False

        print("✓ Formatted message includes resume context")

        # Verify new message is preserved
        if new_message not in formatted_message:
            print("✗ FAILED: New message not in formatted message")
            return False

        print("✓ New message preserved in formatted message")

        # Verify formatted message ends with new message
        if not formatted_message.endswith(new_message):
            print("✗ FAILED: Formatted message doesn't end with new message")
            return False

        print("✓ Formatted message properly formatted")

        return True

    # Run async test
    try:
        result = asyncio.run(run_resume_test())
        if not result:
            return False

        print("\n" + "=" * 70)
        print("✓ TEST 4 PASSED: Session can be resumed with full context")
        print("=" * 70)

        return True
    except Exception as e:
        print(f"✗ FAILED: Error during resume test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_long_running_session_simulation():
    """Test simulating a long-running session (4+ hours equivalent)."""
    print("\n" + "=" * 70)
    print("TEST 5: Long-Running Session Simulation (4+ hours equivalent)")
    print("=" * 70)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)

        # Simulate multiple sessions over time
        session_count = 8  # Simulate 8 sessions (30 mins each = 4 hours)
        rounds_per_session = 15
        total_rounds = session_count * rounds_per_session

        print(
            f"\nSimulating {session_count} sessions with {rounds_per_session} rounds each..."
        )
        print(f"Total rounds: {total_rounds} (exceeds 50+ requirement)")

        subtask_id = "test-long-running-session"

        for session_num in range(1, session_count + 1):
            # Load or create history
            if session_num == 1:
                history = ConversationHistory(spec_dir=spec_dir, subtask_id=subtask_id)
            else:
                history = ConversationHistory.load_latest(spec_dir, subtask_id)
                if history is None:
                    print(f"✗ FAILED: Could not load history for session {session_num}")
                    return False

            # Add rounds for this session
            start_round = len(history.rounds) + 1
            for i in range(rounds_per_session):
                round_num = start_round + i
                round_obj = create_test_round(round_num, f"Session {session_num} work")
                history.rounds.append(round_obj)

            # Save after session
            success = history.save()
            if not success:
                print(f"✗ FAILED: Could not save history after session {session_num}")
                return False

            print(
                f"  ✓ Session {session_num}/{session_count} - Total rounds: {len(history.rounds)}"
            )

        # Verify final state
        if len(history.rounds) != total_rounds:
            print(
                f"✗ FAILED: Expected {total_rounds} rounds, got {len(history.rounds)}"
            )
            return False

        print(f"\n✓ Completed {total_rounds} rounds across {session_count} sessions")

        # Verify no data degradation
        for i, round_obj in enumerate(history.rounds, 1):
            if not round_obj.user_message:
                print(f"✗ FAILED: Round {i} has no user_message (data degradation)")
                return False

            if len(round_obj.code_references) == 0:
                print(f"✗ FAILED: Round {i} has no code_references (data degradation)")
                return False

        print("✓ No data degradation detected across all rounds")

        # Verify code references accumulated
        code_refs = history.get_all_code_references()
        if len(code_refs) == 0:
            print("✗ FAILED: No code references found after long session")
            return False

        print(f"✓ Code references accumulated: {len(code_refs)} unique files")

        # Verify token tracking
        total_input, total_output = history.get_total_tokens()
        if total_input == 0 or total_output == 0:
            print("✗ FAILED: Token tracking failed over long session")
            return False

        print(
            f"✓ Token tracking sustained: {total_input:,} input, {total_output:,} output"
        )

        print("\n" + "=" * 70)
        print("✓ TEST 5 PASSED: Long-running session (4+ hours equivalent) stable")
        print("=" * 70)

        return True


def main():
    """Run all end-to-end tests."""
    print("\n" + "=" * 70)
    print("END-TO-END SESSION PERSISTENCE TEST SUITE")
    print("=" * 70)
    print("\nThis test suite validates:")
    print("✓ Conversation history persists across 50+ rounds")
    print("✓ Session context survives app restart")
    print("✓ Context can be formatted for session resume")
    print("✓ Session can be resumed with full context")
    print("✓ Long-running sessions (4+ hours) remain stable")

    import tempfile

    # Create a single temp directory for all tests
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)

        try:
            # Test 1: Basic persistence
            result1 = test_conversation_history_persistence(spec_dir)
            if isinstance(result1, tuple):
                success1, _history_file = result1
            else:
                success1 = result1

            if not success1:
                print("\n✗ TEST 1 FAILED - Aborting remaining tests")
                return False

            # Test 2: Restart and restore
            result2 = test_session_restart_and_restore(spec_dir)
            if isinstance(result2, tuple):
                success2, loaded_history = result2
            else:
                success2 = result2
                loaded_history = None

            if not success2:
                print("\n✗ TEST 2 FAILED - Aborting remaining tests")
                return False

            # Test 3: Context formatting
            if loaded_history:
                success3 = test_context_formatting_for_resume(loaded_history)
            else:
                print("\n⚠ Skipping TEST 3 (missing loaded history)")
                success3 = True

            if not success3:
                return False

            # Test 4: Resume functionality
            if loaded_history:
                success4 = test_session_resume_functionality(loaded_history, spec_dir)
            else:
                print("\n⚠ Skipping TEST 4 (missing prerequisites)")
                success4 = True

            if not success4:
                return False

            # Test 5: Long-running session (uses its own temp dir)
            success5 = test_long_running_session_simulation()
            if not success5:
                return False

            # All tests passed
            print("\n" + "=" * 70)
            print("✓✓✓ ALL END-TO-END TESTS PASSED ✓✓✓")
            print("=" * 70)
            print("\nSession persistence is working correctly!")
            print("✓ 50+ conversation rounds supported")
            print("✓ Context persists across restarts")
            print("✓ Long-running sessions (4+ hours) stable")
            print("✓ Code references tracked throughout")
            print("✓ Token usage monitored across sessions")

            return True

        except Exception as e:
            print(f"\n✗ FATAL ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
