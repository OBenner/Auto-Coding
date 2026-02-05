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

## Platform Abstraction

**CRITICAL:** Auto Claude supports Windows, macOS, and Linux. Platform-specific bugs are the #1 source of breakage. All platform-specific code MUST be centralized in the platform abstraction layer.

### The Problem

When developers fix something using platform-specific assumptions, it breaks on other platforms. This happens because:

1. **Scattered platform checks** - `process.platform === 'win32'` checks spread across 50+ files
2. **Hardcoded paths** - Direct paths like `C:\Program Files` or `/opt/homebrew/bin` throughout code
3. **CI tested only on Linux** - Platform-specific bugs weren't caught until after merge

### The Solution

**Centralized Platform Abstraction Layer:** `main/platform/`

All platform-specific code lives in dedicated modules:

```
main/platform/
├── index.ts           # Platform detection (isWindows, isMacOS, isLinux)
├── paths.ts           # Path utilities (joinPaths, getPathDelimiter)
├── executables.ts     # Executable discovery (findExecutable)
└── shell.ts           # Shell command handling (requiresShell)
```

**Key principles:**
- **Never check `process.platform` directly** - Always use platform abstraction functions
- **Never hardcode paths** - Use `findExecutable()` and dynamic path discovery
- **Feature detection over OS detection** - Check for file/path existence when possible
- **Multi-platform CI** - All three platforms tested on every PR

### Platform Abstraction API

#### Platform Detection

```typescript
import { isWindows, isMacOS, isLinux } from './platform';

// ❌ WRONG - Direct platform check
if (process.platform === 'win32') {
  // Windows logic
}

// ✅ CORRECT - Use abstraction
if (isWindows()) {
  // Windows logic
}
```

**Available functions:**
- `isWindows()` - Returns `true` on Windows
- `isMacOS()` - Returns `true` on macOS
- `isLinux()` - Returns `true` on Linux

#### Path Handling

```typescript
import { joinPaths, getPathDelimiter } from './platform';

// ❌ WRONG - Hardcoded Windows path
const claudePath = 'C:\\Program Files\\Claude\\claude.exe';

// ❌ WRONG - Hardcoded macOS path
const brewPath = '/opt/homebrew/bin/python3';

// ❌ WRONG - Manual path joining
const fullPath = dir + '/subdir/file.txt';

// ✅ CORRECT - Use platform abstraction
const fullPath = joinPaths(dir, 'subdir', 'file.txt');
const pathDelimiter = getPathDelimiter();  // ';' on Windows, ':' on Unix
```

**Available functions:**
- `joinPaths(...parts: string[])` - Join path segments using OS-specific separator
- `getPathDelimiter()` - Get `;` (Windows) or `:` (Unix) for PATH environment variable

#### Executable Discovery

```typescript
import { findExecutable, getExecutableExtension } from './platform';

// ❌ WRONG - Assume executable name
const pythonPath = 'python';  // Doesn't exist on many systems

// ✅ CORRECT - Use findExecutable with fallbacks
const pythonPath = await findExecutable('python', [
  'python3',
  'python',
]);

// Get platform-specific extension
const ext = getExecutableExtension();  // '.exe' on Windows, '' on Unix
```

**Available functions:**
- `findExecutable(name: string, fallbacks?: string[])` - Find executable in PATH or common locations
- `getExecutableExtension()` - Get `.exe` (Windows) or `` (Unix)
- `getBinaryDirectories()` - Get platform-specific binary directories

#### Shell Command Handling

```typescript
import { requiresShell } from './platform';

// Check if command needs shell on Windows (.cmd, .bat files)
const needsShell = requiresShell(command);

if (needsShell) {
  spawn(command, args, { shell: true });
} else {
  spawn(command, args);
}
```

**Available functions:**
- `requiresShell(command: string)` - Returns `true` if command needs shell (e.g., .cmd/.bat on Windows)

### Platform-Specific Features

**Windows:**
- `.exe` file extensions
- `;` PATH delimiter
- Windows Terminal integration
- PowerShell support
- Case-insensitive filesystem

**macOS:**
- `.app` application bundles
- macOS Keychain integration
- Touch Bar support
- Code signing requirements
- `/opt/homebrew/bin` for Homebrew (Apple Silicon)
- `/usr/local/bin` for Homebrew (Intel)

**Linux:**
- `.desktop` files
- System notifications via D-Bus
- Multiple package managers (apt, yum, pacman)
- `/usr/bin`, `/usr/local/bin` standard paths

### Usage Patterns

#### Adding Platform-Specific Logic

When you need platform-specific code, add it to the platform module, NOT scattered in your feature code:

