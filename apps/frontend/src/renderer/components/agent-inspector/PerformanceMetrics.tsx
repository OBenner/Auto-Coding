/**
 * PerformanceMetrics Component
 *
 * Displays performance metrics for agent sessions including token usage
 * and timing information for debugging and optimization.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Clock, Coins, TrendingUp, Activity, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

/**
 * Performance metrics data structure
 */
export interface PerformanceMetricsData {
  /** Total input tokens used */
  inputTokens: number;
  /** Total output tokens used */
  outputTokens: number;
  /** Total thinking tokens used (extended_thinking) */
  thinkingTokens?: number;
  /** Total duration in milliseconds */
  totalDurationMs: number;
  /** Number of tool calls */
  toolCallCount: number;
  /** Number of thinking blocks */
  thinkingBlockCount: number;
  /** Average duration per step in milliseconds */
  avgStepDurationMs?: number;
  /** Slowest step duration in milliseconds */
  slowestStepMs?: number;
  /** Fastest step duration in milliseconds */
  fastestStepMs?: number;
  /** Session start time */
  sessionStartTime?: string;
  /** Session end time (null if in progress) */
  sessionEndTime?: string | null;
}

interface PerformanceMetricsProps {
  /** Performance metrics to display */
  metrics: PerformanceMetricsData;
  /** Optional CSS class name */
  className?: string;
  /** Whether to show detailed breakdown */
  showDetails?: boolean;
}

/**
 * PerformanceMetrics component
 * Displays token usage and timing information for agent sessions
 */
