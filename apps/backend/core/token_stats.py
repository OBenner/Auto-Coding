#!/usr/bin/env python3
"""
Token Statistics Data Structures
=================================

Data classes for tracking token usage across agent execution phases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

PhaseType = Literal["planning", "coding", "validation"]


@dataclass
class PhaseTokenStats:
    """Token statistics for a single execution phase."""

    phase: PhaseType
    input_tokens: int = 0
    output_tokens: int = 0
    session_count: int = 0  # Number of agent sessions in this phase
    model: str | None = None  # Most recent model used in this phase
    provider: str | None = None  # Most recent provider used in this phase
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens (input + output)."""
        return self.input_tokens + self.output_tokens


@dataclass
class TaskTokenStats:
    """Aggregated token statistics for an entire task."""

    phases: dict[PhaseType, PhaseTokenStats]
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "phases": {
                name: {
                    "phase": stats.phase,
                    "input_tokens": stats.input_tokens,
                    "output_tokens": stats.output_tokens,
                    "total_tokens": stats.total_tokens,
                    "session_count": stats.session_count,
                    "model": stats.model,
                    "provider": stats.provider,
                    "updated_at": stats.updated_at.isoformat(),
                }
                for name, stats in self.phases.items()
            },
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
