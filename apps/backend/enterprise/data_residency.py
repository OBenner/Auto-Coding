"""
Data Residency Controls
=======================

Region-specific API endpoint configuration for GDPR and data sovereignty compliance.

Features:
- Regional data residency configuration (EU, US, UK, etc.)
- API endpoint mapping for region-specific Claude deployments
- Data transfer validation and compliance checks
- GDPR Article 44-49 compliance for international data transfers
- Audit logging integration for residency violations

Supported Regions:
- EU: European Union (GDPR compliant)
- US: United States
- UK: United Kingdom
- AP: Asia Pacific
- GLOBAL: No specific regional constraints

Usage:
    from enterprise.data_residency import DataResidencyConfig, get_regional_endpoint

    # Configure for EU region
    config = DataResidencyConfig('EU')
    print(config.region)  # 'EU'
    print(config.requires_gdpr_compliance)  # True

    # Get regional API endpoint
    endpoint = get_regional_endpoint('EU')
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DataRegion(str, Enum):
    """Supported data residency regions."""

    EU = "EU"  # European Union - GDPR compliant
    US = "US"  # United States
    UK = "UK"  # United Kingdom - GDPR + UK DPA
    AP = "AP"  # Asia Pacific
    GLOBAL = "GLOBAL"  # No regional constraints


class ComplianceFramework(str, Enum):
    """Compliance frameworks applicable to data residency."""

    GDPR = "GDPR"  # EU General Data Protection Regulation
    UK_DPA = "UK_DPA"  # UK Data Protection Act 2018
    CCPA = "CCPA"  # California Consumer Privacy Act
    PIPEDA = "PIPEDA"  # Canadian Personal Information Protection
    APPI = "APPI"  # Japanese Act on Protection of Personal Information


@dataclass
class DataResidencyConfig:
    """
    Configuration for data residency and regional compliance.

    Attributes:
        region: Data residency region (EU, US, UK, AP, GLOBAL)
        requires_gdpr_compliance: Whether GDPR compliance is required
        compliance_frameworks: List of applicable compliance frameworks
        allowed_transfer_regions: Regions to which data transfers are allowed
        custom_endpoint: Optional custom API endpoint for this region
    """

    region: str
    requires_gdpr_compliance: bool = field(init=False)
    compliance_frameworks: list[str] = field(init=False, default_factory=list)
    allowed_transfer_regions: list[str] = field(init=False, default_factory=list)
    custom_endpoint: str | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize compliance settings based on region."""
        # Normalize region to uppercase
        self.region = self.region.upper()

        # Validate region
        try:
            DataRegion(self.region)
        except ValueError:
            logger.warning(
                "Unknown data region '%s'. Supported regions: %s. Defaulting to GLOBAL.",
                self.region,
                ", ".join(r.value for r in DataRegion)
            )
            self.region = DataRegion.GLOBAL.value

        # Set GDPR compliance based on region
        self.requires_gdpr_compliance = self.region in {
            DataRegion.EU.value,
            DataRegion.UK.value
        }

        # Set compliance frameworks
        if self.region == DataRegion.EU.value:
            self.compliance_frameworks = [ComplianceFramework.GDPR.value]
        elif self.region == DataRegion.UK.value:
            self.compliance_frameworks = [
                ComplianceFramework.GDPR.value,
                ComplianceFramework.UK_DPA.value
            ]
        elif self.region == DataRegion.US.value:
            self.compliance_frameworks = [ComplianceFramework.CCPA.value]
        elif self.region == DataRegion.AP.value:
            self.compliance_frameworks = []  # Varies by country
        else:
            self.compliance_frameworks = []

        # Set allowed transfer regions based on adequacy decisions
        # EU adequacy decisions: https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en
        if self.region == DataRegion.EU.value:
            # EU can transfer to regions with adequacy decisions
            self.allowed_transfer_regions = [
                DataRegion.UK.value,  # UK adequacy decision
                DataRegion.GLOBAL.value  # With safeguards (SCCs)
            ]
        elif self.region == DataRegion.UK.value:
            self.allowed_transfer_regions = [
                DataRegion.EU.value,  # UK-EU data bridge
                DataRegion.GLOBAL.value  # With safeguards
            ]
        else:
            # Non-GDPR regions can transfer freely
            self.allowed_transfer_regions = [r.value for r in DataRegion]

        logger.debug(
            "Data residency configured: region=%s, gdpr=%s, frameworks=%s",
            self.region,
            self.requires_gdpr_compliance,
            self.compliance_frameworks
        )

    def can_transfer_to(self, target_region: str) -> bool:
        """
        Check if data transfer to target region is allowed.

        Args:
            target_region: Target region code (EU, US, etc.)

        Returns:
            True if transfer is allowed, False otherwise
        """
        target_region = target_region.upper()
        return target_region in self.allowed_transfer_regions

    def validate_transfer(self, target_region: str) -> tuple[bool, str]:
        """
        Validate data transfer with compliance explanation.

        Args:
            target_region: Target region code

        Returns:
            Tuple of (is_valid, explanation)
        """
        target_region = target_region.upper()

        if self.can_transfer_to(target_region):
            return True, f"Transfer from {self.region} to {target_region} is allowed"

        # GDPR-specific rejection reasons
        if self.requires_gdpr_compliance:
            return False, (
                f"Transfer from {self.region} to {target_region} requires additional "
                f"safeguards (e.g., Standard Contractual Clauses) under GDPR Article 46"
            )

        return False, f"Transfer from {self.region} to {target_region} is not permitted"

    def get_endpoint(self) -> str:
        """
        Get the API endpoint for this region.

        Returns:
            Regional API endpoint URL
        """
        if self.custom_endpoint:
            return self.custom_endpoint

        # Currently Anthropic uses a single global endpoint
        # In the future, regional endpoints may be available
        # This function provides the abstraction for future regional endpoints
        return "https://api.anthropic.com"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "region": self.region,
            "requires_gdpr_compliance": self.requires_gdpr_compliance,
            "compliance_frameworks": self.compliance_frameworks,
            "allowed_transfer_regions": self.allowed_transfer_regions,
            "custom_endpoint": self.custom_endpoint,
        }


