import { ipcMain, dialog, app, shell } from 'electron';
import { existsSync, writeFileSync, mkdirSync, statSync, readFileSync } from 'fs';
import { execFile, execFileSync } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'path';
import { fileURLToPath } from 'url';
import { is } from '@electron-toolkit/utils';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
import { IPC_CHANNELS, DEFAULT_APP_SETTINGS, DEFAULT_AGENT_PROFILES } from '../../shared/constants';
import type {
  AppSettings,
  IPCResult,
  SourceEnvConfig,
  SourceEnvCheckResult,
  ProviderSettings,
  AIEngineProvider,
  AgentRuntimeMode,
  ProviderConnectionTestResult,
  ProviderRuntimeDiagnostics,
  RuntimeExternalMcpSmokeResult,
  RuntimeControlPlaneDiagnostics
} from '../../shared/types';
import { AgentManager } from '../agent';
import type { BrowserWindow } from 'electron';
import { setUpdateChannel, setUpdateChannelWithDowngradeCheck } from '../app-updater';
import { getSettingsPath, readSettingsFile } from '../settings-utils';
import { configureTools, getToolPath, getToolInfo, isPathFromWrongPlatform, preWarmToolCache } from '../cli-tool-manager';
import { parseEnvFile } from './utils';
import { getCurrentOS, isMacOS, isWindows } from '../platform';
import { projectStore } from '../project-store';
import { getBestAvailableProfileEnv } from '../rate-limit-detector';
import { getAPIProfileEnv } from '../services/profile';
import { getCodexProfileManager } from '../codex-profile-manager';
import {
  mapProviderContractHealth,
  mapProviderE2eSuite,
  mapProviderNegativeFixtures,
  mapProviderReliability,
  mapProviderRunHistory,
  mapProviderRuntimeResumePolicy,
  mapProviderTransactionBatchContract,
  mapProviderToolLoopContract,
} from './provider-smoke-diagnostics';
import { resolveProviderSmokeRuntime } from './provider-smoke-runtime';

const settingsPath = getSettingsPath();
const execFileAsync = promisify(execFile);
const PROVIDER_SMOKE_TIMEOUT_SECONDS = 30;
const PROVIDER_SMOKE_PROCESS_TIMEOUT_MS = 45_000;
const RUNTIME_DIAGNOSTICS_PROCESS_TIMEOUT_MS = 45_000;
const EXTERNAL_MCP_SMOKE_PROCESS_TIMEOUT_MS = 90_000;

function hasClaudeProviderAuth(vars: Record<string, string>): boolean {
  return Boolean(
    vars['ANTHROPIC_API_KEY'] ||
    vars['ANTHROPIC_AUTH_TOKEN'] ||
    vars['CLAUDE_CODE_OAUTH_TOKEN'] ||
    vars['CLAUDE_CONFIG_DIR']
  );
}

function hasCodexProviderAuth(vars: Record<string, string>): boolean {
  return Boolean(vars['CODEX_HOME']);
}

/**
 * Auto-detect the auto-claude source path relative to the app location.
 * Works across platforms (macOS, Windows, Linux) in both dev and production modes.
 */
const detectAutoBuildSourcePath = (): string | null => {
  const possiblePaths: string[] = [];

  // Development mode paths
  if (is.dev) {
    // In dev, __dirname is typically apps/frontend/out/main
    // We need to go up to find apps/backend
    possiblePaths.push(
      path.resolve(__dirname, '..', '..', '..', 'backend'),      // From out/main -> apps/backend
      path.resolve(process.cwd(), 'apps', 'backend')             // From cwd (repo root)
    );
  } else {
    // Production mode paths (packaged app)
    // The backend is bundled as extraResources/backend
    // On all platforms, it should be at process.resourcesPath/backend
    possiblePaths.push(
      path.resolve(process.resourcesPath, 'backend')             // Primary: extraResources/backend
    );
    // Fallback paths for different app structures
    const appPath = app.getAppPath();
    possiblePaths.push(
      path.resolve(appPath, '..', 'backend'),                    // Sibling to asar
      path.resolve(appPath, '..', '..', 'Resources', 'backend')  // macOS bundle structure
    );
  }

  // Add process.cwd() as last resort on all platforms
  possiblePaths.push(path.resolve(process.cwd(), 'apps', 'backend'));

  // Enable debug logging with DEBUG=1
  const debug = process.env.DEBUG === '1' || process.env.DEBUG === 'true';

  if (debug) {
    console.warn('[detectAutoBuildSourcePath] Platform:', getCurrentOS());
    console.warn('[detectAutoBuildSourcePath] Is dev:', is.dev);
    console.warn('[detectAutoBuildSourcePath] __dirname:', __dirname);
    console.warn('[detectAutoBuildSourcePath] app.getAppPath():', app.getAppPath());
    console.warn('[detectAutoBuildSourcePath] process.cwd():', process.cwd());
    console.warn('[detectAutoBuildSourcePath] Checking paths:', possiblePaths);
  }

  for (const p of possiblePaths) {
    // Use runners/spec_runner.py as marker - this is the file actually needed for task execution
    // This prevents matching legacy 'auto-claude/' directories that don't have the runners
    const markerPath = path.join(p, 'runners', 'spec_runner.py');
    const exists = existsSync(p) && existsSync(markerPath);

    if (debug) {
      console.warn(`[detectAutoBuildSourcePath] Checking ${p}: ${exists ? '✓ FOUND' : '✗ not found'}`);
    }

    if (exists) {
      console.warn(`[detectAutoBuildSourcePath] Auto-detected source path: ${p}`);
      return p;
    }
  }

  console.warn('[detectAutoBuildSourcePath] Could not auto-detect Auto Code source path. Please configure manually in settings.');
  console.warn('[detectAutoBuildSourcePath] Set DEBUG=1 environment variable for detailed path checking.');
  return null;
};

/**
 * Apply ProviderSettings fields onto an existing env vars map.
 * Sets or deletes keys based on whether values are truthy.
 */
function applyProviderSettingsToVars(
  vars: Record<string, string>,
  settings: ProviderSettings
): void {
  if (settings.provider !== undefined) {
    vars['AI_ENGINE_PROVIDER'] = settings.provider;
  }
  const keyMap: Array<[keyof ProviderSettings, string]> = [
    ['codexModel', 'CODEX_MODEL'],
    ['openaiApiKey', 'OPENAI_API_KEY'],
    ['googleApiKey', 'GOOGLE_API_KEY'],
    ['openrouterApiKey', 'OPENROUTER_API_KEY'],
    ['zhipuaiApiKey', 'ZHIPUAI_API_KEY'],
    ['plannerModel', 'AGENT_MODEL_PLANNER'],
    ['coderModel', 'AGENT_MODEL_CODER'],
    ['qaModel', 'AGENT_MODEL_QA_REVIEWER'],
    ['runtimeMode', 'AUTO_CODE_RUNTIME_MODE'],
    ['plannerRuntimeMode', 'AGENT_RUNTIME_MODE_PLANNER'],
    ['coderRuntimeMode', 'AGENT_RUNTIME_MODE_CODER'],
    ['qaReviewerRuntimeMode', 'AGENT_RUNTIME_MODE_QA_REVIEWER'],
    ['qaFixerRuntimeMode', 'AGENT_RUNTIME_MODE_QA_FIXER'],
  ];
  for (const [settingKey, envKey] of keyMap) {
    const value = settings[settingKey];
    if (value !== undefined) {
      vars[envKey] = value as string;
    }
  }
  if (settings.runtimeFallbackEnabled !== undefined) {
    vars['AUTO_CODE_RUNTIME_FALLBACK'] = settings.runtimeFallbackEnabled
      ? 'true'
      : 'false';
  }
  if (settings.cliRunnerRouterEnabled !== undefined) {
    vars['AUTO_CODE_CLI_RUNNER_ROUTER'] = settings.cliRunnerRouterEnabled
      ? 'true'
      : 'false';
  }
}

/**
 * Read existing .env content safely (returns '' if file not found).
 * Avoids TOCTOU by reading directly and catching ENOENT.
 */
function readEnvFileSafe(envPath: string): string {
  try {
    return readFileSync(envPath, 'utf-8');
  } catch (err: unknown) {
    const code = (err as { code?: string }).code;
    if (code === 'ENOENT') {
      return '';
    }
    throw err;
  }
}

