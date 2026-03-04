# File Watcher — Debounced Event Batching

The `FileWatcher` class monitors `implementation_plan.json` files for real-time
progress updates during autonomous agent sessions. It uses chokidar for
cross-platform filesystem watching and EventEmitter for notifying the renderer.

## Problem

When agents modify multiple files rapidly (e.g., during a multi-file refactor),
each file change triggers a separate event. Without batching, this causes:

- Multiple redundant re-renders in the UI
- Potential race conditions from overlapping IPC calls
- Wasted CPU reading/parsing the same file repeatedly

## Solution

### Debounced Event Emission

File change events are debounced per task. When multiple changes occur within
the debounce window (default 300ms), only the final state is emitted:

```text
File changes:  ──X──X──X──X──────────────────X──X────────
Debounce:                    |-- 300ms --|              |-- 300ms --|
Emitted:                                 ✓                         ✓
```

### Race Condition Protection

The watcher handles concurrent `watch()`/`unwatch()` calls safely:

- **Pending watches**: Tracks in-flight `watch()` calls to prevent duplicate
  watchers from concurrent callers
- **Cancellation**: If `unwatch()` is called while `watch()` is in-flight,
  the watcher creation is cancelled rather than leaked
- **Listener cleanup**: Change handlers are stored and removed before closing
  watchers, preventing stale timeout scheduling during teardown

## API

```typescript
const watcher = new FileWatcher(debounceDelay?: number);

// Start watching a task's plan file
await watcher.watch(taskId: string, specDir: string): Promise<void>;

// Stop watching a specific task
await watcher.unwatch(taskId: string): Promise<void>;

// Stop all watchers (removes listeners, closes watchers, clears timeouts)
await watcher.unwatchAll(): Promise<void>;

// Query state
watcher.isWatching(taskId: string): boolean;
watcher.getWatchedSpecDir(taskId: string): string | null;
watcher.getCurrentPlan(taskId: string): ImplementationPlan | null;

// Events
watcher.on('progress', (taskId: string, plan: ImplementationPlan) => void);
watcher.on('error', (taskId: string, message: string) => void);
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `debounceDelay` | 300ms | Delay before emitting after the last change event |
| `awaitWriteFinish.stabilityThreshold` | 300ms | chokidar file stability check |
| `awaitWriteFinish.pollInterval` | 100ms | chokidar polling interval |

## Teardown Order

`unwatchAll()` follows a specific order to prevent race conditions:

1. Cancel in-flight `watch()` calls (set cancellation flags)
2. Remove `change` listeners from all watchers (prevents new timeouts)
3. Close all chokidar watchers
4. Clear remaining debounce timeouts
