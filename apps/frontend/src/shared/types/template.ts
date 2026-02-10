/**
 * Template-related types for spec template library
 */

// Template parameter types (matching Python types)
export type TemplateParamType = 'str' | 'int' | 'float' | 'bool' | 'list' | 'dict';

// Template parameter definition
export interface TemplateParameter {
  type: TemplateParamType;
  required: boolean;
  description: string;
  default?: string | number | boolean | string[] | Record<string, unknown>;
  options?: string[];  // For enum-like parameters
  placeholder?: string;  // UI hint for input
  validation?: {
    min?: number;  // For numeric types
    max?: number;
    pattern?: string;  // Regex for string validation
  };
}

// Template metadata (from backend Template class)
export interface Template {
  name: string;  // Unique template identifier
  description: string;  // Human-readable description
  category: TemplateCategory;
  parameters: Record<string, TemplateParameter>;
  tags?: string[];  // Optional tags for search/filtering
  examples?: TemplateExample[];  // Example parameter sets
}

// Template categories (matching backend categories)
export type TemplateCategory =
  | 'api'  // REST APIs, GraphQL, etc.
  | 'authentication'  // Auth flows, OAuth, JWT
  | 'database'  // Migrations, models, queries
  | 'ui'  // React components, UI patterns
  | 'file'  // File upload, download, processing
  | 'search'  // Search functionality, filters
  | 'pagination'  // Pagination patterns
  | 'caching'  // Redis, in-memory caching
  | 'notification'  // Email, push, in-app notifications
  | 'data_processing'  // Import/export, transformation
  | 'user_management'  // User profiles, roles, permissions
  | 'settings'  // App settings, configuration
  | 'dashboard'  // Dashboard widgets, analytics
  | 'admin'  // Admin panels, management UIs
  | 'logging'  // Logging, monitoring, error tracking
  | 'testing'  // Unit tests, integration tests
  | 'documentation'  // API docs, user guides
  | 'cicd'  // CI/CD pipelines, deployment
  | 'security'  // Security audits, hardening
  | 'performance'  // Optimization, profiling
  | 'other';

// Example parameter set for a template
export interface TemplateExample {
  name: string;  // Example name (e.g., "Basic User CRUD")
  description: string;  // What this example demonstrates
  parameters: Record<string, unknown>;  // Parameter values
}

// Template info returned by list_templates (lighter than full Template)
export interface TemplateInfo {
  name: string;
  description: string;
  category: TemplateCategory;
  parameters: Record<string, TemplateParameter>;
  tags?: string[];
}

// Generated spec content (from template.generate())
export interface GeneratedSpec {
  title: string;
  description: string;
  rationale: string;
  user_stories: string[];
  acceptance_criteria: string[];
  technical_details: string;
  test_coverage?: string[];  // Test requirements
  dependencies?: string[];  // Required packages/services
}

// Template search/filter state
export interface TemplateFilterState {
  category: TemplateCategory | 'all';
  searchQuery: string;
  tags: string[];  // Selected tags
}

// Template wizard state (multi-step form)
export interface TemplateWizardState {
  templateName: string;  // Selected template
  step: number;  // Current wizard step (0-based)
  parameters: Record<string, unknown>;  // Collected parameter values
  validationErrors: Record<string, string>;  // Parameter validation errors
  isPreviewing: boolean;  // Whether preview modal is open
  generatedSpec?: GeneratedSpec;  // Previewed spec content
}

// Template preview result
export interface TemplatePreviewResult {
  success: boolean;
  spec?: GeneratedSpec;
  validationErrors?: string[];  // Parameter validation errors
  error?: string;  // Other errors (template not found, etc.)
}

// Template suggestion (from project analysis)
export interface TemplateSuggestion {
  template: TemplateInfo;
  reason: string;  // Why this template is suggested
  confidence: number;  // 0-1 score
  matchedFiles?: string[];  // Files that triggered the suggestion
}

// Spec creation from template request
export interface CreateSpecFromTemplateRequest {
  templateName: string;
  parameters: Record<string, unknown>;
  specId?: string;  // Optional spec ID (auto-generated if not provided)
  projectPath: string;  // Project directory path
}

// Spec creation result
export interface CreateSpecFromTemplateResult {
  success: boolean;
  specId?: string;
  specPath?: string;
  validationErrors?: string[];
  error?: string;
}

// Template library statistics
export interface TemplateLibraryStats {
  totalTemplates: number;
  categories: Record<TemplateCategory, number>;  // Count per category
  popularTemplates?: string[];  // Most used template names
  recentlyUsed?: string[];  // Recently used template names
}

// Custom template (user-created)
export interface CustomTemplate extends Template {
  id: string;  // Unique ID for custom template
  createdAt: Date;
  updatedAt: Date;
  author?: string;  // Creator name
  isPublic: boolean;  // Whether shared with community
}

// Template sharing metadata
export interface SharedTemplateMetadata {
  id: string;
  templateName: string;
  author: string;
  version: string;
  downloads: number;
  rating: number;  // 0-5
  reviews: number;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
}
