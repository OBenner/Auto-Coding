#!/usr/bin/env python3
"""
Patterns and Gotchas Management
================================

Functions for managing code patterns and gotchas (pitfalls to avoid).
"""

import logging
import re
from pathlib import Path

from .graphiti_helpers import get_graphiti_memory, is_graphiti_memory_enabled, run_async
from .paths import get_memory_dir

logger = logging.getLogger(__name__)

# Regex to strip trailing metadata brackets like [category: ...] [confidence: ...] [reasoning: ...]
_TRAILING_META_RE = re.compile(r"( \[(category|confidence|reasoning): [^\]]*\])+$")


def append_gotcha(spec_dir: Path, gotcha: str) -> None:
    """
    Append a gotcha (pitfall to avoid) to the gotchas list.

    Gotchas are deduplicated - if the same gotcha already exists,
    it won't be added again.

    Args:
        spec_dir: Path to spec directory
        gotcha: Description of the pitfall to avoid

    Example:
        append_gotcha(spec_dir, "Database connections must be closed in workers")
        append_gotcha(spec_dir, "API rate limits: 100 req/min per IP")
    """
    memory_dir = get_memory_dir(spec_dir)
    gotchas_file = memory_dir / "gotchas.md"

    # Load existing gotchas
    existing_gotchas = set()
    if gotchas_file.exists():
        content = gotchas_file.read_text(encoding="utf-8")
        # Extract bullet points
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                existing_gotchas.add(line[2:].strip())

    # Add new gotcha if not duplicate
    gotcha_stripped = gotcha.strip()
    if gotcha_stripped and gotcha_stripped not in existing_gotchas:
        # Append to file
        with open(gotchas_file, "a", encoding="utf-8") as f:
            if gotchas_file.stat().st_size == 0:
                # First entry - add header
                f.write("# Gotchas and Pitfalls\n\n")
                f.write("Things to watch out for in this codebase:\n\n")
            f.write(f"- {gotcha_stripped}\n")

        # Also save to Graphiti if enabled
        if is_graphiti_memory_enabled():
            try:
                graphiti = run_async(get_graphiti_memory(spec_dir))
                if graphiti:
                    run_async(graphiti.save_gotcha(gotcha_stripped))
                    run_async(graphiti.close())
            except Exception as e:
                logger.warning(f"Graphiti gotcha save failed: {e}")


def load_gotchas(spec_dir: Path) -> list[str]:
    """
    Load all gotchas.

    Args:
        spec_dir: Path to spec directory

    Returns:
        List of gotcha strings
    """
    memory_dir = get_memory_dir(spec_dir)
    gotchas_file = memory_dir / "gotchas.md"

    if not gotchas_file.exists():
        return []

    content = gotchas_file.read_text(encoding="utf-8")
    gotchas = []

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            gotchas.append(line[2:].strip())

    return gotchas


def append_pattern(
    spec_dir: Path,
    pattern: str,
    category: str | None = None,
    confidence: float | None = None,
    reasoning: str | None = None,
) -> None:
    """
    Append a code pattern to follow.

    Patterns are deduplicated - if the same pattern already exists,
    it won't be added again.

    Args:
        spec_dir: Path to spec directory
        pattern: Description of the code pattern
        category: Optional pattern category (naming, error-handling, organization, etc.)
        confidence: Optional confidence score 0.0-1.0
        reasoning: Optional explanation of why this is a pattern

    Example:
        append_pattern(spec_dir, "Use try/except with specific exceptions",
                      category="error-handling", confidence=0.9)
        append_pattern(spec_dir, "All API responses use {success: bool, data: any, error: string}",
                      category="api-patterns")
    """
    memory_dir = get_memory_dir(spec_dir)
    patterns_file = memory_dir / "patterns.md"

    # Load existing patterns
    existing_patterns = set()
    if patterns_file.exists():
        content = patterns_file.read_text(encoding="utf-8")
        # Extract bullet points
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                # Extract just the pattern text (strip trailing metadata brackets)
                raw = line[2:].strip()
                pattern_text = _TRAILING_META_RE.sub("", raw).strip()
                existing_patterns.add(pattern_text)

    # Add new pattern if not duplicate
    pattern_stripped = pattern.strip()
    if pattern_stripped and pattern_stripped not in existing_patterns:
        # Format pattern with metadata
        pattern_line = f"- {pattern_stripped}"
        if category:
            pattern_line += f" [category: {category}]"
        if confidence is not None:
            pattern_line += f" [confidence: {confidence:.2f}]"
        if reasoning:
            pattern_line += f" [reasoning: {reasoning}]"
        pattern_line += "\n"

        # Append to file
        with open(patterns_file, "a", encoding="utf-8") as f:
            if patterns_file.stat().st_size == 0:
                # First entry - add header
                f.write("# Code Patterns\n\n")
                f.write("Established patterns to follow in this codebase:\n\n")
            f.write(pattern_line)

        # Also save to Graphiti if enabled with metadata
        if is_graphiti_memory_enabled():
            try:
                graphiti = run_async(get_graphiti_memory(spec_dir))
                if graphiti:
                    category_metadata = None
                    if category or confidence is not None or reasoning:
                        category_metadata = {
                            "category": category or "uncategorized",
                            "confidence": confidence if confidence is not None else 0.0,
                            "reasoning": reasoning or "",
                        }
                    run_async(
                        graphiti.save_pattern(pattern_stripped, category_metadata)
                    )
                    run_async(graphiti.close())
            except Exception as e:
                logger.warning(f"Graphiti pattern save failed: {e}")


