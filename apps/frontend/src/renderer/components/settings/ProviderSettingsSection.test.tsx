/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest';

import {
  buildProviderE2eSuiteDiagnosticRows,
  buildProviderNegativeFixtureDiagnosticRows,
  buildProviderReliabilityDiagnosticRows,
  buildProviderResumePolicyDiagnosticRows,
  buildProviderRunHistoryDiagnosticRows,
  buildProviderTransactionBatchDiagnosticRows,
  buildRuntimeEvalDiagnosticRows,
  buildRuntimePolicyDiagnosticRows
} from './ProviderSettingsSection';

const translate = (key: string) =>
  ({
    'settings:aiProvider.connectionTest.resumePolicy': 'Resume policy',
    'settings:aiProvider.connectionTest.resumeStrategy': 'Resume strategy',
    'settings:aiProvider.connectionTest.resumeCanResume': 'Can resume',
    'settings:aiProvider.connectionTest.resumeFinishBlocked': 'Finish blocked',
    'settings:aiProvider.connectionTest.resumeNextIteration': 'Next iteration',
    'settings:aiProvider.connectionTest.resumeRequiredActions': 'Required recovery actions',
    'settings:aiProvider.connectionTest.resumeRequiredArtifacts': 'Required resume artifacts',
    'settings:aiProvider.connectionTest.resumeUnresolvedFailures': 'Unresolved partial failures',
    'settings:aiProvider.connectionTest.resumeUnresolvedGroups': 'Unresolved transaction groups',
    'settings:aiProvider.connectionTest.resumeOpenBatches': 'Open transaction batches',
    'settings:aiProvider.connectionTest.batchContract': 'Batch contract',
    'settings:aiProvider.connectionTest.batchBoundaryGuard': 'Batch boundary guard',
    'settings:aiProvider.connectionTest.batchCount': 'Transaction batches',
    'settings:aiProvider.connectionTest.batchBoundaryErrors': 'Batch boundary errors',
    'settings:aiProvider.connectionTest.batchOpenBatches': 'Open batches',
    'settings:aiProvider.connectionTest.batchPreferredStrategy': 'Batch preferred strategy',
    'settings:aiProvider.connectionTest.batchRequiredActions': 'Batch required actions',
    'settings:aiProvider.connectionTest.batchResolutionStrategies': 'Batch resolution strategies',
    'settings:aiProvider.connectionTest.reliabilityStatus': 'Provider reliability',
    'settings:aiProvider.connectionTest.reliabilitySuite': 'Reliability suite',
    'settings:aiProvider.connectionTest.reliabilityCoverage': 'Reliability coverage',
    'settings:aiProvider.connectionTest.reliabilityUncovered': 'Reliability uncovered',
    'settings:aiProvider.connectionTest.reliabilityCases': 'Reliability cases',
    'settings:aiProvider.connectionTest.providerE2eSuite': 'Provider e2e suite',
    'settings:aiProvider.connectionTest.providerE2eRuns': 'Provider e2e runs',
    'settings:aiProvider.connectionTest.providerNegativeFixtures': 'Provider negative fixtures',
    'settings:aiProvider.connectionTest.providerNegativeFixtureCases': 'Negative fixture cases',
    'settings:aiProvider.connectionTest.providerRunHistory': 'Provider run history',
    'settings:aiProvider.connectionTest.providerRunHistoryRuns': 'Provider history runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLast': 'Provider history latest',
    'settings:aiProvider.connectionTest.providerRunHistoryPath': 'Provider history artifact',
    'settings:aiProvider.controlPlane.runtimePolicy': 'Runtime policy',
    'settings:aiProvider.controlPlane.runtimeEval': 'Runtime evals',
    'settings:aiProvider.runtimeDiagnosticValues.abortBatch': 'Abort batch',
    'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryGuarded': 'Boundary guarded',
    'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryViolation': 'Batch boundary violation',
    'settings:aiProvider.runtimeDiagnosticValues.blocked': 'Blocked',
    'settings:aiProvider.runtimeDiagnosticValues.coder': 'Coder',
    'settings:aiProvider.runtimeDiagnosticValues.complete': 'Complete',
    'settings:aiProvider.runtimeDiagnosticValues.directApiFullAutonomy': 'Direct API full autonomy',
    'settings:aiProvider.runtimeDiagnosticValues.failed': 'Failed',
    'settings:aiProvider.runtimeDiagnosticValues.inspectDiff': 'Inspect diff',
    'settings:aiProvider.runtimeDiagnosticValues.notCovered': 'Not covered',
    'settings:aiProvider.runtimeDiagnosticValues.partialCoverage': 'Partial coverage',
    'settings:aiProvider.runtimeDiagnosticValues.preExecutionBlocked': 'Pre-execution blocked',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eRequired': 'Provider e2e required',
    'settings:aiProvider.runtimeDiagnosticValues.ready': 'Ready',
    'settings:aiProvider.runtimeDiagnosticValues.repairMutation': 'Repair mutation',
    'settings:aiProvider.runtimeDiagnosticValues.recoverPartialFailure': 'Recover partial failure',
    'settings:aiProvider.runtimeDiagnosticValues.gatewayModelLimitations': 'Gateway model limitations',
    'settings:aiProvider.runtimeDiagnosticValues.gatewayModelProbe': 'Gateway/model probe',
    'settings:aiProvider.runtimeDiagnosticValues.genericEdit': 'Generic edit',
    'settings:aiProvider.runtimeDiagnosticValues.miniPipeline': 'Mini pipeline',
    'settings:aiProvider.runtimeDiagnosticValues.passed': 'Passed',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2e': 'Provider e2e',
    'settings:aiProvider.runtimeDiagnosticValues.providerAdapterNegativeFixture':
      'Provider adapter negative fixture',
    'settings:aiProvider.runtimeDiagnosticValues.codexCli': 'Codex CLI',
    'settings:aiProvider.runtimeDiagnosticValues.mustUseFullRuntime': 'Must use full runtime',
    'settings:aiProvider.runtimeDiagnosticValues.preferGenericEdit': 'Prefer generic edit',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eSuite': 'Provider e2e suite',
    'settings:aiProvider.runtimeDiagnosticValues.planner': 'Planner',
    'settings:aiProvider.runtimeDiagnosticValues.recorded': 'Recorded',
    'settings:aiProvider.runtimeDiagnosticValues.textCompletion': 'Text completion',
    'settings:aiProvider.runtimeDiagnosticValues.unsupportedTools': 'Unsupported tools',
    'settings:aiProvider.runtimeDiagnosticValues.unsupportedToolsProbe': 'Unsupported tools probe',
    'settings:aiProvider.runtimeDiagnosticValues.yes': 'Yes',
  })[key] ?? key;

