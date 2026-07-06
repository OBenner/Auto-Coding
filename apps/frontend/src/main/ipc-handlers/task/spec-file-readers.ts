/**
 * Spec File Reader Utilities
 *
 * Provides utilities for reading task specification files from the worktree.
 * These files are read-only and provide task progress information:
 * - spec.md: Feature specification body
 * - implementation_plan.json: Implementation stages and progress
 * - artifacts/generic_edit_artifact_manifest.json: Generic Edit runtime artifacts
 * - artifacts/verification-report.json: Trust Layer verification report
 * - qa_report.md: QA testing results
 * - QA_ESCALATION.md: Escalated issues requiring attention
 */

import path from 'path';
import fs from 'fs/promises';
import { AUTO_BUILD_PATHS, getSpecsDir } from '../../../shared/constants';
import type {
  Project,
  Task,
  ImplementationPlan,
  VerificationReport,
  QAEscalation,
  GenericEditArtifactManifest,
  GenericEditArtifactManifestEntry,
  GenericEditBatchBoundaryError,
  GenericEditBatchLifecycleEvent,
  GenericEditMcpOpenSession,
  GenericEditMcpPermissionPolicy,
  GenericEditMcpServerStatus,
  GenericEditMcpSessionLifecycle,
  GenericEditMcpToolPolicy,
  GenericEditNativeToolFallback,
  GenericEditRecoveryAction,
  GenericEditRecoverySummary,
  GenericEditTransactionBatch,
  GenericEditResumeAction,
  GenericEditResumePolicy,
  GenericEditRecentEvent
} from '../../../shared/types';

/**
 * Check if an error is a "file not found" error
 */
function isFileNotFoundError(err: unknown): boolean {
  return (err as NodeJS.ErrnoException).code === 'ENOENT';
}

/**
 * Validate specId to prevent path traversal attacks
 */
function isValidSpecId(specId: string): boolean {
  return /^[\w-]+$/.test(specId);
}

/**
 * Get the spec directory path for a task.
 * Validates specId to prevent path traversal.
 */
