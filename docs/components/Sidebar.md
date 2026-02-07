# Component: Sidebar

Main navigation sidebar for Auto Code with collapsible state, dynamic navigation items, and keyboard shortcuts.

## Overview

**Type:** React Component
**Location:** `apps/frontend/src/renderer/components/Sidebar.tsx`
**Category:** UI Component
**Status:** Stable

### Purpose

The Sidebar component provides the primary navigation interface for Auto Code. It displays navigation items based on enabled integrations (GitHub/GitLab), manages project switching and initialization, and provides keyboard shortcuts for quick navigation. The sidebar can be collapsed to save screen space while maintaining full functionality through tooltips.

### Key Features

- **Dynamic Navigation Items:** Navigation items are conditionally shown based on GitHub/GitLab integration status
- **Keyboard Shortcuts:** Single-key shortcuts for quick navigation (K for Kanban, A for Terminals, etc.)
- **Collapsible State:** Sidebar can collapse to icon-only view with tooltips
- **Project Management:** Handles project initialization, git setup, and project switching
- **State Persistence:** Collapsed state is persisted to settings store
- **Integration Indicators:** Shows rate limit status, update availability, and Claude Code connection status

### Use Cases

- **Primary Navigation:** Main navigation interface for all app views (Kanban, Terminals, Insights, etc.)
- **Project Management:** Initialize new projects, set up Git repositories, switch between projects
- **Quick Access:** Use keyboard shortcuts to navigate without mouse interaction
- **Space Optimization:** Collapse sidebar when working with limited screen space

---

## Installation / Import

### React Component Import

```typescript
import { Sidebar, type SidebarView } from '@/components/Sidebar';
```

### Dependencies

**Required:**
- `react` - Core React functionality
- `react-i18next` - Internationalization for labels and tooltips
- `lucide-react` - Icon library for navigation items
- `@/components/ui/*` - Radix UI components (Button, ScrollArea, Dialog, Tooltip)
- `@/stores/project-store` - Zustand store for project management
- `@/stores/settings-store` - Zustand store for sidebar state

**Optional:**
- `@/components/AddProjectModal` - Modal for adding new projects
- `@/components/GitSetupModal` - Modal for Git repository setup
- `@/components/RateLimitIndicator` - Shows Claude API rate limit status
- `@/components/ClaudeCodeStatusBadge` - Shows connection status
- `@/components/UpdateBanner` - Shows available app updates

---

## API Reference

### Props (React) / Parameters (Python)

#### Required Props/Parameters

| Prop/Parameter | Type | Description | Example |
|----------------|------|-------------|---------|
| `onSettingsClick` | `() => void` | Callback when Settings button is clicked | `() => setShowSettings(true)` |
| `onNewTaskClick` | `() => void` | Callback when New Task button is clicked | `() => setShowTaskModal(true)` |

#### Optional Props/Parameters

| Prop/Parameter | Type | Default | Description | Example |
|----------------|------|---------|-------------|---------|
| `activeView` | `SidebarView` | `'kanban'` | Currently active view/page | `'terminals'` |
| `onViewChange` | `(view: SidebarView) => void` | `undefined` | Callback when navigation item is clicked | `(view) => navigate(view)` |

### Events / Callbacks

| Event/Callback | Signature | Description | When Triggered |
|----------------|-----------|-------------|----------------|
| `onSettingsClick` | `() => void` | Settings button clicked | User clicks Settings button in bottom section |
| `onNewTaskClick` | `() => void` | New Task button clicked | User clicks New Task button (only enabled when project is initialized) |
| `onViewChange` | `(view: SidebarView) => void` | Navigation view changed | User clicks navigation item or uses keyboard shortcut |

---

## Type Definitions

### TypeScript Types

