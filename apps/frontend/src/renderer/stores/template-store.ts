import { create } from 'zustand';
import type {
  Template,
  CustomTemplate,
  TemplateCategory,
  CreateSpecFromTemplateRequest,
  CreateSpecFromTemplateResult,
  GeneratedSpec
} from '../../shared/types/template';
import { toast } from '../hooks/use-toast';

interface TemplateState {
  // State
  templates: CustomTemplate[];
  isLoading: boolean;
  error: string | null;

  // Editor state
  editingTemplate: CustomTemplate | null;
  isSaving: boolean;
  validationErrors: Record<string, string>;

  // Test state
  isTesting: boolean;
  testResult: GeneratedSpec | null;

  // Import/Export state
  isImporting: boolean;
  isExporting: boolean;

  // Actions
  setTemplates: (templates: CustomTemplate[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Template CRUD
  loadTemplates: () => Promise<void>;
  saveTemplate: (template: Omit<CustomTemplate, 'id' | 'createdAt' | 'updatedAt'>) => Promise<boolean>;
  updateTemplate: (template: CustomTemplate) => Promise<boolean>;
  deleteTemplate: (templateId: string) => Promise<boolean>;
  exportTemplate: (templateId: string) => Promise<string | null>;
  importTemplate: (jsonData: string) => Promise<boolean>;

  // Editor actions
  setEditingTemplate: (template: CustomTemplate | null) => void;
  clearValidationErrors: () => void;

  // Test actions
  testTemplate: (template: CustomTemplate, testInput: string) => Promise<GeneratedSpec | null>;

  // Filter/search actions
  filterByCategory: (category: TemplateCategory) => CustomTemplate[];
  searchTemplates: (query: string) => CustomTemplate[];
}

export const useTemplateStore = create<TemplateState>((set, get) => ({
  // Initial state
  templates: [],
  isLoading: true,
  error: null,

  // Editor state
  editingTemplate: null,
  isSaving: false,
  validationErrors: {},

  // Test state
  isTesting: false,
  testResult: null,

  // Import/Export state
  isImporting: false,
  isExporting: false,

  // Basic setters
  setTemplates: (templates) => set({ templates }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  // Template CRUD
  loadTemplates: async (): Promise<void> => {
    set({ isLoading: true, error: null });
    try {
      const result = await window.electronAPI.listCustomTemplates();
      if (result.success && result.data) {
        set({ templates: result.data, isLoading: false });
      } else {
        set({
          error: result.error || 'Failed to load templates',
          isLoading: false
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load templates',
        isLoading: false
      });
    }
  },

  saveTemplate: async (template: Omit<CustomTemplate, 'id' | 'createdAt' | 'updatedAt'>): Promise<boolean> => {
    set({ isSaving: true, validationErrors: {}, error: null });
    try {
      const result = await window.electronAPI.saveCustomTemplate(template);
      if (result.success && result.data) {
        const savedTemplate = result.data;
        set((state) => ({
          templates: [...state.templates, savedTemplate],
          isSaving: false
        }));
        toast({
          title: 'Template saved',
          description: `"${savedTemplate.name}" has been created successfully.`
        });
        return true;
      }

      // Handle validation errors
      if (result.data?.validationErrors) {
        const errors: Record<string, string> = {};
        result.data.validationErrors.forEach((err: string) => {
          errors[err] = err;
        });
        set({
          validationErrors: errors,
          error: 'Please fix the validation errors',
          isSaving: false
        });
        return false;
      }

      set({
        error: result.error || 'Failed to save template',
        isSaving: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to save template',
        description: result.error || 'Unknown error occurred'
      });
      return false;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to save template',
        isSaving: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to save template',
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      });
      return false;
    }
  },

  updateTemplate: async (template: CustomTemplate): Promise<boolean> => {
    set({ isSaving: true, validationErrors: {}, error: null });
    try {
      const result = await window.electronAPI.updateCustomTemplate(template);
      if (result.success && result.data) {
        const updatedTemplate = result.data;
        set((state) => ({
          templates: state.templates.map((t) =>
            t.id === updatedTemplate.id ? updatedTemplate : t
          ),
          editingTemplate: state.editingTemplate?.id === updatedTemplate.id ? updatedTemplate : state.editingTemplate,
          isSaving: false
        }));
        toast({
          title: 'Template updated',
          description: `"${updatedTemplate.name}" has been updated successfully.`
        });
        return true;
      }

      // Handle validation errors
      if (result.data?.validationErrors) {
        const errors: Record<string, string> = {};
        result.data.validationErrors.forEach((err: string) => {
          errors[err] = err;
        });
        set({
          validationErrors: errors,
          error: 'Please fix the validation errors',
          isSaving: false
        });
        return false;
      }

      set({
        error: result.error || 'Failed to update template',
        isSaving: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to update template',
        description: result.error || 'Unknown error occurred'
      });
      return false;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update template',
        isSaving: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to update template',
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      });
      return false;
    }
  },

  deleteTemplate: async (templateId: string): Promise<boolean> => {
    set({ isLoading: true, error: null });
    try {
      const result = await window.electronAPI.deleteCustomTemplate(templateId);
      if (result.success) {
        set((state) => ({
          templates: state.templates.filter((t) => t.id !== templateId),
          editingTemplate: state.editingTemplate?.id === templateId ? null : state.editingTemplate,
          isLoading: false
        }));
        toast({
          title: 'Template deleted',
          description: 'The template has been removed.'
        });
        return true;
      }
      set({
        error: result.error || 'Failed to delete template',
        isLoading: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to delete template',
        description: result.error || 'Unknown error occurred'
      });
      return false;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete template',
        isLoading: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to delete template',
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      });
      return false;
    }
  },

