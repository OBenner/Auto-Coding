"""
Graphiti Memory System - Modular Architecture

This package provides a clean separation of concerns for Graphiti memory:
- graphiti.py: Main facade and coordination
- client.py: Database connection management
- queries.py: Episode storage operations
- code_relationships.py: Code relationship storage operations
- search.py: Semantic search and retrieval
- schema.py: Data structures and constants

Public API exports maintain backward compatibility with the original
graphiti_memory.py module.
"""

from .code_relationships import CodeRelationshipQueries
from .graphiti import GraphitiMemory
from .schema import (
    EPISODE_TYPE_CLASS_INHERITANCE,
    EPISODE_TYPE_CODE_RELATIONSHIP,
    EPISODE_TYPE_CODEBASE_DISCOVERY,
    EPISODE_TYPE_FUNCTION_CALL,
    EPISODE_TYPE_GOTCHA,
    EPISODE_TYPE_HISTORICAL_CONTEXT,
    EPISODE_TYPE_IMPORT_DEPENDENCY,
    EPISODE_TYPE_PATTERN,
    EPISODE_TYPE_QA_RESULT,
    EPISODE_TYPE_ROOT_CAUSE,
    EPISODE_TYPE_SESSION_INSIGHT,
    EPISODE_TYPE_TASK_OUTCOME,
    EPISODE_TYPE_USER_CORRECTION,
    MAX_CONTEXT_RESULTS,
    GroupIdMode,
)

# Re-export for convenience
__all__ = [
    "GraphitiMemory",
    "CodeRelationshipQueries",
    "GroupIdMode",
    "MAX_CONTEXT_RESULTS",
    "EPISODE_TYPE_SESSION_INSIGHT",
    "EPISODE_TYPE_CODEBASE_DISCOVERY",
    "EPISODE_TYPE_PATTERN",
    "EPISODE_TYPE_GOTCHA",
    "EPISODE_TYPE_TASK_OUTCOME",
    "EPISODE_TYPE_QA_RESULT",
    "EPISODE_TYPE_HISTORICAL_CONTEXT",
    "EPISODE_TYPE_ROOT_CAUSE",
    "EPISODE_TYPE_USER_CORRECTION",
    "EPISODE_TYPE_CODE_RELATIONSHIP",
    "EPISODE_TYPE_FUNCTION_CALL",
    "EPISODE_TYPE_IMPORT_DEPENDENCY",
    "EPISODE_TYPE_CLASS_INHERITANCE",
]
