"""
Search Commands
===============

CLI commands for semantic code search with Graphiti memory integration
"""

import sys
from pathlib import Path

# Add apps/backend/ to sys.path so that sibling packages (context/, etc.)
# can be imported when this module is loaded via relative imports from cli/.
# This is the established pattern across all CLI modules in this project.
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from context.enhanced_search import EnhancedCodeSearch
from context.saved_searches import SavedSearches
from integrations.graphiti.memory import get_graphiti_memory
from ui import (
    Icons,
    bold,
    divider,
    icon,
    info,
    muted,
    print_header,
    print_key_value,
    success,
    warning,
)

from .utils import print_banner


async def search_code(
    project_dir: Path,
    query: str,
    search_type: str = "unified",
    limit: int = 20,
    entity_type: str | None = None,
    export_path: Path | None = None,
    export_format: str = "json",
) -> None:
    """
    Perform semantic code search.

    Search types:
    - unified: Search across all dimensions (files, purpose, patterns)
    - purpose: Search by code purpose/intent
    - patterns: Find similar code patterns
    - callers: Find functions that call a specific function
    - callees: Find functions called by a specific function

    Args:
        project_dir: Project directory path
        query: Natural language search query
        search_type: Type of search to perform
        limit: Maximum results per search type
        entity_type: Optional entity type filter (for purpose search)
        export_path: Optional path to export results
        export_format: Export format (json or csv)
    """
    print_banner()
    print(f"\n{icon(Icons.SEARCH)} Code Search\n")

    # Initialize Graphiti memory
    memory = None
    try:
        memory = get_graphiti_memory(project_dir / ".auto-claude", project_dir)
    except Exception as e:
        print(warning(f"{icon(Icons.WARNING)} Graphiti memory not available: {e}"))
        print(muted("Proceeding with file-based search only...\n"))

    # Create enhanced searcher
    searcher = EnhancedCodeSearch(project_dir, graphiti_memory=memory)

    # Perform search based on type
    results = None

    if search_type == "unified":
        print(info(f"Searching: {query}"))
        print(muted("Search type: Unified (files, purpose, patterns)\n"))

        results = await searcher.search_unified(
            query=query,
            limit=limit,
            search_files=True,
            search_purpose=memory is not None,
            search_patterns=memory is not None,
        )

        # Display unified results
        _display_unified_results(results)

    elif search_type == "purpose":
        print(info(f"Searching by purpose: {query}\n"))

        if entity_type:
            print(muted(f"Entity type filter: {entity_type}\n"))

        results = await searcher.search_by_purpose(
            query=query, limit=limit, entity_type=entity_type
        )

        _display_purpose_results(results)

    elif search_type == "patterns":
        print(info(f"Finding similar patterns: {query}\n"))

        results = await searcher.find_similar_patterns(query=query, num_results=limit)

        _display_pattern_results(results)

    elif search_type == "callers":
        print(info(f"Finding callers of: {query}\n"))

        results = await searcher.find_callers(function_name=query, limit=limit)

        _display_caller_results(results, query)

    elif search_type == "callees":
        print(info(f"Finding callees of: {query}\n"))

        results = await searcher.find_callees(function_name=query, limit=limit)

        _display_callee_results(results, query)

    else:
        print(warning(f"{icon(Icons.WARNING)} Unknown search type: {search_type}"))
        print(muted("Valid types: unified, purpose, patterns, callers, callees\n"))
        return

    # Export if requested
    if export_path and results:
        try:
            output_path = searcher.export_search_results(
                results=results, output_path=export_path, format=export_format
            )
            print(success(f"{icon(Icons.SUCCESS)} Exported to: {output_path}"))
        except Exception as e:
            print(warning(f"{icon(Icons.WARNING)} Export failed: {e}"))

    print()