def load_patterns(spec_dir: Path) -> list[str]:
    """
    Load all code patterns.

    Args:
        spec_dir: Path to spec directory

    Returns:
        List of pattern strings
    """
    memory_dir = get_memory_dir(spec_dir)
    patterns_file = memory_dir / "patterns.md"

    if not patterns_file.exists():
        return []

    content = patterns_file.read_text(encoding="utf-8")
    patterns = []

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            patterns.append(line[2:].strip())

    return patterns


def save_detected_patterns_from_naming(
    spec_dir: Path, naming_conventions: dict, confidence: float = 0.8
) -> None:
    """
    Save patterns detected from naming convention analysis.

    Args:
        spec_dir: Path to spec directory
        naming_conventions: Output from NamingDetector.detect_naming_conventions()
        confidence: Confidence score for detected patterns (default: 0.8)
    """
    if not naming_conventions:
        return

    category = "naming-conventions"

    # Variable naming
    if naming_conventions.get("variable_style"):
        pattern = f"Variables use {naming_conventions['variable_style']}"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from codebase analysis",
        )

    # Function naming
    if naming_conventions.get("function_style"):
        pattern = f"Functions use {naming_conventions['function_style']}"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from codebase analysis",
        )

    # Class naming
    if naming_conventions.get("class_style"):
        pattern = f"Classes use {naming_conventions['class_style']}"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from codebase analysis",
        )

    # Constant naming
    if naming_conventions.get("constant_style"):
        pattern = f"Constants use {naming_conventions['constant_style']}"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from codebase analysis",
        )

    # Private prefix
    if naming_conventions.get("private_prefix"):
        pattern = f"Private members use '{naming_conventions['private_prefix']}' prefix"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from codebase analysis",
        )

    # File naming
    if naming_conventions.get("file_style"):
        pattern = f"Files use {naming_conventions['file_style']}"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from codebase analysis",
        )


