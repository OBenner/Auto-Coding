"""
Tests for agent workspace context handling.
"""

import json
from pathlib import Path

import pytest


def test_load_workspace_context(tmp_path):
    """Test loading workspace context from spec directory."""
    from core.agent import load_workspace_context

    spec_dir = tmp_path / "specs" / "001-test"
    spec_dir.mkdir(parents=True)

    # Create workspace context file
    workspace_context = {
        "name": "test-workspace",
        "projects": [
            {"name": "project1", "path": "/path/to/project1", "enabled": True},
            {"name": "project2", "path": "/path/to/project2", "enabled": True},
        ],
    }

    context_file = spec_dir / "workspace_context.json"
    context_file.write_text(json.dumps(workspace_context, indent=2))

    # Load context
    loaded_context = load_workspace_context(spec_dir)

    assert loaded_context is not None
    assert loaded_context["name"] == "test-workspace"
    assert len(loaded_context["projects"]) == 2
    assert loaded_context["projects"][0]["name"] == "project1"


def test_load_workspace_context_missing_file(tmp_path):
    """Test loading workspace context when file doesn't exist."""
    from core.agent import load_workspace_context

    spec_dir = tmp_path / "specs" / "001-test"
    spec_dir.mkdir(parents=True)

    # No workspace context file
    loaded_context = load_workspace_context(spec_dir)

    # Should return None when file doesn't exist
    assert loaded_context is None


def test_load_workspace_context_invalid_json(tmp_path):
    """Test loading workspace context with invalid JSON."""
    from core.agent import load_workspace_context

    spec_dir = tmp_path / "specs" / "001-test"
    spec_dir.mkdir(parents=True)

    # Create invalid JSON file
    context_file = spec_dir / "workspace_context.json"
    context_file.write_text("{ invalid json }")

    # Should return None for invalid JSON
    loaded_context = load_workspace_context(spec_dir)
    assert loaded_context is None


def test_get_workspace_project_dirs(tmp_path):
    """Test extracting project directories from workspace context."""
    from core.agent import get_workspace_project_dirs

    workspace_context = {
        "name": "test-workspace",
        "projects": [
            {"name": "project1", "path": "/path/to/project1", "enabled": True},
            {"name": "project2", "path": "/path/to/project2", "enabled": True},
            {"name": "project3", "path": "/path/to/project3", "enabled": False},
        ],
    }

    # Get enabled project directories
    project_dirs = get_workspace_project_dirs(workspace_context)

    assert len(project_dirs) == 2
    assert Path("/path/to/project1") in project_dirs
    assert Path("/path/to/project2") in project_dirs
    assert Path("/path/to/project3") not in project_dirs


def test_get_workspace_project_dirs_no_context():
    """Test getting project directories when no workspace context exists."""
    from core.agent import get_workspace_project_dirs

    project_dirs = get_workspace_project_dirs(None)

    # Should return empty list when no context
    assert project_dirs == []
