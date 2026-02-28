"""
Heuristic Decision Extraction from Agent Conversation Streams
==============================================================

Extracts meaningful decisions from agent tool calls and text responses
WITHOUT making additional LLM calls. Uses pattern matching and heuristics
to identify high-level choices the agent makes during task execution.

Decisions are extracted at conversation round boundaries and logged
via the existing DecisionTracker infrastructure.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from task_logger.decision_models import Alternative, DecisionType

if TYPE_CHECKING:
    from .decision_tracker import DecisionTracker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Regex patterns for detecting decision signals in agent text
# ---------------------------------------------------------------------------

APPROACH_PATTERNS = [
    re.compile(r"I'll go with\b", re.IGNORECASE),
    re.compile(r"I(?:'ll| will) use\b", re.IGNORECASE),
    re.compile(r"I(?:'ve| have) decided to\b", re.IGNORECASE),
    re.compile(r"(?:the )?best approach (?:is|would be)\b", re.IGNORECASE),
    re.compile(r"\bI chose\b", re.IGNORECASE),
    re.compile(r"\binstead of\b", re.IGNORECASE),
    re.compile(r"\brather than\b", re.IGNORECASE),
]

ARCHITECTURE_PATTERNS = [
    re.compile(
        r"(?:I'll |Let me )create a new (?:module|class|component|service|interface|file)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:I'll |Let me )introduce a new\b", re.IGNORECASE),
    re.compile(r"extract (?:into|to) (?:a )?(?:new|separate)\b", re.IGNORECASE),
    re.compile(r"separate concern", re.IGNORECASE),
    re.compile(r"new abstraction", re.IGNORECASE),
    re.compile(
        r"(?:I'll |Let me )(?:add|create) (?:a )?new (?:utility|helper|hook|provider|context|store)",
        re.IGNORECASE,
    ),
]

RECOVERY_PATTERNS = [
    re.compile(
        r"\b(?:fix(?:ing)?|resolv(?:e|ing)|workaround|fallback|different approach|try (?:a )?different)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bthat (?:didn't|did not) work\b", re.IGNORECASE),
    re.compile(r"\blet me try\b", re.IGNORECASE),
]

DEPENDENCY_COMMANDS = (
    "npm install",
    "npm i ",
    "yarn add",
    "pip install",
    "uv add",
    "uv pip install",
    "cargo add",
    "go get",
    "composer require",
    "pnpm add",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RoundContext:
    """Accumulated context from a single conversation round."""

    text_blocks: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_errors: list[dict[str, str]] = field(default_factory=list)
    has_write_call: bool = False
    edit_call_count: int = 0
    created_files: list[str] = field(default_factory=list)
    edited_files: list[str] = field(default_factory=list)
    bash_commands: list[str] = field(default_factory=list)


@dataclass
class ExtractedDecision:
    """A decision extracted from heuristic analysis of agent behaviour."""

    decision_type: DecisionType | str
    context: str
    chosen_approach: str
    reasoning: str
    confidence: float
    alternatives: list[dict[str, str]] = field(default_factory=list)
    impact: str | None = None
    requires_review: bool = False


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _extract_sentence(text: str, pos: int) -> str:
    """Extract the sentence containing *pos*."""
    # Find sentence start (look back for sentence-ending punctuation)
    start = 0
    for delim in (".", "!", "?", "\n"):
        idx = text.rfind(delim, 0, pos)
        if idx != -1 and idx + 1 > start:
            start = idx + 1

    # Find sentence end
    end = len(text)
    for delim in (".", "!", "?", "\n"):
        idx = text.find(delim, pos)
        if idx != -1 and idx + 1 < end:
            end = idx + 1

    return text[start:end].strip()[:300]


def _extract_paragraph(text: str, pos: int) -> str:
    """Extract the paragraph containing *pos*."""
    start = text.rfind("\n\n", 0, pos)
    start = start + 2 if start != -1 else 0
    end = text.find("\n\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end].strip()[:500]


def _shorten_path(path: str, max_len: int = 60) -> str:
    """Shorten a file path for display."""
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3) :]


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


class DecisionExtractor:
    """
    Extracts decisions from conversation rounds using heuristics.

    Designed to be fed events during the response stream in
    ``run_agent_session`` and queried at round boundaries.

    Stateful: tracks previously emitted decisions for deduplication.
    """

    def __init__(self) -> None:
        self._seen_approaches: set[str] = set()
        self._ctx = RoundContext()

    # -- event feed ----------------------------------------------------------

    def on_text_block(self, text: str) -> None:
        """Called when a TextBlock is received from the agent."""
        self._ctx.text_blocks.append(text)

    def on_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Called when a ToolUseBlock is received."""
        self._ctx.tool_calls.append({"name": tool_name, "input": tool_input})

        if tool_name == "Write":
            self._ctx.has_write_call = True
            fp = tool_input.get("file_path", "")
            if fp:
                self._ctx.created_files.append(fp)
        elif tool_name == "Edit":
            self._ctx.edit_call_count += 1
            fp = tool_input.get("file_path", "")
            if fp:
                self._ctx.edited_files.append(fp)
        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")
            if cmd:
                self._ctx.bash_commands.append(cmd)

    def on_tool_error(self, tool_name: str, error_content: str) -> None:
        """Called when a tool returns an error."""
        self._ctx.tool_errors.append(
            {"tool_name": tool_name, "error": error_content[:500]}
        )

    # -- round boundary ------------------------------------------------------

    def end_round(self) -> ExtractedDecision | None:
        """
        Analyse accumulated round context and return a decision if detected.

        Resets internal context afterwards so the extractor is ready for the
        next round.  Returns ``None`` if no decision is detected or if the
        decision would be a duplicate.
        """
        try:
            decision = self._extract_decision()
            if decision and not self._is_duplicate(decision):
                self._seen_approaches.add(decision.chosen_approach[:80])
                return decision
            return None
        except Exception as e:
            logger.debug("Decision extraction error (non-fatal): %s", e)
            return None
        finally:
            self._ctx = RoundContext()

    # -- heuristic pipeline --------------------------------------------------

    def _extract_decision(self) -> ExtractedDecision | None:
        """Apply heuristics in priority order (max 1 per round)."""
        ctx = self._ctx
        full_text = " ".join(ctx.text_blocks)

        if not full_text.strip() and not ctx.tool_calls:
            return None

        # Priority 1: Architecture decisions
        if ctx.has_write_call:
            d = self._check_architecture(full_text, ctx)
            if d:
                return d

        # Priority 2: Approach decisions (explicit reasoning about options)
        d = self._check_approach(full_text)
        if d:
            return d

        # Priority 3: Error recovery
        if ctx.tool_errors:
            d = self._check_error_recovery(full_text, ctx)
            if d:
                return d

        # Priority 4: New file creation
        if ctx.has_write_call and ctx.created_files:
            return self._make_file_creation_decision(full_text, ctx)

        # Priority 5: Dependency / config changes via Bash
        d = self._check_implementation(full_text, ctx)
        if d:
            return d

        return None

    # -- individual heuristics -----------------------------------------------

    def _check_architecture(
        self, text: str, ctx: RoundContext
    ) -> ExtractedDecision | None:
        for pattern in ARCHITECTURE_PATTERNS:
            match = pattern.search(text)
            if match:
                sentence = _extract_sentence(text, match.start())
                paragraph = _extract_paragraph(text, match.start())
                files_display = ", ".join(
                    _shorten_path(f) for f in ctx.created_files[:3]
                )
                return ExtractedDecision(
                    decision_type=DecisionType.ARCHITECTURE,
                    context=f"Creating new files: {files_display}"
                    if files_display
                    else "Architectural change",
                    chosen_approach=sentence,
                    reasoning=paragraph,
                    confidence=0.75,
                    impact=f"New files: {files_display}" if files_display else None,
                )
        return None

    def _check_approach(self, text: str) -> ExtractedDecision | None:
        for pattern in APPROACH_PATTERNS:
            match = pattern.search(text)
            if match:
                sentence = _extract_sentence(text, match.start())
                paragraph = _extract_paragraph(text, match.start())

                # Try to extract rejected alternatives
                alternatives: list[dict[str, str]] = []
                search_region = text[max(0, match.start() - 200) : match.end() + 500]

                for alt_pattern, label in (
                    (r"instead of (.+?)(?:\.|,|\n|$)", "Agent chose alternative"),
                    (r"rather than (.+?)(?:\.|,|\n|$)", "Agent chose alternative"),
                ):
                    alt_match = re.search(alt_pattern, search_region, re.IGNORECASE)
                    if alt_match:
                        desc = alt_match.group(1).strip()[:200]
                        if desc:
                            alternatives.append(
                                {
                                    "description": desc,
                                    "reasoning": "",
                                    "rejected_reason": label,
                                }
                            )

                return ExtractedDecision(
                    decision_type=DecisionType.APPROACH,
                    context=paragraph[:300],
                    chosen_approach=sentence,
                    reasoning=paragraph,
                    confidence=0.70,
                    alternatives=alternatives,
                )
        return None

    def _check_error_recovery(
        self, text: str, ctx: RoundContext
    ) -> ExtractedDecision | None:
        for pattern in RECOVERY_PATTERNS:
            match = pattern.search(text)
            if match:
                last_error = ctx.tool_errors[-1]
                error_summary = last_error["error"][:200]
                sentence = _extract_sentence(text, match.start())
                paragraph = _extract_paragraph(text, match.start())

                return ExtractedDecision(
                    decision_type=DecisionType.ERROR_RECOVERY,
                    context=f"Error in {last_error['tool_name']}: {error_summary}",
                    chosen_approach=sentence,
                    reasoning=paragraph,
                    confidence=0.60,
                    requires_review=True,
                )
        return None

    def _make_file_creation_decision(
        self, text: str, ctx: RoundContext
    ) -> ExtractedDecision:
        files_display = ", ".join(_shorten_path(f) for f in ctx.created_files[:5])
        # Try to get reasoning from surrounding text
        reasoning = ""
        if ctx.text_blocks:
            # Use the last text block before tool calls as reasoning
            reasoning = ctx.text_blocks[-1].strip()[:500]

        return ExtractedDecision(
            decision_type=DecisionType.FILE_MODIFICATION,
            context=f"Creating {len(ctx.created_files)} new file(s)",
            chosen_approach=f"Create: {files_display}",
            reasoning=reasoning or "New file creation",
            confidence=0.80,
            impact=f"Files created: {files_display}",
        )

    def _check_implementation(
        self, text: str, ctx: RoundContext
    ) -> ExtractedDecision | None:
        for cmd in ctx.bash_commands:
            cmd_lower = cmd.lower()
            for dep_cmd in DEPENDENCY_COMMANDS:
                if dep_cmd in cmd_lower:
                    reasoning = ""
                    if ctx.text_blocks:
                        reasoning = ctx.text_blocks[-1].strip()[:500]

                    return ExtractedDecision(
                        decision_type=DecisionType.IMPLEMENTATION,
                        context="Dependency or configuration change",
                        chosen_approach=cmd[:200],
                        reasoning=reasoning or "Installing dependency",
                        confidence=0.80,
                        impact=f"Command: {cmd[:100]}",
                    )
        return None

    # -- deduplication -------------------------------------------------------

    def _is_duplicate(self, decision: ExtractedDecision) -> bool:
        return decision.chosen_approach[:80] in self._seen_approaches