export function getSpecDir(project: Project, task: Task): string {
  if (!isValidSpecId(task.specId)) {
    throw new Error(`Invalid specId: ${task.specId}`);
  }
  const specsBaseDir = getSpecsDir(project.autoBuildPath);
  const specDir = path.join(project.path, specsBaseDir, task.specId);
  const resolvedSpecDir = path.resolve(specDir);
  const resolvedProjectDir = path.resolve(project.path);
  if (!resolvedSpecDir.startsWith(resolvedProjectDir + path.sep) && resolvedSpecDir !== resolvedProjectDir) {
    throw new Error(`Path traversal detected: specDir escapes project root`);
  }
  return specDir;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readString(value: Record<string, unknown>, key: string): string | null {
  const result = value[key];
  return typeof result === 'string' ? result : null;
}

function readNullableString(value: Record<string, unknown>, key: string): string | null {
  const result = value[key];
  return typeof result === 'string' || result === null ? result : null;
}

function normalizeStringMap(value: unknown): GenericEditArtifactManifest['entrypoints'] | null {
  if (!isRecord(value)) return null;
  const result: GenericEditArtifactManifest['entrypoints'] = {};

  for (const [key, mapValue] of Object.entries(value)) {
    if (typeof mapValue !== 'string') {
      return null;
    }
    result[key] = mapValue;
  }

  return result;
}

function normalizeBooleanMap(
  value: unknown,
  requiredKeys: readonly string[]
): GenericEditArtifactManifest['flags'] | null {
  if (!isRecord(value)) return null;
  const result: Record<string, boolean> = {};

  for (const [key, mapValue] of Object.entries(value)) {
    if (typeof mapValue !== 'boolean') {
      return null;
    }
    result[key] = mapValue;
  }

  for (const key of requiredKeys) {
    if (typeof result[key] !== 'boolean') {
      return null;
    }
  }

  return result as GenericEditArtifactManifest['flags'];
}

function normalizeNumberMap(
  value: unknown,
  requiredKeys: readonly string[]
): GenericEditArtifactManifest['counts'] | null {
  if (!isRecord(value)) return null;
  const result: Record<string, number> = {};

  for (const [key, mapValue] of Object.entries(value)) {
    if (typeof mapValue !== 'number' || !Number.isFinite(mapValue)) {
      return null;
    }
    result[key] = mapValue;
  }

  for (const key of requiredKeys) {
    if (typeof result[key] !== 'number') {
      return null;
    }
  }

  return result as GenericEditArtifactManifest['counts'];
}

function normalizeManifestEntry(value: unknown): GenericEditArtifactManifestEntry | null {
  if (!isRecord(value)) return null;

  const name = readString(value, 'name');
  const kind = readString(value, 'kind');
  const entryPath = value.path;
  const { active, required, present } = value;

  if (
    name === null ||
    kind === null ||
    (entryPath !== null && typeof entryPath !== 'string') ||
    typeof active !== 'boolean' ||
    typeof required !== 'boolean' ||
    typeof present !== 'boolean'
  ) {
    return null;
  }

  return {
    name,
    kind,
    path: entryPath,
    active,
    required,
    present,
  };
}

function normalizeRecentEvent(value: unknown): GenericEditRecentEvent | null {
  if (!isRecord(value)) return null;

  const sequence = value.sequence;
  const eventType = readString(value, 'event_type');

  if (typeof sequence !== 'number' || !Number.isFinite(sequence) || eventType === null) {
    return null;
  }

  const result: GenericEditRecentEvent = {
    sequence,
    event_type: eventType,
  };

  for (const [key, eventValue] of Object.entries(value)) {
    if (key === 'sequence' || key === 'event_type') {
      continue;
    }
    if (
      typeof eventValue === 'string' ||
      typeof eventValue === 'number' ||
      typeof eventValue === 'boolean' ||
      eventValue === null
    ) {
      result[key] = eventValue;
    }
  }

  return result;
}

function normalizeRecentEvents(value: unknown): GenericEditRecentEvent[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;

  const result: GenericEditRecentEvent[] = [];
  for (const event of value) {
    const normalizedEvent = normalizeRecentEvent(event);
    if (!normalizedEvent) {
      return null;
    }
    result.push(normalizedEvent);
  }
  return result;
}

function normalizeStringList(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const result: string[] = [];
  for (const item of value) {
    if (typeof item !== 'string') {
      return null;
    }
    result.push(item);
  }
  return result;
}

function normalizeOptionalMcpStringList(value: Record<string, unknown>, key: string): string[] | null {
  const fieldValue = value[key];
  if (fieldValue === undefined) return [];
  return normalizeStringList(fieldValue);
}

function normalizeOptionalNumber(value: Record<string, unknown>, key: string): number | null | undefined {
  const fieldValue = value[key];
  if (fieldValue === undefined || fieldValue === null) return null;
  if (typeof fieldValue !== 'number' || !Number.isFinite(fieldValue)) return undefined;
  return fieldValue;
}

function normalizeOptionalBoolean(value: Record<string, unknown>, key: string): boolean | null | undefined {
  const fieldValue = value[key];
  if (fieldValue === undefined || fieldValue === null) return null;
  if (typeof fieldValue !== 'boolean') return undefined;
  return fieldValue;
}

function normalizeOptionalRecord(value: Record<string, unknown>, key: string): Record<string, unknown> | null | undefined {
  const fieldValue = value[key];
  if (fieldValue === undefined || fieldValue === null) return null;
  if (!isRecord(fieldValue)) return undefined;
  return { ...fieldValue };
}

function normalizeMcpServerStatus(value: unknown): GenericEditMcpServerStatus | null {
  if (!isRecord(value)) return null;

  const server = readString(value, 'server');
  const bridgeable = normalizeOptionalBoolean(value, 'bridgeable');
  const externalClient = normalizeOptionalRecord(value, 'external_client');

  if (server === null || bridgeable === undefined || externalClient === undefined) {
    return null;
  }

  return {
    server,
    display_name: readString(value, 'display_name'),
    availability: readString(value, 'availability'),
    runtime_path: readString(value, 'runtime_path'),
    bridgeable,
    reason: readString(value, 'reason'),
    notes: readString(value, 'notes'),
    external_client: externalClient,
  };
}

function normalizeOptionalMcpServerStatuses(
  value: Record<string, unknown>,
  key: string
): GenericEditMcpServerStatus[] | null {
  const fieldValue = value[key];
  if (fieldValue === undefined) return [];
  if (!Array.isArray(fieldValue)) return null;

  const result: GenericEditMcpServerStatus[] = [];
  for (const item of fieldValue) {
    const status = normalizeMcpServerStatus(item);
    if (status === null) {
      return null;
    }
    result.push(status);
  }
  return result;
}

function normalizeMcpToolPolicy(value: unknown): GenericEditMcpToolPolicy | null {
  if (!isRecord(value)) return null;

  const name = readString(value, 'name');
  const exposedName = readString(value, 'exposed_name');
  const mutating = normalizeOptionalBoolean(value, 'mutating');
  const auditRequired = normalizeOptionalBoolean(value, 'audit_required');

  if (name === null || exposedName === null || mutating === undefined || auditRequired === undefined) {
    return null;
  }

  return {
    server: readString(value, 'server'),
    name,
    exposed_name: exposedName,
    permission: readString(value, 'permission'),
    audit_level: readString(value, 'audit_level'),
    mutating,
    audit_required: auditRequired,
  };
}

function normalizeOptionalMcpToolPolicies(
  value: Record<string, unknown>,
  key: string
): GenericEditMcpToolPolicy[] | null {
  const fieldValue = value[key];
  if (fieldValue === undefined) return [];
  if (!Array.isArray(fieldValue)) return null;

  const result: GenericEditMcpToolPolicy[] = [];
  for (const item of fieldValue) {
    const policy = normalizeMcpToolPolicy(item);
    if (policy === null) {
      return null;
    }
    result.push(policy);
  }
  return result;
}

function normalizeMcpPermissionPolicy(value: unknown): GenericEditMcpPermissionPolicy | null {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const allowedPermissions = value.allowed_permissions;
  if (allowedPermissions !== null && allowedPermissions !== undefined && !Array.isArray(allowedPermissions)) {
    return null;
  }
  const normalizedAllowedPermissions =
    allowedPermissions === null || allowedPermissions === undefined
      ? null
      : normalizeStringList(allowedPermissions);

  if (normalizedAllowedPermissions === null && Array.isArray(allowedPermissions)) {
    return null;
  }

  return {
    mode: readString(value, 'mode'),
    allowed_permissions: normalizedAllowedPermissions,
  };
}

function normalizeMcpOpenSession(value: unknown): GenericEditMcpOpenSession | null {
  if (!isRecord(value)) return null;

  const server = readString(value, 'server');
  const transport = readString(value, 'transport');
  const status = readString(value, 'status');

  if (server === null || transport === null || status === null) {
    return null;
  }

  return { server, transport, status };
}

function normalizeMcpOpenSessions(value: unknown): GenericEditMcpOpenSession[] | null {
  if (!Array.isArray(value)) return null;

  const result: GenericEditMcpOpenSession[] = [];
  for (const item of value) {
    const session = normalizeMcpOpenSession(item);
    if (session === null) {
      return null;
    }
    result.push(session);
  }
  return result;
}

function normalizeMcpSessionLifecycle(value: unknown): GenericEditMcpSessionLifecycle | null {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const reuse = readString(value, 'reuse');
  const openSessionCount = normalizeOptionalNumber(value, 'open_session_count');
  const openSessions = normalizeMcpOpenSessions(value.open_sessions);

  if (reuse === null || openSessionCount === undefined || openSessionCount === null || openSessions === null) {
    return null;
  }

  return {
    reuse,
    open_session_count: openSessionCount,
    open_sessions: openSessions,
  };
}

function normalizeMcpBridgePlan(
  value: unknown
): NonNullable<GenericEditArtifactManifest['mcp_support']>['bridge_plan'] {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const bridgedServers = normalizeOptionalMcpStringList(value, 'bridged_servers');
  const externalBridgedServers = normalizeOptionalMcpStringList(value, 'external_bridged_servers');
  const nativeRequiredServers = normalizeOptionalMcpStringList(value, 'native_required_servers');
  const localBridgeRequiredServers = normalizeOptionalMcpStringList(value, 'local_bridge_required_servers');
  const externalBridgeRequiredServers = normalizeOptionalMcpStringList(value, 'external_bridge_required_servers');
  const unsupportedServers = normalizeOptionalMcpStringList(value, 'unsupported_servers');
  if (
    bridgedServers === null ||
    externalBridgedServers === null ||
    nativeRequiredServers === null ||
    localBridgeRequiredServers === null ||
    externalBridgeRequiredServers === null ||
    unsupportedServers === null
  ) {
    return null;
  }

  return {
    status: readString(value, 'status'),
    action_required: readString(value, 'action_required'),
    recommended_runtime_path: readString(value, 'recommended_runtime_path'),
    native_required_servers: nativeRequiredServers,
    local_bridge_required_servers: localBridgeRequiredServers,
    external_bridge_required_servers: externalBridgeRequiredServers,
    unsupported_servers: unsupportedServers,
    bridged_servers: bridgedServers,
    external_bridged_servers: externalBridgedServers,
  };
}

function normalizeMcpBridge(
  value: unknown
): NonNullable<GenericEditArtifactManifest['mcp_support']>['bridge'] {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const tools = normalizeOptionalMcpStringList(value, 'tools');
  const toolPolicies = normalizeOptionalMcpToolPolicies(value, 'tool_policies');
  const permissionPolicy = normalizeMcpPermissionPolicy(value.permission_policy);
  const serverStatuses = normalizeOptionalMcpServerStatuses(value, 'server_statuses');
  const sessionLifecycle = normalizeMcpSessionLifecycle(value.session_lifecycle);
  if (
    tools === null ||
    toolPolicies === null ||
    (value.permission_policy !== undefined && value.permission_policy !== null && permissionPolicy === null) ||
    serverStatuses === null ||
    (value.session_lifecycle !== undefined && value.session_lifecycle !== null && sessionLifecycle === null)
  ) {
    return null;
  }

  return {
    tools,
    tool_policies: toolPolicies,
    permission_policy: permissionPolicy,
    server_statuses: serverStatuses,
    session_lifecycle: sessionLifecycle,
  };
}

function normalizeMcpSupport(value: unknown): GenericEditArtifactManifest['mcp_support'] {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const strategy = readString(value, 'strategy');
  const toolCount = normalizeOptionalNumber(value, 'tool_count');
  const availableServers = normalizeOptionalMcpStringList(value, 'available_servers');
  const unavailableServers = normalizeOptionalMcpStringList(value, 'unavailable_servers');
  const serverStatuses = normalizeOptionalMcpServerStatuses(value, 'server_statuses');
  const bridgePlan = normalizeMcpBridgePlan(value.bridge_plan);
  const bridge = normalizeMcpBridge(value.bridge);

  if (
    strategy === null ||
    toolCount === undefined ||
    availableServers === null ||
    unavailableServers === null ||
    serverStatuses === null ||
    (value.bridge_plan !== undefined && value.bridge_plan !== null && bridgePlan === null) ||
    (value.bridge !== undefined && value.bridge !== null && bridge === null)
  ) {
    return null;
  }

  return {
    strategy,
    reason: readString(value, 'reason'),
    server: readString(value, 'server'),
    tool_count: toolCount,
    available_servers: availableServers,
    unavailable_servers: unavailableServers,
    server_statuses: serverStatuses,
    bridge_plan: bridgePlan,
    bridge,
  };
}

function normalizeRecoverySummary(value: unknown): GenericEditRecoverySummary | null {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const version = value.version;
  const status = readString(value, 'status');
  const { finish_blocked, unresolved_transaction_group_count, warning_count } = value;
  const unresolvedTransactionGroupIds = normalizeStringList(value.unresolved_transaction_group_ids);
  const warnings = normalizeStringList(value.warnings);
  const resolutionStrategies = normalizeStringList(value.resolution_strategies);
  const recommendedVerificationTools = normalizeStringList(value.recommended_verification_tools);

  if (
    typeof version !== 'number' ||
    !Number.isFinite(version) ||
    status === null ||
    typeof finish_blocked !== 'boolean' ||
    typeof unresolved_transaction_group_count !== 'number' ||
    !Number.isFinite(unresolved_transaction_group_count) ||
    typeof warning_count !== 'number' ||
    !Number.isFinite(warning_count) ||
    unresolvedTransactionGroupIds === null ||
    warnings === null ||
    resolutionStrategies === null ||
    recommendedVerificationTools === null
  ) {
    return null;
  }

  return {
    version,
    status,
    finish_blocked,
    unresolved_transaction_group_count,
    unresolved_transaction_group_ids: unresolvedTransactionGroupIds,
    warning_count,
    warnings,
    resolution_strategies: resolutionStrategies,
    recommended_verification_tools: recommendedVerificationTools,
  };
}

function normalizeOptionalString(
  result: GenericEditRecoveryAction,
  value: Record<string, unknown>,
  field: 'transaction_id' | 'transaction_group_id' | 'rollback_operation_id'
): boolean {
  const fieldValue = value[field];
  if (fieldValue === undefined) return true;
  if (typeof fieldValue !== 'string') return false;
  result[field] = fieldValue;
  return true;
}

function normalizeOptionalStringList(
  result: GenericEditRecoveryAction,
  value: Record<string, unknown>,
  field: 'paths' | 'mutation_snapshot_ids'
): boolean {
  const fieldValue = value[field];
  if (fieldValue === undefined) return true;
  const normalized = normalizeStringList(fieldValue);
  if (normalized === null) return false;
  result[field] = normalized;
  return true;
}

function normalizeRecoveryAction(value: unknown): GenericEditRecoveryAction | null {
  if (!isRecord(value)) return null;
  const id = readString(value, 'id');
  const kind = readString(value, 'kind');
  const tool = readString(value, 'tool');
  const { required_before_finish } = value;

  if (id === null || kind === null || tool === null || typeof required_before_finish !== 'boolean') {
    return null;
  }

  const result: GenericEditRecoveryAction = {
    id,
    kind,
    tool,
    required_before_finish,
  };
  const optionalStringFields: Array<'transaction_id' | 'transaction_group_id' | 'rollback_operation_id'> = [
    'transaction_id',
    'transaction_group_id',
    'rollback_operation_id',
  ];
  const optionalStringListFields: Array<'paths' | 'mutation_snapshot_ids'> = [
    'paths',
    'mutation_snapshot_ids',
  ];

  for (const field of optionalStringFields) {
    if (!normalizeOptionalString(result, value, field)) return null;
  }
  for (const field of optionalStringListFields) {
    if (!normalizeOptionalStringList(result, value, field)) return null;
  }
  return result;
}

function normalizeRecoveryActions(value: unknown): GenericEditRecoveryAction[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;

  const result: GenericEditRecoveryAction[] = [];
  for (const action of value) {
    const normalizedAction = normalizeRecoveryAction(action);
    if (!normalizedAction) {
      return null;
    }
    result.push(normalizedAction);
  }
  return result;
}

function normalizeNativeToolFallback(value: unknown): GenericEditNativeToolFallback | null {
  if (!isRecord(value)) return null;

  const provider = readString(value, 'provider');
  const fromLoop = readString(value, 'from_loop');
  const toLoop = readString(value, 'to_loop');
  const reason = readString(value, 'reason');
  const message = readString(value, 'message');
  const toolSchemaCount = value.tool_schema_count;

  if (
    provider === null ||
    fromLoop === null ||
    toLoop === null ||
    reason === null ||
    message === null ||
    typeof toolSchemaCount !== 'number' ||
    !Number.isFinite(toolSchemaCount)
  ) {
    return null;
  }

  return {
    provider,
    from_loop: fromLoop,
    to_loop: toLoop,
    reason,
    message,
    tool_schema_count: toolSchemaCount,
  };
}

function normalizeNativeToolFallbacks(value: unknown): GenericEditNativeToolFallback[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;

  const result: GenericEditNativeToolFallback[] = [];
  for (const fallback of value) {
    const normalizedFallback = normalizeNativeToolFallback(fallback);
    if (!normalizedFallback) {
      return null;
    }
    result.push(normalizedFallback);
  }
  return result;
}

function normalizeBatchLifecycleEvent(value: unknown): GenericEditBatchLifecycleEvent | null {
  if (!isRecord(value)) return null;

  const action = readString(value, 'action');
  const transactionId = readString(value, 'transaction_id');
  const status = readString(value, 'status');
  const reason = readString(value, 'reason');
  const blockedTransactionGroupIds =
    value.blocked_transaction_group_ids === undefined
      ? []
      : normalizeStringList(value.blocked_transaction_group_ids);

  if (action === null || blockedTransactionGroupIds === null) {
    return null;
  }

  return {
    action,
    ...(transactionId !== null ? { transaction_id: transactionId } : {}),
    ...(status !== null ? { status } : {}),
    ...(reason !== null ? { reason } : {}),
    blocked_transaction_group_ids: blockedTransactionGroupIds,
  };
}

function normalizeBatchLifecycleEvents(value: unknown): GenericEditBatchLifecycleEvent[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;

  const result: GenericEditBatchLifecycleEvent[] = [];
  for (const event of value) {
    const normalizedEvent = normalizeBatchLifecycleEvent(event);
    if (!normalizedEvent) {
      return null;
    }
    result.push(normalizedEvent);
  }
  return result;
}

function normalizeBatchBoundaryError(value: unknown): GenericEditBatchBoundaryError | null {
  if (!isRecord(value)) return null;

  const tool = readString(value, 'tool');
  const batchId = readString(value, 'batch_id');
  const reason = readString(value, 'reason');
  const blockedTransactionGroupIds =
    value.blocked_transaction_group_ids === undefined
      ? []
      : normalizeStringList(value.blocked_transaction_group_ids);

  if (tool === null || batchId === null || reason === null || blockedTransactionGroupIds === null) {
    return null;
  }

  return {
    tool,
    batch_id: batchId,
    reason,
    blocked_transaction_group_ids: blockedTransactionGroupIds,
  };
}

function normalizeBatchBoundaryErrors(value: unknown): GenericEditBatchBoundaryError[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;

  const result: GenericEditBatchBoundaryError[] = [];
  for (const error of value) {
    const normalizedError = normalizeBatchBoundaryError(error);
    if (!normalizedError) {
      return null;
    }
    result.push(normalizedError);
  }
  return result;
}

function normalizeOptionalBatchStringList(value: Record<string, unknown>, key: string): string[] | null {
  const fieldValue = value[key];
  if (fieldValue === undefined) return [];
  return normalizeStringList(fieldValue);
}

function normalizeOptionalBatchCount(value: Record<string, unknown>, key: string): number | null {
  const fieldValue = value[key];
  if (fieldValue === undefined) return 0;
  return typeof fieldValue === 'number' && Number.isFinite(fieldValue) ? fieldValue : null;
}

function normalizeTransactionBatchStringLists(
  value: Record<string, unknown>
): Pick<
  GenericEditTransactionBatch,
  | 'transaction_ids'
  | 'mutation_snapshot_ids'
  | 'committed_mutation_snapshot_ids'
  | 'commit_operation_ids'
  | 'staged_mutation_ids'
  | 'staged_mutated_paths'
  | 'staged_restored_paths'
  | 'staged_deleted_paths'
  | 'transaction_group_ids'
  | 'unresolved_transaction_group_ids'
  | 'boundary_error_reasons'
  | 'required_next_action_kinds'
  | 'resolution_strategies'
> | null {
  const lists = {
    transaction_ids: normalizeOptionalBatchStringList(value, 'transaction_ids'),
    mutation_snapshot_ids: normalizeOptionalBatchStringList(value, 'mutation_snapshot_ids'),
    committed_mutation_snapshot_ids: normalizeOptionalBatchStringList(
      value,
      'committed_mutation_snapshot_ids'
    ),
    commit_operation_ids: normalizeOptionalBatchStringList(value, 'commit_operation_ids'),
    staged_mutation_ids: normalizeOptionalBatchStringList(value, 'staged_mutation_ids'),
    staged_mutated_paths: normalizeOptionalBatchStringList(value, 'staged_mutated_paths'),
    staged_restored_paths: normalizeOptionalBatchStringList(value, 'staged_restored_paths'),
    staged_deleted_paths: normalizeOptionalBatchStringList(value, 'staged_deleted_paths'),
    transaction_group_ids: normalizeOptionalBatchStringList(value, 'transaction_group_ids'),
    unresolved_transaction_group_ids: normalizeOptionalBatchStringList(
      value,
      'unresolved_transaction_group_ids'
    ),
    boundary_error_reasons: normalizeOptionalBatchStringList(value, 'boundary_error_reasons'),
    required_next_action_kinds: normalizeOptionalBatchStringList(
      value,
      'required_next_action_kinds'
    ),
    resolution_strategies: normalizeOptionalBatchStringList(value, 'resolution_strategies'),
  };
  if (Object.values(lists).some((list) => list === null)) {
    return null;
  }
  return lists as Pick<
    GenericEditTransactionBatch,
    | 'transaction_ids'
    | 'mutation_snapshot_ids'
    | 'committed_mutation_snapshot_ids'
    | 'commit_operation_ids'
    | 'staged_mutation_ids'
    | 'staged_mutated_paths'
    | 'staged_restored_paths'
    | 'staged_deleted_paths'
    | 'transaction_group_ids'
    | 'unresolved_transaction_group_ids'
    | 'boundary_error_reasons'
    | 'required_next_action_kinds'
    | 'resolution_strategies'
  >;
}

function normalizeTransactionBatchCounts(
  value: Record<string, unknown>
): Pick<
  GenericEditTransactionBatch,
  'recovery_outcome_count' | 'staged_mutation_count' | 'staged_path_count' | 'lifecycle_event_count' | 'boundary_error_count'
> | null {
  const counts = {
    recovery_outcome_count: normalizeOptionalBatchCount(value, 'recovery_outcome_count'),
    staged_mutation_count: normalizeOptionalBatchCount(value, 'staged_mutation_count'),
    staged_path_count: normalizeOptionalBatchCount(value, 'staged_path_count'),
    lifecycle_event_count: normalizeOptionalBatchCount(value, 'lifecycle_event_count'),
    boundary_error_count: normalizeOptionalBatchCount(value, 'boundary_error_count'),
  };
  if (Object.values(counts).some((count) => count === null)) {
    return null;
  }
  return counts as Pick<
    GenericEditTransactionBatch,
    'recovery_outcome_count' | 'staged_mutation_count' | 'staged_path_count' | 'lifecycle_event_count' | 'boundary_error_count'
  >;
}

function normalizeTransactionBatch(value: unknown): GenericEditTransactionBatch | null {
  if (!isRecord(value)) return null;

  const id = readString(value, 'id');
  const status = readString(value, 'status');
  const recoveryStatus =
    value.recovery_status === undefined ? 'clean' : readString(value, 'recovery_status');
  const finishBlocked = value.finish_blocked === undefined ? false : value.finish_blocked;
  const stringLists = normalizeTransactionBatchStringLists(value);
  const counts = normalizeTransactionBatchCounts(value);
  const lifecycleEvents = normalizeBatchLifecycleEvents(value.lifecycle_events);
  const boundaryErrors = normalizeBatchBoundaryErrors(value.boundary_errors);

  if (
    id === null ||
    status === null ||
    recoveryStatus === null ||
    typeof finishBlocked !== 'boolean' ||
    stringLists === null ||
    counts === null ||
    lifecycleEvents === null ||
    boundaryErrors === null
  ) {
    return null;
  }

  return {
    id,
    status,
    recovery_status: recoveryStatus,
    finish_blocked: finishBlocked,
    ...stringLists,
    ...counts,
    lifecycle_events: lifecycleEvents,
    boundary_errors: boundaryErrors,
  };
}

function normalizeTransactionBatches(value: unknown): GenericEditTransactionBatch[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;

  const result: GenericEditTransactionBatch[] = [];
  for (const batch of value) {
    const normalizedBatch = normalizeTransactionBatch(batch);
    if (!normalizedBatch) {
      return null;
    }
    result.push(normalizedBatch);
  }
  return result;
}

function normalizeResumeAction(value: unknown): GenericEditResumeAction | null {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const runtime = readString(value, 'runtime');
  const checkpointPath = readString(value, 'checkpoint_path');
  const strategy = readString(value, 'strategy');
  const nextIteration = value.next_iteration;

  if (
    runtime !== 'generic_edit' ||
    checkpointPath === null ||
    strategy === null ||
    typeof nextIteration !== 'number' ||
    !Number.isFinite(nextIteration)
  ) {
    return null;
  }

  return {
    runtime,
    checkpoint_path: checkpointPath,
    strategy,
    next_iteration: nextIteration,
  };
}

function normalizeResumePolicy(value: unknown): GenericEditResumePolicy | null {
  if (value === undefined || value === null) return null;
  if (!isRecord(value)) return null;

  const runtime = readString(value, 'runtime');
  const status = readString(value, 'status');
  const strategy = readString(value, 'strategy');
  const checkpointPath = readString(value, 'checkpoint_path');
  const {
    version,
    can_resume,
    finish_blocked,
    next_iteration,
    required_resolution_action_kinds,
    required_artifacts,
    unresolved_partial_failure_ids,
    unresolved_transaction_group_ids,
  } = value;
  const requiredResolutionActionKinds = normalizeStringList(required_resolution_action_kinds);
  const requiredArtifacts = normalizeStringList(required_artifacts);
  const unresolvedPartialFailureIds = normalizeStringList(unresolved_partial_failure_ids);
  const unresolvedTransactionGroupIds = normalizeStringList(unresolved_transaction_group_ids);
  const openTransactionBatchIds =
    value.open_transaction_batch_ids === undefined
      ? []
      : normalizeStringList(value.open_transaction_batch_ids);

  if (
    typeof version !== 'number' ||
    !Number.isFinite(version) ||
    runtime !== 'generic_edit' ||
    status === null ||
    typeof can_resume !== 'boolean' ||
    typeof finish_blocked !== 'boolean' ||
    strategy === null ||
    checkpointPath === null ||
    typeof next_iteration !== 'number' ||
    !Number.isFinite(next_iteration) ||
    requiredResolutionActionKinds === null ||
    requiredArtifacts === null ||
    unresolvedPartialFailureIds === null ||
    unresolvedTransactionGroupIds === null ||
    openTransactionBatchIds === null
  ) {
    return null;
  }

  const policy: GenericEditResumePolicy = {
    version,
    runtime,
    status,
    can_resume,
    finish_blocked,
    strategy,
    checkpoint_path: checkpointPath,
    next_iteration,
    required_resolution_action_kinds: requiredResolutionActionKinds,
    required_artifacts: requiredArtifacts,
    unresolved_partial_failure_ids: unresolvedPartialFailureIds,
    unresolved_transaction_group_ids: unresolvedTransactionGroupIds,
  };
  if (openTransactionBatchIds.length > 0) {
    policy.open_transaction_batch_ids = openTransactionBatchIds;
  }
  return policy;
}

function normalizeGenericEditArtifactManifest(value: unknown): GenericEditArtifactManifest | null {
  if (!isRecord(value)) return null;
  if (value.artifact_type !== 'generic_edit_artifact_manifest' || value.schema_version !== 1) {
    return null;
  }

  const timestamp = readString(value, 'timestamp');
  const provider = readString(value, 'provider');
  const subtaskId = readNullableString(value, 'subtask_id');
  const status = readString(value, 'status');
  const stopReason = readString(value, 'stop_reason');
  const entrypoints = normalizeStringMap(value.entrypoints);
  const flags = normalizeBooleanMap(value.flags, [
    'recoverable',
    'resumable',
    'resumed',
    'recovery_required',
    'recovery_resolved',
    'has_recovery_plan',
    'has_mutation_snapshots',
    'has_transaction_groups',
  ]);
  const counts = normalizeNumberMap(value.counts, [
    'iteration_count',
    'action_count',
    'failed_action_count',
    'event_count',
    'transaction_count',
    'transaction_group_count',
    'mutation_snapshot_count',
    'recovery_attempt_count',
    'failed_recovery_attempt_count',
  ]);
  const recentEvents = normalizeRecentEvents(value.recent_events);
  const recoveryTimeline = normalizeRecentEvents(value.recovery_timeline);
  const nativeToolFallbacks = normalizeNativeToolFallbacks(value.native_tool_fallbacks);
  const transactionBatches = normalizeTransactionBatches(value.transaction_batches);
  const recoverySummary = normalizeRecoverySummary(value.recovery_summary);
  const recoveryActions = normalizeRecoveryActions(value.recovery_actions);
  const resumeAction = normalizeResumeAction(value.resume_action);
  const resumePolicy = normalizeResumePolicy(value.resume_policy);
  const resumeInputs = value.resume_inputs === undefined ? {} : normalizeStringMap(value.resume_inputs);
  const mcpSupport = normalizeMcpSupport(value.mcp_support);

  if (
    timestamp === null ||
    provider === null ||
    status === null ||
    stopReason === null ||
    entrypoints === null ||
    flags === null ||
    counts === null ||
    recentEvents === null ||
    recoveryTimeline === null ||
    nativeToolFallbacks === null ||
    transactionBatches === null ||
    recoveryActions === null ||
    (value.resume_action !== undefined && value.resume_action !== null && resumeAction === null) ||
    (value.resume_policy !== undefined && value.resume_policy !== null && resumePolicy === null) ||
    resumeInputs === null ||
    !Array.isArray(value.artifacts)
  ) {
    return null;
  }
  if (typeof counts.native_tool_fallback_count !== 'number') {
    counts.native_tool_fallback_count = 0;
  }
  if (typeof counts.transaction_batch_count !== 'number') {
    counts.transaction_batch_count = 0;
  }

  const artifacts: GenericEditArtifactManifestEntry[] = [];
  for (const artifact of value.artifacts) {
    const normalizedArtifact = normalizeManifestEntry(artifact);
    if (!normalizedArtifact) {
      return null;
    }
    artifacts.push(normalizedArtifact);
  }

  return {
    artifact_type: 'generic_edit_artifact_manifest',
    schema_version: 1,
    timestamp,
    provider,
    subtask_id: subtaskId,
    status,
    stop_reason: stopReason,
    entrypoints,
    flags,
    counts,
    artifacts,
    recent_events: recentEvents,
    recovery_timeline: recoveryTimeline,
    native_tool_fallbacks: nativeToolFallbacks,
    transaction_batches: transactionBatches,
    recovery_summary: recoverySummary,
    recovery_actions: recoveryActions,
    mcp_support: mcpSupport,
    resume_action: resumeAction,
    resume_inputs: resumeInputs as Record<string, string>,
    resume_policy: resumePolicy,
    resume: isRecord(value.resume) ? value.resume : null,
  };
}

/**
 * Read the implementation plan from implementation_plan.json
 *
 * @param project - The project containing the task
 * @param task - The task to read the plan for
 * @returns The implementation plan, or null if file doesn't exist
 */
export async function readImplementationPlan(
  project: Project,
  task: Task
): Promise<ImplementationPlan | null> {
  try {
    const specDir = getSpecDir(project, task);
    const planPath = path.join(specDir, AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN);

    const planContent = await fs.readFile(planPath, 'utf-8');
    const plan = JSON.parse(planContent) as ImplementationPlan;

    return plan;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading implementation plan:`, err);
    throw err;
  }
}

/**
 * Read and normalize the Generic Edit v2 artifact manifest.
 *
 * @param project - The project containing the task
 * @param task - The task to read the manifest for
 * @returns The parsed artifact manifest, or null if it doesn't exist or is from another schema
 */
export async function readGenericEditArtifactManifest(
  project: Project,
  task: Task
): Promise<GenericEditArtifactManifest | null> {
  try {
    const specDir = getSpecDir(project, task);
    const manifestPath = path.join(specDir, AUTO_BUILD_PATHS.GENERIC_EDIT_ARTIFACT_MANIFEST);

    const manifestContent = await fs.readFile(manifestPath, 'utf-8');
    const manifest = normalizeGenericEditArtifactManifest(JSON.parse(manifestContent));

    if (!manifest) {
      console.warn(`[spec-file-readers] Generic edit artifact manifest has unsupported schema at ${manifestPath}`);
    }

    return manifest;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading generic edit artifact manifest:`, err);
    throw err;
  }
}

