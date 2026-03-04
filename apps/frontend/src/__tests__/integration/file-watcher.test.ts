/**
 * Integration tests for file watching
 * Tests FileWatcher triggers on plan changes
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mkdirSync, mkdtempSync, writeFileSync, rmSync, existsSync } from 'fs';
import path from 'path';
import os from 'os';
import { EventEmitter } from 'events';

// Test directories - use mkdtempSync for secure temp directory creation
const TEST_DIR = mkdtempSync(path.join(os.tmpdir(), 'file-watcher-test-'));
const TEST_SPEC_DIR = path.join(TEST_DIR, 'test-spec');

// Mock chokidar watcher
const mockWatcher = Object.assign(new EventEmitter(), {
  close: vi.fn(() => Promise.resolve()),
  add: vi.fn(),
  unwatch: vi.fn(),
  removeListener: vi.fn(function(this: EventEmitter, event: string, fn: (...args: unknown[]) => void) {
    EventEmitter.prototype.removeListener.call(this, event, fn);
    return this;
  })
});

vi.mock('chokidar', () => ({
  default: {
    watch: vi.fn(() => mockWatcher)
  },
  watch: vi.fn(() => mockWatcher)
}));

// Sample implementation plan
function createTestPlan(overrides: Record<string, unknown> = {}): object {
  return {
    feature: 'Test Feature',
    workflow_type: 'feature',
    services_involved: [],
    phases: [
      {
        phase: 1,
        name: 'Test Phase',
        type: 'implementation',
        subtasks: [
          { id: 'subtask-1', description: 'Subtask 1', status: 'pending' }
        ]
      }
    ],
    final_acceptance: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    spec_file: 'spec.md',
    ...overrides
  };
}

/** Helper: create a plan file and return the path */
function writePlan(dir: string, overrides: Record<string, unknown> = {}): string {
  const planPath = path.join(dir, 'implementation_plan.json');
  writeFileSync(planPath, JSON.stringify(createTestPlan(overrides)));
  return planPath;
}

/** Helper: create a FileWatcher with optional debounce */
async function createWatcher(debounceDelay?: number) {
  const { FileWatcher } = await import('../../main/file-watcher');
  return debounceDelay !== undefined ? new FileWatcher(debounceDelay) : new FileWatcher();
}

// Setup test directories
function setupTestDirs(): void {
  mkdirSync(TEST_SPEC_DIR, { recursive: true });
}

// Cleanup test directories
function cleanupTestDirs(): void {
  if (existsSync(TEST_DIR)) {
    rmSync(TEST_DIR, { recursive: true, force: true });
  }
}

