/**
 * Model Usage pilot on the shared design system (U5 B2).
 *
 * Renders `libs/ui`'s AnalyticsDashboard from the existing
 * `getModelUsageSummary` + `getModelUsageTrends` IPC, mapped with the pure
 * `model-usage-ui` helpers. KPIs + token/cost trend charts + a per-model
 * BarList. Read-only — the legacy Model Usage view keeps its export flow.
 * Reachable via the "Model Usage (new UI)" sidebar item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnalyticsDashboard } from '@auto-code/ui';
import type {
  UiBarListCard,
  UiChartCard,
  UiKpi,
  UiMetaSection,
} from '@auto-code/ui';
import type {
  ModelUsageSummary,
  ModelUsageTrendPoint,
} from '../../shared/types';
import {
  buildModelBarLists,
  buildModelCharts,
  buildModelKpis,
  buildModelSections,
} from '../lib/model-usage-ui';

interface ModelUsagePilotViewProps {
  projectId: string;
}

interface PilotState {
  summary: ModelUsageSummary | null;
  trends: ModelUsageTrendPoint[];
  loading: boolean;
  error: Error | null;
}

export function ModelUsagePilotView({
  projectId,
}: Readonly<ModelUsagePilotViewProps>) {
  const { t, i18n } = useTranslation(['model-usage']);
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
      window.electronAPI.getModelUsageSummary(projectId),
      window.electronAPI.getModelUsageTrends(projectId),
    ])
      .then(([summaryResult, trendsResult]) => {
        if (!active) return;
        if (!summaryResult.success || summaryResult.data == null) {
          console.error(
            '[ModelUsagePilotView] Failed to load summary:',
            summaryResult.success ? 'no data' : summaryResult.error,
          );
          setState({
            summary: null,
            trends: [],
            loading: false,
            error: new Error(t('model-usage:modelUsagePilot.error')),
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
        console.error('[ModelUsagePilotView] Failed to load model usage:', err);
        setState({
          summary: null,
          trends: [],
          loading: false,
          error: new Error(t('model-usage:modelUsagePilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const kpis = useMemo<UiKpi[] | null>(() => {
    if (state.summary == null) return null;
    return buildModelKpis(state.summary, state.trends, {
      calls: t('model-usage:modelUsagePilot.kpis.calls'),
      callsSub: t('model-usage:modelUsagePilot.kpis.callsSub'),
      tokens: t('model-usage:modelUsagePilot.kpis.tokens'),
      cost: t('model-usage:modelUsagePilot.kpis.cost'),
      models: t('model-usage:modelUsagePilot.kpis.models'),
      modelsSub: t('model-usage:modelUsagePilot.kpis.modelsSub'),
    });
  }, [state.summary, state.trends, t]);

  const charts = useMemo<UiChartCard[] | undefined>(() => {
    if (state.summary == null) return undefined;
    return buildModelCharts(
      state.trends,
      {
        tokensTitle: t('model-usage:modelUsagePilot.charts.tokensTitle'),
        tokensAria: t('model-usage:modelUsagePilot.charts.tokensAria'),
        tokensSeries: t('model-usage:modelUsagePilot.charts.tokensSeries'),
        costTitle: t('model-usage:modelUsagePilot.charts.costTitle'),
        costAria: t('model-usage:modelUsagePilot.charts.costAria'),
        costSeries: t('model-usage:modelUsagePilot.charts.costSeries'),
      },
      i18n.language,
    );
  }, [state.summary, state.trends, t, i18n.language]);

  const barLists = useMemo<UiBarListCard[] | undefined>(() => {
    if (state.summary == null) return undefined;
    return buildModelBarLists(
      state.summary.models,
      t('model-usage:modelUsagePilot.models.title'),
      t('model-usage:modelUsagePilot.models.aria'),
    );
  }, [state.summary, t]);

  const sections = useMemo<UiMetaSection[] | undefined>(() => {
    if (state.summary == null) return undefined;
    return buildModelSections(state.summary, {
      splitTitle: t('model-usage:modelUsagePilot.sections.splitTitle'),
      inputTokens: t('model-usage:modelUsagePilot.sections.inputTokens'),
      outputTokens: t('model-usage:modelUsagePilot.sections.outputTokens'),
      providers: t('model-usage:modelUsagePilot.sections.providers'),
    });
  }, [state.summary, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('model-usage:modelUsagePilot.states.loading'),
      retry: t('model-usage:modelUsagePilot.states.retry'),
      empty: t('model-usage:modelUsagePilot.states.empty'),
    }),
    [t],
  );

  return (
    <div className="h-full overflow-hidden">
      <AnalyticsDashboard
        kpis={kpis}
        charts={charts}
        barLists={barLists}
        sections={sections}
        loading={state.loading}
        error={state.error}
        onRetry={reload}
        stateLabels={stateLabels}
      />
    </div>
  );
}
