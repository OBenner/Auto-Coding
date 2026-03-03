/**
 * BuildProgress Component
 *
 * Displays real-time build progress and logs for a task.
 * Shows progress bar, status indicators, and build logs.
 *
 * Follows patterns from desktop app components with web-specific adaptations.
 */

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircle2,
  Loader2,
  Circle,
  AlertCircle,
  ScrollText,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { cn } from '../lib/utils';
import { useTaskStore } from '../store/task-store';
import type { TaskProgressDetail } from '../api/types';

interface BuildProgressProps {
  taskId: string;
  progress: TaskProgressDetail;
  currentPhase?: string;
  message?: string;
}

/**
 * BuildProgress component for monitoring task execution
 *
 * Features:
 * - Visual progress bar with percentage
 * - Status indicators (completed, in progress, pending, failed)
 * - Expandable build logs section
 * - Auto-scrolling log viewer
 * - Current phase display
 */
export function BuildProgress({
  taskId,
  progress,
  currentPhase,
  message
}: BuildProgressProps) {
  const { t } = useTranslation(['tasks', 'common']);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [isLogsExpanded, setIsLogsExpanded] = useState(true);

  // Get logs from task store
  const logs = useTaskStore((state) => state.getTaskLogs(taskId));

  // Auto-scroll to bottom of logs when new logs arrive
  useEffect(() => {
    if (isLogsExpanded && logs.length > 0 && scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [logs, isLogsExpanded]);

  /**
   * Format phase name for display
   */
  const formatPhase = (phase: string): string => {
    const phaseKey = `tasks:execution.phases.${phase.toLowerCase()}`;
    return t(phaseKey, phase);
  };

  /**
   * Get color class for progress bar based on status
   */
  const getProgressColor = () => {
    if (progress.failed > 0) return 'bg-red-600';
    if (progress.completed === progress.total) return 'bg-green-600';
    return 'bg-blue-600';
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-blue-600" />
            <CardTitle className="text-lg">
              {t('tasks:details.progress')}
            </CardTitle>
          </div>
          <Badge
            variant="outline"
            className={cn(
              'text-sm',
              progress.completed === progress.total && 'bg-green-50 text-green-700 border-green-200'
            )}
          >
            {progress.percentage}%
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Current Phase */}
        {currentPhase && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">
              {t('tasks:execution.labels.currentPhase')}
            </span>
            <Badge variant="secondary" className="text-sm">
              {formatPhase(currentPhase)}
            </Badge>
          </div>
        )}

        {/* Progress Message */}
        {message && (
          <p className="text-sm text-gray-700 italic">{message}</p>
        )}

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={cn('h-full transition-all duration-300', getProgressColor())}
              style={{ width: `${progress.percentage}%` }}
            />
          </div>

          {/* Progress Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
              <span className="text-gray-600">
                {t('tasks:execution.phases.complete')}: {progress.completed}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 text-blue-600 flex-shrink-0 animate-spin" />
              <span className="text-gray-600">
                {t('common:labels.inProgress')}: {progress.in_progress}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Circle className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <span className="text-gray-600">
                {t('tasks:status.pending')}: {progress.pending}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
              <span className="text-gray-600">
                {t('common:labels.failed')}: {progress.failed}
              </span>
            </div>
          </div>
        </div>

        {/* Build Logs Section */}
        <Separator />

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold">{t('tasks:logs.title')}</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsLogsExpanded(!isLogsExpanded)}
              className="h-8 px-2"
            >
              {isLogsExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>

          {isLogsExpanded && (
            <ScrollArea
              ref={scrollAreaRef}
              className="h-[300px] w-full rounded-md border bg-gray-950 p-4"
            >
              {logs.length > 0 ? (
                <div className="space-y-1">
                  {logs.map((log, index) => (
                    <div
                      key={index}
                      className="text-xs font-mono whitespace-pre-wrap text-green-400"
                    >
                      {log}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                  {t('tasks:logs.emptyHint')}
                </div>
              )}
            </ScrollArea>
          )}

          {logs.length === 0 && (
            <p className="text-xs text-gray-500 text-center">
              {t('tasks:logs.emptyHint')}
            </p>
          )}
        </div>

        {/* Task Count Summary */}
        <div className="text-xs text-gray-600 text-center">
          {t('tasks:labels.progress')}: {progress.completed} / {progress.total} {t('common:labels.tasks')}
        </div>
      </CardContent>
    </Card>
  );
}
