/**
 * Codex/OpenAI account profile IPC handlers.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { CodexProfile, CodexProfileSettings, IPCResult } from '../../shared/types';
import { getCodexProfileManager } from '../codex-profile-manager';

export function registerCodexProfileHandlers(): void {
  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILES_GET,
    async (): Promise<IPCResult<CodexProfileSettings>> => {
      try {
        return { success: true, data: getCodexProfileManager().getSettings() };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get Codex profiles',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_CREATE,
    async (_, name: string): Promise<IPCResult<CodexProfile>> => {
      try {
        const savedProfile = await getCodexProfileManager().createProfile(name);
        return { success: true, data: savedProfile };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to create Codex profile',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_SAVE,
    async (_, profile: CodexProfile): Promise<IPCResult<CodexProfile>> => {
      try {
        const savedProfile = await getCodexProfileManager().saveProfile(profile);
        return { success: true, data: savedProfile };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save Codex profile',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_DELETE,
    async (_, profileId: string): Promise<IPCResult> => {
      try {
        const success = await getCodexProfileManager().deleteProfile(profileId);
        if (!success) {
          return { success: false, error: 'Cannot delete default or last profile' };
        }
        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to delete Codex profile',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_RENAME,
    async (_, profileId: string, newName: string): Promise<IPCResult> => {
      try {
        const success = await getCodexProfileManager().renameProfile(profileId, newName);
        if (!success) {
          return { success: false, error: 'Profile not found or invalid name' };
        }
        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to rename Codex profile',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_SET_ACTIVE,
    async (_, profileId: string): Promise<IPCResult> => {
      try {
        const success = await getCodexProfileManager().setActiveProfile(profileId);
        if (!success) {
          return { success: false, error: 'Profile not found' };
        }
        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to set active Codex profile',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_AUTHENTICATE,
    async (_, profileId: string): Promise<IPCResult<{ terminalId: string; configDir: string }>> => {
      try {
        const authConfig = await getCodexProfileManager().prepareAuthentication(profileId);
        return { success: true, data: authConfig };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to prepare Codex authentication',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.CODEX_PROFILE_VERIFY_AUTH,
    async (_, profileId: string): Promise<IPCResult<{ authenticated: boolean; email?: string }>> => {
      try {
        const result = getCodexProfileManager().verifyAuthentication(profileId);
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to verify Codex authentication',
        };
      }
    }
  );
}
