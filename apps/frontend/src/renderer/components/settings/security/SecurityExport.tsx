/**
 * SecurityExport - Security configuration export component
 *
 * Allows users to export their security configuration to a JSON file
 * for compliance, backup, or sharing purposes.
 *
 * Features:
 * - One-click export of current security profile
 * - Optional inclusion of recent audit logs
 * - Configurable audit log limit
 * - Export reason tracking (compliance, backup, manual)
 * - Download as JSON file with timestamp
 * - Success/error feedback via toast notifications
 * - Loading state during export
 */
import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { useSettingsStore } from '../../stores/settings-store';
import { useSecurityStore } from '../../stores/security-store';
import { useToast } from '../../hooks/use-toast';
import type { SecurityExport } from '@shared/types/security';

interface SecurityExportProps {
  /** Optional CSS classes */
  className?: string;
}

/**
 * Audit log limit options for export
 */
const AUDIT_LOG_LIMITS = [
  { value: 0, label: 'None' },
  { value: 50, label: '50' },
  { value: 100, label: '100' },
  { value: 500, label: '500' },
  { value: 1000, label: '1000' },
];

/**
 * SecurityExport Component
 *
 * @example
 * ```tsx
 * <SecurityExport />
 * ```
 */
export function SecurityExport({ className }: SecurityExportProps) {
  const { t } = useTranslation(['security', 'common']);
  const { project } = useSettingsStore();
  const {
    exportConfig,
    isExporting,
    exportError
  } = useSecurityStore();
  const { toast } = useToast();

  // Export options
  const [auditLogLimit, setAuditLogLimit] = useState<number>(100);

  /**
   * Download security configuration as JSON file
   */
  const downloadJsonFile = (data: SecurityExport) => {
    try {
      // Create filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
      const projectName = project?.name || 'auto-claude';
      const filename = `${projectName}-security-config-${timestamp}.json`;

      // Create JSON blob
      const jsonString = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      const url = URL.createObjectURL(blob);

      // Create temporary link and trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download JSON file:', error);
      throw new Error('Failed to download file');
    }
  };

  /**
   * Handle export configuration
   */
  const handleExport = async () => {
    try {
      // Export configuration with audit logs
      const exportData = await exportConfig({
        includeAuditLogs: auditLogLimit > 0,
        auditLogLimit,
        reason: 'manual'
      });

      if (!exportData) {
        toast({
          variant: 'destructive',
          title: t('security:toast.exportFailed'),
          description: exportError || t('common:error.unknown'),
        });
        return;
      }

      // Download JSON file
      downloadJsonFile(exportData);

      // Show success toast
      toast({
        title: t('security:toast.exportSuccess'),
        description: t('security:toast.exportSuccessDescription'),
      });
    } catch (error) {
      console.error('Export failed:', error);
      toast({
        variant: 'destructive',
        title: t('security:toast.exportFailed'),
        description: error instanceof Error ? error.message : t('common:error.unknown'),
      });
    }
  };

  return (
    <div className={className}>
      <div className="space-y-4">
        {/* Header */}
        <div className="space-y-1">
          <h3 className="text-lg font-medium">{t('security:actions.export')}</h3>
          <p className="text-sm text-muted-foreground">
            Export your security configuration as a JSON file for compliance or backup.
          </p>
        </div>

        {/* Audit log limit selector */}
        <div className="space-y-2">
          <Label htmlFor="audit-log-limit">Include Recent Audit Logs</Label>
          <Select
            value={auditLogLimit.toString()}
            onValueChange={(value) => setAuditLogLimit(parseInt(value, 10))}
            disabled={isExporting}
          >
            <SelectTrigger id="audit-log-limit">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AUDIT_LOG_LIMITS.map((limit) => (
                <SelectItem key={limit.value} value={limit.value.toString()}>
                  {limit.label === 'None' ? 'No audit logs' : `${limit.label} recent entries`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {auditLogLimit === 0
              ? 'Export will include only the security profile without audit logs.'
              : `Export will include the most recent ${auditLogLimit} audit log entries.`
            }
          </p>
        </div>

        {/* Export button */}
        <Button
          onClick={handleExport}
          disabled={isExporting}
          className="w-full"
          data-testid="security-export-button"
        >
          {isExporting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('security:actions.exporting')}
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              {t('security:actions.export')}
            </>
          )}
        </Button>

        {/* Error display */}
        {exportError && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{exportError}</p>
          </div>
        )}
      </div>
    </div>
  );
}
