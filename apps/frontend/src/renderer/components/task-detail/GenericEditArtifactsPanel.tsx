import { useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Eye,
  FileText,
  Layers,
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
  GenericEditTransactionBatch,
} from '../../../shared/types';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';

type GenericEditArtifactsPanelProps = Readonly<{
  manifest: GenericEditArtifactManifest;
}>;

type ArtifactPreview = Readonly<{
  artifactName: string;
  content: string;
  error: string | null;
  loading: boolean;
}>;

type TranslationFn = (key: string, values?: Record<string, unknown>) => string;

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

function batchStatusVariant(status: string): 'success' | 'destructive' | 'warning' | 'info' | 'muted' {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus === 'committed') {
    return 'success';
  }
  if (normalizedStatus === 'aborted') {
    return 'warning';
  }
  if (normalizedStatus === 'open') {
    return 'info';
  }
  return statusVariant(status);
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
  if (event.recovery_required || event.requires_user_action) {
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

function recoveryTimelineTitle(event: GenericEditRecentEvent): string {
  const strategy = typeof event.strategy === 'string' ? event.strategy : '';
  return event.tool || event.group_id || event.transaction_id || strategy || event.event_type;
}

function recoveryTimelineBadge(event: GenericEditRecentEvent): string {
  return event.timeline_stage || event.status || event.event_type;
}

function recoveryTimelineMeta(event: GenericEditRecentEvent): string {
  return [event.status, event.strategy, event.message, event.transaction_id, event.batch_id, event.active_batch_id]
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .join(' / ');
}

function uniqueStrings(values: readonly (string | undefined)[]): string[] {
  const result: string[] = [];
  for (const value of values) {
    if (!value || result.includes(value)) {
      continue;
    }
    result.push(value);
  }
  return result;
}

function recentEventMeta(event: GenericEditRecentEvent, t: TranslationFn): string {
  const stagedBatch =
    typeof event.staged_workspace_batch_id === 'string' && event.staged_workspace_batch_id.length > 0
      ? t('tasks:overview.genericEditStagedBatch', { batchId: event.staged_workspace_batch_id })
      : null;
  const stagedWorkspaceMaterialized =
    event.staged_workspace_materialized === true
      ? t('tasks:overview.genericEditStagedWorkspaceMaterialized')
      : null;
  const stagedWorkspaceRestored =
    event.staged_workspace_restored === true
      ? t('tasks:overview.genericEditStagedWorkspaceRestored')
      : null;
  return [event.transaction_id, event.path, event.message, stagedBatch, stagedWorkspaceMaterialized, stagedWorkspaceRestored]
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

function transactionBatchMeta(batch: GenericEditTransactionBatch): string {
  return [...batch.transaction_ids, ...batch.mutation_snapshot_ids].join(' / ');
}

function batchLifecycleEventMeta(
  event: NonNullable<GenericEditTransactionBatch['lifecycle_events']>[number]
): string {
  return [
    event.action,
    event.status,
    event.transaction_id,
    event.reason,
    ...(event.blocked_transaction_group_ids ?? []),
  ]
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .join(' / ');
}

function batchBoundaryErrorMeta(
  error: NonNullable<GenericEditTransactionBatch['boundary_errors']>[number]
): string {
  return [error.tool, error.reason, ...error.blocked_transaction_group_ids]
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

function mcpBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function mcpNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function mcpRecordList(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(
    (item): item is Record<string, unknown> =>
      typeof item === 'object' && item !== null && !Array.isArray(item)
  );
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

function mcpAvailabilityVariant(
  availability: string | null
): 'success' | 'destructive' | 'warning' | 'info' | 'muted' {
  if (availability === 'available') {
    return 'success';
  }
  if (availability === 'unavailable') {
    return 'warning';
  }
  return 'muted';
}

function mcpServerStatusName(status: Record<string, unknown>): string {
  return mcpString(status.display_name) ?? mcpString(status.server) ?? 'unknown';
}

function mcpToolPolicyName(policy: Record<string, unknown>): string {
  return mcpString(policy.exposed_name) ?? mcpString(policy.name) ?? 'unknown';
}

function ArtifactPreviewContent({
  preview,
  loadingLabel,
}: Readonly<{ preview: ArtifactPreview; loadingLabel: string }>) {
  if (preview.loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        {loadingLabel}
      </div>
    );
  }
  if (preview.error) {
    return <div className="px-3 py-4 text-xs text-destructive">{preview.error}</div>;
  }
  return (
    <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all px-3 py-3 text-xs">
      {preview.content}
    </pre>
  );
}

export function GenericEditArtifactsPanel({ manifest }: GenericEditArtifactsPanelProps) {
  const { t } = useTranslation(['tasks']);
  const [preview, setPreview] = useState<ArtifactPreview | null>(null);
  const activeArtifacts = manifest.artifacts.filter((artifact) => artifact.active);
  const presentActiveArtifacts = activeArtifacts.filter((artifact) => artifact.present).length;
  const mcpSupport = manifest.mcp_support;
  const mcpBridgePlan = mcpRecord(mcpSupport?.bridge_plan);
  const mcpBridge = mcpRecord(mcpSupport?.bridge);
  const mcpStrategy = mcpString(mcpSupport?.strategy) ?? 'unknown';
  const mcpReason = mcpString(mcpSupport?.reason);
  const mcpServer = mcpString(mcpSupport?.server);
  const mcpToolCount = mcpNumber(mcpSupport?.tool_count) ?? mcpStringList(mcpBridge?.tools).length;
  const mcpAvailableServers = mcpStringList(mcpSupport?.available_servers);
  const mcpUnavailableServers = mcpStringList(mcpSupport?.unavailable_servers);
  const mcpServerStatuses = mcpRecordList(mcpSupport?.server_statuses);
  const mcpBridgePlanStatus = mcpString(mcpBridgePlan?.status);
  const mcpActionRequired = mcpString(mcpBridgePlan?.action_required);
  const mcpRecommendedRuntimePath = mcpString(mcpBridgePlan?.recommended_runtime_path);
  const mcpNativeRequiredServers = mcpStringList(mcpBridgePlan?.native_required_servers);
  const mcpLocalBridgeRequiredServers = mcpStringList(mcpBridgePlan?.local_bridge_required_servers);
  const mcpExternalBridgeRequiredServers = mcpStringList(mcpBridgePlan?.external_bridge_required_servers);
  const mcpUnsupportedServers = mcpStringList(mcpBridgePlan?.unsupported_servers);
  const mcpBridgedServers = mcpStringList(mcpBridgePlan?.bridged_servers);
  const mcpExternalBridgedServers = mcpStringList(mcpBridgePlan?.external_bridged_servers);
  const mcpBridgeTools = mcpStringList(mcpBridge?.tools);
  const mcpBridgeServerStatuses = mcpRecordList(mcpBridge?.server_statuses);
  const mcpDisplayedServerStatuses =
    mcpServerStatuses.length > 0 ? mcpServerStatuses : mcpBridgeServerStatuses;
  const mcpToolPolicies = mcpRecordList(mcpBridge?.tool_policies);
  const mcpPermissionPolicy = mcpRecord(mcpBridge?.permission_policy);
  const mcpPermissionMode = mcpString(mcpPermissionPolicy?.mode);
  const mcpAllowedPermissions = mcpStringList(mcpPermissionPolicy?.allowed_permissions);
  const mcpSessionLifecycle = mcpRecord(mcpBridge?.session_lifecycle);
  const mcpSessionReuse = mcpString(mcpSessionLifecycle?.reuse);
  const mcpOpenSessions = mcpRecordList(mcpSessionLifecycle?.open_sessions);
  const mcpOpenSessionCount =
    mcpNumber(mcpSessionLifecycle?.open_session_count) ?? mcpOpenSessions.length;
  const nativeToolFallbacks = manifest.native_tool_fallbacks;
  const transactionBatches = manifest.transaction_batches;
  const resumeMetadata = mcpRecord(manifest.resume);
  const resumeCheckpointArtifact = mcpString(resumeMetadata?.checkpoint_artifact);
  const resumeTraceArtifact = mcpString(resumeMetadata?.trace_artifact);
  const resumeStrategy = mcpString(resumeMetadata?.strategy);
  const resumeStartIteration = mcpNumber(resumeMetadata?.start_iteration);
  const resumePreviousStatus = mcpString(resumeMetadata?.previous_status);
  const resumePreviousStopReason = mcpString(resumeMetadata?.previous_stop_reason);
  const resumeInputs = Object.entries(manifest.resume_inputs).filter(
    ([, artifactPath]) => artifactPath.length > 0
  );
  const resumePolicy = manifest.resume_policy;
  const recoveryTimeline = manifest.recovery_timeline ?? [];
  const requiredResumeActions = resumePolicy?.required_resolution_action_kinds ?? [];
  const requiredResumeArtifacts = resumePolicy?.required_artifacts ?? [];
  const openResumeBatches = resumePolicy?.open_transaction_batch_ids ?? [];
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
      const result = await globalThis.electronAPI.readFile(artifactPath);
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
            <div className="text-muted-foreground">
              {t('tasks:overview.genericEditTransactionBatches')}
            </div>
            <div className="font-semibold">
              {countValue(manifest.counts.transaction_batch_count)}
            </div>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <div className="text-muted-foreground">{t('tasks:overview.genericEditNativeFallbacks')}</div>
            <div className="font-semibold">
              {countValue(manifest.counts.native_tool_fallback_count)}
            </div>
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

        {nativeToolFallbacks.length > 0 && (
          <div className="mt-4 rounded-md border border-warning/40 bg-warning/5 px-3 py-3 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5 text-warning" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditNativeFallbackDetails')}
              </span>
            </div>
            <div className="space-y-1.5">
              {nativeToolFallbacks.slice(0, 3).map((fallback) => (
                <div
                  key={`${fallback.provider}-${fallback.from_loop}-${fallback.to_loop}-${fallback.reason}`}
                  className="flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border bg-background/50 px-2 py-1.5"
                >
                  <Badge variant="warning" className="text-xs">
                    {fallback.provider}
                  </Badge>
                  <span className="font-medium text-muted-foreground">
                    {t('tasks:overview.genericEditNativeFallbackReason')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {fallback.reason}
                  </Badge>
                  <span className="font-medium text-muted-foreground">
                    {t('tasks:overview.genericEditNativeFallbackLoop')}
                  </span>
                  <span className="min-w-0 truncate text-muted-foreground">
                    {fallback.from_loop} -&gt; {fallback.to_loop}
                  </span>
                  {fallback.message && (
                    <span className="min-w-0 truncate text-muted-foreground">
                      {fallback.message}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {transactionBatches.length > 0 && (
          <div className="mt-4 rounded-md border bg-muted/20 px-3 py-3 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Layers className="h-3.5 w-3.5 text-info" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditTransactionBatches')}
              </span>
            </div>
            <div className="space-y-1.5">
              {transactionBatches.slice(0, 4).map((batch) => {
                const meta = transactionBatchMeta(batch);
                const lifecycleEvents = batch.lifecycle_events ?? [];
                const boundaryErrors = batch.boundary_errors ?? [];
                const boundaryErrorReasons = batch.boundary_error_reasons ?? [];
                const requiredNextActionKinds = batch.required_next_action_kinds ?? [];
                const resolutionStrategies = batch.resolution_strategies ?? [];
                const stagedPaths = uniqueStrings([
                  ...(batch.staged_mutated_paths ?? []),
                  ...(batch.staged_restored_paths ?? []),
                  ...(batch.staged_deleted_paths ?? []),
                ]);
                return (
                  <div
                    key={batch.id}
                    className="flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border bg-background/50 px-2 py-1.5"
                  >
                    <Badge variant={batchStatusVariant(batch.status)} className="text-xs">
                      {batch.status}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {batch.id}
                    </Badge>
                    {batch.recovery_status && batch.recovery_status !== 'clean' && (
                      <Badge variant={batch.finish_blocked ? 'warning' : 'muted'} className="text-xs">
                        {batch.recovery_status}
                      </Badge>
                    )}
                    {batch.finish_blocked && (
                      <Badge variant="destructive" className="text-xs">
                        {t('tasks:overview.genericEditFinishBlocked')}
                      </Badge>
                    )}
                    {meta && <span className="min-w-0 truncate text-muted-foreground">{meta}</span>}
                    {batch.transaction_group_ids.length > 0 && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchGroups')}
                        </span>
                        {batch.transaction_group_ids.map((groupId) => (
                          <Badge key={groupId} variant="muted" className="text-xs">
                            {groupId}
                          </Badge>
                        ))}
                      </span>
                    )}
                    {batch.unresolved_transaction_group_ids.length > 0 && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchUnresolvedGroups')}
                        </span>
                        {batch.unresolved_transaction_group_ids.map((groupId) => (
                          <Badge key={groupId} variant="warning" className="text-xs">
                            {groupId}
                          </Badge>
                        ))}
                      </span>
                    )}
                    {batch.recovery_outcome_count > 0 && (
                      <Badge variant="info" className="text-xs">
                        {t('tasks:overview.genericEditBatchRecoveryOutcomes', {
                          count: batch.recovery_outcome_count,
                        })}
                      </Badge>
                    )}
                    {countValue(batch.staged_mutation_count) > 0 && (
                      <Badge variant="info" className="text-xs">
                        {t('tasks:overview.genericEditBatchStagedMutations', {
                          count: countValue(batch.staged_mutation_count),
                        })}
                      </Badge>
                    )}
                    {countValue(batch.staged_path_count) > 0 && (
                      <Badge variant="muted" className="text-xs">
                        {t('tasks:overview.genericEditBatchStagedPaths', {
                          count: countValue(batch.staged_path_count),
                        })}
                      </Badge>
                    )}
                    {countValue(batch.lifecycle_event_count) > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {t('tasks:overview.genericEditBatchLifecycleEvents', {
                          count: countValue(batch.lifecycle_event_count),
                        })}
                      </Badge>
                    )}
                    {stagedPaths.length > 0 && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchStagedPathList')}
                        </span>
                        {stagedPaths.slice(0, 4).map((stagedPath) => (
                          <Badge key={stagedPath} variant="muted" className="max-w-full truncate text-xs">
                            {stagedPath}
                          </Badge>
                        ))}
                      </span>
                    )}
                    {lifecycleEvents.length > 0 && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchLifecycle')}
                        </span>
                        {lifecycleEvents.slice(0, 3).map((event) => {
                          const eventMeta = batchLifecycleEventMeta(event);
                          return (
                            <Badge key={`${event.action}-${event.transaction_id ?? event.status}`} variant="outline" className="max-w-full truncate text-xs">
                              {eventMeta}
                            </Badge>
                          );
                        })}
                      </span>
                    )}
                    {(boundaryErrors.length > 0 || boundaryErrorReasons.length > 0) && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchBoundaryBlockers')}
                        </span>
                        {boundaryErrors.slice(0, 3).map((error) => {
                          const errorMeta = batchBoundaryErrorMeta(error);
                          return (
                            <Badge key={`${error.tool}-${error.batch_id}-${error.reason}`} variant="warning" className="max-w-full truncate text-xs">
                              {errorMeta}
                            </Badge>
                          );
                        })}
                        {boundaryErrors.length === 0 &&
                          boundaryErrorReasons.slice(0, 3).map((reason) => (
                            <Badge key={reason} variant="warning" className="max-w-full truncate text-xs">
                              {reason}
                            </Badge>
                          ))}
                      </span>
                    )}
                    {requiredNextActionKinds.length > 0 && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchRequiredNextActions')}
                        </span>
                        {requiredNextActionKinds.map((kind) => (
                          <Badge key={kind} variant="warning" className="max-w-full truncate text-xs">
                            {kind}
                          </Badge>
                        ))}
                      </span>
                    )}
                    {resolutionStrategies.length > 0 && (
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        <span className="font-medium text-muted-foreground">
                          {t('tasks:overview.genericEditBatchResolutionStrategies')}
                        </span>
                        {resolutionStrategies.map((strategy) => (
                          <Badge key={strategy} variant="muted" className="max-w-full truncate text-xs">
                            {strategy}
                          </Badge>
                        ))}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

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

        {resumePolicy && (
          <div className="mt-4 rounded-md border bg-muted/20 px-3 py-3 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <ListChecks className="h-3.5 w-3.5 text-info" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditResumePolicy')}
              </span>
              <Badge variant={resumePolicy.finish_blocked ? 'warning' : 'success'} className="text-xs">
                {resumePolicy.status}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {resumePolicy.strategy}
              </Badge>
            </div>
            {requiredResumeActions.length > 0 && (
              <div className="mb-2">
                <div className="mb-1 font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditRequiredResumeActions')}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {requiredResumeActions.map((actionKind) => (
                    <Badge key={actionKind} variant="outline" className="text-xs">
                      {actionKind}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {openResumeBatches.length > 0 && (
              <div className="mb-2">
                <div className="mb-1 font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditOpenTransactionBatches')}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {openResumeBatches.map((batchId) => (
                    <Badge key={batchId} variant="warning" className="text-xs">
                      {batchId}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {requiredResumeArtifacts.length > 0 && (
              <div>
                <div className="mb-1 font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditRequiredResumeArtifacts')}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {requiredResumeArtifacts.map((artifactName) => (
                    <Badge key={artifactName} variant="muted" className="text-xs">
                      {artifactName}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {resumeMetadata && (
          <div className="mt-4 rounded-md border bg-muted/20 px-3 py-3 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <PlayCircle className="h-3.5 w-3.5 text-info" />
              <span className="font-semibold text-muted-foreground">
                {t('tasks:overview.genericEditResumeProvenance')}
              </span>
              {resumeStrategy && (
                <Badge variant="info" className="text-xs">
                  {resumeStrategy}
                </Badge>
              )}
              {typeof resumeStartIteration === 'number' && (
                <Badge variant="muted" className="text-xs">
                  {t('tasks:overview.genericEditResumeStartIteration', {
                    iteration: resumeStartIteration,
                  })}
                </Badge>
              )}
            </div>
            {(resumePreviousStatus || resumePreviousStopReason) && (
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <span className="font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditResumePreviousStop')}
                </span>
                {resumePreviousStatus && (
                  <Badge variant={statusVariant(resumePreviousStatus)} className="text-xs">
                    {resumePreviousStatus}
                  </Badge>
                )}
                {resumePreviousStopReason && (
                  <Badge variant="outline" className="text-xs">
                    {resumePreviousStopReason}
                  </Badge>
                )}
              </div>
            )}
            {resumeCheckpointArtifact && (
              <div className="truncate text-muted-foreground">{resumeCheckpointArtifact}</div>
            )}
            {resumeTraceArtifact && (
              <div className="mt-1 truncate text-muted-foreground">{resumeTraceArtifact}</div>
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

            {mcpServer && (
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <span className="font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditMcpServer')}
                </span>
                <Badge variant="muted" className="text-xs">
                  {mcpServer}
                </Badge>
              </div>
            )}

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

            {mcpDisplayedServerStatuses.length > 0 && (
              <div className="mb-2 space-y-1">
                <div className="font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditMcpServerStatus')}
                </div>
                {mcpDisplayedServerStatuses.slice(0, 4).map((status) => {
                  const serverName = mcpServerStatusName(status);
                  const availability = mcpString(status.availability);
                  const runtimePath = mcpString(status.runtime_path);
                  const reason = mcpString(status.reason);
                  const bridgeable = mcpBoolean(status.bridgeable);
                  return (
                    <div
                      key={`${serverName}-${runtimePath ?? 'unknown'}`}
                      className="flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border bg-background/50 px-2 py-1.5"
                    >
                      <Badge variant="muted" className="text-xs">
                        {serverName}
                      </Badge>
                      {availability && (
                        <Badge variant={mcpAvailabilityVariant(availability)} className="text-xs">
                          {availability}
                        </Badge>
                      )}
                      {runtimePath && (
                        <Badge variant="outline" className="text-xs">
                          {runtimePath}
                        </Badge>
                      )}
                      {bridgeable === true && (
                        <Badge variant="info" className="text-xs">
                          bridgeable
                        </Badge>
                      )}
                      {reason && <span className="min-w-0 truncate text-muted-foreground">{reason}</span>}
                    </div>
                  );
                })}
              </div>
            )}

            {(mcpSessionReuse || mcpOpenSessions.length > 0 || mcpSessionLifecycle) && (
              <div className="mb-2 space-y-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-medium text-muted-foreground">
                    {t('tasks:overview.genericEditMcpSessionReuse')}
                  </span>
                  {mcpSessionReuse && (
                    <Badge variant="outline" className="text-xs">
                      {mcpSessionReuse}
                    </Badge>
                  )}
                  <Badge variant="muted" className="text-xs">
                    {t('tasks:overview.genericEditMcpOpenSessions', {
                      count: mcpOpenSessionCount,
                    })}
                  </Badge>
                </div>
                {mcpOpenSessions.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {mcpOpenSessions.slice(0, 4).map((session) => {
                      const server = mcpString(session.server) ?? 'unknown';
                      const transport = mcpString(session.transport) ?? 'unknown';
                      const sessionStatus = mcpString(session.status) ?? 'unknown';
                      return (
                        <div
                          key={`${server}-${transport}-${sessionStatus}`}
                          className="flex min-w-0 flex-wrap items-center gap-1 rounded-md border bg-background/50 px-2 py-1"
                        >
                          <Badge variant="muted" className="text-xs">
                            {server}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {transport}
                          </Badge>
                          <Badge variant={statusVariant(sessionStatus)} className="text-xs">
                            {sessionStatus}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {(mcpPermissionMode || mcpAllowedPermissions.length > 0) && (
              <div className="mb-2 space-y-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-medium text-muted-foreground">
                    {t('tasks:overview.genericEditMcpPermissionPolicy')}
                  </span>
                  {mcpPermissionMode && (
                    <Badge variant="outline" className="text-xs">
                      {mcpPermissionMode}
                    </Badge>
                  )}
                </div>
                {mcpAllowedPermissions.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpAllowedPermissions')}
                    </span>
                    {mcpAllowedPermissions.map((permission) => (
                      <Badge key={permission} variant="muted" className="max-w-full truncate text-xs">
                        {permission}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {mcpToolPolicies.length > 0 && (
              <div className="mb-2 space-y-1">
                <div className="font-medium text-muted-foreground">
                  {t('tasks:overview.genericEditMcpToolPolicies')}
                </div>
                <div className="flex flex-wrap gap-1">
                  {mcpToolPolicies.slice(0, 4).map((policy) => {
                    const name = mcpToolPolicyName(policy);
                    const permission = mcpString(policy.permission);
                    const auditLevel = mcpString(policy.audit_level);
                    return (
                      <div
                        key={name}
                        className="flex min-w-0 flex-wrap items-center gap-1 rounded-md border bg-background/50 px-2 py-1"
                      >
                        <Badge variant="outline" className="max-w-full truncate text-xs">
                          {name}
                        </Badge>
                        {permission && (
                          <Badge variant="muted" className="max-w-full truncate text-xs">
                            {permission}
                          </Badge>
                        )}
                        {auditLevel && (
                          <Badge variant="info" className="text-xs">
                            {auditLevel}
                          </Badge>
                        )}
                      </div>
                    );
                  })}
                </div>
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

            {(mcpRecommendedRuntimePath ||
              mcpNativeRequiredServers.length > 0 ||
              mcpLocalBridgeRequiredServers.length > 0 ||
              mcpExternalBridgeRequiredServers.length > 0 ||
              mcpUnsupportedServers.length > 0) && (
              <div className="mb-2 flex flex-wrap gap-2">
                {mcpRecommendedRuntimePath && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpRecommendedRuntimePath')}
                    </span>
                    <Badge variant="info" className="text-xs">
                      {mcpRecommendedRuntimePath}
                    </Badge>
                  </div>
                )}
                {mcpNativeRequiredServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpNativeRequired')}
                    </span>
                    {mcpNativeRequiredServers.map((server) => (
                      <Badge key={server} variant="warning" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
                {mcpLocalBridgeRequiredServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpLocalBridgeRequired')}
                    </span>
                    {mcpLocalBridgeRequiredServers.map((server) => (
                      <Badge key={server} variant="warning" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
                {mcpExternalBridgeRequiredServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpExternalBridgeRequired')}
                    </span>
                    {mcpExternalBridgeRequiredServers.map((server) => (
                      <Badge key={server} variant="warning" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
                {mcpUnsupportedServers.length > 0 && (
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground">
                      {t('tasks:overview.genericEditMcpUnsupported')}
                    </span>
                    {mcpUnsupportedServers.map((server) => (
                      <Badge key={server} variant="destructive" className="text-xs">
                        {server}
                      </Badge>
                    ))}
                  </div>
                )}
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
                const meta = recentEventMeta(event, t);
                let badgeText = recentEventBadge(event);
                if (event.event_type === 'action_result' && typeof event.ok === 'boolean') {
                  badgeText = t(
                    event.ok
                      ? 'tasks:overview.genericEditEventOk'
                      : 'tasks:overview.genericEditEventFailed'
                  );
                }
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

        {recoveryTimeline.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <RotateCcw className="h-3.5 w-3.5" />
              {t('tasks:overview.genericEditRecoveryTimeline')}
            </div>
            <div className="space-y-1.5">
              {recoveryTimeline.map((event) => {
                const meta = recoveryTimelineMeta(event);
                return (
                  <div
                    key={`${event.sequence}-${event.timeline_stage ?? event.event_type}`}
                    className="flex min-w-0 items-center gap-2 rounded-md border px-2.5 py-2 text-xs"
                  >
                    <span className="shrink-0 tabular-nums text-muted-foreground">#{event.sequence}</span>
                    <Badge variant={recentEventVariant(event)} className="shrink-0 text-xs">
                      {recoveryTimelineBadge(event)}
                    </Badge>
                    <span className="min-w-0 shrink-0 font-medium">{recoveryTimelineTitle(event)}</span>
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
            <ArtifactPreviewContent
              preview={preview}
              loadingLabel={t('tasks:overview.genericEditLoadingArtifact')}
            />
          </div>
        )}
      </div>
    </div>
  );
}
