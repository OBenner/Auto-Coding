"""
Template Validation
===================

Security validation for custom agent templates.

Validates:
- Prompt safety (no command injection, prompt injection attacks)
- Tool permissions (only allow known, safe tools)
- MCP server permissions (only allow registered MCP servers)
- Parameter safety (no dangerous parameter configurations)

This module provides defense-in-depth for user-provided templates,
preventing malicious or misconfigured templates from compromising the system.
"""

import ipaddress
import logging
import re
from typing import Any
from urllib.parse import urlparse

from agents.templates.models import AgentTemplate
from agents.tools_pkg import (
    BASE_READ_TOOLS,
    BASE_WRITE_TOOLS,
    WEB_TOOLS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Tool and MCP Server Allowlists
# =============================================================================

# All known safe tools that can be used in custom templates
ALLOWED_TOOLS = set(
    BASE_READ_TOOLS
    + BASE_WRITE_TOOLS
    + WEB_TOOLS
    + [
        # Allow tool name references (without mcp__ prefix for template config)
        "Task",
        "TaskOutput",
        "NotebookEdit",
        "TodoWrite",
        "AskUserQuestion",
    ]
)

# All known safe MCP server names that can be used in custom templates
ALLOWED_MCP_SERVERS = {
    "context7",
    "linear",
    "graphiti",
    "graphiti-memory",  # Alias for graphiti
    "auto-claude",
    "electron",
    "puppeteer",
}

# Valid thinking levels
VALID_THINKING_LEVELS = {"none", "low", "medium", "high", "ultrathink"}


# =============================================================================
# Dangerous Pattern Detection
# =============================================================================

# Patterns that indicate potential prompt injection or command execution attacks
DANGEROUS_PROMPT_PATTERNS = [
    # Command execution attempts
    r"(?i)(^|\s)(rm\s+-rf|sudo|chmod|chown|curl.*sh|wget.*sh|eval|exec)",
    # Environment variable manipulation
    r"(?i)\$\{?[A-Z_]+\}?.*=",
    # Shell operators in suspicious contexts
    r"(?i)(\||;|&&|`|>|<)\s*(rm|mv|cp|dd|mkfs|format|del|erase)",
    # Credential patterns
    r"(?i)(password|secret|token|key|auth)\s*[:=]\s*['\"]?\w+",
    # Prompt injection indicators
    r"(?i)(ignore\s+(all\s+)?previous|disregard\s+(all\s+)?instructions|new\s+instructions?)",
    r"(?i)(override\s+system|bypass\s+security|disable\s+safety)",
    # File path traversal
    r"\.\./\.\./",
    # SQL injection patterns (in case templates access databases)
    r"(?i)(union\s+select|or\s+1\s*=\s*1|drop\s+table|delete\s+from)",
]

# Patterns that indicate potentially unsafe parameter configurations
DANGEROUS_PARAMETER_PATTERNS = [
    r"(?i)(__.*__|eval|exec|compile|import)",  # Python internals
    r"(?i)(system|subprocess|shell|popen)",  # Process spawning
]

# Python import statement patterns (for custom_prompt validation)
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

# Safe metadata fields for templates
ALLOWED_TEMPLATE_FIELDS = {
    "name",
    "description",
    "category",
    "author",
    "version",
    "custom_prompt",
    "tools",
    "mcp_servers",
    "thinking_level",
    "parameters",
    "examples",
    "tags",
    "doc_url",
    "repo_url",
    "icon",
    "color",
    "created_at",  # Template metadata
    "updated_at",  # Template metadata
}


# =============================================================================
# Import Validation Functions
# =============================================================================


# =============================================================================
# Validation Functions
# =============================================================================


def validate_template(
    template: AgentTemplate,
    strict: bool = True,
) -> tuple[bool, list[str]]:
    """
    Validate a custom agent template for security and correctness.

    This is the main validation entry point. Performs comprehensive checks:
    1. Basic field validation (name, description, version)
    2. Prompt safety (no injection attacks)
    3. Tool permissions (only known tools)
    4. MCP server permissions (only registered servers)
    5. Parameter safety

    Args:
        template: AgentTemplate instance to validate
        strict: If True, fail on warnings. If False, allow warnings.

    Returns:
        Tuple of (is_valid, list_of_errors)
        - is_valid: True if template passes all checks
        - list_of_errors: List of error/warning messages (empty if valid)
    """
    errors = []

    # Run basic model validation first
    basic_errors = template.validate()
    if basic_errors:
        errors.extend(basic_errors)

    # Validate prompt safety
    prompt_errors = validate_prompt_safety(template.custom_prompt)
    errors.extend(prompt_errors)

    # Validate tool permissions
    tool_errors = validate_tool_permissions(template.tools)
    errors.extend(tool_errors)

    # Validate MCP server permissions
    mcp_errors = validate_mcp_server_permissions(template.mcp_servers)
    errors.extend(mcp_errors)

    # Validate thinking level
    if template.thinking_level not in VALID_THINKING_LEVELS:
        errors.append(
            f"Invalid thinking_level '{template.thinking_level}'. "
            f"Must be one of: {', '.join(sorted(VALID_THINKING_LEVELS))}"
        )

    # Validate parameters
    param_errors = validate_parameters(template.parameters)
    errors.extend(param_errors)

    # Additional safety checks
    safety_errors = validate_safety_constraints(template)
    errors.extend(safety_errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_prompt_safety(prompt: str) -> list[str]:
    """
    Validate custom prompt for security issues.

    Checks for:
    - Command injection patterns
    - Prompt injection attacks
    - Credential leakage
    - File path traversal
    - SQL injection (if template might access databases)

    Args:
        prompt: Custom prompt text to validate

    Returns:
        List of error messages (empty if safe)
    """
    errors = []

    if not prompt or not prompt.strip():
        # Empty prompts are valid (will use base agent behavior)
        return errors

    # Check for dangerous patterns
    for pattern in DANGEROUS_PROMPT_PATTERNS:
        match = re.search(pattern, prompt, re.MULTILINE)
        if match:
            errors.append(
                f"Potentially dangerous pattern detected in prompt: {pattern[:50]}... "
                f"(matched: {match.group(0)})"
            )

    # Check prompt length (prevent DoS via huge prompts)
    if len(prompt) > 50000:  # ~50KB limit
        errors.append(
            f"Prompt is too long ({len(prompt)} chars). Maximum allowed: 50000 chars"
        )

    # Check for excessive newlines (potential context stuffing)
    newline_count = prompt.count("\n")
    if newline_count > 500:
        errors.append(
            f"Prompt contains excessive newlines ({newline_count}). Maximum allowed: 500"
        )

    return errors


def validate_tool_permissions(tools: list[str]) -> list[str]:
    """
    Validate that only known, safe tools are requested.

    Args:
        tools: List of tool names to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not isinstance(tools, list):
        errors.append(f"Tools must be a list, got: {type(tools).__name__}")
        return errors

    if not tools:
        return errors

    # Check for unknown tools
    unknown_tools = set(tools) - ALLOWED_TOOLS
    if unknown_tools:
        errors.append(
            f"Unknown or disallowed tools: {', '.join(sorted(unknown_tools))}. "
            f"Allowed tools: {', '.join(sorted(ALLOWED_TOOLS))}"
        )

    # Check for duplicate tools
    if len(tools) != len(set(tools)):
        duplicates = [t for t in tools if tools.count(t) > 1]
        errors.append(f"Duplicate tools found: {', '.join(set(duplicates))}")

    return errors


def validate_mcp_server_permissions(mcp_servers: list[str]) -> list[str]:
    """
    Validate that only known, registered MCP servers are requested.

    Args:
        mcp_servers: List of MCP server names to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not isinstance(mcp_servers, list):
        errors.append(f"MCP servers must be a list, got: {type(mcp_servers).__name__}")
        return errors

    # Empty MCP server list is valid (some agents don't need MCP)
    if not mcp_servers:
        return errors

    # Check for unknown MCP servers
    unknown_servers = set(mcp_servers) - ALLOWED_MCP_SERVERS
    if unknown_servers:
        errors.append(
            f"Unknown or disallowed MCP servers: {', '.join(sorted(unknown_servers))}. "
            f"Allowed servers: {', '.join(sorted(ALLOWED_MCP_SERVERS))}"
        )

    # Check for duplicate servers
    if len(mcp_servers) != len(set(mcp_servers)):
        duplicates = [s for s in mcp_servers if mcp_servers.count(s) > 1]
        errors.append(f"Duplicate MCP servers found: {', '.join(set(duplicates))}")

    return errors


def validate_parameters(parameters: dict[str, Any]) -> list[str]:
    """
    Validate custom parameters for safety.

    Checks parameter names and values for dangerous patterns.

    Args:
        parameters: Dictionary of custom parameters

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

    # Check parameter names and values
    for key, value in parameters.items():
        # Validate parameter name
        if not isinstance(key, str) or not key.strip():
            errors.append(f"Invalid parameter name: {key}")
            continue

        # Check for dangerous patterns in parameter names
        for pattern in DANGEROUS_PARAMETER_PATTERNS:
            if re.search(pattern, key):
                errors.append(
                    f"Potentially dangerous parameter name: {key} (matches pattern: {pattern[:50]}...)"
                )

        # Check for dangerous patterns in string parameter values
        if isinstance(value, str):
            for pattern in DANGEROUS_PARAMETER_PATTERNS:
                if re.search(pattern, value):
                    errors.append(
                        f"Potentially dangerous parameter value for '{key}': {value[:50]}... "
                        f"(matches pattern: {pattern[:50]}...)"
                    )

    return errors


def validate_safety_constraints(template: AgentTemplate) -> list[str]:
    """
    Validate additional safety constraints on templates.

    Enforces policies like:
    - Templates with Bash tool must have at least Read tool
    - Templates with Write/Edit must have Read tool
    - Dangerous tool combinations

    Args:
        template: AgentTemplate instance to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    tools = set(template.tools)

    # If Bash is enabled, Read must also be enabled (for reviewing commands)
    if "Bash" in tools and "Read" not in tools:
        errors.append(
            "Safety constraint violation: Templates with 'Bash' tool must also include 'Read' tool "
            "(needed to review code before execution)"
        )

    # If Write or Edit is enabled, Read should be enabled (for reviewing existing code)
    if ("Write" in tools or "Edit" in tools) and "Read" not in tools:
        errors.append(
            "Safety constraint violation: Templates with 'Write' or 'Edit' must also include 'Read' tool "
            "(needed to review existing code before modification)"
        )

    # Warn if template has minimal tools (might not be useful)
    if 0 < len(tools) < 2:
        errors.append(
            f"Warning: Template only has {len(tools)} tool(s). "
            "Consider adding more tools for better functionality."
        )

    return errors


def validate_import(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate template data from import (before creating AgentTemplate instance).

    This is used when importing templates from external sources (JSON files,
    marketplace, etc.) to catch security issues before instantiation.

    Performs comprehensive security checks:
    1. Field validation (required fields, types)
    2. Import statement detection (no Python imports in custom_prompt)
    3. URL validation (repo_url, doc_url)
    4. File path validation
    5. Unexpected field detection
    6. Deep parameter validation

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

    if "tools" in data and not isinstance(data["tools"], list):
        errors.append(
            f"Field 'tools' must be a list, got: {type(data['tools']).__name__}"
        )

    if "mcp_servers" in data and not isinstance(data["mcp_servers"], list):
        errors.append(
            f"Field 'mcp_servers' must be a list, got: {type(data['mcp_servers']).__name__}"
        )

    if "parameters" in data and not isinstance(data["parameters"], dict):
        errors.append(
            f"Field 'parameters' must be a dictionary, got: {type(data['parameters']).__name__}"
        )

    # Security: Validate URLs (repo_url, doc_url)
    url_errors = validate_urls(data)
    errors.extend(url_errors)

    # Security: Validate file paths in any field
    path_errors = validate_file_paths(data)
    errors.extend(path_errors)

    # Security: Check for import statements in custom_prompt
    if "custom_prompt" in data and isinstance(data["custom_prompt"], str):
        import_errors = validate_import_statements(data["custom_prompt"])
        errors.extend(import_errors)

    # Security: Deep validate parameters if present
    if "parameters" in data and isinstance(data["parameters"], dict):
        deep_errors = validate_deep_parameters(data["parameters"])
        errors.extend(deep_errors)

    # If basic validation passes, create template and run full validation
    if not errors:
        try:
            template = AgentTemplate.from_dict(data)
            is_valid, validation_errors = validate_template(template)
            errors.extend(validation_errors)
        except Exception as e:
            errors.append(f"Failed to create template from import data: {e}")

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_import_statements(prompt: str) -> list[str]:
    """
    Validate that custom_prompt does not contain Python import statements.

    Import statements in prompts could indicate attempts to:
    - Execute arbitrary code
    - Access dangerous modules (os, sys, subprocess)
    - Bypass security restrictions

    Args:
        prompt: Custom prompt text to validate

    Returns:
        List of error messages (empty if safe)
    """
    errors = []

    if not prompt or not prompt.strip():
        return errors

    # Check for import statement patterns
    for pattern in IMPORT_STATEMENT_PATTERNS:
        matches = re.findall(pattern, prompt, re.MULTILINE)
        if matches:
            # Extract the import statement for better error reporting
            import_lines = [
                line.strip() for line in prompt.split("\n") if re.search(pattern, line)
            ]
            if import_lines:
                errors.append(
                    f"Python import statement detected in custom_prompt: '{import_lines[0][:80]}'. "
                    f"Import statements are not allowed in custom prompts for security reasons."
                )

    # Check for dangerous module references (even without explicit import)
    for module in DANGEROUS_IMPORT_MODULES:
        # Look for module references like "os.path", "sys.argv", etc.
        # Use word boundaries to avoid false positives
        module_pattern = r"\b" + re.escape(module) + r"\b"
        if re.search(module_pattern, prompt):
            # Only warn if it looks like actual usage (module.attribute), not just documentation
            context_patterns = [
                rf"\b{re.escape(module)}\.[A-Za-z_][A-Za-z0-9_]*\b",  # module.attribute
            ]
            if any(re.search(p, prompt) for p in context_patterns):
                errors.append(
                    f"Reference to dangerous Python module '{module}' detected in custom_prompt. "
                    f"System modules (os, sys, subprocess, etc.) are not allowed in custom prompts."
                )
                break  # Only report first dangerous module to avoid spam

    return errors


def _is_private_host(hostname: str) -> bool:
    """Check if a hostname resolves to a private/local address."""
    if not hostname:
        return False
    if hostname in {"localhost", ""}:
        return True
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_reserved
    except ValueError:
        return False


def validate_urls(data: dict[str, Any]) -> list[str]:
    """
    Validate URL fields in template data for security.

    Checks:
    - URLs use safe protocols (http, https)
    - No javascript: or data: URLs (XSS risk)
    - No localhost/127.0.0.1 references (SSRF risk)

    Args:
        data: Template data dictionary

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # URL fields to validate
    url_fields = ["repo_url", "doc_url"]

    for field in url_fields:
        if field not in data or not data[field]:
            continue

        url = data[field]
        if not isinstance(url, str):
            errors.append(
                f"Field '{field}' must be a string, got: {type(url).__name__}"
            )
            continue

        # Check for dangerous protocols
        dangerous_protocols = ["javascript:", "data:", "file:", "ftp:"]
        url_lower = url.lower()
        for protocol in dangerous_protocols:
            if url_lower.startswith(protocol):
                errors.append(
                    f"Unsafe URL protocol in '{field}': {protocol}. "
                    f"Only http:// and https:// URLs are allowed."
                )

        # Check for SSRF risks (localhost, internal IPs) using proper URL parsing
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if _is_private_host(hostname):
                errors.append(
                    f"Potentially unsafe URL in '{field}': {url}. "
                    f"Local/internal network addresses are not allowed."
                )
        except Exception:
            errors.append(f"Could not parse URL in '{field}': {url}.")

    return errors


def validate_file_paths(data: dict[str, Any]) -> list[str]:
    """
    Validate file paths in template data for security.

    Checks for:
    - Path traversal attempts (../..)
    - Absolute paths (should be relative)
    - Suspicious file extensions

    Args:
        data: Template data dictionary

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check string fields for potential file paths
    string_fields = ["name", "description", "category", "custom_prompt"]

    for field in string_fields:
        if field not in data or not data[field]:
            continue

        value = data[field]
        if not isinstance(value, str):
            continue

        # Check for path traversal
        if "../" in value or "..\\" in value:
            errors.append(
                f"Path traversal pattern detected in field '{field}'. "
                f"Relative path traversal (../) is not allowed."
            )

        # Check for absolute paths (Unix / Windows)
        # Unix absolute path starts with /
        if re.match(r"^/[a-zA-Z0-9_]", value):
            errors.append(
                f"Absolute file path detected in field '{field}': {value[:50]}. "
                f"Absolute paths are not allowed in template fields."
            )

        # Windows absolute path (C:\, D:\, etc.)
        if re.match(r"^[A-Za-z]:\\", value):
            errors.append(
                f"Absolute file path detected in field '{field}': {value[:50]}. "
                f"Absolute paths are not allowed in template fields."
            )

    return errors


def validate_deep_parameters(parameters: dict[str, Any]) -> list[str]:
    """
    Deep validate parameter dictionary for nested security issues.

    Recursively checks:
    - Nested dictionaries
    - Lists with potentially malicious content
    - String values with dangerous patterns

    Args:
        parameters: Parameters dictionary

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    def _validate_value(key: str, value: Any, path: str = "") -> None:
        """Recursively validate a value."""
        current_path = f"{path}.{key}" if path else key

        if isinstance(value, dict):
            # Recursively validate nested dicts
            for nested_key, nested_value in value.items():
                _validate_value(nested_key, nested_value, current_path)

        elif isinstance(value, list):
            # Validate each list item
            for i, item in enumerate(value):
                _validate_value(f"[{i}]", item, current_path)

        elif isinstance(value, str):
            # Check for dangerous patterns in strings
            for pattern in DANGEROUS_PARAMETER_PATTERNS:
                if re.search(pattern, value):
                    errors.append(
                        f"Potentially dangerous value in parameter '{current_path}': {value[:50]}... "
                        f"(matches pattern: {pattern[:50]}...)"
                    )
                    break  # Only report first match per value

            # Check for path traversal
            if "../" in value or "..\\" in value:
                errors.append(
                    f"Path traversal pattern detected in parameter '{current_path}': {value[:50]}..."
                )

            # Check for excessive length (prevent DoS)
            if len(value) > 10000:
                errors.append(
                    f"Parameter '{current_path}' value is too long ({len(value)} chars). "
                    f"Maximum allowed: 10000 chars"
                )

    # Validate all parameters
    for key, value in parameters.items():
        _validate_value(key, value)

    return errors


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
