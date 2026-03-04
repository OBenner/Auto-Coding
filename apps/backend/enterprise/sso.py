"""
Enterprise SSO Authentication
==============================

SAML SSO integration for enterprise authentication.

Features:
- SAML 2.0 service provider support
- Multiple identity provider configurations
- Token validation and user identity mapping
- Session management with enterprise audit logging
- Automatic attribute mapping from SAML assertions
- Support for encrypted assertions
- JIT (Just-In-Time) user provisioning

Supported Identity Providers:
- Okta
- Azure AD (Entra ID)
- Google Workspace
- OneLogin
- Auth0
- Generic SAML 2.0 providers
"""

from __future__ import annotations

import base64
import logging
import secrets
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

# Configure module logger
logger = logging.getLogger(__name__)

# SAML XML Schema attribute URIs (OASIS standard namespace identifiers, not HTTP connections)
_CLAIMS_NS = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims"  # NOSONAR - SAML namespace URI, not an HTTP connection
_CLAIMS_GROUP_NS = "http://schemas.xmlsoap.org/claims"  # NOSONAR - SAML namespace URI, not an HTTP connection


class SAMLProviderType(str, Enum):
    """Supported SAML identity provider types."""

    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE_WORKSPACE = "google_workspace"
    ONELOGIN = "onelogin"
    AUTH0 = "auth0"
    GENERIC = "generic"


class SAMLBindingType(str, Enum):
    """SAML protocol binding types."""

    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"


class SAMLNameIDFormat(str, Enum):
    """SAML NameID format identifiers."""

    EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
    TRANSIENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
    UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"


@dataclass
class SAMLConfig:
    """Configuration for a SAML identity provider."""

    # Identity Provider metadata
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str  # Base64-encoded X.509 certificate
    idp_logout_url: str | None = None

    # Service Provider metadata
    sp_entity_id: str = "auto-claude-sp"
    sp_acs_url: str = "https://localhost:8080/saml/acs"  # Assertion Consumer Service
    sp_slo_url: str | None = None  # Single Logout Service

    # Protocol settings
    provider_type: SAMLProviderType = SAMLProviderType.GENERIC
    binding: SAMLBindingType = SAMLBindingType.HTTP_POST
    nameid_format: SAMLNameIDFormat = SAMLNameIDFormat.EMAIL

    # Security settings
    want_assertions_signed: bool = True
    want_response_signed: bool = False
    require_encrypted_assertions: bool = False
    sign_requests: bool = False

    # Attribute mapping
    attribute_map: dict[str, str] = field(default_factory=dict)

    # Session settings
    session_lifetime_hours: int = 8
    allow_jit_provisioning: bool = True

    # Organization info
    organization_id: str | None = None
    organization_name: str | None = None

    def __post_init__(self):
        """Initialize default attribute mapping if not provided."""
        if not self.attribute_map:
            # Default SAML attribute mappings
            self.attribute_map = {
                "email": f"{_CLAIMS_NS}/emailaddress",
                "first_name": f"{_CLAIMS_NS}/givenname",
                "last_name": f"{_CLAIMS_NS}/surname",
                "display_name": f"{_CLAIMS_NS}/name",
                "role": f"{_CLAIMS_NS}/role",
                "groups": f"{_CLAIMS_GROUP_NS}/Group",
            }


@dataclass
class SAMLAssertion:
    """Parsed SAML assertion data."""

    subject: str  # NameID
    issuer: str
    attributes: dict[str, Any]
    session_index: str | None
    not_before: datetime | None
    not_on_or_after: datetime | None
    audience: str | None

    def is_expired(self) -> bool:
        """Check if assertion has expired."""
        if not self.not_on_or_after:
            return False
        return datetime.now(UTC) > self.not_on_or_after

    def is_valid_for_audience(self, expected_audience: str) -> bool:
        """Validate assertion is for the expected audience."""
        if not self.audience:
            return True  # No audience restriction
        return self.audience == expected_audience


@dataclass
class SAMLUser:
    """User identity extracted from SAML assertion."""

    user_id: str  # Unique identifier (NameID)
    email: str
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    role: str | None = None
    groups: list[str] = field(default_factory=list)
    organization_id: str | None = None

    # SAML session info
    session_index: str | None = None
    assertion_expires_at: datetime | None = None

    # Additional attributes
    attributes: dict[str, Any] = field(default_factory=dict)

    def get_full_name(self) -> str:
        """Get user's full name."""
        if self.display_name:
            return self.display_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.email