def get_data_residency_config(
    region: str | None = None,
    custom_endpoint: str | None = None
) -> DataResidencyConfig:
    """
    Get data residency configuration from environment or parameters.

    Checks environment variables:
    - DATA_RESIDENCY_REGION: Preferred data region (EU, US, UK, AP, GLOBAL)
    - DATA_RESIDENCY_ENDPOINT: Custom regional API endpoint

    Args:
        region: Override region (takes precedence over env var)
        custom_endpoint: Custom API endpoint for the region

    Returns:
        DataResidencyConfig instance

    Example:
        # From environment
        os.environ['DATA_RESIDENCY_REGION'] = 'EU'
        config = get_data_residency_config()

        # Explicit region
        config = get_data_residency_config('EU')
    """
    # Determine region from parameter or environment
    resolved_region = region or os.getenv("DATA_RESIDENCY_REGION", DataRegion.GLOBAL.value)

    # Determine endpoint from parameter or environment
    resolved_endpoint = custom_endpoint or os.getenv("DATA_RESIDENCY_ENDPOINT")

    config = DataResidencyConfig(
        region=resolved_region,
        custom_endpoint=resolved_endpoint
    )

    logger.info(
        "Data residency configuration loaded: region=%s, endpoint=%s, gdpr=%s",
        config.region,
        config.get_endpoint(),
        config.requires_gdpr_compliance
    )

    return config


def get_regional_endpoint(region: str) -> str:
    """
    Get API endpoint for a specific region.

    Args:
        region: Data residency region (EU, US, UK, AP, GLOBAL)

    Returns:
        Regional API endpoint URL

    Example:
        endpoint = get_regional_endpoint('EU')
        # Returns: 'https://api.anthropic.com'
    """
    config = DataResidencyConfig(region=region)
    return config.get_endpoint()


def validate_data_transfer(
    source_region: str,
    target_region: str
) -> tuple[bool, str]:
    """
    Validate data transfer between regions.

    Args:
        source_region: Source data region
        target_region: Target data region

    Returns:
        Tuple of (is_valid, explanation)

    Example:
        valid, reason = validate_data_transfer('EU', 'US')
        if not valid:
            print(f"Transfer blocked: {reason}")
    """
    source_config = DataResidencyConfig(region=source_region)
    return source_config.validate_transfer(target_region)
