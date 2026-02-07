"""
Code Search Functionality
==========================

Search codebase for relevant files based on keywords and semantic similarity.
"""

import logging
import math
from pathlib import Path

from core.sentry import capture_exception

from .constants import CODE_EXTENSIONS, SKIP_DIRS
from .embeddings import EmbeddingGenerator
from .models import FileMatch

logger = logging.getLogger(__name__)


class CodeSearcher:
    """Searches code files for relevant matches using keyword and semantic search."""

    def __init__(self, project_dir: Path, use_semantic_search: bool = True):
        """
        Initialize code searcher.

        Args:
            project_dir: Project root directory
            use_semantic_search: Enable semantic search with embeddings (default: True)
        """
        self.project_dir = project_dir.resolve()
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
                    similarity = self._cosine_similarity(query_embedding, file_embedding)

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
