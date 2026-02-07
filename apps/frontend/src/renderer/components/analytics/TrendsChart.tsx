import { useMemo } from 'react';
import { TrendingUp, Calendar } from 'lucide-react';
import type { ProductivityTrendPoint } from '../../../shared/types/productivity-analytics';

interface TrendsChartProps {
  trends: ProductivityTrendPoint[];
  isLoading?: boolean;
}

type MetricType = 'completed_specs' | 'time_saved_hours' | 'success_rate';

interface ChartMetric {
  key: MetricType;
  label: string;
  color: string;
  formatValue: (value: number) => string;
}

const CHART_METRICS: ChartMetric[] = [
  {
    key: 'completed_specs',
    label: 'Completed Specs',
    color: 'rgb(34, 197, 94)', // green-500
    formatValue: (value: number) => value.toFixed(0),
  },
  {
    key: 'time_saved_hours',
    label: 'Time Saved (hours)',
    color: 'rgb(59, 130, 246)', // blue-500
    formatValue: (value: number) => value.toFixed(1),
  },
  {
    key: 'success_rate',
    label: 'Success Rate (%)',
    color: 'rgb(168, 85, 247)', // purple-500
    formatValue: (value: number) => (value * 100).toFixed(1),
  },
];

export function TrendsChart({ trends, isLoading = false }: TrendsChartProps) {
  // Calculate chart dimensions and data
  const chartData = useMemo(() => {
    if (!trends || trends.length === 0) return null;

    const width = 800;
    const height = 300;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Process data for each metric
    const processedMetrics = CHART_METRICS.map((metric) => {
      const values = trends.map((point) => {
        if (metric.key === 'success_rate') {
          return point.success_rate * 100; // Convert to percentage
        }
        return point[metric.key] as number;
      });

      const maxValue = Math.max(...values);
      const minValue = Math.min(...values);
      const range = maxValue - minValue || 1; // Avoid division by zero

      // Generate SVG path
      const points = trends.map((point, index) => {
        const x = padding.left + (index / (trends.length - 1 || 1)) * chartWidth;
        const value = metric.key === 'success_rate' ? point.success_rate * 100 : (point[metric.key] as number);
        const y = padding.top + chartHeight - ((value - minValue) / range) * chartHeight;
        return { x, y, value };
      });

      const pathData = points
        .map((point, index) => {
          const command = index === 0 ? 'M' : 'L';
          return `${command} ${point.x} ${point.y}`;
        })
        .join(' ');

      // Create area path (for fill)
      const areaPath = `${pathData} L ${points[points.length - 1].x} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`;

      return {
        ...metric,
        points,
        pathData,
        areaPath,
        maxValue,
        minValue,
      };
    });

    // Format dates for x-axis
    const dateLabels = trends.map((point) => {
      const date = new Date(point.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    return {
      width,
      height,
      padding,
      chartWidth,
      chartHeight,
      metrics: processedMetrics,
      dateLabels,
    };
  }, [trends]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">Trends Over Time</h2>
        </div>
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
            <p className="text-sm text-muted-foreground">Loading trends...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!trends || trends.length === 0 || !chartData) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">Trends Over Time</h2>
        </div>
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <Calendar className="h-12 w-12 opacity-50" />
            <p className="text-sm">No trend data available</p>
            <p className="text-xs">Complete more tasks to see trends over time</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">Trends Over Time</h2>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4">
          {CHART_METRICS.map((metric) => (
            <div key={metric.key} className="flex items-center gap-2">
              <div
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: metric.color }}
              />
              <span className="text-xs text-muted-foreground">{metric.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Chart Container */}
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${chartData.width} ${chartData.height}`}
          className="w-full h-auto"
          style={{ minHeight: '300px' }}
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
            const y = chartData.padding.top + chartData.chartHeight * (1 - fraction);
            return (
              <line
                key={fraction}
                x1={chartData.padding.left}
                y1={y}
                x2={chartData.width - chartData.padding.right}
                y2={y}
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.1"
                className="text-muted-foreground"
              />
            );
          })}

          {/* X-axis */}
          <line
            x1={chartData.padding.left}
            y1={chartData.height - chartData.padding.bottom}
            x2={chartData.width - chartData.padding.right}
            y2={chartData.height - chartData.padding.bottom}
            stroke="currentColor"
            strokeWidth="2"
            className="text-border"
          />

          {/* Y-axis */}
          <line
            x1={chartData.padding.left}
            y1={chartData.padding.top}
            x2={chartData.padding.left}
            y2={chartData.height - chartData.padding.bottom}
            stroke="currentColor"
            strokeWidth="2"
            className="text-border"
          />

          {/* Date labels (X-axis) */}
          {chartData.dateLabels.map((label, index) => {
            // Show fewer labels on small datasets
            const showLabel =
              index === 0 ||
              index === chartData.dateLabels.length - 1 ||
              (chartData.dateLabels.length > 5 && index % Math.ceil(chartData.dateLabels.length / 5) === 0);

            if (!showLabel) return null;

            const x = chartData.padding.left + (index / (trends.length - 1 || 1)) * chartData.chartWidth;
            return (
              <text
                key={index}
                x={x}
                y={chartData.height - chartData.padding.bottom + 20}
                textAnchor="middle"
                fontSize="10"
                className="fill-muted-foreground"
              >
                {label}
              </text>
            );
          })}

          {/* Plot lines for each metric */}
          {chartData.metrics.map((metric) => (
            <g key={metric.key}>
              {/* Area fill */}
              <path
                d={metric.areaPath}
                fill={metric.color}
                opacity="0.1"
              />

              {/* Line */}
              <path
                d={metric.pathData}
                fill="none"
                stroke={metric.color}
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
              />

              {/* Data points */}
              {metric.points.map((point, index) => (
                <g key={index}>
                  <circle
                    cx={point.x}
                    cy={point.y}
                    r="4"
                    fill={metric.color}
                    className="hover:r-6 transition-all"
                  />
                  {/* Tooltip on hover (simplified) */}
                  <title>
                    {chartData.dateLabels[index]}: {metric.formatValue(point.value)} {metric.label}
                  </title>
                </g>
              ))}
            </g>
          ))}
        </svg>
      </div>

      {/* Summary Stats Below Chart */}
      <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t border-border">
        {CHART_METRICS.map((metric) => {
          const metricData = chartData.metrics.find((m) => m.key === metric.key);
          if (!metricData) return null;

          const latestValue = trends[trends.length - 1][metric.key] as number;
          const displayValue = metric.key === 'success_rate' ? latestValue * 100 : latestValue;

          return (
            <div key={metric.key} className="text-center">
              <p className="text-xs text-muted-foreground mb-1">{metric.label}</p>
              <p className="text-xl font-bold" style={{ color: metric.color }}>
                {metric.formatValue(displayValue)}
              </p>
              <p className="text-xs text-muted-foreground">
                Range: {metric.formatValue(metricData.minValue)} - {metric.formatValue(metricData.maxValue)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
