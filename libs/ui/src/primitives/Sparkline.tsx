import {
  CHART_TONE_VARS,
  pointsToArea,
  seriesToPoints,
  type ChartTone,
} from './charts';
import './Sparkline.css';

export interface SparklineProps {
  /** The numeric series to plot. Fewer than two points renders nothing. */
  values: readonly number[];
  /** Line color tone; defaults to info (blue). */
  tone?: ChartTone;
  /** Draw a soft area fill under the line. */
  area?: boolean;
  /**
   * Accessible label describing the trend. When omitted the sparkline is
   * treated as decorative (aria-hidden) — pair it with a labeled value.
   */
  ariaLabel?: string;
  /** viewBox width; the SVG scales to its container. */
  width?: number;
  /** viewBox height. */
  height?: number;
  className?: string;
}

/**
 * Compact inline trend line drawn as a single SVG polyline (optionally with a
 * soft area fill), mirroring the `.lazyweb` sparkline. Presentational and
 * data-agnostic; the container controls the rendered size.
 */
export function Sparkline({
  values,
  tone = 'info',
  area = false,
  ariaLabel,
  width = 240,
  height = 36,
  className,
}: Readonly<SparklineProps>) {
  if (values.length < 2) return null;
  const color = CHART_TONE_VARS[tone];
  const points = seriesToPoints(values, width, height);
  const labelled = ariaLabel != null;

  return (
    <svg
      className={`ac-sparkline${className != null ? ` ${className}` : ''}`}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role={labelled ? 'img' : undefined}
      aria-label={ariaLabel}
      aria-hidden={labelled ? undefined : true}
    >
      {area && (
        <polyline
          fill={color}
          fillOpacity="0.08"
          stroke="none"
          points={pointsToArea(points, width, height)}
        />
      )}
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}
