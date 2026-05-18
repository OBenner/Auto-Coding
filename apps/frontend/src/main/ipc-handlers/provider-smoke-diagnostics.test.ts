import { describe, expect, it } from 'vitest';

import {
  mapProviderContractHealth,
  mapProviderE2eSuite,
  mapProviderNegativeFixtures,
  mapProviderReliability,
  mapProviderRunHistory,
  mapProviderRuntimeResumePolicy,
  mapProviderTransactionBatchContract,
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

describe('mapProviderTransactionBatchContract', () => {
  it('maps safe generic edit batch-boundary contract fields', () => {
    expect(
      mapProviderTransactionBatchContract({
        status: 'boundary_guarded',
        batch_boundary_guard: 'pre_execution_blocked',
        transaction_batch_count: 0,
        open_transaction_batch_ids: ['batch-1', 42],
        boundary_error_count: 1,
        boundary_error_reasons: ['batch_boundary_violation', null],
        boundary_preferred_strategy: 'abort_batch',
        boundary_required_action_kinds: ['abort_batch', 'repair_mutation', null],
        boundary_resolution_strategies: ['abort_batch', 'repair_mutation', 7],
        staged_workspace_guard_statuses: ['drifted', null],
        staged_drift_paths: ['batched.txt', 9],
        batch_lifecycle_actions: ['begin_batch', 'commit_batch', null],
        batch_lifecycle_statuses: ['open', 'blocked', 7],
        ignored_private_path: 'workspace-private/checkpoint.json',
      })
    ).toEqual({
      status: 'boundary_guarded',
      batchBoundaryGuard: 'pre_execution_blocked',
      transactionBatchCount: 0,
      openTransactionBatchIds: ['batch-1'],
      boundaryErrorCount: 1,
      boundaryErrorReasons: ['batch_boundary_violation'],
      boundaryPreferredStrategy: 'abort_batch',
      boundaryRequiredActionKinds: ['abort_batch', 'repair_mutation'],
      boundaryResolutionStrategies: ['abort_batch', 'repair_mutation'],
      stagedWorkspaceGuardStatuses: ['drifted'],
      stagedDriftPaths: ['batched.txt'],
      batchLifecycleActions: ['begin_batch', 'commit_batch'],
      batchLifecycleStatuses: ['open', 'blocked'],
    });
  });

  it('returns undefined for empty transaction batch contract payloads', () => {
    expect(mapProviderTransactionBatchContract({})).toBeUndefined();
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

describe('mapProviderReliability', () => {
  it('maps safe provider reliability coverage fields', () => {
    expect(
      mapProviderReliability({
        provider: 'openai',
        suite: 'direct_api_full_autonomy',
        status: 'partial_coverage',
        observed_case_count: 5,
        passed_case_count: 5,
        required_case_count: 7,
        uncovered_cases: ['unsupported_tools', 'gateway_model_limitations', null],
        ignored_private_path: 'workspace-private/provider-state.json',
        cases: [
          {
            case: 'text_completion',
            status: 'passed',
            source: 'mini_pipeline',
          },
          {
            case: 'unsupported_tools',
            status: 'not_covered',
            source: 'provider_e2e_required',
            ignored_private_path: 'workspace-private/trace.json',
          },
          null,
        ],
      })
    ).toEqual({
      provider: 'openai',
      suite: 'direct_api_full_autonomy',
      status: 'partial_coverage',
      observedCaseCount: 5,
      passedCaseCount: 5,
      requiredCaseCount: 7,
      uncoveredCases: ['unsupported_tools', 'gateway_model_limitations'],
      cases: [
        {
          case: 'text_completion',
          status: 'passed',
          source: 'mini_pipeline',
        },
        {
          case: 'unsupported_tools',
          status: 'not_covered',
          source: 'provider_e2e_required',
        },
      ],
    });
  });

  it('returns undefined for empty provider reliability payloads', () => {
    expect(mapProviderReliability({})).toBeUndefined();
  });
});

describe('mapProviderE2eSuite', () => {
  it('maps safe provider e2e suite run fields', () => {
    expect(
      mapProviderE2eSuite({
        status: 'passed',
        ignored_private_path: 'workspace-private/provider-e2e.json',
        runs: [
          {
            runtime_mode: 'generic_edit',
            status: 'passed',
            message: 'generic_edit passed',
          },
          {
            runtime_mode: 'mini_pipeline',
            status: 'failed',
            message: 'mini_pipeline failed',
            reason: 'unit_tests_failed',
            ignored_private_path: 'workspace-private/trace.json',
          },
          null,
        ],
      })
    ).toEqual({
      status: 'passed',
      runs: [
        {
          runtimeMode: 'generic_edit',
          status: 'passed',
          message: 'generic_edit passed',
        },
        {
          runtimeMode: 'mini_pipeline',
          status: 'failed',
          message: 'mini_pipeline failed',
          reason: 'unit_tests_failed',
        },
      ],
    });
  });

  it('returns undefined for empty provider e2e suite payloads', () => {
    expect(mapProviderE2eSuite({})).toBeUndefined();
  });
});

describe('mapProviderNegativeFixtures', () => {
  it('maps safe provider negative fixture coverage fields', () => {
    expect(
      mapProviderNegativeFixtures({
        status: 'passed',
        provider: 'openai',
        source: 'provider_adapter_negative_fixture',
        covered_cases: ['unsupported_tools', 'gateway_model_limitations', null],
        ignored_private_path: 'workspace-private/provider-fixture.json',
      })
    ).toEqual({
      status: 'passed',
      provider: 'openai',
      source: 'provider_adapter_negative_fixture',
      coveredCases: ['unsupported_tools', 'gateway_model_limitations'],
    });
  });

  it('returns undefined for empty provider negative fixture payloads', () => {
    expect(mapProviderNegativeFixtures({})).toBeUndefined();
  });
});

describe('mapProviderRunHistory', () => {
  it('maps safe persisted provider run history fields', () => {
    expect(
      mapProviderRunHistory({
        status: 'recorded',
        provider: 'openai',
        runtime_mode: 'provider_e2e',
        total_runs: 3,
        passed_runs: 2,
        failed_runs: 1,
        last_status: 'passed',
        last_reliability_status: 'complete',
        last_provider_e2e_status: 'passed',
        path: '.auto-Codex/provider-smoke-history.json',
        ignored_private_path: 'workspace-private/provider-history.json',
      })
    ).toEqual({
      status: 'recorded',
      provider: 'openai',
      runtimeMode: 'provider_e2e',
      totalRuns: 3,
      passedRuns: 2,
      failedRuns: 1,
      lastStatus: 'passed',
      lastReliabilityStatus: 'complete',
      lastProviderE2eStatus: 'passed',
      path: '.auto-Codex/provider-smoke-history.json',
    });
  });

  it('returns undefined for empty provider run history payloads', () => {
    expect(mapProviderRunHistory({})).toBeUndefined();
  });
});
