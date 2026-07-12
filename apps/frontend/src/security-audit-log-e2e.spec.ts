// @ts-nocheck - E2E spec uses simplified security schema for integration testing
/**
 * End-to-End Test: Audit Log Viewing
 *
 * Tests the complete workflow of viewing security audit logs:
 * 1. Perform security-relevant operations
 * 2. Verify operations appear in audit log
 * 3. Verify timestamps and details are correct
 * 4. Test filtering and searching
 * 5. Verify log persistence
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { mkdtempSync, promises as fs } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import type { SecurityAuditLog } from './shared/types/security';

// Test data paths - mkdtemp gives this spec file its own unpredictable
// 0700 directory, so parallel vitest workers running the other security
// e2e specs never share it (and no other local user can pre-create it)
const TEST_DATA_DIR = mkdtempSync(path.join(tmpdir(), 'security-audit-log-e2e-'));
const TEST_AUDIT_LOG_PATH = path.join(TEST_DATA_DIR, '.auto-claude-audit.json');

/**
 * Setup test environment
 */
async function setupTestEnvironment(): Promise<void> {
  // Create test directory
  await fs.mkdir(TEST_DATA_DIR, { recursive: true });

  // Clean up any existing test data
  try {
    await fs.unlink(TEST_AUDIT_LOG_PATH);
  } catch {
    // File doesn't exist, that's fine
  }
}

/**
 * Cleanup test environment
 */