/**
 * Read the Trust Layer verification report from artifacts/verification-report.json
 *
 * @param project - The project containing the task
 * @param task - The task to read the report for
 * @returns The parsed verification report, or null if it doesn't exist
 */
export async function readVerificationReport(
  project: Project,
  task: Task
): Promise<VerificationReport | null> {
  try {
    const specDir = getSpecDir(project, task);
    const reportPath = path.join(specDir, AUTO_BUILD_PATHS.VERIFICATION_REPORT);

    const reportContent = await fs.readFile(reportPath, 'utf-8');
    return JSON.parse(reportContent) as VerificationReport;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading verification report:`, err);
    throw err;
  }
}

/**
 * Read the QA report from qa_report.md
 *
 * @param project - The project containing the task
 * @param task - The task to read the QA report for
 * @returns The QA report content as markdown string, or null if file doesn't exist
 */
export async function readQAReport(project: Project, task: Task): Promise<string | null> {
  try {
    const specDir = getSpecDir(project, task);
    const qaReportPath = path.join(specDir, AUTO_BUILD_PATHS.QA_REPORT);

    const qaReportContent = await fs.readFile(qaReportPath, 'utf-8');
    return qaReportContent;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading QA report:`, err);
    throw err;
  }
}

/**
 * Read the spec document body from spec.md
 *
 * @param project - The project containing the task
 * @param task - The task to read the spec for
 * @returns The spec content as markdown string, or null if file doesn't exist
 */
