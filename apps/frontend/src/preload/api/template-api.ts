import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type { CustomTemplate, GeneratedSpec, TemplateInfo, TemplateCategory } from '../../shared/types';

export interface TemplateAPI {
  // Built-in template operations
  listTemplates: (projectId: string, options?: { category?: TemplateCategory | 'all'; tags?: string[] }) => Promise<IPCResult<TemplateInfo[]>>;
  getTemplate: (projectId: string, templateName: string) => Promise<IPCResult<TemplateInfo>>;
  getTemplateCategories: (projectId: string) => Promise<IPCResult<string[]>>;
  searchTemplates: (projectId: string, query: string) => Promise<IPCResult<TemplateInfo[]>>;
  previewTemplate: (projectId: string, templateName: string, parameters: Record<string, unknown>) => Promise<IPCResult<GeneratedSpec>>;
  createSpecFromTemplate: (
    projectId: string,
    templateName: string,
    parameters: Record<string, unknown>,
    specId?: string
  ) => Promise<IPCResult<{ specId: string; specPath: string }>>;
  suggestTemplates: (projectId: string, taskDescription: string) => Promise<IPCResult<string[]>>;

  // Custom template operations (user-created)
  listCustomTemplates: () => Promise<IPCResult<CustomTemplate[]>>;
  saveCustomTemplate: (
    template: Omit<CustomTemplate, 'id' | 'createdAt' | 'updatedAt'>
  ) => Promise<IPCResult<CustomTemplate & { validationErrors?: string[] }>>;
  updateCustomTemplate: (
    template: CustomTemplate
  ) => Promise<IPCResult<CustomTemplate & { validationErrors?: string[] }>>;
  deleteCustomTemplate: (templateId: string) => Promise<IPCResult<void>>;
  exportCustomTemplate: (templateId: string) => Promise<IPCResult<string>>; // Returns JSON string
  importCustomTemplate: (
    jsonData: string
  ) => Promise<IPCResult<CustomTemplate & { validationErrors?: string[] }>>;
  testCustomTemplate: (templateId: string, testInput: string) => Promise<IPCResult<GeneratedSpec>>;
}

export const createTemplateAPI = (): TemplateAPI => ({
  // Built-in template operations
  listTemplates: (projectId: string, options?: { category?: TemplateCategory | 'all'; tags?: string[] }): Promise<IPCResult<TemplateInfo[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_LIST, projectId, options),
  getTemplate: (projectId: string, templateName: string): Promise<IPCResult<TemplateInfo>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_GET, projectId, templateName),
  getTemplateCategories: (projectId: string): Promise<IPCResult<string[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_GET_CATEGORIES, projectId),
  searchTemplates: (projectId: string, query: string): Promise<IPCResult<TemplateInfo[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_SEARCH, projectId, query),
  previewTemplate: (
    projectId: string,
    templateName: string,
    parameters: Record<string, unknown>
  ): Promise<IPCResult<GeneratedSpec>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_PREVIEW, projectId, templateName, parameters),
  createSpecFromTemplate: (
    projectId: string,
    templateName: string,
    parameters: Record<string, unknown>,
    specId?: string
  ): Promise<IPCResult<{ specId: string; specPath: string }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CREATE_SPEC, projectId, templateName, parameters, specId),
  suggestTemplates: (projectId: string, taskDescription: string): Promise<IPCResult<string[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_SUGGEST, projectId, taskDescription),

  // Custom template operations (user-created)
  listCustomTemplates: (): Promise<IPCResult<CustomTemplate[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_LIST),
  saveCustomTemplate: (
    template: Omit<CustomTemplate, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<IPCResult<CustomTemplate & { validationErrors?: string[] }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_SAVE, template),
  updateCustomTemplate: (
    template: CustomTemplate
  ): Promise<IPCResult<CustomTemplate & { validationErrors?: string[] }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_UPDATE, template),
  deleteCustomTemplate: (templateId: string): Promise<IPCResult<void>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_DELETE, templateId),
  exportCustomTemplate: (templateId: string): Promise<IPCResult<string>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_EXPORT, templateId),
  importCustomTemplate: (
    jsonData: string
  ): Promise<IPCResult<CustomTemplate & { validationErrors?: string[] }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_IMPORT, jsonData),
  testCustomTemplate: (templateId: string, testInput: string): Promise<IPCResult<GeneratedSpec>> =>
    ipcRenderer.invoke(IPC_CHANNELS.TEMPLATE_CUSTOM_TEST, templateId, testInput)
});
