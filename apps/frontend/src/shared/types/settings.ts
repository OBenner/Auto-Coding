/**
 * Application settings types
 */

import type { NotificationSettings, GraphitiEmbeddingProvider } from './project';
import type { ChangelogFormat, ChangelogAudience, ChangelogEmojiLevel } from './changelog';
import type { SupportedLanguage } from '../constants/i18n';

// ============================================
// Recent Actions Types
// ============================================

/**
 * Recent action entry for quick actions menu
 */
export interface RecentAction {
  /** Unique identifier for this action instance */
  id: string;
  /** Type of action performed */
  type: 'batch_qa' | 'batch_status_update' | 'create_task' | 'start_task' | 'stop_task';
  /** Display label for the action */
  label: string;
  /** Timestamp when the action was performed */
  timestamp: Date;
  /** Number of items affected (for batch operations) */
  itemCount?: number;
  /** Target status (for status updates) */
  targetStatus?: string;
  /** Project ID where the action was performed */
  projectId?: string;
}

// GPU acceleration mode for terminal WebGL rendering
export type GpuAcceleration = 'auto' | 'on' | 'off';

// Color theme types for multi-theme support
export type ColorTheme = 'default' | 'dusk' | 'lime' | 'ocean' | 'retro' | 'neo' | 'forest';

// Developer tools preferences - IDE and terminal selection
// Comprehensive list based on Stack Overflow Developer Survey 2024, JetBrains Survey, and market research
export type SupportedIDE =
  // Microsoft/VS Code Ecosystem
  | 'vscode'           // Visual Studio Code (~73% market share)
  | 'visualstudio'     // Visual Studio (full IDE)
  | 'vscodium'         // VSCodium (OSS VS Code without telemetry)
  // AI-Powered Editors (VS Code forks & alternatives)
  | 'cursor'           // Cursor (AI-first VS Code fork)
  | 'windsurf'         // Windsurf by Codeium (AI editor)
  | 'zed'              // Zed (high-performance, Rust-based, AI features)
  | 'void'             // Void (open-source AI editor)
  | 'pearai'           // PearAI (open-source AI editor)
  | 'kiro'             // Kiro by AWS (spec-driven agentic IDE)
  // JetBrains IDEs
  | 'intellij'         // IntelliJ IDEA
  | 'pycharm'          // PyCharm
  | 'webstorm'         // WebStorm
  | 'phpstorm'         // PhpStorm
  | 'rubymine'         // RubyMine
  | 'goland'           // GoLand
  | 'clion'            // CLion (C/C++)
  | 'rider'            // Rider (.NET)
  | 'datagrip'         // DataGrip (Database)
  | 'fleet'            // Fleet (lightweight)
  | 'androidstudio'    // Android Studio (based on IntelliJ)
  | 'aqua'             // Aqua (test automation)
  | 'rustrover'        // RustRover (Rust IDE)
  // Classic Text Editors
  | 'sublime'          // Sublime Text
  | 'vim'              // Vim
  | 'neovim'           // Neovim
  | 'emacs'            // Emacs
  | 'nano'             // GNU Nano
  | 'micro'            // Micro (modern terminal editor)
  | 'helix'            // Helix (modal editor, Rust-based)
  | 'kakoune'          // Kakoune (modal editor)
  // Platform-Specific IDEs
  | 'xcode'            // Xcode (Apple)
  | 'eclipse'          // Eclipse
  | 'netbeans'         // NetBeans
  | 'qtcreator'        // Qt Creator
  | 'codeblocks'       // Code::Blocks
  // macOS-Specific Editors
  | 'nova'             // Nova by Panic
  | 'bbedit'           // BBEdit
  | 'textmate'         // TextMate
  | 'coteditor'        // CotEditor
  // Windows-Specific Editors
  | 'notepadpp'        // Notepad++
  | 'ultraedit'        // UltraEdit
  // Linux Editors
  | 'kate'             // Kate (KDE)
  | 'gedit'            // gedit (GNOME)
  | 'geany'            // Geany
  | 'lapce'            // Lapce (Rust-based, fast)
  | 'lite-xl'          // Lite XL (lightweight)
  // Cloud/Browser-Based IDEs
  | 'codespaces'       // GitHub Codespaces
  | 'gitpod'           // Gitpod
  | 'replit'           // Replit
  | 'codesandbox'      // CodeSandbox
  | 'stackblitz'       // StackBlitz
  | 'cloud9'           // AWS Cloud9
  | 'cloudshell'       // Google Cloud Shell Editor
  | 'coder'            // Coder (self-hosted)
  | 'glitch'           // Glitch
  | 'codepen'          // CodePen
  | 'jsfiddle'         // JSFiddle
  | 'colab'            // Google Colab (notebooks)
  | 'jupyter'          // Jupyter/JupyterLab
  | 'dataspell'        // DataSpell (JetBrains data science)
  // Archived/Legacy (still in use)
  | 'atom'             // Atom (archived but still used)
  | 'brackets'         // Brackets (archived)
  // Custom option
  | 'custom';

