import { beforeEach, describe, expect, it, vi } from 'vitest';

type IpcHandler = (_event: unknown, payload?: unknown) => Promise<unknown>;

const registeredHandlers = new Map<string, IpcHandler>();

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
    (registerPluginHandlers as unknown as () => void)();

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
        '/app/source/apps/backend/plugins/cli.py',
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
    (registerPluginHandlers as unknown as () => void)();

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
        source: { type: 'directory', path: '/tmp/sample-plugin' }
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
        '/app/source/apps/backend/plugins/cli.py',
        'install',
        '--json',
        '--path',
        '/tmp/sample-plugin'
      ],
      expect.objectContaining({ cwd: '/repo' })
    );
  });
});
