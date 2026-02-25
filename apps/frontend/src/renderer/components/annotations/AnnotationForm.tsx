/**
 * AnnotationForm - Form for collecting annotation details
 *
 * This component provides a dialog for users to add description and severity
 * information after selecting an area of the UI for annotation. It displays
 * the captured screenshot and validates form input before submission.
 *
 * Features:
 * - Screenshot preview of the annotated area
 * - Required description field with minimum length validation
 * - Severity level selector (low, medium, high, critical)
 * - Form validation with visual feedback
 * - Loading state during submission
 * - Cancel confirmation
 */

import { useState, useEffect } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Label } from '../ui/label';
import { cn } from '../../lib/utils';
import type { AnnotationFormProps } from './types';
import type { AnnotationSeverity, AnnotationFormData } from '../../../shared/types/annotation';

/**
 * Minimum description length in characters
 */
const MIN_DESCRIPTION_LENGTH = 10;

/**
 * Helper to get severity color class for visual indication
 */
function _getSeverityColorClass(severity: AnnotationSeverity): string {
  switch (severity) {
    case 'low':
      return 'text-blue-600 border-blue-600';
    case 'medium':
      return 'text-yellow-600 border-yellow-600';
    case 'high':
      return 'text-orange-600 border-orange-600';
    case 'critical':
      return 'text-red-600 border-red-600';
    default:
      return 'text-muted-foreground border-border';
  }
}

/**
 * Helper to get severity icon (using a colored dot)
 */
function SeverityDot({ severity }: { severity: AnnotationSeverity }) {
  const colors: Record<AnnotationSeverity, string> = {
    low: 'bg-blue-500',
    medium: 'bg-yellow-500',
    high: 'bg-orange-500',
    critical: 'bg-red-500'
  };

  return (
    <span className={cn('h-3 w-3 rounded-full inline-block mr-2', colors[severity])} />
  );
}

/**
 * AnnotationForm component
 *
 * Renders a dialog form for collecting annotation details including
 * description and severity level. Shows screenshot preview and validates
 * input before submission.
 */
