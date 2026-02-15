import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, AlertTriangle } from 'lucide-react';
import type { QualityScore } from '../../stores/quality-store';
import {
  type ChartMetricConfig,
  createChartDimensions,
  buildMetricPaths,
} from './chart-utils';
import { ChartGrid, MetricSeries } from './ChartSvg';

interface QualityTrendChartProps {
  scores: QualityScore[];
  isLoading?: boolean;
}

type MetricType = 'composite_score' | 'test_pass_rate' | 'acceptance_criteria_met' | 'user_approval_rate';

interface MetricDef {
  key: MetricType;
  labelKey: string;
  color: string;
}

const METRIC_DEFS: MetricDef[] = [
  { key: 'composite_score', labelKey: 'trends.metrics.compositeScore', color: 'rgb(34, 197, 94)' },
  { key: 'test_pass_rate', labelKey: 'trends.metrics.testPassRate', color: 'rgb(59, 130, 246)' },
  { key: 'acceptance_criteria_met', labelKey: 'trends.metrics.acceptanceCriteria', color: 'rgb(168, 85, 247)' },
  { key: 'user_approval_rate', labelKey: 'trends.metrics.userApproval', color: 'rgb(245, 158, 11)' },
];

export function QualityTrendChart({ scores, isLoading = false }: QualityTrendChartProps) {
  const { t, i18n } = useTranslation('quality');

  const qualityMetrics: ChartMetricConfig<MetricType>[] = useMemo(
    () =>
      METRIC_DEFS.map((def) => ({
        key: def.key,
        label: t(def.labelKey),
        color: def.color,
        formatValue: (v: number) => (v * 100).toFixed(1) + '%',
      })),
    [t],
  );

  const chartData = useMemo(() => {
    if (!scores || scores.length === 0) return null;

    const dims = createChartDimensions();

    // Sort scores by timestamp
    const sortedScores = [...scores].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    // Build metric paths using shared utility
    const metrics = qualityMetrics.map((metric) => {
      const values = sortedScores.map((score) => {
        const raw = score[metric.key];
        const v = Number(raw ?? 0);
        return Number.isFinite(v) ? v : 0;
      });
      return buildMetricPaths(metric, values, dims, [0, 1]);
    });

    // Format dates for x-axis using i18n locale
    const dateLabels = sortedScores.map((score) => {
      const date = new Date(score.timestamp);
      return date.toLocaleDateString(i18n.language, { month: 'short', day: 'numeric' });
    });

    const latestScore = sortedScores[sortedScores.length - 1];

    return {
      dims,
      metrics,
      dateLabels,
      isHighQuality: latestScore.is_high_quality,
      isLowQuality: latestScore.is_low_quality,
    };
  }, [scores, qualityMetrics, i18n.language]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">{t('trends.title')}</h2>
        </div>
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
            <p className="text-sm text-muted-foreground">{t('trends.loading')}</p>
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
          <h2 className="text-lg font-semibold text-foreground">{t('trends.title')}</h2>
        </div>
        <div className="h-80 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <AlertTriangle className="h-12 w-12 opacity-50" />
            <p className="text-sm">{t('trends.empty.title')}</p>
            <p className="text-xs">{t('trends.empty.subtitle')}</p>
          </div>
        </div>
      </div>
    );
  }

  const { dims } = chartData;

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-accent" />
          <h2 className="text-lg font-semibold text-foreground">{t('trends.title')}</h2>
          {chartData.isLowQuality && (
            <span className="ml-2 px-2 py-1 text-xs font-medium rounded-full bg-destructive/10 text-destructive">
              {t('trends.lowQuality')}
            </span>
          )}
          {chartData.isHighQuality && (
            <span className="ml-2 px-2 py-1 text-xs font-medium rounded-full bg-green-500/10 text-green-500">
              {t('trends.highQuality')}
            </span>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4">
          {qualityMetrics.map((metric) => (
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

      {/* Chart */}
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${dims.width} ${dims.height}`}
          className="w-full h-auto"
          style={{ minHeight: '300px' }}
        >
          <ChartGrid
            dims={dims}
            formatYLabel={(f) => `${(f * 100).toFixed(0)}%`}
          />

          {chartData.metrics.map((metric) => (
            <MetricSeries key={metric.key} metric={metric} dateLabels={chartData.dateLabels} />
          ))}

          {/* X-axis labels */}
          {chartData.dateLabels.map((label, index) => {
            const x =
              dims.padding.left +
              (index / (chartData.dateLabels.length - 1 || 1)) * dims.chartWidth;
            return (
              <text
                key={index}
                x={x}
                y={dims.height - dims.padding.bottom + 20}
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
        {qualityMetrics.map((metric) => {
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
