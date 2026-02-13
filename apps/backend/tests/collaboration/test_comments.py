"""Unit tests for CommentManager."""

import pytest
from pathlib import Path
from collaboration.comments import CommentManager
from collaboration.models import CommentStatus


def test_comment_manager_import():
    """Test CommentManager can be imported."""
    from collaboration.comments import CommentManager

    assert CommentManager is not None


def test_comment_status_enum():
    """Test CommentStatus enum."""
    from collaboration.models import CommentStatus

    assert CommentStatus.ACTIVE == "active"
    assert CommentStatus.RESOLVED == "resolved"


def test_add_comment(tmp_path):
    """Test adding a comment."""
    manager = CommentManager(spec_dir=tmp_path)
    comment = manager.add_comment(
        author="user1",
        author_name="User 1",
        content="Test comment",
        section_id="intro"
    )
    assert comment.id is not None
    assert comment.status == CommentStatus.ACTIVE
    assert comment.content == "Test comment"


def test_get_comment(tmp_path):
    """Test retrieving a comment."""
    manager = CommentManager(spec_dir=tmp_path)
    comment = manager.add_comment(
        author="user1",
        author_name="User 1",
        content="Test",
        section_id="intro"
    )
    retrieved = manager.get_comment(comment.id)
    assert retrieved is not None
    assert retrieved.id == comment.id


def test_resolve_comment(tmp_path):
    """Test resolving a comment."""
    manager = CommentManager(spec_dir=tmp_path)
    comment = manager.add_comment(
        author="user1",
        author_name="User 1",
        content="Test",
        section_id="intro"
    )
    manager.resolve_comment(comment.id, resolved_by="user2")
    resolved = manager.get_comment(comment.id)
    assert resolved.status == CommentStatus.RESOLVED


def test_get_thread(tmp_path):
    """Test getting threaded comments."""
    manager = CommentManager(spec_dir=tmp_path)
    parent = manager.add_comment(
        author="user1",
        author_name="User 1",
        content="Parent",
        section_id="intro"
    )
    reply = manager.add_comment(
        author="user2",
        author_name="User 2",
        content="Reply",
        section_id="intro",
        parent_id=parent.id
    )
    thread = manager.get_comment_thread(parent.id)
    assert len(thread) == 2
    assert thread[1].parent_id == parent.id