// Comprehensive terminal emulator support
// Based on GitHub stars, Reddit discussions, and developer surveys
export type SupportedTerminal =
  // System Defaults
  | 'system'           // System default terminal
  // macOS Terminals
  | 'terminal'         // Terminal.app (macOS default)
  | 'iterm2'           // iTerm2 (most popular macOS)
  | 'warp'             // Warp (AI-powered, modern)
  | 'ghostty'          // Ghostty (by Mitchell Hashimoto)
  | 'rio'              // Rio (Rust-based, GPU-accelerated)
  // Windows Terminals
  | 'windowsterminal'  // Windows Terminal (Microsoft)
  | 'powershell'       // PowerShell
  | 'cmd'              // Command Prompt
  | 'conemu'           // ConEmu
  | 'cmder'            // Cmder (ConEmu-based)
  | 'gitbash'          // Git Bash
  | 'cygwin'           // Cygwin
  | 'msys2'            // MSYS2
  // Linux Terminals (Desktop Environment defaults)
  | 'gnometerminal'    // GNOME Terminal
  | 'konsole'          // Konsole (KDE)
  | 'xfce4terminal'    // XFCE4 Terminal
  | 'lxterminal'       // LXTerminal
  | 'mate-terminal'    // MATE Terminal
  // Linux Terminals (Feature-rich)
  | 'terminator'       // Terminator (split panes)
  | 'tilix'            // Tilix (tiling terminal)
  | 'guake'            // Guake (dropdown)
  | 'yakuake'          // Yakuake (KDE dropdown)
  | 'tilda'            // Tilda (dropdown)
  // GPU-Accelerated Terminals (Cross-platform)
  | 'alacritty'        // Alacritty (Rust, ~56k GitHub stars)
  | 'kitty'            // Kitty (Python/C, ~25k GitHub stars)
  | 'wezterm'          // WezTerm (Rust, multiplexer built-in)
  // Cross-Platform Terminals
  | 'hyper'            // Hyper (Electron-based)
  | 'tabby'            // Tabby (formerly Terminus)
  | 'extraterm'        // Extraterm (frames-based)
  | 'contour'          // Contour (modern VT)
  // Minimal/Suckless Terminals
  | 'xterm'            // xterm (X11 classic)
  | 'urxvt'            // rxvt-unicode
  | 'st'               // st (suckless terminal)
  | 'foot'             // Foot (Wayland)
  // Specialty/Retro Terminals
  | 'coolretroterm'    // cool-retro-term (CRT aesthetic)
  // Multiplexers (often used as terminal environment)
  | 'tmux'             // tmux (terminal multiplexer)
  | 'zellij'           // Zellij (modern multiplexer)
  // AI-Enhanced
  | 'fig'              // Fig / Amazon Q Developer (autocomplete)
  // Custom option
  | 'custom';

export interface ThemePreviewColors {
  bg: string;
  accent: string;
  darkBg: string;
  darkAccent?: string;
}

export interface ColorThemeDefinition {
  id: ColorTheme;
  name: string;
  description: string;
  previewColors: ThemePreviewColors;
}

// Thinking level for Claude model (budget token allocation)
export type ThinkingLevel = 'none' | 'low' | 'medium' | 'high' | 'ultrathink';

// Model type shorthand
export type ModelTypeShort = 'haiku' | 'sonnet' | 'opus';

// Phase-based model configuration for Auto profile
// Each phase can use a different model optimized for that task type
export interface PhaseModelConfig {
  spec: ModelTypeShort;       // Spec creation (discovery, requirements, context)
  planning: ModelTypeShort;   // Implementation planning
  coding: ModelTypeShort;     // Actual coding implementation
  qa: ModelTypeShort;         // QA review and fixing
}

// Thinking level configuration per phase
export interface PhaseThinkingConfig {
  spec: ThinkingLevel;
  planning: ThinkingLevel;
  coding: ThinkingLevel;
  qa: ThinkingLevel;
}

// Feature-specific model configuration (for non-pipeline features)
export interface FeatureModelConfig {
  insights: ModelTypeShort;    // Insights chat feature
  ideation: ModelTypeShort;    // Ideation generation
  roadmap: ModelTypeShort;     // Roadmap generation
  githubIssues: ModelTypeShort; // GitHub Issues automation
  githubPrs: ModelTypeShort;    // GitHub PR review automation
  utility: ModelTypeShort;      // Utility agents (commit message, merge resolver)
}

// Feature-specific thinking level configuration
export interface FeatureThinkingConfig {
  insights: ThinkingLevel;
  ideation: ThinkingLevel;
  roadmap: ThinkingLevel;
  githubIssues: ThinkingLevel;
  githubPrs: ThinkingLevel;
  utility: ThinkingLevel;
}

// Agent verbosity level for explanations and responses
export type AgentVerbosityLevel = 'minimal' | 'concise' | 'normal' | 'detailed' | 'verbose';

// Agent risk tolerance for decision-making
export type AgentRiskTolerance = 'cautious' | 'balanced' | 'aggressive';

// Project maturity level affecting risk decisions
export type AgentProjectType = 'greenfield' | 'established' | 'legacy';

// Coding style preferences learned from project conventions
export interface AgentCodingStylePreferences {
  indentation?: 'spaces' | 'tabs' | 'auto';
  quoteStyle?: 'single' | 'double' | 'auto';
  lineLength?: number | null;
  namingConvention?: 'snake_case' | 'camelCase' | 'PascalCase' | 'auto';
  commentDensity?: 'minimal' | 'normal' | 'verbose';
  typeHints?: boolean;
}

