"""Shared JSON extraction helpers for completion-style runtime adapters."""

import json
from collections.abc import Callable


def extract_first_json_object(
    text: str,
    *,
    strip_fence: Callable[[str], str],
    error_factory: Callable[[str], Exception],
    missing_message: str,
    incomplete_message: str,
) -> str:
    """Extract the first complete JSON object substring from model text."""
    stripped = strip_fence(text)
    if "{" not in stripped:
        raise error_factory(missing_message)

    decoder = json.JSONDecoder()
    for start in _json_object_start_positions(stripped):
        try:
            parsed, end = decoder.raw_decode(stripped[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return stripped[start : start + end]

    raise error_factory(incomplete_message)


def _json_object_start_positions(text: str):
    """Yield candidate JSON object start offsets."""
    return (index for index, char in enumerate(text) if char == "{")
