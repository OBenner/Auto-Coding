"""
Sentiment Analyzer
==================

Analyzes sentiment of user feedback text to categorize feedback as positive,
negative, or neutral. Used for feedback analytics and improvement tracking.

Uses the Claude Agent SDK (same as the rest of the system) for analysis.
Falls back to neutral sentiment if analysis fails (never blocks feedback recording).
"""

from __future__ import annotations

import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    __import__("claude_agent_sdk")
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from core.auth import ensure_claude_code_oauth_token, get_auth_token

# Default model for sentiment analysis (fast and cheap)
# Note: Using Haiku 4.5 for fast, cheap analysis. Haiku does not support
# extended thinking, so thinking_default is set to "none" in models.py
DEFAULT_SENTIMENT_MODEL = "claude-haiku-4-5-20251001"

# Maximum feedback text length to analyze (avoid context limits)
MAX_FEEDBACK_CHARS = 5000


class Sentiment(str, Enum):
    """Sentiment categories."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SentimentResult(TypedDict):
    """Structured sentiment analysis result."""

    sentiment: str  # "positive", "negative", or "neutral"
    confidence: float  # 0.0 to 1.0
    key_phrases: list[str]  # Important phrases that influenced the sentiment
    category: str  # e.g., "feature_request", "bug_report", "praise", "complaint"
    severity: str | None  # For negative feedback: "low", "medium", "high"


def is_analysis_enabled() -> bool:
    """Check if sentiment analysis is enabled."""
    # Analysis requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("SENTIMENT_ANALYSIS_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_analysis_model() -> str:
    """Get the model to use for sentiment analysis."""
    return os.environ.get("SENTIMENT_ANALYZER_MODEL", DEFAULT_SENTIMENT_MODEL)


# =============================================================================
# Prompt Building
# =============================================================================


def _build_analysis_prompt(feedback_text: str, context: dict | None = None) -> str:
    """
    Build the prompt for sentiment analysis.

    Args:
        feedback_text: User feedback text to analyze
        context: Optional context (task type, agent type, etc.)

    Returns:
        Prompt string for the LLM
    """
    base_prompt = """Analyze the sentiment of the following user feedback.

Output ONLY valid JSON with this exact structure:
{
  "sentiment": "positive" | "negative" | "neutral",
  "confidence": 0.0 to 1.0,
  "key_phrases": ["phrase1", "phrase2"],
  "category": "feature_request" | "bug_report" | "praise" | "complaint" | "suggestion" | "question",
  "severity": "low" | "medium" | "high" | null
}

Guidelines:
- sentiment: Overall tone (positive, negative, or neutral)
- confidence: How confident you are in the sentiment classification (0.0 to 1.0)
- key_phrases: 2-5 important phrases that influenced your decision
- category: Primary category of the feedback
- severity: Only for negative feedback (low/medium/high), null otherwise

---

