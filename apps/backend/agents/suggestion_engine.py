"""
Suggestion Engine Module
========================

Real-time code analysis engine for AI pair programming mode.

Provides:
- Real-time code analysis as developer types
- Context-aware code suggestions
- Inline refactoring recommendations
- Integration with Claude SDK for AI-powered suggestions
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.client import create_client
from core.sentry import capture_exception

logger = logging.getLogger(__name__)


@dataclass
class CodeContext:
    """
    Context information for code analysis.

    Attributes:
        file_path: Path to the file being edited
        content: Current file content
        cursor_position: Cursor position (line, column)
        selection: Selected text range (if any)
        language: Programming language
    """

    file_path: Path
    content: str
    cursor_position: tuple[int, int]
    selection: tuple[int, int, int, int] | None = None  # start_line, start_col, end_line, end_col
    language: str | None = None


@dataclass
class Suggestion:
    """
    Code suggestion from the analysis engine.

    Attributes:
        type: Type of suggestion (completion, refactor, fix, explanation)
        content: Suggested code or explanation
        confidence: Confidence score (0.0 - 1.0)
        range: Line/column range where suggestion applies
        description: Human-readable description
        reasoning: Why this suggestion was made
    """

    type: str  # "completion" | "refactor" | "fix" | "explanation"
    content: str
    confidence: float
    range: tuple[int, int, int, int] | None  # start_line, start_col, end_line, end_col
    description: str
    reasoning: str | None = None


class SuggestionEngine:
    """
    Real-time code analysis and suggestion engine.

    Analyzes code as the developer types and generates context-aware
    suggestions using Claude SDK for AI-powered analysis.
    """

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_thinking_tokens: int | None = None,
    ):
        """
        Initialize the suggestion engine.

        Args:
            project_dir: Root directory of the project
            spec_dir: Spec directory (optional, for memory context)
            model: Claude model to use for suggestions
            max_thinking_tokens: Max thinking tokens for AI analysis
        """
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.model = model
        self.max_thinking_tokens = max_thinking_tokens
        self._client = None
        self._suggestion_cache: dict[str, list[Suggestion]] = {}

        logger.info(
            f"Initialized SuggestionEngine for {project_dir} with model {model}"
        )

    async def analyze_code(
        self,
        context: CodeContext,
        suggestion_type: str | None = None,
    ) -> list[Suggestion]:
        """
        Analyze code and generate suggestions.

        Args:
            context: Code context information
            suggestion_type: Type of suggestions to generate (None for all types)

        Returns:
            List of suggestions ordered by confidence
        """
        try:
            # Generate cache key from context
            cache_key = self._get_cache_key(context)

            # Check cache for recent suggestions
            if cache_key in self._suggestion_cache:
                logger.debug(f"Using cached suggestions for {context.file_path}")
                return self._suggestion_cache[cache_key]

            # Generate suggestions using AI
            suggestions = await self._generate_suggestions(context, suggestion_type)

            # Cache results
            self._suggestion_cache[cache_key] = suggestions

            # Limit cache size
            if len(self._suggestion_cache) > 100:
                # Remove oldest entries
                keys_to_remove = list(self._suggestion_cache.keys())[:50]
                for key in keys_to_remove:
                    del self._suggestion_cache[key]

            logger.info(
                f"Generated {len(suggestions)} suggestions for {context.file_path}"
            )

            return suggestions

        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            capture_exception(e)
            return []

    async def get_inline_completion(
        self,
        context: CodeContext,
    ) -> str | None:
        """
        Get inline code completion suggestion.

        Args:
            context: Code context at cursor position

        Returns:
            Completion text or None if no suggestion
        """
        suggestions = await self.analyze_code(context, suggestion_type="completion")

        if suggestions and suggestions[0].confidence > 0.7:
            return suggestions[0].content

        return None

    async def get_refactoring_suggestions(
        self,
        context: CodeContext,
    ) -> list[Suggestion]:
        """
        Get refactoring suggestions for selected code.

        Args:
            context: Code context with selection

        Returns:
            List of refactoring suggestions
        """
        if not context.selection:
            logger.warning("No selection provided for refactoring suggestions")
            return []

        return await self.analyze_code(context, suggestion_type="refactor")

    async def explain_code(
        self,
        context: CodeContext,
    ) -> str | None:
        """
        Generate explanation for selected code.

        Args:
            context: Code context with selection

        Returns:
            Explanation text or None
        """
        suggestions = await self.analyze_code(context, suggestion_type="explanation")

        if suggestions:
            return suggestions[0].content

        return None

    def clear_cache(self) -> None:
        """Clear the suggestion cache."""
        self._suggestion_cache.clear()
        logger.debug("Cleared suggestion cache")

    def _get_cache_key(self, context: CodeContext) -> str:
        """
        Generate cache key from context.

        Args:
            context: Code context

        Returns:
            Cache key string
        """
        # Create hash of file path, cursor position, and content snippet
        line, col = context.cursor_position
        content_snippet = context.content[:1000]  # First 1000 chars

        return f"{context.file_path}:{line}:{col}:{hash(content_snippet)}"

    async def _generate_suggestions(
        self,
        context: CodeContext,
        suggestion_type: str | None = None,
    ) -> list[Suggestion]:
        """
        Generate suggestions using Claude SDK.

        Args:
            context: Code context
            suggestion_type: Type of suggestions to generate

        Returns:
            List of suggestions
        """
        # This is a placeholder implementation
        # In a full implementation, this would:
        # 1. Create a Claude SDK client
        # 2. Build a prompt with code context
        # 3. Request suggestions from the AI
        # 4. Parse and rank the suggestions

        # For now, return empty list
        # The actual AI integration will be implemented in later subtasks
        logger.debug(
            f"_generate_suggestions called for {context.file_path} "
            f"(type: {suggestion_type})"
        )

        # Placeholder: Return empty suggestions
        # TODO: Implement AI-powered suggestion generation
        return []

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.clear_cache()
        return False


async def create_suggestion_engine(
    project_dir: Path,
    spec_dir: Path | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    max_thinking_tokens: int | None = None,
) -> SuggestionEngine:
    """
    Factory function to create a configured SuggestionEngine.

    Args:
        project_dir: Root directory of the project
        spec_dir: Spec directory (optional)
        model: Claude model to use
        max_thinking_tokens: Max thinking tokens

    Returns:
        Configured SuggestionEngine instance
    """
    return SuggestionEngine(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        max_thinking_tokens=max_thinking_tokens,
    )
