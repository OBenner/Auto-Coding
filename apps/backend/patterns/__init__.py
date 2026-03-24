"""
Language Patterns Module
========================

Idiomatic code patterns for different programming languages.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Registry mapping language names to (module_name, export_name) pairs.
# Covers all languages supported by the pattern library generator.
_LANGUAGE_REGISTRY: dict[str, tuple[str, str]] = {
    "go": ("go_patterns", "GO_PATTERNS"),
    "php": ("php_patterns", "PHP_PATTERNS"),
    "ruby": ("ruby_patterns", "RUBY_PATTERNS"),
    "rust": ("rust_patterns", "RUST_PATTERNS"),
    "python": ("python_patterns", "PYTHON_PATTERNS"),
    "javascript": ("javascript_patterns", "JAVASCRIPT_PATTERNS"),
    "typescript": ("typescript_patterns", "TYPESCRIPT_PATTERNS"),
    "java": ("java_patterns", "JAVA_PATTERNS"),
    "csharp": ("csharp_patterns", "CSHARP_PATTERNS"),
    "cpp": ("cpp_patterns", "CPP_PATTERNS"),
}


def load_language_patterns(language: str) -> dict[str, Any] | None:
    """
    Load language-specific code patterns.

    Dynamically imports the corresponding pattern module for the given language.
    Returns None if no pattern module exists for the language (e.g., when the
    auto-generated library has not been created yet).

    Args:
        language: Language name (e.g., 'go', 'python', 'javascript')

    Returns:
        Dictionary of patterns for the language, or None if not found
    """
    language = language.lower()

    entry = _LANGUAGE_REGISTRY.get(language)
    if entry is None:
        return None

    module_name, export_name = entry
    try:
        import importlib

        mod = importlib.import_module(f".{module_name}", package=__name__)
        return getattr(mod, export_name, None)
    except ImportError as e:
        logger.debug(
            "Pattern module '%s.%s' not available: %s", __name__, module_name, e
        )
        return None


__all__ = ["load_language_patterns"]
