"""
Collaboration Module
====================

Real-time collaborative spec editing with comments, suggestions,
presence indicators, and version tracking.
"""

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

__all__ = [
    "Comment",
    "CommentStatus",
    "Suggestion",
    "SuggestionStatus",
    "Presence",
    "PresenceType",
    "Version",
    "load_comments",
    "save_comments",
    "load_suggestions",
    "save_suggestions",
    "load_versions",
    "save_versions",
]