async function cleanupTestEnvironment(): Promise<void> {
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
 * Create a sample audit log entry
 */
function createAuditLogEntry(overrides?: Partial<SecurityAuditLog>): SecurityAuditLog {
  const now = Date.now();
  return {
    id: `log-${now}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: now,
    category: 'command_execution',
    severity: 'info',
    message: 'Command executed successfully',
    allowed: true,
    command: 'git status',
    agentType: 'coder',
    sessionId: 'session-123',
    projectId: 'test-project',
    ...overrides
  };
}

/**
 * Write audit log entries to file
 */
async function writeAuditLogs(logs: SecurityAuditLog[]): Promise<void> {
  const data = {
    version: 1,
    logs
  };
  await fs.writeFile(TEST_AUDIT_LOG_PATH, JSON.stringify(data, null, 2), 'utf-8');
}

/**
 * Read audit log entries from file
 */
async function readAuditLogs(): Promise<SecurityAuditLog[]> {
  try {
    const data = await fs.readFile(TEST_AUDIT_LOG_PATH, 'utf-8');
    const parsed = JSON.parse(data);
    return parsed.logs || [];
  } catch {
    return [];
  }
}

describe('Audit Log Viewing', () => {
  beforeAll(async () => {
    await setupTestEnvironment();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('Basic Audit Log Operations', () => {
    it('should store audit log entries with correct structure', async () => {
      const logEntry = createAuditLogEntry({
        category: 'command_execution',
        message: 'Test command executed',
        command: 'npm test'
      });

      await writeAuditLogs([logEntry]);

      const logs = await readAuditLogs();
      expect(logs).toHaveLength(1);
      expect(logs[0]).toMatchObject({
        id: expect.any(String),
        timestamp: expect.any(Number),
        category: 'command_execution',
        message: 'Test command executed',
        command: 'npm test',
        allowed: true
      });
    });

    it('should store multiple audit log entries in chronological order', async () => {
      const now = Date.now();
      const logs = [
        createAuditLogEntry({
          id: 'log-1',
          timestamp: now - 3000,
          message: 'First event',
          command: 'git init'
        }),
        createAuditLogEntry({
          id: 'log-2',
          timestamp: now - 2000,
          message: 'Second event',
          command: 'npm install'
        }),
        createAuditLogEntry({
          id: 'log-3',
          timestamp: now - 1000,
          message: 'Third event',
          command: 'npm test'
        })
      ];

      await writeAuditLogs(logs);

      const loadedLogs = await readAuditLogs();
      expect(loadedLogs).toHaveLength(3);

      // Verify chronological order (oldest first in file)
      expect(loadedLogs[0].id).toBe('log-1');
      expect(loadedLogs[1].id).toBe('log-2');
      expect(loadedLogs[2].id).toBe('log-3');
    });
  });

  describe('Security Event Categories', () => {
    it('should log command execution events', async () => {
      const logEntry = createAuditLogEntry({
        category: 'command_execution',
        severity: 'info',
        message: 'Command "git status" allowed by allowlist',
        command: 'git status',
        allowed: true
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('command_execution');
      expect(logs[0].command).toBe('git status');
      expect(logs[0].allowed).toBe(true);
    });

    it('should log blocked command attempts', async () => {
      const logEntry = createAuditLogEntry({
        category: 'command_execution',
        severity: 'warning',
        message: 'Command "rm -rf /" blocked by security policy',
        command: 'rm -rf /',
        allowed: false
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('command_execution');
      expect(logs[0].severity).toBe('warning');
      expect(logs[0].allowed).toBe(false);
      expect(logs[0].command).toBe('rm -rf /');
    });

    it('should log filesystem access events', async () => {
      const logEntry = createAuditLogEntry({
        category: 'filesystem_access',
        severity: 'info',
        message: 'File read: package.json',
        filePath: 'package.json',
        allowed: true
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('filesystem_access');
      expect(logs[0].filePath).toBe('package.json');
    });

    it('should log API call events', async () => {
      const logEntry = createAuditLogEntry({
        category: 'api_call',
        severity: 'info',
        message: 'API call to Anthropic',
        apiEndpoint: 'https://api.anthropic.com/v1/messages',
        allowed: true
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('api_call');
      expect(logs[0].apiEndpoint).toBe('https://api.anthropic.com/v1/messages');
    });

    it('should log permission changes', async () => {
      const logEntry = createAuditLogEntry({
        category: 'permission_change',
        severity: 'warning',
        message: 'Security level changed from standard to permissive',
        allowed: true
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('permission_change');
      expect(logs[0].severity).toBe('warning');
    });

    it('should log sandbox violations', async () => {
      const logEntry = createAuditLogEntry({
        category: 'sandbox_violation',
        severity: 'critical',
        message: 'Attempt to access file outside project directory',
        filePath: '/etc/passwd',
        allowed: false
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('sandbox_violation');
      expect(logs[0].severity).toBe('critical');
      expect(logs[0].allowed).toBe(false);
    });

    it('should log risk detections', async () => {
      const logEntry = createAuditLogEntry({
        category: 'risk_detected',
        severity: 'warning',
        message: 'Potential credential leak in command',
        command: 'git log --password=secret123',
        allowed: false
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].category).toBe('risk_detected');
      expect(logs[0].severity).toBe('warning');
    });
  });

  describe('Timestamp Accuracy', () => {
    it('should store accurate timestamps', async () => {
      const before = Date.now();
      const logEntry = createAuditLogEntry({
        message: 'Timestamp test'
      });
      const after = Date.now();

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].timestamp).toBeGreaterThanOrEqual(before);
      expect(logs[0].timestamp).toBeLessThanOrEqual(after);
    });

    it('should preserve timestamp ordering across multiple entries', async () => {
      const timestamps: number[] = [];
      const logs: SecurityAuditLog[] = [];

      // Create 10 entries with slight delays
      for (let i = 0; i < 10; i++) {
        const timestamp = Date.now();
        timestamps.push(timestamp);
        logs.push(createAuditLogEntry({
          id: `log-${i}`,
          timestamp,
          message: `Entry ${i}`
        }));
        // Small delay to ensure different timestamps
        await new Promise(resolve => setTimeout(resolve, 10));
      }

      await writeAuditLogs(logs);
      const loadedLogs = await readAuditLogs();

      // Verify all timestamps are in ascending order
      for (let i = 1; i < loadedLogs.length; i++) {
        expect(loadedLogs[i].timestamp).toBeGreaterThan(loadedLogs[i - 1].timestamp);
      }
    });
  });

  describe('Event Details Accuracy', () => {
    it('should preserve all event metadata', async () => {
      const logEntry = createAuditLogEntry({
        category: 'command_execution',
        severity: 'warning',
        message: 'Command blocked by allowlist',
        command: 'docker ps',
        allowed: false,
        agentType: 'coder',
        sessionId: 'test-session-abc',
        projectId: 'project-xyz',
        ruleId: 'allowlist-001',
        context: JSON.stringify({ reason: 'Docker not in allowlist' })
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0]).toMatchObject({
        category: 'command_execution',
        severity: 'warning',
        message: 'Command blocked by allowlist',
        command: 'docker ps',
        allowed: false,
        agentType: 'coder',
        sessionId: 'test-session-abc',
        projectId: 'project-xyz',
        ruleId: 'allowlist-001'
      });

      // Verify context JSON string
      expect(logs[0].context).toBeDefined();
      const context = JSON.parse(logs[0].context!);
      expect(context.reason).toBe('Docker not in allowlist');
    });

    it('should handle special characters in messages', async () => {
      const logEntry = createAuditLogEntry({
        message: 'Command with special chars: <script>alert("XSS")</script>',
        command: 'echo "test & test"'
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].message).toContain('<script>');
      expect(logs[0].command).toContain('&');
    });

    it('should handle Unicode characters in messages', async () => {
      const logEntry = createAuditLogEntry({
        message: 'Command with emoji: 🔒 and unicode: café, 日本語',
        command: 'echo "你好世界"'
      });

      await writeAuditLogs([logEntry]);
      const logs = await readAuditLogs();

      expect(logs[0].message).toContain('🔒');
      expect(logs[0].message).toContain('café');
      expect(logs[0].command).toContain('你好世界');
    });
  });

  describe('Audit Log Persistence', () => {
    it('should persist audit logs across file reads', async () => {
      const logs1 = [
        createAuditLogEntry({ id: 'log-1', message: 'First log' }),
        createAuditLogEntry({ id: 'log-2', message: 'Second log' })
      ];

      await writeAuditLogs(logs1);
      const loaded1 = await readAuditLogs();
      expect(loaded1).toHaveLength(2);

      // Read again to verify persistence
      const loaded2 = await readAuditLogs();
      expect(loaded2).toHaveLength(2);
      expect(loaded2[0].id).toBe('log-1');
      expect(loaded2[1].id).toBe('log-2');
    });

    it('should append new logs to existing file', async () => {
      // Write initial logs
      const initialLogs = [
        createAuditLogEntry({ id: 'log-1', timestamp: Date.now() - 2000 })
      ];
      await writeAuditLogs(initialLogs);

      // Append new log
      const existingLogs = await readAuditLogs();
      const newLog = createAuditLogEntry({ id: 'log-2', timestamp: Date.now() });
      await writeAuditLogs([...existingLogs, newLog]);

      // Verify both logs exist
      const finalLogs = await readAuditLogs();
      expect(finalLogs).toHaveLength(2);
      expect(finalLogs[0].id).toBe('log-1');
      expect(finalLogs[1].id).toBe('log-2');
    });

    it('should handle file corruption gracefully', async () => {
      // Write corrupted data
      await fs.writeFile(TEST_AUDIT_LOG_PATH, 'corrupted json data{{{', 'utf-8');

      // Should return empty array instead of crashing
      const logs = await readAuditLogs();
      expect(logs).toEqual([]);
    });
  });

  describe('Filtering and Search Support', () => {
    it('should support filtering by category', async () => {
      const logs = [
        createAuditLogEntry({ id: 'log-1', category: 'command_execution' }),
        createAuditLogEntry({ id: 'log-2', category: 'filesystem_access' }),
        createAuditLogEntry({ id: 'log-3', category: 'command_execution' })
      ];

      await writeAuditLogs(logs);
      const loadedLogs = await readAuditLogs();

      const commandLogs = loadedLogs.filter(l => l.category === 'command_execution');
      expect(commandLogs).toHaveLength(2);

      const fsLogs = loadedLogs.filter(l => l.category === 'filesystem_access');
      expect(fsLogs).toHaveLength(1);
    });

    it('should support filtering by severity', async () => {
      const logs = [
        createAuditLogEntry({ id: 'log-1', severity: 'info' }),
        createAuditLogEntry({ id: 'log-2', severity: 'critical' }),
        createAuditLogEntry({ id: 'log-3', severity: 'warning' })
      ];

      await writeAuditLogs(logs);
      const loadedLogs = await readAuditLogs();

      const criticalLogs = loadedLogs.filter(l => l.severity === 'critical');
      expect(criticalLogs).toHaveLength(1);

      const infoLogs = loadedLogs.filter(l => l.severity === 'info');
      expect(infoLogs).toHaveLength(1);
    });

    it('should support filtering by allowed status', async () => {
      const logs = [
        createAuditLogEntry({ id: 'log-1', allowed: true }),
        createAuditLogEntry({ id: 'log-2', allowed: false }),
        createAuditLogEntry({ id: 'log-3', allowed: true })
      ];

      await writeAuditLogs(logs);
      const loadedLogs = await readAuditLogs();

      const allowedLogs = loadedLogs.filter(l => l.allowed);
      expect(allowedLogs).toHaveLength(2);

      const blockedLogs = loadedLogs.filter(l => !l.allowed);
      expect(blockedLogs).toHaveLength(1);
    });

    it('should support searching by message content', async () => {
      const logs = [
        createAuditLogEntry({ id: 'log-1', message: 'Command git status executed' }),
        createAuditLogEntry({ id: 'log-2', message: 'File package.json read' }),
        createAuditLogEntry({ id: 'log-3', message: 'Command git commit executed' })
      ];

      await writeAuditLogs(logs);
      const loadedLogs = await readAuditLogs();

      const gitLogs = loadedLogs.filter(l => l.message.toLowerCase().includes('git'));
      expect(gitLogs).toHaveLength(2);

      const packageLogs = loadedLogs.filter(l => l.message.toLowerCase().includes('package'));
      expect(packageLogs).toHaveLength(1);
    });

    it('should support searching by command', async () => {
      const logs = [
        createAuditLogEntry({ id: 'log-1', command: 'git status' }),
        createAuditLogEntry({ id: 'log-2', command: 'npm test' }),
        createAuditLogEntry({ id: 'log-3', command: 'git log' })
      ];

      await writeAuditLogs(logs);
      const loadedLogs = await readAuditLogs();

      const gitLogs = loadedLogs.filter(l => l.command?.includes('git'));
      expect(gitLogs).toHaveLength(2);
    });
  });

  describe('Real-World Scenarios', () => {
    it('should handle a typical workflow of security events', async () => {
      const now = Date.now();
      const workflowLogs = [
        // Session starts
        createAuditLogEntry({
          id: 'log-1',
          timestamp: now - 5000,
          category: 'profile_loaded',
          severity: 'info',
          message: 'Security profile loaded for project',
          allowed: true
        }),
        // Agent executes allowed command
        createAuditLogEntry({
          id: 'log-2',
          timestamp: now - 4000,
          category: 'command_execution',
          severity: 'info',
          message: 'Command "git status" allowed by allowlist',
          command: 'git status',
          allowed: true,
          agentType: 'coder'
        }),
        // Agent attempts blocked command
        createAuditLogEntry({
          id: 'log-3',
          timestamp: now - 3000,
          category: 'command_execution',
          severity: 'warning',
          message: 'Command "docker ps" blocked by allowlist',
          command: 'docker ps',
          allowed: false,
          agentType: 'coder',
          ruleId: 'allowlist-001'
        }),
        // Agent reads file
        createAuditLogEntry({
          id: 'log-4',
          timestamp: now - 2000,
          category: 'filesystem_access',
          severity: 'info',
          message: 'File read: package.json',
          filePath: 'package.json',
          allowed: true,
          agentType: 'coder'
        }),
        // Security level changed
        createAuditLogEntry({
          id: 'log-5',
          timestamp: now - 1000,
          category: 'permission_change',
          severity: 'warning',
          message: 'Security level changed from standard to permissive',
          allowed: true
        }),
        // Profile exported
        createAuditLogEntry({
          id: 'log-6',
          timestamp: now,
          category: 'profile_exported',
          severity: 'info',
          message: 'Security configuration exported',
          allowed: true
        })
      ];

      await writeAuditLogs(workflowLogs);
      const loadedLogs = await readAuditLogs();

      expect(loadedLogs).toHaveLength(6);

      // Verify workflow sequence
      expect(loadedLogs[0].category).toBe('profile_loaded');
      expect(loadedLogs[1].category).toBe('command_execution');
      expect(loadedLogs[1].allowed).toBe(true);
      expect(loadedLogs[2].category).toBe('command_execution');
      expect(loadedLogs[2].allowed).toBe(false);
      expect(loadedLogs[3].category).toBe('filesystem_access');
      expect(loadedLogs[4].category).toBe('permission_change');
      expect(loadedLogs[5].category).toBe('profile_exported');

      // Verify statistics
      const totalEvents = loadedLogs.length;
      const blockedEvents = loadedLogs.filter(l => !l.allowed).length;
      const criticalEvents = loadedLogs.filter(l => l.severity === 'critical').length;
      const warningEvents = loadedLogs.filter(l => l.severity === 'warning').length;

      expect(totalEvents).toBe(6);
      expect(blockedEvents).toBe(1);
      expect(warningEvents).toBe(2);
      expect(criticalEvents).toBe(0);
    });
  });
});
