/**
 * QueueView - Real-time queue view of active builds
 *
 * Displays builds currently in the queue (pending, queued, running, retrying)
 * with status tracking, priority ordering, and dependency information.
 *
 * Features:
 * - Shows active builds grouped by status
 * - Displays queue position for pending/queued builds
 * - Shows duration for running builds
 * - Indicates blocking/blocked relationships
 * - Real-time status updates
 * - Cancel action for pending/queued builds
 *
 * @example
 * ```tsx
 * <QueueView
 *   projectId={project.id}
 *   builds={builds}
 *   isLoading={false}
 *   onRefresh={() => refetch()}
 *   onCancelBuild={(buildId) => cancelBuild(buildId)}
 * />
 * ```
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ListOrdered,
  Clock,
  Loader2,
  AlertCircle,
  X,
  Play,
  Pause,
  FileText
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Progress } from '../ui/progress';
import type { ScheduledBuild, BuildStatus, SchedulePriority } from '../../../shared/types/scheduler';

/**
 * Props for the QueueView component
 */
interface QueueViewProps {
  /** Project ID for the builds */
  projectId: string;
  /** Scheduled builds to display */
  builds: ScheduledBuild[];
  /** Whether data is loading */
  isLoading?: boolean;
  /** Callback when user requests refresh */
  onRefresh?: () => void;
  /** Callback when user cancels a build */
  onCancelBuild?: (buildId: string) => void;
  /** Callback when user views build logs */
  onViewLogs?: (buildId: string) => void;
}

/**
 * Grouped builds by status
 */
interface GroupedBuilds {
  active: ScheduledBuild[];  // running or retrying
  waiting: ScheduledBuild[];  // pending or queued
}

/**
 * Get status badge color
 */
const getStatusColor = (status: BuildStatus): string => {
  switch (status) {
    case 'pending':
      return 'bg-yellow-500/10 text-yellow-500 dark:text-yellow-400 border-yellow-500/30';
    case 'queued':
      return 'bg-blue-500/10 text-blue-500 dark:text-blue-400 border-blue-500/30';
    case 'running':
      return 'bg-green-500/10 text-green-500 dark:text-green-400 border-green-500/30';
    case 'completed':
      return 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 border-emerald-500/30';
    case 'failed':
      return 'bg-red-500/10 text-red-500 dark:text-red-400 border-red-500/30';
    case 'cancelled':
      return 'bg-gray-500/10 text-gray-500 dark:text-gray-400 border-gray-500/30';
    case 'retrying':
      return 'bg-orange-500/10 text-orange-500 dark:text-orange-400 border-orange-500/30';
    default:
      return 'bg-gray-500/10 text-gray-500 dark:text-gray-400 border-gray-500/30';
  }
};

/**
 * Get priority badge color
 */
const getPriorityColor = (priority: SchedulePriority): string => {
  switch (priority) {
    case 'critical':
      return 'bg-red-500/10 text-red-500 dark:text-red-400 border-red-500/30';
    case 'high':
      return 'bg-orange-500/10 text-orange-500 dark:text-orange-400 border-orange-500/30';
    case 'normal':
      return 'bg-blue-500/10 text-blue-500 dark:text-blue-400 border-blue-500/30';
    case 'low':
      return 'bg-gray-500/10 text-gray-500 dark:text-gray-400 border-gray-500/30';
    case 'background':
      return 'bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/30';
    default:
      return 'bg-gray-500/10 text-gray-500 dark:text-gray-400 border-gray-500/30';
  }
};

/**
 * Format duration for running builds
 */
const formatDuration = (startedAt: string | null): { minutes: number; seconds: number } => {
  if (!startedAt) return { minutes: 0, seconds: 0 };

  const start = new Date(startedAt);
  const now = new Date();
  const diffMs = now.getTime() - start.getTime();
  const totalSeconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return { minutes, seconds };
};

/**
 * Priority order for sorting
 */
