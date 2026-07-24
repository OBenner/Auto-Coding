/**
 * Analytics pilot on the shared design system (U5 B2).
 *
 * Renders `libs/ui`'s AnalyticsDashboard from the existing
 * `analytics.getReport` IPC, mapped with the pure `analytics-ui` helpers.
 * Read-only overview — the legacy multi-tab Analytics view keeps the
 * agent/QA drilldowns. Reachable via the "Analytics (new UI)" sidebar item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnalyticsDashboard } from '@auto-code/ui';
import type { UiChartCard, UiKpi, UiMetaSection } from '@auto-code/ui';
import type { AnalyticsReport } from '../../shared/types';
import {
  buildCharts,
  buildKpis,
  buildSections,
} from '../lib/analytics-ui';

interface AnalyticsPilotViewProps {
  projectId: string;
}

interface PilotState {
  report: AnalyticsReport | null;
  loading: boolean;
  error: Error | null;
}

export function AnalyticsPilotView({
  projectId,
}: Readonly<AnalyticsPilotViewProps>) {
  const { t, i18n } = useTranslation(['analytics']);
  const [state, setState] = useState<PilotState>({
    report: null,
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ report: null, loading: true, error: null });
    window.electronAPI.analytics
      .getReport(projectId)
      .then((result) => {
        if (!active) return;
        if (!result.success) {
          console.error('[AnalyticsPilotView] Failed to load report:', result.error);
          setState({
            report: null,
            loading: false,
            error: new Error(t('analytics:analyticsPilot.error')),
          });
          return;
        }
        setState({ report: result.data ?? null, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!active) return;
        console.error('[AnalyticsPilotView] Failed to load report:', err);
        setState({
          report: null,
          loading: false,
          error: new Error(t('analytics:analyticsPilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const kpis = useMemo<UiKpi[] | null>(() => {
    if (state.report == null) return null;
    return buildKpis(state.report, {
      specs: t('analytics:analyticsPilot.kpis.specs'),
      successRate: t('analytics:analyticsPilot.kpis.successRate'),
      cost: t('analytics:analyticsPilot.kpis.cost'),
      tokens: t('analytics:analyticsPilot.kpis.tokens'),
      specsSub: t('analytics:analyticsPilot.kpis.specsSub'),
      tokensSub: t('analytics:analyticsPilot.kpis.tokensSub'),
    });
  }, [state.report, t]);

  const charts = useMemo<UiChartCard[] | undefined>(() => {
    if (state.report == null) return undefined;
    return buildCharts(
      state.report,
      {
        velocityTitle: t('analytics:analyticsPilot.charts.velocityTitle'),
        velocityAria: t('analytics:analyticsPilot.charts.velocityAria'),
        tasksSeries: t('analytics:analyticsPilot.charts.tasksSeries'),
        rateTitle: t('analytics:analyticsPilot.charts.rateTitle'),
        rateAria: t('analytics:analyticsPilot.charts.rateAria'),
        rateSeries: t('analytics:analyticsPilot.charts.rateSeries'),
      },
      i18n.language,
    );
  }, [state.report, t, i18n.language]);

  const sections = useMemo<UiMetaSection[] | undefined>(() => {
    if (state.report == null) return undefined;
    return buildSections(state.report, {
      outcomesTitle: t('analytics:analyticsPilot.sections.outcomesTitle'),
      completed: t('analytics:analyticsPilot.sections.completed'),
      failed: t('analytics:analyticsPilot.sections.failed'),
      inProgress: t('analytics:analyticsPilot.sections.inProgress'),
      qaTitle: t('analytics:analyticsPilot.sections.qaTitle'),
      reviews: t('analytics:analyticsPilot.sections.reviews'),
      approved: t('analytics:analyticsPilot.sections.approved'),
      rejectionRate: t('analytics:analyticsPilot.sections.rejectionRate'),
    });
  }, [state.report, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('analytics:analyticsPilot.states.loading'),
      retry: t('analytics:analyticsPilot.states.retry'),
      empty: t('analytics:analyticsPilot.states.empty'),
    }),
    [t],
  );

  return (
    <div className="h-full overflow-hidden">
      <AnalyticsDashboard
        kpis={kpis}
        charts={charts}
        sections={sections}
        loading={state.loading}
        error={state.error}
        onRetry={reload}
        stateLabels={stateLabels}
      />
    </div>
  );
}
