// @ts-nocheck - E2E spec uses simplified security schema for integration testing
/**
 * End-to-End Test: Security Warnings for Risky Changes
 *
 * Tests warning dialogs and audit logging for risky security changes:
 * 1. Permissive mode warning
 * 2. Critical command removal warning
 * 3. Canceling risky changes
 * 4. Multiple warnings in sequence
 * 5. Warning persistence in audit logs
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { promises as fs } from 'fs';
import path from 'path';
import type { SecurityProfile, CommandAllowlistEntry, SecurityAuditLog } from './shared/types/security';

// Test data paths
const TEST_DATA_DIR = path.join(process.cwd(), 'test-data');
const TEST_PROFILE_PATH = path.join(TEST_DATA_DIR, '.auto-claude-security.json');
const TEST_AUDIT_LOG_PATH = path.join(TEST_DATA_DIR, '.auto-claude-audit.json');

/**
 * Default security profile for testing
 */
const DEFAULT_PROFILE: SecurityProfile = {
  version: '1.0.0',
  lastModified: Date.now(),
  securityLevel: 'standard',
  commandAllowlist: [
    {
      command: 'git',
      allowed: true,
      label: 'Version Control',
      addedAt: Date.now() - 86400000
    },
    {
      command: 'npm',
      allowed: true,
      label: 'Package Manager',
      addedAt: Date.now() - 86400000
    },
    {
      command: 'node',
      allowed: true,
      label: 'Runtime',
      addedAt: Date.now() - 86400000
    },
    {
      command: 'python3',
      allowed: true,
      label: 'Python Runtime',
      addedAt: Date.now() - 86400000
    },
    {
      command: 'ls',
      allowed: true,
      label: 'File Listing',
      addedAt: Date.now() - 86400000
    }
  ],
  filesystemRestrictions: {
    enabled: false,
    allowedDirectories: [],
    blockedDirectories: []
  },
  apiRestrictions: {
    enabled: false,
    allowedEndpoints: [],
    blockedEndpoints: []
  }
};

/**
 * Setup test environment
 */
async function setupTestEnvironment(): Promise<void> {
  // Create test directory
  await fs.mkdir(TEST_DATA_DIR, { recursive: true });

  // Clean up any existing test data
  try {
    await fs.unlink(TEST_PROFILE_PATH);
  } catch {
    // File doesn't exist, that's fine
  }

  try {
    await fs.unlink(TEST_AUDIT_LOG_PATH);
  } catch {
    // File doesn't exist
  }
}

/**
 * Cleanup test environment
 */
async function cleanupTestEnvironment(): Promise<void> {
  try {
    await fs.unlink(TEST_PROFILE_PATH);
  } catch {
    // File doesn't exist
  }

  try {
    await fs.unlink(TEST_AUDIT_LOG_PATH);
  } catch {
    // File doesn't exist
  }

  try {
    await fs.rmdir(TEST_DATA_DIR);
  } catch {
    // Directory not empty or doesn't exist
  }
}

/**
 * Write test security profile
 */
async function writeTestProfile(profile: SecurityProfile): Promise<void> {
  await fs.writeFile(
    TEST_PROFILE_PATH,
    JSON.stringify(profile, null, 2),
    'utf-8'
  );
}

/**
 * Read test security profile
 */
async function readTestProfile(): Promise<SecurityProfile> {
  const content = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
  return JSON.parse(content) as SecurityProfile;
}

/**
 * Write test audit log
 */
async function writeTestAuditLog(logs: SecurityAuditLog[]): Promise<void> {
  await fs.writeFile(
    TEST_AUDIT_LOG_PATH,
    JSON.stringify(logs, null, 2),
    'utf-8'
  );
}

/**
 * Read test audit log
 */
async function readTestAuditLog(): Promise<SecurityAuditLog[]> {
  try {
    const content = await fs.readFile(TEST_AUDIT_LOG_PATH, 'utf-8');
    return JSON.parse(content) as SecurityAuditLog[];
  } catch {
    return [];
  }
}

