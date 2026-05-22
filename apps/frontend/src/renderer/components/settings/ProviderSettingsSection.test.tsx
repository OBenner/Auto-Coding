/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest';

import {
  buildProviderAutonomousPromotionGateDiagnosticRows,
  buildProviderAutonomousReadinessDiagnosticRows,
  buildProviderE2eSuiteDiagnosticRows,
  buildProviderLiveFaultProbeDiagnosticRows,
  buildProviderLiveTaskFamilyDiagnosticRows,
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

const translate = (key: string, options?: Record<string, unknown>) => {
  const value =
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
    'settings:aiProvider.connectionTest.providerLiveTaskFamilies': 'Provider live task families',
    'settings:aiProvider.connectionTest.providerLiveTaskFamilyCovered': 'Covered live task families',
    'settings:aiProvider.connectionTest.providerLiveTaskFamilyFailed': 'Failed live task families',
    'settings:aiProvider.connectionTest.providerLiveTaskFamilyOutcomes': 'Live task family outcomes',
    'settings:aiProvider.connectionTest.providerLiveTaskFamilyMissingEnv': 'Missing live task env',
    'settings:aiProvider.connectionTest.providerLiveTaskFamilyRequiredEnv': 'Required live task env',
    'settings:aiProvider.connectionTest.providerRunHistory': 'Provider run history',
    'settings:aiProvider.connectionTest.providerRunHistoryRuns': 'Provider history runs',
    'settings:aiProvider.connectionTest.providerRunHistoryTotalRuns': 'total',
    'settings:aiProvider.connectionTest.providerRunHistoryPassedRuns': 'passed',
    'settings:aiProvider.connectionTest.providerRunHistoryFailedRuns': 'failed',
    'settings:aiProvider.connectionTest.providerRunHistoryTotalRunsValue':
      '{{count}} total',
    'settings:aiProvider.connectionTest.providerRunHistoryPassedRunsValue':
      '{{count}} passed',
    'settings:aiProvider.connectionTest.providerRunHistoryFailedRunsValue':
      '{{count}} failed',
    'settings:aiProvider.connectionTest.providerRunHistoryLast': 'Provider history latest',
    'settings:aiProvider.connectionTest.providerRunHistoryTrend': 'Provider history trend',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendFailed': 'failed',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendFailStreak': 'fail streak',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendPassed': 'passed',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendPassStreak': 'pass streak',
    'settings:aiProvider.connectionTest.providerRunHistoryTrendWindow': 'run window',
    'settings:aiProvider.connectionTest.providerRunHistoryRecentRuns':
      'Provider history recent runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbes':
      'Provider history live fault probes',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbeEnabled':
      'enabled runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbePassed':
      'passed runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveTaskFamilies':
      'Provider history live task families',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveTaskFamilyEnabled':
      'enabled runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveTaskFamilyPassed':
      'passed runs',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveTaskFamilyFailed':
      'failed families',
    'settings:aiProvider.connectionTest.providerRunHistoryPassRate': 'pass rate',
    'settings:aiProvider.connectionTest.providerRunHistoryRecentPassRate':
      'recent pass rate',
    'settings:aiProvider.connectionTest.providerRunHistoryE2eCasePassRate':
      'e2e case pass rate',
    'settings:aiProvider.connectionTest.providerRunHistoryReliabilityCasePassRate':
      'reliability case pass rate',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultCoverage':
      'live-fault coverage',
    'settings:aiProvider.connectionTest.providerRunHistoryLiveTaskFamilyCoverage':
      'live-task coverage',
    'settings:aiProvider.connectionTest.providerRunHistoryPath': 'Provider history artifact',
    'settings:aiProvider.connectionTest.providerAutonomousReadiness':
      'Provider autonomous readiness',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessRecommendation':
      'Autonomous recommendation',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessRecommendationReasons':
      'Autonomous recommendation reasons',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessBlockers':
      'Autonomous blockers',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessWarnings':
      'Autonomous warnings',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessMissingRequirements':
      'Autonomous missing requirements',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessRequirements':
      'Autonomous requirements',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessConsecutivePasses':
      'Consecutive passes',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessLastRun':
      'last run',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessMaxAge':
      'max age',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessMissingCases':
      'missing',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessEvidence':
      'Autonomous evidence',
    'settings:aiProvider.connectionTest.providerAutonomousReadinessNextActions':
      'Autonomous next actions',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionGate':
      'Autonomous promotion gate',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionReliabilityCases':
      'Promotion reliability cases',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionE2eRuns':
      'Promotion e2e runs',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionReadiness':
      'Promotion readiness',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionMissingRequirements':
      'Promotion missing requirements',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionPassed':
      'passed',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionObserved':
      'observed',
    'settings:aiProvider.connectionTest.providerAutonomousPromotionMissing':
      'missing',
    'settings:aiProvider.controlPlane.runtimePolicy': 'Runtime policy',
    'settings:aiProvider.controlPlane.runtimeCapability': 'Runtime capability',
    'settings:aiProvider.controlPlane.runtimeComparativeEval': 'Comparative evals',
    'settings:aiProvider.controlPlane.runtimeEval': 'Runtime evals',
    'settings:aiProvider.controlPlane.runtimeEvalHistory': 'Runtime eval history',
    'settings:aiProvider.controlPlane.scoreSource': 'source',
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
    'settings:aiProvider.runtimeDiagnosticValues.costDecreasing': 'Decreasing',
    'settings:aiProvider.runtimeDiagnosticValues.costIncreasing': 'Increasing',
    'settings:aiProvider.runtimeDiagnosticValues.costInsufficientData':
      'Insufficient data',
    'settings:aiProvider.runtimeDiagnosticValues.costStable': 'Stable',
    'settings:aiProvider.runtimeDiagnosticValues.costTrend': 'Cost trend',
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
    'settings:aiProvider.runtimeDiagnosticValues.estimated': 'Estimated',
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
    'settings:aiProvider.runtimeDiagnosticValues.apiRuntimeFullAutonomousCandidate':
      'API runtime full autonomous candidate',
    'settings:aiProvider.runtimeDiagnosticValues.collectProviderHistoryRuns':
      'Collect provider history runs',
    'settings:aiProvider.runtimeDiagnosticValues.enableLiveFaultProbes':
      'Enable live fault probes',
    'settings:aiProvider.runtimeDiagnosticValues.fullAutonomousCandidate':
      'Full autonomous candidate',
    'settings:aiProvider.runtimeDiagnosticValues.limitedAutonomousUntilLiveFaults':
      'Limited autonomous until live faults',
    'settings:aiProvider.runtimeDiagnosticValues.limitedAutonomousUntilEvidenceStable':
      'Limited autonomous until evidence stable',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultProbeEvidenceMissing':
      'Live fault probe evidence missing',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultProbeMissing':
      'Live fault probe missing',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultProbeCoverageIncomplete':
      'Live fault probe coverage incomplete',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultCaseCoverage':
      'Live fault case coverage',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultCoverageIncomplete':
      'Live fault coverage incomplete',
    'settings:aiProvider.runtimeDiagnosticValues.liveTaskFamilyCoverage':
      'Live task family coverage',
    'settings:aiProvider.runtimeDiagnosticValues.liveTaskFamilyCoverageIncomplete':
      'Live task family coverage incomplete',
    'settings:aiProvider.runtimeDiagnosticValues.liveTaskFamilyEvidenceMissing':
      'Live task family evidence missing',
    'settings:aiProvider.runtimeDiagnosticValues.liveTaskFamilyMissing':
      'Live task family missing',
    'settings:aiProvider.runtimeDiagnosticValues.liveTaskFamiliesPassed':
      'Live task families passed',
    'settings:aiProvider.runtimeDiagnosticValues.providerLiveTaskFixture':
      'Provider live task fixture',
    'settings:aiProvider.runtimeDiagnosticValues.singleFileEdit':
      'Single file edit',
    'settings:aiProvider.runtimeDiagnosticValues.multiStepEdit':
      'Multi-step edit',
    'settings:aiProvider.runtimeDiagnosticValues.recoveryResume':
      'Recovery/resume',
    'settings:aiProvider.runtimeDiagnosticValues.transactionBatching':
      'Transaction batching',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultProbeCaseCoverage':
      'Live fault probe case coverage',
    'settings:aiProvider.runtimeDiagnosticValues.liveFaultProbesPassed':
      'Live fault probes passed',
    'settings:aiProvider.runtimeDiagnosticValues.latestProviderE2ePass':
      'Latest provider e2e pass',
    'settings:aiProvider.runtimeDiagnosticValues.latestProviderE2eFailed':
      'Latest provider e2e failed',
    'settings:aiProvider.runtimeDiagnosticValues.latestProviderSmokeFailed':
      'Latest provider smoke failed',
    'settings:aiProvider.runtimeDiagnosticValues.latestProviderSmokePass':
      'Latest provider smoke pass',
    'settings:aiProvider.runtimeDiagnosticValues.historyMissing':
      'Missing provider history',
    'settings:aiProvider.runtimeDiagnosticValues.historyDegraded': 'Degraded history',
    'settings:aiProvider.runtimeDiagnosticValues.historyFlaky': 'Flaky history',
    'settings:aiProvider.runtimeDiagnosticValues.historyFreshnessUnknown':
      'History freshness unknown',
    'settings:aiProvider.runtimeDiagnosticValues.historyInsufficientRuns':
      'Insufficient stable history',
    'settings:aiProvider.runtimeDiagnosticValues.historyRecovering':
      'Recovering history',
    'settings:aiProvider.runtimeDiagnosticValues.historyStale': 'Stale history',
    'settings:aiProvider.runtimeDiagnosticValues.historyWarmingUp':
      'Warming up history',
    'settings:aiProvider.runtimeDiagnosticValues.freshProviderHistory':
      'Fresh provider history',
    'settings:aiProvider.runtimeDiagnosticValues.needsLiveFaultEvidence':
      'Needs live fault evidence',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eFailed': 'Provider e2e failed',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2ePassed': 'Provider e2e passed',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eCasePassRate':
      'Provider e2e case pass rate',
    'settings:aiProvider.runtimeDiagnosticValues.providerE2eAndLiveTaskCoverage':
      'Provider e2e and live-task coverage',
    'settings:aiProvider.runtimeDiagnosticValues.providerAutonomousPromotionBlocked':
      'Promotion blocked',
    'settings:aiProvider.runtimeDiagnosticValues.providerAutonomousPromotionPassed':
      'Promotion passed',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryLatestFailed':
      'Provider history latest failed',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryPassRate':
      'Provider history pass rate',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryFreshnessUnknown':
      'Provider history freshness unknown',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryInsufficientRuns':
      'Provider history insufficient runs',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryStale':
      'Stale provider history',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryWarmingUp':
      'Provider history warming up',
    'settings:aiProvider.runtimeDiagnosticValues.providerReliabilityComplete':
      'Provider reliability complete',
    'settings:aiProvider.runtimeDiagnosticValues.providerReliabilityIncomplete':
      'Provider reliability incomplete',
    'settings:aiProvider.runtimeDiagnosticValues.providerReliability':
      'Provider reliability',
    'settings:aiProvider.runtimeDiagnosticValues.providerReliabilityAndLiveFaultCoverage':
      'Provider reliability and live-fault coverage',
    'settings:aiProvider.runtimeDiagnosticValues.providerReliabilityCasePassRate':
      'Provider reliability case pass rate',
    'settings:aiProvider.runtimeDiagnosticValues.warmingUp': 'Warming up',
    'settings:aiProvider.runtimeDiagnosticValues.ready': 'Ready',
    'settings:aiProvider.runtimeDiagnosticValues.repairMutation': 'Repair mutation',
    'settings:aiProvider.runtimeDiagnosticValues.recoverPartialFailure': 'Recover partial failure',
    'settings:aiProvider.runtimeDiagnosticValues.restored': 'Restored',
    'settings:aiProvider.runtimeDiagnosticValues.gatewayModelLimitations': 'Gateway model limitations',
    'settings:aiProvider.runtimeDiagnosticValues.gatewayModelProbe': 'Gateway/model probe',
    'settings:aiProvider.runtimeDiagnosticValues.genericEdit': 'Generic edit',
    'settings:aiProvider.runtimeDiagnosticValues.google': 'Google',
    'settings:aiProvider.runtimeDiagnosticValues.liveProviderE2eRequired':
      'Live provider e2e required',
    'settings:aiProvider.runtimeDiagnosticValues.localModelQualityVaries':
      'Local model quality varies',
    'settings:aiProvider.runtimeDiagnosticValues.localZeroCost': 'Local zero cost',
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
    'settings:aiProvider.runtimeDiagnosticValues.qualityScore': 'Quality',
    'settings:aiProvider.runtimeDiagnosticValues.qualityTrend': 'Quality trend',
    'settings:aiProvider.runtimeDiagnosticValues.qualityTrendDegrading':
      'Quality trend degrading',
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryUnknown':
      'Unknown provider history',
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
    'settings:aiProvider.runtimeDiagnosticValues.stableHistoryRuns':
      'Stable history runs',
    'settings:aiProvider.runtimeDiagnosticValues.planner': 'Planner',
    'settings:aiProvider.runtimeDiagnosticValues.recorded': 'Recorded',
    'settings:aiProvider.runtimeDiagnosticValues.safetyScore': 'Safety',
    'settings:aiProvider.runtimeDiagnosticValues.safetyTrend': 'Safety trend',
    'settings:aiProvider.runtimeDiagnosticValues.safetyTrendDegrading':
      'Safety trend degrading',
    'settings:aiProvider.runtimeDiagnosticValues.skipped': 'Skipped',
    'settings:aiProvider.runtimeDiagnosticValues.scoreDegrading': 'Degrading',
    'settings:aiProvider.runtimeDiagnosticValues.scoreImproving': 'Improving',
    'settings:aiProvider.runtimeDiagnosticValues.scoreStable': 'Stable',
    'settings:aiProvider.runtimeDiagnosticValues.stableEvalTrends':
      'Stable eval trends',
    'settings:aiProvider.runtimeDiagnosticValues.stabilityScore': 'Stability',
    'settings:aiProvider.runtimeDiagnosticValues.stabilityTrend': 'Stability trend',
    'settings:aiProvider.runtimeDiagnosticValues.stabilityTrendDegrading':
      'Stability trend degrading',
    'settings:aiProvider.runtimeDiagnosticValues.stagedBatchDrift': 'Staged batch drift',
    'settings:aiProvider.runtimeDiagnosticValues.textCompletion': 'Text completion',
    'settings:aiProvider.runtimeDiagnosticValues.nativeToolCalls': 'Native tool calls',
    'settings:aiProvider.runtimeDiagnosticValues.transactionBatches': 'Transaction batches',
    'settings:aiProvider.runtimeDiagnosticValues.transactionBatchProbe':
      'Transaction batch probe',
    'settings:aiProvider.runtimeDiagnosticValues.transactionalRecoveryRequired':
      'Transactional recovery required',
    'settings:aiProvider.runtimeDiagnosticValues.trendInsufficientData':
      'Insufficient data',
    'settings:aiProvider.runtimeDiagnosticValues.toolPolicyMetadata': 'Tool policy metadata',
    'settings:aiProvider.runtimeDiagnosticValues.mutatingToolClassification':
      'Mutating tool classification',
    'settings:aiProvider.runtimeDiagnosticValues.unsupportedTools': 'Unsupported tools',
    'settings:aiProvider.runtimeDiagnosticValues.unsupportedToolsProbe': 'Unsupported tools probe',
    'settings:aiProvider.runtimeDiagnosticValues.no': 'No',
    'settings:aiProvider.runtimeDiagnosticValues.yes': 'Yes',
    })[key] ?? key;
  const count = typeof options?.count === 'number' ? String(options.count) : '';
  return value.replace('{{count}}', count);
};

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
          autonomous_readiness_required: true,
          autonomous_policy_gate: 'blocked',
          autonomous_readiness_recommendation:
            'limited_autonomous_until_evidence_stable',
          autonomous_readiness_recommendation_reasons: ['history_stale'],
          autonomous_promotion_gate: 'blocked',
          autonomous_promotion_ready: false,
          autonomous_promotion_missing_reliability_cases: ['native_tool_calls'],
          autonomous_promotion_missing_e2e_runs: ['mini_pipeline'],
          autonomous_readiness_requirements: {
            min_stable_runs: 3,
            observed_recent_window: 2,
            observed_consecutive_passes: 2,
            history_stability_complete: false,
            last_run_at: '2026-05-01T00:00:00Z',
            max_history_age_seconds: 604800,
            history_freshness_complete: false,
            live_fault_missing_cases: ['gateway_model_limitations'],
            live_fault_coverage_complete: false,
            live_task_missing_families: ['single_file_edit'],
            live_task_family_coverage_complete: false,
          },
          autonomous_readiness_missing_requirements: [
            'fresh_provider_history',
            'live_task_family_coverage',
          ],
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
          'Planner: Blocked (Must use full runtime, Blocked, '
          + 'Limited autonomous until evidence stable, Stale history, '
          + 'Promotion blocked, Native tool calls, Mini pipeline, '
          + 'Fresh provider history, Live task family coverage, Stable history runs 2/3, '
          + 'Consecutive passes 2/3, Fresh provider history: No '
          + '(last run 2026-05-01T00:00:00Z, max age 604800s), '
          + 'Live fault case coverage: No (missing Gateway model limitations), '
          + 'Live task family coverage: No (missing Single file edit), '
          + 'Codex CLI); '
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

  it('includes autonomous readiness gate status and recommendation', () => {
    expect(
      buildRuntimeCapabilityDiagnosticRows(translate, [
        {
          provider: 'google',
          readiness: 'needs_live_fault_evidence',
          full_autonomous_ready: false,
          direct_full_autonomous: 'no',
          recommended_runtime_mode: 'generic_edit',
          generic_edit: 'experimental',
          analysis_only: 'yes',
          patch_proposal: 'limited',
          mcp_tools: 'local_bridge',
          subagents: 'orchestrated',
          cli_runner_candidates: ['codex_cli'],
          autonomous_readiness_required: true,
          autonomous_policy_gate: 'blocked',
          autonomous_readiness_status: 'needs_live_fault_evidence',
          autonomous_readiness_recommendation: 'limited_autonomous_until_live_faults',
          autonomous_readiness_recommendation_reasons: [
            'history_warming_up',
            'live_fault_probe_missing',
            'live_task_family_missing',
          ],
          autonomous_readiness_blockers: [],
          autonomous_readiness_warnings: [
            'provider_history_warming_up',
            'live_fault_probe_evidence_missing',
            'live_task_family_evidence_missing',
          ],
          autonomous_readiness_evidence: [
            'provider_e2e_passed',
            'provider_reliability_complete',
          ],
          autonomous_promotion_gate: 'blocked',
          autonomous_promotion_ready: false,
          autonomous_promotion_missing_reliability_cases: ['native_tool_calls'],
          autonomous_promotion_missing_e2e_runs: ['mini_pipeline'],
          autonomous_readiness_requirements: {
            min_stable_runs: 3,
            observed_recent_window: 2,
            observed_consecutive_passes: 2,
            history_stability_complete: false,
            last_run_at: '2026-05-01T00:00:00Z',
            max_history_age_seconds: 604800,
            history_freshness_complete: false,
            live_fault_missing_cases: ['gateway_model_limitations'],
            live_fault_coverage_complete: false,
            live_task_missing_families: ['single_file_edit'],
            live_task_family_coverage_complete: false,
          },
          autonomous_readiness_missing_requirements: [
            'fresh_provider_history',
            'live_task_family_coverage',
          ],
          blockers: [],
          warnings: [
            'provider_history_warming_up',
            'live_fault_probe_evidence_missing',
            'live_task_family_evidence_missing',
          ],
          notes: 'Gemini can use local actions with Gemini-compatible tool schemas.',
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeCapability',
        value: (
          'Google: Needs live fault evidence -> Generic edit '
          + '(Blocked, Limited autonomous until live faults, '
          + 'Warming up history, Live fault probe missing, '
          + 'Live task family missing, '
          + 'Promotion blocked, Native tool calls, Mini pipeline; '
          + 'Provider history warming up, Live fault probe evidence missing, '
          + 'Live task family evidence missing; '
          + 'Fresh provider history, Live task family coverage; Stable history runs 2/3, '
          + 'Consecutive passes 2/3, Fresh provider history: No '
          + '(last run 2026-05-01T00:00:00Z, max age 604800s), '
          + 'Live fault case coverage: No (missing Gateway model limitations), '
          + 'Live task family coverage: No (missing Single file edit); '
          + 'Codex CLI)'
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
        value: 'Provider e2e: Provider e2e (Provider e2e suite, Provider reliability)',
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
          providers: [
            {
              provider: 'openai',
              status: 'passed',
              total_runs: 2,
              passed_runs: 2,
              failed_runs: 0,
              e2e_case_count: 7,
              e2e_passed_case_count: 7,
              e2e_failed_case_count: 0,
              e2e_case_pass_rate_percent: 100,
              reliability_observed_case_count: 8,
              reliability_passed_case_count: 7,
              reliability_required_case_count: 8,
              reliability_case_pass_rate_percent: 88,
              observed_live_fault_case_count: 2,
              required_live_fault_case_count: 2,
              live_fault_probe_case_coverage_percent: 100,
              observed_live_task_family_count: 4,
              required_live_task_family_count: 4,
              live_task_family_coverage_percent: 100,
            },
          ],
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeEvalHistory',
        value: (
          'Provider e2e: Partial (3 total, 2 passed, 1 failed; '
          + 'OpenAI: Passed (e2e case pass rate 100% (7/7), '
          + 'reliability case pass rate 88% (7/8), live-fault coverage 100% (2/2), '
          + 'live-task coverage 100% (4/4)); '
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
          quality_score: 75,
          quality_score_source: 'provider_e2e_case_pass_rate',
          quality_trend: 'score_improving',
          quality_delta_percent: 25,
          stability_score: 75,
          stability_trend: 'score_stable',
          stability_delta_percent: 0,
          cost_status: 'estimated',
          cost_estimate_usd: 0.045,
          cost_estimate_formatted: '$0.0450',
          cost_pricing_model: 'gpt-4o',
          cost_estimate_input_tokens: 10000,
          cost_estimate_output_tokens: 2000,
          cost_trend: 'cost_increasing',
          cost_delta_formatted: '+$0.0200',
          safety_status: 'policy_gated',
          safety_score: 50,
          safety_score_source: 'provider_reliability_and_live_fault_coverage',
          safety_trend: 'score_degrading',
          safety_delta_percent: -10,
          evidence_source: '.auto-Codex/provider-smoke-history.json',
          required_before_full_autonomous: true,
          blockers: ['provider_e2e', 'generic_edit_recovery', 'mcp_bridge_contract'],
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeComparativeEval',
        value: (
          'OpenAI: Passed / Estimated $0.0450 gpt-4o / Policy gated '
          + '(Quality 75% (source Provider e2e case pass rate), '
          + 'Quality trend Improving (+25pp), Stability 75%, '
          + 'Stability trend Stable (0pp), Safety 50% '
          + '(source Provider reliability and live-fault coverage), '
          + 'Safety trend Degrading (-10pp), Cost trend Increasing (+$0.0200); '
          + 'Provider e2e, Generic edit recovery, MCP bridge contract)'
        ),
      },
    ]);
  });

  it('prefers recorded actual cost over benchmark estimates', () => {
    expect(
      buildRuntimeComparativeEvalDiagnosticRows(translate, [
        {
          provider: 'openai',
          runtime_path: 'generic_edit',
          quality_status: 'passed',
          cost_status: 'recorded',
          cost_actual_usd: 0.0075,
          cost_actual_formatted: '$0.0075',
          cost_actual_input_tokens: 1000,
          cost_actual_output_tokens: 500,
          cost_pricing_model: 'gpt-4o',
          cost_estimate_formatted: '$0.0450',
          safety_status: 'policy_gated',
          evidence_source: '.auto-Codex/provider-smoke-history.json',
          required_before_full_autonomous: true,
          blockers: [],
        },
      ])
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.controlPlane.runtimeComparativeEval',
        value: 'OpenAI: Passed / Recorded $0.0075 gpt-4o / Policy gated',
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

describe('buildProviderLiveTaskFamilyDiagnosticRows', () => {
  it('includes live task family opt-in status and env evidence', () => {
    expect(
      buildProviderLiveTaskFamilyDiagnosticRows(translate, {
        status: 'configuration_blocked',
        provider: 'openai',
        source: 'provider_live_task_fixture',
        enabled: true,
        coveredFamilies: ['single_file_edit'],
        failedFamilies: ['multi_step_edit'],
        requiredEnv: [
          'AUTO_CODE_PROVIDER_E2E_LIVE_TASKS',
          'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_MULTI_STEP_EDIT_STATUS',
        ],
        missingEnv: [
          'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_MULTI_STEP_EDIT_STATUS',
        ],
        families: [
          {
            family: 'single_file_edit',
            status: 'passed',
            reason: 'passed',
            envName: 'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_SINGLE_FILE_EDIT_STATUS',
          },
          {
            family: 'multi_step_edit',
            status: 'skipped',
            reason: 'missing_live_task_fixture',
          },
        ],
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilies',
        value: 'Configuration blocked - openai - Provider live task fixture',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilyCovered',
        value: 'Single file edit',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilyFailed',
        value: 'Multi-step edit',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilyMissingEnv',
        value: 'AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_MULTI_STEP_EDIT_STATUS',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilyRequiredEnv',
        value:
          'AUTO_CODE_PROVIDER_E2E_LIVE_TASKS, AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_MULTI_STEP_EDIT_STATUS',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilyOutcomes',
        value:
          'Single file edit: Passed (Passed - AUTO_CODE_PROVIDER_E2E_LIVE_OPENAI_SINGLE_FILE_EDIT_STATUS)',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerLiveTaskFamilyOutcomes',
        value: 'Multi-step edit: Skipped (missing live task fixture)',
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
        liveFaultProbeCoveredCases: ['gateway_model_limitations', 'unsupported_tools'],
        lastLiveTaskFamilyStatus: 'passed',
        liveTaskFamilyEnabledRuns: 2,
        liveTaskFamilyPassedRuns: 2,
        liveTaskFamilyCoveredFamilies: ['single_file_edit', 'multi_step_edit'],
        liveTaskFamilyFailedFamilies: ['transaction_batching'],
        passRatePercent: 67,
        recentPassRatePercent: 100,
        observedLiveFaultCaseCount: 2,
        requiredLiveFaultCaseCount: 2,
        liveFaultProbeCaseCoveragePercent: 100,
        observedLiveTaskFamilyCount: 2,
        requiredLiveTaskFamilyCount: 4,
        liveTaskFamilyCoveragePercent: 50,
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
            liveTaskFamilyStatus: 'passed',
          },
        ],
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
        value: (
          '3 total, 2 passed, 1 failed, pass rate 67%, recent pass rate 100%, '
          + 'e2e case pass rate 100% (7/7), reliability case pass rate 100% (8/8)'
        ),
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
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryRecentRuns',
        value:
          '2026-05-18T09:00:00Z: Failed / Provider e2e / gpt-4o -> 2026-05-18T09:05:00Z: Passed / Provider e2e / gpt-4o / Complete / Passed / Passed / Passed',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbes',
        value:
          'Passed - 2 enabled runs, 2 passed runs - Gateway model limitations, Unsupported tools - live-fault coverage 100%',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryLiveTaskFamilies',
        value:
          'Passed - 2 enabled runs, 2 passed runs - Single file edit, Multi-step edit - failed families Transaction batching - live-task coverage 50%',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryPath',
        value: '.auto-Codex/provider-smoke-history.json',
      },
    ]);
  });
});

describe('buildProviderAutonomousReadinessDiagnosticRows', () => {
  it('includes provider autonomous readiness recommendation evidence', () => {
    const readiness = {
      status: 'warming_up',
      provider: 'openai',
      source: 'provider_autonomous_readiness',
      recommendation: 'limited_autonomous_until_evidence_stable',
      recommendationReasons: [
        'history_warming_up',
        'history_stale',
        'live_fault_probe_missing',
      ],
      blockers: [],
      warnings: [
        'provider_history_warming_up',
        'provider_history_stale',
        'live_fault_probe_evidence_missing',
      ],
      missingRequirements: [
        'stable_history_runs',
        'fresh_provider_history',
        'live_fault_case_coverage',
      ],
      evidence: ['provider_e2e_passed', 'provider_reliability_complete'],
      nextActions: ['collect_provider_history_runs', 'enable_live_fault_probes'],
      requirements: {
        minStableRuns: 3,
        observedRecentWindow: 2,
        observedConsecutivePasses: 2,
        historyStabilityComplete: false,
        lastRunAt: '2026-05-01T00:00:00Z',
        maxHistoryAgeSeconds: 604800,
        historyFreshnessComplete: false,
        requiredLiveFaultCases: [
          'gateway_model_limitations',
          'unsupported_tools',
        ],
        liveFaultCoveredCases: ['unsupported_tools'],
        liveFaultMissingCases: ['gateway_model_limitations'],
        liveFaultCoverageComplete: false,
      },
    };

    expect(
      buildProviderAutonomousReadinessDiagnosticRows(translate, readiness)
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.providerAutonomousReadiness',
        value: 'Warming up - OpenAI',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousReadinessRecommendation',
        value: 'Limited autonomous until evidence stable',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousReadinessRecommendationReasons',
        value: 'Warming up history, Stale history, Live fault probe missing',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerAutonomousReadinessWarnings',
        value:
          'Provider history warming up, Stale provider history, Live fault probe evidence missing',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousReadinessMissingRequirements',
        value: 'Stable history runs, Fresh provider history, Live fault case coverage',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousReadinessRequirements',
        value:
          'Stable history runs 2/3, Consecutive passes 2/3, Fresh provider history: No (last run 2026-05-01T00:00:00Z, max age 604800s), Live fault case coverage: No (missing Gateway model limitations)',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.providerAutonomousReadinessEvidence',
        value: 'Provider e2e passed, Provider reliability complete',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousReadinessNextActions',
        value: 'Collect provider history runs, Enable live fault probes',
      },
    ]);
  });
});

describe('buildProviderAutonomousPromotionGateDiagnosticRows', () => {
  it('includes provider autonomous promotion gate blockers', () => {
    expect(
      buildProviderAutonomousPromotionGateDiagnosticRows(translate, {
        status: 'blocked',
        provider: 'openai',
        promotionReady: false,
        requiredReliabilityCases: ['text_completion', 'native_tool_calls'],
        passedReliabilityCases: ['text_completion'],
        missingReliabilityCases: ['native_tool_calls'],
        requiredE2eRuns: ['generic_edit', 'mini_pipeline'],
        observedE2eRuns: ['generic_edit'],
        missingE2eRuns: ['mini_pipeline'],
        readinessStatus: 'warming_up',
        readinessMissingRequirements: ['stable_history_runs'],
      })
    ).toEqual([
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousPromotionGate',
        value: 'Blocked - OpenAI - No',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousPromotionReliabilityCases',
        value:
          'Text completion, Native tool calls - passed Text completion - missing Native tool calls',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousPromotionE2eRuns',
        value:
          'Generic edit, Mini pipeline - observed Generic edit - missing Mini pipeline',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousPromotionReadiness',
        value: 'Warming up',
      },
      {
        labelKey:
          'settings:aiProvider.connectionTest.providerAutonomousPromotionMissingRequirements',
        value: 'Stable history runs',
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
