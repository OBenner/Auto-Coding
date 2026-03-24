# Error Handling

Auto Code's typed error system provides structured, type-safe error handling that replaces fragile string-based error detection with enum-based error codes and custom exception classes.

## Table of Contents

- [Overview](#overview)
- [Error Code System](#error-code-system)
- [Typed Exceptions](#typed-exceptions)
- [Error Detection](#error-detection)
- [SDK Error Integration](#sdk-error-integration)
- [Usage Examples](#usage-examples)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)
- [Reference](#reference)

## Overview

The typed error system provides **structured error handling** with the following benefits:

- **Type-safe error codes** - Replace string-based pattern matching with enum values
- **Rich metadata** - Error codes, messages, and programmatic error classification
- **IDE support** - Autocomplete and type checking for error handling
- **Backward compatibility** - Gradual migration from existing string-based detection
- **SDK integration** - Automatic conversion of API errors to typed exceptions

### What It Does

- **ErrorCode enum** - Comprehensive error types with auto-generated unique values
- **TypedError base class** - Exceptions with error_code field for structured error handling
- **Specific error subclasses** - AuthError, RateLimitError, NetworkError, etc.
- **Error detection helpers** - get_error_code() function for exception introspection
- **SDK error wrapping** - Automatic conversion of raw API errors to typed exceptions

### Key Benefits

✅ **Type safety** - No more fragile string matching on error messages
✅ **Programmatic classification** - isinstance() checks instead of regex patterns
✅ **Rich metadata** - Error codes, JSON serialization, structured data
✅ **Backward compatibility** - Existing code continues to work during migration
✅ **Zero overhead** - Lightweight implementation with minimal performance impact

## Error Code System

### ErrorCode Enum

**Location:** `apps/backend/core/error_codes.py`

The `ErrorCode` enum defines all error types with auto-generated unique values:

```python
from enum import Enum, auto

class ErrorCode(Enum):
    # Authentication & Authorization Errors
    AUTH_INVALID = auto()
    AUTH_EXPIRED = auto()
    AUTH_MISSING = auto()

    # Billing & Quota Errors
    BILLING_EXHAUSTED = auto()
    QUOTA_EXCEEDED = auto()

    # Rate Limiting & Throttling
    RATE_LIMITED = auto()
    RATE_LIMIT_HARD = auto()

    # Network & Connectivity
    NETWORK = auto()
    NETWORK_UNREACHABLE = auto()
    NETWORK_TIMEOUT = auto()

    # API & Service Errors
    OVERLOADED = auto()
    SERVICE_UNAVAILABLE = auto()
    INTERNAL_ERROR = auto()
    BAD_GATEWAY = auto()

    # Content & Context Errors
    CONTEXT_OVERFLOW = auto()
    PROMPT_TOO_LONG = auto()
    TOKEN_LIMIT_EXCEEDED = auto()

    # Request & Validation Errors
    INVALID_REQUEST = auto()
    MISSING_PARAMETER = auto()
    INVALID_PARAMETER = auto()

    # Agent & Session Errors
    STUCK_LOOP = auto()
    SESSION_TIMEOUT = auto()
    SESSION_TERMINATED = auto()

    # Tool & Execution Errors
    TOOL_EXECUTION_FAILED = auto()
    TOOL_NOT_FOUND = auto()
    TOOL_PERMISSION_DENIED = auto()
    BASH_COMMAND_ERROR = auto()

    # File & Filesystem Errors
    FILE_NOT_FOUND = auto()
    FILE_ACCESS_DENIED = auto()
    FILE_ALREADY_EXISTS = auto()

    # Configuration Errors
    CONFIGURATION_ERROR = auto()
    ENVIRONMENT_ERROR = auto()

    # Memory & Graphiti Errors
    MEMORY_ERROR = auto()
    MEMORY_CONNECTION_FAILED = auto()

    # Integration Errors
    LINEAR_API_ERROR = auto()
    GITHUB_API_ERROR = auto()

    # Unknown / Uncategorized
    UNKNOWN = auto()
```

### Error Categories

Error codes are organized by category for easier handling:

```python
# Authentication
AUTH_INVALID, AUTH_EXPIRED, AUTH_MISSING

# Rate Limiting
RATE_LIMITED, RATE_LIMIT_HARD

# Network
NETWORK, NETWORK_UNREACHABLE, NETWORK_TIMEOUT

# API Service Issues
OVERLOADED, SERVICE_UNAVAILABLE, INTERNAL_ERROR, BAD_GATEWAY

# Context Issues
CONTEXT_OVERFLOW, PROMPT_TOO_LONG, TOKEN_LIMIT_EXCEEDED

# Agent Issues
STUCK_LOOP, SESSION_TIMEOUT, SESSION_TERMINATED

# Tool Issues
TOOL_EXECUTION_FAILED, TOOL_NOT_FOUND, TOOL_PERMISSION_DENIED, BASH_COMMAND_ERROR

# File Issues
FILE_NOT_FOUND, FILE_ACCESS_DENIED, FILE_ALREADY_EXISTS
```

## Typed Exceptions

### TypedError Base Class

**Location:** `apps/backend/core/typed_errors.py`

The `TypedError` base class provides structured error handling with error codes:

```python
class TypedError(Exception):
    """Base exception class with typed error code field.

    Provides structured error handling with error codes that can be
    programmatically inspected and matched.

    Args:
        error_code: ErrorCode enum value identifying the error type
        message: Human-readable error message

    Example:
        >>> raise TypedError(ErrorCode.AUTH_INVALID, "Invalid API key")
    """

    def __init__(self, error_code: ErrorCode, message: str):
        """Initialize TypedError with error code and message."""
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation including error code."""
        return f"[{self.error_code.name}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code.name,
            "message": self.message
        }

    def to_json(self) -> str:
        """Convert error to JSON string."""
        return json.dumps(self.to_dict())
```

### Specific Error Subclasses

Pre-defined error subclasses for common error types:

```python
class AuthError(TypedError):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(ErrorCode.AUTH_INVALID, message)

class RateLimitError(TypedError):
    """Raised when API rate limits are exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(ErrorCode.RATE_LIMITED, message)

class NetworkError(TypedError):
    """Raised when network operations fail."""

    def __init__(self, message: str = "Network error"):
        super().__init__(ErrorCode.NETWORK, message)

class OperationTimeoutError(TypedError):
    """Raised when an operation times out."""

    def __init__(self, message: str = "Operation timed out"):
        super().__init__(ErrorCode.NETWORK_TIMEOUT, message)

class ValidationError(TypedError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(ErrorCode.INVALID_REQUEST, message)

class NotFoundError(TypedError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(ErrorCode.NOT_FOUND, message)

class ConfigurationError(TypedError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str = "Configuration error"):
        super().__init__(ErrorCode.INVALID_REQUEST, message)
```

### Creating Custom Errors

Create custom error classes for specific use cases:

```python
class DatabaseError(TypedError):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database error"):
        super().__init__(ErrorCode.INTERNAL_ERROR, message)

class AgentStuckError(TypedError):
    """Raised when agent is stuck in a loop."""

    def __init__(self, message: str = "Agent stuck in repetitive loop"):
        super().__init__(ErrorCode.STUCK_LOOP, message)

class MemoryConnectionError(TypedError):
    """Raised when Graphiti memory connection fails."""

    def __init__(self, message: str = "Memory system connection failed"):
        super().__init__(ErrorCode.MEMORY_CONNECTION_FAILED, message)
```

## Error Detection

### get_error_code() Helper Function

**Location:** `apps/backend/core/error_detection.py`

The `get_error_code()` function performs introspection on exceptions to extract error codes:

```python
def get_error_code(error: Exception) -> ErrorCode | None:
    """Extract error code from a typed exception.

    This function performs introspection on exceptions to determine if they
    are typed errors (instances of TypedError) and extracts the associated
    ErrorCode enum value. For non-typed exceptions, it returns None.

    Args:
        error: The exception to inspect

    Returns:
        ErrorCode enum value if the exception is a TypedError, None otherwise

    Example:
        >>> from core.typed_errors import AuthError
        >>> get_error_code(AuthError())
        ErrorCode.AUTH_INVALID

        >>> get_error_code(Exception("generic error"))
        None
    """
    # Check if exception has an error_code attribute (TypedError instances)
    if hasattr(error, "error_code"):
        from core.error_codes import ErrorCode

        error_code = getattr(error, "error_code")
        # Validate that it's actually an ErrorCode enum value
        if isinstance(error_code, ErrorCode):
            return error_code

    return None
```

### Error Classification

**Location:** `apps/backend/core/error_classifier.py`

The `ErrorClassifier` has been updated to use typed error detection first, falling back to string-based matching:

```python
from core.error_detection import get_error_code

def classify_exception(error: Exception) -> ErrorCategory:
    """Classify an exception into error category.

    First checks for typed errors using get_error_code(), then falls back
    to string-based pattern matching for backward compatibility.

    Args:
        error: The exception to classify

    Returns:
        ErrorCategory enum value

    Example:
        >>> classify_exception(AuthError())
        ErrorCategory.AUTHENTICATION

        >>> classify_exception(Exception("rate limit exceeded"))
        ErrorCategory.RATE_LIMITING
    """
    # Check for typed errors first
    error_code = get_error_code(error)
    if error_code is not None:
        return _ERROR_CODE_TO_CATEGORY.get(error_code, ErrorCategory.UNKNOWN)

    # Fall back to string-based pattern matching
    error_message = str(error).lower()

    # Use regex patterns to classify (existing logic)
    # ...
```

## SDK Error Integration

### wrap_sdk_error() Function

**Location:** `apps/backend/core/error_detection.py`

The `wrap_sdk_error()` function converts raw SDK exceptions to typed errors:

```python
def wrap_sdk_error(error: Exception) -> Exception:
    """Wrap a raw SDK exception in a TypedError.

    This function converts raw SDK exceptions (from the Claude Agent SDK,
    Anthropic API, or other sources) into structured TypedError instances
    with appropriate error codes. This enables consistent error handling
    and programmatic error classification throughout the system.

    If the exception is already a TypedError instance, it is returned
    unchanged. Otherwise, the error message is analyzed to determine
    the appropriate error category and a new TypedError is created.

    Args:
        error: The exception to wrap

    Returns:
        A TypedError instance with the appropriate error code.
        Returns the original error if it's already a TypedError.

    Example:
        >>> try:
        ...     # Some SDK call that raises an exception
        ...     pass
        ... except Exception as e:
        ...     typed_error = wrap_sdk_error(e)
        ...     if hasattr(typed_error, 'error_code'):
        ...         print(f"Error code: {typed_error.error_code}")
        ...
        Error code: ErrorCode.AUTH_INVALID
    """
    from core.error_codes import ErrorCode
    from core.typed_errors import (
        AuthError,
        NetworkError,
        OperationTimeoutError,
        TypedError,
    )

    # If it's already a TypedError, return as-is
    if get_error_code(error) is not None:
        return error

    # Extract error message
    error_message = str(error)

    # Classify the error using pattern matching
    error_code = _classify_error_message(error_message)

    # Map ErrorCode to appropriate TypedError subclass
    error_class_mapping: dict[ErrorCode, type[TypedError]] = {
        ErrorCode.AUTH_INVALID: AuthError,
        ErrorCode.AUTH_EXPIRED: AuthError,
        ErrorCode.AUTH_MISSING: AuthError,
        ErrorCode.BILLING_EXHAUSTED: TypedError,
        ErrorCode.QUOTA_EXCEEDED: TypedError,
        ErrorCode.RATE_LIMITED: TypedError,
        ErrorCode.RATE_LIMIT_HARD: TypedError,
        ErrorCode.NETWORK: NetworkError,
        ErrorCode.NETWORK_UNREACHABLE: NetworkError,
        ErrorCode.NETWORK_TIMEOUT: OperationTimeoutError,
        ErrorCode.OVERLOADED: TypedError,
        ErrorCode.SERVICE_UNAVAILABLE: TypedError,
        ErrorCode.INTERNAL_ERROR: TypedError,
        ErrorCode.BAD_GATEWAY: NetworkError,
        ErrorCode.CONTEXT_OVERFLOW: TypedError,
        ErrorCode.PROMPT_TOO_LONG: TypedError,
        ErrorCode.TOKEN_LIMIT_EXCEEDED: TypedError,
        ErrorCode.UNKNOWN: TypedError,
    }

    # Get the appropriate error class
    error_class = error_class_mapping.get(error_code, TypedError)

    # Create and return the typed error
    if error_class is TypedError:
        return error_class(error_code, error_message)
    else:
        # Subclasses have their own error_code defaults, just pass message
        return error_class(error_message)
```

### Client Integration

**Location:** `apps/backend/core/client.py`

The Claude SDK client now wraps SDK errors in typed exceptions:

```python
from core.error_detection import wrap_sdk_error

def create_client(project_dir: Path, spec_dir: Path, **options) -> ClaudeSDKClient:
    """Create a Claude SDK client with error handling.

    Args:
        project_dir: Path to the project directory
        spec_dir: Path to the spec directory
        **options: Additional options for the client

    Returns:
        Configured ClaudeSDKClient instance

    Raises:
        TypedError: If client initialization fails, wrapped with appropriate error code
    """
    try:
        # Existing client creation logic
        options_kwargs = {
            **options,
            **get_agent_options(),
            **get_mcp_options(),
        }
        client = ClaudeSDKClient(options=ClaudeAgentOptions(**options_kwargs))
        return client
    except Exception as e:
        # Wrap SDK errors with typed errors
        raise wrap_sdk_error(e) from e
```

## Usage Examples

### Basic Error Handling

```python
from core.error_codes import ErrorCode
from core.typed_errors import AuthError, NetworkError, TypedError
from core.error_detection import get_error_code

try:
    # Code that might raise exceptions
    result = risky_operation()
except AuthError as e:
    print(f"Authentication failed: {e}")
    print(f"Error code: {e.error_code}")
    # Handle auth error specifically
except NetworkError as e:
    print(f"Network error: {e}")
    print(f"Error code: {e.error_code}")
    # Retry or show offline message
except TypedError as e:
    print(f"System error: {e}")
    print(f"Error code: {e.error_code}")
    # Handle other typed errors
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle generic exceptions
```

### Error Classification

```python
from core.error_classifier import ErrorClassifier
from core.error_detection import get_error_code

def handle_error(error: Exception) -> str:
    """Handle different types of errors appropriately."""

    # Get error code for typed errors
    error_code = get_error_code(error)
    if error_code:
        print(f"Typed error: {error_code.name}")

        if error_code in [ErrorCode.AUTH_INVALID, ErrorCode.AUTH_EXPIRED]:
            return "Please check your credentials and try again"
        elif error_code == ErrorCode.RATE_LIMITED:
            return "Too many requests, please wait and try again"
        elif error_code == ErrorCode.CONTEXT_OVERFLOW:
            return "Request too large, please reduce the size"

    # Fallback to string-based classification
    category = ErrorClassifier.classify_exception(error)

    if category == ErrorCategory.AUTHENTICATION:
        return "Authentication failed"
    elif category == ErrorCategory.RATE_LIMITING:
        return "Rate limit exceeded"
    elif category == ErrorCategory.NETWORK:
        return "Network error, check your connection"
    else:
        return "An unexpected error occurred"
```

### SDK Error Handling

```python
from core.client import create_client

try:
    # Create client with automatic error wrapping
    client = create_client(
        project_dir=Path("/path/to/project"),
        spec_dir=Path("/path/to/spec")
    )

    # Use client - errors will be automatically wrapped
    response = client.create_agent_session("test-agent")

except AuthError as e:
    print(f"Authentication failed: {e}")
    # Prompt user to re-authenticate
except NetworkError as e:
    print(f"Network error: {e}")
    # Show offline mode or retry
except OperationTimeoutError as e:
    print(f"Operation timed out: {e}")
    # Increase timeout or split into smaller operations
except TypedError as e:
    print(f"System error: {e}")
    # Log and show generic error message
```

### Custom Error Creation

```python
from core.typed_errors import TypedError, ErrorCode
from core.error_detection import get_error_code

def create_resource(resource_type: str, resource_data: dict) -> dict:
    """Create a resource with proper error handling."""

    try:
        # Validate input
        if not resource_data:
            raise ValidationError("Resource data cannot be empty")

        # Check if resource exists
        if resource_exists(resource_type, resource_data):
            raise TypedError(
                ErrorCode.FILE_ALREADY_EXISTS,
                f"{resource_type} already exists"
            )

        # Create resource
        result = create_resource_in_database(resource_type, resource_data)

        return result

    except ValidationError as e:
        print(f"Validation error: {e}")
        # Show validation message to user
    except TypedError as e:
        print(f"Error creating {resource_type}: {e}")
        # Handle specific error types
    except Exception as e:
        error_code = get_error_code(e)
        if error_code == ErrorCode.QUOTA_EXCEEDED:
            print("Resource limit reached, please upgrade your plan")
        else:
            print(f"Unexpected error: {e}")
```

## Migration Guide

### From String-Based to Typed Errors

#### Step 1: Update Import Statements

**Before:**
```python
from core.error_utils import is_rate_limit_error, is_authentication_error
```

**After:**
```python
from core.error_utils import is_rate_limit_error, is_authentication_error
from core.typed_errors import AuthError, RateLimitError
from core.error_detection import get_error_code
```

#### Step 2: Update Error Detection Logic

**Before:**
```python
def handle_api_error(error: Exception):
    if is_rate_limit_error(error):
        print("Rate limit exceeded")
    elif is_authentication_error(error):
        print("Authentication failed")
    else:
        print("Unknown error")
```

**After:**
```python
def handle_api_error(error: Exception):
    # Check for typed errors first
    if isinstance(error, RateLimitError):
        print("Rate limit exceeded")
    elif isinstance(error, AuthError):
        print("Authentication failed")
    # Fallback to string-based detection
    elif is_rate_limit_error(error):
        print("Rate limit exceeded")
    elif is_authentication_error(error):
        print("Authentication failed")
    else:
        print("Unknown error")
```

#### Step 3: Add Error Code Handling

**Before:**
```python
try:
    result = api_call()
except Exception as e:
    if "429" in str(e):
        handle_rate_limit()
    elif "401" in str(e):
        handle_auth_error()
    else:
        handle_generic_error(e)
```

**After:**
```python
try:
    result = api_call()
except RateLimitError as e:
    handle_rate_limit()
    print(f"Error code: {e.error_code}")
except AuthError as e:
    handle_auth_error()
    print(f"Error code: {e.error_code}")
except Exception as e:
    error_code = get_error_code(e)
    if error_code == ErrorCode.RATE_LIMITED:
        handle_rate_limit()
    elif error_code == ErrorCode.AUTH_INVALID:
        handle_auth_error()
    else:
        handle_generic_error(e)
```

#### Step 4: Update Exception Handling

**Before:**
```python
def process_user_data(user_data: dict):
    if not user_data:
        raise ValueError("User data cannot be empty")

    # Process data
    result = process_data(user_data)
    return result
```

**After:**
```python
from core.typed_errors import ValidationError

def process_user_data(user_data: dict):
    if not user_data:
        raise ValidationError("User data cannot be empty")

    # Process data
    result = process_data(user_data)
    return result
```

### Migration Strategy

1. **Phase 1: Enable Typed Detection**
   - Update imports to include typed error classes
   - Add `isinstance()` checks for common error types
   - Keep existing string-based logic as fallback

2. **Phase 2: Add Error Code Handling**
   - Use `get_error_code()` to extract error codes
   - Handle errors by error code enum values
   - Add custom error classes for specific use cases

3. **Phase 3: Replace String-Based Logic**
   - Gradually replace string-based patterns with typed checks
   - Remove regex pattern matching for errors you handle with typed classes
   - Keep minimal string-based fallback for unknown errors

4. **Phase 4: Complete Migration**
   - Remove deprecated string-based functions
   - Update all error handling to use typed errors
   - Remove backward compatibility fallbacks

### Backward Compatibility

The typed error system maintains full backward compatibility during migration:

```python
# Old code continues to work
from core.error_utils import is_rate_limit_error

def handle_error(error: Exception):
    if is_rate_limit_error(error):
        # Still works for both typed and string-based errors
        handle_rate_limit()
```

### Deprecation Handling

String-based functions emit deprecation warnings when used:

```bash
$ python -W default::DeprecationWarning -c "
from core.error_utils import is_rate_limit_error
is_rate_limit_error(Exception('429 too many requests'))
"
<string>:1: DeprecationWarning: is_rate_limit_error() is deprecated. Use isinstance(error, RateLimitError) for typed errors, or migrate to error code-based handling.
```

## Best Practices

### 1. Use Specific Error Types

```python
# Good: Use specific error types
try:
    user = authenticate_user(email, password)
except AuthError as e:
    show_login_form()
    show_error_message("Invalid credentials")

# Avoid: Generic exception handling
try:
    user = authenticate_user(email, password)
except Exception as e:
    show_error_message("Error")  # Not specific enough
```

### 2. Always Include Error Codes

```python
# Good: Include error code in logging
except AuthError as e:
    logger.error(f"Auth failed: {e}, code: {e.error_code}")
    # Show user-friendly message
    show_error("Invalid credentials")

# Avoid: Don't lose error code information
except Exception as e:
    logger.error(f"Error: {e}")  # Lost error code
```

### 3. Use Error Classification for Handling

```python
# Good: Classify errors and handle by category
def handle_agent_error(error: Exception):
    error_code = get_error_code(error)

    if error_code == ErrorCode.STUCK_LOOP:
        handle_stuck_loop()
    elif error_code == ErrorCode.SESSION_TIMEOUT:
        handle_session_timeout()
    elif error_code == ErrorCode.CONTEXT_OVERFLOW:
        handle_context_overflow()
    else:
        handle_generic_error(error)
```

### 4. Create Custom Error Classes

```python
# Good: Create domain-specific error classes
class AgentError(TypedError):
    """Base class for agent-related errors"""
    def __init__(self, message: str, error_code: ErrorCode):
        super().__init__(error_code, message)

class AgentTimeoutError(AgentError):
    """Raised when agent operation times out"""
    def __init__(self, message: str = "Agent operation timed out"):
        super().__init__(message, ErrorCode.SESSION_TIMEOUT)
```

### 5. Use SDK Error Wrapping

```python
# Good: Let SDK errors be wrapped automatically
try:
    client = create_client(project_dir, spec_dir)
    response = client.create_agent_session("test")
except AuthError as e:
    # Automatically converted from raw SDK error
    handle_auth_error()
```

### 6. Maintain Error Message Chains

```python
# Good: Preserve original error context
try:
    user_data = validate_user_input(raw_data)
except ValidationError as e:
    raise ValidationError(
        f"Invalid user data: {e}",
    ) from e
```

### 7. Use Error Categories for High-Level Handling

```python
# Good: Handle error categories for user interface
def show_error_to_user(error: Exception):
    category = ErrorClassifier.classify_exception(error)

    if category == ErrorCategory.AUTHENTICATION:
        show_auth_error()
    elif category == ErrorCategory.RATE_LIMITING:
        show_rate_limit_error()
    elif category == ErrorCategory.NETWORK:
        show_network_error()
    else:
        show_generic_error()
```

### 8. Test Error Handling

```python
# Good: Test specific error types
def test_user_authentication():
    # Test with typed error
    with pytest.raises(AuthError):
        authenticate_user("invalid@email.com", "wrongpass")

    # Test error code extraction
    error = AuthError("Test")
    assert get_error_code(error) == ErrorCode.AUTH_INVALID
```

## Reference

### Core Files

- **`apps/backend/core/error_codes.py`** - ErrorCode enum definitions
- **`apps/backend/core/typed_errors.py`** - TypedError base class and subclasses
- **`apps/backend/core/error_detection.py`** - get_error_code() and wrap_sdk_error() functions
- **`apps/backend/core/error_classifier.py`** - Error classification with typed error support
- **`apps/backend/core/error_utils.py`** - Legacy string-based functions with deprecation warnings
- **`apps/backend/core/client.py`** - SDK client with automatic error wrapping

### API Reference

#### ErrorCode

```python
class ErrorCode(Enum):
    """All error types in the system."""

    # Authentication
    AUTH_INVALID = auto()
    AUTH_EXPIRED = auto()
    AUTH_MISSING = auto()

    # Rate Limiting
    RATE_LIMITED = auto()
    RATE_LIMIT_HARD = auto()

    # Network
    NETWORK = auto()
    NETWORK_UNREACHABLE = auto()
    NETWORK_TIMEOUT = auto()

    # And more...
```

#### TypedError

```python
class TypedError(Exception):
    """Base class for all typed errors."""

    def __init__(self, error_code: ErrorCode, message: str)
    def __str__(self) -> str
    def to_dict() -> dict[str, Any]
    def to_json() -> str
```

#### get_error_code()

```python
def get_error_code(error: Exception) -> ErrorCode | None:
    """Extract error code from exception."""
    # Returns ErrorCode enum or None for non-typed errors
```

#### wrap_sdk_error()

```python
def wrap_sdk_error(error: Exception) -> Exception:
    """Convert SDK errors to typed errors."""
    # Returns TypedError instance or original error if already typed
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ERROR_CODE_DEBUG` | Enable debug logging for error detection | `false` |
| `ERROR_DEPRECATION_WARNINGS` | Enable deprecation warnings for legacy functions | `true` |

### Error Patterns

#### Authentication Errors

```python
# Code 401, "authentication failed", "invalid api key"
AuthError(error_code=ErrorCode.AUTH_INVALID)
```

#### Rate Limit Errors

```python
# Code 429, "rate limit exceeded", "too many requests"
RateLimitError(error_code=ErrorCode.RATE_LIMITED)
```

#### Network Errors

```python
# Connection refused, timeout, unreachable
NetworkError(error_code=ErrorCode.NETWORK)
OperationTimeoutError(error_code=ErrorCode.NETWORK_TIMEOUT)
```

#### Context Errors

```python
# Context overflow, prompt too long, token limit exceeded
TypedError(error_code=ErrorCode.CONTEXT_OVERFLOW)
```

### Testing

#### Unit Testing Typed Errors

```python
def test_auth_error():
    error = AuthError("Invalid credentials")
    assert get_error_code(error) == ErrorCode.AUTH_INVALID
    assert "AUTH_INVALID" in str(error)

def test_sdk_wrapping():
    sdk_error = Exception("401 unauthorized")
    wrapped = wrap_sdk_error(sdk_error)
    assert isinstance(wrapped, AuthError)
    assert wrapped.error_code == ErrorCode.AUTH_INVALID
```

#### Integration Testing

```python
def test_error_classification():
    # Test typed error classification
    assert ErrorClassifier.classify_exception(AuthError()) == ErrorCategory.AUTHENTICATION

    # Test string-based fallback
    error = Exception("rate limit exceeded")
    assert ErrorClassifier.classify_exception(error) == ErrorCategory.RATE_LIMITING
```

---

**Questions or issues?** Check existing error handling tests in `tests/test_error_classifier.py` and `tests/test_sdk_error_wrapping.py` for usage examples.