// Agent profile for preset model/thinking configurations
// All profiles have per-phase configuration (phaseModels/phaseThinking)
export interface AgentProfile {
  id: string;
  name: string;
  description: string;
  model: ModelTypeShort;           // Primary model (shown in profile card)
  thinkingLevel: ThinkingLevel;    // Primary thinking level (shown in profile card)
  icon?: string;                   // Lucide icon name
  // Per-phase configuration - all profiles now have this
  phaseModels?: PhaseModelConfig;
  phaseThinking?: PhaseThinkingConfig;
  /** @deprecated Use phaseModels and phaseThinking for per-phase configuration. Will be removed in v3.0. */
  isAutoProfile?: boolean;
}

export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  colorTheme?: ColorTheme;
  defaultModel: string;
  agentFramework: string;
  // Autonomy level (AUTO_CODE_AUTONOMY) — how independent agents are. See ADR-006.
  autonomyLevel?: 'off' | 'claude' | 'safe' | 'bold';
  pythonPath?: string;
  gitPath?: string;
  githubCLIPath?: string;
  claudePath?: string;
  autoBuildPath?: string;
  autoUpdateAutoBuild: boolean;
  autoNameTerminals: boolean;
  notifications: NotificationSettings;
  // Global API keys (used as defaults for all projects)
  globalClaudeOAuthToken?: string;
  globalOpenAIApiKey?: string;
  globalAnthropicApiKey?: string;
  globalGoogleApiKey?: string;
  globalGroqApiKey?: string;
  globalOpenRouterApiKey?: string;
  // Graphiti LLM provider settings (legacy)
  graphitiLlmProvider?: 'openai' | 'anthropic' | 'google' | 'groq' | 'ollama';
  ollamaBaseUrl?: string;
  // Memory/Graphiti configuration (app-wide, set during onboarding)
  memoryEnabled?: boolean;
  memoryEmbeddingProvider?: GraphitiEmbeddingProvider;
  memoryOllamaEmbeddingModel?: string;
  memoryOllamaEmbeddingDim?: number;
  memoryVoyageApiKey?: string;
  memoryVoyageEmbeddingModel?: string;
  memoryAzureApiKey?: string;
  memoryAzureBaseUrl?: string;
  memoryAzureEmbeddingDeployment?: string;
  // Agent Memory Access (MCP) - app-wide defaults
  graphitiMcpEnabled?: boolean;
  graphitiMcpUrl?: string;
  // Onboarding wizard completion state
  onboardingCompleted?: boolean;
  // Selected AI provider (anthropic, openrouter, groq, etc.)
  selectedProviderId?: string;
  // Backend AI engine provider used for runtime routing
  aiProvider?: AIEngineProvider;
  // Fallback model ID to use if primary model unavailable
  fallbackModelId?: string;
  // Selected agent profile for preset model/thinking configurations
  selectedAgentProfile?: string;
  // Custom phase configuration for Auto profile (overrides defaults)
  customPhaseModels?: PhaseModelConfig;
  customPhaseThinking?: PhaseThinkingConfig;
  // Feature-specific configuration (insights, ideation, roadmap)
  featureModels?: FeatureModelConfig;
  featureThinking?: FeatureThinkingConfig;
  // Changelog preferences
  changelogFormat?: ChangelogFormat;
  changelogAudience?: ChangelogAudience;
  changelogEmojiLevel?: ChangelogEmojiLevel;
  // UI Scale setting (75-200%, default 100)
  uiScale?: number;
  // Beta updates opt-in (receive pre-release updates)
  betaUpdates?: boolean;
  // Migration flags (internal use)
  _migratedAgentProfileToAuto?: boolean;
  _migratedDefaultModelSync?: boolean;
  // Language preference for UI (i18n)
  language?: SupportedLanguage;
  // Developer tools preferences
  preferredIDE?: SupportedIDE;
  customIDEPath?: string;      // For 'custom' IDE
  preferredTerminal?: SupportedTerminal;
  customTerminalPath?: string; // For 'custom' terminal
  // Agent behavior preferences (adaptive personality system)
  agentVerbosity?: AgentVerbosityLevel;
  agentRiskTolerance?: AgentRiskTolerance;
  agentProjectType?: AgentProjectType;
  agentCodingStyle?: AgentCodingStylePreferences;
  agentUserInstructions?: string[]; // Explicit user preferences (e.g., "be more cautious")
  // YOLO mode: invoke Claude with --dangerously-skip-permissions flag
  dangerouslySkipPermissions?: boolean;
  // Anonymous error reporting (Sentry) - enabled by default to help improve the app
  sentryEnabled?: boolean;
  // Auto-name Claude terminals based on initial message (only triggers once per session)
  autoNameClaudeTerminals?: boolean;
  // Track which version warnings have been shown (e.g., ["2.7.5"])
  seenVersionWarnings?: string[];
  // Sidebar collapsed state (icons only when true)
  sidebarCollapsed?: boolean;
  // Keyboard shortcuts customization
  keyboardShortcuts?: Record<KeyboardShortcutAction, KeyCombination>;
  // Recent actions for quick actions menu (persisted between sessions)
  recentActions?: RecentAction[];
  /**
   * Whether feedback collection is enabled.
   * Defaults to `true` (opt-out model: feedback is collected unless the user disables it).
   * When `undefined`, callers should treat it as `true`.
   */
  feedbackEnabled?: boolean;
  /** GPU acceleration mode for terminal WebGL rendering */
  gpuAcceleration?: GpuAcceleration;
}

