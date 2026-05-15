import type {
  ProviderContractHealth,
  ProviderValidatedRuntimeResumePolicy,
  ProviderValidatedToolLoopContract
} from '../../shared/types';

function arrayFromUnknown(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.length > 0)
    : [];
}

function stringFromUnknown(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function booleanFromUnknown(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

function numberFromUnknown(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export function mapProviderRuntimeResumePolicy(
  value: unknown
): ProviderValidatedRuntimeResumePolicy | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const policy: ProviderValidatedRuntimeResumePolicy = {
    status: stringFromUnknown(payload.status),
    strategy: stringFromUnknown(payload.strategy),
    canResume: booleanFromUnknown(payload.can_resume),
    finishBlocked: booleanFromUnknown(payload.finish_blocked),
    nextIteration: numberFromUnknown(payload.next_iteration),
    requiredResolutionActionKinds: arrayFromUnknown(
      payload.required_resolution_action_kinds
    ),
    requiredArtifacts: arrayFromUnknown(payload.required_artifacts),
    unresolvedPartialFailureIds: arrayFromUnknown(
      payload.unresolved_partial_failure_ids
    ),
    unresolvedTransactionGroupIds: arrayFromUnknown(
      payload.unresolved_transaction_group_ids
    ),
    openTransactionBatchIds: arrayFromUnknown(payload.open_transaction_batch_ids),
  };

  return Object.values(policy).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? policy
    : undefined;
}

export function mapProviderToolLoopContract(
  value: unknown
): ProviderValidatedToolLoopContract | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const contract: ProviderValidatedToolLoopContract = {
    status: stringFromUnknown(payload.status),
    toolCallSupport: stringFromUnknown(payload.tool_call_support),
    toolResultSupport: stringFromUnknown(payload.tool_result_support),
    fallback: stringFromUnknown(payload.fallback),
    fallbackReason: stringFromUnknown(payload.fallback_reason),
    recoveryStatus: stringFromUnknown(payload.recovery_status),
    blockingReason: stringFromUnknown(payload.blocking_reason),
  };

  return Object.values(contract).some((field) => field !== undefined)
    ? contract
    : undefined;
}

export function mapProviderContractHealth(
  value: unknown
): ProviderContractHealth | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const health: ProviderContractHealth = {
    status: stringFromUnknown(payload.status),
    smokeScope: stringFromUnknown(payload.smoke_scope),
    reason: stringFromUnknown(payload.reason),
    message: stringFromUnknown(payload.message),
    toolCallSupport: stringFromUnknown(payload.tool_call_support),
    toolResultSupport: stringFromUnknown(payload.tool_result_support),
    fallback: stringFromUnknown(payload.fallback),
    fallbackReason: stringFromUnknown(payload.fallback_reason),
    recoveryStatus: stringFromUnknown(payload.recovery_status),
  };

  return Object.values(health).some((field) => field !== undefined)
    ? health
    : undefined;
}
