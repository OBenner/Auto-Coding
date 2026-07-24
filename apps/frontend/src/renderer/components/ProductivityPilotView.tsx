/**
 * Productivity pilot on the shared design system (U5 B2).
 *
 * Renders `libs/ui`'s AnalyticsDashboard from the existing
 * `getProductivitySummary` + `getProductivityTrends` IPC, mapped with the
 * pure `productivity-ui` helpers. Read-only — the legacy Productivity view
 * keeps its spec table. Reachable via the "Productivity (new UI)" sidebar
 * item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnalyticsDashboard } from '@auto-code/ui';
import type { UiChartCard, UiKpi, UiMetaSection } from '@auto-code/ui';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
} from '../../shared/types';
import {
  buildProductivityCharts,
  buildProductivityKpis,
  buildProductivitySections,
} from '../lib/productivity-ui';

interface ProductivityPilotViewProps {
  projectId: string;
}

interface PilotState {
  summary: ProductivitySummary | null;
  trends: ProductivityTrendPoint[];
  loading: boolean;
  error: Error | null;
}

export function ProductivityPilotView({
  projectId,
}: Readonly<ProductivityPilotViewProps>) {
  const { t, i18n } = useTranslation(['analytics']);
  const [state, setState] = useState<PilotState>({
    summary: null,
    trends: [],
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ summary: null, trends: [], loading: true, error: null });
    Promise.all([
      window.electronAPI.getProductivitySummary(projectId),
      window.electronAPI.getProductivityTrends(projectId),
    ])
      .then(([summaryResult, trendsResult]) => {
        if (!active) return;
        if (!summaryResult.success || summaryResult.data == null) {
          console.error(
            '[ProductivityPilotView] Failed to load summary:',
            summaryResult.success ? 'no data' : summaryResult.error,
          );
          setState({
            summary: null,
            trends: [],
            loading: false,
            error: new Error(t('analytics:productivityPilot.error')),
          });
          return;
        }
        setState({
          summary: summaryResult.data,
          trends: trendsResult.success ? (trendsResult.data ?? []) : [],
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        console.error('[ProductivityPilotView] Failed to load productivity:', err);
        setState({
          summary: null,
          trends: [],
          loading: false,
          error: new Error(t('analytics:productivityPilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const kpis = useMemo<UiKpi[] | null>(() => {
    if (state.summary == null) return null;
    return buildProductivityKpis(state.summary, state.trends, {
      specs: t('analytics:productivityPilot.kpis.specs'),
      specsSub: t('analytics:productivityPilot.kpis.specsSub'),
      timeSaved: t('analytics:productivityPilot.kpis.timeSaved'),
      timeSavedSub: t('analytics:productivityPilot.kpis.timeSavedSub'),
      successRate: t('analytics:productivityPilot.kpis.successRate'),
      buildTime: t('analytics:productivityPilot.kpis.buildTime'),
      buildTimeSub: t('analytics:productivityPilot.kpis.buildTimeSub'),
    });
  }, [state.summary, state.trends, t]);

  const charts = useMemo<UiChartCard[] | undefined>(() => {
    if (state.summary == null) return undefined;
    return buildProductivityCharts(
      state.trends,
      {
        velocityTitle: t('analytics:productivityPilot.charts.velocityTitle'),
        velocityAria: t('analytics:productivityPilot.charts.velocityAria'),
        velocitySeries: t('analytics:productivityPilot.charts.velocitySeries'),
        timeSavedTitle: t('analytics:productivityPilot.charts.timeSavedTitle'),
        timeSavedAria: t('analytics:productivityPilot.charts.timeSavedAria'),
        timeSavedSeries: t('analytics:productivityPilot.charts.timeSavedSeries'),
      },
      i18n.language,
    );
  }, [state.summary, state.trends, t, i18n.language]);

  const sections = useMemo<UiMetaSection[] | undefined>(() => {
    if (state.summary == null) return undefined;
    return buildProductivitySections(state.summary, {
      outcomesTitle: t('analytics:productivityPilot.sections.outcomesTitle'),
      completed: t('analytics:productivityPilot.sections.completed'),
      inProgress: t('analytics:productivityPilot.sections.inProgress'),
      failed: t('analytics:productivityPilot.sections.failed'),
      effortTitle: t('analytics:productivityPilot.sections.effortTitle'),
      subtasksPerSpec: t('analytics:productivityPilot.sections.subtasksPerSpec'),
      qaIterations: t('analytics:productivityPilot.sections.qaIterations'),
      firstAttempt: t('analytics:productivityPilot.sections.firstAttempt'),
    });
  }, [state.summary, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('analytics:productivityPilot.states.loading'),
      retry: t('analytics:productivityPilot.states.retry'),
      empty: t('analytics:productivityPilot.states.empty'),
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
