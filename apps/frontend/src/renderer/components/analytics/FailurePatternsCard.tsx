import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  Bug,
  FileWarning,
  TrendingDown,
  ShieldAlert
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { FailureMetrics } from '../../../shared/types/productivity-analytics';

interface FailurePatternsCardProps {
  failureMetrics: FailureMetrics | null;
  isLoading?: boolean;
}

const VARIANT_STYLES: Record<string, string> = {
  default: 'bg-accent/10 text-accent',
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  error: 'bg-destructive/10 text-destructive',
};

interface CategoryItemProps {
  category: string;
  count: number;
  total: number;
}

function CategoryItem({ category, count, total }: CategoryItemProps) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-md bg-muted/20 border border-border/30">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <Bug className="h-4 w-4 text-destructive/70 flex-shrink-0" />
        <span className="text-sm font-medium text-foreground truncate">{category}</span>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="text-xs text-muted-foreground">{percentage}%</div>
        <Badge variant="outline" className="text-xs min-w-[2.5rem] justify-center">
          {count}
        </Badge>
      </div>
    </div>
  );
}

function formatPct(rate: number | undefined): string {
  return `${((rate ?? 0) * 100).toFixed(1)}%`;
}

export function FailurePatternsCard({ failureMetrics, isLoading = false }: FailurePatternsCardProps) {
  const { t } = useTranslation(['common']);

  const topCategories = useMemo(
    () => failureMetrics?.top_failure_categories ?? [],
    [failureMetrics],
  );

  const statCards = useMemo(() => {
    if (!failureMetrics) return [];
    const f = failureMetrics;
    const rootRate = f.root_cause_rate ?? 0;
    const patternRate = f.pattern_detection_rate ?? 0;
    const recurRate = f.recurrence_rate ?? 0;

    const rateVariant = (v: number, high: number, mid: number) =>
      v >= high ? 'success' : v >= mid ? 'warning' : 'error';
    const inverseVariant = (v: number, low: number, mid: number) =>
      v <= low ? 'success' : v <= mid ? 'warning' : 'error';

    return [
      { key: 'total', icon: AlertTriangle, labelKey: 'common:failurePatterns.totalFailures', value: f.total_failures, variant: f.total_failures > 10 ? 'error' : f.total_failures > 5 ? 'warning' : 'default' },
      { key: 'rootCause', icon: Bug, labelKey: 'common:failurePatterns.rootCauseRate', value: formatPct(rootRate), variant: rateVariant(rootRate, 0.8, 0.5) },
      { key: 'pattern', icon: FileWarning, labelKey: 'common:failurePatterns.patternDetection', value: formatPct(patternRate), variant: rateVariant(patternRate, 0.8, 0.5) },
      { key: 'recurrence', icon: TrendingDown, labelKey: 'common:failurePatterns.recurrenceRate', value: formatPct(recurRate), variant: inverseVariant(recurRate, 0.2, 0.5) },
    ];
  }, [failureMetrics]);

  const hasData = failureMetrics && failureMetrics.total_failures > 0;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-destructive" />
            {t('common:failurePatterns.title')}
          </CardTitle>
          {hasData && (
            <Badge variant="outline" className="text-xs">
              {t('common:failurePatterns.failureCount', { count: failureMetrics.total_failures })}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <AlertTriangle className="h-5 w-5 animate-pulse mr-2" />
            {t('common:failurePatterns.loading')}
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <ShieldAlert className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">{t('common:failurePatterns.noData')}</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              {t('common:failurePatterns.noDataHint')}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Metrics Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {statCards.map(({ key, icon: Icon, labelKey, value, variant }) => (
                <div key={key} className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                  <div className={`p-2 rounded-lg ${VARIANT_STYLES[variant]}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-muted-foreground mb-1">{t(labelKey)}</div>
                    <div className="text-2xl font-semibold text-foreground">{value}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Top Failure Categories */}
            {topCategories.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Bug className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold text-foreground">{t('common:failurePatterns.commonCategories')}</h3>
                </div>
                <div className="space-y-2">
                  {topCategories.map((item) => (
                    <CategoryItem
                      key={item.category}
                      category={item.category}
                      count={item.count}
                      total={failureMetrics.total_failures}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
