"""
Content Deduplication for Context Window Optimization
======================================================

Removes duplicate and redundant content from context to save tokens.
Uses hash-based exact matching and similarity-based near-duplicate detection.

Components:
- ContentDeduplicator: Main class for deduplication operations
- Exact duplicate removal via content hashing
- Near-duplicate detection using line-level similarity
- Configurable similarity threshold for near-duplicate detection

Usage:
    # Create deduplicator
    deduplicator = ContentDeduplicator()

    # Remove exact duplicates
    unique_items = deduplicator.deduplicate_exact([item1, item2, item3])

    # Remove near-duplicates (>=80% similar)
    unique_items = deduplicator.deduplicate_similar(
        items,
        similarity_threshold=0.8
    )

    # Deduplicate file content
    unique_files = deduplicator.deduplicate_files(file_list)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContentItem:
    """Represents a content item for deduplication."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None

    def __post_init__(self):
        """Calculate content hash after initialization."""
        if self.content_hash is None:
            self.content_hash = self._compute_hash(self.content)

    @staticmethod
    def _compute_hash(content: str) -> str:
        """
        Compute SHA-256 hash of content.

        Args:
            content: Text content to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ContentDeduplicator:
    """
    Removes duplicate and redundant content from context.

    Provides exact and near-duplicate detection to optimize token usage
    by eliminating redundant information.

    Args:
        similarity_threshold: Default threshold for near-duplicate detection (0.0-1.0)
        min_content_length: Minimum content length to consider for deduplication
    """

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        min_content_length: int = 10,
    ):
        """Initialize deduplicator with configuration."""
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                f"similarity_threshold must be between 0.0 and 1.0, got {similarity_threshold}"
            )

        self.similarity_threshold = similarity_threshold
        self.min_content_length = min_content_length
        self._seen_hashes: set[str] = set()

    def reset(self) -> None:
        """Reset internal state (clears seen hashes cache)."""
        self._seen_hashes.clear()

    def deduplicate_exact(
        self,
        items: list[str],
    ) -> list[str]:
        """
        Remove exact duplicates from a list of strings.

        Uses content hashing for O(n) exact duplicate detection.

        Args:
            items: List of content strings

        Returns:
            List with exact duplicates removed, preserving order

        Example:
            >>> deduplicator = ContentDeduplicator()
            >>> deduplicator.deduplicate_exact(["a", "b", "a", "c"])
            ['a', 'b', 'c']
        """
        seen = set()
        unique = []

        for item in items:
            # Skip very short content
            if len(item) < self.min_content_length:
                unique.append(item)
                continue

            # Compute hash
            content_hash = ContentItem._compute_hash(item)

            # Add if not seen
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(item)

        return unique

    def deduplicate_similar(
        self,
        items: list[str],
        similarity_threshold: float | None = None,
    ) -> list[str]:
        """
        Remove near-duplicate content using similarity detection.

        Compares items using line-level Jaccard similarity. Items with
        similarity >= threshold are considered duplicates.

        Args:
            items: List of content strings
            similarity_threshold: Override default threshold (0.0-1.0)

        Returns:
            List with near-duplicates removed, preserving order

        Example:
            >>> deduplicator = ContentDeduplicator()
            >>> deduplicator.deduplicate_similar(["code line 1\\ncode line 2", "code line 1\\ncode line 3"])
            ['code line 1\\ncode line 2', 'code line 1\\ncode line 3']
        """
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self.similarity_threshold
        )

        if not items:
            return []

        unique = []
        unique_line_sets = []

        for item in items:
            # Skip very short content
            if len(item) < self.min_content_length:
                unique.append(item)
                continue

            # Convert to set of lines for comparison
            lines = set(line.strip() for line in item.split("\n") if line.strip())

            # Check similarity against all unique items
            is_duplicate = False
            for existing_lines in unique_line_sets:
                similarity = self._jaccard_similarity(lines, existing_lines)
                if similarity >= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(item)
                unique_line_sets.append(lines)

        return unique

    def deduplicate_files(
        self,
        files: list[dict[str, Any]],
        content_key: str = "content",
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate files from a list.

        Deduplicates based on file content using exact hash matching.
        Preserves all metadata from the first occurrence.

        Args:
            files: List of file dictionaries with content
            content_key: Key name for content field in dictionaries

        Returns:
            List with duplicate files removed, preserving order

        Example:
            >>> files = [
            ...     {"path": "a.py", "content": "code"},
            ...     {"path": "b.py", "content": "code"},
            ...     {"path": "c.py", "content": "other"}
            ... ]
            >>> deduplicator = ContentDeduplicator()
            >>> deduped = deduplicator.deduplicate_files(files)
            >>> len(deduped)
            2
        """
        if not files:
            return []

        seen_hashes = set()
        unique_files = []

        for file_dict in files:
            content = file_dict.get(content_key, "")

            # Skip empty or very short content
            if not content or len(content) < self.min_content_length:
                unique_files.append(file_dict)
                continue

            # Compute hash
            content_hash = ContentItem._compute_hash(content)

            # Add if not seen
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_files.append(file_dict)

        return unique_files

    def deduplicate_lines(
        self,
        text: str,
        consecutive_only: bool = True,
    ) -> str:
        """
        Remove duplicate lines from text content.

        Args:
            text: Input text with potential duplicate lines
            consecutive_only: If True, only remove consecutive duplicates

        Returns:
            Text with duplicate lines removed

        Example:
            >>> deduplicator = ContentDeduplicator()
            >>> deduplicator.deduplicate_lines("line1\\nline1\\nline2")
            'line1\\nline2'
        """
        if not text:
            return text

        lines = text.split("\n")

        if consecutive_only:
            # Remove consecutive duplicate lines
            deduped = []
            prev_line = None

            for line in lines:
                if line != prev_line:
                    deduped.append(line)
                prev_line = line

            return "\n".join(deduped)
        else:
            # Remove all duplicate lines (keeps first occurrence)
            seen = set()
            deduped = []

            for line in lines:
                if line not in seen:
                    seen.add(line)
                    deduped.append(line)

            return "\n".join(deduped)

    def get_deduplication_stats(
        self,
        original_items: list[str],
        deduped_items: list[str],
    ) -> dict[str, Any]:
        """
        Get statistics about deduplication results.

        Args:
            original_items: Original list before deduplication
            deduped_items: Deduplicated list

        Returns:
            Dictionary with deduplication statistics

        Example:
            >>> deduplicator = ContentDeduplicator()
            >>> original = ["a", "b", "a", "c"]
            >>> deduped = deduplicator.deduplicate_exact(original)
            >>> stats = deduplicator.get_deduplication_stats(original, deduped)
            >>> stats["reduction_percent"]
            25.0
        """
        original_count = len(original_items)
        deduped_count = len(deduped_items)
        removed_count = original_count - deduped_count

        # Calculate character-level savings
        original_chars = sum(len(item) for item in original_items)
        deduped_chars = sum(len(item) for item in deduped_items)
        saved_chars = original_chars - deduped_chars

        return {
            "original_count": original_count,
            "deduped_count": deduped_count,
            "removed_count": removed_count,
            "reduction_percent": (
                (removed_count / original_count * 100) if original_count > 0 else 0.0
            ),
            "original_chars": original_chars,
            "deduped_chars": deduped_chars,
            "saved_chars": saved_chars,
            "char_reduction_percent": (
                (saved_chars / original_chars * 100) if original_chars > 0 else 0.0
            ),
        }

    @staticmethod
    def _jaccard_similarity(set1: set[str], set2: set[str]) -> float:
        """
        Calculate Jaccard similarity between two sets.

        Args:
            set1: First set
            set2: Second set

        Returns:
            Similarity score between 0.0 and 1.0

        Example:
            >>> ContentDeduplicator._jaccard_similarity({"a", "b"}, {"b", "c"})
            0.333...
        """
        if not set1 and not set2:
            return 1.0

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0


def get_content_deduplicator(
    similarity_threshold: float = 0.8,
    min_content_length: int = 10,
) -> ContentDeduplicator:
    """
    Factory function to create a ContentDeduplicator instance.

    Args:
        similarity_threshold: Threshold for near-duplicate detection (0.0-1.0)
        min_content_length: Minimum content length to consider

    Returns:
        Configured ContentDeduplicator instance

    Example:
        >>> deduplicator = get_content_deduplicator(similarity_threshold=0.9)
        >>> unique = deduplicator.deduplicate_exact(["a", "b", "a"])
    """
    return ContentDeduplicator(
        similarity_threshold=similarity_threshold,
        min_content_length=min_content_length,
    )
