"""Result objects returned by runtime sessions."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentRunResult:
    """Provider-neutral result for one agent run."""

    status: str
    response_text: str
    usage_metadata: dict[str, int] | None = None
    decision_tracker: Any = None
