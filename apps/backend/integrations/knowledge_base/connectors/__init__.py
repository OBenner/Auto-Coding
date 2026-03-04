"""
Knowledge Base Connectors
=========================

Provider-specific connectors for team documentation systems.
"""

from .confluence import ConfluenceConnector
from .gitbook import GitBookConnector
from .github_wiki import GitHubWikiConnector
from .notion import NotionConnector

__all__ = [
    "ConfluenceConnector",
    "GitBookConnector",
    "GitHubWikiConnector",
    "NotionConnector",
]
