import chokidar, { FSWatcher } from 'chokidar';
import { readFileSync, existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import type { ImplementationPlan } from '../shared/types';

/**
 * Default debounce delay in milliseconds
 */
const DEFAULT_DEBOUNCE_DELAY = 300;

interface WatcherInfo {
  taskId: string;
  watcher: FSWatcher;
  planPath: string;
}

/**
 * Watches implementation_plan.json files for real-time progress updates
 */
export class FileWatcher extends EventEmitter {
  private watchers: Map<string, WatcherInfo> = new Map();
  private debounceTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private debounceDelay: number;

  constructor(debounceDelay: number = DEFAULT_DEBOUNCE_DELAY) {
    super();
    this.debounceDelay = debounceDelay;
  }

  /**
   * Start watching a task's implementation plan
   */
  async watch(taskId: string, specDir: string): Promise<void> {
    // Stop any existing watcher for this task
    await this.unwatch(taskId);

    const planPath = path.join(specDir, 'implementation_plan.json');

    // Check if plan file exists
    if (!existsSync(planPath)) {
      this.emit('error', taskId, `Plan file not found: ${planPath}`);
      return;
    }

    // Create watcher with settings to handle frequent writes
    const watcher = chokidar.watch(planPath, {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 300,
        pollInterval: 100
      }
    });

    // Store watcher info
    this.watchers.set(taskId, {
      taskId,
      watcher,
      planPath
    });

    // Handle file changes
    watcher.on('change', () => {
      // Clear existing timeout for this task
      const existingTimeout = this.debounceTimeouts.get(taskId);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
      }

      // Set new timeout to emit after debounce delay
      const timeout = setTimeout(() => {
        try {
          const content = readFileSync(planPath, 'utf-8');
          const plan: ImplementationPlan = JSON.parse(content);
          this.emit('progress', taskId, plan);
        } catch {
          // File might be in the middle of being written
          // Ignore parse errors, next change event will have complete file
        }
        // Remove timeout from map after it executes
        this.debounceTimeouts.delete(taskId);
      }, this.debounceDelay);

      // Store timeout in map
      this.debounceTimeouts.set(taskId, timeout);
    });

    // Handle errors
    watcher.on('error', (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      this.emit('error', taskId, message);
    });

    // Read and emit initial state
    try {
      const content = readFileSync(planPath, 'utf-8');
      const plan: ImplementationPlan = JSON.parse(content);
      this.emit('progress', taskId, plan);
    } catch {
      // Initial read failed - not critical
    }
  }

  /**
   * Stop watching a task
   */
  async unwatch(taskId: string): Promise<void> {
    // Clear any pending timeout
    const timeout = this.debounceTimeouts.get(taskId);
    if (timeout) {
      clearTimeout(timeout);
      this.debounceTimeouts.delete(taskId);
    }

    const watcherInfo = this.watchers.get(taskId);
    if (watcherInfo) {
      await watcherInfo.watcher.close();
      this.watchers.delete(taskId);
    }
  }

  /**
   * Stop all watchers
   */
  async unwatchAll(): Promise<void> {
    // Clear all pending timeouts
    for (const timeout of this.debounceTimeouts.values()) {
      clearTimeout(timeout);
    }
    this.debounceTimeouts.clear();

    const closePromises = Array.from(this.watchers.values()).map(
      async (info) => {
        await info.watcher.close();
      }
    );
    await Promise.all(closePromises);
    this.watchers.clear();
  }

  /**
   * Check if a task is being watched
   */
  isWatching(taskId: string): boolean {
    return this.watchers.has(taskId);
  }

  /**
   * Get current plan state for a task
   */
  getCurrentPlan(taskId: string): ImplementationPlan | null {
    const watcherInfo = this.watchers.get(taskId);
    if (!watcherInfo) return null;

    try {
      const content = readFileSync(watcherInfo.planPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return null;
    }
  }
}

// Singleton instance
export const fileWatcher = new FileWatcher();
