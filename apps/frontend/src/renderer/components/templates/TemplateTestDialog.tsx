/**
 * TemplateTestDialog - Dialog for testing custom agent templates
 *
 * Allows users to test templates with a dry-run before publishing.
 * Uses the same dialog pattern as AddFeatureDialog for consistency.
 *
 * Features:
 * - Test input for simulating a task
 * - Loading state during test execution
 * - Displays generated spec as test result
 * - Error handling for test failures
 *
 * @example
 * ```tsx
 * <TemplateTestDialog
 *   template={customTemplate}
 *   open={isTestDialogOpen}
 *   onOpenChange={setIsTestDialogOpen}
 *   onTestComplete={(result) => console.log('Test result:', result)}
 * />
 * ```
 */
import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, X, CheckCircle2, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import type { CustomTemplate, GeneratedSpec } from '../../../shared/types/template';

/**
 * Props for the TemplateTestDialog component
 */
interface TemplateTestDialogProps {
  /** The template to test */
  template: CustomTemplate;
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when the dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Optional callback when test completes successfully, receives the generated spec */
  onTestComplete?: (result: GeneratedSpec) => void;
}

export function TemplateTestDialog({
  template,
  open,
  onOpenChange,
  onTestComplete
}: TemplateTestDialogProps) {
  const { t } = useTranslation(['templates', 'common']);

  const mountedRef = useRef(true);
  useEffect(() => { return () => { mountedRef.current = false; }; }, []);

  // Form state
  const [testInput, setTestInput] = useState('');

  // UI state
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<GeneratedSpec | null>(null);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      setTestInput('');
      setError(null);
      setTestResult(null);
    }
  }, [open]);

  const handleRunTest = async () => {
    // Guard API availability
    if (!window?.electronAPI?.testCustomTemplate) {
      setError(t('templates:testDialog.apiNotAvailable'));
      return;
    }

    // Validate test input
    if (!testInput.trim()) {
      setError(t('templates:testDialog.inputRequired'));
      return;
    }

    setIsRunning(true);
    setError(null);
    setTestResult(null);

    try {
      // Call the test API via template store
      const result = await window.electronAPI.testCustomTemplate(template.id, testInput.trim());

      if (!mountedRef.current) return;

      if (result.success && result.data) {
        setTestResult(result.data);
        onTestComplete?.(result.data);
      } else {
        setError(result.error || t('templates:testDialog.testFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('templates:testDialog.testFailed'));
    } finally {
      if (mountedRef.current) {
        setIsRunning(false);
      }
    }
  };

  const handleClose = () => {
    if (!isRunning) {
      onOpenChange(false);
    }
  };

  // Form validation
  const isValid = testInput.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-foreground">
            {t('templates:testDialog.title')}
          </DialogTitle>
          <DialogDescription>
            {t('templates:testDialog.description', { name: template.name })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Template Info */}
          <div className="rounded-lg bg-muted/50 border border-border p-3">
            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">{t('templates:testDialog.templateName')}</span>
                <span className="text-muted-foreground">{template.name}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">{t('templates:testDialog.category')}</span>
                <span className="text-muted-foreground">{template.category}</span>
              </div>
              {template.description && (
                <div className="pt-2">
                  <span className="text-muted-foreground">{template.description}</span>
                </div>
              )}
            </div>
          </div>

          {/* Test Input */}
          <div className="space-y-2">
            <Label htmlFor="test-input" className="text-sm font-medium text-foreground">
              {t('templates:testDialog.testInput')} <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="test-input"
              placeholder={t('templates:testDialog.inputPlaceholder')}
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              rows={4}
              disabled={isRunning}
              aria-required="true"
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              {t('templates:testDialog.inputHint')}
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive" role="alert">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Test Result */}
          {testResult && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-lg bg-green-500/10 border border-green-500/30 p-3 text-sm text-green-600 dark:text-green-400">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span className="font-medium">{t('templates:testDialog.testSuccess')}</span>
              </div>

              <div className="rounded-lg bg-muted/50 border border-border p-4">
                <h4 className="text-sm font-semibold text-foreground mb-3">{t('templates:preview.sections.acceptanceCriteria')}</h4>
                <ul className="space-y-1 text-sm">
                  {testResult.acceptance_criteria?.map((criterion, index) => (
                    <li key={`${index}-${criterion}`} className="text-muted-foreground flex items-start gap-2">
                      <span className="text-primary mt-0.5">•</span>
                      <span>{criterion}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {testResult.technical_details && (
                <div className="rounded-lg bg-muted/50 border border-border p-4">
                  <h4 className="text-sm font-semibold text-foreground mb-2">{t('templates:preview.sections.technicalDetails')}</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{testResult.technical_details}</p>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isRunning}>
            {testResult ? t('common:close') : t('common:cancel')}
          </Button>
          {!testResult && (
            <Button
              onClick={handleRunTest}
              disabled={isRunning || !isValid}
            >
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('templates:testDialog.running')}
                </>
              ) : (
                t('templates:testDialog.runTest')
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
