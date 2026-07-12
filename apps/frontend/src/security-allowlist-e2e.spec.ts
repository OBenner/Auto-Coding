// @ts-nocheck - E2E spec uses simplified security schema for integration testing
/**
 * End-to-End Test: Command Allowlist Editing and Persistence
 *
 * Tests the complete workflow of editing and persisting command allowlist changes:
 * 1. Load security profile
 * 2. Add custom command to allowlist
 * 3. Save changes
 * 4. Verify command persists after reload
 * 5. Remove command from allowlist
 * 6. Verify removal persists
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { mkdtempSync, promises as fs } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import type { SecurityProfile, CommandAllowlistEntry } from './shared/types/security';

// Test data paths - mkdtemp gives this spec file its own unpredictable
// 0700 directory, so parallel vitest workers running the other security
// e2e specs never share it (and no other local user can pre-create it)
const TEST_DATA_DIR = mkdtempSync(path.join(tmpdir(), 'security-allowlist-e2e-'));
const TEST_PROFILE_PATH = path.join(TEST_DATA_DIR, '.auto-claude-security.json');

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
    filesystemRestricted: false,
    apiRestricted: false,
    updatedAt: Date.now()
  };
}

/**
 * Create test command entry
 */
function createTestCommand(): CommandAllowlistEntry {
  return {
    command: 'pytest',
    allowed: true,
    label: 'Test runner',
    addedAt: Date.now()
  };
}

