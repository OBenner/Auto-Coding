"""
Knowledge Base Integration
==========================

Connectors for team documentation systems (Notion, Confluence, GitHub Wiki, GitBook).
Allows agents to query team documentation for context and standards.
"""

from integrations.knowledge_base.config import (
    KnowledgeBaseConfig,
    KnowledgeBaseState,
)

__all__ = [
    "KnowledgeBaseConfig",
    "KnowledgeBaseState",
]