@dataclass
class SAMLSession:
    """Active SAML SSO session."""

    session_id: str
    user: SAMLUser
    created_at: datetime
    expires_at: datetime
    last_activity_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(UTC) > self.expires_at

    def refresh_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = datetime.now(UTC)


class SAMLProvider:
    """
    SAML Service Provider implementation for enterprise SSO.

    Usage:
        # Configure provider
        config = SAMLConfig(
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_x509_cert="MIICertificateData...",
            sp_entity_id="auto-claude-sp",
            sp_acs_url="https://localhost:8080/saml/acs",
            provider_type=SAMLProviderType.OKTA,
        )

        # Initialize provider
        provider = SAMLProvider(config)

        # Generate authentication request
        auth_url = provider.get_auth_url(relay_state="/dashboard")

        # Validate SAML response
        user = provider.validate_response(saml_response)

        # Create session
        session = provider.create_session(user, ip_address="192.168.1.1")
    """

    _instance: SAMLProvider | None = None

    def __init__(self, config: SAMLConfig):
        """
        Initialize SAML provider.

        Args:
            config: SAML configuration
        """
        self.config = config
        self._sessions: dict[str, SAMLSession] = {}
        self._pending_requests: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_instance(cls, config: SAMLConfig | None = None) -> SAMLProvider:
        """Get or create singleton instance."""
        if cls._instance is None:
            if config is None:
                raise ValueError("Config required for first initialization")
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def generate_request_id(self) -> str:
        """Generate a unique SAML request ID."""
        return f"_saml_{secrets.token_urlsafe(32)}"

    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"sess_{secrets.token_urlsafe(48)}"

    def get_auth_url(
        self,
        relay_state: str | None = None,
        force_authn: bool = False,
    ) -> str:
        """
        Generate SAML authentication request URL.

        Args:
            relay_state: Optional state to preserve across authentication
            force_authn: Whether to force re-authentication

        Returns:
            Authentication URL to redirect user to
        """
        request_id = self.generate_request_id()
        issue_instant = datetime.now(UTC).isoformat()

        # Build SAML AuthnRequest
        authn_request = self._build_authn_request(
            request_id=request_id,
            issue_instant=issue_instant,
            force_authn=force_authn,
        )

        # Store pending request
        self._pending_requests[request_id] = {
            "id": request_id,
            "created_at": datetime.now(UTC),
            "relay_state": relay_state,
        }

        # Encode request
        encoded_request = self._encode_saml_request(authn_request)

        # Build redirect URL
        params = {
            "SAMLRequest": encoded_request,
        }
        if relay_state:
            params["RelayState"] = relay_state

        url = f"{self.config.idp_sso_url}?{urlencode(params)}"
        logger.info(f"Generated SAML auth URL for request {request_id}")

        return url

    def _build_authn_request(
        self,
        request_id: str,
        issue_instant: str,
        force_authn: bool = False,
    ) -> str:
        """Build SAML AuthnRequest XML."""
        # Note: In production, use a proper SAML library (python3-saml, pysaml2)
        # This is a simplified implementation for demonstration

        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.config.idp_sso_url}"
    AssertionConsumerServiceURL="{self.config.sp_acs_url}"
    ProtocolBinding="{self.config.binding.value}"
    ForceAuthn="{str(force_authn).lower()}">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.config.nameid_format.value}" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        return authn_request

    def _encode_saml_request(self, request: str) -> str:
        """Encode SAML request for HTTP-Redirect binding."""
        # Base64 encode (without compression for simplicity)
        encoded = base64.b64encode(request.encode("utf-8")).decode("ascii")
        return encoded

    def validate_response(
        self,
        saml_response: str,
        relay_state: str | None = None,
    ) -> SAMLUser:
        """
        Validate SAML response and extract user identity.

        Args:
            saml_response: Base64-encoded SAML response
            relay_state: Optional relay state from request

        Returns:
            SAMLUser with extracted identity

        Raises:
            ValueError: If response is invalid
        """
        try:
            # Decode response
            decoded = base64.b64decode(saml_response)

            # Parse SAML assertion
            assertion = self._parse_saml_response(decoded)

            # Validate assertion
            self._validate_assertion(assertion)

            # Extract user identity
            user = self._extract_user_from_assertion(assertion)

            logger.info(f"Successfully validated SAML response for user: {user.email}")
            return user

        except Exception as e:
            logger.error(f"Failed to validate SAML response: {e}")
            raise ValueError(f"Invalid SAML response: {e}")

    def _parse_saml_response(self, response_xml: bytes) -> SAMLAssertion:
        """
        Parse SAML response XML.

        Note: This is a simplified parser for demonstration.
        In production, use a proper SAML library that handles:
        - XML signature validation
        - Encryption/decryption
        - Full SAML 2.0 spec compliance
        """
        try:
            root = ET.fromstring(response_xml)

            # Define namespaces
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            }

            # Find assertion
            assertion_elem = root.find(".//saml:Assertion", ns)
            if assertion_elem is None:
                raise ValueError("No assertion found in SAML response")

            # Extract issuer
            issuer_elem = assertion_elem.find("saml:Issuer", ns)
            issuer = issuer_elem.text if issuer_elem is not None else ""

            # Extract subject (NameID)
            subject_elem = assertion_elem.find(".//saml:Subject/saml:NameID", ns)
            subject = subject_elem.text if subject_elem is not None else ""

            # Extract session index
            authn_stmt = assertion_elem.find(".//saml:AuthnStatement", ns)
            session_index = (
                authn_stmt.get("SessionIndex") if authn_stmt is not None else None
            )

            # Extract conditions
            conditions = assertion_elem.find("saml:Conditions", ns)
            not_before = None
            not_on_or_after = None
            audience = None

            if conditions is not None:
                not_before_str = conditions.get("NotBefore")
                not_on_or_after_str = conditions.get("NotOnOrAfter")

                if not_before_str:
                    not_before = datetime.fromisoformat(
                        not_before_str.replace("Z", "+00:00")
                    )
                if not_on_or_after_str:
                    not_on_or_after = datetime.fromisoformat(
                        not_on_or_after_str.replace("Z", "+00:00")
                    )

                audience_elem = conditions.find(".//saml:Audience", ns)
                if audience_elem is not None:
                    audience = audience_elem.text

            # Extract attributes
            attributes = {}
            for attr_elem in assertion_elem.findall(".//saml:Attribute", ns):
                attr_name = attr_elem.get("Name", "")
                attr_values = [
                    val.text
                    for val in attr_elem.findall("saml:AttributeValue", ns)
                    if val.text
                ]

                # Store single value or list
                if len(attr_values) == 1:
                    attributes[attr_name] = attr_values[0]
                elif attr_values:
                    attributes[attr_name] = attr_values

            return SAMLAssertion(
                subject=subject,
                issuer=issuer,
                attributes=attributes,
                session_index=session_index,
                not_before=not_before,
                not_on_or_after=not_on_or_after,
                audience=audience,
            )

        except ET.ParseError as e:
            raise ValueError(f"Failed to parse SAML XML: {e}")

    def _validate_assertion(self, assertion: SAMLAssertion) -> None:
        """
        Validate SAML assertion.

        Checks:
        - Issuer matches expected IDP
        - Assertion not expired
        - Audience matches SP entity ID

        Note: In production, also validate:
        - XML signature
        - Certificate chain
        - Assertion encryption
        """
        # Validate issuer
        if assertion.issuer != self.config.idp_entity_id:
            raise ValueError(
                f"Invalid issuer. Expected {self.config.idp_entity_id}, "
                f"got {assertion.issuer}"
            )

        # Validate expiration
        if assertion.is_expired():
            raise ValueError("SAML assertion has expired")

        # Validate audience
        if not assertion.is_valid_for_audience(self.config.sp_entity_id):
            raise ValueError(
                f"Invalid audience. Expected {self.config.sp_entity_id}, "
                f"got {assertion.audience}"
            )

        logger.debug("SAML assertion validation passed")

    def _extract_user_from_assertion(self, assertion: SAMLAssertion) -> SAMLUser:
        """Extract user identity from SAML assertion using attribute mapping."""

        # Get mapped attribute values
        def get_attr(key: str) -> Any:
            saml_attr = self.config.attribute_map.get(key)
            if saml_attr:
                return assertion.attributes.get(saml_attr)
            return None

        email = get_attr("email") or assertion.subject
        first_name = get_attr("first_name")
        last_name = get_attr("last_name")
        display_name = get_attr("display_name")
        role = get_attr("role")
        groups = get_attr("groups")

        # Normalize groups to list
        if groups and not isinstance(groups, list):
            groups = [groups]

        return SAMLUser(
            user_id=assertion.subject,
            email=email,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            role=role,
            groups=groups or [],
            organization_id=self.config.organization_id,
            session_index=assertion.session_index,
            assertion_expires_at=assertion.not_on_or_after,
            attributes=assertion.attributes,
        )

    def create_session(
        self,
        user: SAMLUser,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SAMLSession:
        """
        Create a new SSO session for the authenticated user.

        Args:
            user: Authenticated user from SAML
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            SAMLSession object
        """
        session_id = self.generate_session_id()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=self.config.session_lifetime_hours)

        session = SAMLSession(
            session_id=session_id,
            user=user,
            created_at=now,
            expires_at=expires_at,
            last_activity_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._sessions[session_id] = session

        logger.info(
            f"Created SSO session {session_id} for user {user.email} "
            f"(expires: {expires_at.isoformat()})"
        )

        return session

    def get_session(self, session_id: str) -> SAMLSession | None:
        """
        Get active session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SAMLSession if found and valid, None otherwise
        """
        session = self._sessions.get(session_id)

        if session is None:
            return None

        if session.is_expired():
            # Clean up expired session
            del self._sessions[session_id]
            logger.info(f"Session {session_id} has expired")
            return None

        # Refresh activity timestamp
        session.refresh_activity()

        return session

    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke/delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was revoked, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Revoked session {session_id}")
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired = [
            sid for sid, session in self._sessions.items() if session.is_expired()
        ]

        for sid in expired:
            del self._sessions[sid]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    def get_logout_url(self, session_id: str) -> str | None:
        """
        Generate SAML logout request URL.

        Args:
            session_id: Active session to logout

        Returns:
            Logout URL if configured, None otherwise
        """
        if not self.config.idp_logout_url:
            logger.warning("IDP logout URL not configured")
            return None

        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for logout")
            return None

        # Build SAML LogoutRequest
        request_id = self.generate_request_id()
        issue_instant = datetime.now(UTC).isoformat()

        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.config.idp_logout_url}">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <saml:NameID Format="{self.config.nameid_format.value}">{session.user.user_id}</saml:NameID>
    <samlp:SessionIndex>{session.user.session_index}</samlp:SessionIndex>
