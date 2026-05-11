import { describe, expect, it } from 'vitest';

import {
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
        checkpoint_path: '/tmp/private/checkpoint.json',
        required_resolution_action_kinds: ['inspect_diff', 'rollback_transaction', 42],
        required_artifacts: ['trace_artifact', 'recovery_plan_artifact', null],
        unresolved_partial_failure_ids: ['json_actions-1'],
        unresolved_transaction_group_ids: ['transaction-group-1'],
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
        ignored_private_path: '/tmp/checkpoint.json',
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