describe('File Watcher Integration', () => {
  beforeEach(async () => {
    cleanupTestDirs();
    setupTestDirs();
    vi.clearAllMocks();
    vi.resetModules();
    mockWatcher.removeAllListeners();
  });

  afterEach(() => {
    cleanupTestDirs();
    vi.clearAllMocks();
  });

  describe('FileWatcher', () => {
    it('should emit error when plan file does not exist', async () => {
      const watcher = await createWatcher();

      const errorHandler = vi.fn();
      watcher.on('error', errorHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);

      expect(errorHandler).toHaveBeenCalledWith(
        'task-1',
        expect.stringContaining('not found')
      );
    });

    it('should start watching existing plan file', async () => {
      const planPath = writePlan(TEST_SPEC_DIR);

      const chokidar = await import('chokidar');
      const watcher = await createWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);

      expect(chokidar.default.watch).toHaveBeenCalledWith(
        planPath,
        expect.objectContaining({
          persistent: true,
          ignoreInitial: true,
          awaitWriteFinish: expect.objectContaining({
            stabilityThreshold: 300,
            pollInterval: 100
          })
        })
      );
    });

    it('should emit initial progress after starting watch', async () => {
      writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);

      expect(progressHandler).toHaveBeenCalledWith('task-1', expect.objectContaining({
        feature: 'Test Feature'
      }));
    });

    it('should emit progress on file change', async () => {
      vi.useFakeTimers();
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // Update file
      const updatedPlan = createTestPlan({
        phases: [
          {
            phase: 1,
            name: 'Test Phase',
            type: 'implementation',
            subtasks: [
              { id: 'subtask-1', description: 'Subtask 1', status: 'completed' }
            ]
          }
        ]
      });
      writeFileSync(planPath, JSON.stringify(updatedPlan));

      // Simulate file change event
      mockWatcher.emit('change', planPath);

      // Advance past debounce period (default 300ms)
      await vi.advanceTimersByTimeAsync(350);

      expect(progressHandler).toHaveBeenCalledWith('task-1', expect.objectContaining({
        phases: expect.arrayContaining([
          expect.objectContaining({
            subtasks: expect.arrayContaining([
              expect.objectContaining({ status: 'completed' })
            ])
          })
        ])
      }));

      vi.useRealTimers();
    });

    it('should handle file parse errors gracefully', async () => {
      vi.useFakeTimers();
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      const progressHandler = vi.fn();
      const errorHandler = vi.fn();
      watcher.on('progress', progressHandler);
      watcher.on('error', errorHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // Write invalid JSON
      writeFileSync(planPath, 'invalid json {{{');

      // Simulate file change
      mockWatcher.emit('change', planPath);

      // Advance past debounce period so the callback fires
      await vi.advanceTimersByTimeAsync(350);

      // Should not crash or emit error, just silently ignore the invalid JSON
      expect(errorHandler).not.toHaveBeenCalled();
      expect(progressHandler).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('should forward watcher errors', async () => {
      writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      const errorHandler = vi.fn();
      watcher.on('error', errorHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);

      // Simulate watcher error
      mockWatcher.emit('error', new Error('Watch failed'));

      expect(errorHandler).toHaveBeenCalledWith('task-1', 'Watch failed');
    });

    it('should stop watching task when unwatched', async () => {
      writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      expect(watcher.isWatching('task-1')).toBe(true);

      await watcher.unwatch('task-1');

      expect(watcher.isWatching('task-1')).toBe(false);
      expect(mockWatcher.close).toHaveBeenCalled();
    });

    it('should stop watching when same task is watched again', async () => {
      writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      await watcher.watch('task-1', TEST_SPEC_DIR);

      // Should have called close on the first watcher
      expect(mockWatcher.close).toHaveBeenCalled();
    });

    it('should track multiple watched tasks', async () => {
      writePlan(TEST_SPEC_DIR);

      const spec2Dir = path.join(TEST_DIR, 'test-spec-2');
      mkdirSync(spec2Dir, { recursive: true });
      writePlan(spec2Dir, { feature: 'Feature 2' });

      const watcher = await createWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      await watcher.watch('task-2', spec2Dir);

      expect(watcher.isWatching('task-1')).toBe(true);
      expect(watcher.isWatching('task-2')).toBe(true);
    });

    it('should unwatchAll and clear all watchers', async () => {
      writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      await watcher.unwatchAll();

      expect(watcher.isWatching('task-1')).toBe(false);
    });

    it('should get current plan for watched task', async () => {
      writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);

      const currentPlan = watcher.getCurrentPlan('task-1');

      expect(currentPlan).toMatchObject({
        feature: 'Test Feature'
      });
    });

    it('should return null for non-watched task', async () => {
      const watcher = await createWatcher();

      const currentPlan = watcher.getCurrentPlan('nonexistent');

      expect(currentPlan).toBeNull();
    });

    it('should stop watching multiple tasks', async () => {
      const task1Dir = path.join(TEST_SPEC_DIR, 'task1');
      const task2Dir = path.join(TEST_SPEC_DIR, 'task2');
      mkdirSync(task1Dir, { recursive: true });
      mkdirSync(task2Dir, { recursive: true });
      writePlan(task1Dir);
      writePlan(task2Dir);

      const watcher = await createWatcher();

      await watcher.watch('task-1', task1Dir);
      await watcher.watch('task-2', task2Dir);

      expect(watcher.isWatching('task-1')).toBe(true);
      expect(watcher.isWatching('task-2')).toBe(true);

      await watcher.unwatchAll();

      expect(watcher.isWatching('task-1')).toBe(false);
      expect(watcher.isWatching('task-2')).toBe(false);
    });
  });

  describe('FileWatcher - Debounce Behavior', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should debounce rapid file changes', async () => {
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher(100);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // Simulate 5 rapid changes
      for (let i = 1; i <= 5; i++) {
        writeFileSync(planPath, JSON.stringify(createTestPlan({
          updated_at: new Date(Date.now() + i).toISOString()
        })));
        mockWatcher.emit('change', planPath);
      }

      // Advance past debounce period
      await vi.advanceTimersByTimeAsync(150);

      // Should only emit once after debounce
      expect(progressHandler).toHaveBeenCalledTimes(1);
    });

    it('should emit latest state after debounce period', async () => {
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher(100);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // First change
      writeFileSync(planPath, JSON.stringify(createTestPlan({
        phases: [{
          phase: 1, name: 'Phase 1', type: 'implementation',
          subtasks: [{ id: 'subtask-1', description: 'Task 1', status: 'in_progress' }]
        }]
      })));
      mockWatcher.emit('change', planPath);

      // Second change (should override first)
      writeFileSync(planPath, JSON.stringify(createTestPlan({
        phases: [{
          phase: 1, name: 'Phase 1', type: 'implementation',
          subtasks: [{ id: 'subtask-1', description: 'Task 1', status: 'completed' }]
        }]
      })));
      mockWatcher.emit('change', planPath);

      // Advance past debounce
      await vi.advanceTimersByTimeAsync(150);

      // Should emit only the latest state
      expect(progressHandler).toHaveBeenCalledTimes(1);
      expect(progressHandler).toHaveBeenCalledWith('task-1', expect.objectContaining({
        phases: expect.arrayContaining([
          expect.objectContaining({
            subtasks: expect.arrayContaining([
              expect.objectContaining({ status: 'completed' })
            ])
          })
        ])
      }));
    });

    it('should respect custom debounce delay', async () => {
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher(200);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Updated' })));
      mockWatcher.emit('change', planPath);

      // Check before debounce period
      await vi.advanceTimersByTimeAsync(100);
      expect(progressHandler).not.toHaveBeenCalled();

      // Advance past full debounce period
      await vi.advanceTimersByTimeAsync(150);
      expect(progressHandler).toHaveBeenCalledTimes(1);
    });

    it('should clear pending debounce on unwatch', async () => {
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher(200);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // Trigger change
      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Updated' })));
      mockWatcher.emit('change', planPath);

      // Unwatch before debounce period expires
      await watcher.unwatch('task-1');

      // Advance past debounce period
      await vi.advanceTimersByTimeAsync(250);

      // Should not emit because unwatch cleared the timeout
      expect(progressHandler).not.toHaveBeenCalled();
    });

    it('should clear all pending debounces on unwatchAll', async () => {
      const task1Dir = path.join(TEST_SPEC_DIR, 'task1');
      const task2Dir = path.join(TEST_SPEC_DIR, 'task2');
      mkdirSync(task1Dir, { recursive: true });
      mkdirSync(task2Dir, { recursive: true });
      const plan1Path = writePlan(task1Dir);
      const plan2Path = writePlan(task2Dir);

      const watcher = await createWatcher(200);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', task1Dir);
      await watcher.watch('task-2', task2Dir);
      progressHandler.mockClear();

      // Trigger changes on both tasks
      writeFileSync(plan1Path, JSON.stringify(createTestPlan({ feature: 'Updated 1' })));
      writeFileSync(plan2Path, JSON.stringify(createTestPlan({ feature: 'Updated 2' })));
      mockWatcher.emit('change', plan1Path);
      mockWatcher.emit('change', plan2Path);

      // Unwatch all before debounce period expires
      await watcher.unwatchAll();

      // Advance past debounce period
      await vi.advanceTimersByTimeAsync(250);

      // Should not emit for either task
      expect(progressHandler).not.toHaveBeenCalled();
    });

    it('should handle consecutive debounce windows separately', async () => {
      const planPath = writePlan(TEST_SPEC_DIR);

      const watcher = await createWatcher(100);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // First batch of changes
      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Update 1' })));
      mockWatcher.emit('change', planPath);

      // Advance past first debounce
      await vi.advanceTimersByTimeAsync(150);
      expect(progressHandler).toHaveBeenCalledTimes(1);
      progressHandler.mockClear();

      // Second batch of changes
      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Update 2' })));
      mockWatcher.emit('change', planPath);

      // Advance past second debounce
      await vi.advanceTimersByTimeAsync(150);
      expect(progressHandler).toHaveBeenCalledTimes(1);
    });
  });
});
