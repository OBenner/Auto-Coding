/**
 * GitHub Issues pilot on the shared design system (U5 B1).
 *
 * Renders `libs/ui`'s IssueList from the existing `getGitHubIssues` IPC,
 * paired with the explicit connection check so a disconnected project
 * surfaces the error state (the list handler folds failures into empty
 * pages). Read-only list — investigation/import flows stay on the legacy
 * view. Reachable via the "GitHub Issues (new UI)" sidebar item.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IssueList } from '@auto-code/ui';
import type { UiIssue, UiMetaSection } from '@auto-code/ui';
import type { GitHubIssue, GitHubSyncStatus } from '../../shared/types';
import { filterIssues, mapIssueToUi } from '../lib/github-issues-ui';
import { relativeAge } from '../lib/github-prs-ui';

type IssueStateFilter = 'open' | 'closed' | 'all';

interface GitHubIssuesPilotViewProps {
  projectId: string;
}

interface PilotState {
  issues: GitHubIssue[] | null;
  sync: GitHubSyncStatus | null;
  loading: boolean;
  error: Error | null;
}

export function GitHubIssuesPilotView({
  projectId,
}: Readonly<GitHubIssuesPilotViewProps>) {
  const { t } = useTranslation(['github']);
  const [state, setState] = useState<PilotState>({
    issues: null,
    sync: null,
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');
  const [stateFilter, setStateFilter] = useState<IssueStateFilter>('open');

  useEffect(() => {
    let active = true;
    setState({ issues: null, sync: null, loading: true, error: null });
    Promise.all([
      window.electronAPI.github.checkGitHubConnection(projectId),
      window.electronAPI.github.getGitHubIssues(projectId, stateFilter, 1),
    ])
      .then(([connection, result]) => {
        if (!active) return;
        if (!connection.success || connection.data?.connected !== true) {
          console.error(
            '[GitHubIssuesPilotView] GitHub is not connected:',
            connection.success ? connection.data : connection.error,
          );
          setState({
            issues: null,
            sync: null,
            loading: false,
            error: new Error(t('github:issuesPilot.error')),
          });
          return;
        }
        if (!result.success) {
          console.error(
            '[GitHubIssuesPilotView] Failed to list issues:',
            result.error,
          );
          setState({
            issues: null,
            sync: null,
            loading: false,
            error: new Error(t('github:issuesPilot.error')),
          });
          return;
        }
        setState({
          issues: result.data?.issues ?? [],
          sync: connection.data ?? null,
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        // Log the raw IPC error; the screen shows only localized text.
        console.error('[GitHubIssuesPilotView] Failed to load issues:', err);
        setState({
          issues: null,
          sync: null,
          loading: false,
          error: new Error(t('github:issuesPilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, stateFilter, reloadKey, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const issues = useMemo<UiIssue[] | null>(() => {
    if (state.issues == null) return null;
    const now = new Date();
    return state.issues.map((issue) => ({
      ...mapIssueToUi(issue),
      metaText: t('github:issuesPilot.rowMeta', {
        author: issue.author.login,
        age: relativeAge(issue.createdAt, now, {
          minute: t('github:prsPilot.age.minute'),
          hour: t('github:prsPilot.age.hour'),
          day: t('github:prsPilot.age.day'),
        }),
      }),
    }));
  }, [state.issues, t]);

  const visible = useMemo(
    () => (issues == null ? null : filterIssues(issues, query)),
    [issues, query],
  );

  const filters = useMemo(
    () => [
      { id: 'open', label: t('github:issuesPilot.filters.open') },
      { id: 'closed', label: t('github:issuesPilot.filters.closed') },
      { id: 'all', label: t('github:issuesPilot.filters.all') },
    ],
    [t],
  );

  const metaSections = useMemo<UiMetaSection[] | undefined>(() => {
    if (state.sync == null) return undefined;
    const rows = [
      ...(state.sync.repoFullName != null
        ? [
            {
              label: t('github:issuesPilot.meta.repository'),
              value: state.sync.repoFullName,
            },
          ]
        : []),
      ...(state.sync.issueCount != null
        ? [
            {
              label: t('github:issuesPilot.meta.openIssues'),
              value: String(state.sync.issueCount),
            },
          ]
        : []),
    ];
    if (rows.length === 0) return undefined;
    return [{ title: t('github:issuesPilot.meta.title'), rows }];
  }, [state.sync, t]);

  const stateLabels = useMemo(
    () => ({
      loading: t('github:issuesPilot.states.loading'),
      retry: t('github:issuesPilot.states.retry'),
      empty: t('github:issuesPilot.states.empty'),
    }),
    [t],
  );

  const issueStateLabels = useMemo(
    () => ({
      open: t('github:issuesPilot.issueStates.open'),
      closed: t('github:issuesPilot.issueStates.closed'),
      draft: t('github:issuesPilot.issueStates.draft'),
    }),
    [t],
  );

  return (
    <div className="h-full overflow-hidden">
      <IssueList
        issues={visible}
        loading={state.loading}
        error={state.error}
        onRetry={reload}
        searchValue={query}
        onSearchChange={setQuery}
        searchPlaceholder={t('github:issuesPilot.searchPlaceholder')}
        searchLabel={t('github:issuesPilot.searchLabel')}
        filters={filters}
        activeFilterId={stateFilter}
        onSelectFilter={(id) => setStateFilter(id as IssueStateFilter)}
        filtersLabel={t('github:issuesPilot.filtersLabel')}
        stateLabels={stateLabels}
        issueStateLabels={issueStateLabels}
        commentsLabel={t('github:issuesPilot.commentsLabel')}
        metaSections={metaSections}
      />
    </div>
  );
}
