import { useState, useEffect, useCallback } from 'react';
import { Download, Loader2, RefreshCw, BarChart3, FileText, Calendar, Cpu } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import type {
  ModelUsageSummary,
  ModelUsageTrendPoint,
  ModelUsageExportOptions,
  ModelUsageFilter
} from '../../../shared/types/model-usage';

interface ModelUsageDashboardProps {
  projectId: string;
}

type TimeRange = 'all' | '7d' | '30d' | '90d';

export function ModelUsageDashboard({ projectId }: ModelUsageDashboardProps) {
  const { toast } = useToast();

  // State
  const [summary, setSummary] = useState<ModelUsageSummary | null>(null);
  const [trends, setTrends] = useState<ModelUsageTrendPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  // Calculate date filter based on time range
  const getDateFilter = useCallback((): Pick<ModelUsageFilter, 'start_date' | 'end_date'> => {
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

  // Load all model usage data
  const loadModelUsageData = useCallback(async (showRefreshToast = false) => {
    try {
      const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
      loadingState(true);

      const dateFilter = getDateFilter();

      // Load summary analytics
      const summaryResult = await window.electronAPI.getModelUsageSummary(
        projectId,
        dateFilter
      );

      if (summaryResult.success && summaryResult.data) {
        setSummary(summaryResult.data);
      } else {
        console.error('Failed to load model usage summary:', summaryResult.error);
        toast({
          title: 'Warning',
          description: summaryResult.error || 'Failed to load model usage summary.',
          variant: 'destructive',
        });
      }

      // Load trends data
      const trendsResult = await window.electronAPI.getModelUsageTrends(
        projectId,
        dateFilter
      );

      if (trendsResult.success && trendsResult.data) {
        setTrends(trendsResult.data);
      } else {
        console.error('Failed to load model usage trends:', trendsResult.error);
      }

      if (showRefreshToast) {
        toast({
          title: 'Analytics Refreshed',
          description: 'Model usage analytics data has been updated.',
        });
      }
    } catch (error) {
      console.error('Error loading model usage data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load model usage analytics data.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId, timeRange, getDateFilter, toast]);

  // Initial load
  useEffect(() => {
    loadModelUsageData();
  }, [loadModelUsageData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadModelUsageData(true);
  }, [loadModelUsageData]);

  // Handle export
  const handleExport = useCallback(async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);

      const dateFilter = getDateFilter();
      const options: ModelUsageExportOptions = {
        format,
        filter: dateFilter,
      };

      const result = await window.electronAPI.exportModelUsageAnalytics(projectId, options);

      if (result.success && result.data) {
        toast({
          title: 'Export Successful',
          description: `Model usage analytics exported to ${result.data}`,
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
          <p className="text-sm text-muted-foreground">Loading model usage analytics...</p>
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
            <Cpu className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Model Usage Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Track AI model usage, costs, and configuration transparency
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
          {/* Summary Metrics Card */}
          {summary && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Summary Metrics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total API Calls</p>
                  <p className="text-2xl font-bold">{summary.total_usage_count ?? 0}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Tokens</p>
                  <p className="text-2xl font-bold">
                    {Number(summary.total_tokens ?? 0).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Cost</p>
                  <p className="text-2xl font-bold text-green-600">
                    ${Number(summary.total_cost ?? 0).toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Models Used</p>
                  <p className="text-2xl font-bold">
                    {summary.models?.length ?? 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Model Usage by Agent */}
          {summary && summary.agents && summary.agents.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Model Usage by Agent</h2>
              <div className="space-y-2">
                {summary.agents.map((agent) => (
                  <div key={agent.agent_type} className="flex justify-between items-center p-2 rounded hover:bg-muted/50">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium capitalize">{agent.agent_type}</span>
                      <span className="text-xs text-muted-foreground">
                        Preferred: {agent.preferred_model}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold">{agent.total_usage_count} calls</p>
                        <p className="text-xs text-muted-foreground">
                          {Number(agent.total_tokens).toLocaleString()} tokens
                        </p>
                      </div>
                      <div className="text-right w-24">
                        <p className="text-sm font-semibold text-green-600">
                          ${Number(agent.total_cost).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Models by Usage */}
          {summary && summary.top_models_by_usage && summary.top_models_by_usage.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Top Models by Usage</h2>
              <div className="space-y-2">
                {summary.top_models_by_usage.slice(0, 5).map((model) => (
                  <div key={model.model} className="flex justify-between items-center p-2 rounded hover:bg-muted/50">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">{model.model}</span>
                      <span className="text-xs text-muted-foreground">{model.provider}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold">{model.total_usage_count} calls</p>
                        <p className="text-xs text-muted-foreground">
                          {Number(model.total_tokens).toLocaleString()} tokens
                        </p>
                      </div>
                      <div className="text-right w-24">
                        <p className="text-sm font-semibold text-green-600">
                          ${Number(model.total_cost).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Models by Cost */}
          {summary && summary.top_models_by_cost && summary.top_models_by_cost.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Top Models by Cost</h2>
              <div className="space-y-2">
                {summary.top_models_by_cost.slice(0, 5).map((model) => (
                  <div key={model.model} className="flex justify-between items-center p-2 rounded hover:bg-muted/50">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">{model.model}</span>
                      <span className="text-xs text-muted-foreground">{model.provider}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold">{model.total_usage_count} calls</p>
                        <p className="text-xs text-muted-foreground">
                          {Number(model.total_tokens).toLocaleString()} tokens
                        </p>
                      </div>
                      <div className="text-right w-24">
                        <p className="text-sm font-semibold text-green-600">
                          ${Number(model.total_cost).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Models Details */}
          {summary && summary.models && summary.models.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">All Models</h2>
              <div className="space-y-2">
                {summary.models.map((model) => (
                  <div key={model.model} className="flex justify-between items-center p-2 rounded hover:bg-muted/50">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">{model.model}</span>
                      <span className="text-xs text-muted-foreground">{model.provider}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold">{model.total_usage_count} calls</p>
                        <p className="text-xs text-muted-foreground">
                          {Number(model.total_tokens).toLocaleString()} tokens
                        </p>
                      </div>
                      <div className="text-right w-24">
                        <p className="text-sm font-semibold text-green-600">
                          ${Number(model.total_cost).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trends Chart Placeholder */}
          {trends.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Trends Over Time</h2>
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                <p>Trends chart will be displayed here (CostChart component)</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {(!summary || summary.total_usage_count === 0) && (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Cpu className="h-16 w-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">No model usage data available</p>
              <p className="text-sm">Run some tasks to see your model usage analytics</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