// Auto-Code Source Environment Configuration (for auto-claude repo .env)
export interface SourceEnvConfig {
  // Claude Authentication (required for ideation, roadmap generation, etc.)
  hasClaudeToken: boolean;
  claudeOAuthToken?: string;

  // Source path info
  sourcePath?: string;
  envExists: boolean;
}

export interface SourceEnvCheckResult {
  hasToken: boolean;
  sourcePath?: string;
  error?: string;
}

// Provider Settings for Multi-Model Support (used by ProviderSettingsSection)
export interface ProviderSettings {
  provider?: AIEngineProvider;
  autonomyLevel?: AutonomyLevel;
  codexModel?: string;
  openaiApiKey?: string;
  googleApiKey?: string;
  openrouterApiKey?: string;
  zhipuaiApiKey?: string;
  plannerModel?: string;
  coderModel?: string;
  qaModel?: string;
  runtimeMode?: AgentRuntimeMode;
  plannerRuntimeMode?: AgentRuntimeMode;
  coderRuntimeMode?: AgentRuntimeMode;
  qaReviewerRuntimeMode?: AgentRuntimeMode;
  qaFixerRuntimeMode?: AgentRuntimeMode;
  runtimeFallbackEnabled?: boolean;
  cliRunnerRouterEnabled?: boolean;
}

/**
 * User-facing autonomy level (ADR-006), the primary autonomy knob. Maps to the
 * backend ``AUTO_CODE_AUTONOMY`` env var. The direct-API promotion gate is always
 * enforced under ``safe`` — only providers with recorded evidence are promoted.
 */
export type AutonomyLevel = 'off' | 'claude' | 'safe' | 'bold';

// ============================================
// Keyboard Shortcuts Types
// ============================================

export type KeyboardShortcutAction =
  | 'commandPalette'
  | 'quickActions'
  | 'createTask'
  | 'batchQA'
  | 'batchStatusUpdate';

export type KeyCombination = string;

export interface KeyboardShortcut {
  action: KeyboardShortcutAction;
  keyCombination: KeyCombination;
  description: string;
}

export interface KeyboardShortcuts {
  shortcuts: Record<KeyboardShortcutAction, KeyCombination>;
}

export const DEFAULT_KEYBOARD_SHORTCUTS: Record<KeyboardShortcutAction, KeyCombination> = {
  commandPalette: 'Cmd+K',
  quickActions: 'Cmd+.',
  createTask: 'Cmd+N',
  batchQA: 'Cmd+Shift+Q',
  batchStatusUpdate: 'Cmd+Shift+S'
};

// ============================================
// AI Provider Configuration (Backend .env sync)
// ============================================

export type AIEngineProvider = 'claude' | 'codex' | 'openai' | 'google' | 'litellm' | 'openrouter' | 'zhipuai' | 'ollama';
export type AgentRuntimeMode = 'full_autonomous' | 'analysis_only' | 'patch_proposal' | 'generic_edit';

export interface AIProviderConfig {
  provider: AIEngineProvider;
  autonomyLevel?: AutonomyLevel;
  anthropicApiKey?: string;
  claudeModel?: string;
  codexModel?: string;
  openaiApiKey?: string;
  openaiModel?: string;
  openaiBaseUrl?: string;
  googleApiKey?: string;
  googleModel?: string;
  litellmModel?: string;
  litellmApiBase?: string;
  litellmApiKey?: string;
  openrouterApiKey?: string;
  openrouterModel?: string;
  openrouterBaseUrl?: string;
  zhipuaiApiKey?: string;
  zhipuaiModel?: string;
  ollamaModel?: string;
  ollamaBaseUrl?: string;
  // Per-agent model overrides
  plannerModel?: string;
  coderModel?: string;
  qaModel?: string;
  // Runtime mode overrides
  runtimeMode?: AgentRuntimeMode;
  plannerRuntimeMode?: AgentRuntimeMode;
  coderRuntimeMode?: AgentRuntimeMode;
  qaReviewerRuntimeMode?: AgentRuntimeMode;
  qaFixerRuntimeMode?: AgentRuntimeMode;
  runtimeFallbackEnabled?: boolean;
  cliRunnerRouterEnabled?: boolean;
}

export interface ProviderConfigValidation {
  isValid: boolean;
  errors: string[];
  availableProviders: AIEngineProvider[];
}

