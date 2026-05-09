import { useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Eye,
  FileText,
  ListChecks,
  Loader2,
  Network,
  PlayCircle,
  RotateCcw,
  Wrench,
  X,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type {
  GenericEditArtifactManifest,
  GenericEditRecentEvent,
  GenericEditRecoveryAction,
} from '../../../shared/types';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
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

function recentEventVariant(
  event: GenericEditRecentEvent
): 'success' | 'destructive' | 'warning' | 'info' | 'muted' {
  if (event.ok === false || event.status === 'partial_failure' || event.status === 'failed') {
    return 'destructive';
  }
  if (event.recovery_required) {
    return 'warning';
  }
  if (event.ok === true || event.status === 'complete' || event.status === 'resolved') {
    return 'success';
  }
  if (event.event_type === 'resume') {
    return 'info';
  }
  return 'muted';
}

function recentEventTitle(event: GenericEditRecentEvent): string {
  return event.tool || event.status || event.group_id || event.transaction_id || event.event_type;
}

function recentEventBadge(event: GenericEditRecentEvent): string {
  return event.status || event.event_type;
}

function recentEventMeta(event: GenericEditRecentEvent): string {
  return [event.transaction_id, event.path, event.message]
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .join(' / ');
}

function recoveryActionMeta(action: GenericEditRecoveryAction): string {
  const actionPaths = action.paths?.join(', ');
  const mutationSnapshots = action.mutation_snapshot_ids?.join(', ');
  return [
    action.tool !== action.kind ? action.tool : null,
    action.transaction_id,
    action.transaction_group_id,
    action.rollback_operation_id,
    actionPaths,
    mutationSnapshots,
  ]
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .join(' / ');
}

function mcpRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function mcpString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function mcpNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function mcpStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string' && item.length > 0);
  }
  return typeof value === 'string' && value.length > 0 ? [value] : [];
}

function mcpStrategyVariant(
  strategy: string
): 'success' | 'destructive' | 'warning' | 'info' | 'muted' {
  if (strategy === 'native') {
    return 'success';
  }
  if (strategy === 'local_bridge') {
    return 'info';
  }
  if (strategy === 'unavailable') {
    return 'warning';
  }
  return 'muted';
}