def _display_unified_results(results: dict) -> None:
    """Display unified search results."""
    total = results.get("total", 0)

    if total == 0:
        print(info(f"{icon(Icons.INFO)} No results found"))
        print()
        return

    print(success(f"{icon(Icons.SUCCESS)} Found {total} results\n"))

    # File results
    files = results.get("files", [])
    if files:
        print_header("Files")
        print()

        for idx, match in enumerate(files[:10], 1):
            file_path = getattr(match, "path", "Unknown")
            score = getattr(match, "relevance_score", 0.0)
            matching_lines = getattr(match, "matching_lines", [])

            print(f"  {idx}. {file_path}")
            print(f"     Score: {score:.2f}")

            if matching_lines:
                formatted = [
                    f"line {lineno}: {text}" for lineno, text in matching_lines[:3]
                ]
                match_summary = ", ".join(formatted)
                if len(matching_lines) > 3:
                    match_summary += f" (+{len(matching_lines) - 3} more)"
                print(f"     Matches: {match_summary}")

            print()

        if len(files) > 10:
            print(muted(f"  ... and {len(files) - 10} more files\n"))

    # Purpose results
    purpose = results.get("purpose", [])
    if purpose:
        print_header("By Purpose")
        print()

        for idx, result in enumerate(purpose[:10], 1):
            entity_name = result.get("entity_name", "Unknown")
            entity_type = result.get("entity_type", "unknown")
            purpose_text = result.get("purpose", "")[:100]
            file_path = result.get("file_path", "")
            score = result.get("score", 0.0)

            print(f"  {idx}. {entity_name} ({entity_type})")
            print(f"     Score: {score:.2f}")

            if purpose_text:
                print(f"     Purpose: {purpose_text}")

            if file_path:
                print(f"     Location: {file_path}")

            print()

        if len(purpose) > 10:
            print(muted(f"  ... and {len(purpose) - 10} more entities\n"))

    # Pattern results
    patterns = results.get("patterns", [])
    if patterns:
        print_header("Patterns & Gotchas")
        print()

        for idx, result in enumerate(patterns[:10], 1):
            content = result.get("content", "")[:100]
            score = result.get("score", 0.0)
            pattern_type = result.get("type", "unknown")

            print(f"  {idx}. [{pattern_type.upper()}] Score: {score:.2f}")
            if content:
                print(f"     {content}")
            print()

        if len(patterns) > 10:
            print(muted(f"  ... and {len(patterns) - 10} more patterns\n"))

    print(divider())
    print()


def _display_purpose_results(results: list) -> None:
    """Display purpose search results."""
    if not results:
        print(info(f"{icon(Icons.INFO)} No entities found"))
        print()
        return

    print(success(f"{icon(Icons.SUCCESS)} Found {len(results)} entities\n"))

    for idx, result in enumerate(results[:20], 1):
        entity_name = result.get("entity_name", "Unknown")
        entity_type = result.get("entity_type", "unknown")
        purpose_text = result.get("purpose", "")[:150]
        file_path = result.get("file_path", "")
        lineno = result.get("lineno", "")
        score = result.get("score", 0.0)

        print(f"{idx}. {bold(entity_name)} ({entity_type})")
        print(f"   Score: {score:.2f}")

        if purpose_text:
            print(f"   Purpose: {purpose_text}")

        if file_path:
            location = f"{file_path}:{lineno}" if lineno else file_path
            print(muted(f"   Location: {location}"))

        print()

    if len(results) > 20:
        print(muted(f"... and {len(results) - 20} more entities\n"))

    print()


def _display_pattern_results(results: list) -> None:
    """Display pattern search results."""
    if not results:
        print(info(f"{icon(Icons.INFO)} No patterns found"))
        print()
        return

    print(success(f"{icon(Icons.SUCCESS)} Found {len(results)} patterns\n"))

    for idx, result in enumerate(results[:20], 1):
        content = result.get("content", "")[:150]
        score = result.get("score", 0.0)
        pattern_type = result.get("type", "unknown")
        category = result.get("category", "")

        print(f"{idx}. [{pattern_type.upper()}] Score: {score:.2f}")

        if category:
            print(f"   Category: {category}")

        if content:
            print(f"   {content}")

        print()

    if len(results) > 20:
        print(muted(f"... and {len(results) - 20} more patterns\n"))

    print()


def _display_caller_results(results: list, function_name: str) -> None:
    """Display caller search results."""
    if not results:
        print(info(f"{icon(Icons.INFO)} No callers found for '{function_name}'"))
        print()
        return

    print(success(f"{icon(Icons.SUCCESS)} Found {len(results)} callers\n"))

    for idx, result in enumerate(results[:50], 1):
        caller = result.get("caller", "Unknown")
        file_path = result.get("file_path", "")
        lineno = result.get("lineno", "")
        call_type = result.get("call_type", "unknown")

        print(f"{idx}. {bold(caller)} ({call_type})")

        if file_path:
            location = f"{file_path}:{lineno}" if lineno else file_path
            print(muted(f"   Location: {location}"))

        print()

    if len(results) > 50:
        print(muted(f"... and {len(results) - 50} more callers\n"))

    print()


def _display_callee_results(results: list, function_name: str) -> None:
    """Display callee search results."""
    if not results:
        print(info(f"{icon(Icons.INFO)} No callees found for '{function_name}'"))
        print()
        return

    print(success(f"{icon(Icons.SUCCESS)} Found {len(results)} callees\n"))

    for idx, result in enumerate(results[:50], 1):
        callee = result.get("callee", "Unknown")
        file_path = result.get("file_path", "")
        lineno = result.get("lineno", "")
        call_type = result.get("call_type", "unknown")

        print(f"{idx}. {bold(callee)} ({call_type})")

        if file_path:
            location = f"{file_path}:{lineno}" if lineno else file_path
            print(muted(f"   Location: {location}"))

        print()

    if len(results) > 50:
        print(muted(f"... and {len(results) - 50} more callees\n"))

    print()


