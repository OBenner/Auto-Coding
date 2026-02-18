/**
 * Scheduler API
 * =============
 *
 * Preload API for scheduler operations.
 * Exposes scheduler functionality to the renderer process.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  ScheduledBuild,
  SchedulePriority,
  SchedulerStatus,
  ScheduleBuildOptions,
  QueueItem
} from '../../shared/types';

export interface SchedulerAPI {
  /**
   * Schedule a build for a task
   */
  scheduleBuild: (
    taskId: string,
    scheduledTime: string | null,
    priority: SchedulePriority,
    dependencies?: string[]
  ) => Promise<IPCResult<{ buildId: string }>>;

  /**
   * Get scheduler status and queue
   */
  getStatus: (projectId: string) => Promise<IPCResult<SchedulerStatus>>;

  /**
   * Cancel a scheduled build
   */
  cancelBuild: (buildId: string, projectId: string) => Promise<IPCResult>;

  /**
   * Start the scheduler service
   */
  start: (projectId: string) => Promise<IPCResult>;

  /**
   * Stop the scheduler service
   */
  stop: (projectId: string) => Promise<IPCResult>;

  /**
   * Get all scheduled builds for a project
   */
  getBuilds: (projectId: string) => Promise<IPCResult<ScheduledBuild[]>>;

  /**
   * Listen for build scheduled events
   */
  onBuildScheduled: (callback: (projectId: string, build: ScheduledBuild) => void) => () => void;

  /**
   * Listen for build cancelled events
   */
  onBuildCancelled: (callback: (projectId: string, buildId: string) => void) => () => void;

  /**
   * Listen for scheduler status changes
   */
  onStatusChanged: (callback: (projectId: string, running: boolean) => void) => () => void;

  /**
   * Listen for build progress updates
   */
  onBuildProgress: (
    callback: (projectId: string, buildId: string, progress: number) => void
  ) => () => void;

  /**
   * Listen for build completion
   */
  onBuildComplete: (
    callback: (projectId: string, build: ScheduledBuild) => void
  ) => () => void;

  /**
   * Listen for build failures
   */
  onBuildFailed: (
    callback: (projectId: string, buildId: string, error: string) => void
  ) => () => void;
}

export const createSchedulerAPI = (): SchedulerAPI => ({
  scheduleBuild: (
    taskId: string,
    scheduledTime: string | null,
    priority: SchedulePriority,
    dependencies: string[] = []
  ): Promise<IPCResult<{ buildId: string }>> =>
    ipcRenderer.invoke(
      IPC_CHANNELS.SCHEDULER_SCHEDULE_BUILD,
      taskId,
      scheduledTime,
      priority,
      dependencies
    ),

  getStatus: (projectId: string): Promise<IPCResult<SchedulerStatus>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SCHEDULER_GET_STATUS, projectId),

  cancelBuild: (buildId: string, projectId: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.SCHEDULER_CANCEL_BUILD, buildId, projectId),

  start: (projectId: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.SCHEDULER_START, projectId),

  stop: (projectId: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.SCHEDULER_STOP, projectId),

  getBuilds: (projectId: string): Promise<IPCResult<ScheduledBuild[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SCHEDULER_GET_BUILDS, projectId),

  onBuildScheduled: (
    callback: (projectId: string, build: ScheduledBuild) => void
  ): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      projectId: string,
      build: ScheduledBuild
    ): void => {
      callback(projectId, build);
    };
    ipcRenderer.on(IPC_CHANNELS.SCHEDULER_BUILD_SCHEDULED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SCHEDULER_BUILD_SCHEDULED, handler);
    };
  },

  onBuildCancelled: (
    callback: (projectId: string, buildId: string) => void
  ): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      projectId: string,
      buildId: string
    ): void => {
      callback(projectId, buildId);
    };
    ipcRenderer.on(IPC_CHANNELS.SCHEDULER_BUILD_CANCELLED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SCHEDULER_BUILD_CANCELLED, handler);
    };
  },

  onStatusChanged: (
    callback: (projectId: string, running: boolean) => void
  ): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      projectId: string,
      running: boolean
    ): void => {
      callback(projectId, running);
    };
    ipcRenderer.on(IPC_CHANNELS.SCHEDULER_STATUS_CHANGED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SCHEDULER_STATUS_CHANGED, handler);
    };
  },

  onBuildProgress: (
    callback: (projectId: string, buildId: string, progress: number) => void
  ): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      projectId: string,
      buildId: string,
      progress: number
    ): void => {
      callback(projectId, buildId, progress);
    };
    ipcRenderer.on(IPC_CHANNELS.SCHEDULER_BUILD_PROGRESS, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SCHEDULER_BUILD_PROGRESS, handler);
    };
  },

  onBuildComplete: (
    callback: (projectId: string, build: ScheduledBuild) => void
  ): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      projectId: string,
      build: ScheduledBuild
    ): void => {
      callback(projectId, build);
    };
    ipcRenderer.on(IPC_CHANNELS.SCHEDULER_BUILD_COMPLETE, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SCHEDULER_BUILD_COMPLETE, handler);
    };
  },

  onBuildFailed: (
    callback: (projectId: string, buildId: string, error: string) => void
  ): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      projectId: string,
      buildId: string,
      error: string
    ): void => {
      callback(projectId, buildId, error);
    };
    ipcRenderer.on(IPC_CHANNELS.SCHEDULER_BUILD_FAILED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SCHEDULER_BUILD_FAILED, handler);
    };
  }
});
