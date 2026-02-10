import { useState, useEffect, useCallback } from 'react';
import { Download, Loader2, RefreshCw, BarChart3, FileText, Calendar } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
  ProductivityAnalyticsExportOptions,
  ProductivityAnalyticsFilter
} from '../../../shared/types/productivity-analytics';

interface ProductivityDashboardProps {
  projectId: string;
}

type TimeRange = 'all' | '7d' | '30d' | '90d';

export function ProductivityDashboard({ projectId }: ProductivityDashboardProps) {
  const { toast } = useToast();

  // State
  const [summary, setSummary] = useState<ProductivitySummary | null>(null);
  const [trends, setTrends] = useState<ProductivityTrendPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  // Calculate date filter based on time range
  const getDateFilter = useCallback((): Pick<ProductivityAnalyticsFilter, 'start_date' | 'end_date'> => {
    if (timeRange === 'all') {
      return {};
    }

    const endDate = new Date();
    const startDate = new Date();

    switch (timeRange) {
      case '7d':
        startDate.setDate(startDate.getDate() - 7);
        break;
      case '30d':
        startDate.setDate(startDate.getDate() - 30);
        break;
      case '90d':
        startDate.setDate(startDate.getDate() - 90);
        break;
    }

    return {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
    };
  }, [timeRange]);

  // Load all analytics data
  const loadAnalyticsData = useCallback(async (showRefreshToast = false) => {
    try {
      const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
      loadingState(true);

      const dateFilter = getDateFilter();

      // Load summary analytics
      const summaryResult = await window.electronAPI.getProductivitySummary(
        projectId,
        dateFilter
      );

      if (summaryResult.success && summaryResult.data) {
        setSummary(summaryResult.data);
      } else {
        console.error('Failed to load productivity summary:', summaryResult.error);
        toast({
          title: 'Warning',
          description: summaryResult.error || 'Failed to load productivity summary.',
          variant: 'destructive',
        });
      }

      // Load trends data
      const trendsResult = await window.electronAPI.getProductivityTrends(
        projectId,
        dateFilter
      );

      if (trendsResult.success && trendsResult.data) {
        setTrends(trendsResult.data);
      } else {
        console.error('Failed to load productivity trends:', trendsResult.error);
      }

      if (showRefreshToast) {
        toast({
          title: 'Analytics Refreshed',
          description: 'Productivity analytics data has been updated.',
        });
      }
    } catch (error) {
      console.error('Error loading analytics data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load productivity analytics data.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId, timeRange, getDateFilter, toast]);

  // Initial load
  useEffect(() => {
    loadAnalyticsData();
  }, [loadAnalyticsData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadAnalyticsData(true);
  }, [loadAnalyticsData]);

  // Handle export
  const handleExport = useCallback(async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);

      const dateFilter = getDateFilter();
      const options: ProductivityAnalyticsExportOptions = {
        format,
        filter: dateFilter,
      };

      const result = await window.electronAPI.exportProductivityAnalytics(projectId, options);

      if (result.success && result.data) {
        toast({
          title: 'Export Successful',
          description: `Analytics exported to ${result.data}`,
        });
      } else {
        toast({
          title: 'Export Failed',
          description: result.error || 'Failed to export analytics',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error exporting analytics:', error);
      toast({
        title: 'Export Error',
        description: 'An error occurred while exporting analytics.',
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  }, [projectId, getDateFilter, toast]);

  // Handle time range change
  const handleTimeRangeChange = useCallback((range: TimeRange) => {
    setTimeRange(range);
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading productivity analytics...</p>
        </div>
      </div>
    );
  }

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
          </div>

          <div className="flex items-center gap-2">
            {/* Time Range Filter */}
            <div className="flex items-center gap-1 border border-border rounded-md p-1">
              <Button
                variant={timeRange === '7d' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('7d')}
                className="h-7"
              >
                <Calendar className="h-3 w-3 mr-1" />
                7d
              </Button>
              <Button
                variant={timeRange === '30d' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('30d')}
                className="h-7"
              >
                <Calendar className="h-3 w-3 mr-1" />
                30d
              </Button>
              <Button
                variant={timeRange === '90d' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('90d')}
                className="h-7"
              >
                <Calendar className="h-3 w-3 mr-1" />
                90d
              </Button>
              <Button
                variant={timeRange === 'all' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('all')}
                className="h-7"
              >
                All
              </Button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={isExporting}
            >
              <FileText className="h-4 w-4 mr-2" />
              Export JSON
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={isExporting}
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Summary Metrics Card - Will be replaced with MetricsSummaryCard component */}
          {summary && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Summary Metrics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Specs</p>
                  <p className="text-2xl font-bold">{summary.total_specs ?? 0}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Completed</p>
                  <p className="text-2xl font-bold text-green-600">{summary.completed_specs ?? 0}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Time Saved</p>
                  <p className="text-2xl font-bold">
                    {Number(summary.total_time_saved_hours ?? 0).toFixed(1)}h
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <p className="text-2xl font-bold">
                    {(Number(summary.average_success_rate ?? 0) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Trends Chart Placeholder - Will be replaced with TrendsChart component */}
          {trends.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Trends Over Time</h2>
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                <p>Trends chart will be displayed here (TrendsChart component)</p>
              </div>
            </div>
          )}

          {/* Breakdown by Type and Complexity */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* By Type */}
              <div className="rounded-lg border border-border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4">By Type</h2>
                <div className="space-y-2">
                  {Object.entries(summary.specs_by_type).map(([type, count]) => (
                    <div key={type} className="flex justify-between items-center">
                      <span className="text-sm capitalize">{type}</span>
                      <span className="text-sm font-semibold">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* By Complexity */}
              <div className="rounded-lg border border-border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4">By Complexity</h2>
                <div className="space-y-2">
                  {Object.entries(summary.specs_by_complexity).map(([complexity, count]) => (
                    <div key={complexity} className="flex justify-between items-center">
                      <span className="text-sm capitalize">{complexity}</span>
                      <span className="text-sm font-semibold">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Spec Details Table Placeholder - Will be replaced with SpecBreakdownTable component */}
          {summary && summary.specs.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Spec Details</h2>
              <div className="flex items-center justify-center h-32 text-muted-foreground">
                <p>Detailed spec breakdown table will be displayed here (SpecBreakdownTable component)</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {(!summary || summary.total_specs === 0) && (
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
