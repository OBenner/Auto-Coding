/**
 * CustomTemplateSelector - Reusable component for selecting custom agent templates in forms
 *
 * Provides a dropdown for selecting user-created agent templates with inline
 * display of template details (category, description, tools).
 *
 * Used in TaskCreationWizard for template-based task creation.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileCode, ChevronDown, Tag, Wrench } from 'lucide-react';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { useTemplateStore } from '../../stores/template-store';
import type { CustomTemplate } from '../../../shared/types/template';
import { cn } from '../../lib/utils';

interface CustomTemplateSelectorProps {
  /** Currently selected template ID (or empty string for none) */
  selectedTemplateId: string;
  /** Called when template selection changes */
  onTemplateChange: (template: CustomTemplate | null) => void;
  /** Whether the selector is disabled */
  disabled?: boolean;
}

export function CustomTemplateSelector({
  selectedTemplateId,
  onTemplateChange,
  disabled
}: CustomTemplateSelectorProps) {
  const { t } = useTranslation('templates');
  const { templates, isLoading, loadTemplates } = useTemplateStore();

  // Load templates on mount
  useEffect(() => {
    if (templates.length === 0 && !isLoading) {
      loadTemplates();
    }
  }, [templates.length, isLoading, loadTemplates]);

  const handleTemplateSelect = (templateId: string) => {
    if (templateId === '') {
      onTemplateChange(null);
    } else {
      const template = templates.find((t) => t.id === templateId);
      if (template) {
        onTemplateChange(template);
      }
    }
  };

  // Get selected template for display
  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  return (
    <div className="space-y-4">
      {/* Custom Template Selection */}
      <div className="space-y-2">
        <Label htmlFor="custom-template" className="text-sm font-medium text-foreground">
          {t('editor.fields.name')}
        </Label>
        <Select
          value={selectedTemplateId}
          onValueChange={handleTemplateSelect}
          disabled={disabled || isLoading}
        >
          <SelectTrigger id="custom-template" className="h-10">
            <SelectValue
              placeholder={isLoading
                ? t('wizard.loading')
                : t('editor.placeholders.name')
              }
            >
              {selectedTemplate && (
                <div className="flex items-center gap-2">
                  <FileCode className="h-4 w-4" />
                  <span className="truncate">{selectedTemplate.name}</span>
                </div>
              )}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">
              <div className="flex items-center gap-2 text-muted-foreground">
                <span>None</span>
                <span className="text-xs">(Use default agent)</span>
              </div>
            </SelectItem>
            {templates.map((template) => (
              <SelectItem key={template.id} value={template.id}>
                <div className="flex items-center gap-2">
                  <FileCode className="h-4 w-4 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{template.name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {template.description}
                    </div>
                  </div>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Template Details */}
        {selectedTemplate && (
          <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
            {/* Category */}
            <div className="flex items-center gap-2 text-xs">
              <Tag className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Category:</span>
              <span className="font-medium text-foreground capitalize">
                {selectedTemplate.category}
              </span>
            </div>

            {/* Description */}
            <p className="text-xs text-muted-foreground">
              {selectedTemplate.description}
            </p>

            {/* Tools summary */}
            {selectedTemplate.parameters.tools && (
              <div className="flex items-center gap-2 text-xs">
                <Wrench className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Tools configured</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