export async function readSpecContent(project: Project, task: Task): Promise<string | null> {
  try {
    const specDir = getSpecDir(project, task);
    const specPath = path.join(specDir, AUTO_BUILD_PATHS.SPEC_FILE);

    const specContent = await fs.readFile(specPath, 'utf-8');
    return specContent;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading spec content:`, err);
    throw err;
  }
}

/**
 * Parse QA escalation metadata from QA_ESCALATION.md frontmatter
 *
 * The file format is:
 * ---
 * generated: "2024-01-15T10:30:00Z"
 * iteration: 5
 * maxIterations: 5
 * reason: "Max iterations reached"
 * ---
 * [Rest of markdown content]
 */
function parseQAEscalationFrontmatter(content: string): Partial<QAEscalation> | null {
  // Extract frontmatter between --- delimiters using indexOf (avoids ReDoS)
  const firstDelim = content.indexOf('---');
  if (firstDelim === -1) return null;

  const afterFirst = content.indexOf('\n', firstDelim);
  if (afterFirst === -1) return null;

  const secondDelim = content.indexOf('\n---', afterFirst);
  if (secondDelim === -1) return null;

  const frontmatter = content.slice(afterFirst + 1, secondDelim);
  const metadata: Partial<QAEscalation> = {};

  // Parse YAML-like frontmatter line by line
  const lines = frontmatter.split('\n');
  for (const line of lines) {
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;

    const trimmedKey = line.slice(0, colonIdx).trim();
    const value = line.slice(colonIdx + 1).trim().replace(/(^["'])|(['"]$)/g, '');

    if (trimmedKey === 'generated') {
      metadata.generated = value;
    } else if (trimmedKey === 'iteration') {
      metadata.iteration = parseInt(value, 10);
    } else if (trimmedKey === 'maxIterations') {
      metadata.maxIterations = parseInt(value, 10);
    } else if (trimmedKey === 'reason') {
      metadata.reason = value;
    }
  }

  return metadata;
}

/**
 * Parse QA escalation summary section from markdown content
 */
function parseQAEscalationSummary(content: string): QAEscalation['summary'] | null {
  // Find "## Summary" section and parse bullet points (avoids ReDoS)
  const summaryIdx = content.search(/## Summary/i);
  if (summaryIdx === -1) return null;

  const sectionEnd = content.indexOf('\n## ', summaryIdx + 1);
  const section = sectionEnd === -1
    ? content.slice(summaryIdx)
    : content.slice(summaryIdx, sectionEnd);

  const lines = section.split('\n');
  let totalIterations = 0;
  let totalIssues = 0;
  let uniqueIssues = 0;
  let fixSuccessRate = 0;
  let found = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- Total iterations:')) {
      totalIterations = parseInt(trimmed.split(':')[1].trim(), 10);
      found++;
    } else if (trimmed.startsWith('- Total issues found:')) {
      totalIssues = parseInt(trimmed.split(':')[1].trim(), 10);
      found++;
    } else if (trimmed.startsWith('- Unique issues:')) {
      uniqueIssues = parseInt(trimmed.split(':')[1].trim(), 10);
      found++;
    } else if (trimmed.startsWith('- Fix success rate:')) {
      fixSuccessRate = parseFloat(trimmed.split(':')[1].trim()) / 100;
      found++;
    }
  }

  if (found < 4) return null;

  return { totalIterations, totalIssues, uniqueIssues, fixSuccessRate };
}

/**
 * Parse recurring issues section from markdown content
 */
function parseRecurringIssues(content: string): QAEscalation['recurringIssues'] {
  const issues: QAEscalation['recurringIssues'] = [];

  // Find "## Recurring Issues" section using indexOf (avoids ReDoS)
  const sectionIdx = content.search(/## Recurring Issues/i);
  if (sectionIdx === -1) return issues;

  const sectionEnd = content.indexOf('\n## ', sectionIdx + 1);
  const section = sectionEnd === -1
    ? content.slice(sectionIdx)
    : content.slice(sectionIdx, sectionEnd);

  const lines = section.split('\n');
  let currentTitle = '';
  let currentFile = '';
  let currentLine = 0;
  let currentType = '';
  let currentOccurrences = 0;
  let currentDescription = '';
  let inIssue = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('### ')) {
      if (inIssue && currentTitle) {
        issues.push({
          title: currentTitle,
          file: currentFile || undefined,
          line: currentLine,
          type: currentType,
          occurrences: currentOccurrences,
          description: currentDescription
        });
      }
      currentTitle = trimmed.slice(4).trim();
      currentFile = '';
      currentLine = 0;
      currentType = '';
      currentOccurrences = 0;
      currentDescription = '';
      inIssue = true;
    } else if (inIssue) {
      if (trimmed.startsWith('- File:')) {
        const backtickStart = trimmed.indexOf('`');
        const backtickEnd = trimmed.lastIndexOf('`');
        currentFile = backtickStart >= 0 && backtickEnd > backtickStart
          ? trimmed.slice(backtickStart + 1, backtickEnd)
          : '';
      } else if (trimmed.startsWith('- Line:')) {
        currentLine = parseInt(trimmed.split(':')[1].trim(), 10);
      } else if (trimmed.startsWith('- Type:')) {
        currentType = trimmed.slice(trimmed.indexOf(':') + 1).trim();
      } else if (trimmed.startsWith('- Occurrences:')) {
        currentOccurrences = parseInt(trimmed.split(':')[1].trim(), 10);
      } else if (trimmed.startsWith('- Description:')) {
        currentDescription = trimmed.slice(trimmed.indexOf(':') + 1).trim();
      }
    }
  }

  // Push last issue
  if (inIssue && currentTitle) {
    issues.push({
      title: currentTitle,
      file: currentFile || undefined,
      line: currentLine,
      type: currentType,
      occurrences: currentOccurrences,
      description: currentDescription
    });
  }

  return issues;
}

