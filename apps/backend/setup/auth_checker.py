"""
Authentication checker for setup wizard.

Provides OAuth token validation for the setup wizard to verify
Claude SDK authentication status.
"""

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


class AuthCheckResult(TypedDict):
    """Result of OAuth token check."""

    authenticated: bool
    hasToken: bool
    message: str


def check_oauth_token() -> AuthCheckResult:
    """
    Check if Claude SDK OAuth token exists and is valid.

    Returns:
        AuthCheckResult: Dictionary with authentication status.

    The function checks for OAuth token in the system keychain
    using the core.auth module. Returns status indicating whether
    the user is authenticated and has a valid token.
    """
    try:
        from core.auth import get_auth_token

        token = get_auth_token()

        if token:
            logger.debug("OAuth token found in keychain")
            return AuthCheckResult(
                authenticated=True,
                hasToken=True,
                message="Authentication configured - OAuth token found in system keychain",
            )
        else:
            logger.debug("No OAuth token found in keychain")
            return AuthCheckResult(
                authenticated=False,
                hasToken=False,
                message="No authentication token found - please run 'claude' CLI and complete OAuth login",
            )

    except ImportError as e:
        logger.error(f"Failed to import authentication module: {e}")
        return AuthCheckResult(
            authenticated=False,
            hasToken=False,
            message=f"Authentication module not available: {e}",
        )
    except Exception as e:
        logger.error(f"Authentication check failed: {e}")
        return AuthCheckResult(
            authenticated=False,
            hasToken=False,
            message=f"Authentication check failed: {e}",
        )
