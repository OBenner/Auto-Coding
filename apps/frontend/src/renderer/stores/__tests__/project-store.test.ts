/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useProjectStore } from '../project-store';
import type { Project } from '../../../shared/types';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock electronAPI (for tab state save, not directly tested)
const mockElectronAPI = {
  saveTabState: vi.fn().mockResolvedValue({ success: true }),
  getTabState: vi.fn().mockResolvedValue({ success: true, data: null }),
  getProjects: vi.fn().mockResolvedValue({ success: true, data: [] }),
};

Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    name: 'Test Project',
    path: '/path/to/project',
    ...overrides,
  } as Project;
}

describe('project-store', () => {
  beforeEach(() => {
    useProjectStore.setState({
      projects: [],
      selectedProjectId: null,
      isLoading: false,
      error: null,
      openProjectIds: [],
      activeProjectId: null,
      tabOrder: [],
    });
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should have correct defaults', () => {
      const state = useProjectStore.getState();
      expect(state.projects).toEqual([]);
      expect(state.selectedProjectId).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.openProjectIds).toEqual([]);
      expect(state.activeProjectId).toBeNull();
      expect(state.tabOrder).toEqual([]);
    });
  });

  describe('project CRUD', () => {
    it('should set projects', () => {
      const projects = [makeProject({ id: 'p1' }), makeProject({ id: 'p2' })];
      useProjectStore.getState().setProjects(projects);
      expect(useProjectStore.getState().projects).toHaveLength(2);
    });

    it('should add project', () => {
      useProjectStore.setState({ projects: [makeProject({ id: 'p1' })] });

      useProjectStore.getState().addProject(makeProject({ id: 'p2', name: 'New' }));

      expect(useProjectStore.getState().projects).toHaveLength(2);
      expect(useProjectStore.getState().projects[1].id).toBe('p2');
    });

    it('should remove project', () => {
      useProjectStore.setState({
        projects: [makeProject({ id: 'p1' }), makeProject({ id: 'p2' })],
      });

      useProjectStore.getState().removeProject('p1');

      expect(useProjectStore.getState().projects).toHaveLength(1);
      expect(useProjectStore.getState().projects[0].id).toBe('p2');
    });

    it('should clear selectedProjectId when removing selected project', () => {
      useProjectStore.setState({
        projects: [makeProject({ id: 'p1' })],
        selectedProjectId: 'p1',
      });

      useProjectStore.getState().removeProject('p1');

      expect(useProjectStore.getState().selectedProjectId).toBeNull();
    });

    it('should not clear selectedProjectId when removing different project', () => {
      useProjectStore.setState({
        projects: [makeProject({ id: 'p1' }), makeProject({ id: 'p2' })],
        selectedProjectId: 'p1',
      });

      useProjectStore.getState().removeProject('p2');

      expect(useProjectStore.getState().selectedProjectId).toBe('p1');
    });

    it('should update project', () => {
      useProjectStore.setState({
        projects: [makeProject({ id: 'p1', name: 'Old Name' })],
      });

      useProjectStore.getState().updateProject('p1', { name: 'New Name' });

      expect(useProjectStore.getState().projects[0].name).toBe('New Name');
    });
  });

  describe('selectProject', () => {
    it('should set selectedProjectId and persist to localStorage', () => {
      useProjectStore.getState().selectProject('p1');
      expect(useProjectStore.getState().selectedProjectId).toBe('p1');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('lastSelectedProjectId', 'p1');
    });

    it('should remove from localStorage when selecting null', () => {
      useProjectStore.getState().selectProject(null);
      expect(useProjectStore.getState().selectedProjectId).toBeNull();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('lastSelectedProjectId');
    });
  });

  describe('tab management', () => {
    it('should open a new project tab', () => {
      useProjectStore.getState().openProjectTab('p1');

      const state = useProjectStore.getState();
      expect(state.openProjectIds).toContain('p1');
      expect(state.tabOrder).toContain('p1');
      expect(state.activeProjectId).toBe('p1');
    });

    it('should not duplicate when opening already open tab', () => {
      useProjectStore.setState({
        openProjectIds: ['p1'],
        tabOrder: ['p1'],
        activeProjectId: 'p1',
      });

      useProjectStore.getState().openProjectTab('p1');

      expect(useProjectStore.getState().openProjectIds).toEqual(['p1']);
    });

    it('should close a project tab', () => {
      useProjectStore.setState({
        openProjectIds: ['p1', 'p2'],
        tabOrder: ['p1', 'p2'],
        activeProjectId: 'p1',
      });

      useProjectStore.getState().closeProjectTab('p1');

      const state = useProjectStore.getState();
      expect(state.openProjectIds).toEqual(['p2']);
      expect(state.tabOrder).toEqual(['p2']);
      // Active should switch to next tab
      expect(state.activeProjectId).toBe('p2');
    });

    it('should set activeProjectId to null when closing last tab', () => {
      useProjectStore.setState({
        openProjectIds: ['p1'],
        tabOrder: ['p1'],
        activeProjectId: 'p1',
      });

      useProjectStore.getState().closeProjectTab('p1');

      expect(useProjectStore.getState().activeProjectId).toBeNull();
    });

    it('should reorder tabs', () => {
      useProjectStore.setState({
        tabOrder: ['p1', 'p2', 'p3'],
      });

      useProjectStore.getState().reorderTabs(0, 2);

      expect(useProjectStore.getState().tabOrder).toEqual(['p2', 'p3', 'p1']);
    });
  });

  describe('loading and error', () => {
    it('should set loading state', () => {
      useProjectStore.getState().setLoading(true);
      expect(useProjectStore.getState().isLoading).toBe(true);
    });

    it('should set error', () => {
      useProjectStore.getState().setError('Something went wrong');
      expect(useProjectStore.getState().error).toBe('Something went wrong');
    });
  });

  describe('selectors', () => {
    const projects = [
      makeProject({ id: 'p1', name: 'Project 1' }),
      makeProject({ id: 'p2', name: 'Project 2' }),
      makeProject({ id: 'p3', name: 'Project 3' }),
    ];

    it('getSelectedProject should return project matching selectedProjectId', () => {
      useProjectStore.setState({ projects, selectedProjectId: 'p2' });
      expect(useProjectStore.getState().getSelectedProject()?.name).toBe('Project 2');
    });

    it('getSelectedProject should return undefined when no match', () => {
      useProjectStore.setState({ projects, selectedProjectId: 'p99' });
      expect(useProjectStore.getState().getSelectedProject()).toBeUndefined();
    });

    it('getOpenProjects should return open projects', () => {
      useProjectStore.setState({
        projects,
        openProjectIds: ['p1', 'p3'],
      });

      const open = useProjectStore.getState().getOpenProjects();
      expect(open).toHaveLength(2);
      expect(open.map((p) => p.id)).toEqual(['p1', 'p3']);
    });

    it('getActiveProject should return active project', () => {
      useProjectStore.setState({ projects, activeProjectId: 'p2' });
      expect(useProjectStore.getState().getActiveProject()?.name).toBe('Project 2');
    });

    it('getProjectTabs should return projects in tab order', () => {
      useProjectStore.setState({
        projects,
        openProjectIds: ['p1', 'p2', 'p3'],
        tabOrder: ['p3', 'p1', 'p2'],
      });

      const tabs = useProjectStore.getState().getProjectTabs();
      expect(tabs.map((p) => p.id)).toEqual(['p3', 'p1', 'p2']);
    });

    it('getProjectTabs should include open projects not in tabOrder', () => {
      useProjectStore.setState({
        projects,
        openProjectIds: ['p1', 'p2', 'p3'],
        tabOrder: ['p1'],
      });

      const tabs = useProjectStore.getState().getProjectTabs();
      expect(tabs).toHaveLength(3);
      expect(tabs[0].id).toBe('p1'); // from tabOrder
      // p2, p3 appended after
    });
  });
});
