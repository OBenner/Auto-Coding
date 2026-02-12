"""
Fix Suggester
==============

AI-powered fix suggestion engine for debugging errors.
Analyzes stack traces, error patterns, and code context to generate
targeted fix recommendations with code examples.

Uses the Claude Agent SDK (same as the rest of the system) for suggestions.
Falls back to pattern-based suggestions if AI fails (never blocks debugging).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    import claude_agent_sdk  # noqa: F401

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from core.auth import ensure_claude_code_oauth_token, get_auth_token

# Default model for fix suggestions (fast and accurate)
# Note: Using Haiku 4.5 for fast, cheap suggestions. Haiku does not support
# extended thinking, so thinking_default is set to "none" in models.py
DEFAULT_SUGGESTION_MODEL = "claude-haiku-4-5-20251001"

# Maximum stack trace size to send to the LLM
MAX_TRACE_CHARS = 15000


def is_suggestion_enabled() -> bool:
    """Check if fix suggestion is enabled."""
    # Suggestion requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("FIX_SUGGESTION_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_suggestion_model() -> str:
    """Get the model to use for fix suggestions."""
    return os.environ.get("FIX_SUGGESTION_MODEL", DEFAULT_SUGGESTION_MODEL)


# =============================================================================
# Input Gathering
# =============================================================================


def gather_suggestion_inputs(
    parsed_trace: dict | None,
    pattern_match: dict | None,
    code_context: dict | None,
    historical_errors: list[dict] | None = None,
) -> dict:
    """
    Gather all inputs needed for fix suggestion.

    Args:
        parsed_trace: Parsed stack trace from stack_trace_parser
        pattern_match: Error pattern match from error_pattern_matcher
        code_context: Context about the code (failing file, surrounding code, etc.)
        historical_errors: List of similar past errors with their fixes

    Returns:
        Dict with all inputs for the suggester
    """
    return {
        "parsed_trace": parsed_trace or {},
        "pattern_match": pattern_match,
        "code_context": code_context or {},
        "historical_errors": historical_errors or [],
    }


# =============================================================================
# LLM-Based Suggestions
# =============================================================================


def _build_suggestion_prompt(inputs: dict) -> str:
    """Build the prompt for fix suggestion."""
    prompt_file = Path(__file__).parent / "prompts" / "fix_suggestion.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        # Fallback if prompt file missing
        base_prompt = """Analyze this error and suggest specific fixes with code examples.
Output ONLY valid JSON with: root_cause, fix_category, suggested_fixes (array), verification_steps."""

    # Build error context
    error_context = _format_error_context(inputs)

    # Build code context
    code_section = _format_code_context(inputs)

    # Build historical context
    history_section = _format_historical_errors(inputs)

    session_context = f"""
---

## ERROR CONTEXT

### Stack Trace Summary
{error_context}

### Code Context
{code_section}

### Historical Similar Errors
{history_section}

---

Now analyze this error and provide specific, actionable fix suggestions.
Output ONLY the JSON object.
"""

    return base_prompt + session_context


def _format_error_context(inputs: dict) -> str:
    """Format the error trace for the prompt."""
    trace = inputs.get("parsed_trace", {})

    error_type = trace.get("error_type", "UnknownError")
    error_message = trace.get("error_message", "No message")
    language = trace.get("language", "unknown")
    failing_file = trace.get("failing_file", "Unknown")
    failing_line = trace.get("failing_line", "Unknown")

    return f"""- **Error Type**: {error_type}
