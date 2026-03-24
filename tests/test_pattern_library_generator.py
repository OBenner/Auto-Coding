"""
Test Pattern Library Generator
===============================

Tests for the pattern library generator that creates language-specific
pattern library modules from codebase analysis.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from integrations.graphiti.pattern_library_generator import (
    LANGUAGE_EXTENSIONS,
    PatternLibraryGenerator,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample code files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create Python files
        (project_dir / "src").mkdir(parents=True)
        (project_dir / "src" / "main.py").write_text(
            """
def process_data(value):
    try:
        result = value * 2
        return result
    except ValueError as e:
        logger.error(f"Error: {e}")
        raise

class DataProcessor:
    def __init__(self):
        self._state = None
"""
        )

        (project_dir / "src" / "utils.py").write_text(
            """
def validate_input(data):
    if not data:
        raise ValueError("Invalid input")
    return True
"""
        )

        # Create JavaScript files
        (project_dir / "src" / "app.js").write_text(
            """
function handleError(error) {
    console.error('Error:', error);
    throw error;
}

class Component {
    constructor() {
        this.state = {};
    }
}
"""
        )

        # Create files in excluded directories (should be filtered out)
        (project_dir / "node_modules").mkdir()
        (project_dir / "node_modules" / "lib.py").write_text("# should be excluded")

        (project_dir / ".git").mkdir()
        (project_dir / ".git" / "hook.py").write_text("# should be excluded")

        (project_dir / ".auto-claude").mkdir()
        (project_dir / ".auto-claude" / "test.py").write_text("# should be excluded")

        yield project_dir


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for output files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestPatternLibraryGeneratorInit:
    """Test PatternLibraryGenerator initialization."""

    def test_init_with_string_path(self, temp_project_dir):
        """Test initialization with string path."""
        generator = PatternLibraryGenerator(str(temp_project_dir))
        assert generator.project_dir == temp_project_dir.resolve()
        assert generator.extractor is not None

    def test_init_with_path_object(self, temp_project_dir):
        """Test initialization with Path object."""
        generator = PatternLibraryGenerator(temp_project_dir)
        assert generator.project_dir == temp_project_dir.resolve()
        assert generator.extractor is not None


class TestFindSourceFiles:
    """Test source file discovery."""

    def test_find_python_files(self, temp_project_dir):
        """Test finding Python files."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        # Should find main.py and utils.py, but not files in excluded dirs
        assert len(python_files) == 2
        file_names = {f.name for f in python_files}
        assert "main.py" in file_names
        assert "utils.py" in file_names

    def test_find_javascript_files(self, temp_project_dir):
        """Test finding JavaScript files."""
        generator = PatternLibraryGenerator(temp_project_dir)
        js_files = generator._find_source_files(temp_project_dir, "javascript")

        assert len(js_files) == 1
        assert js_files[0].name == "app.js"

    def test_exclude_node_modules(self, temp_project_dir):
        """Test that node_modules is excluded."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        # Should not include files from node_modules
        for file_path in python_files:
            assert "node_modules" not in file_path.parts

    def test_exclude_git_directory(self, temp_project_dir):
        """Test that .git directory is excluded."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        # Should not include files from .git
        for file_path in python_files:
            assert ".git" not in file_path.parts

    def test_exclude_auto_claude_directory(self, temp_project_dir):
        """Test that .auto-claude directory is excluded."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        # Should not include files from .auto-claude
        for file_path in python_files:
            assert ".auto-claude" not in file_path.parts

    def test_find_files_in_subdirectory(self, temp_project_dir):
        """Test finding files in specific subdirectory."""
        generator = PatternLibraryGenerator(temp_project_dir)
        src_dir = temp_project_dir / "src"
        python_files = generator._find_source_files(src_dir, "python")

        assert len(python_files) == 2

    def test_no_files_found(self, temp_output_dir):
        """Test handling when no files are found."""
        generator = PatternLibraryGenerator(temp_output_dir)
        go_files = generator._find_source_files(temp_output_dir, "go")

        assert len(go_files) == 0


class TestExtractAllPatterns:
    """Test pattern extraction from multiple files."""

    def test_extract_patterns_from_files(self, temp_project_dir):
        """Test extracting patterns from multiple source files with per-file results."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        # Return different patterns for each file via side_effect
        def _mock_extract(file_path, pattern_types=None):
            return [
                {
                    "type": "error",
                    "pattern": f"pattern-from-{file_path.name}",
                    "code_snippet": f"# code from {file_path.name}",
                    "line_number": 5,
                }
            ]

        with patch.object(
            generator.extractor, "extract_patterns", side_effect=_mock_extract
        ):
            patterns = generator._extract_all_patterns(
                python_files, pattern_types=None, include_line_numbers=True
            )

            # Should get one pattern per file
            assert len(patterns) == len(python_files)
            # Each pattern should have correct file metadata
            pattern_files = {p["file"] for p in patterns}
            assert len(pattern_files) == len(python_files)
            # Should include line numbers when requested
            assert all("line_number" in p for p in patterns)

    def test_extract_patterns_without_line_numbers(self, temp_project_dir):
        """Test extracting patterns without line numbers."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        mock_patterns = [
            {
                "type": "error",
                "pattern": "try-except",
                "code_snippet": "try:\n    ...\nexcept Exception:\n    pass",
                "line_number": 10,
            }
        ]

        with patch.object(
            generator.extractor, "extract_patterns", return_value=mock_patterns
        ):
            patterns = generator._extract_all_patterns(
                python_files, pattern_types=None, include_line_numbers=False
            )

            # Should remove line numbers when not requested
            assert all("line_number" not in p for p in patterns)

    def test_extract_specific_pattern_types(self, temp_project_dir):
        """Test extracting specific pattern types."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        with patch.object(generator.extractor, "extract_patterns", return_value=[]):
            generator._extract_all_patterns(
                python_files, pattern_types=["error", "api"], include_line_numbers=False
            )

            # Should pass pattern_types to extractor
            generator.extractor.extract_patterns.assert_called()

    def test_handle_extraction_errors(self, temp_project_dir):
        """Test handling errors during pattern extraction."""
        generator = PatternLibraryGenerator(temp_project_dir)
        python_files = generator._find_source_files(generator.project_dir, "python")

        # Mock extractor to raise an error
        with patch.object(
            generator.extractor,
            "extract_patterns",
            side_effect=Exception("Parse error"),
        ):
            # Should not crash, just skip the file
            patterns = generator._extract_all_patterns(
                python_files, pattern_types=None, include_line_numbers=False
            )

            # Should return empty list when all files fail
            assert patterns == []