```typescript
// ✅ CORRECT - Add to platform/paths.ts
export function getMyToolPaths(): string[] {
  if (isWindows()) {
    return [
      joinPaths('C:', 'Program Files', 'MyTool', 'tool.exe'),
      joinPaths(process.env.USERPROFILE || '', 'MyTool', 'tool.exe'),
    ];
  }
  if (isMacOS()) {
    return [
      '/Applications/MyTool.app/Contents/MacOS/tool',
      joinPaths(process.env.HOME || '', 'Applications', 'MyTool.app', 'Contents', 'MacOS', 'tool'),
    ];
  }
  return [
    '/usr/local/bin/mytool',
    '/usr/bin/mytool',
  ];
}

// Then use in your code:
import { findExecutable, getMyToolPaths } from './platform';
const toolPath = await findExecutable('mytool', getMyToolPaths());
```

#### Testing Platform-Specific Code

Mock `process.platform` in tests to verify behavior on all platforms:

```typescript
// Mock platform detection
jest.mock('./platform', () => ({
  isWindows: () => true,  // Simulate Windows
  isMacOS: () => false,
  isLinux: () => false,
}));

// Test your code
test('works on Windows', () => {
  // Test Windows-specific behavior
});

// Reset and test other platforms
jest.mock('./platform', () => ({
  isWindows: () => false,
  isMacOS: () => true,  // Simulate macOS
  isLinux: () => false,
}));

test('works on macOS', () => {
  // Test macOS-specific behavior
});
```

### Multi-Platform CI

**GitHub Actions tests all three platforms on every PR:**

```yaml
# .github/workflows/ci.yml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
```

A PR cannot merge unless all platforms pass:
- ✅ Ubuntu (Linux)
- ✅ Windows Server
- ✅ macOS (latest)

### Best Practices

1. **Never check `process.platform` directly** - Use `isWindows()`, `isMacOS()`, `isLinux()`
2. **Never hardcode paths** - Use `findExecutable()` and `getBinaryDirectories()`
3. **Add platform logic to platform module** - Not scattered in feature code
4. **Use feature detection when possible** - Check for file existence, not just OS
5. **Test on all platforms** - Rely on CI to catch platform-specific bugs
6. **Document platform differences** - Explain why platform-specific code is needed

### Common Pitfalls

❌ **Direct platform checks:**
```typescript
if (process.platform === 'win32') { ... }
```

❌ **Hardcoded paths:**
```typescript
const path = 'C:\\Program Files\\Tool\\tool.exe';
```

❌ **Assuming forward slashes work:**
```typescript
const path = dir + '/subdir/file.txt';
```

❌ **Assuming executables have no extension:**
```typescript
const executable = 'python';  // Missing .exe on Windows
```

✅ **Use platform abstraction:**
```typescript
import { isWindows, joinPaths, findExecutable } from './platform';

if (isWindows()) { ... }
const path = joinPaths(dir, 'subdir', 'file.txt');
const python = await findExecutable('python', ['python3', 'python']);
```

### Related Documentation