```typescript
// Possible view/page types in the application
export type SidebarView =
  | 'kanban'              // Task board view
  | 'terminals'           // Terminal sessions
  | 'roadmap'             // Project roadmap
  | 'context'             // Context explorer
  | 'ideation'            // Ideation workspace
  | 'github-issues'       // GitHub issues (shown when GitHub enabled)
  | 'gitlab-issues'       // GitLab issues (shown when GitLab enabled)
  | 'github-prs'          // GitHub pull requests (shown when GitHub enabled)
  | 'gitlab-merge-requests' // GitLab merge requests (shown when GitLab enabled)
  | 'changelog'           // Project changelog
  | 'insights'            // AI insights
  | 'worktrees'           // Git worktree management
  | 'agent-tools'         // MCP agent tools
  | 'plugins'             // Plugin management
  | 'merge-analytics';    // Merge analytics dashboard

interface SidebarProps {
  onSettingsClick: () => void;
  onNewTaskClick: () => void;
  activeView?: SidebarView;
  onViewChange?: (view: SidebarView) => void;
}

// Navigation item configuration (internal)
interface NavItem {
  id: SidebarView;
  labelKey: string;           // i18n translation key
  icon: React.ElementType;    // Lucide icon component
  shortcut?: string;          // Single-key keyboard shortcut
}
```

---

## Usage Examples

### Basic Usage

```typescript
import { Sidebar, type SidebarView } from '@/components/Sidebar';
import { useState } from 'react';

function App() {
  const [currentView, setCurrentView] = useState<SidebarView>('kanban');
  const [showSettings, setShowSettings] = useState(false);
  const [showTaskModal, setShowTaskModal] = useState(false);

  return (
    <div className="flex h-screen">
      <Sidebar
        activeView={currentView}
        onViewChange={setCurrentView}
        onSettingsClick={() => setShowSettings(true)}
        onNewTaskClick={() => setShowTaskModal(true)}
      />
      <main className="flex-1">
        {/* Render current view based on currentView */}
      </main>
    </div>
  );
}
```

### With React Router

```typescript
import { Sidebar, type SidebarView } from '@/components/Sidebar';
import { useNavigate, useLocation } from 'react-router-dom';

function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  // Extract current view from route
  const currentView = location.pathname.slice(1) as SidebarView;

  return (
    <div className="flex h-screen">
      <Sidebar
        activeView={currentView}
        onViewChange={(view) => navigate(`/${view}`)}
        onSettingsClick={() => navigate('/settings')}
        onNewTaskClick={() => navigate('/tasks/new')}
      />
      <main className="flex-1">
        {/* Router outlet */}
      </main>
    </div>
  );
}
```

### Controlled Sidebar State

```typescript
import { Sidebar } from '@/components/Sidebar';
import { saveSettings, useSettingsStore } from '@/stores/settings-store';

function App() {
  const settings = useSettingsStore((state) => state.settings);

  // Sidebar collapse state is managed internally via settings store
  // Access current state from store:
  const isCollapsed = settings.sidebarCollapsed ?? false;

  // Toggle programmatically via settings store:
  const toggleSidebar = () => {
    saveSettings({ sidebarCollapsed: !isCollapsed });
  };

  return (
    <Sidebar
      onSettingsClick={() => console.log('Settings')}
      onNewTaskClick={() => console.log('New Task')}
    />
  );
}
```

---

## Navigation Items Configuration

### Base Navigation Items

These navigation items are always visible:

| View ID | Label Key | Icon | Shortcut | Description |
|---------|-----------|------|----------|-------------|
| `kanban` | `navigation:items.kanban` | LayoutGrid | `K` | Task board view |
| `terminals` | `navigation:items.terminals` | Terminal | `A` | Terminal sessions |
| `insights` | `navigation:items.insights` | Sparkles | `N` | AI insights |
| `roadmap` | `navigation:items.roadmap` | Map | `D` | Project roadmap |
| `ideation` | `navigation:items.ideation` | Lightbulb | `I` | Ideation workspace |
| `changelog` | `navigation:items.changelog` | FileText | `L` | Project changelog |
| `context` | `navigation:items.context` | BookOpen | `C` | Context explorer |
| `agent-tools` | `navigation:items.agentTools` | Wrench | `M` | MCP agent tools |
| `plugins` | `navigation:items.plugins` | Puzzle | `U` | Plugin management |
| `worktrees` | `navigation:items.worktrees` | GitBranch | `W` | Git worktree management |
| `merge-analytics` | `navigation:items.mergeAnalytics` | BarChart3 | `Y` | Merge analytics dashboard |

### GitHub Navigation Items

Shown when `GITHUB_ENABLED=true` in project `.env`:

| View ID | Label Key | Icon | Shortcut | Description |
|---------|-----------|------|----------|-------------|
| `github-issues` | `navigation:items.githubIssues` | Github | `G` | GitHub issues |
| `github-prs` | `navigation:items.githubPRs` | GitPullRequest | `P` | GitHub pull requests |