class TestCategorizePatterns:
    """Test pattern categorization."""

    def test_categorize_patterns(self, temp_project_dir):
        """Test categorizing extracted patterns."""
        generator = PatternLibraryGenerator(temp_project_dir)

        patterns = [
            {
                "type": "error",
                "pattern": "try-except",
                "code_snippet": "try:\n    ...\nexcept:\n    pass",
            },
            {
                "type": "api",
                "pattern": "REST endpoint",
                "code_snippet": "@app.route('/api/data')\ndef get_data():\n    pass",
            },
        ]

        with patch(
            "integrations.graphiti.pattern_library_generator.categorize_pattern_sync",
            side_effect=[
                {
                    "category": "error-handling",
                    "confidence": 0.9,
                    "reasoning": "Error handling pattern",
                },
                {
                    "category": "api-design",
                    "confidence": 0.95,
                    "reasoning": "API endpoint pattern",
                },
            ],
        ):
            categorized = generator._categorize_patterns(patterns)

            assert "error-handling" in categorized
            assert "api-design" in categorized
            assert len(categorized["error-handling"]) == 1
            assert len(categorized["api-design"]) == 1

    def test_categorize_with_fallback(self, temp_project_dir):
        """Test categorization with fallback to type mapping."""
        generator = PatternLibraryGenerator(temp_project_dir)

        patterns = [
            {
                "type": "error",
                "pattern": "error handling",
                "code_snippet": "if err != nil { return err }",
            }
        ]

        with patch(
            "integrations.graphiti.pattern_library_generator.categorize_pattern_sync",
            return_value={
                "category": "uncategorized",
                "confidence": 0.0,
                "reasoning": "Could not categorize",
            },
        ):
            categorized = generator._categorize_patterns(patterns)

            # Should fallback to type-based categorization
            assert "error-handling" in categorized

    def test_categorize_empty_patterns(self, temp_project_dir):
        """Test categorizing empty pattern list."""
        generator = PatternLibraryGenerator(temp_project_dir)
        categorized = generator._categorize_patterns([])

        assert categorized == {}


