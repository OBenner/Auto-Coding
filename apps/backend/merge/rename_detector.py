"""
Rename Detector
==============

AST-based rename detection for semantic merge analysis.

This module provides functions for detecting when variables or functions
have been renamed versus replaced, using Abstract Syntax Tree (AST)
similarity analysis.
"""

from __future__ import annotations

import ast
from typing import Any


def detect_rename(code_before: str, code_after: str) -> bool:
    """
    Detect if code_after represents a renamed version of code_before.

    Uses AST analysis to determine if the two code snippets have
    identical structure except for identifier names.

    Args:
        code_before: Original code snippet
        code_after: Modified code snippet

    Returns:
        True if the snippets are structurally identical except for renames
    """
    try:
        # Parse both code snippets into ASTs
        ast_before = ast.parse(code_before)
        ast_after = ast.parse(code_after)
    except (SyntaxError, ValueError):
        # If either snippet can't be parsed, they can't be renames
        return False

    # Compare AST structures
    return _compare_ast_nodes(ast_before, ast_after, check_names=False)


def _compare_ast_nodes(
    node1: ast.AST | None,
    node2: ast.AST | None,
    check_names: bool = True,
) -> bool:
    """
    Compare two AST nodes for structural similarity.

    Args:
        node1: First AST node
        node2: Second AST node
        check_names: If True, require identifier names to match.
                    If False, ignore name differences (for rename detection).

    Returns:
        True if nodes have matching structure
    """
    # Handle None cases
    if node1 is None and node2 is None:
        return True
    if node1 is None or node2 is None:
        return False

    # Check node types match
    if type(node1) != type(node2):
        return False

    # For Name nodes, check based on check_names flag
    if isinstance(node1, ast.Name):
        if check_names:
            return node1.id == node2.id
        # If not checking names, any Name matches any Name
        return isinstance(node2, ast.Name)

    # For Constant/Num/Str/etc., compare values
    if isinstance(node1, (ast.Constant, ast.Num, ast.Str, ast.Bytes)):
        if isinstance(node1, ast.Constant):
            return node1.value == node2.value
        if isinstance(node1, ast.Num):
            return node1.n == node2.n  # type: ignore
        if isinstance(node1, ast.Str):
            return node1.s == node2.s  # type: ignore
        if isinstance(node1, ast.Bytes):
            return node1.s == node2.s  # type: ignore

    # Compare all child fields recursively
    for field in _get_ast_fields(node1):
        if not hasattr(node2, field):
            return False

        value1 = getattr(node1, field)
        value2 = getattr(node2, field)

        # Handle lists of nodes (e.g., function body statements)
        if isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                return False
            for v1, v2 in zip(value1, value2):
                if isinstance(v1, ast.AST) and isinstance(v2, ast.AST):
                    if not _compare_ast_nodes(v1, v2, check_names):
                        return False
                elif v1 != v2:
                    return False
        # Handle single AST nodes
        elif isinstance(value1, ast.AST) and isinstance(value2, ast.AST):
            if not _compare_ast_nodes(value1, value2, check_names):
                return False
        # Handle simple values
        elif value1 != value2:
            return False

    return True


def _get_ast_fields(node: ast.AST) -> list[str]:
    """
    Get relevant AST fields for comparison, excluding metadata.

    Args:
        node: AST node

    Returns:
        List of field names to compare
    """
    # Get all fields
    all_fields = node._fields if hasattr(node, "_fields") else []

    # Skip fields that are typically metadata
    skip_fields = {"ctx", "type_comment", "end_lineno", "end_col_offset"}

    return [f for f in all_fields if f not in skip_fields]


def extract_renamed_identifiers(code_before: str, code_after: str) -> dict[str, str] | None:
    """
    Extract renamed identifier mappings between two code snippets.

    Args:
        code_before: Original code snippet
        code_after: Modified code snippet

    Returns:
        Dictionary mapping old names to new names if a rename is detected,
        None if snippets are not structurally identical
    """
    if not detect_rename(code_before, code_after):
        return None

    try:
        ast_before = ast.parse(code_before)
        ast_after = ast.parse(code_after)
    except (SyntaxError, ValueError):
        return None

    # Extract name pairs
    name_pairs: list[tuple[str, str]] = []
    _extract_name_pairs(ast_before, ast_after, name_pairs)

    # Remove duplicates and create mapping
    mapping: dict[str, str] = {}
    for old_name, new_name in name_pairs:
        if old_name != new_name:
            # If we've seen this old_name mapped to a different new_name,
            # it's not a simple rename (multiple renames in one snippet)
            if old_name in mapping and mapping[old_name] != new_name:
                return None
            mapping[old_name] = new_name

    return mapping if mapping else None


