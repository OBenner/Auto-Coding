"""
Pattern Discovery
=================

Discovers code patterns from reference files to guide implementation.
Enhanced with Graphiti memory integration for semantic pattern search
and auto-generated pattern libraries.
"""

import logging
from pathlib import Path

from core.sentry import capture_exception

from .models import FileMatch

logger = logging.getLogger(__name__)


def _load_library_patterns(project_dir: Path) -> dict[str, str]:
    """
    Load patterns from auto-generated language-specific libraries.

    Detects the project's programming languages and loads corresponding
    pattern libraries (e.g., go_patterns, php_patterns, etc.)

    Args:
        project_dir: Project root directory

    Returns:
        Dictionary mapping pattern keys to code snippets from libraries
    """
    library_patterns = {}

    def _extract_patterns(
        lang: str, category: str, patterns_dict: dict, prefix: str = ""
    ):
        """Recursively extract patterns from nested dictionaries."""
        for pattern_name, pattern_value in patterns_dict.items():
            if isinstance(pattern_value, dict):
                # Nested category (e.g., frameworks.gin)
                new_prefix = f"{prefix}_{pattern_name}" if prefix else pattern_name
                _extract_patterns(lang, category, pattern_value, new_prefix)
            elif isinstance(pattern_value, str):
                # Actual pattern code
                full_pattern_name = (
                    f"{prefix}_{pattern_name}" if prefix else pattern_name
                )
                pattern_key = f"library_{lang}_{category}_{full_pattern_name}"
                pattern_text = (
                    f"Language: {lang}\n"
                    f"Category: {category}\n"
                    f"Pattern: {full_pattern_name}\n\n"
                    f"{pattern_value}"
                )
                library_patterns[pattern_key] = pattern_text

    try:
        from patterns import load_language_patterns
        from project import get_or_create_profile

        # Get project's detected languages
        profile = get_or_create_profile(project_dir)
        languages = profile.detected_stack.languages

        if not languages:
            logger.debug("No languages detected for library pattern loading")
            return library_patterns

        # Load patterns for each detected language
        for language in languages:
            lang_patterns = load_language_patterns(language)
            if lang_patterns:
                # Extract patterns from the library module
                # Pattern libraries contain categorized dictionaries
                for category_name, category_patterns in lang_patterns.items():
                    if isinstance(category_patterns, dict):
                        _extract_patterns(language, category_name, category_patterns)

                pattern_count = len(
                    [k for k in library_patterns.keys() if f"library_{language}_" in k]
                )
                if pattern_count > 0:
                    logger.info(
                        f"Loaded {pattern_count} patterns from {language} library"
                    )

    except ImportError as e:
        logger.debug(f"Pattern libraries not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to load library patterns: {e}")
        capture_exception(
            e,
            project_dir=str(project_dir),
            operation="_load_library_patterns",
        )

    return library_patterns


