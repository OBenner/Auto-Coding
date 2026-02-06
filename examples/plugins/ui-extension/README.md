# UI Extension Example Plugin

A comprehensive example UI plugin that demonstrates how to create custom dashboard widgets with React components and IPC communication in Auto Code.

## Overview

This plugin adds a **Project Statistics** widget to the Auto Code dashboard that displays real-time metrics about your specs, including completion rates, in-progress builds, and success rates. It's a complete implementation demonstrating all key aspects of UI plugin development.

## What It Does

- **Dashboard Widget**: Adds a beautiful, informative widget to the main dashboard
- **Real-time Stats**: Shows spec counts (total, completed, pending, in-progress, failed)
- **Success Rate**: Calculates and displays project success percentage with visual progress bar
- **Auto-refresh**: Automatically updates statistics every 30 seconds
- **Manual Refresh**: Click-to-refresh button for instant updates
- **Backend Communication**: Demonstrates IPC handlers for frontend-backend data flow
- **State Caching**: Implements performance optimizations with data caching
- **Error Handling**: Graceful error states with retry functionality

## Features Demonstrated

### UI Plugin Interface

This plugin demonstrates the complete `UIPlugin` API:

- `get_ui_components()` - Registers dashboard widget component
- `register_ipc_handlers()` - Provides IPC handlers for data fetching
- `on_frontend_ready()` - Pre-calculates stats for fast initial load
- `on_window_focus()` - Refreshes data when window regains focus

### React Component Integration

The `ui-component.tsx` file shows best practices for React components:

- **Modern React Hooks** - `useState`, `useEffect` for state and lifecycle
- **TypeScript** - Fully typed props and state interfaces
- **IPC Communication** - Calling backend handlers via `window.electronAPI`
- **Auto-refresh** - Interval-based data updates
- **Loading States** - Skeleton loaders and spinners
- **Error Handling** - Error boundaries and retry logic
- **Tailwind CSS** - Modern, responsive styling
- **Icons** - Lucide React icons for visual polish

### IPC Communication Pattern

The plugin demonstrates bidirectional communication:

**Backend (plugin.py):**
```python
def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
    def get_project_stats(event, project_dir: str):
        # Calculate and return stats
        stats = self._calculate_stats(Path(project_dir))
        return {"success": True, "data": stats}

    return {
        "ui-extension:get-stats": get_project_stats,
        "ui-extension:refresh-stats": refresh_stats,
    }
```

**Frontend (ui-component.tsx):**
```typescript
const result = await window.electronAPI.invoke('ui-extension:get-stats', projectDir);
if (result.success) {
    setStats(result.data);
}
```

## Installation

### From Directory

1. **Using the Electron UI** (Recommended):
   - Open Auto Code desktop app
   - Navigate to **Plugins** (keyboard shortcut: `U`)
   - Click **Install Plugin**
   - Select **Directory** as installation source
   - Browse to `examples/plugins/ui-extension`
   - Click **Install**

2. **Manual Installation**:
   ```bash
   cp -r examples/plugins/ui-extension ~/.auto-claude/plugins/user/
   ```

3. **Verify Installation**:
   ```bash
   python -c "from apps.backend.plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('examples/plugins/ui-extension'); print('OK')"
   ```

## Usage

Once installed and enabled:

1. **Navigate to Dashboard**: The widget appears automatically on the main dashboard
2. **View Statistics**: See your project metrics at a glance
3. **Auto-updates**: Stats refresh every 30 seconds automatically
4. **Manual Refresh**: Click the refresh icon in the top-right corner to update immediately

### Statistics Displayed

- **Total Specs**: Count of all specs in `.auto-claude/specs/`
- **Completed**: Specs with `status: "completed"`
- **In Progress**: Specs currently being built
- **Failed**: Specs that failed during build
- **Success Rate**: Percentage of completed specs

## Configuration

### Default Props

The widget accepts these configuration props (defined in `get_ui_components()`):

```python
props={
    "refreshInterval": 30000,  # Auto-refresh interval (ms)
    "showCharts": True,        # Show visual charts (future)
}
```

### Permissions

This plugin requires:
- **`read_files`** - To read spec directories and implementation plans

No write or network permissions needed.

## Development

### File Structure

```
ui-extension/
├── plugin.json       # Plugin metadata and manifest
├── plugin.py         # Backend implementation (Python)
├── ui-component.tsx  # Frontend component (React/TypeScript)
└── README.md         # This documentation
```

### Extending This Plugin

#### Adding More Statistics

To add new metrics to the stats calculation:

