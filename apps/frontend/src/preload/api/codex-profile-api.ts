import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { CodexProfile, CodexProfileSettings, IPCResult } from '../../shared/types';

export interface CodexProfileAPI {
  getCodexProfiles: () => Promise<IPCResult<CodexProfileSettings>>;
  createCodexProfile: (name: string) => Promise<IPCResult<CodexProfile>>;
  saveCodexProfile: (profile: CodexProfile) => Promise<IPCResult<CodexProfile>>;
  deleteCodexProfile: (profileId: string) => Promise<IPCResult>;
  renameCodexProfile: (profileId: string, newName: string) => Promise<IPCResult>;
  setActiveCodexProfile: (profileId: string) => Promise<IPCResult>;
  authenticateCodexProfile: (
    profileId: string
  ) => Promise<IPCResult<{ terminalId: string; configDir: string }>>;
  verifyCodexProfileAuth: (
    profileId: string
  ) => Promise<IPCResult<{ authenticated: boolean; email?: string }>>;
}

export const createCodexProfileAPI = (): CodexProfileAPI => ({
  getCodexProfiles: (): Promise<IPCResult<CodexProfileSettings>> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILES_GET),

  createCodexProfile: (name: string): Promise<IPCResult<CodexProfile>> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_CREATE, name),

  saveCodexProfile: (profile: CodexProfile): Promise<IPCResult<CodexProfile>> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_SAVE, profile),

  deleteCodexProfile: (profileId: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_DELETE, profileId),

  renameCodexProfile: (profileId: string, newName: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_RENAME, profileId, newName),

  setActiveCodexProfile: (profileId: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_SET_ACTIVE, profileId),

  authenticateCodexProfile: (
    profileId: string
  ): Promise<IPCResult<{ terminalId: string; configDir: string }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_AUTHENTICATE, profileId),

  verifyCodexProfileAuth: (
    profileId: string
  ): Promise<IPCResult<{ authenticated: boolean; email?: string }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.CODEX_PROFILE_VERIFY_AUTH, profileId),
});
