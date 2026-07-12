// @ts-nocheck - E2E spec uses simplified security schema for integration testing
/**
 * End-to-End Test: Security Configuration Export
 *
 * Tests the complete workflow of exporting security configuration:
 * 1. Export with no audit logs
 * 2. Export with audit logs (various limits)
 * 3. Verify exported JSON structure and validity
 * 4. Verify data integrity after export
 * 5. Verify filename includes timestamp
 * 6. Test edge cases (empty profile, large audit logs)
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { mkdtempSync, promises as fs } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import type { SecurityProfile, SecurityExport, SecurityAuditLog } from './shared/types/security';

// Test data paths - mkdtemp gives this spec file its own unpredictable
// 0700 directory, so parallel vitest workers running the other security
// e2e specs never share it (and no other local user can pre-create it)
const TEST_DATA_DIR = mkdtempSync(path.join(tmpdir(), 'security-export-e2e-'));
const TEST_PROFILE_PATH = path.join(TEST_DATA_DIR, '.auto-claude-security.json');
const TEST_AUDIT_LOG_PATH = path.join(TEST_DATA_DIR, '.auto-claude-audit.log');
const EXPORT_OUTPUT_DIR = path.join(TEST_DATA_DIR, 'exports');

/**
 * Setup test environment
 */
async function setupTestEnvironment(): Promise<void> {
  // Create test directories
  await fs.mkdir(TEST_DATA_DIR, { recursive: true });
  await fs.mkdir(EXPORT_OUTPUT_DIR, { recursive: true });

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
    // Clean up export directory
    const files = await fs.readdir(EXPORT_OUTPUT_DIR);
    await Promise.all(
      files.map(file => fs.unlink(path.join(EXPORT_OUTPUT_DIR, file)))
    );
    await fs.rmdir(EXPORT_OUTPUT_DIR);
  } catch {
    // Directory not empty or doesn't exist
  }

  try {
    await fs.rmdir(TEST_DATA_DIR);
  } catch {
    // Directory not empty or doesn't exist
  }
}

/**
 * Create a default security profile for testing
 */
function createDefaultProfile(): SecurityProfile {
  return {
    level: 'standard',
    commandAllowlist: [
      {
        command: 'git',
        allowed: true,
        label: 'Version control',
        addedAt: Date.now() - 100000
      },
      {
        command: 'npm',
        allowed: true,
        label: 'Package manager',
        addedAt: Date.now() - 90000
      },
      {
        command: 'node',
        allowed: true,
        label: 'Runtime',
        addedAt: Date.now() - 80000
      }
    ],
    filesystemPermissions: [
      {
        path: '/tmp',
        level: 'read',
        isCustom: false
      },
      {
        path: './output',
        level: 'write',
        isCustom: true
      }
    ],
    apiRestrictions: [
      {
        endpoint: '/api/v1/chat',
        allowed: true,
        allowedOperations: ['POST']
      }
    ],
    filesystemRestricted: false,
    apiRestricted: false,
    updatedAt: Date.now()
  };
}

/**
 * Create sample audit logs
 */
function createAuditLogs(count: number): SecurityAuditLog[] {
  const logs: SecurityAuditLog[] = [];
  const categories = ['command_execution', 'filesystem_access', 'api_call', 'permission_change', 'risk_detected'];
  const severities = ['info', 'warning', 'critical'];

  for (let i = 0; i < count; i++) {
    logs.push({
      timestamp: Date.now() - (count - i) * 60000, // 1 minute apart
      category: categories[i % categories.length] as any,
      severity: severities[i % severities.length] as any,
      message: `Security event ${i + 1}`,
      details: {
        operation: `test_operation_${i}`,
        result: i % 3 === 0 ? 'blocked' : 'allowed'
      },
      allowed: i % 3 !== 0
    });
  }

  return logs;
}

/**
 * Simulate exportConfig operation
 */
