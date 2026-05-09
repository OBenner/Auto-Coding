import { Activity, AlertCircle, CheckCircle2, FileText, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { GenericEditArtifactManifest } from '../../../shared/types';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

interface GenericEditArtifactsPanelProps {
  manifest: GenericEditArtifactManifest;
}

function statusVariant(status: string): 'success' | 'destructive' | 'warning' | 'info' | 'muted' {
  const normalizedStatus = status.toLowerCase();
  if (['success', 'ok', 'completed', 'done'].includes(normalizedStatus)) {
    return 'success';
  }
  if (['error', 'failed', 'failure'].includes(normalizedStatus)) {
    return 'destructive';
  }
  if (['cancelled', 'canceled', 'interrupted'].includes(normalizedStatus)) {
    return 'warning';
  }
  if (['running', 'in_progress'].includes(normalizedStatus)) {
    return 'info';
  }
  return 'muted';
}

function countValue(value: number | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

export function GenericEditArtifactsPanel({ manifest }: GenericEditArtifactsPanelProps) {
  const { t } = useTranslation(['tasks']);
  const activeArtifacts = manifest.artifacts.filter((artifact) => artifact.active);
  const presentActiveArtifacts = activeArtifacts.filter((artifact) => artifact.present).length;
  const recoveryFlags = [
    manifest.flags.resumable && t('tasks:overview.genericEditResumable'),
    manifest.flags.recoverable && t('tasks:overview.genericEditRecoverable'),
    manifest.flags.has_recovery_plan && t('tasks:overview.genericEditRecoveryPlan'),
    manifest.flags.has_mutation_snapshots && t('tasks:overview.genericEditMutationSnapshots'),
    manifest.flags.has_transaction_groups && t('tasks:overview.genericEditTransactionGroups'),
  ].filter((flag): flag is string => typeof flag === 'string');

  return (
    <div>
      <div className="section-divider mb-4">
        <Activity className="h-3 w-3" />
        {t('tasks:overview.genericEditArtifacts')}
      </div>

      <div className="rounded-lg border p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={statusVariant(manifest.status)} className="text-xs">
                {manifest.status}
              </Badge>
              {recoveryFlags.map((flag) => (
                <Badge key={flag} variant="outline" className="text-xs">
                  {flag}
                </Badge>
              ))}
            </div>
            <div className="text-xs text-muted-foreground">
              <span>{t('tasks:overview.genericEditProvider')}: </span>
              <span className="font-medium text-foreground">{manifest.provider}</span>
              <span className="mx-2">/</span>
              <span>{t('tasks:overview.genericEditStopReason')}: </span>
              <span className="font-medium text-foreground">{manifest.stop_reason}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs">
            {presentActiveArtifacts === activeArtifacts.length ? (
              <CheckCircle2 className="h-4 w-4 text-success" />
            ) : (
              <AlertCircle className="h-4 w-4 text-warning" />
            )}
            <span>
              {t('tasks:overview.genericEditArtifactsPresent', {
                present: presentActiveArtifacts,
                total: activeArtifacts.length,
              })}
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditIterations')}</div>
            <div className="font-semibold">{countValue(manifest.counts.iteration_count)}</div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditActions')}</div>
            <div className="font-semibold">
              {countValue(manifest.counts.action_count)}
              {manifest.counts.failed_action_count > 0 && (
                <span className="ml-1 text-destructive">
                  ({countValue(manifest.counts.failed_action_count)})
                </span>
              )}
            </div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditEvents')}</div>
            <div className="font-semibold">{countValue(manifest.counts.event_count)}</div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditTransactions')}</div>
            <div className="font-semibold">{countValue(manifest.counts.transaction_count)}</div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditRecoveryAttempts')}</div>
            <div className="font-semibold">
              {countValue(manifest.counts.recovery_attempt_count)}
              {manifest.counts.failed_recovery_attempt_count > 0 && (
                <span className="ml-1 text-destructive">
                  ({countValue(manifest.counts.failed_recovery_attempt_count)})
                </span>
              )}
            </div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditMutationSnapshots')}</div>
            <div className="font-semibold">{countValue(manifest.counts.mutation_snapshot_count)}</div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditTransactionGroups')}</div>
            <div className="font-semibold">{countValue(manifest.counts.transaction_group_count)}</div>
          </div>
        </div>

        {activeArtifacts.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              {t('tasks:overview.genericEditActiveArtifacts')}
            </div>
            <div className="space-y-1.5">
              {activeArtifacts.map((artifact) => (
                <div
                  key={artifact.name}
                  className={cn(
                    'flex min-w-0 items-center gap-2 rounded-md border px-2.5 py-2 text-xs',
                    !artifact.present && 'border-warning/50 bg-warning/10'
                  )}
                >
                  {artifact.present ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                  ) : (
                    <RotateCcw className="h-3.5 w-3.5 shrink-0 text-warning" />
                  )}
                  <span className="min-w-0 flex-1 truncate font-medium">{artifact.name}</span>
                  <Badge variant={artifact.present ? 'muted' : 'warning'} className="text-xs">
                    {artifact.present ? artifact.kind : t('tasks:overview.genericEditMissingArtifact')}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
