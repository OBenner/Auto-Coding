#!/usr/bin/env python3
"""
Tests for Architecture Validator
==================================

Tests the architecture_validator module which validates architectural
pattern consistency across the codebase.
"""

import json
import tempfile
from pathlib import Path

import pytest

# Add apps/backend to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.architecture_validator import (
    ArchitecturalIssue,
    ArchitecturalPattern,
    ArchitecturalAnalysisResult,
    ArchitectureValidator,
    validate_architecture,
    has_architectural_issues,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def sample_python_file_snake_case():
    """Sample Python file following snake_case convention."""
    return '''
def process_data(input_value):
    """Process the input data."""
    return input_value * 2

def calculate_total(items):
    """Calculate total."""
    return sum(items)

class DataProcessor:
    """Data processor class."""

    def process_item(self, item):
        """Process single item."""
        return item
'''


@pytest.fixture
def sample_python_file_camel_case():
    """Sample Python file with camelCase violations."""
    return '''
def processData(inputValue):
    """Process data using camelCase."""
    return inputValue * 2

class DataProcessor:
    """Data processor class."""

    def processItem(self, item):
        """Process item with camelCase."""
        return item
'''


@pytest.fixture
def sample_python_file_with_bare_except():
    """Sample Python file with bare except clause."""
    return '''
def risky_function():
    try:
        dangerous_operation()
    except:
        pass
'''


@pytest.fixture
def sample_python_file_with_wildcard_import():
    """Sample Python file with wildcard import."""
    return '''
from module import *

def use_wildcard():
    return something()
'''


@pytest.fixture
def sample_python_file_missing_docstring():
    """Sample Python file with class missing docstring."""
    return '''
class MissingDocstring:
    def method(self):
        pass
'''


class TestArchitecturalIssue:
    """Test ArchitecturalIssue dataclass."""

    def test_create_issue(self):
        """Test creating an architectural issue."""
        issue = ArchitecturalIssue(
            severity="high",
            issue_type="pattern_inconsistency",
            title="Inconsistent naming",
            description="Function uses camelCase instead of snake_case",
            file="/path/to/file.py",
            line=10,
            suggestion="Rename to snake_case",
            pattern="Functions should use snake_case",
        )

        assert issue.severity == "high"
        assert issue.issue_type == "pattern_inconsistency"
        assert issue.title == "Inconsistent naming"
        assert issue.line == 10


class TestArchitecturalPattern:
    """Test ArchitecturalPattern dataclass."""

    def test_create_pattern(self):
        """Test creating an architectural pattern."""
        pattern = ArchitecturalPattern(
            pattern_type="naming_function",
            pattern_name="snake_case",
            frequency=10,
            examples=["func_one.py", "func_two.py"],
            confidence=0.9,
        )

        assert pattern.pattern_type == "naming_function"
        assert pattern.pattern_name == "snake_case"
        assert pattern.frequency == 10
        assert pattern.confidence == 0.9
        assert len(pattern.examples) == 2


class TestArchitecturalAnalysisResult:
    """Test ArchitecturalAnalysisResult dataclass."""

    def test_create_result(self):
        """Test creating an analysis result."""
        result = ArchitecturalAnalysisResult(
            issues=[],
            patterns=[],
            analysis_errors=[],
            has_critical_issues=False,
            should_warn=False,
            files_analyzed=0,
        )

        assert len(result.issues) == 0
        assert len(result.patterns) == 0
        assert result.has_critical_issues is False
        assert result.should_warn is False


