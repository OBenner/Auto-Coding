import type {
  ProviderAutonomousPromotionGateDiagnostics,
  ProviderAutonomousReadinessDiagnostics,
  ProviderAutonomousReadinessRequirements,
  ProviderContractHealth,
  ProviderE2eSuiteDiagnostics,
  ProviderLiveFaultProbeDiagnostics,
  ProviderLiveTaskFamilyDiagnostics,
  ProviderNegativeFixtureDiagnostics,
  ProviderReliabilityDiagnostics,
  ProviderRunHistoryRecentRun,
  ProviderRunHistoryDiagnostics,
  ProviderValidatedRuntimeResumePolicy,
  ProviderValidatedTransactionBatchContract,
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

function providerReadinessRequirementsFromUnknown(
  value: unknown
): ProviderAutonomousReadinessRequirements | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const requirements: ProviderAutonomousReadinessRequirements = {
    minStableRuns: numberFromUnknown(payload.min_stable_runs),
    observedRecentWindow: numberFromUnknown(payload.observed_recent_window),
    observedConsecutivePasses: numberFromUnknown(
      payload.observed_consecutive_passes
    ),
    historyStabilityComplete: booleanFromUnknown(
      payload.history_stability_complete
    ),
    requiredLiveFaultCases: arrayFromUnknown(payload.required_live_fault_cases),
    liveFaultCoveredCases: arrayFromUnknown(payload.live_fault_covered_cases),
    liveFaultMissingCases: arrayFromUnknown(payload.live_fault_missing_cases),
    liveFaultCoverageComplete: booleanFromUnknown(
      payload.live_fault_coverage_complete
    ),
    requiredLiveTaskFamilies: arrayFromUnknown(
      payload.required_live_task_families
    ),
    liveTaskCoveredFamilies: arrayFromUnknown(
      payload.live_task_covered_families
    ),
    liveTaskMissingFamilies: arrayFromUnknown(
      payload.live_task_missing_families
    ),
    liveTaskFamilyCoverageComplete: booleanFromUnknown(
      payload.live_task_family_coverage_complete
    ),
    lastRunAt: stringFromUnknown(payload.last_run_at),
    maxHistoryAgeSeconds: numberFromUnknown(payload.max_history_age_seconds),
    historyFreshnessComplete: booleanFromUnknown(
      payload.history_freshness_complete
    ),
  };

  return Object.values(requirements).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? requirements
    : undefined;
}

function providerRunHistoryRecentRunFromUnknown(
  value: unknown
): ProviderRunHistoryRecentRun | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const run: ProviderRunHistoryRecentRun = {
    timestamp: stringFromUnknown(payload.timestamp),
    status: stringFromUnknown(payload.status),
    runtimeMode: stringFromUnknown(payload.runtime_mode),
    model: stringFromUnknown(payload.model),
    reliabilityStatus: stringFromUnknown(payload.reliability_status),
    providerE2eStatus: stringFromUnknown(payload.provider_e2e_status),
    liveFaultProbeStatus: stringFromUnknown(payload.live_fault_probe_status),
    liveTaskFamilyStatus: stringFromUnknown(payload.live_task_family_status),
  };

  return Object.values(run).some((field) => field !== undefined) ? run : undefined;
}

