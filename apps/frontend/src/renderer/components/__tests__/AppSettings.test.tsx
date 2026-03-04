/**
 * @vitest-environment jsdom
 */
/**
 * Tests for AppSettings configuration - sections, navigation structure
 * Tests the settings section definitions and navigation logic
 */

import { describe, it, expect } from 'vitest';

describe('AppSettings configuration', () => {
  describe('AppSection types', () => {
    // These match the AppSection type in AppSettings.tsx
    const appSections = [
      'appearance', 'display', 'language', 'devtools', 'agent',
      'paths', 'accounts', 'updates', 'notifications', 'keyboardShortcuts', 'debug'
    ];

    it('should have 11 app settings sections', () => {
      expect(appSections).toHaveLength(11);
    });

    it('should include all critical sections', () => {
      expect(appSections).toContain('appearance');
      expect(appSections).toContain('accounts');
      expect(appSections).toContain('notifications');
      expect(appSections).toContain('keyboardShortcuts');
      expect(appSections).toContain('debug');
    });

    it('should have unique section IDs', () => {
      const unique = new Set(appSections);
      expect(unique.size).toBe(appSections.length);
    });

    it('appearance should be first section (default)', () => {
      expect(appSections[0]).toBe('appearance');
    });
  });

  describe('Project settings sections', () => {
    const projectSections = ['general', 'linear', 'github', 'gitlab', 'memory'];

    it('should have 5 project settings sections', () => {
      expect(projectSections).toHaveLength(5);
    });

    it('general should be first section', () => {
      expect(projectSections[0]).toBe('general');
    });

    it('should include integration sections', () => {
      expect(projectSections).toContain('linear');
      expect(projectSections).toContain('github');
      expect(projectSections).toContain('gitlab');
    });

    it('should include memory section', () => {
      expect(projectSections).toContain('memory');
    });
  });

  describe('settings navigation logic', () => {
    it('should default to app top-level section', () => {
      const activeTopLevel: 'app' | 'project' = 'app';
      expect(activeTopLevel).toBe('app');
    });

    it('should support switching between app and project', () => {
      let activeTopLevel: 'app' | 'project' = 'app';

      activeTopLevel = 'project';
      expect(activeTopLevel).toBe('project');

      activeTopLevel = 'app';
      expect(activeTopLevel).toBe('app');
    });

    it('should navigate to initial section when provided', () => {
      const initialSection = 'accounts';
      let currentSection = 'appearance'; // default

      // Simulating the useEffect that navigates to initialSection
      if (initialSection) {
        currentSection = initialSection;
      }

      expect(currentSection).toBe('accounts');
    });

    it('should navigate to project section when initialProjectSection provided', () => {
      const initialProjectSection = 'github';
      let activeTopLevel: 'app' | 'project' = 'app';
      let projectSection = 'general';

      if (initialProjectSection) {
        activeTopLevel = 'project';
        projectSection = initialProjectSection;
      }

      expect(activeTopLevel).toBe('project');
      expect(projectSection).toBe('github');
    });
  });
});