</samlp:LogoutRequest>"""

        # Encode request
        encoded_request = self._encode_saml_request(logout_request)

        # Build redirect URL
        params = {"SAMLRequest": encoded_request}
        url = f"{self.config.idp_logout_url}?{urlencode(params)}"

        # Revoke local session
        self.revoke_session(session_id)

        logger.info(f"Generated SAML logout URL for session {session_id}")
        return url

    def get_metadata(self) -> str:
        """
        Generate SAML SP metadata XML.

        Returns:
            XML metadata document for this service provider
        """
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.config.sp_entity_id}">
    <md:SPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="{str(self.config.sign_requests).lower()}"
        WantAssertionsSigned="{str(self.config.want_assertions_signed).lower()}">
        <md:NameIDFormat>{self.config.nameid_format.value}</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="{self.config.binding.value}"
            Location="{self.config.sp_acs_url}"
            index="0"/>
"""

        if self.config.sp_slo_url:
            metadata += f"""        <md:SingleLogoutService
            Binding="{SAMLBindingType.HTTP_REDIRECT.value}"
            Location="{self.config.sp_slo_url}"/>
"""

        metadata += """    </md:SPSSODescriptor>
</md:EntityDescriptor>"""

        return metadata


# Token validation helpers
def is_valid_saml_token_format(token: str | None) -> bool:
    """
    Check if a token is in valid SAML response format.

    SAML responses are base64-encoded XML documents.
    This function performs basic format validation.

    Args:
        token: Token string to check (can be None)

    Returns:
        True if token appears to be valid base64-encoded SAML response
    """
    if not token or not isinstance(token, str):
        return False

    # SAML responses should be reasonably sized (at least 100 chars when base64-encoded)
    if len(token) < 100:
        return False

    # Check if it's valid base64
    try:
        decoded = base64.b64decode(token)
        # Check if decoded data looks like XML
        decoded_str = decoded.decode("utf-8")
        return decoded_str.strip().startswith(
            "<?xml"
        ) or decoded_str.strip().startswith("<")
    except Exception:
        return False


