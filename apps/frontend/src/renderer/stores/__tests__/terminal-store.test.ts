/**
 * @vitest-environment jsdom
 */
/**
 * Tests for terminal-store (Zustand) - state management and actions
 * Separate from terminal-store.callbacks.test.ts which tests output callbacks
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock terminal-buffer-manager module
vi.mock('../../lib/terminal-buffer-manager', () => ({
  terminalBufferManager: {
    append: vi.fn(),
    getSize: vi.fn(() => 100),
    get: vi.fn(() => ''),
    set: vi.fn(),
    clear: vi.fn(),
    dispose: vi.fn(),
  },
}));

// Mock debug-logger module
vi.mock('../../../shared/utils/debug-logger', () => ({
  debugLog: vi.fn(),
  debugError: vi.fn(),
}));

// Mock uuid with incrementing IDs
let uuidCounter = 0;
vi.mock('uuid', () => ({
  v4: vi.fn(() => `mock-uuid-${++uuidCounter}`),
}));

// Mock @dnd-kit/sortable
vi.mock('@dnd-kit/sortable', () => ({
  arrayMove: vi.fn((arr: unknown[], from: number, to: number) => {
    const result = [...arr];
    const [item] = result.splice(from, 1);
    result.splice(to, 0, item);
    return result;
  }),
}));

import { useTerminalStore } from '../terminal-store';
import type { Terminal } from '../terminal-store';

describe('terminal-store state management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    uuidCounter = 0;
    // Reset store
    useTerminalStore.setState({
      terminals: [],
      layouts: [],
      activeTerminalId: null,
      maxTerminals: 12,
      hasRestoredSessions: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useTerminalStore.getState();
      expect(state.terminals).toEqual([]);
      expect(state.layouts).toEqual([]);
      expect(state.activeTerminalId).toBeNull();
      expect(state.maxTerminals).toBe(12);
      expect(state.hasRestoredSessions).toBe(false);
    });
  });

  describe('addTerminal', () => {
    it('should add a new terminal', () => {
      const { addTerminal } = useTerminalStore.getState();
      const terminal = addTerminal('/home/user', '/project');

      expect(terminal).not.toBeNull();
      expect(terminal!.cwd).toBe('/home/user');
      expect(terminal!.projectPath).toBe('/project');
      expect(terminal!.status).toBe('idle');
      expect(terminal!.isClaudeMode).toBe(false);

      const state = useTerminalStore.getState();
      expect(state.terminals).toHaveLength(1);
      expect(state.activeTerminalId).toBe(terminal!.id);
    });

    it('should set new terminal as active', () => {
      const { addTerminal } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      const t2 = addTerminal('/home', '/project');

      const state = useTerminalStore.getState();
      expect(state.activeTerminalId).toBe(t2!.id);
    });

    it('should return null when limit is reached', () => {
      useTerminalStore.setState({ maxTerminals: 2 });
      const { addTerminal } = useTerminalStore.getState();

      addTerminal('/home', '/project');
      addTerminal('/home', '/project');
      const third = addTerminal('/home', '/project');

      expect(third).toBeNull();
      expect(useTerminalStore.getState().terminals).toHaveLength(2);
    });

    it('should count limits per project', () => {
      useTerminalStore.setState({ maxTerminals: 2 });
      const { addTerminal } = useTerminalStore.getState();

      addTerminal('/home', '/projectA');
      addTerminal('/home', '/projectA');
      const t3 = addTerminal('/home', '/projectB'); // different project

      expect(t3).not.toBeNull();
      expect(useTerminalStore.getState().terminals).toHaveLength(3);
    });

    it('should not count exited terminals against limit', () => {
      useTerminalStore.setState({ maxTerminals: 2 });
      const { addTerminal, setTerminalStatus } = useTerminalStore.getState();

      const t1 = addTerminal('/home', '/project');
      addTerminal('/home', '/project');

      // Exit the first terminal
      setTerminalStatus(t1!.id, 'exited');

      // Should be able to add another now
      const t3 = addTerminal('/home', '/project');
      expect(t3).not.toBeNull();
    });
  });

  describe('addExternalTerminal', () => {
    it('should add a terminal with specified ID', () => {
      const { addExternalTerminal } = useTerminalStore.getState();
      const terminal = addExternalTerminal('ext-123', 'OAuth Login', '/home', '/project');

      expect(terminal).not.toBeNull();
      expect(terminal!.id).toBe('ext-123');
      expect(terminal!.title).toBe('OAuth Login');
      expect(terminal!.status).toBe('running');
    });

    it('should activate existing terminal if ID already exists', () => {
      const { addTerminal, addExternalTerminal } = useTerminalStore.getState();
      addTerminal('/home', '/project');

      const state = useTerminalStore.getState();
      const existingId = state.terminals[0].id;

      const result = addExternalTerminal(existingId, 'Duplicate', '/home', '/project');
      expect(result!.id).toBe(existingId);
      expect(useTerminalStore.getState().terminals).toHaveLength(1);
      expect(useTerminalStore.getState().activeTerminalId).toBe(existingId);
    });
  });

  describe('removeTerminal', () => {
    it('should remove terminal by id', () => {
      const { addTerminal, removeTerminal } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      addTerminal('/home', '/project');

      removeTerminal(t1!.id);

      const state = useTerminalStore.getState();
      expect(state.terminals).toHaveLength(1);
      expect(state.terminals.find(t => t.id === t1!.id)).toBeUndefined();
    });

    it('should switch active to last terminal when active is removed', () => {
      const { addTerminal, removeTerminal } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      const t2 = addTerminal('/home', '/project');

      removeTerminal(t2!.id);

      expect(useTerminalStore.getState().activeTerminalId).toBe(t1!.id);
    });

    it('should set activeTerminalId to null when last terminal removed', () => {
      const { addTerminal, removeTerminal } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');

      removeTerminal(t1!.id);

      expect(useTerminalStore.getState().activeTerminalId).toBeNull();
      expect(useTerminalStore.getState().terminals).toHaveLength(0);
    });
  });

  describe('updateTerminal', () => {
    it('should update terminal fields', () => {
      const { addTerminal, updateTerminal } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      updateTerminal(t!.id, { title: 'My Terminal', cwd: '/new/path' });

      const updated = useTerminalStore.getState().terminals[0];
      expect(updated.title).toBe('My Terminal');
      expect(updated.cwd).toBe('/new/path');
    });

    it('should only update specified terminal', () => {
      const { addTerminal, updateTerminal } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      const t2 = addTerminal('/home', '/project');

      updateTerminal(t1!.id, { title: 'Updated' });

      const state = useTerminalStore.getState();
      const term1 = state.terminals.find(t => t.id === t1!.id)!;
      const term2 = state.terminals.find(t => t.id === t2!.id)!;
      expect(term1.title).toBe('Updated');
      // t2 should keep its auto-generated title
      expect(term2.title).toContain('Terminal');
      expect(term2.title).not.toBe('Updated');
    });
  });

  describe('setActiveTerminal', () => {
    it('should set active terminal', () => {
      const { addTerminal, setActiveTerminal } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      addTerminal('/home', '/project');

      setActiveTerminal(t1!.id);
      expect(useTerminalStore.getState().activeTerminalId).toBe(t1!.id);
    });

    it('should allow null', () => {
      const { addTerminal, setActiveTerminal } = useTerminalStore.getState();
      addTerminal('/home', '/project');

      setActiveTerminal(null);
      expect(useTerminalStore.getState().activeTerminalId).toBeNull();
    });
  });

  describe('setTerminalStatus', () => {
    it('should update terminal status', () => {
      const { addTerminal, setTerminalStatus } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setTerminalStatus(t!.id, 'running');
      expect(useTerminalStore.getState().terminals[0].status).toBe('running');

      setTerminalStatus(t!.id, 'exited');
      expect(useTerminalStore.getState().terminals[0].status).toBe('exited');
    });
  });

  describe('setClaudeMode', () => {
    it('should enable claude mode and set status', () => {
      const { addTerminal, setClaudeMode } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setClaudeMode(t!.id, true);

      const terminal = useTerminalStore.getState().terminals[0];
      expect(terminal.isClaudeMode).toBe(true);
      expect(terminal.status).toBe('claude-active');
    });

    it('should disable claude mode and reset busy/named flags', () => {
      const { addTerminal, setClaudeMode, setClaudeBusy, setClaudeNamedOnce } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setClaudeMode(t!.id, true);
      setClaudeBusy(t!.id, true);
      setClaudeNamedOnce(t!.id, true);

      setClaudeMode(t!.id, false);

      const terminal = useTerminalStore.getState().terminals[0];
      expect(terminal.isClaudeMode).toBe(false);
      expect(terminal.status).toBe('running');
      expect(terminal.isClaudeBusy).toBeUndefined();
      expect(terminal.claudeNamedOnce).toBeUndefined();
    });
  });

  describe('setClaudeSessionId', () => {
    it('should set claude session id for resume', () => {
      const { addTerminal, setClaudeSessionId } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setClaudeSessionId(t!.id, 'session-abc-123');

      expect(useTerminalStore.getState().terminals[0].claudeSessionId).toBe('session-abc-123');
    });
  });

  describe('setAssociatedTask', () => {
    it('should associate a task with terminal', () => {
      const { addTerminal, setAssociatedTask } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setAssociatedTask(t!.id, 'task-001');
      expect(useTerminalStore.getState().terminals[0].associatedTaskId).toBe('task-001');
    });

    it('should clear task association', () => {
      const { addTerminal, setAssociatedTask } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setAssociatedTask(t!.id, 'task-001');
      setAssociatedTask(t!.id, undefined);
      expect(useTerminalStore.getState().terminals[0].associatedTaskId).toBeUndefined();
    });
  });

  describe('setWorktreeConfig', () => {
    it('should set worktree config', () => {
      const { addTerminal, setWorktreeConfig } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');
      const config = { branch: 'auto-code/feature', worktreePath: '/project/.worktrees/feature' };

      setWorktreeConfig(t!.id, config as any);
      expect(useTerminalStore.getState().terminals[0].worktreeConfig).toEqual(config);
    });
  });

  describe('setClaudeBusy', () => {
    it('should toggle claude busy state', () => {
      const { addTerminal, setClaudeBusy } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setClaudeBusy(t!.id, true);
      expect(useTerminalStore.getState().terminals[0].isClaudeBusy).toBe(true);

      setClaudeBusy(t!.id, false);
      expect(useTerminalStore.getState().terminals[0].isClaudeBusy).toBe(false);
    });
  });

  describe('setPendingClaudeResume', () => {
    it('should set pending resume flag', () => {
      const { addTerminal, setPendingClaudeResume } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      setPendingClaudeResume(t!.id, true);
      expect(useTerminalStore.getState().terminals[0].pendingClaudeResume).toBe(true);
    });
  });

  describe('clearAllTerminals', () => {
    it('should clear all terminals and reset state', () => {
      const { addTerminal, clearAllTerminals, setHasRestoredSessions } = useTerminalStore.getState();
      addTerminal('/home', '/project');
      addTerminal('/home', '/project');
      setHasRestoredSessions(true);

      clearAllTerminals();

      const state = useTerminalStore.getState();
      expect(state.terminals).toEqual([]);
      expect(state.activeTerminalId).toBeNull();
      expect(state.hasRestoredSessions).toBe(false);
    });
  });

  describe('reorderTerminals', () => {
    it('should reorder terminals and update displayOrder', () => {
      const { addTerminal, reorderTerminals } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      const t2 = addTerminal('/home', '/project');
      const t3 = addTerminal('/home', '/project');

      // Move t3 to first position
      reorderTerminals(t3!.id, t1!.id);

      const state = useTerminalStore.getState();
      expect(state.terminals[0].id).toBe(t3!.id);
      expect(state.terminals[0].displayOrder).toBe(0);
      expect(state.terminals[1].displayOrder).toBe(1);
      expect(state.terminals[2].displayOrder).toBe(2);
    });

    it('should handle invalid ids gracefully', () => {
      const { addTerminal, reorderTerminals } = useTerminalStore.getState();
      addTerminal('/home', '/project');

      // Should not throw or change state
      reorderTerminals('nonexistent', 'also-nonexistent');

      expect(useTerminalStore.getState().terminals).toHaveLength(1);
    });
  });

  describe('selectors', () => {
    it('getTerminal should find terminal by id', () => {
      const { addTerminal, getTerminal } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      expect(getTerminal(t!.id)).toBeDefined();
      expect(getTerminal(t!.id)!.id).toBe(t!.id);
      expect(getTerminal('nonexistent')).toBeUndefined();
    });

    it('getActiveTerminal should return active terminal', () => {
      const { addTerminal, getActiveTerminal } = useTerminalStore.getState();
      const t = addTerminal('/home', '/project');

      expect(getActiveTerminal()).toBeDefined();
      expect(getActiveTerminal()!.id).toBe(t!.id);
    });

    it('canAddTerminal should check project limit', () => {
      useTerminalStore.setState({ maxTerminals: 2 });
      const { addTerminal, canAddTerminal } = useTerminalStore.getState();

      expect(canAddTerminal('/project')).toBe(true);

      addTerminal('/home', '/project');
      expect(useTerminalStore.getState().canAddTerminal('/project')).toBe(true);

      addTerminal('/home', '/project');
      expect(useTerminalStore.getState().canAddTerminal('/project')).toBe(false);
      // Different project should still allow
      expect(useTerminalStore.getState().canAddTerminal('/other')).toBe(true);
    });

    it('getTerminalsForProject should filter by project', () => {
      const { addTerminal, getTerminalsForProject } = useTerminalStore.getState();
      addTerminal('/home', '/projectA');
      addTerminal('/home', '/projectA');
      addTerminal('/home', '/projectB');

      expect(useTerminalStore.getState().getTerminalsForProject('/projectA')).toHaveLength(2);
      expect(useTerminalStore.getState().getTerminalsForProject('/projectB')).toHaveLength(1);
      expect(useTerminalStore.getState().getTerminalsForProject('/projectC')).toHaveLength(0);
    });

    it('getWorktreeCount should count terminals with worktree config', () => {
      const { addTerminal, setWorktreeConfig, getWorktreeCount } = useTerminalStore.getState();
      const t1 = addTerminal('/home', '/project');
      addTerminal('/home', '/project');

      expect(useTerminalStore.getState().getWorktreeCount()).toBe(0);

      setWorktreeConfig(t1!.id, { branch: 'feat', worktreePath: '/wt' } as any);
      expect(useTerminalStore.getState().getWorktreeCount()).toBe(1);
    });
  });

  describe('addRestoredTerminal', () => {
    it('should restore terminal from session data', () => {
      const { addRestoredTerminal } = useTerminalStore.getState();
      const session = {
        id: 'restored-1',
        title: 'Restored Terminal',
        cwd: '/project',
        createdAt: Date.now(),
        projectPath: '/project',
        claudeSessionId: 'claude-session-1',
        outputBuffer: 'Hello from previous session',
        displayOrder: 0,
      };

      const terminal = addRestoredTerminal(session as any);

      expect(terminal.id).toBe('restored-1');
      expect(terminal.title).toBe('Restored Terminal');
      expect(terminal.isClaudeMode).toBe(false); // Reset on restore
      expect(terminal.claudeSessionId).toBe('claude-session-1');
      expect(terminal.isRestored).toBe(true);
    });

    it('should not duplicate existing terminal', () => {
      const { addRestoredTerminal } = useTerminalStore.getState();
      const session = {
        id: 'restored-1',
        title: 'Restored Terminal',
        cwd: '/project',
        createdAt: Date.now(),
        projectPath: '/project',
      };

      addRestoredTerminal(session as any);
      addRestoredTerminal(session as any);

      expect(useTerminalStore.getState().terminals).toHaveLength(1);
    });

    it('should set first restored terminal as active if no active', () => {
      const { addRestoredTerminal } = useTerminalStore.getState();
      const session = {
        id: 'restored-1',
        title: 'Restored',
        cwd: '/project',
        createdAt: Date.now(),
        projectPath: '/project',
      };

      addRestoredTerminal(session as any);
      expect(useTerminalStore.getState().activeTerminalId).toBe('restored-1');
    });
  });

  describe('setHasRestoredSessions', () => {
    it('should update restored sessions flag', () => {
      const { setHasRestoredSessions } = useTerminalStore.getState();

      setHasRestoredSessions(true);
      expect(useTerminalStore.getState().hasRestoredSessions).toBe(true);

      setHasRestoredSessions(false);
      expect(useTerminalStore.getState().hasRestoredSessions).toBe(false);
    });
  });
});