def show_search_status(project_dir: Path) -> None:
    """
    Display search system status.

    Args:
        project_dir: Project directory path
    """
    print_banner()
    print(f"\n{icon(Icons.INFO)} Search System Status\n")

    # Check Graphiti memory
    try:
        memory = get_graphiti_memory(project_dir / ".auto-claude", project_dir)
        graphiti_available = memory is not None and memory.is_initialized
    except Exception:
        graphiti_available = False

    # Create searcher to get status
    searcher = EnhancedCodeSearch(
        project_dir, graphiti_memory=memory if graphiti_available else None
    )
    status = searcher.get_status()

    # Display status
    print_header("Graphiti Memory")
    print()

    if status["graphiti_enabled"]:
        print(success(f"{icon(Icons.SUCCESS)} Enabled"))
        print_key_value("Initialized", str(status["graphiti_initialized"]))
        print_key_value(
            "Code Relationships", str(status["code_relationships_available"])
        )
        print_key_value("Pattern Search", str(status["graphiti_search_available"]))
    else:
        print(warning(f"{icon(Icons.WARNING)} Disabled"))
        print(muted("Set GRAPHITI_ENABLED=true to enable semantic search"))

    print()

    # File-based search
    print_header("File-Based Search")
    print()

    print_key_value("Semantic Search", str(status["semantic_search_enabled"]))
    print_key_value("Project", str(status["project_dir"]))

    print()

    # Saved searches
    print_header("Saved Searches")
    print()

    saved_searches = SavedSearches(
        storage_path=project_dir / ".auto-claude" / "saved_searches.json"
    )
    print_key_value("Total", str(saved_searches.count))

    if saved_searches.count > 0:
        searches = saved_searches.list_searches()
        print()

        # Show recent searches
        print(muted("Recent searches:"))
        for search in searches[:5]:
            name = search.name
            query = search.query[:50]
            search_type = search.search_type
            last_used = search.last_used or "Never"
            print(f"  • {name} ({search_type}): {query}...")
            print(muted(f"    Last used: {last_used}"))

    print()


async def manage_saved_searches(
    project_dir: Path,
    action: str,
    name: str | None = None,
    query: str | None = None,
    search_type: str = "semantic",
    description: str | None = None,
    tags: list[str] | None = None,
    export_path: Path | None = None,
    import_path: Path | None = None,
    merge_strategy: str = "error",
) -> None:
    """
    Manage saved searches.

    Actions:
    - list: List all saved searches
    - save: Save a new search
    - load: Load and run a saved search
    - delete: Delete a saved search
    - export: Export saved searches to file
    - import: Import saved searches from file

    Args:
        project_dir: Project directory path
        action: Action to perform
        name: Search name (for save, load, delete)
        query: Search query (for save)
        search_type: Search type (for save)
        description: Search description (for save)
        tags: Search tags (for save)
        export_path: Path to export to (for export)
        import_path: Path to import from (for import)
        merge_strategy: Merge strategy for imports (error, skip, overwrite)
    """
    print_banner()
    print(f"\n{icon(Icons.SEARCH)} Saved Searches\n")

    saved_searches = SavedSearches(
        storage_path=project_dir / ".auto-claude" / "saved_searches.json"
    )

    if action == "list":
        print_header("All Saved Searches")
        print()

        searches = saved_searches.list_searches()

        if not searches:
            print(info(f"{icon(Icons.INFO)} No saved searches"))
            print()
            return

        for idx, search in enumerate(searches, 1):
            print(f"{idx}. {bold(search.name)}")
            print(f"   Query: {search.query}")
            print(f"   Type: {search.search_type}")

            if search.description:
                print(f"   Description: {search.description}")

            if search.tags:
                print(f"   Tags: {', '.join(search.tags)}")

            print(f"   Created: {search.created_at}")
            print(muted(f"   Last used: {search.last_used or 'Never'}"))
            print()

    elif action == "save":
        if not name or not query:
            print(warning(f"{icon(Icons.WARNING)} Name and query are required"))
            print()
            return

        try:
            search = saved_searches.save_search(
                name=name,
                query=query,
                search_type=search_type,
                description=description,
                tags=tags,
            )
            print(success(f"{icon(Icons.SUCCESS)} Saved search: {search.name}"))
            print(muted(f"Query: {search.query}"))
            print()
        except ValueError as e:
            print(warning(f"{icon(Icons.WARNING)} Failed to save: {e}"))
            print()

    elif action == "load":
        if not name:
            print(warning(f"{icon(Icons.WARNING)} Search name is required"))
            print()
            return

        search = saved_searches.get_search(name)

        if not search:
            print(warning(f"{icon(Icons.WARNING)} Search not found: {name}"))
            print()
            return

        print(info(f"Loading search: {search.name}"))
        print(muted(f"Query: {search.query}"))
        print(muted(f"Type: {search.search_type}"))
        print()

        # Translate saved search types to runtime types
        type_mapping = {
            "semantic": "unified",
            "keyword": "unified",
            "hybrid": "unified",
        }
        runtime_type = type_mapping.get(search.search_type, search.search_type)

        # Run the search with saved parameters
        await search_code(
            project_dir=project_dir,
            query=search.query,
            search_type=runtime_type,
        )

    elif action == "delete":
        if not name:
            print(warning(f"{icon(Icons.WARNING)} Search name is required"))
            print()
            return

        if saved_searches.delete_search(name):
            print(success(f"{icon(Icons.SUCCESS)} Deleted search: {name}"))
            print()
        else:
            print(warning(f"{icon(Icons.WARNING)} Search not found: {name}"))
            print()

    elif action == "export":
        if not export_path:
            export_path = Path.cwd() / "saved_searches_export.json"

        try:
            output_path = saved_searches.export_searches(output_path=export_path)
            print(success(f"{icon(Icons.SUCCESS)} Exported to: {output_path}"))
            print(muted(f"Total searches: {saved_searches.count}"))
            print()
        except Exception as e:
            print(warning(f"{icon(Icons.WARNING)} Export failed: {e}"))
            print()

    elif action == "import":
        if not import_path:
            print(warning(f"{icon(Icons.WARNING)} Import path is required"))
            print()
            return

        try:
            count = saved_searches.import_searches(
                input_path=import_path, merge_strategy=merge_strategy
            )
            print(success(f"{icon(Icons.SUCCESS)} Imported {count} searches"))
            print()
        except Exception as e:
            print(warning(f"{icon(Icons.WARNING)} Import failed: {e}"))
            print()

    else:
        print(warning(f"{icon(Icons.WARNING)} Unknown action: {action}"))
        print(muted("Valid actions: list, save, load, delete, export, import"))
        print()


