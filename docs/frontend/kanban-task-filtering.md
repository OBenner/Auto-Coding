# Kanban Board Task Filtering

## Overview

The Kanban board provides a comprehensive filtering and search system for managing tasks. Users can search by text, filter by metadata (status, category, complexity, impact, priority), and sort columns by different criteria. Filter state persists per project via localStorage.

## Architecture

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `KanbanFilters` | `components/KanbanFilters.tsx` | UI controls: search input, sort dropdown, clear filters button |
| `useTaskFiltering` | `hooks/useTaskFiltering.ts` | Core filtering logic: search + metadata filters with memoization |
| `KanbanBoard` | `components/KanbanBoard.tsx` | Integrates filtering with archive toggle, grouping, and column sorting |

### Data Flow

```
tasks (from store)
  → tasksFilteredByArchive (archive toggle)
    → useTaskFiltering (search + metadata filters)
      → filteredTasks
        → tasksByStatus (grouped by column, sorted by sortBy/sortOrder)
          → DroppableColumn (rendered)
```

### Filter State

The `useTaskFiltering` hook manages search and metadata filters:

```typescript
interface TaskFilterState {
  searchQuery: string;
  status: TaskStatus | 'all';
  category: TaskCategory | 'all';
  complexity: TaskComplexity | 'all';
  impact: TaskImpact | 'all';
  priority: TaskPriority | 'all';
}
```

The `KanbanFilters` component manages sort and search via the kanban settings store:

```typescript
interface KanbanFilterSettings {
  searchQuery: string;
  sortBy: 'manual' | 'priority' | 'created' | 'updated';
  sortOrder: 'asc' | 'desc';
}
```

## Features

### Search

- Searches across task `id`, `title`, `description`, and `specId`
- Case-insensitive matching
- Safe access via optional chaining (handles undefined fields without crashing)
- Debounced save to localStorage (300ms)

### Metadata Filters

- **Status**: Filter tasks by status (backlog, in_progress, done, etc.)
- **Category**: Filter by task category (feature, bug_fix, etc.)
- **Complexity**: Filter by complexity level (small, medium, complex)
- **Impact**: Filter by impact level (low, medium, high)
- **Priority**: Filter by priority level (low, medium, high)

Each filter supports an `'all'` value that shows all tasks for that dimension.

### Sort Modes

- **Manual** (default): Drag-and-drop ordering within columns
- **Priority**: Sort by task priority (high → low or reverse)
- **Created**: Sort by creation date
- **Updated**: Sort by last update date

Sort order can be toggled between ascending and descending.

### Persistence

Filter and sort preferences are saved per project in localStorage via `kanban-settings-store`. Preferences load automatically when switching projects.

## i18n Keys

Translation keys are defined in `shared/i18n/locales/{lang}/tasks.json` under the `kanban` namespace:

| Key | EN | FR |
|-----|-----|-----|
| `kanban.searchTasks` | Search tasks... | Rechercher des tâches... |
| `kanban.searchPlaceholder` | Search tasks... | Rechercher des tâches... |
| `kanban.allStatuses` | All statuses | Tous les statuts |
| `kanban.category` | Category | Catégorie |
| `kanban.allCategories` | All categories | Toutes les catégories |
| `kanban.priority` | Priority | Priorité |
| `kanban.allPriorities` | All priorities | Toutes les priorités |
| `kanban.clearFilters` | Clear Filters | Effacer les filtres |
| `kanban.dragDisabledAutoSort` | Drag-and-drop disabled when auto-sort is active | Glisser-déposer désactivé... |

## Testing

Tests are located at `hooks/__tests__/useTaskFiltering.test.ts` and cover:

- Initial state (no filters active)
- Search filtering (title, description, specId, id, case-insensitive)
- Individual metadata filters (status, category, complexity, impact, priority)
- Combined filters (search + metadata)
- Clear filters
- Unique value extraction from tasks
- Search callbacks (onSearchStart, onSearchClear)
- Edge cases: empty tasks array, undefined optional fields

Run tests:

```bash
cd apps/frontend
npx vitest run src/renderer/hooks/__tests__/useTaskFiltering.test.ts
```
