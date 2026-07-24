/**
 * Merge Analytics pilot on the shared design system (U5 B2).
 *
 * Renders `libs/ui`'s AnalyticsDashboard from the existing `getMergeSummary`
 * + `getConflictPatterns` IPC, mapped with the pure `merge-analytics-ui`
 * helpers. The conflict patterns render as a BarList distribution. Read-only
 * — the legacy Merge Analytics view keeps its export flow. Reachable via the
 * "Merge Analytics (new UI)" sidebar item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnalyticsDashboard } from '@auto-code/ui';
import type { UiBarListCard, UiKpi, UiMetaSection } from '@auto-code/ui';
import type { ConflictPattern, MergeAnalytics } from '../../shared/types';
import {
  buildMergeBarLists,
  buildMergeKpis,
  buildMergeSections,
} from '../lib/merge-analytics-ui';

interface MergeAnalyticsPilotViewProps {
  projectId: string;
}

interface PilotState {
  analytics: MergeAnalytics | null;
  patterns: ConflictPattern[];
  loading: boolean;
  error: Error | null;
}

export function MergeAnalyticsPilotView({
  projectId,
}: Readonly<MergeAnalyticsPilotViewProps>) {
  const { t } = useTranslation(['analytics']);
  const [state, setState] = useState<PilotState>({
    analytics: null,
    patterns: [],
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ analytics: null, patterns: [], loading: true, error: null });
    Promise.all([
      window.electronAPI.getMergeSummary(projectId),
      window.electronAPI.getConflictPatterns(projectId, 10),
    ])
      .then(([summaryResult, patternsResult]) => {
        if (!active) return;
        if (!summaryResult.success || summaryResult.data == null) {
          console.error(
            '[MergeAnalyticsPilotView] Failed to load summary:',
            summaryResult.success ? 'no data' : summaryResult.error,
          );
          setState({
            analytics: null,
            patterns: [],
            loading: false,
            error: new Error(t('analytics:mergePilot.error')),
          });
          return;
        }
        setState({
          analytics: summaryResult.data,
          patterns: patternsResult.success ? (patternsResult.data ?? []) : [],
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        console.error('[MergeAnalyticsPilotView] Failed to load merge analytics:', err);
        setState({
          analytics: null,
          patterns: [],
          loading: false,
          error: new Error(t('analytics:mergePilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const kpis = useMemo<UiKpi[] | null>(() => {
    if (state.analytics == null) return null;
    return buildMergeKpis(state.analytics, {
      operations: t('analytics:mergePilot.kpis.operations'),
      operationsSub: t('analytics:mergePilot.kpis.operationsSub'),
      successRate: t('analytics:mergePilot.kpis.successRate'),
      autoMerge: t('analytics:mergePilot.kpis.autoMerge'),
      conflicts: t('analytics:mergePilot.kpis.conflicts'),
      conflictsSub: t('analytics:mergePilot.kpis.conflictsSub'),
    });
  }, [state.analytics, t]);

  const barLists = useMemo<UiBarListCard[] | undefined>(() => {
    if (state.analytics == null) return undefined;
    return buildMergeBarLists(
      state.patterns,
      t('analytics:mergePilot.conflicts.title'),
      t('analytics:mergePilot.conflicts.aria'),
    );
  }, [state.analytics, state.patterns, t]);

  const sections = useMemo<UiMetaSection[] | undefined>(() => {
    if (state.analytics == null) return undefined;
    return buildMergeSections(state.analytics, {
      outcomesTitle: t('analytics:mergePilot.sections.outcomesTitle'),
      successful: t('analytics:mergePilot.sections.successful'),
      failed: t('analytics:mergePilot.sections.failed'),
      filesMerged: t('analytics:mergePilot.sections.filesMerged'),
      efficiencyTitle: t('analytics:mergePilot.sections.efficiencyTitle'),
      avgDuration: t('analytics:mergePilot.sections.avgDuration'),
      aiCalls: t('analytics:mergePilot.sections.aiCalls'),
      tokens: t('analytics:mergePilot.sections.tokens'),
    });
  }, [state.analytics, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('analytics:mergePilot.states.loading'),
      retry: t('analytics:mergePilot.states.retry'),
      empty: t('analytics:mergePilot.states.empty'),
    }),
    [t],
  );

  return (
    <div className="h-full overflow-hidden">
      <AnalyticsDashboard
        kpis={kpis}
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