```python
def _calculate_stats(self, project_dir: Path) -> dict[str, Any]:
    stats = {
        # ... existing stats ...
        "customMetric": 0,  # Add your metric
    }

    # Calculate your metric
    for spec_path in specs_dir.iterdir():
        # ... your calculation logic ...
        stats["customMetric"] += 1

    return stats
```

Then update the frontend interface and display:

```typescript
interface ProjectStats {
  // ... existing fields ...
  customMetric: number;
}

// In component JSX:
<StatCard
  icon={<YourIcon />}
  label="Custom Metric"
  value={stats.customMetric}
  color="text-purple-500"
/>
```

#### Adding New IPC Handlers

To add more backend functionality:

```python
def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
    def custom_handler(event, param: str):
        # Your logic here
        return {"success": True, "data": result}

    return {
        # ... existing handlers ...
        f"{self.name}:custom-action": custom_handler,
    }
```

Call from frontend:

```typescript
const result = await window.electronAPI.invoke('ui-extension:custom-action', param);
```

#### Customizing the UI Component

The React component uses Tailwind CSS classes. Customize the appearance:

```tsx
// Change color scheme
<div className="bg-purple-500">  // Instead of bg-primary

// Adjust layout
<div className="grid grid-cols-3 gap-6">  // Instead of grid-cols-4

// Add animations
<div className="transition-all duration-300 hover:scale-105">
```

### Building for Production

For real-world plugins, you may want to:

1. **Bundle TypeScript/React**: Use Vite or Webpack to compile TypeScript
2. **Add Tests**: Write unit tests for both Python and TypeScript code
3. **Optimize Performance**: Add debouncing, memoization, virtual scrolling
4. **Add Configuration UI**: Let users customize refresh interval, colors, etc.

## Extension Points

This plugin uses the `DASHBOARD` extension point. UI plugins can also extend:

- **`SIDEBAR`** - Add items to sidebar navigation
- **`SETTINGS`** - Add panels to settings page
- **`TOOLBAR`** - Add buttons to main toolbar
- **`CONTEXT_MENU`** - Add items to right-click menus
- **`STATUS_BAR`** - Add items to status bar

Example for sidebar:

```python
UIComponentDefinition(
    id="my-sidebar-item",
    extension_point=UIExtensionPoint.SIDEBAR,
    title="My Tool",
    icon="puzzle",
    route="/my-tool",
    order=50,
)
```

## Troubleshooting

### Widget Not Appearing

- **Check plugin is enabled**: Go to Plugins page and verify status
- **Refresh the page**: Try reloading the Electron app
- **Check extension point**: Verify you're on the Dashboard view
- **Check logs**: Look for errors in backend logs

### IPC Handlers Not Working

- **Verify channel names**: Must match exactly between backend and frontend
- **Check permissions**: Ensure `read_files` permission is granted
- **Test backend separately**: Try calling handler from Python REPL

### Stats Not Updating

- **Check project directory**: Verify path to `.auto-claude/specs/` is correct
- **Verify spec format**: Ensure specs have `implementation_plan.json` files
- **Clear cache**: Call `ui-extension:refresh-stats` to force recalculation

### TypeScript Errors

- **Install dependencies**: Run `npm install` in `apps/frontend/`
- **Check types**: Ensure `window.electronAPI` types are defined
- **Rebuild frontend**: Run `npm run build` in `apps/frontend/`

## Performance Considerations

This plugin implements several optimizations:

1. **Data Caching**: Stats are cached in memory to avoid re-reading files
2. **Debounced Refresh**: Auto-refresh doesn't show loading spinner
3. **Lazy Calculation**: Stats only calculated when widget is visible
4. **Window Focus**: Cache is cleared when window regains focus for fresh data

For very large projects (100+ specs), consider:
- Adding pagination or filtering
- Using background workers for calculation
- Implementing incremental updates instead of full recalculation

## Learn More

- [UI Plugin Development Guide](../../../guides/plugins/ui-plugins.md)
- [Plugin SDK Documentation](../../../apps/backend/plugins/sdk/ui.py)
- [Plugin Getting Started](../../../guides/plugins/getting-started.md)
- [React Component Patterns](../../../apps/frontend/src/renderer/components/)

## Real-World Examples

This pattern can be adapted for many use cases:

- **Build Queue Widget**: Show current and upcoming builds
- **Test Results Dashboard**: Display test coverage and pass rates
- **Git Activity Timeline**: Visualize commits and branches
- **Resource Monitor**: Show CPU, memory, disk usage
- **Integration Status**: Display connected services (Linear, GitHub, etc.)

## License

MIT - See LICENSE file for details
