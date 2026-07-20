/**
 * GitHub PRs pilot on the shared design system (U5 B1).
 *
 * Renders `libs/ui`'s PullRequestList from the existing `github:pr:list`
 * IPC (open PRs via GraphQL), mapped with the pure `github-prs-ui`
 * helpers. Read-only list — review/merge flows stay on the legacy GitHub
 * PRs view. Reachable via the "GitHub PRs (new UI)" sidebar item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PullRequestList } from '@auto-code/ui';
import type { UiPrStat, UiPullRequest } from '@auto-code/ui';
import type { PRData } from '../../preload/api/modules/github-api';
import {
  computePrStatValues,
  filterPullRequests,
  mapPRToUi,
  relativeAge,
} from '../lib/github-prs-ui';

interface GitHubPRsPilotViewProps {
  projectId: string;
}

interface PilotState {
  prs: PRData[] | null;
  loading: boolean;
  error: Error | null;
}

export function GitHubPRsPilotView({
  projectId,
}: Readonly<GitHubPRsPilotViewProps>) {
  const { t } = useTranslation(['github']);
  const [state, setState] = useState<PilotState>({
    prs: null,
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let active = true;
    setState({ prs: null, loading: true, error: null });
    // The list handler folds every failure into an empty list, so a real
    // "not connected" state must come from the explicit connection check.
    Promise.all([
      window.electronAPI.github.checkGitHubConnection(projectId),
      window.electronAPI.github.listPRs(projectId),
    ])
      .then(([connection, result]) => {
        if (!active) return;
        if (!connection.success || connection.data?.connected !== true) {
          console.error(
            '[GitHubPRsPilotView] GitHub is not connected:',
            connection.success ? connection.data : connection.error,
          );
          setState({
            prs: null,
            loading: false,
            error: new Error(t('github:prsPilot.error')),
          });
          return;
        }
        setState({
          prs: result.prs ?? [],
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        // Log the raw IPC error; the screen shows only localized text.
        console.error('[GitHubPRsPilotView] Failed to list PRs:', err);
        setState({
          prs: null,
          loading: false,
          error: new Error(t('github:prsPilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const ageUnits = useMemo(
    () => ({
      minute: t('github:prsPilot.age.minute'),
      hour: t('github:prsPilot.age.hour'),
      day: t('github:prsPilot.age.day'),
    }),
    [t],
  );

  const pullRequests = useMemo<UiPullRequest[] | null>(() => {
    if (state.prs == null) return null;
    const now = new Date();
    return state.prs.map((pr) => ({
      ...mapPRToUi(pr, now, ageUnits),
      metaText: t('github:prsPilot.rowMeta', {
        count: pr.changedFiles,
        age: relativeAge(pr.createdAt, now, ageUnits),
      }),
    }));
  }, [state.prs, t, ageUnits]);

  const visible = useMemo(
    () => (pullRequests == null ? null : filterPullRequests(pullRequests, query)),
    [pullRequests, query],
  );

  const stats = useMemo<UiPrStat[] | undefined>(() => {
    if (state.prs == null || state.prs.length === 0) return undefined;
    const values = computePrStatValues(state.prs);
    return [
      {
        value: String(values.open),
        label: t('github:prsPilot.stats.open'),
        tone: 'good',
      },
      {
        value: String(values.authors),
        label: t('github:prsPilot.stats.authors'),
      },
      {
        value: `+${values.additions} −${values.deletions}`,
        label: t('github:prsPilot.stats.lines'),
      },
    ];
  }, [state.prs, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('github:prsPilot.states.loading'),
      retry: t('github:prsPilot.states.retry'),
      empty: t('github:prsPilot.states.empty'),
    }),
    [t],
  );

  return (
    <div className="h-full overflow-hidden">
      <PullRequestList
        pullRequests={visible}
        stats={stats}
        loading={state.loading}
        error={state.error}
        onRetry={reload}
        searchValue={query}
        onSearchChange={setQuery}
        searchPlaceholder={t('github:prsPilot.searchPlaceholder')}
        searchLabel={t('github:prsPilot.searchLabel')}
        stateLabels={stateLabels}
      />
    </div>
  );
}
