import path from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';

type IpcHandler = (_event: unknown, payload?: unknown) => Promise<unknown>;

const registeredHandlers = new Map<string, IpcHandler>();
const pluginCliPath = path.join('/app/source', 'apps', 'backend', 'plugins', 'cli.py');
const samplePluginPath = path.join('/repo', 'plugins', 'sample-plugin');

const { mockExecFileSync } = vi.hoisted(() => ({
  mockExecFileSync: vi.fn()
}));

vi.mock('electron', () => ({
  ipcMain: {
    handle: vi.fn((channel: string, handler: IpcHandler) => {
      registeredHandlers.set(channel, handler);
    })
  }
}));

vi.mock('child_process', () => ({
  execFileSync: mockExecFileSync
}));

vi.mock('../python-env-manager', () => ({
  getConfiguredPythonPath: vi.fn(() => '/usr/bin/python3')
}));

vi.mock('../updater/path-resolver', () => ({
  getEffectiveSourcePath: vi.fn(() => '/app/source')
}));

vi.mock('../app-logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn()
  }
}));

import { IPC_CHANNELS } from '../../shared/constants';

describe('plugin IPC handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    registeredHandlers.clear();
  });

  it('lists plugins using project-scoped JSON CLI output', async () => {
    const { registerPluginHandlers } = await import('./loader');
    registerPluginHandlers();

    mockExecFileSync.mockReturnValue(
      JSON.stringify({
        success: true,
        plugins: [
          {
            metadata: {
              name: 'codebase-intelligence',
              version: '0.1.0',
              author: 'Auto Code',
              description: 'Code graph tools',
              plugin_type: 'integration',
              required_permissions: ['read_files'],
              dependencies: []
            },
            status: 'enabled',
            plugin_dir: '/repo/apps/backend/plugins/system/codebase-intelligence'
          }
        ]
      })
    );

    const handler = registeredHandlers.get(IPC_CHANNELS.PLUGIN_LIST);
    expect(handler).toBeDefined();

    const result = await handler?.(
      {},
      {
        projectPath: '/repo',
        filter: { pluginType: 'integration', enabledOnly: true }
      }
    );

    expect(result).toEqual({
      success: true,
      data: [
        expect.objectContaining({
          metadata: expect.objectContaining({ name: 'codebase-intelligence' }),
          status: 'enabled',
          plugin_dir: '/repo/apps/backend/plugins/system/codebase-intelligence'
        })
      ]
    });
    expect(mockExecFileSync).toHaveBeenCalledWith(
      '/usr/bin/python3',
      [
        pluginCliPath,
        'list',
        '--json',
        '--type',
        'integration',
        '--enabled-only'
      ],
      expect.objectContaining({ cwd: '/repo' })
    );
  });

  it('installs directory plugins using backend CLI flags that exist', async () => {
    const { registerPluginHandlers } = await import('./loader');
    registerPluginHandlers();

    mockExecFileSync.mockReturnValue(
      JSON.stringify({
        success: true,
        plugin: {
          name: 'sample-plugin',
          version: '1.0.0',
          author: 'Auto Code',
          description: 'Sample',
          plugin_type: 'integration',
          required_permissions: [],
          dependencies: []
        }
      })
    );

    const handler = registeredHandlers.get(IPC_CHANNELS.PLUGIN_INSTALL);
    expect(handler).toBeDefined();

    const result = await handler?.(
      {},
      {
        projectPath: '/repo',
        source: { type: 'directory', path: samplePluginPath }
      }
    );

    expect(result).toEqual({
      success: true,
      data: {
        success: true,
        plugin: expect.objectContaining({ name: 'sample-plugin' })
      }
    });
    expect(mockExecFileSync).toHaveBeenCalledWith(
      '/usr/bin/python3',
      [
        pluginCliPath,
        'install',
        '--json',
        '--path',
        samplePluginPath
      ],
      expect.objectContaining({ cwd: '/repo' })
    );
  });

  it('returns plugin health diagnostics using project-scoped JSON CLI output', async () => {
    const { registerPluginHandlers } = await import('./loader');
    registerPluginHandlers();

    const diagnostics = {
      directories: {
        user_plugins_dir: '/repo/.auto-claude/plugins/user',
        system_plugins_dir: '/app/source/apps/backend/plugins/system'
      },
      summary: {
        total_entries: 1,
        valid_plugins: 1,
        invalid_plugins: 0,
        security_warnings: 0,
        duplicate_names: 0
      },
      plugins: [
        {
          name: 'codebase-intelligence',
          version: '0.1.0',
          plugin_type: 'integration',
          source: 'system',
          plugin_dir: '/app/source/apps/backend/plugins/system/codebase-intelligence',
          manifest_status: 'valid',
          metadata: {
            name: 'codebase-intelligence',
            version: '0.1.0',
            author: 'Auto Code',
            description: 'Code graph tools',
            plugin_type: 'integration',
            required_permissions: ['read_files'],
            dependencies: []
          },
          security: { safe: true, warnings: [] },
          issues: []
        }
      ],
      issues: []
    };

    mockExecFileSync.mockReturnValue(
      JSON.stringify({
        success: true,
        diagnostics
      })
    );

    const handler = registeredHandlers.get(IPC_CHANNELS.PLUGIN_HEALTH);
    expect(handler).toBeDefined();

    const result = await handler?.({}, { projectPath: '/repo' });

    expect(result).toEqual({
      success: true,
      data: diagnostics
    });
    expect(mockExecFileSync).toHaveBeenCalledWith(
      '/usr/bin/python3',
      [
        pluginCliPath,
        'health',
        '--json'
      ],
      expect.objectContaining({ cwd: '/repo' })
    );
  });
});
