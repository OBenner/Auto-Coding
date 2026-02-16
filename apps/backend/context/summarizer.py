"""
Context Summarization for Context Window Optimization
======================================================

Intelligently summarizes context content to maintain coherence across long sessions
while reducing token usage. Uses Claude SDK for high-quality summarization.

Components:
- ContextSummarizer: Main class for context summarization operations
- Configurable summarization levels (light, medium, aggressive)
- Intelligent summarization for files, conversations, and code snippets

Usage:
    # Create summarizer
    summarizer = ContextSummarizer()

    # Summarize file content
    summary = await summarizer.summarize_file_content(
        file_path="apps/backend/core/client.py",
        content=file_content
    )

    # Summarize conversation history
    summary = await summarizer.summarize_conversation(
        messages=conversation_messages,
        max_words=500
    )

    # Batch summarize multiple files
    summaries = await summarizer.summarize_batch(
        files=[{"path": "file1.py", "content": "..."}, ...]
    )
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from core.auth import require_auth_token
from core.simple_client import create_simple_client

logger = logging.getLogger(__name__)

_TRUNCATION_MARKER = "\n\n[... truncated ...]"


class SummarizationLevel(Enum):
    """
    Configurable summarization levels for context optimization.

    Each level defines a target word count and compression strategy:
    - LIGHT: Preserves more detail (800 words) - good for complex code
    - MEDIUM: Balanced summarization (400 words) - default for most files
    - AGGRESSIVE: Maximum compression (150 words) - for token-constrained contexts
    """

    LIGHT = "light"
    MEDIUM = "medium"
    AGGRESSIVE = "aggressive"

    @property
    def target_words(self) -> int:
        """Return the target word count for this summarization level."""
        word_counts = {
            SummarizationLevel.LIGHT: 800,
            SummarizationLevel.MEDIUM: 400,
            SummarizationLevel.AGGRESSIVE: 150,
        }
        return word_counts[self]

    @property
    def max_input_chars(self) -> int:
        """Return the maximum input characters for this summarization level."""
        char_limits = {
            SummarizationLevel.LIGHT: 20000,
            SummarizationLevel.MEDIUM: 15000,
            SummarizationLevel.AGGRESSIVE: 10000,
        }
        return char_limits[self]


async def _extract_response_text(client) -> str:
    """Send a query via the client and extract the text from the response."""
    response_text = ""
    async for msg in client.receive_response():
        msg_type = type(msg).__name__
        if msg_type != "AssistantMessage" or not hasattr(msg, "content"):
            continue
        for block in msg.content:
            if type(block).__name__ == "TextBlock" and hasattr(block, "text"):
                response_text += block.text
    return response_text.strip()


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, appending a marker if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + _TRUNCATION_MARKER


class ContextSummarizer:
    """
    Summarizes context content to optimize token usage while maintaining coherence.

    Provides intelligent summarization of files, conversations, and code snippets
    using Claude SDK for high-quality results.

    Args:
        model: Model to use for summarization (defaults to Haiku for efficiency)
        default_level: Default summarization level
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        default_level: SummarizationLevel = SummarizationLevel.MEDIUM,
    ):
        """Initialize summarizer with configuration."""
        self.model = model
        self.default_level = default_level

    async def summarize_file_content(
        self,
        file_path: str,
        content: str,
        level: SummarizationLevel | None = None,
        preserve_imports: bool = True,
    ) -> str:
        """
        Summarize file content to reduce token usage.

        Preserves critical information like function signatures, class definitions,
        and key logic while removing verbose implementations.

        Args:
            file_path: Path to the file (for context)
            content: File content to summarize
            level: Summarization level (defaults to instance default)
            preserve_imports: Whether to preserve import statements

        Returns:
            Summarized file content

        Example:
            >>> summarizer = ContextSummarizer()
            >>> summary = await summarizer.summarize_file_content(
            ...     "apps/backend/core/client.py",
            ...     file_content
            ... )
        """
        # Validate auth token
        require_auth_token()

        # Determine summarization level
        level = level or self.default_level
        target_words = level.target_words
        max_input_chars = level.max_input_chars

        # Truncate input if needed
        if len(content) > max_input_chars:
            truncated_content = (
                content[:max_input_chars]
                + "\n\n[... content truncated for summarization ...]"
            )
        else:
            truncated_content = content

        # Build prompt
        preserve_note = (
            "\n- Preserve all import statements at the top" if preserve_imports else ""
        )

        prompt = f"""Summarize the following code file in {target_words} words or less.

Focus on:
- Main purpose and functionality
- Key classes, functions, and their signatures
- Important patterns and design decisions
- Critical dependencies and integrations{preserve_note}
- Notable implementation details

Skip verbose implementations, comments, and boilerplate.

## File: {file_path}
```
{truncated_content}
```

## Summary:
"""

        client = create_simple_client(
            agent_type="context_summary",
            model=self.model,
            system_prompt=(
                "You are a technical code summarizer. Extract key information "
                "from code files while preserving critical details like signatures, "
                "class definitions, and important logic. Be concise and technical."
            ),
        )

        try:
            async with client:
                await client.query(prompt)
                return await _extract_response_text(client)
        except Exception as e:
            logger.warning(f"File summarization failed for {file_path}: {e}")
            fallback = _truncate(content, 2000)
            return f"[Summarization failed: {e}]\n\n{fallback}"

    async def summarize_conversation(
        self,
        messages: list[dict[str, Any]],
        max_words: int = 500,
    ) -> str:
        """
        Summarize conversation history to maintain session coherence.

        Extracts key decisions, findings, and action items from conversation
        history to provide context for continued work.

        Args:
            messages: List of conversation messages
            max_words: Maximum words in summary

        Returns:
            Summarized conversation context

        Example:
            >>> summarizer = ContextSummarizer()
            >>> summary = await summarizer.summarize_conversation(
            ...     messages=[
            ...         {"role": "user", "content": "Implement feature X"},
            ...         {"role": "assistant", "content": "..."}
            ...     ]
            ... )
        """
        # Validate auth token
        require_auth_token()

        # Format conversation for summarization
        conversation_text = []
        for msg in messages[-20:]:  # Last 20 messages only
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                conversation_text.append(f"**{role.upper()}**: {content[:1000]}")

        formatted_conversation = "\n\n".join(conversation_text)

        # Truncate if too long
        formatted_conversation = _truncate(formatted_conversation, 10000)

        prompt = f"""Summarize the following conversation in {max_words} words or less.

Focus on:
- Key decisions made and their rationale
- Important findings and discoveries
- Action items and implementation progress
- Critical issues or blockers encountered
- Recommendations for next steps

Be concise and use bullet points. Skip greetings and meta-commentary.

## Conversation:
{formatted_conversation}

## Summary:
"""

        client = create_simple_client(
            agent_type="context_summary",
            model=self.model,
            system_prompt=(
                "You are a concise conversation summarizer. Extract key decisions, "
                "findings, and action items. Use bullet points. Focus on technical "
                "content and skip pleasantries."
            ),
        )

        try:
            async with client:
                await client.query(prompt)
                return await _extract_response_text(client)
        except Exception as e:
            logger.warning(f"Conversation summarization failed: {e}")
            fallback = formatted_conversation[:1000]
            return f"[Summarization failed: {e}]\n\n{fallback}"

    async def summarize_batch(
        self,
        files: list[dict[str, str]],
        level: SummarizationLevel | None = None,
    ) -> list[dict[str, str]]:
        """
        Summarize multiple files in batch.

        Args:
            files: List of file dicts with 'path' and 'content' keys
            level: Summarization level (defaults to instance default)

        Returns:
            List of file dicts with 'path', 'content', and 'summary' keys

        Example:
            >>> summarizer = ContextSummarizer()
            >>> summaries = await summarizer.summarize_batch([
            ...     {"path": "file1.py", "content": "..."},
            ...     {"path": "file2.py", "content": "..."}
            ... ])
        """
        results = []

        for file_dict in files:
            file_path = file_dict.get("path", "unknown")
            content = file_dict.get("content", "")

            if not content:
                results.append(
                    {
                        "path": file_path,
                        "content": content,
                        "summary": "[Empty file]",
                    }
                )
                continue

            try:
                summary = await self.summarize_file_content(
                    file_path=file_path,
                    content=content,
                    level=level,
                )
                results.append(
                    {
                        "path": file_path,
                        "content": content,
                        "summary": summary,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to summarize {file_path}: {e}")
                results.append(
                    {
                        "path": file_path,
                        "content": content,
                        "summary": f"[Summarization failed: {e}]",
                    }
                )

        return results

    async def summarize_code_snippet(
        self,
        code: str,
        language: str | None = None,
        max_words: int = 200,
    ) -> str:
        """
        Summarize a code snippet to extract key functionality.

        Args:
            code: Code snippet to summarize
            language: Programming language (optional)
            max_words: Maximum words in summary

        Returns:
            Summarized code description

        Example:
            >>> summarizer = ContextSummarizer()
            >>> summary = await summarizer.summarize_code_snippet(
            ...     code="def foo(): return 42",
            ...     language="python"
            ... )
        """
        # Validate auth token
        require_auth_token()

        # Truncate if too long
        truncated_code = _truncate(code, 5000)

        lang_note = f" ({language})" if language else ""

        prompt = f"""Summarize the following code snippet{lang_note} in {max_words} words or less.

Focus on:
- What the code does (functionality)
- Key algorithms or patterns used
- Important inputs/outputs
- Notable edge cases or error handling

Be concise and technical.

## Code:
```
{truncated_code}
```

## Summary:
"""

        client = create_simple_client(
            agent_type="context_summary",
            model=self.model,
            system_prompt=(
                "You are a code analysis expert. Summarize code snippets concisely, "
                "focusing on functionality, patterns, and key implementation details."
            ),
        )

        try:
            async with client:
                await client.query(prompt)
                return await _extract_response_text(client)
        except Exception as e:
            logger.warning(f"Code snippet summarization failed: {e}")
            fallback = _truncate(code, 500)
            return f"[Summarization failed: {e}]\n\n{fallback}"


def get_context_summarizer(
    model: str = "claude-haiku-4-5-20251001",
    default_level: SummarizationLevel = SummarizationLevel.MEDIUM,
) -> ContextSummarizer:
    """
    Factory function to create a ContextSummarizer instance.

    Args:
        model: Model to use for summarization
        default_level: Default summarization level

    Returns:
        Configured ContextSummarizer instance

    Example:
        >>> summarizer = get_context_summarizer(
        ...     model="claude-haiku-4-5-20251001",
        ...     default_level=SummarizationLevel.LIGHT
        ... )
    """
    return ContextSummarizer(model=model, default_level=default_level)
