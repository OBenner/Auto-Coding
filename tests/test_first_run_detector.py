#!/usr/bin/env python3
"""Tests for First-Run Detection."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from setup.first_run_detector import detect_first_run, mark_setup_complete, reset_first_run


def test_returns_true_when_neither_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend_dir = Path(tmpdir) / "apps" / "backend"
        backend_dir.mkdir(parents=True)
        home_dir = Path(tmpdir)

        with patch("setup.first_run_detector.Path") as mock_path:
            mock_instance = MagicMock()
            mock_instance.resolve.return_value = backend_dir
            mock_path.return_value = mock_instance

            with patch("os.path.expanduser", return_value=str(home_dir)):
                result = detect_first_run()

        assert result is True


def test_returns_false_when_env_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend_dir = Path(tmpdir) / "apps" / "backend"
        backend_dir.mkdir(parents=True)
        
        env_file = backend_dir / ".env"
        env_file.write_text("# Test\n")

        with patch("setup.first_run_detector.Path") as mock_path:
            mock_instance = MagicMock()
            mock_instance.resolve.return_value = backend_dir
            mock_instance.exists.return_value = True
            mock_path.return_value = mock_instance

            with patch("os.path.expanduser", return_value=tmpdir):
                result = detect_first_run()

        assert result is False


def test_returns_false_when_marker_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend_dir = Path(tmpdir) / "apps" / "backend"
        backend_dir.mkdir(parents=True)
        home_dir = Path(tmpdir)

        setup_marker = home_dir / ".auto-claude" / ".setup_complete"
        setup_marker.parent.mkdir(parents=True, exist_ok=True)
        setup_marker.write_text("Setup completed\n")

        mock_env = MagicMock()
        mock_env.exists.return_value = False
        mock_marker = MagicMock()
        mock_marker.exists.return_value = True

        with patch("setup.first_run_detector.Path") as mock_path:
            def path_constructor(*args, **kwargs):
                if len(args) > 0 and ".env" in str(args[0]):
                    return mock_env
                return mock_marker
            mock_path.side_effect = path_constructor

            with patch("os.path.expanduser", return_value=str(home_dir)):
                result = detect_first_run()

        assert result is False


def test_creates_marker_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        home_dir = Path(tmpdir)

        with patch("os.path.expanduser", return_value=str(home_dir)):
            result = mark_setup_complete()

        setup_marker = home_dir / ".auto-claude" / ".setup_complete"
        assert setup_marker.exists()
        assert "Setup completed at:" in setup_marker.read_text()
        assert result is True


def test_creates_directory_if_needed():
    with tempfile.TemporaryDirectory() as tmpdir:
        home_dir = Path(tmpdir)
        auto_claude_dir = home_dir / ".auto-claude"
        
        assert not auto_claude_dir.exists()

        with patch("os.path.expanduser", return_value=str(home_dir)):
            result = mark_setup_complete()

        assert auto_claude_dir.exists()
        assert result is True


def test_removes_marker_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        home_dir = Path(tmpdir)
        auto_claude_dir = home_dir / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)
        setup_marker = auto_claude_dir / ".setup_complete"
        setup_marker.write_text("Setup\n")

        with patch("os.path.expanduser", return_value=str(home_dir)):
            result = reset_first_run()

        assert not setup_marker.exists()
        assert result is True


def test_returns_false_when_no_marker():
    with tempfile.TemporaryDirectory() as tmpdir:
        home_dir = Path(tmpdir)

        with patch("os.path.expanduser", return_value=str(home_dir)):
            result = reset_first_run()

        assert result is False


def test_does_not_remove_env_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        home_dir = Path(tmpdir)
        backend_dir = Path(tmpdir) / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        env_file = backend_dir / ".env"
        env_file.write_text("# Test\n")

        auto_claude_dir = home_dir / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)
        setup_marker = auto_claude_dir / ".setup_complete"
        setup_marker.write_text("Setup\n")

        with patch("os.path.expanduser", return_value=str(home_dir)):
            result = reset_first_run()

        assert not setup_marker.exists()
        assert env_file.exists()
        assert result is True
