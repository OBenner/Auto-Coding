#!/usr/bin/env python3
"""
Tests for Scope Inference
=========================

Tests scope inference utilities for Python variables in conflict resolution.

Covers:
- Inferring scope from location strings
- Inferring scope from context descriptions
- Checking scope compatibility
- Getting scope priority levels
- Edge cases and special scenarios
"""

from merge.scope_analyzer import (
    get_scope_priority,
    infer_scope,
    infer_scope_from_context,
    is_same_scope,
)


class TestInferScope:
    """Tests for inferring scope from location strings."""

    def test_infer_scope_module_level(self):
        """Infer global scope from module-level location."""
        scope = infer_scope("my_var", "module")
        assert scope == "global"

    def test_infer_scope_module_with_substring(self):
        """Infer global scope from module: prefix location."""
        scope = infer_scope("my_var", "module:main")
        assert scope == "global"

    def test_infer_scope_class_level(self):
        """Infer class scope from class: prefix location."""
        scope = infer_scope("attribute", "class:MyClass")
        assert scope == "class"

    def test_infer_scope_class_special_method(self):
        """Infer special scope for dunder methods in classes."""
        scope = infer_scope("__init__", "class:MyClass")
        assert scope == "special"

    def test_infer_scope_class_special_attribute(self):
        """Infer special scope for dunder attributes."""
        scope = infer_scope("__version__", "class:MyClass")
        assert scope == "special"

    def test_infer_scope_function_level(self):
        """Infer local scope from function: prefix location."""
        scope = infer_scope("local_var", "function:foo")
        assert scope == "local"

    def test_infer_scope_method_level(self):
        """Infer local scope from method: prefix location."""
        scope = infer_scope("method_var", "method:MyClass.my_method")
        assert scope == "local"

    def test_infer_scope_block_level(self):
        """Infer block scope from block: prefix location."""
        scope = infer_scope("loop_var", "block:for_loop")
        assert scope == "block"

    def test_infer_scope_empty_location(self):
        """Default to global scope when location is empty."""
        scope = infer_scope("my_var", "")
        assert scope == "global"

    def test_infer_scope_none_location(self):
        """Default to global scope when location is None."""
        scope = infer_scope("my_var", None)
        assert scope == "global"

    def test_infer_scope_unknown_location(self):
        """Default to local scope for unknown location formats."""
        scope = infer_scope("my_var", "unknown:format")
        assert scope == "local"


class TestInferScopeFromContext:
    """Tests for inferring scope from context descriptions."""

    def test_infer_from_context_module(self):
        """Infer global scope from 'module' context."""
        scope = infer_scope_from_context("my_var", "at module level")
        assert scope == "global"

    def test_infer_from_context_global(self):
        """Infer global scope from 'global' context."""
        scope = infer_scope_from_context("my_var", "global variable")
        assert scope == "global"

    def test_infer_from_context_class_only(self):
        """Infer class scope when context mentions 'class' but not 'function'."""
        scope = infer_scope_from_context("attr", "in class MyClass")
        assert scope == "class"

    def test_infer_from_context_function(self):
        """Infer local scope from 'function' context."""
        scope = infer_scope_from_context("local_var", "in function foo")
        assert scope == "local"

    def test_infer_from_context_method(self):
        """Infer local scope from 'method' context."""
        scope = infer_scope_from_context("method_var", "in method bar")
        assert scope == "local"

    def test_infer_from_context_block(self):
        """Infer block scope from 'block' context."""
        scope = infer_scope_from_context("block_var", "inside block")
        assert scope == "block"

    def test_infer_from_context_loop(self):
        """Infer block scope from 'loop' context."""
        scope = infer_scope_from_context("i", "in for loop")
        assert scope == "block"

    def test_infer_from_context_class_and_function(self):
        """Infer local scope when context mentions both class and function."""
        # Methods are functions, so "function" should take precedence
        scope = infer_scope_from_context(
            "method_var", "in class MyClass and function foo"
        )
        assert scope == "local"

    def test_infer_from_context_unknown(self):
        """Default to local scope for unknown context."""
        scope = infer_scope_from_context("my_var", "somewhere in code")
        assert scope == "local"

    def test_infer_from_context_case_insensitive(self):
        """Context matching is case-insensitive."""
        scope = infer_scope_from_context("my_var", "At MODULE Level")
        assert scope == "global"

        scope = infer_scope_from_context("my_var", "FUNCTION scope")
        assert scope == "local"


