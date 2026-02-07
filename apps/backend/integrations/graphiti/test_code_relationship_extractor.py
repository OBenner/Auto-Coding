#!/usr/bin/env python3
"""
Test Code Relationship Extractor
=================================

Tests for the CodeRelationshipExtractor module.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from integrations.graphiti.code_relationship_extractor import (
    CodeRelationshipExtractor,
    FunctionCall,
    ImportRelationship,
    InheritanceRelationship,
)


class TestFunctionCalls:
    """Test function call detection."""

    def test_function_calls(self):
        """Test that function calls are detected correctly."""
        source = """
def caller_function():
    callee_function()
    another_function()

def callee_function():
    pass

def another_function():
    pass
"""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        # Should find 2 function calls
        assert len(result["calls"]) == 2

        # Check first call
        calls = result["calls"]
        assert calls[0]["caller"] == "caller_function"
        assert calls[0]["callee"] in ["callee_function", "another_function"]
        assert calls[0]["call_type"] == "function"

        # Check second call
        assert calls[1]["caller"] == "caller_function"
        assert calls[1]["callee"] in ["callee_function", "another_function"]
        assert calls[1]["call_type"] == "function"

        # Ensure both callees are captured
        callees = {call["callee"] for call in calls}
        assert callees == {"callee_function", "another_function"}

    def test_method_calls(self):
        """Test that method calls are detected correctly."""
        source = """
class MyClass:
    def method_one(self):
        self.method_two()

    def method_two(self):
        pass
"""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        # Should find 1 method call
        assert len(result["calls"]) == 1

        # Check method call
        call = result["calls"][0]
        assert call["caller"] == "MyClass.method_one"
        assert call["callee"] == "method_two"
        assert call["call_type"] == "method"

    def test_nested_function_calls(self):
        """Test that nested function calls are detected."""
        source = """
def outer():
    def inner():
        helper()
    inner()

def helper():
    pass
"""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        # Should find calls from both outer and inner
        assert len(result["calls"]) >= 1

        # Check that calls are tracked
        callers = {call["caller"] for call in result["calls"]}
        assert "outer" in callers

    def test_imported_function_calls(self):
        """Test that calls to imported functions track module info."""
        source = """
from pathlib import Path

def my_function():
    Path('test.txt')
"""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        # Should find the call to Path
        assert len(result["calls"]) == 1

        call = result["calls"][0]
        assert call["caller"] == "my_function"
        assert call["callee"] == "Path"
        assert call["module"] == "pathlib"


class TestImports:
    """Test import detection."""

    def test_imports_inheritance(self):
        """Test that imports and inheritance are detected correctly."""
        source = """
import os
from pathlib import Path

class Child(Path):
    pass

class Another:
    def method(self):
        os.path.join('a', 'b')
"""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        # Check imports
        assert len(result["imports"]) == 2

        import_modules = {imp["module"] for imp in result["imports"]}
        assert "os" in import_modules
        assert "pathlib" in import_modules

        # Check inheritance
        assert len(result["inheritance"]) == 1

        inh = result["inheritance"][0]
        assert inh["child"] == "Child"
        assert inh["parent"] == "Path"
        assert inh["parent_module"] == "pathlib"


class TestEntities:
    """Test entity collection."""

    def test_entity_collection(self):
        """Test that all entities are collected."""
        source = """
def standalone_function():
    pass

class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
"""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        # Check entities
        entities = set(result["entities"])
        assert "standalone_function" in entities
        assert "MyClass" in entities
        assert "MyClass.method_one" in entities
        assert "MyClass.method_two" in entities


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file(self):
        """Test analyzing an empty file."""
        source = ""
        extractor = CodeRelationshipExtractor()
        result = extractor.analyze_source(source)

        assert result["calls"] == []
        assert result["imports"] == []
        assert result["inheritance"] == []
        assert result["total_relationships"] == 0

    def test_syntax_error(self):
        """Test that syntax errors are handled gracefully."""
        source = "def broken("
        extractor = CodeRelationshipExtractor()

        with pytest.raises(ValueError, match="Syntax error"):
            extractor.analyze_source(source)

    def test_file_not_found(self):
        """Test that missing files are handled gracefully."""
        extractor = CodeRelationshipExtractor()

        with pytest.raises(FileNotFoundError):
            extractor.analyze_file("nonexistent_file.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