export function AnnotationForm({
  coordinates,
  screenshot,
  onSubmit,
  onCancel
}: AnnotationFormProps) {
  const { t } = useTranslation(['common', 'dialogs']);

  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<AnnotationSeverity>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens (new selection)
  // biome-ignore lint/correctness/useExhaustiveDependencies: Intentional - track prop changes for form reset
  useEffect(() => {
    setDescription('');
    setSeverity('medium');
    setError(null);
  }, [coordinates, screenshot]);

  /**
   * Validate form before submission
   */
  const validateForm = (): boolean => {
    if (!description.trim()) {
      setError(t('dialogs:annotation.error.descriptionRequired', 'Description is required'));
      return false;
    }

    if (description.trim().length < MIN_DESCRIPTION_LENGTH) {
      setError(
        t('dialogs:annotation.error.descriptionTooShort', 'Description must be at least {{min}} characters', {
          min: MIN_DESCRIPTION_LENGTH
        })
      );
      return false;
    }

    setError(null);
    return true;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const formData: AnnotationFormData = {
        description: description.trim(),
        severity
      };

      await onSubmit(formData);

      // Reset form on successful submission
      setDescription('');
      setSeverity('medium');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(
        t('dialogs:annotation.error.submitFailed', 'Failed to submit annotation: {{error}}', {
          error: errorMessage
        })
      );
      // Re-throw so parent can handle (e.g., show toast notification)
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle cancel/close
   */
  const handleClose = () => {
    if (isSubmitting) return;
    onCancel();
  };

  /**
   * Get description character count info
   */
  const descriptionLength = description.trim().length;
  const isDescriptionValid = descriptionLength >= MIN_DESCRIPTION_LENGTH;

  return (
    <Dialog open={true} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {t('dialogs:annotation.title', 'Add Annotation Details')}
          </DialogTitle>
          <DialogDescription>
            {t('dialogs:annotation.description', 'Describe the issue and set its severity level.')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Screenshot Preview */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('dialogs:annotation.screenshotLabel', 'Selected Area')}
            </Label>
            <div className="relative border rounded-lg overflow-hidden bg-muted/30">
              {screenshot ? (
                <img
                  src={screenshot}
                  alt={t('dialogs:annotation.screenshotAlt', 'Screenshot of annotated area')}
                  className="w-full h-auto max-h-[200px] object-contain"
                />
              ) : (
                <div className="flex items-center justify-center h-[120px] text-muted-foreground text-sm">
                  {t('dialogs:annotation.noScreenshot', 'No screenshot available')}
                </div>
              )}
              {/* Selection dimensions badge */}
              <div className="absolute bottom-2 right-2 bg-background/90 backdrop-blur text-xs px-2 py-1 rounded border">
                {coordinates.width} × {coordinates.height}
              </div>
            </div>
          </div>

          {/* Description Field */}
          <div className="space-y-2">
            <Label htmlFor="annotation-description" className="text-sm font-medium text-foreground">
              {t('dialogs:annotation.descriptionLabel', 'Description')}
              <span className="text-destructive ml-1">*</span>
            </Label>
            <Textarea
              id="annotation-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('dialogs:annotation.descriptionPlaceholder', 'Describe the issue or improvement needed...')}
              disabled={isSubmitting}
              className={cn(
                'min-h-[100px] resize-none',
                !isDescriptionValid && descriptionLength > 0 && 'border-destructive focus-visible:ring-destructive'
              )}
              aria-invalid={!isDescriptionValid && descriptionLength > 0}
            />
            <div className="flex items-center justify-between text-xs">
              <span className={cn(
                'text-muted-foreground',
                !isDescriptionValid && descriptionLength > 0 && 'text-destructive'
              )}>
                {descriptionLength} / {MIN_DESCRIPTION_LENGTH} {t('dialogs:annotation.characters', 'characters')}
              </span>
              {descriptionLength > 0 && !isDescriptionValid && (
                <span className="text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {t('dialogs:annotation.tooShort', 'Too short')}
                </span>
              )}
            </div>
          </div>

          {/* Severity Selection */}
          <div className="space-y-2">
            <Label htmlFor="annotation-severity" className="text-sm font-medium text-foreground">
              {t('dialogs:annotation.severityLabel', 'Severity Level')}
            </Label>
            <Select
              value={severity}
              onValueChange={(value) => setSeverity(value as AnnotationSeverity)}
              disabled={isSubmitting}
            >
              <SelectTrigger id="annotation-severity" className="w-full">
                <SelectValue>
                  <div className="flex items-center">
                    <SeverityDot severity={severity} />
                    {t(`dialogs:annotation.severity.${severity}`, severity)}
                  </div>
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">
                  <div className="flex items-center">
                    <SeverityDot severity="low" />
                    {t('dialogs:annotation.severity.low', 'Low - Minor visual or UX issue')}
                  </div>
                </SelectItem>
                <SelectItem value="medium">
                  <div className="flex items-center">
                    <SeverityDot severity="medium" />
                    {t('dialogs:annotation.severity.medium', 'Medium - Noticeable problem affecting some users')}
                  </div>
                </SelectItem>
                <SelectItem value="high">
                  <div className="flex items-center">
                    <SeverityDot severity="high" />
                    {t('dialogs:annotation.severity.high', 'High - Significant issue affecting many users')}
                  </div>
                </SelectItem>
                <SelectItem value="critical">
                  <div className="flex items-center">
                    <SeverityDot severity="critical" />
                    {t('dialogs:annotation.severity.critical', 'Critical - Blocking issue that prevents core feature usage')}
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {t('dialogs:annotation.severityHelp', 'How severe is this issue?')}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            {t('common:buttons.cancel', 'Cancel')}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!isDescriptionValid || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('dialogs:annotation.submitting', 'Submitting...')}
              </>
            ) : (
              t('dialogs:annotation.submit', 'Submit Annotation')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
