"""
Signature Parser
================

Parser for extracting function signature information from Python code.

This module provides functions for parsing function signatures to extract
the function name, parameters, and return type information for semantic analysis.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class ParameterInfo(NamedTuple):
    """
    Information about a single parameter.

    Attributes:
        name: Parameter name
        type_hint: Type annotation if present (e.g., "int", "str")
        has_default: Whether parameter has a default value
        is_vararg: True for *args
        is_kwarg: True for **kwargs
    """

    name: str
    type_hint: str = ""
    has_default: bool = False
    is_vararg: bool = False
    is_kwarg: bool = False


def parse_function_signature(signature: str) -> FunctionSignature:
    """
    Parse a Python function signature into structured components.

    Args:
        signature: Function signature string (e.g., "def foo(x: int, y: str) -> bool:")

    Returns:
        FunctionSignature object with name, params (names only), and return_type

    Raises:
        ValueError: If signature is invalid or cannot be parsed

    Examples:
        >>> sig = parse_function_signature('def foo(x: int, y: str) -> bool:')
        >>> sig.name
        'foo'
        >>> sig.params
        ['x', 'y']
        >>> sig.return_type
        'bool'
    """
    if not signature or not isinstance(signature, str):
        raise ValueError("Signature must be a non-empty string")

    # Strip leading/trailing whitespace and normalise runs of whitespace to a
    # single space so that the patterns below do not need adjacent \s* groups
    # (which can exhibit polynomial backtracking on non-matching input).
    signature = re.sub(r"\s+", " ", signature.strip())

    # Match the function signature pattern.
    # Supports: async def, regular def, with type hints, with return types.
    # The trailing colon is required for syntactically valid Python signatures;
    # we also accept signatures without a colon (e.g., extracted from diffs).
    # With whitespace pre-normalised, each space slot uses ' ?' (at most one).
    pattern = (
        r"^(async )?"  # Optional async keyword
        r"def ([a-zA-Z_]\w*) ?"  # def + function name
        r"\(([^)]*)\)"  # Parameters in parens
        r"(?: -> ([^:(]+))?"  # Optional return type
        r" ?:$"  # Trailing colon
    )

    match = re.match(pattern, signature)

    # Fall back to accepting signatures without a trailing colon (e.g., from diffs)
    if not match:
        pattern_no_colon = (
            r"^(async )?"
            r"def ([a-zA-Z_]\w*) ?"
            r"\(([^)]*)\)"
            r"(?: -> ([^:(]+))?"
            r" ?$"
        )
        match = re.match(pattern_no_colon, signature)

    if not match:
        raise ValueError(
            f"Invalid function signature format: '{signature}'. "
            "Expected format: 'def function_name(params) -> return_type:'"
        )

    # Extract components
    func_name = match.group(2)
    params_str = match.group(3) or ""
    return_type = (match.group(4) or "").strip() if match.group(4) else ""

    # Parse parameter names (extract just the names, ignore type hints and defaults)
    param_names = _extract_parameter_names(params_str)

    return FunctionSignature(
        name=func_name,
        params=param_names,
        return_type=return_type,
    )


def _extract_parameter_names(params_str: str) -> list[str]:
    """
    Extract parameter names from a parameter string.

    Args:
        params_str: Parameter list string (e.g., "x: int, y: str = None, *args")

    Returns:
        List of parameter names (e.g., ["x", "y", "args"])
    """
    if not params_str or params_str.strip() == "":
        return []

    param_names = []

    # Split by comma, but handle nested brackets/generics
    # Simple approach: split by comma and clean up each parameter
    raw_params = _split_parameters(params_str)

    for param in raw_params:
        param = param.strip()
        if not param:
            continue

        # Handle *args and **kwargs
        if param.startswith("*"):
            # Extract name after * or **
            name = param.lstrip("*").split("=")[0].split(":")[0].strip()
            if name:
                param_names.append(name)
            continue

        # Extract parameter name (first word before : or =)
        # This handles: "x", "x: int", "x = None", "x: int = None"
        name = param.split(":")[0].split("=")[0].strip()

        if name and name not in param_names:  # Avoid duplicates
            param_names.append(name)

    return param_names


def _split_parameters(params_str: str) -> list[str]:
    """
    Split parameter string by commas, handling nested brackets.

    Args:
        params_str: Raw parameter string

    Returns:
        List of individual parameter strings
    """
    params = []
    current = []
    depth = 0  # Track bracket/paren depth for generics like Dict[str, int]

    for char in params_str:
        if char in "[{(":
            depth += 1
            current.append(char)
        elif char in "]})":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            # Top-level comma - split here
            params.append("".join(current))
            current = []
        else:
            current.append(char)

    # Add the last parameter
    if current:
        params.append("".join(current))

    return [p.strip() for p in params if p.strip()]


def get_signature_fingerprint(signature: str) -> str:
    """
    Generate a unique fingerprint for a function signature.

    The fingerprint encodes function name, parameter count, and whether
    the signature uses *args or **kwargs to avoid false matches between
    signatures that differ only in variadic parameters.

    Args:
        signature: Function signature string

    Returns:
        Fingerprint string for comparison

    Examples:
        >>> get_signature_fingerprint('def foo(x, y):')
        'foo:2:v0:kw0'
        >>> get_signature_fingerprint('def bar(*args, **kwargs):')
        'bar:2:v1:kw1'
    """
    sig = parse_function_signature(signature)
    param_count = len(sig.params)

    # Detect *args / **kwargs from the raw signature to encode in fingerprint
    raw_params = _split_parameters(
        re.search(r"\(([^)]*)\)", signature, re.DOTALL).group(1)
        if re.search(r"\(([^)]*)\)", signature, re.DOTALL)
        else ""
    )
    has_vararg = int(
        any(
            p.strip().startswith("*") and not p.strip().startswith("**")
            for p in raw_params
        )
    )
    has_kwarg = int(any(p.strip().startswith("**") for p in raw_params))

    return f"{sig.name}:{param_count}:v{has_vararg}:kw{has_kwarg}"


def signatures_match(sig1: str, sig2: str) -> bool:
    """
    Check if two function signatures match semantically.

    Two signatures match if they have the same name and parameter count.
    Return types and type hints are not considered for matching.

    Args:
        sig1: First function signature
        sig2: Second function signature

    Returns:
        True if signatures match, False otherwise
    """
    try:
        fp1 = get_signature_fingerprint(sig1)
        fp2 = get_signature_fingerprint(sig2)
        return fp1 == fp2
    except ValueError:
        # If either signature is invalid, they don't match
        return False


# Import at end to avoid circular dependency
from .types import FunctionSignature
