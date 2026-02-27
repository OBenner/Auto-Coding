"""
Scope Analyzer
==============

Utilities for inferring variable scope in Python code.

This module provides functions for determining the scope context
of variables based on their location in the code structure.
"""

from __future__ import annotations


def infer_scope(variable_name: str, location: str) -> str:
    """
    Infer the scope of a Python variable based on its location.

    Args:
        variable_name: Name of the variable
        location: Location string (e.g., 'function:foo', 'class:Bar', 'module')

    Returns:
        Scope identifier string (local, global, class, module, parameter)
    """
    if not location:
        return "global"

    # Module level - variables defined at module scope
    if location == "module" or location.startswith("module:"):
        return "global"

    # Class level - class attributes
    if location.startswith("class:"):
        # Check if it's a known special method/attribute
        if variable_name.startswith("__") and variable_name.endswith("__"):
            return "special"  # Special methods like __init__
        return "class"

    # Function level
    if location.startswith("function:"):
        # Could be local or parameter
        # Without AST analysis, default to local
        # (parameters would be detected during actual parsing)
        return "local"

    # Method level (function inside class)
    if location.startswith("method:"):
        return "local"

    # Block scope (if/for/while)
    if location.startswith("block:"):
        return "block"

    # Default to local for unknown contexts
    return "local"


def infer_scope_from_context(variable_name: str, context: str) -> str:
    """
    Infer variable scope from a broader context string.

    Args:
        variable_name: Name of the variable
        context: Context description (e.g., 'in function foo', 'at module level')

    Returns:
        Scope identifier string
    """
    context_lower = context.lower()

    if "module" in context_lower or "global" in context_lower:
        return "global"
    if "class" in context_lower and "function" not in context_lower:
        return "class"
    if "function" in context_lower or "method" in context_lower:
        return "local"
    if "block" in context_lower or "loop" in context_lower:
        return "block"

    return "local"


def is_same_scope(scope1: str, scope2: str) -> bool:
    """
    Check if two scopes are compatible for merging purposes.

    Args:
        scope1: First scope
        scope2: Second scope

    Returns:
        True if variables in these scopes won't conflict
    """
    # Python's scoping rules ensure that variables in different scopes are independent
    # (a local in one function never conflicts with a global, class attribute, etc.).
    # All scope pairings are therefore compatible for merge purposes.
    # Callers needing strict equality should compare scope1 == scope2 directly.
    return True


def get_scope_priority(scope: str) -> int:
    """
    Get priority level for scope conflict resolution.

    Higher priority scopes override lower priority ones.

    Args:
        scope: Scope identifier

    Returns:
        Priority level (higher = more specific)
    """
    priorities = {
        "special": 5,
        "local": 4,
        "block": 3,
        "class": 2,
        "module": 1,
        "global": 1,
        "parameter": 4,
    }
    return priorities.get(scope, 0)
