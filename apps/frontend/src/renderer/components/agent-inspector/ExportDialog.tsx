/**
 * ExportDialog - Agent Inspector session export.
 *
 * Thin wrapper around BaseExportDialog with agent-inspector-specific
 * IPC call and i18n namespace.
 */
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BaseExportDialog,
  type BaseExportDialogLabels,
} from '../ui/base-export-dialog';

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectPath: string;
  specId: string;
  sessionId: string;
}

export function ExportDialog({
  open,
  onOpenChange,
  projectPath,
  specId,
  sessionId,
}: Readonly<ExportDialogProps>) {
  const { t } = useTranslation(['agent-inspector']);

  const labels: BaseExportDialogLabels = {
    title: t('agent-inspector:export.title'),
    description: t('agent-inspector:export.description'),
    formatLabel: t('agent-inspector:export.format'),
    jsonLabel: t('agent-inspector:export.formatJson'),
    markdownLabel: t('agent-inspector:export.formatMarkdown'),
    jsonInfo: t('agent-inspector:export.formatJsonInfo'),
    markdownInfo: t('agent-inspector:export.formatMarkdownInfo'),
    cancelLabel: t('agent-inspector:export.cancel'),
    exportLabel: t('agent-inspector:export.export'),
    exportingLabel: t('agent-inspector:export.exporting'),
    errorFallback: t('agent-inspector:errors.exportFailed'),
  };

  const handleExport = useCallback(
    async (format: 'json' | 'markdown'): Promise<string> => {
      const result = await (
        globalThis as unknown as Window
      ).electronAPI.agentInspector.exportSession(
        projectPath,
        specId,
        sessionId,
        format,
      );

      if (!result.success) {
        throw new Error(
          result.error || t('agent-inspector:errors.exportFailed'),
        );
      }

      return typeof result.data === 'string'
        ? result.data
        : JSON.stringify(result.data, null, 2);
    },
    [projectPath, specId, sessionId, t],
  );

  return (
    <BaseExportDialog
      open={open}
      onOpenChange={onOpenChange}
      labels={labels}
      onExport={handleExport}
      filenamePrefix={`agent-session-${sessionId}`}
    />
  );
}
