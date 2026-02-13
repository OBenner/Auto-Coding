"""
Enterprise Configuration
========================

Centralized configuration management for enterprise features.

Provides a unified interface to all enterprise configuration settings including:
- SSO/SAML authentication settings
- Data residency controls
- Audit logging configuration
- Permission and role settings
- Deployment mode (cloud, self-hosted, air-gapped)
- Compliance frameworks (SOC2, GDPR, HIPAA)

Environment Variables:
    ENTERPRISE_MODE: Enable enterprise features (default: false)
    ENTERPRISE_DEPLOYMENT_MODE: cloud|self-hosted|air-gapped (default: cloud)
    ENTERPRISE_AUDIT_ENABLED: Enable audit logging (default: true when enterprise mode on)
    ENTERPRISE_SSO_ENABLED: Enable SSO authentication (default: false)
    ENTERPRISE_DATA_REGION: Data residency region (EU|US|UK|AP|GLOBAL)
    ENTERPRISE_COMPLIANCE_FRAMEWORKS: Comma-separated list (SOC2,GDPR,HIPAA)

Usage:
    from enterprise.config import EnterpriseConfig, get_enterprise_config

    # Get configuration singleton
    config = get_enterprise_config()

    # Check if enterprise features are enabled
    if config.is_enabled:
        print(f"Deployment mode: {config.deployment_mode}")
        print(f"Data region: {config.data_region}")

    # Access specific settings
    if config.audit_enabled:
        audit_path = config.audit_log_path
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DeploymentMode(str, Enum):
    """Supported deployment modes for enterprise installations."""

    CLOUD = "cloud"  # Cloud deployment (default)
    SELF_HOSTED = "self-hosted"  # Self-hosted on-premise
    AIR_GAPPED = "air-gapped"  # Air-gapped (no internet access)


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    SOC2 = "SOC2"  # SOC2 Type II
    GDPR = "GDPR"  # General Data Protection Regulation
    HIPAA = "HIPAA"  # Health Insurance Portability and Accountability Act
    CCPA = "CCPA"  # California Consumer Privacy Act
    UK_DPA = "UK_DPA"  # UK Data Protection Act


@dataclass
class EnterpriseConfig:
    """
    Enterprise configuration settings.

    Centralizes all enterprise feature configuration with sensible defaults
    and environment variable overrides.
    """

    # Core enterprise settings
    is_enabled: bool = False
    deployment_mode: DeploymentMode = DeploymentMode.CLOUD

    # Feature toggles
    audit_enabled: bool = True
    sso_enabled: bool = False
    permissions_enabled: bool = True
    data_residency_enabled: bool = False

    # Data residency
    data_region: str | None = None

    # Compliance frameworks
    compliance_frameworks: list[ComplianceFramework] = field(default_factory=list)

    # Audit logging paths
    audit_log_path: Path | None = None
    audit_retention_days: int = 90

    # SSO configuration
    sso_provider_type: str | None = None
    sso_metadata_url: str | None = None
    sso_entity_id: str | None = None

    # Custom API endpoints (for self-hosted)
    custom_api_base_url: str | None = None
    custom_model_proxy_url: str | None = None

    # Air-gapped mode settings
    offline_mode: bool = False
    local_model_path: Path | None = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Auto-enable audit logging in enterprise mode
        if self.is_enabled and self.audit_enabled:
            if self.audit_log_path is None:
                # Default to .auto-claude/enterprise/audit/
                self.audit_log_path = Path.cwd() / ".auto-claude" / "enterprise" / "audit"

        # Validate air-gapped settings
        if self.deployment_mode == DeploymentMode.AIR_GAPPED:
            self.offline_mode = True
            if not self.custom_model_proxy_url and not self.local_model_path:
                logger.warning(
                    "Air-gapped mode enabled but no local model proxy or path configured. "
                    "Set ENTERPRISE_MODEL_PROXY_URL or ENTERPRISE_LOCAL_MODEL_PATH."
                )

    @property
    def is_air_gapped(self) -> bool:
        """Check if deployment is in air-gapped mode."""
        return self.deployment_mode == DeploymentMode.AIR_GAPPED

    @property
    def is_self_hosted(self) -> bool:
        """Check if deployment is self-hosted (including air-gapped)."""
        return self.deployment_mode in (DeploymentMode.SELF_HOSTED, DeploymentMode.AIR_GAPPED)

    @property
    def requires_gdpr_compliance(self) -> bool:
        """Check if GDPR compliance is required."""
        return ComplianceFramework.GDPR in self.compliance_frameworks

    @property
    def requires_soc2_compliance(self) -> bool:
        """Check if SOC2 compliance is required."""
        return ComplianceFramework.SOC2 in self.compliance_frameworks

    @property
    def requires_hipaa_compliance(self) -> bool:
        """Check if HIPAA compliance is required."""
        return ComplianceFramework.HIPAA in self.compliance_frameworks

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary for serialization.

        Returns:
            Dict with all configuration values
        """
        return {
            "is_enabled": self.is_enabled,
            "deployment_mode": self.deployment_mode.value,
            "audit_enabled": self.audit_enabled,
            "sso_enabled": self.sso_enabled,
            "permissions_enabled": self.permissions_enabled,
            "data_residency_enabled": self.data_residency_enabled,
            "data_region": self.data_region,
            "compliance_frameworks": [f.value for f in self.compliance_frameworks],
            "audit_log_path": str(self.audit_log_path) if self.audit_log_path else None,
            "audit_retention_days": self.audit_retention_days,
            "sso_provider_type": self.sso_provider_type,
            "offline_mode": self.offline_mode,
            "is_air_gapped": self.is_air_gapped,
            "is_self_hosted": self.is_self_hosted,
        }


