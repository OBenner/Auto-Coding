/**
 * Shared SVG chart primitives for line/area charts.
 *
 * Extracted to reduce duplication between QualityTrendChart and TrendsChart.
 */

import type { ChartDimensions, ProcessedMetric } from './chart-utils';

// ---------------------------------------------------------------------------
// Grid & Axes
// ---------------------------------------------------------------------------

const GRID_FRACTIONS = [0, 0.25, 0.5, 0.75, 1] as const;

interface ChartGridProps {
  dims: ChartDimensions;
  /** Optional Y-axis label formatter. When provided, labels are rendered. */
  formatYLabel?: (fraction: number) => string;
}

export function ChartGrid({ dims, formatYLabel }: ChartGridProps) {
  return (
    <>
      {/* Horizontal grid lines */}
      {GRID_FRACTIONS.map((fraction) => {
        const y = dims.padding.top + dims.chartHeight * (1 - fraction);
        return (
          <line
            key={fraction}
            x1={dims.padding.left}
            y1={y}
            x2={dims.width - dims.padding.right}
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
        x1={dims.padding.left}
        y1={dims.height - dims.padding.bottom}
        x2={dims.width - dims.padding.right}
        y2={dims.height - dims.padding.bottom}
        stroke="currentColor"
        strokeWidth="2"
        className="text-border"
      />

      {/* Y-axis */}
      <line
        x1={dims.padding.left}
        y1={dims.padding.top}
        x2={dims.padding.left}
        y2={dims.height - dims.padding.bottom}
        stroke="currentColor"
        strokeWidth="2"
        className="text-border"
      />

      {/* Y-axis labels (optional) */}
      {formatYLabel &&
        GRID_FRACTIONS.map((fraction) => {
          const y = dims.padding.top + dims.chartHeight * (1 - fraction);
          return (
            <text
              key={`label-${fraction}`}
              x={dims.padding.left - 10}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              className="text-xs fill-muted-foreground"
            >
              {formatYLabel(fraction)}
            </text>
          );
        })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Metric lines / areas / data-points
// ---------------------------------------------------------------------------

interface MetricSeriesProps {
  metric: ProcessedMetric;
  dateLabels?: string[];
}

export function MetricSeries({ metric, dateLabels }: MetricSeriesProps) {
  return (
    <g>
      {/* Area fill */}
      <path d={metric.areaPath} fill={metric.color} opacity="0.1" />

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
          <title>
            {dateLabels?.[index] ? `${dateLabels[index]}: ` : ''}
            {`${metric.label}: ${metric.formatValue(point.value)}`}
          </title>
        </circle>
      ))}
    </g>
  );
}
