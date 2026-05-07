/**
 * @vitest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CompletionStep } from './CompletionStep';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'completion.title': "You're All Set!",
        'completion.subtitle': 'Auto-Coding is ready',
        'completion.setupComplete': 'Setup Complete',
        'completion.setupCompleteDescription': 'Your environment is configured.',
        'completion.whatsNext': "What's Next?",
        'completion.createTask.title': 'Create a Task',
        'completion.createTask.description': 'Start by creating your first task.',
        'completion.createTask.action': 'Open Task Creator',
        'completion.customizeSettings.title': 'Customize Settings',
        'completion.customizeSettings.description': 'Fine-tune your preferences.',
        'completion.customizeSettings.action': 'Open Settings',
        'completion.exploreDocs.title': 'Explore Documentation',
        'completion.exploreDocs.description': 'Learn more about advanced features.',
        'completion.finish': 'Finish & Start Building',
        'completion.rerunHint': 'You can re-run this wizard from Settings',
        'completion.readiness.title': 'Environment readiness',
        'completion.readiness.checking': 'Checking readiness...',
        'completion.readiness.codexAuth.ready': 'Codex account connected',
        'completion.readiness.codexAuth.issue': 'Connect a Codex account',
        'completion.readiness.codexCli.ready': 'Codex CLI ready',
        'completion.readiness.codexCli.issue': 'Install Codex CLI',
        'completion.readiness.memory.ready': 'Memory database ready',
        'completion.readiness.memory.issue': 'Memory needs attention',
        'completion.readiness.memory.skipped': 'Memory disabled'
      };
      return translations[key] || key;
    }
  })
}));

vi.mock('../../stores/settings-store', () => ({
  useSettingsStore: () => ({
    settings: { memoryEnabled: true },
    profiles: []
  })
}));

vi.mock('../../stores/claude-profile-store', () => ({
  useClaudeProfileStore: () => ({
    profiles: []
  })
}));

const mockElectronAPI = {
  checkCodexCodeVersion: vi.fn(),
  getCodexProfiles: vi.fn(),
  getMemoryInfrastructureStatus: vi.fn()
};

Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true
});

describe('CompletionStep readiness checks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockElectronAPI.checkCodexCodeVersion.mockResolvedValue({
      success: true,
      data: {
        installed: '0.128.0',
        latest: '0.128.0',
        isOutdated: false,
        path: '/usr/local/bin/codex'
      }
    });
    mockElectronAPI.getCodexProfiles.mockResolvedValue({
      success: true,
      data: {
        activeProfileId: 'codex-work',
        profiles: [{ id: 'codex-work', name: 'Work', authenticated: true }]
      }
    });
    mockElectronAPI.getMemoryInfrastructureStatus.mockResolvedValue({
      success: true,
      data: {
        ready: true,
        memory: {
          kuzuInstalled: true,
          databasePath: '/tmp/memory',
          databaseExists: true,
          databases: []
        }
      }
    });
  });

  it('checks the selected Codex runtime and memory readiness before finish', async () => {
    render(
      <CompletionStep
        authRuntime="codex"
        onFinish={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(mockElectronAPI.getCodexProfiles).toHaveBeenCalled();
      expect(mockElectronAPI.checkCodexCodeVersion).toHaveBeenCalled();
      expect(mockElectronAPI.getMemoryInfrastructureStatus).toHaveBeenCalled();
    });

    expect(screen.getByText('Environment readiness')).toBeInTheDocument();
    expect(screen.getByText('Codex account connected')).toBeInTheDocument();
    expect(screen.getByText('Codex CLI ready')).toBeInTheDocument();
    expect(screen.getByText('Memory database ready')).toBeInTheDocument();
  });
});
