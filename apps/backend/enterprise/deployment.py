"""
Self-Hosted Deployment Configuration
====================================

Configuration and utilities for self-hosted and air-gapped deployments.

Features:
- Air-gapped mode detection and configuration
- Local model proxy support (for isolated environments)
- Network connectivity validation
- Custom API endpoint configuration
- Offline model serving integration
- Deployment health checks

Deployment Modes:
- Cloud: Standard cloud deployment (default)
- Self-Hosted: On-premise deployment with internet access
- Air-Gapped: Isolated deployment with no internet access

Air-Gapped Mode:
    In air-gapped mode, Auto Code can operate without internet access by using:
    1. Local model proxy (e.g., llama.cpp, vLLM, TGI)
    2. Pre-downloaded models on local filesystem
    3. Custom API endpoint that mimics Claude API

Environment Variables:
    ENTERPRISE_DEPLOYMENT_MODE: cloud|self-hosted|air-gapped
    ENTERPRISE_MODEL_PROXY_URL: Local model proxy endpoint (e.g., http://localhost:8080)
    ENTERPRISE_LOCAL_MODEL_PATH: Path to local model files
    ENTERPRISE_API_BASE_URL: Custom API base URL for self-hosted deployments
    ENTERPRISE_OFFLINE_MODE: Disable all internet connectivity checks
    ENTERPRISE_PROXY_VERIFY_SSL: Verify SSL for model proxy (default: true)

Usage:
    from enterprise.deployment import (
        is_air_gapped,
        get_model_proxy_url,
        validate_deployment,
    )

    # Check deployment mode
    if is_air_gapped():
        proxy_url = get_model_proxy_url()
        print(f"Using local model proxy: {proxy_url}")

    # Validate deployment configuration
    validation = validate_deployment()
    if not validation.is_valid:
        print(f"Deployment issues: {validation.errors}")
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class DeploymentValidation:
    """
    Result of deployment configuration validation.

    Attributes:
        is_valid: Whether deployment configuration is valid
        errors: List of validation error messages
        warnings: List of validation warning messages
        info: Additional diagnostic information
    """

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)


@dataclass
class ModelProxyConfig:
    """
    Configuration for local model proxy.

    Attributes:
        url: Proxy endpoint URL (e.g., http://localhost:8080)
        model_name: Name of the model to use
        verify_ssl: Whether to verify SSL certificates
        timeout_seconds: Request timeout in seconds
        api_key: Optional API key for proxy authentication
    """

    url: str
    model_name: str = "claude-sonnet-4"
    verify_ssl: bool = True
    timeout_seconds: int = 300
    api_key: str | None = None

    @property
    def is_local(self) -> bool:
        """Check if proxy is running on localhost."""
        parsed = urlparse(self.url)
        return parsed.hostname in ("localhost", "127.0.0.1", "::1")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "model_name": self.model_name,
            "verify_ssl": self.verify_ssl,
            "timeout_seconds": self.timeout_seconds,
            "is_local": self.is_local,
        }


def is_air_gapped() -> bool:
    """
    Check if deployment is in air-gapped mode.

    Returns:
        True if ENTERPRISE_DEPLOYMENT_MODE is 'air-gapped'
    """
    from enterprise.config import DeploymentMode, get_enterprise_config

    config = get_enterprise_config()
    return config.deployment_mode == DeploymentMode.AIR_GAPPED


def is_self_hosted() -> bool:
    """
    Check if deployment is self-hosted (including air-gapped).

    Returns:
        True if deployment mode is self-hosted or air-gapped
    """
    from enterprise.config import get_enterprise_config

    config = get_enterprise_config()
    return config.is_self_hosted


def is_offline_mode() -> bool:
    """
    Check if offline mode is enabled.

    Offline mode disables all network connectivity checks and assumes
    no internet access is available.

    Returns:
        True if offline mode is enabled
    """
    from enterprise.config import get_enterprise_config

    config = get_enterprise_config()
    return config.offline_mode or is_air_gapped()


def get_model_proxy_url() -> str | None:
    """
    Get the local model proxy URL if configured.

    Returns:
        Model proxy URL or None if not configured
    """
    from enterprise.config import get_enterprise_config

    config = get_enterprise_config()
    return config.custom_model_proxy_url


def get_local_model_path() -> Path | None:
    """
    Get the local model path if configured.

    Returns:
        Path to local model files or None if not configured
    """
    from enterprise.config import get_enterprise_config

    config = get_enterprise_config()
    return config.local_model_path


def get_api_base_url() -> str | None:
    """
    Get the custom API base URL for self-hosted deployments.

    Returns:
        Custom API base URL or None if using default
    """
    from enterprise.config import get_enterprise_config

    config = get_enterprise_config()
    return config.custom_api_base_url


def get_model_proxy_config() -> ModelProxyConfig | None:
    """
    Get model proxy configuration.

    Returns:
        ModelProxyConfig instance or None if not configured
    """
    proxy_url = get_model_proxy_url()
    if not proxy_url:
        return None

    # Get optional configuration
    model_name = os.environ.get("ENTERPRISE_MODEL_PROXY_MODEL", "claude-sonnet-4")
    verify_ssl = os.environ.get("ENTERPRISE_PROXY_VERIFY_SSL", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    timeout_seconds = int(os.environ.get("ENTERPRISE_PROXY_TIMEOUT", "300"))
    api_key = os.environ.get("ENTERPRISE_PROXY_API_KEY")

    return ModelProxyConfig(
        url=proxy_url,
        model_name=model_name,
        verify_ssl=verify_ssl,
        timeout_seconds=timeout_seconds,
        api_key=api_key,
    )


def check_network_connectivity(host: str = "api.anthropic.com", port: int = 443, timeout: int = 5) -> bool:
    """
    Check if network connectivity is available.

    Args:
        host: Hostname to check connectivity to
        port: Port to check
        timeout: Timeout in seconds

    Returns:
        True if connection successful, False otherwise
    """
    # Skip check in offline mode
    if is_offline_mode():
        logger.debug("Offline mode enabled, skipping network connectivity check")
        return False

    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.error, socket.timeout, OSError) as e:
        logger.debug(f"Network connectivity check failed: {e}")
        return False


def validate_model_proxy(proxy_config: ModelProxyConfig) -> DeploymentValidation:
    """
    Validate model proxy configuration.

    Args:
        proxy_config: Model proxy configuration to validate

    Returns:
        DeploymentValidation with validation results
    """
    validation = DeploymentValidation()

    # Validate URL format
    try:
        parsed = urlparse(proxy_config.url)
        if not parsed.scheme or not parsed.netloc:
            validation.add_error(f"Invalid proxy URL format: {proxy_config.url}")
        elif parsed.scheme not in ("http", "https"):
            validation.add_error(f"Proxy URL must use http or https: {proxy_config.url}")
        else:
            validation.info["proxy_scheme"] = parsed.scheme
            validation.info["proxy_host"] = parsed.netloc

            # Warn if using http (not https)
            if parsed.scheme == "http" and not proxy_config.is_local:
                validation.add_warning(
                    "Using insecure HTTP for remote proxy. Consider using HTTPS."
                )

    except Exception as e:
        validation.add_error(f"Failed to parse proxy URL: {e}")

    # Check if SSL verification is disabled
    if not proxy_config.verify_ssl:
        validation.add_warning("SSL verification disabled for model proxy")

    # Validate timeout
    if proxy_config.timeout_seconds < 10:
        validation.add_warning(
            f"Proxy timeout very low ({proxy_config.timeout_seconds}s), may cause failures"
        )

    return validation


def validate_deployment() -> DeploymentValidation:
    """
    Validate deployment configuration.

    Checks:
    - Enterprise config is loaded correctly
    - Required settings for air-gapped/self-hosted are present
    - Model proxy is configured if in air-gapped mode
    - Network connectivity if not in offline mode

    Returns:
        DeploymentValidation with validation results
    """
    validation = DeploymentValidation()

    try:
        from enterprise.config import DeploymentMode, get_enterprise_config

        config = get_enterprise_config()
        validation.info["deployment_mode"] = config.deployment_mode.value
        validation.info["enterprise_enabled"] = config.is_enabled

        # Validate air-gapped mode
        if config.deployment_mode == DeploymentMode.AIR_GAPPED:
            # Must have either model proxy or local model path
            if not config.custom_model_proxy_url and not config.local_model_path:
                validation.add_error(
                    "Air-gapped mode requires ENTERPRISE_MODEL_PROXY_URL or ENTERPRISE_LOCAL_MODEL_PATH"
                )

            # Validate model proxy if configured
            proxy_config = get_model_proxy_config()
            if proxy_config:
                proxy_validation = validate_model_proxy(proxy_config)
                validation.errors.extend(proxy_validation.errors)
                validation.warnings.extend(proxy_validation.warnings)
                validation.info["model_proxy"] = proxy_config.to_dict()

            # Validate local model path if configured
            if config.local_model_path:
                if not config.local_model_path.exists():
                    validation.add_error(
                        f"Local model path does not exist: {config.local_model_path}"
                    )
                elif not config.local_model_path.is_dir():
                    validation.add_error(
                        f"Local model path is not a directory: {config.local_model_path}"
                    )
                else:
                    validation.info["local_model_path"] = str(config.local_model_path)

        # Validate self-hosted mode
        elif config.deployment_mode == DeploymentMode.SELF_HOSTED:
            if config.custom_api_base_url:
                validation.info["custom_api_base_url"] = config.custom_api_base_url
            else:
                validation.add_warning(
                    "Self-hosted mode without custom API base URL (using default Anthropic API)"
                )

        # Check network connectivity (unless in offline mode)
        if not is_offline_mode():
            has_connectivity = check_network_connectivity()
            validation.info["network_connectivity"] = has_connectivity

            if not has_connectivity and config.deployment_mode == DeploymentMode.CLOUD:
                validation.add_warning(
                    "No network connectivity detected in cloud deployment mode. "
                    "Consider enabling offline mode or switching to air-gapped mode."
                )

    except ImportError:
        validation.add_error("Enterprise config module not available")
    except Exception as e:
        validation.add_error(f"Deployment validation failed: {e}")

    return validation


# Alias for backward compatibility (verification command uses this name)
is_airgapped = is_air_gapped


def get_deployment_info() -> dict[str, Any]:
    """
    Get comprehensive deployment information.

    Returns:
        Dict with deployment mode, configuration, and status
    """
    try:
        from enterprise.config import get_enterprise_config

        config = get_enterprise_config()

        info = {
            "deployment_mode": config.deployment_mode.value,
            "is_air_gapped": config.is_air_gapped,
            "is_self_hosted": config.is_self_hosted,
            "offline_mode": config.offline_mode,
            "enterprise_enabled": config.is_enabled,
        }

        # Add model proxy info if configured
        proxy_config = get_model_proxy_config()
        if proxy_config:
            info["model_proxy"] = proxy_config.to_dict()

        # Add local model path if configured
        if config.local_model_path:
            info["local_model_path"] = str(config.local_model_path)

        # Add custom API endpoint if configured
        if config.custom_api_base_url:
            info["custom_api_base_url"] = config.custom_api_base_url

        # Add network connectivity status
        if not is_offline_mode():
            info["network_connectivity"] = check_network_connectivity()

        # Add validation results
        validation = validate_deployment()
        info["validation"] = {
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }

        return info

    except ImportError:
        return {
            "error": "Enterprise modules not available",
            "deployment_mode": "cloud",
            "enterprise_enabled": False,
        }
    except Exception as e:
        return {
            "error": f"Failed to get deployment info: {e}",
            "deployment_mode": "unknown",
            "enterprise_enabled": False,
        }
