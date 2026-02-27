"""
Code Parsers
============

Utilities for parsing code from AI responses.

This module contains functions for extracting code blocks from AI
responses and validating that content looks like code.
"""

from __future__ import annotations

import re


def extract_code_block(response: str, language: str) -> str | None:
    """
    Extract code block from AI response.

    Args:
        response: The AI response text
        language: Expected programming language

    Returns:
        Extracted code block, or None if not found
    """
    # Try to find fenced code block
    escaped_lang = re.escape(language)
    escaped_lang_lower = re.escape(language.lower())
    patterns = [
        rf"```{escaped_lang}\n(.*?)```",
        rf"```{escaped_lang_lower}\n(.*?)```",
        r"```\n(.*?)```",
        r"```(.*?)```",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

    # If no code block, check if the entire response looks like code
    lines = response.strip().split("\n")
    if lines and not lines[0].startswith("```"):
        # Assume entire response is code if it looks like it
        if looks_like_code(response, language):
            return response.strip()

    return None


def looks_like_code(text: str, language: str) -> bool:
    """
    Heuristic to check if text looks like code.

    Args:
        text: Text to check
        language: Programming language to check for

    Returns:
        True if text appears to be code
    """
    indicators = {
        "python": ["def ", "import ", "class ", "if ", "for "],
        "javascript": ["function", "const ", "let ", "var ", "import ", "export "],
        "typescript": ["function", "const ", "let ", "interface ", "type ", "import "],
        "tsx": ["function", "const ", "return ", "import ", "export ", "<"],
        "jsx": ["function", "const ", "return ", "import ", "export ", "<"],
    }

    lang_indicators = indicators.get(language.lower(), [])
    if lang_indicators:
        return any(ind in text for ind in lang_indicators)

    # Generic code indicators
    return any(
        ind in text for ind in ["=", "(", ")", "{", "}", "import", "def", "function"]
    )


def extract_batch_code_blocks(
    response: str,
    location: str,
    language: str,
) -> str | None:
    """
    Extract code block for a specific location from a batch response.

    Args:
        response: The batch AI response
        location: The conflict location to extract
        language: Programming language

    Returns:
        Extracted code block for the location, or None if not found
    """
    # Try to find the resolution for this location
    pattern = (
        rf"## Location: {re.escape(location)}.*?```{re.escape(language)}\n(.*?)```"
    )
    match = re.search(pattern, response, re.DOTALL)

    if match:
        return match.group(1).strip()

    return None


def extract_explanation(response: str) -> str | None:
    """
    Extract explanation from AI response.

    Args:
        response: The AI response text

    Returns:
        Extracted explanation text, or None if not found
    """
    # Look for "EXPLANATION:" / "Explanation:" / "**Explanation:**" headers.
    # Pattern allows optional leading asterisks, optional trailing asterisks
    # after the colon, and optional colon/dash separator.
    # Use re.MULTILINE so ^ matches any line start (not just the string start).
    # Bounded input to mitigate ReDoS on very large AI responses.
    if len(response) > 100_000:
        response = response[:100_000]

    # Split on the first ``` to isolate text before code blocks, avoiding
    # the need for re.DOTALL with (.*?) which risks polynomial backtracking.
    text_section = response.split("```")[0] if "```" in response else response

    # Match the Explanation header line; content is everything after the header.
    pattern = r"^\s*\*{0,2}\s*Explanation\s*[:\-]?\s*\*{0,2}\s*"
    match = re.search(pattern, text_section, re.IGNORECASE | re.MULTILINE)

    if match:
        # Everything after the header is the explanation text
        explanation = text_section[match.end() :].strip()
        explanation = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", explanation)
        return explanation or None

    return None
