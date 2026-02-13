"""
Context Compressor
==================

Intelligent compression for large files using AI summarization.

This module provides the ContextCompressor class that uses Claude
to summarize large files, extract key sections, and reduce token usage
while preserving important information.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from context.token_estimator import TokenEstimator

logger = logging.getLogger(__name__)


# Default compression thresholds (in tokens)
DEFAULT_COMPRESSION_THRESHOLD = 2000  # Compress files over 2K tokens
TARGET_COMPRESSION_RATIO = 0.4  # Target 40% of original size


@dataclass
class CompressionResult:
    """Result of compressing a file."""

    original_content: str
    compressed_content: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float  # compressed / original
    method: str  # "summary", "key_sections", "none"


class ContextCompressor:
    """
    Intelligent context compression using AI summarization.

    Provides methods to compress large files by generating summaries,
    extracting key sections, and removing redundant content while
    preserving important information.
    """

    def __init__(
        self,
        compression_threshold: int = DEFAULT_COMPRESSION_THRESHOLD,
        target_ratio: float = TARGET_COMPRESSION_RATIO,
        token_estimator: TokenEstimator | None = None,
    ) -> None:
        """
        Initialize the context compressor.

        Args:
            compression_threshold: Token threshold for triggering compression
            target_ratio: Target compression ratio (compressed / original)
            token_estimator: Optional TokenEstimator instance
        """
        self.compression_threshold = compression_threshold
        self.target_ratio = target_ratio
        self.token_estimator = token_estimator or TokenEstimator()

    def compress_file(
        self,
        file_path: str | Path,
        strategy: str = "auto",
    ) -> CompressionResult:
        """
        Compress a file synchronously.

        This is a convenience wrapper for CLI / non-async callers.
        Call ``compress_file_async`` instead when already inside an event loop.

        Args:
            file_path: Path to the file to compress
            strategy: Compression strategy ("summary", "key_sections", "auto")

        Returns:
            CompressionResult with original and compressed content

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
        """
        try:
            asyncio.get_running_loop()
            # Already in an event loop - cannot use asyncio.run()
            raise RuntimeError(
                "compress_file() cannot be called from an async context. "
                "Use 'await compress_file_async()' instead."
            )
        except RuntimeError as e:
            if "compress_file()" in str(e):
                raise
            # No running loop - safe to create one
            return asyncio.run(self.compress_file_async(file_path, strategy))

    async def compress_file_async(
        self,
        file_path: str | Path,
        strategy: str = "auto",
    ) -> CompressionResult:
        """
        Compress a file using AI summarization.

        Args:
            file_path: Path to the file to compress
            strategy: Compression strategy ("summary", "key_sections", "auto")

        Returns:
            CompressionResult with original and compressed content

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Guard against extremely large files to avoid OOM
        max_bytes = 5 * 1024 * 1024  # 5 MB
        try:
            size = path.stat().st_size
        except OSError as e:
            raise OSError(f"Failed to stat file {file_path}: {e}")

        if size > max_bytes:
            raise OSError(
                f"File {file_path} is too large to compress ({size} bytes > {max_bytes} bytes). "
                "Consider splitting the file or using a streaming strategy."
            )

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise OSError(f"Failed to read file {file_path}: {e}")

        # Count tokens
        original_tokens = self.token_estimator.count_tokens(content)

        # Check if compression is needed
        if original_tokens <= self.compression_threshold:
            logger.debug(
                f"File {file_path} ({original_tokens} tokens) below threshold, "
                "not compressing"
            )
            return CompressionResult(
                original_content=content,
                compressed_content=content,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                method="none",
            )

        # Determine strategy
        if strategy == "auto":
            # Use summary for very large files, key sections for moderately large
            strategy = "summary" if original_tokens > 5000 else "key_sections"

        # Apply compression
        if strategy == "summary":
            result = await self._summarize_content(content, file_path)
        elif strategy == "key_sections":
            result = await self._extract_key_sections(content, file_path)
        else:
            logger.warning(f"Unknown strategy: {strategy}, using summary")
            result = await self._summarize_content(content, file_path)

        return result

    async def _summarize_content(
        self,
        content: str,
        file_path: str | Path,
    ) -> CompressionResult:
        """
        Summarize content using AI.

        Args:
            content: The content to summarize
            file_path: Path to the file (for context)

        Returns:
            CompressionResult with summarized content
        """
        original_tokens = self.token_estimator.count_tokens(content)

        # Build summarization prompt
        target_tokens = int(original_tokens * self.target_ratio)
        prompt = self._build_summary_prompt(content, file_path, target_tokens)

        # Call Claude SDK
        try:
            summary = await self._call_claude_for_summary(prompt)
        except Exception as e:
            logger.warning(f"Summarization failed for {file_path}: {e}")
            # Fallback: truncate content
            summary = self._truncate_content(content, target_tokens)

        compressed_tokens = self.token_estimator.count_tokens(summary)
        compression_ratio = (
            compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        )

        return CompressionResult(
            original_content=content,
            compressed_content=summary,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            method="summary",
        )

    async def _extract_key_sections(
        self,
        content: str,
        file_path: str | Path,
    ) -> CompressionResult:
        """
        Extract key sections from content using AI.

        Args:
            content: The content to process
            file_path: Path to the file (for context)

        Returns:
            CompressionResult with key sections
        """
        original_tokens = self.token_estimator.count_tokens(content)

        # Build extraction prompt
        target_tokens = int(original_tokens * self.target_ratio)
        prompt = self._build_extraction_prompt(content, file_path, target_tokens)

        # Call Claude SDK
        try:
            extracted = await self._call_claude_for_summary(prompt)
        except Exception as e:
            logger.warning(f"Key section extraction failed for {file_path}: {e}")
            # Fallback: truncate content
            extracted = self._truncate_content(content, target_tokens)

        compressed_tokens = self.token_estimator.count_tokens(extracted)
        compression_ratio = (
            compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        )

        return CompressionResult(
            original_content=content,
            compressed_content=extracted,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            method="key_sections",
        )

    @staticmethod
    def _sanitize_for_code_fence(content: str) -> str:
        """Escape triple backticks in content to avoid breaking code fences."""
        return content.replace("```", "`\u200b``")

    def _build_summary_prompt(
        self,
        content: str,
        file_path: str | Path,
        target_tokens: int,
    ) -> str:
        """
        Build a prompt for file summarization.

        Args:
            content: The content to summarize
            file_path: Path to the file (for context)
            target_tokens: Target token count for summary

        Returns:
            Prompt string for Claude
        """
        original_tokens = self.token_estimator.count_tokens(content)
        safe_content = self._sanitize_for_code_fence(content)

        return f"""Summarize the following file to reduce it from {original_tokens} tokens to approximately {target_tokens} tokens (about {int(self.target_ratio * 100)}% of original size).

File path: {file_path}

Requirements:
- Preserve the core purpose and functionality
- Keep key class/function definitions and signatures
- Maintain important logic and algorithms
- Remove redundant comments, examples, and boilerplate
- Focus on what the code DOES, not implementation details
- Use concise language

Content to summarize:
```
{safe_content}
```

Provide ONLY the summarized content, no explanations."""

    def _build_extraction_prompt(
        self,
        content: str,
        file_path: str | Path,
        target_tokens: int,
    ) -> str:
        """
        Build a prompt for key section extraction.

        Args:
            content: The content to process
            file_path: Path to the file (for context)
            target_tokens: Target token count for extracted sections

        Returns:
            Prompt string for Claude
        """
        original_tokens = self.token_estimator.count_tokens(content)
        safe_content = self._sanitize_for_code_fence(content)

        return f"""Extract the most important sections from this file to reduce it from {original_tokens} tokens to approximately {target_tokens} tokens (about {int(self.target_ratio * 100)}% of original size).

File path: {file_path}

Requirements:
- Extract key classes, functions, and methods
- Include important imports and dependencies
- Preserve critical logic and data structures
- Skip tests, examples, and non-essential code
- Maintain code structure and readability
- DO NOT rewrite or refactor - just extract

Content:
```
{safe_content}
```

Provide ONLY the extracted sections, no explanations."""

    async def _call_claude_for_summary(
        self, prompt: str, *, timeout: float = 60.0
    ) -> str:
        """
        Call Claude SDK to generate a summary with timeout.

        Args:
            prompt: The prompt to send to Claude
            timeout: Maximum seconds to wait for a response

        Returns:
            Generated summary text

        Raises:
            RuntimeError: If Claude SDK call fails after retries
        """
        from core.simple_client import create_simple_client

        # Use Haiku for fast/cheap summarization
        client = create_simple_client(
            agent_type="merge_resolver",  # Text-only, no tools needed
            model="claude-haiku-4-5-20251001",
            max_turns=1,
        )

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                async with client:
                    await asyncio.wait_for(client.query(prompt), timeout=timeout)

                    response_text = ""
                    async for msg in client.receive_response():
                        msg_type = type(msg).__name__
                        if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                            for block in msg.content:
                                block_type = type(block).__name__
                                if block_type == "TextBlock" and hasattr(block, "text"):
                                    response_text += block.text

                    return response_text.strip()

            except TimeoutError:
                last_error = TimeoutError(
                    f"Claude summarization timed out (attempt {attempt})"
                )
                logger.warning("Claude summarization timed out on attempt %s", attempt)
            except Exception as e:
                last_error = e
                logger.warning("Claude SDK call failed on attempt %s: %s", attempt, e)

            await asyncio.sleep(min(2 * attempt, 10))

        logger.error("Claude SDK call failed after 3 attempts: %s", last_error)
        raise RuntimeError(f"Failed to generate summary: {last_error}")

    def _truncate_content(self, content: str, target_tokens: int) -> str:
        """
        Fallback: truncate content to target token count.

        Args:
            content: The content to truncate
            target_tokens: Target token count

        Returns:
            Truncated content
        """
        lines = content.split("\n")
        result_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = self.token_estimator.count_tokens(line + "\n")
            if current_tokens + line_tokens > target_tokens:
                break
            result_lines.append(line)
            current_tokens += line_tokens

        truncated = "\n".join(result_lines)
        if len(truncated) < len(content):
            truncated += f"\n\n... (truncated to {target_tokens} tokens)"

        return truncated

    def compress_text(
        self,
        text: str,
        context_hint: str = "code snippet",
    ) -> CompressionResult:
        """
        Compress a text string (not from a file).

        Args:
            text: The text to compress
            context_hint: Hint about what the text is (for summarization)

        Returns:
            CompressionResult with compressed text
        """
        original_tokens = self.token_estimator.count_tokens(text)

        if original_tokens <= self.compression_threshold:
            return CompressionResult(
                original_content=text,
                compressed_content=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                method="none",
            )

        # For text snippets, use truncation for simplicity
        target_tokens = int(original_tokens * self.target_ratio)
        compressed = self._truncate_content(text, target_tokens)
        compressed_tokens = self.token_estimator.count_tokens(compressed)

        return CompressionResult(
            original_content=text,
            compressed_content=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens,
            method="summary",
        )
