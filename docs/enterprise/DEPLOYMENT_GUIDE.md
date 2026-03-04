# Enterprise Deployment Guide

This guide covers deploying Auto Code in enterprise environments, including self-hosted and air-gapped deployments with full security and compliance controls.

## Table of Contents

- [Overview](#overview)
- [Deployment Modes](#deployment-modes)
  - [Cloud Deployment](#cloud-deployment)
  - [Self-Hosted Deployment](#self-hosted-deployment)
  - [Air-Gapped Deployment](#air-gapped-deployment)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Enterprise Configuration](#enterprise-configuration)
- [Security Setup](#security-setup)
  - [SSO/SAML Integration](#ssosaml-integration)
  - [Role-Based Access Control](#role-based-access-control)
  - [Data Residency](#data-residency)
- [Compliance Frameworks](#compliance-frameworks)
- [Audit Logging](#audit-logging)
- [Deployment Steps](#deployment-steps)
- [Verification](#verification)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

---

## Overview

Auto Code supports multiple deployment modes for enterprise requirements:

**Deployment Modes:**
- **Cloud** - Standard deployment with managed services
- **Self-Hosted** - On-premise deployment with internet access
- **Air-Gapped** - Isolated deployment with no internet access

**Enterprise Features:**
- SAML SSO integration (Okta, Azure AD, Google Workspace, etc.)
- Comprehensive audit logging for SOC2/GDPR/HIPAA compliance
- Role-based access control (RBAC) with 5 roles and 29 permissions
- Data residency controls (EU, US, UK, AP regions)
- Compliance framework support (SOC2, GDPR, HIPAA, CCPA, UK DPA)
- Local model proxy support for air-gapped environments
- Automated compliance reporting

---

## Deployment Modes

### Cloud Deployment

**Best for:** Organizations using cloud infrastructure with internet connectivity

**Requirements:**
- Internet connectivity for API access
- Claude API credentials or compatible LLM provider
- Optional: SAML SSO for authentication

**Configuration:**

```bash
# Enable enterprise mode
export ENTERPRISE_MODE=true

# Set deployment mode (default: cloud)
export ENTERPRISE_DEPLOYMENT_MODE=cloud

# Enable SSO (optional)
export ENTERPRISE_SSO_ENABLED=true
export ENTERPRISE_SSO_PROVIDER_TYPE=okta

# Configure data residency (optional)
export ENTERPRISE_DATA_REGION=EU

# Specify compliance frameworks
export ENTERPRISE_COMPLIANCE_FRAMEWORKS=SOC2,GDPR
```

**Deployment:**

```bash
# Clone repository
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Coding

# Install backend dependencies
cd apps/backend
pip install -r requirements.txt

# Authenticate with Claude
claude
# Follow OAuth flow

# Run build
python run.py --spec 001
```

### Self-Hosted Deployment

**Best for:** Organizations requiring on-premise deployment with internet access

**Requirements:**
- On-premise server or private cloud
- Internet connectivity for API access
- Custom API endpoint configuration (optional)
- SAML SSO recommended

**Configuration:**

```bash
# Enable enterprise mode
export ENTERPRISE_MODE=true

# Set deployment mode
export ENTERPRISE_DEPLOYMENT_MODE=self-hosted

# Custom API endpoint (if using proxy)
export ENTERPRISE_API_BASE_URL=https://your-proxy.example.com

# Enable required enterprise features
export ENTERPRISE_SSO_ENABLED=true
export ENTERPRISE_AUDIT_ENABLED=true
export ENTERPRISE_PERMISSIONS_ENABLED=true

# Configure data residency
export ENTERPRISE_DATA_REGION=EU
```

**Deployment:**

```bash
# Set up server
sudo apt-get update
sudo apt-get install python3.12 python3.12-venv git

# Create deployment user
sudo useradd -m -s /bin/bash autoclaude
sudo su - autoclaude

# Clone and install
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Coding/apps/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cat > .env << EOF
ENTERPRISE_MODE=true
ENTERPRISE_DEPLOYMENT_MODE=self-hosted
ENTERPRISE_SSO_ENABLED=true
ENTERPRISE_DATA_REGION=EU
ENTERPRISE_COMPLIANCE_FRAMEWORKS=SOC2,GDPR
EOF

# Validate deployment
python -c "
from enterprise.deployment import validate_deployment
validation = validate_deployment()
print(f'Valid: {validation.is_valid}')
for error in validation.errors:
    print(f'Error: {error}')
"
```

### Air-Gapped Deployment

**Best for:** Isolated environments with no internet access (government, defense, highly regulated industries)

**Requirements:**
- No internet connectivity required
- Local model server (llama.cpp, vLLM, TGI, etc.)
- Pre-downloaded model files
- Manual software transfer

**Architecture:**

```
┌─────────────────┐
│   Air-Gapped   │
│    Network      │
└────────┬────────┘
         │
         │ (no internet)
         │
┌────────▼────────────────────────────────┐
│  Auto Code (Air-Gapped Mode)        │
│  ├─ Local Model Proxy (llama.cpp)   │
│  ├─ Model Files (local filesystem)    │
│  ├─ SAML SSO (local IDP or bypass)  │
│  └─ Audit Logs (local storage)       │
└────────────────────────────────────────┘
```

**Configuration:**

```bash
# Enable enterprise mode
export ENTERPRISE_MODE=true

# Set air-gapped mode
export ENTERPRISE_DEPLOYMENT_MODE=air-gapped

# Configure local model proxy
export ENTERPRISE_MODEL_PROXY_URL=http://localhost:8080
export ENTERPRISE_MODEL_PROXY_MODEL=claude-sonnet-4
export ENTERPRISE_PROXY_VERIFY_SSL=false

# OR configure local model path
export ENTERPRISE_LOCAL_MODEL_PATH=/opt/models/claude

# Disable connectivity checks
export ENTERPRISE_OFFLINE_MODE=true
```

**Local Model Proxy Setup:**

Using llama.cpp:

```bash
# Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make

# Download model (on internet-connected machine, then transfer)
# Example: Claude Sonnet 4 compatible model
wget https://example.com/model.gguf

# Start model server
./llama-server --model model.gguf --port 8080 --host 0.0.0.0

# Configure Auto Code
export ENTERPRISE_MODEL_PROXY_URL=http://localhost:8080
```

Using vLLM:

```bash
# Install vLLM
pip install vllm

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
    --model /path/to/model \
    --port 8080 \
    --host 0.0.0.0

# Configure Auto Code
export ENTERPRISE_MODEL_PROXY_URL=http://localhost:8080
```

**Deployment:**

```bash
# On internet-connected machine: download dependencies
mkdir -p /tmp/autoclaude-deploy
cd /tmp/autoclaude-deploy
pip download -r apps/backend/requirements.txt -d packages/

# Transfer to air-gapped environment (sneakernet)
scp -r packages/ user@airgapped-server:/tmp/

# On air-gapped server: install from local packages
cd apps/backend
pip install --no-index --find-links=/tmp/packages -r requirements.txt

# Validate air-gapped deployment
python -c "
from enterprise.deployment import validate_deployment
validation = validate_deployment()
if validation.is_valid:
    print('Air-gapped deployment valid')
else:
    print('Errors:', validation.errors)
"
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|----------|---------------|
| **OS** | Linux, macOS, Windows | Ubuntu 22.04 LTS |
| **Python** | 3.12+ | 3.12+ |
| **Memory** | 8 GB RAM | 16 GB RAM |
| **Storage** | 20 GB free | 50 GB SSD |
| **Network** | 1 Mbps | 100 Mbps (not air-gapped) |

### Software Dependencies

```bash
# Python 3.12+
python3.12 --version

# Git
git --version

# Virtual environment
python3.12 -m venv .venv

# Activation
source .venv/bin/activate  # Linux/mac
.venv\Scripts\activate     # Windows
```

### Optional Dependencies

**For SAML SSO:**
```bash
pip install python3-saml
```

**For local model proxy (air-gapped):**
```bash
pip install vllm  # or llama.cpp
```

---

## Configuration

### Environment Variables

#### Core Settings

```bash
# Enable enterprise features (required for all enterprise capabilities)
ENTERPRISE_MODE=true

# Deployment mode: cloud|self-hosted|air-gapped
ENTERPRISE_DEPLOYMENT_MODE=cloud

# Compliance frameworks (comma-separated)
ENTERPRISE_COMPLIANCE_FRAMEWORKS=SOC2,GDPR,HIPAA
```

#### Audit Logging

```bash
# Enable audit logging (default: true in enterprise mode)
ENTERPRISE_AUDIT_ENABLED=true

# Audit log directory (default: .auto-claude/enterprise/audit)
ENTERPRISE_AUDIT_LOG_PATH=/var/log/autoclaude/audit

# Retention period in days (default: 90)
ENTERPRISE_AUDIT_RETENTION_DAYS=365
```

#### SSO/SAML

```bash
# Enable SAML SSO
ENTERPRISE_SSO_ENABLED=true

# Identity provider type: okta|azure_ad|google_workspace|onelogin|auth0|generic
ENTERPRISE_SSO_PROVIDER_TYPE=okta

# SAML configuration file (optional, can use env vars)
ENTERPRISE_SSO_CONFIG_PATH=/etc/autoclaude/saml.json
```

#### Data Residency

```bash
# Data region: EU|US|UK|AP|GLOBAL
ENTERPRISE_DATA_REGION=EU

# Custom API base URL for regional endpoints
ENTERPRISE_API_BASE_URL=https://eu-api.anthropic.com
```

#### Air-Gapped Mode

```bash
# Local model proxy URL
ENTERPRISE_MODEL_PROXY_URL=http://localhost:8080

# Model name for proxy
ENTERPRISE_MODEL_PROXY_MODEL=claude-sonnet-4

# Local model filesystem path
ENTERPRISE_LOCAL_MODEL_PATH=/opt/models/claude

# Disable SSL verification for local proxy
ENTERPRISE_PROXY_VERIFY_SSL=false

# Proxy timeout (seconds)
ENTERPRISE_PROXY_TIMEOUT=300
```

### Enterprise Configuration

**Programmatic Configuration:**

```python
from enterprise.config import EnterpriseConfig, get_enterprise_config

# Get current configuration
config = get_enterprise_config()

# Check deployment mode
if config.deployment_mode == EnterpriseConfig.DeploymentMode.AIR_GAPPED:
    print(f"Air-gapped mode: {config.custom_model_proxy_url}")

# Check compliance requirements
if config.requires_gdpr_compliance:
    print("GDPR compliance required")

# Export configuration
import json
with open('enterprise-config.json', 'w') as f:
    json.dump(config.to_dict(), f, indent=2)
```

**Configuration File:**

Create `enterprise-config.json`:

```json
{
  "is_enabled": true,
  "deployment_mode": "self-hosted",
  "audit_enabled": true,
  "sso_enabled": true,
  "data_residency_enabled": true,
  "data_region": "EU",
  "compliance_frameworks": ["SOC2", "GDPR"],
  "audit_log_path": "/var/log/autoclaude/audit",
  "audit_retention_days": 365,
  "custom_api_base_url": "https://eu-api.anthropic.com",
  "offline_mode": false
}
```

Load programmatically:

```python
import json
from enterprise.config import EnterpriseConfig

with open('enterprise-config.json') as f:
    data = json.load(f)
    config = EnterpriseConfig(**data)
```

---

## Security Setup

### SSO/SAML Integration

See [SSO Setup Guide](SSO_SETUP.md) for detailed SAML configuration with:
- Okta
- Azure AD (Entra ID)
- Google Workspace
- OneLogin
- Auth0
- Generic SAML 2.0 providers

### Role-Based Access Control

Auto Code implements RBAC with 5 predefined roles:

| Role | Permissions | Use Case |
|------|--------------|-----------|
| **ADMIN** | 29 permissions (all) | System administrators |
| **DEVELOPER** | 17 permissions | Developers creating specs and running builds |
| **OPERATOR** | 10 permissions | Build operators without spec modification |
| **AUDITOR** | 4 permissions | Compliance auditors |
| **VIEWER** | 5 permissions | Read-only access |

**Assigning Roles:**

```python
from enterprise.permissions import Role, Permission

# In SAML assertion mapping
user.groups = ["autoclaude-admins"]  # Map to ADMIN role

# Or programmatically
if user.groups and "autoclaude-developers" in user.groups:
    user.role = Role.DEVELOPER
```

**Custom Role Definitions:**

```python
from enterprise.permissions import Role, Permission, PermissionPolicy

# Define custom role
CUSTOM_POLICIES = {
    "BUILD_MANAGER": {
        Permission.BUILD_RUN,
        Permission.BUILD_STOP,
        Permission.BUILD_REVIEW,
        Permission.BUILD_MERGE,
        Permission.BUILD_DISCARD,
    }
}

# Use with permission checking
from enterprise.permissions import check_permission

if check_permission(user.role, Permission.BUILD_RUN):
    # User can run builds
    pass
```

### Data Residency

**Regional Configuration:**

```bash
# Set data region
export ENTERPRISE_DATA_REGION=EU

# Auto Code will:
# - Use EU API endpoints
# - Log data residency in audit trail
# - Validate data transfers
# - Enable GDPR compliance controls
```

**Supported Regions:**

| Region | Compliance Frameworks | API Endpoint |
|--------|----------------------|---------------|
| **EU** | GDPR, UK DPA | https://api.anthropic.com |
| **US** | CCPA | https://api.anthropic.com |
| **UK** | UK DPA, GDPR | https://api.anthropic.com |
| **AP** | Various APAC regulations | https://api.anthropic.com |
| **GLOBAL** | None specified | https://api.anthropic.com |

**Data Transfer Validation:**

```python
from enterprise.data_residency import DataResidencyConfig, validate_data_transfer

config = DataResidencyConfig('EU')

# Check if transfer is allowed
if config.is_data_transfer_allowed('US'):
    # Transfer EU data to US
    pass
else:
    # Log violation
    from enterprise.audit import get_audit_logger
    audit = get_audit_logger()
    audit.log_data_residency_check(
        context=context,
        compliant=False,
        required_region='EU',
        actual_region='US',
        resource_type='user_data',
        resource_id='user_123'
    )
```

---

## Compliance Frameworks

Auto Code supports simultaneous compliance with multiple frameworks:

**Supported Frameworks:**

| Framework | Environment Variable | Key Requirements |
|-----------|----------------------|-------------------|
| **SOC2** | `ENTERPRISE_COMPLIANCE_FRAMEWORKS=SOC2` | Access control, audit logging, encryption |
| **GDPR** | `ENTERPRISE_COMPLIANCE_FRAMEWORKS=GDPR` | Data residency, subject rights, breach notification |
| **HIPAA** | `ENTERPRISE_COMPLIANCE_FRAMEWORKS=HIPAA` | PHI protection, audit logs, access controls |
| **CCPA** | `ENTERPRISE_COMPLIANCE_FRAMEWORKS=CCPA` | Privacy rights, data disclosure |
| **UK DPA** | `ENTERPRISE_COMPLIANCE_FRAMEWORKS=UK_DPA` | GDPR-UK requirements |

**Enable Multiple Frameworks:**

```bash
export ENTERPRISE_COMPLIANCE_FRAMEWORKS=SOC2,GDPR,HIPAA
```

**Framework-Specific Controls:**

Each framework enables specific controls:

- **SOC2**: Enables RBAC, comprehensive audit logging, session management
- **GDPR**: Enables data residency, data subject rights, DPIA support
- **HIPAA**: Enables PHI logging, access logging, breach detection
- **CCPA**: Enables opt-out mechanisms, data disclosure tracking
- **UK DPA**: Enables post-Brexit GDPR controls

See [SOC2 Compliance](../compliance/SOC2_COMPLIANCE.md) and [GDPR Compliance](../compliance/GDPR_COMPLIANCE.md) for detailed requirements.

---

## Audit Logging

Auto Code provides comprehensive audit logging for compliance and security monitoring.

See [Audit Logging Guide](AUDIT_LOGGING.md) for:
- Audit event types and schemas
- Query and filtering capabilities
- Compliance report generation
- Log retention and rotation
- Export and integration

**Quick Start:**

```python
from enterprise.audit import EnterpriseAuditLogger, ActorType, AuditAction

# Initialize audit logger
audit = EnterpriseAuditLogger(log_dir=Path("/var/log/autoclaude/audit"))

# Start operation with context
ctx = audit.start_operation(
    actor_type=ActorType.USER,
    actor_id="user_123",
    user_email="user@example.com",
    user_role="developer",
    organization_id="org_456",
    project_id="proj_789",
    data_region="EU"
)

# Log events
audit.log(ctx, AuditAction.AGENT_CODER_STARTED)

# Log completion
audit.log(
    ctx,
    AuditAction.AGENT_CODER_COMPLETED,
    result="success",
    details={"subtasks_completed": 5}
)
```

---

## Deployment Steps

### Step 1: Prepare Environment

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev git

# Create user
sudo useradd -m -s /bin/bash autoclaude
sudo su - autoclaude
```

### Step 2: Install Auto Code

```bash
# Clone repository
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Coding

# Create virtual environment
cd apps/backend
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Enterprise Features

```bash
# Create environment file
cat > .env << EOF
# Enterprise mode
ENTERPRISE_MODE=true
ENTERPRISE_DEPLOYMENT_MODE=self-hosted

# Compliance
ENTERPRISE_COMPLIANCE_FRAMEWORKS=SOC2,GDPR

# Data residency
ENTERPRISE_DATA_REGION=EU

# SSO
ENTERPRISE_SSO_ENABLED=true
ENTERPRISE_SSO_PROVIDER_TYPE=okta

# Audit logging
ENTERPRISE_AUDIT_ENABLED=true
ENTERPRISE_AUDIT_LOG_PATH=/var/log/autoclaude/audit
ENTERPRISE_AUDIT_RETENTION_DAYS=365
EOF

# Load environment
source .env
```

### Step 4: Configure SAML SSO

See [SSO Setup Guide](SSO_SETUP.md) for identity provider-specific instructions.

```bash
# Copy SAML configuration
cp /path/to/saml-config.json ./

# Or configure via environment
export SAML_IDP_ENTITY_ID=https://okta.com/id/12345
export SAML_IDP_SSO_URL=https://okta.com/sso/12345
export SAML_IDP_X509_CERT="MIICert..."
```

### Step 5: Validate Deployment

```bash
# Run deployment validation
python -c "
from enterprise.deployment import validate_deployment
validation = validate_deployment()

print(f'Deployment valid: {validation.is_valid}')
print(f'Deployment mode: {validation.info[\"deployment_mode\"]}')
print(f'Enterprise enabled: {validation.info[\"enterprise_enabled\"]}')

for error in validation.errors:
    print(f'ERROR: {error}')
for warning in validation.warnings:
    print(f'WARNING: {warning}')
"
```

### Step 6: Test Authentication

```bash
# Test SSO authentication flow
python -c "
from enterprise.sso import SAMLProvider, load_saml_config

config = load_saml_config('saml-config.json')
provider = SAMLProvider(config)

# Generate auth URL
auth_url = provider.get_auth_url(relay_state='/test')
print(f'Auth URL: {auth_url}')
"
```

### Step 7: Verify Audit Logging

```bash
# Test audit logging
python -c "
from enterprise.audit import EnterpriseAuditLogger, ActorType, AuditAction

audit = EnterpriseAuditLogger()
ctx = audit.start_operation(
    actor_type=ActorType.USER,
    actor_id='test_user',
    user_email='test@example.com'
)

audit.log(ctx, AuditAction.AGENT_SESSION_STARTED, result='success')
print('Audit log test passed')
"

# Check log file
cat .auto-claude/enterprise/audit/audit_*.jsonl | jq .
```

### Step 8: Run Test Build

```bash
# Authenticate with Claude (or use SSO)
claude  # Follow OAuth flow

# Run test build
python run.py --spec 001

# Check audit logs for entries
ls .auto-claude/enterprise/audit/
```

---

## Verification

### Health Checks

```bash
# Check deployment status
python -c "
from enterprise.deployment import get_deployment_info
import json

info = get_deployment_info()
print(json.dumps(info, indent=2))
"
```

**Expected Output:**

```json
{
  "deployment_mode": "self-hosted",
  "is_air_gapped": false,
  "is_self_hosted": true,
  "offline_mode": false,
  "enterprise_enabled": true,
  "network_connectivity": true,
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

### Audit Log Verification

```bash
# Check for recent audit entries
python -c "
from enterprise.audit import get_audit_logger
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()
since = datetime.now(UTC) - timedelta(hours=1)

entries = audit.query_logs(since=since, limit=10)
for entry in entries:
    print(f'{entry.timestamp}: {entry.action.value}')
"
```

### Compliance Validation

```bash
# Validate SOC2 controls
python -c "
from enterprise.config import get_enterprise_config

config = get_enterprise_config()

if config.requires_soc2_compliance:
    print('SOC2 compliance enabled')
    print(f'  - Audit logging: {config.audit_enabled}')
    print(f'  - Permissions: {config.permissions_enabled}')
    print(f'  - SSO: {config.sso_enabled}')
"

# Validate GDPR controls
if config.requires_gdpr_compliance:
    print('GDPR compliance enabled')
    print(f'  - Data region: {config.data_region}')
    print(f'  - Data residency: {config.data_residency_enabled}')
"
```

### SSO Authentication Test

```bash
# Test SAML flow
python -c "
from enterprise.sso import SAMLProvider, load_saml_config
from enterprise.audit import get_audit_logger, ActorType

config = load_saml_config('saml-config.json')
provider = SAMLProvider(config)

# Generate auth request
auth_url = provider.get_auth_url(relay_state='/dashboard')
print(f'1. Auth URL generated: {auth_url[:50]}...')

# Simulate SAML response validation (requires actual SAML response)
# This step must be tested with real IdP callback
print('2. Complete auth flow via IdP')
print('3. Validate SAML response at ACS URL')
"
```

---

## Monitoring and Maintenance

### Log Management

**View Recent Audit Logs:**

```bash
# Today's audit log
today=$(date +%Y-%m-%d)
cat .auto-claude/enterprise/audit/audit_${today}.jsonl | jq .

# Filter by action
cat .auto-claude/enterprise/audit/audit_*.jsonl | \
  jq 'select(.action == "agent_coder_started")'
```

**Export Audit Logs:**

```python
from enterprise.audit import get_audit_logger
from datetime import datetime, timedelta, UTC
import json

audit = get_audit_logger()

# Export last 7 days
since = datetime.now(UTC) - timedelta(days=7)
entries = audit.query_logs(since=since, limit=10000)

with open('audit-export.json', 'w') as f:
    json.dump([e.to_dict() for e in entries], f, indent=2)
```

**Rotate Old Logs:**

```bash
# Configure logrotate
sudo tee /etc/logrotate.d/autoclaude-audit << EOF
/var/log/autoclaude/audit/*.jsonl {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    create 0640 autoclaude autoclaude
}
EOF

# Test configuration
sudo logrotate -d /etc/logrotate.d/autoclaude-audit
```

### Performance Monitoring

**Monitor Agent Performance:**

```python
from enterprise.audit import get_audit_logger
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()

# Get statistics for last 24 hours
since = datetime.now(UTC) - timedelta(hours=24)
stats = audit.get_statistics(since=since)

print(f"Total entries: {stats['total_entries']}")
print(f"Total duration: {stats['total_duration_ms'] / 1000:.2f}s")
print(f"Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']}")

# By action
for action, count in stats['by_action'].items():
    print(f"  {action}: {count}")
```

**Monitor Build Success Rate:**

```python
# Build success rate
builds = audit.query_logs(
    action=audit.AuditAction.BUILD_COMPLETED,
    since=datetime.now(UTC) - timedelta(days=7)
)

failed = audit.query_logs(
    action=audit.AuditAction.BUILD_FAILED,
    since=datetime.now(UTC) - timedelta(days=7)
)

total = len(builds) + len(failed)
success_rate = len(builds) / total * 100 if total > 0 else 0

print(f"Build success rate: {success_rate:.1f}%")
```

### Compliance Reporting

**Generate Weekly Compliance Report:**

```python
from enterprise.audit import get_audit_logger
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()

# Date range
end_date = datetime.now(UTC)
start_date = end_date - timedelta(days=7)

# Get statistics
stats = audit.get_statistics(since=start_date)

# Generate report
report = {
    "report_type": "weekly_compliance",
    "period_start": start_date.isoformat(),
    "period_end": end_date.isoformat(),
    "entry_count": stats["total_entries"],
    "by_action": stats["by_action"],
    "by_result": stats["by_result"],
    "by_actor_type": stats["by_actor_type"],
    "by_data_region": stats["by_data_region"],
    "token_usage": {
        "total_input_tokens": stats["total_input_tokens"],
        "total_output_tokens": stats["total_output_tokens"],
    },
    "duration_seconds": stats["total_duration_ms"] / 1000,
}

# Log report generation
ctx = audit.start_operation(
    actor_type=audit.ActorType.SYSTEM,
    actor_id="compliance_reporter"
)
audit.log_compliance_report(
    context=ctx,
    report_type="weekly",
    period_start=start_date,
    period_end=end_date,
    entry_count=stats["total_entries"]
)

print(json.dumps(report, indent=2))
```

---

## Troubleshooting

### Common Issues

**Issue: Enterprise modules not found**

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify enterprise directory exists
ls apps/backend/enterprise/

# Reinstall dependencies
pip install -r requirements.txt
```

**Issue: Deployment validation fails**

```bash
# Get detailed error information
python -c "
from enterprise.deployment import validate_deployment
validation = validate_deployment()

import json
print(json.dumps({
    'is_valid': validation.is_valid,
    'errors': validation.errors,
    'warnings': validation.warnings,
    'info': validation.info
}, indent=2))
"

# Check specific issues
# - Missing model proxy for air-gapped
# - Invalid data region
# - Network connectivity issues
# - Missing audit log directory permissions
```

**Issue: SSO authentication fails**

```bash
# Verify SAML configuration
python -c "
from enterprise.sso import load_saml_config

try:
    config = load_saml_config('saml-config.json')
    print(f'IdP: {config.idp_entity_id}')
    print(f'SSO URL: {config.idp_sso_url}')
    print(f'SP Entity ID: {config.sp_entity_id}')
    print(f'ACS URL: {config.sp_acs_url}')
except Exception as e:
    print(f'Configuration error: {e}')
"

# Check IdP connectivity
curl -v https://okta.com/id/12345  # Replace with your IdP URL
```

**Issue: Audit logs not written**

```bash
# Check directory permissions
ls -la .auto-claude/enterprise/audit/

# Fix permissions
chmod 755 .auto-claude/enterprise/audit/
chown autoclaude:autoclaude .auto-claude/enterprise/audit/

# Verify audit logger initialization
python -c "
from enterprise.audit import get_audit_logger

audit = get_audit_logger()
print(f'Enabled: {audit.enabled}')
print(f'Log dir: {audit.log_dir}')
print(f'Log file: {audit._get_log_file_path()}')
"
```

**Issue: Air-gapped mode not working**

```bash
# Verify air-gapped configuration
python -c "
from enterprise.deployment import is_air_gapped, get_model_proxy_url, get_local_model_path

print(f'Air-gapped: {is_air_gapped()}')
print(f'Model proxy URL: {get_model_proxy_url()}')
print(f'Local model path: {get_local_model_path()}')
"

# Test model proxy connectivity
curl -v http://localhost:8080/v1/models

# Verify model files
ls -lh /opt/models/claude/
```

**Issue: Data residency validation fails**

```bash
# Check configured region
python -c "
from enterprise.config import get_enterprise_config

config = get_enterprise_config()
print(f'Data region: {config.data_region}')
print(f'Regional endpoint: {config.custom_api_base_url}')
"

# Validate region selection
python -c "
from enterprise.data_residency import DataResidencyConfig

try:
    config = DataResidencyConfig('EU')
    print(f'Region: {config.region}')
    print(f'GDPR compliant: {config.is_gdpr_compliant()}')
except ValueError as e:
    print(f'Invalid region: {e}')
"
```

### Debug Mode

Enable verbose logging:

```bash
# Set environment
export AUTO_CLAUDE_DEBUG=true
export PYTHONUNBUFFERED=1

# Run with verbose output
python run.py --spec 001 --verbose
```

Check enterprise module logs:

```bash
# Tail audit logs in real-time
tail -f .auto-claude/enterprise/audit/audit_*.jsonl | jq .

# Filter by specific action
tail -f .auto-claude/enterprise/audit/audit_*.jsonl | \
  jq 'select(.action == "sso_login_failed")'
```

### Getting Help

**Resources:**
- [Documentation](../README.md)
- [SOC2 Compliance](../compliance/SOC2_COMPLIANCE.md)
- [GDPR Compliance](../compliance/GDPR_COMPLIANCE.md)
- [SSO Setup Guide](SSO_SETUP.md)
- [Audit Logging Guide](AUDIT_LOGGING.md)

**Community:**
- [Discord](https://discord.gg/KCXaPBr4Dj)
- [GitHub Issues](https://github.com/OBenner/Auto-Coding/issues)
- [GitHub Discussions](https://github.com/OBenner/Auto-Coding/discussions)

---

## Appendix

### Configuration Checklist

**Pre-Deployment:**
- [ ] Python 3.12+ installed
- [ ] Git repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] User account created
- [ ] File permissions configured

**Enterprise Configuration:**
- [ ] `ENTERPRISE_MODE=true` set
- [ ] Deployment mode configured
- [ ] Compliance frameworks specified
- [ ] Data residency region set
- [ ] Audit logging enabled
- [ ] Audit log directory created with proper permissions

**SSO Setup:**
- [ ] SAML IdP configured
- [ ] SAML configuration file created
- [ ] IdP metadata uploaded to Auto Code
- [ ] Auto Code SP metadata uploaded to IdP
- [ ] ACS URL configured in IdP
- [ ] Attribute mapping configured
- [ ] Test authentication successful

**RBAC Configuration:**
- [ ] User roles defined
- [ ] Group mappings configured
- [ ] Permission policies verified
- [ ] Test users created
- [ ] Role assignment tested

**Air-Gapped Deployment:**
- [ ] Model proxy installed and running
- [ ] Model files downloaded and accessible
- [ ] Local model path configured
- [ ] Network connectivity verified (offline)
- [ ] Proxy URL tested
- [ ] SSL verification configured
- [ ] Timeout values set appropriately

**Compliance:**
- [ ] Compliance frameworks selected
- [ ] Audit log retention policy configured
- [ ] Data residency controls validated
- [ ] Data transfer rules configured
- [ ] Compliance reporting scheduled
- [ ] Audit evidence collection tested

**Post-Deployment:**
- [ ] Deployment validation passes
- [ ] SSO authentication works
- [ ] Audit logs are written
- [ ] Test build runs successfully
- [ ] Permissions enforced correctly
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Documentation updated

### Environment Variable Reference

| Variable | Type | Default | Description |
|-----------|------|---------|-------------|
| `ENTERPRISE_MODE` | bool | false | Enable enterprise features |
| `ENTERPRISE_DEPLOYMENT_MODE` | enum | cloud | Deployment mode (cloud/self-hosted/air-gapped) |
| `ENTERPRISE_AUDIT_ENABLED` | bool | true | Enable audit logging |
| `ENTERPRISE_AUDIT_LOG_PATH` | path | .auto-claude/enterprise/audit | Audit log directory |
| `ENTERPRISE_AUDIT_RETENTION_DAYS` | int | 90 | Log retention period |
| `ENTERPRISE_SSO_ENABLED` | bool | false | Enable SAML SSO |
| `ENTERPRISE_SSO_PROVIDER_TYPE` | enum | generic | Identity provider type |
| `ENTERPRISE_SSO_CONFIG_PATH` | path | null | SAML configuration file |
| `ENTERPRISE_PERMISSIONS_ENABLED` | bool | true | Enable RBAC |
| `ENTERPRISE_DATA_REGION` | enum | null | Data residency region (EU/US/UK/AP/GLOBAL) |
| `ENTERPRISE_COMPLIANCE_FRAMEWORKS` | list | [] | Compliance frameworks (comma-separated) |
| `ENTERPRISE_API_BASE_URL` | url | null | Custom API endpoint |
| `ENTERPRISE_MODEL_PROXY_URL` | url | null | Local model proxy (air-gapped) |
| `ENTERPRISE_MODEL_PROXY_MODEL` | string | claude-sonnet-4 | Model name for proxy |
| `ENTERPRISE_LOCAL_MODEL_PATH` | path | null | Local model filesystem path |
| `ENTERPRISE_OFFLINE_MODE` | bool | auto | Disable connectivity checks |
| `ENTERPRISE_PROXY_VERIFY_SSL` | bool | true | Verify SSL for proxy |
| `ENTERPRISE_PROXY_TIMEOUT` | int | 300 | Proxy timeout (seconds) |

### Support Contact

For enterprise deployment assistance:
- **Documentation:** https://github.com/OBenner/Auto-Coding
- **Issues:** https://github.com/OBenner/Auto-Coding/issues
- **Discord:** https://discord.gg/KCXaPBr4Dj
- **Email:** enterprise@autoclaude.example.com (replace with actual contact)

---

<div align="center">

**Enterprise Deployment Guide**

[← Back to Main Documentation](../README.md)

</div>