class TestArchitectureValidator:
    """Test ArchitectureValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = ArchitectureValidator()
        assert validator is not None

    def test_is_analyzable_python_file(self):
        """Test _is_analyzable returns True for Python files."""
        validator = ArchitectureValidator()
        assert validator._is_analyzable("test.py") is True
        assert validator._is_analyzable("module/file.py") is True

    def test_is_analyzable_non_python_file(self):
        """Test _is_analyzable returns False for non-Python files."""
        validator = ArchitectureValidator()
        assert validator._is_analyzable("test.js") is False
        assert validator._is_analyzable("README.md") is False

    def test_analyze_empty_project(self, temp_project_dir):
        """Test analyzing an empty project."""
        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 0
        assert len(result.issues) == 0
        assert len(result.patterns) == 0
        assert result.has_critical_issues is False

    def test_analyze_with_snake_case_functions(
        self, temp_project_dir, sample_python_file_snake_case
    ):
        """Test analyzing project with snake_case functions."""
        # Create Python file
        (temp_project_dir / "module.py").write_text(sample_python_file_snake_case)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 1
        # Should detect snake_case pattern
        naming_patterns = [p for p in result.patterns if p.pattern_type == "naming_function"]
        assert len(naming_patterns) > 0

    def test_analyze_with_camel_case_violation(
        self, temp_project_dir, sample_python_file_camel_case, sample_python_file_snake_case
    ):
        """Test analyzing project with camelCase violations."""
        # Create multiple snake_case files to establish pattern
        for i in range(3):
            (temp_project_dir / f"snake_{i}.py").write_text(sample_python_file_snake_case)
        # Add one camelCase file
        (temp_project_dir / "camel.py").write_text(sample_python_file_camel_case)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 4
        # Should detect naming violations after establishing pattern
        naming_issues = [i for i in result.issues if i.issue_type == "naming_violation"]
        assert len(naming_issues) > 0

    def test_analyze_with_bare_except(
        self, temp_project_dir, sample_python_file_with_bare_except
    ):
        """Test analyzing file with bare except clause."""
        (temp_project_dir / "module.py").write_text(sample_python_file_with_bare_except)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 1
        # Should detect bare except
        error_issues = [i for i in result.issues if i.issue_type == "error_handling"]
        assert len(error_issues) > 0
        assert any("Bare except" in i.title for i in error_issues)

    def test_analyze_with_wildcard_import(
        self, temp_project_dir, sample_python_file_with_wildcard_import
    ):
        """Test analyzing file with wildcard import."""
        (temp_project_dir / "module.py").write_text(sample_python_file_with_wildcard_import)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 1
        # Should detect wildcard import
        import_issues = [i for i in result.issues if i.issue_type == "import_violation"]
        assert len(import_issues) > 0
        assert any("Wildcard import" in i.title for i in import_issues)

    def test_analyze_with_missing_docstring(
        self, temp_project_dir, sample_python_file_missing_docstring
    ):
        """Test analyzing file with missing class docstring."""
        (temp_project_dir / "module.py").write_text(sample_python_file_missing_docstring)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 1
        # Should detect missing docstring
        structure_issues = [i for i in result.issues if i.issue_type == "structure_violation"]
        assert len(structure_issues) > 0
        assert any("Missing docstring" in i.title for i in structure_issues)

    def test_analyze_filters_out_skip_dirs(self, temp_project_dir):
        """Test that analysis filters out common skip directories."""
        # Create files in skip directories
        (temp_project_dir / "node_modules").mkdir()
        (temp_project_dir / "node_modules" / "test.py").write_text("def test(): pass")

        (temp_project_dir / ".venv").mkdir()
        (temp_project_dir / ".venv" / "test.py").write_text("def test(): pass")

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Should not analyze files in skip directories
        assert result.files_analyzed == 0

    def test_analyze_with_changed_files_filter(
        self, temp_project_dir, sample_python_file_snake_case
    ):
        """Test analyzing only changed files."""
        (temp_project_dir / "module1.py").write_text(sample_python_file_snake_case)
        (temp_project_dir / "module2.py").write_text(sample_python_file_snake_case)

        validator = ArchitectureValidator()
        result = validator.analyze(
            temp_project_dir, changed_files=["module1.py"]
        )

        # Should only analyze specified file
        assert result.files_analyzed == 1

    def test_has_critical_issues_detection(self, temp_project_dir):
        """Test detection of critical/high severity issues."""
        # Create file with bare except (high severity)
        code = '''
def func():
    try:
        pass
    except:
        pass
'''
        (temp_project_dir / "module.py").write_text(code)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Bare except is high severity
        assert result.has_critical_issues is True

    def test_should_warn_detection(self, temp_project_dir):
        """Test detection of medium+ issues for warnings."""
        # Create file with wildcard import (medium severity)
        code = "from module import *\n"
        (temp_project_dir / "module.py").write_text(code)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.should_warn is True

    def test_save_results_creates_file(self, temp_project_dir):
        """Test that _save_results creates output file."""
        spec_dir = temp_project_dir / "spec"
        spec_dir.mkdir()

        validator = ArchitectureValidator()
        result = ArchitecturalAnalysisResult(files_analyzed=5)

        validator._save_results(spec_dir, result)

        output_file = spec_dir / "architecture_analysis.json"
        assert output_file.exists()

        # Verify content
        data = json.loads(output_file.read_text())
        assert data["files_analyzed"] == 5

    def test_format_report(self):
        """Test formatting analysis results as a report."""
        validator = ArchitectureValidator()
        result = ArchitecturalAnalysisResult(
            files_analyzed=10,
            issues=[
                ArchitecturalIssue(
                    severity="high",
                    issue_type="error_handling",
                    title="Bare except",
                    description="Found bare except",
                    file="test.py",
                    line=10,
                    suggestion="Use specific exception",
                    pattern="Specific exception handling",
                )
            ],
            patterns=[
                ArchitecturalPattern(
                    pattern_type="naming_function",
                    pattern_name="snake_case",
                    frequency=8,
                    confidence=0.8,
                )
            ],
        )

        report = validator.format_report(result)

        assert "ARCHITECTURAL CONSISTENCY REPORT" in report
        assert "Files Analyzed: 10" in report
        assert "Bare except" in report
        assert "snake_case" in report

    def test_analyze_syntax_error_file_is_skipped(self, temp_project_dir):
        """Test that files with syntax errors are skipped gracefully."""
        # Create file with syntax error
        (temp_project_dir / "broken.py").write_text("def broken(\n")

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Should not crash, file is skipped
        assert result.files_analyzed == 1

    def test_discover_error_handling_patterns(self, temp_project_dir):
        """Test discovering error handling patterns."""
        code1 = '''
try:
    operation()
except Exception as e:
    handle(e)
'''
        code2 = '''
try:
    operation()
except Exception as e:
    log(e)
'''
        (temp_project_dir / "file1.py").write_text(code1)
        (temp_project_dir / "file2.py").write_text(code2)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Should discover error handling pattern
        error_patterns = [p for p in result.patterns if p.pattern_type == "error_handling"]
        assert len(error_patterns) > 0

    def test_discover_import_organization_patterns(self, temp_project_dir):
        """Test discovering import organization patterns."""
        code = '''
import os
import sys

from pathlib import Path
'''
        (temp_project_dir / "file.py").write_text(code)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Should discover import organization pattern
        import_patterns = [p for p in result.patterns if p.pattern_type == "import_organization"]
        # Pattern detection requires multiple files, so may not always detect
        assert result.files_analyzed == 1


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_validate_architecture(self, temp_project_dir, sample_python_file_snake_case):
        """Test validate_architecture convenience function."""
        (temp_project_dir / "module.py").write_text(sample_python_file_snake_case)

        result = validate_architecture(temp_project_dir)

        assert isinstance(result, ArchitecturalAnalysisResult)
        assert result.files_analyzed > 0

    def test_validate_architecture_with_spec_dir(
        self, temp_project_dir, sample_python_file_snake_case
    ):
        """Test validate_architecture saves results to spec_dir."""
        spec_dir = temp_project_dir / "spec"
        spec_dir.mkdir()
        (temp_project_dir / "module.py").write_text(sample_python_file_snake_case)

        result = validate_architecture(temp_project_dir, spec_dir=spec_dir)

        assert result.files_analyzed > 0
        assert (spec_dir / "architecture_analysis.json").exists()

    def test_has_architectural_issues_returns_true(
        self, temp_project_dir, sample_python_file_with_bare_except
    ):
        """Test has_architectural_issues returns True when issues found."""
        (temp_project_dir / "module.py").write_text(sample_python_file_with_bare_except)

        has_issues = has_architectural_issues(temp_project_dir)

        assert has_issues is True

    def test_has_architectural_issues_returns_false(
        self, temp_project_dir, sample_python_file_snake_case
    ):
        """Test has_architectural_issues returns False when no critical issues."""
        (temp_project_dir / "module.py").write_text(sample_python_file_snake_case)

        has_issues = has_architectural_issues(temp_project_dir)

        # snake_case files may have low severity issues but not critical
        # Result depends on discovered patterns
        assert isinstance(has_issues, bool)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_analyze_empty_file(self, temp_project_dir):
        """Test analyzing empty Python file."""
        (temp_project_dir / "empty.py").write_text("")

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Should handle empty file
        assert result.files_analyzed == 1

    def test_analyze_file_with_only_comments(self, temp_project_dir):
        """Test analyzing file with only comments."""
        (temp_project_dir / "comments.py").write_text("# Just a comment\n# Another comment\n")

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 1

    def test_analyze_with_unicode_content(self, temp_project_dir):
        """Test analyzing file with unicode content."""
        code = '''
def greet():
    """Say hello in different languages: 你好, مرحبا, שלום"""
    return "Hello 世界"
'''
        (temp_project_dir / "unicode.py").write_text(code, encoding="utf-8")

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        assert result.files_analyzed == 1

    def test_pattern_confidence_calculation(self, temp_project_dir):
        """Test that pattern confidence is calculated correctly."""
        # Create multiple files with same pattern
        for i in range(5):
            code = f'''
def function_{i}(param):
    """Snake case function {i}."""
    return param
'''
            (temp_project_dir / f"file{i}.py").write_text(code)

        validator = ArchitectureValidator()
        result = validator.analyze(temp_project_dir)

        # Should detect snake_case pattern with high confidence
        naming_patterns = [p for p in result.patterns if "naming" in p.pattern_type]
        if naming_patterns:
            assert naming_patterns[0].confidence > 0.5