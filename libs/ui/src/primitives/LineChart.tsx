import { CHART_TONE_VARS, type ChartTone } from './charts';
import './LineChart.css';

export interface LineChartSeries {
  label: string;
  values: readonly number[];
  tone?: ChartTone;
}

export interface LineChartProps {
  /** One or more series, plotted on a shared y-scale. */
  series: readonly LineChartSeries[];
  /** Optional x-axis tick labels (rendered evenly across the width). */
  xLabels?: readonly string[];
  /** Number of horizontal grid lines. */
  gridLines?: number;
  /** Show a legend row above the chart. */
  showLegend?: boolean;
  /** Accessible label; when omitted the chart svg is decorative (aria-hidden). */
  ariaLabel?: string;
  /** viewBox width. */
  width?: number;
  /** viewBox height (chart plot area, excluding the axis-label row). */
  height?: number;
  className?: string;
}

const PLOT_PADDING = 8;
const AXIS_ROW = 18;

/**
 * Multi-series line chart drawn as SVG polylines over a dashed grid, mirroring
 * the `.lazyweb` line-chart. All series share one y-scale so they compare
 * directly. Presentational and data-agnostic.
 */
export function LineChart({
  series,
  xLabels,
  gridLines = 4,
  showLegend = false,
  ariaLabel,
  width = 760,
  height = 220,
  className,
}: Readonly<LineChartProps>) {
  const drawable = series.filter((s) => s.values.length >= 2);
  const allValues = drawable.flatMap((s) => s.values);
  const min = allValues.length > 0 ? Math.min(...allValues) : 0;
  const max = allValues.length > 0 ? Math.max(...allValues) : 1;
  const span = max - min;
  const plotHeight = height - PLOT_PADDING * 2;

  const toPoints = (values: readonly number[]): string => {
    const stepX = values.length > 1 ? width / (values.length - 1) : 0;
    return values
      .map((value, index) => {
        const x = index * stepX;
        const ratio = span === 0 ? 0.5 : (value - min) / span;
        const y = PLOT_PADDING + (1 - ratio) * plotHeight;
        return `${round(x)},${round(y)}`;
      })
      .join(' ');
  };

  const totalHeight = xLabels != null ? height + AXIS_ROW : height;
  const labelled = ariaLabel != null;

  return (
    <div className={`ac-linechart${className != null ? ` ${className}` : ''}`}>
      {showLegend && (
        <div className="ac-linechart__legend">
          {series.map((s) => (
            <span key={s.label} className="ac-linechart__legend-item">
              <span
                aria-hidden="true"
                className="ac-linechart__swatch"
                style={{ background: CHART_TONE_VARS[s.tone ?? 'info'] }}
              />
              {s.label}
            </span>
          ))}
        </div>
      )}
      <svg
        className="ac-linechart__svg"
        viewBox={`0 0 ${width} ${totalHeight}`}
        preserveAspectRatio="none"
        role={labelled ? 'img' : undefined}
        aria-label={ariaLabel}
        aria-hidden={labelled ? undefined : true}
      >
        <g
          stroke="var(--line)"
          strokeWidth="1"
          strokeDasharray="2 4"
          opacity="0.7"
        >
          {Array.from({ length: gridLines }, (_, i) => {
            const y = PLOT_PADDING + (plotHeight * (i + 1)) / (gridLines + 1);
            return <line key={i} x1="0" y1={round(y)} x2={width} y2={round(y)} />;
          })}
        </g>

        {drawable.map((s) => (
          <polyline
            key={s.label}
            fill="none"
            stroke={CHART_TONE_VARS[s.tone ?? 'info']}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={toPoints(s.values)}
          />
        ))}

        {xLabels != null && xLabels.length > 0 && (
          <g
            fill="var(--quiet)"
            fontSize="10"
            fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
          >
            {xLabels.map((label, index) => {
              const x =
                xLabels.length > 1
                  ? (width * index) / (xLabels.length - 1)
                  : width / 2;
              const anchor = tickAnchor(index, xLabels.length);
              return (
                <text
                  key={label}
                  x={round(x)}
                  y={height + AXIS_ROW - 4}
                  textAnchor={anchor}
                >
                  {label}
                </text>
              );
            })}
          </g>
        )}
      </svg>
    </div>
  );
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}

/** Edge ticks anchor to the plot edges so labels don't overflow the viewBox. */
function tickAnchor(index: number, count: number): 'start' | 'middle' | 'end' {
  if (index === 0) return 'start';
  if (index === count - 1) return 'end';
  return 'middle';
}
