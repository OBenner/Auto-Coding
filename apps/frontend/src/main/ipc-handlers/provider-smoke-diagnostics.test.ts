import { describe, expect, it } from 'vitest';

import { mapProviderRuntimeResumePolicy } from './provider-smoke-diagnostics';

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
