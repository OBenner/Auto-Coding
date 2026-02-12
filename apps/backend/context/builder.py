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
from .graphiti_integration import fetch_graph_hints, is_graphiti_enabled
from .keyword_extractor import KeywordExtractor
from .models import FileMatch, TaskContext
from .pattern_discovery import PatternDiscoverer
from .preloader import ContextPreloader
from .search import CodeSearcher
from .service_matcher import ServiceMatcher


class ContextBuilder:
    """Builds task-specific context by searching the codebase."""

    def __init__(
        self,
        project_dir: Path | None,
        project_index: dict | None = None,
        cache_dir: Path | None = None,
    ):
        self.project_dir = project_dir.resolve() if project_dir else None
        self.project_index = project_index or self._load_project_index()
        self.cache_dir = cache_dir

        # Initialize components
        self.searcher = CodeSearcher(self.project_dir) if self.project_dir else None
        self.service_matcher = ServiceMatcher(self.project_index)
        self.keyword_extractor = KeywordExtractor()
        self.categorizer = FileCategorizer()
        self.pattern_discoverer = (
            PatternDiscoverer(self.project_dir) if self.project_dir else None
        )

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

        if self.searcher and self.project_dir:
            for service_name in services:
                service_info = self.project_index.get("services", {}).get(service_name)
                if not service_info:
                    continue

                service_path = Path(service_info.get("path", service_name))
                if not service_path.is_absolute():
                    service_path = self.project_dir / service_path

                # Search this service
                matches = self.searcher.search_service(
                    service_path, service_name, keywords
                )
                all_matches.extend(matches)

                # Load or generate service context
                service_contexts[service_name] = self._get_service_context(
                    service_path, service_name, service_info
                )

        # Categorize matches
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
                # Run the async function in a new event loop if necessary
                try:
                    asyncio.get_running_loop()
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

        if self.searcher and self.project_dir:
            for service_name in services:
                service_info = self.project_index.get("services", {}).get(service_name)
                if not service_info:
                    continue

                service_path = Path(service_info.get("path", service_name))
                if not service_path.is_absolute():
                    service_path = self.project_dir / service_path

                # Search this service
                matches = self.searcher.search_service(
                    service_path, service_name, keywords
                )
                all_matches.extend(matches)

                # Load or generate service context
                service_contexts[service_name] = self._get_service_context(
                    service_path, service_name, service_info
                )

        # Categorize matches
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

        available_files = []
        try:
            # Walk through project directory to collect Python/TypeScript/JavaScript files
            # Exclude common directories to avoid noise
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

            for root, dirs, files in self.project_dir.walk():
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    # Include common code file extensions
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
                        file_path = Path(root) / file
                        try:
                            rel_path = file_path.relative_to(self.project_dir)
                            available_files.append(str(rel_path))
                        except ValueError:
                            # Skip files outside project_dir
                            continue

        except (OSError, PermissionError):
            # If we can't walk the directory, return empty list
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

        This method uses the preloader to predict which files are likely
        to be modified for the given task and preloads them into cache.

        Args:
            task: Task description
            max_files: Maximum number of files to preload
            min_score: Minimum relevance score to preload
            skip_cache: If True, reload files even if cached

        Returns:
            Dictionary with preloading results:
            - predictions: List of file prediction dictionaries
            - preloaded: Number of files successfully preloaded
            - cached: Number of files already cached
            - failed: Number of files that failed to load
            - total: Total number of predictions
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
