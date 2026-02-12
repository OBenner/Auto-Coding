"""
Pattern Categorizer
===================

Automatically categorizes extracted code patterns using AI-based classification.
Patterns are classified into categories like architecture, testing, error handling, etc.

Uses the Claude Agent SDK (same as the rest of the system) for classification.
Falls back to generic "uncategorized" if classification fails (never blocks the build).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    import claude_agent_sdk  # noqa: F401

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from core.auth import ensure_claude_code_oauth_token, get_auth_token

# Default model for pattern categorization (fast and cheap)
# Note: Using Haiku 4.5 for fast, cheap categorization. Haiku does not support
# extended thinking, so thinking_default is set to "none" in models.py
DEFAULT_CATEGORIZATION_MODEL = "claude-haiku-4-5-20251001"

# Pattern categories
PATTERN_CATEGORIES = [
    "architecture",  # Architectural patterns (MVC, layering, module structure)
    "testing",  # Testing patterns (mocking, fixtures, test structure)
    "error-handling",  # Error handling patterns (try-catch, error boundaries, validation)
    "api-design",  # API design patterns (REST, GraphQL, endpoints, routing)
    "state-management",  # State management patterns (Redux, Context, local state)
    "security",  # Security patterns (auth, permissions, validation, sanitization)
    "performance",  # Performance patterns (caching, optimization, lazy loading)
    "data-access",  # Data access patterns (ORM, queries, repositories)
    "ui-patterns",  # UI patterns (components, layouts, forms)
    "integration",  # Integration patterns (third-party APIs, webhooks, events)
    "deployment",  # Deployment patterns (CI/CD, docker, infrastructure)
    "logging",  # Logging patterns (structured logging, metrics, monitoring)
    "configuration",  # Configuration patterns (env vars, feature flags, settings)
    "uncategorized",  # Fallback category
]


def is_categorization_enabled() -> bool:
    """Check if pattern categorization is enabled."""
    # Categorization requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("PATTERN_CATEGORIZATION_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_categorization_model() -> str:
    """Get the model to use for pattern categorization."""
    return os.environ.get("PATTERN_CATEGORIZER_MODEL", DEFAULT_CATEGORIZATION_MODEL)


# =============================================================================
# Categorization Prompt
# =============================================================================


def _build_categorization_prompt(pattern: str) -> str:
    """Build the prompt for pattern categorization."""
    return f"""Analyze the following code pattern and classify it into ONE of these categories:

CATEGORIES:
- architecture: Architectural patterns (MVC, layering, module structure, separation of concerns)
- testing: Testing patterns (mocking, fixtures, test structure, assertions)
- error-handling: Error handling patterns (try-catch, error boundaries, validation, error messages)
- api-design: API design patterns (REST, GraphQL, endpoints, routing, request/response handling)
- state-management: State management patterns (Redux, Context, local state, data flow)
- security: Security patterns (auth, permissions, validation, sanitization, encryption)
- performance: Performance patterns (caching, optimization, lazy loading, debouncing)
- data-access: Data access patterns (ORM, queries, repositories, database interactions)
- ui-patterns: UI patterns (components, layouts, forms, rendering)
- integration: Integration patterns (third-party APIs, webhooks, events, external services)
- deployment: Deployment patterns (CI/CD, docker, infrastructure, environment setup)
- logging: Logging patterns (structured logging, metrics, monitoring, debugging)
- configuration: Configuration patterns (env vars, feature flags, settings management)
- uncategorized: If none of the above categories fit

PATTERN TO CATEGORIZE:
{pattern}

Respond with ONLY valid JSON in this exact format:
{{
  "category": "category-name",
  "confidence": 0.95,
  "reasoning": "Brief explanation of why this category fits"
}}