function providerRunHistoryRecentRunsFromUnknown(
  value: unknown
): ProviderRunHistoryRecentRun[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const runs = value
    .map(providerRunHistoryRecentRunFromUnknown)
    .filter((run): run is ProviderRunHistoryRecentRun => Boolean(run));
  return runs.length ? runs : undefined;
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

export function mapProviderTransactionBatchContract(
  value: unknown
): ProviderValidatedTransactionBatchContract | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const contract: ProviderValidatedTransactionBatchContract = {
    status: stringFromUnknown(payload.status),
    batchBoundaryGuard: stringFromUnknown(payload.batch_boundary_guard),
    transactionBatchCount: numberFromUnknown(payload.transaction_batch_count),
    openTransactionBatchIds: arrayFromUnknown(payload.open_transaction_batch_ids),
    boundaryErrorCount: numberFromUnknown(payload.boundary_error_count),
    boundaryErrorReasons: arrayFromUnknown(payload.boundary_error_reasons),
    boundaryPreferredStrategy: stringFromUnknown(
      payload.boundary_preferred_strategy
    ),
    boundaryRequiredActionKinds: arrayFromUnknown(
      payload.boundary_required_action_kinds
    ),
    boundaryResolutionStrategies: arrayFromUnknown(
      payload.boundary_resolution_strategies
    ),
    stagedWorkspaceGuardStatuses: arrayFromUnknown(
      payload.staged_workspace_guard_statuses
    ),
    stagedDriftPaths: arrayFromUnknown(payload.staged_drift_paths),
    stagedIsolationStatuses: arrayFromUnknown(payload.staged_isolation_statuses),
    stagedWorkspaceRestoreStatuses: arrayFromUnknown(
      payload.staged_workspace_restore_statuses
    ),
    stagedBaselinePaths: arrayFromUnknown(payload.staged_baseline_paths),
    batchLifecycleActions: arrayFromUnknown(payload.batch_lifecycle_actions),
    batchLifecycleStatuses: arrayFromUnknown(payload.batch_lifecycle_statuses),
    committedMutationSnapshotIds: arrayFromUnknown(
      payload.committed_mutation_snapshot_ids
    ),
    commitOperationIds: arrayFromUnknown(payload.commit_operation_ids),
  };

  return Object.values(contract).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
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

export function mapProviderAutonomousReadiness(
  value: unknown
): ProviderAutonomousReadinessDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const readiness: ProviderAutonomousReadinessDiagnostics = {
    status: stringFromUnknown(payload.status),
    provider: stringFromUnknown(payload.provider),
    source: stringFromUnknown(payload.source),
    recommendation: stringFromUnknown(payload.recommendation),
    recommendationReasons: arrayFromUnknown(payload.recommendation_reasons),
    blockers: arrayFromUnknown(payload.blockers),
    warnings: arrayFromUnknown(payload.warnings),
    evidence: arrayFromUnknown(payload.evidence),
    requirements: providerReadinessRequirementsFromUnknown(payload.requirements),
    missingRequirements: arrayFromUnknown(payload.missing_requirements),
    nextActions: arrayFromUnknown(payload.next_actions),
  };

  return Object.values(readiness).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? readiness
    : undefined;
}

export function mapProviderAutonomousPromotionGate(
  value: unknown
): ProviderAutonomousPromotionGateDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const gate: ProviderAutonomousPromotionGateDiagnostics = {
    status: stringFromUnknown(payload.status),
    provider: stringFromUnknown(payload.provider),
    source: stringFromUnknown(payload.source),
    promotionReady: booleanFromUnknown(payload.promotion_ready),
    requiredReliabilityCases: arrayFromUnknown(payload.required_reliability_cases),
    passedReliabilityCases: arrayFromUnknown(payload.passed_reliability_cases),
    missingReliabilityCases: arrayFromUnknown(payload.missing_reliability_cases),
    requiredE2eRuns: arrayFromUnknown(payload.required_e2e_runs),
    observedE2eRuns: arrayFromUnknown(payload.observed_e2e_runs),
    missingE2eRuns: arrayFromUnknown(payload.missing_e2e_runs),
    readinessStatus: stringFromUnknown(payload.readiness_status),
    readinessMissingRequirements: arrayFromUnknown(
      payload.readiness_missing_requirements
    ),
  };

  return Object.values(gate).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? gate
    : undefined;
}

export function mapProviderReliability(
  value: unknown
): ProviderReliabilityDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const cases = Array.isArray(payload.cases)
    ? payload.cases
      .filter((item): item is Record<string, unknown> =>
        Boolean(item) && typeof item === 'object' && !Array.isArray(item)
      )
      .map((item) => ({
        case: stringFromUnknown(item.case),
        status: stringFromUnknown(item.status),
        source: stringFromUnknown(item.source),
      }))
      .filter((item) => Object.values(item).some((field) => field !== undefined))
    : undefined;
  const reliability: ProviderReliabilityDiagnostics = {
    provider: stringFromUnknown(payload.provider),
    suite: stringFromUnknown(payload.suite),
    status: stringFromUnknown(payload.status),
    observedCaseCount: numberFromUnknown(payload.observed_case_count),
    passedCaseCount: numberFromUnknown(payload.passed_case_count),
    requiredCaseCount: numberFromUnknown(payload.required_case_count),
    uncoveredCases: arrayFromUnknown(payload.uncovered_cases),
    cases: cases?.length ? cases : undefined,
  };

  return Object.values(reliability).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? reliability
    : undefined;
}

