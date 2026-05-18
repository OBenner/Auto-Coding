import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleSlash,
  DollarSign,
  Info,
  RefreshCw,
  ShieldCheck,
  XCircle
} from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { SettingsSection } from './SettingsSection';
import { MODEL_PRICING, estimateSessionCost } from '../../../shared/constants/model-costs';
import type {
  AgentRuntimeMode,
  AIEngineProvider,
  AIProviderConfig,
  CliRunnerContractMatrixRow,
  ProviderConfigValidation,
  ProviderConnectionTestResult,
  ProviderE2eSuiteDiagnostics,
  ProviderLiveFaultProbeDiagnostics,
  ProviderNegativeFixtureDiagnostics,
  ProviderReliabilityDiagnostics,
  ProviderRunHistoryDiagnostics,
  ProviderRuntimeDiagnostics,
  ProviderValidatedRuntimeResumePolicy,
  ProviderValidatedTransactionBatchContract,
  RuntimeCapabilityMatrixRow,
  RuntimeComparativeEvalMatrixRow,
  RuntimeControlPlaneDiagnostics,
  RuntimeEvalHistoryRow,
  RuntimeExternalMcpSmokeResult,
  RuntimeExternalMcpHealthRow,
  RuntimeEvalMatrixRow,
  RuntimeFallbackMatrixRow,
  RuntimeMcpBridgePermissionRow,
  RuntimeMcpBridgePlanRow,
  RuntimePolicyMatrixRow,
  RuntimeSubagentMutationPolicyRow,
  RuntimeSubagentMatrixRow
} from '../../../shared/types/settings';

type ProviderSettingsSectionProps = Record<string, never>;
type CapabilityStatus = 'supported' | 'limited' | 'unavailable';
type ProviderCapabilityKey =
  | 'fullAutonomous'
  | 'genericEdit'
  | 'patchProposal'
  | 'analysisOnly'
  | 'nativeTools'
  | 'mcp'
  | 'subagents'
  | 'filesystemEdits';

const USE_GLOBAL_RUNTIME_MODE = '__global__';
const NON_CLAUDE_DEFAULT_RUNTIME_MODE: AgentRuntimeMode = 'generic_edit';
const COST_ESTIMATE_INPUT_TOKENS = 80_000;
const COST_ESTIMATE_OUTPUT_TOKENS = 20_000;
const RUNTIME_OVERRIDE_KEYS = [
  'plannerRuntimeMode',
  'coderRuntimeMode',
  'qaReviewerRuntimeMode',
  'qaFixerRuntimeMode'
] as const;
const PROVIDER_CAPABILITY_KEYS: ProviderCapabilityKey[] = [
  'fullAutonomous',
  'genericEdit',
  'patchProposal',
  'analysisOnly',
  'nativeTools',
  'mcp',
  'subagents',
  'filesystemEdits'
];

const DEFAULT_PROVIDER_MODEL: Record<AIEngineProvider, string> = {
  claude: 'claude-sonnet-4-5-20250929',
  codex: 'codex-default',
  openai: 'gpt-4o',
  google: 'gemini-2.0-flash',
  litellm: 'openai/gpt-4o',
  openrouter: 'openai/gpt-4o',
  zhipuai: 'glm-4-flash-250414',
  ollama: 'llama3'
};

const PROVIDER_CAPABILITY_MATRIX: Record<
  AIEngineProvider,
  Record<ProviderCapabilityKey, CapabilityStatus>
> = {
  claude: {
    fullAutonomous: 'supported',
    genericEdit: 'supported',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'supported',
    mcp: 'supported',
    subagents: 'supported',
    filesystemEdits: 'supported'
  },
  codex: {
    fullAutonomous: 'supported',
    genericEdit: 'supported',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'supported',
    mcp: 'unavailable',
    subagents: 'limited',
    filesystemEdits: 'supported'
  },
  openai: {
    fullAutonomous: 'unavailable',
    genericEdit: 'supported',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'supported',
    mcp: 'limited',
    subagents: 'limited',
    filesystemEdits: 'limited'
  },
  google: {
    fullAutonomous: 'unavailable',
    genericEdit: 'limited',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'unavailable',
    mcp: 'limited',
    subagents: 'limited',
    filesystemEdits: 'limited'
  },
  litellm: {
    fullAutonomous: 'unavailable',
    genericEdit: 'limited',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'limited',
    mcp: 'limited',
    subagents: 'limited',
    filesystemEdits: 'limited'
  },
  openrouter: {
    fullAutonomous: 'unavailable',
    genericEdit: 'limited',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'limited',
    mcp: 'limited',
    subagents: 'limited',
    filesystemEdits: 'limited'
  },
  zhipuai: {
    fullAutonomous: 'unavailable',
    genericEdit: 'limited',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'limited',
    mcp: 'limited',
    subagents: 'limited',
    filesystemEdits: 'limited'
  },
  ollama: {
    fullAutonomous: 'unavailable',
    genericEdit: 'limited',
    patchProposal: 'supported',
    analysisOnly: 'supported',
    nativeTools: 'unavailable',
    mcp: 'limited',
    subagents: 'limited',
    filesystemEdits: 'limited'
  }
};

const PROVIDER_OPTIONS: Array<{
  value: AIEngineProvider;
  labelKey: string;
  descriptionKey: string;
}> = [
  { value: 'claude', labelKey: 'settings:aiProvider.providers.claude.name', descriptionKey: 'settings:aiProvider.providers.claude.description' },
  { value: 'codex', labelKey: 'settings:aiProvider.providers.codex.name', descriptionKey: 'settings:aiProvider.providers.codex.description' },
  { value: 'openai', labelKey: 'settings:aiProvider.providers.openai.name', descriptionKey: 'settings:aiProvider.providers.openai.description' },
  { value: 'google', labelKey: 'settings:aiProvider.providers.google.name', descriptionKey: 'settings:aiProvider.providers.google.description' },
  { value: 'litellm', labelKey: 'settings:aiProvider.providers.litellm.name', descriptionKey: 'settings:aiProvider.providers.litellm.description' },
  { value: 'openrouter', labelKey: 'settings:aiProvider.providers.openrouter.name', descriptionKey: 'settings:aiProvider.providers.openrouter.description' },
  { value: 'zhipuai', labelKey: 'settings:aiProvider.providers.zhipuai.name', descriptionKey: 'settings:aiProvider.providers.zhipuai.description' },
  { value: 'ollama', labelKey: 'settings:aiProvider.providers.ollama.name', descriptionKey: 'settings:aiProvider.providers.ollama.description' },
];

const RUNTIME_MODE_OPTIONS: Array<{
  value: AgentRuntimeMode;
  labelKey: string;
  descriptionKey: string;
}> = [
  { value: 'full_autonomous', labelKey: 'settings:aiProvider.runtimeModes.fullAutonomous.name', descriptionKey: 'settings:aiProvider.runtimeModes.fullAutonomous.description' },
  { value: 'generic_edit', labelKey: 'settings:aiProvider.runtimeModes.genericEdit.name', descriptionKey: 'settings:aiProvider.runtimeModes.genericEdit.description' },
  { value: 'patch_proposal', labelKey: 'settings:aiProvider.runtimeModes.patchProposal.name', descriptionKey: 'settings:aiProvider.runtimeModes.patchProposal.description' },
  { value: 'analysis_only', labelKey: 'settings:aiProvider.runtimeModes.analysisOnly.name', descriptionKey: 'settings:aiProvider.runtimeModes.analysisOnly.description' },
];