FEEDBACK TEXT:
"""

    # Truncate if too long
    if len(feedback_text) > MAX_FEEDBACK_CHARS:
        feedback_text = (
            feedback_text[:MAX_FEEDBACK_CHARS]
            + f"\n\n... (truncated, {len(feedback_text)} chars total)"
        )

    prompt = base_prompt + feedback_text

    # Add context if provided
    if context:
        context_str = "\n\n---\n\nCONTEXT:\n"
        if "task_type" in context:
            context_str += f"- Task Type: {context['task_type']}\n"
        if "agent_type" in context:
            context_str += f"- Agent Type: {context['agent_type']}\n"
        if "rating" in context:
            context_str += f"- User Rating: {context['rating']}\n"
        prompt += context_str

    prompt += "\n\n---\n\nOutput ONLY the JSON object, no additional text or markdown."

    return prompt


# =============================================================================
# LLM Analysis
# =============================================================================


async def run_sentiment_analysis(
    feedback_text: str,
    context: dict | None = None,
    project_dir: Path | None = None,
) -> SentimentResult | None:
    """
    Run sentiment analysis using Claude Agent SDK.

    Args:
        feedback_text: User feedback text to analyze
        context: Optional context about the feedback
        project_dir: Project directory for SDK context (optional)

    Returns:
        SentimentResult or None if analysis failed
    """
    if not SDK_AVAILABLE:
        logger.warning("Claude SDK not available, skipping sentiment analysis")
        return None

    if not get_auth_token():
        logger.warning("No authentication token found, skipping sentiment analysis")
        return None

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = get_analysis_model()
    prompt = _build_analysis_prompt(feedback_text, context)

    # Use current directory if project_dir not specified
    cwd = str(project_dir.resolve()) if project_dir else os.getcwd()

    try:
        # Use simple_client for sentiment analysis
        from core.simple_client import create_simple_client

        client = create_simple_client(
            agent_type="sentiment",
            model=model,
            system_prompt=(
                "You are an expert sentiment analyzer. You analyze user feedback to determine sentiment. "
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
                f"Sentiment analysis response: {message_count} messages, "
                f"{text_blocks_found} text blocks, {len(response_text)} chars collected"
            )

            # Validate we received content before parsing
            if not response_text.strip():
                logger.warning(
                    f"Sentiment analysis returned empty response. "
                    f"Messages received: {message_count}, TextBlocks found: {text_blocks_found}. "
                    f"This may indicate the AI model did not respond with text content."
                )
                return None

        # Parse JSON from response
        return parse_sentiment_result(response_text)

    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {e}")
        return None


def parse_sentiment_result(response_text: str) -> SentimentResult | None:
    """
    Parse the LLM response into structured sentiment result.

    Args:
        response_text: Raw LLM response

    Returns:
        SentimentResult or None if parsing failed
    """
    # Try to extract JSON from the response
    text = response_text.strip()

    # Early validation - check for empty response
    if not text:
        logger.warning("Cannot parse sentiment: response text is empty")
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
                "Cannot parse sentiment: response contained only markdown code block markers with no content"
            )
            return None

    try:
        result = json.loads(text)

        # Validate structure
        if not isinstance(result, dict):
            logger.warning(
                f"Sentiment result is not a dict, got type: {type(result).__name__}"
            )
            return None

        # Validate required fields
        if "sentiment" not in result:
            logger.warning("Sentiment result missing required field: sentiment")
            return None

        # Ensure all fields exist with defaults
        result.setdefault("confidence", 0.5)
        result.setdefault("key_phrases", [])
        result.setdefault("category", "general")
        result.setdefault("severity", None)

        # Validate sentiment value
        if result["sentiment"] not in ["positive", "negative", "neutral"]:
            logger.warning(f"Invalid sentiment value: {result['sentiment']}")
            return None

        # Ensure confidence is in valid range
        if not isinstance(result["confidence"], (int, float)):
            result["confidence"] = 0.5
        else:
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

        # Ensure key_phrases is a list
        if not isinstance(result["key_phrases"], list):
            result["key_phrases"] = []

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse sentiment JSON: {e}")
        # Show more context in the error message
        preview_length = min(200, len(text))
        logger.warning(
            f"Response text preview (first {preview_length} chars): {text[:preview_length]}"
        )
        if len(text) > preview_length:
            logger.warning(f"... (total length: {len(text)} chars)")
        return None


# =============================================================================
# Fallback Sentiment
# =============================================================================


def get_neutral_sentiment(reason: str = "analysis_disabled") -> SentimentResult:
    """
    Get a neutral sentiment result as a fallback.

    Args:
        reason: Reason for using neutral sentiment

    Returns:
        Neutral SentimentResult
    """
    logger.debug(f"Using neutral sentiment fallback: {reason}")
    return {
        "sentiment": Sentiment.NEUTRAL,
        "confidence": 0.0,
        "key_phrases": [],
        "category": "general",
        "severity": None,
    }


# =============================================================================
# Main Entry Point
# =============================================================================


async def analyze_sentiment(
    feedback_text: str,
    context: dict | None = None,
    project_dir: Path | None = None,
) -> SentimentResult:
    """
    Analyze sentiment of user feedback text.

    This is the main entry point called from feedback recording.
    Falls back to neutral sentiment if analysis fails.

    Args:
        feedback_text: User feedback text to analyze
        context: Optional context (task_type, agent_type, rating, etc.)
        project_dir: Project directory for SDK context

    Returns:
        SentimentResult (rich if analysis succeeded, neutral if failed)
    """
    # Validate input
    if not feedback_text or not feedback_text.strip():
        logger.debug("Empty feedback text, using neutral sentiment")
        return get_neutral_sentiment("empty_feedback")

    # Check if analysis is enabled
    if not is_analysis_enabled():
        logger.info("Sentiment analysis disabled")
        return get_neutral_sentiment("analysis_disabled")

    try:
        # Run analysis
        result = await run_sentiment_analysis(feedback_text, context, project_dir)

        # Fallback to neutral if analysis failed
        if result is None:
            logger.info("Sentiment analysis failed, using neutral fallback")
            return get_neutral_sentiment("analysis_failed")

        return result

    except Exception as e:
        logger.warning(f"Error during sentiment analysis: {e}")
        return get_neutral_sentiment("error")


# =============================================================================
# Synchronous Wrapper (for non-async contexts)
# =============================================================================


def analyze_sentiment_sync(
    feedback_text: str,
    context: dict | None = None,
    project_dir: Path | None = None,
) -> SentimentResult:
    """
    Synchronous wrapper for analyze_sentiment.

    Args:
        feedback_text: User feedback text to analyze
        context: Optional context (task_type, agent_type, rating, etc.)
        project_dir: Project directory for SDK context

    Returns:
        SentimentResult
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're in an async context already, need to run in a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                analyze_sentiment(feedback_text, context, project_dir),
            )
            return future.result()
    else:
        # No running loop, can use asyncio.run directly
        return asyncio.run(analyze_sentiment(feedback_text, context, project_dir))