export function PerformanceMetrics({
  metrics,
  className,
  showDetails = true,
}: PerformanceMetricsProps) {
  const { t, i18n } = useTranslation(['agent-inspector', 'common']);

  // Calculate derived metrics
  const totalTokens = useMemo(
    () => metrics.inputTokens + metrics.outputTokens + (metrics.thinkingTokens || 0),
    [metrics.inputTokens, metrics.outputTokens, metrics.thinkingTokens]
  );

  const totalSteps = useMemo(
    () => metrics.toolCallCount + metrics.thinkingBlockCount,
    [metrics.toolCallCount, metrics.thinkingBlockCount]
  );

  // Format helpers
  const formatNumber = useMemo(() => {
    const formatter = new Intl.NumberFormat(i18n.language);
    return (num: number) => formatter.format(num);
  }, [i18n.language]);

  const formatDuration = useMemo(
    () => (ms: number) => {
      if (ms < 1000) return `${ms.toFixed(0)}${t('agent-inspector:units.milliseconds')}`;
      if (ms < 60000) return `${(ms / 1000).toFixed(2)}${t('agent-inspector:units.seconds')}`;
      if (ms < 3600000) return `${(ms / 60000).toFixed(2)}${t('agent-inspector:units.minutes')}`;
      return `${(ms / 3600000).toFixed(2)}${t('agent-inspector:units.hours')}`;
    },
    [t]
  );

  const formatPercentage = useMemo(
    () => (value: number, total: number) => {
      if (total === 0) return '0%';
      return `${((value / total) * 100).toFixed(1)}%`;
    },
    []
  );

  return (
    <div className={cn('space-y-4', className)}>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Tokens Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('agent-inspector:metrics.totalTokens', 'Total Tokens')}
            </CardTitle>
            <Coins className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(totalTokens)}</div>
            {showDetails && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {t('agent-inspector:metrics.input', 'Input')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {formatNumber(metrics.inputTokens)}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {t('agent-inspector:metrics.output', 'Output')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {formatNumber(metrics.outputTokens)}
                  </Badge>
                </div>
                {metrics.thinkingTokens !== undefined && metrics.thinkingTokens > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">
                      {t('agent-inspector:metrics.thinking', 'Thinking')}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {formatNumber(metrics.thinkingTokens)}
                    </Badge>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Total Duration Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('agent-inspector:metrics.totalDuration', 'Total Duration')}
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatDuration(metrics.totalDurationMs)}</div>
            {showDetails && metrics.avgStepDurationMs !== undefined && (
              <p className="text-xs text-muted-foreground mt-2">
                {t('agent-inspector:metrics.avgPerStep', 'Avg per step')}:{' '}
                {formatDuration(metrics.avgStepDurationMs)}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Total Steps Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('agent-inspector:metrics.totalSteps', 'Total Steps')}
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(totalSteps)}</div>
            {showDetails && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {t('agent-inspector:metrics.toolCalls', 'Tool calls')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {formatNumber(metrics.toolCallCount)}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {t('agent-inspector:metrics.thoughts', 'Thoughts')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {formatNumber(metrics.thinkingBlockCount)}
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Efficiency Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('agent-inspector:metrics.efficiency', 'Efficiency')}
            </CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalSteps > 0
                ? formatNumber(Math.round(totalTokens / totalSteps))
                : '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {t('agent-inspector:metrics.tokensPerStep', 'Tokens per step')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Breakdown */}
      {showDetails && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              {t('agent-inspector:metrics.breakdown', 'Performance Breakdown')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Token Distribution */}
            <div>
              <h4 className="text-sm font-medium mb-3">
                {t('agent-inspector:metrics.tokenDistribution', 'Token Distribution')}
              </h4>
              <div className="space-y-2">
                {/* Input Tokens Bar */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">
                      {t('agent-inspector:metrics.input', 'Input')}
                    </span>
                    <span className="font-medium">
                      {formatNumber(metrics.inputTokens)} (
                      {formatPercentage(metrics.inputTokens, totalTokens)})
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all"
                      style={{
                        width: formatPercentage(metrics.inputTokens, totalTokens),
                      }}
                    />
                  </div>
                </div>

                {/* Output Tokens Bar */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">
                      {t('agent-inspector:metrics.output', 'Output')}
                    </span>
                    <span className="font-medium">
                      {formatNumber(metrics.outputTokens)} (
                      {formatPercentage(metrics.outputTokens, totalTokens)})
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 transition-all"
                      style={{
                        width: formatPercentage(metrics.outputTokens, totalTokens),
                      }}
                    />
                  </div>
                </div>

                {/* Thinking Tokens Bar */}
                {metrics.thinkingTokens !== undefined && metrics.thinkingTokens > 0 && (
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-muted-foreground">
                        {t('agent-inspector:metrics.thinking', 'Thinking')}
                      </span>
                      <span className="font-medium">
                        {formatNumber(metrics.thinkingTokens)} (
                        {formatPercentage(metrics.thinkingTokens, totalTokens)})
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 transition-all"
                        style={{
                          width: formatPercentage(metrics.thinkingTokens, totalTokens),
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Timing Statistics */}
            {(metrics.slowestStepMs !== undefined || metrics.fastestStepMs !== undefined) && (
              <div>
                <h4 className="text-sm font-medium mb-3">
                  {t('agent-inspector:metrics.timingStats', 'Timing Statistics')}
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  {metrics.fastestStepMs !== undefined && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        {t('agent-inspector:metrics.fastest', 'Fastest')}
                      </p>
                      <p className="text-sm font-medium">
                        {formatDuration(metrics.fastestStepMs)}
                      </p>
                    </div>
                  )}
                  {metrics.avgStepDurationMs !== undefined && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        {t('agent-inspector:metrics.average', 'Average')}
                      </p>
                      <p className="text-sm font-medium">
                        {formatDuration(metrics.avgStepDurationMs)}
                      </p>
                    </div>
                  )}
                  {metrics.slowestStepMs !== undefined && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        {t('agent-inspector:metrics.slowest', 'Slowest')}
                      </p>
                      <p className="text-sm font-medium">
                        {formatDuration(metrics.slowestStepMs)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Session Timeline */}
            {metrics.sessionStartTime && (
              <div>
                <h4 className="text-sm font-medium mb-3">
                  {t('agent-inspector:metrics.sessionTimeline', 'Session Timeline')}
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">
                      {t('agent-inspector:metrics.started', 'Started')}
                    </span>
                    <span className="font-medium">
                      {new Date(metrics.sessionStartTime).toLocaleString()}
                    </span>
                  </div>
                  {metrics.sessionEndTime && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">
                        {t('agent-inspector:metrics.completed', 'Completed')}
                      </span>
                      <span className="font-medium">
                        {new Date(metrics.sessionEndTime).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {!metrics.sessionEndTime && (
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">
                        {t('agent-inspector:metrics.inProgress', 'In Progress')}
                      </Badge>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