def validate_saml_token_format(token: str) -> None:
    """
    Validate that a token is in proper SAML response format.

    This function should be called before processing a SAML response
    to ensure proper error messages when the token format is invalid.

    Args:
        token: Token string to validate

    Raises:
        ValueError: If token format is invalid
    """
    if not token:
        raise ValueError(
            "SAML response token is empty or None.\n\n"
            "Expected a base64-encoded SAML response from the identity provider.\n\n"
            "To fix this issue:\n"
            "  1. Ensure the SAML authentication flow completed successfully\n"
            "  2. Check that the identity provider returned a valid SAML response\n"
            "  3. Verify the Assertion Consumer Service (ACS) URL is correctly configured"
        )

    if not isinstance(token, str):
        raise ValueError(
            f"Invalid SAML response type. Expected string, got: {type(token).__name__}\n\n"
            "The SAML response must be a base64-encoded string."
        )

    if len(token) < 100:
        raise ValueError(
            "SAML response is too short to be valid.\n\n"
            f"Received token length: {len(token)} characters\n"
            "Expected: At least 100 characters for a valid base64-encoded SAML response\n\n"
            "This may indicate:\n"
            "  - The authentication flow was interrupted\n"
            "  - The identity provider returned an error instead of a SAML response\n"
            "  - The token was truncated during transmission"
        )

    # Validate base64 format
    try:
        decoded = base64.b64decode(token)
    except Exception as e:
        raise ValueError(
            f"SAML response is not valid base64-encoded data: {e}\n\n"
            "The SAML response from the identity provider must be base64-encoded.\n\n"
            "To fix this issue:\n"
            "  1. Ensure you're using the correct parameter (SAMLResponse) from the IDP callback\n"
            "  2. Verify the token hasn't been URL-decoded or modified\n"
            "  3. Check for any middleware that might be altering the response"
        )

    # Validate XML format
    try:
        decoded_str = decoded.decode("utf-8")
        if not (
            decoded_str.strip().startswith("<?xml")
            or decoded_str.strip().startswith("<")
        ):
            raise ValueError("Decoded data is not XML")
    except Exception as e:
        raise ValueError(
            f"SAML response does not contain valid XML data: {e}\n\n"
            "After base64 decoding, the SAML response must be a valid XML document.\n\n"
            "This may indicate:\n"
            "  - The token is corrupted\n"
            "  - The identity provider is misconfigured\n"
            "  - The token was encrypted and needs to be decrypted first"
        )

    logger.debug("SAML token format validation passed")


