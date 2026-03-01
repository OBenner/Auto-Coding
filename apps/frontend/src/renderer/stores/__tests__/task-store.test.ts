/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Task, TaskStatus, ImplementationPlan, ExecutionPhase } from '../../../shared/types';

// Mock window.electronAPI
vi.stubGlobal('window', {
  ...globalThis.window,
  electronAPI: {
    getTasks: vi.fn(),
    createTask: vi.fn(),
    startTask: vi.fn(),
    stopTask: vi.fn(),
    submitReview: vi.fn(),
    updateTaskStatus: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    archiveTasks: vi.fn(),
    getTokenStats: vi.fn(),
    checkTaskRunning: vi.fn(),
    recoverStuckTask: vi.fn(),
  },
});

// Mock debugLog
vi.mock('../../../shared/utils/debug-logger', () => ({
  debugLog: vi.fn(),
}));

// Mock isTerminalPhase
vi.mock('../../../shared/constants/phase-protocol', () => ({
  isTerminalPhase: vi.fn((phase: string) => phase === 'complete' || phase === 'failed'),
}));

import {
  useTaskStore,
  isDraftEmpty,
  isIncompleteHumanReview,
  getCompletedSubtaskCount,
  getTaskProgress,
  saveDraft,
  loadDraft,
  clearDraft,
  hasDraft,
  getTaskByGitHubIssue,
} from '../task-store';

function createMockTask(overrides: Partial<Task> = {}): Task {
  return {
    id: `task-${Math.random().toString(36).substr(2, 9)}`,
    specId: `spec-${Math.random().toString(36).substr(2, 9)}`,
    projectId: 'project-1',
    title: 'Test Task',
    description: 'A test task',
    status: 'backlog' as TaskStatus,
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides,
  } as Task;
}

