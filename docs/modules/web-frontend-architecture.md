# Web Frontend Architecture

Electron-based desktop application built with React, TypeScript, and Zustand. This module provides the user interface for Auto Claude's autonomous coding framework.

## Architecture

The frontend is organized into three main layers:

```
apps/frontend/src/
├── main/                # Main process (Node.js/Electron)
│   ├── agent/           # Agent execution and parsing
│   ├── changelog/       # Release changelog generation
│   ├── claude-profile/  # OAuth authentication and profile management
│   ├── insights/        # AI-powered codebase insights
│   ├── integrations/    # External service integrations
│   ├── ipc-handlers/    # IPC communication handlers
│   ├── platform/        # Cross-platform abstractions
│   ├── services/        # Backend service orchestration
│   ├── terminal/        # PTY terminal management
│   └── updater/         # Auto-update system
├── renderer/            # Renderer process (React UI)
│   ├── components/      # React components
│   ├── contexts/        # React contexts
│   ├── hooks/           # Custom React hooks
│   ├── stores/          # Zustand state management
│   ├── styles/          # Global styles
│   └── lib/             # UI utilities
├── preload/             # Preload scripts (bridge layer)
│   └── api/             # IPC API definitions
└── shared/              # Shared code (types, constants, utils)
    ├── constants/       # Shared constants
    ├── i18n/            # Internationalization
    ├── types/           # TypeScript type definitions
    └── utils/           # Shared utilities
```

## Main Process Architecture

The main process is the Electron backend that manages system resources, spawns Python agents, and handles IPC communication.

### Core Modules

**Agent Management** (`main/agent/`)
- `agent-manager.ts` - Orchestrates agent lifecycle and state
- `agent-process.ts` - Spawns and manages Python agent subprocesses
- `agent-queue.ts` - Task queue for sequential agent execution
- `agent-state.ts` - Agent state machine (idle, running, paused, etc.)
- `parsers/` - Parse agent output (spec creation, execution, roadmap phases)

**Authentication** (`main/claude-profile/`)
- `profile-storage.ts` - Persist Claude OAuth profiles
- `token-refresh.ts` - Auto-refresh expired tokens
- `rate-limit-manager.ts` - Track API usage limits
- `usage-monitor.ts` - Monitor real-time API usage
- `credential-utils.ts` - Secure credential handling

**Terminal Management** (`main/terminal/`)
- PTY process management for integrated terminals
- Session persistence across app restarts
- Terminal output buffering for seamless UI switching

**Platform Abstraction** (`main/platform/`)
- Centralized OS detection (Windows, macOS, Linux)
- Cross-platform executable discovery
- Path handling for consistent behavior across platforms

**IPC Handlers** (`main/ipc-handlers/`)
- Bridge between renderer and main process
- Handlers for: tasks, projects, settings, terminals, GitHub/GitLab, changelogs, insights

### Agent Execution Flow

```
User creates task → Agent Manager queues task
                   ↓
Agent Process spawns Python subprocess (run.py)
                   ↓
Agent Events parser extracts phase events
                   ↓
IPC broadcasts updates to renderer
                   ↓
Renderer stores update UI state
```

## Renderer Process Architecture

The renderer is a React single-page application with component-based architecture.

### Component Organization

**Layout Components**
- `App.tsx` - Root component, routing, global state
- `Sidebar.tsx` - Navigation sidebar with view switching
- `ProjectTabBar.tsx` - Multi-project tab management with drag-and-drop

**Feature Views**
- `KanbanBoard.tsx` - Task management board (Kanban columns)
- `Roadmap.tsx` - Project roadmap generation and visualization
- `Context.tsx` - Project context discovery (services, dependencies, APIs)
- `Ideation.tsx` - AI-powered feature ideation
- `Insights.tsx` - Codebase quality insights
- `TerminalGrid.tsx` - Integrated terminals with PTY support
- `Changelog.tsx` - Release changelog generation
- `Worktrees.tsx` - Git worktree management
- `GitHubIssues.tsx` / `GitLabIssues.tsx` - Issue tracking integration
- `GitHubPRs.tsx` / `GitLabMergeRequests.tsx` - Pull request management

**Task Management**
- `TaskCard.tsx` - Individual task card display
- `TaskDetailModal.tsx` - Full task details with execution logs
- `TaskCreationWizard.tsx` - Multi-step task creation flow
- `task-detail/` - Modular task detail panels

**Settings & Configuration**
- `settings/AppSettings.tsx` - App-wide settings dialog
- `settings/ProjectSettings.tsx` - Per-project configuration
- `AgentProfiles.tsx` - AI model profile management
- `CustomModelModal.tsx` - Custom model configuration

