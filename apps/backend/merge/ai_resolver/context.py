"""
Conflict Context
================

Minimal context needed to resolve a conflict.

This module provides the ConflictContext class that encapsulates
all the information needed to send to the AI for conflict resolution,
optimized for minimal token usage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..types import SemanticChange


@dataclass
class ConflictContext:
    """
    Minimal context needed to resolve a conflict.

    This is what gets sent to the AI - optimized for minimal tokens.
    """

    file_path: str
    location: str
    baseline_code: str  # The code before any task modified it
    task_changes: list[
        tuple[str, str, list[SemanticChange]]
    ]  # (task_id, intent, changes)
    conflict_description: str
    language: str = "unknown"
    semantic_context: dict[str, Any] = field(
        default_factory=dict
    )  # Additional semantic information (scopes, signatures, renames, etc.)

    def to_prompt_context(self) -> str:
        """Format as context for the AI prompt."""
        lines = [
            f"File: {self.file_path}",
            f"Location: {self.location}",
            f"Language: {self.language}",
        ]

        # Add semantic context if available
        if self.semantic_context:
            lines.append("")
            lines.append("--- SEMANTIC CONTEXT ---")
            for key, value in self.semantic_context.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"{key}: {json.dumps(value, indent=2)}")
                else:
                    lines.append(f"{key}: {value}")
            lines.append("--- END SEMANTIC CONTEXT ---")

        lines.extend(
            [
                "",
                "--- BASELINE CODE (before any changes) ---",
                self.baseline_code,
                "--- END BASELINE ---",
                "",
                "CHANGES FROM EACH TASK:",
            ]
        )

        for task_id, intent, changes in self.task_changes:
            lines.append(f"\n[Task: {task_id}]")
            lines.append(f"Intent: {intent}")
            lines.append("Changes:")
            for change in changes:
                lines.append(f"  - {change.change_type.value}: {change.target}")
                if change.content_after:
                    # Truncate long content
                    content = change.content_after
                    if len(content) > 500:
                        content = content[:500] + "... (truncated)"
                    lines.append(f"    Code: {content}")

        lines.extend(
            [
                "",
                f"CONFLICT: {self.conflict_description}",
            ]
        )

        return "\n".join(lines)

    @property
    def estimated_tokens(self) -> int:
        """Rough estimate of tokens in this context."""
        text = self.to_prompt_context()
        # Rough estimate: 4 chars per token for code
        return len(text) // 4
