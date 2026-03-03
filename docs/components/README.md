# Frontend Component Documentation

Comprehensive documentation for Auto Code's React components and Zustand stores.

## Overview

This directory contains detailed API documentation for the frontend's key UI components and state management stores. Each document follows the component-api template and includes type definitions, usage examples, props/actions documentation, and integration patterns.

## Component Documentation

### Core UI Components

| Component | Description | Location |
|-----------|-------------|----------|
| **[KanbanBoard](KanbanBoard.md)** | Feature-rich Kanban board with drag-and-drop, queue management, column customization, and real-time progress tracking | `apps/frontend/src/renderer/components/KanbanBoard.tsx` |
| **[Sidebar](Sidebar.md)** | Main navigation sidebar with collapsible state, dynamic navigation items, and keyboard shortcuts | `apps/frontend/src/renderer/components/Sidebar.tsx` |
| **[TaskCard & SortableTaskCard](TaskCard.md)** | High-performance task card components with execution monitoring, multi-selection, and drag-and-drop integration | `apps/frontend/src/renderer/components/TaskCard.tsx`, `SortableTaskCard.tsx` |

## State Management (Zustand Stores)

Auto Code uses [Zustand](https://github.com/pmndrs/zustand) for state management. Store documentation is located in `docs/stores/`:

| Store | Description | Location |
|-------|-------------|----------|
| **[task-store](../stores/task-store.md)** | Central task state management: task lifecycle, execution progress, subtasks, logs, and Kanban ordering | `apps/frontend/src/renderer/stores/task-store.ts` |
| **[kanban-settings-store](../stores/kanban-settings-store.md)** | Kanban board column preferences: width, collapse state, lock state with per-project persistence | `apps/frontend/src/renderer/stores/kanban-settings-store.ts` |

## Key Patterns and Technologies

### UI Framework Stack

- **React 18+** - Core UI library with hooks and functional components
- **TypeScript** - Type-safe component props and store state
- **Radix UI** - Accessible, unstyled component primitives (Dialog, Tooltip, ScrollArea, etc.)
- **Tailwind CSS** - Utility-first styling with custom design system
- **Lucide React** - Icon library for consistent iconography

### State Management

- **Zustand** - Lightweight state management with React hooks
- **React Context** - Used for i18n (react-i18next)
- **IPC Communication** - Electron main-renderer communication for backend integration

### Drag & Drop

- **@dnd-kit** - Modern drag-and-drop library used in KanbanBoard
  - `@dnd-kit/core` - Core drag-and-drop functionality
  - `@dnd-kit/sortable` - Sortable lists (task ordering within columns)
  - `@dnd-kit/modifiers` - Drag modifiers (restrictions, snapping)

### Internationalization

- **react-i18next** - Translation keys for all user-facing text
- **Translation Namespaces:**
  - `common.json` - Shared labels, buttons
  - `navigation.json` - Sidebar navigation
  - `tasks.json` - Task/spec content
  - `dialogs.json` - Modal dialogs
  - `errors.json` - Error messages

## Component Documentation Structure

Each component document follows this structure:

1. **Overview** - Purpose, location, status
2. **Installation/Import** - Import syntax and dependencies
3. **API Reference** - Props, types, interfaces
4. **Usage Examples** - Basic and advanced usage patterns
5. **State Integration** - Zustand store interactions
6. **Best Practices** - Performance tips, common patterns
7. **Common Issues** - Troubleshooting and gotchas

## Quick Start for Contributors

### Understanding Component Architecture

1. **Read Component Docs First** - Start with [KanbanBoard](KanbanBoard.md) and [Sidebar](Sidebar.md) to understand the core UI
2. **Review Store Docs** - Read [task-store](../stores/task-store.md) for state management patterns
3. **Check Usage Examples** - Each doc includes real-world integration examples

### Making Component Changes

1. **Follow Type Definitions** - All props and state are fully typed in the documentation
2. **Respect Store Patterns** - Use documented store actions, don't modify state directly
3. **Maintain i18n** - All user-facing text must use translation keys (see component docs for examples)
4. **Test Drag & Drop** - Changes to KanbanBoard or TaskCard require testing drag-and-drop flows
5. **Verify Performance** - TaskCard uses custom memo comparators; changes must preserve optimization

### Common Integration Patterns

**Accessing Task State:**
```typescript
import { useTaskStore } from '@/renderer/stores/task-store';

function MyComponent() {
  const tasks = useTaskStore(state => state.tasks);
  const selectedTaskId = useTaskStore(state => state.selectedTaskId);
  const selectTask = useTaskStore(state => state.selectTask);

  // Use tasks...
}
```

**Using Kanban Settings:**
```typescript
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';

function MyComponent() {
  const prefs = useKanbanSettingsStore(state =>
    state.getColumnPreferences('in_progress')
  );
  const setColumnWidth = useKanbanSettingsStore(state => state.setColumnWidth);

  // Use column width...
}
```

**Translation Keys:**
```typescript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation(['navigation', 'common']);

  return <span>{t('navigation:items.kanban')}</span>;
}
```

## Performance Considerations

### KanbanBoard Optimization

- **Virtualization** - Not currently implemented; large task lists may impact performance
- **Memoization** - TaskCard uses custom `React.memo` comparator to prevent re-renders
- **Drag Modifiers** - Collision detection optimized for vertical scrolling

### Store Performance

- **Selective Subscriptions** - Use Zustand selectors to prevent unnecessary re-renders
- **Batch Updates** - Use store actions that combine multiple state updates
- **LocalStorage Throttling** - Settings stores throttle localStorage writes

## Testing

### Manual Testing

1. **Component Visual Testing** - Verify UI appearance and interactions
2. **Drag & Drop Testing** - Test task movement between columns
3. **Keyboard Shortcuts** - Verify navigation shortcuts in Sidebar
4. **Multi-Selection** - Test bulk operations in Human Review column

### E2E Testing (Electron MCP)

QA agents can perform automated E2E testing using the Electron MCP server:

- **UI Interaction** - Click buttons, fill forms, send keyboard shortcuts
- **Visual Verification** - Take screenshots for visual comparison
- **State Verification** - Inspect page structure and form state

See [CLAUDE.md](../../CLAUDE.md#end-to-end-testing-electron-app) for Electron MCP setup and usage.

## Related Documentation

- **[Main Docs README](../README.md)** - Documentation hub and style guide
- **[CLAUDE.md](../../CLAUDE.md)** - Full project architecture for AI agents
- **[CONTRIBUTING.md](../../CONTRIBUTING.md)** - Contribution guidelines
- **[Frontend Architecture](../../apps/frontend/README.md)** - Frontend-specific architecture (if exists)

## Contributing

When contributing component documentation:

1. **Follow the Template** - Use `docs/templates/api/component-api.md`
2. **Document All Props** - Include types, descriptions, and default values
3. **Provide Examples** - Include real-world integration examples
4. **Explain Store Integration** - Document which stores the component uses and how
5. **Add Usage Patterns** - Show common patterns and best practices
6. **Update This Index** - Add new components to the tables above

For documentation style guidelines, see [docs/STYLE_GUIDE.md](../STYLE_GUIDE.md).
