# GDPR Compliance

Auto Code implements comprehensive data protection controls to meet GDPR (General Data Protection Regulation) compliance requirements for processing personal data of EU data subjects. This document describes how Auto Code addresses GDPR requirements and helps enterprises demonstrate compliance.

## Table of Contents

- [Overview](#overview)
- [Data Protection Principles](#data-protection-principles)
  - [Lawfulness, Fairness, and Transparency](#lawfulness-fairness-and-transparency)
  - [Purpose Limitation](#purpose-limitation)
  - [Data Minimization](#data-minimization)
  - [Accuracy](#accuracy)
  - [Storage Limitation](#storage-limitation)
  - [Integrity and Confidentiality](#integrity-and-confidentiality)
  - [Accountability](#accountability)
- [Lawful Basis for Processing](#lawful-basis-for-processing)
- [Data Subject Rights](#data-subject-rights)
  - [Right to be Informed](#right-to-be-informed)
  - [Right of Access](#right-of-access)
  - [Right to Rectification](#right-to-rectification)
  - [Right to Erasure](#right-to-erasure)
  - [Right to Restrict Processing](#right-to-restrict-processing)
  - [Right to Data Portability](#right-to-data-portability)
  - [Right to Object](#right-to-object)
  - [Rights Regarding Automated Decision Making](#rights-regarding-automated-decision-making)
- [Data Residency and International Transfers](#data-residency-and-international-transfers)
- [Data Protection by Design and by Default](#data-protection-by-design-and-by-default)
- [Records of Processing Activities](#records-of-processing-activities)
- [Data Protection Impact Assessments](#data-protection-impact-assessments)
- [Data Breach Notification](#data-breach-notification)
- [Data Protection Officer](#data-protection-officer)
- [Compliance Monitoring](#compliance-monitoring)
- [Audit Evidence](#audit-evidence)

---

## Overview

The GDPR (EU 2016/679) is a European Union regulation that governs the processing of personal data of EU data subjects. Auto Code provides comprehensive controls to help enterprises achieve and demonstrate GDPR compliance.

**Key GDPR Requirements:**
- **Territorial Scope** - Applies to processing of EU data subjects' data, regardless of where processing occurs
- **Lawful Processing** - Must have a lawful basis for processing personal data
- **Data Subject Rights** - Individuals have enhanced rights over their personal data
- **Data Protection by Design** - Privacy must be built into systems from the ground up
- **Accountability** - Organizations must demonstrate compliance through documentation
- **Data Breach Notification** - Must notify authorities and affected individuals within 72 hours
- **International Data Transfers** - Restrictions on transferring data outside the EU/EEA
- **DPO Requirements** - May require a Data Protection Officer for certain processing activities

Auto Code's enterprise features provide built-in GDPR controls for compliance demonstration, including audit logging, data residency controls, data subject rights automation, and comprehensive record-keeping.

---

## Data Protection Principles

### Lawfulness, Fairness, and Transparency

Auto Code ensures all processing activities are lawful, fair, and transparent to data subjects.

#### Legal Basis Identification

Identify and document the lawful basis for each processing activity:

| Legal Basis | Description | When to Use |
|-------------|-------------|-------------|
| **Consent** | Data subject consented to processing | User opts in to data collection |
| **Contract** - Necessary for contract performance | Employment contracts, service agreements |
| **Legal Obligation** - Required by law | Regulatory reporting requirements |
| **Vital Interests** - Protect life | Emergency situations |
| **Public Task** - Public interest task | Government functions |
| **Legitimate Interests** - Legitimate business purposes | Fraud prevention, security |

**Configuration Example:**

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Log processing with legal basis
audit_logger.log_processing_activity(
    activity_type="user_authentication",
    legal_basis="contract",
    data_subject_id="user_123",
    purpose="Service access provision"
)
```

#### Transparency Controls

Auto Code provides transparency features:

- **Privacy Notice Management** - Configurable privacy notices for data collection
- **Purpose Specification** - Clear documentation of data processing purposes
- **Processing Logs** - Complete audit trail of all data processing activities

### Purpose Limitation

Auto Code ensures personal data is processed only for specified, explicit, and legitimate purposes.

#### Purpose Configuration

Define processing purposes in your enterprise configuration:

```yaml
# .auto-claude/enterprise_config.yaml
processing_purposes:
  - id: "user_authentication"
    description: "User authentication and session management"
    legal_basis: "contract"
    data_categories: ["user_id", "authentication_tokens"]
    retention_days: 365

  - id: "audit_logging"
    description: "Security and compliance audit logging"
    legal_basis: "legal_obligation"
    data_categories: ["user_actions", "access_logs"]
    retention_days: 2555  # 7 years
```

#### Purpose Validation

Automatic validation prevents purpose drift:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Validates that data is used only for declared purposes
audit_logger.validate_processing_purpose(
    activity="code_generation",
    declared_purpose="user_authentication",
    allowed_purposes=["user_authentication", "session_management"]
)
```

### Data Minimization

Auto Code implements data minimization by collecting only necessary data.

#### Default Data Collection

By default, Auto Code minimizes PII collection:

- **User IDs instead of email addresses**
- **Truncated IP addresses** (last octet zeroed)
- **No sensitive data by default**
- **Optional PII redaction**

**Enable PII redaction:**

```bash
# .env configuration
AUDIT_LOG_REDACT_PII=true
```

#### Data Minimization Controls

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Log with minimized data
audit_logger.log_event(
    action="user_login",
    data_subject_id="user_123",  # Not email address
    ip_address="192.168.1.100",  # Will be truncated to 192.168.1.0
    redact_pii=True  # Additional redaction layer
)
```

#### Data Classification

Classify data to apply appropriate minimization rules:

| Classification | Minimization Level | Example |
|----------------|-------------------|---------|
| **Public** | No minimization needed | Documentation |
| **Internal** | User IDs only | Build logs |
| **Confidential** | User IDs + truncated IPs | Authentication logs |
| **Special Category** | Explicit consent required | Health data (if collected) |

### Accuracy

Auto Code maintains accurate and up-to-date personal data.

#### Data Quality Controls

- **Input Validation** - All user inputs validated and sanitized
- **Type Checking** - Strong type enforcement for all data
- **Error Logging** - Complete error tracking with context
- **Data Verification** - SHA256 checksums for file integrity

#### Rectification Support

Enable data subjects to correct inaccurate data:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Data subject requests rectification
audit_logger.log_data_rectification(
    data_subject_id="user_123",
    field="user_email",
    old_value="old@email.com",
    new_value="new@email.com",
    requested_by="data_subject",
    approved_by="admin_456"
)
```

### Storage Limitation

Auto Code implements data retention policies to ensure data is not kept longer than necessary.

#### Configurable Retention Periods

Set retention periods by data type:

```bash
# .env configuration
AUDIT_LOG_RETENTION_YEARS=7
USER_DATA_RETENTION_DAYS=365
BUILD_ARTIFACT_RETENTION_DAYS=90
DELETED_DATA_RETENTION_DAYS=30  # Backup retention
```

#### Automated Deletion

Automatic data deletion after retention period expires:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Check for expired data
expired_data = audit_logger.get_expired_data(
    retention_years=7
)

# Delete expired data
for record in expired_data:
    audit_logger.delete_expired_record(
        record_id=record['id'],
        reason="retention_period_expired",
        approved_by="system"
    )
```

#### Retention by Data Type

| Data Type | Default Retention | Legal Basis |
|-----------|-------------------|-------------|
| Audit Logs | 7 years | Legal obligation (SOC2/GDPR) |
| User Data | 1 year | Contractual necessity |
| Build Artifacts | 90 days | Legitimate interests |
| Authentication Data | 1 year | Contractual necessity |
| Backup Data | 30 days | Legal requirement |

### Integrity and Confidentiality

Auto Code implements comprehensive security measures to ensure data integrity and confidentiality (see [SOC2 Compliance](SOC2_COMPLIANCE.md) for detailed security controls).

#### Security Measures

- **Encryption at Rest** - AES-256-GCM for sensitive data
- **Encryption in Transit** - TLS 1.3 for all network communications
- **Access Controls** - Role-based access control (RBAC)
- **Audit Logging** - Complete audit trail of all data access
- **Authentication** - OAuth 2.0 and SAML SSO support

#### Data Protection Impact Assessment (DPIA) Support

Auto Code supports DPIA by logging:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Log DPIA scoping
audit_logger.log_dpia_scope(
    processing_activity="automated_code_generation",
    data_types_processed=["user_code", "user_metadata"],
    data_subjects_count="all_users",
    risk_likelihood="low",
    risk_severity="low",
    mitigation_measures=["encryption", "access_controls", "audit_logging"]
)
```

### Accountability

Auto Code helps demonstrate compliance through comprehensive record-keeping and audit trails.

#### Compliance Documentation

Auto Code provides:

- **[Records of Processing Activities](#records-of-processing-activities)** - Article 30 ROPA
- **[Audit Logs](#audit-evidence)** - Complete processing history
- **[Data Subject Request Logs](#data-subject-rights)** - DSR tracking
- **[Breach Notification Records](#data-breach-notification)** - Incident documentation
- **[Policy Documentation](#compliance-monitoring)** - Internal policies

#### Accountability Features

```bash
# Generate GDPR compliance report
python -m enterprise.compliance gdpr-report \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --include-ropa \
  --include-dsrs \
  --include-security-measures \
  --output gdpr_compliance_2024.pdf
```

---

## Lawful Basis for Processing

Auto Code supports all six lawful bases under GDPR Article 6.

### Legal Basis Configuration

Configure the legal basis for each processing activity:

```yaml
# .auto-claude/processing_config.yaml
processing_activities:
  - activity: "user_authentication"
    legal_basis: "contract"
    description: "Necessary for service provision"
    data_types: ["user_id", "authentication_tokens"]

  - activity: "audit_logging"
    legal_basis: "legal_obligation"
    description: "Required for SOC2/GDPR compliance"
    data_types: ["user_actions", "access_logs", "timestamps"]

  - activity: "usage_analytics"
    legal_basis: "legitimate_interests"
    description: "Service improvement and security"
    data_types: ["usage_patterns", "performance_metrics"]
    legitimate_interest_test: "Documented in LIA assessment"
```

### Legitimate Interests Assessment (LIA)

When relying on legitimate interests, complete an LIA:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Log legitimate interests assessment
audit_logger.log_legitimate_interests_assessment(
    processing_purpose="usage_analytics",
    purpose_description="Improve service performance",
    interest_necessity="Service improvement requires usage patterns",
    balancing_test="Data minimization applied; user can opt out",
    data_subject_rights="Users can request deletion/portability",
    risk_assessment="Low risk; anonymized aggregates used"
)
```

### Special Category Data

For special category data (Article 9), additional safeguards apply:

| Special Category | Condition for Processing | Auto Code Support |
|-----------------|--------------------------|-------------------|
| Health data | Explicit consent or vital interests | Configurable consent tracking |
| Biometric data | Explicit consent or substantial public interest | Biometric data exclusion |
| Political opinions | Explicit consent | No political data collection |
| Trade union membership | Explicit consent | No union data collection |

**Auto Code does not collect special category data by default.**

---

## Data Subject Rights

GDPR grants data subjects specific rights over their personal data. Auto Code provides tools to manage and automate these rights.

### Right to be Informed

#### Privacy Notice Management

Auto Code supports configurable privacy notices:

```yaml
# .auto-claude/privacy_notices.yaml
privacy_notice:
  version: "1.0"
  last_updated: "2024-02-13"

  data_controller:
    name: "Your Organization"
    address: "123 Business St, City, Country"
    email: "dpo@yourorg.com"
    phone: "+1-555-0123"

  data_protection_officer:
    name: "Jane Smith"
    email: "dpo@yourorg.com"

  processing_activities:
    - activity: "User Authentication"
      purpose: "Service access and session management"
      legal_basis: "Contract performance"
      data_types: ["User ID", "Authentication tokens"]
      retention_period: "1 year"
      international_transfers: "None (EU region)"

  data_subject_rights:
    - right: "Right of Access"
      description: "Request a copy of your personal data"
    - right: "Right to Erasure"
      description: "Request deletion of your personal data"
    - right: "Right to Rectification"
      description: "Correct inaccurate personal data"
    - right: "Right to Portability"
      description: "Receive your data in machine-readable format"
    - right: "Right to Object"
      description: "Object to processing based on legitimate interests"
```

### Right of Access

Data subjects can request a copy of all personal data processed by Auto Code.

#### Data Access Request Automation

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Process data access request (DSAR)
access_report = audit_logger.export_user_data(
    data_subject_id="user_123",
    format="json",
    include_processing_activities=True,
    include_audit_trail=True
)

# Report includes:
# - All personal data stored
# - Processing activities
# - Data categories
# - Recipients (if any)
# - Retention periods
# - Source of data
# - Automated decision-making details
```

#### Access Report Contents

```json
{
  "data_subject_id": "user_123",
  "request_date": "2024-02-13T10:00:00Z",
  "response_date": "2024-02-13T10:05:00Z",

  "personal_data": {
    "user_id": "user_123",
    "authentication_events": [...],
    "audit_logs": [...],
    "preferences": {...}
  },

  "processing_activities": [
    {
      "activity": "user_authentication",
      "purpose": "Service access",
      "legal_basis": "contract",
      "data_categories": ["user_id", "auth_tokens"],
      "retention_days": 365
    }
  ],

  "data_recipients": [],
  "retention_periods": {...},
  "data_sources": ["user_provided", "system_generated"]
}
```

### Right to Rectification

Data subjects can correct inaccurate or incomplete personal data.

#### Rectification Workflow

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Process rectification request
audit_logger.log_data_rectification_request(
    data_subject_id="user_123",
    fields_to_update=["user_email"],
    current_values={"user_email": "old@email.com"},
    requested_values={"user_email": "new@email.com"},
    request_date="2024-02-13T10:00:00Z",
    evidence=["Email verification link clicked"]
)

# Update the data
audit_logger.rectify_user_data(
    data_subject_id="user_123",
    updates={"user_email": "new@email.com"},
    approved_by="admin_456",
    reason="data_subject_request"
)
```

### Right to Erasure (Right to be Forgotten)

Data subjects can request deletion of their personal data, with certain exceptions.

#### Deletion Request Handling

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Process erasure request
deletion_report = audit_logger.process_deletion_request(
    data_subject_id="user_123",
    reason="gdpr_erasure_request",
    requested_by="data_subject",
    check_exceptions=True  # Check for legal exceptions
)

# Report includes:
# - Data deleted
# - Data retained (with legal reason)
# - Third-party notifications sent
```

#### Deletion Exceptions

Auto Code checks for legal exceptions before deletion:

| Exception | Description | Example |
|-----------|-------------|---------|
| **Legal Obligation** | Data required by law | Audit logs (7 years) |
| **Contract** | Needed for contract performance | Active user account |
| **Public Interest** | Public task or official authority | Regulatory reporting |
| **Legal Claim** | Needed for legal defense | Investigation data |
| **Public Health** | Public health or medical | Health monitoring (if applicable) |

**Deletion Result:**

```json
{
  "data_subject_id": "user_123",
  "request_date": "2024-02-13T10:00:00Z",
  "completion_date": "2024-02-13T10:05:00Z",

  "deleted": {
    "user_preferences": true,
    "session_data": true,
    "build_artifacts": true
  },

  "retained": {
    "audit_logs": {
      "reason": "legal_obligation",
      "retention_until": "2031-02-13",
      "regulation": "SOC2/GDPR Article 30"
    }
  }
}
```

### Right to Restrict Processing

Data subjects can request restriction of processing in certain circumstances.

#### Restriction Scenarios

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Restrict processing (data kept but not used)
audit_logger.restrict_processing(
    data_subject_id="user_123",
    reason="accuracy_contested",
    fields=["user_email", "user_metadata"],
    restricted_until="accuracy_verified",
    note="User claims email is incorrect; verification pending"
)
```

#### Restriction Types

| Restriction Reason | Effect | Duration |
|-------------------|--------|----------|
| Accuracy contested | Data stored but not processed | Until verified |
| Unlawful processing | Processing stopped | Until lawful |
| No longer needed | Data stored but not processed | Indefinite |
| Legal claim | Data preserved for defense | Until claim resolved |

### Right to Data Portability

Data subjects can receive their data in a structured, machine-readable format.

#### Portability Export

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Export for portability
portability_data = audit_logger.export_user_data(
    data_subject_id="user_123",
    format="json",  # Machine-readable format
    include_consent_history=True,
    include_processing_activities=True
)

# Save to file for data subject
with open(f"user_123_portability_{datetime.now().isoformat()}.json", "w") as f:
    json.dump(portability_data, f, indent=2)
```

#### Portability Format

```json
{
  "export_metadata": {
    "data_subject_id": "user_123",
    "export_date": "2024-02-13T10:00:00Z",
    "format": "json",
    "version": "1.0"
  },

  "personal_data": {
    "user_id": "user_123",
    "user_preferences": {...},
    "activity_history": [...]
  },

  "processing_activities": [...],
  "consent_history": [...]
}
```

### Right to Object

Data subjects can object to processing based on legitimate interests or direct marketing.

#### Objection Handling

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Process objection
audit_logger.process_objection(
    data_subject_id="user_123",
    objection_type="legitimate_interests",
    processing_activities=["usage_analytics"],
    reason="User objects to analytics processing",
    action_taken="processing_stopped"
)
```

### Rights Regarding Automated Decision Making

Data subjects have rights regarding automated decision-making, including profiling.

#### Automated Decision Logging

Auto Code logs all AI agent decisions for transparency:

```json
{
  "timestamp": "2024-02-13T10:30:45.123456Z",
  "agent_decision": {
    "agent_type": "coder",
    "model": "claude-sonnet-4-5",
    "task": "Implement authentication feature",
    "decision": "Generate OAuth integration code",
    "logic": "Spec requirement for SSO support",
    "human_review": "qa_reviewer_agent",
    "confidence_level": "high"
  }
}
```

#### Human Oversight

Auto Code provides human oversight through:

- **QA Reviewer Agent** - Validates all AI-generated code
- **QA Fixer Agent** - Corrects issues identified by reviewer
- **Manual Review** - Final merge requires user approval
- **Audit Trail** - Complete decision documentation

---

## Data Residency and International Transfers

GDPR restricts the transfer of personal data outside the European Economic Area (EEA) unless adequate safeguards are in place.

### Data Residency Configuration

Auto Code supports data residency controls for EU data:

```bash
# .env configuration
DATA_RESIDENCY_REGION=EU
```

#### Supported Regions

| Region | API Endpoint | GDPR Adequacy Decision |
|--------|--------------|------------------------|
| **EU** | `https://api.anthropic.com` | Yes (in EU) |
| **US** | `https://api.anthropic.com` | No (requires SCCs) |
| **UK** | `https://api.anthropic.com` | Yes (UK GDPR) |
| **AP** | `https://api.anthropic.com` | No (requires SCCs) |
| **GLOBAL** | `https://api.anthropic.com` | No (requires SCCs) |

**Configuration:**

```python
from enterprise.data_residency import DataResidencyConfig

# Configure EU data residency
config = DataResidencyConfig('EU')

# Check if transfer to US is allowed
if not config.can_transfer_to_region('US'):
    raise ValueError("GDPR restriction: EU-US transfer requires SCCs")
```

### Transfer Mechanisms

#### Standard Contractual Clauses (SCCs)

For transfers outside the EEA without an adequacy decision, use SCCs:

```yaml
# .auto-claude/transfer_config.yaml
international_transfers:
  - destination: "US"
    mechanism: "scc"
    scc_version: "2021-09-01"
    scc_signed_date: "2024-01-15"
    scc_counterparty: "Anthropic PBC"
    third_party_benefits: "Yes"
    onward_transfer_allowed: "No"
    supplement_signed: "Yes"
```

#### Adequacy Decisions

Some countries have adequacy decisions from the European Commission:

| Country | Adequacy Decision | Notes |
|---------|-------------------|-------|
| United Kingdom | ✅ Yes | UK GDPR |
| Japan | ✅ Yes | Mutual adequacy |
| Canada (commercial) | ✅ Yes | Partial adequacy |
| United States | ❌ No | Requires SCCs or TIA |
| Australia | ❌ No | Requires SCCs |
| India | ❌ No | Requires SCCs |

### Transfer Validation

Automatic validation before data transfers:

```python
from enterprise.data_residency import DataResidencyConfig
from enterprise.audit import EnterpriseAuditLogger

config = DataResidencyConfig('EU')
audit_logger = EnterpriseAuditLogger(spec_dir)

# Attempt data transfer
target_region = 'US'

if config.can_transfer_to_region(target_region):
    # Transfer allowed (e.g., SCCs in place)
    audit_logger.log_data_transfer_approved(
        from_region='EU',
        to_region='US',
        mechanism='scc',
        scc_reference='scc_001',
        data_categories=['user_logs'],
        data_subject_count=150
    )
else:
    # Transfer not allowed
    audit_logger.log_data_residency_violation(
        from_region='EU',
        to_region='US',
        reason='No adequate safeguards',
        gdpr_article='44-50'
    )
```

---

## Data Protection by Design and by Default

### Data Protection by Design (Article 25)

Auto Code implements data protection measures from the ground up:

#### Architecture Principles

1. **Privacy as Default** - No personal data collected unless necessary
2. **Data Minimization** - Only collect data required for processing
3. **Privacy by Default Settings** - Most private configuration by default
4. **End-to-End Security** - Encryption at rest and in transit
5. **Access Controls** - RBAC with principle of least privilege
6. **Audit Logging** - Complete processing trail

#### Technical Measures

```python
# Privacy by design in action

# 1. Default: No PII collection
AUDIT_LOG_INCLUDE_PII=false  # Default setting

# 2. Data minimization
AUDIT_LOG_REDACT_PII=true  # PII redaction enabled

# 3. Encryption by default
AUDIT_LOG_ENCRYPTION_ENABLED=true

# 4. Access control
ENTERPRISE_DEFAULT_ROLE=viewer  # Least privilege by default

# 5. Data residency
DATA_RESIDENCY_REGION=EU  # GDPR compliance by default
```

### DPIA Integration

For high-risk processing, Auto Code supports Data Protection Impact Assessments:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# DPIA for automated decision-making
audit_logger.create_dpia(
    processing_activity="automated_code_generation",
    risk_necessity="Generative AI output may contain security vulnerabilities",
    risk_likelihood="medium",
    risk_severity="high",
    mitigation_measures=[
        "QA reviewer agent validates all output",
        "Security scanning before merge",
        "Manual user approval required",
        "Complete audit trail"
    ],
    dpia_approved_by="dpo@yourorg.com",
    dpia_date="2024-02-13"
)
```

---

## Records of Processing Activities

GDPR Article 30 requires organizations to maintain comprehensive records of processing activities.

### ROPA Template

Auto Code generates ROPA documentation:

```python
from enterprise.compliance import ComplianceReportGenerator

generator = ComplianceReportGenerator()

# Generate Article 30 ROPA
ropa = generator.generate_ropa(
    include_vendors=True,
    include_data_categories=True,
    include_data_subjects=True
)

# Export to Excel for GDPR submission
ropa.export_excel("ropa_article_30.xlsx")
```

### ROPA Contents

The ROPA includes:

#### Processing Activity Record

| Field | Description | Example |
|-------|-------------|---------|
| **Controller Name** | Organization name | "Acme Corp" |
| **Controller Representative** | EU representative (if non-EU) | "Acme EU GmbH" |
| **Purpose of Processing** | Why data is processed | "Service authentication" |
| **Categories of Data** | Types of personal data | "User IDs, authentication tokens" |
| **Data Subjects** | Individuals whose data is processed | "Service users, employees" |
| **Data Recipients** | Who receives the data | "None (EU region)" |
| **International Transfers** | Transfers outside EEA | "None" |
| **Retention Period** | How long data is kept | "1 year" |
| **Security Measures** | Technical safeguards | "Encryption, access controls, audit logging" |
| **Legal Basis** | GDPR Article 6 basis | "Contract performance (Article 6(1)(b))" |

#### Auto Code Processing Activities

Auto Code maintains ROPA for:

1. **User Authentication**
   - Purpose: Service access and session management
   - Legal Basis: Contract (Article 6(1)(b))
   - Data: User IDs, authentication tokens, timestamps
   - Retention: 1 year
   - Recipients: None

2. **Audit Logging**
   - Purpose: Security monitoring, compliance demonstration
   - Legal Basis: Legal obligation (Article 6(1)(c))
   - Data: User actions, timestamps, IP addresses (truncated)
   - Retention: 7 years
   - Recipients: Internal security team, auditors

3. **Agent Operations**
   - Purpose: Automated code generation and validation
   - Legal Basis: Legitimate interests (Article 6(1)(f))
   - Data: Code repositories, build artifacts
   - Retention: 90 days
   - Recipients: None

---

## Data Protection Impact Assessments

GDPR Article 35 requires DPIAs for high-risk processing.

### When to Conduct a DPIA

Conduct a DPIA for:

- **Systematic and extensive evaluation** - Including profiling
- **Large-scale processing** - Special category data or criminal convictions
- **Public monitoring** - Public areas, large scale
- **New technologies** - AI, biometrics, etc.

### DPIA Process

Auto Code supports DPIA through audit logging:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# 1. Describe processing
audit_logger.log_dpia_description(
    processing_name="automated_code_review",
    purposes=["Security vulnerability detection", "Code quality analysis"],
    technologies=["AI model (Claude)", "Static analysis"],
    data_sources=["Code repositories", "Git history"],
    data_categories=["User-generated code", "Commit metadata"]
)

# 2. Assess necessity and proportionality
audit_logger.log_dpia_necessity_assessment(
    necessity="Code review required for security",
    proportionality="Limited to code metadata; no PII",
    alternatives=["Manual review (slower)", "No review (unacceptable)"]
)

# 3. Assess risks to data subjects
audit_logger.log_dpia_risk_assessment(
    risk_type="automated_decision_making",
    likelihood="low",
    severity="medium",
    impact="Code may contain vulnerabilities; human review mitigates"
)

# 4. Identify mitigation measures
audit_logger.log_dpia_mitigation(
    measures=[
        "Human QA reviewer validates AI output",
        "Users control final merge decision",
        "Complete audit trail",
        "Users can request deletion",
        "No PII in code analysis"
    ]
)
```

### DPIA Template

```markdown
# Data Protection Impact Assessment

## 1. Processing Description
- **Name:** Automated Code Generation
- **Purpose:** Generate code from natural language specifications
- **Technologies:** AI model (Claude), Git version control
- **Data Sources:** User specifications, code repositories

## 2. Necessity and Proportionality
- **Necessity:** Required for autonomous coding functionality
- **Proportionality:** Limited to code generation; minimal personal data
- **Alternatives Considered:** Manual coding (slower), No automation (not viable)

## 3. Risk Assessment
| Risk | Likelihood | Severity | Mitigation |
|------|-----------|----------|------------|
| Generated code vulnerabilities | Low | Medium | QA reviewer validation |
| Exposure of sensitive code | Low | Low | Project directory isolation |
| Automated decision errors | Low | Medium | Human oversight, audit trail |

## 4. Mitigation Measures
- Human QA review of all AI-generated code
- User approval required for merge
- Complete audit logging
- Data minimization (no PII by default)
- User control over data deletion

## 5. Conclusion
**Residual Risk:** Low
**Recommendation:** Proceed with mitigation measures
**Approved By:** DPO (dpo@yourorg.com)
**Date:** 2024-02-13
```

---

## Data Breach Notification

GDPR Articles 33-34 require notification of personal data breaches to authorities and affected individuals.

### Breach Detection

Auto Code's audit logging helps detect breaches:

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Check for suspicious activity
suspicious_events = audit_logger.query_events(
    filters={
        "action": "permission_denied",
        "count_threshold": 10,
        "time_window": "1 hour"
    }
)

if suspicious_events:
    # Potential breach detected
    audit_logger.log_security_incident(
        incident_type="potential_unauthorized_access",
        severity="high",
        description="Multiple permission denied events for single user",
        affected_data_subjects=suspicious_events['user_ids'].tolist(),
        containment_actions=["Account locked", "Security team notified"]
    )
```

### Breach Notification Workflow

#### 1. Assess the Breach

```python
from enterprise.audit import EnterpriseAuditLogger

audit_logger = EnterpriseAuditLogger(spec_dir)

# Log breach assessment
audit_logger.log_breach_assessment(
    breach_id="br_20240213_001",
    breach_type="unauthorized_access",
    affected_data_types=["user_id", "authentication_events"],
    affected_data_subjects_count=50,
    data_subject_categories=["employees"],
    consequences="Unauthorized viewing of audit logs",
    likelihood_of_risk="high",
    high_risk_to_rights="true"
)
```

#### 2. Notify Authorities (within 72 hours)

```python
# Generate breach notification report for supervisory authority
breach_report = audit_logger.generate_breach_report(
    breach_id="br_20240213_001",
    include_ropa=True,
    include_mitigation_measures=True,
    format="gdpr_article_33"
)

# Submit to supervisory authority (e.g., ICO in UK, CNIL in France)
# Report includes:
# - Nature of breach
# - Categories and approximate number of data subjects concerned
# - Categories and approximate number of personal data records concerned
# - Likely consequences of breach
# - Measures taken or proposed to address breach
```

#### 3. Notify Data Subjects (if high risk)

```python
# Notify affected individuals
if breach_assessment['high_risk_to_rights']:
    for data_subject_id in affected_data_subjects:
        audit_logger.log_data_subject_notification(
            data_subject_id=data_subject_id,
            breach_id="br_20240213_001",
            notification_method="email",
            notification_content="""
Dear Data Subject,

We are writing to inform you of a personal data breach involving your data.

What happened:
On 2024-02-13, unauthorized access to audit logs was detected.

What data was affected:
Your user ID and authentication records were accessed.

What we are doing:
- We have secured the affected systems
- We have notified the relevant supervisory authority
- We are reviewing our security measures

What you can do:
- Monitor your account for suspicious activity
- Contact us if you notice anything unusual

We sincerely apologize for any inconvenience or concern.

[Your Organization Name]
Data Protection Officer: dpo@yourorg.com
""",
            sent_at="2024-02-13T15:00:00Z"
        )
```

### Breach Documentation

Auto Code maintains complete breach records for GDPR demonstration:

| Breach Record Field | Description |
|---------------------|-------------|
| **Breach ID** | Unique identifier |
| **Detection Date/Time** | When breach was discovered |
| **Breach Type** | Unauthorized access, disclosure, loss, etc. |
| **Data Categories** | Types of personal data affected |
| **Data Subjects Affected** | Number and categories of individuals |
| **Root Cause** | How the breach occurred |
| **Consequences** | Impact on data subjects |
| **Mitigation Measures** | Steps taken to address breach |
| **Authority Notification** | Date and details of authority notification |
| **Data Subject Notification** | Whether individuals were notified |
| **Lessons Learned** | Post-incident review findings |

---

## Data Protection Officer

GDPR Articles 37-39 specify when a Data Protection Officer (DPO) is required.

### When to Appoint a DPO

A DPO must be designated in three cases:

1. **Public Authority** - Processing by public bodies (except courts)
2. **Core Activities** - Regular and systematic monitoring of data subjects on a large scale
3. **Special Categories** - Large-scale processing of special category data (Article 9) or criminal data

**Auto Code DPO Recommendations:**

| Scenario | DPO Required? | Reason |
|----------|---------------|--------|
| Enterprise SSO deployment | ✅ Yes | Large-scale monitoring (audit logs) |
| Small business deployment | ❌ No | Not large-scale |
| Healthcare deployment | ✅ Yes | Special category data (if applicable) |
| Government deployment | ✅ Yes | Public authority |

### DPO Integration

Auto Code supports DPO operations:

#### DPO Dashboard

```bash
# DPO view of compliance status
python -m enterprise.compliance dpo-dashboard

# Output:
GDPR Compliance Dashboard
├── Data Subject Rights Requests
│   ├── Access requests: 5 (3 completed, 2 pending)
│   ├── Erasure requests: 2 (2 completed)
│   ├── Rectification requests: 1 (1 completed)
│   └── Portability requests: 3 (3 completed)
├── Data Residency
│   ├── Region: EU
│   ├── Transfer violations: 0
│   └── Last compliance check: 2024-02-13
├── Data Breaches
│   ├── Breaches in last 24 hours: 0
│   ├── Breaches in last 30 days: 1 (resolved)
│   └── Average notification time: 12 hours
└── DPIAs
    ├── Active DPIAs: 1
    ├── High-risk processing: Automated code generation
    └── Last review: 2024-02-13
```

#### DPO Audit Access

```python
from enterprise.permissions import Role, create_user

# Create DPO account with read-only access
dpo = create_user(
    username="dpo@yourorg.com",
    role=Role.AUDITOR,  # Read-only access
    expires_at=None  # No expiration
)

# DPO can access:
# - All audit logs
# - Data subject request records
# - Data breach notifications
# - ROPA documentation
# - DPIA records
# - Compliance reports
```

### DPO Contact Information

Configure DPO contact details:

```bash
# .env configuration
DPO_NAME="Jane Smith"
DPO_EMAIL="dpo@yourorg.com"
DPO_PHONE="+1-555-0123"
DPO_ADDRESS="123 Privacy Lane, Brussels, Belgium"
```

---

## Compliance Monitoring

Auto Code provides real-time GDPR compliance monitoring.

### GDPR Compliance Dashboard

```bash
# View GDPR compliance status
python -m enterprise.compliance gdpr-status

# Example output:
GDPR Compliance Status: COMPLIANT
├── Data Protection Principles: ✓ All 7 principles implemented
├── Lawful Basis: ✓ All processing activities documented
├── Data Subject Rights: ✓ All 8 rights supported
├── Data Residency: ✓ EU region configured
│   ├── International transfers: 0 violations
│   └── SCCs in place: Yes
├── ROPA: ✓ Article 30 records maintained
│   ├── Processing activities: 3 documented
│   └── Last updated: 2024-02-13
├── DPIA: ✓ Article 35 assessments completed
│   ├── High-risk processing: 1 assessed
│   └── Residual risk: Low
├── Data Breaches: ✓ Article 33/34 procedures in place
│   ├── Breaches (30 days): 1 (resolved)
│   └── Average notification time: 12 hours
└── Accountability: ✓ Documentation complete
    ├── Policies: 6 documented
    └── Training: All staff completed
```

### Automated Compliance Checks

Continuous compliance validation:

```yaml
# .auto-claude/gdpr_rules.yaml
compliance_checks:
  - name: "EU Data Residency"
    check: "DATA_RESIDENCY_REGION == 'EU'"
    severity: "critical"
    failure_action: "Alert DPO"

  - name: "PII Redaction"
    check: "AUDIT_LOG_REDACT_PII == true"
    severity: "high"
    failure_action: "Enable automatically"

  - name: "Audit Log Retention"
    check: "AUDIT_LOG_RETENTION_YEARS >= 7"
    severity: "medium"
    failure_action: "Log warning"

  - name: "DSR Response Time"
    check: "dsr_response_time <= 30 days"
    severity: "high"
    failure_action: "Alert DPO"

  - name: "Breach Notification Time"
    check: "breach_notification_time <= 72 hours"
    severity: "critical"
    failure_action: "Alert DPO + Executive Team"
```

### GDPR Compliance Reports

Generate comprehensive compliance reports:

```python
from enterprise.compliance import ComplianceReportGenerator

generator = ComplianceReportGenerator()

# Annual GDPR compliance report
report = generator.generate_gdpr_report(
    period_start="2024-01-01",
    period_end="2024-12-31",
    include_sections=[
        "data_protection_principles",
        "lawful_basis",
        "data_subject_rights",
        "international_transfers",
        "ropa",
        "dpia",
        "security_measures",
        "breaches",
        "dsr_statistics",
        "training_records"
    ]
)

# Export to PDF for supervisory authority
report.export_pdf("gdpr_compliance_report_2024.pdf")
```

---

## Audit Evidence

### Preparing for GDPR Audit/Inspection

#### Evidence Collection Checklist

**Data Protection Principles Evidence:**
- [ ] Documentation of all 7 principles implementation
- [ ] Legal basis assessment for each processing activity
- [ ] Purpose limitation documentation
- [ ] Data minimization procedures
- [ ] Data accuracy controls
- [ ] Retention policy documentation
- [ ] Security measures implementation

**Lawful Basis Evidence:**
- [ ] Legal basis for each processing activity
- [ ] Legitimate interests assessment (if applicable)
- [ ] Consent records (if consent is basis)
- [ ] Contract documentation (if contract is basis)
- [ ] Legal obligation references (if legal obligation is basis)

**Data Subject Rights Evidence:**
- [ ] Data subject request procedures
- [ ] DSAR response logs (last 3 years)
- [ ] Erasure request logs
- [ ] Rectification logs
- [ ] Portability exports
- [ ] Objection handling records
- [ ] Response times (all under 30 days)

**International Transfers Evidence:**
- [ ] Data residency configuration
- [ ] Transfer mechanism documentation (SCCs, BCRs, etc.)
- [ ] Transfer approval logs
- [ ] Transfer violation logs (should be 0)

**Records of Processing Activities (ROPA):**
- [ ] Complete Article 30 ROPA
- [ ] Vendor/supplier records
- [ ] Data categories documentation
- [ ] Data subject categories documentation
- [ ] Retention periods documentation
- [ ] Security measures documentation

**DPIA Evidence:**
- [ ] DPIAs for high-risk processing
- [ ] Risk assessments
- [ ] Mitigation measures
- [ ] DPO approval records
- [ ] DPIA review documentation

**Data Breach Evidence:**
- [ ] Breach detection procedures
- [ ] Breach notification logs (Article 33)
- [ ] Data subject notification logs (Article 34)
- [ ] Breach response documentation
- [ ] Lessons learned documentation
- [ ] Notification times (all under 72 hours)

**Security Evidence:**
- [ ] Access control policy
- [ ] Audit log samples
- [ ] Encryption documentation
- [ ] Authentication procedures
- [ ] Security training records
- [ ] Incident response procedures

**Accountability Evidence:**
- [ ] GDPR policies and procedures
- [ ] Staff training records
- [ ] DPO appointment (if required)
- [ ] Compliance monitoring reports
- [ ] Governance documentation

### Export Audit Trail

```bash
# Export audit logs for GDPR examination
python -m enterprise.audit export \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --data-subject-id user_123 \
  --format json \
  --output gdpr_audit_user_123_2024.json

# Export all DSR requests
python -m enterprise.audit export-dsrs \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --format csv \
  --output gdpr_dsrs_2024.csv

# Export data transfer logs
python -m enterprise.audit export-transfers \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --format json \
  --output gdpr_transfers_2024.json
```

### GDPR Audit Report Template

Auto Code generates GDPR audit-ready reports:

```python
from enterprise.compliance import ComplianceReportGenerator

generator = ComplianceReportGenerator()

# Generate GDPR audit report
audit_report = generator.generate_gdpr_audit_report(
    inspection_date="2024-02-13",
    inspector_name="Supervisory Authority",
    include_all_evidence=True
)

# Report includes:
# - Executive summary
# - Data protection principles compliance
# - Lawful basis documentation
# - Data subject rights statistics
# - International transfer evidence
# - ROPA (Article 30)
# - DPIA summary (Article 35)
# - Breach history (Articles 33-34)
# - Security measures
# - Accountability documentation
# - Sample audit logs
# - Staff training records
# - DPO contact information
```

### Frequently Asked Questions

**Q: Does Auto Code replace the need for GDPR compliance?**

A: No, Auto Code provides tools and documentation to help you achieve and demonstrate GDPR compliance. You are responsible for ensuring your use of Auto Code complies with GDPR and for completing your own GDPR compliance activities.

**Q: Does Auto Code include a Data Protection Officer?**

A: No, Auto Code does not provide a DPO. If your processing requires a DPO under GDPR Articles 37-39, you must appoint your own. Auto Code provides tools to help your DPO monitor compliance and access audit data.

**Q: How long are data subject request records kept?**

A: DSR records are kept for 7 years to align with audit log retention requirements. This is configurable via the `AUDIT_LOG_RETENTION_YEARS` environment variable.

**Q: Does Auto Code support data subject access requests (DSARs)?**

A: Yes, Auto Code can export all personal data for a data subject in a structured, machine-readable format to fulfill DSARs. See [Right of Access](#right-of-access) for details.

**Q: Can I use Auto Code for special category data (health, biometrics, etc.)?**

A: Auto Code does not collect special category data by default. If you use Auto Code to process special category data, you must ensure you have an appropriate lawful basis under GDPR Article 9 and complete additional safeguards.

**Q: How do I demonstrate data residency compliance?**

A: All data residency checks are logged with correlation IDs. Export audit logs filtered by `data_residency_validated` and `data_residency_violation` events to demonstrate compliance.

**Q: What happens if there's a data breach?**

A: Auto Code's audit logging helps detect and investigate breaches. You must notify your supervisory authority within 72 hours of becoming aware of a breach. Auto Code generates breach notification reports to help you meet this deadline.

**Q: Does Auto Code store personal data outside the EU?**

A: When `DATA_RESIDENCY_REGION=EU` is configured, Auto Code validates that data stays within the EU. Any attempts to transfer data outside the EU without adequate safeguards (e.g., SCCs) are logged as violations.

**Q: Can Auto Code help with GDPR accountability?**

A: Yes, Auto Code provides comprehensive documentation and audit trails to demonstrate accountability under GDPR Article 5(2). This includes ROPA (Article 30), DPIA support (Article 35), and complete processing records.

**Q: What's the difference between SOC2 and GDPR compliance?**

A: SOC2 is a US-focused security framework with 5 trust services criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy). GDPR is an EU regulation focused on personal data protection with specific data subject rights and data transfer restrictions. See [SOC2 Compliance](SOC2_COMPLIANCE.md) for SOC2-specific controls.

---

## See Also

- [SOC2 Compliance](SOC2_COMPLIANCE.md) - SOC2-specific security controls
- [Enterprise Deployment Guide](../enterprise/DEPLOYMENT_GUIDE.md) - Self-hosted setup
- [SSO Setup Guide](../enterprise/SSO_SETUP.md) - SAML configuration
- [Audit Logging Guide](../enterprise/AUDIT_LOGGING.md) - Audit log management
- [Enterprise Permissions](../enterprise/PERMISSIONS.md) - RBAC documentation
- [GDPR Official Text](https://gdpr-info.eu/) - Full GDPR regulation
- [UK GDPR](https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-gdpr/) - UK implementation

---

**Last Updated:** 2024-02-13

**Document Version:** 1.0

**Maintained By:** Auto Code Privacy Team
