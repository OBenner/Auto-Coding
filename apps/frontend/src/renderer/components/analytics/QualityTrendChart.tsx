import { useMemo } from 'react';
import { TrendingUp, AlertTriangle } from 'lucide-react';
import type { QualityScore } from '../../stores/quality-store';

interface QualityTrendChartProps {
  scores: QualityScore[];
  isLoading?: boolean;
}

type MetricType = 'composite_score' | 'test_pass_rate' | 'acceptance_criteria_met' | 'user_approval_rate';

interface ChartMetric {
  key: MetricType;
  label: string;
  color: string;
  formatValue: (value: number) => string;
}

const CHART_METRICS: ChartMetric[] = [
  {
    key: 'composite_score',
    label: 'Overall Quality',
    color: 'rgb(34, 197, 94)', // green-500
    formatValue: (value: number) => (value * 100).toFixed(1) + '%',
  },
  {
    key: 'test_pass_rate',
    label: 'Test Pass Rate',
    color: 'rgb(59, 130, 246)', // blue-500
    formatValue: (value: number) => (value * 100).toFixed(1) + '%',
  },
  {
    key: 'acceptance_criteria_met',
    label: 'Acceptance Criteria',
    color: 'rgb(168, 85, 247)', // purple-500
    formatValue: (value: number) => (value * 100).toFixed(1) + '%',
  },
  {
    key: 'user_approval_rate',
    label: 'User Approval',
    color: 'rgb(245, 158, 11)', // amber-500
    formatValue: (value: number) => (value * 100).toFixed(1) + '%',
  },
];

export function QualityTrendChart({ scores, isLoading = false }: QualityTrendChartProps) {
  // Calculate chart dimensions and data
  const chartData = useMemo(() => {
    if (!scores || scores.length === 0) return null;

    const width = 800;
    const height = 300;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Sort scores by timestamp
    const sortedScores = [...scores].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    // Process data for each metric
    // Values are kept in their original scale (0..1);
    // conversion to display units (percentage) happens only in formatValue.
    const processedMetrics = CHART_METRICS.map((metric) => {
      const values = sortedScores.map((score) => {
        const raw = score[metric.key];
        const v = Number(raw ?? 0);
        return Number.isFinite(v) ? v : 0;
      });

      const maxValue = Math.max(...values);
      const minValue = Math.min(...values);
      const range = maxValue - minValue || 1; // Avoid division by zero

      // Generate SVG path
      const points = sortedScores.map((score, index) => {
        const x = padding.left + (index / (sortedScores.length - 1 || 1)) * chartWidth;
        const raw = score[metric.key];
        const value = Number.isFinite(Number(raw)) ? Number(raw) : 0;
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
    const dateLabels = sortedScores.map((score) => {
      const date = new Date(score.timestamp);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    // Calculate quality status
    const latestScore = sortedScores[sortedScores.length - 1];
    const isHighQuality = latestScore.is_high_quality;
    const isLowQuality = latestScore.is_low_quality;

    return {
      width,
      height,
      padding,
      chartWidth,
      chartHeight,
      metrics: processedMetrics,
      dateLabels,
      isHighQuality,
      isLowQuality,
    };
  }, [scores]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">Quality Trends Over Time</h2>
        </div>
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
            <p className="text-sm text-muted-foreground">Loading quality trends...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!scores || scores.length === 0 || !chartData) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">Quality Trends Over Time</h2>
        </div>
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <AlertTriangle className="h-12 w-12 opacity-50" />
            <p className="text-sm">No quality data available</p>
            <p className="text-xs">Complete more sessions to see quality trends</p>
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
          <h2 className="text-lg font-semibold text-foreground">Quality Trends Over Time</h2>
          {chartData.isLowQuality && (
            <span className="ml-2 px-2 py-1 text-xs font-medium rounded-full bg-destructive/10 text-destructive">
              Low Quality Detected
            </span>
          )}
          {chartData.isHighQuality && (
            <span className="ml-2 px-2 py-1 text-xs font-medium rounded-full bg-green-500/10 text-green-500">
              High Quality
            </span>
          )}
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

          {/* Y-axis labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
            const y = chartData.padding.top + chartData.chartHeight * (1 - fraction);
            return (
              <text
                key={fraction}
                x={chartData.padding.left - 10}
                y={y}
                textAnchor="end"
                dominantBaseline="middle"
                className="text-xs fill-muted-foreground"
              >
                {(fraction * 100).toFixed(0)}%
              </text>
            );
          })}

          {/* Chart lines and areas */}
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
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Data points */}
              {metric.points.map((point, index) => (
                <circle
                  key={index}
                  cx={point.x}
                  cy={point.y}
                  r="4"
                  fill={metric.color}
                  className="cursor-pointer transition-transform hover:scale-125"
                >
                  <title>{`${metric.label}: ${metric.formatValue(point.value)}`}</title>
                </circle>
              ))}
            </g>
          ))}

          {/* X-axis labels */}
          {chartData.dateLabels.map((label, index) => {
            const x =
              chartData.padding.left +
              (index / (chartData.dateLabels.length - 1 || 1)) * chartData.chartWidth;
            return (
              <text
                key={index}
                x={x}
                y={chartData.height - chartData.padding.bottom + 20}
                textAnchor="middle"
                className="text-xs fill-muted-foreground"
              >
                {label}
              </text>
            );
          })}
        </svg>
      </div>

      {/* Summary Stats */}
      <div className="mt-6 grid grid-cols-4 gap-4">
        {CHART_METRICS.map((metric) => {
          const metricData = chartData.metrics.find((m) => m.key === metric.key);
          if (!metricData) return null;

          const latestValue = metricData.points[metricData.points.length - 1]?.value || 0;

          return (
            <div key={metric.key} className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: metric.color }}
                />
                <span className="text-xs text-muted-foreground">{metric.label}</span>
              </div>
              <p className="text-lg font-semibold text-foreground">
                {metric.formatValue(latestValue)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