describe('task-store', () => {
  beforeEach(() => {
    useTaskStore.setState({
      tasks: [],
      selectedTaskId: null,
      isLoading: false,
      error: null,
      taskOrder: null,
    });
    localStorage.clear();
  });

  describe('basic state management', () => {
    it('should start with empty state', () => {
      const state = useTaskStore.getState();
      expect(state.tasks).toEqual([]);
      expect(state.selectedTaskId).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should set tasks', () => {
      const tasks = [createMockTask({ id: 't1' }), createMockTask({ id: 't2' })];
      useTaskStore.getState().setTasks(tasks);
      expect(useTaskStore.getState().tasks).toHaveLength(2);
    });

    it('should add a task', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().addTask(task);
      expect(useTaskStore.getState().tasks).toHaveLength(1);
      expect(useTaskStore.getState().tasks[0].id).toBe('t1');
    });

    it('should update a task', () => {
      const task = createMockTask({ id: 't1', title: 'Original' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTask('t1', { title: 'Updated' });
      expect(useTaskStore.getState().tasks[0].title).toBe('Updated');
    });

    it('should find task by specId', () => {
      const task = createMockTask({ id: 't1', specId: 'spec-1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTask('spec-1', { title: 'Found by specId' });
      expect(useTaskStore.getState().tasks[0].title).toBe('Found by specId');
    });

    it('should not update non-existent task', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTask('nonexistent', { title: 'Nope' });
      expect(useTaskStore.getState().tasks[0].title).toBe('Test Task');
    });

    it('should select and deselect task', () => {
      useTaskStore.getState().selectTask('t1');
      expect(useTaskStore.getState().selectedTaskId).toBe('t1');
      useTaskStore.getState().selectTask(null);
      expect(useTaskStore.getState().selectedTaskId).toBeNull();
    });

    it('should set loading state', () => {
      useTaskStore.getState().setLoading(true);
      expect(useTaskStore.getState().isLoading).toBe(true);
    });

    it('should set error', () => {
      useTaskStore.getState().setError('Something went wrong');
      expect(useTaskStore.getState().error).toBe('Something went wrong');
    });

    it('should clear tasks', () => {
      useTaskStore.getState().setTasks([createMockTask()]);
      useTaskStore.getState().selectTask('t1');
      useTaskStore.getState().clearTasks();
      expect(useTaskStore.getState().tasks).toEqual([]);
      expect(useTaskStore.getState().selectedTaskId).toBeNull();
    });
  });

  describe('updateTaskStatus', () => {
    it('should update task status', () => {
      const task = createMockTask({ id: 't1', status: 'backlog' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTaskStatus('t1', 'in_progress');
      expect(useTaskStore.getState().tasks[0].status).toBe('in_progress');
    });

    it('should skip update if status is the same', () => {
      const task = createMockTask({ id: 't1', status: 'backlog' });
      useTaskStore.getState().setTasks([task]);
      const originalUpdatedAt = useTaskStore.getState().tasks[0].updatedAt;
      useTaskStore.getState().updateTaskStatus('t1', 'backlog');
      expect(useTaskStore.getState().tasks[0].updatedAt).toBe(originalUpdatedAt);
    });

    it('should reset execution progress to idle when status goes to backlog', () => {
      const task = createMockTask({
        id: 't1',
        status: 'in_progress',
        executionProgress: { phase: 'coding' as ExecutionPhase, phaseProgress: 50, overallProgress: 30 },
      });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTaskStatus('t1', 'backlog');
      expect(useTaskStore.getState().tasks[0].executionProgress?.phase).toBe('idle');
    });

    it('should set default planning phase when starting a task with no phase', () => {
      const task = createMockTask({ id: 't1', status: 'backlog' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTaskStatus('t1', 'in_progress');
      expect(useTaskStore.getState().tasks[0].executionProgress?.phase).toBe('planning');
    });

    it('should not update non-existent task', () => {
      useTaskStore.getState().setTasks([]);
      useTaskStore.getState().updateTaskStatus('nonexistent', 'done');
      // No error thrown
    });
  });

  describe('updateExecutionProgress', () => {
    it('should update execution progress', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateExecutionProgress('t1', {
        phase: 'coding' as ExecutionPhase,
        phaseProgress: 50,
        overallProgress: 25,
      });
      const updatedTask = useTaskStore.getState().tasks[0];
      expect(updatedTask.executionProgress?.phase).toBe('coding');
      expect(updatedTask.executionProgress?.phaseProgress).toBe(50);
    });

    it('should drop out-of-order updates based on sequence numbers', () => {
      const task = createMockTask({
        id: 't1',
        executionProgress: {
          phase: 'coding' as ExecutionPhase,
          phaseProgress: 50,
          overallProgress: 25,
          sequenceNumber: 10,
        },
      });
      useTaskStore.getState().setTasks([task]);
      // Try to apply an older update
      useTaskStore.getState().updateExecutionProgress('t1', {
        phase: 'planning' as ExecutionPhase,
        phaseProgress: 0,
        sequenceNumber: 5,
      });
      // Should still be at coding phase
      expect(useTaskStore.getState().tasks[0].executionProgress?.phase).toBe('coding');
    });
  });

  describe('updateTokenStats', () => {
    it('should update token stats', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().updateTokenStats('t1', {
        total_tokens: 1000,
        input_tokens: 600,
        output_tokens: 400,
      } as any);
      expect(useTaskStore.getState().tasks[0].tokenStats?.total_tokens).toBe(1000);
    });
  });

  describe('appendLog and batchAppendLogs', () => {
    it('should append a single log', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().appendLog('t1', 'Log entry 1');
      expect(useTaskStore.getState().tasks[0].logs).toEqual(['Log entry 1']);
    });

    it('should batch append multiple logs', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().batchAppendLogs('t1', ['Log 1', 'Log 2', 'Log 3']);
      expect(useTaskStore.getState().tasks[0].logs).toEqual(['Log 1', 'Log 2', 'Log 3']);
    });

    it('should skip batch append for empty logs array', () => {
      const task = createMockTask({ id: 't1' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().batchAppendLogs('t1', []);
      // State should not change (logs remain undefined)
    });
  });

  describe('selectors', () => {
    it('should get selected task', () => {
      const task = createMockTask({ id: 't1', title: 'Selected Task' });
      useTaskStore.getState().setTasks([task]);
      useTaskStore.getState().selectTask('t1');
      expect(useTaskStore.getState().getSelectedTask()?.title).toBe('Selected Task');
    });

    it('should return undefined if no task selected', () => {
      expect(useTaskStore.getState().getSelectedTask()).toBeUndefined();
    });

    it('should get tasks by status', () => {
      useTaskStore.getState().setTasks([
        createMockTask({ id: 't1', status: 'backlog' }),
        createMockTask({ id: 't2', status: 'in_progress' }),
        createMockTask({ id: 't3', status: 'backlog' }),
      ]);
      const backlogTasks = useTaskStore.getState().getTasksByStatus('backlog');
      expect(backlogTasks).toHaveLength(2);
    });
  });

  describe('task order (kanban drag-and-drop)', () => {
    it('should set task order', () => {
      useTaskStore.getState().setTaskOrder({
        backlog: ['t1', 't2'],
        queue: [],
        in_progress: [],
        ai_review: [],
        human_review: [],
        done: [],
        pr_created: [],
        error: [],
      });
      expect(useTaskStore.getState().taskOrder?.backlog).toEqual(['t1', 't2']);
    });

    it('should add new task to top of column in task order', () => {
      useTaskStore.getState().setTaskOrder({
        backlog: ['existing-1'],
        queue: [],
        in_progress: [],
        ai_review: [],
        human_review: [],
        done: [],
        pr_created: [],
        error: [],
      });
      const task = createMockTask({ id: 'new-task', status: 'backlog' });
      useTaskStore.getState().addTask(task);
      expect(useTaskStore.getState().taskOrder?.backlog[0]).toBe('new-task');
    });

    it('should move task to column top', () => {
      useTaskStore.getState().setTaskOrder({
        backlog: ['t1', 't2'],
        queue: [],
        in_progress: ['t3'],
        ai_review: [],
        human_review: [],
        done: [],
        pr_created: [],
        error: [],
      });
      useTaskStore.getState().moveTaskToColumnTop('t2', 'in_progress', 'backlog');
      expect(useTaskStore.getState().taskOrder?.backlog).toEqual(['t1']);
      expect(useTaskStore.getState().taskOrder?.in_progress[0]).toBe('t2');
    });

    it('should load task order from localStorage', () => {
      const order = {
        backlog: ['t1'],
        queue: ['t2'],
        in_progress: [],
        ai_review: [],
        human_review: [],
        done: [],
        pr_created: [],
        error: [],
      };
      localStorage.setItem('task-order-state-project-1', JSON.stringify(order));
      useTaskStore.getState().loadTaskOrder('project-1');
      expect(useTaskStore.getState().taskOrder?.backlog).toEqual(['t1']);
      expect(useTaskStore.getState().taskOrder?.queue).toEqual(['t2']);
    });

    it('should handle invalid localStorage data gracefully', () => {
      localStorage.setItem('task-order-state-project-1', 'invalid json');
      useTaskStore.getState().loadTaskOrder('project-1');
      // Should reset to empty order
      expect(useTaskStore.getState().taskOrder).toBeDefined();
      expect(useTaskStore.getState().taskOrder?.backlog).toEqual([]);
    });

    it('should save task order to localStorage', () => {
      useTaskStore.getState().setTaskOrder({
        backlog: ['t1'],
        queue: [],
        in_progress: [],
        ai_review: [],
        human_review: [],
        done: [],
        pr_created: [],
        error: [],
      });
      const result = useTaskStore.getState().saveTaskOrder('project-1');
      expect(result).toBe(true);
      const stored = JSON.parse(localStorage.getItem('task-order-state-project-1')!);
      expect(stored.backlog).toEqual(['t1']);
    });

    it('should return false when saving with no task order', () => {
      const result = useTaskStore.getState().saveTaskOrder('project-1');
      expect(result).toBe(false);
    });

    it('should clear task order', () => {
      localStorage.setItem('task-order-state-project-1', '{}');
      useTaskStore.getState().setTaskOrder({ backlog: ['t1'] } as any);
      useTaskStore.getState().clearTaskOrder('project-1');
      expect(useTaskStore.getState().taskOrder).toBeNull();
      expect(localStorage.getItem('task-order-state-project-1')).toBeNull();
    });
  });

  describe('task status change listeners', () => {
    it('should register and call listener on status change', async () => {
      const listener = vi.fn();
      const task = createMockTask({ id: 't1', status: 'backlog' });
      useTaskStore.getState().setTasks([task]);
      const unregister = useTaskStore.getState().registerTaskStatusChangeListener(listener);

      useTaskStore.getState().updateTaskStatus('t1', 'in_progress');

      // Wait for queueMicrotask
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(listener).toHaveBeenCalledWith('t1', 'backlog', 'in_progress');
      unregister();
    });

    it('should unregister listener', async () => {
      const listener = vi.fn();
      const task = createMockTask({ id: 't1', status: 'backlog' });
      useTaskStore.getState().setTasks([task]);
      const unregister = useTaskStore.getState().registerTaskStatusChangeListener(listener);
      unregister();

      useTaskStore.getState().updateTaskStatus('t1', 'in_progress');
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('draft management', () => {
    it('should save and load draft', () => {
      const draft = {
        projectId: 'project-1',
        title: 'My Draft',
        description: 'Draft description',
        images: [],
      };
      saveDraft(draft as any);
      const loaded = loadDraft('project-1');
      expect(loaded?.title).toBe('My Draft');
      expect(loaded?.description).toBe('Draft description');
    });

    it('should return null for non-existent draft', () => {
      expect(loadDraft('nonexistent')).toBeNull();
    });

    it('should clear draft', () => {
      saveDraft({ projectId: 'project-1', title: 'Draft', description: '', images: [] } as any);
      clearDraft('project-1');
      expect(loadDraft('project-1')).toBeNull();
    });

    it('should check if draft exists', () => {
      expect(hasDraft('project-1')).toBe(false);
      saveDraft({ projectId: 'project-1', title: 'Draft', description: '', images: [] } as any);
      expect(hasDraft('project-1')).toBe(true);
    });
  });

  describe('isDraftEmpty', () => {
    it('should return true for null', () => {
      expect(isDraftEmpty(null)).toBe(true);
    });

    it('should return true for empty draft', () => {
      expect(isDraftEmpty({
        title: '', description: '', images: [],
        projectId: 'p1',
      } as any)).toBe(true);
    });

    it('should return false for draft with title', () => {
      expect(isDraftEmpty({
        title: 'Something', description: '', images: [],
        projectId: 'p1',
      } as any)).toBe(false);
    });

    it('should return false for draft with images', () => {
      expect(isDraftEmpty({
        title: '', description: '', images: [{ data: 'x' }],
        projectId: 'p1',
      } as any)).toBe(false);
    });

    it('should return false for draft with category', () => {
      expect(isDraftEmpty({
        title: '', description: '', images: [],
        category: 'feature', projectId: 'p1',
      } as any)).toBe(false);
    });
  });

  describe('task state detection helpers', () => {
    it('isIncompleteHumanReview should return false for non-human_review tasks', () => {
      expect(isIncompleteHumanReview(createMockTask({ status: 'backlog' }))).toBe(false);
    });

    it('isIncompleteHumanReview should return false for error review reason', () => {
      expect(isIncompleteHumanReview(createMockTask({
        status: 'human_review',
        reviewReason: 'errors',
      } as any))).toBe(false);
    });

    it('isIncompleteHumanReview should return true for no subtasks', () => {
      expect(isIncompleteHumanReview(createMockTask({
        status: 'human_review',
        subtasks: [],
      } as any))).toBe(true);
    });

    it('isIncompleteHumanReview should return true for zero completed subtasks', () => {
      expect(isIncompleteHumanReview(createMockTask({
        status: 'human_review',
        subtasks: [
          { id: 's1', status: 'pending' },
          { id: 's2', status: 'pending' },
        ],
      } as any))).toBe(true);
    });

    it('isIncompleteHumanReview should return false if some subtasks completed', () => {
      expect(isIncompleteHumanReview(createMockTask({
        status: 'human_review',
        subtasks: [
          { id: 's1', status: 'completed' },
          { id: 's2', status: 'pending' },
        ],
      } as any))).toBe(false);
    });

    it('getCompletedSubtaskCount should count completed subtasks', () => {
      expect(getCompletedSubtaskCount(createMockTask({
        subtasks: [
          { id: 's1', status: 'completed' },
          { id: 's2', status: 'pending' },
          { id: 's3', status: 'completed' },
        ],
      } as any))).toBe(2);
    });

    it('getCompletedSubtaskCount should return 0 for no subtasks', () => {
      expect(getCompletedSubtaskCount(createMockTask())).toBe(0);
    });

    it('getTaskProgress should calculate progress', () => {
      const progress = getTaskProgress(createMockTask({
        subtasks: [
          { id: 's1', status: 'completed' },
          { id: 's2', status: 'completed' },
          { id: 's3', status: 'pending' },
          { id: 's4', status: 'pending' },
        ],
      } as any));
      expect(progress.completed).toBe(2);
      expect(progress.total).toBe(4);
      expect(progress.percentage).toBe(50);
    });

    it('getTaskProgress should handle no subtasks', () => {
      const progress = getTaskProgress(createMockTask());
      expect(progress.completed).toBe(0);
      expect(progress.total).toBe(0);
      expect(progress.percentage).toBe(0);
    });
  });

  describe('getTaskByGitHubIssue', () => {
    it('should find task by GitHub issue number', () => {
      useTaskStore.getState().setTasks([
        createMockTask({ id: 't1', metadata: { githubIssueNumber: 42 } as any }),
        createMockTask({ id: 't2', metadata: { githubIssueNumber: 99 } as any }),
      ]);
      const found = getTaskByGitHubIssue(42);
      expect(found?.id).toBe('t1');
    });

    it('should return undefined if not found', () => {
      useTaskStore.getState().setTasks([
        createMockTask({ id: 't1' }),
      ]);
      expect(getTaskByGitHubIssue(999)).toBeUndefined();
    });
  });
});