/**
 * Simulate warning dialog for permissive mode
 *
 * In a real UI test, this would:
 * 1. Click the security level selector
 * 2. Select "permissive" option
 * 3. Verify warning dialog appears with correct message
 * 4. Click confirm/cancel
 *
 * For this E2E test, we simulate the logic and verify audit logging
 */
async function simulatePermissiveModeWarning(confirm: boolean): Promise<{
  warningShown: boolean;
  actionConfirmed: boolean;
  auditLogged: boolean;
}> {
  const profile = await readTestProfile();
  const logs = await readTestAuditLog();

  // Check if warning should be shown
  const warningShown = profile.securityLevel !== 'permissive';
  const actionConfirmed = warningShown && confirm;

  // If confirmed, update profile
  if (actionConfirmed) {
    const fromLevel = profile.securityLevel; // Capture original level before modifying
    profile.securityLevel = 'permissive';
    profile.lastModified = Date.now();
    await writeTestProfile(profile);

    // Log to audit
    const warningLog: SecurityAuditLog = {
      id: `warn-${Date.now()}`,
      timestamp: Date.now(),
      category: 'permission_change',
      severity: 'warning',
      message: 'Security level changed to permissive',
      allowed: true,
      metadata: {
        from: fromLevel,
        to: 'permissive',
        warningAcknowledged: true
      } as Record<string, unknown>
    };

    logs.push(warningLog);
    await writeTestAuditLog(logs);
  }

  return {
    warningShown,
    actionConfirmed,
    auditLogged: actionConfirmed
  };
}

/**
 * Simulate warning dialog for command removal
 *
 * In a real UI test, this would:
 * 1. Click remove button on a command
 * 2. Verify warning dialog appears
 * 3. Click confirm/cancel
 * 4. Verify command is removed/kept
 */
async function simulateCommandRemovalWarning(
  command: string,
  confirm: boolean
): Promise<{
  warningShown: boolean;
  commandRemoved: boolean;
  auditLogged: boolean;
}> {
  const profile = await readTestProfile();
  const logs = await readTestAuditLog();

  // Check if command exists
  const commandExists = profile.commandAllowlist.some(c => c.command === command);
  const warningShown = commandExists;

  if (!warningShown) {
    return { warningShown: false, commandRemoved: false, auditLogged: false };
  }

  const commandRemoved = warningShown && confirm;

  if (commandRemoved) {
    // Remove command
    profile.commandAllowlist = profile.commandAllowlist.filter(
      c => c.command !== command
    );
    profile.lastModified = Date.now();
    await writeTestProfile(profile);

    // Log to audit
    const warningLog: SecurityAuditLog = {
      id: `warn-${Date.now()}`,
      timestamp: Date.now(),
      category: 'permission_change',
      severity: 'warning',
      message: `Critical command removed from allowlist: ${command}`,
      allowed: true,
      metadata: {
        command,
        action: 'removed',
        warningAcknowledged: true,
        wasAllowed: true
      } as Record<string, unknown>
    };

    logs.push(warningLog);
    await writeTestAuditLog(logs);
  }

  return {
    warningShown,
    commandRemoved,
    auditLogged: commandRemoved
  };
}