export interface ProviderRuntimeDiagnostics {
  smokeScope?: string;
  providerContractHealth?: ProviderContractHealth;
  requestedRuntimeMode?: string;
  validatedRuntimeMode?: string;
  validatedRequirements?: string[];
  requestedRuntimeCapabilities?: string[];
  validatedRuntimeCapabilities?: string[];
  validatedRuntimeMissingCapabilities?: string[];
  validatedRuntimeExecution?: ProviderValidatedRuntimeExecution | null;
  miniPipeline?: ProviderMiniPipelineDiagnostics | null;
  providerE2eSuite?: ProviderE2eSuiteDiagnostics;
  providerLiveFaultProbes?: ProviderLiveFaultProbeDiagnostics;
  providerLiveTaskFamilies?: ProviderLiveTaskFamilyDiagnostics;
  providerNegativeFixtures?: ProviderNegativeFixtureDiagnostics;
  providerRunHistory?: ProviderRunHistoryDiagnostics;
  providerAutonomousReadiness?: ProviderAutonomousReadinessDiagnostics;
  providerAutonomousPromotionGate?: ProviderAutonomousPromotionGateDiagnostics;
  providerReliability?: ProviderReliabilityDiagnostics;
  fullAutonomousMissingCapabilities?: string[];
  note?: string;
}

export interface ProviderContractHealth {
  status?: string;
  smokeScope?: string;
  reason?: string;
  message?: string;
  toolCallSupport?: string;
  toolResultSupport?: string;
  fallback?: string;
  fallbackReason?: string;
  recoveryStatus?: string;
}

export interface ProviderValidatedRuntimeExecution {
  status?: string;
  stopReason?: string;
  loop?: string;
  actionCount?: number;
  failedActionCount?: number;
  nativeToolFallbackCount?: number;
  nativeToolFallbacks?: ProviderValidatedRuntimeFallback[];
  toolCounts?: Record<string, number>;
  resumePolicy?: ProviderValidatedRuntimeResumePolicy;
  toolLoopContract?: ProviderValidatedToolLoopContract;
  transactionBatchContract?: ProviderValidatedTransactionBatchContract;
}

export interface ProviderValidatedRuntimeFallback {
  provider?: string;
  fromLoop?: string;
  toLoop?: string;
  reason?: string;
  message?: string;
  toolSchemaCount?: number;
}

export interface ProviderValidatedRuntimeResumePolicy {
  status?: string;
  strategy?: string;
  canResume?: boolean;
  finishBlocked?: boolean;
  nextIteration?: number;
  requiredResolutionActionKinds?: string[];
  requiredArtifacts?: string[];
  unresolvedPartialFailureIds?: string[];
  unresolvedTransactionGroupIds?: string[];
  openTransactionBatchIds?: string[];
}

export interface ProviderValidatedToolLoopContract {
  status?: string;
  toolCallSupport?: string;
  toolResultSupport?: string;
  fallback?: string;
  fallbackReason?: string;
  recoveryStatus?: string;
  blockingReason?: string;
}

export interface ProviderValidatedTransactionBatchContract {
  status?: string;
  batchBoundaryGuard?: string;
  transactionBatchCount?: number;
  openTransactionBatchIds?: string[];
  boundaryErrorCount?: number;
  boundaryErrorReasons?: string[];
  boundaryPreferredStrategy?: string;
  boundaryRequiredActionKinds?: string[];
  boundaryResolutionStrategies?: string[];
  stagedWorkspaceGuardStatuses?: string[];
  stagedDriftPaths?: string[];
  stagedIsolationStatuses?: string[];
  stagedWorkspaceRestoreStatuses?: string[];
  stagedBaselinePaths?: string[];
  batchLifecycleActions?: string[];
  batchLifecycleStatuses?: string[];
  committedMutationSnapshotIds?: string[];
  commitOperationIds?: string[];
}

export interface ProviderMiniPipelineDiagnostics {
  status?: string;
  task?: string;
  testCommand?: string;
  testExitCode?: number;
  changedFiles?: string[];
  reason?: string;
  phases?: ProviderMiniPipelinePhase[];
}

export interface ProviderMiniPipelinePhase {
  name?: string;
  status?: string;
}

export interface ProviderReliabilityDiagnostics {
  provider?: string;
  suite?: string;
  status?: string;
  observedCaseCount?: number;
  passedCaseCount?: number;
  requiredCaseCount?: number;
  uncoveredCases?: string[];
  cases?: ProviderReliabilityCase[];
}

export interface ProviderReliabilityCase {
  case?: string;
  status?: string;
  source?: string;
}

export interface ProviderAutonomousReadinessDiagnostics {
  status?: string;
  provider?: string;
  source?: string;
  recommendation?: string;
  recommendationReasons?: string[];
  blockers?: string[];
  warnings?: string[];
  evidence?: string[];
  requirements?: ProviderAutonomousReadinessRequirements;
  missingRequirements?: string[];
  nextActions?: string[];
}

export interface ProviderAutonomousReadinessRequirements {
  minStableRuns?: number;
  observedRecentWindow?: number;
  observedConsecutivePasses?: number;
  historyStabilityComplete?: boolean;
  requiredLiveFaultCases?: string[];
  liveFaultCoveredCases?: string[];
  liveFaultMissingCases?: string[];
  liveFaultCoverageComplete?: boolean;
  requiredLiveTaskFamilies?: string[];
  liveTaskCoveredFamilies?: string[];
  liveTaskMissingFamilies?: string[];
  liveTaskFamilyCoverageComplete?: boolean;
  lastRunAt?: string;
  maxHistoryAgeSeconds?: number;
  historyFreshnessComplete?: boolean;
}

