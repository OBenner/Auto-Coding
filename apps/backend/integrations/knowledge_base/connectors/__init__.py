"""
Knowledge Base Connectors
=========================

Provider-specific connectors for team documentation systems.
"""

from .notion import NotionConnector

__all__ = [
    "NotionConnector",
]
