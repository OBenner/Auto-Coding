import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldAlert, TrendingDown, TrendingUp, Minus, AlertTriangle } from 'lucide-react';
import type { FailureMetrics } from '../../../shared/types/productivity-analytics';

export interface FailureTrendPoint {
  date: string;
  failure_count: number;
  root_cause_rate: number;
  recurrence_rate: number;
}

interface FailureAnalysisDashboardProps {
  failureMetrics: FailureMetrics | null;
  trends?: FailureTrendPoint[];
  isLoading?: boolean;
}

interface ChartMetric {
  key: keyof FailureTrendPoint;
  labelKey: string;
  color: string;
  formatValue: (value: number) => string;
}

const CHART_METRICS: ChartMetric[] = [
  {
    key: 'failure_count',
    labelKey: 'common:failureAnalysis.metrics.failures',
    color: 'rgb(239, 68, 68)',
    formatValue: (value: number) => value.toFixed(0),
  },
  {
    key: 'root_cause_rate',
    labelKey: 'common:failureAnalysis.metrics.rootCauseRatePercent',
    color: 'rgb(34, 197, 94)',
    formatValue: (value: number) => (value * 100).toFixed(1),
  },
  {
    key: 'recurrence_rate',
    labelKey: 'common:failureAnalysis.metrics.recurrenceRatePercent',
    color: 'rgb(249, 115, 22)',
    formatValue: (value: number) => (value * 100).toFixed(1),
  },
];

function TrendIcon({ trend, className }: { trend: 'up' | 'down' | 'neutral'; className: string }) {
  const Icon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  return <Icon className={className} />;
}

function trendColor(trend: 'up' | 'down' | 'neutral', goodDirection: 'up' | 'down'): string {
  if (trend === goodDirection) return 'text-success';
  if (trend !== 'neutral') return 'text-destructive';
  return 'text-muted-foreground';
}

function formatPct(v: number | undefined): string {
  return `${((v ?? 0) * 100).toFixed(1)}%`;
}