/** Generate minimal .env content for a fresh file */
function generateFreshEnvContent(vars: Record<string, string>): string {
  const varLine = (name: string) =>
    vars[name] ? `${name}=${vars[name]}` : `# ${name}=`;
  return `# Multi-Provider Configuration
AI_ENGINE_PROVIDER=${vars['AI_ENGINE_PROVIDER'] || 'claude'}

# Provider API Keys
${varLine('ANTHROPIC_API_KEY')}
${varLine('OPENAI_API_KEY')}
${varLine('GOOGLE_API_KEY')}
${varLine('LITELLM_API_KEY')}
${varLine('OPENROUTER_API_KEY')}
${varLine('ZHIPUAI_API_KEY')}

# Provider Models and Endpoints
${varLine('CLAUDE_MODEL')}
${varLine('CODEX_MODEL')}
${varLine('CODEX_HOME')}
${varLine('CODEX_CLI_PATH')}
${varLine('OPENAI_MODEL')}
${varLine('OPENAI_BASE_URL')}
${varLine('GOOGLE_MODEL')}
${varLine('LITELLM_MODEL')}
${varLine('LITELLM_API_BASE')}
${varLine('OPENROUTER_MODEL')}
${varLine('OPENROUTER_BASE_URL')}
${varLine('ZHIPUAI_MODEL')}
${varLine('OLLAMA_MODEL')}
${varLine('OLLAMA_BASE_URL')}

# Per-Agent Model Configuration
${varLine('AGENT_MODEL_PLANNER')}
${varLine('AGENT_MODEL_CODER')}
${varLine('AGENT_MODEL_QA_REVIEWER')}

# Runtime Mode Configuration
${varLine('AUTO_CODE_RUNTIME_MODE')}
${varLine('AGENT_RUNTIME_MODE_PLANNER')}
${varLine('AGENT_RUNTIME_MODE_CODER')}
${varLine('AGENT_RUNTIME_MODE_QA_REVIEWER')}
${varLine('AGENT_RUNTIME_MODE_QA_FIXER')}
${varLine('AUTO_CODE_RUNTIME_FALLBACK')}
${varLine('AUTO_CODE_CLI_RUNNER_ROUTER')}
`;
}

/** Collect active (non-commented) variable names from parsed lines */
function collectActiveVarNames(lines: string[]): Set<string> {
  const active = new Set<string>();
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const m = trimmed.match(/^([A-Z_]+)=/);
      if (m) active.add(m[1]);
    }
  }
  return active;
}

/** Transform a single line, substituting updated variable values */
function updateEnvLine(
  line: string,
  vars: Record<string, string>,
  activeVars: Set<string>
): string {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) {
    // Uncomment a commented-out variable if we have a new value and it's not active yet
    const commentMatch = trimmed.match(/^#\s*([A-Z_]+)=/);
    if (commentMatch) {
      const varName = commentMatch[1];
      if (vars[varName] !== undefined && !activeVars.has(varName)) {
        activeVars.add(varName);
        return `${varName}=${vars[varName]}`;
      }
    }
    return line;
  }
  const match = trimmed.match(/^([A-Z_]+)=/);
  if (match && vars[match[1]] !== undefined) {
    return `${match[1]}=${vars[match[1]]}`;
  }
  return line;
}

/**
 * Generate .env file content with updated provider settings
 * Preserves existing file structure and only updates provider-related variables
 */