export function mapProviderE2eSuite(
  value: unknown
): ProviderE2eSuiteDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const runs = Array.isArray(payload.runs)
    ? payload.runs
      .filter((item): item is Record<string, unknown> =>
        Boolean(item) && typeof item === 'object' && !Array.isArray(item)
      )
      .map((item) => ({
        runtimeMode: stringFromUnknown(item.runtime_mode),
        status: stringFromUnknown(item.status),
        message: stringFromUnknown(item.message),
        reason: stringFromUnknown(item.reason),
      }))
      .filter((item) => Object.values(item).some((field) => field !== undefined))
    : undefined;
  const suite: ProviderE2eSuiteDiagnostics = {
    status: stringFromUnknown(payload.status),
    runs: runs?.length ? runs : undefined,
  };

  return Object.values(suite).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? suite
    : undefined;
}

export function mapProviderNegativeFixtures(
  value: unknown
): ProviderNegativeFixtureDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const fixtures: ProviderNegativeFixtureDiagnostics = {
    status: stringFromUnknown(payload.status),
    provider: stringFromUnknown(payload.provider),
    source: stringFromUnknown(payload.source),
    coveredCases: arrayFromUnknown(payload.covered_cases),
  };

  return Object.values(fixtures).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? fixtures
    : undefined;
}

export function mapProviderLiveFaultProbes(
  value: unknown
): ProviderLiveFaultProbeDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const probes =
    payload.probes && typeof payload.probes === 'object' && !Array.isArray(payload.probes)
      ? Object.entries(payload.probes)
        .filter(
          (entry): entry is [string, Record<string, unknown>] =>
            Boolean(entry[1]) && typeof entry[1] === 'object' && !Array.isArray(entry[1])
        )
        .map(([caseName, probe]) => ({
          case: caseName,
          status: stringFromUnknown(probe.status),
          source: stringFromUnknown(probe.source),
          reason: stringFromUnknown(probe.reason),
          envName: stringFromUnknown(probe.env_name),
        }))
        .filter((item) => Object.values(item).some((field) => field !== undefined))
      : undefined;
  const diagnostics: ProviderLiveFaultProbeDiagnostics = {
    status: stringFromUnknown(payload.status),
    provider: stringFromUnknown(payload.provider),
    source: stringFromUnknown(payload.source),
    enabled: booleanFromUnknown(payload.enabled),
    coveredCases: arrayFromUnknown(payload.covered_cases),
    requiredEnv: arrayFromUnknown(payload.required_env),
    missingEnv: arrayFromUnknown(payload.missing_env),
    probes: probes?.length ? probes : undefined,
  };

  return Object.values(diagnostics).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? diagnostics
    : undefined;
}

export function mapProviderLiveTaskFamilies(
  value: unknown
): ProviderLiveTaskFamilyDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const families =
    payload.families && typeof payload.families === 'object' && !Array.isArray(payload.families)
      ? Object.entries(payload.families)
        .filter(
          (entry): entry is [string, Record<string, unknown>] =>
            Boolean(entry[1]) && typeof entry[1] === 'object' && !Array.isArray(entry[1])
        )
        .map(([familyName, family]) => ({
          family: familyName,
          status: stringFromUnknown(family.status),
          source: stringFromUnknown(family.source),
          reason: stringFromUnknown(family.reason),
          envName: stringFromUnknown(family.env_name),
        }))
        .filter((item) => Object.values(item).some((field) => field !== undefined))
      : undefined;
  const diagnostics: ProviderLiveTaskFamilyDiagnostics = {
    status: stringFromUnknown(payload.status),
    provider: stringFromUnknown(payload.provider),
    source: stringFromUnknown(payload.source),
    enabled: booleanFromUnknown(payload.enabled),
    coveredFamilies: arrayFromUnknown(payload.covered_families),
    failedFamilies: arrayFromUnknown(payload.failed_families),
    requiredEnv: arrayFromUnknown(payload.required_env),
    missingEnv: arrayFromUnknown(payload.missing_env),
    families: families?.length ? families : undefined,
  };

  return Object.values(diagnostics).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? diagnostics
    : undefined;
}