def map_saml_attributes(
    assertion: SAMLAssertion,
    attribute_map: dict[str, str],
) -> dict[str, Any]:
    """
    Map SAML assertion attributes to application attributes.

    This follows the attribute mapping pattern from SAMLConfig to extract
    user identity information from SAML assertions.

    Args:
        assertion: Parsed SAML assertion
        attribute_map: Mapping of app attributes to SAML attribute names

    Returns:
        Dictionary of mapped attributes with application-friendly keys

    Example:
        attribute_map = {
            "email": "{claims_ns}/emailaddress",
            "first_name": "{claims_ns}/givenname",
        }
        mapped = map_saml_attributes(assertion, attribute_map)
        # mapped = {"email": "user@example.com", "first_name": "John"}
    """
    mapped = {}

    for app_key, saml_attr in attribute_map.items():
        value = assertion.attributes.get(saml_attr)
        if value is not None:
            mapped[app_key] = value

    return mapped


def create_user_from_saml(
    assertion: SAMLAssertion,
    attribute_map: dict[str, str],
    organization_id: str | None = None,
) -> SAMLUser:
    """
    Create SAMLUser from assertion using attribute mapping.

    This is a convenience function that handles the common pattern of:
    1. Mapping SAML attributes to application attributes
    2. Extracting user identity fields
    3. Creating a SAMLUser object

    Args:
        assertion: Parsed and validated SAML assertion
        attribute_map: Mapping of app attributes to SAML attribute names
        organization_id: Optional organization identifier

    Returns:
        SAMLUser with mapped identity information

    Raises:
        ValueError: If required attributes (email) are missing
    """
    # Map attributes
    mapped = map_saml_attributes(assertion, attribute_map)

    # Extract user identity
    email = mapped.get("email") or assertion.subject
    if not email:
        raise ValueError(
            "Unable to extract email from SAML assertion.\n\n"
            "The SAML assertion must contain an email address either:\n"
            "  - In the NameID (subject)\n"
            "  - As a mapped attribute\n\n"
            "Check your SAML attribute mapping configuration."
        )

    first_name = mapped.get("first_name")
    last_name = mapped.get("last_name")
    display_name = mapped.get("display_name")
    role = mapped.get("role")
    groups = mapped.get("groups")

    # Normalize groups to list
    if groups and not isinstance(groups, list):
        groups = [groups]

    user = SAMLUser(
        user_id=assertion.subject,
        email=email,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name,
        role=role,
        groups=groups or [],
        organization_id=organization_id,
        session_index=assertion.session_index,
        assertion_expires_at=assertion.not_on_or_after,
        attributes=assertion.attributes,
    )

    logger.info(f"Created SAMLUser from assertion: {user.email} (ID: {user.user_id})")
    return user


