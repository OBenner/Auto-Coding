import { LineChart } from '../primitives/LineChart';
import { Sparkline } from '../primitives/Sparkline';
import { StatTile } from '../primitives/StatTile';
import type {
  UiChartCard,
  UiKpi,
  UiMetaSection,
} from '../client/types';
import './AnalyticsDashboard.css';

export interface AnalyticsDashboardStateLabels {
  loading?: string;
  retry?: string;
  empty?: string;
}

export interface AnalyticsDashboardProps {
  /** KPI tiles across the top; null renders the loading/empty state. */
  kpis: UiKpi[] | null;
  /** Titled chart cards (line charts) in the main column. */
  charts?: UiChartCard[];
  /** Summary meta cards (outcomes, QA, agents …) in the right rail. */
  sections?: UiMetaSection[];
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  /** Localized loading/retry/empty labels; falls back to English. */
  stateLabels?: AnalyticsDashboardStateLabels;
}

/**
 * Generic analytics dashboard mirroring the `.lazyweb` layout: a KPI stat-tile
 * row, a column of titled line-chart cards, and an optional right rail of
 * summary meta cards. Composes the shared chart primitives; data-agnostic, so
 * every B2 analytics screen (Analytics, Productivity, Merge, Model Usage) can
 * reuse it by mapping its report onto UiKpi[] / UiChartCard[] / UiMetaSection[].
 */
export function AnalyticsDashboard({
  kpis,
  charts,
  sections,
  loading = false,
  error = null,
  onRetry,
  stateLabels,
}: Readonly<AnalyticsDashboardProps>) {
  if (loading) {
    return (
      <section className="ac-analytics">
        <p className="ac-analytics__state" aria-live="polite">
          {stateLabels?.loading ?? 'Loading…'}
        </p>
      </section>
    );
  }

  if (error != null) {
    return (
      <section className="ac-analytics">
        <p className="ac-analytics__state ac-analytics__state--error" role="alert">
          {error.message}
          {onRetry != null && (
            <button
              type="button"
              className="ac-analytics__retry"
              onClick={onRetry}
            >
              {stateLabels?.retry ?? 'Retry'}
            </button>
          )}
        </p>
      </section>
    );
  }

  if (kpis == null || kpis.length === 0) {
    return (
      <section className="ac-analytics">
        <p className="ac-analytics__state" aria-live="polite">
          {stateLabels?.empty ?? 'No analytics yet.'}
        </p>
      </section>
    );
  }

  const chartCards = charts ?? [];
  const metaCards = sections ?? [];

  return (
    <section className="ac-analytics">
      <div className="ac-analytics__kpis">
        {kpis.map((kpi) => (
          <StatTile
            key={kpi.label}
            value={kpi.value}
            label={kpi.label}
            sub={kpi.sub}
            tone={kpi.tone}
            sparkline={
              kpi.trend != null && kpi.trend.length >= 2 ? (
                <Sparkline
                  values={kpi.trend}
                  tone={kpi.trendTone ?? 'info'}
                  area
                />
              ) : undefined
            }
          />
        ))}
      </div>

      <div
        className={`ac-analytics__body${
          metaCards.length > 0 ? '' : ' ac-analytics__body--no-rail'
        }`}
      >
        <div className="ac-analytics__charts">
          {chartCards.map((chart) => (
            <div key={chart.title} className="ac-analytics__chart-card">
              <h3 className="ac-analytics__chart-title">{chart.title}</h3>
              <LineChart
                series={chart.series}
                xLabels={chart.xLabels}
                showLegend={chart.showLegend}
                ariaLabel={chart.ariaLabel}
              />
            </div>
          ))}
        </div>

        {metaCards.length > 0 && (
          <aside className="ac-analytics__rail">
            {metaCards.map((section) => (
              <div key={section.title} className="ac-analytics__card">
                <h3>{section.title}</h3>
                {section.rows.map((row) => (
                  <div key={row.label} className="ac-analytics__kv">
                    <span>{row.label}</span>
                    <strong>{row.value}</strong>
                  </div>
                ))}
              </div>
            ))}
          </aside>
        )}
      </div>
    </section>
  );
}
