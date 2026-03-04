/**
 * Security Configuration Types
 *
 * Types for security settings including command allowlists,
 * filesystem permissions, sandbox levels, and audit logs.
 */

// ============================================
// Security Level Presets
// ============================================

/**
 * Security level presets for different risk tolerances
 */
export type SecurityLevel = 'paranoid' | 'standard' | 'permissive';

/**
 * Security level preset definition
 */
export interface SecurityLevelPreset {
  id: SecurityLevel;
  name: string;
  description: string;
  icon?: string; // Lucide icon name
  commandAllowlist: string[]; // Default commands for this level
  filesystemAccess: FilesystemPermissionLevel;
  sandboxEnabled: boolean;
  apiRestrictions: boolean;
}

/**
 * Filesystem permission level
 */
export type FilesystemPermissionLevel = 'none' | 'read-only' | 'restricted' | 'full';

// ============================================
// Security Profile
// ============================================

/**
 * Command allowlist entry
 */
export interface CommandAllowlistEntry {
  /** Command name or pattern (e.g., 'git', 'npm', 'pip') */
  command: string;
  /** Whether this command is allowed */
  allowed: boolean;
  /** Optional arguments pattern (e.g., '--only-read') */
  argsPattern?: string;
  /** User-defined label for grouping */
  label?: string;
  /** When this entry was added */
  addedAt?: number; // Unix timestamp
}

/**
 * Filesystem permission rule
 */
export interface FilesystemPermissionRule {
  /** Path pattern (e.g., '/tmp/**', '*.log') */
  path: string;
  /** Permission level for this path */
  level: 'read' | 'write' | 'execute' | 'deny';
  /** Whether this is a user-defined rule */
  isCustom?: boolean;
}

/**
 * API restriction rule
 */
export interface APIRestrictionRule {
  /** API domain or endpoint pattern (e.g., 'api.anthropic.com') */
  endpoint: string;
  /** Whether this API is allowed */
  allowed: boolean;
  /** Allowed operations (e.g., ['GET', 'POST']) */
  allowedOperations?: string[];
  /** Rate limit (requests per minute) */
  rateLimit?: number;
}

/**
 * Security Profile - main security configuration
 *
 * Most fields are optional to support both simplified profiles
 * (from IPC handlers) and full detailed profiles.
 */
export interface SecurityProfile {
  /** Profile version (for migrations) */
  version?: number;
  /** Current security level preset */
  level: SecurityLevel;
  /** Command allowlist (allowed commands for agents) */
  commandAllowlist: CommandAllowlistEntry[];
  /** Filesystem permission rules */
  filesystemPermissions?: FilesystemPermissionRule[];
  /** Overall filesystem access level */
  filesystemAccessLevel?: FilesystemPermissionLevel;
  /** Whether OS-level sandbox is enabled */
  sandboxEnabled?: boolean;
  /** Sandbox level (affects which operations are blocked) */
  sandboxLevel?: 'full' | 'partial' | 'none';
  /** API restriction rules */
  apiRestrictions?: APIRestrictionRule[];
  /** Whether API restrictions are enforced */
  apiRestrictionsEnabled?: boolean;
  /** Whether to warn about risky operations */
  warnOnRiskyOperations?: boolean;
  /** Whether to require confirmation for destructive operations */
  requireConfirmationForDestructive?: boolean;
  /** Custom security notes or warnings */
  notes?: string;
  /** Last time this profile was modified */
  lastModified?: number; // Unix timestamp

  // Convenience fields used by simplified IPC handlers
  /** Whether filesystem access is restricted */
  filesystemRestricted?: boolean;
  /** Whether API access is restricted */
  apiRestricted?: boolean;
  /** Last update timestamp (alternative to lastModified) */
  updatedAt?: number;
  /** Security level name (alternative to level for display) */
  securityLevel?: SecurityLevel;
}

// ============================================
// Audit Log Types
// ============================================

/**
 * Security event severity
 */
export type SecurityEventSeverity = 'info' | 'warning' | 'critical';

/**
 * Security event categories
 */
export type SecurityEventCategory =
  | 'command_execution'      // Command was executed (blocked or allowed)
  | 'filesystem_access'       // File/directory was accessed
  | 'api_call'                // External API was called
  | 'permission_change'       // Security settings were modified
  | 'sandbox_violation'       // Sandbox was violated
  | 'profile_loaded'          // Security profile was loaded
  | 'profile_exported'        // Security profile was exported
  | 'risk_detected';          // Risky operation was detected

/**
 * Security audit log entry
 */
export interface SecurityAuditLog {
  /** Unique identifier for this log entry */
  id: string;
  /** Event timestamp (Unix timestamp) */
  timestamp: number;
  /** Event category */
  category: SecurityEventCategory;
  /** Event severity level */
  severity: SecurityEventSeverity;
  /** Human-readable event description */
  message: string;
  /** Related command (if applicable) */
  command?: string;
  /** Related file path (if applicable) */
  filePath?: string;
  /** Related API endpoint (if applicable) */
  apiEndpoint?: string;
  /** Whether the operation was allowed or blocked */
  allowed: boolean;
  /** Security rule that triggered this log */
  ruleId?: string;
  /** Additional context (JSON string) */
  context?: string;
  /** Project ID where this event occurred */
  projectId?: string;
  /** Agent type that caused this event */
  agentType?: string; // 'planner' | 'coder' | 'qa_reviewer' | 'qa_fixer'
  /** Session ID for correlation */
  sessionId?: string;

  // Extended fields for detailed log views
  /** Operation name/description */
  operation?: string;
  /** Structured event details */
  details?: Record<string, unknown>;
  /** Event metadata (e.g., security level changes) */
  metadata?: Record<string, unknown>;
}

// ============================================
// Security Export Types
// ============================================

/**
 * Exported security configuration (for compliance)
 */
export interface SecurityExport {
  /** Export format version */
  version: string;
  /** When this export was created */
  exportedAt: number; // Unix timestamp
  /** The security profile being exported */
  profile: SecurityProfile;
  /** Recent audit log entries (optional) */
  auditLogs?: SecurityAuditLog[];
  /** Export metadata */
  metadata: {
    /** Application version */
    appVersion: string;
    /** Project name */
    projectName?: string;
    /** Project path */
    projectPath?: string;
    /** Export reason (manual, compliance, backup) */
    reason?: string;
    /** Export format identifier */
    format?: string;
    /** Export source identifier */
    source?: string;
  };
}

// ============================================
// Security State Types
// ============================================

/**
 * Security validation result
 */
export interface SecurityValidationResult {
  /** Whether the configuration is valid */
  valid: boolean;
  /** Validation errors (if any) */
  errors: string[];
  /** Validation warnings (if any) */
  warnings: string[];
  /** Risk score (0-100, higher = more risky) */
  riskScore: number;
}

/**
 * Security risk assessment
 */
export interface SecurityRiskAssessment {
  /** Overall risk level */
  level: 'low' | 'medium' | 'high' | 'critical';
  /** Risk score (0-100) */
  score: number;
  /** Specific risk factors detected */
  factors: RiskFactor[];
  /** Recommended security level */
  recommendedLevel: SecurityLevel;
  /** Recommended actions */
  recommendations: string[];
}

/**
 * Individual risk factor
 */
export interface RiskFactor {
  /** Factor category */
  category: 'command' | 'filesystem' | 'api' | 'sandbox' | 'general';
  /** Risk description */
  description: string;
  /** Severity of this risk factor */
  severity: 'low' | 'medium' | 'high';
  /** Which setting causes this risk */
  affectedSetting?: string;
}
