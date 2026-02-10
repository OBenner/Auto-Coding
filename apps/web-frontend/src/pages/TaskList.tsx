/**
 * TaskList Page
 *
 * Displays all tasks from the backend in a grid layout.
 * Allows navigation to individual task details.
 *
 * Integrated with task store for state management.
 */

import { useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { TaskCard } from '../components/TaskCard';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { useTaskStore } from '../store/task-store';
import type { Task } from '../shared/types';
import type { TaskSummary } from '../api/types';

interface TaskListProps {
  onTaskClick: (taskId: string) => void;
}

export function TaskList({ onTaskClick }: TaskListProps) {
  const { t } = useTranslation(['common', 'tasks', 'navigation', 'buttons']);

  // Get state and actions from task store
  const {
    tasks,
    isLoading,
    error,
    fetchTasks,
    refreshTasks
  } = useTaskStore();

  /**
   * Convert API TaskSummary to frontend Task type
   * Maps backend API response to frontend Task type for TaskCard component
   */
  const convertTaskSummary = useCallback((summary: TaskSummary): Task => {
    return {
      id: summary.number,
      specId: summary.number,
      title: summary.name,
      description: `${t('labels.status')}: ${summary.status}`,
      status: summary.status as any, // Will be refined when backend provides proper status enum
      subtasks: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata: {}
    };
  }, [t]);

  // Convert tasks from store to Task type for TaskCard
  const convertedTasks = useMemo(() => {
    return tasks.map(convertTaskSummary);
  }, [tasks, convertTaskSummary]);

  /**
   * Initial load of tasks
   */
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  /**
   * Handle refresh button click
   */
  const handleRefresh = useCallback(async () => {
    await refreshTasks();
  }, [refreshTasks]);

  /**
   * Handle task card click
   */
  const handleTaskClick = useCallback((task: Task) => {
    onTaskClick(task.id);
  }, [onTaskClick]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">{t('buttons.loading')}</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px] p-4">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">
            {t('labels.error')}
          </h2>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('buttons.retry')}
          </Button>
        </div>
      </div>
    );
  }

  // Empty state
  if (tasks.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-lg text-muted-foreground mb-2">
            {t('empty.title')}
          </p>
          <p className="text-sm text-muted-foreground">
            {t('empty.description')}
          </p>
        </div>
      </div>
    );
  }

  // Task list view
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            {t('tasks')}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {tasks.length} {tasks.length === 1 ? 'task' : 'tasks'} total
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={isLoading}
          variant="outline"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          {t('buttons.refresh')}
        </Button>
      </div>

      {/* Task Grid */}
      <ScrollArea className="h-[calc(100vh-250px)]">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
          {convertedTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => handleTaskClick(task)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
