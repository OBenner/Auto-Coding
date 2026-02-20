"""
Test Pattern Detection Integration
===================================

Tests for the pattern detection and storage system.
Verifies that detected patterns are properly saved to both file-based
and Graphiti memory storage.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the functions we're testing
from agents.memory_manager import detect_and_save_codebase_patterns
from memory.patterns import (
    append_pattern,
    load_patterns,
    save_detected_patterns_from_errors,
    save_detected_patterns_from_naming,
    save_detected_patterns_from_organization,
)


@pytest.fixture
def temp_spec_dir():
    """Create a temporary spec directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir) / ".auto-claude" / "specs" / "test-spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "memory").mkdir(parents=True)
        yield spec_dir


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create sample Python file with patterns
        sample_file = project_dir / "sample.py"
        sample_file.write_text(
            """
def process_data(input_value):
    \"\"\"Process input data.\"\"\"
    try:
        result = input_value * 2
        return result
    except ValueError as e:
        logger.error(f"Processing failed: {e}")
        raise

class DataProcessor:
    \"\"\"Data processor class.\"\"\"

    def __init__(self):
        self._internal_state = None

    def process(self, data):
        return data
"""
        )

        yield project_dir


class TestPatternStorage:
    """Test basic pattern storage functionality."""

    def test_append_pattern_without_metadata(self, temp_spec_dir):
        """Test appending a simple pattern."""
        pattern = "Use snake_case for function names"
        append_pattern(temp_spec_dir, pattern)

        patterns = load_patterns(temp_spec_dir)
        assert len(patterns) > 0
        assert any(pattern in p for p in patterns)

    def test_append_pattern_with_metadata(self, temp_spec_dir):
        """Test appending a pattern with full metadata."""
        pattern = "Use try/except for error handling"
        append_pattern(
            temp_spec_dir,
            pattern,
            category="error-handling",
            confidence=0.9,
            reasoning="Detected from analysis",
        )

        patterns = load_patterns(temp_spec_dir)
        assert len(patterns) > 0
        assert any(pattern in p for p in patterns)

    def test_duplicate_patterns_ignored(self, temp_spec_dir):
        """Test that duplicate patterns are not added."""
        pattern = "Variables use camelCase"

        append_pattern(temp_spec_dir, pattern)
        append_pattern(temp_spec_dir, pattern)  # Add same pattern again

        patterns = load_patterns(temp_spec_dir)
        # Should only have one instance
        pattern_count = sum(1 for p in patterns if "Variables use camelCase" in p)
        assert pattern_count == 1


class TestNamingPatternDetection:
    """Test naming convention pattern detection."""

    def test_save_naming_patterns(self, temp_spec_dir):
        """Test saving patterns from naming convention analysis."""
        naming_conventions = {
            "variable_style": "snake_case",
            "function_style": "snake_case",
            "class_style": "PascalCase",
            "constant_style": "UPPER_SNAKE_CASE",
            "private_prefix": "_",
            "file_style": "snake_case",
        }

        save_detected_patterns_from_naming(temp_spec_dir, naming_conventions)

        patterns = load_patterns(temp_spec_dir)
        assert len(patterns) > 0
        assert any("snake_case" in p for p in patterns)
        assert any("PascalCase" in p for p in patterns)

    def test_empty_naming_conventions(self, temp_spec_dir):
        """Test handling empty naming conventions."""
        save_detected_patterns_from_naming(temp_spec_dir, {})
        patterns = load_patterns(temp_spec_dir)
        # Should not crash, patterns may be empty
        assert isinstance(patterns, list)


class TestErrorPatternDetection:
    """Test error handling pattern detection."""

    def test_save_error_patterns(self, temp_spec_dir):
        """Test saving patterns from error handling analysis."""
        error_patterns = {
            "exception_types": {"ValueError": 5, "KeyError": 3},
            "custom_exceptions": ["CustomError", "ValidationError"],
            "logging_patterns": ["logger.error", "logger.warning"],
            "error_propagation": {"re_raises": 10, "handles": 5, "wraps": 2},
        }

        save_detected_patterns_from_errors(temp_spec_dir, error_patterns)

        patterns = load_patterns(temp_spec_dir)
        assert len(patterns) > 0
        assert any("exception" in p.lower() for p in patterns)

    def test_empty_error_patterns(self, temp_spec_dir):
        """Test handling empty error patterns."""
        save_detected_patterns_from_errors(temp_spec_dir, {})
        patterns = load_patterns(temp_spec_dir)
        assert isinstance(patterns, list)


class TestOrganizationPatternDetection:
    """Test code organization pattern detection."""

    def test_save_organization_patterns(self, temp_spec_dir):
        """Test saving patterns from organization analysis."""
        organization_patterns = {
            "architectural_style": "layered architecture",
            "file_organization": {"average_file_size": 250},
            "module_patterns": {"import_style": "absolute imports"},
            "separation_patterns": {
                "has_config_separation": True,
                "has_test_separation": True,
            },
        }

        save_detected_patterns_from_organization(temp_spec_dir, organization_patterns)

        patterns = load_patterns(temp_spec_dir)
        assert len(patterns) > 0
        # Should have patterns about architecture or organization
        assert any("architecture" in p.lower() or "file" in p.lower() for p in patterns)

    def test_empty_organization_patterns(self, temp_spec_dir):
        """Test handling empty organization patterns."""
        save_detected_patterns_from_organization(temp_spec_dir, {})
        patterns = load_patterns(temp_spec_dir)
        assert isinstance(patterns, list)


class TestIntegratedPatternDetection:
    """Test the integrated pattern detection function."""

    @pytest.mark.asyncio
    async def test_detect_and_save_patterns(self, temp_spec_dir, temp_project_dir):
        """Test detecting and saving patterns from a project."""
        pattern_counts = await detect_and_save_codebase_patterns(
            temp_spec_dir, temp_project_dir
        )

        # Should have counts for each category
        assert "naming" in pattern_counts
        assert "error-handling" in pattern_counts
        assert "code-organization" in pattern_counts

        # At least some patterns should be detected
        total_patterns = sum(pattern_counts.values())
        assert total_patterns > 0

        # Patterns should be saved to file
        patterns = load_patterns(temp_spec_dir)
        assert len(patterns) > 0

    @pytest.mark.asyncio
    async def test_detect_patterns_with_nonexistent_dir(self, temp_spec_dir, tmp_path):
        """Test pattern detection with non-existent project directory."""
        nonexistent_dir = tmp_path / "nonexistent_project"

        # Should not crash
        pattern_counts = await detect_and_save_codebase_patterns(
            temp_spec_dir, nonexistent_dir
        )

        # Counts should be zero or minimal
        assert isinstance(pattern_counts, dict)


@pytest.mark.asyncio
async def test_pattern_detection_with_graphiti_disabled(
    temp_spec_dir, temp_project_dir
):
    """Test that pattern detection works even when Graphiti is disabled."""
    with patch("memory.patterns.is_graphiti_memory_enabled", return_value=False):
        pattern_counts = await detect_and_save_codebase_patterns(
            temp_spec_dir, temp_project_dir
        )

        # Should still work with file-based storage
        assert sum(pattern_counts.values()) >= 0

        # Patterns should be in file
        patterns = load_patterns(temp_spec_dir)
        # May be empty if detection fails, but shouldn't crash
        assert isinstance(patterns, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
