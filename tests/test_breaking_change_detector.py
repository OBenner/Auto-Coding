#!/usr/bin/env python3
"""
Tests for Breaking Change Detector
====================================

Tests the breaking_change_detector module which analyzes code changes
to detect breaking API contract violations.
"""

import json
from pathlib import Path

import pytest

# Add apps/backend to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.breaking_change_detector import (
    BreakingChange,
    BreakingChangeResult,
    ApiElement,
    BreakingChangeDetector,
    detect_breaking_changes,
    has_breaking_changes,
)


class TestBreakingChange:
    """Test BreakingChange dataclass."""

    def test_create_breaking_change(self):
        """Test creating a breaking change."""
        change = BreakingChange(
            severity="critical",
            change_type="removed_function",
            title="Function removed",
            description="Public function was removed",
            file="module.py",
            old_signature="def func(a, b)",
            new_signature=None,
            migration_guide="Restore the function",
        )

        assert change.severity == "critical"
        assert change.change_type == "removed_function"
        assert change.new_signature is None


class TestBreakingChangeResult:
    """Test BreakingChangeResult dataclass."""

    def test_create_result(self):
        """Test creating a result."""
        result = BreakingChangeResult(
            breaking_changes=[],
            analysis_errors=[],
            has_breaking_changes=False,
            should_block=False,
            files_analyzed=0,
        )

        assert len(result.breaking_changes) == 0
        assert result.has_breaking_changes is False


class TestApiElement:
    """Test ApiElement dataclass."""

    def test_create_api_element(self):
        """Test creating an API element."""
        element = ApiElement(
            name="process_data",
            element_type="function",
            signature="def process_data(data: str) -> str",
            params=["data"],
            param_types={"data": "str"},
            return_type="str",
            required_params=["data"],
            optional_params=[],
        )

        assert element.name == "process_data"
        assert element.element_type == "function"
        assert "data" in element.params
        assert element.return_type == "str"


class TestBreakingChangeDetector:
    """Test BreakingChangeDetector class."""

    def test_init(self):
        """Test detector initialization."""
        detector = BreakingChangeDetector()
        assert detector is not None

    def test_extract_api_elements_from_simple_function(self):
        """Test extracting API elements from simple function."""
        code = '''
def public_func():
    pass

def _private_func():
    pass
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        # Should only extract public function
        assert len(api_elements) == 1
        assert api_elements[0].name == "public_func"
        assert api_elements[0].element_type == "function"

    def test_extract_api_elements_from_function_with_params(self):
        """Test extracting API elements from function with parameters."""
        code = '''
def process_data(data: str, count: int = 10) -> str:
    return data * count
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        assert len(api_elements) == 1
        element = api_elements[0]
        assert element.name == "process_data"
        assert "data" in element.params
        assert "count" in element.params
        assert element.param_types["data"] == "str"
        assert element.param_types["count"] == "int"
        assert element.return_type == "str"
        assert "data" in element.required_params
        assert "count" in element.optional_params

    def test_extract_api_elements_from_class(self):
        """Test extracting API elements from class."""
        code = '''
class PublicClass:
    """Public class."""

    def public_method(self):
        pass

    def _private_method(self):
        pass

class _PrivateClass:
    """Private class."""
    pass
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        # Should extract PublicClass and its public method
        names = [e.name for e in api_elements]
        assert "PublicClass" in names
        assert "PublicClass.public_method" in names
        assert "_PrivateClass" not in names
        assert "PublicClass._private_method" not in names

    def test_extract_api_elements_from_async_function(self):
        """Test extracting async function."""
        code = '''
async def async_func(param: int) -> str:
    return str(param)
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        assert len(api_elements) == 1
        element = api_elements[0]
        assert element.is_async is True
        assert element.name == "async_func"

    def test_extract_api_elements_from_syntax_error_file(self):
        """Test extracting from file with syntax error returns empty list."""
        code = "def broken(\n"

        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        assert len(api_elements) == 0

    def test_analyze_file_change_with_no_changes(self):
        """Test analyzing file with no changes."""
        old_code = '''
def func():
    pass
'''
        new_code = '''
def func():
    pass
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        assert len(changes) == 0

    def test_analyze_file_change_with_removed_function(self):
        """Test detecting removed function."""
        old_code = '''
def public_func():
    pass
'''
        new_code = ""

        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        assert len(changes) == 1
        assert changes[0].change_type == "removed_function"
        assert changes[0].severity == "critical"
        assert "public_func" in changes[0].title

    def test_analyze_file_change_with_parameter_change(self):
        """Test detecting parameter changes."""
        old_code = '''
def func(a, b):
    pass
'''
        new_code = '''