/**
 * Parse most common issues section from markdown content
 */
function parseMostCommonIssues(content: string): QAEscalation['mostCommonIssues'] {
  const issues: QAEscalation['mostCommonIssues'] = [];

  // Find "## Most Common Issues" section using indexOf (avoids ReDoS)
  const sectionIdx = content.search(/## Most Common Issues/i);
  if (sectionIdx === -1) return issues;

  const sectionEnd = content.indexOf('\n## ', sectionIdx + 1);
  const section = sectionEnd === -1
    ? content.slice(sectionIdx)
    : content.slice(sectionIdx, sectionEnd);

  // Parse numbered list items: "1. **Title** (N occurrences) - File: `path`"
  const lines = section.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    // Match lines starting with a number and dot
    if (!/^\d+\./.test(trimmed)) continue;

    const boldStart = trimmed.indexOf('**');
    const boldEnd = trimmed.indexOf('**', boldStart + 2);
    if (boldStart === -1 || boldEnd === -1) continue;

    const title = trimmed.slice(boldStart + 2, boldEnd).trim();

    const parenStart = trimmed.indexOf('(', boldEnd);
    const parenEnd = trimmed.indexOf(')', parenStart);
    let occurrences = 0;
    if (parenStart >= 0 && parenEnd >= 0) {
      occurrences = parseInt(trimmed.slice(parenStart + 1, parenEnd), 10);
    }

    let file: string | undefined;
    const backtickStart = trimmed.indexOf('`', parenEnd);
    const backtickEnd = trimmed.indexOf('`', backtickStart + 1);
    if (backtickStart >= 0 && backtickEnd > backtickStart) {
      file = trimmed.slice(backtickStart + 1, backtickEnd).trim() || undefined;
    }

    issues.push({ title, occurrences, file });
  }

  return issues;
}

