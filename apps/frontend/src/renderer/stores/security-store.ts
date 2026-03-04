import { create } from 'zustand';
import type {
  SecurityProfile,
  SecurityAuditLog,
  SecurityExport,
  SecurityValidationResult,
  SecurityLevel,
  CommandAllowlistEntry,
  FilesystemPermissionRule,
  APIRestrictionRule
} from '../../shared/types';

// ============================================
// Security State Interface
// ============================================

interface SecurityState {
  // Security Profile state
  profile: SecurityProfile | null;
  isProfileLoading: boolean;
  profileError: string | null;

  // Audit Log state
  auditLogs: SecurityAuditLog[];
  auditLogsLoading: boolean;
  auditLogsError: string | null;
  auditLogsTotal: number;
  auditLogsHasMore: boolean;

  // Security Export state
  isExporting: boolean;
  exportError: string | null;

  // Command Validation state
  isValidatingCommand: boolean;
  validationResult: SecurityValidationResult | null;

  // Actions - Security Profile
  setProfile: (profile: SecurityProfile | null) => void;
  setProfileLoading: (loading: boolean) => void;
  setProfileError: (error: string | null) => void;
  loadProfile: () => Promise<void>;
  saveProfile: (updates: Partial<SecurityProfile>) => Promise<boolean>;
  resetToDefault: () => Promise<boolean>;
  updateSecurityLevel: (level: SecurityLevel) => Promise<boolean>;

  // Actions - Command Allowlist
  addCommandToAllowlist: (command: string, allowed?: boolean, label?: string) => Promise<boolean>;
  removeCommandFromAllowlist: (command: string) => Promise<boolean>;
  updateCommandInAllowlist: (command: string, updates: Partial<CommandAllowlistEntry>) => Promise<boolean>;

  // Actions - Filesystem Permissions
  addFilesystemPermission: (path: string, level: 'read' | 'write' | 'execute' | 'deny') => Promise<boolean>;
  removeFilesystemPermission: (path: string) => Promise<boolean>;
  updateFilesystemPermission: (path: string, level: 'read' | 'write' | 'execute' | 'deny') => Promise<boolean>;

  // Actions - API Restrictions
  addAPIRestriction: (endpoint: string, allowed?: boolean, allowedOperations?: string[]) => Promise<boolean>;
  removeAPIRestriction: (endpoint: string) => Promise<boolean>;
  updateAPIRestriction: (endpoint: string, updates: Partial<APIRestrictionRule>) => Promise<boolean>;

  // Actions - Audit Logs
  setAuditLogs: (logs: SecurityAuditLog[], total: number, hasMore: boolean) => void;
  setAuditLogsLoading: (loading: boolean) => void;
  setAuditLogsError: (error: string | null) => void;
  loadAuditLogs: (options?: {
    limit?: number;
    offset?: number;
    category?: string;
    severity?: string;
    startDate?: number;
    endDate?: number;
  }) => Promise<void>;
  clearAuditLogs: () => void;

  // Actions - Security Export
  setExporting: (exporting: boolean) => void;
  setExportError: (error: string | null) => void;
  exportConfig: (options?: {
    includeAuditLogs?: boolean;
    auditLogLimit?: number;
    reason?: string;
  }) => Promise<SecurityExport | null>;

  // Actions - Command Validation
  setValidatingCommand: (validating: boolean) => void;
  setValidationResult: (result: SecurityValidationResult | null) => void;
  validateCommand: (command: string) => Promise<SecurityValidationResult | null>;
}

// ============================================
// Security Store
// ============================================