See [Cross-Platform Development](../../CLAUDE.md#cross-platform-development) for detailed guidelines on writing cross-platform code.

## Internationalization (i18n)

Auto Claude frontend uses `react-i18next` for comprehensive internationalization support. All user-facing text must use translation keys.

### Architecture

**Library:** `react-i18next` with `i18next`
**Configuration:** `shared/i18n/index.ts`
**Translation files:** `shared/i18n/locales/{lang}/*.json`
**Default language:** English (`en`)
**Fallback language:** English (`en`)
**Suspense:** Disabled for Electron compatibility

### Directory Structure

```
shared/i18n/
├── index.ts                    # i18n initialization and configuration
└── locales/
    ├── en/                     # English translations
    │   ├── common.json         # Shared UI elements (buttons, labels, accessibility)
    │   ├── navigation.json     # Sidebar navigation and sections
    │   ├── settings.json       # Settings page content
    │   ├── tasks.json          # Task/spec management content
    │   ├── welcome.json        # Welcome screen content
    │   ├── onboarding.json     # Onboarding wizard content
    │   ├── dialogs.json        # Dialog boxes and modals
    │   ├── gitlab.json         # GitLab integration UI
    │   ├── taskReview.json     # Task review and QA content
    │   ├── terminal.json       # Terminal-related content
    │   └── errors.json         # Error messages with interpolation
    └── fr/                     # French translations
        ├── common.json
        ├── navigation.json
        ├── settings.json
        ├── tasks.json
        ├── welcome.json
        ├── onboarding.json
        ├── dialogs.json
        ├── gitlab.json
        ├── taskReview.json
        ├── terminal.json
        └── errors.json
```

### Translation Namespaces

| Namespace | Purpose | Example Keys |
|-----------|---------|--------------|
| **common** | Shared UI elements, buttons, labels, accessibility strings | `projectTab.settings`, `accessibility.deleteFeatureAriaLabel` |
| **navigation** | Sidebar navigation items, sections, actions, tooltips | `items.kanban`, `sections.project`, `actions.newTask` |
| **settings** | Settings page content, preferences, configuration | Settings-specific translations |
| **tasks** | Task/spec management, kanban board, statuses | Task-related content |
| **welcome** | Welcome screen content and onboarding flow | Welcome page strings |
| **onboarding** | Onboarding wizard steps and instructions | Wizard content |
| **dialogs** | Dialog boxes, modals, confirmation prompts | Dialog titles, buttons, messages |
| **gitlab** | GitLab integration UI (issues, merge requests) | GitLab-specific content |
| **taskReview** | Task review, QA workflow, acceptance criteria | Review process strings |
| **terminal** | Terminal-related UI, commands, status messages | Terminal content |
| **errors** | Error messages with interpolation support | `task.parseImplementationPlan`, `task.jsonError.titleSuffix` |

### Translation Key Structure

Translation keys follow a hierarchical structure using dot notation:

```
namespace:section.subsection.key
```

**Examples:**
- `navigation:items.githubPRs` - GitHub PRs menu item
- `common:projectTab.settings` - Project settings label
- `common:accessibility.deleteFeatureAriaLabel` - Accessibility label for delete button
- `errors:task.parseImplementationPlan` - Error message with interpolation

### Usage in Components

**Basic usage:**

```tsx
import { useTranslation } from 'react-i18next';

const MyComponent = () => {
  const { t } = useTranslation(['navigation', 'common']);

  return (
    <div>
      <span>{t('navigation:items.githubPRs')}</span>
      <button>{t('common:projectTab.settings')}</button>
    </div>
  );
};
```

**With interpolation (dynamic values):**

```tsx
import { useTranslation } from 'react-i18next';

const ErrorDisplay = ({ error }) => {
  const { t } = useTranslation(['errors']);

  // errors.json: { "task": { "parseImplementationPlan": "Failed to parse implementation_plan.json for {{specId}}: {{error}}" } }
  return (
    <span>
      {t('errors:task.parseImplementationPlan', {
        specId: '001-my-feature',
        error: error.message
      })}
    </span>
  );
};
```

**With accessibility labels:**

```tsx
import { useTranslation } from 'react-i18next';

const DeleteButton = () => {
  const { t } = useTranslation(['common']);

  return (
    <button aria-label={t('common:accessibility.deleteFeatureAriaLabel')}>
      <TrashIcon />
    </button>
  );
};
```

### Adding New Translations

**1. Add translation keys to ALL language files:**

```bash
# Add to en/common.json
{
  "myFeature": {
    "title": "My Feature",
    "description": "This is my feature"
  }
}

# Add to fr/common.json
{
  "myFeature": {
    "title": "Ma Fonctionnalité",
    "description": "Ceci est ma fonctionnalité"
  }
}
```

**2. Import and register in `shared/i18n/index.ts` (if adding a new namespace):**

```typescript
import enMyFeature from './locales/en/myFeature.json';
import frMyFeature from './locales/fr/myFeature.json';

export const resources = {
  en: {
    // ... existing namespaces
    myFeature: enMyFeature
  },
  fr: {
    // ... existing namespaces
    myFeature: frMyFeature
  }
};
```

**3. Use in components:**

```tsx
const { t } = useTranslation(['myFeature']);
<h1>{t('myFeature:title')}</h1>
```

### Supported Languages

- **English (en)** - Default and fallback language
- **French (fr)** - Fully supported

The language preference is stored in the user's settings and persists across sessions.

### Best Practices

**DO:**
- ✅ Always use translation keys for user-facing text
- ✅ Use interpolation for dynamic values: `{{variableName}}`
- ✅ Add translations to ALL language files when adding new keys
- ✅ Use descriptive, hierarchical key names
- ✅ Group related translations under common sections
- ✅ Use the `common` namespace for shared UI elements
- ✅ Provide accessibility labels using translation keys

**DON'T:**
- ❌ Never hardcode user-facing strings in JSX
- ❌ Don't use hardcoded strings even in console.log for UI-visible errors
- ❌ Don't skip translations for "temporary" features
- ❌ Don't use emojis in translation keys (emojis are fine in values)
- ❌ Don't create duplicate keys across namespaces

**Examples:**

```tsx
// ❌ WRONG - Hardcoded string
<button>Delete Feature</button>

// ✅ CORRECT - Translation key
const { t } = useTranslation(['common']);
<button>{t('common:accessibility.deleteAriaLabel')}</button>

// ❌ WRONG - Missing interpolation
<span>Failed to parse implementation_plan.json for 001-my-feature</span>

// ✅ CORRECT - Using interpolation
const { t } = useTranslation(['errors']);
<span>{t('errors:task.parseImplementationPlan', { specId, error })}</span>
```

### Error Message Patterns

The `errors.json` namespace uses structured error information with substitution:

```json
{
  "task": {
    "parseImplementationPlan": "Failed to parse implementation_plan.json for {{specId}}: {{error}}",
    "jsonError": {
      "titleSuffix": "(JSON Error)",
      "description": "⚠️ JSON Parse Error: {{error}}\n\nThe implementation_plan.json file is malformed. Run the backend auto-fix or manually repair the file."
    }
  }
}
```

This allows for consistent error messaging across the application with dynamic context.

### Language Switching

Users can change the language preference in the application settings. The selected language persists across sessions and is applied globally to all UI elements.

**Rule:** All new UI components MUST use translation keys. Hardcoded strings are not permitted.

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
