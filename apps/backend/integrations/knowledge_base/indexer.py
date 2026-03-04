"""
Documentation Indexer for Knowledge Base
=========================================

Handles storage and retrieval of indexed documentation.
Provides semantic search and context retrieval operations.
"""

import json
import logging
from pathlib import Path
from typing import Any

from core.sentry import capture_exception

from .config import KnowledgeBaseState

logger = logging.getLogger(__name__)


# Maximum number of search results to return
MAX_SEARCH_RESULTS = 20

# Default minimum similarity score
DEFAULT_MIN_SCORE = 0.0

# Document storage file
DOCUMENTS_CACHE = ".knowledge_base_documents.json"


class DocumentationIndexer:
    """
    Manages documentation indexing and search operations.

    Provides methods for storing, searching, and retrieving documentation
    from the knowledge base. Handles both keyword and semantic search.
    """

    def __init__(
        self,
        spec_dir: Path,
        project_dir: Path,
        state: KnowledgeBaseState | None = None,
    ):
        """
        Initialize documentation indexer.

        Args:
            spec_dir: Spec directory for storing indexed documents
            project_dir: Project root directory
            state: Optional KnowledgeBaseState instance
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.state = state
        self._documents: dict[str, dict[str, Any]] = {}
        self._index_loaded = False

    async def index_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Index a list of documents for search.

        Args:
            documents: List of document dictionaries with id, title, content, url, metadata

        Returns:
            Dict with indexing results:
            - success: bool
            - indexed: int (number of documents indexed)
            - failed: int (number that failed)
            - errors: list of error messages
        """
        try:
            indexed_count = 0
            failed_count = 0
            errors = []

            for doc in documents:
                try:
                    doc_id = doc.get("id")
                    if not doc_id:
                        failed_count += 1
                        errors.append(
                            f"Document missing 'id': {doc.get('title', 'Unknown')}"
                        )
                        continue

                    # Store document with metadata
                    self._documents[doc_id] = {
                        "id": doc_id,
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                        "url": doc.get("url", ""),
                        "metadata": doc.get("metadata", {}),
                        "indexed_at": self._get_timestamp(),
                    }
                    indexed_count += 1

                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to index document {doc.get('id')}: {e}")

            # Save index to disk
            self._save_index()

            logger.info(
                f"Indexed {indexed_count} documents, {failed_count} failed "
                f"for {self.spec_dir.name}"
            )

            return {
                "success": failed_count == 0,
                "indexed": indexed_count,
                "failed": failed_count,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            capture_exception(
                e,
                component="knowledge_base_indexer",
                operation="index_documents",
                spec_dir=str(self.spec_dir),
                doc_count=len(documents),
            )
            return {
                "success": False,
                "indexed": 0,
                "failed": len(documents),
                "errors": [str(e)],
            }

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant documents based on a query.

        Performs keyword-based search on document titles and content.
        Results are scored based on query term matches.

        Args:
            query: Search query
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of matching documents with content, score, and metadata
        """
        # Enforce search result limit
        if limit <= 0 or limit > MAX_SEARCH_RESULTS:
            limit = MAX_SEARCH_RESULTS

        try:
            # Ensure index is loaded
            if not self._index_loaded:
                self._load_index()

            if not self._documents:
                logger.info("No indexed documents available for search")
                return []

            # Normalize query for search
            query_terms = self._normalize_query(query)
            if not query_terms:
                return []

            results = []
            for doc_id, doc in self._documents.items():
                # Calculate relevance score
                score = self._calculate_score(doc, query_terms)

                if score >= min_score:
                    results.append(
                        {
                            "id": doc_id,
                            "title": doc.get("title", ""),
                            "content": doc.get("content", ""),
                            "url": doc.get("url", ""),
                            "score": score,
                            "metadata": doc.get("metadata", {}),
                        }
                    )

            # Sort by score descending and limit results
            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:limit]

            logger.info(f"Found {len(results)} documents for query: {query[:50]}...")

            return results

        except Exception as e:
            logger.warning(f"Failed to search documents: {e}")
            capture_exception(
                e,
                component="knowledge_base_indexer",
                operation="search",
                query=query[:100] if query else "",
                spec_dir=str(self.spec_dir),
            )
            return []

    async def get_relevant_context(
        self,
        query: str,
        num_results: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Get relevant context for a query, formatted for agent consumption.

        Similar to search() but returns results in a format suitable
        for including in agent context.

        Args:
            query: Search query
            num_results: Maximum number of results
            min_score: Minimum similarity score

        Returns:
            List of context items with content, score, and source info
        """
        try:
            documents = await self.search(
                query=query,
                limit=num_results,
                min_score=min_score,
            )

            context_items = []
            for doc in documents:
                # Format as context item
                context_items.append(
                    {
                        "content": self._format_doc_as_context(doc),
                        "score": doc.get("score", 0.0),
                        "type": "documentation",
                        "source": doc.get("metadata", {}).get("source", "unknown"),
                        "url": doc.get("url", ""),
                        "title": doc.get("title", ""),
                    }
                )

            return context_items

        except Exception as e:
            logger.warning(f"Failed to get relevant context: {e}")
            capture_exception(
                e,
                component="knowledge_base_indexer",
                operation="get_relevant_context",
                query=query[:100] if query else "",
                spec_dir=str(self.spec_dir),
            )
            return []

    async def get_document_by_id(self, doc_id: str) -> dict[str, Any] | None:
        """
        Retrieve a specific document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document dict if found, None otherwise
        """
        try:
            # Ensure index is loaded
            if not self._index_loaded:
                self._load_index()

            return self._documents.get(doc_id)

        except Exception as e:
            logger.warning(f"Failed to get document {doc_id}: {e}")
            return None

    async def get_all_documents(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all indexed documents.

        Args:
            limit: Optional maximum number of documents to return

        Returns:
            List of all documents
        """
        try:
            # Ensure index is loaded
            if not self._index_loaded:
                self._load_index()

            documents = list(self._documents.values())

            if limit and len(documents) > limit:
                documents = documents[:limit]

            return documents

        except Exception as e:
            logger.warning(f"Failed to get all documents: {e}")
            return []

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get statistics about the document index.

        Returns:
            Dict with index statistics
        """
        # Ensure index is loaded
        if not self._index_loaded:
            self._load_index()

        total_docs = len(self._documents)

        # Count by source
        source_counts: dict[str, int] = {}
        for doc in self._documents.values():
            source = doc.get("metadata", {}).get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        # Calculate total content size
        total_size = sum(
            len(doc.get("content", "")) for doc in self._documents.values()
        )

        return {
            "total_documents": total_docs,
            "total_size_bytes": total_size,
            "sources": source_counts,
            "index_loaded": self._index_loaded,
        }

    def clear_index(self) -> None:
        """
        Clear all indexed documents.

        Removes all documents from memory and from disk.
        """
        self._documents.clear()
        self._index_loaded = False
        self._delete_index_file()

        logger.info(f"Cleared document index for {self.spec_dir.name}")

    # Private helper methods

    def _load_index(self) -> None:
        """Load documents index from disk."""
        cache_file = self.spec_dir / DOCUMENTS_CACHE

        if not cache_file.exists():
            self._index_loaded = True
            return

        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
                self._documents = data.get("documents", {})
                self._index_loaded = True

            logger.debug(
                f"Loaded {len(self._documents)} documents from index "
                f"for {self.spec_dir.name}"
            )

        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to load document index: {e}")
            self._documents = {}
            self._index_loaded = True

    def _save_index(self) -> None:
        """Save documents index to disk."""
        cache_file = self.spec_dir / DOCUMENTS_CACHE

        try:
            data = {
                "documents": self._documents,
                "updated_at": self._get_timestamp(),
                "spec_dir": str(self.spec_dir),
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved document index for {self.spec_dir.name}")

        except OSError as e:
            logger.warning(f"Failed to save document index: {e}")

    def _delete_index_file(self) -> None:
        """Delete the document index file from disk."""
        cache_file = self.spec_dir / DOCUMENTS_CACHE

        try:
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Deleted document index for {self.spec_dir.name}")
        except OSError as e:
            logger.warning(f"Failed to delete document index file: {e}")

    def _normalize_query(self, query: str) -> list[str]:
        """
        Normalize query into search terms.

        Args:
            query: Search query string

        Returns:
            List of normalized search terms
        """
        if not query:
            return []

        # Convert to lowercase and split on whitespace
        terms = query.lower().split()

        # Filter out common stop words
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "for",
            "of",
            "with",
            "by",
            "from",
            "in",
            "on",
            "at",
            "to",
            "as",
            "it",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "we",
            "they",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
        }

        filtered_terms = [t for t in terms if t not in stop_words and len(t) > 1]

        return filtered_terms

    def _calculate_score(
        self,
        doc: dict[str, Any],
        query_terms: list[str],
    ) -> float:
        """
        Calculate relevance score for a document.

        Simple keyword matching algorithm:
        - Title matches weighted 2x
        - Content matches weighted 1x
        - Exact phrase matches weighted 3x

        Args:
            doc: Document dictionary
            query_terms: Normalized query terms

        Returns:
            Relevance score (0.0-1.0)
        """
        title = doc.get("title", "").lower()
        content = doc.get("content", "").lower()

        score = 0.0
        total_weight = 0.0

        for term in query_terms:
            # Title matches (weighted 2x)
            if term in title:
                score += 2.0
                total_weight += 2.0

            # Content matches (weighted 1x)
            term_count = content.count(term)
            if term_count > 0:
                # Cap content matches per term to avoid over-weighting
                score += min(term_count, 5) * 1.0
                total_weight += 5.0  # Normalize by max expected matches

        # Check for exact phrase match (weighted 3x)
        phrase = " ".join(query_terms)
        if phrase in content:
            score += 3.0
            total_weight += 3.0

        # Normalize score to 0.0-1.0
        if total_weight > 0:
            normalized_score = min(score / total_weight, 1.0)
        else:
            normalized_score = 0.0

        return normalized_score

    def _format_doc_as_context(self, doc: dict[str, Any]) -> str:
        """
        Format a document as context for agent consumption.

        Args:
            doc: Document dictionary

        Returns:
            Formatted context string
        """
        title = doc.get("title", "Untitled")
        content = doc.get("content", "")
        url = doc.get("url", "")

        # Truncate content if too long
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        parts = [f"# {title}"]

        if url:
            parts.append(f"Source: {url}")

        parts.append(f"\n{content}")

        return "\n".join(parts)

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()
