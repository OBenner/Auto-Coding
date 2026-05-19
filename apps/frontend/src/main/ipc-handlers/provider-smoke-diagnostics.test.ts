import { describe, expect, it } from 'vitest';

import {
  mapProviderAutonomousReadiness,
  mapProviderContractHealth,
  mapProviderE2eSuite,
  mapProviderLiveFaultProbes,
  mapProviderNegativeFixtures,
  mapProviderReliability,
  mapProviderRunHistory,
  mapProviderRuntimeResumePolicy,
  mapProviderTransactionBatchContract,
  mapProviderToolLoopContract
} from './provider-smoke-diagnostics';

describe('mapProviderAutonomousReadiness', () => {
  it('maps safe provider autonomous readiness fields', () => {
    expect(
      mapProviderAutonomousReadiness({
        status: 'warming_up',
        provider: 'openai',
        source: 'provider_autonomous_readiness',
        recommendation: 'limited_autonomous_until_evidence_stable',
        recommendation_reasons: ['history_warming_up', 'live_fault_probe_missing', 42],
        blockers: ['provider_e2e_failed', null],
        warnings: ['provider_history_warming_up', 7],
        next_actions: ['collect_provider_history_runs', null],
        evidence: ['provider_e2e_passed', 'live_fault_probes_passed', false],
        requirements: {
          min_stable_runs: 3,
          observed_recent_window: 2,
          observed_consecutive_passes: 2,
          history_stability_complete: false,
          required_live_fault_cases: ['gateway_model_limitations', 42],
          live_fault_covered_cases: ['unsupported_tools'],
          live_fault_missing_cases: ['gateway_model_limitations'],
          live_fault_coverage_complete: false,
          ignored_private_path: 'workspace-private/requirements.json',
        },
        missing_requirements: ['stable_history_runs', null],
        ignored_private_path: 'workspace-private/readiness.json',
      })
    ).toEqual({
      status: 'warming_up',
      provider: 'openai',
      source: 'provider_autonomous_readiness',
      recommendation: 'limited_autonomous_until_evidence_stable',
      recommendationReasons: ['history_warming_up', 'live_fault_probe_missing'],
      blockers: ['provider_e2e_failed'],
      warnings: ['provider_history_warming_up'],
      nextActions: ['collect_provider_history_runs'],
      evidence: ['provider_e2e_passed', 'live_fault_probes_passed'],
      requirements: {
        minStableRuns: 3,
        observedRecentWindow: 2,
        observedConsecutivePasses: 2,
        historyStabilityComplete: false,
        requiredLiveFaultCases: ['gateway_model_limitations'],
        liveFaultCoveredCases: ['unsupported_tools'],
        liveFaultMissingCases: ['gateway_model_limitations'],
        liveFaultCoverageComplete: false,
      },
      missingRequirements: ['stable_history_runs'],
    });
  });

  it('returns undefined for empty readiness payloads', () => {
    expect(mapProviderAutonomousReadiness({})).toBeUndefined();
  });
});

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
        staged_isolation_statuses: ['isolated', null],
        staged_workspace_restore_statuses: ['restored', 7],
        staged_baseline_paths: ['batched.txt', false],
        batch_lifecycle_actions: ['begin_batch', 'commit_batch', null],
        batch_lifecycle_statuses: ['open', 'blocked', 7],
        committed_mutation_snapshot_ids: ['mutation-1', null],
        commit_operation_ids: ['batch-1:commit', 7],
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
      stagedIsolationStatuses: ['isolated'],
      stagedWorkspaceRestoreStatuses: ['restored'],
      stagedBaselinePaths: ['batched.txt'],
      batchLifecycleActions: ['begin_batch', 'commit_batch'],
      batchLifecycleStatuses: ['open', 'blocked'],
      committedMutationSnapshotIds: ['mutation-1'],
      commitOperationIds: ['batch-1:commit'],
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