const RUNTIME_DIAGNOSTIC_TRANSLATION_KEYS: Record<string, string> = {
  abort_batch: 'settings:aiProvider.runtimeDiagnosticValues.abortBatch',
  amp: 'settings:aiProvider.runtimeDiagnosticValues.amp',
  adapter_missing: 'settings:aiProvider.runtimeDiagnosticValues.adapterMissing',
  adapter_tool_missing_on_server: 'settings:aiProvider.runtimeDiagnosticValues.adapterToolMissingOnServer',
  analysis_only: 'settings:aiProvider.runtimeDiagnosticValues.analysisOnly',
  apply_patch: 'settings:aiProvider.runtimeDiagnosticValues.applyPatch',
  batch_boundary_violation: 'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryViolation',
  begin_batch: 'settings:aiProvider.runtimeDiagnosticValues.beginBatch',
  boundary_guarded: 'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryGuarded',
  blocked: 'settings:aiProvider.runtimeDiagnosticValues.blocked',
  call_custom_mcp: 'settings:aiProvider.runtimeDiagnosticValues.callCustomMcp',
  choose_concrete_server: 'settings:aiProvider.runtimeDiagnosticValues.chooseConcreteServer',
  claude_code: 'settings:aiProvider.runtimeDiagnosticValues.claudeCode',
  client_disabled: 'settings:aiProvider.runtimeDiagnosticValues.clientDisabled',
  coder: 'settings:aiProvider.runtimeDiagnosticValues.coder',
  codex_cli: 'settings:aiProvider.runtimeDiagnosticValues.codexCli',
  commit_batch: 'settings:aiProvider.runtimeDiagnosticValues.commitBatch',
  configuration_blocked: 'settings:aiProvider.runtimeDiagnosticValues.configurationBlocked',
  configuration_error: 'settings:aiProvider.runtimeDiagnosticValues.configurationError',
  configure_external_mcp_client: 'settings:aiProvider.runtimeDiagnosticValues.configureExternalMcpClient',
  configure_local_bridge_tools: 'settings:aiProvider.runtimeDiagnosticValues.configureLocalBridgeTools',
  cursor_cli: 'settings:aiProvider.runtimeDiagnosticValues.cursorCli',
  deepv_code: 'settings:aiProvider.runtimeDiagnosticValues.deepvCode',
  deny_before_execution: 'settings:aiProvider.runtimeDiagnosticValues.denyBeforeExecution',
  dynamic_auto_claude_tool_policy:
    'settings:aiProvider.runtimeDiagnosticValues.dynamicAutoClaudeToolPolicy',
  dynamic_mutating_tool_policy:
    'settings:aiProvider.runtimeDiagnosticValues.dynamicMutatingToolPolicy',
  enforced: 'settings:aiProvider.runtimeDiagnosticValues.enforced',
  error: 'settings:aiProvider.runtimeDiagnosticValues.error',
  external_mcp_client: 'settings:aiProvider.runtimeDiagnosticValues.externalMcpClient',
  failed: 'settings:aiProvider.runtimeDiagnosticValues.failed',
  fallback_active: 'settings:aiProvider.runtimeDiagnosticValues.fallbackActive',
  filesystem_edit: 'settings:aiProvider.runtimeDiagnosticValues.filesystemEdit',
  filesystem_read: 'settings:aiProvider.runtimeDiagnosticValues.filesystemRead',
  full_autonomous: 'settings:aiProvider.runtimeDiagnosticValues.fullAutonomous',
  function_tools: 'settings:aiProvider.runtimeDiagnosticValues.functionTools',
  generic_core_configurable: 'settings:aiProvider.runtimeDiagnosticValues.genericCoreConfigurable',
  generic_cli_pool: 'settings:aiProvider.runtimeDiagnosticValues.genericCliPool',
  generic_edit: 'settings:aiProvider.runtimeDiagnosticValues.genericEdit',
  generic_edit_recovery: 'settings:aiProvider.runtimeDiagnosticValues.genericEditRecovery',
  generic_edit_tool_loop: 'settings:aiProvider.runtimeDiagnosticValues.genericEditToolLoop',
  generic_jsonl_core: 'settings:aiProvider.runtimeDiagnosticValues.genericJsonlCore',
  google: 'settings:aiProvider.runtimeDiagnosticValues.google',
  goose: 'settings:aiProvider.runtimeDiagnosticValues.goose',
  gateway_blocked: 'settings:aiProvider.runtimeDiagnosticValues.gatewayBlocked',
  gateway_error: 'settings:aiProvider.runtimeDiagnosticValues.gatewayError',
  gateway_model_probe: 'settings:aiProvider.runtimeDiagnosticValues.gatewayModelProbe',
  http_error: 'settings:aiProvider.runtimeDiagnosticValues.httpError',
  incomplete: 'settings:aiProvider.runtimeDiagnosticValues.incomplete',
  inspect_diff: 'settings:aiProvider.runtimeDiagnosticValues.inspectDiff',
  isolated: 'settings:aiProvider.runtimeDiagnosticValues.isolated',
  invalid_response: 'settings:aiProvider.runtimeDiagnosticValues.invalidResponse',
  json_actions: 'settings:aiProvider.runtimeDiagnosticValues.jsonActions',
  json_fallback: 'settings:aiProvider.runtimeDiagnosticValues.jsonFallback',
  inspect_runtime_mcp_support: 'settings:aiProvider.runtimeDiagnosticValues.inspectRuntimeMcpSupport',
  implement_external_mcp_transport: 'settings:aiProvider.runtimeDiagnosticValues.implementExternalMcpTransport',
  litellm: 'settings:aiProvider.runtimeDiagnosticValues.litellm',
  live_gateway_model_probe: 'settings:aiProvider.runtimeDiagnosticValues.liveGatewayModelProbe',
  live_unsupported_tools_probe:
    'settings:aiProvider.runtimeDiagnosticValues.liveUnsupportedToolsProbe',
  live_provider_e2e_required: 'settings:aiProvider.runtimeDiagnosticValues.liveProviderE2eRequired',
  local_bridge: 'settings:aiProvider.runtimeDiagnosticValues.localBridge',
  local_model_quality_varies: 'settings:aiProvider.runtimeDiagnosticValues.localModelQualityVaries',
  limited: 'settings:aiProvider.runtimeDiagnosticValues.limited',
  model_blocked: 'settings:aiProvider.runtimeDiagnosticValues.modelBlocked',
  model_unavailable: 'settings:aiProvider.runtimeDiagnosticValues.modelUnavailable',
  missing_configuration: 'settings:aiProvider.runtimeDiagnosticValues.missingConfiguration',
  missing_full_autonomous_runtime: 'settings:aiProvider.runtimeDiagnosticValues.missingFullAutonomousRuntime',
  missing_runner_resume: 'settings:aiProvider.runtimeDiagnosticValues.missingRunnerResume',
  must_use_full_runtime: 'settings:aiProvider.runtimeDiagnosticValues.mustUseFullRuntime',
  mini_pipeline: 'settings:aiProvider.runtimeDiagnosticValues.miniPipeline',
  mini_pipeline_blocked: 'settings:aiProvider.runtimeDiagnosticValues.miniPipelineBlocked',
  mini_pipeline_ready: 'settings:aiProvider.runtimeDiagnosticValues.miniPipelineReady',
  mini_task_pipeline: 'settings:aiProvider.runtimeDiagnosticValues.miniTaskPipeline',
  mcp_bridge_contract: 'settings:aiProvider.runtimeDiagnosticValues.mcpBridgeContract',
  mutating_subagents_require_transactional_merge:
    'settings:aiProvider.runtimeDiagnosticValues.mutatingSubagentsRequireTransactionalMerge',
  native: 'settings:aiProvider.runtimeDiagnosticValues.native',
  native_mcp_runtime: 'settings:aiProvider.runtimeDiagnosticValues.nativeMcpRuntime',
  native_runtime_policy: 'settings:aiProvider.runtimeDiagnosticValues.nativeRuntimePolicy',
  native_tool_loop: 'settings:aiProvider.runtimeDiagnosticValues.nativeToolLoop',
  native_tool_calls: 'settings:aiProvider.runtimeDiagnosticValues.nativeToolCalls',
  native_tool_request_failed: 'settings:aiProvider.runtimeDiagnosticValues.nativeToolRequestFailed',
  needs_recovery: 'settings:aiProvider.runtimeDiagnosticValues.needsRecovery',
  normalized: 'settings:aiProvider.runtimeDiagnosticValues.normalized',
  no: 'settings:aiProvider.runtimeDiagnosticValues.no',
  none: 'settings:aiProvider.runtimeDiagnosticValues.none',
  not_covered: 'settings:aiProvider.runtimeDiagnosticValues.notCovered',
  not_observed: 'settings:aiProvider.runtimeDiagnosticValues.notObserved',
  not_required: 'settings:aiProvider.runtimeDiagnosticValues.notRequired',
  not_bridgeable: 'settings:aiProvider.runtimeDiagnosticValues.notBridgeable',
  not_requested: 'settings:aiProvider.runtimeDiagnosticValues.notRequested',
  not_recorded: 'settings:aiProvider.runtimeDiagnosticValues.notRecorded',
  observed: 'settings:aiProvider.runtimeDiagnosticValues.observed',
  ok: 'settings:aiProvider.runtimeDiagnosticValues.ok',
  open: 'settings:aiProvider.runtimeDiagnosticValues.openBatch',
  open_batch: 'settings:aiProvider.runtimeDiagnosticValues.openBatch',
  openai: 'settings:aiProvider.runtimeDiagnosticValues.openai',
  opencode: 'settings:aiProvider.runtimeDiagnosticValues.opencode',
  openrouter: 'settings:aiProvider.runtimeDiagnosticValues.openrouter',
  ollama: 'settings:aiProvider.runtimeDiagnosticValues.ollama',
  opaque_batch_mutation: 'settings:aiProvider.runtimeDiagnosticValues.opaqueBatchMutation',
  orchestrated: 'settings:aiProvider.runtimeDiagnosticValues.orchestrated',
  partial: 'settings:aiProvider.runtimeDiagnosticValues.partial',
  partial_failure: 'settings:aiProvider.runtimeDiagnosticValues.partialFailure',
  partial_coverage: 'settings:aiProvider.runtimeDiagnosticValues.partialCoverage',
  passed: 'settings:aiProvider.runtimeDiagnosticValues.passed',
  patch_proposal: 'settings:aiProvider.runtimeDiagnosticValues.patchProposal',
  permission_allowlist_check: 'settings:aiProvider.runtimeDiagnosticValues.permissionAllowlistCheck',
  policy_gated: 'settings:aiProvider.runtimeDiagnosticValues.policyGated',
  planned: 'settings:aiProvider.runtimeDiagnosticValues.planned',
  provider_error: 'settings:aiProvider.runtimeDiagnosticValues.providerError',
  provider_e2e: 'settings:aiProvider.runtimeDiagnosticValues.providerE2e',
  provider_e2e_suite: 'settings:aiProvider.runtimeDiagnosticValues.providerE2eSuite',
  provider_adapter_negative_fixture:
    'settings:aiProvider.runtimeDiagnosticValues.providerAdapterNegativeFixture',
  provider_e2e_blocked: 'settings:aiProvider.runtimeDiagnosticValues.providerE2eBlocked',
  provider_e2e_required: 'settings:aiProvider.runtimeDiagnosticValues.providerE2eRequired',
  provider_e2e_ready: 'settings:aiProvider.runtimeDiagnosticValues.providerE2eReady',
  provider_live_fault_fixture:
    'settings:aiProvider.runtimeDiagnosticValues.providerLiveFaultFixture',
  provider_history_degraded: 'settings:aiProvider.runtimeDiagnosticValues.providerHistoryDegraded',
  provider_history_flaky: 'settings:aiProvider.runtimeDiagnosticValues.providerHistoryFlaky',
  provider_history_recovering:
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryRecovering',
  provider_history_stable: 'settings:aiProvider.runtimeDiagnosticValues.providerHistoryStable',
  provider_history_unknown: 'settings:aiProvider.runtimeDiagnosticValues.providerHistoryUnknown',
  provider_history_warming_up:
    'settings:aiProvider.runtimeDiagnosticValues.providerHistoryWarmingUp',
  provider_smoke_blocked: 'settings:aiProvider.runtimeDiagnosticValues.providerSmokeBlocked',
  provider_smoke_ready: 'settings:aiProvider.runtimeDiagnosticValues.providerSmokeReady',
  pre_execution_blocked: 'settings:aiProvider.runtimeDiagnosticValues.preExecutionBlocked',
  prefer_analysis_only: 'settings:aiProvider.runtimeDiagnosticValues.preferAnalysisOnly',
  prefer_generic_edit: 'settings:aiProvider.runtimeDiagnosticValues.preferGenericEdit',
  planner: 'settings:aiProvider.runtimeDiagnosticValues.planner',
  qwen_code: 'settings:aiProvider.runtimeDiagnosticValues.qwenCode',
  read_only: 'settings:aiProvider.runtimeDiagnosticValues.readOnly',
  ready: 'settings:aiProvider.runtimeDiagnosticValues.ready',
  ready_to_connect: 'settings:aiProvider.runtimeDiagnosticValues.readyToConnect',
  recorded: 'settings:aiProvider.runtimeDiagnosticValues.recorded',
  recorded_after_repair: 'settings:aiProvider.runtimeDiagnosticValues.recordedAfterRepair',
  record_failed: 'settings:aiProvider.runtimeDiagnosticValues.recordFailed',
  recover_partial_failure: 'settings:aiProvider.runtimeDiagnosticValues.recoverPartialFailure',
  recovered: 'settings:aiProvider.runtimeDiagnosticValues.recovered',
  repair_mutation: 'settings:aiProvider.runtimeDiagnosticValues.repairMutation',
  requires_resolution: 'settings:aiProvider.runtimeDiagnosticValues.requiresResolution',
  restored: 'settings:aiProvider.runtimeDiagnosticValues.restored',
  not_restored: 'settings:aiProvider.runtimeDiagnosticValues.notRestored',
  register_external_mcp_adapter: 'settings:aiProvider.runtimeDiagnosticValues.registerExternalMcpAdapter',
  register_or_remove_unsupported_servers: 'settings:aiProvider.runtimeDiagnosticValues.registerOrRemoveUnsupportedServers',
  review_only: 'settings:aiProvider.runtimeDiagnosticValues.reviewOnly',
  reviewer: 'settings:aiProvider.runtimeDiagnosticValues.reviewer',
  sandbox: 'settings:aiProvider.runtimeDiagnosticValues.sandbox',
  runtime_blocked: 'settings:aiProvider.runtimeDiagnosticValues.runtimeBlocked',
  server_disabled: 'settings:aiProvider.runtimeDiagnosticValues.serverDisabled',
  server_error: 'settings:aiProvider.runtimeDiagnosticValues.serverError',
  session_closed: 'settings:aiProvider.runtimeDiagnosticValues.sessionClosed',
  shell: 'settings:aiProvider.runtimeDiagnosticValues.shell',
  server_has_extra_tools: 'settings:aiProvider.runtimeDiagnosticValues.serverHasExtraTools',
  staged_batch_drift: 'settings:aiProvider.runtimeDiagnosticValues.stagedBatchDrift',
  streaming_text: 'settings:aiProvider.runtimeDiagnosticValues.streamingText',
  structured_output: 'settings:aiProvider.runtimeDiagnosticValues.structuredOutput',
  recent_runs_all_passed: 'settings:aiProvider.runtimeDiagnosticValues.recentRunsAllPassed',
  subagent: 'settings:aiProvider.runtimeDiagnosticValues.subagent',
  subagents: 'settings:aiProvider.runtimeDiagnosticValues.subagents',
  skipped: 'settings:aiProvider.runtimeDiagnosticValues.skipped',
  single_history_run: 'settings:aiProvider.runtimeDiagnosticValues.singleHistoryRun',
  smoke_not_completed: 'settings:aiProvider.runtimeDiagnosticValues.smokeNotCompleted',
  consecutive_recent_failures:
    'settings:aiProvider.runtimeDiagnosticValues.consecutiveRecentFailures',
  text_completion: 'settings:aiProvider.runtimeDiagnosticValues.textCompletion',
  transaction_batches: 'settings:aiProvider.runtimeDiagnosticValues.transactionBatches',
  transaction_batch_probe:
    'settings:aiProvider.runtimeDiagnosticValues.transactionBatchProbe',
  tool_policy_metadata: 'settings:aiProvider.runtimeDiagnosticValues.toolPolicyMetadata',
  mutating_tool_classification:
    'settings:aiProvider.runtimeDiagnosticValues.mutatingToolClassification',
  tools_list: 'settings:aiProvider.runtimeDiagnosticValues.toolsList',
  text_completion_ready: 'settings:aiProvider.runtimeDiagnosticValues.textCompletionReady',
  text_completion_only: 'settings:aiProvider.runtimeDiagnosticValues.textCompletionOnly',
  tests: 'settings:aiProvider.runtimeDiagnosticValues.tests',
  transactional_recovery_required: 'settings:aiProvider.runtimeDiagnosticValues.transactionalRecoveryRequired',
  tool_loop_blocked: 'settings:aiProvider.runtimeDiagnosticValues.toolLoopBlocked',
  tool_loop_limited: 'settings:aiProvider.runtimeDiagnosticValues.toolLoopLimited',
  tool_loop_needs_recovery: 'settings:aiProvider.runtimeDiagnosticValues.toolLoopNeedsRecovery',
  tool_loop_ready: 'settings:aiProvider.runtimeDiagnosticValues.toolLoopReady',
  complete: 'settings:aiProvider.runtimeDiagnosticValues.complete',
  direct_api_full_autonomy: 'settings:aiProvider.runtimeDiagnosticValues.directApiFullAutonomy',
  direct_api_full_autonomy_e2e: 'settings:aiProvider.runtimeDiagnosticValues.directApiFullAutonomyE2e',
  direct_full_autonomous_blocked: 'settings:aiProvider.runtimeDiagnosticValues.directFullAutonomousBlocked',
  drifted: 'settings:aiProvider.runtimeDiagnosticValues.drifted',
  finish: 'settings:aiProvider.runtimeDiagnosticValues.finish',
  gateway_model_limitations: 'settings:aiProvider.runtimeDiagnosticValues.gatewayModelLimitations',
  unavailable: 'settings:aiProvider.runtimeDiagnosticValues.unavailable',
  unknown: 'settings:aiProvider.runtimeDiagnosticValues.unknown',
  unresolved: 'settings:aiProvider.runtimeDiagnosticValues.unresolved',
  unresolved_batch_recovery: 'settings:aiProvider.runtimeDiagnosticValues.unresolvedBatchRecovery',
  unresolved_partial_failure: 'settings:aiProvider.runtimeDiagnosticValues.unresolvedPartialFailure',
  unsupported: 'settings:aiProvider.runtimeDiagnosticValues.unsupported',
  unsupported_local_tool: 'settings:aiProvider.runtimeDiagnosticValues.unsupportedLocalTool',
  unsupported_tools: 'settings:aiProvider.runtimeDiagnosticValues.unsupportedTools',
  unsupported_tools_probe: 'settings:aiProvider.runtimeDiagnosticValues.unsupportedToolsProbe',
  unsupported_transport: 'settings:aiProvider.runtimeDiagnosticValues.unsupportedTransport',
  startup_failed: 'settings:aiProvider.runtimeDiagnosticValues.startupFailed',
  timeout: 'settings:aiProvider.runtimeDiagnosticValues.timeout',
  use_native_mcp_runtime: 'settings:aiProvider.runtimeDiagnosticValues.useNativeMcpRuntime',
  wire_external_mcp_tool_execution: 'settings:aiProvider.runtimeDiagnosticValues.wireExternalMcpToolExecution',
  yes: 'settings:aiProvider.runtimeDiagnosticValues.yes',
  zhipuai: 'settings:aiProvider.runtimeDiagnosticValues.zhipuai',
  latest_run_passed_after_failures:
    'settings:aiProvider.runtimeDiagnosticValues.latestRunPassedAfterFailures',
  mixed_recent_results: 'settings:aiProvider.runtimeDiagnosticValues.mixedRecentResults',
  no_history_runs: 'settings:aiProvider.runtimeDiagnosticValues.noHistoryRuns',
};

