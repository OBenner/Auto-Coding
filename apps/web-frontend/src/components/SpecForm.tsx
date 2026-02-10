/**
 * SpecForm Component
 *
 * Form for creating new specifications in the web frontend.
 * Follows patterns from desktop app and web components.
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Select } from './ui/select';
import { cn } from '../lib/utils';
import { apiClient } from '../api/client';

// ============================================
// TYPES
// ============================================

export type ComplexityLevel = 'simple' | 'standard' | 'complex';

export interface SpecFormData {
  taskDescription: string;
  complexity: ComplexityLevel;
  attachments: File[];
}

export interface SpecFormProps {
  onSubmit?: (data: SpecFormData) => Promise<void>;
  onCancel?: () => void;
  className?: string;
}

// ============================================
// COMPONENT
// ============================================

export function SpecForm({ onSubmit, onCancel, className }: SpecFormProps) {
  const { t } = useTranslation(['dialogs', 'common']);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [taskDescription, setTaskDescription] = useState('');
  const [complexity, setComplexity] = useState<ComplexityLevel>('standard');
  const [attachments, setAttachments] = useState<File[]>([]);

  // Validation
  const isValid = taskDescription.trim().length > 0;

  // Handle form submission
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValid || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const formData: SpecFormData = {
        taskDescription: taskDescription.trim(),
        complexity,
        attachments
      };

      // Call custom onSubmit handler if provided, otherwise use default API call
      if (onSubmit) {
        await onSubmit(formData);
      } else {
        // Default: call API to create spec
        // Note: This will need to be adjusted based on actual API endpoint for creating specs
        await apiClient.runAgent({
          spec_id: taskDescription.trim(),
          agent_type: 'planner'
        });
      }

      // Reset form on success
      setTaskDescription('');
      setComplexity('standard');
      setAttachments([]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('dialogs:createSpec.error');
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  }, [taskDescription, complexity, attachments, isValid, isSubmitting, onSubmit, t]);

  // Handle file selection
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setAttachments(files);
  }, []);

  // Handle cancel
  const handleCancel = useCallback(() => {
    setTaskDescription('');
    setComplexity('standard');
    setAttachments([]);
    setError(null);
    onCancel?.();
  }, [onCancel]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('dialogs:createSpec.title')}</CardTitle>
        <CardDescription>{t('dialogs:createSpec.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Task Description */}
          <div className="space-y-2">
            <Label htmlFor="task-description">
              {t('dialogs:createSpec.taskDescription')}
            </Label>
            <Textarea
              id="task-description"
              placeholder={t('dialogs:createSpec.taskDescriptionPlaceholder')}
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              disabled={isSubmitting}
              rows={6}
              className="resize-y"
              required
            />
          </div>

          {/* Complexity Level */}
          <div className="space-y-2">
            <Label htmlFor="complexity">
              {t('dialogs:createSpec.complexity')}
            </Label>
            <Select
              id="complexity"
              value={complexity}
              onChange={(e) => setComplexity(e.target.value as ComplexityLevel)}
              disabled={isSubmitting}
            >
              <option value="simple">
                {t('dialogs:createSpec.complexitySimple')}
              </option>
              <option value="standard">
                {t('dialogs:createSpec.complexityStandard')}
              </option>
              <option value="complex">
                {t('dialogs:createSpec.complexityComplex')}
              </option>
            </Select>
          </div>

          {/* Attachments (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="attachments">
              {t('dialogs:createSpec.attachments')}
            </Label>
            <Input
              id="attachments"
              type="file"
              multiple
              onChange={handleFileChange}
              disabled={isSubmitting}
              className="cursor-pointer"
            />
            <p className="text-xs text-muted-foreground">
              {t('dialogs:createSpec.attachmentsDescription')}
            </p>
            {attachments.length > 0 && (
              <div className="text-xs text-muted-foreground">
                {t('common:labels.optional', { defaultValue: 'Optional' })}: {attachments.length} {attachments.length === 1 ? 'file' : 'files'} selected
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              {t('dialogs:createSpec.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={!isValid || isSubmitting}
            >
              {isSubmitting ? t('dialogs:createSpec.creating') : t('dialogs:createSpec.create')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