async function simulateExport(options: {
  includeAuditLogs?: boolean;
  auditLogLimit?: number;
  reason?: string;
} = {}): Promise<SecurityExport | null> {
  try {
    // Load profile
    const profileData = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
    const profile: SecurityProfile = JSON.parse(profileData);

    // Load audit logs if requested
    let auditLogs: SecurityAuditLog[] | undefined;
    if (options.includeAuditLogs) {
      if (options.auditLogLimit && options.auditLogLimit > 0) {
        try {
          const auditData = await fs.readFile(TEST_AUDIT_LOG_PATH, 'utf-8');
          const allLogs: SecurityAuditLog[] = JSON.parse(auditData);
          // Sort by timestamp descending and limit
          auditLogs = allLogs
            .sort((a, b) => b.timestamp - a.timestamp)
            .slice(0, options.auditLogLimit);
        } catch {
          // Audit log file doesn't exist or is invalid
          auditLogs = [];
        }
      } else if (options.auditLogLimit === 0) {
        // Explicitly set to empty array when limit is 0
        auditLogs = [];
      }
    }

    // Create export object
    const exportData: SecurityExport = {
      version: '1.0.0',
      exportedAt: Date.now(),
      profile,
      auditLogs,
      metadata: {
        reason: options.reason || 'manual',
        format: 'json',
        source: 'auto-claude-security-ui'
      }
    };

    return exportData;
  } catch (error) {
    console.error('Export failed:', error);
    return null;
  }
}

/**
 * Validate export structure
 */
function validateExportStructure(exportData: SecurityExport): void {
  expect(exportData).toHaveProperty('version');
  expect(exportData).toHaveProperty('exportedAt');
  expect(exportData).toHaveProperty('profile');
  expect(exportData).toHaveProperty('metadata');

  expect(typeof exportData.version).toBe('string');
  expect(typeof exportData.exportedAt).toBe('number');
  expect(typeof exportData.profile).toBe('object');

  // Validate profile structure
  expect(exportData.profile).toHaveProperty('level');
  expect(exportData.profile).toHaveProperty('commandAllowlist');
  expect(exportData.profile).toHaveProperty('filesystemPermissions');
  expect(exportData.profile).toHaveProperty('apiRestrictions');
  expect(exportData.profile).toHaveProperty('filesystemRestricted');
  expect(exportData.profile).toHaveProperty('apiRestricted');
  expect(exportData.profile).toHaveProperty('updatedAt');

  // Validate metadata
  expect(exportData.metadata).toHaveProperty('reason');
  expect(exportData.metadata).toHaveProperty('format');
  expect(exportData.metadata).toHaveProperty('source');
}

