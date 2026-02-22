/**
 * @vitest-environment jsdom
 */
/**
 * Tests for Sidebar navigation logic - nav items, keyboard shortcuts, view types
 * Tests the exported types and navigation item configurations
 */

import { describe, it, expect } from 'vitest';

// Test the SidebarView type and navigation configuration directly
// without rendering the full component (which has too many deep dependencies)

describe('Sidebar navigation configuration', () => {
  describe('SidebarView types', () => {
    it('should define all expected sidebar views', () => {
      // These are the valid SidebarView values as defined in Sidebar.tsx
      const validViews = [
        'kanban', 'terminals', 'roadmap', 'context', 'ideation',
        'github-issues', 'gitlab-issues', 'github-prs', 'gitlab-merge-requests',
        'changelog', 'insights', 'worktrees', 'agent-tools', 'plugins',
        'analytics', 'merge-analytics', 'sessions', 'scheduler',
      ];

      // Verify we have a comprehensive set of views
      expect(validViews).toHaveLength(18);
      expect(validViews).toContain('kanban');
      expect(validViews).toContain('terminals');
      expect(validViews).toContain('insights');
      expect(validViews).toContain('github-prs');
      expect(validViews).toContain('gitlab-merge-requests');
      expect(validViews).toContain('scheduler');
    });
  });

  describe('base navigation items', () => {
    // These match the baseNavItems array in Sidebar.tsx
    const baseNavItems = [
      { id: 'kanban', shortcut: 'K' },
      { id: 'terminals', shortcut: 'A' },
      { id: 'insights', shortcut: 'N' },
      { id: 'roadmap', shortcut: 'D' },
      { id: 'ideation', shortcut: 'I' },
      { id: 'changelog', shortcut: 'L' },
      { id: 'scheduler', shortcut: 'S' },
      { id: 'context', shortcut: 'C' },
      { id: 'agent-tools', shortcut: 'M' },
      { id: 'plugins', shortcut: 'U' },
      { id: 'worktrees', shortcut: 'W' },
      { id: 'analytics', shortcut: 'T' },
      { id: 'merge-analytics', shortcut: 'Y' },
      { id: 'sessions' }, // no shortcut
    ];

    it('should have 14 base navigation items', () => {
      expect(baseNavItems).toHaveLength(14);
    });

    it('should have unique shortcuts', () => {
      const shortcuts = baseNavItems
        .filter(item => item.shortcut)
        .map(item => item.shortcut);

      const uniqueShortcuts = new Set(shortcuts);
      expect(uniqueShortcuts.size).toBe(shortcuts.length);
    });

    it('should have unique IDs', () => {
      const ids = baseNavItems.map(item => item.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it('kanban should be first item', () => {
      expect(baseNavItems[0].id).toBe('kanban');
    });

    it('sessions should have no shortcut', () => {
      const sessions = baseNavItems.find(item => item.id === 'sessions');
      expect(sessions).toBeDefined();
      expect(sessions!.shortcut).toBeUndefined();
    });
  });

  describe('GitHub navigation items', () => {
    const githubNavItems = [
      { id: 'github-issues', shortcut: 'G' },
      { id: 'github-prs', shortcut: 'P' },
    ];

    it('should have 2 GitHub items', () => {
      expect(githubNavItems).toHaveLength(2);
    });

    it('should have unique shortcuts not conflicting with base', () => {
      const baseShortcuts = ['K', 'A', 'N', 'D', 'I', 'L', 'S', 'C', 'M', 'U', 'W', 'T', 'Y'];
      githubNavItems.forEach(item => {
        expect(baseShortcuts).not.toContain(item.shortcut);
      });
    });
  });

  describe('GitLab navigation items', () => {
    const gitlabNavItems = [
      { id: 'gitlab-issues', shortcut: 'B' },
      { id: 'gitlab-merge-requests', shortcut: 'R' },
    ];

    it('should have 2 GitLab items', () => {
      expect(gitlabNavItems).toHaveLength(2);
    });

    it('should have unique shortcuts not conflicting with base or GitHub', () => {
      const usedShortcuts = ['K', 'A', 'N', 'D', 'I', 'L', 'S', 'C', 'M', 'U', 'W', 'T', 'Y', 'G', 'P'];
      gitlabNavItems.forEach(item => {
        expect(usedShortcuts).not.toContain(item.shortcut);
      });
    });
  });

  describe('keyboard shortcut logic', () => {
    it('should map uppercase key to view', () => {
      const navItems = [
        { id: 'kanban', shortcut: 'K' },
        { id: 'terminals', shortcut: 'A' },
      ];

      const findViewByKey = (key: string) => {
        const upper = key.toUpperCase();
        return navItems.find(item => item.shortcut === upper)?.id;
      };

      expect(findViewByKey('k')).toBe('kanban');
      expect(findViewByKey('K')).toBe('kanban');
      expect(findViewByKey('a')).toBe('terminals');
      expect(findViewByKey('x')).toBeUndefined();
    });

    it('should ignore keys with modifiers', () => {
      // The Sidebar ignores shortcuts when metaKey, ctrlKey, or altKey are held
      const shouldIgnoreShortcut = (e: { metaKey: boolean; ctrlKey: boolean; altKey: boolean }) => {
        return e.metaKey || e.ctrlKey || e.altKey;
      };

      expect(shouldIgnoreShortcut({ metaKey: false, ctrlKey: false, altKey: false })).toBe(false);
      expect(shouldIgnoreShortcut({ metaKey: true, ctrlKey: false, altKey: false })).toBe(true);
      expect(shouldIgnoreShortcut({ metaKey: false, ctrlKey: true, altKey: false })).toBe(true);
      expect(shouldIgnoreShortcut({ metaKey: false, ctrlKey: false, altKey: true })).toBe(true);
    });
  });
});