class TestIsSameScope:
    """Tests for checking scope compatibility."""

    def test_same_scope_identical(self):
        """Identical scopes are compatible."""
        assert is_same_scope("local", "local") is True
        assert is_same_scope("global", "global") is True
        assert is_same_scope("class", "class") is True

    def test_same_scope_module_global(self):
        """Module and global scopes are equivalent."""
        assert is_same_scope("module", "global") is True
        assert is_same_scope("global", "module") is True

    def test_same_scope_class_special(self):
        """Class and special method scopes are compatible."""
        assert is_same_scope("class", "special") is True
        assert is_same_scope("special", "class") is True

    def test_same_scope_different_scopes(self):
        """Different scopes generally don't conflict."""
        # Local vs global
        assert is_same_scope("local", "global") is True
        # Class vs local
        assert is_same_scope("class", "local") is True
        # Block vs local
        assert is_same_scope("block", "local") is True
        # Module vs local
        assert is_same_scope("module", "local") is True

    def test_same_scope_symmetric(self):
        """Compatibility check is symmetric."""
        assert is_same_scope("local", "class") == is_same_scope("class", "local")
        assert is_same_scope("block", "global") == is_same_scope("global", "block")


class TestGetScopePriority:
    """Tests for getting scope priority levels."""

    def test_priority_special(self):
        """Special methods have highest priority (5)."""
        assert get_scope_priority("special") == 5

    def test_priority_local(self):
        """Local variables have high priority (4)."""
        assert get_scope_priority("local") == 4

    def test_priority_parameter(self):
        """Parameters have same priority as local (4)."""
        assert get_scope_priority("parameter") == 4

    def test_priority_block(self):
        """Block scope has medium priority (3)."""
        assert get_scope_priority("block") == 3

    def test_priority_class(self):
        """Class scope has lower priority (2)."""
        assert get_scope_priority("class") == 2

    def test_priority_module(self):
        """Module scope has low priority (1)."""
        assert get_scope_priority("module") == 1

    def test_priority_global(self):
        """Global scope has low priority (1), same as module."""
        assert get_scope_priority("global") == 1

    def test_priority_unknown(self):
        """Unknown scopes have priority 0."""
        assert get_scope_priority("unknown") == 0
        assert get_scope_priority("") == 0

    def test_priority_hierarchical(self):
        """Priority hierarchy: special > local/parameter > block > class > module/global."""
        assert get_scope_priority("special") > get_scope_priority("local")
        assert get_scope_priority("local") > get_scope_priority("block")
        assert get_scope_priority("block") > get_scope_priority("class")
        assert get_scope_priority("class") > get_scope_priority("module")
        assert get_scope_priority("module") == get_scope_priority("global")


class TestScopeInferenceIntegration:
    """Integration tests for scope inference scenarios."""

    def test_module_level_variable(self):
        """Complete flow for module-level variable."""
        var_name = "CONFIG"
        location = "module"

        scope = infer_scope(var_name, location)
        assert scope == "global"

        priority = get_scope_priority(scope)
        assert priority == 1

    def test_class_attribute_scenario(self):
        """Complete flow for class attribute."""
        var_name = "counter"
        location = "class:Counter"

        scope = infer_scope(var_name, location)
        assert scope == "class"

        priority = get_scope_priority(scope)
        assert priority == 2

    def test_special_method_scenario(self):
        """Complete flow for special method."""
        var_name = "__init__"
        location = "class:MyClass"

        scope = infer_scope(var_name, location)
        assert scope == "special"

        priority = get_scope_priority(scope)
        assert priority == 5

        # Should be compatible with class scope
        assert is_same_scope(scope, "class") is True

    def test_function_local_scenario(self):
        """Complete flow for function-local variable."""
        var_name = "temp"
        location = "function:process_data"

        scope = infer_scope(var_name, location)
        assert scope == "local"

        priority = get_scope_priority(scope)
        assert priority == 4

    def test_block_variable_scenario(self):
        """Complete flow for block-scoped variable."""
        var_name = "i"
        location = "block:for_loop"

        scope = infer_scope(var_name, location)
        assert scope == "block"

        priority = get_scope_priority(scope)
        assert priority == 3

    def test_context_based_inference_scenario(self):
        """Complete flow using context-based inference."""
        var_name = "data"
        context = "in function process_data"

        scope = infer_scope_from_context(var_name, context)
        assert scope == "local"

        priority = get_scope_priority(scope)
        assert priority == 4

    def test_scope_compatibility_in_merge(self):
        """Test scope compatibility for merge scenarios."""
        # Same scope - compatible
        assert is_same_scope("local", "local") is True

        # Different scopes - compatible (no conflict)
        assert is_same_scope("local", "global") is True

        # Module/Global equivalence - compatible
        assert is_same_scope("module", "global") is True
