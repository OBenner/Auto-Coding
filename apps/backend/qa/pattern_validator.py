"""
Pattern Validator Module
=========================

Validates generated code against learned codebase patterns including:
- Naming conventions (variables, functions, classes, constants)
- Error handling patterns (exception types, logging, propagation)
- Code organization patterns (file structure, imports, separation)

Used by QA reviewer to ensure generated code follows established conventions.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

from graphiti_config import is_graphiti_enabled
from memory.graphiti_helpers import get_graphiti_memory
from memory.patterns import load_patterns

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION RESULT TYPES
# =============================================================================


class PatternViolation:
    """Represents a violation of a learned pattern."""

    def __init__(
        self,
        pattern: str,
        violation_type: str,
        file_path: str,
        line_number: int | None = None,
        description: str = "",
        severity: str = "warning",
    ):
        self.pattern = pattern
        self.violation_type = violation_type
        self.file_path = file_path
        self.line_number = line_number
        self.description = description
        self.severity = severity  # "error", "warning", "info"

    def __repr__(self) -> str:
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"
        return f"<PatternViolation {self.severity} in {location}: {self.description}>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern": self.pattern,
            "violation_type": self.violation_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "description": self.description,
            "severity": self.severity,
        }


class ValidationResult:
    """Aggregated validation results."""

    def __init__(self):
        self.violations: list[PatternViolation] = []
        self.patterns_checked: int = 0
        self.files_validated: int = 0

    def add_violation(self, violation: PatternViolation) -> None:
        """Add a pattern violation."""
        self.violations.append(violation)

    def has_errors(self) -> bool:
        """Check if there are any error-level violations."""
        return any(v.severity == "error" for v in self.violations)

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(v.severity == "warning" for v in self.violations)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of validation results."""
        errors = [v for v in self.violations if v.severity == "error"]
        warnings = [v for v in self.violations if v.severity == "warning"]
        info_items = [v for v in self.violations if v.severity == "info"]

        return {
            "patterns_checked": self.patterns_checked,
            "files_validated": self.files_validated,
            "total_violations": len(self.violations),
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info_items),
            "violations": [v.to_dict() for v in self.violations],
        }


# =============================================================================
# PATTERN RETRIEVAL
# =============================================================================


