import { useTranslation } from 'react-i18next';
import { ShieldCheck, ShieldX, ShieldQuestion, FileWarning, HelpCircle } from 'lucide-react';
import { Badge } from '../ui/badge';
import type { VerificationReport } from '../../../shared/types';

type VerificationReportPanelProps = Readonly<{
  report: VerificationReport;
}>;

function verdictBadgeVariant(
  verdict: VerificationReport['verdict']
): 'success' | 'destructive' | 'warning' {
  if (verdict === 'approved') return 'success';
  if (verdict === 'rejected') return 'destructive';
  return 'warning';
}

function isPrimitive(value: unknown): value is string | number | boolean {
  return (
    typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
  );
}

function VerdictIcon({ verdict }: Readonly<{ verdict: VerificationReport['verdict'] }>) {
  if (verdict === 'approved') return <ShieldCheck className="h-3 w-3" />;
  if (verdict === 'rejected') return <ShieldX className="h-3 w-3" />;
  return <ShieldQuestion className="h-3 w-3" />;
}

/**
 * Trust Layer verification report — the structured "what was verified" summary
 * (verdict, confidence, tests, out-of-scope edits, uncertainty) read from
 * artifacts/verification-report.json.
 */
export function VerificationReportPanel({ report }: VerificationReportPanelProps) {
  const { t } = useTranslation(['tasks', 'common']);

  const testEntries = Object.entries(report.tests_run ?? {}).filter(([, v]) =>
    isPrimitive(v)
  );
  const filesChanged = report.diff_summary?.files_changed;

  return (
    <div>
      <div className="section-divider mb-4">
        <VerdictIcon verdict={report.verdict} />
        {t('tasks:overview.verificationReport')}
      </div>

      <div className="rounded-lg border p-4 space-y-3">
        {/* Verdict + confidence + files changed */}
        <div className="flex items-center gap-3 flex-wrap">
          <Badge variant={verdictBadgeVariant(report.verdict)} className="text-xs">
            {t(`tasks:overview.verdict.${report.verdict}`)}
          </Badge>
          {report.confidence !== null && report.confidence !== undefined && (
            <span className="text-xs text-muted-foreground">
              {t('tasks:overview.confidence')}:{' '}
              <span className="font-semibold text-foreground">
                {Math.round(report.confidence * 100)}%
              </span>
            </span>
          )}
          {typeof filesChanged === 'number' && (
            <span className="text-xs text-muted-foreground">
              {t('tasks:overview.filesChanged')}:{' '}
              <span className="font-semibold text-foreground">{filesChanged}</span>
            </span>
          )}
        </div>

        {/* Tests run */}
        {testEntries.length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {testEntries.map(([key, value]) => (
              <span key={key}>
                {key}:{' '}
                <span className="font-medium text-foreground">{String(value)}</span>
              </span>
            ))}
          </div>
        )}

        {/* Out-of-scope edits */}
        {report.out_of_scope_edits.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold mb-1 flex items-center gap-1.5 text-warning">
              <FileWarning className="h-3.5 w-3.5" />
              {t('tasks:overview.outOfScopeEdits')}
            </h4>
            <ul className="space-y-1">
              {report.out_of_scope_edits.map((edit) => (
                <li
                  key={`${edit.file ?? ''}|${edit.reason ?? ''}`}
                  className="text-xs text-muted-foreground"
                >
                  <span className="font-mono text-foreground">{edit.file ?? '?'}</span>
                  {edit.reason ? ` — ${edit.reason}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Uncertainty */}
        {report.uncertainty.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold mb-1 flex items-center gap-1.5">
              <HelpCircle className="h-3.5 w-3.5" />
              {t('tasks:overview.uncertainty')}
            </h4>
            <ul className="space-y-1">
              {report.uncertainty.map((item) => (
                <li
                  key={`${item.area ?? ''}|${item.reason ?? ''}`}
                  className="text-xs text-muted-foreground"
                >
                  {item.area && (
                    <span className="font-medium text-foreground">{item.area}</span>
                  )}
                  {item.area && item.reason ? ' — ' : ''}
                  {item.reason ?? ''}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