describe('mapProviderLiveFaultProbes', () => {
  it('maps safe provider live fault probe fields', () => {
    expect(
      mapProviderLiveFaultProbes({
        status: 'passed',
        provider: 'openai',
        source: 'provider_live_fault_fixture',
        enabled: true,
        covered_cases: ['unsupported_tools', 'gateway_model_limitations', null],
        required_env: ['AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES'],
        missing_env: ['AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR'],
        probes: {
          unsupported_tools: {
            status: 'passed',
            source: 'provider_live_fault_fixture',
            reason: 'unsupported_tools',
            env_name: 'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR',
          },
        },
        ignored_private_path: 'workspace-private/provider-live-fixture.json',
      })
    ).toEqual({
      status: 'passed',
      provider: 'openai',
      source: 'provider_live_fault_fixture',
      enabled: true,
      coveredCases: ['unsupported_tools', 'gateway_model_limitations'],
      requiredEnv: ['AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES'],
      missingEnv: ['AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR'],
      probes: [
        {
          case: 'unsupported_tools',
          status: 'passed',
          source: 'provider_live_fault_fixture',
          reason: 'unsupported_tools',
          envName: 'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR',
        },
      ],
    });
  });

  it('returns undefined for empty provider live fault probe payloads', () => {
    expect(mapProviderLiveFaultProbes({})).toBeUndefined();
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
        e2e_case_count: 7,
        e2e_passed_case_count: 7,
        e2e_failed_case_count: 0,
        e2e_case_pass_rate_percent: 100,
        reliability_observed_case_count: 8,
        reliability_passed_case_count: 8,
        reliability_required_case_count: 8,
        reliability_case_pass_rate_percent: 100,
        last_live_fault_probe_status: 'passed',
        live_fault_probe_enabled_runs: 2,
        live_fault_probe_passed_runs: 2,
        live_fault_probe_covered_cases: ['unsupported_tools', 'gateway_model_limitations', null],
        pass_rate_percent: 67,
        recent_pass_rate_percent: 100,
        observed_live_fault_case_count: 2,
        required_live_fault_case_count: 2,
        live_fault_probe_case_coverage_percent: 100,
        trend: 'provider_history_stable',
        trend_reason: 'recent_runs_all_passed',
        recent_window: 3,
        recent_passed_runs: 3,
        recent_failed_runs: 0,
        recent_runs: [
          {
            timestamp: '2026-05-18T09:00:00Z',
            status: 'failed',
            runtime_mode: 'provider_e2e',
            model: 'gpt-4o',
            ignored_private_path: 'workspace-private/old-run.json',
          },
          {
            timestamp: '2026-05-18T09:05:00Z',
            status: 'passed',
            runtime_mode: 'provider_e2e',
            model: 'gpt-4o',
            reliability_status: 'complete',
            provider_e2e_status: 'passed',
            live_fault_probe_status: 'passed',
          },
          null,
        ],
        consecutive_passes: 3,
        consecutive_failures: 0,
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
      e2eCaseCount: 7,
      e2ePassedCaseCount: 7,
      e2eFailedCaseCount: 0,
      e2eCasePassRatePercent: 100,
      reliabilityObservedCaseCount: 8,
      reliabilityPassedCaseCount: 8,
      reliabilityRequiredCaseCount: 8,
      reliabilityCasePassRatePercent: 100,
      lastLiveFaultProbeStatus: 'passed',
      liveFaultProbeEnabledRuns: 2,
      liveFaultProbePassedRuns: 2,
      liveFaultProbeCoveredCases: ['unsupported_tools', 'gateway_model_limitations'],
      passRatePercent: 67,
      recentPassRatePercent: 100,
      observedLiveFaultCaseCount: 2,
      requiredLiveFaultCaseCount: 2,
      liveFaultProbeCaseCoveragePercent: 100,
      trend: 'provider_history_stable',
      trendReason: 'recent_runs_all_passed',
      recentWindow: 3,
      recentPassedRuns: 3,
      recentFailedRuns: 0,
      recentRuns: [
        {
          timestamp: '2026-05-18T09:00:00Z',
          status: 'failed',
          runtimeMode: 'provider_e2e',
          model: 'gpt-4o',
        },
        {
          timestamp: '2026-05-18T09:05:00Z',
          status: 'passed',
          runtimeMode: 'provider_e2e',
          model: 'gpt-4o',
          reliabilityStatus: 'complete',
          providerE2eStatus: 'passed',
          liveFaultProbeStatus: 'passed',
        },
      ],
      consecutivePasses: 3,
      consecutiveFailures: 0,
      path: '.auto-Codex/provider-smoke-history.json',
    });
  });

  it('returns undefined for empty provider run history payloads', () => {
    expect(mapProviderRunHistory({})).toBeUndefined();
  });
});