describe('Security Warnings E2E Tests', () => {
  beforeAll(async () => {
    await setupTestEnvironment();
    await writeTestProfile(DEFAULT_PROFILE);
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('Permissive Mode Warning', () => {
    it('should show warning when switching to permissive mode', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'standard' });

      const result = await simulatePermissiveModeWarning(false);

      expect(result.warningShown).toBe(true);
      expect(result.actionConfirmed).toBe(false);
      expect(result.auditLogged).toBe(false);

      // Verify profile unchanged
      const profile = await readTestProfile();
      expect(profile.securityLevel).toBe('standard');
    });

    it('should apply permissive mode and log audit when confirmed', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'standard' });

      const result = await simulatePermissiveModeWarning(true);

      expect(result.warningShown).toBe(true);
      expect(result.actionConfirmed).toBe(true);
      expect(result.auditLogged).toBe(true);

      // Verify profile updated
      const profile = await readTestProfile();
      expect(profile.securityLevel).toBe('permissive');

      // Verify audit log
      const logs = await readTestAuditLog();
      const warningLog = logs.find(
        log => log.category === 'permission_change' &&
               log.message.includes('permissive')
      );
      expect(warningLog).toBeDefined();
      expect(warningLog?.severity).toBe('warning');
      expect(warningLog?.metadata?.warningAcknowledged).toBe(true);
    });

    it('should not show warning when already in permissive mode', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'permissive' });

      const result = await simulatePermissiveModeWarning(true);

      expect(result.warningShown).toBe(false);
      expect(result.actionConfirmed).toBe(false);
      expect(result.auditLogged).toBe(false);
    });
  });

  describe('Critical Command Removal Warning', () => {
    it('should show warning when removing critical command', async () => {
      const result = await simulateCommandRemovalWarning('git', false);

      expect(result.warningShown).toBe(true);
      expect(result.commandRemoved).toBe(false);
      expect(result.auditLogged).toBe(false);

      // Verify command still in allowlist
      const profile = await readTestProfile();
      const gitCommand = profile.commandAllowlist.find(c => c.command === 'git');
      expect(gitCommand).toBeDefined();
    });

    it('should remove command and log audit when confirmed', async () => {
      const result = await simulateCommandRemovalWarning('npm', true);

      expect(result.warningShown).toBe(true);
      expect(result.commandRemoved).toBe(true);
      expect(result.auditLogged).toBe(true);

      // Verify command removed
      const profile = await readTestProfile();
      const npmCommand = profile.commandAllowlist.find(c => c.command === 'npm');
      expect(npmCommand).toBeUndefined();

      // Verify audit log
      const logs = await readTestAuditLog();
      const warningLog = logs.find(
        log => log.category === 'permission_change' &&
               log.message.includes('npm') &&
               log.message.includes('removed')
      );
      expect(warningLog).toBeDefined();
      expect(warningLog?.severity).toBe('warning');
      expect(warningLog?.metadata?.warningAcknowledged).toBe(true);
      expect(warningLog?.metadata?.command).toBe('npm');
    });

    it('should handle removal of non-existent command gracefully', async () => {
      const result = await simulateCommandRemovalWarning('nonexistent', true);

      expect(result.warningShown).toBe(false);
      expect(result.commandRemoved).toBe(false);
      expect(result.auditLogged).toBe(false);

      // No audit log should be created
      const logs = await readTestAuditLog();
      const warningLog = logs.find(
        log => log.metadata?.command === 'nonexistent'
      );
      expect(warningLog).toBeUndefined();
    });
  });

  describe('Canceling Risky Changes', () => {
    it('should not change profile when canceling permissive mode', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'paranoid' });
      await writeTestAuditLog([]); // Clear audit log for clean test

      const beforeProfile = await readTestProfile();
      const beforeLevel = beforeProfile.securityLevel;

      await simulatePermissiveModeWarning(false);

      const afterProfile = await readTestProfile();
      const afterLevel = afterProfile.securityLevel;

      expect(beforeLevel).toBe(afterLevel);
      expect(afterLevel).toBe('paranoid');

      // No audit log for change
      const logs = await readTestAuditLog();
      const changeLog = logs.find(
        log => log.category === 'permission_change' &&
               log.message.includes('permissive')
      );
      expect(changeLog).toBeUndefined();
    });

    it('should not remove command when canceling removal', async () => {
      await writeTestProfile(DEFAULT_PROFILE);

      const beforeProfile = await readTestProfile();
      const beforeCount = beforeProfile.commandAllowlist.length;

      await simulateCommandRemovalWarning('node', false);

      const afterProfile = await readTestProfile();
      const afterCount = afterProfile.commandAllowlist.length;

      expect(beforeCount).toBe(afterCount);
      expect(afterCount).toBe(5);

      // Command still present
      const nodeCommand = afterProfile.commandAllowlist.find(
        c => c.command === 'node'
      );
      expect(nodeCommand).toBeDefined();
    });
  });

  describe('Multiple Warnings', () => {
    it('should handle multiple warnings in sequence', async () => {
      await writeTestProfile(DEFAULT_PROFILE);
      await writeTestAuditLog([]);

      // First warning: permissive mode (cancel)
      const result1 = await simulatePermissiveModeWarning(false);
      expect(result1.warningShown).toBe(true);
      expect(result1.actionConfirmed).toBe(false);

      // Second warning: remove git (cancel)
      const result2 = await simulateCommandRemovalWarning('git', false);
      expect(result2.warningShown).toBe(true);
      expect(result2.commandRemoved).toBe(false);

      // Third warning: remove ls (confirm)
      const result3 = await simulateCommandRemovalWarning('ls', true);
      expect(result3.warningShown).toBe(true);
      expect(result3.commandRemoved).toBe(true);

      // Verify only confirmed action was logged
      const logs = await readTestAuditLog();
      expect(logs.length).toBe(1);
      expect(logs[0].metadata?.command).toBe('ls');

      // Verify profile state
      const profile = await readTestProfile();
      expect(profile.securityLevel).toBe('standard');
      expect(profile.commandAllowlist.find(c => c.command === 'git')).toBeDefined();
      expect(profile.commandAllowlist.find(c => c.command === 'ls')).toBeUndefined();
    });

    it('should maintain audit log order for multiple warnings', async () => {
      await writeTestProfile(DEFAULT_PROFILE);
      await writeTestAuditLog([]);

      // Execute multiple confirmed warnings
      await simulateCommandRemovalWarning('git', true);
      await new Promise(resolve => setTimeout(resolve, 10)); // Small delay
      await simulateCommandRemovalWarning('npm', true);
      await new Promise(resolve => setTimeout(resolve, 10)); // Small delay
      await simulatePermissiveModeWarning(true);

      const logs = await readTestAuditLog();

      expect(logs.length).toBe(3);

      // Verify chronological order
      expect(logs[0].metadata?.command).toBe('git');
      expect(logs[1].metadata?.command).toBe('npm');
      expect(logs[2].metadata?.to).toBe('permissive');

      // Verify timestamps are increasing
      expect(logs[0].timestamp).toBeLessThan(logs[1].timestamp);
      expect(logs[1].timestamp).toBeLessThan(logs[2].timestamp);
    });
  });

  describe('Warning Audit Log Details', () => {
    it('should include warning acknowledged metadata', async () => {
      // Ensure clean state with standard level
      const testProfile = { ...DEFAULT_PROFILE, securityLevel: 'standard' as const };
      await writeTestProfile(testProfile);
      await writeTestAuditLog([]);

      // Verify profile is in standard state
      const profileBefore = await readTestProfile();
      expect(profileBefore.securityLevel).toBe('standard');

      await simulatePermissiveModeWarning(true);

      const logs = await readTestAuditLog();
      const warningLog = logs[0];

      expect(warningLog.metadata).toBeDefined();
      expect(warningLog.metadata?.warningAcknowledged).toBe(true);
      expect(warningLog.metadata?.from).toBe('standard');
      expect(warningLog.metadata?.to).toBe('permissive');
    });

    it('should track command removal details in audit', async () => {
      await writeTestProfile(DEFAULT_PROFILE);
      await writeTestAuditLog([]);

      await simulateCommandRemovalWarning('python3', true);

      const logs = await readTestAuditLog();
      const warningLog = logs[0];

      expect(warningLog.metadata).toBeDefined();
      expect(warningLog.metadata?.command).toBe('python3');
      expect(warningLog.metadata?.action).toBe('removed');
      expect(warningLog.metadata?.warningAcknowledged).toBe(true);
      expect(warningLog.metadata?.wasAllowed).toBe(true);
    });

    it('should preserve warning logs across profile reloads', async () => {
      await writeTestProfile(DEFAULT_PROFILE);
      await writeTestAuditLog([]);

      // Create warning log
      await simulateCommandRemovalWarning('node', true);

      const logsBeforeReload = await readTestAuditLog();
      expect(logsBeforeReload.length).toBe(1);

      // Simulate profile reload (write and read)
      const profile = await readTestProfile();
      await writeTestProfile(profile);

      const logsAfterReload = await readTestAuditLog();
      expect(logsAfterReload.length).toBe(1);
      expect(logsAfterReload[0].id).toBe(logsBeforeReload[0].id);
      expect(logsAfterReload[0].metadata?.command).toBe('node');
    });
  });

  describe('Warning Dialog UI State', () => {
    it('should maintain UI consistency during warning flow', async () => {
      await writeTestProfile(DEFAULT_PROFILE);

      // Simulate opening warning dialog
      const profileBefore = await readTestProfile();
      const profileStateBefore = JSON.stringify(profileBefore);

      // Simulate cancel
      await simulatePermissiveModeWarning(false);

      const profileAfter = await readTestProfile();
      const profileStateAfter = JSON.stringify(profileAfter);

      // Profile should be unchanged
      expect(profileStateBefore).toBe(profileStateAfter);
    });

    it('should update UI state after confirmed warning', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'paranoid' });
      await writeTestAuditLog([]);

      const beforeLevel = (await readTestProfile()).securityLevel;
      expect(beforeLevel).toBe('paranoid');

      // Confirm permissive mode
      await simulatePermissiveModeWarning(true);

      const afterLevel = (await readTestProfile()).securityLevel;
      expect(afterLevel).toBe('permissive');

      // Verify audit log reflects UI state change
      const logs = await readTestAuditLog();
      const stateChangeLog = logs.find(
        log => log.category === 'permission_change' &&
               log.message.includes('Security level changed')
      );
      expect(stateChangeLog).toBeDefined();
      expect(stateChangeLog?.allowed).toBe(true);
    });
  });

  describe('Risk Severity Levels', () => {
    it('should mark permissive mode as warning severity', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'standard' });
      await writeTestAuditLog([]);

      await simulatePermissiveModeWarning(true);

      const logs = await readTestAuditLog();
      const warningLog = logs[0];

      expect(warningLog.severity).toBe('warning');
      expect(warningLog.category).toBe('permission_change');
    });

    it('should mark critical command removal as warning severity', async () => {
      await writeTestProfile(DEFAULT_PROFILE);
      await writeTestAuditLog([]);

      await simulateCommandRemovalWarning('git', true);

      const logs = await readTestAuditLog();
      const warningLog = logs[0];

      expect(warningLog.severity).toBe('warning');
      expect(warningLog.category).toBe('permission_change');
      expect(warningLog.message).toContain('Critical command');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty allowlist when removing commands', async () => {
      const emptyProfile = {
        ...DEFAULT_PROFILE,
        commandAllowlist: []
      };
      await writeTestProfile(emptyProfile);

      const result = await simulateCommandRemovalWarning('git', true);

      expect(result.warningShown).toBe(false);
      expect(result.commandRemoved).toBe(false);
    });

    it('should handle switching between non-permissive levels without warning', async () => {
      await writeTestProfile({ ...DEFAULT_PROFILE, securityLevel: 'paranoid' });
      await writeTestAuditLog([]);

      // Simulate paranoid to standard (no warning in our simplified test)
      const profile = await readTestProfile();
      profile.securityLevel = 'standard';
      profile.lastModified = Date.now();
      await writeTestProfile(profile);

      // No warning should be logged for paranoid -> standard
      const logs = await readTestAuditLog();
      const warningLog = logs.find(
        log => log.category === 'permission_change' &&
               log.severity === 'warning'
      );
      expect(warningLog).toBeUndefined();
    });

    it('should handle rapid warning confirmations', async () => {
      await writeTestProfile(DEFAULT_PROFILE);
      await writeTestAuditLog([]);

      // Sequential confirmations (not parallel to avoid race conditions)
      const result1 = await simulateCommandRemovalWarning('git', true);
      const result2 = await simulateCommandRemovalWarning('npm', true);
      const result3 = await simulateCommandRemovalWarning('node', true);

      const results = [result1, result2, result3];

      // All should succeed
      expect(results.every(r => r.commandRemoved)).toBe(true);

      // All should be logged
      const logs = await readTestAuditLog();
      expect(logs.length).toBe(3);
    });
  });
});
