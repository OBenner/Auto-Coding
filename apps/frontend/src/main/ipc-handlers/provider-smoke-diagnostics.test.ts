import { describe, expect, it } from 'vitest';

import {
  mapProviderContractHealth,
  mapProviderRuntimeResumePolicy,
  mapProviderToolLoopContract
} from './provider-smoke-diagnostics';

describe('mapProviderRuntimeResumePolicy', () => {
  it('maps safe generic edit resume policy fields from provider smoke diagnostics', () => {
    expect(
      mapProviderRuntimeResumePolicy({
        status: 'requires_resolution',
        strategy: 'recover_partial_failure',
        can_resume: true,
        finish_blocked: true,
        next_iteration: 4,
        checkpoint_path: 'workspace-private/checkpoint.json',
        required_resolution_action_kinds: ['inspect_diff', 'rollback_transaction', 42],
        required_artifacts: ['trace_artifact', 'recovery_plan_artifact', null],
        unresolved_partial_failure_ids: ['json_actions-1'],
        unresolved_transaction_group_ids: ['transaction-group-1'],
        open_transaction_batch_ids: ['batch-1', 12],
      })
    ).toEqual({
      status: 'requires_resolution',
      strategy: 'recover_partial_failure',
      canResume: true,
      finishBlocked: true,
      nextIteration: 4,
      requiredResolutionActionKinds: ['inspect_diff', 'rollback_transaction'],
      requiredArtifacts: ['trace_artifact', 'recovery_plan_artifact'],
      unresolvedPartialFailureIds: ['json_actions-1'],
      unresolvedTransactionGroupIds: ['transaction-group-1'],
      openTransactionBatchIds: ['batch-1'],
    });
  });
});

describe('mapProviderToolLoopContract', () => {
  it('maps safe generic edit tool-loop contract fields', () => {
    expect(
      mapProviderToolLoopContract({
        status: 'needs_recovery',
        tool_call_support: 'json_fallback',
        tool_result_support: 'partial_failure',
        fallback: 'json_actions',
        fallback_reason: 'native_tool_request_failed',
        recovery_status: 'requires_resolution',
        blocking_reason: 'unresolved_partial_failure',
        ignored_private_path: 'workspace-private/checkpoint.json',
      })
    ).toEqual({
      status: 'needs_recovery',
      toolCallSupport: 'json_fallback',
      toolResultSupport: 'partial_failure',
      fallback: 'json_actions',
      fallbackReason: 'native_tool_request_failed',
      recoveryStatus: 'requires_resolution',
      blockingReason: 'unresolved_partial_failure',
    });
  });

  it('returns undefined for empty tool-loop contract payloads', () => {
    expect(mapProviderToolLoopContract({})).toBeUndefined();
  });
});

describe('mapProviderContractHealth', () => {
  it('maps safe provider contract health fields', () => {
    expect(
      mapProviderContractHealth({
        status: 'gateway_blocked',
        smoke_scope: 'generic_edit_tool_loop',
        reason: 'gateway_error',
        message: '502 Bad gateway from LiteLLM upstream',
        tool_call_support: 'json_fallback',
        tool_result_support: 'normalized',
        fallback: 'json_actions',
        fallback_reason: 'native_tool_request_failed',
        recovery_status: 'not_required',
        ignored_private_path: 'workspace-private/provider-state.json',
      })
    ).toEqual({
      status: 'gateway_blocked',
      smokeScope: 'generic_edit_tool_loop',
      reason: 'gateway_error',
      message: '502 Bad gateway from LiteLLM upstream',
      toolCallSupport: 'json_fallback',
      toolResultSupport: 'normalized',
      fallback: 'json_actions',
      fallbackReason: 'native_tool_request_failed',
      recoveryStatus: 'not_required',
    });
  });

  it('returns undefined for empty provider contract health payloads', () => {
    expect(mapProviderContractHealth({})).toBeUndefined();
  });
});