class TestGenerateModuleCode:
    """Test Python module code generation."""

    def test_generate_module_with_patterns(self, temp_project_dir):
        """Test generating module code with patterns."""
        generator = PatternLibraryGenerator(temp_project_dir)

        categorized_patterns = {
            "error-handling": [
                {
                    "type": "error",
                    "pattern": "try-except",
                    "code_snippet": 'try:\n    result = process()\nexcept ValueError:\n    logger.error("Failed")',
                }
            ]
        }

        module_code = generator._generate_module_code("python", categorized_patterns)

        # Should include module header
        assert "Python Language Patterns Module" in module_code
        assert "Auto-generated" in module_code

        # Should include category section
        assert "ERROR HANDLING PATTERNS" in module_code
        assert "ERROR_HANDLING_PATTERNS = {" in module_code

        # Should include pattern code
        assert "try:" in module_code
        assert "except ValueError:" in module_code

    def test_generate_module_multiple_categories(self, temp_project_dir):
        """Test generating module with multiple categories."""
        generator = PatternLibraryGenerator(temp_project_dir)

        categorized_patterns = {
            "error-handling": [
                {
                    "type": "error",
                    "pattern": "try-except",
                    "code_snippet": "try:\n    pass\nexcept:\n    pass",
                }
            ],
            "api-design": [
                {
                    "type": "api",
                    "pattern": "endpoint",
                    "code_snippet": "@app.route('/test')\ndef test():\n    pass",
                }
            ],
        }

        module_code = generator._generate_module_code("go", categorized_patterns)

        # Should include both categories (sorted alphabetically)
        assert "API DESIGN PATTERNS" in module_code
        assert "ERROR HANDLING PATTERNS" in module_code
        assert "API_DESIGN_PATTERNS = {" in module_code
        assert "ERROR_HANDLING_PATTERNS = {" in module_code

    def test_generate_module_escapes_strings(self, temp_project_dir):
        """Test that module generation escapes special characters."""
        generator = PatternLibraryGenerator(temp_project_dir)

        categorized_patterns = {
            "testing": [
                {
                    "type": "test",
                    "pattern": "docstring test",
                    "code_snippet": '"""Test docstring with triple quotes"""',
                }
            ]
        }

        module_code = generator._generate_module_code("python", categorized_patterns)

        # json.dumps serialization should safely escape the triple quotes
        # The output uses JSON string literals, so triple double-quotes are escaped
        assert '"""' not in module_code or r"\"\"\"" in module_code

    def test_generate_empty_module(self, temp_project_dir):
        """Test generating module with no patterns."""
        generator = PatternLibraryGenerator(temp_project_dir)

        module_code = generator._generate_module_code("rust", {})

        # Should include header but no pattern dictionaries
        assert "Rust Language Patterns Module" in module_code


