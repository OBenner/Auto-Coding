"""
Context Builder
===============

Main builder class that orchestrates context building for tasks.
"""

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from .categorizer import FileCategorizer
from .deduplicator import ContentDeduplicator
from .dependency_analyzer import DependencyAnalyzer
from .graphiti_integration import fetch_graph_hints, is_graphiti_enabled
from .keyword_extractor import KeywordExtractor
from .models import FileMatch, TaskContext
from .pattern_discovery import PatternDiscoverer
from .prioritizer import FilePrioritizer
from .search import CodeSearcher
from .service_matcher import ServiceMatcher
from .token_counter import TokenCounter


class ContextBuilder:
    """Builds task-specific context by searching the codebase."""

    def __init__(
        self,
        project_dir: Path,
        project_index: dict | None = None,
        token_budget: int | None = None,
    ):
        self.project_dir = project_dir.resolve()
        self.project_index = project_index or self._load_project_index()
        self.token_budget = token_budget

        # Initialize components
        self.searcher = CodeSearcher(self.project_dir)
        self.service_matcher = ServiceMatcher(self.project_index)
        self.keyword_extractor = KeywordExtractor()
        self.categorizer = FileCategorizer()
        self.pattern_discoverer = PatternDiscoverer(self.project_dir)

        # Initialize prioritization components
        self.prioritizer = FilePrioritizer(self.project_dir)
        self.dependency_analyzer = DependencyAnalyzer(self.project_dir)

        # Initialize token budget manager components
        self.token_counter = TokenCounter()
        self.deduplicator = ContentDeduplicator()
        self._token_usage = 0

    def _load_project_index(self) -> dict:
        """Load project index from file or create new one (.auto-claude is the installed instance)."""
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

    def build_context(
        self,
        task: str,
        services: list[str] | None = None,
        keywords: list[str] | None = None,
        include_graph_hints: bool = True,
    ) -> TaskContext:
        """
        Build context for a specific task.

        Args:
            task: Description of the task
            services: List of service names to search (None = auto-detect)
            keywords: Additional keywords to search for
            include_graph_hints: Whether to include historical hints from Graphiti

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

        for service_name in services:
            service_info = self.project_index.get("services", {}).get(service_name)
            if not service_info:
                continue

            service_path = Path(service_info.get("path", service_name))
            if not service_path.is_absolute():
                service_path = self.project_dir / service_path

            # Search this service
            matches = self.searcher.search_service(service_path, service_name, keywords)
            all_matches.extend(matches)

            # Load or generate service context
            service_contexts[service_name] = self._get_service_context(
                service_path, service_name, service_info
            )

        # Prioritize matches using recency and dependency analysis
        all_matches = self._prioritize_matches(all_matches)

        # Categorize matches
        files_to_modify, files_to_reference = self.categorizer.categorize_matches(
            all_matches, task
        )

        # Discover patterns from reference files
        patterns = self.pattern_discoverer.discover_patterns(
            files_to_reference, keywords
        )

        # Get graph hints (synchronously wrap async call)
        graph_hints = []
        if include_graph_hints and is_graphiti_enabled():
            try:
                # Run the async function in a new event loop if necessary
                try:
                    loop = asyncio.get_running_loop()
                    # We're already in an async context - this shouldn't happen in CLI
                    # but handle it gracefully
                    graph_hints = []
                except RuntimeError:
                    # No event loop running - create one
                    graph_hints = asyncio.run(
                        fetch_graph_hints(task, str(self.project_dir))
                    )
            except Exception:
                # Graphiti is optional - fail gracefully
                graph_hints = []

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
    ) -> TaskContext:
        """
        Build context for a specific task (async version).

        This version is preferred when called from async code as it can
        properly await the graph hints retrieval.

        Args:
            task: Description of the task
            services: List of service names to search (None = auto-detect)
            keywords: Additional keywords to search for
            include_graph_hints: Whether to include historical hints from Graphiti

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

        for service_name in services:
            service_info = self.project_index.get("services", {}).get(service_name)
            if not service_info:
                continue

            service_path = Path(service_info.get("path", service_name))
            if not service_path.is_absolute():
                service_path = self.project_dir / service_path

            # Search this service
            matches = self.searcher.search_service(service_path, service_name, keywords)
            all_matches.extend(matches)

            # Load or generate service context
            service_contexts[service_name] = self._get_service_context(
                service_path, service_name, service_info
            )

        # Prioritize matches using recency and dependency analysis
        all_matches = self._prioritize_matches(all_matches)

        # Categorize matches
        files_to_modify, files_to_reference = self.categorizer.categorize_matches(
            all_matches, task
        )

        # Discover patterns from reference files
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
        if not matches:
            return []

        # Apply recency-based prioritization
        prioritized = self.prioritizer.prioritize_matches(matches)

        # Enhance with dependency impact scores
        for match in prioritized:
            try:
                impact_score = self.dependency_analyzer.calculate_impact_score(
                    match.path
                )
                # Boost relevance by 10% of impact score (0-1 range)
                if impact_score > 0:
                    match.relevance_score += impact_score * 0.1
            except (FileNotFoundError, ValueError):
                # File might not be Python or not analyzable - skip
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