type RuntimeDiagnosticTranslate = (key: string) => string;

export type ProviderResumePolicyDiagnosticRow = {
  labelKey: string;
  value: string;
};

type RuntimeDiagnosticRowProps = {
  label: string;
  value?: ReactNode;
  breakWords?: boolean;
};

function RuntimeDiagnosticRow({ label, value, breakWords = false }: RuntimeDiagnosticRowProps) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  return (
    <div>
      <dt>{label}</dt>
      <dd className={`${breakWords ? 'break-words ' : ''}font-medium text-foreground`}>
        {value}
      </dd>
    </div>
  );
}

function normalizeProviderRuntimeConfig(config: AIProviderConfig): AIProviderConfig {
  if (config.provider === 'claude' || config.provider === 'codex') {
    return config;
  }

  const normalized: AIProviderConfig = { ...config };
  const allowFullAutonomous = normalized.runtimeFallbackEnabled || normalized.cliRunnerRouterEnabled;
  if (normalized.runtimeMode === 'full_autonomous' && !allowFullAutonomous) {
    normalized.runtimeMode = NON_CLAUDE_DEFAULT_RUNTIME_MODE;
  }
  for (const key of RUNTIME_OVERRIDE_KEYS) {
    if (normalized[key] === 'full_autonomous' && !allowFullAutonomous) {
      normalized[key] = undefined;
    }
  }
  return normalized;
}

function getPrimaryProviderModel(config: AIProviderConfig): string {
  switch (config.provider) {
    case 'codex':
      return config.codexModel || DEFAULT_PROVIDER_MODEL.codex;
    case 'openai':
      return config.openaiModel || DEFAULT_PROVIDER_MODEL.openai;
    case 'google':
      return config.googleModel || DEFAULT_PROVIDER_MODEL.google;
    case 'litellm':
      return config.litellmModel || DEFAULT_PROVIDER_MODEL.litellm;
    case 'openrouter':
      return config.openrouterModel || DEFAULT_PROVIDER_MODEL.openrouter;
    case 'zhipuai':
      return config.zhipuaiModel || DEFAULT_PROVIDER_MODEL.zhipuai;
    case 'ollama':
      return config.ollamaModel || DEFAULT_PROVIDER_MODEL.ollama;
    default:
      return config.claudeModel || DEFAULT_PROVIDER_MODEL.claude;
  }
}

function normalizePricingModel(model: string): string | null {
  const trimmed = model.trim();
  if (!trimmed) {
    return null;
  }
  if (MODEL_PRICING[trimmed] && trimmed !== 'default') {
    return trimmed;
  }

  const segments = trimmed.split('/').reverse();
  for (const segment of segments) {
    if (MODEL_PRICING[segment] && segment !== 'default') {
      return segment;
    }
  }

  return null;
}

function getCapabilityStatusClass(status: CapabilityStatus): string {
  switch (status) {
    case 'supported':
      return 'border-success/30 bg-success/10 text-success';
    case 'limited':
      return 'border-warning/30 bg-warning/10 text-warning';
    default:
      return 'border-border bg-muted text-muted-foreground';
  }
}

function isFullAutonomousProvider(provider: AIEngineProvider): boolean {
  return provider === 'claude' || provider === 'codex';
}

function countFullAutonomousSelections(config: AIProviderConfig, activeRuntimeMode: AgentRuntimeMode): number {
  return [
    activeRuntimeMode,
    config.plannerRuntimeMode,
    config.coderRuntimeMode,
    config.qaReviewerRuntimeMode,
    config.qaFixerRuntimeMode
  ].filter((mode) => mode === 'full_autonomous').length;
}

function getCompatibilityMessageKey(
  nonClaudeFullAutonomous: boolean,
  runtimeFallbackEnabled: boolean,
  cliRunnerRouterEnabled: boolean
): string {
  if (!nonClaudeFullAutonomous) {
    return 'settings:aiProvider.compatibility.claudeFirst';
  }
  if (runtimeFallbackEnabled) {
    return 'settings:aiProvider.compatibility.fallbackActive';
  }
  if (cliRunnerRouterEnabled) {
    return 'settings:aiProvider.compatibility.runnerRouterActive';
  }
  return 'settings:aiProvider.compatibility.nonClaudeFullAutonomous';
}

function getRuntimeNoticeKey(
  fullAutonomousProvider: boolean,
  fullAutonomousSelectionCount: number,
  runtimeFallbackEnabled: boolean,
  cliRunnerRouterEnabled: boolean
): string | null {
  if (fullAutonomousProvider || fullAutonomousSelectionCount === 0) {
    return null;
  }
  if (runtimeFallbackEnabled) {
    return 'settings:aiProvider.runtime.validation.fallbackWillApply';
  }
  if (cliRunnerRouterEnabled) {
    return 'settings:aiProvider.runtime.validation.runnerRouterWillApply';
  }
  return 'settings:aiProvider.runtime.validation.fullAutonomousUnavailable';
}

function getCostInfo(config: AIProviderConfig, primaryModel: string) {
  if (config.provider === 'ollama') {
    return {
      model: primaryModel,
      isLocal: true,
      estimate: null,
      pricingModel: null
    };
  }

  const pricingModel = normalizePricingModel(primaryModel);
  if (!pricingModel) {
    return {
      model: primaryModel,
      isLocal: false,
      estimate: null,
      pricingModel: null
    };
  }

  return {
    model: primaryModel,
    isLocal: false,
    estimate: estimateSessionCost(
      pricingModel,
      COST_ESTIMATE_INPUT_TOKENS,
      COST_ESTIMATE_OUTPUT_TOKENS
    ),
    pricingModel
  };
}

function formatRuntimeDiagnosticValue(
  translate: RuntimeDiagnosticTranslate,
  value?: string | null
): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return '';
  }
  const translationKey = RUNTIME_DIAGNOSTIC_TRANSLATION_KEYS[trimmed];
  if (translationKey) {
    return translate(translationKey);
  }
  return trimmed.replaceAll('_', ' ');
}

function formatRuntimeDiagnosticList(
  translate: RuntimeDiagnosticTranslate,
  values?: string[] | null
): string {
  if (!values?.length) {
    return '';
  }
  return values
    .map((value) => formatRuntimeDiagnosticValue(translate, value))
    .filter(Boolean)
    .join(', ');
}

function formatRuntimeDiagnosticBoolean(
  translate: RuntimeDiagnosticTranslate,
  value?: boolean | null
): string {
  if (typeof value !== 'boolean') {
    return '';
  }
  return formatRuntimeDiagnosticValue(translate, value ? 'yes' : 'no');
}

export function buildProviderResumePolicyDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  resumePolicy?: ProviderValidatedRuntimeResumePolicy | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!resumePolicy) {
    return [];
  }
  return [
    {
      labelKey: 'settings:aiProvider.connectionTest.resumePolicy',
      value: formatRuntimeDiagnosticValue(translate, resumePolicy.status),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeStrategy',
      value: formatRuntimeDiagnosticValue(translate, resumePolicy.strategy),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeCanResume',
      value: formatRuntimeDiagnosticBoolean(translate, resumePolicy.canResume),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeFinishBlocked',
      value: formatRuntimeDiagnosticBoolean(translate, resumePolicy.finishBlocked),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeNextIteration',
      value: typeof resumePolicy.nextIteration === 'number'
        ? String(resumePolicy.nextIteration)
        : '',
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeRequiredActions',
      value: formatRuntimeDiagnosticList(
        translate,
        resumePolicy.requiredResolutionActionKinds
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeRequiredArtifacts',
      value: formatRuntimeDiagnosticList(translate, resumePolicy.requiredArtifacts),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeUnresolvedFailures',
      value: formatRuntimeDiagnosticList(
        translate,
        resumePolicy.unresolvedPartialFailureIds
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeUnresolvedGroups',
      value: formatRuntimeDiagnosticList(
        translate,
        resumePolicy.unresolvedTransactionGroupIds
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.resumeOpenBatches',
      value: formatRuntimeDiagnosticList(
        translate,
        resumePolicy.openTransactionBatchIds
      ),
    },
  ].filter((row) => row.value);
}

export function buildProviderReliabilityDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  reliability?: ProviderReliabilityDiagnostics | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!reliability) {
    return [];
  }
  const coverageValue = [
    typeof reliability.passedCaseCount === 'number'
      && typeof reliability.requiredCaseCount === 'number'
      ? `${reliability.passedCaseCount}/${reliability.requiredCaseCount} passed`
      : '',
    typeof reliability.observedCaseCount === 'number'
      ? `${reliability.observedCaseCount} observed`
      : '',
  ].filter(Boolean).join(', ');
  const caseValue = reliability.cases
    ?.map((entry) => {
      const name = formatRuntimeDiagnosticValue(translate, entry.case);
      const status = formatRuntimeDiagnosticValue(translate, entry.status);
      const source = formatRuntimeDiagnosticValue(translate, entry.source);
      if (!name || !status) {
        return '';
      }
      return source ? `${name}: ${status} (${source})` : `${name}: ${status}`;
    })
    .filter(Boolean)
    .join(', ');
  const rows: ProviderResumePolicyDiagnosticRow[] = [
    {
      labelKey: 'settings:aiProvider.connectionTest.reliabilityStatus',
      value: formatRuntimeDiagnosticValue(translate, reliability.status) || '',
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.reliabilitySuite',
      value: formatRuntimeDiagnosticValue(translate, reliability.suite) || '',
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.reliabilityCoverage',
      value: coverageValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.reliabilityUncovered',
      value: formatRuntimeDiagnosticList(translate, reliability.uncoveredCases),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.reliabilityCases',
      value: caseValue || '',
    },
  ];
  return rows.filter((row) => row.value);
}

export function buildProviderE2eSuiteDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  providerE2eSuite?: ProviderE2eSuiteDiagnostics | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!providerE2eSuite) {
    return [];
  }
  const runsValue = providerE2eSuite.runs
    ?.map((run) => {
      const runtime = formatRuntimeDiagnosticValue(translate, run.runtimeMode);
      const status = formatRuntimeDiagnosticValue(translate, run.status);
      if (!runtime || !status) {
        return '';
      }
      return [runtime, status].join(': ')
        + (run.message ? ` - ${run.message}` : '')
        + (run.reason ? ` - ${run.reason}` : '');
    })
    .filter(Boolean)
    .join(', ');
  const rows: ProviderResumePolicyDiagnosticRow[] = [
    {
      labelKey: 'settings:aiProvider.connectionTest.providerE2eSuite',
      value: formatRuntimeDiagnosticValue(translate, providerE2eSuite.status) || '',
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerE2eRuns',
      value: runsValue || '',
    },
  ];
  return rows.filter((row) => row.value);
}

export function buildProviderNegativeFixtureDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  fixtures?: ProviderNegativeFixtureDiagnostics | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!fixtures) {
    return [];
  }
  const status = formatRuntimeDiagnosticValue(translate, fixtures.status);
  const source = formatRuntimeDiagnosticValue(translate, fixtures.source);
  const summaryValue = [status, fixtures.provider, source].filter(Boolean).join(' - ');
  return [
    {
      labelKey: 'settings:aiProvider.connectionTest.providerNegativeFixtures',
      value: summaryValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerNegativeFixtureCases',
      value: formatRuntimeDiagnosticList(translate, fixtures.coveredCases),
    },
  ].filter((row) => row.value);
}

export function buildProviderLiveFaultProbeDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  probes?: ProviderLiveFaultProbeDiagnostics | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!probes) {
    return [];
  }
  const status = formatRuntimeDiagnosticValue(translate, probes.status);
  const source = formatRuntimeDiagnosticValue(translate, probes.source);
  const summaryValue = [status, probes.provider, source].filter(Boolean).join(' - ');
  const probeRows = probes.probes?.map((probe) => {
    const caseName = formatRuntimeDiagnosticValue(translate, probe.case);
    const probeStatus = formatRuntimeDiagnosticValue(translate, probe.status);
    const reason = formatRuntimeDiagnosticValue(translate, probe.reason);
    const details = [reason, probe.envName].filter(Boolean).join(' - ');
    const value = [caseName, probeStatus].filter(Boolean).join(': ');
    return {
      labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeOutcomes',
      value: value ? `${value}${details ? ` (${details})` : ''}` : '',
    };
  }) ?? [];
  return [
    {
      labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbes',
      value: summaryValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeCases',
      value: formatRuntimeDiagnosticList(translate, probes.coveredCases),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeMissingEnv',
      value: probes.missingEnv?.join(', ') || '',
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerLiveFaultProbeRequiredEnv',
      value: probes.requiredEnv?.join(', ') || '',
    },
    ...probeRows,
  ].filter((row) => row.value);
}

