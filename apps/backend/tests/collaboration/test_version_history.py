"""Unit tests for VersionManager."""

import pytest
from pathlib import Path
from collaboration.version_history import VersionManager, DiffResult


def test_version_manager_import():
    """Test VersionManager can be imported."""
    from collaboration.version_history import VersionManager

    assert VersionManager is not None


def test_diff_result_import():
    """Test DiffResult can be imported."""
    from collaboration.version_history import DiffResult

    assert DiffResult is not None


def test_create_version(tmp_path):
    """Test creating a version."""
    manager = VersionManager(spec_dir=tmp_path)
    version = manager.create_version(
        author="user1",
        author_name="User 1",
        content="Version 1 content"
    )
    assert version.id is not None
    assert version.content == "Version 1 content"


def test_get_diff(tmp_path):
    """Test getting diff between versions."""
    manager = VersionManager(spec_dir=tmp_path)
    v1 = manager.create_version("user1", "User 1", "Version 1")
    v2 = manager.create_version("user1", "User 1", "Version 2")
    diff = manager.diff_versions(v1.id, v2.id)
    assert diff is not None
    assert isinstance(diff, DiffResult)
    # Check that diff detected changes between versions
    assert len(diff.added) > 0 or len(diff.removed) > 0
