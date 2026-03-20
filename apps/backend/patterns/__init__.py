"""
Language Patterns Module
========================

Idiomatic code patterns for different programming languages.
"""

from typing import Dict, Any, Optional


def load_language_patterns(language: str) -> Optional[Dict[str, Any]]:
    """
    Load language-specific code patterns.

    Args:
        language: Language name (e.g., 'go', 'php', 'ruby', 'rust')

    Returns:
        Dictionary of patterns for the language, or None if not found
    """
    language = language.lower()

    try:
        if language == "go":
            from .go_patterns import GO_PATTERNS
            return GO_PATTERNS
        elif language == "php":
            from .php_patterns import PHP_PATTERNS
            return PHP_PATTERNS
        elif language == "ruby":
            from .ruby_patterns import RUBY_PATTERNS
            return RUBY_PATTERNS
        elif language == "rust":
            from .rust_patterns import RUST_PATTERNS
            return RUST_PATTERNS
        else:
            return None
    except ImportError:
        return None


__all__ = ["load_language_patterns"]