export function FailureAnalysisDashboard({ failureMetrics, trends: trendsProp = [], isLoading = false }: FailureAnalysisDashboardProps) {
  const { t } = useTranslation(['common']);

  const trends = trendsProp;

  const chartData = useMemo(() => {
    if (trends.length === 0) return null;

    const width = 800;
    const height = 300;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const denom = trends.length > 1 ? trends.length - 1 : 1;

    const processedMetrics = CHART_METRICS.map((metric) => {
      const values = trends.map((point) => Number(point[metric.key]) || 0);
      const maxValue = values.length > 0 ? Math.max(...values) : 0;
      const minValue = values.length > 0 ? Math.min(...values) : 0;
      const range = maxValue - minValue || 1;

      const points = trends.map((point, index) => {
        const x = padding.left + (index / denom) * chartWidth;
        const value = Number(point[metric.key]) || 0;
        const y = padding.top + chartHeight - ((value - minValue) / range) * chartHeight;
        return { x, y, value };
      });

      const pathData = points
        .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
        .join(' ');

      const lastPoint = points[points.length - 1];
      const areaPath = lastPoint
        ? `${pathData} L ${lastPoint.x} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`
        : '';

      return { ...metric, points, pathData, areaPath, maxValue, minValue };
    });

    const dateLabels = trends.map((point) => {
      const date = new Date(point.date);
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    });

    return { width, height, padding, chartWidth, chartHeight, denom, metrics: processedMetrics, dateLabels };
  }, [trends]);

  const trendIndicators = useMemo((): {
    failureTrend: 'up' | 'down' | 'neutral';
    rootCauseTrend: 'up' | 'down' | 'neutral';
    recurrenceTrend: 'up' | 'down' | 'neutral';
  } => {
    if (trends.length < 2) {
      return { failureTrend: 'neutral', rootCauseTrend: 'neutral', recurrenceTrend: 'neutral' };
    }
    const first = trends[0];
    const last = trends[trends.length - 1];
    return {
      failureTrend: last.failure_count < first.failure_count ? 'down' : last.failure_count > first.failure_count ? 'up' : 'neutral',
      rootCauseTrend: last.root_cause_rate > first.root_cause_rate ? 'up' : last.root_cause_rate < first.root_cause_rate ? 'down' : 'neutral',
      recurrenceTrend: last.recurrence_rate < first.recurrence_rate ? 'down' : last.recurrence_rate > first.recurrence_rate ? 'up' : 'neutral',
    };
  }, [trends]);

  const summaryCards = useMemo(() => {
    if (!failureMetrics) return [];
    return [
      {
        key: 'totalFailures',
        labelKey: 'common:failureAnalysis.totalFailures',
        value: String(failureMetrics.total_failures),
        trend: trendIndicators.failureTrend,
        colorClass: trendColor(trendIndicators.failureTrend, 'down'),
      },
      {
        key: 'rootCauseRate',
        labelKey: 'common:failureAnalysis.rootCauseRate',
        value: formatPct(failureMetrics.root_cause_rate),
        trend: trendIndicators.rootCauseTrend,
        colorClass: trendColor(trendIndicators.rootCauseTrend, 'up'),
      },
      {
        key: 'recurrenceRate',
        labelKey: 'common:failureAnalysis.recurrenceRate',
        value: formatPct(failureMetrics.recurrence_rate),
        trend: trendIndicators.recurrenceTrend,
        colorClass: trendColor(trendIndicators.recurrenceTrend, 'down'),
      },
    ];
  }, [failureMetrics, trendIndicators]);

  const hasData = failureMetrics && failureMetrics.total_failures > 0 && chartData;

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-destructive" />
          <h2 className="text-lg font-semibold text-foreground">{t('common:failureAnalysis.title')}</h2>
        </div>
        {hasData && (
          <div className="flex items-center gap-4">
            {CHART_METRICS.map((metric) => (
              <div key={metric.key} className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full" style={{ backgroundColor: metric.color }} />
                <span className="text-xs text-muted-foreground">{t(metric.labelKey)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
            <p className="text-sm text-muted-foreground">{t('common:failureAnalysis.loading')}</p>
          </div>
        </div>
      )}

      {/* No data state */}
      {!isLoading && !hasData && (
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <AlertTriangle className="h-12 w-12 opacity-50" />
            <p className="text-sm">{t('common:failureAnalysis.noData')}</p>
            <p className="text-xs">{t('common:failureAnalysis.noDataHint')}</p>
          </div>
        </div>
      )}

      {/* Data state */}
      {!isLoading && hasData && chartData && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {summaryCards.map((card) => (
              <div key={card.key} className="p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">{t(card.labelKey)}</span>
                  <TrendIcon trend={card.trend} className={`h-4 w-4 ${card.colorClass}`} />
                </div>
                <div className="text-2xl font-semibold text-foreground">{card.value}</div>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="w-full overflow-x-auto">
            <svg
              viewBox={`0 0 ${chartData.width} ${chartData.height}`}
              className="w-full h-auto"
              style={{ minHeight: '300px' }}
              role="img"
              aria-label={t('common:failureAnalysis.chartAriaLabel')}
            >
              <title>{t('common:failureAnalysis.chartTitle')}</title>
              {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
                const y = chartData.padding.top + chartData.chartHeight * (1 - fraction);
                return (
                  <line key={fraction} x1={chartData.padding.left} y1={y} x2={chartData.width - chartData.padding.right} y2={y} stroke="currentColor" strokeWidth="1" opacity="0.1" className="text-muted-foreground" />
                );
              })}
              <line x1={chartData.padding.left} y1={chartData.height - chartData.padding.bottom} x2={chartData.width - chartData.padding.right} y2={chartData.height - chartData.padding.bottom} stroke="currentColor" strokeWidth="2" className="text-border" />
              <line x1={chartData.padding.left} y1={chartData.padding.top} x2={chartData.padding.left} y2={chartData.height - chartData.padding.bottom} stroke="currentColor" strokeWidth="2" className="text-border" />
              {chartData.dateLabels.map((label, index) => {
                const x = chartData.padding.left + (index / chartData.denom) * chartData.chartWidth;
                return (
                  <text key={trends[index]?.date ?? `date-${index}`} x={x} y={chartData.height - chartData.padding.bottom + 20} textAnchor="middle" className="text-xs fill-muted-foreground">
                    {label}
                  </text>
                );
              })}
              {chartData.metrics.map((metric) => (
                <g key={metric.key}>
                  <path d={metric.areaPath} fill={metric.color} opacity="0.1" />
                  <path d={metric.pathData} stroke={metric.color} strokeWidth="2" fill="none" />
                  {metric.points.map((point, pointIndex) => (
                    <g key={`${metric.key}-point-${pointIndex}`}>
                      <circle cx={point.x} cy={point.y} r="4" fill={metric.color} className="opacity-80 hover:opacity-100" />
                      <title>{chartData.dateLabels[pointIndex]}: {metric.formatValue(point.value)}</title>
                    </g>
                  ))}
                </g>
              ))}
            </svg>
          </div>

          {/* Chart Footer */}
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground text-center">
              {t('common:failureAnalysis.chartFooter')}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
