import { useState, useEffect, useCallback, useRef } from 'react';
import { Loader2, BarChart3, Calendar, AlertTriangle, RefreshCw, Timer, Zap, ListChecks, RotateCcw } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { toast } from '../../hooks/use-toast';
import { MetricsSummaryCard } from './MetricsSummaryCard';
import { TrendsChart } from './TrendsChart';
import { SpecBreakdownTable } from './SpecBreakdownTable';
import { FailureAnalysisDashboard } from './FailureAnalysisDashboard';
import { QualityTrendChart } from './QualityTrendChart';
import { QualityAlertCard } from './QualityAlertCard';
import { DashboardActions } from './DashboardActions';
import { useQualityStore, loadAllQualityData } from '../../stores/quality-store';
import { useShallow } from 'zustand/react/shallow';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
  ProductivityAnalyticsExportOptions,
  ProductivityAnalyticsFilter,
  FailureMetrics
} from '../../../shared/types/productivity-analytics';

interface ProductivityDashboardProps {
  projectId: string;
}

type TimeRange = 'all' | '7d' | '30d' | '90d';

/** Race a promise against a timeout so a hung IPC can never block the UI. */
function withTimeout<T>(promise: Promise<T>, ms = 5_000): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('IPC request timed out')), ms)
    ),
  ]);
}

function formatHoursCompact(hours: number): string {
  if (hours < 1 / 60) return '0m';
  if (hours < 1) return `${(hours * 60).toFixed(0)}m`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  const days = Math.floor(hours / 24);
  const remainingHours = Math.floor(hours % 24);
  return `${days}d ${remainingHours}h`;
}

