"""
Test Session Resume Functionality
==================================

Tests for session resumption with full context restore.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Test imports
from agents.session import (
    ConversationHistory,
    ConversationRound,
    format_context_for_resume,
    resume_session,
)


@pytest.fixture
def temp_spec_dir(tmp_path):
    """Create a temporary spec directory for testing."""
    spec_dir = tmp_path / "specs" / "test-spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    return spec_dir


@pytest.fixture
def sample_conversation_history(temp_spec_dir):
    """Create a sample conversation history with multiple rounds."""
    history = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="subtask-1-1")

    # Add multiple conversation rounds
    for i in range(1, 6):
        round_obj = history.add_round(
            user_message=f"User message {i}",
            phase="coding",
        )
        round_obj.add_text(f"Assistant response {i}")
        round_obj.add_tool_call("Read", {"file_path": f"file{i}.py"})
        round_obj.set_usage(input_tokens=100 * i, output_tokens=50 * i)

    return history


def test_conversation_round_creation():
    """Test ConversationRound initialization and data tracking."""
    round_obj = ConversationRound(
        round_number=1,
        user_message="Test message",
        phase="coding",
    )

    assert round_obj.round_number == 1
    assert round_obj.user_message == "Test message"
    assert round_obj.phase == "coding"
    assert round_obj.assistant_response == ""
    assert len(round_obj.tool_calls) == 0
    assert len(round_obj.code_references) == 0


def test_conversation_round_add_text():
    """Test adding text to assistant response."""
    round_obj = ConversationRound(
        round_number=1,
        user_message="Test",
        phase="coding",
    )

    round_obj.add_text("First part. ")
    round_obj.add_text("Second part.")

    assert round_obj.assistant_response == "First part. Second part."


def test_conversation_round_add_tool_call():
    """Test recording tool calls and extracting file paths."""
    round_obj = ConversationRound(
        round_number=1,
        user_message="Test",
        phase="coding",
    )

    # Test file_path extraction
    round_obj.add_tool_call("Read", {"file_path": "test.py"})
    assert len(round_obj.tool_calls) == 1
    assert "test.py" in round_obj.code_references

    # Test path extraction
    round_obj.add_tool_call("Grep", {"pattern": "test", "path": "src/"})
    assert len(round_obj.tool_calls) == 2
    assert "src/" in round_obj.code_references


def test_conversation_round_serialization():
    """Test ConversationRound to_dict and from_dict."""
    round_obj = ConversationRound(
        round_number=1,
        user_message="Test message",
        phase="coding",
    )
    round_obj.add_text("Response text")
    round_obj.add_tool_call("Read", {"file_path": "test.py"})
    round_obj.set_usage(100, 50)

    # Serialize
    data = round_obj.to_dict()
    assert data["round_number"] == 1
    assert data["user_message"] == "Test message"
    assert data["assistant_response"] == "Response text"
    assert len(data["tool_calls"]) == 1
    assert "test.py" in data["code_references"]
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50

    # Deserialize
    restored = ConversationRound.from_dict(data)
    assert restored.round_number == 1
    assert restored.user_message == "Test message"
    assert restored.assistant_response == "Response text"
    assert len(restored.tool_calls) == 1
    assert "test.py" in restored.code_references
    assert restored.input_tokens == 100
    assert restored.output_tokens == 50


def test_conversation_history_add_round(temp_spec_dir):
    """Test adding rounds to conversation history."""
    history = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="subtask-1-1")

    round1 = history.add_round("Message 1", phase="coding")
    assert round1.round_number == 1
    assert len(history.rounds) == 1

    round2 = history.add_round("Message 2", phase="coding")
    assert round2.round_number == 2
    assert len(history.rounds) == 2


def test_conversation_history_get_current_round(temp_spec_dir):
    """Test getting the current (most recent) round."""
    history = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="subtask-1-1")

    assert history.get_current_round() is None

    round1 = history.add_round("Message 1")
    assert history.get_current_round() == round1

    round2 = history.add_round("Message 2")
    assert history.get_current_round() == round2


def test_conversation_history_get_total_tokens(sample_conversation_history):
    """Test calculating total tokens across all rounds."""
    total_input, total_output = sample_conversation_history.get_total_tokens()

    # Should sum: 100+200+300+400+500 = 1500 input, 50+100+150+200+250 = 750 output
    assert total_input == 1500
    assert total_output == 750


def test_conversation_history_get_all_code_references(sample_conversation_history):
    """Test extracting all unique code references."""
    code_refs = sample_conversation_history.get_all_code_references()

    assert len(code_refs) == 5
    assert "file1.py" in code_refs
    assert "file5.py" in code_refs


def test_conversation_history_serialization(sample_conversation_history, temp_spec_dir):
    """Test ConversationHistory to_dict and from_dict."""
    # Serialize
    data = sample_conversation_history.to_dict()
    assert data["subtask_id"] == "subtask-1-1"
    assert data["total_rounds"] == 5
    assert len(data["rounds"]) == 5

    # Deserialize
    restored = ConversationHistory.from_dict(temp_spec_dir, data)
    assert restored.subtask_id == "subtask-1-1"
    assert len(restored.rounds) == 5
    assert restored.session_id == sample_conversation_history.session_id


def test_conversation_history_save_and_load(sample_conversation_history, temp_spec_dir):
    """Test saving and loading conversation history."""
    # Save
    success = sample_conversation_history.save()
    assert success is True

    # Verify file exists
    history_dir = temp_spec_dir / "conversation_history"
    assert history_dir.exists()
    assert len(list(history_dir.glob("*.json"))) == 1

    # Load
    loaded = ConversationHistory.load_latest(temp_spec_dir, subtask_id="subtask-1-1")
    assert loaded is not None
    assert loaded.subtask_id == "subtask-1-1"
    assert len(loaded.rounds) == 5


def test_conversation_history_load_latest_no_history(temp_spec_dir):
    """Test loading when no history exists."""
    loaded = ConversationHistory.load_latest(temp_spec_dir, subtask_id="nonexistent")
    assert loaded is None


def test_conversation_history_load_latest_filters_by_subtask(temp_spec_dir):
    """Test that load_latest filters by subtask_id."""
    # Create history for subtask-1-1
    history1 = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="subtask-1-1")
    history1.add_round("Message 1")
    history1.save()

    # Create history for subtask-1-2
    history2 = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="subtask-1-2")
    history2.add_round("Message 2")
    history2.save()

    # Load subtask-1-1 history
    loaded = ConversationHistory.load_latest(temp_spec_dir, subtask_id="subtask-1-1")
    assert loaded is not None
    assert loaded.subtask_id == "subtask-1-1"


def test_format_context_for_resume(sample_conversation_history):
    """Test formatting conversation history for session resumption."""
    context = format_context_for_resume(sample_conversation_history)

    assert "Session Resume Context" in context
    assert "subtask-1-1" in context
    assert "Total rounds: 5" in context
    assert "Round 1" in context
    assert "Round 5" in context
    assert "Code References from Session" in context
    assert "file1.py" in context
    assert "Token Usage" in context
    assert "1,500" in context  # Input tokens formatted


def test_format_context_for_resume_empty_history(temp_spec_dir):
    """Test formatting empty history returns empty string."""
    history = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="test")
    context = format_context_for_resume(history)

    assert context == ""


def test_format_context_for_resume_limits_recent_rounds(temp_spec_dir):
    """Test that format_context_for_resume only includes last 5 rounds."""
    history = ConversationHistory(spec_dir=temp_spec_dir, subtask_id="test")

    # Add 10 rounds with unique word-based identifiers
    words = ["alpha", "beta", "gamma", "delta", "epsilon",
             "zeta", "eta", "theta", "iota", "kappa"]
    for i, word in enumerate(words, 1):
        round_obj = history.add_round(f"Message using word {word}")
        round_obj.add_text(f"Response using word {word}")

    context = format_context_for_resume(history)

    # Should include last 5 rounds (rounds 6-10: zeta, eta, theta, iota, kappa)
    assert "zeta" in context
    assert "eta" in context
    assert "theta" in context
    assert "iota" in context
    assert "kappa" in context
    assert "Total rounds: 10" in context

    # Should NOT include first 5 rounds (alpha, beta, gamma, delta, epsilon)
    assert "alpha" not in context.lower()
    assert "beta" not in context.lower()
    assert "gamma" not in context.lower()
    assert "delta" not in context.lower()
    assert "epsilon" not in context.lower()


@pytest.mark.anyio
async def test_resume_session_no_history(temp_spec_dir):
    """Test resuming when no previous history exists."""
    message, history = await resume_session(
        spec_dir=temp_spec_dir,
        subtask_id="nonexistent",
        new_message="Continue working",
    )

    assert history is None
    assert message == "Continue working"  # Returns as-is


@pytest.mark.anyio
async def test_resume_session_with_history(sample_conversation_history, temp_spec_dir):
    """Test resuming with existing history."""
    # Save the sample history first
    sample_conversation_history.save()

    # Resume
    message, history = await resume_session(
        spec_dir=temp_spec_dir,
        subtask_id="subtask-1-1",
        new_message="Continue working on the feature",
    )

    assert history is not None
    assert history.subtask_id == "subtask-1-1"
    assert len(history.rounds) == 5

    # Check message includes context
    assert "Session Resume Context" in message
    assert "Continue working on the feature" in message
    assert "Resuming Session" in message


@pytest.mark.anyio
async def test_resume_session_preserves_new_message(
    sample_conversation_history, temp_spec_dir
):
    """Test that resume_session preserves the new message."""
    sample_conversation_history.save()

    new_msg = "Now implement the authentication feature"
    message, history = await resume_session(
        spec_dir=temp_spec_dir,
        subtask_id="subtask-1-1",
        new_message=new_msg,
    )

    assert new_msg in message
    assert message.endswith(new_msg)
