/**
 * Changelog pilot on the shared design system (U5 B1).
 *
 * Renders `libs/ui`'s ChangelogView from the project's CHANGELOG.md, read
 * over the existing `changelog:readExisting` IPC and parsed with the pure
 * `changelog-releases` helper. Read-only browser — the generator wizard
 * stays on the legacy Changelog view. Reachable via the
 * "Changelog (new UI)" sidebar item next to it.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChangelogView } from '@auto-code/ui';
import type { UiMetaSection, UiRelease, UiReleaseType } from '@auto-code/ui';
import { parseChangelogMarkdown } from '../lib/changelog-releases';

interface ChangelogPilotViewProps {
  projectId: string;
}

interface PilotState {
  releases: UiRelease[] | null;
  loading: boolean;
  error: Error | null;
}

export function ChangelogPilotView({
  projectId,
}: Readonly<ChangelogPilotViewProps>) {
  const { t, i18n } = useTranslation(['changelog']);
  const [state, setState] = useState<PilotState>({
    releases: null,
    loading: true,
    error: null,
  });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ releases: null, loading: true, error: null });
    window.electronAPI
      .readExistingChangelog(projectId)
      .then((result) => {
        if (!active) return;
        if (!result.success) {
          // Log the raw IPC error; the screen shows only localized text.
          console.error('[ChangelogPilotView] Failed to read changelog:', result.error);
          setState({
            releases: null,
            loading: false,
            error: new Error(t('changelog:pilot.error')),
          });
          return;
        }
        const content = result.data?.content ?? '';
        setState({
          releases: parseChangelogMarkdown(content, i18n.language),
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        console.error('[ChangelogPilotView] Failed to read changelog:', err);
        setState({
          releases: null,
          loading: false,
          error: new Error(t('changelog:pilot.error')),
        });
      });
    return () => {
      active = false;
    };
  }, [projectId, reloadKey, i18n.language, t]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const stateLabels = useMemo(
    () => ({
      loading: t('changelog:pilot.states.loading'),
      retry: t('changelog:pilot.states.retry'),
      empty: t('changelog:pilot.states.empty'),
    }),
    [t],
  );

  const typeLabels = useMemo<Partial<Record<UiReleaseType, string>>>(
    () => ({
      major: t('changelog:pilot.types.major'),
      minor: t('changelog:pilot.types.minor'),
      patch: t('changelog:pilot.types.patch'),
      draft: t('changelog:pilot.types.draft'),
    }),
    [t],
  );

  const metaSections = useMemo<UiMetaSection[] | undefined>(() => {
    const latest = state.releases?.find((release) => release.type !== 'draft');
    if (latest == null) return undefined;
    return [
      {
        title: t('changelog:pilot.meta.latestTitle'),
        rows: [
          { label: t('changelog:pilot.meta.version'), value: latest.version },
          ...(latest.dateLabel != null
            ? [
                {
                  label: t('changelog:pilot.meta.released'),
                  value: [latest.dateLabel, latest.yearLabel]
                    .filter(Boolean)
                    .join(' '),
                },
              ]
            : []),
          {
            label: t('changelog:pilot.meta.releases'),
            value: String(state.releases?.length ?? 0),
          },
        ],
      },
    ];
  }, [state.releases, t]);

  return (
    <div className="h-full overflow-hidden">
      <ChangelogView
        releases={state.releases}
        loading={state.loading}
        error={state.error}
        onRetry={reload}
        typeLabels={typeLabels}
        stateLabels={stateLabels}
        metaSections={metaSections}
      />
    </div>
  );
}
