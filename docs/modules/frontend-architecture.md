# Frontend Architecture

Electron desktop application for Auto Claude autonomous coding framework. Built with React, TypeScript, and modern web technologies.

## Architecture

The frontend is organized into four main modules following Electron's architecture:

```
apps/frontend/src/
├── main/              # Electron main process (Node.js)
├── renderer/          # React UI (Browser)
├── shared/            # Shared code between main and renderer
└── preload/           # Electron preload scripts (Security bridge)
```

## Modules

### `main/` - Electron Main Process (Node.js Backend)

The main process runs in Node.js and handles system-level operations, file I/O, and orchestrates the backend Python agents.

**Key modules:**

| Module | Purpose | Size |
|--------|---------|------|
| **agent/** | Agent process management and state tracking | 18 KB |
| **ipc-handlers/** | IPC communication handlers for renderer ↔ main | 485 KB |
| **platform/** | Cross-platform abstractions (Windows/macOS/Linux) | 52 KB |
| **terminal/** | Terminal session management (node-pty) | - |
| **claude-profile/** | Claude API profile and rate limit management | - |
| **integrations/** | Third-party integrations (Linear, GitHub, GitLab) | - |
| **insights/** | AI-powered insights and chat history | - |
| **changelog/** | Changelog generation and version management | - |
| **services/** | Background services (updates, monitoring) | - |
| **utils/** | Utility functions (fs, env, config) | - |

**Main process responsibilities:**
- Spawning and managing Python agent subprocesses
- File system operations (project files, specs, worktrees)
- Terminal sessions via node-pty
- IPC communication with renderer process
- Native OS integrations (notifications, menus)
- Claude API authentication and profile management
- Rate limit detection and auto-recovery
- Python environment management

**Entry point:** `main/index.ts`

### `renderer/` - React Frontend (Browser)

The renderer process runs in Chromium and provides the React-based user interface.

**Key modules:**

| Module | Purpose |
|--------|---------|
| **components/** | React UI components (1000+ KB) |
| **contexts/** | React contexts for state management |
| **hooks/** | Custom React hooks |
| **stores/** | State management (Zustand/Jotai) |
| **lib/** | UI utilities and helpers |
| **styles/** | Tailwind CSS and global styles |

**Major components:**
- `App.tsx` - Root application component
- `Sidebar.tsx` - Navigation sidebar
- `KanbanBoard.tsx` - Task management board
- `TerminalGrid.tsx` - Multi-terminal interface
- `TaskCreationWizard.tsx` - Spec creation wizard
- `Roadmap.tsx` - Roadmap planning view
- `Context.tsx` - Project context viewer
- `Ideation.tsx` - AI brainstorming interface
- `Insights.tsx` - Chat history and insights
- `AgentTools.tsx` - Agent management interface

**UI Framework:**
- **React 18** with hooks and functional components
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **Radix UI** for accessible primitives
- **shadcn/ui** component library
- **@dnd-kit** for drag-and-drop
- **CodeMirror 6** for code editing
- **xterm.js** for terminal emulation

**Entry point:** `renderer/App.tsx`

### `shared/` - Shared Code

Code shared between main and renderer processes. Must be serializable for IPC communication.

**Structure:**

```
shared/
├── types/             # TypeScript type definitions
│   ├── common.ts      # Common types
│   ├── project.ts     # Project types
│   ├── task.ts        # Task/spec types
│   ├── terminal.ts    # Terminal types
│   ├── agent.ts       # Agent types
│   ├── settings.ts    # Settings types
│   ├── ipc.ts         # IPC channel types
│   └── ...
├── constants/         # Shared constants
│   ├── ipc-channels.ts
│   └── defaults.ts
├── utils/             # Shared utilities
│   ├── debug-logger.ts
│   └── validation.ts
└── i18n/              # Internationalization
    └── locales/       # Translation files (en, fr, etc.)
```

**Key principles:**
- **Type-safe IPC:** All IPC channels have typed contracts
- **No DOM/Node APIs:** Must work in both processes
- **Serializable only:** No functions, classes, or circular refs
- **i18n support:** All user-facing strings use translation keys

### `preload/` - Electron Preload Scripts (Security Bridge)

The preload script bridges the gap between main and renderer processes securely using `contextBridge`.

**Purpose:**
- Expose safe IPC APIs to renderer via `window.electronAPI`
- Prevent direct access to Node.js APIs from renderer
- Type-safe API with TypeScript definitions

**Structure:**

```
preload/
├── index.ts           # Entry point, exposes electronAPI
└── api/               # API definitions
    ├── agent-api.ts
    ├── project-api.ts
    ├── terminal-api.ts
    ├── settings-api.ts
    └── ...
```

**How it works:**

```typescript
// preload/index.ts
const electronAPI = createElectronAPI();
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// renderer can now use:
const projects = await window.electronAPI.project.listProjects();
```

**Security model:**
- **No Node.js in renderer:** Renderer cannot access Node.js APIs directly
- **Explicit API surface:** Only exposed APIs are accessible
- **Type safety:** Full TypeScript support for all APIs

## IPC Communication Pattern

Auto Claude uses a type-safe IPC architecture:

```
┌─────────────────┐                    ┌──────────────────┐
│   Renderer      │                    │   Main Process   │
│   (React UI)    │                    │   (Node.js)      │
└─────────────────┘                    └──────────────────┘
        │                                        │
        │  1. Call electronAPI method            │
        │  ──────────────────────────────────>   │
        │     window.electronAPI.project.list()  │
        │                                        │
        │                                    2. ipcMain.handle
        │                                    processes request
        │                                        │
        │  3. Return result                      │
        │  <──────────────────────────────────   │
        │     { projects: [...] }                │
        │                                        │
```

**Key files:**
- `shared/types/ipc.ts` - IPC channel type definitions
- `shared/constants/ipc-channels.ts` - IPC channel names
- `preload/api/` - Exposed API implementations
- `main/ipc-handlers/` - Main process handlers

## Module Dependencies

```
renderer/
  ├── shared/ (types, constants, utils, i18n)
  └── preload/ (electronAPI)

main/
  ├── shared/ (types, constants, utils)
  ├── agent/ (process management)
  ├── ipc-handlers/ (communication)
  ├── platform/ (OS abstractions)
  └── services/ (background tasks)

preload/
  └── shared/ (types for API contracts)
```

## Cross-Platform Support

Auto Claude supports Windows, macOS, and Linux through platform abstractions:

**Platform module:** `main/platform/`

```typescript
// Platform detection
import { isWindows, isMacOS, isLinux } from './platform';

// Path handling
import { getPathDelimiter, joinPaths } from './platform';

// Executable detection
import { findExecutable, getExecutableExtension } from './platform';

// Binary directories
import { getBinaryDirectories } from './platform';
```

**Platform-specific features:**
- **Windows:** .exe extensions, `;` path delimiter, Windows Terminal integration
- **macOS:** .app bundles, Keychain integration, Touch Bar support
- **Linux:** .desktop files, system notifications

**CI/CD:** All three platforms tested on every PR via GitHub Actions.

See [Cross-Platform Development](../../CLAUDE.md#cross-platform-development) for guidelines.

## Internationalization (i18n)

All user-facing text uses `react-i18next` for internationalization.

**Translation files:** `shared/i18n/locales/{lang}/*.json`

**Namespaces:**
- `common.json` - Shared labels, buttons, common terms
- `navigation.json` - Sidebar navigation items
- `settings.json` - Settings page content
- `dialogs.json` - Dialog boxes and modals
- `tasks.json` - Task/spec related content
- `errors.json` - Error messages (with substitution)
- `onboarding.json` - Onboarding wizard
- `welcome.json` - Welcome screen

**Usage:**

```tsx
import { useTranslation } from 'react-i18next';

const MyComponent = () => {
  const { t } = useTranslation(['navigation', 'common']);

  return (
    <span>{t('navigation:items.githubPRs')}</span>  // ✅ CORRECT
    // NOT: <span>GitHub PRs</span>                 // ❌ WRONG
  );
};
```

**CRITICAL:** Never hardcode user-facing strings. Always use translation keys.

## State Management

Auto Claude uses a hybrid state management approach:

**Local state:**
- React `useState` for component-local state
- React `useReducer` for complex component state

**Global state:**
- React Context for theme, settings, authentication
- Zustand/Jotai stores for cross-component state
- IPC events for main ↔ renderer synchronization

**Server state:**
- SWR or React Query for data fetching (future)

## Testing

The frontend uses Vitest for unit/integration tests and Playwright for E2E tests:

```bash
# Unit/integration tests
npm test                    # Run all tests
npm run test:watch          # Watch mode
npm run test:coverage       # Coverage report

# E2E tests (Playwright)
npm run test:e2e            # Run E2E tests
```

**Test locations:**
- `src/main/__tests__/` - Main process tests
- `src/renderer/__tests__/` - Renderer tests
- `src/shared/__tests__/` - Shared code tests
- `e2e/` - End-to-end tests

**Test utilities:**
- `src/__tests__/setup.ts` - Test setup
- `src/__mocks__/` - Mocks for Electron, Sentry, etc.

## Development Workflow

**Starting the app:**

```bash
npm run dev              # Development mode
npm run dev:debug        # With debug logging
npm run dev:mcp          # With remote debugging (port 9222)
```

**Building:**

```bash
npm run build            # Build for production
npm run package          # Package for current platform
npm run package:mac      # Package for macOS
npm run package:win      # Package for Windows
npm run package:linux    # Package for Linux
```

**Code quality:**

```bash
npm run lint             # Lint code
npm run lint:fix         # Auto-fix lint issues
npm run format           # Format code (Biome)
npm run typecheck        # TypeScript type checking
```

## Agent Integration

The frontend integrates with Python backend agents via subprocess spawning:

**Flow:**

1. Renderer initiates task via `electronAPI.agent.startTask()`
2. Main process spawns Python subprocess: `python run.py --spec 001`
3. Main process parses agent output (NDJSON stream)
4. Main process sends progress updates to renderer via IPC events
5. Renderer updates UI in real-time

**Key files:**
- `main/agent/agent-manager.ts` - High-level agent orchestration
- `main/agent/agent-process.ts` - Subprocess lifecycle management
- `main/agent/agent-queue.ts` - Task queue and scheduling
- `main/agent/parsers/` - Agent output parsers
- `main/ipc-handlers/agent-events-handlers.ts` - IPC event forwarding

## Python Environment Management

Auto Claude bundles Python with the app or uses system Python:

**Python discovery:**
1. Check bundled Python (for packaged apps)
2. Check `PYTHON_PATH` env variable
3. Search system PATH for `python3`, `python`

**Virtual environment:**
- Backend uses `uv` for dependency management
- Main process activates venv before spawning agents

**Key files:**
- `main/python-env-manager.ts` - Python discovery and venv activation
- `scripts/download-python.cjs` - Download standalone Python for packaging
- `scripts/package-with-python.cjs` - Bundle Python with app

## Security

The frontend follows Electron security best practices:

**Security features:**
- **Context isolation:** Enabled by default
- **Node integration:** Disabled in renderer
- **Content Security Policy:** Strict CSP headers
- **Webview:** Disabled
- **Remote module:** Disabled
- **Sandbox:** Enabled for renderer process
- **Navigation protection:** Only allow trusted domains
- **IPC validation:** Validate all IPC inputs

**Key files:**
- `main/index.ts` - BrowserWindow security settings
- `preload/index.ts` - contextBridge API exposure
- `main/ipc-handlers/` - Input validation

## Benefits

1. **Separation of Concerns**: Clear boundaries between UI, IPC, and system operations
2. **Type Safety**: End-to-end TypeScript with strict null checks
3. **Cross-Platform**: Unified codebase for Windows, macOS, and Linux
4. **Security**: Follows Electron security best practices
5. **Maintainability**: Modular architecture with focused responsibilities
6. **Testability**: Isolated modules can be tested independently
7. **Internationalization**: Multi-language support built-in

## Module Size Reference

Approximate module sizes (uncompressed):

| Module | Size |
|--------|------|
| `main/` | ~500 KB |
| `renderer/` | ~2 MB |
| `shared/` | ~100 KB |
| `preload/` | ~10 KB |
| **Total** | **~2.6 MB** |

## Migration Notes

When adding new features:

1. **New IPC channel?** → Add to `shared/types/ipc.ts` and `shared/constants/ipc-channels.ts`
2. **New component?** → Add to `renderer/components/`
3. **New main process logic?** → Add handler to `main/ipc-handlers/`
4. **Cross-platform code?** → Use `main/platform/` abstractions
5. **User-facing text?** → Add translation keys to `shared/i18n/locales/`

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project overview and development guidelines
- [RELEASE.md](../../RELEASE.md) - Release process
- [apps/backend/agents/README.md](../../apps/backend/agents/README.md) - Backend agents architecture
- [main/ipc-handlers/README.md](../../apps/frontend/src/main/ipc-handlers/README.md) - IPC handlers guide
