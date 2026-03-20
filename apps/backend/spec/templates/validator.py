"""
Template Validation
===================

Security validation for spec templates.

Validates:
- Template structure (name, description, category, parameters)
- Parameter safety (no dangerous parameter configurations)
- Placeholder validity (proper {{PLACEHOLDER}} format)
- Content safety (no command injection, prompt injection attacks)
- Generated content validation

This module provides defense-in-depth for user-provided templates,
preventing malicious or misconfigured templates from compromising the system.
"""

import logging
import re
from typing import Any

from .placeholders import PlaceholderParser
from .registry import Template

logger = logging.getLogger(__name__)


# =============================================================================
# Template Validation Constants
# =============================================================================

# Patterns that indicate potential security issues in template content
DANGEROUS_CONTENT_PATTERNS = [
    # Command execution attempts
    r"(?i)(^|\s)(rm\s+-rf|sudo|chmod|chown|curl.*sh|wget.*sh|eval|exec)",
    # Environment variable manipulation
    r"(?i)\$\{?[A-Z_]+\}?.*=",
    # Shell operators in suspicious contexts
    r"(?i)(\||;|&&|`|>|<)\s*(rm|mv|cp|dd|mkfs|format|del|erase)",
    # Credential patterns (excluding placeholders)
    r"(?i)(password|secret|token|key|auth)\s*[:=]\s*['\"]?\w{8,}",
    # Prompt injection indicators
    r"(?i)(ignore\s+(all\s+)?previous|disregard\s+(all\s+)?instructions|new\s+instructions?)",
    r"(?i)(override\s+system|bypass\s+security|disable\s+safety)",
    # File path traversal
    r"\.\./\.\./",
    # SQL injection patterns
    r"(?i)(union\s+select|or\s+1\s*=\s*1|drop\s+table|delete\s+from)",
]

# Patterns that indicate potentially unsafe parameter configurations
DANGEROUS_PARAMETER_PATTERNS = [
    r"(?i)(__.*__|eval|exec|compile|import)",  # Python internals
    r"(?i)(system|subprocess|shell|popen)",  # Process spawning
]

# Python import statement patterns
IMPORT_STATEMENT_PATTERNS = [
    r"(?m)^\s*import\s+\w+",  # `import os`
    r"(?m)^\s*from\s+\w+\s+import",  # `from os import path`
    r"(?m)^\s*import\s+\w+\s*,",  # `import os, sys`
    r"(?i)(__import__|__builtins__|globals|locals|vars)",  # Dangerous built-ins
]

# Dangerous Python modules that should never be imported in templates
DANGEROUS_IMPORT_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "pathlib",
    "threading",
    "multiprocessing",
    "socket",
    "http",
    "urllib",
    "requests",
    "ftplib",
    "telnetlib",
    "pickle",
    "shelve",
    "marshal",
    "eval",
    "exec",
    "compile",
}

# Valid parameter types for template parameters
VALID_PARAM_TYPES = {str, bool, list, dict, int, float}

# Safe template fields
ALLOWED_TEMPLATE_FIELDS = {
    "name",
    "description",
    "category",
    "parameters",
    "placeholders",
}


# =============================================================================
# Validation Functions
# =============================================================================


