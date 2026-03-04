# SSO/SAML Authentication Integration Usage

This document describes how to use the SSO authentication integration added to `core/auth.py` in subtask-3-3.

## Overview

The SSO integration provides enterprise SAML authentication with comprehensive audit logging. It supports multiple identity providers (Okta, Azure AD, Google Workspace, OneLogin, Auth0) and creates a complete audit trail of all authentication attempts.

## Features

- ✅ SAML 2.0 authentication support
- ✅ Multiple identity provider support
- ✅ Comprehensive audit logging (SSO_LOGIN_STARTED, COMPLETED, FAILED, etc.)
- ✅ Session management with configurable lifetime
- ✅ JIT (Just-In-Time) user provisioning
- ✅ Graceful degradation when enterprise modules unavailable
- ✅ Detailed error messages and logging

## Configuration

### Environment Variables

Set the following environment variables to enable SSO:

```bash
# Required - Enable SSO
export SSO_ENABLED=true

# Required - Identity Provider Configuration
export SAML_IDP_ENTITY_ID="https://your-idp.com/metadata"
export SAML_IDP_SSO_URL="https://your-idp.com/sso"
export SAML_IDP_X509_CERT="<base64-encoded-certificate>"

# Optional - Identity Provider Logout
export SAML_IDP_LOGOUT_URL="https://your-idp.com/logout"

# Optional - Service Provider Configuration (defaults shown)
export SAML_SP_ENTITY_ID="auto-claude-sp"
export SAML_SP_ACS_URL="http://localhost:8080/saml/acs"
export SAML_SP_SLO_URL="http://localhost:8080/saml/slo"

# Optional - Provider Type (okta, azure_ad, google_workspace, onelogin, auth0, generic)
export SAML_PROVIDER_TYPE="generic"

# Optional - Session Configuration
export SAML_SESSION_LIFETIME_HOURS="8"
export SAML_ALLOW_JIT_PROVISIONING="true"
```

### Example: Okta Configuration

```bash
export SSO_ENABLED=true
export SAML_PROVIDER_TYPE="okta"
export SAML_IDP_ENTITY_ID="http://www.okta.com/exkabcdef1234567890"
export SAML_IDP_SSO_URL="https://your-org.okta.com/app/yourapp/exkabcdef1234567890/sso/saml"
export SAML_IDP_X509_CERT="MIIDpDCCAoygAwIBAgIGAXyZ..."
```

### Example: Azure AD Configuration

```bash
export SSO_ENABLED=true
export SAML_PROVIDER_TYPE="azure_ad"
export SAML_IDP_ENTITY_ID="https://sts.windows.net/your-tenant-id/"
export SAML_IDP_SSO_URL="https://login.microsoftonline.com/your-tenant-id/saml2"
export SAML_IDP_X509_CERT="MIIDQjCCAiqgAwIBAgIVAK..."
```

## Usage

### Basic Authentication Flow

```python
from core.auth import authenticate_with_sso, is_sso_enabled

# Check if SSO is enabled
if is_sso_enabled():
    # Authenticate with SAML response from IdP
    user = authenticate_with_sso(
        saml_response=saml_response_from_idp,
        ip_address="192.168.1.100",
        user_agent="Auto-Claude/1.0",
        organization_id="org-123"
    )

    print(f"Authenticated: {user.email}")
    print(f"Role: {user.role}")
    print(f"Groups: {user.groups}")
```

### Get Current SSO User

```python
from core.auth import get_sso_user

# Retrieve user from active session
user = get_sso_user(session_id="session-abc123")

if user:
    print(f"Active user: {user.email}")
else:
    print("Session expired or not found")
```

### Check Configuration

```python
from core.auth import get_sso_config

try:
    config = get_sso_config()
    print(f"Provider: {config.provider_type}")
    print(f"SP Entity ID: {config.sp_entity_id}")
    print(f"Session lifetime: {config.session_lifetime_hours} hours")
except ValueError as e:
    print(f"SSO not configured: {e}")
```

## Audit Trail

Every SSO authentication attempt creates a comprehensive audit trail:

### Successful Authentication

1. **SSO_LOGIN_STARTED** - When authentication begins
   - Includes provider type and SP entity ID

2. **SAML_ASSERTION_VERIFIED** - When SAML response is validated
   - Includes user ID, email, session index, expiration

3. **SSO_LOGIN_COMPLETED** - On successful authentication
   - Includes user details, role, groups, JIT provisioning status

### Failed Authentication

1. **SSO_LOGIN_STARTED** - When authentication begins

2. **SAML_ASSERTION_REJECTED** - If SAML validation fails
   - Includes rejection reason

3. **SSO_LOGIN_FAILED** - On authentication failure
   - Includes error details and error type

### Audit Log Location

Audit logs are stored in:
```
.auto-claude/enterprise/audit/audit_log_YYYYMMDD.jsonl
```

Each entry includes:
- Correlation ID for request tracking
- Timestamp (UTC)
- Actor type, ID, email, role
- Organization ID
- IP address and user agent
- Action and result
- Detailed context and metadata

## Testing

Run the included test script to verify SSO integration:

```bash
cd apps/backend
python test_sso_integration.py
```

This will verify:
1. ✓ Enterprise modules are available
2. ✓ SSO configuration (if set)
3. ✓ Audit logger creation
4. ✓ Authentication flow availability
5. ✓ Audit trail actions

## Error Handling

The integration provides detailed error messages:

### Enterprise Modules Not Available

```
RuntimeError: Enterprise SSO modules are not available.

To enable SSO authentication:
  1. Ensure enterprise modules are installed
  2. Verify apps/backend/enterprise/sso.py exists
  3. Set required environment variables
```

### SSO Not Configured

```
ValueError: SSO is not enabled or configured.

To enable SSO:
  1. Set SSO_ENABLED=true
  2. Set SAML_IDP_ENTITY_ID=<your-idp-entity-id>
  3. Set SAML_IDP_SSO_URL=<your-sso-url>
  4. Set SAML_IDP_X509_CERT=<base64-encoded-cert>
```

### Missing Configuration

```
ValueError: Missing required SAML configuration: SAML_IDP_ENTITY_ID, SAML_IDP_X509_CERT

Required environment variables:
  - SAML_IDP_ENTITY_ID: Identity provider entity ID
  - SAML_IDP_SSO_URL: SSO endpoint URL
  - SAML_IDP_X509_CERT: Base64-encoded X.509 certificate
```

## Security Considerations

1. **Certificate Validation**: Always validate the IdP's X.509 certificate
2. **Assertion Signing**: Enable `want_assertions_signed` in production
3. **Session Lifetime**: Use appropriate session timeouts for your security requirements
4. **Audit Logs**: Regularly review audit logs for suspicious activity
5. **JIT Provisioning**: Consider disabling JIT provisioning if you require manual user approval

## Integration with Existing Auth

The SSO integration coexists with the existing OAuth authentication:

```python
from core.auth import get_auth_token, is_sso_enabled, authenticate_with_sso

# Use SSO if enabled, fallback to OAuth
if is_sso_enabled() and saml_response:
    user = authenticate_with_sso(saml_response)
else:
    # Use existing OAuth flow
    token = get_auth_token()
```

## Support

For issues or questions:
- Check audit logs in `.auto-claude/enterprise/audit/`
- Run test script: `python test_sso_integration.py`
- Review error messages for troubleshooting guidance

## See Also

- `apps/backend/enterprise/sso.py` - SAML provider implementation
- `apps/backend/enterprise/audit.py` - Audit logging implementation
- `apps/backend/test_sso_integration.py` - Integration test script