export interface ProviderAutonomousReadinessRequirementsSnake {
  min_stable_runs?: number;
  observed_recent_window?: number;
  observed_consecutive_passes?: number;
  history_stability_complete?: boolean;
  required_live_fault_cases?: string[];
  live_fault_covered_cases?: string[];
  live_fault_missing_cases?: string[];
  live_fault_coverage_complete?: boolean;
  required_live_task_families?: string[];
  live_task_covered_families?: string[];
  live_task_missing_families?: string[];
  live_task_family_coverage_complete?: boolean;
  last_run_at?: string;
  max_history_age_seconds?: number;
  history_freshness_complete?: boolean;
}

export type ProviderAutonomousReadinessRequirementsPayload =
  | ProviderAutonomousReadinessRequirements
  | ProviderAutonomousReadinessRequirementsSnake;

export interface ProviderAutonomousPromotionGateDiagnostics {
  status?: string;
  provider?: string;
  source?: string;
  promotionReady?: boolean;
  requiredReliabilityCases?: string[];
  passedReliabilityCases?: string[];
  missingReliabilityCases?: string[];
  requiredE2eRuns?: string[];
  observedE2eRuns?: string[];
  missingE2eRuns?: string[];
  readinessStatus?: string;
  readinessMissingRequirements?: string[];
}

export interface ProviderE2eSuiteDiagnostics {
  status?: string;
  runs?: ProviderE2eSuiteRun[];
}

export interface ProviderE2eSuiteRun {
  runtimeMode?: string;
  status?: string;
  message?: string;
  reason?: string;
}

export interface ProviderNegativeFixtureDiagnostics {
  status?: string;
  provider?: string;
  source?: string;
  coveredCases?: string[];
}

export interface ProviderLiveFaultProbeDiagnostics {
  status?: string;
  provider?: string;
  source?: string;
  enabled?: boolean;
  coveredCases?: string[];
  requiredEnv?: string[];
  missingEnv?: string[];
  probes?: ProviderLiveFaultProbeCase[];
}

export interface ProviderLiveFaultProbeCase {
  case?: string;
  status?: string;
  source?: string;
  reason?: string;
  envName?: string;
}

export interface ProviderLiveTaskFamilyDiagnostics {
  status?: string;
  provider?: string;
  source?: string;
  enabled?: boolean;
  coveredFamilies?: string[];
  failedFamilies?: string[];
  requiredEnv?: string[];
  missingEnv?: string[];
  families?: ProviderLiveTaskFamilyCase[];
}

export interface ProviderLiveTaskFamilyCase {
  family?: string;
  status?: string;
  source?: string;
  reason?: string;
  runtimeMode?: string;
  envName?: string;
}

export interface ProviderRunHistoryDiagnostics {
  status?: string;
  provider?: string;
  runtimeMode?: string;
  totalRuns?: number;
  passedRuns?: number;
  failedRuns?: number;
  lastStatus?: string;
  lastReliabilityStatus?: string;
  lastProviderE2eStatus?: string;
  e2eCaseCount?: number;
  e2ePassedCaseCount?: number;
  e2eFailedCaseCount?: number;
  e2eCasePassRatePercent?: number | null;
  reliabilityObservedCaseCount?: number;
  reliabilityPassedCaseCount?: number;
  reliabilityRequiredCaseCount?: number;
  reliabilityCasePassRatePercent?: number | null;
  lastLiveFaultProbeStatus?: string;
  liveFaultProbeEnabledRuns?: number;
  liveFaultProbePassedRuns?: number;
  liveFaultProbeCoveredCases?: string[];
  lastLiveTaskFamilyStatus?: string;
  liveTaskFamilyEnabledRuns?: number;
  liveTaskFamilyPassedRuns?: number;
  liveTaskFamilyCoveredFamilies?: string[];
  liveTaskFamilyFailedFamilies?: string[];
  passRatePercent?: number | null;
  recentPassRatePercent?: number | null;
  observedLiveFaultCaseCount?: number;
  requiredLiveFaultCaseCount?: number;
  liveFaultProbeCaseCoveragePercent?: number | null;
  observedLiveTaskFamilyCount?: number;
  requiredLiveTaskFamilyCount?: number;
  liveTaskFamilyCoveragePercent?: number | null;
  trend?: string;
  trendReason?: string;
  recentWindow?: number;
  recentPassedRuns?: number;
  recentFailedRuns?: number;
  recentRuns?: ProviderRunHistoryRecentRun[];
  consecutivePasses?: number;
  consecutiveFailures?: number;
  path?: string;
  reason?: string;
}

export interface ProviderRunHistoryRecentRun {
  timestamp?: string;
  status?: string;
  runtimeMode?: string;
  model?: string;
  reliabilityStatus?: string;
  providerE2eStatus?: string;
  liveFaultProbeStatus?: string;
  liveTaskFamilyStatus?: string;
}

export interface ProviderConnectionTestResult {
  success: boolean;
  provider: AIEngineProvider | string;
  model?: string | null;
  runtimeMode: string;
  message: string;
  responseExcerpt?: string | null;
  errorDetails?: string | null;
  runtimeDiagnostics?: ProviderRuntimeDiagnostics | null;
}

