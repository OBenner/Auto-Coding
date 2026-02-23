/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useFileExplorerStore } from '../file-explorer-store';
import type { FileNode } from '../../../shared/types';

const mockElectronAPI = {
  listDirectory: vi.fn(),
};

Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

function makeFileNode(overrides: Partial<FileNode> = {}): FileNode {
  return {
    name: 'file.ts',
    path: '/project/file.ts',
    isDirectory: false,
    size: 1024,
    ...overrides,
  } as FileNode;
}

describe('file-explorer-store', () => {
  beforeEach(() => {
    useFileExplorerStore.setState({
      isOpen: false,
      expandedFolders: new Set(),
      files: new Map(),
      isLoading: new Map(),
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('toggle / open / close', () => {
    it('should toggle isOpen', () => {
      expect(useFileExplorerStore.getState().isOpen).toBe(false);
      useFileExplorerStore.getState().toggle();
      expect(useFileExplorerStore.getState().isOpen).toBe(true);
      useFileExplorerStore.getState().toggle();
      expect(useFileExplorerStore.getState().isOpen).toBe(false);
    });

    it('should open', () => {
      useFileExplorerStore.getState().open();
      expect(useFileExplorerStore.getState().isOpen).toBe(true);
    });

    it('should close', () => {
      useFileExplorerStore.setState({ isOpen: true });
      useFileExplorerStore.getState().close();
      expect(useFileExplorerStore.getState().isOpen).toBe(false);
    });
  });

  describe('folder expansion', () => {
    it('should toggle folder expansion', () => {
      useFileExplorerStore.getState().toggleFolder('/src');
      expect(useFileExplorerStore.getState().isExpanded('/src')).toBe(true);

      useFileExplorerStore.getState().toggleFolder('/src');
      expect(useFileExplorerStore.getState().isExpanded('/src')).toBe(false);
    });

    it('should expand folder', () => {
      useFileExplorerStore.getState().expandFolder('/src');
      expect(useFileExplorerStore.getState().isExpanded('/src')).toBe(true);
    });

    it('should collapse folder', () => {
      useFileExplorerStore.getState().expandFolder('/src');
      useFileExplorerStore.getState().collapseFolder('/src');
      expect(useFileExplorerStore.getState().isExpanded('/src')).toBe(false);
    });

    it('should manage multiple expanded folders', () => {
      useFileExplorerStore.getState().expandFolder('/src');
      useFileExplorerStore.getState().expandFolder('/lib');
      expect(useFileExplorerStore.getState().isExpanded('/src')).toBe(true);
      expect(useFileExplorerStore.getState().isExpanded('/lib')).toBe(true);

      useFileExplorerStore.getState().collapseFolder('/src');
      expect(useFileExplorerStore.getState().isExpanded('/src')).toBe(false);
      expect(useFileExplorerStore.getState().isExpanded('/lib')).toBe(true);
    });
  });

  describe('loadDirectory', () => {
    it('should load and cache directory contents', async () => {
      const files = [
        makeFileNode({ name: 'a.ts', path: '/project/a.ts' }),
        makeFileNode({ name: 'b.ts', path: '/project/b.ts' }),
      ];
      mockElectronAPI.listDirectory.mockResolvedValue({ success: true, data: files });

      const result = await useFileExplorerStore.getState().loadDirectory('/project');

      expect(result).toEqual(files);
      expect(useFileExplorerStore.getState().getFiles('/project')).toEqual(files);
      expect(useFileExplorerStore.getState().isLoadingDir('/project')).toBe(false);
    });

    it('should return cached data on subsequent calls', async () => {
      const files = [makeFileNode()];
      mockElectronAPI.listDirectory.mockResolvedValue({ success: true, data: files });

      await useFileExplorerStore.getState().loadDirectory('/project');
      mockElectronAPI.listDirectory.mockClear();

      const result = await useFileExplorerStore.getState().loadDirectory('/project');
      expect(result).toEqual(files);
      expect(mockElectronAPI.listDirectory).not.toHaveBeenCalled();
    });

    it('should handle load errors', async () => {
      mockElectronAPI.listDirectory.mockResolvedValue({
        success: false,
        error: 'Access denied',
      });

      const result = await useFileExplorerStore.getState().loadDirectory('/protected');

      expect(result).toEqual([]);
      expect(useFileExplorerStore.getState().error).toBe('Access denied');
    });
  });

  describe('clearCache', () => {
    it('should clear files cache and expanded folders', () => {
      const files = new Map([['/project', [makeFileNode()]]]);
      const expanded = new Set(['/project']);
      useFileExplorerStore.setState({ files, expandedFolders: expanded });

      useFileExplorerStore.getState().clearCache();

      expect(useFileExplorerStore.getState().files.size).toBe(0);
      expect(useFileExplorerStore.getState().expandedFolders.size).toBe(0);
    });
  });

  describe('selectors', () => {
    it('isLoadingDir should return false for unknown directory', () => {
      expect(useFileExplorerStore.getState().isLoadingDir('/unknown')).toBe(false);
    });

    it('getFiles should return undefined for uncached directory', () => {
      expect(useFileExplorerStore.getState().getFiles('/uncached')).toBeUndefined();
    });

    it('getAllExpandedFiles should return copy of expanded folders set', () => {
      useFileExplorerStore.getState().expandFolder('/a');
      useFileExplorerStore.getState().expandFolder('/b');
      const expanded = useFileExplorerStore.getState().getAllExpandedFiles();
      expect(expanded.size).toBe(2);
      expect(expanded.has('/a')).toBe(true);
      expect(expanded.has('/b')).toBe(true);
    });
  });

  describe('getVisibleFiles', () => {
    it('should collect visible files from expanded directories', () => {
      const rootFiles: FileNode[] = [
        makeFileNode({ name: 'src', path: '/root/src', isDirectory: true }),
        makeFileNode({ name: 'readme.md', path: '/root/readme.md' }),
      ];
      const srcFiles: FileNode[] = [
        makeFileNode({ name: 'index.ts', path: '/root/src/index.ts' }),
      ];

      const files = new Map<string, FileNode[]>();
      files.set('/root', rootFiles);
      files.set('/root/src', srcFiles);

      const expanded = new Set(['/root/src']);

      useFileExplorerStore.setState({ files, expandedFolders: expanded });

      const visible = useFileExplorerStore.getState().getVisibleFiles('/root');
      expect(visible).toHaveLength(3); // src dir, index.ts (child), readme.md
      expect(visible[0].name).toBe('src');
      expect(visible[1].name).toBe('index.ts');
      expect(visible[2].name).toBe('readme.md');
    });

    it('should not include children of collapsed directories', () => {
      const rootFiles: FileNode[] = [
        makeFileNode({ name: 'src', path: '/root/src', isDirectory: true }),
      ];
      const srcFiles: FileNode[] = [
        makeFileNode({ name: 'index.ts', path: '/root/src/index.ts' }),
      ];

      const files = new Map<string, FileNode[]>();
      files.set('/root', rootFiles);
      files.set('/root/src', srcFiles);

      // src is NOT expanded
      useFileExplorerStore.setState({ files, expandedFolders: new Set() });

      const visible = useFileExplorerStore.getState().getVisibleFiles('/root');
      expect(visible).toHaveLength(1);
      expect(visible[0].name).toBe('src');
    });
  });

  describe('computeVisibleItems', () => {
    it('should return nodes and count', () => {
      const rootFiles: FileNode[] = [
        makeFileNode({ name: 'a.ts', path: '/root/a.ts' }),
        makeFileNode({ name: 'b.ts', path: '/root/b.ts' }),
      ];

      const files = new Map<string, FileNode[]>();
      files.set('/root', rootFiles);
      useFileExplorerStore.setState({ files });

      const result = useFileExplorerStore.getState().computeVisibleItems('/root');
      expect(result.count).toBe(2);
      expect(result.nodes).toHaveLength(2);
    });
  });
});
