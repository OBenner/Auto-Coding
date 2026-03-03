"""
Shared Regex Patterns for Context Analyzers
=============================================

Centralized compiled regex patterns used across multiple context analyzer modules.
Avoids duplication and reduces total compiled-pattern count.
"""

from __future__ import annotations

import re

# Dependency name pattern - extracts package names from requirements.txt lines
DEPENDENCY_NAME_PATTERN = re.compile(r"^([a-zA-Z0-9_-]+)", re.MULTILINE)

# Auth decorator pattern - finds auth-related decorators in Python files
AUTH_DECORATOR_PATTERN = re.compile(r"@(\w*(?:require|auth|login)\w*)")

# Celery task decorator pattern - finds Celery task definitions
CELERY_TASK_PATTERN = re.compile(
    r"@(?:celery\.task|shared_task|app\.task)\s*(?:\([^)]*\))?\s*def\s+(\w+)"
)