export function buildProviderRunHistoryDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  history?: ProviderRunHistoryDiagnostics | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!history) {
    return [];
  }
  const summaryValue = [
    formatRuntimeDiagnosticValue(translate, history.status),
    history.provider,
    formatRuntimeDiagnosticValue(translate, history.runtimeMode),
  ].filter(Boolean).join(' - ');
  const runsValue = [
    typeof history.totalRuns === 'number' ? `${history.totalRuns} total` : '',
    typeof history.passedRuns === 'number' ? `${history.passedRuns} passed` : '',
    typeof history.failedRuns === 'number' ? `${history.failedRuns} failed` : '',
  ].filter(Boolean).join(', ');
  const lastValue = [
    formatRuntimeDiagnosticValue(translate, history.lastStatus),
    formatRuntimeDiagnosticValue(translate, history.lastReliabilityStatus),
    formatRuntimeDiagnosticValue(translate, history.lastProviderE2eStatus),
  ].filter(Boolean).join(', ');
  const trendCounts = [
    typeof history.recentWindow === 'number'
      ? `${history.recentWindow} ${translate('settings:aiProvider.connectionTest.providerRunHistoryTrendWindow')}`
      : '',
    typeof history.recentPassedRuns === 'number' && typeof history.recentFailedRuns === 'number'
      ? `${history.recentPassedRuns} ${translate('settings:aiProvider.connectionTest.providerRunHistoryTrendPassed')}, ${history.recentFailedRuns} ${translate('settings:aiProvider.connectionTest.providerRunHistoryTrendFailed')}`
      : '',
    typeof history.consecutivePasses === 'number' && history.consecutivePasses > 0
      ? `${history.consecutivePasses} ${translate('settings:aiProvider.connectionTest.providerRunHistoryTrendPassStreak')}`
      : '',
    typeof history.consecutiveFailures === 'number' && history.consecutiveFailures > 0
      ? `${history.consecutiveFailures} ${translate('settings:aiProvider.connectionTest.providerRunHistoryTrendFailStreak')}`
      : '',
  ].filter(Boolean).join(', ');
  const trendValue = [
    formatRuntimeDiagnosticValue(translate, history.trend),
    trendCounts,
  ].filter(Boolean).join(' - ');
  const liveFaultProbeRunCounts = [
    typeof history.liveFaultProbeEnabledRuns === 'number'
      ? `${history.liveFaultProbeEnabledRuns} enabled`
      : '',
    typeof history.liveFaultProbePassedRuns === 'number'
      ? `${history.liveFaultProbePassedRuns} passed`
      : '',
  ].filter(Boolean).join(', ');
  const liveFaultProbeValue = [
    formatRuntimeDiagnosticValue(translate, history.lastLiveFaultProbeStatus),
    liveFaultProbeRunCounts,
    formatRuntimeDiagnosticList(translate, history.liveFaultProbeCoveredCases),
  ].filter(Boolean).join(' - ');
  return [
    {
      labelKey: 'settings:aiProvider.connectionTest.providerRunHistory',
      value: summaryValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryRuns',
      value: runsValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryLast',
      value: lastValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryTrend',
      value: trendValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryLiveFaultProbes',
      value: liveFaultProbeValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.providerRunHistoryPath',
      value: history.path || history.reason || '',
    },
  ].filter((row) => row.value);
}

export function buildRuntimePolicyDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimePolicyMatrixRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const phase = formatRuntimeDiagnosticValue(translate, row.phase);
      const selected = formatRuntimeDiagnosticValue(translate, row.selected_runtime_mode);
      const policy = formatRuntimeDiagnosticValue(translate, row.policy);
      const runners = formatRuntimeDiagnosticList(translate, row.runner_candidates);
      const suffix = [policy, runners].filter(Boolean).join(', ');
      return `${phase}: ${selected}${suffix ? ` (${suffix})` : ''}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.runtimePolicy',
      value,
    },
  ];
}

export function buildRuntimeCapabilityDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimeCapabilityMatrixRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const provider = formatRuntimeDiagnosticValue(translate, row.provider);
      const readiness = formatRuntimeDiagnosticValue(translate, row.readiness);
      const recommended = formatRuntimeDiagnosticValue(
        translate,
        row.recommended_runtime_mode
      );
      const blockers = formatRuntimeDiagnosticList(translate, row.blockers);
      const warnings = formatRuntimeDiagnosticList(translate, row.warnings);
      const runners = formatRuntimeDiagnosticList(
        translate,
        row.cli_runner_candidates
      );
      const suffix = [blockers, warnings, runners].filter(Boolean).join('; ');
      return `${provider}: ${readiness} -> ${recommended}${suffix ? ` (${suffix})` : ''}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.runtimeCapability',
      value,
    },
  ];
}

export function buildRuntimeEvalDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimeEvalMatrixRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const caseId = formatRuntimeDiagnosticValue(translate, row.case_id);
      const runtime = formatRuntimeDiagnosticValue(translate, row.runtime_mode);
      const artifacts = formatRuntimeDiagnosticList(translate, row.required_artifacts);
      return `${caseId}: ${runtime}${artifacts ? ` (${artifacts})` : ''}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.runtimeEval',
      value,
    },
  ];
}

export function buildRuntimeEvalHistoryDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimeEvalHistoryRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const caseId = formatRuntimeDiagnosticValue(translate, row.case_id);
      const status = formatRuntimeDiagnosticValue(translate, row.status);
      const runSummary = [
        `${row.total_runs} total`,
        `${row.passed_runs} passed`,
        `${row.failed_runs} failed`,
      ].join(', ');
      const missing = formatRuntimeDiagnosticList(
        translate,
        row.missing_providers
      );
      const details = [
        runSummary,
        missing ? `missing ${missing}` : '',
        row.history_path,
      ].filter(Boolean).join('; ');
      return `${caseId}: ${status}${details ? ` (${details})` : ''}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.runtimeEvalHistory',
      value,
    },
  ];
}

export function buildRuntimeComparativeEvalDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimeComparativeEvalMatrixRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const provider = formatRuntimeDiagnosticValue(translate, row.provider);
      const quality = formatRuntimeDiagnosticValue(translate, row.quality_status);
      const cost = formatRuntimeDiagnosticValue(translate, row.cost_status);
      const safety = formatRuntimeDiagnosticValue(translate, row.safety_status);
      const blockers = formatRuntimeDiagnosticList(translate, row.blockers);
      const suffix = blockers ? ` (${blockers})` : '';
      return `${provider}: ${quality} / ${cost} / ${safety}${suffix}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.runtimeComparativeEval',
      value,
    },
  ];
}

export function buildCliRunnerContractDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: CliRunnerContractMatrixRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .filter((row) => row.contract_status === 'ready' || row.adapter_required)
    .map((row) => {
      const status = formatRuntimeDiagnosticValue(translate, row.contract_status);
      const missing = row.missing_contract_facets.join(', ');
      return `${row.display_name}: ${status}${missing ? ` (${missing})` : ''}`;
    })
    .join('; ');
  return value
    ? [
      {
        labelKey: 'settings:aiProvider.controlPlane.cliRunnerContracts',
        value,
      },
    ]
    : [];
}

export function buildMutatingSubagentPolicyDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimeSubagentMutationPolicyRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const runtime = formatRuntimeDiagnosticValue(translate, row.runtime_mode);
      const status = formatRuntimeDiagnosticValue(translate, row.status);
      const missing = formatRuntimeDiagnosticList(translate, row.missing_gates);
      const reason = formatRuntimeDiagnosticValue(translate, row.reason);
      const suffix = [missing, reason].filter(Boolean).join('; ');
      return `${runtime}: ${status}${suffix ? ` (${suffix})` : ''}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.mutatingSubagentPolicy',
      value,
    },
  ];
}

export function buildMcpBridgePermissionDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  rows?: RuntimeMcpBridgePermissionRow[] | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!rows?.length) {
    return [];
  }
  const value = rows
    .map((row) => {
      const label = row.display_name || row.server;
      const status = formatRuntimeDiagnosticValue(translate, row.status);
      const strict = formatRuntimeDiagnosticBoolean(
        translate,
        row.strict_allowlist_configured
      );
      const permissions = formatRuntimeDiagnosticList(translate, row.permissions);
      const mutating = formatRuntimeDiagnosticList(
        translate,
        row.mutating_permissions
      );
      const missing = formatRuntimeDiagnosticList(translate, row.missing_gates);
      const parts = [
        permissions,
        mutating ? `mutating ${mutating}` : '',
        strict ? `strict ${strict}` : '',
        missing ? `missing ${missing}` : '',
      ].filter(Boolean);
      return `${label}: ${status}${parts.length ? ` (${parts.join('; ')})` : ''}`;
    })
    .join('; ');
  return [
    {
      labelKey: 'settings:aiProvider.controlPlane.mcpPermissions',
      value,
    },
  ];
}

