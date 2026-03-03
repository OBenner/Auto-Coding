import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Loader2, RefreshCw, FileText, Calendar, Cpu } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import { ModelUsageCard } from './ModelUsageCard';
import { CostChart } from './CostChart';
import type {
  ModelUsageSummary,
  ModelUsageTrendPoint,
  ModelMetrics,
  ModelUsageExportOptions,
  ModelUsageFilter
} from '../../../shared/types/model-usage';

interface ModelUsageDashboardProps {
  projectId: string;
}

type TimeRange = 'all' | '7d' | '30d' | '90d';

function ModelRow({ model }: { model: ModelMetrics }) {
  const { t } = useTranslation(['model-usage']);
  return (
    <div className="flex justify-between items-center p-2 rounded hover:bg-muted/50">
      <div className="flex flex-col">
        <span className="text-sm font-medium">{model.model}</span>
        <span className="text-xs text-muted-foreground">{model.provider}</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-semibold">{model.total_usage_count} {t('model-usage:dashboard.calls')}</p>
          <p className="text-xs text-muted-foreground">
            {Number(model.total_tokens).toLocaleString()} {t('model-usage:dashboard.tokens')}
          </p>
        </div>
        <div className="text-right w-24">
          <p className="text-sm font-semibold text-green-600">
            ${Number(model.total_cost).toFixed(2)}
          </p>
        </div>
      </div>
    </div>
  );
}

function ModelListSection({ title, models, limit }: { title: string; models: ModelMetrics[]; limit?: number }) {
  if (!models || models.length === 0) return null;
  const displayModels = limit ? models.slice(0, limit) : models;
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <div className="space-y-2">
        {displayModels.map((model) => (
          <ModelRow key={`${model.provider}:${model.model}`} model={model} />
        ))}
      </div>
    </div>
  );
}

export function ModelUsageDashboard({ projectId }: ModelUsageDashboardProps) {
  const { t } = useTranslation(['model-usage']);
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
      let allSucceeded = true;

      // Load summary analytics
      const summaryResult = await window.electronAPI.getModelUsageSummary(
        projectId,
        dateFilter
      );

      if (summaryResult.success && summaryResult.data) {
        setSummary(summaryResult.data);
      } else {
        allSucceeded = false;
        console.error('Failed to load model usage summary:', summaryResult.error);
        toast({
          title: t('model-usage:dashboard.toast.warning'),
          description: summaryResult.error || t('model-usage:dashboard.toast.summaryFailed'),
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
        allSucceeded = false;
        console.error('Failed to load model usage trends:', trendsResult.error);
      }

      if (showRefreshToast && allSucceeded) {
        toast({
          title: t('model-usage:dashboard.toast.refreshed'),
          description: t('model-usage:dashboard.toast.refreshedDescription'),
        });
      }
    } catch (error) {
      console.error('Error loading model usage data:', error);
      toast({
        title: t('model-usage:dashboard.toast.error'),
        description: t('model-usage:dashboard.toast.loadError'),
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId, timeRange, getDateFilter, toast, t]);

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
          title: t('model-usage:dashboard.toast.exportSuccess'),
          description: t('model-usage:dashboard.toast.exportSuccessDescription', { path: result.data }),
        });
      } else {
        toast({
          title: t('model-usage:dashboard.toast.exportFailed'),
          description: result.error || t('model-usage:dashboard.toast.exportFailedDescription'),
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error exporting analytics:', error);
      toast({
        title: t('model-usage:dashboard.toast.exportError'),
        description: t('model-usage:dashboard.toast.exportErrorDescription'),
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  }, [projectId, getDateFilter, toast, t]);

  // Handle time range change
  const handleTimeRangeChange = useCallback((range: TimeRange) => {
    setTimeRange(range);
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t('model-usage:dashboard.loadingAnalytics')}</p>
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
              <h1 className="text-2xl font-semibold text-foreground">{t('model-usage:dashboard.title')}</h1>
              <p className="text-sm text-muted-foreground">
                {t('model-usage:dashboard.subtitle')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Time Range Filter */}
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
                  {range === 'all' ? t('model-usage:dashboard.timeRange.all') : range}
                </Button>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              {t('model-usage:dashboard.refresh')}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={isExporting}
            >
              <FileText className="h-4 w-4 mr-2" />
              {t('model-usage:dashboard.exportJson')}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={isExporting}
            >
              <Download className="h-4 w-4 mr-2" />
              {t('model-usage:dashboard.exportCsv')}
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
              <h2 className="text-lg font-semibold mb-4">{t('model-usage:dashboard.summaryMetrics')}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: t('model-usage:dashboard.totalApiCalls'), value: String(summary.total_usage_count ?? 0) },
                  { label: t('model-usage:dashboard.totalTokens'), value: Number(summary.total_tokens ?? 0).toLocaleString() },
                  { label: t('model-usage:dashboard.totalCost'), value: `$${Number(summary.total_cost ?? 0).toFixed(2)}`, className: 'text-green-600' },
                  { label: t('model-usage:dashboard.modelsUsed'), value: String(summary.models?.length ?? 0) },
                ].map((stat) => (
                  <div key={stat.label}>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <p className={`text-2xl font-bold ${stat.className ?? ''}`}>{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model Usage by Agent */}
          {summary && summary.agents && summary.agents.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">{t('model-usage:dashboard.usageByAgent')}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...summary.agents]
                  .sort((a, b) => b.total_usage_count - a.total_usage_count)
                  .map((agent, index) => (
                    <ModelUsageCard
                      key={agent.agent_type}
                      agent={agent}
                      showRank
                      rank={index + 1}
                    />
                  ))}
              </div>
            </div>
          )}

          {/* Top Models by Usage */}
          {summary && <ModelListSection title={t('model-usage:dashboard.topByUsage')} models={summary.top_models_by_usage} limit={5} />}

          {/* Top Models by Cost */}
          {summary && <ModelListSection title={t('model-usage:dashboard.topByCost')} models={summary.top_models_by_cost} limit={5} />}

          {/* All Models Details */}
          {summary && <ModelListSection title={t('model-usage:dashboard.allModels')} models={summary.models} />}

          {/* Cost Trends Chart */}
          <CostChart trends={trends} />

          {/* Empty State */}
          {(!summary || summary.total_usage_count === 0) && (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Cpu className="h-16 w-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">{t('model-usage:dashboard.empty.title')}</p>
              <p className="text-sm">{t('model-usage:dashboard.empty.description')}</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
