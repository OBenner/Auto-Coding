/**
 * Security Profile IPC Handlers
 *
 * IPC handlers for security profile management:
 * - security:getProfile - Get current security profile
 * - security:saveProfile - Save/update security profile
 * - security:getAuditLogs - Get security audit logs
 * - security:exportConfig - Export security configuration
 * - security:resetToDefault - Reset to default security settings
 * - security:validateCommand - Validate a command against allowlist
 */

import { ipcMain, dialog, app } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type { SecurityProfile, SecurityAuditLog } from '../../shared/types/security';
import { promises as fs } from 'fs';
import path from 'path';

const SECURITY_PROFILE_FILE = '.auto-claude-security.json';
const AUDIT_LOG_FILE = '.auto-claude-audit.json';
/**
 * Get security profile file path for current project
 */
function getSecurityProfilePath(): string {
  // TODO: Get from project store or app settings
  // For now, use app.getPath('userData') as fallback
  return path.join(app.getPath('userData'), SECURITY_PROFILE_FILE);
}

/**
 * Get audit log file path for current project
 */
function getAuditLogPath(): string {
  return path.join(app.getPath('userData'), AUDIT_LOG_FILE);
}

/**
 * Create a fresh default security profile
 */
function createDefaultProfile(): SecurityProfile {
  return {
    level: 'standard',
    commandAllowlist: [],
    filesystemRestricted: false,
    apiRestricted: false,
    updatedAt: Date.now()
  };
}

/**
 * Register all security-related IPC handlers
 */