export function buildProviderTransactionBatchDiagnosticRows(
  translate: RuntimeDiagnosticTranslate,
  transactionBatchContract?: ProviderValidatedTransactionBatchContract | null
): ProviderResumePolicyDiagnosticRow[] {
  if (!transactionBatchContract) {
    return [];
  }
  const boundaryErrorValue = [
    typeof transactionBatchContract.boundaryErrorCount === 'number'
      ? String(transactionBatchContract.boundaryErrorCount)
      : '',
    formatRuntimeDiagnosticList(
      translate,
      transactionBatchContract.boundaryErrorReasons
    ),
  ].filter(Boolean).join(' - ');
  return [
    {
      labelKey: 'settings:aiProvider.connectionTest.batchContract',
      value: formatRuntimeDiagnosticValue(translate, transactionBatchContract.status),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchBoundaryGuard',
      value: formatRuntimeDiagnosticValue(
        translate,
        transactionBatchContract.batchBoundaryGuard
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchCount',
      value: typeof transactionBatchContract.transactionBatchCount === 'number'
        ? String(transactionBatchContract.transactionBatchCount)
        : '',
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchBoundaryErrors',
      value: boundaryErrorValue,
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchOpenBatches',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.openTransactionBatchIds
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchPreferredStrategy',
      value: formatRuntimeDiagnosticValue(
        translate,
        transactionBatchContract.boundaryPreferredStrategy
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchRequiredActions',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.boundaryRequiredActionKinds
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchResolutionStrategies',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.boundaryResolutionStrategies
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchStagedGuardStatuses',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.stagedWorkspaceGuardStatuses
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchStagedDriftPaths',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.stagedDriftPaths
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchStagedIsolation',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.stagedIsolationStatuses
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchStagedWorkspaceRestore',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.stagedWorkspaceRestoreStatuses
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchStagedBaselinePaths',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.stagedBaselinePaths
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchLifecycleActions',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.batchLifecycleActions
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchLifecycleStatuses',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.batchLifecycleStatuses
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchCommittedSnapshots',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.committedMutationSnapshotIds
      ),
    },
    {
      labelKey: 'settings:aiProvider.connectionTest.batchCommitOperations',
      value: formatRuntimeDiagnosticList(
        translate,
        transactionBatchContract.commitOperationIds
      ),
    },
  ].filter((row) => row.value);
}

function hasRuntimeDiagnostics(
  diagnostics?: ProviderRuntimeDiagnostics | null
): diagnostics is ProviderRuntimeDiagnostics {
  return Boolean(diagnostics);
}

function findMcpBridgePlanRow(
  diagnostics: RuntimeControlPlaneDiagnostics | null,
  provider: AIEngineProvider,
  runtimeMode: AgentRuntimeMode
): RuntimeMcpBridgePlanRow | null {
  return diagnostics?.mcp_bridge_plan_matrix?.find(
    (row) => row.provider === provider && row.runtime_mode === runtimeMode
  ) ?? null;
}

function findFallbackMatrixRow(
  diagnostics: RuntimeControlPlaneDiagnostics | null,
  provider: AIEngineProvider,
  runtimeMode: AgentRuntimeMode
): RuntimeFallbackMatrixRow | null {
  return diagnostics?.runtime_fallback_matrix?.find(
    (row) => row.provider === provider && row.requested_mode === runtimeMode
  ) ?? null;
}

function findSubagentMatrixRow(
  diagnostics: RuntimeControlPlaneDiagnostics | null,
  provider: AIEngineProvider,
  runtimeMode: AgentRuntimeMode
): RuntimeSubagentMatrixRow | null {
  return diagnostics?.runtime_subagent_matrix?.find(
    (row) => row.provider === provider && row.runtime_mode === runtimeMode
  ) ?? null;
}

function findRelevantExternalMcpHealthRows(
  diagnostics: RuntimeControlPlaneDiagnostics | null,
  mcpPlan: RuntimeMcpBridgePlanRow | null
): RuntimeExternalMcpHealthRow[] {
  const externalServers = new Set([
    ...(mcpPlan?.available_servers ?? []),
    ...(mcpPlan?.external_bridge_required_servers ?? []),
    ...(mcpPlan?.external_bridge_ready_servers ?? [])
  ]);
  return diagnostics?.external_mcp_server_health?.filter(
    (row) =>
      row.bridgeable && (externalServers.has(row.server) || row.execution_supported)
  ) ?? [];
}

function findRelevantMcpPermissionRows(
  diagnostics: RuntimeControlPlaneDiagnostics | null,
  mcpPlan: RuntimeMcpBridgePlanRow | null
): RuntimeMcpBridgePermissionRow[] {
  if (!mcpPlan || mcpPlan.strategy === 'native') {
    return [];
  }
  const relevantServers = new Set([
    ...(mcpPlan.available_servers ?? []),
    ...(mcpPlan.local_bridge_required_servers ?? []),
    ...(mcpPlan.external_bridge_required_servers ?? []),
    ...(mcpPlan.external_bridge_ready_servers ?? []),
    ...(mcpPlan.external_bridged_servers ?? [])
  ]);
  return diagnostics?.mcp_bridge_permission_matrix?.filter((row) =>
    relevantServers.has(row.server)
  ) ?? [];
}

function formatExternalMcpHealthRows(
  rows: RuntimeExternalMcpHealthRow[],
  translate: (key: string) => string
): string {
  return rows
    .map((row) => {
      const label = row.display_name || row.server;
      const status = formatRuntimeDiagnosticValue(translate, row.status);
      return status ? `${label}: ${status}` : label;
    })
    .filter(Boolean)
    .join(', ');
}

function formatExecutableExternalMcpTools(rows: RuntimeExternalMcpHealthRow[]): string {
  return rows
    .flatMap((row) =>
      (row.executable_tools ?? []).map((tool) => `mcp__${row.server}__${tool}`)
    )
    .join(', ');
}

function getElectronAPI() {
  return (globalThis as unknown as Partial<Window>).electronAPI;
}

function ProviderField({
  id,
  label,
  description,
  value,
  onChange,
  type = 'text',
  placeholder
}: {
  id: string;
  label: string;
  description: string;
  value: string;
  onChange: (value: string) => void;
  type?: 'text' | 'password';
  placeholder?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </Label>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-xl"
      />
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

/**
 * Provider settings component for configuring AI providers and runtime modes.
 */
export function ProviderSettingsSection(_props: ProviderSettingsSectionProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [config, setConfig] = useState<AIProviderConfig>({
    provider: 'claude',
    runtimeMode: 'full_autonomous'
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [testingProvider, setTestingProvider] = useState(false);
  const [testingPipeline, setTestingPipeline] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [validationStatus, setValidationStatus] = useState<ProviderConfigValidation | null>(null);
  const [connectionTestStatus, setConnectionTestStatus] = useState<ProviderConnectionTestResult | null>(null);
  const [runtimeControlPlaneDiagnostics, setRuntimeControlPlaneDiagnostics] =
    useState<RuntimeControlPlaneDiagnostics | null>(null);
  const [runtimeControlPlaneLoading, setRuntimeControlPlaneLoading] = useState(false);
  const [runtimeControlPlaneError, setRuntimeControlPlaneError] = useState<string | null>(null);
  const [externalMcpSmokeResult, setExternalMcpSmokeResult] =
    useState<RuntimeExternalMcpSmokeResult | null>(null);
  const [externalMcpSmokeLoading, setExternalMcpSmokeLoading] = useState(false);
  const [externalMcpSmokeError, setExternalMcpSmokeError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await getElectronAPI()?.getProviderConfig?.();
        if (!cancelled && result?.success && result.data) {
          setConfig(
            normalizeProviderRuntimeConfig({
              ...result.data,
              provider: result.data.provider ?? 'claude',
              runtimeMode: result.data.runtimeMode ?? 'full_autonomous'
            })
          );
        }
      } catch {
        if (!cancelled) {
          setSaveStatus('error');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadRuntimeControlPlaneDiagnostics = useCallback(async () => {
    setRuntimeControlPlaneLoading(true);
    setRuntimeControlPlaneError(null);
    try {
      const result = await getElectronAPI()?.getProviderRuntimeDiagnostics?.();
      if (result?.success && result.data) {
        setRuntimeControlPlaneDiagnostics(result.data);
      } else {
        setRuntimeControlPlaneDiagnostics(null);
        setRuntimeControlPlaneError(
          result?.error ?? t('settings:aiProvider.controlPlane.unavailable')
        );
      }
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : t('settings:aiProvider.controlPlane.unavailable');
      setRuntimeControlPlaneDiagnostics(null);
      setRuntimeControlPlaneError(message);
    } finally {
      setRuntimeControlPlaneLoading(false);
    }
  }, [t]);

  const runExternalMcpSmokeCheck = useCallback(async () => {
    setExternalMcpSmokeLoading(true);
    setExternalMcpSmokeError(null);
    try {
      const result = await getElectronAPI()?.testExternalMcpContracts?.();
      if (result?.success && result.data) {
        setExternalMcpSmokeResult(result.data);
      } else {
        setExternalMcpSmokeResult(null);
        setExternalMcpSmokeError(
          result?.error ?? t('settings:aiProvider.controlPlane.contractUnavailable')
        );
      }
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : t('settings:aiProvider.controlPlane.contractUnavailable');
      setExternalMcpSmokeResult(null);
      setExternalMcpSmokeError(message);
    } finally {
      setExternalMcpSmokeLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadRuntimeControlPlaneDiagnostics();
  }, [loadRuntimeControlPlaneDiagnostics]);

  const selectedProvider = useMemo(
    () => PROVIDER_OPTIONS.find((provider) => provider.value === config.provider) ?? PROVIDER_OPTIONS[0],
    [config.provider]
  );

  const activeRuntimeMode = config.runtimeMode ?? 'full_autonomous';
  const runtimeFallbackEnabled = config.runtimeFallbackEnabled ?? false;
  const cliRunnerRouterEnabled = config.cliRunnerRouterEnabled ?? false;
  const fullAutonomousProvider = isFullAutonomousProvider(config.provider);
  const nonClaudeFullAutonomous = !fullAutonomousProvider && activeRuntimeMode === 'full_autonomous';
  const compatibilityMessageKey = getCompatibilityMessageKey(
    nonClaudeFullAutonomous,
    runtimeFallbackEnabled,
    cliRunnerRouterEnabled
  );
  const selectedCapabilities = PROVIDER_CAPABILITY_MATRIX[config.provider];
  const fullAutonomousSelectionCount = countFullAutonomousSelections(config, activeRuntimeMode);
  const runtimeNoticeKey = getRuntimeNoticeKey(
    fullAutonomousProvider,
    fullAutonomousSelectionCount,
    runtimeFallbackEnabled,
    cliRunnerRouterEnabled
  );
  const primaryModel = getPrimaryProviderModel(config);
  const costInfo = useMemo(() => getCostInfo(config, primaryModel), [config, primaryModel]);

  const updateConfig = (updates: Partial<AIProviderConfig>) => {
    setConfig((current) => normalizeProviderRuntimeConfig({ ...current, ...updates }));
    setSaveStatus('idle');
    setValidationStatus(null);
    setConnectionTestStatus(null);
  };

  const handleProviderChange = (provider: AIEngineProvider) => {
    updateConfig({
      provider,
      runtimeMode: isFullAutonomousProvider(provider) ? 'full_autonomous' : config.runtimeMode
    });
  };

  const handleRuntimeOverrideChange = (
    key: 'plannerRuntimeMode' | 'coderRuntimeMode' | 'qaReviewerRuntimeMode' | 'qaFixerRuntimeMode',
    value: string
  ) => {
    updateConfig({
      [key]: value === USE_GLOBAL_RUNTIME_MODE ? undefined : value
    } as Partial<AIProviderConfig>);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const nextConfig = normalizeProviderRuntimeConfig(config);
      setConfig(nextConfig);
      const result = await getElectronAPI()?.updateProviderConfig?.(nextConfig);
      setSaveStatus(result?.success ? 'success' : 'error');
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    setSaveStatus('idle');
    setValidationStatus(null);
    setConnectionTestStatus(null);
    try {
      const nextConfig = normalizeProviderRuntimeConfig(config);
      setConfig(nextConfig);
      const saveResult = await getElectronAPI()?.updateProviderConfig?.(nextConfig);
      if (!saveResult?.success) {
        setSaveStatus('error');
        return;
      }
      const validationResult = await getElectronAPI()?.validateProviderConfig?.();
      setValidationStatus(
        validationResult?.success ? validationResult.data ?? null : null
      );
      setSaveStatus(validationResult?.success ? 'success' : 'error');
    } catch {
      setSaveStatus('error');
    } finally {
      setValidating(false);
    }
  };

  const runProviderSmokeTest = async (requestedRuntime?: string) => {
    const isPipelineCheck = requestedRuntime === 'mini_pipeline';
    if (isPipelineCheck) {
      setTestingPipeline(true);
    } else {
      setTestingProvider(true);
    }
    setSaveStatus('idle');
    setValidationStatus(null);
    setConnectionTestStatus(null);
    try {
      const nextConfig = normalizeProviderRuntimeConfig(config);
      setConfig(nextConfig);
      const saveResult = await getElectronAPI()?.updateProviderConfig?.(nextConfig);
      if (!saveResult?.success) {
        setSaveStatus('error');
        setConnectionTestStatus({
          success: false,
          provider: nextConfig.provider,
          runtimeMode: 'analysis_only',
          message: saveResult?.error ?? t('settings:aiProvider.connectionTest.saveFailed'),
          errorDetails: saveResult?.error ?? null
        });
        return;
      }

      const testResult = await getElectronAPI()?.testProviderConfig?.(requestedRuntime);
      if (testResult?.success && testResult.data) {
        setConnectionTestStatus(testResult.data);
        setSaveStatus('success');
      } else {
        setConnectionTestStatus({
          success: false,
          provider: nextConfig.provider,
          runtimeMode: 'analysis_only',
          message: testResult?.error ?? t('settings:aiProvider.connectionTest.unavailable'),
          errorDetails: testResult?.error ?? null
        });
        setSaveStatus('error');
      }
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : t('settings:aiProvider.connectionTest.unavailable');
      setConnectionTestStatus({
        success: false,
        provider: config.provider,
        runtimeMode: 'analysis_only',
        message,
        errorDetails: message
      });
      setSaveStatus('error');
    } finally {
      if (isPipelineCheck) {
        setTestingPipeline(false);
      } else {
        setTestingProvider(false);
      }
    }
  };

  const renderRuntimeSelect = (
    id: string,
    value: AgentRuntimeMode | '' | undefined,
    onChange: (value: string) => void,
    includeGlobal: boolean
  ) => {
    const runtimeModeOptions = RUNTIME_MODE_OPTIONS.filter(
      (mode) => mode.value !== 'full_autonomous' || fullAutonomousProvider
    );
    return (
      <Select value={value || USE_GLOBAL_RUNTIME_MODE} onValueChange={onChange}>
        <SelectTrigger id={id} className="w-full max-w-xl">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {includeGlobal && (
            <SelectItem value={USE_GLOBAL_RUNTIME_MODE}>
              {t('settings:aiProvider.runtimeModes.useGlobal')}
            </SelectItem>
          )}
          {runtimeModeOptions.map((mode) => (
            <SelectItem key={mode.value} value={mode.value}>
              <div className="flex flex-col items-start">
                <span className="font-medium">{t(mode.labelKey)}</span>
                <span className="text-xs text-muted-foreground">{t(mode.descriptionKey)}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  };

  const renderCapabilityStatus = (status: CapabilityStatus) => {
    const Icon = status === 'supported'
      ? CheckCircle2
      : status === 'limited'
        ? AlertTriangle
        : XCircle;
    return (
      <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${getCapabilityStatusClass(status)}`}>
        <Icon className="h-3 w-3" />
        {t(`settings:aiProvider.compatibilityMatrix.status.${status}`)}
      </span>
    );
  };

  const renderCapabilityMatrix = () => (
    <div className="space-y-3 border-t border-border pt-4">
      <div className="flex items-start gap-2">
        <ShieldCheck className="mt-0.5 h-4 w-4 text-muted-foreground" />
        <div>
          <h3 className="text-sm font-medium text-foreground">
            {t('settings:aiProvider.compatibilityMatrix.title')}
          </h3>
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.compatibilityMatrix.description', {
              provider: t(selectedProvider.labelKey)
            })}
          </p>
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {PROVIDER_CAPABILITY_KEYS.map((capability) => (
          <div
            key={capability}
            className="flex min-h-10 items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2"
          >
            <span className="text-xs font-medium text-foreground">
              {t(`settings:aiProvider.compatibilityMatrix.capabilities.${capability}`)}
            </span>
            {renderCapabilityStatus(selectedCapabilities[capability])}
          </div>
        ))}
      </div>
    </div>
  );

  const renderRuntimeControlPlane = () => {
    const mcpPlan = findMcpBridgePlanRow(
      runtimeControlPlaneDiagnostics,
      config.provider,
      activeRuntimeMode
    );
    const fallbackRow = findFallbackMatrixRow(
      runtimeControlPlaneDiagnostics,
      config.provider,
      activeRuntimeMode
    );
    const subagentRow = findSubagentMatrixRow(
      runtimeControlPlaneDiagnostics,
      config.provider,
      activeRuntimeMode
    );
    const externalMcpHealthRows = findRelevantExternalMcpHealthRows(
      runtimeControlPlaneDiagnostics,
      mcpPlan
    );
    const mcpPermissionRows = buildMcpBridgePermissionDiagnosticRows(
      t,
      findRelevantMcpPermissionRows(runtimeControlPlaneDiagnostics, mcpPlan)
    );
    const noneLabel = t('settings:aiProvider.controlPlane.none');
    const formatControlPlaneValue = (value?: string | null) => {
      const formatted = formatRuntimeDiagnosticValue(t, value);
      return formatted && formatted !== 'none' ? formatted : noneLabel;
    };
    const formatControlPlaneList = (values?: string[] | null) =>
      formatRuntimeDiagnosticList(t, values) || noneLabel;
    const mcpStatus = mcpPlan ? formatControlPlaneValue(mcpPlan.status) : noneLabel;
    const mcpAction = mcpPlan ? formatControlPlaneValue(mcpPlan.action_required) : noneLabel;
    const externalMcpHealth = externalMcpHealthRows.length
      ? formatExternalMcpHealthRows(externalMcpHealthRows, t)
      : noneLabel;
    const executableExternalMcpTools =
      mcpPlan?.executable_external_tools?.join(', ') ||
      formatExecutableExternalMcpTools(externalMcpHealthRows) ||
      noneLabel;
    const externalMcpSmokeSummary = externalMcpSmokeResult?.summary;
    const externalMcpSmokeFailures =
      externalMcpSmokeResult?.external_mcp_contract_checks.filter(
        (row) => !row.ok && row.status !== 'skipped'
      ) ?? [];
    const externalMcpSmokeLabel = externalMcpSmokeSummary
      ? t('settings:aiProvider.controlPlane.contractSummary', {
        ok: externalMcpSmokeSummary.ok,
        failed: externalMcpSmokeSummary.failed,
        skipped: externalMcpSmokeSummary.skipped
      })
      : noneLabel;
    const fallbackSelected = fallbackRow
      ? formatControlPlaneValue(fallbackRow.fallback_selected_mode)
      : noneLabel;
    const runnerCandidates = formatControlPlaneList(
      fallbackRow?.selected_mode_runner_candidates
    );
    const subagentStrategy = subagentRow
      ? formatControlPlaneValue(subagentRow.strategy)
      : noneLabel;
    const subagentAvailability = subagentRow?.available
      ? t('settings:aiProvider.controlPlane.available')
      : t('settings:aiProvider.controlPlane.unavailableShort');
    const subagentMaxAttempts = subagentRow
      ? String(subagentRow.max_attempts)
      : noneLabel;
    const subagentMergePolicy = subagentRow
      ? formatControlPlaneValue(subagentRow.merge_policy)
      : noneLabel;
    const runtimePolicyRows = buildRuntimePolicyDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.runtime_policy_matrix?.filter(
        (row) => row.provider === config.provider
      )
    );
    const runtimeCapabilityRows = buildRuntimeCapabilityDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.runtime_capability_matrix?.filter(
        (row) => row.provider === config.provider
      )
    );
    const runtimeEvalRows = buildRuntimeEvalDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.runtime_eval_matrix
    );
    const runtimeEvalHistoryRows = buildRuntimeEvalHistoryDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.runtime_eval_history
    );
    const runtimeComparativeEvalRows = buildRuntimeComparativeEvalDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.runtime_comparative_eval_matrix
    );
    const cliRunnerContractRows = buildCliRunnerContractDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.cli_runner_contract_matrix
    );
    const mutatingSubagentPolicyRows = buildMutatingSubagentPolicyDiagnosticRows(
      t,
      runtimeControlPlaneDiagnostics?.runtime_subagent_mutation_policy?.filter(
        (row) => row.provider === config.provider && row.runtime_mode === activeRuntimeMode
      )
    );

    let controlPlaneContent: ReactNode;
    if (runtimeControlPlaneLoading && !runtimeControlPlaneDiagnostics) {
      controlPlaneContent = (
        <p className="max-w-xl rounded-md border border-border bg-background p-3 text-xs text-muted-foreground">
          {t('settings:aiProvider.controlPlane.loading')}
        </p>
      );
    } else if (runtimeControlPlaneError) {
      controlPlaneContent = (
        <div className="flex max-w-xl items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>
            {t('settings:aiProvider.controlPlane.error', {
              error: runtimeControlPlaneError
            })}
          </p>
        </div>
      );
    } else if (runtimeControlPlaneDiagnostics) {
      controlPlaneContent = (
        <div className="grid gap-3 xl:grid-cols-3">
          <div className="rounded-md border border-border bg-background p-3">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground">
              {t('settings:aiProvider.controlPlane.mcpBridgeTitle')}
            </h4>
            <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              <div>
                <dt>{t('settings:aiProvider.controlPlane.mcpStatus')}</dt>
                <dd className="font-medium text-foreground">{mcpStatus}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.mcpAction')}</dt>
                <dd className="font-medium text-foreground">{mcpAction}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.bridgedServers')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(mcpPlan?.bridged_servers)}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.externalBridgedServers')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(mcpPlan?.external_bridged_servers)}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.externalRequiredServers')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(mcpPlan?.external_bridge_required_servers)}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.nativeRequiredServers')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(mcpPlan?.native_required_servers)}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.externalHealth')}</dt>
                <dd className="font-medium text-foreground">{externalMcpHealth}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt>{t('settings:aiProvider.controlPlane.executableTools')}</dt>
                <dd className="break-words font-medium text-foreground">
                  {executableExternalMcpTools}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.contractSmoke')}</dt>
                <dd className={`font-medium ${
                  externalMcpSmokeFailures.length ? 'text-destructive' : 'text-foreground'
                }`}
                >
                  {externalMcpSmokeLabel}
                </dd>
              </div>
              {mcpPermissionRows.map((row) => (
                <div key={row.labelKey} className="sm:col-span-2">
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="break-words font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
            </dl>
            {externalMcpSmokeError && (
              <div className="mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <p>
                  {t('settings:aiProvider.controlPlane.contractError', {
                    error: externalMcpSmokeError
                  })}
                </p>
              </div>
            )}
            {externalMcpSmokeFailures.length > 0 && (
              <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
                <p className="font-medium">
                  {t('settings:aiProvider.controlPlane.contractFailures')}
                </p>
                <ul className="mt-1 space-y-1">
                  {externalMcpSmokeFailures.map((row) => (
                    <li key={row.server}>
                      {row.server}: {[
                        formatRuntimeDiagnosticValue(t, row.status),
                        formatRuntimeDiagnosticValue(t, row.failure_stage),
                        formatRuntimeDiagnosticValue(t, row.failure_kind)
                      ].filter(Boolean).join(' / ')}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-md border border-border bg-background p-3">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground">
              {t('settings:aiProvider.controlPlane.fallbackTitle')}
            </h4>
            <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              <div>
                <dt>{t('settings:aiProvider.controlPlane.selectedRuntime')}</dt>
                <dd className="font-medium text-foreground">{fallbackSelected}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.runnerCandidates')}</dt>
                <dd className="font-medium text-foreground">{runnerCandidates}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.missingCapabilities')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(fallbackRow?.missing_capabilities)}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.compatibleFallbacks')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(fallbackRow?.compatible_fallbacks)}
                </dd>
              </div>
            </dl>
          </div>

          <div className="rounded-md border border-border bg-background p-3">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground">
              {t('settings:aiProvider.controlPlane.subagentsTitle')}
            </h4>
            <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              <div>
                <dt>{t('settings:aiProvider.controlPlane.subagentStrategy')}</dt>
                <dd className="font-medium text-foreground">{subagentStrategy}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.subagentAvailability')}</dt>
                <dd className="font-medium text-foreground">{subagentAvailability}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.mergePolicy')}</dt>
                <dd className="font-medium text-foreground">{subagentMergePolicy}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.maxAttempts')}</dt>
                <dd className="font-medium text-foreground">{subagentMaxAttempts}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.missingCapabilities')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(subagentRow?.missing_capabilities)}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.controlPlane.requiredCapabilities')}</dt>
                <dd className="font-medium text-foreground">
                  {formatControlPlaneList(subagentRow?.required_capabilities)}
                </dd>
              </div>
              {mutatingSubagentPolicyRows.map((row) => (
                <div key={row.labelKey} className="sm:col-span-2">
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="rounded-md border border-border bg-background p-3 xl:col-span-3">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground">
              {t('settings:aiProvider.controlPlane.policyTitle')}
            </h4>
            <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              {runtimePolicyRows.map((row) => (
                <div key={row.labelKey}>
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
              {runtimeCapabilityRows.map((row) => (
                <div key={row.labelKey} className="sm:col-span-2">
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="break-words font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
              {runtimeEvalRows.map((row) => (
                <div key={row.labelKey}>
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
              {runtimeEvalHistoryRows.map((row) => (
                <div key={row.labelKey}>
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="break-words font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
              {runtimeComparativeEvalRows.map((row) => (
                <div key={row.labelKey} className="sm:col-span-2">
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="break-words font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
              {cliRunnerContractRows.map((row) => (
                <div key={row.labelKey} className="sm:col-span-2">
                  <dt>{t(row.labelKey)}</dt>
                  <dd className="break-words font-medium text-foreground">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      );
    } else {
      controlPlaneContent = (
        <p className="max-w-xl rounded-md border border-border bg-background p-3 text-xs text-muted-foreground">
          {t('settings:aiProvider.controlPlane.unavailable')}
        </p>
      );
    }

    return (
      <div className="space-y-3 border-t border-border pt-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-2">
            <Activity className="mt-0.5 h-4 w-4 text-muted-foreground" />
            <div>
              <h3 className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.controlPlane.title')}
              </h3>
              <p className="text-xs text-muted-foreground">
                {t('settings:aiProvider.controlPlane.description')}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="h-8 gap-2 self-start text-xs"
              onClick={runExternalMcpSmokeCheck}
              disabled={externalMcpSmokeLoading}
            >
              <ShieldCheck className={`h-3.5 w-3.5 ${
                externalMcpSmokeLoading ? 'animate-pulse' : ''
              }`}
              />
              {externalMcpSmokeLoading
                ? t('settings:aiProvider.controlPlane.testingContracts')
                : t('settings:aiProvider.controlPlane.testContracts')}
            </Button>
            <Button
              variant="outline"
              className="h-8 gap-2 self-start text-xs"
              onClick={loadRuntimeControlPlaneDiagnostics}
              disabled={runtimeControlPlaneLoading}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${
                runtimeControlPlaneLoading ? 'animate-spin' : ''
              }`}
              />
              {t('settings:aiProvider.controlPlane.refresh')}
            </Button>
          </div>
        </div>

        {controlPlaneContent}
      </div>
    );
  };

  const renderCostPanel = () => (
    <div className="space-y-3 border-t border-border pt-4">
      <div className="flex items-start gap-2">
        <DollarSign className="mt-0.5 h-4 w-4 text-muted-foreground" />
        <div>
          <h3 className="text-sm font-medium text-foreground">
            {t('settings:aiProvider.cost.title')}
          </h3>
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.cost.description')}
          </p>
        </div>
      </div>
      <div className="max-w-xl rounded-md border border-border bg-background p-3">
        {costInfo.isLocal ? (
          <div className="flex items-start gap-2 text-sm">
            <CircleSlash className="mt-0.5 h-4 w-4 text-success" />
            <div>
              <p className="font-medium text-foreground">
                {t('settings:aiProvider.cost.localTitle', { model: costInfo.model })}
              </p>
              <p className="text-xs text-muted-foreground">
                {t('settings:aiProvider.cost.localDescription')}
              </p>
            </div>
          </div>
        ) : costInfo.estimate ? (
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">
                {t('settings:aiProvider.cost.referenceEstimate')}
              </span>
              <span className="font-semibold text-foreground">
                {costInfo.estimate.formatted}
              </span>
            </div>
            <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              <div>
                <dt>{t('settings:aiProvider.cost.modelLabel')}</dt>
                <dd className="font-medium text-foreground">{costInfo.model}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.cost.pricingModelLabel')}</dt>
                <dd className="font-medium text-foreground">{costInfo.pricingModel}</dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.cost.inputLabel')}</dt>
                <dd className="font-medium text-foreground">
                  {t('settings:aiProvider.cost.perMillion', {
                    amount: costInfo.estimate.pricing.inputPerMillion.toFixed(2)
                  })}
                </dd>
              </div>
              <div>
                <dt>{t('settings:aiProvider.cost.outputLabel')}</dt>
                <dd className="font-medium text-foreground">
                  {t('settings:aiProvider.cost.perMillion', {
                    amount: costInfo.estimate.pricing.outputPerMillion.toFixed(2)
                  })}
                </dd>
              </div>
            </dl>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.cost.referenceTokens', {
                input: COST_ESTIMATE_INPUT_TOKENS.toLocaleString(),
                output: COST_ESTIMATE_OUTPUT_TOKENS.toLocaleString()
              })}
            </p>
          </div>
        ) : (
          <div className="flex items-start gap-2 text-sm">
            <Info className="mt-0.5 h-4 w-4 text-muted-foreground" />
            <div>
              <p className="font-medium text-foreground">
                {t('settings:aiProvider.cost.pricingUnavailableTitle', {
                  model: costInfo.model
                })}
              </p>
              <p className="text-xs text-muted-foreground">
                {t('settings:aiProvider.cost.pricingUnavailableDescription')}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderConnectionTestStatus = () => {
    if (!connectionTestStatus) {
      return null;
    }

    const isSuccess = connectionTestStatus.success;
    const Icon = isSuccess ? CheckCircle2 : AlertTriangle;
    const runtimeDiagnostics = hasRuntimeDiagnostics(connectionTestStatus.runtimeDiagnostics)
      ? connectionTestStatus.runtimeDiagnostics
      : null;
    const smokeScope = runtimeDiagnostics?.smokeScope === 'text_completion_only'
      ? t('settings:aiProvider.connectionTest.textCompletionOnly')
      : formatRuntimeDiagnosticValue(t, runtimeDiagnostics?.smokeScope);
    const contractHealth = runtimeDiagnostics?.providerContractHealth;
    const contractHealthStatus = formatRuntimeDiagnosticValue(t, contractHealth?.status);
    const contractHealthReason = formatRuntimeDiagnosticValue(t, contractHealth?.reason);
    const contractHealthMessage = contractHealth?.message?.trim();
    const requestedRuntime = formatRuntimeDiagnosticValue(t, runtimeDiagnostics?.requestedRuntimeMode);
    const validatedRuntime = formatRuntimeDiagnosticValue(t, runtimeDiagnostics?.validatedRuntimeMode);
    const validatedScope = formatRuntimeDiagnosticList(t, runtimeDiagnostics?.validatedRequirements);
    const requestedCapabilities = formatRuntimeDiagnosticList(t, runtimeDiagnostics?.requestedRuntimeCapabilities);
    const validatedCapabilities = formatRuntimeDiagnosticList(t, runtimeDiagnostics?.validatedRuntimeCapabilities);
    const validatedMissingCapabilities = formatRuntimeDiagnosticList(
      t,
      runtimeDiagnostics?.validatedRuntimeMissingCapabilities
    );
    const validatedExecution = runtimeDiagnostics?.validatedRuntimeExecution ?? null;
    const validatedExecutionLoop = formatRuntimeDiagnosticValue(t, validatedExecution?.loop);
    const validatedExecutionStatus = formatRuntimeDiagnosticValue(t, validatedExecution?.status);
    const validatedExecutionStopReason = formatRuntimeDiagnosticValue(
      t,
      validatedExecution?.stopReason
    );
    const toolLoopContract = validatedExecution?.toolLoopContract;
    const toolLoopContractStatus = formatRuntimeDiagnosticValue(t, toolLoopContract?.status);
    const toolLoopCallSupport = formatRuntimeDiagnosticValue(t, toolLoopContract?.toolCallSupport);
    const toolLoopResultSupport = formatRuntimeDiagnosticValue(t, toolLoopContract?.toolResultSupport);
    const toolLoopFallback = formatRuntimeDiagnosticValue(t, toolLoopContract?.fallback);
    const toolLoopFallbackReason = formatRuntimeDiagnosticValue(t, toolLoopContract?.fallbackReason);
    const toolLoopRecoveryStatus = formatRuntimeDiagnosticValue(t, toolLoopContract?.recoveryStatus);
    const toolLoopBlockingReason = formatRuntimeDiagnosticValue(t, toolLoopContract?.blockingReason);
    const resumePolicy = validatedExecution?.resumePolicy;
    const resumePolicyRows = buildProviderResumePolicyDiagnosticRows(t, resumePolicy);
    const transactionBatchContract = validatedExecution?.transactionBatchContract;
    const transactionBatchRows = buildProviderTransactionBatchDiagnosticRows(
      t,
      transactionBatchContract
    );
    const miniPipeline = runtimeDiagnostics?.miniPipeline ?? null;
    const miniPipelineStatus = formatRuntimeDiagnosticValue(t, miniPipeline?.status);
    const miniPipelineReason = formatRuntimeDiagnosticValue(t, miniPipeline?.reason);
    const miniPipelinePhases = miniPipeline?.phases
      ?.map((phase) => {
        const name = formatRuntimeDiagnosticValue(t, phase.name);
        const status = formatRuntimeDiagnosticValue(t, phase.status);
        return name && status ? `${name}: ${status}` : name || status;
      })
      .filter(Boolean)
      .join(', ');
    const miniPipelineChangedFiles = miniPipeline?.changedFiles?.join(', ');
    const providerE2eRows = buildProviderE2eSuiteDiagnosticRows(
      t,
      runtimeDiagnostics?.providerE2eSuite
    );
    const providerNegativeFixtureRows = buildProviderNegativeFixtureDiagnosticRows(
      t,
      runtimeDiagnostics?.providerNegativeFixtures
    );
    const providerLiveFaultProbeRows = buildProviderLiveFaultProbeDiagnosticRows(
      t,
      runtimeDiagnostics?.providerLiveFaultProbes
    );
    const providerRunHistoryRows = buildProviderRunHistoryDiagnosticRows(
      t,
      runtimeDiagnostics?.providerRunHistory
    );
    const reliabilityRows = buildProviderReliabilityDiagnosticRows(
      t,
      runtimeDiagnostics?.providerReliability
    );
    const validatedNativeFallback = validatedExecution?.nativeToolFallbacks?.[0];
    const validatedNativeFallbackReason = formatRuntimeDiagnosticValue(
      t,
      validatedNativeFallback?.reason
    );
    const validatedExecutionToolCounts = validatedExecution?.toolCounts
      ? Object.entries(validatedExecution.toolCounts)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([tool, count]) => `${formatRuntimeDiagnosticValue(t, tool)} x ${count}`)
        .join(', ')
      : null;
    const missingFullAutonomous = formatRuntimeDiagnosticList(
      t,
      runtimeDiagnostics?.fullAutonomousMissingCapabilities
    );
    return (
      <div className={`max-w-xl rounded-md border p-3 text-sm ${
        isSuccess
          ? 'border-success/30 bg-success/10'
          : 'border-destructive/30 bg-destructive/10'
      }`}
      >
        <div className={`flex items-start gap-2 ${isSuccess ? 'text-success' : 'text-destructive'}`}>
          <Icon className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="space-y-1">
            <p className="font-medium">
              {isSuccess
                ? t('settings:aiProvider.connectionTest.success')
                : t('settings:aiProvider.connectionTest.failure')}
            </p>
            <p className="text-xs text-foreground">{connectionTestStatus.message}</p>
          </div>
        </div>
        <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
          <div>
            <dt>{t('settings:aiProvider.connectionTest.provider')}</dt>
            <dd className="font-medium text-foreground">{connectionTestStatus.provider}</dd>
          </div>
          <div>
            <dt>{t('settings:aiProvider.connectionTest.model')}</dt>
            <dd className="font-medium text-foreground">
              {connectionTestStatus.model ?? t('settings:aiProvider.connectionTest.defaultModel')}
            </dd>
          </div>
          <div>
            <dt>{t('settings:aiProvider.connectionTest.runtime')}</dt>
            <dd className="font-medium text-foreground">{connectionTestStatus.runtimeMode}</dd>
          </div>
        </dl>
        {runtimeDiagnostics && (
          <div className="mt-3 border-t border-border/70 pt-3 text-xs text-muted-foreground">
            <div className="flex items-start gap-2">
              <Activity className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <div className="space-y-1">
                <p className="font-medium text-foreground">
                  {t('settings:aiProvider.connectionTest.runtimeDiagnostics')}
                </p>
                <p>{t('settings:aiProvider.connectionTest.diagnosticsNote')}</p>
              </div>
            </div>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2">
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.smokeScope')}
                value={smokeScope}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.providerContractHealth')}
                value={contractHealthStatus}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.providerContractReason')}
                value={contractHealthReason}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.providerContractMessage')}
                value={contractHealthMessage}
                breakWords
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.requestedRuntime')}
                value={requestedRuntime}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.validatedRuntime')}
                value={validatedRuntime}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.validatedScope')}
                value={validatedScope}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.requestedCapabilities')}
                value={requestedCapabilities}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.validatedCapabilities')}
                value={validatedCapabilities}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.missingValidatedRuntime')}
                value={validatedMissingCapabilities || t('settings:aiProvider.connectionTest.noneMissing')}
              />
              <RuntimeDiagnosticRow
                label={t('settings:aiProvider.connectionTest.missingFullAutonomous')}
                value={missingFullAutonomous || t('settings:aiProvider.connectionTest.noneMissing')}
              />
              {providerE2eRows.map((row) => (
                <RuntimeDiagnosticRow
                  key={row.labelKey}
                  label={t(row.labelKey)}
                  value={row.value}
                />
              ))}
              {providerNegativeFixtureRows.map((row) => (
                <RuntimeDiagnosticRow
                  key={row.labelKey}
                  label={t(row.labelKey)}
                  value={row.value}
                />
              ))}
              {providerLiveFaultProbeRows.map((row) => (
                <RuntimeDiagnosticRow
                  key={`${row.labelKey}-${row.value}`}
                  label={t(row.labelKey)}
                  value={row.value}
                  breakWords
                />
              ))}
              {providerRunHistoryRows.map((row) => (
                <RuntimeDiagnosticRow
                  key={row.labelKey}
                  label={t(row.labelKey)}
                  value={row.value}
                  breakWords={row.labelKey === 'settings:aiProvider.connectionTest.providerRunHistoryPath'}
                />
              ))}
              {reliabilityRows.map((row) => (
                <RuntimeDiagnosticRow
                  key={row.labelKey}
                  label={t(row.labelKey)}
                  value={row.value}
                />
              ))}
              {miniPipeline && (
                <>
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelineStatus')}
                    value={miniPipelineStatus}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelineTask')}
                    value={miniPipeline.task}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelinePhases')}
                    value={miniPipelinePhases}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelineTestCommand')}
                    value={miniPipeline.testCommand}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelineTestExitCode')}
                    value={typeof miniPipeline.testExitCode === 'number' ? miniPipeline.testExitCode : null}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelineChangedFiles')}
                    value={miniPipelineChangedFiles}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.pipelineReason')}
                    value={miniPipelineReason}
                  />
                </>
              )}
              {validatedExecution && (
                <>
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionLoop')}
                    value={validatedExecutionLoop}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionStatus')}
                    value={validatedExecutionStatus}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionStopReason')}
                    value={validatedExecutionStopReason}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolLoopContract')}
                    value={toolLoopContractStatus}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolCallSupport')}
                    value={toolLoopCallSupport}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolResultSupport')}
                    value={toolLoopResultSupport}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolLoopFallback')}
                    value={toolLoopFallback}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolLoopFallbackReason')}
                    value={toolLoopFallbackReason}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolLoopRecovery')}
                    value={toolLoopRecoveryStatus}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.toolLoopBlockingReason')}
                    value={toolLoopBlockingReason}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionActions')}
                    value={typeof validatedExecution.actionCount === 'number' ? validatedExecution.actionCount : null}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionFailures')}
                    value={typeof validatedExecution.failedActionCount === 'number' ? validatedExecution.failedActionCount : null}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionNativeFallbacks')}
                    value={typeof validatedExecution.nativeToolFallbackCount === 'number' ? validatedExecution.nativeToolFallbackCount : null}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionNativeFallbackReason')}
                    value={validatedNativeFallbackReason}
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionNativeFallbackMessage')}
                    value={validatedNativeFallback?.message}
                    breakWords
                  />
                  <RuntimeDiagnosticRow
                    label={t('settings:aiProvider.connectionTest.executionTools')}
                    value={validatedExecutionToolCounts}
                  />
                  {resumePolicyRows.map((row) => (
                    <RuntimeDiagnosticRow
                      key={row.labelKey}
                      label={t(row.labelKey)}
                      value={row.value}
                    />
                  ))}
                  {transactionBatchRows.map((row) => (
                    <RuntimeDiagnosticRow
                      key={row.labelKey}
                      label={t(row.labelKey)}
                      value={row.value}
                    />
                  ))}
                </>
              )}
            </dl>
          </div>
        )}
        {connectionTestStatus.responseExcerpt && (
          <p className="mt-3 rounded-md bg-background/80 p-2 text-xs text-foreground">
            {connectionTestStatus.responseExcerpt}
          </p>
        )}
        {connectionTestStatus.errorDetails && (
          <p className="mt-3 rounded-md bg-background/80 p-2 text-xs text-destructive">
            {connectionTestStatus.errorDetails}
          </p>
        )}
      </div>
    );
  };

  const renderProviderConfiguration = () => {
    switch (config.provider) {
      case 'codex':
        return (
          <ProviderField
            id="codexModel"
            label={t('settings:aiProvider.providerModels.codex.label')}
            description={t('settings:aiProvider.providerModels.codex.description')}
            placeholder={t('settings:aiProvider.providerModels.codex.placeholder')}
            value={config.codexModel ?? ''}
            onChange={(codexModel) => updateConfig({ codexModel })}
          />
        );
      case 'openai':
        return (
          <>
            <ProviderField
              id="openaiApiKey"
              label={t('settings:aiProvider.apiKeys.openai.label')}
              description={t('settings:aiProvider.apiKeys.openai.description')}
              placeholder={t('settings:aiProvider.apiKeys.openai.placeholder')}
              type="password"
              value={config.openaiApiKey ?? ''}
              onChange={(openaiApiKey) => updateConfig({ openaiApiKey })}
            />
            <ProviderField
              id="openaiModel"
              label={t('settings:aiProvider.providerModels.openai.label')}
              description={t('settings:aiProvider.providerModels.openai.description')}
              placeholder={t('settings:aiProvider.providerModels.openai.placeholder')}
              value={config.openaiModel ?? ''}
              onChange={(openaiModel) => updateConfig({ openaiModel })}
            />
            <ProviderField
              id="openaiBaseUrl"
              label={t('settings:aiProvider.baseUrls.openai.label')}
              description={t('settings:aiProvider.baseUrls.openai.description')}
              placeholder={t('settings:aiProvider.baseUrls.openai.placeholder')}
              value={config.openaiBaseUrl ?? ''}
              onChange={(openaiBaseUrl) => updateConfig({ openaiBaseUrl })}
            />
          </>
        );
      case 'google':
        return (
          <>
            <ProviderField
              id="googleApiKey"
              label={t('settings:aiProvider.apiKeys.google.label')}
              description={t('settings:aiProvider.apiKeys.google.description')}
              placeholder={t('settings:aiProvider.apiKeys.google.placeholder')}
              type="password"
              value={config.googleApiKey ?? ''}
              onChange={(googleApiKey) => updateConfig({ googleApiKey })}
            />
            <ProviderField
              id="googleModel"
              label={t('settings:aiProvider.providerModels.google.label')}
              description={t('settings:aiProvider.providerModels.google.description')}
              placeholder={t('settings:aiProvider.providerModels.google.placeholder')}
              value={config.googleModel ?? ''}
              onChange={(googleModel) => updateConfig({ googleModel })}
            />
          </>
        );
      case 'litellm':
        return (
          <>
            <ProviderField
              id="litellmModel"
              label={t('settings:aiProvider.providerModels.litellm.label')}
              description={t('settings:aiProvider.providerModels.litellm.description')}
              placeholder={t('settings:aiProvider.providerModels.litellm.placeholder')}
              value={config.litellmModel ?? ''}
              onChange={(litellmModel) => updateConfig({ litellmModel })}
            />
            <ProviderField
              id="litellmApiBase"
              label={t('settings:aiProvider.baseUrls.litellm.label')}
              description={t('settings:aiProvider.baseUrls.litellm.description')}
              placeholder={t('settings:aiProvider.baseUrls.litellm.placeholder')}
              value={config.litellmApiBase ?? ''}
              onChange={(litellmApiBase) => updateConfig({ litellmApiBase })}
            />
            <ProviderField
              id="litellmApiKey"
              label={t('settings:aiProvider.apiKeys.litellm.label')}
              description={t('settings:aiProvider.apiKeys.litellm.description')}
              placeholder={t('settings:aiProvider.apiKeys.litellm.placeholder')}
              type="password"
              value={config.litellmApiKey ?? ''}
              onChange={(litellmApiKey) => updateConfig({ litellmApiKey })}
            />
          </>
        );
      case 'openrouter':
        return (
          <>
            <ProviderField
              id="openrouterApiKey"
              label={t('settings:aiProvider.apiKeys.openrouter.label')}
              description={t('settings:aiProvider.apiKeys.openrouter.description')}
              placeholder={t('settings:aiProvider.apiKeys.openrouter.placeholder')}
              type="password"
              value={config.openrouterApiKey ?? ''}
              onChange={(openrouterApiKey) => updateConfig({ openrouterApiKey })}
            />
            <ProviderField
              id="openrouterModel"
              label={t('settings:aiProvider.providerModels.openrouter.label')}
              description={t('settings:aiProvider.providerModels.openrouter.description')}
              placeholder={t('settings:aiProvider.providerModels.openrouter.placeholder')}
              value={config.openrouterModel ?? ''}
              onChange={(openrouterModel) => updateConfig({ openrouterModel })}
            />
            <ProviderField
              id="openrouterBaseUrl"
              label={t('settings:aiProvider.baseUrls.openrouter.label')}
              description={t('settings:aiProvider.baseUrls.openrouter.description')}
              placeholder={t('settings:aiProvider.baseUrls.openrouter.placeholder')}
              value={config.openrouterBaseUrl ?? ''}
              onChange={(openrouterBaseUrl) => updateConfig({ openrouterBaseUrl })}
            />
          </>
        );
      case 'zhipuai':
        return (
          <>
            <ProviderField
              id="zhipuaiApiKey"
              label={t('settings:aiProvider.apiKeys.zhipuai.label')}
              description={t('settings:aiProvider.apiKeys.zhipuai.description')}
              placeholder={t('settings:aiProvider.apiKeys.zhipuai.placeholder')}
              type="password"
              value={config.zhipuaiApiKey ?? ''}
              onChange={(zhipuaiApiKey) => updateConfig({ zhipuaiApiKey })}
            />
            <ProviderField
              id="zhipuaiModel"
              label={t('settings:aiProvider.providerModels.zhipuai.label')}
              description={t('settings:aiProvider.providerModels.zhipuai.description')}
              placeholder={t('settings:aiProvider.providerModels.zhipuai.placeholder')}
              value={config.zhipuaiModel ?? ''}
              onChange={(zhipuaiModel) => updateConfig({ zhipuaiModel })}
            />
          </>
        );
      case 'ollama':
        return (
          <>
            <ProviderField
              id="ollamaModel"
              label={t('settings:aiProvider.providerModels.ollama.label')}
              description={t('settings:aiProvider.providerModels.ollama.description')}
              placeholder={t('settings:aiProvider.providerModels.ollama.placeholder')}
              value={config.ollamaModel ?? ''}
              onChange={(ollamaModel) => updateConfig({ ollamaModel })}
            />
            <ProviderField
              id="ollamaBaseUrl"
              label={t('settings:aiProvider.baseUrls.ollama.label')}
              description={t('settings:aiProvider.baseUrls.ollama.description')}
              placeholder={t('settings:aiProvider.baseUrls.ollama.placeholder')}
              value={config.ollamaBaseUrl ?? ''}
              onChange={(ollamaBaseUrl) => updateConfig({ ollamaBaseUrl })}
            />
          </>
        );
      default:
        return (
          <ProviderField
            id="claudeModel"
            label={t('settings:aiProvider.providerModels.claude.label')}
            description={t('settings:aiProvider.providerModels.claude.description')}
            placeholder={t('settings:aiProvider.providerModels.claude.placeholder')}
            value={config.claudeModel ?? ''}
            onChange={(claudeModel) => updateConfig({ claudeModel })}
          />
        );
    }
  };

  return (
    <SettingsSection
      title={t('settings:aiProvider.title')}
      description={t('settings:aiProvider.description')}
    >
      <div className="space-y-6">
        <div className="space-y-3">
          <Label htmlFor="aiProvider" className="text-sm font-medium text-foreground">
            {t('settings:aiProvider.label')}
          </Label>
          <Select
            value={config.provider}
            onValueChange={(value) => handleProviderChange(value as AIEngineProvider)}
            disabled={loading}
          >
            <SelectTrigger id="aiProvider" className="w-full max-w-xl">
              <SelectValue placeholder={t('settings:aiProvider.selectProvider')} />
            </SelectTrigger>
            <SelectContent>
              {PROVIDER_OPTIONS.map((provider) => (
                <SelectItem key={provider.value} value={provider.value}>
                  <div className="flex flex-col items-start">
                    <span className="font-medium">{t(provider.labelKey)}</span>
                    <span className="text-xs text-muted-foreground">{t(provider.descriptionKey)}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.hints.envOverride')}
          </p>
        </div>

        <div className="rounded-md border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            {nonClaudeFullAutonomous ? (
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            ) : (
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <div className="space-y-1">
              <h3 className="text-sm font-medium text-foreground">
                {t(selectedProvider.labelKey)}
              </h3>
              <p className="text-xs text-muted-foreground">
                {t(compatibilityMessageKey)}
              </p>
            </div>
          </div>
        </div>

        {renderCapabilityMatrix()}

        {renderRuntimeControlPlane()}

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.runtime.title')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.runtime.description')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="runtimeMode" className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.runtime.globalLabel')}
            </Label>
            {renderRuntimeSelect(
              'runtimeMode',
              activeRuntimeMode,
              (runtimeMode) => updateConfig({ runtimeMode: runtimeMode as AgentRuntimeMode }),
              false
            )}
          </div>

          <div className="flex max-w-xl items-start gap-3 rounded-md border border-border bg-background p-3">
            <Switch
              id="runtimeFallbackEnabled"
              checked={runtimeFallbackEnabled}
              onCheckedChange={(runtimeFallbackEnabled) =>
                updateConfig({ runtimeFallbackEnabled })
              }
              disabled={loading}
            />
            <div className="space-y-1">
              <Label htmlFor="runtimeFallbackEnabled" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.fallbackLabel')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('settings:aiProvider.runtime.fallbackDescription')}
              </p>
            </div>
          </div>

          <div className="flex max-w-xl items-start gap-3 rounded-md border border-border bg-background p-3">
            <Switch
              id="cliRunnerRouterEnabled"
              checked={cliRunnerRouterEnabled}
              onCheckedChange={(cliRunnerRouterEnabled) =>
                updateConfig({ cliRunnerRouterEnabled })
              }
              disabled={loading}
            />
            <div className="space-y-1">
              <Label htmlFor="cliRunnerRouterEnabled" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.runnerRouterLabel')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('settings:aiProvider.runtime.runnerRouterDescription')}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="plannerRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.plannerLabel')}
              </Label>
              {renderRuntimeSelect(
                'plannerRuntimeMode',
                config.plannerRuntimeMode,
                (value) => handleRuntimeOverrideChange('plannerRuntimeMode', value),
                true
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="coderRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.coderLabel')}
              </Label>
              {renderRuntimeSelect(
                'coderRuntimeMode',
                config.coderRuntimeMode,
                (value) => handleRuntimeOverrideChange('coderRuntimeMode', value),
                true
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="qaReviewerRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.qaReviewerLabel')}
              </Label>
              {renderRuntimeSelect(
                'qaReviewerRuntimeMode',
                config.qaReviewerRuntimeMode,
                (value) => handleRuntimeOverrideChange('qaReviewerRuntimeMode', value),
                true
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="qaFixerRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.qaFixerLabel')}
              </Label>
              {renderRuntimeSelect(
                'qaFixerRuntimeMode',
                config.qaFixerRuntimeMode,
                (value) => handleRuntimeOverrideChange('qaFixerRuntimeMode', value),
                true
              )}
            </div>
          </div>

          {runtimeNoticeKey && (
            <div className="flex max-w-xl items-start gap-2 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{t(runtimeNoticeKey)}</p>
            </div>
          )}
        </div>

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.configuration.title')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.configuration.description')}
            </p>
          </div>
          {renderProviderConfiguration()}
        </div>

        {renderCostPanel()}

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.models.title')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.models.description')}
            </p>
          </div>
          <ProviderField
            id="plannerModel"
            label={t('settings:aiProvider.models.planner.label')}
            description={t('settings:aiProvider.models.planner.description')}
            placeholder={t('settings:aiProvider.models.planner.placeholder')}
            value={config.plannerModel ?? ''}
            onChange={(plannerModel) => updateConfig({ plannerModel })}
          />
          <ProviderField
            id="coderModel"
            label={t('settings:aiProvider.models.coder.label')}
            description={t('settings:aiProvider.models.coder.description')}
            placeholder={t('settings:aiProvider.models.coder.placeholder')}
            value={config.coderModel ?? ''}
            onChange={(coderModel) => updateConfig({ coderModel })}
          />
          <ProviderField
            id="qaModel"
            label={t('settings:aiProvider.models.qa.label')}
            description={t('settings:aiProvider.models.qa.description')}
            placeholder={t('settings:aiProvider.models.qa.placeholder')}
            value={config.qaModel ?? ''}
            onChange={(qaModel) => updateConfig({ qaModel })}
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? t('common:buttons.saving') : t('common:buttons.save')}
          </Button>
          <Button
            variant="outline"
            onClick={handleValidate}
            disabled={saving || validating || testingProvider || testingPipeline || loading}
          >
            {validating
              ? t('settings:aiProvider.validation.validating')
              : t('settings:aiProvider.validation.action')}
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => runProviderSmokeTest()}
            disabled={saving || validating || testingProvider || testingPipeline || loading}
          >
            <Activity className="h-4 w-4" />
            {testingProvider
              ? t('settings:aiProvider.connectionTest.testing')
              : t('settings:aiProvider.connectionTest.action')}
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => runProviderSmokeTest('mini_pipeline')}
            disabled={saving || validating || testingProvider || testingPipeline || loading}
          >
            <ShieldCheck className="h-4 w-4" />
            {testingPipeline
              ? t('settings:aiProvider.connectionTest.pipelineTesting')
              : t('settings:aiProvider.connectionTest.pipelineAction')}
          </Button>
          {saveStatus === 'success' && (
            <span className="inline-flex items-center gap-1.5 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              {t('common:labels.success')}
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="inline-flex items-center gap-1.5 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              {t('common:labels.error')}
            </span>
          )}
        </div>
        {validationStatus && (
          <div className="max-w-xl rounded-md border border-border bg-muted/30 p-3 text-sm">
            {validationStatus.isValid ? (
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="h-4 w-4" />
                {t('settings:aiProvider.validation.valid')}
              </div>
            ) : (
              <div className="space-y-2 text-destructive">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  {t('settings:aiProvider.validation.invalid')}
                </div>
                <ul className="list-disc space-y-1 pl-5">
                  {validationStatus.errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
            {validationStatus.availableProviders.length > 0 && (
              <p className="mt-2 text-xs text-muted-foreground">
                {t('settings:aiProvider.validation.availableProviders', {
                  providers: validationStatus.availableProviders.join(', ')
                })}
              </p>
            )}
          </div>
        )}
        {renderConnectionTestStatus()}
      </div>
    </SettingsSection>
  );
}