def func(a, b, c):
    pass
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        assert len(changes) >= 1
        assert any(c.change_type == "signature_change" for c in changes)

    def test_analyze_file_change_with_removed_parameter(self):
        """Test detecting removed parameters (critical)."""
        old_code = '''
def func(a, b, c):
    pass
'''
        new_code = '''
def func(a, b):
    pass
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        # Removed parameters should be critical
        assert len(changes) >= 1
        signature_changes = [c for c in changes if c.change_type == "signature_change"]
        assert len(signature_changes) > 0
        assert signature_changes[0].severity == "critical"

    def test_analyze_file_change_with_return_type_change(self):
        """Test detecting return type changes."""
        old_code = '''
def func() -> int:
    return 1
'''
        new_code = '''
def func() -> str:
    return "1"
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        assert len(changes) >= 1
        return_changes = [c for c in changes if c.change_type == "return_type_change"]
        assert len(return_changes) > 0
        assert return_changes[0].severity == "high"

    def test_analyze_file_change_with_async_sync_change(self):
        """Test detecting async/sync changes."""
        old_code = '''
def func():
    pass
'''
        new_code = '''
async def func():
    pass
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        assert len(changes) >= 1
        async_changes = [c for c in changes if c.change_type == "async_sync_change"]
        assert len(async_changes) > 0
        assert async_changes[0].severity == "critical"

    def test_analyze_file_change_with_added_optional_parameter(self):
        """Test adding optional parameter (lower severity)."""
        old_code = '''
def func(a):
    pass
'''
        new_code = '''
