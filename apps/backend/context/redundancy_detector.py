"""
Redundancy Detection
====================

Detects duplicate and similar code to reduce token usage in context.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from .models import FileMatch

if TYPE_CHECKING:
    from .token_estimator import TokenEstimator

logger = logging.getLogger(__name__)


class RedundancyDetector:
    """
    Detects duplicate and similar code to optimize context window usage.

    Identifies redundant files based on:
    - Exact content matches
    - High similarity scores (near-duplicates)
    - Common code patterns
    """

    def __init__(
        self,
        project_dir: Path,
        similarity_threshold: float = 0.85,
        token_estimator: "TokenEstimator | None" = None,
    ):
        """
        Initialize the redundancy detector.

        Args:
            project_dir: Root directory of the project
            similarity_threshold: Threshold for considering files as duplicates (0.0-1.0)
            token_estimator: Optional TokenEstimator for token-aware deduplication
        """
        self.project_dir = project_dir.resolve()
        self.similarity_threshold = similarity_threshold
        self.token_estimator = token_estimator

    def detect_redundancies(
        self,
        files: list[FileMatch],
        keep_highest_relevance: bool = True,
    ) -> tuple[list[FileMatch], list[dict]]:
        """
        Detect and remove redundant files from the list.

        Args:
            files: List of FileMatch objects to analyze
            keep_highest_relevance: If True, keep highest relevance score when duplicates found

        Returns:
            Tuple of (filtered_files, removal_report) where:
            - filtered_files: List with redundant files removed
            - removal_report: List of dicts describing removed files and reasons
        """
        if not files:
            return [], []

        logger.info(
            f"Analyzing {len(files)} files for redundancy (threshold={self.similarity_threshold})"
        )

        filtered_files: list[FileMatch] = []
        removal_report: list[dict] = []
        seen_hashes: dict[str, str] = {}
        seen_content_signatures: dict[str, dict] = {}

        # Sort by relevance score if keeping highest relevance
        if keep_highest_relevance:
            sorted_files = sorted(files, key=lambda f: f.relevance_score, reverse=True)
        else:
            sorted_files = files

        for file_match in sorted_files:
            try:
                # Resolve path and ensure it's inside the project directory
                raw_path = Path(file_match.path)
                candidate = (
                    raw_path if raw_path.is_absolute() else self.project_dir / raw_path
                )
                file_path = candidate.resolve()

                if not str(file_path).startswith(str(self.project_dir) + os.sep):
                    logger.warning(
                        "Skipping file outside project root: %s", file_match.path
                    )
                    continue

                # Check if file exists and is readable
                if not file_path.exists():
                    logger.debug(f"File not found, skipping: {file_match.path}")
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Check for exact duplicate (hash-based)
                content_hash = self._compute_hash(content)
                if content_hash in seen_hashes:
                    removal_report.append(
                        {
                            "file": file_match.path,
                            "reason": "exact_duplicate",
                            "duplicate_of": seen_hashes[content_hash],
                            "tokens_saved": file_match.estimated_tokens or 0,
                        }
                    )
                    logger.debug(f"Exact duplicate found: {file_match.path}")
                    continue

                # Normalize content for near-duplicate detection
                normalized_content = self._normalize_content(content)

                # Check for near-duplicate (signature-based)
                signature = self._compute_content_signature(content)
                if signature in seen_content_signatures:
                    stored = seen_content_signatures[signature]
                    similarity = self._compute_similarity(
                        normalized_content, stored["normalized"]
                    )

                    if similarity >= self.similarity_threshold:
                        removal_report.append(
                            {
                                "file": file_match.path,
                                "reason": "near_duplicate",
                                "similar_to": stored["file"].path,
                                "similarity": similarity,
                                "tokens_saved": file_match.estimated_tokens or 0,
                            }
                        )
                        logger.debug(
                            f"Near-duplicate found: {file_match.path} "
                            f"(similarity={similarity:.2f})"
                        )
                        continue

                # No redundancy found, keep this file
                filtered_files.append(file_match)
                seen_hashes[content_hash] = file_match.path
                seen_content_signatures[signature] = {
                    "file": file_match,
                    "normalized": normalized_content,
                }

            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to analyze file {file_match.path}: {e}")
                # Keep files that can't be analyzed (better safe than sorry)
                filtered_files.append(file_match)

        tokens_saved = sum(r.get("tokens_saved", 0) for r in removal_report)
        logger.info(
            f"Removed {len(removal_report)} redundant files, "
            f"saving ~{tokens_saved} tokens ({len(filtered_files)} files remaining)"
        )

        return filtered_files, removal_report

    def _compute_hash(self, content: str) -> str:
        """
        Compute a hash of the content for exact duplicate detection.

        Args:
            content: File content to hash

        Returns:
            Hexadecimal hash string
        """
        import hashlib

        # Use SHA256 for exact matching
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _compute_content_signature(self, content: str) -> str:
        """
        Compute a signature for similarity detection.

        Creates a normalized representation of the content by:
        - Removing whitespace variations
        - Lowercasing
        - Removing comments (basic)

        Args:
            content: File content to analyze

        Returns:
            Signature string for comparison
        """
        lines = content.split("\n")
        normalized_lines = []

        for line in lines:
            # Strip leading/trailing whitespace
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip single-line comments (basic)
            if line.startswith("#") or line.startswith("//"):
                continue

            # Normalize whitespace within line
            normalized = " ".join(line.split())
            normalized_lines.append(normalized.lower())

        # Join and create a signature based on line patterns
        normalized_content = "\n".join(normalized_lines)

        # Create a simple hash of the normalized content
        import hashlib

        return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()

    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for similarity comparison.

        Args:
            content: Raw file content

        Returns:
            Normalized content string
        """
        lines = content.split("\n")
        normalized_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(("#", "//")):
                continue
            normalized = " ".join(line.split()).lower()
            if normalized:
                normalized_lines.append(normalized)
        return "\n".join(normalized_lines)

    def _compute_similarity(self, a: str, b: str) -> float:
        """
        Compute Jaccard similarity between two normalized contents.

        Args:
            a: First normalized content string
            b: Second normalized content string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not a or not b:
            return 0.0

        a_lines = {line for line in a.split("\n") if line}
        b_lines = {line for line in b.split("\n") if line}
        if not a_lines or not b_lines:
            return 0.0

        intersection = a_lines & b_lines
        union = a_lines | b_lines
        return len(intersection) / len(union)

    def find_redundant_snippets(
        self,
        files: list[FileMatch],
        min_lines: int = 3,
    ) -> list[dict]:
        """
        Find redundant code snippets within files.

        Args:
            files: List of FileMatch objects to analyze
            min_lines: Minimum number of lines for a snippet to consider

        Returns:
            List of dicts describing redundant snippets found
        """
        if not files:
            return []

        snippets = []

        # Collect all code snippets from files
        all_snippets: dict[str, list[tuple[str, int, list[str]]]] = {}

        for file_match in files:
            try:
                file_path = self.project_dir / file_match.path
                if not file_path.exists():
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")

                # Extract potential snippets (functions, classes, blocks)
                for i in range(len(lines) - min_lines + 1):
                    snippet_lines = lines[i : i + min_lines]
                    # Skip empty/comment-only snippets
                    if any(
                        line.strip() and not line.strip().startswith(("#", "//"))
                        for line in snippet_lines
                    ):
                        snippet_key = "\n".join(snippet_lines)
                        if snippet_key not in all_snippets:
                            all_snippets[snippet_key] = []
                        all_snippets[snippet_key].append(
                            (file_match.path, i, snippet_lines)
                        )

            except (OSError, UnicodeDecodeError):
                continue

        # Find duplicates
        for snippet, occurrences in all_snippets.items():
            if len(occurrences) > 1:
                # Found duplicate snippet
                total_tokens = len(snippet.split()) // 4 if self.token_estimator else 0
                snippets.append(
                    {
                        "snippet": snippet[:200],  # Truncate for report
                        "occurrences": [
                            {"file": path, "line": line_num}
                            for path, line_num, _ in occurrences
                        ],
                        "count": len(occurrences),
                        "potential_token_savings": total_tokens
                        * (len(occurrences) - 1),
                    }
                )

        logger.info(f"Found {len(snippets)} redundant code snippets")
        return snippets
