/** Shared chart tones → CSS token color, used by Sparkline and LineChart. */
export type ChartTone = 'info' | 'good' | 'warn' | 'bad' | 'neutral';

export const CHART_TONE_VARS: Record<ChartTone, string> = {
  info: 'var(--blue)',
  good: 'var(--green)',
  warn: 'var(--amber)',
  bad: 'var(--red)',
  neutral: 'var(--quiet)',
};

/**
 * Map a numeric series to evenly-spaced "x,y" SVG points, normalized so the
 * min value sits near the bottom and the max near the top of `height` (with a
 * small vertical padding). A flat series is drawn as a centered line.
 */
export function seriesToPoints(
  values: readonly number[],
  width: number,
  height: number,
  padding = 3,
): string {
  if (values.length === 0) return '';
  const usable = Math.max(1, height - padding * 2);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  const stepX = values.length > 1 ? width / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = values.length > 1 ? index * stepX : width / 2;
      // Invert Y (SVG origin is top-left); flat series centers vertically.
      const ratio = span === 0 ? 0.5 : (value - min) / span;
      const y = padding + (1 - ratio) * usable;
      return `${round(x)},${round(y)}`;
    })
    .join(' ');
}

/** Close a line's points into an area polygon down to the baseline. */
export function pointsToArea(
  points: string,
  width: number,
  height: number,
): string {
  if (points === '') return '';
  return `${points} ${round(width)},${round(height)} 0,${round(height)}`;
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
