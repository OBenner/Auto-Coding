/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest';

import {
  buildProviderE2eSuiteDiagnosticRows,
  buildProviderLiveFaultProbeDiagnosticRows,
  buildProviderNegativeFixtureDiagnosticRows,
  buildProviderReliabilityDiagnosticRows,
  buildProviderResumePolicyDiagnosticRows,
  buildProviderRunHistoryDiagnosticRows,
  buildProviderTransactionBatchDiagnosticRows,
  buildCliRunnerContractDiagnosticRows,
  buildMcpBridgePermissionDiagnosticRows,
  buildMutatingSubagentPolicyDiagnosticRows,
  buildRuntimeComparativeEvalDiagnosticRows,
  buildRuntimeCapabilityDiagnosticRows,
  buildRuntimeEvalHistoryDiagnosticRows,
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
    'settings:aiProvider.connectionTest.batchStagedGuardStatuses': 'Staged guard statuses',
    'settings:aiProvider.connectionTest.batchStagedDriftPaths': 'Staged drift paths',
    'settings:aiProvider.connectionTest.batchStagedIsolation': 'Staged isolation',
    'settings:aiProvider.connectionTest.batchStagedWorkspaceRestore': 'Staged workspace restore',
    'settings:aiProvider.connectionTest.batchStagedBaselinePaths': 'Staged baseline paths',
    'settings:aiProvider.connectionTest.batchLifecycleActions': 'Batch lifecycle actions',
    'settings:aiProvider.connectionTest.batchLifecycleStatuses': 'Batch lifecycle statuses',
    'settings:aiProvider.connectionTest.batchCommittedSnapshots': 'Committed snapshots',
    'settings:aiProvider.connectionTest.batchCommitOperations': 'Commit operations',
    'settings:aiProvider.connectionTest.reliabilityStatus': 'Provider reliability',
    'settings:aiProvider.connectionTest.reliabilitySuite': 'Reliability suite',
    'settings:aiProvider.connectionTest.reliabilityCoverage': 'Reliability coverage',
    'settings:aiProvider.connectionTest.reliabilityUncovered': 'Reliability uncovered',
    'settings:aiProvider.connectionTest.reliabilityCases': 'Reliability cases',
    'settings:aiProvider.connectionTest.providerE2eSuite': 'Provider e2e suite',
    'settings:aiProvider.connectionTest.providerE2eRuns': 'Provider e2e runs',
    'settings:aiProvider.connectionTest.providerNegativeFixtures': 'Provider negative fixtures',
    'settings:aiProvider.connectionTest.providerNegativeFixtureCases': 'Negative fixture cases',
    'settings:aiProvider.connectionTest.providerLiveFaultProbes': 'Provider live fault probes',
    'settings:aiProvider.connectionTest.providerLiveFaultProbeCases': 'Live fault probe cases',
    'settings:aiProvider.connectionTest.providerLiveFaultProbeOutcomes': 'Live fault probe outcomes',
    'settings:aiProvider.connectionTest.providerLiveFaultProbeMissingEnv': 'Missing live fault env',
    'settings:aiProvider.connectionTest.providerLiveFaultProbeRequiredEnv': 'Required live fault env',
    'settings:aiProvider.connectionTest.providerRunHistory': 'Provider run history',
    'settings:aiProvider.connectionTest.providerRunHistoryRuns': 'Provider history runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLast': 'Provider history latest',
    'settings:aiProvider.connectionTest.providerRunHistoryTrend': 'Provider history trend',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendFailed': 'failed',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendFailStreak': 'fail streak',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendPassed': 'passed',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendPassStreak': 'pass streak',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendWindow': 'run window',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbes':
      'Provider history live fault probes',
    'settings:aiProvider.connectionTest.providerRunHistoryPath': 'Provider history artifact',
    'settings:aiProvider.controlPlane.runtimePolicy': 'Runtime policy',
    'settings:aiProvider.controlPlane.runtimeCapability': 'Runtime capability',
    'settings:aiProvider.controlPlane.runtimeComparativeEval': 'Comparative evals',
    'settings:aiProvider.controlPlane.runtimeEval': 'Runtime evals',
    'settings:aiProvider.controlPlane.runtimeEvalHistory': 'Runtime eval history',
    'settings:aiProvider.controlPlane.cliRunnerContracts': 'CLI runner contracts',
    'settings:aiProvider.controlPlane.mcpPermissions': 'MCP permissions',
    'settings:aiProvider.controlPlane.mutatingSubagentPolicy': 'Mutating subagent policy',
    'settings:aiProvider.runtimeDiagnosticValues.abortBatch': 'Abort batch',
    'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryGuarded': 'Boundary guarded',
    'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryViolation': 'Batch boundary violation',
    'settings:aiProvider.runtimeDiagnosticValues.beginBatch': 'Begin batch',
    'settings:aiProvider.runtimeDiagnosticValues.blocked': 'Blocked',
    'settings:aiProvider.runtimeDiagnosticValues.callCustomMcp': 'Call custom MCP',
    'settings:aiProvider.runtimeDiagnosticValues.coder': 'Coder',
    'settings:aiProvider.runtimeDiagnosticValues.commitBatch': 'Commit batch',
    'settings:aiProvider.runtimeDiagnosticValues.complete': 'Complete',
    'settings:aiProvider.runtimeDiagnosticValues.configurationBlocked': 'Configuration blocked',
    'settings:aiProvider.runtimeDiagnosticValues.denyBeforeExecution': 'Deny before execution',
    'settings:aiProvider.runtimeDiagnosticValues.directApiFullAutonomy': 'Direct API full autonomy',
    'settings:aiProvider.runtimeDiagnosticValues.directFullAutonomousBlocked':
      'Direct full autonomous blocked',
    'settings:aiProvider.runtimeDiagnosticValues.drifted': 'Drifted',
    'settings:aiProvider.runtimeDiagnosticValues.dynamicAutoClaudeToolPolicy':
      'Dynamic Auto Code tool policy',
    'settings:aiProvider.runtimeDiagnosticValues.dynamicMutatingToolPolicy':
      'Dynamic mutating tool policy',
    'settings:aiProvider.runtimeDiagnosticValues.enforced': 'Enforced',
    'settings:aiProvider.runtimeDiagnosticValues.failed': 'Failed',
    'settings:aiProvider.runtimeDiagnosticValues.inspectDiff': 'Inspect diff',
    'settings:aiProvider.runtimeDiagnosticValues.isolated': 'Isolated',
    'settings:aiProvider.runtimeDiagnosticValues.notCovered': 'Not covered',
    'settings:aiProvider.runtimeDiagnosticValues.litellm': 'LiteLLM',
    'settings:aiProvider.runtimeDiagnosticValues.openrouter': 'OpenRouter',
    'settings:aiProvider.runtimeDiagnosticValues.planned': 'Planned',
    'settings:aiProvider.runtimeDiagnosticValues.mutatingSubagentsRequireTransactionalMerge':
      'Mutating subagents require transactional merge',
    'settings:aiProvider.runtimeDiagnosticValues.partial': 'Partial',
    'settings:aiProvider.runtimeDiagnosticValues.partialCoverage': 'Partial coverage',
    'settings:aiProvider.runtimeDiagnosticValues.preExecutionBlocked': 'Pre-execution blocked',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eRequired': 'Provider e2e required',
    'settings:aiProvider.runtimeDiagnosticValues.ready': 'Ready',
    'settings:aiProvider.runtimeDiagnosticValues.repairMutation': 'Repair mutation',
    'settings:aiProvider.runtimeDiagnosticValues.recoverPartialFailure': 'Recover partial failure',
    'settings:aiProvider.runtimeDiagnosticValues.restored': 'Restored',
    'settings:aiProvider.runtimeDiagnosticValues.gatewayModelLimitations': 'Gateway model limitations',
    'settings:aiProvider.runtimeDiagnosticValues.gatewayModelProbe': 'Gateway/model probe',
    'settings:aiProvider.runtimeDiagnosticValues.genericEdit': 'Generic edit',
    'settings:aiProvider.runtimeDiagnosticValues.liveProviderE2eRequired':
      'Live provider e2e required',
    'settings:aiProvider.runtimeDiagnosticValues.localModelQualityVaries':
      'Local model quality varies',
    'settings:aiProvider.runtimeDiagnosticValues.limited': 'Limited',
    'settings:aiProvider.runtimeDiagnosticValues.missingFullAutonomousRuntime':
      'Missing full autonomous runtime',
    'settings:aiProvider.runtimeDiagnosticValues.openai': 'OpenAI',
    'settings:aiProvider.runtimeDiagnosticValues.openBatch': 'Open batch',
    'settings:aiProvider.runtimeDiagnosticValues.miniPipeline': 'Mini pipeline',
    'settings:aiProvider.runtimeDiagnosticValues.passed': 'Passed',
    'settings:aiProvider.runtimeDiagnosticValues.permissionAllowlistCheck':
      'Permission allowlist check',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2e': 'Provider e2e',
    'settings:aiProvider.runtimeDiagnosticValues.policyGated': 'Policy gated',
    'settings:aiProvider.runtimeDiagnosticValues.notRecorded': 'Not recorded',
    'settings:aiProvider.runtimeDiagnosticValues.notObserved': 'Not observed',
    'settings:aiProvider.runtimeDiagnosticValues.notRestored': 'Not restored',
    'settings:aiProvider.runtimeDiagnosticValues.nativeRuntimePolicy': 'Native runtime policy',
    'settings:aiProvider.runtimeDiagnosticValues.mcpBridgeContract': 'MCP bridge contract',
    'settings:aiProvider.runtimeDiagnosticValues.genericEditRecovery': 'Generic edit recovery',
    'settings:aiProvider.runtimeDiagnosticValues.providerAdapterNegativeFixture':
      'Provider adapter negative fixture',
    'settings:aiProvider.runtimeDiagnosticValues.providerLiveFaultFixture':
      'Provider live fault fixture',
    'settings:aiProvider.runtimeDiagnosticValues.codexCli': 'Codex CLI',
    'settings:aiProvider.runtimeDiagnosticValues.mustUseFullRuntime': 'Must use full runtime',
    'settings:aiProvider.runtimeDiagnosticValues.preferGenericEdit': 'Prefer generic edit',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eSuite': 'Provider e2e suite',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryStable': 'Stable history',
    'settings:aiProvider.runtimeDiagnosticValues.planner': 'Planner',
    'settings:aiProvider.runtimeDiagnosticValues.recorded': 'Recorded',
    'settings:aiProvider.runtimeDiagnosticValues.skipped': 'Skipped',
    'settings:aiProvider.runtimeDiagnosticValues.stagedBatchDrift': 'Staged batch drift',
    'settings:aiProvider.runtimeDiagnosticValues.textCompletion': 'Text completion',
    'settings:aiProvider.runtimeDiagnosticValues.transactionBatches': 'Transaction batches',
    'settings:aiProvider.runtimeDiagnosticValues.transactionBatchProbe':
      'Transaction batch probe',
    'settings:aiProvider.runtimeDiagnosticValues.transactionalRecoveryRequired':
      'Transactional recovery required',
    'settings:aiProvider.runtimeDiagnosticValues.toolPolicyMetadata': 'Tool policy metadata',
    'settings:aiProvider.runtimeDiagnosticValues.mutatingToolClassification':
      'Mutating tool classification',
    'settings:aiProvider.runtimeDiagnosticValues.unsupportedTools': 'Unsupported tools',
    'settings:aiProvider.runtimeDiagnosticValues.unsupportedToolsProbe': 'Unsupported tools probe',
    'settings:aiProvider.runtimeDiagnosticValues.no': 'No',
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

describe('buildRuntimeCapabilityDiagnosticRows', () => {
  it('summarizes selected provider readiness blockers and warnings', () => {
    expect(
      buildRuntimeCapabilityDiagnosticRows(translate, [
        {
          provider: 'openai',
          readiness: 'limited',
          full_autonomous_ready: false,
          direct_full_autonomous: 'no',
          recommended_runtime_mode: 'generic_edit',
          generic_edit: 'experimental',
          analysis_only: 'yes',
          patch_proposal: 'limited',
          mcp_tools: 'local_bridge',
          subagents: 'orchestrated',
          cli_runner_candidates: ['codex_cli'],
          blockers: [
            'missing_full_autonomous_runtime',
            'live_provider_e2e_required',
            'transactional_recovery_required',
          ],
          warnings: ['direct_full_autonomous_blocked'],
          notes: 'Direct SDK sessions use native tools when available.',
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeCapability',
        value: (
          'OpenAI: Limited -> Generic edit '
          + '(Missing full autonomous runtime, Live provider e2e required, '
          + 'Transactional recovery required; Direct full autonomous blocked; Codex CLI)'
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

describe('buildRuntimeEvalHistoryDiagnosticRows', () => {
  it('summarizes persisted runtime eval history', () => {
    expect(
      buildRuntimeEvalHistoryDiagnosticRows(translate, [
        {
          case_id: 'provider_e2e',
          runtime_mode: 'provider_e2e',
          history_path: '.auto-Codex/provider-smoke-history.json',
          status: 'partial',
          total_runs: 3,
          passed_runs: 2,
          failed_runs: 1,
          missing_providers: ['openrouter', 'litellm'],
          providers: [],
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeEvalHistory',
        value: (
          'Provider e2e: Partial (3 total, 2 passed, 1 failed; '
          + 'missing OpenRouter, LiteLLM; .auto-Codex/provider-smoke-history.json)'
        ),
      },
    ]);
  });
});

describe('buildRuntimeComparativeEvalDiagnosticRows', () => {
  it('summarizes quality cost and safety signals', () => {
    expect(
      buildRuntimeComparativeEvalDiagnosticRows(translate, [
        {
          provider: 'openai',
          runtime_path: 'generic_edit',
          quality_status: 'passed',
          cost_status: 'not_recorded',
          safety_status: 'policy_gated',
          evidence_source: '.auto-Codex/provider-smoke-history.json',
          required_before_full_autonomous: true,
          blockers: ['provider_e2e', 'generic_edit_recovery', 'mcp_bridge_contract'],
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeComparativeEval',
        value: (
          'OpenAI: Passed / Not recorded / Policy gated '
          + '(Provider e2e, Generic edit recovery, MCP bridge contract)'
        ),
      },
    ]);
  });
});

describe('buildCliRunnerContractDiagnosticRows', () => {
  it('summarizes CLI runner contract readiness', () => {
    expect(
      buildCliRunnerContractDiagnosticRows(translate, [
        {
          runner_id: 'codex_cli',
          display_name: 'Codex CLI',
          runner_status: 'wired',
          contract_status: 'ready',
          required_facets: ['run', 'cancel'],
          missing_contract_facets: [],
          facets: { run: 'wired', cancel: 'wired' },
          adapter_required: false,
          supported_runtime_modes: ['full_autonomous'],
          artifact_contract: 'codex_cli_result.json, codex_cli_timeline.json',
        },
        {
          runner_id: 'opencode',
          display_name: 'OpenCode',
          runner_status: 'planned',
          contract_status: 'partial',
          required_facets: ['run', 'cancel', 'resume'],
          missing_contract_facets: ['resume'],
          facets: {
            run: 'generic_core_configurable',
            cancel: 'generic_core_configurable',
            resume: 'missing_runner_resume',
          },
          adapter_required: true,
          supported_runtime_modes: ['generic_edit'],
          artifact_contract: 'opencode_result.json, opencode_timeline.json',
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.cliRunnerContracts',
        value: 'Codex CLI: Ready; OpenCode: Partial (resume)',
      },
    ]);
  });
});

describe('buildMutatingSubagentPolicyDiagnosticRows', () => {
  it('summarizes mutating subagent gates for the selected runtime', () => {
    expect(
      buildMutatingSubagentPolicyDiagnosticRows(translate, [
        {
          provider: 'openai',
          runtime_mode: 'generic_edit',
          mutating_subagents_enabled: false,
          status: 'blocked',
          transaction_boundary_required: true,
          parent_approval_required: true,
          merge_protocol: 'read_only_until_transactional_merge',
          required_gates: ['isolated_child_contexts', 'transaction_boundaries'],
          satisfied_gates: ['isolated_child_contexts'],
          missing_gates: ['transaction_boundaries'],
          reason: 'mutating_subagents_require_transactional_merge',
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.mutatingSubagentPolicy',
        value: (
          'Generic edit: Blocked (transaction boundaries; '
          + 'Mutating subagents require transactional merge)'
        ),
      },
    ]);
  });
});

describe('buildMcpBridgePermissionDiagnosticRows', () => {
  it('summarizes permission enforcement and missing gates', () => {
    expect(
      buildMcpBridgePermissionDiagnosticRows(translate, [
        {
          server: 'auto-claude',
          display_name: 'Auto Code local tools',
          bridge_path: 'local_bridge',
          status: 'enforced',
          permission_enforced: true,
          strict_allowlist_configured: false,
          allowlist_source: 'allow_all_default',
          audit_required: true,
          audit_artifact: '.auto-Codex/specs/<spec>/artifacts/mcp_bridge_audit.jsonl',
          tool_count: null,
          tool_policy_coverage: 'dynamic',
          permissions: ['dynamic_auto_claude_tool_policy'],
          mutating_permissions: ['dynamic_mutating_tool_policy'],
          required_gates: ['tool_policy_metadata'],
          satisfied_gates: ['tool_policy_metadata'],
          missing_gates: [],
          reason: 'local_tools_receive_runtime_policy_before_execution',
        },
        {
          server: 'linear',
          display_name: 'Linear',
          bridge_path: 'external_bridge',
          status: 'partial',
          permission_enforced: true,
          strict_allowlist_configured: true,
          allowlist_source: 'AUTO_CODE_MCP_ALLOWED_PERMISSIONS',
          allowed_permissions: ['read_linear'],
          audit_required: false,
          audit_artifact: '.auto-Codex/specs/<spec>/artifacts/mcp_bridge_audit.jsonl',
          tool_count: 2,
          tool_policy_coverage: 'static',
          permissions: ['read_linear', 'write_linear'],
          mutating_permissions: ['write_linear'],
          required_gates: ['audit_artifact'],
          satisfied_gates: [],
          missing_gates: ['audit_artifact'],
          reason: 'external_tools_receive_runtime_policy_before_execution',
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.mcpPermissions',
        value: (
          'Auto Code local tools: Enforced (Dynamic Auto Code tool policy; '
          + 'mutating Dynamic mutating tool policy; strict No); '
          + 'Linear: Partial (read linear, write linear; mutating write linear; '
          + 'strict Yes; missing audit artifact)'
        ),
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
        requiredCaseCount: 8,
        uncoveredCases: [
          'transaction_batches',
          'unsupported_tools',
          'gateway_model_limitations',
        ],
        cases: [
          {
            case: 'text_completion',
            status: 'passed',
            source: 'mini_pipeline',
          },
          {
            case: 'transaction_batches',
            status: 'not_covered',
            source: 'provider_e2e_required',
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
        value: '5/8 passed, 5 observed',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilityUncovered',
        value: 'Transaction batches, Unsupported tools, Gateway model limitations',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.reliabilityCases',
        value: (
          'Text completion: Passed (Mini pipeline), Transaction batches: '
          + 'Not covered (Provider e2e required), Unsupported tools: '
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
            runtimeMode: 'transaction_batch_probe',
            status: 'passed',
            message: 'transaction batch probe passed',
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
          + ', Transaction batch probe: Passed - transaction batch probe passed'
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

describe('buildProviderLiveFaultProbeDiagnosticRows', () => {
  it('includes live fault opt-in probe status and env evidence', () => {
    expect(
      buildProviderLiveFaultProbeDiagnosticRows(translate, {
        status: 'configuration_blocked',
        provider: 'openai',
        source: 'provider_live_fault_fixture',
        enabled: true,
        coveredCases: ['unsupported_tools'],
        requiredEnv: [
          'AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES',
          'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR',
        ],
        missingEnv: ['AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR'],
        probes: [
          {
            case: 'unsupported_tools',
            status: 'passed',
            reason: 'unsupported_tools',
            envName: 'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR',
          },
          {
            case: 'gateway_model_limitations',
            status: 'skipped',
            reason: 'missing_live_fault_fixture',
          },
        ],
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbes',
        value: 'Configuration blocked - openai - Provider live fault fixture',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeCases',
        value: 'Unsupported tools',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeMissingEnv',
        value: 'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeRequiredEnv',
        value: 'AUTO_CODE_PROVIDER_E2E_LIVE_FAULT_PROBES, AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_GATEWAY_MODEL_ERROR',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeOutcomes',
        value: 'Unsupported tools: Passed (Unsupported tools - AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_UNSUPPORTED_TOOLS_ERROR)',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeOutcomes',
        value: 'Gateway model limitations: Skipped (missing live fault fixture)',
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
        lastLiveFaultProbeStatus: 'passed',
        liveFaultProbeEnabledRuns: 2,
        liveFaultProbePassedRuns: 2,
        liveFaultProbeCoveredCases: ['gateway_model_limitations', 'unsupported_tools'],
        trend: 'provider_history_stable',
        trendReason: 'recent_runs_all_passed',
        recentWindow: 3,
        recentPassedRuns: 3,
        recentFailedRuns: 0,
        consecutivePasses: 3,
        consecutiveFailures: 0,
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
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryTrend',
        value: 'Stable history - 3 run window, 3 passed, 0 failed, 3 pass streak',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbes',
        value: 'Passed - 2 enabled, 2 passed - Gateway model limitations, Unsupported tools',
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
        stagedWorkspaceGuardStatuses: ['drifted'],
        stagedDriftPaths: ['batched.txt'],
        stagedIsolationStatuses: ['isolated'],
        stagedWorkspaceRestoreStatuses: ['restored'],
        stagedBaselinePaths: ['batched.txt'],
        batchLifecycleActions: ['begin_batch', 'commit_batch'],
        batchLifecycleStatuses: ['open', 'blocked'],
        committedMutationSnapshotIds: ['mutation-1'],
        commitOperationIds: ['batch-1:commit'],
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
      {
        labelKey: 'settings:aiProvider.connectionTest.batchStagedGuardStatuses',
        value: 'Drifted',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchStagedDriftPaths',
        value: 'batched.txt',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchStagedIsolation',
        value: 'Isolated',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchStagedWorkspaceRestore',
        value: 'Restored',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchStagedBaselinePaths',
        value: 'batched.txt',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchLifecycleActions',
        value: 'Begin batch, Commit batch',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchLifecycleStatuses',
        value: 'Open batch, Blocked',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchCommittedSnapshots',
        value: 'mutation-1',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchCommitOperations',
        value: 'batch-1:commit',
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