async def get_learned_patterns(
    spec_dir: Path,
    project_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """
    Retrieve learned patterns from memory system.

    Args:
        spec_dir: Spec directory path
        project_dir: Project root directory

    Returns:
        Dictionary mapping pattern categories to pattern lists:
        {
            "naming-conventions": [...],
            "error-handling": [...],
            "code-organization": [...]
        }
    """
    patterns_by_category: dict[str, list[dict[str, Any]]] = {
        "naming-conventions": [],
        "error-handling": [],
        "code-organization": [],
    }

    # Load from file-based memory first
    file_patterns = load_patterns(spec_dir)
    for pattern_str in file_patterns:
        # Parse pattern string format: "Pattern text [category: X] [confidence: Y]"
        pattern_data = _parse_pattern_string(pattern_str)
        category = pattern_data.get("category", "uncategorized")
        if category in patterns_by_category:
            patterns_by_category[category].append(pattern_data)

    # If Graphiti is enabled, retrieve from knowledge graph
    if is_graphiti_enabled():
        memory = None
        try:
            memory = await get_graphiti_memory(spec_dir, project_dir)
            if memory:
                # Search for patterns by category
                for category in patterns_by_category:
                    try:
                        # Use search_facts to find pattern nodes
                        results = await memory.client.search_facts(
                            query=f"category:{category}",
                            group_ids=[memory.group_id],
                            limit=20,
                        )
                        for result in results:
                            fact = result.get("fact", "")
                            if fact:
                                pattern_data = {
                                    "text": fact,
                                    "category": category,
                                    "confidence": result.get("score", 0.0),
                                }
                                patterns_by_category[category].append(pattern_data)
                    except Exception as e:
                        logger.warning(
                            f"Graphiti pattern retrieval failed for {category}: {e}"
                        )
        except Exception as e:
            logger.warning(f"Graphiti memory access failed: {e}")
        finally:
            if memory:
                try:
                    await memory.close()
                except (OSError, RuntimeError):
                    pass

    return patterns_by_category


def _parse_pattern_string(pattern_str: str) -> dict[str, Any]:
    """
    Parse pattern string to extract metadata.

    Format: "Pattern text [category: X] [confidence: Y] [reasoning: Z]"
    """
    pattern_data: dict[str, Any] = {
        "text": pattern_str,
        "category": "uncategorized",
        "confidence": 0.0,
    }

    # Extract category
    category_match = re.search(r"\[category: ([^\]]+)\]", pattern_str)
    if category_match:
        pattern_data["category"] = category_match.group(1)
        # Remove metadata from text
        pattern_data["text"] = pattern_str.split(" [category:")[0].strip()

    # Extract confidence
    confidence_match = re.search(r"\[confidence: ([\d.]+)\]", pattern_str)
    if confidence_match:
        pattern_data["confidence"] = float(confidence_match.group(1))

    return pattern_data


# =============================================================================
# PATTERN VALIDATORS
# =============================================================================


def validate_naming_conventions(
    file_path: Path,
    patterns: list[dict[str, Any]],
    result: ValidationResult,
) -> None:
    """
    Validate that code follows naming convention patterns.

    Args:
        file_path: Path to file to validate
        patterns: List of naming convention patterns
        result: ValidationResult to append violations to
    """
    if not file_path.exists() or file_path.suffix != ".py":
        return

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return

    # Extract expected styles from patterns
    expected_styles = _extract_naming_styles(patterns)

    # Validate function names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _validate_function_name(node, expected_styles, file_path, result)

        elif isinstance(node, ast.ClassDef):
            _validate_class_name(node, expected_styles, file_path, result)

        elif isinstance(node, ast.Assign):
            _validate_variable_names(node, expected_styles, file_path, result)


def _extract_naming_styles(patterns: list[dict[str, Any]]) -> dict[str, str]:
    """Extract expected naming styles from patterns."""
    styles = {}
    for pattern in patterns:
        text = pattern.get("text", "").lower()

        if "variables use" in text or "variable" in text:
            if "snake_case" in text:
                styles["variable"] = "snake_case"
            elif "camelcase" in text:
                styles["variable"] = "camelCase"

        if "functions use" in text or "function" in text:
            if "snake_case" in text:
                styles["function"] = "snake_case"
            elif "camelcase" in text:
                styles["function"] = "camelCase"
            elif "pascalcase" in text:
                styles["function"] = "PascalCase"

        if "classes use" in text or "class" in text:
            if "pascalcase" in text:
                styles["class"] = "PascalCase"
            elif "snake_case" in text:
                styles["class"] = "snake_case"

        if "constants use" in text or "constant" in text:
            if "upper_snake_case" in text or "upper" in text:
                styles["constant"] = "UPPER_SNAKE_CASE"

    return styles


def _validate_function_name(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    expected_styles: dict[str, str],
    file_path: Path,
    result: ValidationResult,
) -> None:
    """Validate function name against expected style."""
    expected_style = expected_styles.get("function")
    if not expected_style:
        return

    name = node.name
    if name.startswith("_"):
        # Skip private functions
        return

    actual_style = _detect_name_style(name)
    if actual_style != expected_style:
        violation = PatternViolation(
            pattern=f"Functions use {expected_style}",
            violation_type="naming-convention",
            file_path=str(file_path),
            line_number=node.lineno,
            description=f"Function '{name}' uses {actual_style} but codebase expects {expected_style}",
            severity="warning",
        )
        result.add_violation(violation)


def _validate_class_name(
    node: ast.ClassDef,
    expected_styles: dict[str, str],
    file_path: Path,
    result: ValidationResult,
) -> None:
    """Validate class name against expected style."""
    expected_style = expected_styles.get("class")
    if not expected_style:
        return

    name = node.name
    actual_style = _detect_name_style(name)
    if actual_style != expected_style:
        violation = PatternViolation(
            pattern=f"Classes use {expected_style}",
            violation_type="naming-convention",
            file_path=str(file_path),
            line_number=node.lineno,
            description=f"Class '{name}' uses {actual_style} but codebase expects {expected_style}",
            severity="warning",
        )
        result.add_violation(violation)


def _validate_variable_names(
    node: ast.Assign,
    expected_styles: dict[str, str],
    file_path: Path,
    result: ValidationResult,
) -> None:
    """Validate variable/constant names against expected style."""
    for target in node.targets:
        if isinstance(target, ast.Name):
            name = target.id
            if name.isupper():
                # Constant
                expected_style = expected_styles.get("constant")
                if expected_style and expected_style == "UPPER_SNAKE_CASE":
                    if "_" not in name and len(name) > 3:
                        violation = PatternViolation(
                            pattern=f"Constants use {expected_style}",
                            violation_type="naming-convention",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            description=f"Constant '{name}' should use UPPER_SNAKE_CASE",
                            severity="info",
                        )
                        result.add_violation(violation)


def _detect_name_style(name: str) -> str:
    """Detect the naming style of an identifier."""
    if "_" in name:
        if name.isupper():
            return "UPPER_SNAKE_CASE"
        return "snake_case"
    elif name[0].isupper():
        return "PascalCase"
    elif any(c.isupper() for c in name):
        return "camelCase"
    else:
        return "snake_case"


def validate_error_handling(
    file_path: Path,
    patterns: list[dict[str, Any]],
    result: ValidationResult,
) -> None:
    """
    Validate that code follows error handling patterns.

    Args:
        file_path: Path to file to validate
        patterns: List of error handling patterns
        result: ValidationResult to append violations to
    """
    if not file_path.exists() or file_path.suffix != ".py":
        return

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return

    # Extract expected error handling from patterns
    expected_exceptions = _extract_expected_exceptions(patterns)

    # Validate try/except blocks
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            _validate_exception_handling(node, expected_exceptions, file_path, result)


def _extract_expected_exceptions(patterns: list[dict[str, Any]]) -> list[str]:
    """Extract common exception types from patterns."""
    exceptions = []
    for pattern in patterns:
        text = pattern.get("text", "")
        if "exception" in text.lower():
            # Extract exception type names
            match = re.search(r"([A-Z]\w+Error|[A-Z]\w+Exception)", text)
            if match:
                exceptions.append(match.group(1))
    return exceptions


def _validate_exception_handling(
    node: ast.Try,
    expected_exceptions: list[str],
    file_path: Path,
    result: ValidationResult,
) -> None:
    """Validate try/except block patterns."""
    has_bare_except = False

    for handler in node.handlers:
        if handler.type is None:
            # Bare except clause
            has_bare_except = True

    if has_bare_except:
        violation = PatternViolation(
            pattern="Use specific exception types",
            violation_type="error-handling",
            file_path=str(file_path),
            line_number=node.lineno,
            description="Bare 'except:' clause found - should catch specific exceptions",
            severity="warning",
        )
        result.add_violation(violation)


# =============================================================================
# MAIN VALIDATION API
# =============================================================================


async def validate_patterns(
    spec_dir: Path,
    project_dir: Path,
    files_to_validate: list[Path] | None = None,
) -> ValidationResult:
    """
    Validate files against learned codebase patterns.

    Args:
        spec_dir: Spec directory path
        project_dir: Project root directory
        files_to_validate: Optional list of files to validate (defaults to all modified files)

    Returns:
        ValidationResult with violations and summary
    """
    result = ValidationResult()

    # Retrieve learned patterns
    patterns_by_category = await get_learned_patterns(spec_dir, project_dir)

    # If no files specified, validate all Python files in project
    if files_to_validate is None:
        files_to_validate = list(project_dir.glob("**/*.py"))
        # Filter out common ignore patterns
        files_to_validate = [
            f
            for f in files_to_validate
            if not any(
                part.startswith(".") or part == "__pycache__" for part in f.parts
            )
        ]

    result.files_validated = len(files_to_validate)

    # Validate naming conventions
    naming_patterns = patterns_by_category.get("naming-conventions", [])
    if naming_patterns:
        result.patterns_checked += len(naming_patterns)
        for file_path in files_to_validate:
            validate_naming_conventions(file_path, naming_patterns, result)

    # Validate error handling
    error_patterns = patterns_by_category.get("error-handling", [])
    if error_patterns:
        result.patterns_checked += len(error_patterns)
        for file_path in files_to_validate:
            validate_error_handling(file_path, error_patterns, result)

    # Code organization patterns are typically validated at project level,
    # not individual files, so we skip them here

    return result


async def validate_patterns_for_qa(
    spec_dir: Path,
    project_dir: Path,
    modified_files: list[str] | None = None,
) -> dict[str, Any]:
    """
    Validate patterns for QA review.

    This is the main entry point for QA reviewer integration.

    Args:
        spec_dir: Spec directory path
        project_dir: Project root directory
        modified_files: Optional list of modified file paths

    Returns:
        Dictionary with validation results:
        {
            "passed": bool,
            "summary": {...},
            "violations": [...]
        }
    """
    # Convert string paths to Path objects
    files_to_validate = None
    if modified_files:
        files_to_validate = [Path(f) for f in modified_files if Path(f).suffix == ".py"]

    # Run validation
    result = await validate_patterns(spec_dir, project_dir, files_to_validate)

    # Get summary
    summary = result.get_summary()

    return {
        "passed": not result.has_errors(),
        "summary": summary,
        "violations": [v.to_dict() for v in result.violations],
    }