  exportTemplate: async (templateId: string): Promise<string | null> => {
    set({ isExporting: true, error: null });
    try {
      const result = await window.electronAPI.exportCustomTemplate(templateId);
      if (result.success && result.data) {
        set({ isExporting: false });
        toast({
          title: 'Template exported',
          description: 'Template has been exported to JSON.'
        });
        return result.data;
      }
      set({
        error: result.error || 'Failed to export template',
        isExporting: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to export template',
        description: result.error || 'Unknown error occurred'
      });
      return null;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to export template',
        isExporting: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to export template',
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      });
      return null;
    }
  },

  importTemplate: async (jsonData: string): Promise<boolean> => {
    set({ isImporting: true, validationErrors: {}, error: null });
    try {
      const result = await window.electronAPI.importCustomTemplate(jsonData);
      if (result.success && result.data) {
        const importedTemplate = result.data;
        set((state) => ({
          templates: [...state.templates, importedTemplate],
          isImporting: false
        }));
        toast({
          title: 'Template imported',
          description: `"${importedTemplate.name}" has been imported successfully.`
        });
        return true;
      }

      // Handle validation errors
      if (result.data?.validationErrors) {
        const errors: Record<string, string> = {};
        result.data.validationErrors.forEach((err: string) => {
          errors[err] = err;
        });
        set({
          validationErrors: errors,
          error: 'Please fix the validation errors',
          isImporting: false
        });
        return false;
      }

      set({
        error: result.error || 'Failed to import template',
        isImporting: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to import template',
        description: result.error || 'Unknown error occurred'
      });
      return false;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to import template',
        isImporting: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to import template',
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      });
      return false;
    }
  },

  // Editor actions
  setEditingTemplate: (template) => set({ editingTemplate: template }),

  clearValidationErrors: () => set({ validationErrors: {} }),

  // Test actions
  testTemplate: async (template: CustomTemplate, testInput: string): Promise<GeneratedSpec | null> => {
    set({ isTesting: true, testResult: null, error: null });
    try {
      const result = await window.electronAPI.testCustomTemplate(template.id, testInput);
      if (result.success && result.data) {
        set({ testResult: result.data, isTesting: false });
        toast({
          title: 'Test completed',
          description: 'Template test generated successfully.'
        });
        return result.data;
      }
      set({
        error: result.error || 'Failed to test template',
        isTesting: false
      });
      toast({
        variant: 'destructive',
        title: 'Test failed',
        description: result.error || 'Template test failed'
      });
      return null;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to test template',
        isTesting: false
      });
      toast({
        variant: 'destructive',
        title: 'Test failed',
        description: error instanceof Error ? error.message : 'Template test failed'
      });
      return null;
    }
  },

  // Filter/search actions (synchronous)
  filterByCategory: (category: TemplateCategory): CustomTemplate[] => {
    const state = get();
    return state.templates.filter((t) => t.category === category);
  },

  searchTemplates: (query: string): CustomTemplate[] => {
    const state = get();
    const lowerQuery = query.toLowerCase();
    return state.templates.filter(
      (t) =>
        t.name.toLowerCase().includes(lowerQuery) ||
        t.description.toLowerCase().includes(lowerQuery) ||
        t.tags?.some((tag) => tag.toLowerCase().includes(lowerQuery))
    );
  }
}));

/**
 * Load templates from main process
 */
export async function loadTemplates(): Promise<void> {
  const store = useTemplateStore.getState();
  await store.loadTemplates();
}
