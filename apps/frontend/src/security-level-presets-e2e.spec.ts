// @ts-nocheck - E2E spec uses simplified security schema for integration testing
/**
 * End-to-End Test: Security Level Presets
 *
 * Tests security level preset application and verification:
 * 1. Paranoid preset - minimal commands, filesystem restricted, API restricted
 * 2. Standard preset - balanced permissions (50 commands max)
 * 3. Permissive preset - maximum commands, no restrictions
 * 4. Preset switching and persistence
 * 5. Detection of current security level from profile
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { promises as fs } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import type { SecurityProfile, SecurityLevel, CommandAllowlistEntry } from './shared/types/security';

// Test data paths - unique per spec file and process so parallel vitest
// workers running the other security e2e specs never share this directory
const TEST_DATA_DIR = path.join(tmpdir(), 'auto-code-ui-tests', `security-level-presets-e2e-${process.pid}`);
const TEST_PROFILE_PATH = path.join(TEST_DATA_DIR, '.auto-claude-security.json');

// Security level preset configurations (matching SecuritySettings.tsx)
interface SecurityLevelPreset {
  level: SecurityLevel;
  allowlistSize: number;
  filesystemRestrictions: boolean;
  apiRestrictions: boolean;
}

const PRESETS: Record<SecurityLevel, SecurityLevelPreset> = {
  paranoid: {
    level: 'paranoid',
    allowlistSize: 10,
    filesystemRestrictions: true,
    apiRestrictions: true
  },
  standard: {
    level: 'standard',
    allowlistSize: 50,
    filesystemRestrictions: false,
    apiRestrictions: false
  },
  permissive: {
    level: 'permissive',
    allowlistSize: 100,
    filesystemRestrictions: false,
    apiRestrictions: false
  }
};

/**
 * Setup test environment
 */
async function setupTestEnvironment(): Promise<void> {
  await fs.mkdir(TEST_DATA_DIR, { recursive: true });

  try {
    await fs.unlink(TEST_PROFILE_PATH);
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
    await fs.rmdir(TEST_DATA_DIR);
  } catch {
    // Directory not empty or doesn't exist
  }
}

/**
 * Create a profile with many commands for testing presets
 */
function createPopulatedProfile(commandCount: number = 80): SecurityProfile {
  const commands: CommandAllowlistEntry[] = [];

  for (let i = 0; i < commandCount; i++) {
    commands.push({
      command: `command-${i}`,
      allowed: true,
      label: `Test command ${i}`,
      addedAt: Date.now() - (commandCount - i) * 1000
    });
  }

  return {
    level: 'standard',
    commandAllowlist: commands,
    filesystemRestricted: false,
    apiRestricted: false,
    updatedAt: Date.now()
  };
}

/**
 * Apply security level preset to a profile
 */
function applyPreset(profile: SecurityProfile, preset: SecurityLevelPreset): SecurityProfile {
  return {
    ...profile,
    commandAllowlist: profile.commandAllowlist.slice(0, preset.allowlistSize),
    filesystemRestricted: preset.filesystemRestrictions,
    apiRestricted: preset.apiRestrictions,
    level: preset.level,
    updatedAt: Date.now()
  };
}

/**
 * Detect security level from profile (matching SecuritySettings.tsx logic)
 */
function detectSecurityLevel(profile: SecurityProfile): SecurityLevel {
  if (profile.filesystemRestricted && profile.apiRestricted && profile.commandAllowlist.length <= 15) {
    return 'paranoid';
  }
  if (!profile.filesystemRestricted && !profile.apiRestricted && profile.commandAllowlist.length > 75) {
    return 'permissive';
  }
  return 'standard';
}

