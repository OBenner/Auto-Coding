"""
Error Codes
===========

Typed error codes for structured error handling.
Provides a comprehensive enum of all error types with unique auto-generated values.
"""

from enum import Enum, auto


class ErrorCode(Enum):
    """Typed error codes for structured error handling across the system."""

    # Authentication & Authorization Errors
    AUTH_INVALID = auto()
    """Invalid API key or credentials."""

    AUTH_EXPIRED = auto()
    """OAuth token or session has expired."""

    AUTH_MISSING = auto()
    """No authentication credentials provided."""

    # Billing & Quota Errors
    BILLING_EXHAUSTED = auto()
    """Account credits exhausted or payment required."""

    QUOTA_EXCEEDED = auto()
    """Usage quota exceeded."""

    # Rate Limiting & Throttling
    RATE_LIMITED = auto()
    """Request rate limit exceeded."""

    RATE_LIMIT_HARD = auto()
    """Hard rate limit (longer backoff required)."""

    # Network & Connectivity
    NETWORK = auto()
    """General network error (connection, timeout, etc.)."""

    NETWORK_UNREACHABLE = auto()
    """Host or service unreachable."""

    NETWORK_TIMEOUT = auto()
    """Connection or read timeout."""

    # API & Service Errors
    OVERLOADED = auto()
    """API service overloaded (503)."""

    SERVICE_UNAVAILABLE = auto()
    """Service temporarily unavailable."""

    INTERNAL_ERROR = auto()
    """API internal error (500)."""

    BAD_GATEWAY = auto()
    """Bad gateway error (502)."""

    # Content & Context Errors
    CONTEXT_OVERFLOW = auto()
    """Request exceeds context window."""

    PROMPT_TOO_LONG = auto()
    """Prompt text exceeds maximum length."""

    TOKEN_LIMIT_EXCEEDED = auto()
    """Token count exceeds model limit."""

    # Request & Validation Errors
    INVALID_REQUEST = auto()
    """Malformed or invalid request."""

    MISSING_PARAMETER = auto()
    """Required parameter not provided."""

    INVALID_PARAMETER = auto()
    """Parameter value is invalid."""

    # Agent & Session Errors
    STUCK_LOOP = auto()
    """Agent stuck in a repetitive loop."""

    SESSION_TIMEOUT = auto()
    """Agent session timed out."""

    SESSION_TERMINATED = auto()
    """Agent session was terminated."""

    # Tool & Execution Errors
    TOOL_EXECUTION_FAILED = auto()
    """Tool execution failed."""

    TOOL_NOT_FOUND = auto()
    """Requested tool does not exist."""

    TOOL_PERMISSION_DENIED = auto()
    """Permission denied for tool operation."""

    BASH_COMMAND_ERROR = auto()
    """Bash command execution failed."""

    # File & Filesystem Errors
    FILE_NOT_FOUND = auto()
    """Requested file not found."""

    FILE_ACCESS_DENIED = auto()
    """Permission denied for file operation."""

    FILE_ALREADY_EXISTS = auto()
    """File already exists."""

    # Configuration Errors
    CONFIGURATION_ERROR = auto()
    """Invalid or missing configuration."""

    ENVIRONMENT_ERROR = auto()
    """Environment variable missing or invalid."""

    # Memory & Graphiti Errors
    MEMORY_ERROR = auto()
    """Graphiti memory system error."""

    MEMORY_CONNECTION_FAILED = auto()
    """Failed to connect to memory store."""

    # Integration Errors
    LINEAR_API_ERROR = auto()
    """Linear API integration error."""

    GITHUB_API_ERROR = auto()
    """GitHub API integration error."""

    # Unknown / Uncategorized
    UNKNOWN = auto()
    """Unknown or uncategorized error."""