export interface RuntimeMcpBridgePlanRow {
  provider: string;
  runtime_mode: string;
  strategy: string;
  available: boolean;
  status: string;
  action_required: string;
  recommended_runtime_path: string;
  available_servers: string[];
  unavailable_servers: string[];
  native_required_servers: string[];
  local_bridge_required_servers: string[];
  external_bridge_required_servers: string[];
  external_bridge_ready_servers: string[];
  external_bridge_adapter_missing_servers?: string[];
  external_bridge_unsupported_transport_servers?: string[];
  unsupported_servers: string[];
  bridged_servers: string[];
  local_bridged_servers: string[];
  external_bridged_servers: string[];
  executable_external_tools: string[];
}

export interface RuntimeMcpBridgePermissionRow {
  server: string;
  display_name: string;
  bridge_path: string;
  status: string;
  permission_enforced: boolean;
  strict_allowlist_configured: boolean;
  allowlist_source: string;
  allowed_permissions?: string[];
  audit_required: boolean;
  audit_artifact: string;
  tool_count?: number | null;
  tool_policy_coverage: string;
  permissions: string[];
  mutating_permissions: string[];
  required_gates: string[];
  satisfied_gates: string[];
  missing_gates: string[];
  reason: string;
}

export interface RuntimeExternalMcpHealthRow {
  server: string;
  display_name: string;
  bridgeable: boolean;
  client_enabled: boolean;
  server_enabled: boolean;
  configured: boolean;
  status: string;
  reason: string;
  transport?: string | null;
  command?: string | null;
  args: string[];
  url?: string | null;
  enabled_env?: string | null;
  required_env: string[];
  missing_env: string[];
  concrete_servers: string[];
  execution_supported: boolean;
  executable_tools: string[];
  executable_tool_count: number;
  adapter_registered?: boolean;
  adapter_name?: string | null;
  adapter_transport?: string | null;
  adapter_exposed_server?: string | null;
  transport_supported?: boolean;
  supported_transports?: string[];
}

export interface RuntimeExternalMcpContractCheckRow {
  server: string;
  ok: boolean;
  status: string;
  reason: string;
  transport?: string | null;
  adapter_tools: string[];
  server_tools: string[];
  adapter_tools_missing_on_server: string[];
  server_tools_missing_in_adapter: string[];
  error?: string | null;
  failure_stage?: string | null;
  failure_kind?: string | null;
}

export interface RuntimeExternalMcpSmokeSummary {
  total: number;
  ok: number;
  skipped: number;
  failed: number;
}

export interface RuntimeExternalMcpSmokeResult {
  external_mcp_contract_checks: RuntimeExternalMcpContractCheckRow[];
  summary: RuntimeExternalMcpSmokeSummary;
}

export interface RuntimeFallbackMatrixRow {
  provider: string;
  phase: string;
  requested_mode: string;
  fail_fast_selected_mode: string;
  fallback_selected_mode: string;
  fallback_applied: boolean;
  fallback_reason: string;
  missing_capabilities: string[];
  compatible_fallbacks: string[];
  runner_candidate_ids_by_mode: Record<string, string[]>;
  selected_mode_runner_candidates: string[];
}

export interface RuntimeSubagentMatrixRow {
  provider: string;
  runtime_mode: string;
  strategy: string;
  available: boolean;
  reason: string;
  required_capabilities: string[];
  missing_capabilities: string[];
  available_capabilities: string[];
  max_attempts: number;
  merge_policy: string;
  artifact_support: boolean;
}

export interface RuntimeSubagentMutationPolicyRow {
  provider: string;
  runtime_mode: string;
  mutating_subagents_enabled: boolean;
  status: string;
  transaction_boundary_required: boolean;
  parent_approval_required: boolean;
  merge_protocol: string;
  required_gates: string[];
  satisfied_gates: string[];
  missing_gates: string[];
  reason: string;
}

export interface RuntimePolicyMatrixRow {
  phase: string;
  provider: string;
  required_runtime_mode: string;
  selected_runtime_mode: string;
  fallback_allowed: boolean;
  fallback_modes: string[];
  requires_full_autonomous: boolean;
  requires_cli_runner: boolean;
  runner_candidates: string[];
  policy: string;
  reason: string;
  autonomous_readiness_required?: boolean;
  autonomous_policy_gate?: string;
  autonomous_readiness_status?: string;
  autonomous_readiness_recommendation?: string;
  autonomous_readiness_recommendation_reasons?: string[];
  autonomous_readiness_blockers?: string[];
  autonomous_readiness_warnings?: string[];
  autonomous_readiness_requirements?: ProviderAutonomousReadinessRequirementsPayload;
  autonomous_readiness_missing_requirements?: string[];
  autonomous_promotion_gate?: string;
  autonomous_promotion_ready?: boolean;
  autonomous_promotion_missing_reliability_cases?: string[];
  autonomous_promotion_missing_e2e_runs?: string[];
}