async def discover_with_memory(
    task: str,
    spec_dir: Path,
    project_dir: Path,
    reference_files: list[FileMatch] | None = None,
    keywords: list[str] | None = None,
    categories: list[str] | None = None,
    num_results: int = 5,
    min_score: float = 0.5,
    include_file_patterns: bool = True,
    include_library_patterns: bool = True,
) -> dict[str, str]:
    """
    Discover code patterns by querying Graphiti memory and pattern libraries.

    This function provides comprehensive pattern discovery by:
    1. Querying Graphiti for semantically relevant patterns
    2. Loading auto-generated language-specific pattern libraries
    3. Optionally combining with traditional file-based pattern discovery
    4. Returning unified pattern suggestions

    Args:
        task: Task description to search for relevant patterns
        spec_dir: Spec directory for memory context
        project_dir: Project root directory
        reference_files: Optional list of FileMatch objects for file-based patterns
        keywords: Optional keywords to search in files
        categories: Optional pattern categories to filter by (e.g., ["api-usage", "error-handling"])
        num_results: Maximum number of Graphiti patterns to retrieve (default: 5)
        min_score: Minimum relevance score for Graphiti patterns 0.0-1.0 (default: 0.5)
        include_file_patterns: Whether to also include file-based patterns (default: True)
        include_library_patterns: Whether to include auto-generated library patterns (default: True)

    Returns:
        Dictionary mapping pattern keys to pattern descriptions/snippets:
        {
            "graphiti_pattern_0": "Pattern: Use async/await for API calls\nCategory: api-usage\nConfidence: 0.95",
            "graphiti_pattern_1": "Pattern: Always log errors with context\nCategory: error-handling\nConfidence: 0.87",
            "library_go_ERROR_HANDLING_PATTERNS_basic_error_check": "Language: go\nCategory: ERROR_HANDLING_PATTERNS\n...",
            "file_pattern_keyword": "From path/to/file.py:\n<code snippet>",
            ...
        }
    """
    patterns = {}

    # Try Graphiti memory first
    try:
        from memory.graphiti_helpers import get_graphiti_memory

        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is not None:
            try:
                from integrations.graphiti.pattern_suggester import suggest_patterns

                # Get pattern suggestions from Graphiti
                graphiti_patterns = await suggest_patterns(
                    client=memory.client,
                    group_id=memory.group_id,
                    spec_context_id=memory.spec_context_id,
                    query=task,
                    categories=categories,
                    num_results=num_results,
                    min_score=min_score,
                    include_project_context=True,
                    project_dir=project_dir,
                )

                if graphiti_patterns:
                    # Format Graphiti patterns for output
                    for i, pattern_data in enumerate(graphiti_patterns):
                        pattern_text = pattern_data.get("pattern", "")
                        category = pattern_data.get("category", "uncategorized")
                        confidence = pattern_data.get("confidence", 0.0)
                        reasoning = pattern_data.get("reasoning", "")

                        # Create formatted pattern entry
                        pattern_key = f"graphiti_pattern_{i}"
                        pattern_value = f"Pattern: {pattern_text}\nCategory: {category}\nConfidence: {confidence:.2f}"
                        if reasoning:
                            pattern_value += f"\nReasoning: {reasoning}"

                        patterns[pattern_key] = pattern_value

                    logger.info(
                        f"Found {len(graphiti_patterns)} patterns from Graphiti for task: {task[:50]}..."
                    )
            finally:
                await memory.close()

    except ImportError:
        logger.debug("Graphiti memory not available, skipping memory-based patterns")
    except Exception as e:
        logger.warning(f"Failed to query Graphiti for patterns: {e}")
        capture_exception(
            e,
            task_summary=task[:100] if task else "",
            categories=categories,
            operation="discover_with_memory",
        )

    # Add auto-generated library patterns
    if include_library_patterns:
        library_patterns = _load_library_patterns(project_dir)
        if library_patterns:
            patterns.update(library_patterns)
            logger.info(
                f"Added {len(library_patterns)} patterns from language-specific libraries"
            )

    # Optionally add file-based patterns
    if include_file_patterns and reference_files and keywords:
        discoverer = PatternDiscoverer(project_dir)
        file_patterns = discoverer.discover_patterns(
            reference_files=reference_files,
            keywords=keywords,
        )
        # Merge file patterns (file patterns won't override Graphiti patterns due to different keys)
        patterns.update(file_patterns)

    return patterns


class PatternDiscoverer:
    """Discovers code patterns from reference files and language libraries."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()

    def discover_patterns(
        self,
        reference_files: list[FileMatch],
        keywords: list[str],
        max_files: int = 5,
        include_library_patterns: bool = True,
    ) -> dict[str, str]:
        """
        Discover code patterns from reference files and language libraries.

        Args:
            reference_files: List of FileMatch objects to analyze
            keywords: Keywords to look for in the code
            max_files: Maximum number of files to analyze
            include_library_patterns: Whether to include auto-generated library patterns

        Returns:
            Dictionary mapping pattern keys to code snippets
        """
        patterns = {}

        # Add auto-generated library patterns first
        if include_library_patterns:
            library_patterns = _load_library_patterns(self.project_dir)
            patterns.update(library_patterns)

        # Add file-based patterns
        for match in reference_files[:max_files]:
            try:
                file_path = self.project_dir / match.path
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Look for common patterns
                for keyword in keywords:
                    if keyword in content.lower():
                        # Extract a snippet around the keyword
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if keyword in line.lower():
                                # Get context (3 lines before and after)
                                start = max(0, i - 3)
                                end = min(len(lines), i + 4)
                                snippet = "\n".join(lines[start:end])

                                pattern_key = f"{keyword}_pattern"
                                if pattern_key not in patterns:
                                    patterns[pattern_key] = (
                                        f"From {match.path}:\n{snippet[:300]}"
                                    )
                                break

            except (OSError, UnicodeDecodeError):
                continue

        return patterns