export function GenericEditArtifactsPanel({ manifest }: GenericEditArtifactsPanelProps) {
  const { t } = useTranslation(['tasks']);
  const [preview, setPreview] = useState<{
    artifactName: string;
    content: string;
    error: string | null;
    loading: boolean;
  } | null>(null);
  const activeArtifacts = manifest.artifacts.filter((artifact) => artifact.active);
  const presentActiveArtifacts = activeArtifacts.filter((artifact) => artifact.present).length;
  const mcpSupport = manifest.mcp_support;
  const mcpBridgePlan = mcpRecord(mcpSupport?.bridge_plan);
  const mcpBridge = mcpRecord(mcpSupport?.bridge);
  const mcpStrategy = mcpString(mcpSupport?.strategy) ?? 'unknown';
  const mcpReason = mcpString(mcpSupport?.reason);
  const mcpToolCount = mcpNumber(mcpSupport?.tool_count) ?? mcpStringList(mcpBridge?.tools).length;
  const mcpAvailableServers = mcpStringList(mcpSupport?.available_servers);
  const mcpUnavailableServers = mcpStringList(mcpSupport?.unavailable_servers);
  const mcpBridgePlanStatus = mcpString(mcpBridgePlan?.status);
  const mcpActionRequired = mcpString(mcpBridgePlan?.action_required);
  const mcpBridgedServers = mcpStringList(mcpBridgePlan?.bridged_servers);
  const mcpExternalBridgedServers = mcpStringList(mcpBridgePlan?.external_bridged_servers);
  const mcpBridgeTools = mcpStringList(mcpBridge?.tools);
  const resumeInputs = Object.entries(manifest.resume_inputs).filter(
    ([, artifactPath]) => artifactPath.length > 0
  );
  const recoveryFlags = [
    manifest.flags.resumable && t('tasks:overview.genericEditResumable'),
    manifest.flags.recoverable && t('tasks:overview.genericEditRecoverable'),
    manifest.flags.has_recovery_plan && t('tasks:overview.genericEditRecoveryPlan'),
    manifest.flags.has_mutation_snapshots && t('tasks:overview.genericEditMutationSnapshots'),
    manifest.flags.has_transaction_groups && t('tasks:overview.genericEditTransactionGroups'),
  ].filter((flag): flag is string => typeof flag === 'string');

  const handleViewArtifact = async (artifactName: string, artifactPath: string) => {
    setPreview({
      artifactName,
      content: '',
      error: null,
      loading: true,
    });

    try {
      const result = await window.electronAPI.readFile(artifactPath);
      if (!result.success || result.data === undefined) {
        throw new Error(result.error || t('tasks:overview.genericEditArtifactLoadFailed'));
      }
      setPreview({
        artifactName,
        content: result.data,
        error: null,
        loading: false,
      });
    } catch (err) {
      setPreview({
        artifactName,
        content: '',
        error: err instanceof Error ? err.message : t('tasks:overview.genericEditArtifactLoadFailed'),
        loading: false,
      });
    }
  };

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

        {manifest.recovery_summary && manifest.recovery_summary.status !== 'clean' && (
          <div
            className={cn(
              'mt-4 rounded-md border px-3 py-3 text-xs',
              manifest.recovery_summary.finish_blocked
                ? 'border-warning/50 bg-warning/10'
                : 'bg-muted/20'
            )}
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5 text-warning" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditRecoveryStatus')}
              </span>
              <Badge
                variant={manifest.recovery_summary.finish_blocked ? 'warning' : 'muted'}
                className="text-xs"
              >
                {manifest.recovery_summary.status}
              </Badge>
              {manifest.recovery_summary.finish_blocked && (
                <Badge variant="destructive" className="text-xs">
                  {t('tasks:overview.genericEditFinishBlocked')}
                </Badge>
              )}
            </div>
            {manifest.recovery_summary.unresolved_transaction_group_ids.length > 0 && (
              <div className="truncate text-muted-foreground">
                {manifest.recovery_summary.unresolved_transaction_group_ids.join(', ')}
              </div>
            )}
            {manifest.recovery_summary.warning_count > 0 && (
              <div className="mt-2 space-y-1">
                <div className="font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditRecoveryWarnings')}
                </div>
                {manifest.recovery_summary.warnings.map((warning) => (
                  <div key={warning} className="text-warning">
                    {warning}
                  </div>
                ))}
              </div>
            )}
            {manifest.recovery_summary.resolution_strategies.length > 0 && (
              <div className="mt-3">
                <div className="mb-1 font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditResolutionStrategies')}
                </div>
                <div className="flex flex-wrap gap-1">
                  {manifest.recovery_summary.resolution_strategies.map((strategy) => (
                    <Badge key={strategy} variant="outline" className="text-xs">
                      {strategy}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {manifest.recovery_summary.recommended_verification_tools.length > 0 && (
              <div className="mt-3">
                <div className="mb-1 font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditRecommendedVerificationTools')}
                </div>
                <div className="flex flex-wrap gap-1">
                  {manifest.recovery_summary.recommended_verification_tools.map((tool) => (
                    <Badge key={tool} variant="muted" className="text-xs">
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {manifest.recovery_actions.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <Wrench className="h-3.5 w-3.5" />
              {t('tasks:overview.genericEditRecoveryActions')}
            </div>
            <div className="space-y-1.5">
              {manifest.recovery_actions.map((action) => {
                const meta = recoveryActionMeta(action);
                return (
                  <div
                    key={action.id}
                    className="flex min-w-0 items-center gap-2 rounded-md border border-warning/40 bg-warning/5 px-2.5 py-2 text-xs"
                  >
                    <Badge variant="warning" className="shrink-0 text-xs">
                      {action.kind}
                    </Badge>
                    {action.required_before_finish && (
                      <Badge variant="destructive" className="shrink-0 text-xs">
                        {t('tasks:overview.genericEditRequiredAction')}
                      </Badge>
                    )}
                    {meta && <span className="min-w-0 truncate text-muted-foreground">{meta}</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {manifest.resume_action && (
          <div className="mt-4 rounded-md border bg-muted/20 px-3 py-3 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <PlayCircle className="h-3.5 w-3.5 text-info" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditResumeEntrypoint')}
              </span>
              <Badge variant="info" className="text-xs">
                {manifest.resume_action.runtime}
              </Badge>
              <Badge variant="muted" className="text-xs">
                {t('tasks:overview.genericEditNextIteration', {
                  iteration: manifest.resume_action.next_iteration,
                })}
              </Badge>
            </div>
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              <span className="font-medium text-muted-foreground">
                {t('tasks:overview.genericEditResumeStrategy')}
              </span>
              <Badge variant="outline" className="text-xs">
                {manifest.resume_action.strategy}
              </Badge>
            </div>
            <div className="truncate text-muted-foreground">
              {manifest.resume_action.checkpoint_path}
            </div>
            {resumeInputs.length > 0 && (
              <div className="mt-3">
                <div className="mb-1 font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditResumeInputs')}
                </div>
                <div className="space-y-1">
                  {resumeInputs.map(([artifactName, artifactPath]) => (
                    <div key={artifactName} className="flex min-w-0 items-center gap-2">
                      <Badge variant="outline" className="shrink-0 text-xs">
                        {artifactName}
                      </Badge>
                      <span className="min-w-0 truncate text-muted-foreground">{artifactPath}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {mcpSupport && (
          <div className="mt-4 rounded-md border bg-muted/20 px-3 py-3 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Network className="h-3.5 w-3.5 text-info" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditMcpSupport')}
              </span>
              <Badge variant={mcpStrategyVariant(mcpStrategy)} className="text-xs">
                {mcpStrategy}
              </Badge>
              <Badge variant="muted" className="text-xs">
                {t('tasks:overview.genericEditMcpTools', { count: mcpToolCount })}
              </Badge>
            </div>

            {mcpReason && <div className="mb-2 text-muted-foreground">{mcpReason}</div>}

            {(mcpAvailableServers.length > 0 || mcpUnavailableServers.length > 0) && (
              <div className="mb-2 flex flex-wrap gap-2">
                {mcpAvailableServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpAvailable')}
                    </span>
                    {mcpAvailableServers.map((server) => (
                      <Badge key={server} variant="success" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
                {mcpUnavailableServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpUnavailable')}
                    </span>
                    {mcpUnavailableServers.map((server) => (
                      <Badge key={server} variant="warning" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {mcpActionRequired && mcpActionRequired !== 'none' && (
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <span className="font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditMcpActionRequired')}
                </span>
                <Badge variant="warning" className="text-xs">
                  {mcpActionRequired}
                </Badge>
              </div>
            )}

            {(mcpBridgePlanStatus || mcpBridgedServers.length > 0 || mcpExternalBridgedServers.length > 0) && (
              <div className="mb-2 flex flex-wrap gap-2">
                {mcpBridgePlanStatus && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpBridgePlan')}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {mcpBridgePlanStatus}
                    </Badge>
                  </div>
                )}
                {mcpBridgedServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpBridged')}
                    </span>
                    {mcpBridgedServers.map((server) => (
                      <Badge key={server} variant="muted" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
                {mcpExternalBridgedServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpExternalBridged')}
                    </span>
                    {mcpExternalBridgedServers.map((server) => (
                      <Badge key={server} variant="info" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {mcpBridgeTools.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {mcpBridgeTools.slice(0, 4).map((tool) => (
                  <Badge key={tool} variant="outline" className="max-w-full truncate text-xs">
                    {tool}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}

        {manifest.recent_events.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <ListChecks className="h-3.5 w-3.5" />
              {t('tasks:overview.genericEditRecentEvents')}
            </div>
            <div className="space-y-1.5">
              {manifest.recent_events.map((event) => {
                const meta = recentEventMeta(event);
                const badgeText =
                  event.event_type === 'action_result' && typeof event.ok === 'boolean'
                    ? t(event.ok ? 'tasks:overview.genericEditEventOk' : 'tasks:overview.genericEditEventFailed')
                    : recentEventBadge(event);
                return (
                  <div
                    key={`${event.sequence}-${event.event_type}`}
                    className="flex min-w-0 items-center gap-2 rounded-md border px-2.5 py-2 text-xs"
                  >
                    <span className="shrink-0 tabular-nums text-muted-foreground">#{event.sequence}</span>
                    <Badge variant={recentEventVariant(event)} className="shrink-0 text-xs">
                      {badgeText}
                    </Badge>
                    <span className="min-w-0 shrink-0 font-medium">{recentEventTitle(event)}</span>
                    {meta && <span className="min-w-0 truncate text-muted-foreground">{meta}</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeArtifacts.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              {t('tasks:overview.genericEditActiveArtifacts')}
            </div>
            <TooltipProvider>
              <div className="space-y-1.5">
                {activeArtifacts.map((artifact) => {
                  const artifactPath = artifact.present ? artifact.path : null;
                  const canPreview = typeof artifactPath === 'string';
                  return (
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
                      {canPreview && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 shrink-0 rounded-md"
                              aria-label={t('tasks:overview.genericEditViewArtifact')}
                              onClick={() => handleViewArtifact(artifact.name, artifactPath)}
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>{t('tasks:overview.genericEditViewArtifact')}</TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  );
                })}
              </div>
            </TooltipProvider>
          </div>
        )}

        {preview && (
          <div className="mt-4 rounded-md border bg-muted/20">
            <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
              <div className="min-w-0">
                <div className="text-xs font-semibold text-muted-foreground">
                  {t('tasks:overview.genericEditArtifactPreview')}
                </div>
                <div className="truncate text-xs font-medium">{preview.artifactName}</div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0 rounded-md"
                aria-label={t('tasks:overview.genericEditClosePreview')}
                onClick={() => setPreview(null)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            {preview.loading ? (
              <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {t('tasks:overview.genericEditLoadingArtifact')}
              </div>
            ) : preview.error ? (
              <div className="px-3 py-4 text-xs text-destructive">{preview.error}</div>
            ) : (
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all px-3 py-3 text-xs">
                {preview.content}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
