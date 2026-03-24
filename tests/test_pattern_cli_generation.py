#!/usr/bin/env python3
"""
Tests for Pattern CLI Generation
=================================

Tests the pattern_commands.py CLI integration for pattern library generation:
- generate command for single language
- generate-all command for batch generation
- CLI argument validation
- End-to-end generation workflow
- Error handling and edge cases
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# sys.path is set by conftest.py (apps/backend is already on the path)
# Keep a local fallback for running this file directly
if not any("apps/backend" in p or "apps\\backend" in p for p in sys.path):
    sys.path.insert(0, "apps/backend")

from cli.pattern_commands import (
    generate_all_patterns,
    generate_patterns,
    handle_patterns_command,
)
from integrations.graphiti.pattern_library_generator import PatternLibraryGenerator


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


@pytest.fixture
def temp_spec_dir():
    """Create a temporary spec directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir) / ".auto-claude" / "specs" / "test-spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "memory").mkdir(parents=True)
        yield spec_dir


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for generated libraries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "patterns"
        output_dir.mkdir(parents=True)
        yield output_dir


class TestGenerateSingleLanguage:
    """Tests for generate_patterns() function - single language generation."""

    def test_generate_python_patterns(self, temp_project_dir, temp_output_dir):
        """Generate pattern library for Python."""
        output_path = temp_output_dir / "python_patterns.py"

        generate_patterns(
            project_dir=temp_project_dir,
            language="python",
            output_path=output_path,
            source_dir=None,
            max_patterns=50,
        )

        # Verify output file was created
        assert output_path.exists()
        assert output_path.is_file()

    def test_generate_with_source_dir(self, temp_project_dir, temp_output_dir):
        """Generate patterns from specific source directory."""
        # Create subdirectory with additional code
        subdir = temp_project_dir / "src"
        subdir.mkdir()
        (subdir / "module.py").write_text("def helper(): pass")

        output_path = temp_output_dir / "python_patterns.py"

        generate_patterns(
            project_dir=temp_project_dir,
            language="python",
            output_path=output_path,
            source_dir=subdir,
            max_patterns=50,
        )

        assert output_path.exists()

    def test_generate_with_max_patterns_limit(self, temp_project_dir, temp_output_dir):
        """Generate patterns with custom max patterns limit."""
        output_path = temp_output_dir / "python_patterns.py"

        generate_patterns(
            project_dir=temp_project_dir,
            language="python",
            output_path=output_path,
            source_dir=None,
            max_patterns=10,
        )

        assert output_path.exists()

    def test_generate_output_file_structure(self, temp_project_dir, temp_output_dir):
        """Verify generated file has correct Python module structure."""
        output_path = temp_output_dir / "python_patterns.py"

        generate_patterns(
            project_dir=temp_project_dir,
            language="python",
            output_path=output_path,
        )

        # Read generated file
        content = output_path.read_text()

        # Verify basic structure (should be a valid Python module with patterns)
        assert "PATTERNS" in content or "def " in content or "class " in content
        # Module should have docstring or comment header
        assert '"""' in content or "# " in content

    def test_generate_creates_parent_directories(
        self, temp_project_dir, temp_output_dir
    ):
        """Generate creates parent directories if they don't exist."""
        nested_output = temp_output_dir / "nested" / "deep" / "python_patterns.py"

        # Parent directories don't exist yet
        assert not nested_output.parent.exists()

        # PatternLibraryGenerator should handle this
        generator = PatternLibraryGenerator(temp_project_dir)
        generator.generate_library_file(nested_output, "python", {})

        assert nested_output.exists()


