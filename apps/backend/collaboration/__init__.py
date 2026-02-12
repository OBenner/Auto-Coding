"""
Collaboration Module
====================

Real-time collaborative spec editing with comments, suggestions,
presence indicators, and version tracking.
"""

from collaboration.comments import CommentManager
from collaboration.crdt_store import (
    CRDTStore,
    CrdtOperation,
    OpType,
)
from collaboration.models import (
    Comment,
    CommentStatus,
    Presence,
    PresenceType,
    Suggestion,
    SuggestionStatus,
    Version,
    load_comments,
    load_suggestions,
    load_versions,
    save_comments,
    save_suggestions,
    save_versions,
)
from collaboration.presence import PresenceManager
from collaboration.suggestions import SuggestionManager
from collaboration.version_history import DiffResult, VersionManager

__all__ = [
    "Comment",
    "CommentStatus",
    "CommentManager",
    "Suggestion",
    "SuggestionStatus",
    "SuggestionManager",
    "Presence",
    "PresenceManager",
    "PresenceType",
    "Version",
    "load_comments",
    "save_comments",
    "load_suggestions",
    "save_suggestions",
    "load_versions",
    "save_versions",
    "CRDTStore",
    "CrdtOperation",
    "OpType",
    "VersionManager",
    "DiffResult",
]