def validate_template(
    template: Template,
    strict: bool = True,
) -> tuple[bool, list[str]]:
    """
    Validate a spec template for security and correctness.

    This is the main validation entry point. Performs comprehensive checks:
    1. Basic field validation (name, description, category)
    2. Parameter validation (types, required fields)
    3. Placeholder validation (proper format, no duplicates)
    4. Content safety (no injection attacks)
    5. Generated content validation

    Args:
        template: Template instance to validate
        strict: If True, fail on warnings. If False, allow warnings.

    Returns:
        Tuple of (is_valid, list_of_errors)
        - is_valid: True if template passes all checks
        - list_of_errors: List of error/warning messages (empty if valid)
    """
    errors = []

    # Validate basic fields
    basic_errors = validate_basic_fields(template)
    errors.extend(basic_errors)

    # Validate parameters
    param_errors = validate_parameters(template.parameters)
    errors.extend(param_errors)

    # Validate placeholders
    placeholder_errors = validate_placeholders(template.placeholders)
    errors.extend(placeholder_errors)

    # Validate generated content safety (sample generation)
    if not errors:  # Only if basic validation passes
        content_errors = validate_generated_content(template, strict=strict)
        errors.extend(content_errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_basic_fields(template: Template) -> list[str]:
    """
    Validate basic template fields.

    Checks:
    - Name is present and valid format
    - Description is present and meaningful
    - Category is present

    Args:
        template: Template instance to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate name
    if not template.name or not template.name.strip():
        errors.append("Template name is required")
    elif not _is_valid_name(template.name):
        errors.append(
            f"Invalid template name '{template.name}'. "
            "Name must be lowercase alphanumeric with underscores/hyphens only"
        )

    # Validate description
    if not template.description or not template.description.strip():
        errors.append("Template description is required")
    elif len(template.description.strip()) < 10:
        errors.append(
            f"Template description too short ({len(template.description)} chars). "
            "Minimum: 10 characters"
        )

    # Validate category
    if not template.category or not template.category.strip():
        errors.append("Template category is required")
    elif not _is_valid_category(template.category):
        errors.append(
            f"Invalid template category '{template.category}'. "
            "Category must be lowercase alphanumeric with underscores/hyphens only"
        )

    return errors


def validate_parameters(parameters: dict[str, Any]) -> list[str]:
    """
    Validate template parameters for safety and correctness.

    Checks parameter definitions for:
    - Valid parameter names
    - Supported types
    - Dangerous patterns in default values
    - Required field completeness

    Args:
        parameters: Dictionary of parameter definitions

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not isinstance(parameters, dict):
        errors.append(
            f"Parameters must be a dictionary, got: {type(parameters).__name__}"
        )
        return errors

    # Empty parameters are valid
    if not parameters:
        return errors

    for param_name, param_def in parameters.items():
        # Validate parameter name
        if not isinstance(param_name, str) or not param_name.strip():
            errors.append(f"Invalid parameter name: {param_name}")
            continue

        if not _is_valid_param_name(param_name):
            errors.append(
                f"Invalid parameter name '{param_name}'. "
                "Must be lowercase alphanumeric with underscores only"
            )

        # Check for dangerous patterns in parameter names
        for pattern in DANGEROUS_PARAMETER_PATTERNS:
            if re.search(pattern, param_name):
                errors.append(
                    f"Potentially dangerous parameter name: {param_name} "
                    f"(matches pattern: {pattern[:50]}...)"
                )

        # Validate parameter definition structure
        if not isinstance(param_def, dict):
            errors.append(
                f"Parameter definition for '{param_name}' must be a dictionary, "
                f"got: {type(param_def).__name__}"
            )
            continue

        # Check for required fields in parameter definition
        if "type" not in param_def:
            errors.append(f"Parameter '{param_name}' missing 'type' field")

        # Validate parameter type
        if "type" in param_def:
            param_type = param_def["type"]
            if param_type not in VALID_PARAM_TYPES:
                errors.append(
                    f"Invalid type for parameter '{param_name}': {param_type}. "
                    f"Valid types: {', '.join(str(t.__name__) for t in VALID_PARAM_TYPES)}"
                )

        # Validate default value if present
        if "default" in param_def:
            default_value = param_def["default"]
            if isinstance(default_value, str):
                # Check for dangerous patterns in default values
                for pattern in DANGEROUS_PARAMETER_PATTERNS:
                    if re.search(pattern, default_value):
                        errors.append(
                            f"Potentially dangerous default value for '{param_name}': "
                            f"{default_value[:50]}... (matches pattern: {pattern[:50]}...)"
                        )

    return errors


def validate_placeholders(placeholders: list[str]) -> list[str]:
    """
    Validate template placeholders.

    Checks:
    - All placeholders have valid format ({{PLACEHOLDER_NAME}})
    - No duplicate placeholders
    - Placeholder names follow naming conventions

    Args:
        placeholders: List of placeholder names

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not isinstance(placeholders, list):
        errors.append(
            f"Placeholders must be a list, got: {type(placeholders).__name__}"
        )
        return errors

    # Empty placeholders are valid
    if not placeholders:
        return errors

    parser = PlaceholderParser()

    # Check for duplicates
    if len(placeholders) != len(set(placeholders)):
        duplicates = [p for p in placeholders if placeholders.count(p) > 1]
        errors.append(f"Duplicate placeholders found: {', '.join(set(duplicates))}")

    # Validate each placeholder
    for placeholder in placeholders:
        if not isinstance(placeholder, str):
            errors.append(
                f"Placeholder must be a string, got: {type(placeholder).__name__}"
            )
            continue

        # Validate placeholder name format
        if not parser.is_valid_placeholder_name(placeholder):
            errors.append(
                f"Invalid placeholder name: {placeholder}. "
                "Must be uppercase letters, numbers, and underscores only"
            )

    return errors


def validate_generated_content(
    template: Template, strict: bool = True
) -> list[str]:
    """
    Validate content generated by the template for security issues.

    Performs a sample template generation with default/sample parameters
    and validates the output for dangerous patterns.

    Args:
        template: Template instance to validate
        strict: If True, fail on warnings. If False, allow warnings.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    try:
        # Build sample parameters for template generation
        sample_params = {}
        for param_name, param_def in template.parameters.items():
            if "default" in param_def:
                sample_params[param_name] = param_def["default"]
            else:
                # Provide a sample value based on type
                param_type = param_def.get("type", str)
                if param_type == str:
                    sample_params[param_name] = "sample_value"
                elif param_type == bool:
                    sample_params[param_name] = False
                elif param_type == list:
                    sample_params[param_name] = ["sample_item"]
                elif param_type == dict:
                    sample_params[param_name] = {"key": "value"}
                elif param_type == int:
                    sample_params[param_name] = 0
                elif param_type == float:
                    sample_params[param_name] = 0.0
                else:
                    sample_params[param_name] = None

        # Generate sample content
        content = template.generate(sample_params)

        # Validate the generated content
        content_errors = validate_content_safety(content, strict=strict)
        errors.extend(content_errors)

    except Exception as e:
        errors.append(f"Failed to generate sample content for validation: {e}")

    return errors


def validate_content_safety(content: Any, strict: bool = True) -> list[str]:
    """
    Validate generated content for security issues.

    Recursively checks all string values in the content for:
    - Command injection patterns
    - Prompt injection attempts
    - Import statements
    - Dangerous module references

    Args:
        content: Generated content to validate (dict, list, str, etc.)
        strict: If True, fail on warnings. If False, allow warnings.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    def _validate_string(text: str, path: str = "") -> None:
        """Validate a string value for dangerous patterns."""
        if not text or not isinstance(text, str):
            return

        # Check for dangerous content patterns
        for pattern in DANGEROUS_CONTENT_PATTERNS:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                # Skip if it's a placeholder (will be replaced by user)
                if "{{" in match.group(0) and "}}" in match.group(0):
                    continue
                errors.append(
                    f"Potentially dangerous pattern in generated content{path}: "
                    f"{pattern[:50]}... (matched: {match.group(0)[:30]}...)"
                )

        # Check for import statements
        for pattern in IMPORT_STATEMENT_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                errors.append(
                    f"Python import statement detected in generated content{path}. "
                    "Import statements are not allowed in template output."
                )
                break

        # Check for dangerous module references
        for module in DANGEROUS_IMPORT_MODULES:
            module_pattern = r"\b" + re.escape(module) + r"\.[A-Za-z_][A-Za-z0-9_]*\b"
            if re.search(module_pattern, text):
                errors.append(
                    f"Reference to dangerous Python module '{module}' in generated content{path}. "
                    "System modules are not allowed in template output."
                )
                break

        # Check content length (prevent DoS via huge content)
        if len(text) > 100000:  # 100KB limit per string
            errors.append(
                f"Generated content{path} is too long ({len(text)} chars). "
                "Maximum allowed: 100000 chars per field"
            )

    def _validate_recursive(obj: Any, path: str = "") -> None:
        """Recursively validate an object."""
        if isinstance(obj, str):
            _validate_string(obj, path)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                _validate_recursive(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _validate_recursive(item, f"{path}[{i}]")

    _validate_recursive(content)
    return errors


def validate_import(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate template data from import (before creating Template instance).

    This is used when importing templates from external sources (JSON files,
    marketplace, etc.) to catch security issues before instantiation.

    Performs comprehensive security checks:
    1. Field validation (required fields, types)
    2. Unexpected field detection
    3. Parameter validation
    4. Placeholder validation

    Args:
        data: Dictionary containing template data

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Security: Check for unexpected fields that could be exploited
    unexpected_fields = set(data.keys()) - ALLOWED_TEMPLATE_FIELDS
    if unexpected_fields:
        errors.append(
            f"Unexpected fields in template data: {', '.join(sorted(unexpected_fields))}. "
            f"Allowed fields: {', '.join(sorted(ALLOWED_TEMPLATE_FIELDS))}"
        )

    # Validate required fields are present
    required_fields = ["name", "description", "category"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Validate field types
    if "name" in data and not isinstance(data["name"], str):
        errors.append(
            f"Field 'name' must be a string, got: {type(data['name']).__name__}"
        )

    if "description" in data and not isinstance(data["description"], str):
        errors.append(
            f"Field 'description' must be a string, got: {type(data['description']).__name__}"
        )

    if "category" in data and not isinstance(data["category"], str):
        errors.append(
            f"Field 'category' must be a string, got: {type(data['category']).__name__}"
        )

    if "parameters" in data and not isinstance(data["parameters"], dict):
        errors.append(
            f"Field 'parameters' must be a dictionary, got: {type(data['parameters']).__name__}"
        )

    if "placeholders" in data and not isinstance(data["placeholders"], list):
        errors.append(
            f"Field 'placeholders' must be a list, got: {type(data['placeholders']).__name__}"
        )

    # Validate parameters if present
    if "parameters" in data and isinstance(data["parameters"], dict):
        param_errors = validate_parameters(data["parameters"])
        errors.extend(param_errors)

    # Validate placeholders if present
    if "placeholders" in data and isinstance(data["placeholders"], list):
        placeholder_errors = validate_placeholders(data["placeholders"])
        errors.extend(placeholder_errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_template_for_import(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Convenience wrapper for validate_import with better error formatting.

    This function is intended for use by template importers (storage modules,
    registry, marketplace) and provides formatted error messages suitable
    for user display.

    Args:
        data: Dictionary containing template data

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    is_valid, errors = validate_import(data)

    # Add summary if there are errors
    if errors:
        error_summary = [f"Template validation failed with {len(errors)} error(s):"]
        error_summary.extend(errors)
        return is_valid, error_summary

    return is_valid, errors


# =============================================================================
# Helper Functions
# =============================================================================


def _is_valid_name(name: str) -> bool:
    """
    Check if a template name is valid.

    Valid names:
    - Lowercase letters, numbers, hyphens, underscores
    - Must start with a letter
    - Examples: api-template, database_migration, crud123

    Args:
        name: Template name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    pattern = re.compile(r"^[a-z][a-z0-9_-]*$")
    return bool(pattern.match(name))


def _is_valid_category(category: str) -> bool:
    """
    Check if a template category is valid.

    Valid categories:
    - Lowercase letters, numbers, hyphens, underscores
    - Must start with a letter
    - Examples: api, database, ui, testing

    Args:
        category: Category name to validate

    Returns:
        True if valid, False otherwise
    """
    if not category:
        return False

    pattern = re.compile(r"^[a-z][a-z0-9_-]*$")
    return bool(pattern.match(category))


def _is_valid_param_name(param_name: str) -> bool:
    """
    Check if a parameter name is valid.

    Valid parameter names:
    - Lowercase letters, numbers, underscores
    - Must start with a letter
    - Examples: entity_name, include_auth, max_items

    Args:
        param_name: Parameter name to validate

    Returns:
        True if valid, False otherwise
    """
    if not param_name:
        return False

    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    return bool(pattern.match(param_name))
