/**
 * Mock implementation for task operations
 */

import type { TaskRecoveryOptions } from '../../../shared/types';
import { mockTasks } from './mock-data';

export const taskMock = {
  getTasks: async (projectId: string) => ({
    success: true,
    data: mockTasks.filter(t => t.projectId === projectId)
  }),

  createTask: async (projectId: string, title: string, description: string) => ({
    success: true,
    data: {
      id: `task-${Date.now()}`,
      projectId,
      specId: `00${mockTasks.length + 1}-new-task`,
      title,
      description,
      status: 'backlog' as const,
      subtasks: [],
      logs: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }
  }),

  createTaskFromTemplate: async (projectId: string, templateName: string, _parameters: Record<string, unknown>) => ({
    success: true,
    data: {
      id: `task-${Date.now()}`,
      projectId,
      specId: `00${mockTasks.length + 1}-${templateName}`,
      title: `Task from ${templateName}`,
      description: `Task created from template: ${templateName}`,
      status: 'backlog' as const,
      subtasks: [],
      logs: [],
      metadata: {
        sourceType: 'template' as const,
        templateName
      },
      createdAt: new Date(),
      updatedAt: new Date()
    }
  }),

  deleteTask: async () => ({ success: true }),

  updateTask: async (_taskId: string, updates: { title?: string; description?: string }) => ({
    success: true,
    data: {
      id: _taskId,
      projectId: 'mock-project-1',
      specId: '001-updated',
      title: updates.title || 'Updated Task',
      description: updates.description || 'Updated description',
      status: 'backlog' as const,
      subtasks: [],
      logs: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }
  }),

  startTask: () => {
    console.warn('[Browser Mock] startTask called');
  },

  stopTask: () => {
    console.warn('[Browser Mock] stopTask called');
  },

  submitReview: async () => ({ success: true }),

  // Task archive operations
  archiveTasks: async () => ({ success: true, data: true }),
  unarchiveTasks: async () => ({ success: true, data: true }),

  // Task export operation
  exportTask: async (projectId: string, taskId: string) => {
    console.log('[Browser Mock] exportTask:', projectId, taskId);
    return { success: true, data: '/mock/path/to/spec.zip' };
  },

  // Task status operations
  updateTaskStatus: async (_taskId: string, _status: string, _options?: { forceCleanup?: boolean }) => ({ success: true }),

  recoverStuckTask: async (taskId: string, options?: TaskRecoveryOptions) => ({
    success: true,
    data: {
      taskId,
      recovered: true,
      newStatus: options?.targetStatus || 'backlog',
      message: '[Browser Mock] Task recovered successfully'
    }
  }),

  checkTaskRunning: async () => ({ success: true, data: false }),

  // Batch operations
  batchRunQA: async (taskId: string) => ({
    success: true,
    data: {
      success: true,
      issues: []
    },
    error: undefined
  }),

  // Task logs operations
  getTaskLogs: async () => ({
    success: true,
    data: null
  }),

  watchTaskLogs: async () => ({ success: true }),

  unwatchTaskLogs: async () => ({ success: true }),

  // Background task operations (long-running commands)
  backgroundTaskStart: async (_command: string, _workingDir: string, _timeout?: number) => ({
    success: true,
    data: { taskId: `bg-task-${Date.now()}` }
  }),

  backgroundTaskCancel: async () => ({
    success: true,
    data: { cancelled: true }
  }),

  backgroundTaskGetStatus: async (taskId: string) => ({
    success: true,
    data: {
      id: taskId,
      command: 'echo "Mock command"',
      workingDir: '/mock/path',
      status: 'completed' as const,
      createdAt: new Date().toISOString(),
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      timeout: 14400,
      output: 'Mock output\n',
      error: null,
      exitCode: 0,
      pid: null
    }
  }),

  backgroundTaskGetOutput: async () => ({
    success: true,
    data: { output: 'Mock output\n' }
  }),

  backgroundTaskListRunning: async () => ({
    success: true,
    data: []
  }),

  backgroundTaskListByStatus: async () => ({
    success: true,
    data: []
  }),

  // Task spec file reading (for task overview display)
  getImplementationPlan: async () => ({
    success: true,
    data: null
  }),

  getGenericEditArtifactManifest: async () => ({
    success: true,
    data: null
  }),

  getQAReport: async () => ({
    success: true,
    data: null
  }),

  getQAEscalation: async () => ({
    success: true,
    data: null
  }),

  getVerificationReport: async () => ({
    success: true,
    data: null
  }),

  // Event Listeners (no-op in browser)
  onTaskProgress: () => () => {},
  onTaskError: () => () => {},
  onTaskLog: () => () => {},
  onTaskStatusChange: () => () => {},
  onTaskExecutionProgress: () => () => {},
  onTaskLogsChanged: () => () => {},
  onTaskLogsStream: () => () => {},
  onBackgroundTaskProgress: () => () => {},
  onBackgroundTaskComplete: () => () => {},
  onBackgroundTaskError: () => () => {}
};
