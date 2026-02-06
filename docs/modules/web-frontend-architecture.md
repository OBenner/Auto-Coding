# Web Frontend Module

React-based web interface for Auto Code autonomous coding framework. This module provides a browser-based UI for managing specs, monitoring agent execution, and viewing project insights.

## Architecture

The web frontend is organized by feature and responsibility:

```
apps/web-frontend/src/
├── App.tsx              # Root component
├── main.tsx             # Application entry point
├── api/                 # Backend API integration
│   ├── client.ts        # REST API client
│   ├── types.ts         # API type definitions
│   └── websocket.ts     # WebSocket connection
├── components/          # React components
│   ├── Sidebar.tsx      # Main navigation sidebar
│   ├── TaskCard.tsx     # Task/spec display card
│   ├── Terminal.tsx     # Terminal output viewer
│   └── ui/              # Radix UI primitives (styled)
├── pages/               # Route-based page components
│   ├── TaskList.tsx     # Task overview page
│   └── TaskDetail.tsx   # Individual task details
├── hooks/               # Custom React hooks
│   └── use-toast.tsx    # Toast notification hook
├── i18n/                # Internationalization
│   └── index.ts         # i18n configuration
├── lib/                 # Utility functions
│   └── utils.ts         # Common utilities (cn, etc.)
└── shared/              # Shared types and constants
    ├── types/           # TypeScript type definitions
    └── constants/       # Application constants
```

## Modules

### `api/` (REST API Integration)

**client.ts** (9.8 KB) - REST API client for web backend communication:
- `ApiClient` class with methods for tasks, specs, agents, and auth
- Automatic error handling and timeout management
- Environment-based configuration (`VITE_API_URL`)
- Debug logging support
- Health check utilities

**types.ts** - TypeScript type definitions for API contracts:
- Request/response schemas for all endpoints
- Agent execution types (`AgentRunRequest`, `AgentStatusResponse`)
- Task and spec data models
- Error response types

**websocket.ts** - WebSocket client for real-time updates:
- Live agent execution progress
- Task status notifications
- Connection management with reconnection logic
- Event-based message handling

### `components/` (React Components)

**Sidebar.tsx** (7.8 KB) - Main navigation component:
- Collapsible sidebar with view switching
- Navigation items: Kanban, Terminals, Insights, Roadmap, Ideation, Changelog, Context, Agent Tools, Worktrees
- Keyboard shortcut indicators
- i18n support with `react-i18next`
- Tooltip-enhanced collapsed mode

**TaskCard.tsx** - Task/spec display component:
- Compact task information display
- Status indicators (pending, in-progress, completed)
- Quick action buttons
- Responsive card layout

**Terminal.tsx** - Terminal output viewer:
- Real-time agent output display
- Auto-scrolling terminal view
- ANSI color support (if implemented)
- Copy-to-clipboard functionality

