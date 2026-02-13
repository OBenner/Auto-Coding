"""
Semantic Relevance Scorer for Context Optimization

Uses embeddings from Graphiti to compute semantic similarity between
task queries and file content for intelligent context ranking.
"""

import logging
from typing import Any

import numpy as np
from core.sentry import capture_exception

logger = logging.getLogger(__name__)


class SemanticScorer:
    """
    Computes semantic relevance scores using embeddings.

    Provides methods for scoring files based on their semantic similarity
    to a task query, using embeddings from Graphiti's embedder.
    """

    def __init__(self, embedder: Any):
        """
        Initialize the semantic scorer.

        Args:
            embedder: Graphiti embedder instance (async interface)
        """
        self.embedder = embedder

    async def score_files(
        self,
        files: list[dict],
        task_query: str,
        max_results: int | None = None,
    ) -> list[dict]:
        """
        Score files based on semantic similarity to task query.

        Args:
            files: List of file dicts with 'path' and 'content' keys
            task_query: Task description to compare against
            max_results: Optional limit on number of results

        Returns:
            List of file dicts with added 'semantic_score' field, sorted by score
        """
        if not files:
            return []

        try:
            # Get embedding for task query
            query_embedding = await self._get_embedding(task_query)
            if query_embedding is None:
                logger.warning("Failed to get embedding for task query")
                return self._add_zero_scores(files)

            # Score each file
            scored_files = []
            for file_dict in files:
                content = file_dict.get("content", "")
                if not content:
                    scored_files.append({**file_dict, "semantic_score": 0.0})
                    continue

                try:
                    # Get embedding for file content
                    content_embedding = await self._get_embedding(content)
                    if content_embedding is None:
                        scored_files.append({**file_dict, "semantic_score": 0.0})
                        continue

                    # Compute cosine similarity
                    score = self._cosine_similarity(query_embedding, content_embedding)
                    scored_files.append({**file_dict, "semantic_score": score})

                except Exception as e:
                    logger.debug(f"Failed to score file {file_dict.get('path')}: {e}")
                    scored_files.append({**file_dict, "semantic_score": 0.0})

            # Sort by score descending
            scored_files.sort(key=lambda x: x.get("semantic_score", 0.0), reverse=True)

            if max_results:
                scored_files = scored_files[:max_results]

            logger.info(
                f"Scored {len(scored_files)} files for query: {task_query[:50]}..."
            )
            return scored_files

        except Exception as e:
            logger.warning(f"Failed to score files: {e}")
            capture_exception(
                e,
                query_summary=task_query[:100] if task_query else "",
                file_count=len(files),
                operation="score_files",
            )
            return self._add_zero_scores(files)

    async def score_query_pairs(
        self,
        queries: list[str],
        documents: list[str],
    ) -> list[tuple[str, str, float]]:
        """
        Score multiple query-document pairs.

        Args:
            queries: List of query strings
            documents: List of document strings

        Returns:
            List of (query, document, score) tuples
        """
        if not queries or not documents:
            return []

        try:
            # Get embeddings for all queries
            query_embeddings = []
            for query in queries:
                emb = await self._get_embedding(query)
                if emb is not None:
                    query_embeddings.append((query, emb))
                else:
                    query_embeddings.append((query, None))

            # Get embeddings for all documents
            doc_embeddings = []
            for doc in documents:
                emb = await self._get_embedding(doc)
                if emb is not None:
                    doc_embeddings.append((doc, emb))
                else:
                    doc_embeddings.append((doc, None))

            # Score all pairs
            results = []
            for query_text, query_emb in query_embeddings:
                for doc_text, doc_emb in doc_embeddings:
                    if query_emb is not None and doc_emb is not None:
                        score = self._cosine_similarity(query_emb, doc_emb)
                    else:
                        score = 0.0
                    results.append((query_text, doc_text, score))

            return results

        except Exception as e:
            logger.warning(f"Failed to score query pairs: {e}")
            capture_exception(e, operation="score_query_pairs")
            return [(q, d, 0.0) for q in queries for d in documents]

    async def _get_embedding(self, text: str) -> Any | None:
        """
        Get embedding for a text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        try:
            # The embedder interface from graphiti-core
            # Typically has an async embed() or similar method
            if hasattr(self.embedder, "embed"):
                result = await self.embedder.embed(text)
                # Handle different embedder return types
                if isinstance(result, dict) and "embedding" in result:
                    return result["embedding"]
                elif isinstance(result, list):
                    return result
                elif hasattr(result, "embedding"):
                    return result.embedding
                else:
                    return result
            else:
                logger.warning(f"Embedder has no 'embed' method: {type(self.embedder)}")
                return None

        except Exception as e:
            logger.debug(f"Failed to get embedding: {e}")
            return None

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            arr1 = np.array(vec1, dtype=np.float32)
            arr2 = np.array(vec2, dtype=np.float32)

            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = float(dot_product / (norm1 * norm2))
            # Clamp to [0, 1] range
            return max(0.0, min(1.0, similarity))

        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to compute cosine similarity: {e}")
            return 0.0

    def _add_zero_scores(self, files: list[dict]) -> list[dict]:
        """
        Add zero semantic scores to files.

        Args:
            files: List of file dicts

        Returns:
            Files with semantic_score added
        """
        return [{**file_dict, "semantic_score": 0.0} for file_dict in files]
