"""
Token Counting Utility for Context Window Management
=====================================================

Provides accurate token counting using tiktoken for various LLM models.
Used to optimize context window usage and track token budgets.

Components:
- TokenCounter: Main class for counting tokens across different encodings
- Encoding support: cl100k_base (Claude, GPT-4), p50k_base (GPT-3), etc.

Usage:
    # Create counter (uses cl100k_base by default for Claude models)
    counter = TokenCounter()

    # Count tokens in a string
    token_count = counter.count_tokens("Hello, world!")

    # Count tokens with specific model encoding
    counter = TokenCounter(model="gpt-3.5-turbo")
    token_count = counter.count_tokens("Some text")

    # Count tokens for multiple strings
    total = counter.count_tokens_batch(["text1", "text2", "text3"])
"""

from __future__ import annotations

from typing import Any

try:
    import tiktoken
except ImportError:
    tiktoken = None


# Model to encoding mapping
# Based on tiktoken documentation
MODEL_ENCODINGS: dict[str, str] = {
    # Claude models use cl100k_base encoding
    "claude-opus-4-5-20251101": "cl100k_base",
    "claude-sonnet-4-5-20250929": "cl100k_base",
    "claude-haiku-4-5-20251001": "cl100k_base",
    "claude-sonnet-4-5-20250929-thinking": "cl100k_base",
    "claude-opus-4-5-20251101-thinking": "cl100k_base",
    # GPT-4 models
    "gpt-4": "cl100k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-4o": "cl100k_base",
    # GPT-3.5 models
    "gpt-3.5-turbo": "cl100k_base",
    # Older models
    "text-davinci-003": "p50k_base",
    "text-davinci-002": "p50k_base",
    # Default encoding
    "default": "cl100k_base",
}


class TokenCounter:
    """
    Count tokens for LLM inputs using tiktoken.

    Provides accurate token counting for context window management
    and cost estimation. Supports multiple model encodings.

    Args:
        model: Model identifier (defaults to cl100k_base encoding)
        encoding_name: Override encoding (e.g., "cl100k_base", "p50k_base")

    Raises:
        ImportError: If tiktoken is not installed
        ValueError: If encoding cannot be loaded
    """

    def __init__(
        self,
        model: str | None = None,
        encoding_name: str | None = None,
    ):
        """Initialize token counter with specified encoding."""
        if tiktoken is None:
            raise ImportError(
                "tiktoken is required for token counting. "
                "Install it with: pip install tiktoken"
            )

        # Determine encoding to use
        if encoding_name:
            self._encoding_name = encoding_name
        elif model:
            self._encoding_name = MODEL_ENCODINGS.get(
                model, MODEL_ENCODINGS["default"]
            )
        else:
            self._encoding_name = MODEL_ENCODINGS["default"]

        # Load encoding
        try:
            self._encoding = tiktoken.get_encoding(self._encoding_name)
        except Exception as e:
            raise ValueError(
                f"Failed to load encoding '{self._encoding_name}': {e}"
            ) from e

    @property
    def encoding_name(self) -> str:
        """Get the name of the current encoding."""
        return self._encoding_name

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Input text to tokenize

        Returns:
            Number of tokens in the text

        Example:
            >>> counter = TokenCounter()
            >>> counter.count_tokens("Hello, world!")
            4
        """
        if not text:
            return 0

        try:
            tokens = self._encoding.encode(text)
            return len(tokens)
        except Exception:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4

    def count_tokens_batch(self, texts: list[str]) -> int:
        """
        Count tokens across multiple text strings.

        Args:
            texts: List of text strings to tokenize

        Returns:
            Total number of tokens across all texts

        Example:
            >>> counter = TokenCounter()
            >>> counter.count_tokens_batch(["Hello", "world"])
            3
        """
        return sum(self.count_tokens(text) for text in texts)

    def count_tokens_dict(self, data: dict[str, Any]) -> int:
        """
        Count tokens in a dictionary of values.

        Recursively counts tokens in string values, handling nested
        dictionaries and lists.

        Args:
            data: Dictionary containing text values

        Returns:
            Total number of tokens in all string values

        Example:
            >>> counter = TokenCounter()
            >>> counter.count_tokens_dict({"key": "value", "nested": {"text": "more"}})
            4
        """
        total = 0

        for value in data.values():
            if isinstance(value, str):
                total += self.count_tokens(value)
            elif isinstance(value, dict):
                total += self.count_tokens_dict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        total += self.count_tokens(item)
                    elif isinstance(item, dict):
                        total += self.count_tokens_dict(item)

        return total

    def estimate_cost(
        self,
        text: str,
        input_price_per_million: float,
    ) -> float:
        """
        Estimate cost for processing text.

        Args:
            text: Input text
            input_price_per_million: Price per 1M tokens

        Returns:
            Estimated cost in dollars

        Example:
            >>> counter = TokenCounter()
            >>> counter.estimate_cost("Hello world", 3.0)  # $3 per 1M tokens
            0.00001
        """
        tokens = self.count_tokens(text)
        return (tokens / 1_000_000) * input_price_per_million

    def truncate_to_limit(
        self,
        text: str,
        max_tokens: int,
    ) -> str:
        """
        Truncate text to fit within token limit.

        Args:
            text: Input text
            max_tokens: Maximum number of tokens

        Returns:
            Truncated text that fits within the token limit

        Example:
            >>> counter = TokenCounter()
            >>> counter.truncate_to_limit("Very long text...", 10)
            'Very long...'
        """
        if not text:
            return text

        # Check if already within limit
        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text

        # Encode and truncate
        try:
            tokens = self._encoding.encode(text)
            truncated_tokens = tokens[:max_tokens]
            return self._encoding.decode(truncated_tokens)
        except Exception:
            # Fallback: character-based truncation (rough estimate)
            estimated_chars = max_tokens * 4
            return text[:estimated_chars]


def get_token_counter(
    model: str | None = None,
    encoding_name: str | None = None,
) -> TokenCounter:
    """
    Factory function to create a TokenCounter instance.

    Args:
        model: Model identifier
        encoding_name: Override encoding name

    Returns:
        Configured TokenCounter instance

    Example:
        >>> counter = get_token_counter(model="claude-sonnet-4-5-20250929")
        >>> tokens = counter.count_tokens("Hello")
    """
    return TokenCounter(model=model, encoding_name=encoding_name)