**Authentication**
- `onboarding/` - First-run onboarding wizard
- `RateLimitModal.tsx` - Usage limit warnings
- `AuthFailureModal.tsx` - Authentication error handling

### State Management

**Zustand Stores** (`renderer/stores/`)

Auto Claude uses Zustand for lightweight, performant state management:

| Store | Purpose |
|-------|---------|
| `project-store.ts` | Projects, tabs, active project |
| `task-store.ts` | Tasks, subtasks, execution state |
| `terminal-store.ts` | Terminal sessions, PTY state |
| `settings-store.ts` | App settings, user preferences |
| `claude-profile-store.ts` | OAuth profiles, authentication |
| `roadmap-store.ts` | Roadmap generation state |
| `ideation-store.ts` | Feature ideation sessions |
| `insights-store.ts` | Codebase insights data |
| `changelog-store.ts` | Changelog generation state |
| `context-store.ts` | Project context discovery |
| `github/` | GitHub integration (issues, PRs) |
| `gitlab/` | GitLab integration (issues, MRs) |

**Store Architecture Pattern**
```typescript
// Example: project-store.ts
export const useProjectStore = create<ProjectState>((set, get) => ({
  // State
  projects: [],
  selectedProjectId: null,

  // Actions
  setProjects: (projects) => set({ projects }),
  selectProject: (id) => set({ selectedProjectId: id }),

  // Selectors
  getSelectedProject: () => get().projects.find(p => p.id === get().selectedProjectId)
}));
```

### Custom Hooks

**IPC Communication** (`renderer/hooks/`)
- `useIpc.ts` - Global IPC event listeners for real-time updates
- `useGlobalTerminalListeners.ts` - Buffer terminal output across project switches

**UI State**
- `useResolvedAgentSettings.ts` - Resolve agent settings (project → profile → defaults)
- `useVirtualizedLogs.ts` - Virtualize long log lists for performance
- `useVirtualizedTree.ts` - Virtualize file trees

**Feature-Specific**
- `useTerminalProfileChange.ts` - Handle terminal profile switches
- `use-profile-swap-notifications.ts` - Proactive profile swap suggestions
- `use-toast.ts` - Toast notification system

### IPC Communication

**Bidirectional Communication** (`preload/api/`)

The preload script exposes a type-safe API for renderer-to-main communication:

```typescript
// Renderer invokes main process
window.electronAPI.createTask(projectId, taskData)
window.electronAPI.startAgent(taskId)

// Main process broadcasts to renderer
window.electronAPI.onTaskUpdated((task) => { /* update store */ })
window.electronAPI.onAgentStatus((status) => { /* update UI */ })
```

**Key IPC Channels**
- Task lifecycle: `task:created`, `task:updated`, `task:deleted`
- Agent events: `agent:status`, `agent:phase-event`, `agent:log`
- Terminal: `terminal:output`, `terminal:exit`
- Projects: `project:updated`, `project:settings-changed`
- Auth: `auth:profile-added`, `auth:rate-limit-hit`

## Cross-Platform Support

**Platform Abstraction** (`main/platform/`)

Critical for supporting Windows, macOS, and Linux:

```typescript
// Platform detection
import { isWindows, isMacOS, isLinux } from './platform';

// Executable discovery
const claudePath = await findExecutable('claude', getClaudeCliPaths());

// Path handling
const fullPath = joinPaths(dir, 'subdir', 'file.txt');
```

**Why This Matters**
- CI tests all three platforms before merge
- Prevents platform-specific bugs from breaking users
- Centralized platform checks (avoid scattered `process.platform === 'win32'`)

## Internationalization (i18n)

**Translation System** (`shared/i18n/`)

Uses `react-i18next` for multi-language support:

```typescript
// In component
const { t } = useTranslation(['navigation', 'common']);

// Use translation keys (NOT hardcoded strings!)
<span>{t('navigation:items.githubPRs')}</span>  // ✅ CORRECT
<span>GitHub PRs</span>                          // ❌ WRONG
```

**Translation Namespaces**
- `common.json` - Shared labels, buttons
- `navigation.json` - Sidebar navigation
- `settings.json` - Settings page
- `dialogs.json` - Dialog boxes
- `tasks.json` - Task-related content
- `errors.json` - Error messages (with substitution support)

**Adding New UI Text**
1. Add translation key to ALL language files (`en/*.json`, `fr/*.json`)
2. Use `namespace:section.key` format
3. Never use hardcoded strings in JSX/TSX files

## Key Architectural Patterns

### Component Composition

**Modular Components**
- Break large components into focused subcomponents
- Use `components/task-detail/` pattern for complex features
- Separate presentation from logic (hooks + components)

