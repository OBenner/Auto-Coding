import { useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

export type IssueSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface IssueReport {
  title: string;
  description: string;
  severity: IssueSeverity;
}

interface IssueReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit?: (report: IssueReport) => Promise<void> | void;
  defaultTitle?: string;
  defaultDescription?: string;
}

/**
 * Dialog for reporting detailed issues or suggestions
 * Includes title, description, and severity fields
 */
export function IssueReportDialog({
  open,
  onOpenChange,
  onSubmit,
  defaultTitle = '',
  defaultDescription = ''
}: IssueReportDialogProps) {
  const { t } = useTranslation(['common', 'dialogs']);

  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState(defaultDescription);
  const [severity, setSeverity] = useState<IssueSeverity>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    // Validate form
    if (!title.trim()) {
      setError(t('common:errors.generic', 'Title is required'));
      return;
    }

    if (!description.trim()) {
      setError(t('common:errors.generic', 'Description is required'));
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await onSubmit?.({
        title: title.trim(),
        description: description.trim(),
        severity
      });

      // Reset form on successful submission
      setTitle('');
      setDescription('');
      setSeverity('medium');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common:errors.generic', 'An error occurred'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (isSubmitting) return;

    // Reset form state when closing
    setTitle(defaultTitle);
    setDescription(defaultDescription);
    setSeverity('medium');
    setError(null);
    onOpenChange(false);
  };

  // Severity options with translations
  const severityOptions: Array<{ value: IssueSeverity; label: string; description: string }> = [
    {
      value: 'low',
      label: t('common:prReview.severity.low', 'Suggestion'),
      description: t('common:prReview.severity.lowDesc', 'Consider')
    },
    {
      value: 'medium',
      label: t('common:prReview.severity.medium', 'Recommended'),
      description: t('common:prReview.severity.mediumDesc', 'Improve quality')
    },
    {
      value: 'high',
      label: t('common:prReview.severity.high', 'Required'),
      description: t('common:prReview.severity.highDesc', 'Should fix')
    },
    {
      value: 'critical',
      label: t('common:prReview.severity.critical', 'Blocker'),
      description: t('common:prReview.severity.criticalDesc', 'Must fix')
    }
  ];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            {t('common:feedback.reportIssueTitle', 'Report an Issue')}
          </DialogTitle>
          <DialogDescription>
            {t('common:feedback.reportIssueDescription', 'Provide details about the issue or suggestion to help us improve.')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Title Field */}
          <div className="space-y-2">
            <Label htmlFor="issue-title">
              {t('common:feedback.issueTitle', 'Title')}
              <span className="text-destructive ml-1">*</span>
            </Label>
            <Input
              id="issue-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('common:feedback.issueTitlePlaceholder', 'Brief summary of the issue...')}
              disabled={isSubmitting}
              className="w-full"
            />
          </div>

          {/* Description Field */}
          <div className="space-y-2">
            <Label htmlFor="issue-description">
              {t('common:feedback.issueDescription', 'Description')}
              <span className="text-destructive ml-1">*</span>
            </Label>
            <Textarea
              id="issue-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('common:feedback.issueDescriptionPlaceholder', 'Detailed description of the issue, including steps to reproduce if applicable...')}
              disabled={isSubmitting}
              className="min-h-[150px] resize-none"
            />
          </div>

          {/* Severity Field */}
          <div className="space-y-2">
            <Label htmlFor="issue-severity">
              {t('common:feedback.issueSeverity', 'Severity')}
            </Label>
            <Select
              value={severity}
              onValueChange={(value) => setSeverity(value as IssueSeverity)}
              disabled={isSubmitting}
            >
              <SelectTrigger id="issue-severity" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {severityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{option.label}</span>
                      <span className="text-xs text-muted-foreground">{option.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
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
            disabled={!title.trim() || !description.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('common:feedback.submitting', 'Submitting...')}
              </>
            ) : (
              t('common:feedback.submitReport', 'Submit Report')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
