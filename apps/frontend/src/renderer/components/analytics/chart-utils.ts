/**
 * Shared chart utilities for SVG line/area charts.
 *
 * Extracted to reduce duplication between QualityTrendChart and TrendsChart.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChartMetricConfig<K extends string = string> {
  key: K;
  label: string;
  color: string;
  formatValue: (value: number) => string;
}

export interface ChartPoint {
  x: number;
  y: number;
  value: number;
}

export interface ProcessedMetric<K extends string = string> extends ChartMetricConfig<K> {
  points: ChartPoint[];
  pathData: string;
  areaPath: string;
  maxValue: number;
  minValue: number;
}

export interface ChartDimensions {
  width: number;
  height: number;
  padding: { top: number; right: number; bottom: number; left: number };
  chartWidth: number;
  chartHeight: number;
}

// ---------------------------------------------------------------------------
// Dimension helpers
// ---------------------------------------------------------------------------

export function createChartDimensions(
  width = 800,
  height = 300,
  padding = { top: 20, right: 20, bottom: 40, left: 60 },
): ChartDimensions {
  return {
    width,
    height,
    padding,
    chartWidth: width - padding.left - padding.right,
    chartHeight: height - padding.top - padding.bottom,
  };
}

// ---------------------------------------------------------------------------
// Path builders
// ---------------------------------------------------------------------------

/**
 * Build SVG line-path and area-path for a series of numeric values.
 *
 * @param fixedRange - When provided, use a fixed [min, max] range for Y-axis
 *   instead of auto-scaling. Useful for quality scores that are always 0-1.
 */
export function buildMetricPaths<K extends string>(
  metric: ChartMetricConfig<K>,
  values: number[],
  dims: ChartDimensions,
  fixedRange?: [number, number],
): ProcessedMetric<K> {
  if (values.length === 0) {
    return {
      ...metric,
      points: [],
      pathData: '',
      areaPath: '',
      maxValue: fixedRange ? fixedRange[1] : 0,
      minValue: fixedRange ? fixedRange[0] : 0,
    };
  }

  const maxValue = fixedRange ? fixedRange[1] : Math.max(...values);
  const minValue = fixedRange ? fixedRange[0] : Math.min(...values);
  const range = maxValue - minValue || 1;

  const points: ChartPoint[] = values.map((value, index) => {
    const x =
      dims.padding.left + (index / (values.length - 1 || 1)) * dims.chartWidth;
    const y =
      dims.padding.top +
      dims.chartHeight -
      ((value - minValue) / range) * dims.chartHeight;
    return { x, y, value };
  });

  const pathData = points
    .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`)
    .join(' ');

  const lastPt = points[points.length - 1];
  const areaPath = `${pathData} L ${lastPt.x} ${dims.height - dims.padding.bottom} L ${dims.padding.left} ${dims.height - dims.padding.bottom} Z`;

  return { ...metric, points, pathData, areaPath, maxValue, minValue };
}
