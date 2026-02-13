"""Unit tests for SuggestionManager."""

import pytest
from pathlib import Path
from collaboration.suggestions import SuggestionManager
from collaboration.models import SuggestionStatus


def test_suggestion_manager_import():
    """Test SuggestionManager can be imported."""
    from collaboration.suggestions import SuggestionManager

    assert SuggestionManager is not None


def test_suggestion_status_enum():
    """Test SuggestionStatus enum."""
    from collaboration.models import SuggestionStatus

    assert SuggestionStatus.PENDING == "pending"
    assert SuggestionStatus.ACCEPTED == "accepted"
    assert SuggestionStatus.REJECTED == "rejected"


def test_add_suggestion(tmp_path):
    """Test adding a suggestion."""
    manager = SuggestionManager(spec_dir=tmp_path)
    suggestion = manager.add_suggestion(
        author="user1",
        author_name="User 1",
        original_text="Old text",
        suggested_text="New text",
        section_id="intro"
    )
    assert suggestion.id is not None
    assert suggestion.status == SuggestionStatus.PENDING


def test_accept_suggestion(tmp_path):
    """Test accepting a suggestion."""
    manager = SuggestionManager(spec_dir=tmp_path)
    suggestion = manager.add_suggestion(
        author="user1",
        author_name="User 1",
        original_text="Old",
        suggested_text="New",
        section_id="intro"
    )
    manager.accept_suggestion(suggestion.id, reviewed_by="user2")
    accepted = manager.get_suggestion(suggestion.id)
    assert accepted.status == SuggestionStatus.ACCEPTED
