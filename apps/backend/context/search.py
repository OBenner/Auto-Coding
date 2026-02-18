"""
Code Search Functionality
==========================

Search codebase for relevant files based on keywords and semantic similarity.
"""

import logging
import math
from pathlib import Path
from typing import Any

from core.sentry import capture_exception

from .constants import CODE_EXTENSIONS, SKIP_DIRS
from .embeddings import EmbeddingGenerator
from .models import FileMatch

logger = logging.getLogger(__name__)


class CodeSearcher:
    """Searches code files for relevant matches using keyword and semantic search."""

    def __init__(
        self,
        project_dir: Path,
        semantic_scorer: Any = None,
        use_semantic_search: bool = True,
    ):
        """
        Initialize the code searcher.

        Args:
            project_dir: Root directory of the project
            semantic_scorer: Optional SemanticScorer instance for semantic ranking
            use_semantic_search: Enable semantic search with embeddings (default: True)
        """
        self.project_dir = project_dir.resolve()
        self.semantic_scorer = semantic_scorer
        self.use_semantic_search = use_semantic_search

        # Initialize embedding generator for semantic search
        self._embedding_generator = None
        if use_semantic_search:
            try:
                self._embedding_generator = EmbeddingGenerator(use_cache=True)
                logger.info(
                    f"Semantic search enabled "
                    f"({'OpenAI' if self._embedding_generator.is_using_openai() else 'local'})"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize semantic search: {e}")
                capture_exception(
                    e,
                    project_dir=str(project_dir),
                    operation="init_semantic_search",
                )

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
                    files_to_score.append(
                        {
                            "path": match.path,
                            "content": content,
                            "keyword_score": match.relevance_score,
                        }
                    )
                except (OSError, UnicodeDecodeError):
                    files_to_score.append(
                        {
                            "path": match.path,
                            "content": "",
                            "keyword_score": match.relevance_score,
                        }
                    )

            # Score files semantically
            scored_files = await self.semantic_scorer.score_files(
                files_to_score, task_query, max_results=None
            )

            # Update matches with combined scores
            enhanced_matches = []
            # Normalize keyword scores to [0, 1] using the max observed value
            max_keyword = max((m.relevance_score for m in matches), default=1.0) or 1.0

            for scored_file in scored_files:
                # Find the original match
                original_match = next(
                    (m for m in matches if m.path == scored_file["path"]), None
                )
                if original_match is None:
                    continue

                # Normalize both scores to [0, 1] and combine
                keyword_norm = min(original_match.relevance_score / max_keyword, 1.0)
                semantic_score = float(scored_file.get("semantic_score", 0.0) or 0.0)

                # Weighted linear combination (both in [0, 1])
                combined_norm = 0.7 * keyword_norm + 0.3 * semantic_score
                # Project back to original keyword scale
                combined_score = combined_norm * max_keyword

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
            logger.warning(
                f"Semantic scoring failed, falling back to keyword-only: {e}"
            )
            return matches

    def search_semantic(
        self,
        service_path: Path,
        service_name: str,
        query: str,
        num_results: int = 20,
        min_score: float = 0.3,
    ) -> list[FileMatch]:
        """
        Search a service for files using semantic similarity.

        Args:
            service_path: Path to the service directory
            service_name: Name of the service
            query: Search query (e.g., "authentication logic", "database models")
            num_results: Maximum number of results to return (default: 20)
            min_score: Minimum similarity score threshold 0-1 (default: 0.3)

        Returns:
            List of FileMatch objects sorted by similarity score
        """
        matches = []

        # Check if semantic search is available
        if not self._embedding_generator:
            logger.warning("Semantic search not available, returning empty results")
            return matches

        if not service_path.exists():
            return matches

        try:
            # Generate query embedding
            query_embedding = self._embedding_generator.generate_embedding(query)

            # Search files
            for file_path in self._iter_code_files(service_path):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    # Skip empty files
                    if not content.strip():
                        continue

                    # Generate file embedding (first 2000 chars to avoid token limits)
                    file_text = content[:2000]
                    file_embedding = self._embedding_generator.generate_embedding(
                        file_text
                    )

                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(
                        query_embedding, file_embedding
                    )

                    # Filter by minimum score
                    if similarity >= min_score:
                        # Resolve paths before calculating relative path
                        resolved_file = file_path.resolve()
                        try:
                            rel_path = str(resolved_file.relative_to(self.project_dir))
                        except ValueError:
                            # Fallback to absolute path if relative calculation fails
                            rel_path = str(resolved_file)

                        # Extract preview lines (first few non-empty lines)
                        preview_lines = []
                        for i, line in enumerate(content.split("\n")[:10], 1):
                            stripped = line.strip()
                            if stripped and not stripped.startswith("#"):
                                preview_lines.append((i, stripped[:100]))
                                if len(preview_lines) >= 3:
                                    break

                        matches.append(
                            FileMatch(
                                path=rel_path,
                                service=service_name,
                                reason=f"Semantic match (similarity: {similarity:.2f})",
                                relevance_score=similarity,
                                matching_lines=preview_lines,
                            )
                        )

                except (OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Failed to read file {file_path}: {e}")
                    continue

            # Sort by similarity score
            matches.sort(key=lambda m: m.relevance_score, reverse=True)
            return matches[:num_results]

        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            capture_exception(
                e,
                query=query[:100] if query else "",
                service_path=str(service_path),
                operation="search_semantic",
            )
            return []

    def _cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        if len(vec1) != len(vec2):
            logger.warning(
                f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}, "
                "returning 0 similarity"
            )
            return 0.0

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)

        # Clamp to [0, 1] range (cosine can be [-1, 1], but we want positive similarity)
        return max(0.0, min(1.0, similarity))

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