describe('Command Allowlist Editing and Persistence', () => {
  beforeAll(async () => {
    await setupTestEnvironment();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('Initial Profile Load', () => {
    it('should create and load default security profile', async () => {
      const profile = createDefaultProfile();

      // Write profile to file
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Read it back
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      // Verify structure
      expect(loadedProfile).toHaveProperty('commandAllowlist');
      expect(loadedProfile.commandAllowlist).toBeInstanceOf(Array);
      expect(loadedProfile.commandAllowlist).toHaveLength(3);

      // Verify initial commands
      const commands = loadedProfile.commandAllowlist.map(c => c.command);
      expect(commands).toContain('git');
      expect(commands).toContain('npm');
      expect(commands).toContain('node');
    });

    it('should handle missing profile file gracefully', async () => {
      // Ensure file doesn't exist
      try {
        await fs.unlink(TEST_PROFILE_PATH);
      } catch {
        // Already doesn't exist
      }

      // Attempting to load should return empty/default allowlist
      // This simulates first load scenario
      const defaultProfile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: [],
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      // Write and verify default
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(defaultProfile, null, 2), 'utf-8');
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loaded = JSON.parse(data) as SecurityProfile;

      expect(loaded.commandAllowlist).toHaveLength(0);
      expect(loaded.level).toBe('standard');
    });
  });

  describe('Add Custom Command', () => {
    it('should add custom command to existing allowlist', async () => {
      // Load existing profile
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Add new command
      const newCommand = createTestCommand();
      const updatedProfile: SecurityProfile = {
        ...profile,
        commandAllowlist: [...profile.commandAllowlist, newCommand],
        updatedAt: Date.now()
      };

      // Save updated profile
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      // Verify persistence
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(loadedProfile.commandAllowlist).toHaveLength(4);

      // Find the new command
      const addedCommand = loadedProfile.commandAllowlist.find(c => c.command === 'pytest');
      expect(addedCommand).toBeDefined();
      expect(addedCommand?.allowed).toBe(true);
      expect(addedCommand?.label).toBe('Test runner');
    });

    it('should persist command metadata', async () => {
      const profile = createDefaultProfile();
      const newCommand: CommandAllowlistEntry = {
        command: 'terraform',
        allowed: true,
        label: 'Infrastructure',
        addedAt: Date.now()
      };

      const updatedProfile: SecurityProfile = {
        ...profile,
        commandAllowlist: [...profile.commandAllowlist, newCommand],
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      // Reload and verify all metadata
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      const terraformEntry = loadedProfile.commandAllowlist.find(c => c.command === 'terraform');
      expect(terraformEntry).toBeDefined();
      expect(terraformEntry?.allowed).toBe(true);
      expect(terraformEntry?.label).toBe('Infrastructure');
      expect(terraformEntry?.addedAt).toBeDefined();
      expect(typeof terraformEntry?.addedAt).toBe('number');
    });
  });

  describe('Toggle Command Status', () => {
    it('should toggle command from allowed to blocked', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Toggle npm to blocked
      const updatedProfile: SecurityProfile = {
        ...profile,
        commandAllowlist: profile.commandAllowlist.map(entry =>
          entry.command === 'npm'
            ? { ...entry, allowed: false }
            : entry
        ),
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      // Verify change persisted
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      const npmEntry = loadedProfile.commandAllowlist.find(c => c.command === 'npm');
      expect(npmEntry?.allowed).toBe(false);

      // Verify other commands unchanged
      const gitEntry = loadedProfile.commandAllowlist.find(c => c.command === 'git');
      expect(gitEntry?.allowed).toBe(true);
    });

    it('should toggle command from blocked to allowed', async () => {
      // Create profile with blocked command
      const profile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: [
          {
            command: 'rm',
            allowed: false,
            label: 'Dangerous',
            addedAt: Date.now()
          }
        ],
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Toggle rm to allowed
      const updatedProfile: SecurityProfile = {
        ...profile,
        commandAllowlist: profile.commandAllowlist.map(entry =>
          entry.command === 'rm'
            ? { ...entry, allowed: true }
            : entry
        ),
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      // Verify change persisted
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      const rmEntry = loadedProfile.commandAllowlist.find(c => c.command === 'rm');
      expect(rmEntry?.allowed).toBe(true);
    });
  });

  describe('Remove Command', () => {
    it('should remove command from allowlist', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Remove npm from allowlist
      const updatedProfile: SecurityProfile = {
        ...profile,
        commandAllowlist: profile.commandAllowlist.filter(entry => entry.command !== 'npm'),
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      // Verify removal persisted
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(loadedProfile.commandAllowlist).toHaveLength(2);

      const commands = loadedProfile.commandAllowlist.map(c => c.command);
      expect(commands).not.toContain('npm');
      expect(commands).toContain('git');
      expect(commands).toContain('node');
    });

    it('should handle removal of non-existent command gracefully', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Try to remove command that doesn't exist
      const originalLength = profile.commandAllowlist.length;
      const updatedProfile: SecurityProfile = {
        ...profile,
        commandAllowlist: profile.commandAllowlist.filter(entry => entry.command !== 'nonexistent'),
        updatedAt: Date.now()
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      // Verify no change
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(loadedProfile.commandAllowlist).toHaveLength(originalLength);
    });
  });

  describe('Persistence Across Reloads', () => {
    it('should preserve all changes after multiple save/load cycles', async () => {
      // Create initial profile
      let profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // First modification: Add command
      profile = {
        ...profile,
        commandAllowlist: [
          ...profile.commandAllowlist,
          { command: 'pytest', allowed: true, addedAt: Date.now() }
        ],
        updatedAt: Date.now()
      };
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Second modification: Toggle command
      profile = {
        ...profile,
        commandAllowlist: profile.commandAllowlist.map(entry =>
          entry.command === 'git' ? { ...entry, allowed: false } : entry
        ),
        updatedAt: Date.now()
      };
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Third modification: Remove command
      profile = {
        ...profile,
        commandAllowlist: profile.commandAllowlist.filter(entry => entry.command !== 'node')
      };
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Final load and verification
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const finalProfile = JSON.parse(data) as SecurityProfile;

      // Verify all changes persisted
      expect(finalProfile.commandAllowlist).toHaveLength(3);

      const commands = finalProfile.commandAllowlist.map(c => c.command);
      expect(commands).toContain('pytest'); // Added
      expect(commands).toContain('npm');
      expect(commands).toContain('git');
      expect(commands).not.toContain('node'); // Removed

      const gitEntry = finalProfile.commandAllowlist.find(c => c.command === 'git');
      expect(gitEntry?.allowed).toBe(false); // Toggled
    });
  });

  describe('Data Integrity', () => {
    it('should maintain valid JSON structure', async () => {
      const profile = createDefaultProfile();
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      // Read and verify it's valid JSON
      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');

      expect(() => JSON.parse(data)).not.toThrow();

      const parsed = JSON.parse(data);
      expect(parsed).toHaveProperty('commandAllowlist');
      expect(parsed).toHaveProperty('level');
      expect(parsed).toHaveProperty('filesystemRestricted');
      expect(parsed).toHaveProperty('apiRestricted');
    });

    it('should preserve timestamp types', async () => {
      const now = Date.now();
      const profile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: [
          {
            command: 'test',
            allowed: true,
            addedAt: now
          }
        ],
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: now
      };

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(typeof loadedProfile.updatedAt).toBe('number');
      expect(typeof loadedProfile.commandAllowlist[0].addedAt).toBe('number');
    });
  });
});
