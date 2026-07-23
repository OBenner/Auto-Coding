/**
 * Patterns library pilot on the shared design system (U5 B1).
 *
 * The backend stores learned patterns per spec, so this pilot aggregates
 * across the project's known specs (from the task store) via the existing
 * `window.electronAPI.pattern.listPatterns` IPC and renders them through
 * `libs/ui`'s PatternLibrary. Read-only — the approve/override/delete
 * flows stay on the legacy Patterns view. Reachable via the "Patterns
 * (new UI)" sidebar item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PatternLibrary } from '@auto-code/ui';
import type { UiMetaSection, UiPattern } from '@auto-code/ui';
import { useTaskStore } from '../stores/task-store';
import {
  aggregatePatterns,
  filterPatterns,
  type SpecPatterns,
} from '../lib/patterns-ui';

interface PatternsPilotViewProps {
  projectId: string;
}

interface PilotState {
  patterns: UiPattern[] | null;
  specCount: number;
  loading: boolean;
  error: Error | null;
}

export function PatternsPilotView({
  projectId,
}: Readonly<PatternsPilotViewProps>) {
  const { t } = useTranslation(['patterns']);
  const [state, setState] = useState<PilotState>({
    patterns: null,
    specCount: 0,
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');

  const confidenceLabels = useMemo(
    () => ({
      high: t('patternsPilot.confidence.high'),
      medium: t('patternsPilot.confidence.medium'),
      low: t('patternsPilot.confidence.low'),
    }),
    [t],
  );

  useEffect(() => {
    let active = true;
    setState({ patterns: null, specCount: 0, loading: true, error: null });

    // Patterns are stored per spec; collect the project's known specs from
    // the task store and load each spec's patterns, tolerating per-spec
    // failures (a spec may have none / an unreadable file).
    const specIds = Array.from(
      new Set(
        useTaskStore
          .getState()
          .tasks.filter((task) => task.projectId === projectId)
          .map((task) => task.specId),
      ),
    );

    Promise.all(
      specIds.map((specId) =>
        window.electronAPI.pattern
          .listPatterns(projectId, specId)
          .then((result): SpecPatterns => ({
            specId,
            patterns: result.success ? (result.data ?? []) : [],
          }))
          .catch((err: unknown): SpecPatterns => {
            console.warn(
              '[PatternsPilotView] Failed to load patterns for spec',
              specId,
              err,
            );
            return { specId, patterns: [] };
          }),
      ),
    )
      .then((perSpec) => {
        if (!active) return;
        setState({
          patterns: aggregatePatterns(perSpec, confidenceLabels),
          specCount: specIds.length,
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        console.error('[PatternsPilotView] Failed to load patterns:', err);
        setState({
          patterns: null,
          specCount: 0,
          loading: false,
          error: new Error(t('patternsPilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, confidenceLabels, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const visible = useMemo(
    () =>
      state.patterns == null ? null : filterPatterns(state.patterns, query),
    [state.patterns, query],
  );

  const metaSections = useMemo<UiMetaSection[] | undefined>(() => {
    if (state.patterns == null) return undefined;
    return [
      {
        title: t('patternsPilot.meta.title'),
        rows: [
          {
            label: t('patternsPilot.meta.total'),
            value: String(state.patterns.length),
          },
          {
            label: t('patternsPilot.meta.specs'),
            value: String(state.specCount),
          },
        ],
      },
    ];
  }, [state.patterns, state.specCount, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('patternsPilot.states.loading'),
      retry: t('patternsPilot.states.retry'),
      empty: t('patternsPilot.states.empty'),
    }),
    [t],
  );

  const kindLabels = useMemo(
    () => ({
      pattern: t('patternsPilot.kinds.pattern'),
      gotcha: t('patternsPilot.kinds.gotcha'),
      decision: t('patternsPilot.kinds.decision'),
      rule: t('patternsPilot.kinds.rule'),
    }),
    [t],
  );

  return (
    <div className="h-full overflow-hidden">
      <PatternLibrary
        patterns={visible}
        loading={state.loading}
        error={state.error}
        onRetry={reload}
        searchValue={query}
        onSearchChange={setQuery}
        searchPlaceholder={t('patternsPilot.searchPlaceholder')}
        searchLabel={t('patternsPilot.searchLabel')}
        stateLabels={stateLabels}
        kindLabels={kindLabels}
        metaSections={metaSections}
      />
    </div>
  );
}
