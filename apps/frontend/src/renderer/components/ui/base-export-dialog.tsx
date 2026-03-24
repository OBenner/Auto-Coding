/**
 * BaseExportDialog - Shared dialog for exporting data as JSON or Markdown.
 *
 * Used by both session-replay and agent-inspector export features.
 * Encapsulates format selection, download logic, and error display.
 */
import { useState, useCallback } from 'react';
import { Loader2, Download, FileText, Code } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './dialog';
import { Button } from './button';
import { Label } from './label';

type ExportFormat = 'json' | 'markdown';

export interface BaseExportDialogLabels {
  title: string;
  description: string;
  formatLabel: string;
  jsonLabel: string;
  markdownLabel: string;
  jsonInfo: string;
  markdownInfo: string;
  cancelLabel: string;
  exportLabel: string;
  exportingLabel: string;
  errorFallback: string;
}

interface BaseExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  labels: BaseExportDialogLabels;
  /** Called with the selected format. Must return the file content string. */
  onExport: (format: ExportFormat) => Promise<string>;
  /** File name prefix (e.g. "agent-session-123" or "session-456") */
  filenamePrefix: string;
}

const FORMAT_OPTIONS: ReadonlyArray<{
  value: ExportFormat;
  iconKey: 'json' | 'markdown';
  icon: typeof Code;
}> = [
  { value: 'json', iconKey: 'json', icon: Code },
  { value: 'markdown', iconKey: 'markdown', icon: FileText },
];

export function BaseExportDialog({
  open,
  onOpenChange,
  labels,
  onExport,
  filenamePrefix,
}: Readonly<BaseExportDialogProps>) {
  const [format, setFormat] = useState<ExportFormat>('json');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    setIsExporting(true);
    setError(null);

    try {
      const content = await onExport(format);

      const blob = new Blob([content], {
        type: format === 'json' ? 'application/json' : 'text/markdown',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      const timestamp = new Date().toISOString().replaceAll(/[:.]/g, '-');
      const extension = format === 'json' ? 'json' : 'md';
      link.download = `${filenamePrefix}-${timestamp}.${extension}`;

      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : labels.errorFallback);
    } finally {
      setIsExporting(false);
    }
  }, [format, onExport, filenamePrefix, onOpenChange, labels.errorFallback]);

  const handleClose = useCallback(() => {
    if (!isExporting) {
      onOpenChange(false);
    }
  }, [isExporting, onOpenChange]);

  const formatLabels = {
    json: labels.jsonLabel,
    markdown: labels.markdownLabel,
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-foreground">{labels.title}</DialogTitle>
          <DialogDescription>{labels.description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Format Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium text-foreground">
              {labels.formatLabel}
            </Label>
            <div className="grid grid-cols-2 gap-3">
              {FORMAT_OPTIONS.map(({ value, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFormat(value)}
                  disabled={isExporting}
                  className={`
                    flex items-center gap-3 p-4 rounded-lg border-2 transition-all
                    ${
                      format === value
                        ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                        : 'border-border hover:border-primary/50 hover:bg-muted/50'
                    }
                    ${isExporting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  <Icon
                    className={`h-5 w-5 ${format === value ? 'text-primary' : 'text-muted-foreground'}`}
                  />
                  <span
                    className={`font-medium ${format === value ? 'text-foreground' : 'text-muted-foreground'}`}
                  >
                    {formatLabels[value]}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Info Box */}
          <div className="rounded-lg bg-muted/50 border border-border p-3 text-sm text-muted-foreground">
            <p className="flex items-start gap-2">
              <Download className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{format === 'json' ? labels.jsonInfo : labels.markdownInfo}</span>
            </p>
          </div>

          {/* Error */}
          {error && (
            <div
              className="flex items-start gap-2 rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive"
              role="alert"
            >
              <span>{error}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isExporting}>
            {labels.cancelLabel}
          </Button>
          <Button onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {labels.exportingLabel}
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                {labels.exportLabel}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
