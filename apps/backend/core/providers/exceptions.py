"""
Core Provider Exceptions
========================

Exception classes for provider-related errors in the core providers module.
"""


class ProviderError(Exception):
    """Raised when a provider cannot be initialized."""

    pass


class ProviderNotInstalled(ProviderError):
    """Raised when required packages for a provider are not installed."""

    pass


class ProviderConfigError(ProviderError):
    """Raised when provider configuration is invalid or missing."""

    pass
