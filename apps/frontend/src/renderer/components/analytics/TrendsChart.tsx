import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp } from 'lucide-react';
import type { ProductivityTrendPoint } from '../../../shared/types/productivity-analytics';
import type { ChartMetricConfig } from './chart-utils';
import { createChartDimensions, buildMetricPaths } from './chart-utils';
import { SVGLineChart } from './SVGLineChart';

interface TrendsChartProps {
  trends: ProductivityTrendPoint[];
  isLoading?: boolean;
}

type MetricType = 'completed_specs' | 'time_saved_hours' | 'success_rate';

function TrendsHeader() {
  const { t } = useTranslation(['analytics']);
  return (
    <div className="flex items-center gap-2 mb-4">
      <TrendingUp className="h-5 w-5 text-accent" />
      <h2 className="text-lg font-semibold text-foreground">{t('analytics:trends.title')}</h2>
    </div>
  );
}

export function TrendsChart({ trends, isLoading = false }: TrendsChartProps) {
  const { t, i18n } = useTranslation(['analytics']);

  const chartMetrics: ChartMetricConfig<MetricType>[] = useMemo(() => [
    {
      key: 'completed_specs',
      label: t('analytics:trends.completedSpecs'),
      color: 'rgb(34, 197, 94)',
      formatValue: (value: number) => value.toFixed(0),
    },
    {
      key: 'time_saved_hours',
      label: t('analytics:trends.timeSaved'),
      color: 'rgb(59, 130, 246)',
      formatValue: (value: number) => value.toFixed(1),
    },
    {
      key: 'success_rate',
      label: t('analytics:trends.successRate'),
      color: 'rgb(168, 85, 247)',
      formatValue: (value: number) => (value * 100).toFixed(1),
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
      completed_specs: last.completed_specs as number,
      time_saved_hours: last.time_saved_hours as number,
      success_rate: last.success_rate as number,
    };
  }, [trends]);

  return (
    <SVGLineChart
      data={chartData}
      dataLength={trends?.length ?? 0}
      metricConfigs={chartMetrics}
      header={<TrendsHeader />}
      isLoading={isLoading}
      loadingText={t('analytics:trends.loading')}
      emptyText={t('analytics:trends.empty')}
      emptySubtext={t('analytics:trends.emptySubtext')}
      latestValues={latestValues}
    />
  );
}