export function mapProviderRunHistory(
  value: unknown
): ProviderRunHistoryDiagnostics | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const history: ProviderRunHistoryDiagnostics = {
    status: stringFromUnknown(payload.status),
    provider: stringFromUnknown(payload.provider),
    runtimeMode: stringFromUnknown(payload.runtime_mode),
    totalRuns: numberFromUnknown(payload.total_runs),
    passedRuns: numberFromUnknown(payload.passed_runs),
    failedRuns: numberFromUnknown(payload.failed_runs),
    lastStatus: stringFromUnknown(payload.last_status),
    lastReliabilityStatus: stringFromUnknown(payload.last_reliability_status),
    lastProviderE2eStatus: stringFromUnknown(payload.last_provider_e2e_status),
    e2eCaseCount: numberFromUnknown(payload.e2e_case_count),
    e2ePassedCaseCount: numberFromUnknown(payload.e2e_passed_case_count),
    e2eFailedCaseCount: numberFromUnknown(payload.e2e_failed_case_count),
    e2eCasePassRatePercent: numberFromUnknown(
      payload.e2e_case_pass_rate_percent
    ),
    reliabilityObservedCaseCount: numberFromUnknown(
      payload.reliability_observed_case_count
    ),
    reliabilityPassedCaseCount: numberFromUnknown(
      payload.reliability_passed_case_count
    ),
    reliabilityRequiredCaseCount: numberFromUnknown(
      payload.reliability_required_case_count
    ),
    reliabilityCasePassRatePercent: numberFromUnknown(
      payload.reliability_case_pass_rate_percent
    ),
    lastLiveFaultProbeStatus: stringFromUnknown(payload.last_live_fault_probe_status),
    liveFaultProbeEnabledRuns: numberFromUnknown(payload.live_fault_probe_enabled_runs),
    liveFaultProbePassedRuns: numberFromUnknown(payload.live_fault_probe_passed_runs),
    liveFaultProbeCoveredCases: arrayFromUnknown(payload.live_fault_probe_covered_cases),
    lastLiveTaskFamilyStatus: stringFromUnknown(
      payload.last_live_task_family_status
    ),
    liveTaskFamilyEnabledRuns: numberFromUnknown(
      payload.live_task_family_enabled_runs
    ),
    liveTaskFamilyPassedRuns: numberFromUnknown(
      payload.live_task_family_passed_runs
    ),
    liveTaskFamilyCoveredFamilies: arrayFromUnknown(
      payload.live_task_family_covered_families
    ),
    liveTaskFamilyFailedFamilies: arrayFromUnknown(
      payload.live_task_family_failed_families
    ),
    passRatePercent: numberFromUnknown(payload.pass_rate_percent),
    recentPassRatePercent: numberFromUnknown(payload.recent_pass_rate_percent),
    observedLiveFaultCaseCount: numberFromUnknown(
      payload.observed_live_fault_case_count
    ),
    requiredLiveFaultCaseCount: numberFromUnknown(
      payload.required_live_fault_case_count
    ),
    liveFaultProbeCaseCoveragePercent: numberFromUnknown(
      payload.live_fault_probe_case_coverage_percent
    ),
    observedLiveTaskFamilyCount: numberFromUnknown(
      payload.observed_live_task_family_count
    ),
    requiredLiveTaskFamilyCount: numberFromUnknown(
      payload.required_live_task_family_count
    ),
    liveTaskFamilyCoveragePercent: numberFromUnknown(
      payload.live_task_family_coverage_percent
    ),
    trend: stringFromUnknown(payload.trend),
    trendReason: stringFromUnknown(payload.trend_reason),
    recentWindow: numberFromUnknown(payload.recent_window),
    recentPassedRuns: numberFromUnknown(payload.recent_passed_runs),
    recentFailedRuns: numberFromUnknown(payload.recent_failed_runs),
    recentRuns: providerRunHistoryRecentRunsFromUnknown(payload.recent_runs),
    consecutivePasses: numberFromUnknown(payload.consecutive_passes),
    consecutiveFailures: numberFromUnknown(payload.consecutive_failures),
    path: stringFromUnknown(payload.path),
    reason: stringFromUnknown(payload.reason),
  };

  return Object.values(history).some((field) =>
    Array.isArray(field) ? field.length > 0 : field !== undefined
  )
    ? history
    : undefined;
}