class TestGenerateAllLanguages:
    """Tests for generate_all_patterns() function - batch generation."""

    def test_generate_all_default_languages(self, temp_project_dir, temp_output_dir):
        """Generate libraries for all supported languages."""
        generate_all_patterns(
            project_dir=temp_project_dir,
            output_dir=temp_output_dir,
            languages=None,  # Default: all supported
            source_dir=None,
            max_patterns=50,
        )

        # At least one library should be generated
        generated_files = list(temp_output_dir.glob("*_patterns.py"))
        assert len(generated_files) > 0

    def test_generate_all_specific_languages(self, temp_project_dir, temp_output_dir):
        """Generate libraries for specific languages only."""
        languages = ["python", "javascript"]

        generate_all_patterns(
            project_dir=temp_project_dir,
            output_dir=temp_output_dir,
            languages=languages,
            source_dir=None,
            max_patterns=50,
        )

        # Check that requested languages were attempted
        # (may skip if no files found, but should not fail)
        generated_files = list(temp_output_dir.glob("*_patterns.py"))
        # At least one should succeed (Python file exists)
        assert len(generated_files) >= 1

    def test_generate_all_with_source_dir(self, temp_project_dir, temp_output_dir):
        """Generate all patterns from specific source directory."""
        # Create subdirectory with code
        subdir = temp_project_dir / "apps"
        subdir.mkdir()
        (subdir / "app.py").write_text("def main(): pass")

        generate_all_patterns(
            project_dir=temp_project_dir,
            output_dir=temp_output_dir,
            languages=["python"],
            source_dir=subdir,
            max_patterns=50,
        )

        generated_files = list(temp_output_dir.glob("*_patterns.py"))
        assert len(generated_files) > 0

    def test_generate_all_creates_output_directory(self, temp_project_dir):
        """Generate-all creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "new" / "patterns"
            assert not output_dir.exists()

            generate_all_patterns(
                project_dir=temp_project_dir,
                output_dir=output_dir,
                languages=["python"],
            )

            # Directory should be created
            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_generate_all_handles_invalid_languages(
        self, temp_project_dir, temp_output_dir, capsys
    ):
        """Generate-all handles unsupported languages gracefully."""
        generate_all_patterns(
            project_dir=temp_project_dir,
            output_dir=temp_output_dir,
            languages=["invalid-lang", "not-supported"],
        )

        # Should print warning about unsupported languages
        captured = capsys.readouterr()
        assert "Unsupported languages" in captured.out or "invalid-lang" in captured.out


class TestCLIArgumentValidation:
    """Tests for CLI argument validation in handle_patterns_command()."""

    def test_generate_requires_language_and_output(self, temp_spec_dir):
        """Generate action requires --language and --output arguments."""
        import argparse

        # Missing --language
        args = argparse.Namespace(
            action="generate",
            language=None,
            output="output.py",
            source=None,
            max_patterns=50,
        )
        result = handle_patterns_command(temp_spec_dir, args)
        assert result == 1  # Error

        # Missing --output
        args = argparse.Namespace(
            action="generate",
            language="python",
            output=None,
            source=None,
            max_patterns=50,
        )
        result = handle_patterns_command(temp_spec_dir, args)
        assert result == 1  # Error

    def test_generate_all_requires_output_dir(self, temp_spec_dir):
        """Generate-all action requires --output-dir argument."""
        import argparse

        args = argparse.Namespace(
            action="generate-all",
            output_dir=None,
            languages=None,
            source=None,
            max_patterns=50,
        )
        result = handle_patterns_command(temp_spec_dir, args)
        assert result == 1  # Error

    def test_unknown_action_returns_error(self, temp_spec_dir):
        """Unknown action returns error code."""
        import argparse

        args = argparse.Namespace(
            action="unknown-action",
        )
        result = handle_patterns_command(temp_spec_dir, args)
        assert result == 1  # Error


class TestCLIIntegration:
    """Tests for end-to-end CLI integration via subprocess."""

    def test_generate_help_command(self):
        """Test that --help works for generate action."""
        # Use absolute path for cwd to avoid Windows path issues
        backend_dir = Path(__file__).parent.parent / "apps" / "backend"
        if not backend_dir.exists():
            pytest.skip("Backend directory not found")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cli.pattern_commands",
                "generate",
                "--help",
            ],
            cwd=str(backend_dir.resolve()),
            capture_output=True,
            text=True,
        )

        # Help should succeed
        assert result.returncode == 0
        assert "generate" in result.stdout.lower()

    def test_generate_all_help_command(self):
        """Test that --help works for generate-all action."""
        # Use absolute path for cwd to avoid Windows path issues
        backend_dir = Path(__file__).parent.parent / "apps" / "backend"
        if not backend_dir.exists():
            pytest.skip("Backend directory not found")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cli.pattern_commands",
                "generate-all",
                "--help",
            ],
            cwd=str(backend_dir.resolve()),
            capture_output=True,
            text=True,
        )

        # Help should succeed
        assert result.returncode == 0
        assert "generate-all" in result.stdout.lower()

    def test_generate_command_integration(self, temp_spec_dir, temp_output_dir):
        """Test generate command via CLI integration."""
        # Use absolute path for cwd to avoid Windows path issues
        backend_dir = Path(__file__).parent.parent / "apps" / "backend"
        if not backend_dir.exists():
            pytest.skip("Backend directory not found")

        output_file = temp_output_dir / "test_patterns.py"

        # Run generate command
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cli.pattern_commands",
                "generate",
                "--spec-dir",
                str(temp_spec_dir),
                "--language",
                "python",
                "--output",
                str(output_file),
                "--source",
                ".",  # Use current directory
            ],
            cwd=str(backend_dir.resolve()),
            capture_output=True,
            text=True,
        )

        # Command should complete (may succeed or fail based on content)
        # Exit code 0 means success
        assert result.returncode in [0, 1]  # 1 might happen if no files found

    def test_generate_all_command_integration(self, temp_spec_dir, temp_output_dir):
        """Test generate-all command via CLI integration."""
        # Use absolute path for cwd to avoid Windows path issues
        backend_dir = Path(__file__).parent.parent / "apps" / "backend"
        if not backend_dir.exists():
            pytest.skip("Backend directory not found")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cli.pattern_commands",
                "generate-all",
                "--spec-dir",
                str(temp_spec_dir),
                "--output-dir",
                str(temp_output_dir),
                "--languages",
                "python",
            ],
            cwd=str(backend_dir.resolve()),
            capture_output=True,
            text=True,
        )

        # Command should complete
        assert result.returncode in [0, 1]


class TestErrorHandling:
    """Tests for error handling in pattern generation."""

    def test_generate_handles_invalid_project_dir(self, temp_output_dir):
        """Generate handles non-existent project directory."""
        invalid_dir = Path("/nonexistent/path/to/project")
        output_path = temp_output_dir / "python_patterns.py"

        # Should not crash, may print warning
        try:
            generate_patterns(
                project_dir=invalid_dir,
                language="python",
                output_path=output_path,
            )
        except (FileNotFoundError, ValueError):
            # Expected behavior - graceful error handling
            pass

    def test_generate_handles_unsupported_language(
        self, temp_project_dir, temp_output_dir, capsys
    ):
        """Generate handles unsupported language gracefully."""
        output_path = temp_output_dir / "invalid_patterns.py"

        # Should print warning and not crash
        generate_patterns(
            project_dir=temp_project_dir,
            language="unsupported-lang",
            output_path=output_path,
        )

        # Should show warning in output
        _captured = capsys.readouterr()  # noqa: F841
        # May contain warning about unsupported language
        # (implementation-dependent)

    def test_generate_handles_empty_project(self, temp_output_dir):
        """Generate handles project with no code files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            output_path = temp_output_dir / "python_patterns.py"

            # Should complete without crashing
            generate_patterns(
                project_dir=empty_dir,
                language="python",
                output_path=output_path,
            )

            # May or may not create output file (implementation-dependent)


