"""
Context Builder
===============

Main builder class that orchestrates context building for tasks.
"""

import asyncio
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

from .categorizer import FileCategorizer
from .deduplicator import ContentDeduplicator
from .dependency_analyzer import DependencyAnalyzer
from .graphiti_integration import fetch_graph_hints, is_graphiti_enabled
from .keyword_extractor import KeywordExtractor
from .models import FileMatch, TaskContext
from .pattern_discovery import PatternDiscoverer
from .preloader import ContextPreloader
from .prioritizer import FilePrioritizer
from .priority_manager import PriorityManager
from .redundancy_detector import RedundancyDetector
from .search import CodeSearcher
from .semantic_scorer import SemanticScorer
from .service_matcher import ServiceMatcher
from .token_counter import TokenCounter
from .token_estimator import TokenEstimator

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds task-specific context by searching the codebase."""

    def __init__(
        self,
        project_dir: Path | None,
        project_index: dict | None = None,
        token_budget: int | None = None,
        cache_dir: Path | None = None,
    ):
        self.project_dir = project_dir.resolve() if project_dir else None
        self.project_index = project_index or self._load_project_index()
        self.token_budget = token_budget
        self.cache_dir = cache_dir

        # Initialize semantic scorer if Graphiti is enabled
        self.semantic_scorer = self._init_semantic_scorer()

        # Initialize token estimator
        self.token_estimator = TokenEstimator()

        # Initialize components
        self.searcher = (
            CodeSearcher(self.project_dir, semantic_scorer=self.semantic_scorer)
            if self.project_dir
            else None
        )
        self.service_matcher = ServiceMatcher(self.project_index)
        self.keyword_extractor = KeywordExtractor()
        self.categorizer = FileCategorizer()
        self.pattern_discoverer = (
            PatternDiscoverer(self.project_dir) if self.project_dir else None
        )
        self.redundancy_detector = (
            RedundancyDetector(self.project_dir, token_estimator=self.token_estimator)
            if self.project_dir
            else None
        )
        self.priority_manager = (
            PriorityManager(self.project_dir) if self.project_dir else None
        )

        # Initialize prioritization components
        self.prioritizer = (
            FilePrioritizer(self.project_dir) if self.project_dir else None
        )
        self.dependency_analyzer = (
            DependencyAnalyzer(self.project_dir) if self.project_dir else None
        )

        # Initialize token budget manager components
        self.token_counter = TokenCounter()
        self.deduplicator = ContentDeduplicator()
        self._token_usage = 0

        # Initialize preloader (optional - only if cache_dir provided)
        self.preloader = None
        if cache_dir and project_dir:
            available_files = self._get_available_files()
            self.preloader = ContextPreloader(
                project_dir=self.project_dir,
                cache_dir=self.cache_dir,
                available_files=available_files,
            )

    def _load_project_index(self) -> dict:
        """Load project index from file or create new one (.auto-claude is the installed instance)."""
        if not self.project_dir:
            return {"services": {}}

        index_file = self.project_dir / ".auto-claude" / "project_index.json"
        if index_file.exists():
            try:
                with open(index_file, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                # Corrupted or legacy-encoded file, regenerate
                pass

        # Try to create one
        from analyzer import analyze_project

        return analyze_project(self.project_dir)

    def _init_semantic_scorer(self) -> SemanticScorer | None:
        """
        Initialize semantic scorer if Graphiti is enabled.

        Returns:
            SemanticScorer instance or None if Graphiti is not available
        """
        if not is_graphiti_enabled():
            logger.debug("Graphiti not enabled, semantic scoring unavailable")
            return None

        try:
            from graphiti_config import GraphitiConfig
            from graphiti_providers import create_embedder

            config = GraphitiConfig.from_env()
            embedder = create_embedder(config)

            if embedder is None:
                logger.warning("Failed to create embedder for semantic scoring")
                return None

            scorer = SemanticScorer(embedder)
            logger.info("Semantic scorer initialized successfully")
            return scorer

        except ImportError as e:
            logger.debug(f"Graphiti dependencies not available: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize semantic scorer: {e}")
            return None

    def build_context(
        self,
        task: str,
        services: list[str] | None = None,
        keywords: list[str] | None = None,
        include_graph_hints: bool = True,
        semantic_search: bool = False,
    ) -> TaskContext:
        """
        Build context for a specific task.

        Args:
            task: Description of the task
            services: List of service names to search (None = auto-detect)
            keywords: Additional keywords to search for
            include_graph_hints: Whether to include historical hints from Graphiti
            semantic_search: Whether to use semantic search with embeddings

        Returns:
            TaskContext with relevant files and patterns
        """
        # Auto-detect services if not specified
        if not services:
            services = self.service_matcher.suggest_services(task)

        # Extract keywords from task if not provided
        if not keywords:
            keywords = self.keyword_extractor.extract_keywords(task)

        # Search each service
        all_matches: list[FileMatch] = []
        service_contexts = {}

        if self.searcher and self.project_dir:
            for service_name in services:
                service_info = self.project_index.get("services", {}).get(service_name)
                if not service_info:
                    continue

                service_path = Path(service_info.get("path", service_name))
                if not service_path.is_absolute():
                    service_path = self.project_dir / service_path

                # Search this service (sync version always uses keyword search;
                # use build_context_async for semantic search support)
                matches = self.searcher.search_service(
                    service_path, service_name, keywords
                )

                all_matches.extend(matches)

                # If semantic search is enabled, also search using embeddings
                if semantic_search:
                    semantic_matches = self.searcher.search_semantic(
                        service_path, service_name, task
                    )
                    all_matches.extend(semantic_matches)

                # Load or generate service context
                service_contexts[service_name] = self._get_service_context(
                    service_path, service_name, service_info
                )

        # Prioritize matches using recency and dependency analysis
        all_matches = self._prioritize_matches(all_matches)

        # Apply user priorities to filter and sort matches
        if self.priority_manager:
            all_matches = self.priority_manager.apply_priorities(
                all_matches, exclude_never=True, sort=True
            )

        # Log priority application
        if all_matches:
            logger.debug(f"Applied user priorities to {len(all_matches)} files")

        # Detect and remove redundant files
        if self.redundancy_detector:
            all_matches, redundancy_report = (
                self.redundancy_detector.detect_redundancies(
                    all_matches, keep_highest_relevance=True
                )
            )

            # Log redundancy report
            if redundancy_report:
                logger.info(
                    f"Removed {len(redundancy_report)} redundant files from context: "
                    f"{sum(r.get('tokens_saved', 0) for r in redundancy_report)} tokens saved"
                )

        # Categorize matches after redundancy removal
        files_to_modify, files_to_reference = self.categorizer.categorize_matches(
            all_matches, task
        )

        # Discover patterns from reference files
        patterns = []
        if self.pattern_discoverer:
            patterns = self.pattern_discoverer.discover_patterns(
                files_to_reference, keywords
            )

        # Get graph hints (synchronously wrap async call)
        graph_hints = []
        if include_graph_hints and is_graphiti_enabled():
            try:
                asyncio.get_running_loop()
                # Already in an async context - skip to avoid RuntimeError
            except RuntimeError:
                # No event loop running - safe to create one
                try:
                    graph_hints = asyncio.run(
                        fetch_graph_hints(task, str(self.project_dir))
                    )
                except Exception:
                    # Graphiti is optional - fail gracefully;
                    # graph_hints remains [] from initial assignment
                    pass

        return TaskContext(
            task_description=task,
            scoped_services=services,
            files_to_modify=[
                asdict(f) if isinstance(f, FileMatch) else f for f in files_to_modify
            ],
            files_to_reference=[
                asdict(f) if isinstance(f, FileMatch) else f for f in files_to_reference
            ],
            patterns_discovered=patterns,
            service_contexts=service_contexts,
            graph_hints=graph_hints,
        )

    async def build_context_async(
        self,
        task: str,
        services: list[str] | None = None,
        keywords: list[str] | None = None,
        include_graph_hints: bool = True,
        semantic_search: bool = False,
    ) -> TaskContext:
        """
        Build context for a specific task (async version).

        This version is preferred when called from async code as it can
        properly await the graph hints retrieval and semantic search.

        Args:
            task: Description of the task
            services: List of service names to search (None = auto-detect)
            keywords: Additional keywords to search for
            include_graph_hints: Whether to include historical hints from Graphiti
            semantic_search: Whether to use semantic search with embeddings

        Returns:
            TaskContext with relevant files and patterns
        """
        # Auto-detect services if not specified
        if not services:
            services = self.service_matcher.suggest_services(task)

        # Extract keywords from task if not provided
        if not keywords:
            keywords = self.keyword_extractor.extract_keywords(task)

        # Search each service
        all_matches: list[FileMatch] = []
        service_contexts = {}

        if self.searcher and self.project_dir:
            for service_name in services:
                service_info = self.project_index.get("services", {}).get(service_name)
                if not service_info:
                    continue

                service_path = Path(service_info.get("path", service_name))
                if not service_path.is_absolute():
                    service_path = self.project_dir / service_path

                # Search this service
                # Use semantic search if available, otherwise fall back to keyword search
                if self.semantic_scorer:
                    try:
                        matches = await self.searcher.search_with_semantics(
                            service_path, service_name, keywords, task
                        )
                    except Exception as e:
                        logger.warning(
                            f"Semantic search failed for {service_name}, falling back: {e}"
                        )
                        matches = self.searcher.search_service(
                            service_path, service_name, keywords
                        )
                else:
                    matches = self.searcher.search_service(
                        service_path, service_name, keywords
                    )

                all_matches.extend(matches)

                # If semantic search is enabled, also search using embeddings
                if semantic_search:
                    semantic_matches = self.searcher.search_semantic(
                        service_path, service_name, task
                    )
                    all_matches.extend(semantic_matches)

                # Load or generate service context
                service_contexts[service_name] = self._get_service_context(
                    service_path, service_name, service_info
                )

        # Prioritize matches using recency and dependency analysis
        all_matches = self._prioritize_matches(all_matches)

        # Apply user priorities to filter and sort matches
        if self.priority_manager:
            all_matches = self.priority_manager.apply_priorities(
                all_matches, exclude_never=True, sort=True
            )

        # Log priority application
        if all_matches:
            logger.debug(f"Applied user priorities to {len(all_matches)} files")

        # Detect and remove redundant files
        if self.redundancy_detector:
            all_matches, redundancy_report = (
                self.redundancy_detector.detect_redundancies(
                    all_matches, keep_highest_relevance=True
                )
            )

            # Log redundancy report
            if redundancy_report:
                logger.info(
                    f"Removed {len(redundancy_report)} redundant files from context: "
                    f"{sum(r.get('tokens_saved', 0) for r in redundancy_report)} tokens saved"
                )

        # Categorize matches after redundancy removal
        files_to_modify, files_to_reference = self.categorizer.categorize_matches(
            all_matches, task
        )

        # Discover patterns from reference files
        patterns = []
        if self.pattern_discoverer:
            patterns = self.pattern_discoverer.discover_patterns(
                files_to_reference, keywords
            )

        # Get graph hints asynchronously
        graph_hints = []
        if include_graph_hints:
            graph_hints = await fetch_graph_hints(task, str(self.project_dir))

        return TaskContext(
            task_description=task,
            scoped_services=services,
            files_to_modify=[
                asdict(f) if isinstance(f, FileMatch) else f for f in files_to_modify
            ],
            files_to_reference=[
                asdict(f) if isinstance(f, FileMatch) else f for f in files_to_reference
            ],
            patterns_discovered=patterns,
            service_contexts=service_contexts,
            graph_hints=graph_hints,
        )

    def _get_service_context(
        self,
        service_path: Path,
        service_name: str,
        service_info: dict,
    ) -> dict:
        """Get or generate context for a service."""
        # Check for SERVICE_CONTEXT.md
        context_file = service_path / "SERVICE_CONTEXT.md"
        if context_file.exists():
            return {
                "source": "SERVICE_CONTEXT.md",
                "content": context_file.read_text(encoding="utf-8")[
                    :2000
                ],  # First 2000 chars
            }

        # Generate basic context from service info
        return {
            "source": "generated",
            "language": service_info.get("language"),
            "framework": service_info.get("framework"),
            "type": service_info.get("type"),
            "entry_point": service_info.get("entry_point"),
            "key_directories": service_info.get("key_directories", {}),
        }

    def _get_available_files(self) -> list[str]:
        """
        Get list of available files in the project for prediction.

        Returns:
            List of relative file paths from project root
        """
        if not self.project_dir:
            return []

        available_files: list[str] = []
        exclude_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".venv",
            "venv",
            "dist",
            "build",
            ".auto-claude",
            ".worktrees",
        }

        try:
            for root, dirs, files in os.walk(self.project_dir):
                root_path = Path(root)
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    if file.endswith(
                        (
                            ".py",
                            ".ts",
                            ".tsx",
                            ".js",
                            ".jsx",
                            ".vue",
                            ".go",
                            ".rs",
                            ".java",
                            ".md",
                        )
                    ):
                        file_path = root_path / file
                        try:
                            rel_path = file_path.relative_to(self.project_dir)
                            available_files.append(str(rel_path))
                        except ValueError:
                            continue
        except (OSError, PermissionError):
            pass

        return available_files

    def preload_context(
        self,
        task: str,
        max_files: int = 10,
        min_score: float = 0.2,
        skip_cache: bool = False,
    ) -> dict:
        """
        Predict and preload file contents for a task.

        Args:
            task: Task description
            max_files: Maximum number of files to preload
            min_score: Minimum relevance score to preload
            skip_cache: If True, reload files even if cached

        Returns:
            Dictionary with preloading results
        """
        if not self.preloader:
            return {
                "predictions": [],
                "preloaded": 0,
                "cached": 0,
                "failed": 0,
                "total": 0,
                "error": "Preloader not initialized (cache_dir required)",
            }

        return self.preloader.preload_context(task, max_files, min_score, skip_cache)

    def get_preloaded_content(self, file_path: str) -> str | None:
        """
        Get preloaded content for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            File content if cached, None otherwise
        """
        if not self.preloader:
            return None

        return self.preloader.get_preloaded_content(file_path)

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (file count, size, age)
        """
        if not self.preloader:
            return {"error": "Preloader not initialized"}

        return self.preloader.get_cache_stats()

    def clear_preload_cache(self) -> None:
        """Clear all preloaded content from cache."""
        if self.preloader:
            self.preloader.clear_cache()

    def _prioritize_matches(self, matches: list[FileMatch]) -> list[FileMatch]:
        """
        Prioritize file matches using recency and dependency analysis.

        Enhances relevance scores by:
        1. Applying recency scoring (70% relevance, 30% recency)
        2. Boosting scores for high-impact files (many dependents)

        Args:
            matches: List of FileMatch objects from search

        Returns:
            Prioritized list of FileMatch objects
        """
        if not matches or not self.prioritizer:
            return matches if matches else []

        # Apply recency-based prioritization
        prioritized = self.prioritizer.prioritize_matches(matches)

        # Enhance with dependency impact scores
        if self.dependency_analyzer:
            for match in prioritized:
                try:
                    impact_score = self.dependency_analyzer.calculate_impact_score(
                        match.path
                    )
                    # Boost relevance by 10% of impact score (0-1 range)
                    if impact_score > 0 and hasattr(match, "relevance_score"):
                        match.relevance_score += impact_score * 0.1
                except (FileNotFoundError, ValueError, AttributeError):
                    continue

        # Re-sort after applying dependency boost
        prioritized.sort(key=lambda m: m.relevance_score, reverse=True)

        return prioritized

    # Token Budget Manager Methods

    def reset_token_usage(self) -> None:
        """Reset the token usage counter."""
        self._token_usage = 0

    def get_token_usage(self) -> int:
        """Get the current token usage."""
        return self._token_usage

    def get_remaining_budget(self) -> int | None:
        """
        Get the remaining token budget.

        Returns:
            Remaining tokens, or None if no budget is set
        """
        if self.token_budget is None:
            return None
        return max(0, self.token_budget - self._token_usage)

    def is_within_budget(self, additional_tokens: int = 0) -> bool:
        """
        Check if we're within the token budget.

        Args:
            additional_tokens: Additional tokens to account for

        Returns:
            True if within budget or no budget is set, False otherwise
        """
        if self.token_budget is None:
            return True
        return (self._token_usage + additional_tokens) <= self.token_budget

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Input text to tokenize

        Returns:
            Number of tokens in the text
        """
        return self.token_counter.count_tokens(text)

    def count_and_track_tokens(self, text: str) -> int:
        """
        Count tokens and add to usage tracking.

        Args:
            text: Input text to tokenize

        Returns:
            Number of tokens counted
        """
        tokens = self.token_counter.count_tokens(text)
        self._token_usage += tokens
        return tokens

    def deduplicate_files(self, files: list[dict]) -> list[dict]:
        """
        Remove duplicate files from a list.

        Args:
            files: List of file dictionaries with content

        Returns:
            List with duplicate files removed
        """
        return self.deduplicator.deduplicate_files(files)

    def get_budget_stats(self) -> dict:
        """
        Get token budget statistics.

        Returns:
            Dictionary with budget usage statistics
        """
        stats = {
            "total_usage": self._token_usage,
            "budget": self.token_budget,
            "remaining": self.get_remaining_budget(),
            "within_budget": self.is_within_budget(),
        }

        if self.token_budget is not None:
            stats["usage_percent"] = (
                (self._token_usage / self.token_budget * 100)
                if self.token_budget > 0
                else 0.0
            )
        else:
            stats["usage_percent"] = None

        return stats
