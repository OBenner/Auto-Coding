"""
Pattern Learner
===============

Monitors agent code generation and automatically learns patterns from generated code.
Integrates with PatternExtractor to analyze code changes and stores discovered patterns
in Graphiti memory for future reference.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.sentry import capture_exception
from debug import (
    debug,
    debug_detailed,
    debug_error,
    debug_success,
    debug_warning,
    is_debug_enabled,
)
from graphiti_config import is_graphiti_enabled

from .pattern_extractor import PatternExtractor

logger = logging.getLogger(__name__)


class PatternLearner:
    """
    Monitors agent code generation and learns patterns from generated code.

    This class watches for code changes during agent sessions, extracts patterns
    using PatternExtractor, and stores them in Graphiti memory for future reference.
    """

    def __init__(self, spec_dir: Path, project_dir: Path):
        """
        Initialize pattern learner.

        Args:
            spec_dir: Spec directory (for Graphiti namespace)
            project_dir: Project root directory
        """
        self.spec_dir = spec_dir.resolve()
        self.project_dir = project_dir.resolve()
        self.pattern_extractor = PatternExtractor(project_dir)
        self._learned_patterns: list[dict[str, Any]] = []
        self._monitored_files: set[Path] = set()

        if is_debug_enabled():
            debug(
                "patterns",
                "PatternLearner initialized",
                spec_dir=str(self.spec_dir.name),
                project_dir=str(self.project_dir.name),
            )

    async def learn_from_file(
        self,
        file_path: Path,
        pattern_types: list[str] | None = None,
        store_immediately: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Learn patterns from a single file.

        Args:
            file_path: Path to file to analyze
            pattern_types: Optional list of pattern types to extract
                          (e.g., ["api", "error", "state"])
            store_immediately: Whether to store patterns in Graphiti immediately

        Returns:
            List of extracted patterns
        """
        if is_debug_enabled():
            debug(
                "patterns",
                "Learning patterns from file",
                file_path=str(file_path),
                pattern_types=pattern_types,
            )

        try:
            # Extract patterns from the file
            patterns = self.pattern_extractor.extract_patterns(
                file_path, pattern_types=pattern_types
            )

            if not patterns:
                if is_debug_enabled():
                    debug(
                        "patterns",
                        "No patterns found in file",
                        file_path=str(file_path),
                    )
                return []

            # Add file path to each pattern for tracking
            for pattern in patterns:
                pattern["file_path"] = str(file_path.relative_to(self.project_dir))

            # Track learned patterns
            self._learned_patterns.extend(patterns)
            self._monitored_files.add(file_path.resolve())

            if is_debug_enabled():
                debug_success(
                    "patterns",
                    "Patterns extracted from file",
                    file_path=str(file_path),
                    pattern_count=len(patterns),
                )

            # Store in Graphiti if requested
            if store_immediately and is_graphiti_enabled():
                stored_count = await self._store_patterns(patterns)
                if is_debug_enabled():
                    debug_success(
                        "patterns",
                        "Patterns stored in Graphiti",
                        stored_count=stored_count,
                        total_extracted=len(patterns),
                    )

            return patterns

        except Exception as e:
            logger.warning(f"Failed to learn patterns from {file_path}: {e}")
            if is_debug_enabled():
                debug_error(
                    "patterns",
                    "Pattern learning failed",
                    file_path=str(file_path),
                    error=str(e),
                )
            capture_exception(
                e,
                operation="learn_from_file",
                file_path=str(file_path),
            )
            return []

    async def learn_from_files(
        self,
        file_paths: list[Path],
        pattern_types: list[str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Learn patterns from multiple files.

        Args:
            file_paths: List of file paths to analyze
            pattern_types: Optional list of pattern types to extract

        Returns:
            Dictionary mapping file paths to extracted patterns
        """
        if is_debug_enabled():
            debug(
                "patterns",
                "Learning patterns from multiple files",
                file_count=len(file_paths),
                pattern_types=pattern_types,
            )

        results = {}
        total_patterns = 0

        for file_path in file_paths:
            patterns = await self.learn_from_file(
                file_path,
                pattern_types=pattern_types,
                store_immediately=False,  # Store all at once at the end
            )
            if patterns:
                results[str(file_path)] = patterns
                total_patterns += len(patterns)

        # Store all patterns at once
        if total_patterns > 0 and is_graphiti_enabled():
            all_patterns = [p for patterns in results.values() for p in patterns]
            stored_count = await self._store_patterns(all_patterns)
            if is_debug_enabled():
                debug_success(
                    "patterns",
                    "Batch pattern learning complete",
                    files_processed=len(file_paths),
                    patterns_found=total_patterns,
                    patterns_stored=stored_count,
                )

        return results

    async def learn_from_session(
        self,
        modified_files: list[Path],
        pattern_types: list[str] | None = None,
    ) -> int:
        """
        Learn patterns from an agent session's modified files.

        This is the primary entry point for pattern learning during agent sessions.
        It analyzes all files modified during a session and stores the learned patterns.

        Args:
            modified_files: List of files modified during the session
            pattern_types: Optional list of pattern types to extract
                          Defaults to ["api", "error", "state", "import"]

        Returns:
            Total number of patterns learned
        """
        if not modified_files:
            if is_debug_enabled():
                debug("patterns", "No modified files to learn from")
            return 0

        # Default to key pattern types if not specified
        if pattern_types is None:
            pattern_types = ["api", "error", "state", "import"]

        if is_debug_enabled():
            debug(
                "patterns",
                "Learning patterns from agent session",
                modified_files_count=len(modified_files),
                pattern_types=pattern_types,
            )

        # Filter to only code files
        code_extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".go", ".rs"}
        code_files = [f for f in modified_files if f.suffix.lower() in code_extensions]

        if not code_files:
            if is_debug_enabled():
                debug_warning(
                    "patterns",
                    "No code files in modified files list",
                    total_files=len(modified_files),
                )
            return 0

        # Learn from all code files
        results = await self.learn_from_files(code_files, pattern_types=pattern_types)
        total_patterns = sum(len(patterns) for patterns in results.values())

        if is_debug_enabled():
            debug_success(
                "patterns",
                "Session pattern learning complete",
                code_files_analyzed=len(code_files),
                total_patterns_learned=total_patterns,
            )

        return total_patterns

    async def _store_patterns(self, patterns: list[dict[str, Any]]) -> int:
        """
        Store patterns in Graphiti memory.

        Args:
            patterns: List of pattern dictionaries to store

        Returns:
            Number of patterns successfully stored
        """
        if not is_graphiti_enabled():
            if is_debug_enabled():
                debug_warning(
                    "patterns", "Graphiti not enabled, skipping pattern storage"
                )
            return 0

        try:
            # Import here to avoid circular dependency
            from memory.graphiti_helpers import get_graphiti_memory

            from .pattern_store import PatternStore

            memory = await get_graphiti_memory(self.spec_dir, self.project_dir)
            if memory is None:
                if is_debug_enabled():
                    debug_warning(
                        "patterns",
                        "GraphitiMemory not available for pattern storage",
                    )
                return 0

            try:
                store = PatternStore(
                    client=memory.client,
                    group_id=memory.group_id,
                    spec_context_id=memory.spec_context_id,
                    project_dir=self.project_dir,
                )

                # Format patterns for batch storage
                store_patterns = []
                for pattern in patterns:
                    pattern_desc = self._format_pattern_description(pattern)
                    store_patterns.append(
                        {
                            "pattern": pattern_desc,
                            "category": pattern.get("type", "uncategorized"),
                            "confidence": 0.7,  # Initial confidence for learned patterns
                            "metadata": {"reasoning": pattern.get("context", "")},
                        }
                    )

                stored_count = await store.store_patterns_batch(store_patterns)

                if is_debug_enabled():
                    debug_detailed(
                        "patterns",
                        "Pattern storage complete",
                        attempted=len(patterns),
                        stored=stored_count,
                        failed=len(patterns) - stored_count,
                    )

                return stored_count
            finally:
                await memory.close()

        except Exception as e:
            logger.warning(f"Failed to store patterns in Graphiti: {e}")
            if is_debug_enabled():
                debug_error(
                    "patterns",
                    "Pattern storage failed",
                    error=str(e),
                    pattern_count=len(patterns),
                )
            capture_exception(
                e,
                operation="store_patterns",
                pattern_count=len(patterns),
            )
            return 0

    def _format_pattern_description(self, pattern: dict[str, Any]) -> str:
        """
        Format a pattern dictionary into a descriptive string for storage.

        Args:
            pattern: Pattern dictionary from PatternExtractor

        Returns:
            Formatted pattern description
        """
        parts = []

        # Add pattern type and description
        pattern_type = pattern.get("type", "unknown")
        pattern_desc = pattern.get("pattern", "")
        parts.append(f"[{pattern_type}] {pattern_desc}")

        # Add file location
        file_path = pattern.get("file_path", "")
        line_number = pattern.get("line_number", 0)
        if file_path:
            parts.append(f"File: {file_path}:{line_number}")

        # Add code snippet (truncated)
        code_snippet = pattern.get("code_snippet", "")
        if code_snippet:
            # Truncate to first 100 chars
            snippet_short = code_snippet[:100].replace("\n", " ")
            if len(code_snippet) > 100:
                snippet_short += "..."
            parts.append(f"Code: {snippet_short}")

        # Add context
        context = pattern.get("context", "")
        if context:
            parts.append(f"Context: {context}")

        return " | ".join(parts)

    def get_learned_patterns(self) -> list[dict[str, Any]]:
        """
        Get all patterns learned in this session.

        Returns:
            List of learned pattern dictionaries
        """
        return self._learned_patterns.copy()

    def get_monitored_files(self) -> set[Path]:
        """
        Get set of files that have been monitored for patterns.

        Returns:
            Set of monitored file paths
        """
        return self._monitored_files.copy()

    def clear_session(self) -> None:
        """Clear learned patterns and monitored files for a new session."""
        self._learned_patterns.clear()
        self._monitored_files.clear()
        if is_debug_enabled():
            debug("patterns", "Pattern learner session cleared")
