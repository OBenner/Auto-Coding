/**
 * TaskDetail Page
 *
 * Displays detailed information about a single task/spec.
 * Shows spec content, progress, and subtasks.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, RefreshCw, AlertCircle, CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import { apiClient } from '../api/client';
import type { TaskDetail as TaskDetailType } from '../api/types';

interface TaskDetailProps {
  taskId: string;
  onBack: () => void;
}

export function TaskDetail({ taskId, onBack }: TaskDetailProps) {
  const { t } = useTranslation(['common']);
  const [task, setTask] = useState<TaskDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  /**
   * Fetch task details from the API
   */
  const fetchTaskDetail = useCallback(async (showRefreshIndicator = false) => {
    try {
      if (showRefreshIndicator) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      const taskDetail = await apiClient.getTask(taskId);
      setTask(taskDetail);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load task details';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [taskId]);

  // Initial load
  useEffect(() => {
    fetchTaskDetail();
  }, [fetchTaskDetail]);

  // Handle refresh button click
  const handleRefresh = useCallback(() => {
    fetchTaskDetail(true);
  }, [fetchTaskDetail]);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">{t('common:loading')}</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !task) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {t('common:error')}
          </h2>
          <p className="text-gray-600 mb-4">{error || 'Task not found'}</p>
          <div className="flex gap-2 justify-center">
            <Button onClick={onBack} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Tasks
            </Button>
            <Button onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Task detail view
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button onClick={onBack} variant="outline" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{task.name}</h1>
              <p className="text-sm text-gray-600 mt-1">
                Spec #{task.number}
              </p>
            </div>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            variant="outline"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <div className="grid gap-6">
          {/* Status and Progress Card */}
          <Card>
            <CardContent className="space-y-4 pt-6">
              <h3 className="text-lg font-semibold mb-4">Status & Progress</h3>
              <div className="flex items-center gap-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Status</p>
                  <Badge variant="outline" className="text-sm">
                    {task.status}
                  </Badge>
                </div>
                {task.has_build && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Build</p>
                    <Badge variant="outline" className="text-sm bg-green-50 text-green-700 border-green-200">
                      Active
                    </Badge>
                  </div>
                )}
              </div>

              <Separator />

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Overall Progress</span>
                  <span className="font-semibold">
                    {task.progress.percentage}%
                  </span>
                </div>
                <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all duration-300"
                    style={{ width: `${task.progress.percentage}%` }}
                  />
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs text-gray-600">
                  <div className="flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3 text-green-600" />
                    <span>{task.progress.completed} completed</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 text-blue-600" />
                    <span>{task.progress.in_progress} in progress</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Circle className="h-3 w-3 text-gray-400" />
                    <span>{task.progress.pending} pending</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3 text-red-600" />
                    <span>{task.progress.failed} failed</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Spec Content Card */}
          {task.spec_content && (
            <Card>
              <CardContent className="pt-6">
                <h3 className="text-lg font-semibold mb-4">Specification</h3>
                <ScrollArea className="h-[400px] w-full rounded-md border p-4">
                  <pre className="text-sm font-mono whitespace-pre-wrap">
                    {task.spec_content}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          )}

          {/* Folder Location Card */}
          <Card>
            <CardContent className="pt-6">
              <h3 className="text-lg font-semibold mb-4">Location</h3>
              <div className="flex items-center gap-2">
                <code className="text-sm bg-gray-100 px-3 py-1 rounded">
                  {task.folder}
                </code>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