async def handle_search_command(
    project_dir: Path,
    query: str | None = None,
    search_type: str = "unified",
    limit: int = 20,
    entity_type: str | None = None,
    status: bool = False,
    saved_action: str | None = None,
    saved_name: str | None = None,
    saved_query: str | None = None,
    saved_type: str = "semantic",
    saved_description: str | None = None,
    saved_tags: list[str] | None = None,
    export_path: Path | None = None,
    export_format: str = "json",
    import_path: Path | None = None,
    merge_strategy: str = "error",
) -> None:
    """
    Handle the --search command.

    Args:
        project_dir: Project directory path
        query: Search query
        search_type: Type of search (unified, purpose, patterns, callers, callees)
        limit: Maximum results
        entity_type: Entity type filter (for purpose search)
        status: Show search system status
        saved_action: Saved searches action (list, save, load, delete, export, import)
        saved_name: Search name (for save, load, delete)
        saved_query: Search query (for save)
        saved_type: Search type (for save)
        saved_description: Search description (for save)
        saved_tags: Search tags (for save)
        export_path: Path to export results
        export_format: Export format (json or csv)
        import_path: Path to import searches from
        merge_strategy: Merge strategy for imports
    """
    if status:
        show_search_status(project_dir)
    elif saved_action:
        await manage_saved_searches(
            project_dir=project_dir,
            action=saved_action,
            name=saved_name,
            query=saved_query,
            search_type=saved_type,
            description=saved_description,
            tags=saved_tags,
            export_path=export_path,
            import_path=import_path,
            merge_strategy=merge_strategy,
        )
    elif query:
        await search_code(
            project_dir=project_dir,
            query=query,
            search_type=search_type,
            limit=limit,
            entity_type=entity_type,
            export_path=export_path,
            export_format=export_format,
        )
    else:
        # No arguments provided, show help
        print_banner()
        print(f"\n{icon(Icons.SEARCH)} Code Search\n")
        print(info("Usage:"))
        print()
        print("  --search '<query>'              - Perform semantic search")
        print("  --search-status                 - Show search system status")
        print("  --saved-searches list           - List saved searches")
        print("  --saved-searches save           - Save a search")
        print("  --saved-searches load <name>    - Load and run a saved search")
        print("  --saved-searches delete <name>  - Delete a saved search")
        print("  --saved-searches export         - Export saved searches")
        print("  --saved-searches import         - Import saved searches")
        print()
        print(muted("Examples:"))
        print()
        print("  --search 'authentication functions'")
        print("  --search 'error handling' --search-type patterns")
        print("  --search 'validate_token' --search-type callers")
        print("  --saved-searches save --name 'auth' --query 'authentication'")
        print("  --saved-searches load --name 'auth'")
        print()
