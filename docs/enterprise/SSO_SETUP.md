# SSO Setup Guide

This guide covers configuring Single Sign-On (SSO) with SAML 2.0 for Auto Code enterprise deployments.

## Table of Contents

- [Overview](#overview)
- [Supported Identity Providers](#supported-identity-providers)
- [SAML Architecture](#saml-architecture)
- [Prerequisites](#prerequisites)
- [Provider-Specific Setup](#provider-specific-setup)
  - [Okta](#okta)
  - [Azure AD (Entra ID)](#azure-ad-entra-id)
  - [Google Workspace](#google-workspace)
  - [OneLogin](#onelogin)
  - [Auth0](#auth0)
  - [Generic SAML 2.0](#generic-saml-20)
- [Configuration](#configuration)
- [Attribute Mapping](#attribute-mapping)
- [Testing and Verification](#testing-and-verification)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Overview

Auto Code supports SAML 2.0 SSO for enterprise authentication, enabling:

**Features:**
- **Single Sign-On** - Users authenticate once with corporate credentials
- **Just-In-Time Provisioning** - Auto-create users on first login
- **Attribute Mapping** - Map SAML attributes to user profile
- **Role Assignment** - Automatically assign roles based on groups
- **Audit Logging** - Complete audit trail of SSO events
- **Session Management** - Configurable session lifetime
- **Single Logout** - Support for SAML SLO

**Benefits:**
- Centralized user management
- Strong authentication (MFA, SSO policies)
- Automated user provisioning
- Compliance with SOC2/GDPR requirements
- Reduced password fatigue

---

## Supported Identity Providers

Auto Code includes pre-configured templates for:

| Provider | Template | Documentation |
|-----------|----------|---------------|
| **Okta** | `SAMLProviderType.OKTA` | [Okta Setup](#okta) |
| **Azure AD** | `SAMLProviderType.AZURE_AD` | [Azure AD Setup](#azure-ad-entra-id) |
| **Google Workspace** | `SAMLProviderType.GOOGLE_WORKSPACE` | [Google Setup](#google-workspace) |
| **OneLogin** | `SAMLProviderType.ONELOGIN` | [OneLogin Setup](#onelogin) |
| **Auth0** | `SAMLProviderType.AUTH0` | [Auth0 Setup](#auth0) |
| **Generic** | `SAMLProviderType.GENERIC` | [Generic Setup](#generic-saml-20) |

**Custom Providers:** Any SAML 2.0-compliant IdP using generic template

---

## SAML Architecture

```
┌─────────────────┐                    ┌──────────────────┐
│   User Browser  │                    │ Auto Code (SP)   │
└────────┬────────┘                    └─────────┬────────┘
         │                                     │
         │ 1. Access protected resource        │
         ├─────────────────────────────────────>│
         │                                     │
         │ 2. Redirect to IdP (AuthnRequest) │
         │<─────────────────────────────────────┤
         │                                     │
         │ 3. Authenticate at IdP               │
         ├─────────────────────────────────────>│
         │                                     │
         │ 4. SAML Response (Assertion)       │
         │<─────────────────────────────────────┤
         │                                     │
         │ 5. Validate SAML, create session   │
         ├─────────────────────────────────────>│
         │                                     │
         │ 6. Access granted                  │
         │<─────────────────────────────────────┘
```

**Key Components:**

**Service Provider (SP):** Auto Code
- Generates SAML authentication requests
- Validates SAML responses
- Creates user sessions
- Maps attributes to user profile

**Identity Provider (IdP):** Your SSO system
- Authenticates users
- Issues SAML assertions
- Provides user attributes

**SAML Assertion:**
- Signed XML document
- Contains user identity
- Includes authentication statement
- Carries attributes

---

## Prerequisites

### Auto Code Configuration

```bash
# Enable enterprise mode
export ENTERPRISE_MODE=true

# Enable SSO
export ENTERPRISE_SSO_ENABLED=true

# Specify identity provider type
export ENTERPRISE_SSO_PROVIDER_TYPE=okta  # or azure_ad, google_workspace, etc.
```

### Required Information

From your Identity Provider, collect:

**Required:**
- **IdP Entity ID** - Unique identifier for your IdP
- **IdP SSO URL** - Where to send authentication requests
- **IdP X.509 Certificate** - For verifying SAML responses

**Optional:**
- **IdP Logout URL** - For single logout support
- **Attribute Mappings** - Which attributes to map
- **Group Mappings** - For role assignment

### Auto Code Information

Provide to your Identity Provider:

**SP Entity ID:** `auto-claude-sp` (customizable)
**Assertion Consumer Service (ACS) URL:**
```
http://localhost:8080/saml/acs              # Local
https://autoclaude.example.com/saml/acs      # Production
```

**Single Logout Service (SLS) URL:**
```
http://localhost:8080/saml/sls              # Local
https://autoclaude.example.com/saml/sls      # Production
```

**SP Metadata:** Generate from Auto Code (see below)

---

## Provider-Specific Setup

### Okta

**Okta Configuration:**

1. **Log in to Okta Admin Console**
   - Navigate to: **Applications** → **Applications**
   - Click: **Create App Integration**

2. **Select SAML 2.0**
   - Choose: **SAML 2.0**
   - Click: **Next**

3. **General Settings**
   ```
   App name: Auto Code
   App logo: (optional)
   App visibility: (configure later)
   ```
   Click: **Next**

4. **Configure SAML**
   ```
   Single sign-on URL:
     https://autoclaude.example.com/saml/acs

   Audience URI (SP Entity ID):
     auto-claude-sp

   Name ID format:
     Email Address

   Application username:
     Email

   Attributes (Statement):
     - Name: email
       Name format: Basic
       Filter: Regex
       Value: user.email

     - Name: first_name
       Name format: Basic
       Filter: Regex
       Value: user.firstName

     - Name: last_name
       Name format: Basic
       Filter: Regex
       Value: user.lastName

     - Name: role
       Name format: Basic
       Filter: Regex
       Value: appAutoclaude.role

     - Name: groups
       Name format: Basic
       Filter: Regex
       Value: appAutoclaude.groups
   ```
   Click: **Next**

5. **Feedback**
   - Select: **I'm an Okta customer adding an internal app**
   - Click: **Finish**

6. **Copy Configuration**
   - Click: **Sign On** tab
   - Copy: **Identity Provider SSOR URL**
   - Copy: **Identity Provider Issuer** (Entity ID)
   - Copy: **X.509 Certificate**

   **Auto Code Configuration:**

```python
from enterprise.sso import SAMLConfig, SAMLProvider

config = SAMLConfig(
    # IdP metadata
    idp_entity_id="https://okta.com/id/12345",  # Okta Issuer
    idp_sso_url="https://okta.com/sso/12345",  # Okta SSO URL
    idp_x509_cert="MIICert...",  # Okta Certificate

    # SP metadata
    sp_entity_id="auto-claude-sp",
    sp_acs_url="https://autoclaude.example.com/saml/acs",
    sp_slo_url="https://autoclaude.example.com/saml/sls",

    # Provider type
    provider_type=SAMLProviderType.OKTA,

    # Attribute mapping
    attribute_map={
        "email": "email",
        "first_name": "first_name",
        "last_name": "last_name",
        "role": "role",
        "groups": "groups",
    },

    # Organization info
    organization_id="org_123",
    organization_name="Example Corp",
)

provider = SAMLProvider(config)
```

**Okta Group Assignment:**

1. **Create Okta Groups**
   - Navigate to: **Directory** → **Groups**
   - Create groups:
     - `autoclaude-admins`
     - `autoclaude-developers`
     - `autoclaude-operators`
     - `autoclaude-auditors`
     - `autoclaude-viewers`

2. **Assign Groups to App**
   - Navigate to: **Applications** → **Auto Code** → **Assignments**
   - Click: **Assign**
   - Select groups
   - Click: **Done**

3. **Configure Group Attribute**
   - In app settings, add:
   ```
   Expression: appAutoclaude.groups
   Filter: Regex
   Value: groups.join(",")
   ```

**Test Okta Integration:**

```python
# Generate auth URL
auth_url = provider.get_auth_url(relay_state="/dashboard")
print(f"Visit: {auth_url}")

# After authentication at Okta, you'll be redirected to ACS URL
# with SAMLResponse parameter

# Validate response
user = provider.validate_response(saml_response)
print(f"Authenticated: {user.email}, Role: {user.role}, Groups: {user.groups}")
```

### Azure AD (Entra ID)

**Azure AD Configuration:**

1. **Register Application**
   - Navigate to: **Azure Portal** → **Azure Active Directory**
   - Click: **App registrations** → **New registration**
   ```
   Name: Auto Code
   Supported account types: Accounts in this organizational directory only
   Redirect URI: Web
     https://autoclaude.example.com/saml/acs
   ```
   Click: **Register**

2. **Get Application IDs**
   - Copy: **Application (client) ID**
   - Copy: **Directory (tenant) ID**
   - Copy: **Object ID** (use as entity ID)

3. **Configure SAML**
   - Click: **Add a certificate**
   - Upload or auto-generate certificate
   - Download: **Certificate (Base64)**

4. **Set up Single Sign-On**
   - Click: **Single sign-on** → **SAML**
   - Edit **Basic SAML Configuration**:
   ```
   Identifier (Entity ID):
     auto-claude-sp

   Reply URL (Assertion Consumer Service URL):
     https://autoclaude.example.com/saml/acs

   Sign on URL:
     https://autoclaude.example.com/saml/acs

   Relay State:
     (optional)
   ```
   Click: **Save**

5. **Configure Attributes**
   - Click: **Edit** in **Attributes & Claims**
   - Add claims:
   ```
   email
   givenname
   surname
   displayname
   tokenGroups
   ```
   - For **tokenGroups**:
     - Select: **Groups**
     - Select: **Security Groups**
     - Select: **All groups** (or filter)

6. **Assign Users/Groups**
   - Click: **Users and groups**
   - Click: **Add user/group**
   - Select users/groups to assign

**Auto Code Configuration:**

```python
from enterprise.sso import SAMLConfig, SAMLProvider, SAMLNameIDFormat

config = SAMLConfig(
    # IdP metadata (replace TENANT_ID and APP_ID)
    idp_entity_id="https://sts.windows.net/TENANT_ID",  # Azure AD Issuer
    idp_sso_url="https://login.microsoftonline.com/TENANT_ID/saml2",  # SAML SSO URL
    idp_x509_cert="MIICert...",  # Azure AD Certificate

    # SP metadata
    sp_entity_id="auto-claude-sp",
    sp_acs_url="https://autoclaude.example.com/saml/acs",
    sp_slo_url="https://autoclaude.example.com/saml/sls",

    # Provider type
    provider_type=SAMLProviderType.AZURE_AD,

    # Name ID format (Azure AD uses email)
    nameid_format=SAMLNameIDFormat.EMAIL,

    # Attribute mapping (Azure AD uses specific namespaces)
    attribute_map={
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
    },

    # Organization info
    organization_id="azure_tenant_id",
    organization_name="Example Corp",
)

provider = SAMLProvider(config)
```

**Azure AD Group Mapping:**

Create Azure AD groups matching Auto Code roles:

| Azure AD Group | Auto Code Role | Permissions |
|---------------|-----------------|-------------|
| `AutoCode-Admins` | ADMIN | 29 permissions |
| `AutoCode-Developers` | DEVELOPER | 17 permissions |
| `AutoCode-Operators` | OPERATOR | 10 permissions |
| `AutoCode-Auditors` | AUDITOR | 4 permissions |
| `AutoCode-Viewers` | VIEWER | 5 permissions |

### Google Workspace

**Google Workspace Configuration:**

1. **Set up SSO App**
   - Navigate to: **Admin Console** → **Apps** → **Web and mobile apps**
   - Click: **Add app** → **Add custom SAML app**
   ```
   Name: Auto Code
   Description: AI-powered development automation
   ```
   Click: **Continue**

2. **Download Google IdP Metadata**
   - Click: **Download Metadata** button
   - Save XML file

3. **Configure SAML**
   - Under **Google Identity Provider details**:
   ```
   ACS URL:
     https://autoclaude.example.com/saml/acs

   Entity ID:
     auto-claude-sp

   Start URL:
     (optional) https://autoclaude.example.com

   Name ID:
     Basic Information → Primary Email

   Name ID Format:
     EMAIL
   ```
   Click: **Continue**

4. **Configure Service Provider Details**
   - Under **Service Provider Details**:
   ```
   ACS URL:
     https://autoclaude.example.com/saml/acs

   Entity ID:
     auto-claude-sp
   ```
   Click: **Finish**

5. **Enable App**
   - Click: **Enable service** for: **Auto Code**
   - Select: **ON for everyone**

6. **Configure Attribute Mapping**
   - Click: **Add Mapping** for each attribute:
   ```
   Google Directory attributes → App attributes

   Primary Email → email
   Given Name → first_name
   Family Name → last_name
   Full Name → display_name
   Groups → groups
   ```

**Auto Code Configuration:**

```python
from enterprise.sso import SAMLConfig, SAMLProvider

config = SAMLConfig(
    # IdP metadata (from Google metadata XML)
    idp_entity_id="https://accounts.google.com/o/saml2/idpid/...",
    idp_sso_url="https://accounts.google.com/o/saml2/v2/sso",
    idp_x509_cert="MIICert...",  # Google Certificate from metadata

    # SP metadata
    sp_entity_id="auto-claude-sp",
    sp_acs_url="https://autoclaude.example.com/saml/acs",
    sp_slo_url="https://autoclaude.example.com/saml/sls",

    # Provider type
    provider_type=SAMLProviderType.GOOGLE_WORKSPACE,

    # Attribute mapping
    attribute_map={
        "email": "email",
        "first_name": "first_name",
        "last_name": "last_name",
        "display_name": "display_name",
        "groups": "groups",
    },

    # Organization info
    organization_id="google_workspace_customer_id",
    organization_name="Example Corp",
)

provider = SAMLProvider(config)
```

**Google Group Mapping:**

Create Google Groups matching Auto Code roles:

| Google Group | Auto Code Role | Email Format |
|--------------|-----------------|---------------|
| `autoclaude-admins@example.com` | ADMIN | admin@... |
| `autoclaude-developers@example.com` | DEVELOPER | developer@... |
| `autoclaude-operators@example.com` | OPERATOR | operator@... |
| `autoclaude-auditors@example.com` | AUDITOR | auditor@... |
| `autoclaude-viewers@example.com` | VIEWER | viewer@... |

### OneLogin

**OneLogin Configuration:**

1. **Create SAML App**
   - Navigate to: **Administration** → **Applications** → **Applications**
   - Click: **Add App**
   - Search: **SAML Test Connector**
   - Select: **SAML Test Connector (IdP)**

2. **Configuration**
   ```
   Display Name: Auto Code
   Description: AI-powered development automation
   ```
   Click: **Save**

3. **SSO Configuration**
   - **Tab: SSO**
   ```
   ACS URL:
     https://autoclaude.example.com/saml/acs

   SAML initiator: OneLogin

   Recipient:
     https://autoclaude.example.com/saml/acs

   Audience:
     auto-claude-sp

   ACS URL Validator:
     ^https://autoclaude\.example\.com/saml/acs$

   ACS URL Validator:
     ^https://autoclaude\.example\.com/saml/acs$

   Relay State:
     (optional)
   ```

4. **Parameter Configuration**
   - **Tab: Parameters**
   - Add parameters:
   ```
   Field Name: email
     Value: Email

   Field Name: first_name
     Value: First Name

   Field Name: last_name
     Value: Last Name
   ```

**Auto Code Configuration:**

```python
from enterprise.sso import SAMLConfig, SAMLProvider

config = SAMLConfig(
    # IdP metadata (from OneLogin SSO tab)
    idp_entity_id="https://app.onelogin.com/saml/metadata/...",
    idp_sso_url="https://app.onelogin.com/trust/saml2/http-POST/...",
    idp_x509_cert="MIICert...",  # OneLogin Certificate

    # SP metadata
    sp_entity_id="auto-claude-sp",
    sp_acs_url="https://autoclaude.example.com/saml/acs",
    sp_slo_url="https://autoclaude.example.com/saml/sls",

    # Provider type
    provider_type=SAMLProviderType.ONELOGIN,

    # Attribute mapping
    attribute_map={
        "email": "email",
        "first_name": "first_name",
        "last_name": "last_name",
    },

    # Organization info
    organization_id="onelogin_app_id",
    organization_name="Example Corp",
)

provider = SAMLProvider(config)
```

### Auth0

**Auth0 Configuration:**

1. **Create SAML Application**
   - Navigate to: **Applications** → **Applications**
   - Click: **Create Application**
   - Choose: **Regular Web Application**
   - Click: **Create**

2. **Application Settings**
   ```
   Name: Auto Code
   Description: AI-powered development automation
   Application Type: Regular Web Application

   Allowed Callback URLs:
     https://autoclaude.example.com/saml/acs

   Allowed Logout URLs:
     https://autoclaude.example.com/saml/sls
   ```
   Click: **Save Changes**

3. **Configure SAML**
   - Navigate to: **Addons** → **SAML2**
   - Click: **Enable**
   - **Settings:**
   ```
   Application Callback URL:
     https://autoclaude.example.com/saml/acs

   Settings:
     Application Assertion Consumer Service (ACS) URL:
       https://autoclaude.example.com/saml/acs

     Audience:
       auto-claude-sp

     Application Metadata URL:
       https://autoclaude.example.com/saml/metadata

     UPN Claim:
       user.email
   ```

4. **Download Metadata**
   - Click: **Download** metadata XML
   - Or copy: **Identity Provider Login URL**, **Identity Provider Issuer**, **X.509 Signing Certificate**

**Auto Code Configuration:**

```python
from enterprise.sso import SAMLConfig, SAMLProvider

config = SAMLConfig(
    # IdP metadata (from Auth0 SAML settings)
    idp_entity_id="urn:auth0:...",  # Auth0 Issuer
    idp_sso_url="https://your-domain.auth0.com/samlp/...",  # Auth0 SSO URL
    idp_x509_cert="MIICert...",  # Auth0 Certificate

    # SP metadata
    sp_entity_id="auto-claude-sp",
    sp_acs_url="https://autoclaude.example.com/saml/acs",
    sp_slo_url="https://autoclaude.example.com/saml/sls",

    # Provider type
    provider_type=SAMLProviderType.AUTH0,

    # Attribute mapping (Auth0 uses standard SAML attributes)
    attribute_map={
        "email": "email",
        "first_name": "first_name",
        "last_name": "last_name",
        "display_name": "nickname",
    },

    # Organization info
    organization_id="auth0_tenant",
    organization_name="Example Corp",
)

provider = SAMLProvider(config)
```

### Generic SAML 2.0

For any SAML 2.0-compliant identity provider:

**Requirements:**
1. SAML 2.0 support
2. HTTP-POST or HTTP-Redirect binding
3. X.509 certificate for signature verification
4. Support for SAML assertions

**Generic Configuration:**

```python
from enterprise.sso import (
    SAMLConfig,
    SAMLProvider,
    SAMLProviderType,
    SAMLBindingType,
    SAMLNameIDFormat,
)

config = SAMLConfig(
    # IdP metadata (from your IdP documentation)
    idp_entity_id="https://idp.example.com/entityid",  # Required
    idp_sso_url="https://idp.example.com/saml/ssoservice",  # Required
    idp_x509_cert="MIICert...",  # Required (Base64 or PEM)
    idp_logout_url="https://idp.example.com/saml/sloservice",  # Optional

    # SP metadata
    sp_entity_id="auto-claude-sp",  # Required
    sp_acs_url="https://autoclaude.example.com/saml/acs",  # Required
    sp_slo_url="https://autoclaude.example.com/saml/sls",  # Optional

    # Provider type
    provider_type=SAMLProviderType.GENERIC,

    # Protocol settings
    binding=SAMLBindingType.HTTP_POST,  # or HTTP_REDIRECT
    nameid_format=SAMLNameIDFormat.EMAIL,  # or PERSISTENT, TRANSIENT, UNSPECIFIED

    # Security settings
    want_assertions_signed=True,  # Require signed assertions (recommended)
    want_response_signed=False,  # Require signed response
    require_encrypted_assertions=False,  # Require encrypted assertions
    sign_requests=False,  # Sign outgoing requests

    # Attribute mapping (customized to your IdP)
    attribute_map={
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "role": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/role",
        "groups": "http://schemas.xmlsoap.org/claims/Group",
    },

    # Session settings
    session_lifetime_hours=8,
    allow_jit_provisioning=True,

    # Organization info
    organization_id="org_123",
    organization_name="Example Corp",
)

provider = SAMLProvider(config)
```

**Generate SP Metadata:**

```python
# Get Auto Code metadata
metadata_xml = provider.get_metadata()

# Save to file
with open('saml-sp-metadata.xml', 'w') as f:
    f.write(metadata_xml)

# Upload to your IdP
print("Upload saml-sp-metadata.xml to your Identity Provider")
```

**Example Generic IdPs:**
- Keycloak
- FreeIPA
- Shibboleth
- Ping Identity
- CyberArk Identity
- MiniOrange

---

## Configuration

### Configuration File

**Option 1: JSON Configuration File**

Create `saml-config.json`:

```json
{
  "idp_entity_id": "https://okta.com/id/12345",
  "idp_sso_url": "https://okta.com/sso/12345",
  "idp_x509_cert": "MIICert...",
  "idp_logout_url": "https://okta.com/logout/12345",

  "sp_entity_id": "auto-claude-sp",
  "sp_acs_url": "https://autoclaude.example.com/saml/acs",
  "sp_slo_url": "https://autoclaude.example.com/saml/sls",

  "provider_type": "okta",

  "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
  "nameid_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",

  "want_assertions_signed": true,
  "want_response_signed": false,
  "require_encrypted_assertions": false,
  "sign_requests": false,

  "attribute_map": {
    "email": "email",
    "first_name": "first_name",
    "last_name": "last_name",
    "display_name": "display_name",
    "role": "role",
    "groups": "groups"
  },

  "session_lifetime_hours": 8,
  "allow_jit_provisioning": true,

  "organization_id": "org_123",
  "organization_name": "Example Corp"
}
```

Load programmatically:

```python
from enterprise.sso import load_saml_config

config = load_saml_config('saml-config.json')
provider = SAMLProvider(config)
```

**Option 2: Environment Variables**

```bash
# Core SAML settings
export SAML_IDP_ENTITY_ID="https://okta.com/id/12345"
export SAML_IDP_SSO_URL="https://okta.com/sso/12345"
export SAML_IDP_X509_CERT="MIICert..."

# SP settings
export SAML_SP_ENTITY_ID="auto-claude-sp"
export SAML_SP_ACS_URL="https://autoclaude.example.com/saml/acs"

# Provider type
export ENTERPRISE_SSO_PROVIDER_TYPE="okta"

# Session settings
export SAML_SESSION_LIFETIME_HOURS="8"
```

**Option 3: Programmatic Configuration**

```python
from enterprise.sso import SAMLConfig, SAMLProvider, SAMLProviderType

config = SAMLConfig(
    idp_entity_id="https://okta.com/id/12345",
    idp_sso_url="https://okta.com/sso/12345",
    idp_x509_cert="MIICert...",
    sp_entity_id="auto-claude-sp",
    sp_acs_url="https://autoclaude.example.com/saml/acs",
    provider_type=SAMLProviderType.OKTA,
)

provider = SAMLProvider(config)
```

### Security Settings

**Require Signed Assertions:**

```python
config = SAMLConfig(
    ...
    want_assertions_signed=True,  # Recommended
    want_response_signed=True,  # Optional, stricter
    ...
)
```

**Require Encrypted Assertions:**

```python
config = SAMLConfig(
    ...
    require_encrypted_assertions=True,  # HIPAA/HIPAA environments
    ...
)
```

**Sign Requests:**

```python
config = SAMLConfig(
    ...
    sign_requests=True,  # Requires SP certificate
    ...
)
```

**Session Lifetime:**

```python
config = SAMLConfig(
    ...
    session_lifetime_hours=8,  # Balance security and UX
    ...
)
```

### Just-In-Time Provisioning

Auto-create users on first login:

```python
config = SAMLConfig(
    ...
    allow_jit_provisioning=True,  # Default: true
    ...
)
```

**Role Assignment via Groups:**

```python
# In SAML assertion
user = provider.validate_response(saml_response)

# Map groups to roles
if "autoclaude-admins" in user.groups:
    user.role = "ADMIN"
elif "autoclaude-developers" in user.groups:
    user.role = "DEVELOPER"
elif "autoclaude-operators" in user.groups:
    user.role = "OPERATOR"
elif "autoclaude-auditors" in user.groups:
    user.role = "AUDITOR"
else:
    user.role = "VIEWER"  # Default role
```

---

## Attribute Mapping

Attribute mapping translates SAML assertions to user profile fields.

### Default Attributes

```python
from enterprise.sso import SAMLConfig

config = SAMLConfig(
    ...
    # Default attribute mapping (auto-configured)
    attribute_map={
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "role": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/role",
        "groups": "http://schemas.xmlsoap.org/claims/Group",
    },
    ...
)
```

### Custom Attributes

Map custom SAML attributes:

```python
config = SAMLConfig(
    ...
    attribute_map={
        # Standard attributes
        "email": "email",
        "first_name": "firstName",
        "last_name": "lastName",

        # Custom attributes
        "department": "department",
        "title": "jobTitle",
        "location": "officeLocation",
        "cost_center": "costCenter",

        # Custom role attribute
        "role": "appAutoclaudeRole",
        "groups": "appAutoclaudeGroups",
    },
    ...
)
```

### Provider-Specific Namespaces

**Azure AD:**
```python
attribute_map={
    "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
}
```

**Okta:**
```python
attribute_map={
    "email": "email",
    "groups": "groups",
}
```

**Google Workspace:**
```python
attribute_map={
    "email": "email",
    "groups": "groups",
}
```

### Nested Attributes

Access nested attributes in assertions:

```python
# If SAML assertion contains nested structure
# <Attribute Name="profile">
#   <AttributeValue>{"department":"Engineering","level":"Senior"}</AttributeValue>
# </Attribute>

# Map entire attribute
config = SAMLConfig(
    ...
    attribute_map={
        "profile": "profile",  # Capture JSON string
    },
    ...
)

# Parse after extraction
import json
user = provider.validate_response(saml_response)
if "profile" in user.attributes:
    profile = json.loads(user.attributes["profile"])
    user.department = profile.get("department")
    user.level = profile.get("level")
```

---

## Testing and Verification

### Test SAML Flow

**1. Generate Authentication Request:**

```python
from enterprise.sso import SAMLProvider, load_saml_config

config = load_saml_config('saml-config.json')
provider = SAMLProvider(config)

# Generate auth URL
auth_url = provider.get_auth_url(relay_state="/dashboard")

print(f"Visit: {auth_url}")
print(f"This will redirect to: {config.idp_sso_url}")
```

**2. Authenticate at IdP**

- Visit the generated auth URL
- Complete authentication at IdP
- Approve any consent prompts

**3. Validate SAML Response:**

```python
# After IdP redirects back to ACS URL
# Extract SAMLResponse from callback

from urllib.parse import parse_qs
from enterprise.sso import validate_saml_token, load_saml_config

# Simulated callback (replace with actual SAML response)
callback_params = {
    "SAMLResponse": "VGhpcyBpc0BzZXN1cmV0...",  # Base64 SAML response
    "RelayState": "/dashboard"
}

config = load_saml_config('saml-config.json')

# Validate and extract user
try:
    user = validate_saml_token(callback_params["SAMLResponse"], config)
    print(f"Authentication successful!")
    print(f"User: {user.email}")
    print(f"Name: {user.get_full_name()}")
    print(f"Role: {user.role}")
    print(f"Groups: {user.groups}")
except ValueError as e:
    print(f"Authentication failed: {e}")
```

### Test Session Management

**Create Session:**

```python
# Create session after successful authentication
session = provider.create_session(
    user=user,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)

print(f"Session ID: {session.session_id}")
print(f"Expires at: {session.expires_at}")
```

**Retrieve Session:**

```python
# Retrieve active session
session = provider.get_session(session_id)

if session:
    print(f"Session valid for: {user.email}")
    print(f"Last activity: {session.last_activity_at}")
else:
    print("Session expired or not found")
```

**Test Session Expiration:**

```python
from datetime import datetime, timedelta, UTC

# Check expiration
if session.is_expired():
    print("Session has expired")
else:
    time_remaining = session.expires_at - datetime.now(UTC)
    print(f"Session expires in: {time_remaining}")
```

### Test Audit Logging

**Verify SSO Audit Events:**

```python
from enterprise.audit import get_audit_logger, ActorType

audit = get_audit_logger()

# Query recent SSO events
from datetime import datetime, timedelta, UTC

since = datetime.now(UTC) - timedelta(hours=1)

# Check for login events
login_events = audit.query_logs(
    action=audit.AuditAction.SSO_LOGIN_COMPLETED,
    since=since
)

for event in login_events:
    print(f"{event.timestamp}: {event.user_email} logged in via {event.details['sso_provider']}")

# Check for failures
failed_events = audit.query_logs(
    action=audit.AuditAction.SSO_LOGIN_FAILED,
    since=since
)

for event in failed_events:
    print(f"{event.timestamp}: {event.user_email} failed - {event.error}")
```

### Test Attribute Mapping

**Verify Attribute Extraction:**

```python
user = provider.validate_response(saml_response)

# Check extracted attributes
print(f"Email: {user.email}")
print(f"Name: {user.get_full_name()}")
print(f"Role: {user.role}")
print(f"Groups: {user.groups}")

# Check raw attributes
print("Raw SAML attributes:")
for key, value in user.attributes.items():
    print(f"  {key}: {value}")
```

**Test Role Assignment:**

```python
# Define group to role mapping
ROLE_MAPPING = {
    "autoclaude-admins": "ADMIN",
    "autoclaude-developers": "DEVELOPER",
    "autoclaude-operators": "OPERATOR",
    "autoclaude-auditors": "AUDITOR",
    "autoclaude-viewers": "VIEWER",
}

# Assign role based on groups
for group in user.groups:
    if group in ROLE_MAPPING:
        user.role = ROLE_MAPPING[group]
        break
else:
    user.role = "VIEWER"  # Default

print(f"Assigned role: {user.role}")
```

### Test Logout Flow

**Generate Logout URL:**

```python
# Get logout URL for single logout
logout_url = provider.get_logout_url(session_id)

print(f"Visit to logout: {logout_url}")
print(f"User will be logged out of IdP and Auto Code")
```

**Revoke Session:**

```python
# Manually revoke session
if provider.revoke_session(session_id):
    print("Session revoked")
else:
    print("Session not found")
```

---

## Troubleshooting

### Common Issues

**Issue: "SAML response is invalid base64"**

```bash
# Check SAML response format
python -c "
from enterprise.sso import is_valid_saml_token_format

token = 'VGhpcyBpc0BzZXN1cmV0...'  # Your SAML response
print(f'Valid format: {is_valid_saml_token_format(token)}')
"

# Common causes:
# - Wrong parameter (SAMLResponse vs SAMLRequest)
# - URL-encoded multiple times
# - Truncated response
# - Not base64-encoded
```

**Issue: "SAML assertion has expired"**

```bash
# Check system time
date

# SAML assertions typically valid for 5 minutes
# Sync time if system clock is off
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd

# Adjust session lifetime in IdP
# Auto Code accepts assertions up to session_lifetime_hours
```

**Issue: "Invalid audience"**

```bash
# Verify SP Entity ID matches IdP configuration
python -c "
from enterprise.sso import load_saml_config

config = load_saml_config('saml-config.json')
print(f'SP Entity ID: {config.sp_entity_id}')
print(f'This must match Audience setting in IdP')
"

# Fix: Update IdP configuration
# Audience/Entity ID: auto-claude-sp
```

**Issue: "Invalid issuer"**

```bash
# Verify IdP Entity ID matches configuration
python -c "
from enterprise.sso import load_saml_config

config = load_saml_config('saml-config.json')
print(f'Expected IdP: {config.idp_entity_id}')
print(f'Check SAML assertion issuer matches this value')
"

# Fix: Update idp_entity_id in SAML config
```

**Issue: Attributes not mapped**

```bash
# Check raw SAML assertion
python -c "
from enterprise.sso import validate_saml_token, load_saml_config
import json

config = load_saml_config('saml-config.json')
user = validate_saml_token(saml_response, config)

print('Raw attributes:')
print(json.dumps(user.attributes, indent=2))
"

# Verify attribute names match IdP configuration
# Update attribute_map in SAML config
```

**Issue: Role assignment not working**

```bash
# Check group memberships
python -c "
from enterprise.sso import validate_saml_token, load_saml_config

config = load_saml_config('saml-config.json')
user = validate_saml_token(saml_response, config)

print(f'Groups: {user.groups}')
print(f'Role: {user.role}')
"

# Verify:
# - Groups attribute is mapped
# - User is member of correct group in IdP
# - Group name matches mapping (case-sensitive)
```

### Debug Mode

Enable verbose SAML debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add SAML-specific logger
saml_logger = logging.getLogger('enterprise.sso')
saml_logger.setLevel(logging.DEBUG)
```

Inspect SAML assertion XML:

```python
import base64

# Decode SAML response
decoded = base64.b64decode(saml_response)

# Print XML (for debugging only - do not log in production)
print(decoded.decode('utf-8'))
```

Verify SAML request:

```python
# Inspect generated AuthnRequest
from enterprise.sso import SAMLProvider

provider = SAMLProvider(config)

# Generate request
request_xml = provider._build_authn_request(
    request_id="test-123",
    issue_instant=datetime.now(UTC).isoformat()
)

print(request_xml)
```

### IdP-Specific Issues

**Okta: "This app is not assigned"**

- Check user assignments in Okta
- Verify user is not disabled
- Check app availability rules

**Azure AD: "AADSTS650056"**

- Verify Application ID matches configuration
- Check Reply URL matches exactly
- Verify tenant ID is correct
- Check user has been assigned to app

**Google Workspace: "This app is not enabled"**

- Enable app in Admin Console
- Check user/group assignments
- Verify service status is enabled

**OneLogin: "Invalid SAML Request"**

- Verify ACS URL validator regex
- Check Entity ID matches
- Verify X.509 certificate is current

---

## Security Best Practices

### Certificate Management

**Rotate IdP Certificates:**

```bash
# Download new certificate from IdP
# Update saml-config.json with new certificate

# Validate configuration
python -c "
from enterprise.sso import load_saml_config, SAMLProvider

config = load_saml_config('saml-config.json')
provider = SAMLProvider(config)
print('Certificate loaded successfully')
"
```

**Verify Certificate Chain:**

```python
from OpenSSL import crypto

# Load certificate
cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)

# Verify expiration
from datetime import datetime
not_after = datetime.strptime(
    cert.get_notAfter().decode('ascii'),
    '%Y%m%d%H%M%SZ'
)

print(f'Certificate expires: {not_after}')

# Warn if expiring soon
from datetime import timedelta, UTC
if not_after - datetime.now(UTC) < timedelta(days=30):
    print('WARNING: Certificate expiring soon')
```

### Session Security

**Limit Session Lifetime:**

```python
config = SAMLConfig(
    ...
    session_lifetime_hours=8,  # Balance security and UX
    ...
)
```

**Implement Session Refresh:**

```python
# Check session expiration before critical operations
if session.is_expired():
    # Redirect to IdP for re-authentication
    redirect_to_idp()
else:
    # Refresh activity timestamp
    session.refresh_activity()
```

**Monitor Concurrent Sessions:**

```python
# Check for suspicious activity
from enterprise.audit import get_audit_logger

audit = get_audit_logger()

# Query concurrent sessions from same user
events = audit.query_logs(
    actor_id=user.user_id,
    since=datetime.now(UTC) - timedelta(minutes=5)
)

if len(events) > 3:
    # Flag for investigation
    print("WARNING: Multiple concurrent sessions detected")
```

### Attribute Security

**Never Trust IdP Attributes for Authorization:**

```python
# Wrong: Trust IdP role attribute
if user.role == "ADMIN":  # Can be spoofed
    grant_admin_access()

# Correct: Map group membership to role
if "autoclaude-admins" in user.groups:  # Verified by IdP
    user.role = "ADMIN"
    grant_admin_access()
```

**Validate All Attributes:**

```python
# Sanitize user input
import re

def validate_email(email: str) -> bool:
    """Validate email format."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

# Validate before using
if not validate_email(user.email):
    raise ValueError(f"Invalid email: {user.email}")
```

### Audit Logging

**Log All SSO Events:**

```python
from enterprise.audit import get_audit_logger, ActorType

audit = get_audit_logger()

ctx = audit.start_operation(
    actor_type=ActorType.USER,
    actor_id=user.user_id,
    user_email=user.email,
    organization_id=organization_id
)

# Log successful login
audit.log_sso_login(
    context=ctx,
    success=True,
    sso_provider=config.provider_type.value
)
```

**Monitor Failed Authentication Attempts:**

```python
# Check for failed login patterns
failed_logins = audit.query_logs(
    action=audit.AuditAction.SSO_LOGIN_FAILED,
    since=datetime.now(UTC) - timedelta(minutes=15)
)

if len(failed_logins) > 5:
    # Flag potential brute force
    print("WARNING: Multiple failed login attempts")
```

### Network Security

**Enforce HTTPS:**

```python
config = SAMLConfig(
    ...
    sp_acs_url="https://autoclaude.example.com/saml/acs",  # HTTPS required
    sp_slo_url="https://autoclaude.example.com/saml/sls",
    ...
)
```

**Validate ACS URL:**

```python
# Verify callback URL is trusted
from urllib.parse import urlparse

def is_trusted_acs_url(url: str) -> bool:
    """Verify ACS URL is trusted."""
    parsed = urlparse(url)

    # Must be HTTPS
    if parsed.scheme != 'https':
        return False

    # Must be allowed domain
    allowed_domains = [
        'autoclaude.example.com',
        'autoclaude-internal.example.com',
    ]

    return parsed.netloc in allowed_domains

# Validate in SAML response handler
if not is_trusted_acs_url(callback_url):
    raise ValueError("Untrusted ACS URL")
```

---

## Appendix

### SAML Configuration Template

**Complete SAML Configuration:**

```json
{
  "idp_entity_id": "https://idp.example.com/entityid",
  "idp_sso_url": "https://idp.example.com/saml/ssoservice",
  "idp_x509_cert": "MIICert...",
  "idp_logout_url": "https://idp.example.com/saml/sloservice",

  "sp_entity_id": "auto-claude-sp",
  "sp_acs_url": "https://autoclaude.example.com/saml/acs",
  "sp_slo_url": "https://autoclaude.example.com/saml/sls",

  "provider_type": "okta",

  "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
  "nameid_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",

  "want_assertions_signed": true,
  "want_response_signed": false,
  "require_encrypted_assertions": false,
  "sign_requests": false,

  "attribute_map": {
    "email": "email",
    "first_name": "first_name",
    "last_name": "last_name",
    "display_name": "display_name",
    "role": "role",
    "groups": "groups"
  },

  "session_lifetime_hours": 8,
  "allow_jit_provisioning": true,

  "organization_id": "org_123",
  "organization_name": "Example Corp"
}
```

### Environment Variable Reference

| Variable | Type | Description |
|-----------|------|-------------|
| `ENTERPRISE_SSO_ENABLED` | bool | Enable SSO authentication |
| `ENTERPRISE_SSO_PROVIDER_TYPE` | enum | Identity provider type |
| `ENTERPRISE_SSO_CONFIG_PATH` | path | SAML configuration file path |
| `SAML_IDP_ENTITY_ID` | string | IdP Entity ID |
| `SAML_IDP_SSO_URL` | string | IdP SSO URL |
| `SAML_IDP_X509_CERT` | string | IdP X.509 Certificate (Base64) |
| `SAML_IDP_LOGOUT_URL` | string | IdP Logout URL (optional) |
| `SAML_SP_ENTITY_ID` | string | SP Entity ID |
| `SAML_SP_ACS_URL` | string | Assertion Consumer Service URL |
| `SAML_SP_SLO_URL` | string | Single Logout Service URL (optional) |
| `SAML_SESSION_LIFETIME_HOURS` | int | Session lifetime (default: 8) |

### Additional Resources

**SAML Specifications:**
- [SAML 2.0 Core Specification](https://docs.oasis-open.org/security/saml/v2.0/)
- [SAML 2.0 Bindings](https://docs.oasis-open.org/security/saml/v2.0/saml-bindings-2.0-os.pdf)

**IdP Documentation:**
- [Okta SAML Documentation](https://developer.okta.com/docs/reference/saml-settings/)
- [Azure AD SAML Protocol](https://docs.microsoft.com/en-us/azure/active-directory/develop/saml-protocol)
- [Google Workspace SAML](https://support.google.com/a/answer/6087519)

**Testing Tools:**
- [SAML Tracer (Chrome Extension)](https://chrome.google.com/webstore/detail/saml-tracer/mpjjnnoalgnbklojbniojgmigpedmbin)
- [SAML DevTools](https://www.samltool.com/)

**Community Support:**
- [GitHub Issues](https://github.com/OBenner/Auto-Coding/issues)
- [GitHub Discussions](https://github.com/OBenner/Auto-Coding/discussions)

---

<div align="center">

**SSO Setup Guide**

[← Back to Deployment Guide](DEPLOYMENT_GUIDE.md)

</div>
