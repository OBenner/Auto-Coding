import { useState, useEffect, useCallback } from 'react';
import { Download, Loader2, RefreshCw, DollarSign, FileText, Calendar } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import { CostSummaryCard } from './CostSummaryCard';
import { CostTrendsChart } from './CostTrendsChart';
import { CostByModel } from './CostByModel';
import type {
  CostSummary,
  CostTrendPoint,
  ModelCostBreakdown
} from '../../../shared/types/task';

interface CostDashboardProps {
  projectId: string;
}

type TimeRange = 'all' | '7d' | '30d' | '90d';

export function CostDashboard({ projectId }: CostDashboardProps) {
  const { toast } = useToast();

  // State
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [trends, setTrends] = useState<CostTrendPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  // Get window days for trends based on time range
  const getWindowDays = useCallback((): number => {
    switch (timeRange) {
      case '7d':
        return 7;
      case '30d':
        return 30;
      case '90d':
        return 90;
      case 'all':
        return 365; // Default to a year for "all"
      default:
        return 30;
    }
  }, [timeRange]);

  // Get date filter for summary and export
  const getDateFilter = useCallback(() => {
    if (timeRange === 'all') {
      return { startDate: undefined, endDate: undefined };
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
      startDate: startDate.toISOString(),
      endDate: endDate.toISOString(),
    };
  }, [timeRange]);

  // Load all cost data
  const loadCostData = useCallback(async (showRefreshToast = false) => {
    try {
      const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
      loadingState(true);

      const { startDate, endDate } = getDateFilter();
      const windowDays = getWindowDays();

      // Load cost summary
      const summaryResult = await window.electronAPI.getCostSummary(
        projectId,
        startDate,
        endDate
      );

      if (summaryResult.success && summaryResult.data) {
        setSummary(summaryResult.data);
      } else {
        console.error('Failed to load cost summary:', summaryResult.error);
        toast({
          title: 'Warning',
          description: summaryResult.error || 'Failed to load cost summary.',
          variant: 'destructive',
        });
      }

      // Load trends data
      const trendsResult = await window.electronAPI.getCostTrends(
        projectId,
        windowDays,
        'daily'
      );

      if (trendsResult.success && trendsResult.data) {
        setTrends(trendsResult.data);
      } else {
        console.error('Failed to load cost trends:', trendsResult.error);
      }

      if (showRefreshToast) {
        toast({
          title: 'Cost Data Refreshed',
          description: 'Cost analytics data has been updated.',
        });
      }
    } catch (error) {
      console.error('Error loading cost data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load cost analytics data.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId, timeRange, getDateFilter, getWindowDays, toast]);

  // Initial load
  useEffect(() => {
    loadCostData();
  }, [loadCostData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadCostData(true);
  }, [loadCostData]);

  // Handle export
  const handleExport = useCallback(async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);

      const { startDate, endDate } = getDateFilter();

      const result = await window.electronAPI.exportCostAnalytics(
        projectId,
        format,
        undefined, // Let backend choose output path
        startDate,
        endDate
      );

      if (result.success && result.data) {
        toast({
          title: 'Export Successful',
          description: `Cost data exported to ${result.data}`,
        });
      } else {
        toast({
          title: 'Export Failed',
          description: result.error || 'Failed to export cost data',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error exporting cost data:', error);
      toast({
        title: 'Export Error',
        description: 'An error occurred while exporting cost data.',
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
          <p className="text-sm text-muted-foreground">Loading cost analytics...</p>
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
            <DollarSign className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Cost Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Track API costs, token usage, and spending trends
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
          {/* Cost Summary Card */}
          <CostSummaryCard costData={summary} isLoading={isLoading} />

          {/* Cost Trends Chart */}
          <CostTrendsChart
            trends={trends}
            isLoading={isLoading}
            timeRange={timeRange}
            onTimeRangeChange={handleTimeRangeChange}
          />

          {/* Cost by Model Breakdown */}
          <CostByModel
            modelCosts={summary?.model_costs ?? null}
            isLoading={isLoading}
          />

          {/* Empty State */}
          {(!summary || summary.total_cost === 0) && (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <DollarSign className="h-16 w-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">No cost data available</p>
              <p className="text-sm">Run some tasks to see your cost analytics</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