### GitLab Navigation Items

Shown when `GITLAB_ENABLED=true` in project `.env`:

| View ID | Label Key | Icon | Shortcut | Description |
|---------|-----------|------|----------|-------------|
| `gitlab-issues` | `navigation:items.gitlabIssues` | GitlabIcon | `B` | GitLab issues |
| `gitlab-merge-requests` | `navigation:items.gitlabMRs` | GitMerge | `R` | GitLab merge requests |

---

## Keyboard Shortcuts

### Shortcut Behavior

- **Activation:** Plain key press (no modifiers like Ctrl/Cmd/Alt)
- **Scope:** Only active when a project is selected
- **Context:** Disabled when typing in input fields, textareas, or content-editable elements
- **Feedback:** Visual highlight of active navigation item

### Available Shortcuts

| Key | View | Description |
|-----|------|-------------|
| `K` | Kanban | Jump to task board |
| `A` | Terminals | Jump to terminal sessions (Agent) |
| `N` | Insights | Jump to AI insights (New insights) |
| `D` | Roadmap | Jump to project roadmap |
| `I` | Ideation | Jump to ideation workspace |
| `L` | Changelog | Jump to changelog |
| `C` | Context | Jump to context explorer |
| `M` | Agent Tools | Jump to MCP tools |
| `U` | Plugins | Jump to plugin management |
| `W` | Worktrees | Jump to worktree management |
| `Y` | Merge Analytics | Jump to merge analytics |
| `G` | GitHub Issues | Jump to GitHub issues (if enabled) |
| `P` | GitHub PRs | Jump to GitHub pull requests (if enabled) |
| `B` | GitLab Issues | Jump to GitLab issues (if enabled) |
| `R` | GitLab MRs | Jump to GitLab merge requests (if enabled) |

### Implementing Shortcuts

The keyboard shortcuts are implemented using a global `keydown` event listener:

```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Skip if typing in input
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      // ... other checks
    ) {
      return;
    }

    // Only handle shortcuts when project is selected
    if (!selectedProjectId) return;

    // Skip if modifier keys are pressed
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    const key = e.key.toUpperCase();
    const matchedItem = visibleNavItems.find((item) => item.shortcut === key);

    if (matchedItem) {
      e.preventDefault();
      onViewChange?.(matchedItem.id);
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [selectedProjectId, onViewChange, visibleNavItems]);
```

---

## State Management

### Zustand Stores

The Sidebar component integrates with two Zustand stores:

#### Project Store (`project-store`)

```typescript
import { useProjectStore } from '@/stores/project-store';

// Access project list
const projects = useProjectStore((state) => state.projects);

// Access selected project ID
const selectedProjectId = useProjectStore((state) => state.selectedProjectId);

// Get selected project object
const selectedProject = projects.find((p) => p.id === selectedProjectId);
```

**Used for:**
- Determining if a project is selected (enables/disables navigation)
- Checking if project is initialized (enables/disables New Task button)
- Project switching and management

#### Settings Store (`settings-store`)

```typescript
import { useSettingsStore, saveSettings } from '@/stores/settings-store';

// Access sidebar collapsed state
const settings = useSettingsStore((state) => state.settings);
const isCollapsed = settings.sidebarCollapsed ?? false;

// Toggle sidebar
const toggleSidebar = () => {
  saveSettings({ sidebarCollapsed: !isCollapsed });
};
```

**Used for:**
- Persisting sidebar collapsed state across sessions
- Checking Auto Code installation path for project initialization

### Component State

| State Variable | Type | Purpose |
|----------------|------|---------|
| `showAddProjectModal` | `boolean` | Controls Add Project modal visibility |
| `showInitDialog` | `boolean` | Controls project initialization dialog visibility |
| `showGitSetupModal` | `boolean` | Controls Git setup modal visibility |
| `gitStatus` | `GitStatus \| null` | Current Git repository status |
| `pendingProject` | `Project \| null` | Project awaiting initialization |
| `isInitializing` | `boolean` | Project initialization in progress |
| `envConfig` | `ProjectEnvConfig \| null` | Project environment config (GitHub/GitLab enabled) |

---

## Collapsible Sidebar

### Collapsed State

When collapsed, the sidebar:
- Reduces width from `w-64` (256px) to `w-16` (64px)
- Shows only icons (no text labels)
- Displays tooltips on hover with shortcuts
- Maintains all functionality

