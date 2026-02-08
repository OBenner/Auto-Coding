/**
 * CalendarView - Calendar view of scheduled builds
 *
 * Displays scheduled builds organized by date/time with status indicators.
 * Shows upcoming builds, allows cancellation, and provides visual feedback.
 *
 * Features:
 * - Groups builds by date (Today, Tomorrow, This Week, Later)
 * - Shows build status with color-coded badges
 * - Displays priority level and dependencies
 * - Loading and empty states
 * - Cancel and retry actions
 *
 * @example
 * ```tsx
 * <CalendarView
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
  Calendar,
  Clock,
  Loader2,
  AlertCircle,
  X,
  RefreshCw,
  CalendarDays
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import type { ScheduledBuild, BuildStatus, SchedulePriority } from '../../../shared/types/scheduler';

/**
 * Props for the CalendarView component
 */
interface CalendarViewProps {
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
  /** Callback when user retries a failed build */
  onRetryBuild?: (buildId: string) => void;
}

/**
 * Grouped builds by time period
 */
interface GroupedBuilds {
  today: ScheduledBuild[];
  tomorrow: ScheduledBuild[];
  thisWeek: ScheduledBuild[];
  later: ScheduledBuild[];
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
 * Format date for display
 */
const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'Immediate';

  const date = new Date(dateString);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const buildDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (buildDate.getTime() === today.getTime()) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } else if (buildDate.getTime() === tomorrow.getTime()) {
    return `Tomorrow, ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
  } else {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};

/**
 * Group builds by time period
 */
const groupBuildsByTime = (builds: ScheduledBuild[]): GroupedBuilds => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const weekEnd = new Date(today);
  weekEnd.setDate(weekEnd.getDate() + 7);

  const grouped: GroupedBuilds = {
    today: [],
    tomorrow: [],
    thisWeek: [],
    later: []
  };

  builds.forEach((build) => {
    if (!build.scheduled_time) {
      grouped.today.push(build);
      return;
    }

    const buildDate = new Date(build.scheduled_time);
    const buildDay = new Date(buildDate.getFullYear(), buildDate.getMonth(), buildDate.getDate());

    if (buildDay.getTime() === today.getTime()) {
      grouped.today.push(build);
    } else if (buildDay.getTime() === tomorrow.getTime()) {
      grouped.tomorrow.push(build);
    } else if (buildDay < weekEnd) {
      grouped.thisWeek.push(build);
    } else {
      grouped.later.push(build);
    }
  });

  return grouped;
};

export function CalendarView({
  projectId,
  builds,
  isLoading = false,
  onRefresh,
  onCancelBuild,
  onRetryBuild
}: CalendarViewProps) {
  const { t } = useTranslation(['scheduler', 'common']);

  const [cancellingBuilds, setCancellingBuilds] = useState<Set<string>>(new Set());

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
   * Handle build retry
   */
  const handleRetryBuild = async (buildId: string) => {
    await onRetryBuild?.(buildId);
  };

  /**
   * Render a single build card
   */
  const renderBuildCard = (build: ScheduledBuild) => {
    const isCancelling = cancellingBuilds.has(build.id);
    const canCancel = ['pending', 'queued'].includes(build.status);
    const canRetry = build.status === 'failed';

    return (
      <Card key={build.id} className="border-border/50 hover:border-border transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3">
            {/* Left side - Main info */}
            <div className="flex-1 min-w-0">
              {/* Title and status */}
              <div className="flex items-center gap-2 mb-2">
                <h4 className="font-medium text-foreground truncate">{build.spec_name}</h4>
                <Badge variant="outline" className={getStatusColor(build.status)}>
                  {t(`scheduler:calendar.status.${build.status}`)}
                </Badge>
              </div>

              {/* Scheduled time */}
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <Clock className="h-3.5 w-3.5" />
                <span>{formatDate(build.scheduled_time)}</span>
              </div>

              {/* Priority and dependencies */}
              <div className="flex items-center gap-3 text-sm">
                <Badge variant="outline" className={getPriorityColor(build.priority)}>
                  {t('scheduler:calendar.priority')}: {t(`scheduler:priority.${build.priority}`)}
                </Badge>
                {build.dependencies.length > 0 && (
                  <span className="text-muted-foreground">
                    {t('scheduler:calendar.dependencies')}: {build.dependencies.length}
                  </span>
                )}
                {build.dependencies.length === 0 && (
                  <span className="text-muted-foreground">
                    {t('scheduler:calendar.noDependencies')}
                  </span>
                )}
              </div>

              {/* Error message if failed */}
              {build.status === 'failed' && build.error_message && (
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
              {canRetry && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRetryBuild(build.id)}
                  className="h-8 px-2"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
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
  const renderBuildGroup = (title: string, builds: ScheduledBuild[]) => {
    if (builds.length === 0) return null;

    return (
      <div key={title} className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground/70 flex items-center gap-2">
          {title}
          <Badge variant="secondary" className="h-5 px-1.5 text-xs">
            {builds.length}
          </Badge>
        </h3>
        <div className="space-y-2">
          {builds.map(renderBuildCard)}
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
            {t('scheduler:calendar.loading')}
          </p>
        </div>
      </div>
    );
  }

  // Group builds by time
  const groupedBuilds = groupBuildsByTime(builds);
  const hasBuilds = Object.values(groupedBuilds).some((group) => group.length > 0);

  // Empty state
  if (!hasBuilds) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-12 text-center">
            <CalendarDays className="mx-auto h-16 w-16 text-muted-foreground/30" />
            <h3 className="mt-4 text-lg font-semibold text-foreground">
              {t('scheduler:calendar.noBuilds')}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {t('scheduler:calendar.noBuildsDescription')}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Calendar view with grouped builds
  return (
    <ScrollArea className="flex-1">
      <div className="p-6 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-foreground flex items-center gap-2">
              <Calendar className="h-6 w-6" />
              {t('scheduler:calendar.title')}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {builds.length} {builds.length === 1 ? 'build' : 'builds'} scheduled
            </p>
          </div>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              {t('common:buttons.refresh')}
            </Button>
          )}
        </div>

        {/* Build groups */}
        {renderBuildGroup(t('scheduler:calendar.today'), groupedBuilds.today)}
        {renderBuildGroup(t('scheduler:calendar.tomorrow'), groupedBuilds.tomorrow)}
        {renderBuildGroup(t('scheduler:calendar.thisWeek'), groupedBuilds.thisWeek)}
        {renderBuildGroup(t('scheduler:calendar.later'), groupedBuilds.later)}
      </div>
    </ScrollArea>
  );
}
