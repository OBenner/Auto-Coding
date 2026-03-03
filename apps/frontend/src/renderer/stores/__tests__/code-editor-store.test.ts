/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useCodeEditorStore } from '../code-editor-store';

// Mock window.electronAPI
const mockElectronAPI = {
  readFile: vi.fn(),
  writeFile: vi.fn(),
};

Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

describe('code-editor-store', () => {
  beforeEach(() => {
    useCodeEditorStore.setState({
      currentFile: null,
      content: '',
      originalContent: '',
      isDirty: false,
      isLoading: false,
      isSaving: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should have clean initial state', () => {
      const state = useCodeEditorStore.getState();
      expect(state.currentFile).toBeNull();
      expect(state.content).toBe('');
      expect(state.originalContent).toBe('');
      expect(state.isDirty).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.isSaving).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('openFile', () => {
    it('should load file content successfully', async () => {
      mockElectronAPI.readFile.mockResolvedValue({
        success: true,
        data: 'file content here',
      });

      await useCodeEditorStore.getState().openFile('/path/to/file.ts');

      const state = useCodeEditorStore.getState();
      expect(state.currentFile).toBe('/path/to/file.ts');
      expect(state.content).toBe('file content here');
      expect(state.originalContent).toBe('file content here');
      expect(state.isDirty).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should reject binary files without calling API', async () => {
      await useCodeEditorStore.getState().openFile('/path/to/image.png');

      const state = useCodeEditorStore.getState();
      expect(state.currentFile).toBe('/path/to/image.png');
      expect(state.error).toBe('Binary files cannot be displayed in the editor');
      expect(mockElectronAPI.readFile).not.toHaveBeenCalled();
    });

    it('should reject various binary extensions', async () => {
      const binaryExtensions = ['.jpg', '.pdf', '.zip', '.exe', '.mp3', '.woff2'];
      for (const ext of binaryExtensions) {
        await useCodeEditorStore.getState().openFile(`/path/file${ext}`);
        expect(useCodeEditorStore.getState().error).toBe(
          'Binary files cannot be displayed in the editor'
        );
      }
    });

    it('should not reload if same file is already open', async () => {
      mockElectronAPI.readFile.mockResolvedValue({ success: true, data: 'content' });

      await useCodeEditorStore.getState().openFile('/path/to/file.ts');
      mockElectronAPI.readFile.mockClear();

      await useCodeEditorStore.getState().openFile('/path/to/file.ts');
      expect(mockElectronAPI.readFile).not.toHaveBeenCalled();
    });

    it('should handle read errors gracefully', async () => {
      mockElectronAPI.readFile.mockResolvedValue({
        success: false,
        error: 'Permission denied',
      });

      await useCodeEditorStore.getState().openFile('/path/to/protected.ts');

      const state = useCodeEditorStore.getState();
      expect(state.error).toBe('Permission denied');
      expect(state.content).toBe('');
      expect(state.isLoading).toBe(false);
    });
  });

  describe('setContent', () => {
    it('should mark as dirty when content differs from original', () => {
      useCodeEditorStore.setState({ originalContent: 'original', content: 'original' });

      useCodeEditorStore.getState().setContent('modified');

      const state = useCodeEditorStore.getState();
      expect(state.content).toBe('modified');
      expect(state.isDirty).toBe(true);
    });

    it('should mark as clean when content matches original', () => {
      useCodeEditorStore.setState({
        originalContent: 'original',
        content: 'modified',
        isDirty: true,
      });

      useCodeEditorStore.getState().setContent('original');

      const state = useCodeEditorStore.getState();
      expect(state.isDirty).toBe(false);
    });

    it('should clear error when setting content', () => {
      useCodeEditorStore.setState({ error: 'some error', originalContent: '' });
      useCodeEditorStore.getState().setContent('new');
      expect(useCodeEditorStore.getState().error).toBeNull();
    });
  });

  describe('saveFile', () => {
    it('should save file successfully', async () => {
      mockElectronAPI.writeFile.mockResolvedValue({ success: true });
      useCodeEditorStore.setState({
        currentFile: '/path/to/file.ts',
        content: 'new content',
        originalContent: 'old content',
        isDirty: true,
      });

      const result = await useCodeEditorStore.getState().saveFile();

      expect(result).toBe(true);
      const state = useCodeEditorStore.getState();
      expect(state.isDirty).toBe(false);
      expect(state.originalContent).toBe('new content');
      expect(state.isSaving).toBe(false);
    });

    it('should return true without saving when not dirty', async () => {
      useCodeEditorStore.setState({
        currentFile: '/path/to/file.ts',
        isDirty: false,
      });

      const result = await useCodeEditorStore.getState().saveFile();
      expect(result).toBe(true);
      expect(mockElectronAPI.writeFile).not.toHaveBeenCalled();
    });

    it('should return true without saving when no file is open', async () => {
      useCodeEditorStore.setState({ currentFile: null, isDirty: true });

      const result = await useCodeEditorStore.getState().saveFile();
      expect(result).toBe(true);
      expect(mockElectronAPI.writeFile).not.toHaveBeenCalled();
    });

    it('should handle save errors', async () => {
      mockElectronAPI.writeFile.mockResolvedValue({
        success: false,
        error: 'Disk full',
      });
      useCodeEditorStore.setState({
        currentFile: '/path/to/file.ts',
        content: 'content',
        isDirty: true,
      });

      const result = await useCodeEditorStore.getState().saveFile();
      expect(result).toBe(false);
      expect(useCodeEditorStore.getState().error).toBe('Disk full');
    });
  });

  describe('closeFile', () => {
    it('should reset all state', () => {
      useCodeEditorStore.setState({
        currentFile: '/path/file.ts',
        content: 'content',
        originalContent: 'original',
        isDirty: true,
        isLoading: true,
        isSaving: true,
        error: 'some error',
      });

      useCodeEditorStore.getState().closeFile();

      const state = useCodeEditorStore.getState();
      expect(state.currentFile).toBeNull();
      expect(state.content).toBe('');
      expect(state.isDirty).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('discardChanges', () => {
    it('should revert content to original', () => {
      useCodeEditorStore.setState({
        content: 'modified',
        originalContent: 'original',
        isDirty: true,
      });

      useCodeEditorStore.getState().discardChanges();

      const state = useCodeEditorStore.getState();
      expect(state.content).toBe('original');
      expect(state.isDirty).toBe(false);
    });
  });

  describe('selectors', () => {
    it('hasUnsavedChanges should reflect isDirty', () => {
      useCodeEditorStore.setState({ isDirty: false });
      expect(useCodeEditorStore.getState().hasUnsavedChanges()).toBe(false);

      useCodeEditorStore.setState({ isDirty: true });
      expect(useCodeEditorStore.getState().hasUnsavedChanges()).toBe(true);
    });

    it('getFileName should extract file name from path', () => {
      useCodeEditorStore.setState({ currentFile: '/path/to/file.ts' });
      expect(useCodeEditorStore.getState().getFileName()).toBe('file.ts');
    });

    it('getFileName should handle Windows paths', () => {
      useCodeEditorStore.setState({ currentFile: 'C:\\Users\\test\\file.ts' });
      expect(useCodeEditorStore.getState().getFileName()).toBe('file.ts');
    });

    it('getFileName should return null when no file open', () => {
      useCodeEditorStore.setState({ currentFile: null });
      expect(useCodeEditorStore.getState().getFileName()).toBeNull();
    });

    it('getFileExtension should extract extension', () => {
      useCodeEditorStore.setState({ currentFile: '/path/to/file.ts' });
      expect(useCodeEditorStore.getState().getFileExtension()).toBe('.ts');
    });

    it('getFileExtension should return null for no extension', () => {
      useCodeEditorStore.setState({ currentFile: '/path/to/Makefile' });
      expect(useCodeEditorStore.getState().getFileExtension()).toBeNull();
    });

    it('getFileExtension should return null when no file open', () => {
      useCodeEditorStore.setState({ currentFile: null });
      expect(useCodeEditorStore.getState().getFileExtension()).toBeNull();
    });
  });
});
