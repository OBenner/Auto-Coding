/**
 * Dashboard Page
 *
 * Displays an overview of recent specs and tasks.
 * Main landing page for the web frontend.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, AlertCircle, Plus, Activity, FileText, CheckCircle, Clock } from 'lucide-react';
import { useSpecStore } from '../store/spec-store';
import { useTaskStore } from '../store/task-store';
import { TaskCard } from '../components/TaskCard';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import { cn, formatRelativeTime } from '../lib/utils';
import type { Task } from '../shared/types';
import type { TaskSummary, SpecSummary } from '../api/types';

/**
 * Convert API TaskSummary to frontend Task type
 */
function convertTaskSummary(summary: TaskSummary): Task {
  return {
    id: summary.number,
    specId: summary.number,
    title: summary.name,
    description: `Status: ${summary.status}`,
    status: 'backlog',
    subtasks: [],
    createdAt: new Date(),
    updatedAt: new Date(),
    metadata: {}
  };
}

export function Dashboard() {
  const { t } = useTranslation(['common', 'navigation']);
  const navigate = useNavigate();

  // Stores
  const { specs, isLoading: isLoadingSpecs, error: specsError, fetchSpecs } = useSpecStore();
  const { tasks, isLoading: isLoadingTasks, error: tasksError, fetchTasks } = useTaskStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  /**
   * Initial data load
   */
  useEffect(() => {
    fetchSpecs();
    fetchTasks();
  }, [fetchSpecs, fetchTasks]);

  /**
   * Refresh all data
   */
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([fetchSpecs(), fetchTasks()]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchSpecs, fetchTasks]);

  /**
   * Navigate to task detail
   */
  const handleTaskClick = useCallback((task: Task) => {
    navigate(`/tasks/${task.id}`);
  }, [navigate]);

  /**
   * Navigate to create spec page
   */
  const handleCreateSpec = useCallback(() => {
    navigate('/create');
  }, [navigate]);

  /**
   * Navigate to tasks page
   */
  const handleViewAllTasks = useCallback(() => {
    navigate('/tasks');
  }, [navigate]);

  // Get recent items (last 5)
  const recentSpecs = specs.slice(0, 5);
  const recentTasks = tasks.slice(0, 5);

  // Calculate stats
  const totalSpecs = specs.length;
  const totalTasks = tasks.length;
  const runningTasks = tasks.filter(t => t.status === 'running').length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;

  // Loading state
  if (isLoadingSpecs && isLoadingTasks) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">{t('common:labels.loading')}</p>
        </div>
      </div>
    );
  }

  // Error state
  const hasError = specsError || tasksError;
  if (hasError && specs.length === 0 && tasks.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {t('common:labels.error')}
          </h2>
          <p className="text-gray-600 mb-4">{specsError || tasksError}</p>
          <Button onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('common:buttons.retry')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {t('common:dashboard')}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              {t('navigation:messages.welcomeBack')}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleCreateSpec}
              className="flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              {t('navigation:items.createSpec')}
            </Button>
            <Button
              onClick={handleRefresh}
              disabled={isRefreshing}
              variant="outline"
            >
              <RefreshCw className={cn('h-4 w-4 mr-2', isRefreshing && 'animate-spin')} />
              {t('common:buttons.refresh')}
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    {t('common:specs')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {totalSpecs}
                  </p>
                </div>
                <FileText className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    {t('common:tasks')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {totalTasks}
                  </p>
                </div>
                <Activity className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    Running
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {runningTasks}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    Completed
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {completedTasks}
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Tasks */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
              <CardTitle className="text-lg font-semibold">
                Recent {t('common:tasks')}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleViewAllTasks}
              >
                {t('common:actions.view')} All
              </Button>
            </CardHeader>
            <CardContent>
              {recentTasks.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">
                    No tasks yet. Create a spec to get started.
                  </p>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {recentTasks.map((taskSummary) => {
                      const task = convertTaskSummary(taskSummary);
                      return (
                        <TaskCard
                          key={task.id}
                          task={task}
                          onClick={() => handleTaskClick(task)}
                        />
                      );
                    })}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          {/* Recent Specs */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
              <CardTitle className="text-lg font-semibold">
                Recent {t('common:specs')}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCreateSpec}
              >
                {t('common:buttons.create')} New
              </Button>
            </CardHeader>
            <CardContent>
              {recentSpecs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500 mb-4">
                    No specs yet. Create your first spec to begin.
                  </p>
                  <Button onClick={handleCreateSpec}>
                    <Plus className="h-4 w-4 mr-2" />
                    {t('navigation:items.createSpec')}
                  </Button>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {recentSpecs.map((spec) => (
                      <SpecCard key={spec.number} spec={spec} />
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

/**
 * SpecCard Component
 * Displays a single spec summary card
 */
interface SpecCardProps {
  spec: SpecSummary;
}

function SpecCard({ spec }: SpecCardProps) {
  const { t } = useTranslation(['common']);

  return (
    <Card className="cursor-pointer transition-all hover:shadow-md">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <h3 className="font-semibold text-sm truncate">{spec.name}</h3>
          </div>
          <Badge variant="outline" className="text-xs shrink-0">
            #{spec.number}
          </Badge>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2 mb-2">
          <Badge
            variant="outline"
            className={cn(
              'text-xs',
              spec.status === 'completed' && 'bg-green-50 text-green-700 border-green-200',
              spec.status === 'running' && 'bg-blue-50 text-blue-700 border-blue-200',
              spec.status === 'pending' && 'bg-gray-50 text-gray-700 border-gray-200',
              spec.status === 'failed' && 'bg-red-50 text-red-700 border-red-200'
            )}
          >
            {spec.status}
          </Badge>
        </div>

        {/* Footer: Updated Time */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{t('common:labels.updatedRecently')}</span>
        </div>
      </CardContent>
    </Card>
  );
}
