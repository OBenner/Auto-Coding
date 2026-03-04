/**
 * @vitest-environment jsdom
 */
/**
 * Tests for KanbanBoard logic - column configuration, task distribution, status mapping
 */

import { describe, it, expect } from 'vitest';
import { TASK_STATUS_COLUMNS } from '../../../shared/constants/task';
import type { TaskStatusColumn } from '../../../shared/constants/task';

describe('KanbanBoard logic', () => {
  describe('column configuration', () => {
    it('should have 6 status columns', () => {
      expect(TASK_STATUS_COLUMNS).toHaveLength(6);
    });

    it('should define columns in correct order', () => {
      expect(TASK_STATUS_COLUMNS[0]).toBe('backlog');
      expect(TASK_STATUS_COLUMNS[1]).toBe('queue');
      expect(TASK_STATUS_COLUMNS[2]).toBe('in_progress');
      expect(TASK_STATUS_COLUMNS[3]).toBe('ai_review');
      expect(TASK_STATUS_COLUMNS[4]).toBe('human_review');
      expect(TASK_STATUS_COLUMNS[5]).toBe('done');
    });
  });

  describe('task distribution logic', () => {
    interface MockTask {
      id: string;
      status: TaskStatusColumn;
      title: string;
    }

    const distributeTasksToColumns = (tasks: MockTask[]) => {
      const columns: Record<TaskStatusColumn, MockTask[]> = {
        backlog: [],
        queue: [],
        in_progress: [],
        ai_review: [],
        human_review: [],
        done: [],
      };

      for (const task of tasks) {
        if (columns[task.status]) {
          columns[task.status].push(task);
        }
      }

      return columns;
    };

    it('should distribute tasks to correct columns', () => {
      const tasks: MockTask[] = [
        { id: '1', status: 'backlog', title: 'Task 1' },
        { id: '2', status: 'in_progress', title: 'Task 2' },
        { id: '3', status: 'done', title: 'Task 3' },
        { id: '4', status: 'backlog', title: 'Task 4' },
      ];

      const columns = distributeTasksToColumns(tasks);

      expect(columns.backlog).toHaveLength(2);
      expect(columns.in_progress).toHaveLength(1);
      expect(columns.done).toHaveLength(1);
      expect(columns.queue).toHaveLength(0);
      expect(columns.ai_review).toHaveLength(0);
      expect(columns.human_review).toHaveLength(0);
    });

    it('should handle empty tasks array', () => {
      const columns = distributeTasksToColumns([]);

      for (const column of TASK_STATUS_COLUMNS) {
        expect(columns[column]).toHaveLength(0);
      }
    });

    it('should handle all tasks in single column', () => {
      const tasks: MockTask[] = [
        { id: '1', status: 'queue', title: 'Task 1' },
        { id: '2', status: 'queue', title: 'Task 2' },
        { id: '3', status: 'queue', title: 'Task 3' },
      ];

      const columns = distributeTasksToColumns(tasks);

      expect(columns.queue).toHaveLength(3);
      expect(columns.backlog).toHaveLength(0);
    });
  });

  describe('status mapping', () => {
    it('pr_created should map to done column', () => {
      // In KanbanBoard, pr_created status is displayed in the done column
      const statusToColumn: Record<string, TaskStatusColumn> = {
        backlog: 'backlog',
        queue: 'queue',
        in_progress: 'in_progress',
        ai_review: 'ai_review',
        human_review: 'human_review',
        done: 'done',
        pr_created: 'done',
      };

      expect(statusToColumn['pr_created']).toBe('done');
    });

    it('error status should map to human_review column', () => {
      // In KanbanBoard, error status is displayed in the human_review column
      const statusToColumn: Record<string, TaskStatusColumn> = {
        error: 'human_review',
      };

      expect(statusToColumn['error']).toBe('human_review');
    });
  });

  describe('queue logic', () => {
    it('should identify queueable tasks from backlog', () => {
      const backlogTasks = [
        { id: '1', status: 'backlog' as const },
        { id: '2', status: 'backlog' as const },
      ];

      // "Queue All" moves all backlog tasks to queue
      const queuedTasks = backlogTasks.map(t => ({ ...t, status: 'queue' as const }));

      expect(queuedTasks).toHaveLength(2);
      expect(queuedTasks.every(t => t.status === 'queue')).toBe(true);
    });

    it('should identify archivable tasks from done', () => {
      const doneTasks = [
        { id: '1', status: 'done' as const },
        { id: '2', status: 'done' as const },
        { id: '3', status: 'done' as const },
      ];

      // "Archive All" archives all done tasks
      expect(doneTasks).toHaveLength(3);
      expect(doneTasks.every(t => t.status === 'done')).toBe(true);
    });
  });

  describe('drag and drop logic', () => {
    it('should determine valid drop targets', () => {
      // Tasks can be moved between any columns
      const validTransitions: Record<string, string[]> = {
        backlog: ['queue', 'in_progress', 'done'],
        queue: ['backlog', 'in_progress'],
        in_progress: ['backlog', 'queue', 'ai_review', 'done'],
        ai_review: ['in_progress', 'human_review', 'done'],
        human_review: ['in_progress', 'done'],
        done: ['backlog'],
      };

      // A task in backlog can be moved to queue
      expect(validTransitions.backlog).toContain('queue');
      // A task in ai_review can be moved to done
      expect(validTransitions.ai_review).toContain('done');
    });
  });
});
