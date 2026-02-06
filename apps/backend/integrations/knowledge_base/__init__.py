"""
Knowledge Base Integration
==========================

Connectors for team documentation systems (Notion, Confluence, GitHub Wiki, GitBook).
Allows agents to query team documentation for context and standards.
"""

from integrations.knowledge_base.base import BaseConnector
from integrations.knowledge_base.config import (
    KnowledgeBaseConfig,
    KnowledgeBaseState,
)
from integrations.knowledge_base.connectors import (
    ConfluenceConnector,
    GitBookConnector,
    GitHubWikiConnector,
    NotionConnector,
)

__all__ = [
    "BaseConnector",
    "KnowledgeBaseConfig",
    "KnowledgeBaseState",
    "ConfluenceConnector",
    "GitBookConnector",
    "GitHubWikiConnector",
    "NotionConnector",
]
