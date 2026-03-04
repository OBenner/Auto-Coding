import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  SecurityProfile,
  SecurityAuditLog,
  SecurityExport
} from '../../shared/types';

export interface SecurityAPI {
  // Security Profile Operations
  getProfile: () => Promise<IPCResult<SecurityProfile>>;
  saveProfile: (profile: Partial<SecurityProfile>) => Promise<IPCResult<SecurityProfile>>;
  resetToDefault: () => Promise<IPCResult<SecurityProfile>>;

  // Audit Log Operations
  getAuditLogs: (options?: {
    limit?: number;
    offset?: number;
    category?: string;
    severity?: string;
    startDate?: number;
    endDate?: number;
  }) => Promise<IPCResult<{
    logs: SecurityAuditLog[];
    total: number;
    hasMore: boolean;
  }>>;

  // Security Export
  exportConfig: (options?: {
    includeAuditLogs?: boolean;
    auditLogLimit?: number;
    reason?: string;
  }) => Promise<IPCResult<SecurityExport>>;

  // Security Validation
  validateCommand: (command: string) => Promise<IPCResult<{
    allowed: boolean;
    reason?: string;
    ruleId?: string;
  }>>;
}

export const createSecurityAPI = (): SecurityAPI => ({
  // Security Profile Operations
  getProfile: (): Promise<IPCResult<SecurityProfile>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SECURITY_GET_PROFILE),

  saveProfile: (profile: Partial<SecurityProfile>): Promise<IPCResult<SecurityProfile>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SECURITY_SAVE_PROFILE, profile),

  resetToDefault: (): Promise<IPCResult<SecurityProfile>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SECURITY_RESET_TO_DEFAULT),

  // Audit Log Operations
  getAuditLogs: (options?: {
    limit?: number;
    offset?: number;
    category?: string;
    severity?: string;
    startDate?: number;
    endDate?: number;
  }): Promise<IPCResult<{
    logs: SecurityAuditLog[];
    total: number;
    hasMore: boolean;
  }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SECURITY_GET_AUDIT_LOGS, options || {}),

  // Security Export
  exportConfig: (options?: {
    includeAuditLogs?: boolean;
    auditLogLimit?: number;
    reason?: string;
  }): Promise<IPCResult<SecurityExport>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SECURITY_EXPORT_CONFIG, options || {}),

  // Security Validation
  validateCommand: (command: string): Promise<IPCResult<{
    allowed: boolean;
    reason?: string;
    ruleId?: string;
  }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.SECURITY_VALIDATE_COMMAND, command)
});