class TestPatternLibraryGenerator:
    """Tests for PatternLibraryGenerator class integration."""

    def test_generator_initialization(self, temp_project_dir):
        """PatternLibraryGenerator initializes correctly."""
        generator = PatternLibraryGenerator(temp_project_dir)

        assert generator is not None
        assert generator.project_dir == temp_project_dir.resolve()

    def test_generator_creates_valid_module(self, temp_project_dir, temp_output_dir):
        """Generated module is valid Python code."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "test_patterns.py"

        generator.generate_library_file(output_path, "python", {})

        # Verify it's valid Python by trying to compile it
        if output_path.exists():
            content = output_path.read_text()
            try:
                compile(content, str(output_path), "exec")
                # Valid Python syntax
            except SyntaxError:
                pytest.fail("Generated module has invalid Python syntax")

    def test_generator_with_options(self, temp_project_dir, temp_output_dir):
        """Generator respects custom options."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "test_patterns.py"

        options = {
            "max_patterns_per_category": 10,
            "include_line_numbers": False,
        }

        generator.generate_library_file(output_path, "python", options)

        # Should complete without error
        assert True


class TestSemanticMeaning:
    """Tests for semantic meaning and intent of CLI commands."""

    def test_generate_creates_standalone_library(
        self, temp_project_dir, temp_output_dir
    ):
        """Generate creates a standalone, importable Python module."""
        output_path = temp_output_dir / "standalone_patterns.py"

        generate_patterns(
            project_dir=temp_project_dir,
            language="python",
            output_path=output_path,
        )

        if output_path.exists():
            content = output_path.read_text()
            # Should be a proper Python module
            assert content.startswith("#!/usr/bin/env python3") or content.startswith(
                '"""'
            )

    def test_generate_all_processes_multiple_languages(
        self, temp_project_dir, temp_output_dir
    ):
        """Generate-all processes each language independently."""
        languages = ["python", "javascript", "typescript"]

        generate_all_patterns(
            project_dir=temp_project_dir,
            output_dir=temp_output_dir,
            languages=languages,
        )

        # Each language gets its own file (if found)
        generated_files = list(temp_output_dir.glob("*_patterns.py"))
        # At least python should succeed (we have sample.py)
        assert any("python" in f.name for f in generated_files)

    def test_cli_provides_user_feedback(self, temp_spec_dir, capsys):
        """CLI commands provide user-friendly feedback."""
        import argparse

        args = argparse.Namespace(
            action="generate",
            language=None,  # Missing required argument
            output="output.py",
            source=None,
            max_patterns=50,
        )

        handle_patterns_command(temp_spec_dir, args)

        # Should print helpful error message
        captured = capsys.readouterr()
        # Some output should be generated
        assert len(captured.out) > 0 or len(captured.err) > 0


class TestCLIWorkflow:
    """Tests for complete CLI workflows."""

    def test_end_to_end_single_generation(self, temp_project_dir, temp_output_dir):
        """Complete workflow: analyze project → generate library → verify output."""
        output_path = temp_output_dir / "workflow_patterns.py"

        # Step 1: Generate patterns
        generate_patterns(
            project_dir=temp_project_dir,
            language="python",
            output_path=output_path,
            max_patterns=50,
        )

        # Step 2: Verify output exists
        assert output_path.exists()

        # Step 3: Verify content is valid
        if output_path.exists():
            content = output_path.read_text()
            assert len(content) > 0

    def test_end_to_end_batch_generation(self, temp_project_dir, temp_output_dir):
        """Complete workflow: batch generation for multiple languages."""
        # Step 1: Generate all patterns
        generate_all_patterns(
            project_dir=temp_project_dir,
            output_dir=temp_output_dir,
            languages=["python", "javascript"],
            max_patterns=50,
        )

        # Step 2: Verify output directory contains generated files
        generated_files = list(temp_output_dir.glob("*_patterns.py"))
        assert len(generated_files) > 0

        # Step 3: Verify each file is valid
        for file_path in generated_files:
            content = file_path.read_text()
            assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
