import { useMemo } from 'react';
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

const CHART_METRICS: ChartMetricConfig<MetricType>[] = [
  {
    key: 'total_cost',
    label: 'Cost ($)',
    color: 'rgb(34, 197, 94)',
    formatValue: (value: number) => `$${value.toFixed(2)}`,
  },
  {
    key: 'total_tokens',
    label: 'Tokens',
    color: 'rgb(59, 130, 246)',
    formatValue: (value: number) => value.toLocaleString(),
  },
  {
    key: 'usage_count',
    label: 'API Calls',
    color: 'rgb(168, 85, 247)',
    formatValue: (value: number) => value.toFixed(0),
  },
];

function ChartHeader() {
  return (
    <div className="flex items-center gap-2 mb-4">
      <DollarSign className="h-5 w-5 text-accent" />
      <h2 className="text-lg font-semibold text-foreground">Cost Trends Over Time</h2>
    </div>
  );
}

export function CostChart({ trends, isLoading = false }: CostChartProps) {
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
      total_cost: last.total_cost as number,
      total_tokens: last.total_tokens as number,
      usage_count: last.usage_count as number,
    };
  }, [trends]);

  return (
    <SVGLineChart
      data={chartData}
      dataLength={trends?.length ?? 0}
      metricConfigs={CHART_METRICS}
      header={<ChartHeader />}
      isLoading={isLoading}
      loadingText="Loading cost trends..."
      emptyText="No cost trend data available"
      emptySubtext="Run more tasks to see cost trends over time"
      latestValues={latestValues}
    />
  );
}
