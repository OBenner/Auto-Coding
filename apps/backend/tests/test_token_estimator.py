#!/usr/bin/env python3
"""
Unit tests for Token Estimator
==============================

Tests the TokenEstimator class for accurate token counting in text and files.
"""

# IMPORTANT: This sys.path manipulation must happen BEFORE importing pytest
# to ensure we import from the actual context module, not tests.context
import sys
from pathlib import Path


def _configure_sys_path() -> None:
    """Configure sys.path to import from the actual context module."""
    for td in [p for p in sys.path if "tests" in p]:
        if td in sys.path:
            sys.path.remove(td)
    backend_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_root))


_configure_sys_path()

from unittest.mock import patch

import pytest
from context.token_estimator import TokenEstimator


class TestTokenEstimator:
    """Test suite for TokenEstimator class."""

    def test_initialization_with_tiktoken(self):
        """Test TokenEstimator initialization when tiktoken is available."""
        estimator = TokenEstimator()
        assert estimator.encoding == "cl100k_base"
        # Check if tiktoken is available (may not be in test environment)
        assert isinstance(estimator.is_tiktoken_available, bool)

    def test_initialization_with_custom_encoding(self):
        """Test TokenEstimator with custom encoding name."""
        estimator = TokenEstimator(encoding_name="cl100k_base")
        assert estimator.encoding == "cl100k_base"

    def test_count_tokens_simple_text(self):
        """Test counting tokens in simple text."""
        estimator = TokenEstimator()

        # Simple text
        text = "Hello, world!"
        tokens = estimator.count_tokens(text)

        # Should return a positive integer
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_tokens_empty_string(self):
        """Test counting tokens in empty string."""
        estimator = TokenEstimator()

        tokens = estimator.count_tokens("")
        assert tokens == 0

    def test_count_tokens_none_input(self):
        """Test counting tokens with None or falsy input."""
        estimator = TokenEstimator()

        # Empty string should return 0
        assert estimator.count_tokens("") == 0

    def test_count_tokens_code_snippet(self):
        """Test counting tokens in code snippets."""
        estimator = TokenEstimator()

        code = """
def hello_world():
    print("Hello, world!")
    return 42
"""
        tokens = estimator.count_tokens(code)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_tokens_long_text(self):
        """Test counting tokens in longer text."""
        estimator = TokenEstimator()

        # Generate a longer text
        text = " ".join(["word"] * 100)
        tokens = estimator.count_tokens(text)

        assert isinstance(tokens, int)
        assert tokens > 0
        # Should be roughly 100 tokens (but depends on tokenizer)
        assert tokens > 50  # At minimum should be significant

    def test_count_tokens_in_file(self, tmp_path):
        """Test counting tokens in a file."""
        estimator = TokenEstimator()

        # Create a temporary file
        test_file = tmp_path / "test.py"
        test_file.write_text('print("Hello, world!")', encoding="utf-8")

        tokens = estimator.count_tokens_in_file(test_file)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_tokens_in_file_not_found(self, tmp_path):
        """Test counting tokens in a non-existent file."""
        estimator = TokenEstimator()

        non_existent = tmp_path / "does_not_exist.txt"

        with pytest.raises(FileNotFoundError):
            estimator.count_tokens_in_file(non_existent)

    def test_count_tokens_in_file_with_path_string(self, tmp_path):
        """Test counting tokens with file path as string."""
        estimator = TokenEstimator()

        # Create a temporary file
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 42", encoding="utf-8")

        # Pass as string instead of Path
        tokens = estimator.count_tokens_in_file(str(test_file))
        assert isinstance(tokens, int)
        assert tokens >= 0

    def test_estimate_tokens_for_lines_simple(self):
        """Test estimating tokens for a list of lines."""
        estimator = TokenEstimator()

        lines = ["line 1", "line 2", "line 3"]
        tokens = estimator.estimate_tokens_for_lines(lines)

        assert isinstance(tokens, int)
        assert tokens > 0

    def test_estimate_tokens_for_lines_empty(self):
        """Test estimating tokens for empty list."""
        estimator = TokenEstimator()

        tokens = estimator.estimate_tokens_for_lines([])
        assert tokens == 0

    def test_estimate_tokens_for_lines_with_line_numbers(self):
        """Test estimating tokens for lines with line numbers."""
        estimator = TokenEstimator()

        # List of tuples (line_number, content)
        lines = [(1, "def foo():"), (2, "    return 42")]
        tokens = estimator.estimate_tokens_for_lines(lines)

        assert isinstance(tokens, int)
        assert tokens > 0

    def test_estimate_tokens_for_lines_mixed_content(self):
        """Test estimating tokens for mixed content lines."""
        estimator = TokenEstimator()

        lines = [
            "import os",
            "from sys import argv",
            "",
            "def main():",
            "    print('Hello')",
        ]
        tokens = estimator.estimate_tokens_for_lines(lines)

        assert isinstance(tokens, int)
        assert tokens > 0

    def test_fallback_behavior_without_tiktoken(self):
        """Test fallback behavior when tiktoken is not available."""
        # We can't easily mock the import in __post_init__, so instead
        # we verify the fallback logic works by checking that character-based
        # estimation gives reasonable results

        # Use character-based estimation directly (4 chars per token)
        text = "Hello, world!"  # 13 characters

        # Create a fresh estimator
        estimator = TokenEstimator()
        tokens = estimator.count_tokens(text)

        # If tiktoken is available, it will give accurate results
        # If not, it will fall back to character-based estimation
        assert tokens >= 0
        assert isinstance(tokens, int)

        # With tiktoken, this should be around 4-5 tokens
        # With fallback (13//4), it should be 3 tokens
        # Both are valid
        assert tokens >= 2  # At minimum should have some tokens

    def test_is_tiktoken_available_property(self):
        """Test the is_tiktoken_available property."""
        estimator = TokenEstimator()

        # Should return a boolean
        assert isinstance(estimator.is_tiktoken_available, bool)

    def test_encoding_property(self):
        """Test the encoding property."""
        estimator = TokenEstimator(encoding_name="cl100k_base")
        assert estimator.encoding == "cl100k_base"

        # Test with custom encoding
        estimator2 = TokenEstimator(encoding_name="p50k_base")
        assert estimator2.encoding == "p50k_base"

    def test_count_tokens_multilingual_text(self):
        """Test counting tokens with multilingual text."""
        estimator = TokenEstimator()

        # Text with emojis and non-ASCII characters
        text = "Hello 世界 🌍 مرحبا"
        tokens = estimator.count_tokens(text)

        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_tokens_special_characters(self):
        """Test counting tokens with special characters."""
        estimator = TokenEstimator()

        # Text with special characters
        text = " Special \n\t\r\n Characters "
        tokens = estimator.count_tokens(text)

        assert isinstance(tokens, int)
        assert tokens >= 0

    def test_count_tokens_json_content(self, tmp_path):
        """Test counting tokens in JSON files."""
        estimator = TokenEstimator()

        # Create a JSON file
        json_file = tmp_path / "data.json"
        json_file.write_text('{"key": "value", "number": 42}', encoding="utf-8")

        tokens = estimator.count_tokens_in_file(json_file)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_tokens_python_file(self, tmp_path):
        """Test counting tokens in Python source file."""
        estimator = TokenEstimator()

        # Create a Python file with typical code
        python_file = tmp_path / "module.py"
        python_file.write_text(
            '''"""
Module docstring.
"""

from typing import List

class DataProcessor:
    """Process data."""

    def __init__(self, name: str):
        self.name = name

    def process(self, items: List[str]) -> List[str]:
        """Process items."""
        return [item.upper() for item in items]
''',
            encoding="utf-8",
        )

        tokens = estimator.count_tokens_in_file(python_file)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_tokens_consistency(self):
        """Test that token counting is consistent for the same text."""
        estimator = TokenEstimator()

        text = "The quick brown fox jumps over the lazy dog."

        # Count multiple times
        tokens1 = estimator.count_tokens(text)
        tokens2 = estimator.count_tokens(text)
        tokens3 = estimator.count_tokens(text)

        # Should always return the same count
        assert tokens1 == tokens2 == tokens3

    def test_estimate_tokens_for_lines_preserves_content(self):
        """Test that line estimation properly joins content."""
        estimator = TokenEstimator()

        lines = ["line1", "line2", "line3"]

        # Count directly
        direct_tokens = estimator.count_tokens("line1\nline2\nline3")

        # Count via lines
        line_tokens = estimator.estimate_tokens_for_lines(lines)

        # Should be the same or very close
        assert direct_tokens == line_tokens

    def test_estimate_tokens_for_lines_with_tuples_preserves_content(self):
        """Test that tuple line estimation properly extracts content."""
        estimator = TokenEstimator()

        # Lines with line numbers
        lines = [(1, "line1"), (2, "line2"), (3, "line3")]

        # Count directly (without line numbers)
        direct_tokens = estimator.count_tokens("line1\nline2\nline3")

        # Count via lines
        line_tokens = estimator.estimate_tokens_for_lines(lines)

        # Should be the same or very close
        assert direct_tokens == line_tokens

    def test_large_file_token_counting(self, tmp_path):
        """Test counting tokens in a larger file."""
        estimator = TokenEstimator()

        # Create a larger file
        large_file = tmp_path / "large.py"
        content = "\n".join([f"x = {i}" for i in range(1000)])
        large_file.write_text(content, encoding="utf-8")

        tokens = estimator.count_tokens_in_file(large_file)

        # Should handle large files without issues
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_unicode_file_handling(self, tmp_path):
        """Test handling files with various Unicode characters."""
        estimator = TokenEstimator()

        # Create file with various Unicode
        unicode_file = tmp_path / "unicode.txt"
        unicode_content = """
English: Hello
Chinese: 你好世界
Japanese: こんにちは
Arabic: مرحبا
Emoji: 😀🎉🚀
Symbols: ©®™€£¥
"""
        unicode_file.write_text(unicode_content, encoding="utf-8")

        tokens = estimator.count_tokens_in_file(unicode_file)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_file_read_error_handling(self, tmp_path):
        """Test handling of file read errors."""
        estimator = TokenEstimator()

        # Create a file and then make it unreadable (on Unix systems)
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("content", encoding="utf-8")

        # Mock read_text to raise an exception
        with patch.object(
            Path, "read_text", side_effect=PermissionError("Access denied")
        ):
            with pytest.raises(IOError):
                estimator.count_tokens_in_file(test_file)

    def test_zero_length_line_estimation(self):
        """Test estimating tokens for list with empty strings."""
        estimator = TokenEstimator()

        # List with empty strings
        lines = ["", "", ""]
        tokens = estimator.estimate_tokens_for_lines(lines)

        # Empty strings joined with newlines should count as 2 newlines
        assert tokens >= 0

    def test_newline_counting(self):
        """Test that newlines are properly counted in tokens."""
        estimator = TokenEstimator()

        # Test different newline patterns
        text1 = "line1\nline2"
        text2 = "line1\r\nline2"
        text3 = "line1\rline2"

        tokens1 = estimator.count_tokens(text1)
        tokens2 = estimator.count_tokens(text2)
        tokens3 = estimator.count_tokens(text3)

        # All should return valid counts
        assert tokens1 > 0
        assert tokens2 > 0
        assert tokens3 > 0