**Example: Task Detail Modal**
```
TaskDetailModal.tsx (container)
├── TaskHeader.tsx (title, status, metadata)
├── TaskExecutionPanel.tsx (logs, progress)
├── TaskSubtasksPanel.tsx (subtask list)
└── TaskActionsPanel.tsx (buttons, actions)
```

### State Synchronization

**Real-Time Updates**
- Main process broadcasts IPC events on state changes
- Renderer stores update via IPC listeners
- Components re-render automatically via Zustand subscriptions

**Example Flow**
```
Python agent updates spec.md
      ↓
Main process detects file change
      ↓
IPC broadcast: task:updated
      ↓
useIpc hook catches event
      ↓
task-store updates state
      ↓
TaskCard component re-renders
```

### Virtualization

**Performance Optimization**
- Use `@tanstack/react-virtual` for long lists
- Implemented in: logs viewer, file trees, task lists
- Renders only visible items (handles 10k+ items smoothly)

### Terminal Management

**PTY Integration**
- Main process spawns PTY processes via `@lydell/node-pty`
- Renderer displays terminals via `@xterm/xterm`
- Sessions persist across project switches
- Output buffering prevents data loss

## Testing

**Test Structure** (`src/__tests__/`)
- Unit tests: `*.test.ts` (Vitest)
- Integration tests: `integration/*.test.ts`
- E2E tests: `e2e/*.test.ts` (Playwright)

**Key Test Areas**
- IPC communication reliability
- Agent state machine transitions
- Terminal session persistence
- Multi-project tab management
- Cross-platform path handling

## Build System

**Electron Vite** (`electron-vite.config.ts`)
- Main process: Bundles Node.js code
- Renderer: Vite + React + TypeScript
- Preload: Isolated context bridge
- Hot reload in development mode

**Production Build**
```bash
npm run build              # Build all processes
npm run package            # Package for current platform
npm run package:mac        # macOS (DMG, ZIP)
npm run package:win        # Windows (NSIS, ZIP)
npm run package:linux      # Linux (AppImage, DEB, Flatpak)
```

## Dependencies

**Core Framework**
- `electron` - Desktop app framework
- `react` + `react-dom` - UI library
- `zustand` - State management
- `@xterm/xterm` - Terminal emulator
- `@lydell/node-pty` - PTY process support

**UI Components**
- `@radix-ui/*` - Headless UI primitives
- `tailwindcss` - Utility-first CSS
- `lucide-react` - Icon library
- `@dnd-kit/*` - Drag and drop

**Utilities**
- `i18next` + `react-i18next` - Internationalization
- `chokidar` - File watching
- `electron-log` - Logging
- `electron-updater` - Auto-updates

## Migration Notes

**From Monolithic to Modular**
- Originally a single large component tree
- Refactored into focused feature modules
- Shared state moved to Zustand stores
- Platform-specific code centralized in `platform/`

**Backwards Compatibility**
- Old IPC channels maintained for gradual migration
- Settings format versioned for safe upgrades
- Project data structure evolves with migrations

## Development Guidelines

### Adding a New View

1. Create component in `renderer/components/`
2. Add route in `App.tsx`
3. Add sidebar navigation item in `Sidebar.tsx`
4. Add translation keys for UI text
5. Create Zustand store if needed for view-specific state
6. Add IPC handlers in `main/ipc-handlers/` if backend interaction needed

### Adding IPC Communication

1. Define types in `shared/types/`
2. Add handler in `main/ipc-handlers/`
3. Expose API in `preload/api/`
4. Use in renderer via `window.electronAPI`
5. Add error handling and validation

### Platform-Specific Code

- Add to `main/platform/` module (NOT scattered in feature code)
- Write tests for all platforms (mock `process.platform`)
- Use feature detection over OS checks when possible
- Document platform differences in code comments

### Performance Optimization

- Virtualize long lists with `@tanstack/react-virtual`
- Debounce IPC events for high-frequency updates
- Memoize expensive computations with `useMemo`
- Lazy load large components with `React.lazy()`

## Security

**Electron Security**
- Context isolation enabled
- Node integration disabled in renderer
- Preload script for controlled API exposure
- CSP headers for web content security

**Credential Storage**
- OAuth tokens encrypted with `electron-store`
- GitHub/GitLab tokens stored in OS keychain
- API keys never logged or exposed to renderer

**Input Validation**
- All IPC inputs validated in main process
- File paths sanitized to prevent directory traversal
- Command injection prevented via argument arrays

## Future Enhancements

**Planned Improvements**
- WebSocket support for real-time collaboration
- Plugin system for custom integrations
- Advanced terminal features (split panes, tmux integration)
- Offline mode with local model support
- Enhanced accessibility (ARIA, keyboard navigation)
