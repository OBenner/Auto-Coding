"""
JSON Recovery
=============

Three-tier JSON parser with progressive recovery strategies.

Tier 1: Direct json.loads()
Tier 2: Syntax repair (trailing commas, unclosed brackets, unquoted values)
Tier 3: Regex extraction from markdown fences / surrounding prose
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Maximum raw text size we'll attempt to recover (1 MB)
_MAX_INPUT_SIZE = 1_048_576


def _repair_json_syntax(raw: str) -> str | None:
    """Apply common JSON syntax repairs.

    Handles trailing commas, unclosed brackets/braces, and unquoted status
    values. Mirrors the logic in ``spec.validate_pkg.auto_fix._repair_json_syntax``
    but operates on arbitrary JSON text rather than plan files.
    """
    if not raw or len(raw) > _MAX_INPUT_SIZE:
        return None

    repaired = raw.strip()

    # 1. Remove trailing commas before closing brackets/braces
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)

    # 2. Close unclosed brackets/braces
    # Strip string contents to avoid counting brackets inside strings
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', repaired)
    stack: list[str] = []
    for ch in stripped:
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    # Close any remaining open brackets in reverse order
    for opener in reversed(stack):
        if opener == "{":
            repaired += "\n}"
        elif opener == "[":
            repaired += "\n]"

    # 3. Fix unquoted status-like values
    repaired = re.sub(
        r'("[^"]+"\s*):\s*'
        r"(pending|in_progress|completed|failed|done|backlog)"
        r"(\s*[,}\]])",
        r'\1: "\2"\3',
        repaired,
    )

    # Validate the repair
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        return None


def _try_parse_or_repair(candidate: str) -> str | None:
    """Try to parse JSON directly, then attempt syntax repair on failure."""
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        return _repair_json_syntax(candidate)


def _find_matching_bracket(
    raw: str, start_idx: int, start_char: str, end_char: str
) -> int:
    """Find the index of the matching closing bracket, or -1 if not found.

    Tracks string context and escape sequences to avoid counting brackets
    inside JSON string values.
    """
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start_idx, len(raw)):
        ch = raw[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                return i
    return -1


def _extract_bracket_block(raw: str, start_char: str, end_char: str) -> str | None:
    """Extract and validate a JSON block delimited by start_char/end_char."""
    start_idx = raw.find(start_char)
    if start_idx == -1:
        return None

    end_idx = _find_matching_bracket(raw, start_idx, start_char, end_char)
    if end_idx == -1:
        return None

    candidate = raw[start_idx : end_idx + 1]
    return _try_parse_or_repair(candidate)


def _extract_json_block(raw: str) -> str | None:
    """Extract the first JSON object/array from markdown fences or prose."""

    # Try markdown fenced JSON block: ```json ... ``` or ``` ... ```
    fence_pattern = re.compile(r"```(?:json)?[ \t]*\n(.*?)```", re.DOTALL)
    match = fence_pattern.search(raw)
    if match:
        result = _try_parse_or_repair(match.group(1).strip())
        if result is not None:
            return result

    # Try to find the first { ... } or [ ... ] block in the text
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        result = _extract_bracket_block(raw, start_char, end_char)
        if result is not None:
            return result

    return None


def parse_json_with_recovery(
    raw_text: str, context: str = ""
) -> tuple[dict[str, Any] | list[Any], str]:
    """Parse JSON text with three tiers of progressive recovery.

    Args:
        raw_text: The raw text to parse as JSON.
        context: Optional label for log messages (e.g. "implementation_plan").

    Returns:
        A tuple of ``(parsed_object, tier_used)`` where *tier_used* is one of
        ``"tier1_direct"``, ``"tier2_repair"``, or ``"tier3_extract"``.

    Raises:
        json.JSONDecodeError: If all recovery tiers fail.
        ValueError: If *raw_text* exceeds ``_MAX_INPUT_SIZE``.
    """
    if len(raw_text) > _MAX_INPUT_SIZE:
        raise ValueError(
            f"Input too large for JSON recovery ({len(raw_text):,} bytes, "
            f"limit {_MAX_INPUT_SIZE:,}){f' ({context})' if context else ''}"
        )

    ctx = f" ({context})" if context else ""

    # --- Tier 1: direct parse --------------------------------------------------
    try:
        return json.loads(raw_text), "tier1_direct"
    except json.JSONDecodeError:
        logger.debug("JSON tier-1 (direct) failed%s", ctx)

    # --- Tier 2: syntax repair -------------------------------------------------
    repaired = _repair_json_syntax(raw_text)
    if repaired is not None:
        logger.info("JSON tier-2 (repair) succeeded%s", ctx)
        return json.loads(repaired), "tier2_repair"

    # --- Tier 3: extract from surrounding text / fences ------------------------
    extracted = _extract_json_block(raw_text)
    if extracted is not None:
        logger.info("JSON tier-3 (extract) succeeded%s", ctx)
        return json.loads(extracted), "tier3_extract"

    # All tiers failed
    raise json.JSONDecodeError(
        f"All JSON recovery tiers failed{ctx}",
        raw_text[:200],
        0,
    )
