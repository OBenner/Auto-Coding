"""
Webhook Authentication System
==============================

Provides authentication and signature verification for webhook integrations.
Supports API keys, bearer tokens, basic auth, and HMAC signature verification.

Key Functions:
- generate_api_key: Generate cryptographically secure API keys
- verify_webhook_signature: Verify HMAC signatures for incoming webhooks
- verify_api_key: Validate API keys against stored config
- prepare_auth_headers: Prepare authentication headers for outgoing webhooks
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from base64 import b64decode
from typing import Literal

from .models import AuthenticationConfig, WebhookConfig

logger = logging.getLogger(__name__)

# =============================================================================
# API Key Generation
# =============================================================================


def generate_api_key(length: int = 32, prefix: str = "whsk_") -> str:
    """
    Generate a cryptographically secure random API key.

    API keys use a secure random generator (secrets module) and include
    a prefix for easy identification. The default configuration produces
    44-character keys (whsk_ + 32 random bytes in hex).

    Args:
        length: Number of random bytes (default: 32)
        prefix: Key prefix for identification (default: "whsk_")

    Returns:
        API key string with format: {prefix}{random_hex}

    Examples:
        >>> generate_api_key()
        'whsk_a1b2c3d4e5f6...'

        >>> generate_api_key(prefix="custom_")
        'custom_a1b2c3d4e5f6...'
    """
    # Generate cryptographically secure random bytes
    random_bytes = secrets.token_bytes(length)

    # Convert to hexadecimal string
    random_hex = random_bytes.hex()

    # Combine prefix with random data
    api_key = f"{prefix}{random_hex}"

    logger.debug(f"Generated API key with prefix: {prefix}")
    return api_key


def generate_webhook_secret(length: int = 32) -> str:
    """
    Generate a webhook secret for signature verification.

    Webhook secrets are used as HMAC keys to verify the authenticity of
    incoming webhook payloads. They should be kept confidential and
    shared only with the webhook sender.

    Args:
        length: Number of random bytes (default: 32)

    Returns:
        Random hex string suitable for use as HMAC secret

    Examples:
        >>> generate_webhook_secret()
        'a1b2c3d4e5f6...'
    """
    random_bytes = secrets.token_bytes(length)
    return random_bytes.hex()


# =============================================================================
# Signature Verification
# =============================================================================


def verify_webhook_signature(
    payload: bytes | str,
    signature: str,
    secret: str,
    algorithm: Literal["hmac_sha256", "hmac_sha512"] = "hmac_sha256",
    signature_header: str = "X-Hub-Signature-256",
) -> bool:
    """
    Verify HMAC signature for incoming webhook payload.

    This function implements the same signature verification used by GitHub,
    GitLab, and other webhook providers. It computes an HMAC of the payload
    using the shared secret and compares it with the provided signature.

    Args:
        payload: Raw webhook payload (bytes or string)
        signature: Signature from webhook header (e.g., "sha256=...")
        secret: Shared secret for HMAC computation
        algorithm: Hash algorithm to use ("hmac_sha256" or "hmac_sha512")
        signature_header: Header name for logging purposes

    Returns:
        True if signature is valid, False otherwise

    Examples:
        >>> secret = "my_webhook_secret"
        >>> payload = b'{"event": "test"}'
        >>> valid_sig = _compute_signature(payload, secret, "hmac_sha256")
        >>> verify_webhook_signature(payload, valid_sig, secret)
        True

        >>> verify_webhook_signature(payload, "invalid", secret)
        False
    """
    if not payload or not signature or not secret:
        logger.warning("Missing payload, signature, or secret")
        return False

    # Convert payload to bytes if necessary
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    # Compute expected signature
    try:
        expected_signature = _compute_signature(payload_bytes, secret, algorithm)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to compute signature: {e}")
        return False

    # Use constant-time comparison to prevent timing attacks
    # hmac.compare_digest is timing-attack safe
    is_valid = hmac.compare_digest(expected_signature, signature)

    if not is_valid:
        logger.debug(
            f"Signature verification failed for {signature_header}. "
            f"Expected: {expected_signature[:20]}..., Got: {signature[:20]}..."
        )
    else:
        logger.debug(f"Signature verified successfully for {signature_header}")

    return is_valid


def _compute_signature(
    payload: bytes,
    secret: str,
    algorithm: Literal["hmac_sha256", "hmac_sha512"],
) -> str:
    """
    Compute HMAC signature for payload.

    Args:
        payload: Payload bytes to sign
        secret: Secret key for HMAC
        algorithm: Hash algorithm ("hmac_sha256" or "hmac_sha512")

    Returns:
        Signature string with format: {hash_type}={hex_digest}

    Raises:
        ValueError: If algorithm is unsupported
    """
    # Convert secret to bytes
    secret_bytes = secret.encode("utf-8")

    # Select hash function
    if algorithm == "hmac_sha256":
        hash_func = hashlib.sha256
        hash_prefix = "sha256"
    elif algorithm == "hmac_sha512":
        hash_func = hashlib.sha512
        hash_prefix = "sha512"
    else:
        raise ValueError(f"Unsupported signature algorithm: {algorithm}")

    # Compute HMAC
    computed_hmac = hmac.new(secret_bytes, payload, hash_func)
    signature_hex = computed_hmac.hexdigest()

    return f"{hash_prefix}={signature_hex}"


def extract_signature_from_header(
    header_value: str,
) -> str | None:
    """
    Extract signature from header value.

    Handles various signature formats:
    - "sha256=..." (GitHub, GitLab)
    - "..." (plain hex)

    Args:
        header_value: Raw header value

    Returns:
        Signature string (with hash prefix) or None if invalid

    Examples:
        >>> extract_signature_from_header("sha256=abc123...")
        'sha256=abc123...'

        >>> extract_signature_from_header("invalid format")
        'invalid format'
    """
    if not header_value:
        return None

    header_value = header_value.strip()

    # Check if already has hash prefix
    if header_value.startswith(("sha256=", "sha512=")):
        return header_value

    # Return as-is for plain hex signatures
    return header_value


# =============================================================================
# Authentication Verification
# =============================================================================


def verify_api_key(
    provided_key: str | None,
    config: WebhookConfig,
) -> bool:
    """
    Verify API key against webhook configuration.

    Args:
        provided_key: API key from request header
        config: Webhook configuration with expected credentials

    Returns:
        True if API key matches, False otherwise

    Examples:
        >>> config = WebhookConfig(
        ...     id="test",
        ...     name="Test Webhook",
        ...     type=WebhookType.INCOMING,
        ...     integration=WebhookIntegration.GENERIC,
        ...     path="/webhook/test",
        ...     auth=AuthenticationConfig(
        ...         auth_type="api_key",
        ...         api_key="whsk_abc123"
        ...     )
        ... )
        >>> verify_api_key("whsk_abc123", config)
        True
        >>> verify_api_key("wrong_key", config)
        False
    """
    if not provided_key:
        logger.debug("No API key provided")
        return False

    auth_config = config.auth

    # Check if auth type is API key
    if auth_config.auth_type != "api_key":
        logger.debug(f"Auth type is {auth_config.auth_type}, not api_key")
        return False

    # Compare keys
    expected_key = auth_config.api_key
    if not expected_key:
        logger.warning("API key auth configured but no key stored")
        return False

    # Use constant-time comparison
    is_valid = hmac.compare_digest(provided_key, expected_key)

    if not is_valid:
        logger.debug(f"API key verification failed for webhook {config.id}")

    return is_valid


def verify_bearer_token(
    provided_token: str | None,
    config: WebhookConfig,
) -> bool:
    """
    Verify bearer token against webhook configuration.

    Args:
        provided_token: Bearer token from Authorization header
        config: Webhook configuration with expected credentials

    Returns:
        True if token matches, False otherwise
    """
    if not provided_token:
        logger.debug("No bearer token provided")
        return False

    # Remove "Bearer " prefix if present
    if provided_token.startswith("Bearer "):
        provided_token = provided_token[7:]

    auth_config = config.auth

    # Check if auth type is bearer token
    if auth_config.auth_type != "bearer_token":
        logger.debug(f"Auth type is {auth_config.auth_type}, not bearer_token")
        return False

    # Compare tokens
    expected_token = auth_config.api_key
    if not expected_token:
        logger.warning("Bearer token auth configured but no token stored")
        return False

    # Use constant-time comparison
    is_valid = hmac.compare_digest(provided_token, expected_token)

    if not is_valid:
        logger.debug(f"Bearer token verification failed for webhook {config.id}")

    return is_valid


def verify_basic_auth(
    auth_header: str | None,
    config: WebhookConfig,
) -> bool:
    """
    Verify HTTP basic authentication against webhook configuration.

    Args:
        auth_header: Authorization header value (e.g., "Basic base64(username:password)")
        config: Webhook configuration with expected credentials

    Returns:
        True if credentials match, False otherwise
    """
    if not auth_header:
        logger.debug("No Authorization header provided")
        return False

    auth_config = config.auth

    # Check if auth type is basic auth
    if auth_config.auth_type != "basic_auth":
        logger.debug(f"Auth type is {auth_config.auth_type}, not basic_auth")
        return False

    # Check if credentials are configured
    if not auth_config.username or not auth_config.password:
        logger.warning("Basic auth configured but no credentials stored")
        return False

    # Parse header
    if not auth_header.startswith("Basic "):
        logger.debug("Invalid Basic auth header format")
        return False

    try:
        # Decode base64 credentials (validate=True rejects malformed input)
        encoded_credentials = auth_header[6:]  # Remove "Basic "
        decoded_bytes = b64decode(encoded_credentials, validate=True)
        decoded_str = decoded_bytes.decode("utf-8")

        # Split username and password
        if ":" not in decoded_str:
            logger.debug("Invalid Basic auth credentials format")
            return False

        provided_username, provided_password = decoded_str.split(":", 1)

        # Compare credentials
        username_valid = hmac.compare_digest(
            provided_username,
            auth_config.username,
        )
        password_valid = hmac.compare_digest(
            provided_password,
            auth_config.password,
        )

        is_valid = username_valid and password_valid

        if not is_valid:
            logger.debug(f"Basic auth verification failed for webhook {config.id}")

        return is_valid

    except Exception as e:
        logger.error(f"Error decoding Basic auth credentials: {e}")
        return False


# =============================================================================
# Outgoing Webhook Authentication
# =============================================================================


def prepare_auth_headers(config: WebhookConfig) -> dict[str, str]:
    """
    Prepare authentication headers for outgoing webhook request.

    Args:
        config: Webhook configuration with auth settings

    Returns:
        Dictionary of headers to add to the request

    Examples:
        >>> config = WebhookConfig(
        ...     id="test",
        ...     name="Test Webhook",
        ...     type=WebhookType.OUTGOING,
        ...     integration=WebhookIntegration.SLACK,
        ...     url="https://hooks.slack.com/services/...",
        ...     events=[WebhookEventType.BUILD_COMPLETED],
        ...     auth=AuthenticationConfig(
        ...         auth_type="bearer_token",
        ...         api_key="xoxb-abc123"
        ...     )
        ... )
        >>> prepare_auth_headers(config)
        {'Authorization': 'Bearer xoxb-abc123'}
    """
    auth_config = config.auth
    headers: dict[str, str] = {}

    if auth_config.auth_type == "none":
        return headers

    elif auth_config.auth_type == "api_key":
        # Add API key to custom header
        if auth_config.api_key and auth_config.api_key_header:
            headers[auth_config.api_key_header] = auth_config.api_key
            logger.debug("Added API key to custom header")

    elif auth_config.auth_type == "bearer_token":
        # Add bearer token to Authorization header
        if auth_config.api_key:
            headers["Authorization"] = f"Bearer {auth_config.api_key}"
            logger.debug("Added bearer token to Authorization header")

    elif auth_config.auth_type == "basic_auth":
        # Add Basic auth credentials
        if auth_config.username and auth_config.password:
            credentials = f"{auth_config.username}:{auth_config.password}"
            import base64

            encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
            logger.debug("Added Basic auth to Authorization header")

    else:
        logger.warning(f"Unsupported auth type: {auth_config.auth_type}")

    return headers


def sign_webhook_payload(
    payload: bytes | str,
    secret: str,
    algorithm: Literal["hmac_sha256", "hmac_sha512"] = "hmac_sha256",
) -> str:
    """
    Sign webhook payload for outgoing webhooks.

    Computes HMAC signature and returns it in the format expected by
    common webhook providers (GitHub, GitLab, etc.).

    Args:
        payload: Webhook payload to sign
        secret: Secret key for HMAC
        algorithm: Hash algorithm to use

    Returns:
        Signature string ready for use in signature header

    Examples:
        >>> payload = b'{"event": "build_completed"}'
        >>> secret = "my_secret"
        >>> signature = sign_webhook_payload(payload, secret)
        >>> signature
        'sha256=abc123...'
    """
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    return _compute_signature(payload_bytes, secret, algorithm)


# =============================================================================
# Authentication Validation
# =============================================================================


def validate_auth_config(auth_config: AuthenticationConfig) -> list[str]:
    """
    Validate authentication configuration.

    Checks that required credentials are present for the selected auth type.

    Args:
        auth_config: Authentication configuration to validate

    Returns:
        List of validation error messages (empty if valid)

    Examples:
        >>> auth = AuthenticationConfig(auth_type="api_key", api_key="whsk_abc")
        >>> validate_auth_config(auth)
        []

        >>> auth = AuthenticationConfig(auth_type="api_key", api_key=None)
        >>> validate_auth_config(auth)
        ['API key is required for api_key auth type']
    """
    errors: list[str] = []

    if auth_config.auth_type == "none":
        return errors

    elif auth_config.auth_type == "api_key":
        if not auth_config.api_key:
            errors.append("API key is required for api_key auth type")
        if not auth_config.api_key_header:
            errors.append("API key header name is required")

    elif auth_config.auth_type == "bearer_token":
        if not auth_config.api_key:
            errors.append("Bearer token is required for bearer_token auth type")

    elif auth_config.auth_type == "basic_auth":
        if not auth_config.username:
            errors.append("Username is required for basic_auth")
        if not auth_config.password:
            errors.append("Password is required for basic_auth")

    elif auth_config.auth_type == "signature":
        if not auth_config.secret:
            errors.append("Secret is required for signature verification")
        if not auth_config.signature_header:
            errors.append("Signature header name is required")

    else:
        errors.append(f"Unknown auth type: {auth_config.auth_type}")

    return errors