def func(a, b=10):
    pass
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        # Adding optional param should be medium severity
        if len(changes) > 0:
            signature_changes = [c for c in changes if c.change_type == "signature_change"]
            if len(signature_changes) > 0:
                assert signature_changes[0].severity in ["medium", "high"]

    def test_analyze_file_change_with_added_required_parameter(self):
        """Test adding required parameter (high severity)."""
        old_code = '''
def func(a):
    pass
'''
        new_code = '''
def func(a, b):
    pass
'''
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        # Adding required param should be high severity
        assert len(changes) >= 1
        signature_changes = [c for c in changes if c.change_type == "signature_change"]
        assert len(signature_changes) > 0
        assert signature_changes[0].severity == "high"

    def test_analyze_with_file_dict_mode(self):
        """Test analyze using file dict mode."""
        old_files = {
            "module.py": "def func(): pass"
        }
        new_files = {
            "module.py": "def func(param): pass"
        }

        detector = BreakingChangeDetector()
        result = detector.analyze(old_files=old_files, new_files=new_files)

        assert result.files_analyzed == 1
        assert len(result.breaking_changes) > 0
        assert result.has_breaking_changes is True

    def test_analyze_with_removed_file(self):
        """Test detecting removed file."""
        old_files = {
            "module.py": "def public_func(): pass"
        }
        new_files = {}

        detector = BreakingChangeDetector()
        result = detector.analyze(old_files=old_files, new_files=new_files)

        # Should detect removed file with public API
        assert len(result.breaking_changes) >= 1
        removed = [c for c in result.breaking_changes if c.change_type == "removed_file"]
        assert len(removed) > 0
        assert removed[0].severity == "critical"

    def test_analyze_with_removed_class(self):
        """Test detecting removed class."""
        old_code = '''
class PublicClass:
    pass
'''
        new_code = ""

        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        removed_classes = [c for c in changes if c.change_type == "removed_class"]
        assert len(removed_classes) > 0
        assert removed_classes[0].severity == "critical"

    def test_determine_param_change_severity_removed_params(self):
        """Test severity determination for removed parameters."""
        detector = BreakingChangeDetector()

        old_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a, b)",
            params=["a", "b"],
            required_params=["a", "b"],
            optional_params=[],
        )
        new_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a)",
            params=["a"],
            required_params=["a"],
            optional_params=[],
        )

        severity = detector._determine_param_change_severity(old_elem, new_elem)

        assert severity == "critical"

    def test_determine_param_change_severity_added_required_params(self):
        """Test severity for added required parameters."""
        detector = BreakingChangeDetector()

        old_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a)",
            params=["a"],
            required_params=["a"],
            optional_params=[],
        )
        new_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a, b)",
            params=["a", "b"],
            required_params=["a", "b"],
            optional_params=[],
        )

        severity = detector._determine_param_change_severity(old_elem, new_elem)

        assert severity == "high"

    def test_determine_param_change_severity_added_optional_params(self):
        """Test severity for added optional parameters."""
        detector = BreakingChangeDetector()

        old_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a)",
            params=["a"],
            required_params=["a"],
            optional_params=[],
        )
        new_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a, b=10)",
            params=["a", "b"],
            required_params=["a"],
            optional_params=["b"],
        )

        severity = detector._determine_param_change_severity(old_elem, new_elem)

        assert severity == "medium"

    def test_generate_migration_guide_removed_params(self):
        """Test migration guide for removed parameters."""
        detector = BreakingChangeDetector()

        old_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a, b)",
            params=["a", "b"],
            required_params=["a", "b"],
            optional_params=[],
        )
        new_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a)",
            params=["a"],
            required_params=["a"],
            optional_params=[],
        )

        guide = detector._generate_migration_guide(old_elem, new_elem)

        assert "Removed parameters" in guide
        assert "b" in guide

    def test_generate_migration_guide_added_params(self):
        """Test migration guide for added parameters."""
        detector = BreakingChangeDetector()

        old_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a)",
            params=["a"],
            required_params=["a"],
            optional_params=[],
        )
        new_elem = ApiElement(
            name="func",
            element_type="function",
            signature="def func(a, b)",
            params=["a", "b"],
            required_params=["a", "b"],
            optional_params=[],
        )

        guide = detector._generate_migration_guide(old_elem, new_elem)

        assert "Added parameters" in guide
        assert "b" in guide

    def test_save_results(self, tmp_path):
        """Test saving results to file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        detector = BreakingChangeDetector()
        result = BreakingChangeResult(files_analyzed=5, has_breaking_changes=True)

        detector._save_results(spec_dir, result)

        output_file = spec_dir / "breaking_changes.json"
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert data["files_analyzed"] == 5
        assert data["has_breaking_changes"] is True

    def test_format_report(self):
        """Test formatting breaking changes as a report."""
        detector = BreakingChangeDetector()
        result = BreakingChangeResult(
            files_analyzed=10,
            breaking_changes=[
                BreakingChange(
                    severity="critical",
                    change_type="removed_function",
                    title="Removed func",
                    description="Function was removed",
                    file="test.py",
                    old_signature="def func()",
                    new_signature=None,
                    migration_guide="Restore the function",
                )
            ],
            should_block=True,
        )

        report = detector.format_report(result)

        assert "BREAKING CHANGE ANALYSIS REPORT" in report
        assert "Files Analyzed: 10" in report
        assert "Removed func" in report
        assert "SHOULD BLOCK DEPLOYMENT" in report


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_breaking_changes_with_files(self):
        """Test detect_breaking_changes convenience function."""
        old_files = {"module.py": "def func(): pass"}
        new_files = {"module.py": "def func(param): pass"}

        result = detect_breaking_changes(old_files=old_files, new_files=new_files)

        assert isinstance(result, BreakingChangeResult)
        assert result.files_analyzed > 0

    def test_has_breaking_changes_returns_true(self):
        """Test has_breaking_changes returns True when changes found."""
        old_code = "def func(): pass"
        new_code = "def func(param): pass"

        has_changes = has_breaking_changes(old_code, new_code)

        assert has_changes is True

    def test_has_breaking_changes_returns_false(self):
        """Test has_breaking_changes returns False when no changes."""
        old_code = "def func(): pass"
        new_code = "def func(): pass"

        has_changes = has_breaking_changes(old_code, new_code)

        assert has_changes is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_analyze_with_no_mode_specified_raises_error(self):
        """Test analyze without mode raises error."""
        detector = BreakingChangeDetector()
        result = detector.analyze()

        # Should add error message
        assert len(result.analysis_errors) > 0

    def test_analyze_empty_code(self):
        """Test analyzing empty code."""
        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change("", "", "test.py")

        assert len(changes) == 0

    def test_analyze_syntax_error_files(self):
        """Test analyzing files with syntax errors."""
        old_code = "def broken(\n"
        new_code = "def also_broken(\n"

        detector = BreakingChangeDetector()
        changes = detector.analyze_file_change(old_code, new_code, "test.py")

        # Should handle gracefully
        assert len(changes) == 0

    def test_class_with_inheritance(self):
        """Test extracting class with base classes."""
        code = '''
class Child(Parent, Mixin):
    """Child class."""
    pass
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        assert len(api_elements) > 0
        child_class = [e for e in api_elements if e.name == "Child"]
        assert len(child_class) > 0
        # Base classes stored in params
        assert "Parent" in child_class[0].params

    def test_function_with_decorators(self):
        """Test extracting function with decorators."""
        code = '''
@decorator
@another_decorator
def decorated_func():
    pass
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        assert len(api_elements) > 0
        assert len(api_elements[0].decorators) == 2

    def test_keyword_only_arguments(self):
        """Test extracting function with keyword-only arguments."""
        code = '''
def func(a, *, b, c=10):
    pass
'''
        detector = BreakingChangeDetector()
        api_elements = detector._extract_api_elements(code)

        assert len(api_elements) > 0
        element = api_elements[0]
        assert "a" in element.params
        assert "b" in element.params
        assert "c" in element.params
        # b is keyword-only required, c is keyword-only optional
        assert "c" in element.optional_params