export interface RuntimeCapabilityMatrixRow {
  provider: string;
  readiness: string;
  full_autonomous_ready: boolean;
  direct_full_autonomous: string;
  recommended_runtime_mode: string;
  generic_edit: string;
  analysis_only: string;
  patch_proposal: string;
  mcp_tools: string;
  subagents: string;
  cli_runner_candidates: string[];
  autonomous_readiness_required?: boolean;
  autonomous_policy_gate?: string;
  autonomous_readiness_status?: string;
  autonomous_readiness_recommendation?: string;
  autonomous_readiness_recommendation_reasons?: string[];
  autonomous_readiness_blockers?: string[];
  autonomous_readiness_warnings?: string[];
  autonomous_readiness_evidence?: string[];
  autonomous_readiness_requirements?: ProviderAutonomousReadinessRequirementsPayload;
  autonomous_readiness_missing_requirements?: string[];
  autonomous_readiness_next_actions?: string[];
  autonomous_promotion_gate?: string;
  autonomous_promotion_ready?: boolean;
  autonomous_promotion_missing_reliability_cases?: string[];
  autonomous_promotion_missing_e2e_runs?: string[];
  blockers: string[];
  warnings: string[];
  notes: string;
}

export interface RuntimeEvalMatrixRow {
  case_id: string;
  runtime_mode: string;
  required_for_full_autonomous: boolean;
  providers: string[];
  required_artifacts: string[];
}

export interface RuntimeEvalHistoryProviderRow {
  provider: string;
  status: string;
  total_runs: number;
  passed_runs: number;
  failed_runs: number;
  pass_rate_percent?: number | null;
  recent_pass_rate_percent?: number | null;
  e2e_case_count?: number;
  e2e_passed_case_count?: number;
  e2e_failed_case_count?: number;
  e2e_case_pass_rate_percent?: number | null;
  reliability_observed_case_count?: number;
  reliability_passed_case_count?: number;
  reliability_required_case_count?: number;
  reliability_case_pass_rate_percent?: number | null;
  observed_live_fault_case_count?: number;
  required_live_fault_case_count?: number;
  live_fault_probe_case_coverage_percent?: number | null;
  observed_live_task_family_count?: number;
  required_live_task_family_count?: number;
  live_task_family_coverage_percent?: number | null;
  last_status?: string | null;
  last_reliability_status?: string | null;
  last_provider_e2e_status?: string | null;
  last_model?: string | null;
  last_run_at?: string | null;
}

export interface RuntimeEvalHistoryRow {
  case_id: string;
  runtime_mode: string;
  history_path: string;
  status: string;
  total_runs: number;
  passed_runs: number;
  failed_runs: number;
  missing_providers: string[];
  providers: RuntimeEvalHistoryProviderRow[];
}

export interface RuntimeComparativeEvalMatrixRow {
  provider: string;
  runtime_path: string;
  quality_status: string;
  quality_score?: number | null;
  quality_score_source?: string | null;
  quality_trend?: string | null;
  quality_delta_percent?: number | null;
  stability_score?: number | null;
  stability_trend?: string | null;
  stability_delta_percent?: number | null;
  cost_status: string;
  cost_pricing_model?: string | null;
  cost_pricing_provider?: string | null;
  cost_actual_usd?: number | null;
  cost_actual_formatted?: string | null;
  cost_actual_input_tokens?: number | null;
  cost_actual_output_tokens?: number | null;
  cost_observed_run_count?: number | null;
  cost_estimate_usd?: number | null;
  cost_estimate_formatted?: string | null;
  cost_estimate_input_tokens?: number | null;
  cost_estimate_output_tokens?: number | null;
  cost_trend?: string | null;
  cost_delta_usd?: number | null;
  cost_delta_formatted?: string | null;
  safety_status: string;
  safety_score?: number | null;
  safety_score_source?: string | null;
  safety_trend?: string | null;
  safety_delta_percent?: number | null;
  evidence_source: string;
  required_before_full_autonomous: boolean;
  blockers: string[];
}

export interface CliRunnerContractMatrixRow {
  runner_id: string;
  display_name: string;
  runner_status: string;
  contract_status: string;
  required_facets: string[];
  missing_contract_facets: string[];
  facets: Record<string, string>;
  adapter_required: boolean;
  supported_runtime_modes: string[];
  artifact_contract: string;
}

export interface RuntimeControlPlaneDiagnostics {
  cli_runner_contract_matrix?: CliRunnerContractMatrixRow[];
  runtime_fallback_matrix?: RuntimeFallbackMatrixRow[];
  mcp_bridge_plan_matrix?: RuntimeMcpBridgePlanRow[];
  mcp_bridge_permission_matrix?: RuntimeMcpBridgePermissionRow[];
  external_mcp_server_health?: RuntimeExternalMcpHealthRow[];
  runtime_subagent_matrix?: RuntimeSubagentMatrixRow[];
  runtime_subagent_mutation_policy?: RuntimeSubagentMutationPolicyRow[];
  runtime_policy_matrix?: RuntimePolicyMatrixRow[];
  runtime_capability_matrix?: RuntimeCapabilityMatrixRow[];
  runtime_eval_matrix?: RuntimeEvalMatrixRow[];
  runtime_eval_history?: RuntimeEvalHistoryRow[];
  runtime_comparative_eval_matrix?: RuntimeComparativeEvalMatrixRow[];
  recommendations?: Record<string, string>;
}
