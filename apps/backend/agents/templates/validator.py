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

import logging
import re
from typing import Any

from agents.templates.models import AgentTemplate
from agents.tools_pkg import (
    BASE_READ_TOOLS,
    BASE_WRITE_TOOLS,
    CONTEXT7_TOOLS,
    ELECTRON_TOOLS,
    GRAPHITI_MCP_TOOLS,
    LINEAR_TOOLS,
    PUPPETEER_TOOLS,
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
        matches = re.findall(pattern, prompt, re.MULTILINE)
        if matches:
            errors.append(
                f"Potentially dangerous pattern detected in prompt: {pattern[:50]}... "
                f"(matched: {matches[0] if matches else 'N/A'})"
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
        errors.append("At least one tool must be specified")
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
        errors.append(
            f"MCP servers must be a list, got: {type(mcp_servers).__name__}"
        )
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
    if len(tools) < 2:
        errors.append(
            f"Warning: Template only has {len(tools)} tool(s). "
            "Consider adding more tools for better functionality."
        )

    return errors


def validate_import(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate template data from import (before creating AgentTemplate instance).

    This is used when importing templates from external sources (JSON files,
    marketplace, etc.) to catch issues before instantiation.

    Args:
        data: Dictionary containing template data

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate required fields are present
    required_fields = ["name", "description", "category"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Validate field types
    if "name" in data and not isinstance(data["name"], str):
        errors.append(f"Field 'name' must be a string, got: {type(data['name']).__name__}")

    if "description" in data and not isinstance(data["description"], str):
        errors.append(
            f"Field 'description' must be a string, got: {type(data['description']).__name__}"
        )

    if "category" in data and not isinstance(data["category"], str):
        errors.append(
            f"Field 'category' must be a string, got: {type(data['category']).__name__}"
        )

    if "tools" in data and not isinstance(data["tools"], list):
        errors.append(f"Field 'tools' must be a list, got: {type(data['tools']).__name__}")

    if "mcp_servers" in data and not isinstance(data["mcp_servers"], list):
        errors.append(
            f"Field 'mcp_servers' must be a list, got: {type(data['mcp_servers']).__name__}"
        )

    if "parameters" in data and not isinstance(data["parameters"], dict):
        errors.append(
            f"Field 'parameters' must be a dictionary, got: {type(data['parameters']).__name__}"
        )

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
