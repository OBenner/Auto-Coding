import { create } from 'zustand';

interface CodeEditorState {
  currentFile: string | null;
  content: string;
  originalContent: string;
  isDirty: boolean;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;

  // Actions
  openFile: (path: string) => Promise<void>;
  saveFile: () => Promise<boolean>;
  setContent: (content: string) => void;
  closeFile: () => void;
  discardChanges: () => void;
  setError: (error: string | null) => void;

  // Selectors
  hasUnsavedChanges: () => boolean;
  getFileName: () => string | null;
  getFileExtension: () => string | null;
}

// Binary file extensions to reject
const BINARY_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.zip', '.tar', '.gz', '.rar', '.7z',
  '.exe', '.dll', '.so', '.dylib',
  '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
  '.woff', '.woff2', '.ttf', '.eot', '.otf',
  '.pyc', '.class', '.o', '.obj',
]);

function isBinaryFile(filePath: string): boolean {
  const ext = filePath.toLowerCase().substring(filePath.lastIndexOf('.'));
  return BINARY_EXTENSIONS.has(ext);
}

function getFileName(filePath: string | null): string | null {
  if (!filePath) return null;
  const parts = filePath.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || null;
}

function getFileExtension(filePath: string | null): string | null {
  if (!filePath) return null;
  const fileName = getFileName(filePath);
  if (!fileName) return null;
  const lastDot = fileName.lastIndexOf('.');
  if (lastDot === -1 || lastDot === 0) return null;
  return fileName.substring(lastDot).toLowerCase();
}

export const useCodeEditorStore = create<CodeEditorState>((set, get) => ({
  currentFile: null,
  content: '',
  originalContent: '',
  isDirty: false,
  isLoading: false,
  isSaving: false,
  error: null,

  openFile: async (path: string): Promise<void> => {
    const state = get();

    // If same file is already open, do nothing
    if (state.currentFile === path) {
      return;
    }

    // Check for binary files before attempting to load
    if (isBinaryFile(path)) {
      set({
        currentFile: path,
        content: '',
        originalContent: '',
        isDirty: false,
        isLoading: false,
        error: 'Binary files cannot be displayed in the editor',
      });
      return;
    }

    // Set loading state
    set({
      isLoading: true,
      error: null,
    });

    try {
      const result = await window.electronAPI.readFile(path);

      if (!result.success || result.data === undefined) {
        throw new Error(result.error || 'Failed to read file');
      }

      set({
        currentFile: path,
        content: result.data,
        originalContent: result.data,
        isDirty: false,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      set({
        currentFile: path,
        content: '',
        originalContent: '',
        isDirty: false,
        isLoading: false,
        error: errorMessage,
      });
    }
  },

  saveFile: async (): Promise<boolean> => {
    const state = get();

    if (!state.currentFile || !state.isDirty) {
      return true;
    }

    set({
      isSaving: true,
      error: null,
    });

    try {
      const result = await window.electronAPI.writeFile(state.currentFile, state.content);

      if (!result.success) {
        throw new Error(result.error || 'Failed to save file');
      }

      set({
        originalContent: state.content,
        isDirty: false,
        isSaving: false,
        error: null,
      });

      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save file';
      set({
        isSaving: false,
        error: errorMessage,
      });
      return false;
    }
  },

  setContent: (content: string) => {
    const state = get();
    const isDirty = content !== state.originalContent;
    set({
      content,
      isDirty,
      error: null,
    });
  },

  closeFile: () => {
    set({
      currentFile: null,
      content: '',
      originalContent: '',
      isDirty: false,
      isLoading: false,
      isSaving: false,
      error: null,
    });
  },

  discardChanges: () => {
    const state = get();
    set({
      content: state.originalContent,
      isDirty: false,
      error: null,
    });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  hasUnsavedChanges: () => {
    return get().isDirty;
  },

  getFileName: () => {
    return getFileName(get().currentFile);
  },

  getFileExtension: () => {
    return getFileExtension(get().currentFile);
  },
}));