/**
 * Read and parse QA escalation from QA_ESCALATION.md
 *
 * @param project - The project containing the task
 * @param task - The task to read the QA escalation for
 * @returns The parsed QA escalation data, or null if file doesn't exist
 */
export async function readQAEscalation(project: Project, task: Task): Promise<QAEscalation | null> {
  try {
    const specDir = getSpecDir(project, task);
    const escalationPath = path.join(specDir, 'QA_ESCALATION.md');

    const escalationContent = await fs.readFile(escalationPath, 'utf-8');

    // Parse frontmatter
    const metadata = parseQAEscalationFrontmatter(escalationContent);
    if (!metadata) {
      console.warn(`[spec-file-readers] QA escalation missing frontmatter at ${escalationPath}`);
      return null;
    }

    // Parse summary section
    const summary = parseQAEscalationSummary(escalationContent);
    if (!summary) {
      console.warn(`[spec-file-readers] QA escalation missing summary section at ${escalationPath}`);
      return null;
    }

    // Parse recurring issues
    const recurringIssues = parseRecurringIssues(escalationContent);

    // Parse most common issues
    const mostCommonIssues = parseMostCommonIssues(escalationContent);

    // Construct the full QAEscalation object
    const escalation: QAEscalation = {
      generated: metadata.generated || new Date().toISOString(),
      iteration: metadata.iteration || 0,
      maxIterations: metadata.maxIterations || 0,
      reason: metadata.reason || '',
      summary,
      recurringIssues,
      mostCommonIssues
    };

    return escalation;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading QA escalation:`, err);
    throw err;
  }
}
