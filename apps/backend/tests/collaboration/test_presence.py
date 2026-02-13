"""Unit tests for PresenceManager."""

import pytest
from pathlib import Path
from collaboration.presence import PresenceManager
from collaboration.models import PresenceType


def test_presence_manager_import():
    """Test PresenceManager can be imported."""
    from collaboration.presence import PresenceManager

    assert PresenceManager is not None


def test_presence_type_enum():
    """Test PresenceType enum."""
    from collaboration.models import PresenceType

    assert PresenceType.VIEWING == "viewing"
    assert PresenceType.EDITING == "editing"


def test_update_presence(tmp_path):
    """Test updating user presence."""
    manager = PresenceManager(spec_dir=tmp_path)
    manager.update_presence(
        user_id="user1",
        user_name="User 1",
        presence_type=PresenceType.EDITING,
        section_id="intro"
    )
    presence = manager.get_presence("user1")
    assert presence is not None
    assert presence.presence_type == PresenceType.EDITING


def test_get_active_users(tmp_path):
    """Test getting active users."""
    manager = PresenceManager(spec_dir=tmp_path)
    manager.update_presence("user1", "User 1", PresenceType.EDITING)
    manager.update_presence("user2", "User 2", PresenceType.VIEWING)
    active = manager.get_active_users()
    assert len(active) == 2