# ---------------------------------------------------------------------------
# Post-hoc extraction from ConversationHistory
# ---------------------------------------------------------------------------


def extract_decisions_from_history(
    conversation_history: Any,
) -> list[ExtractedDecision]:
    """
    Extract decisions from a completed ConversationHistory.

    Used for subprocess sessions (``run_agent_session_isolated``) where
    we cannot intercept the response stream in real-time.

    Args:
        conversation_history: A ConversationHistory instance with ``.rounds``.

    Returns:
        List of extracted decisions (may be empty).
    """
    extractor = DecisionExtractor()
    decisions: list[ExtractedDecision] = []

    rounds = getattr(conversation_history, "rounds", [])
    for round_obj in rounds:
        # Feed text
        text = getattr(round_obj, "assistant_response", "")
        if text:
            extractor.on_text_block(text)

        # Feed tool calls
        for tc in getattr(round_obj, "tool_calls", []):
            name = tc.get("name", "")
            inp = tc.get("input", {})
            if name:
                extractor.on_tool_call(name, inp if isinstance(inp, dict) else {})

        # End round and collect decision
        decision = extractor.end_round()
        if decision:
            decisions.append(decision)

    return decisions


# ---------------------------------------------------------------------------
# Helper to log an extracted decision via DecisionTracker
# ---------------------------------------------------------------------------


def log_extracted_decision(
    tracker: DecisionTracker,
    extracted: ExtractedDecision,
) -> None:
    """
    Convert an ``ExtractedDecision`` into a tracked and logged
    ``DecisionPoint`` using the existing ``DecisionTracker`` API.
    """
    alternatives = None
    if extracted.alternatives:
        alternatives = [
            Alternative(
                description=alt.get("description", ""),
                reasoning=alt.get("reasoning", ""),
                rejected_reason=alt.get("rejected_reason", ""),
            )
            for alt in extracted.alternatives
        ]

    decision = tracker.track_decision(
        decision_type=extracted.decision_type,
        context=extracted.context,
        chosen_approach=extracted.chosen_approach,
        reasoning=extracted.reasoning,
        confidence=extracted.confidence,
        alternatives=alternatives,
        impact=extracted.impact,
    )
    if extracted.requires_review:
        decision.requires_review = True

    tracker.log_decision(decision, print_to_console=False)