### Visual States

```typescript
// Expanded (default)
<div className="w-64">
  <Icon className="h-4 w-4" />
  <span>Kanban</span>
  <kbd>K</kbd>
</div>

// Collapsed
<Tooltip>
  <TooltipTrigger>
    <div className="w-16 justify-center">
      <Icon className="h-4 w-4" />
    </div>
  </TooltipTrigger>
  <TooltipContent>
    Kanban <kbd>K</kbd>
  </TooltipContent>
</Tooltip>
```

### Toggle Control

```typescript
// Toggle button in sidebar header
<Button
  variant="ghost"
  size="icon"
  onClick={toggleSidebar}
  aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
>
  {isCollapsed ? <PanelLeft /> : <PanelLeftClose />}
</Button>
```

---

## Internationalization (i18n)

### Translation Namespaces

The Sidebar component uses three i18n namespaces:

```typescript
const { t } = useTranslation(['navigation', 'dialogs', 'common']);
```

#### `navigation` Namespace

**Sections:**
- `sections.project` - "Project" section header

**Navigation Items:**
- `items.kanban` - "Kanban"
- `items.terminals` - "Terminals"
- `items.insights` - "Insights"
- `items.roadmap` - "Roadmap"
- `items.ideation` - "Ideation"
- `items.changelog` - "Changelog"
- `items.context` - "Context"
- `items.agentTools` - "Agent Tools"
- `items.plugins` - "Plugins"
- `items.worktrees` - "Worktrees"
- `items.mergeAnalytics` - "Merge Analytics"
- `items.githubIssues` - "GitHub Issues"
- `items.githubPRs` - "GitHub PRs"
- `items.gitlabIssues` - "GitLab Issues"
- `items.gitlabMRs` - "GitLab MRs"

**Actions:**
- `actions.settings` - "Settings"
- `actions.newTask` - "New Task"
- `actions.expandSidebar` - "Expand sidebar"
- `actions.collapseSidebar` - "Collapse sidebar"

**Tooltips:**
- `tooltips.settings` - Settings button tooltip
- `tooltips.help` - Help button tooltip

**Messages:**
- `messages.initializeToCreateTasks` - "Initialize Auto Code to create tasks"

#### `dialogs` Namespace

**Initialize Dialog:**
- `initialize.title` - "Initialize Auto Code"
- `initialize.description` - Dialog description
- `initialize.willDo` - "This will:"
- `initialize.createFolder` - "Create `.auto-claude` folder"
- `initialize.copyFramework` - "Copy framework files"
- `initialize.setupSpecs` - "Set up specs directory"
- `initialize.sourcePathNotConfigured` - "Source path not configured"
- `initialize.sourcePathNotConfiguredDescription` - Warning description

#### `common` Namespace

**Buttons:**
- `buttons.skip` - "Skip"
- `buttons.initialize` - "Initialize"

**Labels:**
- `labels.initializing` - "Initializing..."

### Adding New Navigation Items

When adding new navigation items, ensure translation keys are added to all language files:

```json
// apps/frontend/src/shared/i18n/locales/en/navigation.json
{
  "items": {
    "newView": "New View"
  }
}

// apps/frontend/src/shared/i18n/locales/fr/navigation.json
{
  "items": {
    "newView": "Nouvelle Vue"
  }
}
```

---

## Dynamic Navigation

### Integration-Based Items

Navigation items are dynamically shown based on project environment configuration:

```typescript
// Load project environment config
useEffect(() => {
  const loadEnvConfig = async () => {
    if (selectedProject?.autoBuildPath) {
      const result = await window.electronAPI.getProjectEnv(selectedProject.id);
      if (result.success && result.data) {
        setEnvConfig(result.data);
      }
    }
  };
  loadEnvConfig();
}, [selectedProject?.id]);

// Compute visible items based on GitHub/GitLab enabled
const visibleNavItems = useMemo(() => {
  const items = [...baseNavItems];

  if (envConfig?.githubEnabled) {
    items.push(...githubNavItems);
  }

  if (envConfig?.gitlabEnabled) {
    items.push(...gitlabNavItems);
  }

  return items;
}, [envConfig?.githubEnabled, envConfig?.gitlabEnabled]);
```

### Enabling GitHub/GitLab Navigation

To show GitHub or GitLab navigation items, set environment variables in the project's `.auto-claude/.env` file:

```bash
# Enable GitHub items
GITHUB_ENABLED=true
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Enable GitLab items
GITLAB_ENABLED=true
GITLAB_PROJECT_ID=12345
GITLAB_TOKEN=glpat-xxxxxxxxxxxxx
```

---

## Project Initialization

### Initialization Flow

1. **User adds project** → `AddProjectModal` emits project
2. **Check if initialized** → If `autoBuildPath` is missing, show init dialog
3. **User confirms** → Call `initializeProject(projectId)`
4. **Initialize Auto Code:**
   - Create `.auto-claude` folder in project root
   - Copy framework files from Auto Code installation
   - Set up specs directory
   - Save `autoBuildPath` to project config
5. **Complete** → Enable New Task button and full functionality

### Initialization Dialog

```typescript
<Dialog open={showInitDialog}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Initialize Auto Code</DialogTitle>
      <DialogDescription>
        This will set up Auto Code in your project.
      </DialogDescription>
    </DialogHeader>
    <div>
      {/* List of actions */}
      {/* Warning if source path not configured */}
    </div>
    <DialogFooter>
      <Button variant="outline" onClick={handleSkipInit}>
        Skip
      </Button>
      <Button onClick={handleInitialize} disabled={!settings.autoBuildPath}>
        Initialize
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## Git Setup

### Git Status Check

On project selection, the sidebar checks Git repository status:

```typescript
useEffect(() => {
  const checkGit = async () => {
    if (selectedProject) {
      const result = await window.electronAPI.checkGitStatus(selectedProject.path);
      if (result.success && result.data) {
        setGitStatus(result.data);
        // Show Git setup modal if not a repo or no commits
        if (!result.data.isGitRepo || !result.data.hasCommits) {
          setShowGitSetupModal(true);
        }
      }
    }
  };
  checkGit();
}, [selectedProject]);
```

### GitSetupModal Integration

The `GitSetupModal` component handles:
- Initializing Git repository (`git init`)
- Creating initial commit
- Configuring user name/email
- Setting up `.gitignore`

```typescript
<GitSetupModal
  open={showGitSetupModal}
  onOpenChange={setShowGitSetupModal}
  project={selectedProject || null}
  gitStatus={gitStatus}
  onGitInitialized={handleGitInitialized}
/>
```

---

## Status Indicators

### RateLimitIndicator

Shows when Claude API rate limits are active:

```typescript
<RateLimitIndicator />
```

Displays:
- Rate limit countdown timer
- Warning message
- Animated indicator when rate limited

### UpdateBanner

Shows when app update is available:

```typescript
<UpdateBanner />
```

Displays:
- Update available notification
- Download/install button
- Release notes link

### ClaudeCodeStatusBadge

Shows Claude Code connection status:

```typescript
<ClaudeCodeStatusBadge />
```

Displays:
- Connected (green badge)
- Disconnected (red badge with reconnect button)
- Connection error details

---

## Accessibility

### Keyboard Navigation

- **Tab Navigation:** All interactive elements are keyboard accessible
- **ARIA Labels:** Buttons have descriptive `aria-label` attributes
- **Keyboard Shortcuts:** Announced via `aria-keyshortcuts` attribute
- **Focus Management:** Proper focus order and visual focus indicators

### Screen Reader Support

```typescript
<button
  aria-keyshortcuts="K"
  aria-label="Kanban view"
>
  <Icon />
  <span>Kanban</span>
</button>
```

### Tooltip Positioning

Tooltips adapt based on sidebar state:
- **Expanded:** Tooltips show on top
- **Collapsed:** Tooltips show on right side

---

## Styling

### Tailwind Classes

The Sidebar uses Tailwind CSS with the `cn()` utility for conditional classes:

```typescript
import { cn } from '../lib/utils';

<div className={cn(
  "flex h-full flex-col bg-sidebar border-r border-border transition-all duration-300",
  isCollapsed ? "w-16" : "w-64"
)}>
```

### CSS Variables

The component uses CSS custom properties from the theme:

- `--sidebar` - Sidebar background color
- `--border` - Border color
- `--accent` - Accent color for active items
- `--accent-foreground` - Text color for active items
- `--muted-foreground` - Muted text color

### Electron Drag Region

The header includes Electron window drag region:

```typescript
<div className="electron-drag flex h-14 items-center pt-6">
  <span className="electron-no-drag">Auto Code</span>
