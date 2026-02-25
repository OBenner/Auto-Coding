# UI Plugin Development Guide

UI plugins extend Auto Claude's Electron frontend with custom React components, dashboard widgets, and backend communication via IPC handlers. This guide covers everything you need to build beautiful, functional UI extensions.

## Table of Contents

- [Overview](#overview)
- [UIPlugin API Reference](#uiplugin-api-reference)
- [Extension Points](#extension-points)
- [React Component Development](#react-component-development)
- [IPC Communication](#ipc-communication)
- [Backend Integration](#backend-integration)
- [State Management](#state-management)
- [Styling with Tailwind CSS](#styling-with-tailwind-css)
- [Asset Management](#asset-management)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Best Practices](#best-practices)
- [Complete Example](#complete-example)

## Overview

UI plugins are Python classes (backend) with associated React/TypeScript components (frontend) that extend the Electron desktop app. They enable:

- **Dashboard Widgets** - Display custom data and metrics on the main dashboard
- **Sidebar Items** - Add navigation items to the sidebar
- **Settings Panels** - Create custom settings pages
- **Toolbar Buttons** - Add buttons to the main toolbar
- **Context Menus** - Extend right-click menus
- **Status Bar Items** - Display information in the status bar
- **IPC Handlers** - Backend-frontend bidirectional communication
- **Frontend Assets** - Serve static assets (images, icons, styles)

### When to Use UI Plugins

Use UI plugins when you want to:
- Display custom data or metrics in the dashboard
- Add new navigation items or pages
- Create custom settings interfaces
- Visualize build progress or statistics
- Add interactive controls or widgets
- Integrate with external service UIs
- Provide custom data views or reports

### Quick Start

```bash
# Copy the example plugin
cp -r examples/plugins/ui-extension my-ui-plugin

# Update plugin.json and plugin.py
# Edit ui-component.tsx for your UI
# Install and test
```

## UIPlugin API Reference

### Base Class

```python
from apps.backend.plugins.sdk.ui import UIPlugin, UIContext, UIComponentDefinition, UIExtensionPoint

class MyUIPlugin(UIPlugin):
    """Your custom UI plugin."""

    def __init__(self, metadata):
        super().__init__(metadata)
        self._stats_cache = None
```

### Required Methods

All UI plugins must implement:

| Method | Purpose | Required |
|--------|---------|----------|
| `get_ui_components()` | Register UI components | Yes |
| `register_ipc_handlers(context)` | Provide IPC handlers | Yes (if components need data) |

### Optional UI Methods

Additional methods you can implement:

| Method | Purpose | When Called |
|--------|---------|-------------|
| `get_frontend_assets()` | Provide static assets | When loading plugin |
| `on_frontend_ready()` | Frontend loaded | After frontend initializes |
| `on_window_focus()` | Window gains focus | When window focused |

### Lifecycle Hooks (from PluginBase)

| Method | Purpose | Required |
|--------|---------|----------|
| `on_load()` | Plugin initialization | Yes |
| `on_enable()` | Called when user enables plugin | Yes |
| `on_disable()` | Called when user disables plugin | Yes |
| `on_unload()` | Cleanup before unload | Yes |

## Extension Points

UI components can be added to different locations in the UI via extension points.

### Available Extension Points

| Extension Point | Description | Use Case |
|----------------|-------------|----------|
| `DASHBOARD` | Main dashboard area | Widgets, metrics, quick stats |
| `SIDEBAR` | Left sidebar navigation | New pages, tools, sections |
| `SETTINGS` | Settings page panels | Configuration interfaces |
| `TOOLBAR` | Top toolbar | Quick actions, toggles |
| `CONTEXT_MENU` | Right-click menus | Contextual actions |
| `STATUS_BAR` | Bottom status bar | Status indicators, counters |

### Extension Point Examples

**Dashboard Widget:**

```python
from apps.backend.plugins.sdk.ui import UIComponentDefinition, UIExtensionPoint

def get_ui_components(self) -> list[UIComponentDefinition]:
    return [
        UIComponentDefinition(
            id="my-dashboard-widget",
            extension_point=UIExtensionPoint.DASHBOARD,
            title="My Widget",
            icon="activity",  # Lucide icon name
            component_path="ui-component.tsx",
            order=100,  # Display order
            props={
                "refreshInterval": 30000,
                "showCharts": True,
            }
        )
    ]
```

**Sidebar Navigation Item:**

```python
def get_ui_components(self) -> list[UIComponentDefinition]:
    return [
        UIComponentDefinition(
            id="my-tool",
            extension_point=UIExtensionPoint.SIDEBAR,
            title="My Tool",
            icon="puzzle",
            route="/my-tool",  # Frontend route
            order=50,
        )
    ]
```

**Settings Panel:**

```python
def get_ui_components(self) -> list[UIComponentDefinition]:
    return [
        UIComponentDefinition(
            id="my-settings",
            extension_point=UIExtensionPoint.SETTINGS,
            title="My Plugin Settings",
            icon="settings",
            component_path="settings-component.tsx",
            order=200,
        )
    ]
```

## React Component Development

### Component Structure

UI components are React/TypeScript files that receive props and communicate with the backend via IPC.

**Basic Component Template:**

```typescript
import React, { useState, useEffect } from 'react';

interface MyWidgetProps {
  refreshInterval?: number;
  showCharts?: boolean;
}

interface MyData {
  value: number;
  label: string;
}

export const MyWidget: React.FC<MyWidgetProps> = ({
  refreshInterval = 30000,
  showCharts = true
}) => {
  const [data, setData] = useState<MyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await window.electronAPI.invoke('my-plugin:get-data');

      if (result.success) {
        setData(result.data);
        setError(null);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Auto-refresh
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loading) {
    return <div className="animate-pulse">Loading...</div>;
  }

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">{data?.label}</h2>
      <p className="text-3xl font-semibold">{data?.value}</p>
    </div>
  );
};

export default MyWidget;
```

### TypeScript Interfaces

Define clear interfaces for your data:

```typescript
// Props interface
interface ProjectStatsProps {
  refreshInterval?: number;
  showCharts?: boolean;
  projectDir?: string;
}

// Data interface
interface ProjectStats {
  totalSpecs: number;
  completedSpecs: number;
  inProgressSpecs: number;
  failedSpecs: number;
  successRate: number;
}

// IPC Response interface
interface IPCResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
```

### React Hooks

Use React hooks for state and lifecycle management:

**useState for State:**

```typescript
const [stats, setStats] = useState<ProjectStats | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
```

**useEffect for Side Effects:**

```typescript
useEffect(() => {
  // Initial fetch
  fetchStats();

  // Auto-refresh interval
  const interval = setInterval(fetchStats, refreshInterval);

  // Cleanup
  return () => clearInterval(interval);
}, [refreshInterval, projectDir]);
```

**useMemo for Computed Values:**

```typescript
import { useMemo } from 'react';

const successRate = useMemo(() => {
  if (!stats || stats.totalSpecs === 0) return 0;
  return (stats.completedSpecs / stats.totalSpecs) * 100;
}, [stats]);
```

**useCallback for Event Handlers:**

```typescript
import { useCallback } from 'react';

const handleRefresh = useCallback(async () => {
  setLoading(true);
  await fetchStats();
}, []);
```

### Loading States

Implement skeleton loaders for better UX:

```typescript
const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-4">
    <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
    <div className="grid grid-cols-4 gap-4">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
      ))}
    </div>
  </div>
);

// In component
if (loading) {
  return <LoadingSkeleton />;
}
```

### Error States

Provide clear error messages with retry functionality:

```typescript
const ErrorDisplay = ({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
    <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
      <AlertCircle className="h-5 w-5" />
      <p className="font-semibold">Error loading data</p>
    </div>
    <p className="text-sm text-red-500 dark:text-red-300 mt-2">{error}</p>
    <button
      onClick={onRetry}
      className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
    >
      Retry
    </button>
  </div>
);

// In component
if (error) {
  return <ErrorDisplay error={error} onRetry={fetchStats} />;
}
```

## IPC Communication

IPC (Inter-Process Communication) allows frontend components to communicate with the backend Python plugin.

### Backend: Registering IPC Handlers

**In plugin.py:**

```python
from typing import Any, Callable
from pathlib import Path

def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
    """Register IPC handlers for frontend-backend communication."""

    def get_project_stats(event, project_dir: str) -> dict[str, Any]:
        """
        Get project statistics.

        Args:
            event: IPC event (provided by Electron)
            project_dir: Path to project directory

        Returns:
            dict: Response with success flag and data/error
        """
        try:
            stats = self._calculate_stats(Path(project_dir))
            return {"success": True, "data": stats}
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def refresh_stats(event, project_dir: str) -> dict[str, Any]:
        """Refresh stats by clearing cache."""
        try:
            self._stats_cache = None  # Clear cache
            stats = self._calculate_stats(Path(project_dir))
            return {"success": True, "data": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Return dict of channel name → handler function
    return {
        f"{self.metadata.name}:get-stats": get_project_stats,
        f"{self.metadata.name}:refresh-stats": refresh_stats,
    }
```

### Frontend: Calling IPC Handlers

**In ui-component.tsx:**

```typescript
const fetchStats = async () => {
  try {
    setLoading(true);

    // Call backend IPC handler
    const result = await window.electronAPI.invoke(
      'my-plugin:get-stats',
      projectDir
    );

    if (result.success) {
      setStats(result.data);
      setError(null);
    } else {
      setError(result.error);
    }
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unknown error');
  } finally {
    setLoading(false);
  }
};

const handleRefresh = async () => {
  const result = await window.electronAPI.invoke(
    'my-plugin:refresh-stats',
    projectDir
  );

  if (result.success) {
    setStats(result.data);
  }
};
```

### IPC Channel Naming Convention

Use the plugin name as a prefix:

```
{plugin-name}:{action}

Examples:
- ui-extension:get-stats
- my-plugin:save-config
- dashboard-widget:fetch-data
```

### IPC Response Format

Always return consistent response format:

```python
# Success response
return {
    "success": True,
    "data": {
        "value": 42,
        "label": "Answer"
    }
}

# Error response
return {
    "success": False,
    "error": "Failed to calculate stats: Division by zero"
}
```

### Type-safe IPC Calls

Define TypeScript types for IPC responses:

```typescript
interface IPCResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

interface ProjectStats {
  totalSpecs: number;
  completedSpecs: number;
  successRate: number;
}

// Type-safe IPC call
const fetchStats = async (): Promise<ProjectStats> => {
  const response: IPCResponse<ProjectStats> = await window.electronAPI.invoke(
    'my-plugin:get-stats',
    projectDir
  );

  if (!response.success) {
    throw new Error(response.error || 'Unknown error');
  }

  return response.data!;
};
```

## Backend Integration

### Data Calculation and Processing

Implement backend logic in your plugin class:

```python
from pathlib import Path
import json

class MyUIPlugin(UIPlugin):
    def _calculate_stats(self, project_dir: Path) -> dict:
        """Calculate project statistics."""
        # Use cache if available
        if self._stats_cache:
            return self._stats_cache

        specs_dir = project_dir / ".auto-claude" / "specs"
        if not specs_dir.exists():
            return {
                "totalSpecs": 0,
                "completedSpecs": 0,
                "inProgressSpecs": 0,
                "failedSpecs": 0,
                "successRate": 0
            }

        total = 0
        completed = 0
        in_progress = 0
        failed = 0

        # Count specs by status
        for spec_path in specs_dir.iterdir():
            if not spec_path.is_dir():
                continue

            total += 1
            plan_file = spec_path / "implementation_plan.json"

            if not plan_file.exists():
                continue

            try:
                with open(plan_file) as f:
                    plan = json.load(f)
                    status = plan.get("status", "pending")

                    if status == "completed":
                        completed += 1
                    elif status == "in_progress":
                        in_progress += 1
                    elif status == "failed":
                        failed += 1
            except Exception as e:
                self.logger.error(f"Error reading {plan_file}: {e}")

        # Calculate success rate
        success_rate = (completed / total * 100) if total > 0 else 0

        stats = {
            "totalSpecs": total,
            "completedSpecs": completed,
            "inProgressSpecs": in_progress,
            "failedSpecs": failed,
            "successRate": round(success_rate, 1)
        }

        # Cache results
        self._stats_cache = stats

        return stats
```

### Reading Implementation Plans

Helper methods for accessing Auto Claude data:

```python
def load_implementation_plan(self, spec_dir: Path) -> dict:
    """Load implementation plan from spec directory."""
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        raise FileNotFoundError(f"Plan not found: {plan_file}")

    with open(plan_file) as f:
        return json.load(f)

def get_all_subtasks(self, plan: dict) -> list[dict]:
    """Extract all subtasks from implementation plan."""
    subtasks = []
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            subtasks.append(subtask)
    return subtasks

def count_subtasks_by_status(self, plan: dict) -> dict[str, int]:
    """Count subtasks grouped by status."""
    counts = {
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0
    }

    for subtask in self.get_all_subtasks(plan):
        status = subtask.get("status", "pending")
        if status in counts:
            counts[status] += 1

    return counts
```

## State Management

### Plugin State Persistence

Use state persistence for caching and configuration:

```python
def on_frontend_ready(self) -> None:
    """Pre-calculate stats when frontend is ready."""
    # Load saved state
    state_file = Path(self.metadata.plugin_dir) / "state.json"
    if state_file.exists():
        with open(state_file) as f:
            self.state = json.load(f)
    else:
        self.state = {}

    # Pre-calculate stats for fast initial load
    project_dir = self.state.get("last_project_dir")
    if project_dir:
        self._stats_cache = self._calculate_stats(Path(project_dir))

def on_window_focus(self) -> None:
    """Clear cache when window regains focus."""
    # Invalidate cache to get fresh data
    self._stats_cache = None

def _save_state(self):
    """Save plugin state to disk."""
    state_file = Path(self.metadata.plugin_dir) / "state.json"
    with open(state_file, 'w') as f:
        json.dump(self.state, f, indent=2)
```

### Frontend State Management

Use React state hooks effectively:

```typescript
// Local component state
const [stats, setStats] = useState<ProjectStats | null>(null);

// Derived state
const successRate = useMemo(() => {
  if (!stats || stats.totalSpecs === 0) return 0;
  return (stats.completedSpecs / stats.totalSpecs) * 100;
}, [stats]);

// Shared state (via Context)
import { createContext, useContext } from 'react';

const PluginContext = createContext<PluginState | null>(null);

export const usePluginState = () => {
  const context = useContext(PluginContext);
  if (!context) {
    throw new Error('usePluginState must be used within PluginProvider');
  }
  return context;
};
```

## Styling with Tailwind CSS

Auto Claude uses Tailwind CSS for styling. Use Tailwind utility classes for consistent, responsive design.

### Basic Styling

```tsx
<div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
  <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
    Project Statistics
  </h2>
  <p className="text-gray-600 dark:text-gray-400">
    Your project metrics at a glance
  </p>
</div>
```

### Responsive Design

```tsx
{/* Mobile: 1 column, Tablet: 2 columns, Desktop: 4 columns */}
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
  <StatCard label="Total" value={stats.totalSpecs} />
  <StatCard label="Completed" value={stats.completedSpecs} />
  <StatCard label="In Progress" value={stats.inProgressSpecs} />
  <StatCard label="Failed" value={stats.failedSpecs} />
</div>
```

### Dark Mode Support

Always support both light and dark modes:

```tsx
<div className="bg-gray-100 dark:bg-gray-900">
  <p className="text-gray-800 dark:text-gray-200">Content</p>
  <button className="bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700">
    Action
  </button>
</div>
```

### Common UI Patterns

**Card Component:**

```tsx
const Card = ({ children, className = "" }) => (
  <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
    {children}
  </div>
);
```

**Stat Display:**

```tsx
const StatCard = ({ icon: Icon, label, value, color = "text-blue-500" }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
    <div className="flex items-center gap-3">
      <Icon className={`h-8 w-8 ${color}`} />
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  </div>
);
```

**Progress Bar:**

```tsx
const ProgressBar = ({ value, max, color = "bg-blue-500" }) => (
  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
    <div
      className={`${color} h-2 rounded-full transition-all duration-300`}
      style={{ width: `${(value / max) * 100}%` }}
    />
  </div>
);
```

### Icons

Use Lucide React icons:

```tsx
import { Activity, CheckCircle, Clock, XCircle, RefreshCw } from 'lucide-react';

<div className="flex items-center gap-2">
  <Activity className="h-5 w-5 text-blue-500" />
  <span>Active Builds</span>
</div>

<button onClick={handleRefresh} className="p-2 hover:bg-gray-100 rounded">
  <RefreshCw className="h-4 w-4" />
</button>
```

### Animation

Use Tailwind animations:

```tsx
{/* Pulse animation for loading */}
<div className="animate-pulse">
  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
</div>

{/* Spin animation for refresh */}
<RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />

{/* Fade in */}
<div className="animate-fade-in">Content</div>

{/* Slide in */}
<div className="transition-all duration-300 translate-x-0 opacity-100">
  Content
</div>
```

## Asset Management

### Serving Static Assets

Provide static assets (images, icons, CSS) via `get_frontend_assets()`:

```python
from pathlib import Path

def get_frontend_assets(self) -> dict[str, Path]:
    """Return static assets to serve to frontend."""
    plugin_dir = Path(self.metadata.plugin_dir)

    return {
        "logo.png": plugin_dir / "assets" / "logo.png",
        "icon.svg": plugin_dir / "assets" / "icon.svg",
        "custom.css": plugin_dir / "assets" / "custom.css",
    }
```

### Accessing Assets in Frontend

Assets are served at `/plugins/{plugin-name}/assets/{asset-name}`:

```tsx
<img
  src="/plugins/my-plugin/assets/logo.png"
  alt="Plugin Logo"
  className="h-8 w-8"
/>
```

### Asset Directory Structure

```
my-plugin/
├── plugin.json
├── plugin.py
├── ui-component.tsx
└── assets/
    ├── logo.png
    ├── icon.svg
    └── custom.css
```

## Lifecycle Hooks

### on_frontend_ready()

Called when the frontend has loaded and is ready:

```python
def on_frontend_ready(self) -> None:
    """Pre-calculate data when frontend is ready."""
    try:
        # Pre-calculate stats for fast initial load
        self.logger.info("Frontend ready, pre-calculating stats...")

        # Load last used project directory
        project_dir = self.get_config_value("LAST_PROJECT_DIR")
        if project_dir:
            self._stats_cache = self._calculate_stats(Path(project_dir))
            self.logger.info(f"Pre-calculated stats for {project_dir}")
    except Exception as e:
        self.logger.error(f"Failed to pre-calculate stats: {e}", exc_info=True)
```

### on_window_focus()

Called when the Electron window regains focus:

```python
def on_window_focus(self) -> None:
    """Invalidate cache when window regains focus."""
    # Clear cache to force fresh data on next request
    self._stats_cache = None
    self.logger.debug("Window focused, cache invalidated")
```

## Best Practices

### 1. Performance Optimization

**Cache expensive calculations:**

```python
def _calculate_stats(self, project_dir: Path) -> dict:
    """Calculate stats with caching."""
    # Check cache first
    if self._stats_cache:
        cache_age = time.time() - self._cache_timestamp
        if cache_age < 60:  # Cache for 60 seconds
            return self._stats_cache

    # Calculate stats
    stats = self._do_expensive_calculation(project_dir)

    # Update cache
    self._stats_cache = stats
    self._cache_timestamp = time.time()

    return stats
```

**Debounce frequent updates:**

```typescript
import { useEffect, useState } from 'react';

const useDebounce = (value: string, delay: number) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};

// Usage
const searchTerm = useDebounce(inputValue, 500);
```

### 2. Error Handling

**Backend graceful degradation:**

```python
def register_ipc_handlers(self, context):
    def get_stats(event, project_dir):
        try:
            stats = self._calculate_stats(Path(project_dir))
            return {"success": True, "data": stats}
        except FileNotFoundError:
            # Return empty stats instead of error
            return {"success": True, "data": self._empty_stats()}
        except Exception as e:
            self.logger.error(f"Stats calculation failed: {e}", exc_info=True)
            return {"success": False, "error": "Failed to calculate stats"}

    return {f"{self.metadata.name}:get-stats": get_stats}
```

**Frontend error boundaries:**

```typescript
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Plugin error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded">
          <p className="text-red-600 dark:text-red-400">
            Plugin error: {this.state.error?.message}
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### 3. Accessibility

**Use semantic HTML:**

```tsx
<button
  onClick={handleRefresh}
  aria-label="Refresh statistics"
  className="p-2 rounded hover:bg-gray-100"
>
  <RefreshCw className="h-4 w-4" />
</button>

<div role="status" aria-live="polite">
  {loading ? 'Loading...' : `${stats.totalSpecs} specs`}
</div>
```

**Keyboard navigation:**

```tsx
<button
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleAction();
    }
  }}
>
  Action
</button>
```

### 4. Testing

**Backend unit tests:**

```python
# tests/test_my_ui_plugin.py
import pytest
from pathlib import Path
from my_plugin import MyUIPlugin

def test_calculate_stats(tmp_path):
    # Setup
    plugin = MyUIPlugin(metadata)
    specs_dir = tmp_path / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)

    # Test
    stats = plugin._calculate_stats(tmp_path)

    # Assert
    assert stats["totalSpecs"] == 0
    assert stats["successRate"] == 0
```

**Frontend component tests:**

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { MyWidget } from './ui-component';

test('displays loading state initially', () => {
  render(<MyWidget />);
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
});

test('displays stats after loading', async () => {
  render(<MyWidget />);
  await waitFor(() => {
    expect(screen.getByText(/total specs/i)).toBeInTheDocument();
  });
});
```

### 5. Documentation

Document your component props:

```typescript
/**
 * Project statistics dashboard widget.
 *
 * @param refreshInterval - Auto-refresh interval in milliseconds (default: 30000)
 * @param showCharts - Whether to display charts (default: true)
 * @param projectDir - Project directory path (optional, uses current project)
 */
interface ProjectStatsWidgetProps {
  refreshInterval?: number;
  showCharts?: boolean;
  projectDir?: string;
}
```

## Complete Example

Here's a complete UI plugin that displays project statistics:

**plugin.py:**

```python
"""UI extension plugin that displays project statistics."""
from pathlib import Path
from typing import Any, Callable
import json

from apps.backend.plugins.sdk.ui import (
    UIPlugin,
    UIContext,
    UIComponentDefinition,
    UIExtensionPoint
)


class ProjectStatsPlugin(UIPlugin):
    """
    UI plugin that displays project statistics on the dashboard.

    Shows metrics like total specs, completion rate, and success rate.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._stats_cache = None

    def on_load(self) -> None:
        """Initialize plugin when loaded."""
        self.logger.info("Project Stats Plugin loaded")

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self.logger.info("Project Stats Plugin enabled")

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self._stats_cache = None
        self.logger.info("Project Stats Plugin disabled")

    def on_unload(self) -> None:
        """Cleanup when plugin is unloaded."""
        self.logger.info("Project Stats Plugin unloaded")

    def get_ui_components(self) -> list[UIComponentDefinition]:
        """Register the project stats dashboard widget."""
        return [
            UIComponentDefinition(
                id="project-stats-widget",
                extension_point=UIExtensionPoint.DASHBOARD,
                title="Project Statistics",
                icon="activity",
                component_path="ui-component.tsx",
                order=100,
                props={
                    "refreshInterval": 30000,  # 30 seconds
                    "showCharts": True,
                }
            )
        ]

    def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
        """Register IPC handlers for stats retrieval."""

        def get_project_stats(event, project_dir: str) -> dict[str, Any]:
            """Get project statistics."""
            try:
                stats = self._calculate_stats(Path(project_dir))
                return {"success": True, "data": stats}
            except Exception as e:
                self.logger.error(f"Failed to get stats: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        def refresh_stats(event, project_dir: str) -> dict[str, Any]:
            """Refresh stats by clearing cache."""
            try:
                self._stats_cache = None
                stats = self._calculate_stats(Path(project_dir))
                return {"success": True, "data": stats}
            except Exception as e:
                self.logger.error(f"Failed to refresh stats: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        return {
            f"{self.metadata.name}:get-stats": get_project_stats,
            f"{self.metadata.name}:refresh-stats": refresh_stats,
        }

    def on_frontend_ready(self) -> None:
        """Pre-calculate stats when frontend is ready."""
        self.logger.info("Frontend ready")

    def on_window_focus(self) -> None:
        """Clear cache when window regains focus."""
        self._stats_cache = None

    def _calculate_stats(self, project_dir: Path) -> dict[str, Any]:
        """Calculate project statistics."""
        # Return cached stats if available
        if self._stats_cache:
            return self._stats_cache

        specs_dir = project_dir / ".auto-claude" / "specs"

        if not specs_dir.exists():
            return {
                "totalSpecs": 0,
                "completedSpecs": 0,
                "inProgressSpecs": 0,
                "failedSpecs": 0,
                "successRate": 0
            }

        total = 0
        completed = 0
        in_progress = 0
        failed = 0

        # Count specs by status
        for spec_path in specs_dir.iterdir():
            if not spec_path.is_dir():
                continue

            total += 1
            plan_file = spec_path / "implementation_plan.json"

            if not plan_file.exists():
                continue

            try:
                with open(plan_file) as f:
                    plan = json.load(f)
                    status = plan.get("status", "pending")

                    if status == "completed":
                        completed += 1
                    elif status == "in_progress":
                        in_progress += 1
                    elif status in ["failed", "rejected"]:
                        failed += 1
            except Exception as e:
                self.logger.error(f"Error reading {plan_file}: {e}")

        # Calculate success rate
        success_rate = (completed / total * 100) if total > 0 else 0

        stats = {
            "totalSpecs": total,
            "completedSpecs": completed,
            "inProgressSpecs": in_progress,
            "failedSpecs": failed,
            "successRate": round(success_rate, 1)
        }

        # Cache results
        self._stats_cache = stats

        return stats
```

**ui-component.tsx:**

```typescript
import React, { useState, useEffect, useCallback } from 'react';
import { Activity, CheckCircle, Clock, XCircle, RefreshCw } from 'lucide-react';

interface ProjectStatsWidgetProps {
  refreshInterval?: number;
  showCharts?: boolean;
}

interface ProjectStats {
  totalSpecs: number;
  completedSpecs: number;
  inProgressSpecs: number;
  failedSpecs: number;
  successRate: number;
}

const ProjectStatsWidget: React.FC<ProjectStatsWidgetProps> = ({
  refreshInterval = 30000,
  showCharts = true
}) => {
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStats = useCallback(async (showLoader = false) => {
    try {
      if (showLoader) {
        setLoading(true);
      }

      const projectDir = await window.electronAPI.invoke('get-current-project-dir');
      const result = await window.electronAPI.invoke(
        'ui-extension:get-stats',
        projectDir
      );

      if (result.success) {
        setStats(result.data);
        setError(null);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    const projectDir = await window.electronAPI.invoke('get-current-project-dir');
    const result = await window.electronAPI.invoke(
      'ui-extension:refresh-stats',
      projectDir
    );

    if (result.success) {
      setStats(result.data);
    }
    setRefreshing(false);
  }, []);

  useEffect(() => {
    fetchStats(true);

    const interval = setInterval(() => fetchStats(false), refreshInterval);
    return () => clearInterval(interval);
  }, [fetchStats, refreshInterval]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="text-red-500 dark:text-red-400">
          <p className="font-semibold">Error loading statistics</p>
          <p className="text-sm mt-2">{error}</p>
          <button
            onClick={() => fetchStats(true)}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Activity className="h-6 w-6 text-blue-500" />
          Project Statistics
        </h2>
        <button
          onClick={handleRefresh}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          aria-label="Refresh statistics"
        >
          <RefreshCw className={`h-4 w-4 text-gray-600 dark:text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={Activity}
          label="Total Specs"
          value={stats?.totalSpecs || 0}
          color="text-blue-500"
        />
        <StatCard
          icon={CheckCircle}
          label="Completed"
          value={stats?.completedSpecs || 0}
          color="text-green-500"
        />
        <StatCard
          icon={Clock}
          label="In Progress"
          value={stats?.inProgressSpecs || 0}
          color="text-yellow-500"
        />
        <StatCard
          icon={XCircle}
          label="Failed"
          value={stats?.failedSpecs || 0}
          color="text-red-500"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">Success Rate</span>
          <span className="text-lg font-bold text-gray-900 dark:text-white">
            {stats?.successRate || 0}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
          <div
            className="bg-green-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${stats?.successRate || 0}%` }}
          />
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ icon: Icon, label, value, color }) => (
  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
    <div className="flex items-center gap-3">
      <Icon className={`h-8 w-8 ${color}`} />
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  </div>
);

export default ProjectStatsWidget;
```

## Learn More

- [Plugin Getting Started Guide](getting-started.md) - Basic plugin concepts
- [Agent Plugin Guide](agent-plugins.md) - Building agent plugins
- [Integration Plugin Guide](integration-plugins.md) - Building integration plugins
- [UI Extension Example](../../examples/plugins/ui-extension/README.md) - Working example
- [Frontend Architecture](../../apps/frontend/README.md) - Electron frontend overview

## Troubleshooting

### Component Not Appearing

**Problem:** UI component doesn't show in dashboard/sidebar

**Solutions:**
- Verify plugin is **enabled**, not just installed
- Check extension point matches location (e.g., DASHBOARD for widgets)
- Ensure `get_ui_components()` returns non-empty list
- Look for errors in backend logs during component registration
- Refresh the Electron app (Cmd/Ctrl+R)

### IPC Calls Failing

**Problem:** Frontend can't communicate with backend

**Solutions:**
- Verify IPC channel names match exactly
- Check backend handler is registered in `register_ipc_handlers()`
- Ensure plugin has required permissions (e.g., `read_files`)
- Test backend handler directly in Python REPL
- Check browser console for frontend errors

### Styling Issues

**Problem:** Component looks broken or unstyled

**Solutions:**
- Ensure Tailwind classes are correct
- Support both light and dark modes
- Test responsive breakpoints (sm, md, lg)
- Check for conflicting CSS classes
- Verify component renders correctly in isolation

### Performance Problems

**Problem:** Widget is slow or freezes UI

**Solutions:**
- Cache expensive calculations in backend
- Debounce frequent updates in frontend
- Use `useMemo` for computed values
- Avoid unnecessary re-renders with `React.memo`
- Profile with React DevTools

## Contributing

We welcome contributions to improve this guide or add more UI plugin examples!

- [GitHub Issues](https://github.com/AndyMik90/Auto-Claude/issues)
- [GitHub Discussions](https://github.com/AndyMik90/Auto-Claude/discussions)

Happy building! 🎨