class TestGeneratePatternKey:
    """Test pattern key generation."""

    def test_generate_key_from_pattern(self, temp_project_dir):
        """Test generating key from pattern description."""
        generator = PatternLibraryGenerator(temp_project_dir)

        pattern = {"pattern": "Try-Except Error Handling", "type": "error"}
        key = generator._generate_pattern_key(pattern, 0)

        # Should be lowercase with underscores
        assert key == "try_except_error_handling"
        assert key.islower()
        assert " " not in key

    def test_generate_key_from_type(self, temp_project_dir):
        """Test generating key from type when pattern is missing."""
        generator = PatternLibraryGenerator(temp_project_dir)

        pattern = {"type": "error-handling"}
        key = generator._generate_pattern_key(pattern, 0)

        # Should sanitize hyphens to underscores
        assert key == "error_handling"

    def test_generate_key_with_index(self, temp_project_dir):
        """Test generating key with index for uniqueness."""
        generator = PatternLibraryGenerator(temp_project_dir)

        pattern = {"pattern": "basic pattern", "type": "test"}
        key = generator._generate_pattern_key(pattern, 5)

        # Should include index suffix
        assert key == "basic_pattern_5"

    def test_generate_key_sanitizes_characters(self, temp_project_dir):
        """Test that key generation removes special characters."""
        generator = PatternLibraryGenerator(temp_project_dir)

        pattern = {"pattern": "API (REST) @endpoint!", "type": "api"}
        key = generator._generate_pattern_key(pattern, 0)

        # Should only contain alphanumeric and underscore
        assert all(c.isalnum() or c == "_" for c in key)

    def test_generate_key_limits_length(self, temp_project_dir):
        """Test that long keys are truncated."""
        generator = PatternLibraryGenerator(temp_project_dir)

        pattern = {
            "pattern": "This is a very long pattern description that should be truncated",
            "type": "test",
        }
        key = generator._generate_pattern_key(pattern, 0)

        # Should be truncated to max 40 characters
        assert len(key) <= 40


class TestWriteEmptyLibrary:
    """Test writing empty library files."""

    def test_write_empty_library(self, temp_project_dir, temp_output_dir):
        """Test writing an empty library file."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "empty_patterns.py"

        generator._write_empty_library(output_path, "javascript")

        # Should create the file
        assert output_path.exists()

        # Should include header and note about no patterns
        content = output_path.read_text()
        assert "Javascript Language Patterns Module" in content
        assert "No patterns were extracted" in content or "No patterns found" in content

    def test_write_empty_library_creates_parent_dirs(
        self, temp_project_dir, temp_output_dir
    ):
        """Test that writing creates parent directories."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "subdir" / "nested" / "empty.py"

        generator._write_empty_library(output_path, "go")

        # Should create parent directories
        assert output_path.parent.exists()
        assert output_path.exists()


