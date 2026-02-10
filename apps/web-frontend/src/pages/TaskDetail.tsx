/**
 * TaskDetail Page
 *
 * Displays detailed information about a single task/spec.
 * Shows spec content, progress, and subtasks.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { BuildProgress } from '../components/BuildProgress';
import { apiClient } from '../api/client';
import type { TaskDetail as TaskDetailType } from '../api/types';

interface TaskDetailProps {
  taskId: string;
  onBack: () => void;
}

export function TaskDetail({ taskId, onBack }: TaskDetailProps) {
  const { t } = useTranslation(['common', 'tasks']);
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
              {t('common:buttons.back')}
            </Button>
            <Button onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              {t('common:buttons.retry')}
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
            {t('common:buttons.refresh')}
          </Button>
        </div>

        <div className="grid gap-6">
          {/* Status Card */}
          <Card>
            <CardContent className="space-y-4 pt-6">
              <h3 className="text-lg font-semibold mb-4">{t('common:labels.status')}</h3>
              <div className="flex items-center gap-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">{t('tasks:labels.status')}</p>
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
            </CardContent>
          </Card>

          {/* Build Progress Card */}
          <BuildProgress
            taskId={task.number}
            progress={task.progress}
          />

          {/* Spec Content Card */}
          {task.spec_content && (
            <Card>
              <CardContent className="pt-6">
                <h3 className="text-lg font-semibold mb-4">{t('common:specs')}</h3>
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
              <h3 className="text-lg font-semibold mb-4">{t('common:labels.location', 'Location')}</h3>
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
