"""
Category Mapping Utilities
===========================

Shared utilities for mapping AI-generated category names to valid ReviewCategory enum values.

This module provides a centralized category mapping system used across all PR reviewers
(orchestrator, follow-up, parallel) to ensure consistent category normalization.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, cast

# Import ReviewCategory with robust fallback for different import contexts
# This handles both normal package imports and pytest's direct imports
def _get_review_category():
    """Lazy import ReviewCategory to avoid pytest collection errors."""
    if TYPE_CHECKING:
        from ..models import ReviewCategory
        return ReviewCategory

    # Try relative import first (normal package usage)
    try:
        from ..models import ReviewCategory
        return ReviewCategory
    except (ImportError, ValueError, SystemError, TypeError):
        # Fallback to absolute import for pytest/direct import scenarios
        # During pytest collection, the package structure may not be fully initialized
        try:
            # Try absolute import from project root
            if 'runners.github.models' in sys.modules:
                return sys.modules['runners.github.models'].ReviewCategory

            from runners.github.models import ReviewCategory
            return ReviewCategory
        except ImportError:
            # If we really can't import, raise a helpful error
            raise ImportError(
                "Could not import ReviewCategory. "
                "Ensure runners.github.models is in the Python path."
            )


# Get ReviewCategory at module level (lazy import)
# This will be executed on first access, not during module import
def _get_category_mapping():
    """Build category mapping with lazy import of ReviewCategory."""
    ReviewCategory = _get_review_category()

    return {
        # Direct matches (already valid ReviewCategory values)
        "security": ReviewCategory.SECURITY,
        "quality": ReviewCategory.QUALITY,
        "style": ReviewCategory.STYLE,
        "test": ReviewCategory.TEST,
        "docs": ReviewCategory.DOCS,
        "pattern": ReviewCategory.PATTERN,
        "performance": ReviewCategory.PERFORMANCE,
        "redundancy": ReviewCategory.REDUNDANCY,
        "verification_failed": ReviewCategory.VERIFICATION_FAILED,
        # AI-generated alternatives that need mapping
        "logic": ReviewCategory.QUALITY,  # Logic errors → quality
        "codebase_fit": ReviewCategory.PATTERN,  # Codebase fit → pattern adherence
        "correctness": ReviewCategory.QUALITY,  # Code correctness → quality
        "consistency": ReviewCategory.PATTERN,  # Code consistency → pattern adherence
        "testing": ReviewCategory.TEST,  # Testing → test
        "documentation": ReviewCategory.DOCS,  # Documentation → docs
        "bug": ReviewCategory.QUALITY,  # Bug → quality
        "error_handling": ReviewCategory.QUALITY,  # Error handling → quality
        "maintainability": ReviewCategory.QUALITY,  # Maintainability → quality
        "readability": ReviewCategory.STYLE,  # Readability → style
        "best_practices": ReviewCategory.PATTERN,  # Best practices → pattern (hyphen normalized to underscore)
        "architecture": ReviewCategory.PATTERN,  # Architecture → pattern
        "complexity": ReviewCategory.QUALITY,  # Complexity → quality
        "dead_code": ReviewCategory.REDUNDANCY,  # Dead code → redundancy
        "unused": ReviewCategory.REDUNDANCY,  # Unused code → redundancy
        # Follow-up specific mappings
        "regression": ReviewCategory.QUALITY,  # Regression → quality
        "incomplete_fix": ReviewCategory.QUALITY,  # Incomplete fix → quality
    }


# Module-level cache for category mapping
_CATEGORY_MAPPING = None


def _get_mapping():
    """Get or initialize the category mapping cache."""
    global _CATEGORY_MAPPING
    if _CATEGORY_MAPPING is None:
        _CATEGORY_MAPPING = _get_category_mapping()
    return _CATEGORY_MAPPING


# Export the mapping as a dict-like interface
# Note: This is now accessed via function, not as a module-level constant
# to defer import until first access


def map_category(raw_category: str):
    """
    Map an AI-generated category string to a valid ReviewCategory enum.

    Args:
        raw_category: Raw category string from AI (e.g., "best-practices", "logic", "security")

    Returns:
        ReviewCategory: Normalized category enum value. Defaults to QUALITY if unknown.

    Examples:
        >>> map_category("security")
        ReviewCategory.SECURITY
        >>> map_category("best-practices")
        ReviewCategory.PATTERN
        >>> map_category("unknown-category")
        ReviewCategory.QUALITY
    """
    # Get the mapping (triggers lazy import on first call)
    mapping = _get_mapping()

    # Normalize: lowercase, strip whitespace, replace hyphens with underscores
    normalized = raw_category.lower().strip().replace("-", "_")

    # Look up in mapping, default to QUALITY for unknown categories
    return mapping.get(normalized, _get_review_category().QUALITY)
