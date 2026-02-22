import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Save, X, TestTube, Badge as BadgeIcon, Download, Upload } from 'lucide-react';
import { cn } from '../../lib/utils';
import { SettingsSection } from '../settings/SettingsSection';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';

// Agent template categories matching backend
const TEMPLATE_CATEGORIES = [
  'testing',
  'documentation',
  'security',
  'performance',
  'refactoring',
  'migration',
  'other'
] as const;

// Thinking levels matching backend
const THINKING_LEVELS = [
  { value: 'none', label: 'None' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'ultrathink', label: 'Ultra Think' }
] as const;

interface AgentTemplateData {
  name: string;
  description: string;
  category: string;
  version: string;
  custom_prompt: string;
  thinking_level: string;
}

interface TemplateEditorProps {
  initialData?: Partial<AgentTemplateData>;
  onSave?: (data: AgentTemplateData) => Promise<void>;
  onTest?: (data: AgentTemplateData) => Promise<void>;
  onCancel?: () => void;
  onExport?: () => Promise<void>;
  onImport?: (file: File) => Promise<void>;
  updateAvailable?: boolean; // Show update indicator when newer version exists
  latestVersion?: string; // Latest available version (if updateAvailable)
}

/**
 * Template Editor component
 * Form for creating/editing custom agent templates
 * Provides prompt configuration and basic metadata fields
 */
