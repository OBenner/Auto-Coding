/**
 * ExportDialog - Session Replay session export.
 *
 * Thin wrapper around BaseExportDialog with session-replay-specific
 * IPC call and i18n namespace. Supports exporting a single session
 * or all sessions.
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
  sessionId?: string;
}

export function ExportDialog({
  open,
  onOpenChange,
  projectPath,
  specId,
  sessionId,
}: Readonly<ExportDialogProps>) {
  const { t } = useTranslation(['session-replay']);

  const labels: BaseExportDialogLabels = {
    title: t('session-replay:export.title'),
    description: sessionId
      ? t('session-replay:export.description')
      : t('session-replay:export.descriptionAll'),
    formatLabel: t('session-replay:export.format'),
    jsonLabel: 'JSON',
    markdownLabel: 'Markdown',
    jsonInfo: t('session-replay:export.formatJsonInfo'),
    markdownInfo: t('session-replay:export.formatMarkdownInfo'),
    cancelLabel: t('session-replay:export.cancel'),
    exportLabel: t('session-replay:export.export'),
    exportingLabel: t('session-replay:export.exporting'),
    errorFallback: t('session-replay:errors.exportFailed'),
  };

  const handleExport = useCallback(
    async (format: 'json' | 'markdown'): Promise<string> => {
      const result = sessionId
        ? await (
            globalThis as unknown as Window
          ).electronAPI.sessionReplay.exportSession(
            projectPath,
            specId,
            sessionId,
            format,
          )
        : await (
            globalThis as unknown as Window
          ).electronAPI.sessionReplay.exportAll(projectPath, specId, format);

      if (!result.success) {
        throw new Error(
          result.error || t('session-replay:errors.exportFailed'),
        );
      }

      return typeof result.data === 'string'
        ? result.data
        : JSON.stringify(result.data, null, 2);
    },
    [projectPath, specId, sessionId, t],
  );

  const filenamePrefix = sessionId
    ? `session-${sessionId}`
    : 'all-sessions';

  return (
    <BaseExportDialog
      open={open}
      onOpenChange={onOpenChange}
      labels={labels}
      onExport={handleExport}
      filenamePrefix={filenamePrefix}
    />
  );
}