export function registerSecurityHandlers(): void {
  /**
   * Get current security profile
   */
  ipcMain.handle(
    IPC_CHANNELS.SECURITY_GET_PROFILE,
    async (): Promise<IPCResult<SecurityProfile>> => {
      try {
        const profilePath = getSecurityProfilePath();

        // Check if profile exists
        try {
          const data = await fs.readFile(profilePath, 'utf-8');
          const profile = JSON.parse(data) as SecurityProfile;
          return { success: true, data: profile };
        } catch {
          // File doesn't exist or can't be read - return default profile
          return { success: true, data: createDefaultProfile() };
        }
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load security profile'
        };
      }
    }
  );

  /**
   * Save/update security profile
   */
  ipcMain.handle(
    IPC_CHANNELS.SECURITY_SAVE_PROFILE,
    async (_, profileData: Partial<SecurityProfile>): Promise<IPCResult<SecurityProfile>> => {
      try {
        const profilePath = getSecurityProfilePath();

        // Load existing profile or create default
        let existingProfile: SecurityProfile;
        try {
          const data = await fs.readFile(profilePath, 'utf-8');
          existingProfile = JSON.parse(data) as SecurityProfile;
        } catch {
          existingProfile = createDefaultProfile();
        }

        // Merge with new data
        const updatedProfile: SecurityProfile = {
          ...existingProfile,
          ...profileData,
          updatedAt: Date.now()
        };

        // Write updated profile
        await fs.writeFile(profilePath, JSON.stringify(updatedProfile, null, 2), 'utf-8');

        return { success: true, data: updatedProfile };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save security profile'
        };
      }
    }
  );

  /**
   * Get security audit logs
   */
  ipcMain.handle(
    IPC_CHANNELS.SECURITY_GET_AUDIT_LOGS,
    async (_event, options?: { limit?: number; offset?: number }): Promise<IPCResult<{
      logs: SecurityAuditLog[];
      total: number;
      hasMore: boolean;
    }>> => {
      try {
        const auditLogPath = getAuditLogPath();

        // Check if audit log exists
        try {
          const data = await fs.readFile(auditLogPath, 'utf-8');
          const allLogs = JSON.parse(data) as SecurityAuditLog[];

          // Apply pagination
          const offset = options?.offset || 0;
          const limit = options?.limit || 100;
          const paginatedLogs = allLogs.slice(offset, offset + limit);

          return {
            success: true,
            data: {
              logs: paginatedLogs,
              total: allLogs.length,
              hasMore: offset + limit < allLogs.length
            }
          };
        } catch {
          // File doesn't exist - return empty logs
          return {
            success: true,
            data: {
              logs: [],
              total: 0,
              hasMore: false
            }
          };
        }
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load audit logs'
        };
      }
    }
  );

  /**
   * Export security configuration
   * - Opens a save dialog for user to choose export location
   * - Exports security settings as JSON for compliance purposes
   */
  ipcMain.handle(
    IPC_CHANNELS.SECURITY_EXPORT_CONFIG,
    async (_event, options?: { includeAuditLogs?: boolean; auditLogLimit?: number }): Promise<IPCResult<{ filePath: string }>> => {
      try {
        // Open save dialog
        const result = await dialog.showSaveDialog({
          title: 'Export Security Configuration',
          defaultPath: `security-config-${new Date().toISOString().split('T')[0]}.json`,
          filters: [
            { name: 'JSON Files', extensions: ['json'] },
            { name: 'All Files', extensions: ['*'] }
          ]
        });

        if (result.canceled || !result.filePath) {
          return { success: false, error: 'Export cancelled' };
        }

        // Validate export file path to prevent path traversal
        const resolvedPath = path.resolve(result.filePath);
        if (!resolvedPath.endsWith('.json')) {
          return { success: false, error: 'Export file must have .json extension' };
        }

        // Load security profile
        const profilePath = getSecurityProfilePath();
        let profile: SecurityProfile;
        try {
          const data = await fs.readFile(profilePath, 'utf-8');
          profile = JSON.parse(data) as SecurityProfile;
        } catch {
          profile = createDefaultProfile();
        }

        // Optionally include audit logs
        let auditLogs: SecurityAuditLog[] = [];
        if (options?.includeAuditLogs) {
          const auditLogPath = getAuditLogPath();
          try {
            const data = await fs.readFile(auditLogPath, 'utf-8');
            const allLogs = JSON.parse(data) as SecurityAuditLog[];
            const limit = options.auditLogLimit || 100;
            auditLogs = allLogs.slice(0, limit);
          } catch {
            // No audit logs to include
          }
        }

        // Generate export data
        const exportData = {
          exportedAt: new Date().toISOString(),
          version: '1.0.0',
          profile,
          auditLogs: auditLogs.length > 0 ? auditLogs : undefined
        };

        // Write to validated export file path
        await fs.writeFile(resolvedPath, JSON.stringify(exportData, null, 2), 'utf-8');

        return { success: true, data: { filePath: resolvedPath } };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to export security configuration'
        };
      }
    }
  );

  /**
   * Reset security profile to defaults
   */
  ipcMain.handle(
    IPC_CHANNELS.SECURITY_RESET_TO_DEFAULT,
    async (): Promise<IPCResult<SecurityProfile>> => {
      try {
        const defaultProfile = createDefaultProfile();
        const profilePath = getSecurityProfilePath();
        await fs.writeFile(profilePath, JSON.stringify(defaultProfile, null, 2), 'utf-8');

        return { success: true, data: defaultProfile };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to reset security profile'
        };
      }
    }
  );

  /**
   * Validate a command against current allowlist
   */
  ipcMain.handle(
    IPC_CHANNELS.SECURITY_VALIDATE_COMMAND,
    async (_event, command: string): Promise<IPCResult<{ allowed: boolean; reason?: string }>> => {
      try {
        if (!command || command.trim() === '') {
          return { success: true, data: { allowed: false, reason: 'Empty command' } };
        }

        // Load current profile
        const profilePath = getSecurityProfilePath();
        let profile: SecurityProfile;
        try {
          const data = await fs.readFile(profilePath, 'utf-8');
          profile = JSON.parse(data) as SecurityProfile;
        } catch {
          // No profile exists - allow by default
          return { success: true, data: { allowed: true } };
        }

        // Check if command is in allowlist
        const commandName = command.trim().split(' ')[0]; // Get first word (command name)
        const allowedEntry = profile.commandAllowlist.find(
          entry => entry.command === commandName && entry.allowed
        );

        if (!allowedEntry) {
          // Check if command is explicitly blocked
          const blockedEntry = profile.commandAllowlist.find(
            entry => entry.command === commandName && !entry.allowed
          );
          if (blockedEntry) {
            return {
              success: true,
              data: { allowed: false, reason: 'Command is blocked in security profile' }
            };
          }

          // Command not in allowlist - check profile level
          if (profile.level === 'paranoid') {
            return {
              success: true,
              data: { allowed: false, reason: 'Command not in allowlist (paranoid mode)' }
            };
          }

          // Standard/permissive mode - allow unknown commands
          return { success: true, data: { allowed: true } };
        }

        return { success: true, data: { allowed: true } };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to validate command'
        };
      }
    }
  );
}
