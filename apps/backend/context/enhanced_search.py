"""
Enhanced Code Search with Graphiti Integration
==============================================

Combines keyword/semantic file search with Graphiti memory search
to enable powerful semantic code discovery by intent, not just text.

Features:
- Search code by purpose (e.g., "authentication functions")
- Find similar code patterns
- Find callers/callees of functions
- Search by function signature or type
- Natural language code queries

Usage:
    from pathlib import Path
    from context.enhanced_search import EnhancedCodeSearch
    from integrations.graphiti.memory import get_graphiti_memory

    # Create enhanced searcher
    memory = get_graphiti_memory(spec_dir, project_dir)
    searcher = EnhancedCodeSearch(project_dir, graphiti_memory=memory)

    # Search by purpose
    results = await searcher.search_by_purpose("user authentication")

    # Find callers
    callers = await searcher.find_callers("authenticate_user")

    # Find similar patterns
    patterns = await searcher.find_similar_patterns("error handling")
"""

import logging
from pathlib import Path
from typing import Any

from core.sentry import capture_exception

from .models import FileMatch
from .search import CodeSearcher

logger = logging.getLogger(__name__)


class EnhancedCodeSearch:
    """
    Enhanced code search combining file-based search with Graphiti memory.

    Integrates:
    - CodeSearcher: Keyword and semantic file search
    - GraphitiSearch: Semantic search in knowledge graph
    - CodeRelationshipQueries: Code relationships and purpose search

    Enables natural language code queries like:
    - "where is user auth"
    - "show me error handling patterns"
    - "what calls the login function"
    """

    def __init__(
        self,
        project_dir: Path,
        graphiti_memory: Any = None,
        use_semantic_search: bool = True,
    ):
        """
        Initialize enhanced code searcher.

        Args:
            project_dir: Root directory of the project
            graphiti_memory: Optional GraphitiMemory instance for semantic search
            use_semantic_search: Enable semantic search with embeddings (default: True)
        """
        self.project_dir = project_dir.resolve()
        self.graphiti_memory = graphiti_memory

        # Initialize base code searcher
        self._code_searcher = CodeSearcher(
            project_dir=project_dir,
            use_semantic_search=use_semantic_search,
        )

        # Extract Graphiti components if available
        self._code_relationships = None
        self._graphiti_search = None

        if graphiti_memory and hasattr(graphiti_memory, "code_relationships"):
            self._code_relationships = graphiti_memory.code_relationships

        if graphiti_memory and hasattr(graphiti_memory, "_search"):
            self._graphiti_search = graphiti_memory._search

        if graphiti_memory:
            logger.info(
                "EnhancedCodeSearch initialized with Graphiti memory integration"
            )
        else:
            logger.info(
                "EnhancedCodeSearch initialized without Graphiti (file search only)"
            )

    def search_service(
        self,
        service_path: Path,
        service_name: str,
        keywords: list[str],
    ) -> list[FileMatch]:
        """
        Search a service for files matching keywords (delegates to CodeSearcher).

        Args:
            service_path: Path to the service directory
            service_name: Name of the service
            keywords: List of keywords to search for

        Returns:
            List of FileMatch objects sorted by relevance
        """
        return self._code_searcher.search_service(service_path, service_name, keywords)

    async def search_with_semantics(
        self,
        service_path: Path,
        service_name: str,
        keywords: list[str],
        task_query: str,
    ) -> list[FileMatch]:
        """
        Search with semantic ranking (delegates to CodeSearcher).

        Args:
            service_path: Path to the service directory
            service_name: Name of the service
            keywords: List of keywords to search for
            task_query: Task description for semantic relevance

        Returns:
            List of FileMatch objects sorted by enhanced relevance score
        """
        return await self._code_searcher.search_with_semantics(
            service_path, service_name, keywords, task_query
        )

    async def search_by_purpose(
        self,
        query: str,
        limit: int = 20,
        entity_type: str | None = None,
    ) -> list[dict]:
        """
        Search for code entities by their purpose using natural language.

        This enables semantic search queries like:
        - "authentication functions"
        - "payment processing"
        - "database validation"
        - "API endpoints for users"

        Args:
            query: Natural language query describing the purpose to search for
            limit: Maximum number of results to return
            entity_type: Optional filter for entity type (function, class, module, method)

        Returns:
            List of entity information with name, type, purpose, file path, and metadata:
            [
                {
                    "entity_name": "authenticate_user",
                    "entity_type": "function",
                    "purpose": "Authenticates user credentials",
                    "file_path": "apps/backend/auth.py",
                    "lineno": 42,
                    "docstring": "...",
                    "tags": ["authentication", "security"],
                    "score": 0.95
                }
            ]
        """
        if not self._code_relationships:
            logger.warning(
                "Graphiti code relationships not available, returning empty results"
            )
            return []

        try:
            results = await self._code_relationships.search_by_purpose(
                query=query,
                limit=limit,
                entity_type=entity_type,
            )
            logger.info(
                f"Found {len(results)} entities for purpose query: {query[:50]}..."
            )
            return results
        except Exception as e:
            logger.error(f"Failed to search by purpose: {e}")
            capture_exception(
                e,
                query_summary=query[:100] if query else "",
                operation="search_by_purpose",
            )
            return []

    async def find_similar_patterns(
        self,
        query: str,
        num_results: int = 5,
        min_score: float = 0.5,
    ) -> list[dict]:
        """
        Find similar code patterns from the knowledge graph.

        Searches for patterns and gotchas that match the query, enabling
        code discovery based on implementation patterns.

        Args:
            query: Search query describing the pattern to find
            num_results: Maximum results per type (patterns and gotchas)
            min_score: Minimum relevance score (0.0-1.0)

        Returns:
            List of pattern information with content, score, and metadata:
            [
                {
                    "content": "Pattern description",
                    "score": 0.92,
                    "type": "pattern",
                    "category": "error_handling",
                    "confidence": 0.95
                }
            ]
        """
        if not self._graphiti_search:
            logger.warning("Graphiti search not available, returning empty results")
            return []

        try:
            patterns, gotchas = await self._graphiti_search.get_patterns_and_gotchas(
                query=query,
                num_results=num_results,
                min_score=min_score,
            )

            # Combine patterns and gotchas into a single list
            results = []
            for pattern in patterns:
                results.append(
                    {
                        "content": pattern.get("content", ""),
                        "score": pattern.get("score", 0.0),
                        "type": "pattern",
                        "category": pattern.get("category"),
                        "confidence": pattern.get("confidence"),
                    }
                )

            for gotcha in gotchas:
                results.append(
                    {
                        "content": gotcha.get("content", ""),
                        "score": gotcha.get("score", 0.0),
                        "type": "gotcha",
                    }
                )

            # Sort by score
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

            logger.info(f"Found {len(results)} patterns/gotchas for: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Failed to find similar patterns: {e}")
            capture_exception(
                e,
                query_summary=query[:100] if query else "",
                operation="find_similar_patterns",
            )
            return []

    async def find_callers(
        self,
        function_name: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all functions that call the specified function.

        Useful for understanding impact of changes and tracing call chains.

        Args:
            function_name: Name of the function to find callers for
            limit: Maximum number of results to return

        Returns:
            List of caller information:
            [
                {
                    "caller": "process_request",
                    "file_path": "apps/backend/api.py",
                    "lineno": 123,
                    "call_type": "function",
                    "module": None
                }
            ]
        """
        if not self._code_relationships:
            logger.warning(
                "Graphiti code relationships not available, returning empty results"
            )
            return []

        try:
            callers = await self._code_relationships.find_callers(
                function_name=function_name,
                limit=limit,
            )
            logger.info(f"Found {len(callers)} callers for function: {function_name}")
            return callers
        except Exception as e:
            logger.error(f"Failed to find callers: {e}")
            capture_exception(
                e,
                function_name=function_name,
                operation="find_callers",
            )
            return []

    async def find_callees(
        self,
        function_name: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all functions that the specified function calls.

        Useful for understanding dependencies and call chains.

        Args:
            function_name: Name of the function to find callees for
            limit: Maximum number of results to return

        Returns:
            List of callee information:
            [
                {
                    "callee": "validate_token",
                    "file_path": "apps/backend/auth.py",
                    "lineno": 67,
                    "call_type": "function",
                    "module": "tokens"
                }
            ]
        """
        if not self._code_relationships:
            logger.warning(
                "Graphiti code relationships not available, returning empty results"
            )
            return []

        try:
            callees = await self._code_relationships.find_callees(
                function_name=function_name,
                limit=limit,
            )
            logger.info(f"Found {len(callees)} callees for function: {function_name}")
            return callees
        except Exception as e:
            logger.error(f"Failed to find callees: {e}")
            capture_exception(
                e,
                function_name=function_name,
                operation="find_callees",
            )
            return []

    async def search_unified(
        self,
        query: str,
        limit: int = 20,
        search_files: bool = True,
        search_purpose: bool = True,
        search_patterns: bool = True,
    ) -> dict[str, list]:
        """
        Unified search across all available search methods.

        Performs search across multiple dimensions and returns combined results.

        Args:
            query: Natural language search query
            limit: Maximum results per search type
            search_files: Enable file-based search
            search_purpose: Enable purpose-based search (requires Graphiti)
            search_patterns: Enable pattern search (requires Graphiti)

        Returns:
            Dictionary with results from each search type:
            {
                "files": [...],      # FileMatch objects
                "purpose": [...],    # Entity info by purpose
                "patterns": [...],   # Similar code patterns
                "total": 42
            }
        """
        results = {
            "files": [],
            "purpose": [],
            "patterns": [],
            "total": 0,
        }

        # File-based search (extract keywords from query)
        if search_files:
            try:
                # Simple keyword extraction from query
                keywords = query.lower().split()
                service_path = self.project_dir
                service_name = "project"

                file_results = await self._code_searcher.search_with_semantics(
                    service_path=service_path,
                    service_name=service_name,
                    keywords=keywords,
                    task_query=query,
                )
                results["files"] = file_results[:limit]
                logger.info(f"File search found {len(results['files'])} results")
            except Exception as e:
                logger.warning(f"File search failed: {e}")

        # Purpose-based search (requires Graphiti)
        if search_purpose and self._code_relationships:
            try:
                purpose_results = await self.search_by_purpose(query, limit)
                results["purpose"] = purpose_results
                logger.info(f"Purpose search found {len(results['purpose'])} results")
            except Exception as e:
                logger.warning(f"Purpose search failed: {e}")

        # Pattern search (requires Graphiti)
        if search_patterns and self._graphiti_search:
            try:
                pattern_results = await self.find_similar_patterns(query, limit)
                results["patterns"] = pattern_results
                logger.info(f"Pattern search found {len(results['patterns'])} results")
            except Exception as e:
                logger.warning(f"Pattern search failed: {e}")

        # Calculate total
        results["total"] = (
            len(results["files"]) + len(results["purpose"]) + len(results["patterns"])
        )

        logger.info(f"Unified search completed with {results['total']} total results")
        return results

    def get_status(self) -> dict:
        """
        Get status information about the enhanced searcher.

        Returns:
            Dictionary with status information
        """
        return {
            "project_dir": str(self.project_dir),
            "graphiti_enabled": self.graphiti_memory is not None,
            "graphiti_initialized": (
                self.graphiti_memory.is_initialized if self.graphiti_memory else False
            ),
            "code_relationships_available": self._code_relationships is not None,
            "graphiti_search_available": self._graphiti_search is not None,
            "semantic_search_enabled": self._code_searcher.use_semantic_search,
        }