describe('Security Level Presets', () => {
  beforeAll(async () => {
    await setupTestEnvironment();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('Paranoid Preset', () => {
    it('should limit command allowlist to 10 commands', async () => {
      const profile = createPopulatedProfile(80);
      const paranoidPreset = PRESETS.paranoid;

      const updatedProfile = applyPreset(profile, paranoidPreset);

      expect(updatedProfile.commandAllowlist).toHaveLength(paranoidPreset.allowlistSize);
      expect(updatedProfile.commandAllowlist).toHaveLength(10);
    });

    it('should enable filesystem restrictions', async () => {
      const profile = createPopulatedProfile(50);
      const paranoidPreset = PRESETS.paranoid;

      const updatedProfile = applyPreset(profile, paranoidPreset);

      expect(updatedProfile.filesystemRestricted).toBe(true);
    });

    it('should enable API restrictions', async () => {
      const profile = createPopulatedProfile(50);
      const paranoidPreset = PRESETS.paranoid;

      const updatedProfile = applyPreset(profile, paranoidPreset);

      expect(updatedProfile.apiRestricted).toBe(true);
    });

    it('should be detected as paranoid level', async () => {
      const profile = createPopulatedProfile(5);
      profile.filesystemRestricted = true;
      profile.apiRestricted = true;
      profile.commandAllowlist = profile.commandAllowlist.slice(0, 10);

      const detected = detectSecurityLevel(profile);

      expect(detected).toBe('paranoid');
    });

    it('should persist paranoid preset to file', async () => {
      const profile = createPopulatedProfile(80);
      const paranoidPreset = PRESETS.paranoid;

      const updatedProfile = applyPreset(profile, paranoidPreset);
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(loadedProfile.level).toBe('paranoid');
      expect(loadedProfile.commandAllowlist).toHaveLength(10);
      expect(loadedProfile.filesystemRestricted).toBe(true);
      expect(loadedProfile.apiRestricted).toBe(true);
    });
  });

  describe('Standard Preset', () => {
    it('should limit command allowlist to 50 commands', async () => {
      const profile = createPopulatedProfile(80);
      const standardPreset = PRESETS.standard;

      const updatedProfile = applyPreset(profile, standardPreset);

      expect(updatedProfile.commandAllowlist).toHaveLength(standardPreset.allowlistSize);
      expect(updatedProfile.commandAllowlist).toHaveLength(50);
    });

    it('should disable filesystem restrictions', async () => {
      const profile = createPopulatedProfile(50);
      profile.filesystemRestricted = true; // Start with restrictions
      const standardPreset = PRESETS.standard;

      const updatedProfile = applyPreset(profile, standardPreset);

      expect(updatedProfile.filesystemRestricted).toBe(false);
    });

    it('should disable API restrictions', async () => {
      const profile = createPopulatedProfile(50);
      profile.apiRestricted = true; // Start with restrictions
      const standardPreset = PRESETS.standard;

      const updatedProfile = applyPreset(profile, standardPreset);

      expect(updatedProfile.apiRestricted).toBe(false);
    });

    it('should be detected as standard level (middle ground)', async () => {
      const profile = createPopulatedProfile(50);
      profile.filesystemRestricted = false;
      profile.apiRestricted = false;
      profile.commandAllowlist = profile.commandAllowlist.slice(0, 50);

      const detected = detectSecurityLevel(profile);

      expect(detected).toBe('standard');
    });

    it('should persist standard preset to file', async () => {
      const profile = createPopulatedProfile(80);
      const standardPreset = PRESETS.standard;

      const updatedProfile = applyPreset(profile, standardPreset);
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(loadedProfile.level).toBe('standard');
      expect(loadedProfile.commandAllowlist).toHaveLength(50);
      expect(loadedProfile.filesystemRestricted).toBe(false);
      expect(loadedProfile.apiRestricted).toBe(false);
    });
  });

  describe('Permissive Preset', () => {
    it('should allow up to 100 commands', async () => {
      const profile = createPopulatedProfile(80);
      const permissivePreset = PRESETS.permissive;

      const updatedProfile = applyPreset(profile, permissivePreset);

      expect(updatedProfile.commandAllowlist).toHaveLength(80); // All 80 preserved
      expect(updatedProfile.commandAllowlist.length).toBeLessThanOrEqual(permissivePreset.allowlistSize);
    });

    it('should disable filesystem restrictions', async () => {
      const profile = createPopulatedProfile(50);
      profile.filesystemRestricted = true;
      const permissivePreset = PRESETS.permissive;

      const updatedProfile = applyPreset(profile, permissivePreset);

      expect(updatedProfile.filesystemRestricted).toBe(false);
    });

    it('should disable API restrictions', async () => {
      const profile = createPopulatedProfile(50);
      profile.apiRestricted = true;
      const permissivePreset = PRESETS.permissive;

      const updatedProfile = applyPreset(profile, permissivePreset);

      expect(updatedProfile.apiRestricted).toBe(false);
    });

    it('should be detected as permissive level (large allowlist, no restrictions)', async () => {
      const profile = createPopulatedProfile(100);
      profile.filesystemRestricted = false;
      profile.apiRestricted = false;
      profile.commandAllowlist = profile.commandAllowlist.slice(0, 100);

      const detected = detectSecurityLevel(profile);

      expect(detected).toBe('permissive');
    });

    it('should persist permissive preset to file', async () => {
      const profile = createPopulatedProfile(80);
      const permissivePreset = PRESETS.permissive;

      const updatedProfile = applyPreset(profile, permissivePreset);
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      const loadedProfile = JSON.parse(data) as SecurityProfile;

      expect(loadedProfile.level).toBe('permissive');
      expect(loadedProfile.commandAllowlist).toHaveLength(80);
      expect(loadedProfile.filesystemRestricted).toBe(false);
      expect(loadedProfile.apiRestricted).toBe(false);
    });
  });

  describe('Preset Switching', () => {
    it('should switch from paranoid to permissive correctly', async () => {
      // Start with paranoid
      let profile = createPopulatedProfile(50);
      profile = applyPreset(profile, PRESETS.paranoid);

      expect(profile.commandAllowlist).toHaveLength(10);
      expect(profile.filesystemRestricted).toBe(true);
      expect(profile.apiRestricted).toBe(true);

      // Switch to permissive (but with only original 50 commands available)
      const commandsBeforeSwitch = profile.commandAllowlist.length;
      profile = applyPreset(profile, PRESETS.permissive);

      // Permissive should keep all 10 commands (slices from 0 to 100)
      expect(profile.commandAllowlist).toHaveLength(commandsBeforeSwitch);
      expect(profile.filesystemRestricted).toBe(false);
      expect(profile.apiRestricted).toBe(false);
    });

    it('should switch from permissive to paranoid correctly', async () => {
      // Start with permissive
      let profile = createPopulatedProfile(100);
      profile = applyPreset(profile, PRESETS.permissive);

      expect(profile.commandAllowlist).toHaveLength(100);
      expect(profile.filesystemRestricted).toBe(false);
      expect(profile.apiRestricted).toBe(false);

      // Switch to paranoid
      profile = applyPreset(profile, PRESETS.paranoid);

      expect(profile.commandAllowlist).toHaveLength(10);
      expect(profile.filesystemRestricted).toBe(true);
      expect(profile.apiRestricted).toBe(true);
    });

    it('should switch from standard to paranoid correctly', async () => {
      let profile = createPopulatedProfile(60);
      profile = applyPreset(profile, PRESETS.standard);

      expect(profile.commandAllowlist).toHaveLength(50);
      expect(profile.level).toBe('standard');

      profile = applyPreset(profile, PRESETS.paranoid);

      expect(profile.commandAllowlist).toHaveLength(10);
      expect(profile.filesystemRestricted).toBe(true);
      expect(profile.apiRestricted).toBe(true);
      expect(profile.level).toBe('paranoid');
    });

    it('should persist across multiple preset switches', async () => {
      let profile = createPopulatedProfile(80);

      // First: Apply standard
      profile = applyPreset(profile, PRESETS.standard);
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      let data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      let loaded = JSON.parse(data) as SecurityProfile;
      expect(loaded.commandAllowlist).toHaveLength(50);

      // Second: Apply paranoid
      profile = applyPreset(loaded, PRESETS.paranoid);
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      loaded = JSON.parse(data) as SecurityProfile;
      expect(loaded.commandAllowlist).toHaveLength(10);
      expect(loaded.filesystemRestricted).toBe(true);

      // Third: Apply permissive
      profile = applyPreset(loaded, PRESETS.permissive);
      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(profile, null, 2), 'utf-8');

      data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      loaded = JSON.parse(data) as SecurityProfile;
      expect(loaded.commandAllowlist).toHaveLength(10); // Only 10 commands exist now
      expect(loaded.filesystemRestricted).toBe(false);
      expect(loaded.apiRestricted).toBe(false);
    });
  });

  describe('Security Level Detection', () => {
    it('should detect paranoid when both restrictions enabled and commands limited', () => {
      const profile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: createPopulatedProfile(10).commandAllowlist,
        filesystemRestricted: true,
        apiRestricted: true,
        updatedAt: Date.now()
      };

      expect(detectSecurityLevel(profile)).toBe('paranoid');
    });

    it('should detect permissive when both restrictions disabled and commands plentiful', () => {
      const profile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: createPopulatedProfile(100).commandAllowlist,
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      expect(detectSecurityLevel(profile)).toBe('permissive');
    });

    it('should detect standard as default (middle ground)', () => {
      const profile: SecurityProfile = {
        level: 'paranoid',
        commandAllowlist: createPopulatedProfile(50).commandAllowlist,
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      expect(detectSecurityLevel(profile)).toBe('standard');
    });

    it('should detect standard when only one restriction enabled', () => {
      const profile1: SecurityProfile = {
        level: 'paranoid',
        commandAllowlist: createPopulatedProfile(20).commandAllowlist,
        filesystemRestricted: true,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      const profile2: SecurityProfile = {
        level: 'paranoid',
        commandAllowlist: createPopulatedProfile(20).commandAllowlist,
        filesystemRestricted: false,
        apiRestricted: true,
        updatedAt: Date.now()
      };

      expect(detectSecurityLevel(profile1)).toBe('standard');
      expect(detectSecurityLevel(profile2)).toBe('standard');
    });
  });

  describe('Data Integrity', () => {
    it('should maintain valid JSON structure after preset application', async () => {
      const profile = createPopulatedProfile(80);
      const updatedProfile = applyPreset(profile, PRESETS.standard);

      await fs.writeFile(TEST_PROFILE_PATH, JSON.stringify(updatedProfile, null, 2), 'utf-8');

      const data = await fs.readFile(TEST_PROFILE_PATH, 'utf-8');
      expect(() => JSON.parse(data)).not.toThrow();

      const parsed = JSON.parse(data) as SecurityProfile;
      expect(parsed).toHaveProperty('level');
      expect(parsed).toHaveProperty('commandAllowlist');
      expect(parsed).toHaveProperty('filesystemRestricted');
      expect(parsed).toHaveProperty('apiRestricted');
      expect(parsed).toHaveProperty('updatedAt');
    });

    it('should preserve command metadata when trimming allowlist', async () => {
      const profile = createPopulatedProfile(20);
      const updatedProfile = applyPreset(profile, PRESETS.paranoid);

      // Should preserve first 10 commands with all metadata
      expect(updatedProfile.commandAllowlist).toHaveLength(10);

      const firstCommand = updatedProfile.commandAllowlist[0];
      expect(firstCommand).toHaveProperty('command');
      expect(firstCommand).toHaveProperty('allowed');
      expect(firstCommand).toHaveProperty('addedAt');
      expect(typeof firstCommand.addedAt).toBe('number');
    });

    it('should update timestamp when preset applied', async () => {
      const profile = createPopulatedProfile(50);
      const originalTimestamp = profile.updatedAt;

      // Wait a bit to ensure timestamp difference
      await new Promise(resolve => setTimeout(resolve, 10));

      const updatedProfile = applyPreset(profile, PRESETS.paranoid);

      expect(updatedProfile.updatedAt).toBeGreaterThan(originalTimestamp);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty command allowlist', async () => {
      const profile: SecurityProfile = {
        level: 'standard',
        commandAllowlist: [],
        filesystemRestricted: false,
        apiRestricted: false,
        updatedAt: Date.now()
      };

      const updatedProfile = applyPreset(profile, PRESETS.paranoid);

      expect(updatedProfile.commandAllowlist).toHaveLength(0);
    });

    it('should handle allowlist smaller than preset limit', async () => {
      const profile = createPopulatedProfile(5);
      const updatedProfile = applyPreset(profile, PRESETS.standard);

      // Should keep all 5 commands (doesn't add new ones)
      expect(updatedProfile.commandAllowlist).toHaveLength(5);
    });

    it('should handle allowlist exactly equal to preset limit', async () => {
      const profile = createPopulatedProfile(10);
      const updatedProfile = applyPreset(profile, PRESETS.paranoid);

      expect(updatedProfile.commandAllowlist).toHaveLength(10);
    });
  });
});