def _parse_compliance_frameworks(frameworks_str: str | None) -> list[ComplianceFramework]:
    """
    Parse comma-separated compliance frameworks from environment variable.

    Args:
        frameworks_str: Comma-separated framework names (e.g., "SOC2,GDPR,HIPAA")

    Returns:
        List of ComplianceFramework enums
    """
    if not frameworks_str:
        return []

    frameworks = []
    for name in frameworks_str.split(","):
        name = name.strip().upper()
        try:
            frameworks.append(ComplianceFramework[name])
        except KeyError:
            logger.warning(f"Unknown compliance framework: {name}")

    return frameworks


def load_enterprise_config() -> EnterpriseConfig:
    """
    Load enterprise configuration from environment variables.

    Returns:
        EnterpriseConfig instance populated from environment
    """
    # Check if enterprise mode is enabled
    is_enabled = os.environ.get("ENTERPRISE_MODE", "").lower() in ("true", "1", "yes")

    # Parse deployment mode
    deployment_mode_str = os.environ.get("ENTERPRISE_DEPLOYMENT_MODE", "cloud").lower()
    try:
        deployment_mode = DeploymentMode(deployment_mode_str)
    except ValueError:
        logger.warning(
            f"Invalid deployment mode: {deployment_mode_str}, defaulting to 'cloud'"
        )
        deployment_mode = DeploymentMode.CLOUD

    # Parse compliance frameworks
    frameworks_str = os.environ.get("ENTERPRISE_COMPLIANCE_FRAMEWORKS")
    compliance_frameworks = _parse_compliance_frameworks(frameworks_str)

    # Parse audit settings
    audit_enabled = os.environ.get("ENTERPRISE_AUDIT_ENABLED", "true" if is_enabled else "false").lower() in ("true", "1", "yes")
    audit_log_path_str = os.environ.get("ENTERPRISE_AUDIT_LOG_PATH")
    audit_log_path = Path(audit_log_path_str) if audit_log_path_str else None
    audit_retention_days = int(os.environ.get("ENTERPRISE_AUDIT_RETENTION_DAYS", "90"))

    # Parse SSO settings
    sso_enabled = os.environ.get("ENTERPRISE_SSO_ENABLED", "false").lower() in ("true", "1", "yes")
    sso_provider_type = os.environ.get("ENTERPRISE_SSO_PROVIDER_TYPE")
    sso_metadata_url = os.environ.get("ENTERPRISE_SSO_METADATA_URL")
    sso_entity_id = os.environ.get("ENTERPRISE_SSO_ENTITY_ID")

    # Parse data residency settings
    data_region = os.environ.get("ENTERPRISE_DATA_REGION")
    data_residency_enabled = bool(data_region)

    # Parse permissions settings
    permissions_enabled = os.environ.get("ENTERPRISE_PERMISSIONS_ENABLED", "true" if is_enabled else "false").lower() in ("true", "1", "yes")

    # Parse custom endpoints (for self-hosted/air-gapped)
    custom_api_base_url = os.environ.get("ENTERPRISE_API_BASE_URL")
    custom_model_proxy_url = os.environ.get("ENTERPRISE_MODEL_PROXY_URL")

    # Parse air-gapped settings
    offline_mode = deployment_mode == DeploymentMode.AIR_GAPPED
    local_model_path_str = os.environ.get("ENTERPRISE_LOCAL_MODEL_PATH")
    local_model_path = Path(local_model_path_str) if local_model_path_str else None

    return EnterpriseConfig(
        is_enabled=is_enabled,
        deployment_mode=deployment_mode,
        audit_enabled=audit_enabled,
        sso_enabled=sso_enabled,
        permissions_enabled=permissions_enabled,
        data_residency_enabled=data_residency_enabled,
        data_region=data_region,
        compliance_frameworks=compliance_frameworks,
        audit_log_path=audit_log_path,
        audit_retention_days=audit_retention_days,
        sso_provider_type=sso_provider_type,
        sso_metadata_url=sso_metadata_url,
        sso_entity_id=sso_entity_id,
        custom_api_base_url=custom_api_base_url,
        custom_model_proxy_url=custom_model_proxy_url,
        offline_mode=offline_mode,
        local_model_path=local_model_path,
    )


# Singleton instance
_enterprise_config: EnterpriseConfig | None = None


def get_enterprise_config(reload: bool = False) -> EnterpriseConfig:
    """
    Get the enterprise configuration singleton.

    Args:
        reload: Force reload from environment variables

    Returns:
        EnterpriseConfig instance
    """
    global _enterprise_config

    if _enterprise_config is None or reload:
        _enterprise_config = load_enterprise_config()

        if _enterprise_config.is_enabled:
            logger.info(
                f"Enterprise mode enabled: deployment={_enterprise_config.deployment_mode.value}, "
                f"region={_enterprise_config.data_region or 'GLOBAL'}, "
                f"frameworks={[f.value for f in _enterprise_config.compliance_frameworks]}"
            )

    return _enterprise_config


def is_enterprise_enabled() -> bool:
    """
    Check if enterprise features are enabled.

    Returns:
        True if ENTERPRISE_MODE is enabled
    """
    return get_enterprise_config().is_enabled
