"""
Code Search Functionality
==========================

Search codebase for relevant files based on keywords and semantic similarity.
"""

import logging
from pathlib import Path
from typing import Any

from .constants import CODE_EXTENSIONS, SKIP_DIRS
from .models import FileMatch

logger = logging.getLogger(__name__)


class CodeSearcher:
    """Searches code files for relevant matches."""

    def __init__(self, project_dir: Path, semantic_scorer: Any = None):
        """
        Initialize the code searcher.

        Args:
            project_dir: Root directory of the project
            semantic_scorer: Optional SemanticScorer instance for semantic ranking
        """
        self.project_dir = project_dir.resolve()
        self.semantic_scorer = semantic_scorer

    def search_service(
        self,
        service_path: Path,
        service_name: str,
        keywords: list[str],
    ) -> list[FileMatch]:
        """
        Search a service for files matching keywords.

        Args:
            service_path: Path to the service directory
            service_name: Name of the service
            keywords: List of keywords to search for

        Returns:
            List of FileMatch objects sorted by relevance
        """
        matches = []

        if not service_path.exists():
            return matches

        for file_path in self._iter_code_files(service_path):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                content_lower = content.lower()

                # Score this file
                score = 0
                matching_keywords = []
                matching_lines = []

                for keyword in keywords:
                    if keyword in content_lower:
                        # Count occurrences
                        count = content_lower.count(keyword)
                        score += min(count, 10)  # Cap at 10 per keyword
                        matching_keywords.append(keyword)

                        # Find matching lines (first 3 per keyword)
                        lines = content.split("\n")
                        found = 0
                        for i, line in enumerate(lines, 1):
                            if keyword in line.lower() and found < 3:
                                matching_lines.append((i, line.strip()[:100]))
                                found += 1

                if score > 0:
                    rel_path = str(file_path.relative_to(self.project_dir))
                    matches.append(
                        FileMatch(
                            path=rel_path,
                            service=service_name,
                            reason=f"Contains: {', '.join(matching_keywords)}",
                            relevance_score=score,
                            matching_lines=matching_lines[:5],  # Top 5 lines
                        )
                    )

            except (OSError, UnicodeDecodeError):
                continue

        # Sort by relevance
        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        return matches[:20]  # Top 20 per service

    async def search_with_semantics(
        self,
        service_path: Path,
        service_name: str,
        keywords: list[str],
        task_query: str,
    ) -> list[FileMatch]:
        """
        Search a service for files matching keywords with semantic ranking.

        Combines keyword-based scoring with semantic similarity scoring
        to provide more accurate relevance ranking.

        Args:
            service_path: Path to the service directory
            service_name: Name of the service
            keywords: List of keywords to search for
            task_query: Task description for semantic relevance

        Returns:
            List of FileMatch objects sorted by enhanced relevance score
        """
        # First get keyword-based matches
        matches = self.search_service(service_path, service_name, keywords)

        # If no semantic scorer available, return keyword-only results
        if self.semantic_scorer is None:
            logger.debug("No semantic scorer available, using keyword-only ranking")
            return matches

        if not matches:
            return matches

        try:
            # Prepare files for semantic scoring
            files_to_score = []
            for match in matches:
                try:
                    file_path = self.project_dir / match.path
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    files_to_score.append({
                        "path": match.path,
                        "content": content,
                        "keyword_score": match.relevance_score,
                    })
                except (OSError, UnicodeDecodeError):
                    files_to_score.append({
                        "path": match.path,
                        "content": "",
                        "keyword_score": match.relevance_score,
                    })

            # Score files semantically
            scored_files = await self.semantic_scorer.score_files(
                files_to_score, task_query, max_results=None
            )

            # Update matches with combined scores
            enhanced_matches = []
            for scored_file in scored_files:
                # Find the original match
                original_match = next(
                    (m for m in matches if m.path == scored_file["path"]),
                    None
                )
                if original_match is None:
                    continue

                # Combined scoring: 70% keyword, 30% semantic
                # Keyword scores are typically higher (0-100+), semantic are 0-1
                keyword_score = original_match.relevance_score
                semantic_score = scored_file.get("semantic_score", 0.0)

                # Normalize and combine scores
                # Use semantic score as a multiplier (0.5 to 1.5 range)
                semantic_boost = 0.5 + semantic_score  # 0.5 to 1.5
                combined_score = keyword_score * semantic_boost

                # Update reason to include semantic info
                reason = original_match.reason
                if semantic_score > 0.3:
                    reason += f" | Semantic: {semantic_score:.2f}"

                enhanced_matches.append(
                    FileMatch(
                        path=original_match.path,
                        service=original_match.service,
                        reason=reason,
                        relevance_score=combined_score,
                        matching_lines=original_match.matching_lines,
                    )
                )

            # Sort by combined relevance
            enhanced_matches.sort(key=lambda m: m.relevance_score, reverse=True)
            logger.info(
                f"Semantic search: {len(enhanced_matches)} files for query: {task_query[:50]}..."
            )
            return enhanced_matches[:20]  # Top 20 per service

        except Exception as e:
            logger.warning(f"Semantic scoring failed, falling back to keyword-only: {e}")
            return matches

    def _iter_code_files(self, directory: Path):
        """
        Iterate over code files in a directory.

        Args:
            directory: Root directory to search

        Yields:
            Path objects for code files
        """
        for item in directory.rglob("*"):
            if item.is_file() and item.suffix in CODE_EXTENSIONS:
                # Check if in skip directory
                parts = item.relative_to(directory).parts
                if not any(part in SKIP_DIRS for part in parts):
                    yield item
