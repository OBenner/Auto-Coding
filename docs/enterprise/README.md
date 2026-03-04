# Enterprise Security & Compliance

Enterprise-grade security and compliance features for Auto Code deployments in regulated environments.

## Features Overview

### Audit Logging

Comprehensive, structured audit logging for all operations with compliance reporting support.

- **30+ audit event types** across authentication, agent operations, data access, and configuration changes
- **Correlation ID tracking** for tracing operations across sessions
- **Actor tracking** - distinguishes between user, bot, automation, and system actions
- **Token usage logging** for AI cost attribution and monitoring
- **Log rotation and retention** with configurable 90-day default
- **Export capabilities** for compliance audits (JSON format)
- **Compliance report generation** for SOC2, GDPR, HIPAA frameworks

See [AUDIT_LOGGING.md](AUDIT_LOGGING.md) for full documentation.

### SSO / SAML 2.0 Authentication

Single Sign-On integration with enterprise identity providers.

- **SAML 2.0 Service Provider** implementation
- **6 pre-configured identity providers**: Okta, Azure AD, Google Workspace, OneLogin, Auth0, Generic SAML
- **Just-In-Time (JIT) user provisioning** from SAML assertions
- **Attribute mapping** for roles, email, and display name
- **Session management** with configurable lifetime and idle timeout
- **Assertion validation** with signature verification

See [SSO_SETUP.md](SSO_SETUP.md) for setup instructions per provider.

### Role-Based Access Control (RBAC)

Fine-grained permission system for controlling access to features and operations.

| Role | Description |
|------|-------------|
| **Admin** | Full access to all features, configuration, and user management |
| **Developer** | Create/run specs, execute agents, review code |
| **Operator** | Run and monitor builds, view specs and logs |
| **Auditor** | Read-only access to audit logs, compliance reports, and configuration |
| **Viewer** | Read-only access to specs and build status |

29 granular permissions across spec management, build execution, agent operations, code access, audit/compliance, configuration, and user management.

### Data Residency

Regional data controls for regulatory compliance.

- **5 supported regions**: EU, US, UK, AP (Asia-Pacific), GLOBAL
- **Regional API endpoint routing** to keep data within jurisdiction
- **Data transfer validation** with audit logging for cross-region access
- **GDPR compliance** for international data transfers
- **Configurable per-project** residency requirements

### Deployment Modes

Flexible deployment options for different security requirements.

| Mode | Description |
|------|-------------|
| **Cloud** | Default SaaS deployment with managed infrastructure |
| **Self-Hosted** | On-premise deployment with full data control |
| **Air-Gapped** | Fully isolated deployment with no internet access |

Air-gapped mode supports local model proxies (llama.cpp, vLLM, TGI) as Claude API alternatives.

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for deployment instructions.

### Compliance Frameworks

Built-in support for regulatory compliance documentation and controls.

- **SOC2** - Access control matrix, audit logging, authentication, encryption, network security
- **GDPR** - Data residency, subject rights automation, breach notification, DPA support
- **HIPAA** - PHI protection controls, audit trails, access restrictions
- **CCPA** - Privacy rights, data disclosure controls
- **UK DPA** - Post-Brexit GDPR-equivalent controls

## Quick Start

### 1. Enable Enterprise Mode

```python
# apps/backend/.env
ENTERPRISE_MODE=true
ENTERPRISE_AUDIT_ENABLED=true
ENTERPRISE_SSO_ENABLED=true
ENTERPRISE_DATA_RESIDENCY=EU
```

### 2. Configure SSO (Optional)

```python
SAML_IDP_ENTITY_ID=https://your-idp.example.com
SAML_IDP_SSO_URL=https://your-idp.example.com/sso/saml
SAML_IDP_CERTIFICATE_PATH=/path/to/idp-cert.pem
SAML_SP_ENTITY_ID=https://your-app.example.com/saml/metadata
```

### 3. Agent Integration

Enterprise audit logging integrates automatically with the agent system:

```python
from agents.base import audit_agent_session_with_permissions

with audit_agent_session_with_permissions(
    agent_type="coder",
    user_role="developer",
    spec_dir=spec_dir,
    project_dir=project_dir,
    user_email="dev@company.com",
) as ctx:
    # Agent work is audited automatically
    # Permission is checked before execution
    ctx.metadata["files_modified"] = 5
```

## Architecture

```
enterprise/
├── __init__.py          # Package exports
├── audit.py             # Structured audit logging (900+ lines)
├── config.py            # Enterprise configuration management
├── data_residency.py    # Regional data controls
├── deployment.py        # Deployment mode handling
├── permissions.py       # RBAC system (5 roles, 29 permissions)
└── sso.py               # SAML 2.0 SSO integration
```

## Related Documentation

- [Audit Logging Guide](AUDIT_LOGGING.md) - Event types, querying, compliance reporting
- [SSO Setup Guide](SSO_SETUP.md) - Identity provider configuration
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Cloud, self-hosted, and air-gapped deployment
- [SOC2 Compliance](../compliance/SOC2_COMPLIANCE.md) - SOC2 controls mapping
- [GDPR Compliance](../compliance/GDPR_COMPLIANCE.md) - GDPR controls and data subject rights