def save_detected_patterns_from_errors(
    spec_dir: Path, error_patterns: dict, confidence: float = 0.7
) -> None:
    """
    Save patterns detected from error handling analysis.

    Args:
        spec_dir: Path to spec directory
        error_patterns: Output from ErrorPatternDetector.detect_error_patterns()
        confidence: Confidence score for detected patterns (default: 0.7)
    """
    if not error_patterns:
        return

    category = "error-handling"

    # Exception types — detector may return:
    #   "exception_types" as dict {name: count} OR
    #   "common_exceptions" as list [{"type": name, "count": count}]
    exception_types_raw = error_patterns.get(
        "exception_types", error_patterns.get("common_exceptions")
    )
    if exception_types_raw:
        # Normalize to list of (name, count) tuples
        if isinstance(exception_types_raw, dict):
            top_exceptions = sorted(
                exception_types_raw.items(), key=lambda x: x[1], reverse=True
            )[:3]
        else:
            # list of dicts: [{"type": name, "count": count}]
            top_exceptions = [
                (item.get("type", str(item)), item.get("count", 0))
                for item in exception_types_raw[:3]
            ]
        if top_exceptions:
            exc_list = ", ".join([exc for exc, _ in top_exceptions])
            pattern = f"Common exception types: {exc_list}"
            append_pattern(
                spec_dir,
                pattern,
                category=category,
                confidence=confidence,
                reasoning="Most frequently caught exceptions",
            )

    # Custom exceptions — may be list of strings or list of dicts with "name" key
    custom_exceptions_raw = error_patterns.get("custom_exceptions", [])
    if custom_exceptions_raw:
        # Normalize to list of names
        custom_names = [
            item["name"] if isinstance(item, dict) else str(item)
            for item in custom_exceptions_raw[:5]
        ]
        if custom_names:
            pattern = f"Project defines custom exceptions: {', '.join(custom_names)}"
            append_pattern(
                spec_dir,
                pattern,
                category=category,
                confidence=confidence,
                reasoning="Custom exception classes found in codebase",
            )

    # Logging patterns — may be list of strings or list of dicts with "pattern" key
    logging_patterns_raw = error_patterns.get("logging_patterns", [])
    if logging_patterns_raw:
        log_items = [
            item.get("pattern", str(item)) if isinstance(item, dict) else str(item)
            for item in logging_patterns_raw
        ]
        unique_patterns = set(log_items)
        if unique_patterns:
            pattern = f"Error logging: {', '.join(list(unique_patterns)[:3])}"
            append_pattern(
                spec_dir,
                pattern,
                category=category,
                confidence=confidence,
                reasoning="Detected error logging practices",
            )

    # Error propagation — key may be "error_propagation" or "error_propagation_stats"
    propagation = error_patterns.get(
        "error_propagation", error_patterns.get("error_propagation_stats", {})
    )
    if propagation:
        total = sum(propagation.values())
        if total > 0:
            # Determine dominant strategy
            if propagation.get("re_raises", 0) > propagation.get("handles", 0):
                pattern = "Errors are typically re-raised after logging"
                append_pattern(
                    spec_dir,
                    pattern,
                    category=category,
                    confidence=confidence,
                    reasoning="Error propagation analysis",
                )
            elif propagation.get("wraps", 0) > 0:
                pattern = "Errors are wrapped in custom exceptions"
                append_pattern(
                    spec_dir,
                    pattern,
                    category=category,
                    confidence=confidence,
                    reasoning="Error propagation analysis",
                )


def save_detected_patterns_from_organization(
    spec_dir: Path, organization_patterns: dict, confidence: float = 0.75
) -> None:
    """
    Save patterns detected from code organization analysis.

    Args:
        spec_dir: Path to spec directory
        organization_patterns: Output from OrganizationDetector.detect_organization_patterns()
        confidence: Confidence score for detected patterns (default: 0.75)
    """
    if not organization_patterns:
        return

    category = "code-organization"

    # Architectural style
    arch_style = organization_patterns.get("architectural_style")
    if arch_style:
        pattern = f"Project follows {arch_style} architecture"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Detected from directory structure and imports",
        )

    # File organization
    file_org = organization_patterns.get("file_organization", {})
    avg_file_size = file_org.get("average_file_size_lines") or file_org.get(
        "average_file_size"
    )
    if avg_file_size:
        if avg_file_size < 300:
            pattern = "Files are kept small (< 300 lines)"
        elif avg_file_size < 500:
            pattern = "Files are moderate size (300-500 lines)"
        else:
            pattern = "Files can be large (> 500 lines)"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="File size analysis",
        )

    # Module patterns
    module_patterns = organization_patterns.get("module_patterns", {})
    import_style = module_patterns.get("import_style")
    if import_style:
        pattern = f"Imports follow {import_style} style"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Import pattern analysis",
        )

    # Separation patterns
    separation = organization_patterns.get("separation_patterns", {})
    if separation.get("has_config_separation"):
        pattern = "Configuration is separated into dedicated files"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Config files detected",
        )

    if separation.get("has_test_separation"):
        pattern = "Tests are separated from implementation code"
        append_pattern(
            spec_dir,
            pattern,
            category=category,
            confidence=confidence,
            reasoning="Test directory structure detected",
        )