**ui/** - Radix UI component library (styled with Tailwind):
- `button.tsx` - Button variants (default, ghost, secondary, outline)
- `card.tsx` - Card container with header, content, footer sections
- `dropdown-menu.tsx` - Dropdown menu primitives
- `scroll-area.tsx` - Custom scrollbar component
- `separator.tsx` - Horizontal/vertical dividers
- `tooltip.tsx` - Tooltip wrapper with customizable delay
- `badge.tsx` - Badge/chip component for status labels
- `checkbox.tsx` - Accessible checkbox component

### `pages/` (Route Components)

**TaskList.tsx** - Task overview page:
- Grid or list view of all tasks/specs
- Filtering and sorting capabilities
- Search functionality
- Quick create button

**TaskDetail.tsx** - Individual task detail page:
- Spec content display
- Implementation plan visualization
- QA report viewer
- Agent execution controls

### `hooks/` (Custom React Hooks)

**use-toast.tsx** - Toast notification hook:
- Imperative toast API (`toast({ title, description })`)
- Auto-dismiss with configurable duration
- Success, error, warning, info variants
- Accessible toast notifications (Radix UI)

### `i18n/` (Internationalization)

**index.ts** - i18n configuration:
- `react-i18next` setup
- Language detection (browser default)
- Translation namespaces (common, navigation, tasks, etc.)
- Fallback language (English)

**Translation structure:**
```typescript
// Example usage in components
const { t } = useTranslation(['navigation', 'common']);
t('navigation:items.kanban')  // "Kanban"
t('common:actions.newTask')   // "New Task"
```

### `lib/` (Utilities)

**utils.ts** - Common utility functions:
- `cn()` - Tailwind class name merger (clsx + tailwind-merge)
- Date formatting helpers
- String manipulation utilities
- Type guards

### `shared/` (Shared Code)

**types/** - Global TypeScript types:
- Application-wide type definitions
- Component prop interfaces
- Utility types

**constants/** - Application constants:
- API endpoints
- Route paths
- Configuration values
- Default settings

## State Management

### Zustand Stores

The web frontend uses Zustand for lightweight state management:

```typescript
// Example store structure (not yet implemented)
interface AppStore {
  // Tasks/specs state
  tasks: Task[];
  selectedTask: Task | null;

  // UI state
  sidebarView: SidebarView;
  sidebarCollapsed: boolean;

  // Actions
  setSelectedTask: (task: Task | null) => void;
  setSidebarView: (view: SidebarView) => void;
}
```

**Benefits:**
- No boilerplate (unlike Redux)
- TypeScript-first API
- React hooks integration
- Minimal bundle size

## API Integration

### REST API Client

The `ApiClient` class provides a clean interface to the web backend:

```typescript
import { apiClient } from './api/client';

// List all tasks
const tasks = await apiClient.listTasks();

// Get task details
const task = await apiClient.getTask('001-feature-name');

// Run agent
const response = await apiClient.runAgent({
  spec_id: '001-feature-name',
  agent_type: 'coder'
});

// Check agent status
const status = await apiClient.getAgentStatus(response.task_id);
```

**Features:**
- Automatic timeout handling (30s default)
- Error response parsing
- Debug logging (enabled via `VITE_DEBUG=true`)
- Health check utilities

### WebSocket Integration

Real-time updates for agent execution:

```typescript
// Example WebSocket usage (not yet fully implemented)
const ws = new WebSocketClient({
  url: import.meta.env.VITE_WS_URL,
  onMessage: (event) => {
    // Handle agent progress updates
  }
});

ws.connect();
```

## UI Component System

### Radix UI + Tailwind CSS

The web frontend uses **Radix UI** primitives styled with **Tailwind CSS v4**:

**Why Radix UI:**
- Unstyled, accessible components
- Full keyboard navigation
- ARIA attributes built-in
- Framework-agnostic primitives

**Component pattern:**
```tsx
// Example: Button component (ui/button.tsx)
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
      },
      size: {
        default: 'h-10 px-4 py-2',
        icon: 'h-10 w-10',
      }
    }
  }
);

export function Button({ variant, size, ...props }) {
  return <Slot className={buttonVariants({ variant, size })} {...props} />;
}
```

**Tailwind v4 Configuration:**
- CSS-based configuration (`@import` in main CSS)
- JIT (Just-In-Time) compilation
- Custom design tokens
- Dark mode support (via CSS variables)

## Internationalization (i18n)

### Translation System

The web frontend uses `react-i18next` for multilingual support:

**Setup:**
```typescript
// i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

i18n
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    ns: ['common', 'navigation', 'tasks'],
    defaultNS: 'common',
  });
```

**Usage in components:**
```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation(['navigation', 'common']);

  return (
    <button>{t('common:actions.newTask')}</button>
  );
}
```

**Translation namespaces:**
- `common.json` - Shared labels, buttons, common terms
- `navigation.json` - Sidebar navigation items
- `tasks.json` - Task/spec related content
- `errors.json` - Error messages with interpolation

**CRITICAL:** All user-facing text must use translation keys, not hardcoded strings.

## Routing

### React Router (Planned)

The web frontend will use React Router for navigation:

```typescript
// Example routing structure (not yet implemented)
<BrowserRouter>
  <Routes>
    <Route path="/" element={<TaskList />} />
    <Route path="/task/:id" element={<TaskDetail />} />
    <Route path="/settings" element={<Settings />} />
    <Route path="/kanban" element={<KanbanView />} />
    <Route path="/terminals" element={<TerminalsView />} />
    <Route path="/insights" element={<InsightsView />} />
  </Routes>
</BrowserRouter>
```

**Route structure:**
- `/` - Task list (Kanban view)
- `/task/:id` - Task details
- `/settings` - Application settings
- `/kanban` - Kanban board
- `/terminals` - Terminal output viewer
- `/roadmap` - Project roadmap
- `/insights` - AI insights and patterns

## Benefits

1. **Modern React Stack**: React 19 with TypeScript for type safety
2. **Accessible UI**: Radix UI primitives with ARIA support
3. **Responsive Design**: Tailwind CSS v4 with mobile-first approach
4. **Real-time Updates**: WebSocket integration for live agent progress
5. **Internationalization**: Multi-language support via i18next
6. **Developer Experience**: Vite for fast HMR, TypeScript for IntelliSense
7. **Minimal Bundle Size**: Zustand for state, no heavy frameworks
8. **Consistent Styling**: Tailwind + CVA for variant-based components

## Module Dependencies

```
App.tsx
  ├── Sidebar.tsx (navigation)
  ├── pages/ (route components)
  └── i18n/ (translations)

Sidebar.tsx
  ├── components/ui/ (Radix UI primitives)
  └── i18n (react-i18next)

pages/
  ├── api/client (REST API)
  ├── components/ (UI components)
  └── hooks/ (custom hooks)

api/client.ts
  └── api/types.ts (type definitions)
```

## Development

### Setup

```bash
cd apps/web-frontend
npm install
```

### Run Development Server

```bash
npm run dev
# Opens on http://localhost:3000 (default Vite port)
```

### Environment Variables

Create `.env` file:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_DEBUG=true
```

### Build for Production

```bash
npm run build
# Output: dist/
```

### Type Checking

```bash
npm run typecheck
# Runs tsc --noEmit
```

### Code Quality

```bash
npm run lint         # Check code style
npm run lint:fix     # Auto-fix issues
npm run format       # Format code with Biome
```

## Tech Stack

- **Language**: TypeScript 5.9+
- **Framework**: React 19.2.3
- **Build Tool**: Vite 7.2.7
- **Styling**: Tailwind CSS 4.1.17 (v4 with CSS @import)
- **UI Components**: Radix UI Primitives
- **State Management**: Zustand 5.0.9
- **Internationalization**: react-i18next 16.5.0
- **Icons**: Lucide React 0.562.0
- **HTTP Client**: Fetch API (native)
- **WebSocket**: Native WebSocket API

## Component Conventions

### File Naming

- Components: `PascalCase.tsx` (e.g., `TaskCard.tsx`)
- Utilities: `kebab-case.ts` (e.g., `use-toast.tsx`)
- Pages: `PascalCase.tsx` (e.g., `TaskList.tsx`)

### Import Order

```tsx
// 1. External dependencies
import React from 'react';
import { useTranslation } from 'react-i18next';

// 2. Internal components
import { Button } from './ui/button';
import { Card } from './ui/card';

// 3. Utilities and types
import { cn } from '../lib/utils';
import type { Task } from '../shared/types';

// 4. Styles (if any)
import './component.css';
```

### Component Structure

```tsx
// 1. Type definitions
interface ComponentProps {
  title: string;
  onAction: () => void;
}

// 2. Component function
export function Component({ title, onAction }: ComponentProps) {
  // 3. Hooks
  const { t } = useTranslation(['common']);
  const [state, setState] = useState(false);

  // 4. Event handlers
  const handleClick = () => {
    onAction();
  };

  // 5. Render
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={handleClick}>
        {t('common:actions.submit')}
      </Button>
    </div>
  );
}
```

## API Contract

### Example: Task List Endpoint

**Request:**
```typescript
GET /api/tasks
```

**Response:**
```typescript
{
  "tasks": [
    {
      "id": "001-feature-name",
      "title": "Add user authentication",
      "status": "in-progress",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:20:00Z"
    }
  ],
  "total": 1
}
```

### Example: Agent Run Endpoint

**Request:**
```typescript
POST /api/agents/run
{
  "spec_id": "001-feature-name",
  "agent_type": "coder",
  "subtask_id": "subtask-1-1"
}
```

**Response:**
```typescript
{
  "task_id": "agent-run-uuid-123",
  "status": "started",
  "message": "Agent execution started"
}
```

## Future Enhancements

**Planned features:**
- Drag-and-drop Kanban board (using `dnd-kit`)
- Real-time terminal output streaming
- Agent execution controls (pause, resume, cancel)
- Project insights dashboard with charts
- GitHub PR integration viewer
- Linear issue synchronization UI
- Code diff viewer for agent changes
- Memory system (Graphiti) browser
- Multi-project support
- User preferences persistence

## Troubleshooting

### API Connection Issues

**Problem:** Cannot connect to backend API

**Solution:**
1. Verify web backend is running: `cd apps/web-backend && python main.py`
2. Check `VITE_API_URL` in `.env` matches backend URL
3. Ensure CORS is configured in backend `.env`: `CORS_ORIGINS=http://localhost:3000`

### WebSocket Connection Failures

**Problem:** WebSocket disconnects frequently

**Solution:**
1. Check `VITE_WS_URL` format: `ws://` not `wss://` for local dev
2. Verify backend WebSocket heartbeat: `WS_HEARTBEAT_INTERVAL=30` in backend `.env`
3. Check browser console for connection errors

### Build Errors

**Problem:** `npm run build` fails with TypeScript errors

**Solution:**
1. Run type check: `npm run typecheck`
2. Fix type errors in reported files
3. Ensure all dependencies are installed: `npm install`

### Translation Keys Not Working

**Problem:** Translation keys display as-is instead of translated text

**Solution:**
1. Check i18n initialization in `main.tsx`
2. Verify translation files exist in `i18n/locales/`
3. Ensure namespace is loaded: `useTranslation(['namespace'])`
4. Check browser console for i18n errors

## Migration Guide

### From Electron Frontend to Web Frontend

The web frontend shares component patterns with the Electron frontend but differs in:

**Similarities:**
- Same UI component library (Radix UI + Tailwind)
- Same i18n system (react-i18next)
- Same state management (Zustand)

**Differences:**
- **No IPC**: Web frontend uses REST API instead of Electron IPC
- **No native modules**: No access to Node.js APIs (fs, path, etc.)
- **Browser environment**: Different security model (CORS, CSP)
- **Routing**: React Router instead of Electron window management

**Migration checklist:**
- Replace IPC calls with `apiClient` methods
- Remove Node.js-specific code (fs, path, child_process)
- Update environment variable references (Vite uses `import.meta.env`)
- Configure CORS in web backend for API access
