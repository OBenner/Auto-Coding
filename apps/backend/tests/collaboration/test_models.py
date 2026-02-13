"""Unit tests for collaboration models."""

import pytest
from datetime import datetime, timezone

from collaboration.models import (
    Comment,
    CommentStatus,
    Suggestion,
    SuggestionStatus,
    Presence,
    PresenceType,
    Version,
)


def test_comment_status_enum():
    """Test CommentStatus enum values."""
    assert CommentStatus.ACTIVE == "active"
    assert CommentStatus.RESOLVED == "resolved"


def test_suggestion_status_enum():
    """Test SuggestionStatus enum values."""
    assert SuggestionStatus.PENDING == "pending"
    assert SuggestionStatus.ACCEPTED == "accepted"
    assert SuggestionStatus.REJECTED == "rejected"


def test_presence_type_enum():
    """Test PresenceType enum values."""
    assert PresenceType.VIEWING == "viewing"
    assert PresenceType.EDITING == "editing"


def test_models_import():
    """Test all models can be imported."""
    assert Comment is not None
    assert Suggestion is not None
    assert Presence is not None
    assert Version is not None