export function ProductivityDashboard({ projectId }: ProductivityDashboardProps) {
  const [summary, setSummary] = useState<ProductivitySummary | null>(null);
  const [trends, setTrends] = useState<ProductivityTrendPoint[]>([]);
  const [failureMetrics, setFailureMetrics] = useState<FailureMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [hasLoaded, setHasLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Quality store
  const { scores: qualityScores, alerts: qualityAlerts, isLoadingScores: isLoadingQuality } =
    useQualityStore(useShallow((state) => ({
      scores: state.scores,
      alerts: state.alerts,
      isLoadingScores: state.isLoadingScores,
    })));

  const getDateFilter = useCallback((): Pick<ProductivityAnalyticsFilter, 'start_date' | 'end_date'> => {
    if (timeRange === 'all') {
      return {};
    }
    const endDate = new Date();
    const startDate = new Date();
    switch (timeRange) {
      case '7d': startDate.setDate(startDate.getDate() - 7); break;
      case '30d': startDate.setDate(startDate.getDate() - 30); break;
      case '90d': startDate.setDate(startDate.getDate() - 90); break;
    }
    return { start_date: startDate.toISOString(), end_date: endDate.toISOString() };
  }, [timeRange]);

  const loadAnalyticsData = useCallback(async (showRefreshToast = false) => {
    const errors: string[] = [];
    try {
      setIsLoading(true);
      setLoadError(null);

      const dateFilter = getDateFilter();

      // Check API exists
      if (!window.electronAPI?.getProductivitySummary) {
        throw new Error('electronAPI.getProductivitySummary is not available');
      }

      const ipcCatch = (label: string) => (err: unknown) => {
        const msg = `${label}: ${err instanceof Error ? err.message : String(err)}`;
        errors.push(msg);
        console.error('[Analytics]', msg);
        return { success: false as const, error: msg, data: undefined };
      };

      const [summaryResult, trendsResult, failureResult] = await Promise.all([
        withTimeout(window.electronAPI.getProductivitySummary(projectId, dateFilter))
          .catch(ipcCatch('Summary')),
        withTimeout(window.electronAPI.getProductivityTrends(projectId, dateFilter))
          .catch(ipcCatch('Trends')),
        window.electronAPI.getFailureMetrics
          ? withTimeout(window.electronAPI.getFailureMetrics(projectId)).catch(ipcCatch('Failure Metrics'))
          : Promise.resolve({ success: false as const, error: undefined, data: undefined }),
      ]);

      if (!mountedRef.current) return;

      if (summaryResult.success && summaryResult.data) {
        setSummary(summaryResult.data);
      } else if (summaryResult.error) {
        errors.push(summaryResult.error);
      }

      if (trendsResult.success && trendsResult.data) {
        setTrends(trendsResult.data);
      } else if (trendsResult.error) {
        errors.push(trendsResult.error);
      }

      if (failureResult.success && failureResult.data) {
        setFailureMetrics(failureResult.data);
      }

      await loadAllQualityData(projectId);

      if (!mountedRef.current) return;

      if (showRefreshToast && errors.length === 0) {
        toast({ title: 'Analytics Refreshed', description: 'Productivity analytics data has been updated.' });
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      errors.push(msg);
      console.error('[Analytics] Fatal error:', msg);
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
        setIsRefreshing(false);
        setHasLoaded(true);
        if (errors.length > 0) {
          setLoadError(errors.join('; '));
        }
      }
    }
  }, [projectId, getDateFilter]);

  useEffect(() => {
    loadAnalyticsData();
  }, [loadAnalyticsData]);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    loadAnalyticsData(true);
  }, [loadAnalyticsData]);

  const handleExport = useCallback(async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);
      const dateFilter = getDateFilter();
      const options: ProductivityAnalyticsExportOptions = { format, filter: dateFilter };
      const result = await window.electronAPI.exportProductivityAnalytics(projectId, options);
      if (result.success && result.data) {
        toast({ title: 'Export Successful', description: `Analytics exported to ${result.data}` });
      } else {
        toast({ title: 'Export Failed', description: result.error || 'Failed to export analytics', variant: 'destructive' });
      }
    } catch (error) {
      console.error('Error exporting analytics:', error);
      toast({ title: 'Export Error', description: 'An error occurred while exporting analytics.', variant: 'destructive' });
    } finally {
      setIsExporting(false);
    }
  }, [projectId, getDateFilter]);

  const handleTimeRangeChange = useCallback((range: TimeRange) => {
    setTimeRange(range);
  }, []);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Productivity Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Track build statistics, time savings, and productivity metrics
              </p>
            </div>
            {isLoading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 border border-border rounded-md p-1">
              {(['7d', '30d', '90d', 'all'] as const).map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => handleTimeRangeChange(range)}
                  className="h-7"
                >
                  {range !== 'all' && <Calendar className="h-3 w-3 mr-1" />}
                  {range === 'all' ? 'All' : range}
                </Button>
              ))}
            </div>

            <DashboardActions
              onRefresh={handleRefresh}
              onExportJson={() => handleExport('json')}
              onExportCsv={() => handleExport('csv')}
              isRefreshing={isRefreshing}
              isExporting={isExporting}
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">

          {/* Error Banner */}
          {loadError && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-destructive">Failed to load analytics</p>
                <p className="text-xs text-muted-foreground mt-1 break-all">{loadError}</p>
                <p className="text-xs text-muted-foreground mt-1">ProjectID: {projectId}</p>
              </div>
              <Button variant="outline" size="sm" onClick={handleRefresh} className="shrink-0">
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            </div>
          )}

          {/* Summary Metrics */}
          <MetricsSummaryCard analytics={summary} isLoading={isLoading} />

          {/* Secondary Metrics */}
          {summary && summary.total_specs > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="p-2 rounded-lg bg-accent/10 text-accent">
                  <Timer className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-muted-foreground mb-1">Avg Build Time</div>
                  <div className="text-2xl font-semibold text-foreground">
                    {summary.total_specs > 0
                      ? formatHoursCompact(summary.total_build_time_hours / summary.total_specs)
                      : '-'}
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="p-2 rounded-lg bg-success/10 text-success">
                  <Zap className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-muted-foreground mb-1">First Attempt Pass</div>
                  <div className="text-2xl font-semibold text-foreground">
                    {(summary.first_attempt_success_rate * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="p-2 rounded-lg bg-accent/10 text-accent">
                  <ListChecks className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-muted-foreground mb-1">Avg Subtasks/Spec</div>
                  <div className="text-2xl font-semibold text-foreground">
                    {summary.average_subtasks_per_spec.toFixed(1)}
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="p-2 rounded-lg bg-warning/10 text-warning">
                  <RotateCcw className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-muted-foreground mb-1">Avg QA Iterations</div>
                  <div className="text-2xl font-semibold text-foreground">
                    {summary.average_qa_iterations.toFixed(1)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Trends */}
          <TrendsChart trends={trends} isLoading={isLoading} />

          {/* Quality Section */}
          <div className="space-y-6">
            <QualityAlertCard alerts={qualityAlerts} isLoading={isLoadingQuality} />
            <QualityTrendChart scores={qualityScores} isLoading={isLoadingQuality} />
          </div>

          {/* Failure Analysis Dashboard */}
          <FailureAnalysisDashboard
            failureMetrics={failureMetrics}
            isLoading={isLoading}
          />

          {/* Spec Breakdown */}
          <SpecBreakdownTable specs={summary?.specs ?? []} isLoading={isLoading} />

          {/* Empty State */}
          {hasLoaded && !isLoading && !loadError && (!summary || summary.total_specs === 0) && (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <BarChart3 className="h-16 w-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">No productivity data available</p>
              <p className="text-sm">Complete some tasks to see your analytics</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
