import { useMemo } from 'react';
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

const CHART_METRICS: ChartMetricConfig<MetricType>[] = [
  {
    key: 'completed_specs',
    label: 'Completed Specs',
    color: 'rgb(34, 197, 94)',
    formatValue: (value: number) => value.toFixed(0),
  },
  {
    key: 'time_saved_hours',
    label: 'Time Saved (hours)',
    color: 'rgb(59, 130, 246)',
    formatValue: (value: number) => value.toFixed(1),
  },
  {
    key: 'success_rate',
    label: 'Success Rate (%)',
    color: 'rgb(168, 85, 247)',
    formatValue: (value: number) => (value * 100).toFixed(1),
  },
];

function TrendsHeader() {
  return (
    <div className="flex items-center gap-2 mb-4">
      <TrendingUp className="h-5 w-5 text-accent" />
      <h2 className="text-lg font-semibold text-foreground">Trends Over Time</h2>
    </div>
  );
}

export function TrendsChart({ trends, isLoading = false }: TrendsChartProps) {
  const chartData = useMemo(() => {
    if (!trends || trends.length === 0) return null;

    const dims = createChartDimensions();
    const metrics = CHART_METRICS.map((metric) => {
      const values = trends.map((point) => point[metric.key] as number);
      return buildMetricPaths(metric, values, dims);
    });

    const dateLabels = trends.map((point) => {
      const date = new Date(point.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    return { dims, metrics, dateLabels };
  }, [trends]);

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
      metricConfigs={CHART_METRICS}
      header={<TrendsHeader />}
      isLoading={isLoading}
      loadingText="Loading trends..."
      emptyText="No trend data available"
      emptySubtext="Complete more tasks to see trends over time"
      latestValues={latestValues}
    />
  );
}
