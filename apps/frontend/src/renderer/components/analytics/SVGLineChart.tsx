/**
 * Shared SVG line chart component.
 *
 * Reusable chart renderer used by CostChart, TrendsChart, and QualityTrendChart
 * to eliminate duplicated SVG rendering code.
 */
import { useTranslation } from 'react-i18next';
import { Calendar } from 'lucide-react';
import type { ProcessedMetric, ChartDimensions, ChartMetricConfig } from './chart-utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SVGLineChartData<K extends string = string> {
  dims: ChartDimensions;
  metrics: ProcessedMetric<K>[];
  dateLabels: string[];
}

export interface SVGLineChartProps<K extends string = string> {
  /** Pre-processed chart data (dimensions, metrics, date labels). */
  data: SVGLineChartData<K> | null;
  /** Original data length (used for x-axis positioning). */
  dataLength: number;
  /** Metric configs for legend and summary stats. */
  metricConfigs: ChartMetricConfig<K>[];
  /** Header element rendered above the chart. */
  header: React.ReactNode;
  /** Whether data is loading. */
  isLoading?: boolean;
  /** Loading text. */
  loadingText?: string;
  /** Empty state text. */
  emptyText?: string;
  /** Empty state subtext. */
  emptySubtext?: string;
  /** Latest raw values for summary stats (keyed by metric key). */
  latestValues?: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ChartCardShell({ header, children }: { header: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {header}
      {children}
    </div>
  );
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-80 flex items-center justify-center">
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function SVGLineChart<K extends string = string>({
  data,
  dataLength,
  metricConfigs,
  header,
  isLoading = false,
  loadingText,
  emptyText,
  emptySubtext,
  latestValues,
}: SVGLineChartProps<K>) {
  const { t } = useTranslation(['model-usage']);
  const resolvedLoadingText = loadingText ?? t('model-usage:chart.loading');
  const resolvedEmptyText = emptyText ?? t('model-usage:chart.emptyTitle');
  const resolvedEmptySubtext = emptySubtext ?? t('model-usage:chart.emptySubtitle');
  if (isLoading) {
    return (
      <ChartCardShell header={header}>
        <CenteredMessage>
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
          <p className="text-sm">{resolvedLoadingText}</p>
        </CenteredMessage>
      </ChartCardShell>
    );
  }

  if (!data) {
    return (
      <ChartCardShell header={header}>
        <CenteredMessage>
          <Calendar className="h-12 w-12 opacity-50" />
          <p className="text-sm">{resolvedEmptyText}</p>
          <p className="text-xs">{resolvedEmptySubtext}</p>
        </CenteredMessage>
      </ChartCardShell>
    );
  }

  const { dims, metrics: processedMetrics, dateLabels } = data;

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {/* Header with Legend */}
      <div className="flex items-center justify-between mb-6">
        {header}
        <div className="flex items-center gap-4">
          {metricConfigs.map((m) => (
            <div key={m.key} className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: m.color }} />
              <span className="text-xs text-muted-foreground">{m.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG Chart */}
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${dims.width} ${dims.height}`}
          className="w-full h-auto"
          style={{ minHeight: '300px' }}
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((f) => {
            const y = dims.padding.top + dims.chartHeight * (1 - f);
            return (
              <line key={f} x1={dims.padding.left} y1={y} x2={dims.width - dims.padding.right} y2={y}
                stroke="currentColor" strokeWidth="1" opacity="0.1" className="text-muted-foreground" />
            );
          })}

          {/* Axes */}
          <line x1={dims.padding.left} y1={dims.height - dims.padding.bottom}
            x2={dims.width - dims.padding.right} y2={dims.height - dims.padding.bottom}
            stroke="currentColor" strokeWidth="2" className="text-border" />
          <line x1={dims.padding.left} y1={dims.padding.top}
            x2={dims.padding.left} y2={dims.height - dims.padding.bottom}
            stroke="currentColor" strokeWidth="2" className="text-border" />

          {/* Date labels */}
          {dateLabels.map((label, i) => {
            const show = i === 0 || i === dateLabels.length - 1 ||
              (dateLabels.length > 5 && i % Math.ceil(dateLabels.length / 5) === 0);
            if (!show) return null;
            const x = dims.padding.left + (i / (dataLength - 1 || 1)) * dims.chartWidth;
            return (
              <text key={i} x={x} y={dims.height - dims.padding.bottom + 20}
                textAnchor="middle" fontSize="10" className="fill-muted-foreground">{label}</text>
            );
          })}

          {/* Metric lines */}
          {processedMetrics.map((metric) => (
            <g key={metric.key}>
              <path d={metric.areaPath} fill={metric.color} opacity="0.1" />
              <path d={metric.pathData} fill="none" stroke={metric.color}
                strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
              {metric.points.map((pt, i) => (
                <g key={i}>
                  <circle cx={pt.x} cy={pt.y} r="4" fill={metric.color}
                    className="cursor-pointer transition-transform hover:scale-125" />
                  <title>{dateLabels[i]}: {metric.formatValue(pt.value)} {metric.label}</title>
                </g>
              ))}
            </g>
          ))}
        </svg>
      </div>

      {/* Summary Stats */}
      {latestValues && (
        <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t border-border">
          {metricConfigs.map((metric) => {
            const pm = processedMetrics.find((m) => m.key === metric.key);
            if (!pm) return null;
            const latest = latestValues[metric.key] ?? 0;
            return (
              <div key={metric.key} className="text-center">
                <p className="text-xs text-muted-foreground mb-1">{metric.label}</p>
                <p className="text-xl font-bold" style={{ color: metric.color }}>
                  {metric.formatValue(latest)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Range: {metric.formatValue(pm.minValue)} - {metric.formatValue(pm.maxValue)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
