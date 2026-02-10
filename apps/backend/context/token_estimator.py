"""
Token Estimator
================

Accurate token counting for files and text using tiktoken.

This module provides the TokenEstimator class that uses tiktoken
to accurately count tokens in text and files, with fallback
to character-based estimation when tiktoken is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tiktoken import Encoding

# Default encoding for Claude (claudetk or cl100k_base as fallback)
DEFAULT_ENCODING = "cl100k_base"


@dataclass
class TokenEstimator:
    """
    Accurate token counting using tiktoken.

    Provides methods to count tokens in text and files,
    with fallback to character-based estimation when
    tiktoken is not available.
    """

    encoding_name: str = DEFAULT_ENCODING
    _encoding: Encoding | None = None
    _tiktoken_available: bool = False

    def __post_init__(self) -> None:
        """Initialize tiktoken encoding if available."""
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding(self.encoding_name)
            self._tiktoken_available = True
        except ImportError:
            self._tiktoken_available = False

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0

        if self._tiktoken_available and self._encoding:
            # Use tiktoken for accurate counting
            tokens = self._encoding.encode(text)
            return len(tokens)
        else:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4

    def count_tokens_in_file(self, file_path: str | Path) -> int:
        """
        Count tokens in a file.

        Args:
            file_path: Path to the file

        Returns:
            Number of tokens in the file

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
            return self.count_tokens(content)
        except Exception as e:
            raise IOError(f"Failed to read file {file_path}: {e}")

    def estimate_tokens_for_lines(
        self, lines: list[str] | list[tuple[int, str]]
    ) -> int:
        """
        Estimate tokens for a list of lines.

        Args:
            lines: List of strings or (line_number, content) tuples

        Returns:
            Total number of tokens
        """
        if not lines:
            return 0

        # Extract text content from tuples if needed
        if lines and isinstance(lines[0], tuple):
            text = "\n".join(line[1] if len(line) > 1 else line[0] for line in lines)
        else:
            text = "\n".join(lines)

        return self.count_tokens(text)

    @property
    def is_tiktoken_available(self) -> bool:
        """Check if tiktoken is available."""
        return self._tiktoken_available

    @property
    def encoding(self) -> str:
        """Get the encoding name being used."""
        return self.encoding_name