export function TemplateEditor({
  initialData,
  onSave,
  onTest,
  onCancel,
  onExport,
  onImport,
  updateAvailable = false,
  latestVersion
}: TemplateEditorProps) {
  const { t } = useTranslation('templates');

  const [formData, setFormData] = useState<AgentTemplateData>({
    name: initialData?.name || '',
    description: initialData?.description || '',
    category: initialData?.category || '',
    version: initialData?.version || '1.0.0',
    custom_prompt: initialData?.custom_prompt || '',
    thinking_level: initialData?.thinking_level || 'medium'
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const handleChange = (field: keyof AgentTemplateData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field when user types
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name?.trim()) {
      newErrors.name = t('editor.validation.nameRequired');
    } else if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(formData.name)) {
      newErrors.name = 'Name must be lowercase alphanumeric with hyphens only';
    }

    if (!formData.description?.trim()) {
      newErrors.description = t('editor.validation.descriptionRequired');
    }

    if (!formData.category?.trim()) {
      newErrors.category = t('editor.validation.categoryRequired');
    }

    if (!formData.version?.trim()) {
      newErrors.version = t('editor.validation.invalidVersion');
    } else if (!/^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$/.test(formData.version)) {
      newErrors.version = t('editor.validation.invalidVersion');
    }

    if (formData.custom_prompt && formData.custom_prompt.trim().length < 20) {
      newErrors.custom_prompt = t('editor.validation.promptTooShort');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    setIsSaving(true);
    try {
      await onSave?.(formData);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    if (!validate()) return;

    setIsTesting(true);
    try {
      await onTest?.(formData);
    } finally {
      setIsTesting(false);
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    setImportError(null);
    try {
      await onExport?.();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const handleImportClick = () => {
    document.getElementById('template-import-input')?.click();
  };

  const handleImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    setImportError(null);
    try {
      await onImport?.(file);
      // Reset the input so the same file can be selected again if needed
      event.target.value = '';
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <SettingsSection
      title={t('editor.title')}
      description={t('editor.description')}
    >
      <div className="space-y-4">
        {/* Template Name */}
        <div className="space-y-2">
          <Label htmlFor="template-name" className="text-sm font-medium text-foreground">
            {t('editor.fields.name')}
          </Label>
          <Input
            id="template-name"
            placeholder={t('editor.placeholders.name')}
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className={cn(
              errors.name && 'border-destructive focus-visible:ring-destructive'
            )}
          />
          {errors.name && (
            <p className="text-xs text-destructive">{errors.name}</p>
          )}
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label htmlFor="template-description" className="text-sm font-medium text-foreground">
            {t('editor.fields.description')}
          </Label>
          <Input
            id="template-description"
            placeholder={t('editor.placeholders.description')}
            value={formData.description}
            onChange={(e) => handleChange('description', e.target.value)}
            className={cn(
              errors.description && 'border-destructive focus-visible:ring-destructive'
            )}
          />
          {errors.description && (
            <p className="text-xs text-destructive">{errors.description}</p>
          )}
        </div>

        {/* Category and Version - Two columns */}
        <div className="grid grid-cols-2 gap-4">
          {/* Category */}
          <div className="space-y-2">
            <Label htmlFor="template-category" className="text-sm font-medium text-foreground">
              {t('editor.fields.category')}
            </Label>
            <Select
              value={formData.category}
              onValueChange={(value) => handleChange('category', value)}
            >
              <SelectTrigger
                id="template-category"
                className={cn(
                  errors.category && 'border-destructive focus-visible:ring-destructive'
                )}
              >
                <SelectValue placeholder={t('editor.placeholders.category')} />
              </SelectTrigger>
              <SelectContent>
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.category && (
              <p className="text-xs text-destructive">{errors.category}</p>
            )}
          </div>

          {/* Version */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="template-version" className="text-sm font-medium text-foreground">
                {t('editor.fields.version')}
              </Label>
              {updateAvailable && (
                <Badge
                  variant="outline"
                  className="text-xs gap-1 bg-info/10 text-info border-info/30"
                >
                  <BadgeIcon className="h-3 w-3" />
                  Update Available
                </Badge>
              )}
            </div>
            <Input
              id="template-version"
              placeholder={t('editor.placeholders.version')}
              value={formData.version}
              onChange={(e) => handleChange('version', e.target.value)}
              className={cn(
                errors.version && 'border-destructive focus-visible:ring-destructive'
              )}
            />
            <div className="flex items-center justify-between">
              {errors.version ? (
                <p className="text-xs text-destructive">{errors.version}</p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  {t('editor.hints.versionFormat', 'Semantic versioning (e.g., 1.0.0)')}
                </p>
              )}
              {updateAvailable && latestVersion && (
                <p className="text-xs text-muted-foreground">
                  Latest: <span className="font-medium text-foreground">{latestVersion}</span>
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Version Badge Section (when editing existing template) */}
        {initialData?.version && (
          <div className="rounded-lg border border-border bg-muted/50 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                  {t('editor.currentVersion', 'Current Version')}
                </p>
                <p className="text-base font-medium text-foreground">{formData.version}</p>
                {updateAvailable && latestVersion && (
                  <p className="text-xs text-info mt-1">
                    {t('editor.newVersionAvailable', 'New version {{version}} available', {
                      version: latestVersion
                    })}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {updateAvailable ? (
                  <Badge
                    variant="outline"
                    className="gap-1 bg-info/10 text-info border-info/30"
                  >
                    <BadgeIcon className="h-3 w-3" />
                    Update
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="bg-success/10 text-success border-success/30"
                  >
                    Up to Date
                  </Badge>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Thinking Level */}
        <div className="space-y-2">
          <Label htmlFor="template-thinking" className="text-sm font-medium text-foreground">
            {t('editor.fields.thinkingLevel')}
          </Label>
          <Select
            value={formData.thinking_level}
            onValueChange={(value) => handleChange('thinking_level', value)}
          >
            <SelectTrigger id="template-thinking">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {THINKING_LEVELS.map((level) => (
                <SelectItem key={level.value} value={level.value}>
                  {level.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Custom System Prompt */}
        <div className="space-y-2">
          <Label htmlFor="template-prompt" className="text-sm font-medium text-foreground">
            {t('editor.fields.customPrompt')}
          </Label>
          <Textarea
            id="template-prompt"
            placeholder={t('editor.placeholders.customPrompt')}
            value={formData.custom_prompt}
            onChange={(e) => handleChange('custom_prompt', e.target.value)}
            rows={12}
            className={cn(
              'font-mono text-xs',
              errors.custom_prompt && 'border-destructive focus-visible:ring-destructive'
            )}
          />
          {errors.custom_prompt && (
            <p className="text-xs text-destructive">{errors.custom_prompt}</p>
          )}
          <p className="text-xs text-muted-foreground">
            This prompt will override the default agent system prompt. Use clear instructions to define the agent's behavior and capabilities.
          </p>
        </div>

        {/* Import/Export Buttons */}
        {(onExport || onImport) && (
          <div className="flex items-center gap-2 pt-4 border-t border-border">
            {onImport && (
              <>
                <input
                  id="template-import-input"
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={handleImportFile}
                  disabled={isImporting}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleImportClick}
                  disabled={isImporting || isExporting || isSaving || isTesting}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  {isImporting ? t('editor.actions.importing', 'Importing...') : t('editor.actions.import', 'Import Template')}
                </Button>
              </>
            )}
            {onExport && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleExport}
                disabled={isImporting || isExporting || isSaving || isTesting}
              >
                <Download className="h-4 w-4 mr-2" />
                {isExporting ? t('editor.actions.exporting', 'Exporting...') : t('editor.actions.export', 'Export Template')}
              </Button>
            )}
          </div>
        )}

        {/* Import Error */}
        {importError && (
          <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3">
            <p className="text-sm text-destructive">{importError}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-4 border-t border-border">
          <div className="flex items-center gap-2">
            {onTest && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleTest}
                disabled={isTesting || isSaving}
              >
                <TestTube className="h-4 w-4 mr-2" />
                {isTesting ? 'Testing...' : t('editor.actions.test')}
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {onCancel && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onCancel}
                disabled={isSaving || isTesting}
              >
                <X className="h-4 w-4 mr-2" />
                {t('editor.actions.cancel')}
              </Button>
            )}
            {onSave && (
              <Button
                type="button"
                size="sm"
                onClick={handleSave}
                disabled={isSaving || isTesting}
              >
                <Save className="h-4 w-4 mr-2" />
                {isSaving ? 'Saving...' : t('editor.actions.save')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
