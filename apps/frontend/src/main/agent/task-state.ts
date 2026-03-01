/**
 * Background task tracking for long-running commands
 */

/**
 * Status of a background task
 */
export type BackgroundTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

/**
 * Background task metadata
 */
export interface BackgroundTask {
  id: string;
  command: string;
  workingDir: string;
  status: BackgroundTaskStatus;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  timeout: number;
  output: string;
  error: string | null;
  exitCode: number | null;
  pid: number | null;
  memoryStats?: {
    percent: number;
    availableMb: number;
    totalMb: number;
    usedMb: number;
  };
}

/**
 * State tracking for background tasks
 */
export class BackgroundTaskState {
  private tasks: Map<string, BackgroundTask> = new Map();
  private taskCounter: number = 0;

  /**
   * Generate a unique task counter ID
   */
  generateTaskCounter(): number {
    return ++this.taskCounter;
  }

  /**
   * Add a task to the tracking map
   */
  addTask(taskId: string, task: BackgroundTask): void {
    this.tasks.set(taskId, task);
  }

  /**
   * Get a task by ID
   */
  getTask(taskId: string): BackgroundTask | undefined {
    return this.tasks.get(taskId);
  }

  /**
   * Update task data
   */
  updateTask(taskId: string, updates: Partial<BackgroundTask>): boolean {
    const task = this.tasks.get(taskId);
    if (!task) {
      return false;
    }

    const updatedTask = { ...task, ...updates };
    this.tasks.set(taskId, updatedTask);
    return true;
  }

  /**
   * Remove a task from tracking
   */
  deleteTask(taskId: string): boolean {
    return this.tasks.delete(taskId);
  }

  /**
   * Check if a task exists
   */
  hasTask(taskId: string): boolean {
    return this.tasks.has(taskId);
  }

  /**
   * Get all task IDs
   */
  getAllTaskIds(): string[] {
    return Array.from(this.tasks.keys());
  }

  /**
   * Get all tasks
   */
  getAllTasks(): Map<string, BackgroundTask> {
    return this.tasks;
  }

  /**
   * Get tasks by status
   */
  getTasksByStatus(status: BackgroundTaskStatus): BackgroundTask[] {
    return Array.from(this.tasks.values()).filter((task) => task.status === status);
  }

  /**
   * Get running tasks
   */
  getRunningTasks(): BackgroundTask[] {
    return this.getTasksByStatus('running');
  }

  /**
   * Get completed tasks
   */
  getCompletedTasks(): BackgroundTask[] {
    return this.getTasksByStatus('completed');
  }

  /**
   * Get failed tasks
   */
  getFailedTasks(): BackgroundTask[] {
    return this.getTasksByStatus('failed');
  }

  /**
   * Get cancelled tasks
   */
  getCancelledTasks(): BackgroundTask[] {
    return this.getTasksByStatus('cancelled');
  }

  /**
   * Get count of tasks by status
   */
  getTaskCountByStatus(): Record<BackgroundTaskStatus, number> {
    const counts: Record<BackgroundTaskStatus, number> = {
      pending: 0,
      running: 0,
      completed: 0,
      failed: 0,
      cancelled: 0
    };

    for (const task of this.tasks.values()) {
      counts[task.status]++;
    }

    return counts;
  }

  /**
   * Clear all state (for testing or cleanup)
   */
  clear(): void {
    this.tasks.clear();
  }

  /**
   * Get task count
   */
  getTaskCount(): number {
    return this.tasks.size;
  }

  /**
   * Check if there are any running tasks
   */
  hasRunningTasks(): boolean {
    return this.getRunningTasks().length > 0;
  }

  /**
   * Get oldest running task
   */
  getOldestRunningTask(): BackgroundTask | undefined {
    const runningTasks = this.getRunningTasks();
    if (runningTasks.length === 0) {
      return undefined;
    }

    return runningTasks.reduce((oldest, task) => {
      const oldestTime = new Date(oldest.startedAt || oldest.createdAt).getTime();
      const taskTime = new Date(task.startedAt || task.createdAt).getTime();
      return taskTime < oldestTime ? task : oldest;
    }, runningTasks[0]);
  }
}
