/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useTemplateStore } from '../template-store';
import type { CustomTemplate, TemplateCategory } from '../../../shared/types/template';

// Mock toast
vi.mock('../../hooks/use-toast', () => ({
  toast: vi.fn(),
}));

// Mock electronAPI
const mockElectronAPI = {
  listCustomTemplates: vi.fn(),
  saveCustomTemplate: vi.fn(),
  updateCustomTemplate: vi.fn(),
  deleteCustomTemplate: vi.fn(),
  exportCustomTemplate: vi.fn(),
  importCustomTemplate: vi.fn(),
  testCustomTemplate: vi.fn(),
};

Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

function makeTemplate(overrides: Partial<CustomTemplate> = {}): CustomTemplate {
  return {
    id: 'tmpl-1',
    name: 'Test Template',
    description: 'A test template',
    category: 'feature' as TemplateCategory,
    prompt: 'Create a {{feature}}',
    tags: ['test', 'feature'],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  } as CustomTemplate;
}

describe('template-store', () => {
  beforeEach(() => {
    useTemplateStore.setState({
      templates: [],
      isLoading: true,
      error: null,
      editingTemplate: null,
      isSaving: false,
      validationErrors: {},
      isTesting: false,
      testResult: null,
      isImporting: false,
      isExporting: false,
    });
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should have correct defaults', () => {
      const state = useTemplateStore.getState();
      expect(state.templates).toEqual([]);
      expect(state.isLoading).toBe(true);
      expect(state.error).toBeNull();
      expect(state.editingTemplate).toBeNull();
      expect(state.isSaving).toBe(false);
      expect(state.validationErrors).toEqual({});
    });
  });

  describe('basic setters', () => {
    it('should set templates', () => {
      const templates = [makeTemplate({ id: 't1' }), makeTemplate({ id: 't2' })];
      useTemplateStore.getState().setTemplates(templates);
      expect(useTemplateStore.getState().templates).toHaveLength(2);
    });

    it('should set loading', () => {
      useTemplateStore.getState().setLoading(false);
      expect(useTemplateStore.getState().isLoading).toBe(false);
    });

    it('should set error', () => {
      useTemplateStore.getState().setError('Something went wrong');
      expect(useTemplateStore.getState().error).toBe('Something went wrong');
    });

    it('should set editing template', () => {
      const template = makeTemplate();
      useTemplateStore.getState().setEditingTemplate(template);
      expect(useTemplateStore.getState().editingTemplate).toEqual(template);
    });

    it('should clear validation errors', () => {
      useTemplateStore.setState({ validationErrors: { name: 'required' } });
      useTemplateStore.getState().clearValidationErrors();
      expect(useTemplateStore.getState().validationErrors).toEqual({});
    });
  });

  describe('loadTemplates', () => {
    it('should load templates successfully', async () => {
      const templates = [makeTemplate()];
      mockElectronAPI.listCustomTemplates.mockResolvedValue({
        success: true,
        data: templates,
      });

      await useTemplateStore.getState().loadTemplates();

      expect(useTemplateStore.getState().templates).toEqual(templates);
      expect(useTemplateStore.getState().isLoading).toBe(false);
      expect(useTemplateStore.getState().error).toBeNull();
    });

    it('should handle load errors', async () => {
      mockElectronAPI.listCustomTemplates.mockResolvedValue({
        success: false,
        error: 'Network error',
      });

      await useTemplateStore.getState().loadTemplates();

      expect(useTemplateStore.getState().templates).toEqual([]);
      expect(useTemplateStore.getState().error).toBe('Network error');
      expect(useTemplateStore.getState().isLoading).toBe(false);
    });
  });

  describe('saveTemplate', () => {
    it('should save template and add to list', async () => {
      const saved = makeTemplate({ id: 'new-1', name: 'Saved' });
      mockElectronAPI.saveCustomTemplate.mockResolvedValue({
        success: true,
        data: saved,
      });

      const result = await useTemplateStore.getState().saveTemplate({
        name: 'Saved',
        description: 'desc',
        category: 'feature' as TemplateCategory,
        prompt: 'prompt',
      } as any);

      expect(result).toBe(true);
      expect(useTemplateStore.getState().templates).toHaveLength(1);
      expect(useTemplateStore.getState().templates[0].name).toBe('Saved');
    });

    it('should handle save errors', async () => {
      mockElectronAPI.saveCustomTemplate.mockResolvedValue({
        success: false,
        error: 'Save failed',
      });

      const result = await useTemplateStore.getState().saveTemplate({
        name: 'Test',
      } as any);

      expect(result).toBe(false);
      expect(useTemplateStore.getState().error).toBe('Save failed');
    });
  });

  describe('updateTemplate', () => {
    it('should update existing template in list', async () => {
      const original = makeTemplate({ id: 't1', name: 'Original' });
      useTemplateStore.setState({ templates: [original] });

      const updated = { ...original, name: 'Updated' };
      mockElectronAPI.updateCustomTemplate.mockResolvedValue({
        success: true,
        data: updated,
      });

      const result = await useTemplateStore.getState().updateTemplate(updated);

      expect(result).toBe(true);
      expect(useTemplateStore.getState().templates[0].name).toBe('Updated');
    });

    it('should update editingTemplate if it matches', async () => {
      const template = makeTemplate({ id: 't1' });
      useTemplateStore.setState({ templates: [template], editingTemplate: template });

      const updated = { ...template, name: 'Updated' };
      mockElectronAPI.updateCustomTemplate.mockResolvedValue({
        success: true,
        data: updated,
      });

      await useTemplateStore.getState().updateTemplate(updated);

      expect(useTemplateStore.getState().editingTemplate?.name).toBe('Updated');
    });
  });

  describe('deleteTemplate', () => {
    it('should remove template from list', async () => {
      const t1 = makeTemplate({ id: 't1' });
      const t2 = makeTemplate({ id: 't2' });
      useTemplateStore.setState({ templates: [t1, t2] });

      mockElectronAPI.deleteCustomTemplate.mockResolvedValue({ success: true });

      const result = await useTemplateStore.getState().deleteTemplate('t1');

      expect(result).toBe(true);
      expect(useTemplateStore.getState().templates).toHaveLength(1);
      expect(useTemplateStore.getState().templates[0].id).toBe('t2');
    });

    it('should clear editingTemplate if it was deleted', async () => {
      const template = makeTemplate({ id: 't1' });
      useTemplateStore.setState({
        templates: [template],
        editingTemplate: template,
      });

      mockElectronAPI.deleteCustomTemplate.mockResolvedValue({ success: true });

      await useTemplateStore.getState().deleteTemplate('t1');

      expect(useTemplateStore.getState().editingTemplate).toBeNull();
    });
  });

  describe('filterByCategory', () => {
    it('should return templates matching category', () => {
      useTemplateStore.setState({
        templates: [
          makeTemplate({ id: 't1', category: 'feature' as TemplateCategory }),
          makeTemplate({ id: 't2', category: 'bugfix' as TemplateCategory }),
          makeTemplate({ id: 't3', category: 'feature' as TemplateCategory }),
        ],
      });

      const features = useTemplateStore.getState().filterByCategory('feature' as TemplateCategory);
      expect(features).toHaveLength(2);
    });
  });

  describe('searchTemplates', () => {
    it('should search by name', () => {
      useTemplateStore.setState({
        templates: [
          makeTemplate({ id: 't1', name: 'Auth Flow', description: 'OAuth setup' }),
          makeTemplate({ id: 't2', name: 'API Endpoint', description: 'REST API' }),
          makeTemplate({ id: 't3', name: 'Database Migration', description: 'DB migration' }),
        ],
      });

      const results = useTemplateStore.getState().searchTemplates('auth');
      expect(results).toHaveLength(1);
      expect(results[0].id).toBe('t1');
    });

    it('should search by description', () => {
      useTemplateStore.setState({
        templates: [
          makeTemplate({ id: 't1', name: 'A', description: 'Authentication flow' }),
          makeTemplate({ id: 't2', name: 'B', description: 'API endpoint' }),
        ],
      });

      const results = useTemplateStore.getState().searchTemplates('auth');
      expect(results).toHaveLength(1);
    });

    it('should search by tags', () => {
      useTemplateStore.setState({
        templates: [
          makeTemplate({ id: 't1', name: 'A', description: 'a', tags: ['security'] }),
          makeTemplate({ id: 't2', name: 'B', description: 'b', tags: ['api'] }),
        ],
      });

      const results = useTemplateStore.getState().searchTemplates('security');
      expect(results).toHaveLength(1);
    });

    it('should be case insensitive', () => {
      useTemplateStore.setState({
        templates: [makeTemplate({ name: 'React Component' })],
      });

      expect(useTemplateStore.getState().searchTemplates('REACT')).toHaveLength(1);
      expect(useTemplateStore.getState().searchTemplates('react')).toHaveLength(1);
    });
  });
});