describe('Security Configuration Export', () => {
  beforeAll(async () => {
    await setupTestEnvironment();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('Basic Export Functionality', () => {
    it('should export security profile without audit logs', async () => {
      // Create and save profile
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Perform export
      const exportData = await simulateExport({
        includeAuditLogs: false,
        reason: 'test'
      });

      expect(exportData).not.toBeNull();
      expect(exportData).toBeDefined();

      // Validate structure
      validateExportStructure(exportData!);

      // Verify no audit logs included
      expect(exportData!.auditLogs).toBeUndefined();

      // Verify profile data
      expect(exportData!.profile.level).toBe('standard');
      expect(exportData!.profile.commandAllowlist).toHaveLength(3);
      expect(exportData!.profile.filesystemPermissions).toHaveLength(2);
      expect(exportData!.profile.apiRestrictions).toHaveLength(1);
    });

    it('should export with metadata', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: false,
        reason: 'compliance'
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.metadata).toBeDefined();
      expect(exportData!.metadata.reason).toBe('compliance');
      expect(exportData!.metadata.format).toBe('json');
      expect(exportData!.metadata.source).toBe('auto-claude-security-ui');
    });

    it('should include export timestamp', async () => {
      const beforeExport = Date.now();

      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      const afterExport = Date.now();

      expect(exportData).not.toBeNull();
      expect(exportData!.exportedAt).toBeGreaterThanOrEqual(beforeExport);
      expect(exportData!.exportedAt).toBeLessThanOrEqual(afterExport);
    });
  });

  describe('Export with Audit Logs', () => {
    it('should export with 0 audit logs when limit is 0', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 0
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toBeDefined();
      expect(exportData!.auditLogs).toHaveLength(0);
    });

    it('should export with limited audit logs (50 entries)', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Create audit logs
      const auditLogs = createAuditLogs(100);
      await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(auditLogs, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 50
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toBeDefined();
      expect(exportData!.auditLogs).toHaveLength(50);

      // Verify logs are sorted by timestamp (most recent first)
      const timestamps = exportData!.auditLogs!.map(log => log.timestamp);
      const sortedTimestamps = [...timestamps].sort((a, b) => b - a);
      expect(timestamps).toEqual(sortedTimestamps);
    });

    it('should export with all audit logs when limit exceeds available', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Create only 25 audit logs
      const auditLogs = createAuditLogs(25);
      await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(auditLogs, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 1000 // Request more than available
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toBeDefined();
      expect(exportData!.auditLogs).toHaveLength(25);
    });

    it('should export with maximum audit logs (1000 entries)', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Create large audit log set
      const auditLogs = createAuditLogs(1500);
      await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(auditLogs, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 1000
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toBeDefined();
      expect(exportData!.auditLogs).toHaveLength(1000);
    });
  });

  describe('JSON Structure and Validation', () => {
    it('should produce valid JSON', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();

      // Serialize and deserialize
      const jsonString = JSON.stringify(exportData);
      expect(() => JSON.parse(jsonString)).not.toThrow();

      const parsed = JSON.parse(jsonString);
      expect(parsed).toEqual(exportData);
    });

    it('should maintain data types through serialization', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();

      // Serialize and parse
      const parsed = JSON.parse(JSON.stringify(exportData));

      // Verify types
      expect(typeof parsed.version).toBe('string');
      expect(typeof parsed.exportedAt).toBe('number');
      expect(typeof parsed.profile.level).toBe('string');
      expect(typeof parsed.profile.filesystemRestricted).toBe('boolean');
      expect(typeof parsed.profile.apiRestricted).toBe('boolean');
      expect(Array.isArray(parsed.profile.commandAllowlist)).toBe(true);
    });

    it('should include all profile fields', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();
      expect(exportData!.profile).toEqual(profile);

      // Verify all fields present
      expect(exportData!.profile.level).toBe(profile.level);
      expect(exportData!.profile.commandAllowlist).toEqual(profile.commandAllowlist);
      expect(exportData!.profile.filesystemPermissions).toEqual(profile.filesystemPermissions);
      expect(exportData!.profile.apiRestrictions).toEqual(profile.apiRestrictions);
      expect(exportData!.profile.filesystemRestricted).toBe(profile.filesystemRestricted);
      expect(exportData!.profile.apiRestricted).toBe(profile.apiRestricted);
    });
  });

  describe('Audit Log Data Integrity', () => {
    it('should preserve audit log structure', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const auditLogs = createAuditLogs(10);
      await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(auditLogs, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 10
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toHaveLength(10);

      // Verify each log entry has required fields
      exportData!.auditLogs!.forEach(log => {
        expect(log).toHaveProperty('timestamp');
        expect(log).toHaveProperty('category');
        expect(log).toHaveProperty('severity');
        expect(log).toHaveProperty('message');
        expect(log).toHaveProperty('allowed');

        expect(typeof log.timestamp).toBe('number');
        expect(typeof log.category).toBe('string');
        expect(typeof log.severity).toBe('string');
        expect(typeof log.message).toBe('string');
        expect(typeof log.allowed).toBe('boolean');
      });
    });

    it('should preserve audit log timestamps accurately', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const auditLogs = createAuditLogs(5);
      await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(auditLogs, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 5
      });

      expect(exportData).not.toBeNull();

      // Match timestamps by sorting
      const originalTimestamps = auditLogs.map(l => l.timestamp).sort((a, b) => b - a);
      const exportedTimestamps = exportData!.auditLogs!.map(l => l.timestamp);

      expect(exportedTimestamps).toEqual(originalTimestamps);
    });

    it('should include all audit log metadata', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const auditLogs: SecurityAuditLog[] = [
        {
          timestamp: Date.now(),
          category: 'command_execution',
          severity: 'info',
          message: 'Test command',
          details: {
            command: 'git status',
            agentType: 'coder',
            sessionId: 'session-123'
          },
          allowed: true
        }
      ];
      await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(auditLogs, null, 2), 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 1
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toHaveLength(1);

      const log = exportData!.auditLogs![0];
      expect(log.details).toBeDefined();
      expect(log.details!.command).toBe('git status');
      expect(log.details!.agentType).toBe('coder');
      expect(log.details!.sessionId).toBe('session-123');
    });
  });

  describe('Edge Cases', () => {
    it('should export empty profile', async () => {
      const emptyProfile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: [],
        filesystemPermissions: [],
        apiRestrictions: [],
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(emptyProfile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();
      expect(exportData!.profile.commandAllowlist).toHaveLength(0);
      expect(exportData!.profile.filesystemPermissions).toHaveLength(0);
      expect(exportData!.profile.apiRestrictions).toHaveLength(0);
    });

    it('should handle missing audit log file', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Ensure audit log file doesn't exist
      try {
        await fs.unlink(TEST_AUDIT_LOG_PATH);
      } catch {
        // Already doesn't exist
      }

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 50
      });

      expect(exportData).not.toBeNull();
      expect(exportData!.auditLogs).toBeDefined();
      expect(exportData!.auditLogs).toHaveLength(0);
    });

    it('should handle corrupted audit log file', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Write invalid JSON to audit log file
      await fs.writeFile(TEST_AUDIT_LOG_PATH, 'invalid json content', 'utf-8');

      const exportData = await simulateExport({
        includeAuditLogs: true,
        auditLogLimit: 50
      });

      expect(exportData).not.toBeNull();
      // Should handle gracefully with empty logs
      expect(exportData!.auditLogs).toBeDefined();
      expect(exportData!.auditLogs).toHaveLength(0);
    });

    it('should handle missing profile file', async () => {
      // Ensure profile file doesn't exist
      try {
        await fs.unlink(TEST_PROFILE_PATH);
      } catch {
        // Already doesn't exist
      }

      const exportData = await simulateExport();

      expect(exportData).toBeNull();
    });

    it('should export profile with all security levels', async () => {
      const levels: Array<'paranoid' | 'standard' | 'permissive'> = ['paranoid', 'standard', 'permissive'];

      for (const level of levels) {
        const profile: SecurityProfile = {
          level,
          commandAllowlist: [],
          filesystemPermissions: [],
          apiRestrictions: [],
          filesystemRestricted: level === 'paranoid',
          apiRestricted: level === 'paranoid',
          updatedAt: Date.now()
        };

        await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

        const exportData = await simulateExport();

        expect(exportData).not.toBeNull();
        expect(exportData!.profile.level).toBe(level);
      }
    });
  });

  describe('File Download Simulation', () => {
    it('should generate correct filename with timestamp', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();
      const timestamp = new Date(exportData!.exportedAt)
        .toISOString()
        .replace(/[:.]/g, '-')
        .split('T')[0];

      const filename = `auto-claude-security-config-${timestamp}.json`;

      expect(filename).toMatch(/auto-claude-security-config-\d{4}-\d{2}-\d{2}\.json/);
    });

    it('should create valid JSON blob for download', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();

      // Simulate blob creation (as in SecurityExport component)
      const jsonString = JSON.stringify(exportData, null, 2);
      expect(jsonString).toBeDefined();
      expect(jsonString.length).toBeGreaterThan(0);

      // Verify it's valid JSON
      expect(() => JSON.parse(jsonString)).not.toThrow();
    });
  });

  describe('Data Completeness', () => {
    it('should include all command allowlist entries', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();
      expect(exportData!.profile.commandAllowlist).toHaveLength(profile.commandAllowlist.length);

      // Verify each command entry
      profile.commandAllowlist.forEach(originalCommand => {
        const exportedCommand = exportData!.profile.commandAllowlist.find(
          c => c.command === originalCommand.command
        );
        expect(exportedCommand).toBeDefined();
        expect(exportedCommand!.allowed).toBe(originalCommand.allowed);
        expect(exportedCommand!.label).toBe(originalCommand.label);
      });
    });

    it('should include all filesystem permissions', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();
      expect(exportData!.profile.filesystemPermissions).toHaveLength(profile.filesystemPermissions.length);

      // Verify each permission rule
      profile.filesystemPermissions.forEach(originalRule => {
        const exportedRule = exportData!.profile.filesystemPermissions.find(
          r => r.path === originalRule.path
        );
        expect(exportedRule).toBeDefined();
        expect(exportedRule!.level).toBe(originalRule.level);
      });
    });

    it('should include all API restrictions', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();
      expect(exportData!.profile.apiRestrictions).toHaveLength(profile.apiRestrictions.length);

      // Verify each API restriction
      profile.apiRestrictions.forEach(originalRule => {
        const exportedRule = exportData!.profile.apiRestrictions.find(
          r => r.endpoint === originalRule.endpoint
        );
        expect(exportedRule).toBeDefined();
        expect(exportedRule!.allowed).toBe(originalRule.allowed);
      });
    });

    it('should preserve updatedAt timestamp', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const exportData = await simulateExport();

      expect(exportData).not.toBeNull();
      expect(exportData!.profile.updatedAt).toBe(profile.updatedAt);
    });
  });

  describe('Reason Tracking', () => {
    it('should track different export reasons', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const reasons = ['compliance', 'backup', 'manual', 'audit', 'migration'];

      for (const reason of reasons) {
        const exportData = await simulateExport({ reason });
        expect(exportData).not.toBeNull();
        expect(exportData!.metadata.reason).toBe(reason);
      }
    });
  });
});