- **Error Message**: {error_message}
- **Language**: {language}
- **Failing File**: {failing_file}
- **Failing Line**: {failing_line}"""


def _format_code_context(inputs: dict) -> str:
    """Format the code context for the prompt."""
    context = inputs.get("code_context", {})

    if not context:
        return "(No code context available)"

    failing_code = context.get("failing_code", "(Code not available)")
    surrounding_lines = context.get("surrounding_lines", [])
    file_path = context.get("file_path", "Unknown file")

    lines = [f"**File**: {file_path}", ""]
    lines.append("**Failing Code:**")
    lines.append("```")
    lines.append(failing_code)
    lines.append("```")
    lines.append("")

    if surrounding_lines:
        lines.append("**Surrounding Context:**")
        lines.append("```")
        lines.extend(surrounding_lines)
        lines.append("```")
    else:
        lines.append("(No surrounding context available)")

    return "\n".join(lines)


def _format_historical_errors(inputs: dict) -> str:
    """Format historical errors for the prompt."""
    history = inputs.get("historical_errors", [])

    if not history:
        return "(No historical errors found)"

    lines = []
    for i, past_error in enumerate(history[:5], 1):  # Limit to 5 most recent
        error_type = past_error.get("error_type", "Unknown")
        fix_applied = past_error.get("fix_applied", "No fix recorded")
        outcome = past_error.get("outcome", "unknown")

        lines.append(f"**Past Error {i}** ({outcome}):")
        lines.append(f"  - Error: {error_type}")
        lines.append(f"  - Fix: {fix_applied}")

        if outcome == "success":
            lines.append(f"  - ✅ This fix worked")
        else:
            lines.append(f"  - ❌ This fix did not work")
        lines.append("")

    return "\n".join(lines) if lines else "(No historical errors available)"


async def run_fix_suggestion(
    inputs: dict, project_dir: Path | None = None
) -> dict | None:
    """
    Run the fix suggestion using Claude Agent SDK.

    Args:
        inputs: Gathered suggestion inputs
        project_dir: Project directory for SDK context (optional)

    Returns:
        Suggested fixes dict or None if failed
    """
    if not SDK_AVAILABLE:
        logger.warning("Claude SDK not available, skipping fix suggestion")
        return None

    if not get_auth_token():
        logger.warning("No authentication token found, skipping fix suggestion")
        return None

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = get_suggestion_model()
    prompt = _build_suggestion_prompt(inputs)

    # Use current directory if project_dir not specified
    cwd = str(project_dir.resolve()) if project_dir else os.getcwd()

    try:
        # Use simple_client for fix suggestion
        from pathlib import Path

        from core.simple_client import create_simple_client

        client = create_simple_client(
            agent_type="insights",
            model=model,
            system_prompt=(
                "You are an expert debugging assistant. You analyze errors and suggest "
                "specific fixes with code examples. Always respond with valid JSON only, "
                "no markdown formatting or explanations outside the JSON."
            ),
            cwd=Path(cwd) if cwd else None,
        )

        # Use async context manager
        async with client:
            await client.query(prompt)

            # Collect the response
            response_text = ""
            message_count = 0
            text_blocks_found = 0

            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                message_count += 1

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        # Must check block type - only TextBlock has .text attribute
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            text_blocks_found += 1
                            if block.text:  # Only add non-empty text
                                response_text += block.text
                            else:
                                logger.debug(
                                    f"Found empty TextBlock in response (block #{text_blocks_found})"
                                )

            # Log response collection summary
            logger.debug(
                f"Fix suggestion response: {message_count} messages, "
                f"{text_blocks_found} text blocks, {len(response_text)} chars collected"
            )

            # Validate we received content before parsing
            if not response_text.strip():
                logger.warning(
                    f"Fix suggestion returned empty response. "
                    f"Messages received: {message_count}, TextBlocks found: {text_blocks_found}. "
                    f"This may indicate the AI model did not respond with text content."
                )
                return None

        # Parse JSON from response
        return parse_suggestion(response_text)

    except Exception as e:
        logger.warning(f"Fix suggestion failed: {e}")
        return None


def parse_suggestion(response_text: str) -> dict | None:
    """
    Parse the LLM response into structured suggestions.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed suggestions dict or None if parsing failed
    """
    # Try to extract JSON from the response
    text = response_text.strip()

    # Early validation - check for empty response
    if not text:
        logger.warning("Cannot parse suggestion: response text is empty")
        return None

    # Handle markdown code blocks
    if text.startswith("```"):
        # Remove code block markers
        lines = text.split("\n")
        # Remove first line (```json or ```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

        # Check again after removing code blocks
        if not text:
            logger.warning(
                "Cannot parse suggestion: response contained only markdown code block markers with no content"
            )
            return None

    try:
        suggestion = json.loads(text)

        # Validate structure
        if not isinstance(suggestion, dict):
            logger.warning(
                f"Suggestion is not a dict, got type: {type(suggestion).__name__}"
            )
            return None

        # Ensure required keys exist with defaults
        suggestion.setdefault("root_cause", "Unknown root cause")
        suggestion.setdefault("fix_category", "unknown")
        suggestion.setdefault("suggested_fixes", [])
        suggestion.setdefault("verification_steps", [])
        suggestion.setdefault("confidence", 0.5)

        return suggestion

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse suggestion JSON: {e}")
        # Show more context in the error message
        preview_length = min(500, len(text))
        logger.warning(
            f"Response text preview (first {preview_length} chars): {text[:preview_length]}"
        )
        if len(text) > preview_length:
            logger.warning(f"... (total length: {len(text)} chars)")
        return None


# =============================================================================
# Pattern-Based Fallback Suggestions
# =============================================================================


def get_pattern_based_suggestion(
    parsed_trace: dict | None, pattern_match: dict | None
) -> dict:
    """
    Generate pattern-based fix suggestions (fallback when AI unavailable).

    Args:
        parsed_trace: Parsed stack trace
        pattern_match: Error pattern match result

    Returns:
        Suggestion dict with pattern-based recommendations
    """
    if pattern_match and pattern_match.get("pattern"):
        pattern = pattern_match["pattern"]
        return {
            "root_cause": pattern.get("description", "Unknown error pattern"),
            "fix_category": pattern.get("category", "unknown"),
            "suggested_fixes": [
                pattern.get("suggestion", "No specific suggestion available")
            ],
            "verification_steps": _get_verification_steps(pattern.get("category")),
            "confidence": pattern_match.get("confidence", 0.5),
            "pattern_based": True,
        }

    # Fallback for unknown errors
    error_type = parsed_trace.get("error_type", "UnknownError") if parsed_trace else "UnknownError"
    return {
        "root_cause": f"An error of type '{error_type}' occurred",
        "fix_category": "unknown",
        "suggested_fixes": [
            "Review the stack trace to identify the failing code",
            "Check for common issues like missing imports, type mismatches, or null values",
            "Add error handling or logging to gather more information",
        ],
        "verification_steps": [
            "Reproduce the error consistently",
            "Add debug logging to understand the error context",
            "Test the fix after applying changes",
        ],
        "confidence": 0.3,
        "pattern_based": True,
    }


def _get_verification_steps(category: str) -> list[str]:
    """Get verification steps for an error category."""
    steps = {
        "import_error": [
            "Verify the module is installed in your environment",
            "Check import statement syntax and module path",
            "Restart your development environment after installing",
        ],
        "type_error": [
            "Check variable types before the operation",
            "Add type validation or conversion",
            "Test with different input types to verify fix",
        ],
        "null_reference": [
            "Add null/None checks before accessing properties",
            "Verify all code paths initialize the variable",
            "Test with None values to ensure handling",
        ],
        "lookup_error": [
            "Verify the key/index exists before accessing",
            "Use .get() method with default for dictionaries",
            "Check array/collection bounds before indexing",
        ],
        "syntax_error": [
            "Run a linter to identify exact syntax issue",
            "Check for matching brackets, quotes, and parentheses",
            "Verify language version compatibility",
        ],
        "timeout": [
            "Verify the operation completes within expected time",
            "Check for blocking operations or infinite loops",
            "Consider increasing timeout if operation is legitimately slow",
        ],
        "permission_error": [
            "Check file/directory permissions",
            "Verify credentials and tokens are correct",
            "Ensure process has required access rights",
        ],
        "file_error": [
            "Verify the file path is correct",
            "Check if file exists before accessing",
            "Use absolute paths to avoid path confusion",
        ],
        "network_error": [
            "Verify network connectivity",
            "Check if the service/server is running",
            "Test endpoint with curl or similar tool",
        ],
    }

    return steps.get(category, ["Test the fix thoroughly", "Verify error is resolved", "Check for side effects"])


# =============================================================================
# Main Entry Point
# =============================================================================


async def suggest_fix(
    parsed_trace: dict | None,
    pattern_match: dict | None,
    code_context: dict | None,
    historical_errors: list[dict] | None = None,
    project_dir: Path | None = None,
) -> dict:
    """
    Suggest fixes for an error.

    This is the main entry point for fix suggestion.
    Uses AI-powered suggestions when available, falls back to pattern-based suggestions.

    Args:
        parsed_trace: Parsed stack trace from stack_trace_parser
        pattern_match: Error pattern match from error_pattern_matcher
        code_context: Context about the failing code
        historical_errors: List of similar past errors with fixes
        project_dir: Project directory for SDK context

    Returns:
        Suggestion dict with fix recommendations
    """
    # Check if suggestion is enabled
    if not is_suggestion_enabled():
        logger.info("Fix suggestion disabled, using pattern-based suggestions")
        return get_pattern_based_suggestion(parsed_trace, pattern_match)

    try:
        # Gather inputs
        inputs = gather_suggestion_inputs(
            parsed_trace=parsed_trace,
            pattern_match=pattern_match,
            code_context=code_context,
            historical_errors=historical_errors,
        )

        # Run AI-powered suggestion
        suggestion = await run_fix_suggestion(inputs, project_dir=project_dir)

        if suggestion:
            # Add metadata
            suggestion["pattern_based"] = False
            suggestion["ai_generated"] = True

            logger.info(
                f"Generated AI suggestion: {suggestion.get('fix_category', 'unknown')} "
                f"category, {len(suggestion.get('suggested_fixes', []))} fixes"
            )
            return suggestion
        else:
            logger.warning("AI suggestion returned no results, using pattern-based")
            return get_pattern_based_suggestion(parsed_trace, pattern_match)

    except Exception as e:
        logger.warning(f"Fix suggestion failed: {e}, using pattern-based")
        return get_pattern_based_suggestion(parsed_trace, pattern_match)


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Test fix suggestion")
    parser.add_argument(
        "--trace-file", type=Path, help="File containing stack trace"
    )
    parser.add_argument(
        "--project-dir", type=Path, help="Project directory"
    )

    args = parser.parse_args()

    if not args.trace_file:
        parser.error("--trace-file is required")

    # Read trace from file
    trace_content = args.trace_file.read_text(encoding="utf-8")

    # Parse trace
    from .stack_trace_parser import parse_stack_trace

    parsed = parse_stack_trace(trace_content)

    # Convert to dict for suggestion
    parsed_dict = {
        "error_type": parsed.error_type if parsed else "UnknownError",
        "error_message": parsed.error_message if parsed else "",
        "language": parsed.language if parsed else "unknown",
        "failing_file": parsed.frames[-1].file_path if parsed and parsed.frames else None,
        "failing_line": parsed.frames[-1].line_number if parsed and parsed.frames else None,
        "frame_count": len(parsed.frames) if parsed else 0,
    }

    async def main():
        suggestion = await suggest_fix(
            parsed_trace=parsed_dict,
            pattern_match=None,
            code_context=None,
            historical_errors=None,
            project_dir=args.project_dir,
        )
        print(json.dumps(suggestion, indent=2))

    asyncio.run(main())