describe('buildProviderResumePolicyDiagnosticRows', () => {
  it('includes resume gates and iteration metadata from provider diagnostics', () => {
    expect(
      buildProviderResumePolicyDiagnosticRows(translate, {
        status: 'ready',
        strategy: 'recover_partial_failure',
        canResume: true,
        finishBlocked: true,
        nextIteration: 4,
        requiredResolutionActionKinds: ['inspect_diff'],
        requiredArtifacts: ['trace_artifact'],
        unresolvedPartialFailureIds: ['json_actions-1'],
        unresolvedTransactionGroupIds: ['transaction-group-1'],
        openTransactionBatchIds: ['batch-1'],
      })
    ).toEqual([
      { labelKey: 'settings:aiProvider.connectionTest.resumePolicy', value: 'Ready' },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeStrategy',
        value: 'Recover partial failure',
      },
      { labelKey: 'settings:aiProvider.connectionTest.resumeCanResume', value: 'Yes' },
      { labelKey: 'settings:aiProvider.connectionTest.resumeFinishBlocked', value: 'Yes' },
      { labelKey: 'settings:aiProvider.connectionTest.resumeNextIteration', value: '4' },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeRequiredActions',
        value: 'Inspect diff',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeRequiredArtifacts',
        value: 'trace artifact',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeUnresolvedFailures',
        value: 'json actions-1',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeUnresolvedGroups',
        value: 'transaction-group-1',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeOpenBatches',
        value: 'batch-1',
      },
    ]);
  });
});

