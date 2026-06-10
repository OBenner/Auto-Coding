"""Result objects returned by runtime sessions."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentRunResult:
    """Provider-neutral result for one agent run."""

    status: str
    response_text: str
    usage_metadata: dict[str, Any] | None = None
    decision_tracker: Any = None
    artifacts: dict[str, str] | None = None
    # Phase 1.2 mutating subagents: a changeset-exporting session (a
    # write-confined child) finishes WITHOUT committing its staged mutations
    # to the shared workspace; the staged pre/postimages are returned here so
    # the parent can merge them transactionally.
    changeset: dict[str, Any] | None = None