const priorityOrder: Record<SchedulePriority, number> = {
  critical: 1,
  high: 2,
  normal: 3,
  low: 4,
  background: 5
};

/**
 * Group builds by active/waiting status
 */
const groupBuildsByStatus = (builds: ScheduledBuild[]): GroupedBuilds => {
  const activeStatuses: BuildStatus[] = ['running', 'retrying'];
  const waitingStatuses: BuildStatus[] = ['pending', 'queued'];

  const grouped: GroupedBuilds = {
    active: [],
    waiting: []
  };

  builds.forEach((build) => {
    if (activeStatuses.includes(build.status)) {
      grouped.active.push(build);
    } else if (waitingStatuses.includes(build.status)) {
      grouped.waiting.push(build);
    }
  });

  // Sort by priority within each group
  const sortByPriority = (a: ScheduledBuild, b: ScheduledBuild) => {
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  };

  grouped.active.sort(sortByPriority);
  grouped.waiting.sort(sortByPriority);

  return grouped;
};

export function QueueView({
  projectId,
  builds,
  isLoading = false,
  onRefresh,
  onCancelBuild,
  onViewLogs
}: QueueViewProps) {
  const { t } = useTranslation(['scheduler', 'common']);

  const [cancellingBuilds, setCancellingBuilds] = useState<Set<string>>(new Set());
  const [buildDurations, setBuildDurations] = useState<Map<string, { minutes: number; seconds: number }>>(new Map());

  /**
   * Update durations for running builds
   */
  useEffect(() => {
    const interval = setInterval(() => {
      const newDurations = new Map<string, { minutes: number; seconds: number }>();
      builds
        .filter((b) => b.status === 'running' && b.started_at)
        .forEach((build) => {
          newDurations.set(build.id, formatDuration(build.started_at));
        });
      setBuildDurations(newDurations);
    }, 1000);

    return () => clearInterval(interval);
  }, [builds]);

  /**
   * Handle build cancellation
   */
  const handleCancelBuild = async (buildId: string) => {
    setCancellingBuilds((prev) => new Set(prev).add(buildId));
    try {
      await onCancelBuild?.(buildId);
    } finally {
      setCancellingBuilds((prev) => {
        const next = new Set(prev);
        next.delete(buildId);
        return next;
      });
    }
  };

  /**
   * Handle view logs
   */
  const handleViewLogs = (buildId: string) => {
    onViewLogs?.(buildId);
  };

  /**
   * Render a single build card
   */
  const renderBuildCard = (build: ScheduledBuild, position?: number) => {
    const isCancelling = cancellingBuilds.has(build.id);
    const canCancel = ['pending', 'queued'].includes(build.status);
    const isRunning = build.status === 'running';
    const duration = buildDurations.get(build.id);

    return (
      <Card key={build.id} className="border-border/50 hover:border-border transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3">
            {/* Left side - Main info */}
            <div className="flex-1 min-w-0">
              {/* Title and status */}
              <div className="flex items-center gap-2 mb-2">
                {position !== undefined && (
                  <Badge variant="outline" className="shrink-0">
                    {t('scheduler:queue.position', { position })}
                  </Badge>
                )}
                <h4 className="font-medium text-foreground truncate">{build.spec_name}</h4>
                <Badge variant="outline" className={getStatusColor(build.status)}>
                  {t(`scheduler:queue.status.${build.status}`)}
                </Badge>
              </div>

              {/* Duration for running builds */}
              {isRunning && duration && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                  <Clock className="h-3.5 w-3.5" />
                  <span>
                    {t('scheduler:queue.duration', {
                      minutes: duration.minutes,
                      seconds: duration.seconds
                    })}
                  </span>
                </div>
              )}

              {/* Progress bar for running builds */}
              {isRunning && (
                <div className="mb-2">
                  <Progress value={undefined} className="h-1.5" />
                </div>
              )}

              {/* Priority and dependencies */}
              <div className="flex items-center gap-3 text-sm">
                <Badge variant="outline" className={getPriorityColor(build.priority)}>
                  {t('scheduler:queue.priority')}: {t(`scheduler:priority.${build.priority}`)}
                </Badge>
                {build.dependencies.length > 0 && (
                  <span className="text-muted-foreground">
                    {t('scheduler:queue.dependencies')}: {build.dependencies.length}
                  </span>
                )}
                {build.dependencies.length === 0 && (
                  <span className="text-muted-foreground">
                    {t('scheduler:queue.noDependencies')}
                  </span>
                )}
              </div>

              {/* Retry count */}
              {build.retry_count > 0 && (
                <div className="mt-2 text-sm text-muted-foreground">
                  Retry {build.retry_count} of {build.max_retries}
                </div>
              )}

              {/* Error message if retrying */}
              {build.status === 'retrying' && build.error_message && (
                <div className="mt-2 text-sm text-destructive flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span className="line-clamp-2">{build.error_message}</span>
                </div>
              )}
            </div>

            {/* Right side - Actions */}
            <div className="flex flex-col gap-2 shrink-0">
              {canCancel && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCancelBuild(build.id)}
                  disabled={isCancelling}
                  className="h-8 px-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                >
                  {isCancelling ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <X className="h-3.5 w-3.5" />
                  )}
                </Button>
              )}
              {isRunning && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleViewLogs(build.id)}
                  className="h-8 px-2"
                >
                  <FileText className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  /**
   * Render a build group section
   */
  const renderBuildGroup = (title: string, icon: React.ReactNode, builds: ScheduledBuild[], showPosition = false) => {
    if (builds.length === 0) return null;

    return (
      <div key={title} className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground/70 flex items-center gap-2">
          {icon}
          {title}
          <Badge variant="secondary" className="h-5 px-1.5 text-xs">
            {builds.length}
          </Badge>
        </h3>
        <div className="space-y-2">
          {builds.map((build, index) => renderBuildCard(build, showPosition ? index + 1 : undefined))}
        </div>
      </div>
    );
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center py-12">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground/50" />
          <p className="mt-4 text-sm text-muted-foreground">
            {t('scheduler:queue.loading')}
          </p>
        </div>
      </div>
    );
  }

  // Filter to only active builds (pending, queued, running, retrying)
  const activeBuilds = builds.filter((b) =>
    ['pending', 'queued', 'running', 'retrying'].includes(b.status)
  );

  // Group builds by status
  const groupedBuilds = groupBuildsByStatus(activeBuilds);
  const hasBuilds = activeBuilds.length > 0;

  // Empty state
  if (!hasBuilds) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-12 text-center">
            <ListOrdered className="mx-auto h-16 w-16 text-muted-foreground/30" />
            <h3 className="mt-4 text-lg font-semibold text-foreground">
              {t('scheduler:queue.noBuilds')}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {t('scheduler:queue.noBuildsDescription')}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Queue view with grouped builds
  return (
    <ScrollArea className="flex-1">
      <div className="p-6 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-foreground flex items-center gap-2">
              <ListOrdered className="h-6 w-6" />
              {t('scheduler:queue.title')}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {activeBuilds.length} {activeBuilds.length === 1 ? 'build' : 'builds'} in queue
            </p>
          </div>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <Loader2 className="h-4 w-4 mr-2" />
              {t('common:buttons.refresh')}
            </Button>
          )}
        </div>

        {/* Build groups */}
        {renderBuildGroup(
          t('scheduler:queue.active'),
          <Play className="h-4 w-4" />,
          groupedBuilds.active,
          false
        )}
        {renderBuildGroup(
          t('scheduler:queue.waiting'),
          <Pause className="h-4 w-4" />,
          groupedBuilds.waiting,
          true
        )}
      </div>
    </ScrollArea>
  );
}