Choose the MOST specific category that fits. Use "uncategorized" only if no other category applies.
"""


# =============================================================================
# LLM Categorization
# =============================================================================


async def run_pattern_categorization(
    pattern: str, project_dir: Path | None = None
) -> dict | None:
    """
    Run pattern categorization using Claude Agent SDK.

    Args:
        pattern: Pattern description to categorize
        project_dir: Project directory for SDK context (optional)

    Returns:
        Categorization result dict or None if failed
    """
    if not SDK_AVAILABLE:
        logger.warning("Claude SDK not available, skipping pattern categorization")
        return None

    if not get_auth_token():
        logger.warning("No authentication token found, skipping pattern categorization")
        return None

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = get_categorization_model()
    prompt = _build_categorization_prompt(pattern)

    # Use current directory if project_dir not specified
    cwd = str(project_dir.resolve()) if project_dir else os.getcwd()

    try:
        # Use simple_client for pattern categorization
        from pathlib import Path

        from core.simple_client import create_simple_client

        client = create_simple_client(
            agent_type="pattern_categorizer",
            model=model,
            system_prompt=(
                "You are an expert code pattern analyst. You categorize code patterns accurately. "
                "Always respond with valid JSON only, no markdown formatting or explanations."
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
                f"Pattern categorization response: {message_count} messages, "
                f"{text_blocks_found} text blocks, {len(response_text)} chars collected"
            )

            # Validate we received content before parsing
            if not response_text.strip():
                logger.warning(
                    f"Pattern categorization returned empty response. "
                    f"Messages received: {message_count}, TextBlocks found: {text_blocks_found}. "
                    f"This may indicate the AI model did not respond with text content."
                )
                return None

        # Parse JSON from response
        return parse_categorization(response_text)

    except Exception as e:
        logger.warning(f"Pattern categorization failed: {e}")
        return None


def parse_categorization(response_text: str) -> dict | None:
    """
    Parse the LLM response into a categorization result.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed categorization dict or None if parsing failed
    """
    # Try to extract JSON from the response
    text = response_text.strip()

    # Early validation - check for empty response
    if not text:
        logger.warning("Cannot parse categorization: response text is empty")
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
                "Cannot parse categorization: response contained only markdown code block markers with no content"
            )
            return None

    try:
        result = json.loads(text)

        # Validate structure
        if not isinstance(result, dict):
            logger.warning(
                f"Categorization result is not a dict, got type: {type(result).__name__}"
            )
            return None

        # Validate required fields
        if "category" not in result:
            logger.warning("Categorization result missing 'category' field")
            return None

        # Validate category is in allowed list
        category = result["category"]
        if category not in PATTERN_CATEGORIES:
            logger.warning(
                f"Unknown category '{category}', defaulting to 'uncategorized'"
            )
            result["category"] = "uncategorized"

        # Ensure optional fields exist with defaults
        result.setdefault("confidence", 0.5)
        result.setdefault("reasoning", "")

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse categorization JSON: {e}")
        # Show more context in the error message
        preview_length = min(500, len(text))
        logger.warning(
            f"Response text preview (first {preview_length} chars): {text[:preview_length]}"
        )
        if len(text) > preview_length:
            logger.warning(f"... (total length: {len(text)} chars)")
        return None


# =============================================================================
# Main Entry Point
# =============================================================================


async def categorize_pattern(pattern: str, project_dir: Path | None = None) -> dict:
    """
    Categorize a code pattern using AI-based classification.

    This is the main entry point for pattern categorization.
    Falls back to "uncategorized" if categorization fails.

    Args:
        pattern: Pattern description to categorize
        project_dir: Project root directory (optional)

    Returns:
        Dict with category, confidence, and reasoning:
        {
            "category": "architecture",
            "confidence": 0.95,
            "reasoning": "Pattern describes component structure"
        }
    """
    # Check if categorization is enabled
    if not is_categorization_enabled():
        logger.info("Pattern categorization disabled")
        return _get_default_category()

    # Validate input
    if not pattern or not pattern.strip():
        logger.warning("Empty pattern provided, using default category")
        return _get_default_category()

    try:
        # Run categorization
        result = await run_pattern_categorization(pattern, project_dir=project_dir)

        if result:
            logger.info(
                f"Categorized pattern as '{result['category']}' "
                f"(confidence: {result.get('confidence', 0.0):.2f})"
            )
            return result
        else:
            logger.warning("Categorization returned no results, using default category")
            return _get_default_category()

    except Exception as e:
        logger.warning(f"Pattern categorization failed: {e}, using default category")
        return _get_default_category()


def _get_default_category() -> dict:
    """Return default categorization when classification fails or is disabled."""
    return {
        "category": "uncategorized",
        "confidence": 0.0,
        "reasoning": "Categorization disabled or failed",
    }


def get_pattern_categories() -> list[str]:
    """
    Get the list of available pattern categories.

    Returns:
        List of category names
    """
    return PATTERN_CATEGORIES.copy()


# =============================================================================
# Synchronous Wrapper
# =============================================================================


def categorize_pattern_sync(pattern: str, project_dir: Path | None = None) -> dict:
    """
    Synchronous wrapper for categorize_pattern.

    Args:
        pattern: Pattern description to categorize
        project_dir: Project root directory (optional)

    Returns:
        Dict with category, confidence, and reasoning
    """
    try:
        return asyncio.run(categorize_pattern(pattern, project_dir))
    except Exception as e:
        logger.warning(f"Pattern categorization failed: {e}")
        return _get_default_category()


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test pattern categorization")
    parser.add_argument(
        "--pattern",
        type=str,
        required=True,
        help="Pattern description to categorize",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        help="Project directory",
    )

    args = parser.parse_args()

    async def main():
        result = await categorize_pattern(
            pattern=args.pattern,
            project_dir=args.project_dir,
        )
        print(json.dumps(result, indent=2))

    asyncio.run(main())