export const useSecurityStore = create<SecurityState>((set, get) => ({
  // Initial state
  profile: null,
  isProfileLoading: false,
  profileError: null,

  auditLogs: [],
  auditLogsLoading: false,
  auditLogsError: null,
  auditLogsTotal: 0,
  auditLogsHasMore: false,

  isExporting: false,
  exportError: null,

  isValidatingCommand: false,
  validationResult: null,

  // Security Profile actions
  setProfile: (profile) => set({ profile }),

  setProfileLoading: (isProfileLoading) => set({ isProfileLoading }),

  setProfileError: (profileError) => set({ profileError }),

  loadProfile: async () => {
    const store = get();
    store.setProfileLoading(true);
    store.setProfileError(null);

    try {
      const result = await window.electronAPI.security.getProfile();
      if (result.success && result.data) {
        store.setProfile(result.data);
      } else {
        store.setProfileError(result.error || 'Failed to load security profile');
      }
    } catch (error) {
      store.setProfileError(error instanceof Error ? error.message : 'Failed to load security profile');
    } finally {
      store.setProfileLoading(false);
    }
  },

  saveProfile: async (updates: Partial<SecurityProfile>): Promise<boolean> => {
    const store = get();
    store.setProfileLoading(true);
    store.setProfileError(null);

    try {
      const result = await window.electronAPI.security.saveProfile(updates);
      if (result.success && result.data) {
        store.setProfile(result.data);
        return true;
      }
      store.setProfileError(result.error || 'Failed to save security profile');
      return false;
    } catch (error) {
      store.setProfileError(error instanceof Error ? error.message : 'Failed to save security profile');
      return false;
    } finally {
      store.setProfileLoading(false);
    }
  },

  resetToDefault: async (): Promise<boolean> => {
    const store = get();
    store.setProfileLoading(true);
    store.setProfileError(null);

    try {
      const result = await window.electronAPI.security.resetToDefault();
      if (result.success && result.data) {
        store.setProfile(result.data);
        return true;
      }
      store.setProfileError(result.error || 'Failed to reset security profile');
      return false;
    } catch (error) {
      store.setProfileError(error instanceof Error ? error.message : 'Failed to reset security profile');
      return false;
    } finally {
      store.setProfileLoading(false);
    }
  },

  updateSecurityLevel: async (level: SecurityLevel): Promise<boolean> => {
    const store = get();
    return await store.saveProfile({ level });
  },

  // Command Allowlist actions
  addCommandToAllowlist: async (
    command: string,
    allowed: boolean = true,
    label?: string
  ): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const newEntry: CommandAllowlistEntry = {
      command,
      allowed,
      label,
      addedAt: Date.now()
    };

    const updatedAllowlist = [...store.profile.commandAllowlist, newEntry];
    return await store.saveProfile({ commandAllowlist: updatedAllowlist });
  },

  removeCommandFromAllowlist: async (command: string): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const updatedAllowlist = store.profile.commandAllowlist.filter(
      (entry) => entry.command !== command
    );
    return await store.saveProfile({ commandAllowlist: updatedAllowlist });
  },

  updateCommandInAllowlist: async (
    command: string,
    updates: Partial<CommandAllowlistEntry>
  ): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const updatedAllowlist = store.profile.commandAllowlist.map((entry) =>
      entry.command === command ? { ...entry, ...updates } : entry
    );
    return await store.saveProfile({ commandAllowlist: updatedAllowlist });
  },

  // Filesystem Permissions actions
  addFilesystemPermission: async (
    path: string,
    level: 'read' | 'write' | 'execute' | 'deny'
  ): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const newRule: FilesystemPermissionRule = {
      path,
      level,
      isCustom: true
    };

    const updatedPermissions = [...(store.profile.filesystemPermissions || []), newRule];
    return await store.saveProfile({ filesystemPermissions: updatedPermissions });
  },

  removeFilesystemPermission: async (path: string): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const updatedPermissions = (store.profile.filesystemPermissions || []).filter(
      (rule) => rule.path !== path
    );
    return await store.saveProfile({ filesystemPermissions: updatedPermissions });
  },

  updateFilesystemPermission: async (
    path: string,
    level: 'read' | 'write' | 'execute' | 'deny'
  ): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const updatedPermissions = (store.profile.filesystemPermissions || []).map((rule) =>
      rule.path === path ? { ...rule, level } : rule
    );
    return await store.saveProfile({ filesystemPermissions: updatedPermissions });
  },

  // API Restrictions actions
  addAPIRestriction: async (
    endpoint: string,
    allowed: boolean = true,
    allowedOperations?: string[]
  ): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const newRule: APIRestrictionRule = {
      endpoint,
      allowed,
      allowedOperations
    };

    const updatedRestrictions = [...(store.profile.apiRestrictions || []), newRule];
    return await store.saveProfile({ apiRestrictions: updatedRestrictions });
  },

  removeAPIRestriction: async (endpoint: string): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const updatedRestrictions = (store.profile.apiRestrictions || []).filter(
      (rule) => rule.endpoint !== endpoint
    );
    return await store.saveProfile({ apiRestrictions: updatedRestrictions });
  },

  updateAPIRestriction: async (
    endpoint: string,
    updates: Partial<APIRestrictionRule>
  ): Promise<boolean> => {
    const store = get();
    if (!store.profile) {
      store.setProfileError('No security profile loaded');
      return false;
    }

    const updatedRestrictions = (store.profile.apiRestrictions || []).map((rule) =>
      rule.endpoint === endpoint ? { ...rule, ...updates } : rule
    );
    return await store.saveProfile({ apiRestrictions: updatedRestrictions });
  },

  // Audit Logs actions
  setAuditLogs: (auditLogs, auditLogsTotal, auditLogsHasMore) =>
    set({ auditLogs, auditLogsTotal, auditLogsHasMore }),

  setAuditLogsLoading: (auditLogsLoading) => set({ auditLogsLoading }),

  setAuditLogsError: (auditLogsError) => set({ auditLogsError }),

  loadAuditLogs: async (options?) => {
    const store = get();
    store.setAuditLogsLoading(true);
    store.setAuditLogsError(null);

    try {
      const result = await window.electronAPI.security.getAuditLogs(options);
      if (result.success && result.data) {
        store.setAuditLogs(
          result.data.logs,
          result.data.total,
          result.data.hasMore
        );
      } else {
        store.setAuditLogsError(result.error || 'Failed to load audit logs');
      }
    } catch (error) {
      store.setAuditLogsError(error instanceof Error ? error.message : 'Failed to load audit logs');
    } finally {
      store.setAuditLogsLoading(false);
    }
  },

  clearAuditLogs: () => {
    set({
      auditLogs: [],
      auditLogsTotal: 0,
      auditLogsHasMore: false
    });
  },

  // Security Export actions
  setExporting: (isExporting) => set({ isExporting }),

  setExportError: (exportError) => set({ exportError }),

  exportConfig: async (options?): Promise<SecurityExport | null> => {
    const store = get();
    store.setExporting(true);
    store.setExportError(null);

    try {
      const result = await window.electronAPI.security.exportConfig(options);
      if (result.success && result.data) {
        return result.data;
      }
      store.setExportError(result.error || 'Failed to export security configuration');
      return null;
    } catch (error) {
      store.setExportError(error instanceof Error ? error.message : 'Failed to export security configuration');
      return null;
    } finally {
      store.setExporting(false);
    }
  },

  // Command Validation actions
  setValidatingCommand: (isValidatingCommand) => set({ isValidatingCommand }),

  setValidationResult: (validationResult) => set({ validationResult }),

  validateCommand: async (command: string): Promise<SecurityValidationResult | null> => {
    const store = get();
    store.setValidatingCommand(true);
    store.setValidationResult(null);

    try {
      const result = await window.electronAPI.security.validateCommand(command);
      if (result.success && result.data) {
        const validationResult: SecurityValidationResult = {
          valid: result.data.allowed,
          errors: result.data.allowed ? [] : [result.data.reason || 'Command not allowed'],
          warnings: [],
          riskScore: result.data.allowed ? 0 : 100
        };
        store.setValidationResult(validationResult);
        return validationResult;
      }
      const errorResult: SecurityValidationResult = {
        valid: false,
        errors: [result.error || 'Failed to validate command'],
        warnings: [],
        riskScore: 100
      };
      store.setValidationResult(errorResult);
      return errorResult;
    } catch (error) {
      const errorResult: SecurityValidationResult = {
        valid: false,
        errors: [error instanceof Error ? error.message : 'Failed to validate command'],
        warnings: [],
        riskScore: 100
      };
      store.setValidationResult(errorResult);
      return errorResult;
    } finally {
      store.setValidatingCommand(false);
    }
  }
}));
