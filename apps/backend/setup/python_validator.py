"""
Python version validator for Auto Code setup wizard.

Validates that the Python interpreter meets the minimum version requirement
for Auto Code (Python 3.12+).
"""

import logging
import sys
from typing import TypedDict

logger = logging.getLogger(__name__)

# Minimum Python version required (major, minor)
REQUIRED_PYTHON_VERSION = (3, 12)


class PythonValidationResult(TypedDict):
    """Result of Python version validation."""

    valid: bool
    version: str
    required_version: str
    message: str


def validate_python_version() -> PythonValidationResult:
    """
    Validate that the current Python version meets minimum requirements.

    Returns:
        PythonValidationResult: Dictionary containing:
            - valid: True if Python version is sufficient, False otherwise
            - version: Current Python version string (e.g., "3.12.1")
            - required_version: Required Python version string (e.g., "3.12")
            - message: Human-readable success or error message

    Example:
        >>> result = validate_python_version()
        >>> if result['valid']:
        ...     print(f"Python {result['version']} is compatible")
        ... else:
        ...     print(result['message'])
    """
    try:
        # Get current Python version
        current_version = sys.version_info
        current_version_str = (
            f"{current_version.major}.{current_version.minor}.{current_version.micro}"
        )
        required_version_str = (
            f"{REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}"
        )

        # Check if version meets minimum requirement
        is_valid = current_version >= (*REQUIRED_PYTHON_VERSION, 0)

        if is_valid:
            message = (
                f"Python {current_version_str} meets the minimum requirement "
                f"of Python {required_version_str}+"
            )
            logger.info(message)
        else:
            message = (
                f"Error: Auto Code requires Python {required_version_str} or higher.\n"
                f"You are running Python {current_version_str}\n"
                f"\n"
                f"Please upgrade Python: https://www.python.org/downloads/"
            )
            logger.warning(
                f"Python version check failed: {current_version_str} < {required_version_str}"
            )

        return {
            "valid": is_valid,
            "version": current_version_str,
            "required_version": required_version_str,
            "message": message,
        }

    except Exception as e:
        # If we can't determine version, return error
        error_message = f"Failed to validate Python version: {e}"
        logger.error(error_message)
        return {
            "valid": False,
            "version": "unknown",
            "required_version": f"{REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}",
            "message": error_message,
        }


def get_python_info() -> dict[str, str]:
    """
    Get detailed information about the current Python interpreter.

    Returns:
        dict: Dictionary containing Python interpreter details:
            - version: Full version string
            - executable: Path to Python executable
            - platform: Platform identifier
            - implementation: Python implementation (CPython, PyPy, etc.)

    Useful for debugging and support requests.
    """
    return {
        "version": sys.version,
        "executable": sys.executable,
        "platform": sys.platform,
        "implementation": sys.implementation.name,
    }
