# Integrated Code Search with Graphiti

The Code Search feature provides semantic and structural code search powered by the Graphiti memory system. It enables developers to search across their codebase by meaning, purpose, patterns, and call relationships.

## Search Types

| Type | Description |
|------|-------------|
| `unified` | Combined search across all categories (default) |
| `purpose` | Find code by its functional purpose |
| `patterns` | Discover design patterns and architectural patterns |
| `callers` | Find functions/methods that call a given target |
| `callees` | Find functions/methods called by a given source |
| `semantic` | Saved-search metadata only (maps to `unified` at runtime) |
| `keyword` | Saved-search metadata only (maps to `unified` at runtime) |
| `hybrid` | Saved-search metadata only (maps to `unified` at runtime) |

> **Note:** `semantic`, `keyword`, and `hybrid` are not valid `--search-type` CLI values. They exist only as saved-search metadata and are automatically translated to `unified` when a saved search is loaded.

## CLI Usage

```bash
cd apps/backend

# Unified search (default)
python cli/main.py --project-dir /path/to/project --search "authentication logic"

# Search by type
python cli/main.py --project-dir /path/to/project --search "auth" --search-type purpose

# Search with entity filter
python cli/main.py --project-dir /path/to/project --search "validate" --search-entity-type function

# Show search index status
python cli/main.py --project-dir /path/to/project --search-status
```

## Saved Searches

Searches can be saved, reloaded, and shared via export/import.

```bash
# Save a search
python cli/main.py --project-dir /path/to/project \
  --saved-searches save --saved-name "auth-search" \
  --saved-query "authentication" --saved-type unified

# List saved searches
python cli/main.py --project-dir /path/to/project --saved-searches list

# Load and re-run a saved search
python cli/main.py --project-dir /path/to/project \
  --saved-searches load --saved-name "auth-search"

# Export/Import
python cli/main.py --project-dir /path/to/project \
  --saved-searches export --search-export searches.json
python cli/main.py --project-dir /path/to/project \
  --saved-searches import --search-import searches.json
```

## Architecture

### Backend

- **`apps/backend/context/enhanced_search.py`** -- `EnhancedCodeSearch` class that combines file search, Graphiti semantic search, and code relationship analysis
- **`apps/backend/context/saved_searches.py`** -- `SavedSearches` manager for persisting and organizing search configurations
- **`apps/backend/cli/search_commands.py`** -- CLI command handlers for search operations

### Frontend

- **`apps/frontend/src/renderer/pages/CodeSearchPage.tsx`** -- Main search page
- **`apps/frontend/src/renderer/components/code-search/SearchBar.tsx`** -- Search input with type selector
- **`apps/frontend/src/renderer/components/code-search/SearchResults.tsx`** -- Results display
- **`apps/frontend/src/renderer/components/code-search/SavedSearches.tsx`** -- Saved search management UI
- **`apps/frontend/src/main/ipc-handlers/search-handlers.ts`** -- IPC handlers bridging frontend to backend

### IPC Channels

Search uses dedicated IPC channels defined in `apps/frontend/src/shared/constants/ipc.ts` prefixed with `search:`.

## Internationalization

All UI text uses i18n keys from the `code-search` namespace:
- `apps/frontend/src/shared/i18n/locales/en/code-search.json`
- `apps/frontend/src/shared/i18n/locales/fr/code-search.json`

## Export Formats

Search results can be exported to:
- **JSON** -- Full structured output
- **CSV** -- Flattened tabular format (collects all unique keys across result types)