function generateProviderEnvContent(
  vars: Record<string, string>,
  existingContent: string
): string {
  if (!existingContent) {
    return generateFreshEnvContent(vars);
  }

  const lines = existingContent.split('\n');
  const activeVars = collectActiveVarNames(lines);
  const updatedLines = lines.map(line => updateEnvLine(line, vars, activeVars));

  // Collect all var names that appear (commented or not) in the existing file
  const existingVarNames = new Set(
    lines
      .map(line => { const m = line.trim().match(/^#?\s*([A-Z_]+)=/); return m ? m[1] : null; })
      .filter(Boolean)
  );

  const providerVars = [
    'AI_ENGINE_PROVIDER', 'ANTHROPIC_API_KEY', 'CLAUDE_MODEL',
    'CODEX_MODEL', 'CODEX_HOME', 'CODEX_CLI_PATH',
    'OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_BASE_URL',
    'GOOGLE_API_KEY', 'GOOGLE_MODEL',
    'LITELLM_MODEL', 'LITELLM_API_BASE', 'LITELLM_API_KEY',
    'OPENROUTER_API_KEY', 'OPENROUTER_MODEL', 'OPENROUTER_BASE_URL',
    'ZHIPUAI_API_KEY', 'ZHIPUAI_MODEL', 'OLLAMA_MODEL', 'OLLAMA_BASE_URL',
    'AGENT_MODEL_PLANNER', 'AGENT_MODEL_CODER',
    'AGENT_MODEL_QA_REVIEWER', 'AUTO_CODE_RUNTIME_MODE',
    'AGENT_RUNTIME_MODE_PLANNER', 'AGENT_RUNTIME_MODE_CODER',
    'AGENT_RUNTIME_MODE_QA_REVIEWER', 'AGENT_RUNTIME_MODE_QA_FIXER',
    'AUTO_CODE_RUNTIME_FALLBACK', 'AUTO_CODE_CLI_RUNNER_ROUTER',
  ];
  const newVars = providerVars.filter(v => !existingVarNames.has(v) && vars[v])
    .map(v => `${v}=${vars[v]}`);

  if (newVars.length > 0) {
    updatedLines.push('', '# Provider Settings (added by UI)', ...newVars);
  }

  return updatedLines.join('\n');
}

function collectRuntimeCompatibilityErrors(
  provider: AIEngineProvider,
  vars: Record<string, string>
): string[] {
  const runtimeFallbackEnabled = vars['AUTO_CODE_RUNTIME_FALLBACK'] === 'true';
  const cliRunnerRouterEnabled = vars['AUTO_CODE_CLI_RUNNER_ROUTER'] === 'true';
  if (
    provider === 'claude' ||
    provider === 'codex' ||
    runtimeFallbackEnabled ||
    cliRunnerRouterEnabled
  ) {
    return [];
  }

  const runtimeChecks: Array<[string, AgentRuntimeMode | undefined]> = [
    ['default', (vars['AUTO_CODE_RUNTIME_MODE'] || 'full_autonomous') as AgentRuntimeMode],
    ['planner', vars['AGENT_RUNTIME_MODE_PLANNER'] as AgentRuntimeMode | undefined],
    ['coder', vars['AGENT_RUNTIME_MODE_CODER'] as AgentRuntimeMode | undefined],
    ['QA reviewer', vars['AGENT_RUNTIME_MODE_QA_REVIEWER'] as AgentRuntimeMode | undefined],
    ['QA fixer', vars['AGENT_RUNTIME_MODE_QA_FIXER'] as AgentRuntimeMode | undefined],
  ];

  return runtimeChecks
    .filter(([, mode]) => mode === 'full_autonomous')
    .map(
      ([label]) =>
        `Non-Claude providers cannot use ${label} full_autonomous runtime unless runtime fallback or CLI runner routing is enabled`
    );
}

type ProviderSmokeCliResult = {
  success?: boolean;
  provider?: string;
  model?: string | null;
  runtime_mode?: string;
  message?: string;
  response_excerpt?: string | null;
  error_details?: string | null;
  runtime_diagnostics?: {
    smoke_scope?: string;
    provider_contract_health?: unknown;
    requested_runtime_mode?: string;
    validated_runtime_mode?: string;
    validated_requirements?: string[];
    requested_runtime_capabilities?: string[];
    validated_runtime_capabilities?: string[];
    validated_runtime_missing_capabilities?: string[];
    validated_runtime_execution?: {
      status?: unknown;
      stop_reason?: unknown;
      loop?: unknown;
      action_count?: unknown;
      failed_action_count?: unknown;
      native_tool_fallback_count?: unknown;
      native_tool_fallbacks?: unknown;
      tool_counts?: unknown;
      resume_policy?: unknown;
      tool_loop_contract?: unknown;
      transaction_batch_contract?: unknown;
    } | null;
    mini_pipeline?: {
      status?: unknown;
      task?: unknown;
      test_command?: unknown;
      test_exit_code?: unknown;
      changed_files?: unknown;
      reason?: unknown;
      phases?: unknown;
    } | null;
    provider_e2e_suite?: unknown;
    provider_e2e_negative_fixtures?: unknown;
    provider_run_history?: unknown;
    provider_reliability?: unknown;
    full_autonomous_missing_capabilities?: string[];
    note?: string;
  } | null;
};

type RuntimeModesCliPayload = {
  cli_runner_contract_matrix?: RuntimeControlPlaneDiagnostics['cli_runner_contract_matrix'];
  runtime_fallback_matrix?: RuntimeControlPlaneDiagnostics['runtime_fallback_matrix'];
  mcp_bridge_plan_matrix?: RuntimeControlPlaneDiagnostics['mcp_bridge_plan_matrix'];
  mcp_bridge_permission_matrix?: RuntimeControlPlaneDiagnostics['mcp_bridge_permission_matrix'];
  external_mcp_server_health?: RuntimeControlPlaneDiagnostics['external_mcp_server_health'];
  runtime_subagent_matrix?: RuntimeControlPlaneDiagnostics['runtime_subagent_matrix'];
  runtime_subagent_mutation_policy?: RuntimeControlPlaneDiagnostics['runtime_subagent_mutation_policy'];
  runtime_policy_matrix?: RuntimeControlPlaneDiagnostics['runtime_policy_matrix'];
  runtime_capability_matrix?: RuntimeControlPlaneDiagnostics['runtime_capability_matrix'];
  runtime_eval_matrix?: RuntimeControlPlaneDiagnostics['runtime_eval_matrix'];
  runtime_eval_history?: RuntimeControlPlaneDiagnostics['runtime_eval_history'];
  runtime_comparative_eval_matrix?: RuntimeControlPlaneDiagnostics['runtime_comparative_eval_matrix'];
  recommendations?: Record<string, string>;
};

type ExternalMcpSmokeCliPayload = RuntimeExternalMcpSmokeResult;
type BackendCliCommandMessages = {
  missingRunPy: string;
  noJson: string;
  timedOut: string;
};
type BackendCliCommandError = Error & {
  stdout?: string | Buffer;
  stderr?: string | Buffer;
  killed?: boolean;
  signal?: string | null;
};

function textFromExecOutput(output: unknown): string {
  if (Buffer.isBuffer(output)) {
    return output.toString('utf-8');
  }
  return typeof output === 'string' ? output : '';
}

function extractJsonFromOutput<T>(output: string): T | null {
  const start = output.indexOf('{');
  const end = output.lastIndexOf('}');
  if (start === -1 || end === -1 || end <= start) {
    return null;
  }

  try {
    const parsed = JSON.parse(output.slice(start, end + 1)) as unknown;
    if (parsed && typeof parsed === 'object') {
      return parsed as T;
    }
  } catch (_error) {
    return null;
  }
  return null;
}

function extractProviderSmokeJson(output: string): ProviderSmokeCliResult | null {
  return extractJsonFromOutput<ProviderSmokeCliResult>(output);
}

function arrayFromUnknown(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function stringFromUnknown(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

function numberFromUnknown(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function numberRecordFromUnknown(value: unknown): Record<string, number> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  const entries = Object.entries(value).filter(
    (entry): entry is [string, number] =>
      typeof entry[1] === 'number' && Number.isFinite(entry[1])
  );
  return entries.length ? Object.fromEntries(entries) : undefined;
}

function mapValidatedRuntimeFallbacks(value: unknown) {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const fallbacks = value
    .filter((item): item is Record<string, unknown> =>
      Boolean(item) && typeof item === 'object' && !Array.isArray(item)
    )
    .map((item) => ({
      provider: stringFromUnknown(item.provider),
      fromLoop: stringFromUnknown(item.from_loop),
      toLoop: stringFromUnknown(item.to_loop),
      reason: stringFromUnknown(item.reason),
      message: stringFromUnknown(item.message),
      toolSchemaCount: numberFromUnknown(item.tool_schema_count),
    }));
  return fallbacks.length ? fallbacks : undefined;
}

function mapValidatedRuntimeExecution(
  value: unknown
): ProviderRuntimeDiagnostics['validatedRuntimeExecution'] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }

  const payload = value as Record<string, unknown>;
  return {
    status: stringFromUnknown(payload.status),
    stopReason: stringFromUnknown(payload.stop_reason),
    loop: stringFromUnknown(payload.loop),
    actionCount: numberFromUnknown(payload.action_count),
    failedActionCount: numberFromUnknown(payload.failed_action_count),
    nativeToolFallbackCount: numberFromUnknown(payload.native_tool_fallback_count),
    nativeToolFallbacks: mapValidatedRuntimeFallbacks(payload.native_tool_fallbacks),
    toolCounts: numberRecordFromUnknown(payload.tool_counts),
    resumePolicy: mapProviderRuntimeResumePolicy(payload.resume_policy),
    toolLoopContract: mapProviderToolLoopContract(payload.tool_loop_contract),
    transactionBatchContract: mapProviderTransactionBatchContract(
      payload.transaction_batch_contract
    ),
  };
}

function mapMiniPipelinePhases(value: unknown) {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const phases = value
    .filter((item): item is Record<string, unknown> =>
      Boolean(item) && typeof item === 'object' && !Array.isArray(item)
    )
    .map((item) => ({
      name: stringFromUnknown(item.name),
      status: stringFromUnknown(item.status),
    }));
  return phases.length ? phases : undefined;
}

function mapMiniPipelineDiagnostics(
  value: unknown
): ProviderRuntimeDiagnostics['miniPipeline'] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }

  const payload = value as Record<string, unknown>;
  return {
    status: stringFromUnknown(payload.status),
    task: stringFromUnknown(payload.task),
    testCommand: stringFromUnknown(payload.test_command),
    testExitCode: numberFromUnknown(payload.test_exit_code),
    changedFiles: arrayFromUnknown(payload.changed_files),
    reason: stringFromUnknown(payload.reason),
    phases: mapMiniPipelinePhases(payload.phases),
  };
}

function mapProviderRuntimeDiagnostics(
  diagnostics: ProviderSmokeCliResult['runtime_diagnostics']
): ProviderRuntimeDiagnostics | null {
  if (!diagnostics || typeof diagnostics !== 'object') {
    return null;
  }

  return {
    smokeScope: diagnostics.smoke_scope,
    providerContractHealth: mapProviderContractHealth(diagnostics.provider_contract_health),
    requestedRuntimeMode: diagnostics.requested_runtime_mode,
    validatedRuntimeMode: diagnostics.validated_runtime_mode,
    validatedRequirements: arrayFromUnknown(diagnostics.validated_requirements),
    requestedRuntimeCapabilities: arrayFromUnknown(diagnostics.requested_runtime_capabilities),
    validatedRuntimeCapabilities: arrayFromUnknown(diagnostics.validated_runtime_capabilities),
    validatedRuntimeMissingCapabilities: arrayFromUnknown(diagnostics.validated_runtime_missing_capabilities),
    validatedRuntimeExecution: mapValidatedRuntimeExecution(diagnostics.validated_runtime_execution),
    miniPipeline: mapMiniPipelineDiagnostics(diagnostics.mini_pipeline),
    providerE2eSuite: mapProviderE2eSuite(diagnostics.provider_e2e_suite),
    providerNegativeFixtures: mapProviderNegativeFixtures(
      diagnostics.provider_e2e_negative_fixtures
    ),
    providerRunHistory: mapProviderRunHistory(diagnostics.provider_run_history),
    providerReliability: mapProviderReliability(diagnostics.provider_reliability),
    fullAutonomousMissingCapabilities: arrayFromUnknown(diagnostics.full_autonomous_missing_capabilities),
    note: diagnostics.note
  };
}

function mapProviderSmokeResult(
  result: ProviderSmokeCliResult
): ProviderConnectionTestResult {
  return {
    success: result.success === true,
    provider: result.provider ?? 'unknown',
    model: result.model ?? null,
    runtimeMode: result.runtime_mode ?? 'analysis_only',
    message: result.message ?? 'Provider smoke check completed',
    responseExcerpt: result.response_excerpt ?? null,
    errorDetails: result.error_details ?? null,
    runtimeDiagnostics: mapProviderRuntimeDiagnostics(result.runtime_diagnostics),
  };
}

function readProviderSmokeResult(
  stdout: unknown,
  stderr: unknown
): ProviderConnectionTestResult | null {
  const stdoutText = textFromExecOutput(stdout);
  const stderrText = textFromExecOutput(stderr);
  const parsed = extractProviderSmokeJson(stdoutText) ?? extractProviderSmokeJson(stderrText);
  return parsed ? mapProviderSmokeResult(parsed) : null;
}

function mapRuntimeControlPlaneDiagnostics(
  payload: RuntimeModesCliPayload
): RuntimeControlPlaneDiagnostics {
  return {
    cli_runner_contract_matrix: Array.isArray(payload.cli_runner_contract_matrix)
      ? payload.cli_runner_contract_matrix
      : [],
    runtime_fallback_matrix: Array.isArray(payload.runtime_fallback_matrix)
      ? payload.runtime_fallback_matrix
      : [],
    mcp_bridge_plan_matrix: Array.isArray(payload.mcp_bridge_plan_matrix)
      ? payload.mcp_bridge_plan_matrix
      : [],
    mcp_bridge_permission_matrix: Array.isArray(payload.mcp_bridge_permission_matrix)
      ? payload.mcp_bridge_permission_matrix
      : [],
    external_mcp_server_health: Array.isArray(payload.external_mcp_server_health)
      ? payload.external_mcp_server_health
      : [],
    runtime_subagent_matrix: Array.isArray(payload.runtime_subagent_matrix)
      ? payload.runtime_subagent_matrix
      : [],
    runtime_subagent_mutation_policy: Array.isArray(payload.runtime_subagent_mutation_policy)
      ? payload.runtime_subagent_mutation_policy
      : [],
    runtime_policy_matrix: Array.isArray(payload.runtime_policy_matrix)
      ? payload.runtime_policy_matrix
      : [],
    runtime_capability_matrix: Array.isArray(payload.runtime_capability_matrix)
      ? payload.runtime_capability_matrix
      : [],
    runtime_eval_matrix: Array.isArray(payload.runtime_eval_matrix)
      ? payload.runtime_eval_matrix
      : [],
    runtime_eval_history: Array.isArray(payload.runtime_eval_history)
      ? payload.runtime_eval_history
      : [],
    runtime_comparative_eval_matrix: Array.isArray(payload.runtime_comparative_eval_matrix)
      ? payload.runtime_comparative_eval_matrix
      : [],
    recommendations: payload.recommendations && typeof payload.recommendations === 'object'
      ? payload.recommendations
      : {},
  };
}

function readRuntimeControlPlaneDiagnosticsResult(
  stdout: unknown,
  stderr: unknown
): RuntimeControlPlaneDiagnostics | null {
  const stdoutText = textFromExecOutput(stdout);
  const stderrText = textFromExecOutput(stderr);
  const parsed = extractJsonFromOutput<RuntimeModesCliPayload>(stdoutText)
    ?? extractJsonFromOutput<RuntimeModesCliPayload>(stderrText);
  return parsed ? mapRuntimeControlPlaneDiagnostics(parsed) : null;
}

function mapExternalMcpSmokeResult(
  payload: ExternalMcpSmokeCliPayload
): RuntimeExternalMcpSmokeResult {
  const checks = Array.isArray(payload.external_mcp_contract_checks)
    ? payload.external_mcp_contract_checks
    : [];
  const fallbackSummary = {
    total: checks.length,
    ok: checks.filter((check) => check.ok).length,
    skipped: checks.filter((check) => !check.ok && check.status === 'skipped').length,
    failed: checks.filter((check) => !check.ok && check.status !== 'skipped').length,
  };
  const summary = payload.summary && typeof payload.summary === 'object'
    ? payload.summary
    : fallbackSummary;

  return {
    external_mcp_contract_checks: checks,
    summary: {
      total: Number(summary.total ?? checks.length),
      ok: Number(summary.ok ?? 0),
      skipped: Number(summary.skipped ?? 0),
      failed: Number(summary.failed ?? 0)
    }
  };
}

function readExternalMcpSmokeResult(
  stdout: unknown,
  stderr: unknown
): RuntimeExternalMcpSmokeResult | null {
  const stdoutText = textFromExecOutput(stdout);
  const stderrText = textFromExecOutput(stderr);
  const parsed = extractJsonFromOutput<ExternalMcpSmokeCliPayload>(stdoutText)
    ?? extractJsonFromOutput<ExternalMcpSmokeCliPayload>(stderrText);
  return parsed ? mapExternalMcpSmokeResult(parsed) : null;
}

async function runProviderConnectionTest(
  sourcePath: string,
  envPath: string,
  requestedRuntime?: string
): Promise<IPCResult<ProviderConnectionTestResult>> {
  const pythonPath = getToolPath('python');
  if (!pythonPath) {
    return {
      success: false,
      error: 'Python not found. Please install Python 3.12 or higher.'
    };
  }

  const runPyPath = path.join(sourcePath, 'run.py');
  if (!existsSync(runPyPath)) {
    return {
      success: false,
      error: 'Backend run.py not found. Cannot run provider smoke check.'
    };
  }

  const envVars = existsSync(envPath)
    ? parseEnvFile(readEnvFileSafe(envPath))
    : {};
  const profileEnv = getBestAvailableProfileEnv().env;
  const apiProfileEnv = await getAPIProfileEnv();
  const codexProfileEnv = getCodexProfileManager().getActiveProfileEnv();
  const commandEnv = {
    ...process.env,
    ...envVars,
    ...profileEnv,
    ...apiProfileEnv,
    ...codexProfileEnv,
    PYTHONIOENCODING: 'utf-8'
  };
  const providerSmokeRuntime = resolveProviderSmokeRuntime(commandEnv, requestedRuntime);

  try {
    const { stdout, stderr } = await execFileAsync(
      pythonPath,
      [
        runPyPath,
        '--provider-smoke',
        '--json',
        '--provider-smoke-timeout',
        String(PROVIDER_SMOKE_TIMEOUT_SECONDS),
        '--provider-smoke-runtime',
        providerSmokeRuntime
      ],
      {
        cwd: sourcePath,
        encoding: 'utf-8',
        env: commandEnv,
        maxBuffer: 1024 * 1024,
        timeout: PROVIDER_SMOKE_PROCESS_TIMEOUT_MS,
      }
    );

    const result = readProviderSmokeResult(stdout, stderr);
    if (result) {
      return { success: true, data: result };
    }

    return {
      success: false,
      error: 'Provider smoke check did not return JSON output.'
    };
  } catch (error) {
    const err = error as Error & {
      stdout?: string | Buffer;
      stderr?: string | Buffer;
      killed?: boolean;
      signal?: string | null;
    };
    const result = readProviderSmokeResult(err.stdout, err.stderr);
    if (result) {
      return { success: true, data: result };
    }

    const details = textFromExecOutput(err.stderr) || err.message;
    return {
      success: false,
      error: err.killed || err.signal === 'SIGTERM'
        ? 'Provider smoke check timed out.'
        : details
    };
  }
}

async function runProviderRuntimeDiagnostics(
  sourcePath: string,
  envPath: string | null
): Promise<IPCResult<RuntimeControlPlaneDiagnostics>> {
  return runBackendCliCommand(
    sourcePath,
    envPath,
    ['--runtime-modes', '--json'],
    RUNTIME_DIAGNOSTICS_PROCESS_TIMEOUT_MS,
    readRuntimeControlPlaneDiagnosticsResult,
    {
      missingRunPy: 'Backend run.py not found. Cannot load runtime diagnostics.',
      noJson: 'Runtime diagnostics command did not return JSON output.',
      timedOut: 'Runtime diagnostics command timed out.'
    }
  );
}

async function runBackendCliCommand<T>(
  sourcePath: string,
  envPath: string | null,
  args: string[],
  timeout: number,
  parseResult: (stdout: unknown, stderr: unknown) => T | null,
  messages: BackendCliCommandMessages
): Promise<IPCResult<T>> {
  const pythonPath = getToolPath('python');
  if (!pythonPath) {
    return {
      success: false,
      error: 'Python not found. Please install Python 3.12 or higher.'
    };
  }

  const runPyPath = path.join(sourcePath, 'run.py');
  if (!existsSync(runPyPath)) {
    return {
      success: false,
      error: messages.missingRunPy
    };
  }

  const envVars = envPath && existsSync(envPath)
    ? parseEnvFile(readEnvFileSafe(envPath))
    : {};
  const profileEnv = getBestAvailableProfileEnv().env;
  const apiProfileEnv = await getAPIProfileEnv();
  const codexProfileEnv = getCodexProfileManager().getActiveProfileEnv();

  try {
    const { stdout, stderr } = await execFileAsync(
      pythonPath,
      [runPyPath, ...args],
      {
        cwd: sourcePath,
        encoding: 'utf-8',
        env: {
          ...process.env,
          ...envVars,
          ...profileEnv,
          ...apiProfileEnv,
          ...codexProfileEnv,
          PYTHONIOENCODING: 'utf-8'
        },
        maxBuffer: 1024 * 1024,
        timeout,
      }
    );

    const result = parseResult(stdout, stderr);
    if (result) {
      return { success: true, data: result };
    }

    return {
      success: false,
      error: messages.noJson
    };
  } catch (error) {
    const err = error as BackendCliCommandError;
    const result = parseResult(err.stdout, err.stderr);
    if (result) {
      return { success: true, data: result };
    }

    const details = textFromExecOutput(err.stderr) || err.message;
    return {
      success: false,
      error: err.killed || err.signal === 'SIGTERM'
        ? messages.timedOut
        : details
    };
  }
}

async function runExternalMcpSmoke(
  sourcePath: string,
  envPath: string | null
): Promise<IPCResult<RuntimeExternalMcpSmokeResult>> {
  return runBackendCliCommand(
    sourcePath,
    envPath,
    ['--external-mcp-smoke', '--json'],
    EXTERNAL_MCP_SMOKE_PROCESS_TIMEOUT_MS,
    readExternalMcpSmokeResult,
    {
      missingRunPy: 'Backend run.py not found. Cannot run external MCP smoke check.',
      noJson: 'External MCP smoke command did not return JSON output.',
      timedOut: 'External MCP smoke command timed out.'
    }
  );
}

/**
 * Register all settings-related IPC handlers
 */
export function registerSettingsHandlers(
  agentManager: AgentManager,
  getMainWindow: () => BrowserWindow | null
): void {
  // ============================================
  // Settings Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_GET,
    async (): Promise<IPCResult<AppSettings>> => {
      // Load settings using shared helper and merge with defaults
      const savedSettings = readSettingsFile();
      const settings: AppSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };
      let needsSave = false;

      // Migration: Set agent profile to 'auto' for users who haven't made a selection (one-time)
      // This ensures new users get the optimized 'auto' profile as the default
      // while preserving existing user preferences
      if (!settings._migratedAgentProfileToAuto) {
        // Only set 'auto' if user hasn't made a selection yet
        if (!settings.selectedAgentProfile) {
          settings.selectedAgentProfile = 'auto';
        }
        settings._migratedAgentProfileToAuto = true;
        needsSave = true;
      }

      // Migration: Sync defaultModel with selectedAgentProfile (#414)
      // Fixes bug where defaultModel was stuck at 'opus' regardless of profile selection
      if (!settings._migratedDefaultModelSync) {
        if (settings.selectedAgentProfile) {
          const profile = DEFAULT_AGENT_PROFILES.find(p => p.id === settings.selectedAgentProfile);
          if (profile) {
            settings.defaultModel = profile.model;
          }
        }
        settings._migratedDefaultModelSync = true;
        needsSave = true;
      }

      // Migration: Clear CLI tool paths that are from a different platform
      // Fixes issue where Windows paths persisted on macOS (and vice versa)
      // when settings were synced/transferred between platforms
      // See: https://github.com/OBenner/Auto-Coding/issues/XXX
      const pathFields = ['pythonPath', 'gitPath', 'githubCLIPath', 'claudePath', 'autoBuildPath'] as const;
      for (const field of pathFields) {
        const pathValue = settings[field];
        if (pathValue && isPathFromWrongPlatform(pathValue)) {
          console.warn(
            `[SETTINGS_GET] Clearing ${field} - path from different platform: ${pathValue}`
          );
          delete settings[field];
          needsSave = true;
        }
      }

      // If no manual autoBuildPath is set, try to auto-detect
      if (!settings.autoBuildPath) {
        const detectedPath = detectAutoBuildSourcePath();
        if (detectedPath) {
          settings.autoBuildPath = detectedPath;
        }
      }

      // Persist migration changes
      if (needsSave) {
        try {
          writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
        } catch (error) {
          console.error('[SETTINGS_GET] Failed to persist migration:', error);
          // Continue anyway - settings will be migrated in-memory for this session
        }
      }

      // Configure CLI tools with current settings
      configureTools({
        pythonPath: settings.pythonPath,
        gitPath: settings.gitPath,
        githubCLIPath: settings.githubCLIPath,
        claudePath: settings.claudePath,
      });

      // Re-warm cache asynchronously after configuring (non-blocking)
      preWarmToolCache(['claude']).catch((error) => {
        console.warn('[SETTINGS_GET] Failed to re-warm CLI cache:', error);
      });

      return { success: true, data: settings as AppSettings };
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_SAVE,
    async (_, settings: Partial<AppSettings>): Promise<IPCResult> => {
      try {
        // Load current settings using shared helper
        const savedSettings = readSettingsFile();
        const currentSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };
        const newSettings = { ...currentSettings, ...settings };

        // Sync defaultModel when agent profile changes (#414)
        if (settings.selectedAgentProfile) {
          const profile = DEFAULT_AGENT_PROFILES.find(p => p.id === settings.selectedAgentProfile);
          if (profile) {
            newSettings.defaultModel = profile.model;
          }
        }

        writeFileSync(settingsPath, JSON.stringify(newSettings, null, 2));

        // Apply Python path if changed
        if (settings.pythonPath || settings.autoBuildPath) {
          agentManager.configure(settings.pythonPath, settings.autoBuildPath);
        }

        // Configure CLI tools if any paths changed
        if (
          settings.pythonPath !== undefined ||
          settings.gitPath !== undefined ||
          settings.githubCLIPath !== undefined ||
          settings.claudePath !== undefined
        ) {
          configureTools({
            pythonPath: newSettings.pythonPath,
            gitPath: newSettings.gitPath,
            githubCLIPath: newSettings.githubCLIPath,
            claudePath: newSettings.claudePath,
          });

          // Re-warm cache asynchronously after configuring (non-blocking)
          preWarmToolCache(['claude']).catch((error) => {
            console.warn('[SETTINGS_SAVE] Failed to re-warm CLI cache:', error);
          });
        }

        // Update auto-updater channel if betaUpdates setting changed
        if (settings.betaUpdates !== undefined) {
          if (settings.betaUpdates) {
            // Enabling beta updates - just switch channel
            setUpdateChannel('beta');
          } else {
            // Disabling beta updates - switch to stable and check if downgrade is available
            // This will notify the renderer if user is on a prerelease and stable version exists
            setUpdateChannelWithDowngradeCheck('latest', true).catch((err) => {
              console.error('[settings-handlers] Failed to check for stable downgrade:', err);
            });
          }
        }

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save settings'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_GET_CLI_TOOLS_INFO,
    async (): Promise<IPCResult<{
      python: ReturnType<typeof getToolInfo>;
      git: ReturnType<typeof getToolInfo>;
      gh: ReturnType<typeof getToolInfo>;
      claude: ReturnType<typeof getToolInfo>;
    }>> => {
      try {
        return {
          success: true,
          data: {
            python: getToolInfo('python'),
            git: getToolInfo('git'),
            gh: getToolInfo('gh'),
            claude: getToolInfo('claude'),
          },
        };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get CLI tools info',
        };
      }
    }
  );

  // ============================================
  // Provider Settings Operations
  // ============================================

  /**
   * Handler: saveProviderSettings
   * Saves multi-model provider configuration to project .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_SAVE_PROVIDER,
    async (_, projectId: string, settings: ProviderSettings): Promise<IPCResult> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        if (!project.autoBuildPath) {
          return { success: false, error: 'Project not initialized' };
        }

        const envPath = path.join(project.path, project.autoBuildPath, '.env');

        // Read existing .env content (TOCTOU-safe: read directly, catch ENOENT)
        const existingContent = readEnvFileSafe(envPath);

        // Parse existing environment variables
        const existingVars = parseEnvFile(existingContent);

        // Apply provider settings to env vars map
        applyProviderSettingsToVars(existingVars, settings);

        // Generate new .env content preserving structure
        const newContent = generateProviderEnvContent(existingVars, existingContent);

        // Write to file
        writeFileSync(envPath, newContent);

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save provider settings'
        };
      }
    }
  );

  /**
   * Handler: loadProviderSettings
   * Loads multi-model provider configuration from project .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_LOAD_PROVIDER,
    async (_, projectId: string): Promise<IPCResult<ProviderSettings>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        if (!project.autoBuildPath) {
          return { success: false, error: 'Project not initialized' };
        }

        const envPath = path.join(project.path, project.autoBuildPath, '.env');

        // Parse environment variables (TOCTOU-safe: read directly, catch ENOENT)
        const envVars = parseEnvFile(readEnvFileSafe(envPath));

        // Map env vars to ProviderSettings
        const providerSettings: ProviderSettings = {
          provider: (envVars['AI_ENGINE_PROVIDER'] as AIEngineProvider) || 'claude',
          openaiApiKey: envVars['OPENAI_API_KEY'] || '',
          googleApiKey: envVars['GOOGLE_API_KEY'] || '',
          openrouterApiKey: envVars['OPENROUTER_API_KEY'] || '',
          zhipuaiApiKey: envVars['ZHIPUAI_API_KEY'] || '',
          plannerModel: envVars['AGENT_MODEL_PLANNER'] || '',
          coderModel: envVars['AGENT_MODEL_CODER'] || '',
          qaModel: envVars['AGENT_MODEL_QA_REVIEWER'] || '',
          runtimeMode: envVars['AUTO_CODE_RUNTIME_MODE'] as ProviderSettings['runtimeMode'],
          plannerRuntimeMode: envVars['AGENT_RUNTIME_MODE_PLANNER'] as ProviderSettings['plannerRuntimeMode'],
          coderRuntimeMode: envVars['AGENT_RUNTIME_MODE_CODER'] as ProviderSettings['coderRuntimeMode'],
          qaReviewerRuntimeMode: envVars['AGENT_RUNTIME_MODE_QA_REVIEWER'] as ProviderSettings['qaReviewerRuntimeMode'],
          qaFixerRuntimeMode: envVars['AGENT_RUNTIME_MODE_QA_FIXER'] as ProviderSettings['qaFixerRuntimeMode'],
          runtimeFallbackEnabled: envVars['AUTO_CODE_RUNTIME_FALLBACK'] === 'true',
          cliRunnerRouterEnabled: envVars['AUTO_CODE_CLI_RUNNER_ROUTER'] === 'true',
        };

        return { success: true, data: providerSettings };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load provider settings'
        };
      }
    }
  );

  // ============================================
  // Dialog Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_SELECT_DIRECTORY,
    async (): Promise<string | null> => {
      const mainWindow = getMainWindow();
      if (!mainWindow) return null;

      const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
        title: 'Select Project Directory'
      });

      if (result.canceled || result.filePaths.length === 0) {
        return null;
      }

      return result.filePaths[0];
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_CREATE_PROJECT_FOLDER,
    async (
      _,
      location: string,
      name: string,
      initGit: boolean
    ): Promise<IPCResult<{ path: string; name: string; gitInitialized: boolean }>> => {
      try {
        // Validate inputs
        if (!location || !name) {
          return { success: false, error: 'Location and name are required' };
        }

        // Sanitize project name (convert to kebab-case, remove invalid chars)
        const sanitizedName = name
          .toLowerCase()
          .replace(/\s+/g, '-')
          .replace(/[^a-z0-9-_]/g, '')
          .replace(/-+/g, '-')
          .replace(/^-|-$/g, '');

        if (!sanitizedName) {
          return { success: false, error: 'Invalid project name' };
        }

        const projectPath = path.join(location, sanitizedName);

        // Check if folder already exists
        if (existsSync(projectPath)) {
          return { success: false, error: `Folder "${sanitizedName}" already exists at this location` };
        }

        // Create the directory
        mkdirSync(projectPath, { recursive: true });

        // Initialize git if requested
        let gitInitialized = false;
        if (initGit) {
          try {
            execFileSync(getToolPath('git'), ['init'], { cwd: projectPath, stdio: 'ignore' });
            gitInitialized = true;
          } catch {
            // Git init failed, but folder was created - continue without git
            console.warn('Failed to initialize git repository');
          }
        }

        return {
          success: true,
          data: {
            path: projectPath,
            name: sanitizedName,
            gitInitialized
          }
        };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to create project folder'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_GET_DEFAULT_PROJECT_LOCATION,
    async (): Promise<string | null> => {
      try {
        // Return user's home directory + common project folders
        const homeDir = app.getPath('home');
        const commonPaths = [
          path.join(homeDir, 'Projects'),
          path.join(homeDir, 'Developer'),
          path.join(homeDir, 'Code'),
          path.join(homeDir, 'Documents')
        ];

        // Return the first one that exists, or Documents as fallback
        for (const p of commonPaths) {
          if (existsSync(p)) {
            return p;
          }
        }

        return path.join(homeDir, 'Documents');
      } catch {
        return null;
      }
    }
  );

  // ============================================
  // App Info
  // ============================================

  ipcMain.handle(IPC_CHANNELS.APP_VERSION, async (): Promise<string> => {
    // Return the actual bundled version from package.json
    const version = app.getVersion();
    console.log('[settings-handlers] APP_VERSION returning:', version);
    return version;
  });

  // ============================================
  // Shell Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SHELL_OPEN_EXTERNAL,
    async (_, url: string): Promise<void> => {
      // Validate URL scheme to prevent opening dangerous protocols
      try {
        const parsedUrl = new URL(url);
        if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
          console.warn(`[SHELL_OPEN_EXTERNAL] Blocked URL with unsafe protocol: ${parsedUrl.protocol}`);
          throw new Error(`Unsafe URL protocol: ${parsedUrl.protocol}`);
        }
        await shell.openExternal(url);
      } catch (error) {
        if (error instanceof TypeError) {
          // Invalid URL format
          console.warn(`[SHELL_OPEN_EXTERNAL] Invalid URL format: ${url}`);
          throw new Error('Invalid URL format');
        }
        throw error;
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SHELL_OPEN_TERMINAL,
    async (_, dirPath: string): Promise<IPCResult<void>> => {
      try {
        // Validate dirPath input
        if (!dirPath || typeof dirPath !== 'string' || dirPath.trim() === '') {
          return {
            success: false,
            error: 'Directory path is required and must be a non-empty string'
          };
        }

        // Resolve to absolute path
        const resolvedPath = path.resolve(dirPath);

        // Verify path exists
        if (!existsSync(resolvedPath)) {
          return {
            success: false,
            error: `Directory does not exist: ${resolvedPath}`
          };
        }

        // Verify it's a directory
        try {
          if (!statSync(resolvedPath).isDirectory()) {
            return {
              success: false,
              error: `Path is not a directory: ${resolvedPath}`
            };
          }
        } catch (_statError) {
          return {
            success: false,
            error: `Cannot access path: ${resolvedPath}`
          };
        }

        if (isMacOS()) {
          // macOS: Use execFileSync with argument array to prevent injection
          execFileSync('open', ['-a', 'Terminal', resolvedPath], { stdio: 'ignore' });
        } else if (isWindows()) {
          // Windows: Use cmd.exe directly with argument array
          // /C tells cmd to execute the command and terminate
          // /K keeps the window open after executing cd
          execFileSync('cmd.exe', ['/K', 'cd', '/d', resolvedPath], {
            stdio: 'ignore',
            windowsHide: false,
            shell: false  // Explicitly disable shell to prevent injection
          });
        } else {
          // Linux: Try common terminal emulators with argument arrays
          // Note: xterm uses cwd option to avoid shell injection vulnerabilities
          const terminals: Array<{ cmd: string; args: string[]; useCwd?: boolean }> = [
            { cmd: 'gnome-terminal', args: ['--working-directory', resolvedPath] },
            { cmd: 'konsole', args: ['--workdir', resolvedPath] },
            { cmd: 'xfce4-terminal', args: ['--working-directory', resolvedPath] },
            { cmd: 'xterm', args: ['-e', 'bash'], useCwd: true }
          ];

          let opened = false;
          for (const { cmd, args, useCwd } of terminals) {
            try {
              execFileSync(cmd, args, {
                stdio: 'ignore',
                ...(useCwd ? { cwd: resolvedPath } : {})
              });
              opened = true;
              break;
            } catch {
              // Try next terminal
            }
          }

          if (!opened) {
            return {
              success: false,
              error: 'No supported terminal emulator found. Please install gnome-terminal, konsole, xfce4-terminal, or xterm.'
            };
          }
        }

        return { success: true };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        return {
          success: false,
          error: `Failed to open terminal: ${errorMsg}`
        };
      }
    }
  );

  // ============================================
  // Auto-Build Source Environment Operations
  // ============================================

  /**
   * Helper to get source .env path from settings
   *
   * In production mode, the .env file is NOT bundled (excluded in electron-builder config).
   * We store the source .env in app userData directory instead, which is writable.
   * The sourcePath points to the bundled backend for reference, but envPath is in userData.
   */
  const getSourceEnvPath = (): {
    sourcePath: string | null;
    envPath: string | null;
    isProduction: boolean;
  } => {
    const savedSettings = readSettingsFile();
    const settings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };

    // Get autoBuildPath from settings or try to auto-detect
    let sourcePath: string | null = settings.autoBuildPath || null;
    if (!sourcePath) {
      sourcePath = detectAutoBuildSourcePath();
    }

    if (!sourcePath) {
      return { sourcePath: null, envPath: null, isProduction: !is.dev };
    }

    // In production, use userData directory for .env since resources may be read-only
    // In development, use the actual source path
    let envPath: string;
    if (is.dev) {
      envPath = path.join(sourcePath, '.env');
    } else {
      // Production: store .env in userData/backend/.env
      const userDataBackendDir = path.join(app.getPath('userData'), 'backend');
      if (!existsSync(userDataBackendDir)) {
        mkdirSync(userDataBackendDir, { recursive: true });
      }
      envPath = path.join(userDataBackendDir, '.env');
    }

    return {
      sourcePath,
      envPath,
      isProduction: !is.dev
    };
  };

  ipcMain.handle(
    IPC_CHANNELS.AUTOBUILD_SOURCE_ENV_GET,
    async (): Promise<IPCResult<SourceEnvConfig>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        // Load global settings to check for global token fallback
        const savedSettings = readSettingsFile();
        const globalSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };

        if (!sourcePath) {
          // Even without source path, check global token
          const globalToken = globalSettings.globalClaudeOAuthToken;
          return {
            success: true,
            data: {
              hasClaudeToken: !!globalToken && globalToken.length > 0,
              claudeOAuthToken: globalToken,
              envExists: false
            }
          };
        }

        const envExists = envPath ? existsSync(envPath) : false;
        let hasClaudeToken = false;
        let claudeOAuthToken: string | undefined;

        // First, check source .env file
        if (envExists && envPath) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);
          claudeOAuthToken = vars['CLAUDE_CODE_OAUTH_TOKEN'];
          hasClaudeToken = !!claudeOAuthToken && claudeOAuthToken.length > 0;
        }

        // Fallback to global settings if no token in source .env
        if (!hasClaudeToken && globalSettings.globalClaudeOAuthToken) {
          claudeOAuthToken = globalSettings.globalClaudeOAuthToken;
          hasClaudeToken = true;
        }

        return {
          success: true,
          data: {
            hasClaudeToken,
            claudeOAuthToken,
            sourcePath,
            envExists
          }
        };
      } catch (error) {
        // Log the error for debugging in production
        console.error('[AUTOBUILD_SOURCE_ENV_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get source env'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.AUTOBUILD_SOURCE_ENV_UPDATE,
    async (_, config: { claudeOAuthToken?: string }): Promise<IPCResult> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        // Read existing content or start fresh (avoiding TOCTOU race condition)
        let existingVars: Record<string, string> = {};
        try {
          const content = readFileSync(envPath, 'utf-8');
          existingVars = parseEnvFile(content);
        } catch (_readError) {
          // File doesn't exist or can't be read - start with empty vars
          // This is expected for first-time setup
        }

        // Update with new values
        if (config.claudeOAuthToken !== undefined) {
          existingVars['CLAUDE_CODE_OAUTH_TOKEN'] = config.claudeOAuthToken;
        }

        // Generate content
        const lines: string[] = [
          '# Auto Code Framework Environment Variables',
          '# Managed by Auto Code UI',
          '',
          '# Claude Code OAuth Token (REQUIRED)',
          `CLAUDE_CODE_OAUTH_TOKEN=${existingVars['CLAUDE_CODE_OAUTH_TOKEN'] || ''}`,
          ''
        ];

        // Preserve other existing variables
        for (const [key, value] of Object.entries(existingVars)) {
          if (key !== 'CLAUDE_CODE_OAUTH_TOKEN') {
            lines.push(`${key}=${value}`);
          }
        }

        writeFileSync(envPath, lines.join('\n'));

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update source env'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.AUTOBUILD_SOURCE_ENV_CHECK_TOKEN,
    async (): Promise<IPCResult<SourceEnvCheckResult>> => {
      try {
        const { sourcePath, envPath, isProduction } = getSourceEnvPath();

        // Load global settings to check for global token fallback
        const savedSettings = readSettingsFile();
        const globalSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };

        // Check global token first as it's the primary method
        const globalToken = globalSettings.globalClaudeOAuthToken;
        const hasGlobalToken = !!globalToken && globalToken.length > 0;

        if (!sourcePath) {
          // In production, no source path is acceptable if global token exists
          if (hasGlobalToken) {
            return {
              success: true,
              data: {
                hasToken: true,
                sourcePath: isProduction ? app.getPath('userData') : undefined
              }
            };
          }
          return {
            success: true,
            data: {
              hasToken: false,
              error: isProduction
                ? 'Please configure Claude OAuth token in Settings > API Configuration'
                : 'Auto-build source path not configured'
            }
          };
        }

        // Check source .env file
        let hasEnvToken = false;
        if (envPath && existsSync(envPath)) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);
          const token = vars['CLAUDE_CODE_OAUTH_TOKEN'];
          hasEnvToken = !!token && token.length > 0;
        }

        // Token exists if either source .env has it OR global settings has it
        const hasToken = hasEnvToken || hasGlobalToken;

        return {
          success: true,
          data: {
            hasToken,
            sourcePath
          }
        };
      } catch (error) {
        // Log the error for debugging in production
        console.error('[AUTOBUILD_SOURCE_ENV_CHECK_TOKEN] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to check source token'
        };
      }
    }
  );

  // Static model lists per provider (used by getAvailableModels handler)
  const STATIC_PROVIDER_MODELS: Record<string, string[]> = {
    claude: [
      'claude-sonnet-4-5-20250929',
      'claude-opus-4-20250514',
      'claude-haiku-4-5-20251001',
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229',
    ],
    litellm: [
      'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo',
      'anthropic/claude-3-opus-20240229', 'anthropic/claude-3-sonnet-20240229',
      'anthropic/claude-3-haiku-20240307',
      'gemini/gemini-pro', 'gemini/gemini-1.5-pro', 'gemini/gemini-1.5-flash',
      'gemini/gemini-2.0-flash',
      'ollama/llama3', 'ollama/llama3.1', 'ollama/llama3.2', 'ollama/mistral',
      'ollama/mixtral', 'ollama/codellama', 'ollama/qwen', 'ollama/qwen2',
      'ollama/gemma', 'ollama/gemma2',
    ],
    openrouter: [
      'anthropic/claude-3.5-sonnet', 'anthropic/claude-3-opus',
      'openai/gpt-4-turbo', 'openai/gpt-4o',
      'google/gemini-pro-1.5',
      'meta-llama/llama-3.1-405b-instruct', 'meta-llama/llama-3.1-70b-instruct',
      'mistralai/mixtral-8x7b-instruct',
    ],
  };

  /**
   * Detect available Ollama models by running the Python detector script.
   * Returns IPCResult with models array or an error.
   */
  const fetchOllamaModels = (): IPCResult<{ models: string[] }> => {
    const { sourcePath } = getSourceEnvPath();
    if (!sourcePath) {
      return { success: false, error: 'Auto-build source path not configured. Cannot detect Ollama models.' };
    }
    const scriptPath = path.join(sourcePath, 'ollama_model_detector.py');
    if (!existsSync(scriptPath)) {
      return { success: false, error: 'Ollama model detector script not found' };
    }
    const pythonPath = getToolPath('python');
    if (!pythonPath) {
      return { success: false, error: 'Python not found. Please install Python 3.10 or higher.' };
    }
    const output = execFileSync(pythonPath, [scriptPath, 'list-models'], {
      encoding: 'utf-8',
      timeout: 5000,
    });
    const result = JSON.parse(output);
    if (result.success && result.data?.models) {
      return { success: true, data: { models: result.data.models.map((m: { name: string }) => m.name) } };
    }
    return { success: false, error: result.error || 'Failed to detect Ollama models' };
  };

  // Handler: getAvailableModels - Fetch available models for a provider
  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_GET_AVAILABLE_MODELS,
    async (_, provider: string): Promise<IPCResult<{ models: string[] }>> => {
      try {
        const staticModels = STATIC_PROVIDER_MODELS[provider];
        if (staticModels) {
          return { success: true, data: { models: staticModels } };
        }
        if (provider === 'ollama') {
          try {
            return fetchOllamaModels();
          } catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error detecting Ollama models';
            console.error('[SETTINGS_GET_AVAILABLE_MODELS] Ollama detection error:', message);
            return { success: false, error: message };
          }
        }
        return { success: false, error: `Unknown provider: ${provider}` };
      } catch (error) {
        console.error('[SETTINGS_GET_AVAILABLE_MODELS] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get available models'
        };
      }
    }
  );

  // ============================================
  // AI Provider Configuration (Backend .env sync)
  // ============================================

  /**
   * Get AI provider configuration from backend .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_GET,
    async (): Promise<IPCResult<import('../../shared/types').AIProviderConfig>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        const config: import('../../shared/types').AIProviderConfig = {
          provider: 'claude'
        };

        if (existsSync(envPath)) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);

          config.provider = (vars['AI_ENGINE_PROVIDER'] || 'claude') as import('../../shared/types').AIEngineProvider;
          config.anthropicApiKey = vars['ANTHROPIC_API_KEY'];
          config.claudeModel = vars['CLAUDE_MODEL'];
          config.codexModel = vars['CODEX_MODEL'];
          config.openaiApiKey = vars['OPENAI_API_KEY'];
          config.openaiModel = vars['OPENAI_MODEL'];
          config.openaiBaseUrl = vars['OPENAI_BASE_URL'];
          config.googleApiKey = vars['GOOGLE_API_KEY'];
          config.googleModel = vars['GOOGLE_MODEL'];
          config.litellmModel = vars['LITELLM_MODEL'];
          config.litellmApiBase = vars['LITELLM_API_BASE'];
          config.litellmApiKey = vars['LITELLM_API_KEY'];
          config.openrouterApiKey = vars['OPENROUTER_API_KEY'];
          config.openrouterModel = vars['OPENROUTER_MODEL'];
          config.openrouterBaseUrl = vars['OPENROUTER_BASE_URL'];
          config.zhipuaiApiKey = vars['ZHIPUAI_API_KEY'];
          config.zhipuaiModel = vars['ZHIPUAI_MODEL'];
          config.ollamaModel = vars['OLLAMA_MODEL'];
          config.ollamaBaseUrl = vars['OLLAMA_BASE_URL'];
          config.plannerModel = vars['AGENT_MODEL_PLANNER'];
          config.coderModel = vars['AGENT_MODEL_CODER'];
          config.qaModel = vars['AGENT_MODEL_QA_REVIEWER'];
          config.runtimeMode = vars['AUTO_CODE_RUNTIME_MODE'] as import('../../shared/types').AgentRuntimeMode;
          config.plannerRuntimeMode = vars['AGENT_RUNTIME_MODE_PLANNER'] as import('../../shared/types').AgentRuntimeMode;
          config.coderRuntimeMode = vars['AGENT_RUNTIME_MODE_CODER'] as import('../../shared/types').AgentRuntimeMode;
          config.qaReviewerRuntimeMode = vars['AGENT_RUNTIME_MODE_QA_REVIEWER'] as import('../../shared/types').AgentRuntimeMode;
          config.qaFixerRuntimeMode = vars['AGENT_RUNTIME_MODE_QA_FIXER'] as import('../../shared/types').AgentRuntimeMode;
          config.runtimeFallbackEnabled = vars['AUTO_CODE_RUNTIME_FALLBACK'] === 'true';
          config.cliRunnerRouterEnabled = vars['AUTO_CODE_CLI_RUNNER_ROUTER'] === 'true';
        }

        return {
          success: true,
          data: config
        };
      } catch (error) {
        console.error('[PROVIDER_CONFIG_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get provider config'
        };
      }
    }
  );

  /**
   * Update AI provider configuration in backend .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_UPDATE,
    async (_, config: Partial<import('../../shared/types').AIProviderConfig>): Promise<IPCResult> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        const existingContent = readEnvFileSafe(envPath);
        const existingVars = parseEnvFile(existingContent);
        const setEnvVar = (key: string, value: string | undefined): void => {
          if (value !== undefined) {
            existingVars[key] = value;
          }
        };

        setEnvVar('AI_ENGINE_PROVIDER', config.provider);
        setEnvVar('ANTHROPIC_API_KEY', config.anthropicApiKey);
        setEnvVar('CLAUDE_MODEL', config.claudeModel);
        setEnvVar('CODEX_MODEL', config.codexModel);
        setEnvVar('OPENAI_API_KEY', config.openaiApiKey);
        setEnvVar('OPENAI_MODEL', config.openaiModel);
        setEnvVar('OPENAI_BASE_URL', config.openaiBaseUrl);
        setEnvVar('GOOGLE_API_KEY', config.googleApiKey);
        setEnvVar('GOOGLE_MODEL', config.googleModel);
        setEnvVar('LITELLM_MODEL', config.litellmModel);
        setEnvVar('LITELLM_API_BASE', config.litellmApiBase);
        setEnvVar('LITELLM_API_KEY', config.litellmApiKey);
        setEnvVar('OPENROUTER_API_KEY', config.openrouterApiKey);
        setEnvVar('OPENROUTER_MODEL', config.openrouterModel);
        setEnvVar('OPENROUTER_BASE_URL', config.openrouterBaseUrl);
        setEnvVar('ZHIPUAI_API_KEY', config.zhipuaiApiKey);
        setEnvVar('ZHIPUAI_MODEL', config.zhipuaiModel);
        setEnvVar('OLLAMA_MODEL', config.ollamaModel);
        setEnvVar('OLLAMA_BASE_URL', config.ollamaBaseUrl);
        setEnvVar('AGENT_MODEL_PLANNER', config.plannerModel);
        setEnvVar('AGENT_MODEL_CODER', config.coderModel);
        setEnvVar('AGENT_MODEL_QA_REVIEWER', config.qaModel);
        setEnvVar('AUTO_CODE_RUNTIME_MODE', config.runtimeMode);
        setEnvVar('AGENT_RUNTIME_MODE_PLANNER', config.plannerRuntimeMode);
        setEnvVar('AGENT_RUNTIME_MODE_CODER', config.coderRuntimeMode);
        setEnvVar('AGENT_RUNTIME_MODE_QA_REVIEWER', config.qaReviewerRuntimeMode);
        setEnvVar('AGENT_RUNTIME_MODE_QA_FIXER', config.qaFixerRuntimeMode);
        if (config.runtimeFallbackEnabled !== undefined) {
          setEnvVar(
            'AUTO_CODE_RUNTIME_FALLBACK',
            config.runtimeFallbackEnabled ? 'true' : 'false'
          );
        }
        if (config.cliRunnerRouterEnabled !== undefined) {
          setEnvVar(
            'AUTO_CODE_CLI_RUNNER_ROUTER',
            config.cliRunnerRouterEnabled ? 'true' : 'false'
          );
        }

        const newContent = generateProviderEnvContent(existingVars, existingContent);

        writeFileSync(envPath, newContent, 'utf-8');

        return { success: true };
      } catch (error) {
        console.error('[PROVIDER_CONFIG_UPDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update provider config'
        };
      }
    }
  );

  /**
   * Validate AI provider configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_VALIDATE,
    async (): Promise<IPCResult<import('../../shared/types').ProviderConfigValidation>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        const errors: string[] = [];
        const availableProviders: import('../../shared/types').AIEngineProvider[] = [];

        if (existsSync(envPath)) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);
          const profileEnv = getBestAvailableProfileEnv().env;
          const apiProfileEnv = await getAPIProfileEnv();
          const codexProfileEnv = getCodexProfileManager().getActiveProfileEnv();
          const effectiveVars = {
            ...vars,
            ...profileEnv,
            ...apiProfileEnv,
            ...codexProfileEnv,
          };

          const provider = (vars['AI_ENGINE_PROVIDER'] || 'claude') as import('../../shared/types').AIEngineProvider;

          if (hasClaudeProviderAuth(effectiveVars)) availableProviders.push('claude');
          if (hasCodexProviderAuth(effectiveVars)) availableProviders.push('codex');
          if (effectiveVars['OPENAI_API_KEY']) availableProviders.push('openai');
          if (effectiveVars['GOOGLE_API_KEY']) availableProviders.push('google');
          if (effectiveVars['LITELLM_MODEL']) availableProviders.push('litellm');
          if (effectiveVars['OPENROUTER_API_KEY']) availableProviders.push('openrouter');
          if (effectiveVars['ZHIPUAI_API_KEY']) availableProviders.push('zhipuai');
          if (effectiveVars['OLLAMA_MODEL']) availableProviders.push('ollama');

          errors.push(...collectRuntimeCompatibilityErrors(provider, vars));

          switch (provider) {
            case 'claude':
              if (!hasClaudeProviderAuth(effectiveVars)) errors.push('Claude provider requires Claude OAuth credentials, an active API profile, or ANTHROPIC_API_KEY');
              break;
            case 'codex':
              if (!hasCodexProviderAuth(effectiveVars)) errors.push('Codex provider requires an active Codex profile or CODEX_HOME');
              break;
            case 'openai':
              if (!effectiveVars['OPENAI_API_KEY']) errors.push('OpenAI provider requires OPENAI_API_KEY environment variable');
              break;
            case 'google':
              if (!effectiveVars['GOOGLE_API_KEY']) errors.push('Google provider requires GOOGLE_API_KEY environment variable');
              break;
            case 'litellm':
              if (!effectiveVars['LITELLM_MODEL']) errors.push('LiteLLM provider requires LITELLM_MODEL environment variable');
              break;
            case 'openrouter':
              if (!effectiveVars['OPENROUTER_API_KEY']) errors.push('OpenRouter provider requires OPENROUTER_API_KEY environment variable');
              break;
            case 'zhipuai':
              if (!effectiveVars['ZHIPUAI_API_KEY']) errors.push('ZhipuAI provider requires ZHIPUAI_API_KEY environment variable');
              break;
            case 'ollama':
              if (!effectiveVars['OLLAMA_MODEL']) errors.push('Ollama provider requires OLLAMA_MODEL environment variable');
              break;
          }
        } else {
          errors.push('.env file does not exist in backend directory');
        }

        return {
          success: true,
          data: { isValid: errors.length === 0, errors, availableProviders }
        };
      } catch (error) {
        console.error('[PROVIDER_CONFIG_VALIDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to validate provider config'
        };
      }
    }
  );

  /**
   * Run a real text-only provider smoke check through backend runtime code
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_TEST,
    async (_event, requestedRuntime?: string): Promise<IPCResult<ProviderConnectionTestResult>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        return await runProviderConnectionTest(sourcePath, envPath, requestedRuntime);
      } catch (error) {
        console.error('[PROVIDER_CONFIG_TEST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to test provider config'
        };
      }
    }
  );

  /**
   * Load runtime/MCP/fallback diagnostics from the backend compatibility command
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_RUNTIME_DIAGNOSTICS,
    async (): Promise<IPCResult<RuntimeControlPlaneDiagnostics>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        return await runProviderRuntimeDiagnostics(sourcePath, envPath);
      } catch (error) {
        console.error('[PROVIDER_RUNTIME_DIAGNOSTICS] Error:', error);
        return {
          success: false,
          error: error instanceof Error
            ? error.message
            : 'Failed to load runtime diagnostics'
        };
      }
    }
  );

  /**
   * Run live external MCP tools/list contract checks through backend runtime code
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_EXTERNAL_MCP_SMOKE,
    async (): Promise<IPCResult<RuntimeExternalMcpSmokeResult>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        return await runExternalMcpSmoke(sourcePath, envPath);
      } catch (error) {
        console.error('[PROVIDER_EXTERNAL_MCP_SMOKE] Error:', error);
        return {
          success: false,
          error: error instanceof Error
            ? error.message
            : 'Failed to run external MCP smoke check'
        };
      }
    }
  );
}
