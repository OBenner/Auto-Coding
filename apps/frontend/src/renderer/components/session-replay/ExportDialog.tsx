/**
 * ExportDialog - Dialog for exporting session replay data
 *
 * Allows users to export sessions in JSON or Markdown format.
 * Supports exporting individual sessions or all sessions at once.
 *
 * Features:
 * - Format selection (JSON or Markdown)
 * - Export single session or all sessions
 * - Automatic file download after export
 * - Error handling with user feedback
 *
 * @example
 * ```tsx
 * <ExportDialog
 *   open={isExportOpen}
 *   onOpenChange={setIsExportOpen}
 *   projectPath="/path/to/project"
 *   specId="spec-123"
 *   sessionId="session-456"
 * />
 * ```
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Download, FileText, Code } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';

/**
 * Export format options
 */
type ExportFormat = 'json' | 'markdown';

/**
 * Props for the ExportDialog component
 */
interface ExportDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when the dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Path to the project directory */
  projectPath: string;
  /** Spec ID containing the sessions */
  specId: string;
  /** Optional session ID to export (if not provided, exports all sessions) */
  sessionId?: string;
}

/**
 * Format options for export
 */
const FORMAT_OPTIONS = [
  { value: 'json' as const, label: 'JSON', icon: Code, description: 'export.formatJsonDesc' },
  { value: 'markdown' as const, label: 'Markdown', icon: FileText, description: 'export.formatMarkdownDesc' }
] as const;

export function ExportDialog({
  open,
  onOpenChange,
  projectPath,
  specId,
  sessionId
}: Readonly<ExportDialogProps>) {
  const { t } = useTranslation(['session-replay', 'dialogs']);

  // Form state
  const [format, setFormat] = useState<ExportFormat>('json');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);

    try {
      // Call appropriate export function based on whether sessionId is provided
      const result = sessionId
        ? await (globalThis as unknown as Window).electronAPI.sessionReplay.exportSession(projectPath, specId, sessionId, format)
        : await (globalThis as unknown as Window).electronAPI.sessionReplay.exportAll(projectPath, specId, format);

      if (!result.success) {
        throw new Error(result.error || t('session-replay:errors.exportFailed'));
      }

      // Create a blob and trigger download
      const content = typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2);
      const blob = new Blob([content], {
        type: format === 'json' ? 'application/json' : 'text/markdown'
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Generate filename
      const timestamp = new Date().toISOString().replaceAll(/[:.]/g, '-');
      const extension = format === 'json' ? 'json' : 'md';
      const filename = sessionId
        ? `session-${sessionId}-${timestamp}.${extension}`
        : `all-sessions-${timestamp}.${extension}`;

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      // Close dialog on success
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('session-replay:errors.exportFailed'));
    } finally {
      setIsExporting(false);
    }
  };

  const handleClose = () => {
    if (!isExporting) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-foreground">
            {t('session-replay:export.title')}
          </DialogTitle>
          <DialogDescription>
            {sessionId
              ? t('session-replay:export.description')
              : t('session-replay:export.descriptionAll')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Format Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium text-foreground">
              {t('session-replay:export.format')}
            </Label>
            <div className="grid grid-cols-2 gap-3">
              {FORMAT_OPTIONS.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFormat(value)}
                  disabled={isExporting}
                  className={`
                    flex items-center gap-3 p-4 rounded-lg border-2 transition-all
                    ${format === value
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                      : 'border-border hover:border-primary/50 hover:bg-muted/50'
                    }
                    ${isExporting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  <Icon className={`h-5 w-5 ${format === value ? 'text-primary' : 'text-muted-foreground'}`} />
                  <span className={`font-medium ${format === value ? 'text-foreground' : 'text-muted-foreground'}`}>
                    {label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Info Box */}
          <div className="rounded-lg bg-muted/50 border border-border p-3 text-sm text-muted-foreground">
            <p className="flex items-start gap-2">
              <Download className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                {format === 'json'
                  ? t('session-replay:export.formatJsonInfo')
                  : t('session-replay:export.formatMarkdownInfo')}
              </span>
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive" role="alert">
              <span>{error}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isExporting}>
            {t('session-replay:export.cancel')}
          </Button>
          <Button
            onClick={handleExport}
            disabled={isExporting}
          >
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('session-replay:export.exporting')}
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                {t('session-replay:export.export')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