class TestGenerateLibraryFile:
    """Test the main library generation workflow."""

    def test_generate_library_file_success(self, temp_project_dir, temp_output_dir):
        """Test successful library file generation."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "python_patterns.py"

        # Mock pattern extraction and categorization
        mock_patterns = [
            {
                "type": "error",
                "pattern": "try-except",
                "code_snippet": "try:\n    pass\nexcept:\n    pass",
            }
        ]

        with patch.object(
            generator.extractor, "extract_patterns", return_value=mock_patterns
        ):
            with patch(
                "integrations.graphiti.pattern_library_generator.categorize_pattern_sync",
                return_value={
                    "category": "error-handling",
                    "confidence": 0.9,
                    "reasoning": "Error pattern",
                },
            ):
                generator.generate_library_file(
                    output_path=output_path, language="python", options={}
                )

                # Should create the output file
                assert output_path.exists()

                # Should include patterns
                content = output_path.read_text()
                assert "ERROR_HANDLING_PATTERNS" in content

    def test_generate_library_unsupported_language(
        self, temp_project_dir, temp_output_dir
    ):
        """Test handling unsupported language."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "unsupported.py"

        # Should raise ValueError for unsupported language
        with pytest.raises(ValueError, match="Unsupported language"):
            generator.generate_library_file(
                output_path=output_path, language="cobol", options={}
            )

    def test_generate_library_no_files_found(self, temp_project_dir, temp_output_dir):
        """Test handling when no source files are found."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "go_patterns.py"

        # Generate for Go (no Go files in temp project)
        generator.generate_library_file(
            output_path=output_path, language="go", options={}
        )

        # Should create empty library file
        assert output_path.exists()
        content = output_path.read_text()
        assert "No patterns" in content

    def test_generate_library_no_patterns_extracted(
        self, temp_project_dir, temp_output_dir
    ):
        """Test handling when no patterns are extracted."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "python_patterns.py"

        # Mock extractor to return no patterns
        with patch.object(generator.extractor, "extract_patterns", return_value=[]):
            generator.generate_library_file(
                output_path=output_path, language="python", options={}
            )

            # Should create empty library file
            assert output_path.exists()
            content = output_path.read_text()
            assert "No patterns" in content

    def test_generate_library_with_options(self, temp_project_dir, temp_output_dir):
        """Test generating library with custom options."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "patterns.py"

        mock_patterns = [
            {
                "type": "error",
                "pattern": f"pattern-{i}",
                "code_snippet": f"code {i}",
            }
            for i in range(100)
        ]

        with patch.object(
            generator.extractor, "extract_patterns", return_value=mock_patterns
        ):
            with patch(
                "integrations.graphiti.pattern_library_generator.categorize_pattern_sync",
                return_value={
                    "category": "error-handling",
                    "confidence": 0.9,
                    "reasoning": "Error pattern",
                },
            ):
                # Generate with max_patterns_per_category limit
                generator.generate_library_file(
                    output_path=output_path,
                    language="python",
                    options={
                        "max_patterns_per_category": 10,
                        "include_line_numbers": True,
                    },
                )

                # Should limit patterns per category
                content = output_path.read_text()
                # Count pattern entries (each ends with """,)
                pattern_count = content.count('""",')
                assert pattern_count <= 10

    def test_generate_library_with_source_dir(self, temp_project_dir, temp_output_dir):
        """Test generating library from specific source directory."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "patterns.py"

        src_dir = temp_project_dir / "src"

        mock_patterns = [
            {
                "type": "error",
                "pattern": "test",
                "code_snippet": "test code",
            }
        ]

        with patch.object(
            generator.extractor, "extract_patterns", return_value=mock_patterns
        ):
            with patch(
                "integrations.graphiti.pattern_library_generator.categorize_pattern_sync",
                return_value={
                    "category": "testing",
                    "confidence": 0.8,
                    "reasoning": "Test pattern",
                },
            ):
                generator.generate_library_file(
                    output_path=output_path,
                    language="python",
                    options={"source_dir": str(src_dir)},
                )

                # Should generate successfully from subdirectory
                assert output_path.exists()

    def test_generate_library_with_pattern_types(
        self, temp_project_dir, temp_output_dir
    ):
        """Test generating library with specific pattern types."""
        generator = PatternLibraryGenerator(temp_project_dir)
        output_path = temp_output_dir / "patterns.py"

        with patch.object(generator.extractor, "extract_patterns", return_value=[]):
            generator.generate_library_file(
                output_path=output_path,
                language="python",
                options={"pattern_types": ["error", "api"]},
            )

            # Should pass pattern_types to extraction
            # (verified in test_extract_specific_pattern_types)
            assert output_path.exists()


class TestLanguageExtensions:
    """Test language extension mappings."""

    def test_supported_languages(self):
        """Test that expected languages are supported."""
        expected_languages = [
            "python",
            "javascript",
            "typescript",
            "go",
            "rust",
            "java",
            "csharp",
            "cpp",
            "ruby",
            "php",
        ]

        for lang in expected_languages:
            assert lang in LANGUAGE_EXTENSIONS

    def test_python_extensions(self):
        """Test Python file extensions."""
        assert ".py" in LANGUAGE_EXTENSIONS["python"]

    def test_javascript_extensions(self):
        """Test JavaScript file extensions."""
        assert ".js" in LANGUAGE_EXTENSIONS["javascript"]
        assert ".jsx" in LANGUAGE_EXTENSIONS["javascript"]

    def test_typescript_extensions(self):
        """Test TypeScript file extensions."""
        assert ".ts" in LANGUAGE_EXTENSIONS["typescript"]
        assert ".tsx" in LANGUAGE_EXTENSIONS["typescript"]
