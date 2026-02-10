/**
 * Integration tests for file watching
 * Tests FileWatcher triggers on plan changes
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mkdirSync, writeFileSync, rmSync, existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';

// Test directories
const TEST_DIR = '/tmp/file-watcher-test';
const TEST_SPEC_DIR = path.join(TEST_DIR, 'test-spec');

// Mock chokidar watcher
const mockWatcher = Object.assign(new EventEmitter(), {
  close: vi.fn(() => Promise.resolve()),
  add: vi.fn(),
  unwatch: vi.fn()
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
      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      const errorHandler = vi.fn();
      watcher.on('error', errorHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);

      expect(errorHandler).toHaveBeenCalledWith(
        'task-1',
        expect.stringContaining('not found')
      );
    });

    it('should start watching existing plan file', async () => {
      // Create plan file first
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const chokidar = await import('chokidar');
      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

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
      const plan = createTestPlan();
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(plan));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);

      expect(progressHandler).toHaveBeenCalledWith('task-1', expect.objectContaining({
        feature: 'Test Feature'
      }));
    });

    it('should emit progress on file change', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

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

      // Wait for debounce period (default 300ms)
      await new Promise(resolve => setTimeout(resolve, 350));

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

    it('should handle file parse errors gracefully', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

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

      // Should not crash, just ignore the invalid JSON
      expect(errorHandler).not.toHaveBeenCalled();
    });

    it('should forward watcher errors', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      const errorHandler = vi.fn();
      watcher.on('error', errorHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);

      // Simulate watcher error
      mockWatcher.emit('error', new Error('Watch failed'));

      expect(errorHandler).toHaveBeenCalledWith('task-1', 'Watch failed');
    });

    it('should stop watching task when unwatched', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      expect(watcher.isWatching('task-1')).toBe(true);

      await watcher.unwatch('task-1');

      expect(watcher.isWatching('task-1')).toBe(false);
      expect(mockWatcher.close).toHaveBeenCalled();
    });

    it('should stop watching when same task is watched again', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      await watcher.watch('task-1', TEST_SPEC_DIR);

      // Should have called close on the first watcher
      expect(mockWatcher.close).toHaveBeenCalled();
    });

    it('should track multiple watched tasks', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const spec2Dir = path.join(TEST_DIR, 'test-spec-2');
      mkdirSync(spec2Dir, { recursive: true });
      const plan2Path = path.join(spec2Dir, 'implementation_plan.json');
      writeFileSync(plan2Path, JSON.stringify(createTestPlan({ feature: 'Feature 2' })));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      await watcher.watch('task-2', spec2Dir);

      expect(watcher.isWatching('task-1')).toBe(true);
      expect(watcher.isWatching('task-2')).toBe(true);
    });

    it('should unwatchAll and clear all watchers', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);
      await watcher.unwatchAll();

      expect(watcher.isWatching('task-1')).toBe(false);
    });

    it('should get current plan for watched task', async () => {
      const plan = createTestPlan();
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(plan));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      await watcher.watch('task-1', TEST_SPEC_DIR);

      const currentPlan = watcher.getCurrentPlan('task-1');

      expect(currentPlan).toMatchObject({
        feature: 'Test Feature'
      });
    });

    it('should return null for non-watched task', async () => {
      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      const currentPlan = watcher.getCurrentPlan('nonexistent');

      expect(currentPlan).toBeNull();
    });

    it('should stop watching multiple tasks', async () => {
      const plan1Path = path.join(TEST_SPEC_DIR, 'task1', 'implementation_plan.json');
      const plan2Path = path.join(TEST_SPEC_DIR, 'task2', 'implementation_plan.json');

      mkdirSync(path.join(TEST_SPEC_DIR, 'task1'), { recursive: true });
      mkdirSync(path.join(TEST_SPEC_DIR, 'task2'), { recursive: true });
      writeFileSync(plan1Path, JSON.stringify(createTestPlan()));
      writeFileSync(plan2Path, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher();

      await watcher.watch('task-1', path.join(TEST_SPEC_DIR, 'task1'));
      await watcher.watch('task-2', path.join(TEST_SPEC_DIR, 'task2'));

      expect(watcher.isWatching('task-1')).toBe(true);
      expect(watcher.isWatching('task-2')).toBe(true);

      await watcher.unwatchAll();

      expect(watcher.isWatching('task-1')).toBe(false);
      expect(watcher.isWatching('task-2')).toBe(false);
    });
  });

  describe('FileWatcher - Debounce Behavior', () => {
    it('should debounce rapid file changes', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher(100); // Short debounce for testing

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // Simulate 5 rapid changes
      for (let i = 1; i <= 5; i++) {
        const updatedPlan = createTestPlan({
          updated_at: new Date(Date.now() + i).toISOString()
        });
        writeFileSync(planPath, JSON.stringify(updatedPlan));
        mockWatcher.emit('change', planPath);
      }

      // Wait for debounce period
      await new Promise(resolve => setTimeout(resolve, 150));

      // Should only emit once after debounce
      expect(progressHandler).toHaveBeenCalledTimes(1);
    });

    it('should emit latest state after debounce period', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher(100);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // First change
      const plan1 = createTestPlan({
        phases: [
          {
            phase: 1,
            name: 'Phase 1',
            type: 'implementation',
            subtasks: [
              { id: 'subtask-1', description: 'Task 1', status: 'in_progress' }
            ]
          }
        ]
      });
      writeFileSync(planPath, JSON.stringify(plan1));
      mockWatcher.emit('change', planPath);

      // Second change (should override first)
      const plan2 = createTestPlan({
        phases: [
          {
            phase: 1,
            name: 'Phase 1',
            type: 'implementation',
            subtasks: [
              { id: 'subtask-1', description: 'Task 1', status: 'completed' }
            ]
          }
        ]
      });
      writeFileSync(planPath, JSON.stringify(plan2));
      mockWatcher.emit('change', planPath);

      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 150));

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
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher(200); // Custom delay

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Updated' })));
      mockWatcher.emit('change', planPath);

      // Check before debounce period
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(progressHandler).not.toHaveBeenCalled();

      // Wait for full debounce period
      await new Promise(resolve => setTimeout(resolve, 150));
      expect(progressHandler).toHaveBeenCalledTimes(1);
    });

    it('should clear pending debounce on unwatch', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher(200);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // Trigger change
      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Updated' })));
      mockWatcher.emit('change', planPath);

      // Unwatch before debounce period expires
      await watcher.unwatch('task-1');

      // Wait past debounce period
      await new Promise(resolve => setTimeout(resolve, 250));

      // Should not emit because unwatch cleared the timeout
      expect(progressHandler).not.toHaveBeenCalled();
    });

    it('should clear all pending debounces on unwatchAll', async () => {
      const plan1Path = path.join(TEST_SPEC_DIR, 'task1', 'implementation_plan.json');
      const plan2Path = path.join(TEST_SPEC_DIR, 'task2', 'implementation_plan.json');

      mkdirSync(path.join(TEST_SPEC_DIR, 'task1'), { recursive: true });
      mkdirSync(path.join(TEST_SPEC_DIR, 'task2'), { recursive: true });
      writeFileSync(plan1Path, JSON.stringify(createTestPlan()));
      writeFileSync(plan2Path, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher(200);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', path.join(TEST_SPEC_DIR, 'task1'));
      await watcher.watch('task-2', path.join(TEST_SPEC_DIR, 'task2'));
      progressHandler.mockClear();

      // Trigger changes on both tasks
      writeFileSync(plan1Path, JSON.stringify(createTestPlan({ feature: 'Updated 1' })));
      writeFileSync(plan2Path, JSON.stringify(createTestPlan({ feature: 'Updated 2' })));
      mockWatcher.emit('change', plan1Path);
      mockWatcher.emit('change', plan2Path);

      // Unwatch all before debounce period expires
      await watcher.unwatchAll();

      // Wait past debounce period
      await new Promise(resolve => setTimeout(resolve, 250));

      // Should not emit for either task
      expect(progressHandler).not.toHaveBeenCalled();
    });

    it('should handle consecutive debounce windows separately', async () => {
      const planPath = path.join(TEST_SPEC_DIR, 'implementation_plan.json');
      writeFileSync(planPath, JSON.stringify(createTestPlan()));

      const { FileWatcher } = await import('../../main/file-watcher');
      const watcher = new FileWatcher(100);

      const progressHandler = vi.fn();
      watcher.on('progress', progressHandler);

      await watcher.watch('task-1', TEST_SPEC_DIR);
      progressHandler.mockClear();

      // First batch of changes
      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Update 1' })));
      mockWatcher.emit('change', planPath);

      // Wait for first debounce to complete
      await new Promise(resolve => setTimeout(resolve, 150));
      expect(progressHandler).toHaveBeenCalledTimes(1);
      progressHandler.mockClear();

      // Second batch of changes
      writeFileSync(planPath, JSON.stringify(createTestPlan({ feature: 'Update 2' })));
      mockWatcher.emit('change', planPath);

      // Wait for second debounce to complete
      await new Promise(resolve => setTimeout(resolve, 150));
      expect(progressHandler).toHaveBeenCalledTimes(1);
    });
  });
});