</div>
```

**Classes:**
- `electron-drag` - Makes region draggable (entire header)
- `electron-no-drag` - Excludes specific elements from drag region (text/buttons)

### macOS Traffic Light Adjustment

Extra top padding (`pt-6`) accounts for macOS window control buttons (traffic lights) in the top-left corner.

---

## Best Practices

### Adding New Navigation Items

1. **Define the nav item:**
```typescript
const newNavItems: NavItem[] = [
  {
    id: 'new-view',
    labelKey: 'navigation:items.newView',
    icon: NewIcon,
    shortcut: 'X'
  }
];
```

2. **Add translations:**
```json
// en/navigation.json
{ "items": { "newView": "New View" } }

// fr/navigation.json
{ "items": { "newView": "Nouvelle Vue" } }
```

3. **Add to SidebarView type:**
```typescript
export type SidebarView =
  | 'kanban'
  | 'new-view'  // Add new view
  | ...;
```

4. **Handle view in parent component:**
```typescript
<Sidebar
  activeView={currentView}
  onViewChange={(view) => {
    if (view === 'new-view') {
      // Handle new view
    }
  }}
/>
```

### Conditional Navigation Items

For integration-based items, add to appropriate array:

```typescript
// For new GitHub-related view
const githubNavItems: NavItem[] = [
  { id: 'github-issues', ... },
  { id: 'new-github-view', ... }  // Add here
];

// For new GitLab-related view
const gitlabNavItems: NavItem[] = [
  { id: 'gitlab-issues', ... },
  { id: 'new-gitlab-view', ... }  // Add here
];
```

### State Management

- **Use Zustand stores** for persistent state (collapsed, settings)
- **Use local state** for temporary UI state (modals, dialogs)
- **Avoid prop drilling** by accessing stores directly in child components

### Performance

- **Memoize visible items:** Use `useMemo` for computed navigation items
- **Debounce API calls:** When checking Git status or env config
- **Lazy load modals:** Modals are loaded but not rendered until `open={true}`

---

## Troubleshooting

### Navigation Items Not Showing

**Problem:** GitHub/GitLab navigation items not appearing

**Solution:**
1. Check project `.auto-claude/.env` file has `GITHUB_ENABLED=true` or `GITLAB_ENABLED=true`
2. Verify project is initialized (has `autoBuildPath`)
3. Check browser console for environment config errors
4. Restart app to reload environment config

### Keyboard Shortcuts Not Working

**Problem:** Shortcuts not triggering navigation

**Solution:**
1. Ensure a project is selected (shortcuts disabled without project)
2. Check if focus is in input field (shortcuts disabled while typing)
3. Verify shortcut key is not conflicting with browser/OS shortcuts
4. Check `visibleNavItems` includes the navigation item

### Sidebar State Not Persisting

**Problem:** Collapsed state resets on app restart

**Solution:**
1. Check settings store is properly saving: `saveSettings({ sidebarCollapsed: true })`
2. Verify settings file is writable: `~/.auto-claude/settings.json`
3. Check for settings store initialization errors in console

### New Task Button Disabled

**Problem:** New Task button is grayed out

**Solution:**
1. Verify project is selected: `selectedProjectId` is not null
2. Check project is initialized: `selectedProject.autoBuildPath` exists
3. Initialize project via init dialog if needed
4. Verify Auto Code source path is configured in Settings

---

## Related Components

- **AddProjectModal:** Modal for adding new projects to workspace
- **GitSetupModal:** Modal for initializing Git repositories
- **RateLimitIndicator:** Shows Claude API rate limit status
- **UpdateBanner:** Shows app update availability
- **ClaudeCodeStatusBadge:** Shows Claude Code connection status
- **Settings:** Settings panel for Auto Code configuration
- **KanbanBoard:** Main task board view (navigated via Sidebar)
- **TerminalPanel:** Terminal sessions view (navigated via Sidebar)

---

## See Also

- [KanbanBoard Component](./KanbanBoard.md) - Task board component
- [Project Store](../architecture/stores.md#project-store) - Project management state
- [Settings Store](../architecture/stores.md#settings-store) - Application settings state
- [Internationalization](../guides/i18n.md) - i18n implementation guide
- [Keyboard Shortcuts](../guides/keyboard-shortcuts.md) - Complete keyboard shortcuts reference
