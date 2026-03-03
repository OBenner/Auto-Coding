import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { DollarSign } from 'lucide-react';
import type { ModelUsageTrendPoint } from '../../../shared/types/model-usage';
import type { ChartMetricConfig } from '../analytics/chart-utils';
import { createChartDimensions, buildMetricPaths } from '../analytics/chart-utils';
import { SVGLineChart } from '../analytics/SVGLineChart';

interface CostChartProps {
  trends: ModelUsageTrendPoint[];
  isLoading?: boolean;
}

type MetricType = 'total_cost' | 'total_tokens' | 'usage_count';

function ChartHeader() {
  const { t } = useTranslation(['model-usage']);
  return (
    <div className="flex items-center gap-2 mb-4">
      <DollarSign className="h-5 w-5 text-accent" />
      <h2 className="text-lg font-semibold text-foreground">{t('model-usage:costChart.title')}</h2>
    </div>
  );
}

export function CostChart({ trends, isLoading = false }: CostChartProps) {
  const { t, i18n } = useTranslation(['model-usage']);

  const chartMetrics: ChartMetricConfig<MetricType>[] = useMemo(() => [
    {
      key: 'total_cost',
      label: t('model-usage:costChart.cost'),
      color: 'rgb(34, 197, 94)',
      formatValue: (value: number) => `$${value.toFixed(2)}`,
    },
    {
      key: 'total_tokens',
      label: t('model-usage:costChart.tokens'),
      color: 'rgb(59, 130, 246)',
      formatValue: (value: number) => value.toLocaleString(),
    },
    {
      key: 'usage_count',
      label: t('model-usage:costChart.apiCalls'),
      color: 'rgb(168, 85, 247)',
      formatValue: (value: number) => value.toFixed(0),
    },
  ], [t]);

  const chartData = useMemo(() => {
    if (!trends || trends.length === 0) return null;

    const dims = createChartDimensions();
    const metrics = chartMetrics.map((metric) => {
      const values = trends.map((point) => point[metric.key] as number);
      return buildMetricPaths(metric, values, dims);
    });

    const locale = i18n.language || 'en-US';
    const dateLabels = trends.map((point) => {
      const date = new Date(point.date);
      return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
    });

    return { dims, metrics, dateLabels };
  }, [trends, chartMetrics, i18n.language]);

  const latestValues = useMemo(() => {
    if (!trends || trends.length === 0) return undefined;
    const last = trends[trends.length - 1];
    return {
      total_cost: last.total_cost as number,
      total_tokens: last.total_tokens as number,
      usage_count: last.usage_count as number,
    };
  }, [trends]);

  return (
    <SVGLineChart
      data={chartData}
      dataLength={trends?.length ?? 0}
      metricConfigs={chartMetrics}
      header={<ChartHeader />}
      isLoading={isLoading}
      loadingText={t('model-usage:costChart.loading')}
      emptyText={t('model-usage:costChart.empty')}
      emptySubtext={t('model-usage:costChart.emptySubtext')}
      latestValues={latestValues}
    />
  );
}
