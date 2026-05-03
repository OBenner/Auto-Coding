/**
 * Codex/OpenAI Profile Manager
 *
 * Stores isolated Codex account profiles and exposes CODEX_HOME env vars for
 * terminals and backend subprocesses. This is intentionally separate from
 * Claude OAuth profiles and Anthropic-compatible API key profiles.
 */

import { app } from 'electron';
import { existsSync, readFileSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import path from 'node:path';
import type { CodexProfile, CodexProfileSettings } from '../shared/types';

interface CodexProfileStoreData {
  version: number;
  profiles: CodexProfile[];
  activeProfileId: string | null;
}

const STORE_VERSION = 1;

function getUserDataPath(): string {
  if (typeof app?.getPath === 'function') {
    return app.getPath('userData');
  }
  return path.join(homedir(), '.auto-coding');
}

function getCodexProfilesDir(): string {
  return path.join(getUserDataPath(), 'codex-profiles');
}

function expandHomePath(value: string): string {
  return value.startsWith('~') ? path.join(homedir(), value.slice(1)) : value;
}

function sanitizeProfileSlug(name: string): string {
  return name
    .toLowerCase()
    .replaceAll(/[^a-z0-9]+/g, '-')
    .replaceAll(/-+/g, '-')
    .replaceAll(/^-|-$/g, '') || 'profile';
}

function isValidCodexConfigDir(configDir: string): boolean {
  const normalizedPath = path.resolve(expandHomePath(configDir));
  const codexProfilesDir = path.resolve(getCodexProfilesDir());
  const defaultCodexDir = path.resolve(path.join(homedir(), '.codex'));

  const allowedPrefixes = [codexProfilesDir, defaultCodexDir];
  return allowedPrefixes.some((prefix) => (
    normalizedPath === prefix || normalizedPath.startsWith(prefix + path.sep)
  ));
}

function reviveProfileDates(profile: CodexProfile): CodexProfile {
  return {
    ...profile,
    createdAt: profile.createdAt ? new Date(profile.createdAt) : new Date(),
    lastUsedAt: profile.lastUsedAt ? new Date(profile.lastUsedAt) : undefined,
  };
}

function readCodexEmail(configDir: string): string | undefined {
  const authPath = path.join(expandHomePath(configDir), 'auth.json');
  if (!existsSync(authPath)) {
    return undefined;
  }

  try {
    const authData = JSON.parse(readFileSync(authPath, 'utf-8')) as Record<string, unknown>;
    const account = authData.account as Record<string, unknown> | undefined;
    const email = authData.email || account?.email || authData.user_email;
    return typeof email === 'string' ? email : undefined;
  } catch {
    return undefined;
  }
}

function hasCodexAuthMaterial(configDir: string): boolean {
  const expandedConfigDir = expandHomePath(configDir);
  return [
    'auth.json',
    'credentials.json',
    'sessions',
  ].some((entry) => existsSync(path.join(expandedConfigDir, entry)));
}

export class CodexProfileManager {
  private configDir: string;
  private storePath: string;
  private data: CodexProfileStoreData;
  private initialized = false;

  constructor() {
    this.configDir = path.join(getUserDataPath(), 'config');
    this.storePath = path.join(this.configDir, 'codex-profiles.json');
    this.data = this.createDefaultData();
  }

  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    await mkdir(this.configDir, { recursive: true });
    await mkdir(getCodexProfilesDir(), { recursive: true });

    try {
      const content = await readFile(this.storePath, 'utf-8');
      const parsed = JSON.parse(content) as CodexProfileStoreData;
      this.data = {
        version: parsed.version || STORE_VERSION,
        profiles: (parsed.profiles || []).map(reviveProfileDates),
        activeProfileId: parsed.activeProfileId || null,
      };
    } catch {
      this.data = this.createDefaultData();
      await this.save();
    }

    if (this.data.profiles.length === 0) {
      this.data = this.createDefaultData();
      await this.save();
    }

    this.initialized = true;
  }

  private createDefaultData(): CodexProfileStoreData {
    const profileName = 'Primary';
    const profileId = sanitizeProfileSlug(profileName);
    const configDir = path.join(getCodexProfilesDir(), profileId);

    return {
      version: STORE_VERSION,
      activeProfileId: profileId,
      profiles: [{
        id: profileId,
        name: profileName,
        configDir,
        isDefault: true,
        description: 'Primary Codex/OpenAI account',
        createdAt: new Date(),
      }],
    };
  }

  private async save(): Promise<void> {
    await mkdir(this.configDir, { recursive: true });
    await writeFile(this.storePath, JSON.stringify(this.data, null, 2), 'utf-8');
  }

  getSettings(): CodexProfileSettings {
    return {
      profiles: this.data.profiles.map((profile) => ({
        ...profile,
        email: profile.email || readCodexEmail(profile.configDir),
        isAuthenticated: hasCodexAuthMaterial(profile.configDir),
      })),
      activeProfileId: this.data.activeProfileId,
    };
  }

  getProfile(profileId: string): CodexProfile | undefined {
    return this.data.profiles.find((profile) => profile.id === profileId);
  }

  getActiveProfile(): CodexProfile | null {
    if (!this.data.activeProfileId) {
      return null;
    }
    return this.getProfile(this.data.activeProfileId) || null;
  }

  generateProfileId(name: string): string {
    const base = sanitizeProfileSlug(name);
    const existingIds = new Set(this.data.profiles.map((profile) => profile.id));
    if (!existingIds.has(base)) {
      return base;
    }

    let index = 2;
    while (existingIds.has(`${base}-${index}`)) {
      index += 1;
    }
    return `${base}-${index}`;
  }

  async createProfileDirectory(name: string): Promise<string> {
    const profilesDir = getCodexProfilesDir();
    let dir = path.join(profilesDir, sanitizeProfileSlug(name));
    let index = 2;
    while (existsSync(dir)) {
      dir = path.join(profilesDir, `${sanitizeProfileSlug(name)}-${index}`);
      index += 1;
    }
    await mkdir(dir, { recursive: true });
    return dir;
  }

  async createProfile(name: string): Promise<CodexProfile> {
    const profileName = name.trim();
    if (!profileName) {
      throw new Error('Profile name is required');
    }

    const profile: CodexProfile = {
      id: this.generateProfileId(profileName),
      name: profileName,
      configDir: await this.createProfileDirectory(profileName),
      isDefault: this.data.profiles.length === 0,
      createdAt: new Date(),
    };

    return this.saveProfile(profile);
  }

  async saveProfile(profile: CodexProfile): Promise<CodexProfile> {
    if (!profile.id) {
      profile.id = this.generateProfileId(profile.name);
    }
    profile.configDir = expandHomePath(profile.configDir);

    if (!isValidCodexConfigDir(profile.configDir)) {
      throw new Error(`Invalid Codex config directory: ${profile.configDir}`);
    }

    await mkdir(profile.configDir, { recursive: true });

    const index = this.data.profiles.findIndex((existing) => existing.id === profile.id);
    if (index >= 0) {
      this.data.profiles[index] = profile;
    } else {
      this.data.profiles.push(profile);
    }

    if (!this.data.activeProfileId) {
      this.data.activeProfileId = profile.id;
    }

    await this.save();
    return profile;
  }

  async deleteProfile(profileId: string): Promise<boolean> {
    const profile = this.getProfile(profileId);
    if (!profile || profile.isDefault || this.data.profiles.length <= 1) {
      return false;
    }

    this.data.profiles = this.data.profiles.filter((item) => item.id !== profileId);
    if (this.data.activeProfileId === profileId) {
      this.data.activeProfileId = this.data.profiles[0]?.id || null;
    }
    await this.save();
    return true;
  }

  async renameProfile(profileId: string, newName: string): Promise<boolean> {
    const profile = this.getProfile(profileId);
    if (!profile || !newName.trim()) {
      return false;
    }
    profile.name = newName.trim();
    await this.save();
    return true;
  }

  async setActiveProfile(profileId: string): Promise<boolean> {
    const profile = this.getProfile(profileId);
    if (!profile) {
      return false;
    }
    profile.lastUsedAt = new Date();
    this.data.activeProfileId = profileId;
    await this.save();
    return true;
  }

  getActiveProfileEnv(): Record<string, string> {
    const profile = this.getActiveProfile();
    if (!profile?.configDir) {
      return {};
    }

    return {
      CODEX_HOME: expandHomePath(profile.configDir),
      AUTO_CODING_AUTH_PROVIDER: 'codex',
      OPENAI_AUTH_PROVIDER: 'codex',
    };
  }

  getProfileEnv(profileId: string): Record<string, string> {
    const profile = this.getProfile(profileId);
    if (!profile?.configDir) {
      return {};
    }

    return {
      CODEX_HOME: expandHomePath(profile.configDir),
      AUTO_CODING_AUTH_PROVIDER: 'codex',
      OPENAI_AUTH_PROVIDER: 'codex',
    };
  }

  async prepareAuthentication(profileId: string): Promise<{ terminalId: string; configDir: string }> {
    const profile = this.getProfile(profileId);
    if (!profile) {
      throw new Error(`Profile not found: ${profileId}`);
    }

    if (!isValidCodexConfigDir(profile.configDir)) {
      throw new Error(`Invalid Codex config directory: ${profile.configDir}`);
    }

    const configDir = expandHomePath(profile.configDir);
    await mkdir(configDir, { recursive: true });

    return {
      terminalId: `codex-login-${profileId}-${Date.now()}`,
      configDir,
    };
  }

  verifyAuthentication(profileId: string): { authenticated: boolean; email?: string } {
    const profile = this.getProfile(profileId);
    if (!profile) {
      throw new Error(`Profile not found: ${profileId}`);
    }

    const email = readCodexEmail(profile.configDir);
    if (email && profile.email !== email) {
      profile.email = email;
      void this.save();
    }

    return {
      authenticated: hasCodexAuthMaterial(profile.configDir),
      email,
    };
  }
}

let codexProfileManager: CodexProfileManager | null = null;

export async function initializeCodexProfileManager(): Promise<CodexProfileManager> {
  codexProfileManager ??= new CodexProfileManager();
  await codexProfileManager.initialize();
  return codexProfileManager;
}

export function getCodexProfileManager(): CodexProfileManager {
  codexProfileManager ??= new CodexProfileManager();
  return codexProfileManager;
}