describe('buildRuntimePolicyDiagnosticRows', () => {
  it('summarizes runtime policy by phase for the selected provider', () => {
    expect(
      buildRuntimePolicyDiagnosticRows(translate, [
        {
          phase: 'planner',
          provider: 'openai',
          required_runtime_mode: 'full_autonomous',
          selected_runtime_mode: 'blocked',
          fallback_allowed: false,
          fallback_modes: [],
          requires_full_autonomous: true,
          requires_cli_runner: true,
          runner_candidates: ['codex_cli'],
          policy: 'must_use_full_runtime',
          reason: 'planner_requires_workspace_tools',
        },
        {
          phase: 'coder',
          provider: 'openai',
          required_runtime_mode: 'generic_edit',
          selected_runtime_mode: 'generic_edit',
          fallback_allowed: true,
          fallback_modes: ['patch_proposal', 'analysis_only'],
          requires_full_autonomous: false,
          requires_cli_runner: false,
          runner_candidates: [],
          policy: 'prefer_generic_edit',
          reason: 'coder_can_use_generic_edit_transactions',
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimePolicy',
        value: (
          'Planner: Blocked (Must use full runtime, Codex CLI); '
          + 'Coder: Generic edit (Prefer generic edit)'
        ),
      },
    ]);
  });
});

describe('buildRuntimeEvalDiagnosticRows', () => {
  it('summarizes required runtime eval artifacts', () => {
    expect(
      buildRuntimeEvalDiagnosticRows(translate, [
        {
          case_id: 'provider_e2e',
          runtime_mode: 'provider_e2e',
          required_for_full_autonomous: true,
          providers: ['openai', 'google'],
          required_artifacts: ['provider_e2e_suite', 'provider_reliability'],
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeEval',
        value: 'Provider e2e: Provider e2e (Provider e2e suite, provider reliability)',
      },
    ]);
  });
});

describe('buildProviderReliabilityDiagnosticRows', () => {
  it('includes provider e2e coverage and uncovered cases', () => {
    expect(
      buildProviderReliabilityDiagnosticRows(translate, {
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
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilityStatus',
        value: 'Partial coverage',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilitySuite',
        value: 'Direct API full autonomy',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilityCoverage',
        value: '5/7 passed, 5 observed',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilityUncovered',
        value: 'Unsupported tools, Gateway model limitations',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilityCases',
        value: (
          'Text completion: Passed (Mini pipeline), Unsupported tools: '
          + 'Not covered (Provider e2e required)'
        ),
      },
    ]);
  });
});

describe('buildProviderE2eSuiteDiagnosticRows', () => {
  it('includes provider e2e suite status and child run outcomes', () => {
    expect(
      buildProviderE2eSuiteDiagnosticRows(translate, {
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
          {
            runtimeMode: 'unsupported_tools_probe',
            status: 'passed',
            message: 'unsupported tools classification covered',
          },
          {
            runtimeMode: 'gateway_model_probe',
            status: 'passed',
            message: 'gateway/model classification covered',
          },
        ],
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.providerE2eSuite',
        value: 'Passed',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerE2eRuns',
        value: (
          'Generic edit: Passed - generic_edit passed, '
          + 'Mini pipeline: Failed - mini_pipeline failed - unit_tests_failed'
          + ', Unsupported tools probe: Passed - unsupported tools classification covered'
          + ', Gateway/model probe: Passed - gateway/model classification covered'
        ),
      },
    ]);
  });
});

describe('buildProviderNegativeFixtureDiagnosticRows', () => {
  it('includes provider fixture coverage for negative provider cases', () => {
    expect(
      buildProviderNegativeFixtureDiagnosticRows(translate, {
        status: 'passed',
        provider: 'openai',
        source: 'provider_adapter_negative_fixture',
        coveredCases: ['unsupported_tools', 'gateway_model_limitations'],
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.providerNegativeFixtures',
        value: 'Passed - openai - Provider adapter negative fixture',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerNegativeFixtureCases',
        value: 'Unsupported tools, Gateway model limitations',
      },
    ]);
  });
});

describe('buildProviderRunHistoryDiagnosticRows', () => {
  it('includes persisted provider run history evidence', () => {
    expect(
      buildProviderRunHistoryDiagnosticRows(translate, {
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
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistory',
        value: 'Recorded - openai - Provider e2e',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryRuns',
        value: '3 total, 2 passed, 1 failed',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryLast',
        value: 'Passed, Complete, Passed',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryPath',
        value: '.auto-Codex/provider-smoke-history.json',
      },
    ]);
  });
});

describe('buildProviderTransactionBatchDiagnosticRows', () => {
  it('includes batch-boundary guard and reason metadata from provider diagnostics', () => {
    expect(
      buildProviderTransactionBatchDiagnosticRows(translate, {
        status: 'boundary_guarded',
        batchBoundaryGuard: 'pre_execution_blocked',
        transactionBatchCount: 0,
        openTransactionBatchIds: ['batch-1'],
        boundaryErrorCount: 1,
        boundaryErrorReasons: ['batch_boundary_violation'],
        boundaryPreferredStrategy: 'abort_batch',
        boundaryRequiredActionKinds: ['abort_batch', 'repair_mutation'],
        boundaryResolutionStrategies: ['abort_batch', 'repair_mutation'],
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.batchContract',
        value: 'Boundary guarded',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchBoundaryGuard',
        value: 'Pre-execution blocked',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchCount',
        value: '0',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchBoundaryErrors',
        value: '1 - Batch boundary violation',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchOpenBatches',
        value: 'batch-1',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchPreferredStrategy',
        value: 'Abort batch',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchRequiredActions',
        value: 'Abort batch, Repair mutation',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchResolutionStrategies',
        value: 'Abort batch, Repair mutation',
      },
    ]);
  });

  it('keeps boundary error counts visible when reasons are unavailable', () => {
    expect(
      buildProviderTransactionBatchDiagnosticRows(translate, {
        status: 'boundary_guarded',
        batchBoundaryGuard: 'pre_execution_blocked',
        transactionBatchCount: 0,
        openTransactionBatchIds: [],
        boundaryErrorCount: 2,
        boundaryErrorReasons: [],
      })
    ).toContainEqual({
      labelKey: 'settings:aiProvider.connectionTest.batchBoundaryErrors',
      value: '2',
    });
  });
});