def _extract_name_pairs(
    node1: ast.AST,
    node2: ast.AST,
    pairs: list[tuple[str, str]],
) -> None:
    """
    Recursively extract identifier name pairs from two ASTs.

    Args:
        node1: First AST node
        node2: Second AST node (must have same structure)
        pairs: List to populate with (old_name, new_name) tuples
    """
    if not isinstance(node1, ast.AST) or not isinstance(node2, ast.AST):
        return

    # Extract Name node pairs
    if isinstance(node1, ast.Name) and isinstance(node2, ast.Name):
        pairs.append((node1.id, node2.id))
        return

    # Recurse into matching fields
    for field in _get_ast_fields(node1):
        if not hasattr(node2, field):
            continue

        value1 = getattr(node1, field)
        value2 = getattr(node2, field)

        if isinstance(value1, list) and isinstance(value2, list):
            for v1, v2 in zip(value1, value2):
                if isinstance(v1, ast.AST) and isinstance(v2, ast.AST):
                    _extract_name_pairs(v1, v2, pairs)
        elif isinstance(value1, ast.AST) and isinstance(value2, ast.AST):
            _extract_name_pairs(value1, value2, pairs)


def is_function_rename(code_before: str, code_after: str) -> bool:
    """
    Detect if code_after represents a renamed function definition.

    Args:
        code_before: Original function definition
        code_after: Modified function definition

    Returns:
        True if it's a function name change only
    """
    try:
        ast_before = ast.parse(code_before)
        ast_after = ast.parse(code_after)
    except (SyntaxError, ValueError):
        return False

    # Check if both are FunctionDef nodes
    if not (
        isinstance(ast_before.body[0], ast.FunctionDef)
        and isinstance(ast_after.body[0], ast.FunctionDef)
    ):
        return False

    func_before = ast_before.body[0]
    func_after = ast_after.body[0]

    # Compare everything except the name
    # Create copies with same name for comparison
    kwargs_before = {
        "name": "temp",
        "args": func_before.args,
        "body": func_before.body,
        "decorator_list": func_before.decorator_list,
        "returns": func_before.returns,
    }
    kwargs_after = {
        "name": "temp",
        "args": func_after.args,
        "body": func_after.body,
        "decorator_list": func_after.decorator_list,
        "returns": func_after.returns,
    }

    # Add optional fields if present
    if hasattr(func_before, "type_comment"):
        kwargs_before["type_comment"] = func_before.type_comment
    if hasattr(func_after, "type_comment"):
        kwargs_after["type_comment"] = func_after.type_comment
    if hasattr(func_before, "type_params"):
        kwargs_before["type_params"] = func_before.type_params
    if hasattr(func_after, "type_params"):
        kwargs_after["type_params"] = func_after.type_params

    func_before_copy = ast.FunctionDef(**kwargs_before)
    func_after_copy = ast.FunctionDef(**kwargs_after)

    return _compare_ast_nodes(func_before_copy, func_after_copy, check_names=True)


def get_similarity_score(code_before: str, code_after: str) -> float:
    """
    Calculate AST similarity score between two code snippets.

    Args:
        code_before: First code snippet
        code_after: Second code snippet

    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        ast_before = ast.parse(code_before)
        ast_after = ast.parse(code_after)
    except (SyntaxError, ValueError):
        return 0.0

    # Count total nodes in both ASTs
    total_nodes = _count_ast_nodes(ast_before) + _count_ast_nodes(ast_after)
    if total_nodes == 0:
        return 1.0

    # Count matching nodes (ignoring names)
    matching_nodes = _count_matching_nodes(ast_before, ast_after)

    # Calculate similarity
    return (2.0 * matching_nodes) / total_nodes if total_nodes > 0 else 0.0


def _count_ast_nodes(node: ast.AST | Any) -> int:
    """
    Recursively count AST nodes.

    Args:
        node: AST node or other value

    Returns:
        Number of AST nodes in subtree
    """
    if not isinstance(node, ast.AST):
        return 0

    count = 1
    for field in _get_ast_fields(node):
        value = getattr(node, field, None)
        if isinstance(value, list):
            count += sum(_count_ast_nodes(v) for v in value)
        elif isinstance(value, ast.AST):
            count += _count_ast_nodes(value)

    return count


def _count_matching_nodes(node1: ast.AST | Any, node2: ast.AST | Any) -> int:
    """
    Count matching nodes between two ASTs (ignoring identifier names).

    Args:
        node1: First AST node
        node2: Second AST node

    Returns:
        Number of structurally matching nodes
    """
    if not isinstance(node1, ast.AST) or not isinstance(node2, ast.AST):
        return 0

    if type(node1) != type(node2):
        return 0

    # For Name nodes, any names match
    if isinstance(node1, ast.Name):
        return 1

    # Count this node as matching
    count = 1

    # Recursively count matching children
    for field in _get_ast_fields(node1):
        if not hasattr(node2, field):
            continue

        value1 = getattr(node1, field, None)
        value2 = getattr(node2, field, None)

        if isinstance(value1, list) and isinstance(value2, list):
            for v1, v2 in zip(value1, value2):
                count += _count_matching_nodes(v1, v2)
        elif isinstance(value1, ast.AST) and isinstance(value2, ast.AST):
            count += _count_matching_nodes(value1, value2)

    return count
