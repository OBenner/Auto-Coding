"""
Actor-Critic MCP Configuration
===============================

Configuration and validation for the Actor-Critic Thinking MCP server integration.

The Actor-Critic Thinking MCP server provides structured dual-perspective analysis
through a single actor_critic_thinking tool that implements actor-critic reinforcement
learning pattern for reasoning.

Environment Variables:
    ACTOR_CRITIC_MCP_ENABLED: Set to "true" to enable Actor-Critic MCP integration

Dependencies:
    - npx: Required to run the mcp-server-actor-critic-thinking package
    - No authentication required (public npm package)

Usage:
    from core.actor_critic_config import validate_actor_critic_config

    # Validate configuration (raises RuntimeError if invalid)
    validate_actor_critic_config()
"""

import logging
import os
from dataclasses import dataclass

from core.platform import find_executable

logger = logging.getLogger(__name__)


@dataclass
class ActorCriticConfig:
    """Configuration for Actor-Critic MCP server integration.

    The Actor-Critic Thinking MCP server is a stateless tool that provides
    dual-perspective analysis without requiring authentication or API keys.
    """

    # Core settings
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "ActorCriticConfig":
        """Create config from environment variables.

        Returns:
            ActorCriticConfig instance with settings from environment
        """
        # Check if Actor-Critic MCP is explicitly enabled
        enabled_str = os.environ.get("ACTOR_CRITIC_MCP_ENABLED", "").lower()
        enabled = enabled_str in ("true", "1", "yes")

        return cls(enabled=enabled)

    def is_valid(self) -> bool:
        """
        Check if config has minimum required values for operation.

        Returns True if:
        - ACTOR_CRITIC_MCP_ENABLED is false (disabled is valid)
        - ACTOR_CRITIC_MCP_ENABLED is true and npx is available

        Returns:
            bool: True if configuration is valid
        """
        if not self.enabled:
            # Disabled is a valid state
            return True

        # Check if npx is available when enabled
        return self._check_npx_available()

    def _check_npx_available(self) -> bool:
        """Check if npx command is available on the system.

        Uses the centralized platform find_executable() for cross-platform
        discovery (handles .cmd/.bat extensions on Windows, etc.).

        Returns:
            bool: True if npx is found
        """
        return find_executable("npx") is not None

    def get_validation_errors(self) -> list[str]:
        """Get list of validation errors for current configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.enabled:
            # Disabled is valid, no errors
            return errors

        # Check npx availability when enabled
        if not self._check_npx_available():
            errors.append(
                "Actor-Critic MCP is enabled but npx is not available. "
                "Either disable ACTOR_CRITIC_MCP_ENABLED or ensure Node.js/npm is installed."
            )

        return errors

    def get_status_summary(self) -> str:
        """Get a human-readable summary of the configuration status.

        Returns:
            str: Status summary
        """
        if not self.enabled:
            return "Actor-Critic MCP: Disabled"

        if self._check_npx_available():
            return "Actor-Critic MCP: Enabled (npx available)"
        else:
            return "Actor-Critic MCP: Enabled but npx not available (configuration invalid)"


def is_actor_critic_enabled() -> bool:
    """
    Quick check if Actor-Critic MCP integration is available.

    Returns:
        bool: True if ACTOR_CRITIC_MCP_ENABLED is set to true/1/yes and npx is available
    """
    config = ActorCriticConfig.from_env()
    return config.is_valid() and config.enabled


def get_actor_critic_status() -> dict:
    """
    Get the current Actor-Critic MCP integration status.

    Returns:
        Dict with status information:
            - enabled: bool
            - available: bool
            - npx_available: bool
            - reason: str (why unavailable if not available)
    """
    config = ActorCriticConfig.from_env()
    npx_available = config._check_npx_available()

    status = {
        "enabled": config.enabled,
        "available": False,
        "npx_available": npx_available,
        "reason": "",
    }

    if not config.enabled:
        status["reason"] = "ACTOR_CRITIC_MCP_ENABLED not set to true"
        return status

    if not npx_available:
        status["reason"] = (
            "npx command not found. Install Node.js/npm to use Actor-Critic MCP."
        )
        return status

    status["available"] = True
    return status


def validate_actor_critic_config() -> None:
    """
    Validate Actor-Critic MCP configuration from environment.

    This function is designed to be called at application startup to validate
    the Actor-Critic MCP configuration. It will raise RuntimeError if the
    configuration is invalid when the feature is enabled.

    Raises:
        RuntimeError: If configuration is invalid when ACTOR_CRITIC_MCP_ENABLED is true

    Example:
        >>> from core.actor_critic_config import validate_actor_critic_config
        >>> validate_actor_critic_config()  # Raises RuntimeError if invalid
    """
    config = ActorCriticConfig.from_env()

    # If not enabled, no validation needed
    if not config.enabled:
        return

    # Validate configuration when enabled
    errors = config.get_validation_errors()
    if errors:
        error_msg = "Actor-Critic MCP configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        raise RuntimeError(error_msg)

    # Configuration is valid
    logger.info(
        "Actor-Critic MCP configuration validated: %s", config.get_status_summary()
    )
