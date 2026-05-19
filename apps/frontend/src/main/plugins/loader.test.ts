import path from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';

type IpcHandler = (_event: unknown, payload?: unknown) => Promise<unknown>;

const registeredHandlers = new Map<string, IpcHandler>();
const pluginCliPath = path.join('/app/source', 'apps', 'backend', 'plugins', 'cli.py');
const expectedProjectCwd = path.normalize('/repo');
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
  execFile: vi.fn(),
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
              dependencies: [],
              capabilities: ['analysis_only']
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
          metadata: expect.objectContaining({
            name: 'codebase-intelligence',
            capabilities: ['analysis_only']
          }),
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
      expect.objectContaining({ cwd: expectedProjectCwd })
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
          capabilities: ['analysis_only'],
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
      expect.objectContaining({ cwd: expectedProjectCwd })
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
            capabilities: ['analysis_only'],
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
      expect.objectContaining({ cwd: expectedProjectCwd })
    );
  });

  it('returns plugin permission diff before activation', async () => {
    const { registerPluginHandlers } = await import('./loader');
    registerPluginHandlers();

    const permissionDiff = {
      plugin_name: 'guarded-agent',
      required_permissions: ['read_files', 'execute_commands'],
      capabilities: ['analysis_only', 'generic_edit'],
      added_permissions: ['execute_commands'],
      added_capabilities: ['generic_edit'],
      currently_enabled: false,
      would_enable: true
    };

    mockExecFileSync.mockReturnValue(
      JSON.stringify({
        success: true,
        permission_diff: permissionDiff
      })
    );

    const handler = registeredHandlers.get(IPC_CHANNELS.PLUGIN_PERMISSION_DIFF);
    expect(handler).toBeDefined();

    const result = await handler?.(
      {},
      {
        projectPath: '/repo',
        pluginName: 'guarded-agent'
      }
    );

    expect(result).toEqual({
      success: true,
      data: permissionDiff
    });
    expect(mockExecFileSync).toHaveBeenCalledWith(
      '/usr/bin/python3',
      [
        pluginCliPath,
        'permission-diff',
        '--json',
        'guarded-agent'
      ],
      expect.objectContaining({ cwd: expectedProjectCwd })
    );
  });

  it('returns plugin trace events from project state', async () => {
    const { registerPluginHandlers } = await import('./loader');
    registerPluginHandlers();

    const tracePayload = {
      trace_dir: '/repo/.auto-claude/plugin_traces',
      plugin: 'skill-pack-runtime',
      traces: [
        {
          plugin: 'skill-pack-runtime',
          event: 'activated',
          reason: 'task mentions SKILL.md',
          source: 'skill-pack-runtime.jsonl'
        }
      ]
    };

    mockExecFileSync.mockReturnValue(
      JSON.stringify({
        success: true,
        ...tracePayload
      })
    );

    const handler = registeredHandlers.get(IPC_CHANNELS.PLUGIN_TRACES);
    expect(handler).toBeDefined();

    const result = await handler?.(
      {},
      {
        projectPath: '/repo',
        pluginName: 'skill-pack-runtime',
        limit: 5
      }
    );

    expect(result).toEqual({
      success: true,
      data: tracePayload
    });
    expect(mockExecFileSync).toHaveBeenCalledWith(
      '/usr/bin/python3',
      [
        pluginCliPath,
        'traces',
        '--json',
        '--plugin',
        'skill-pack-runtime',
        '--limit',
        '5'
      ],
      expect.objectContaining({ cwd: expectedProjectCwd })
    );
  });

  it('previews enabled plugin prompt contributions for an agent phase', async () => {
    const { registerPluginHandlers } = await import('./loader');
    registerPluginHandlers();

    const previewPayload = {
      agent_type: 'coder',
      spec_dir: '/repo/.auto-claude/plugin-preview',
      runtime_plugins: [
        {
          plugin_name: 'rules-steering-compiler',
          plugin_type: 'integration',
          capabilities: ['analysis_only'],
          contributed: true
        },
        {
          plugin_name: 'skill-pack-runtime',
          plugin_type: 'integration',
          capabilities: ['analysis_only', 'generic_edit'],
          contributed: false
        }
      ],
      contributions: [
        {
          plugin_name: 'rules-steering-compiler',
          capabilities: ['analysis_only'],
          text: 'Use project steering rules.'
        }
      ],
      preview: 'Use project steering rules.'
    };

    mockExecFileSync.mockReturnValue(
      JSON.stringify({
        success: true,
        ...previewPayload
      })
    );

    const handler = registeredHandlers.get(IPC_CHANNELS.PLUGIN_PREVIEW_CONTEXT);
    expect(handler).toBeDefined();

    const result = await handler?.(
      {},
      {
        projectPath: '/repo',
        agentType: 'coder',
        task: 'Wire plugin controls',
        files: ['apps/backend/plugins/cli.py']
      }
    );

    expect(result).toEqual({
      success: true,
      data: previewPayload
    });
    expect(mockExecFileSync).toHaveBeenCalledWith(
      '/usr/bin/python3',
      [
        pluginCliPath,
        'preview-context',
        '--json',
        '--agent-type',
        'coder',
        '--task',
        'Wire plugin controls',
        '--file',
        'apps/backend/plugins/cli.py'
      ],
      expect.objectContaining({ cwd: expectedProjectCwd })
    );
  });
});