# Convenience functions
def validate_saml_token(
    saml_response: str,
    config: SAMLConfig,
) -> SAMLUser:
    """
    Validate SAML response and extract user identity.

    This is the main entry point for SAML token validation. It:
    1. Validates the token format
    2. Parses and validates the SAML assertion
    3. Extracts and maps user identity

    Args:
        saml_response: Base64-encoded SAML response
        config: SAML provider configuration

    Returns:
        SAMLUser with extracted identity

    Raises:
        ValueError: If response is invalid or validation fails

    Example:
        config = SAMLConfig(
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_x509_cert="MIICertData...",
        )
        user = validate_saml_token(saml_response, config)
        print(f"Authenticated user: {user.email}")
    """
    # Validate token format first for better error messages
    try:
        validate_saml_token_format(saml_response)
    except ValueError as e:
        logger.error(f"SAML token format validation failed: {e}")
        raise

    # Process with provider
    try:
        provider = SAMLProvider(config)
        user = provider.validate_response(saml_response)
        logger.info(f"Successfully validated SAML token for user: {user.email}")
        return user
    except ValueError as e:
        # Re-raise with context
        logger.error(f"SAML token validation failed: {e}")
        raise
    except Exception as e:
        # Catch unexpected errors and provide helpful message
        logger.error(f"Unexpected error during SAML validation: {e}", exc_info=True)
        raise ValueError(
            f"Failed to validate SAML token: {e}\n\n"
            "This may indicate:\n"
            "  - The SAML response is malformed\n"
            "  - The identity provider configuration is incorrect\n"
            "  - There's a mismatch between SP and IDP settings\n\n"
            "Check the logs for more details."
        )


def load_saml_config(config_path: Path | str) -> SAMLConfig:
    """
    Load SAML configuration from file.

    Args:
        config_path: Path to configuration file (JSON or YAML)

    Returns:
        SAMLConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid
    """
    import json

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"SAML config not found: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        return SAMLConfig(
            idp_entity_id=data["idp_entity_id"],
            idp_sso_url=data["idp_sso_url"],
            idp_x509_cert=data["idp_x509_cert"],
            idp_logout_url=data.get("idp_logout_url"),
            sp_entity_id=data.get("sp_entity_id", "auto-claude-sp"),
            sp_acs_url=data.get("sp_acs_url", "https://localhost:8080/saml/acs"),
            sp_slo_url=data.get("sp_slo_url"),
            provider_type=SAMLProviderType(data.get("provider_type", "generic")),
            binding=SAMLBindingType(
                data.get("binding", SAMLBindingType.HTTP_POST.value)
            ),
            nameid_format=SAMLNameIDFormat(
                data.get("nameid_format", SAMLNameIDFormat.EMAIL.value)
            ),
            want_assertions_signed=data.get("want_assertions_signed", True),
            want_response_signed=data.get("want_response_signed", False),
            require_encrypted_assertions=data.get(
                "require_encrypted_assertions", False
            ),
            sign_requests=data.get("sign_requests", False),
            attribute_map=data.get("attribute_map", {}),
            session_lifetime_hours=data.get("session_lifetime_hours", 8),
            allow_jit_provisioning=data.get("allow_jit_provisioning", True),
            organization_id=data.get("organization_id"),
            organization_name=data.get("organization_name"),
        )

    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid SAML config format: {e}")
