import { CheckCircle, XCircle, Clock, TrendingUp, Activity } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import type { WebhookDeliveryStats } from '../../shared/types/webhook';

interface WebhookStatsProps {
  stats: WebhookDeliveryStats | null;
  loading: boolean;
  error: string | null;
}

export function WebhookStats({ stats, loading, error }: WebhookStatsProps) {
  const { t } = useTranslation(['webhooks', 'common']);

  // Loading state
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Activity className="h-8 w-8 animate-pulse text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-12 w-12 text-destructive" />
          <h3 className="mt-4 text-lg font-semibold">{t('webhooks:stats.error.title')}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  // No stats available
  if (!stats) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center py-12">
          <Activity className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">{t('webhooks:stats.empty.title')}</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {t('webhooks:stats.empty.description')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Deliveries */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('webhooks:stats.total')}
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>

        {/* Successful Deliveries */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('webhooks:stats.success')}
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.success}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.total > 0
                ? `${((stats.success / stats.total) * 100).toFixed(1)}%`
                : '0%'}
            </p>
          </CardContent>
        </Card>

        {/* Failed Deliveries */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('webhooks:stats.failed')}
            </CardTitle>
            <XCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{stats.failed}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.total > 0
                ? `${((stats.failed / stats.total) * 100).toFixed(1)}%`
                : '0%'}
            </p>
          </CardContent>
        </Card>

        {/* Pending Deliveries */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('webhooks:stats.pending')}
            </CardTitle>
            <Clock className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.total > 0
                ? `${((stats.pending / stats.total) * 100).toFixed(1)}%`
                : '0%'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Success Rate & Average Duration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Success Rate */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('webhooks:stats.successRate')}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.success_rate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground mt-2">
              {t('webhooks:stats.successRateDescription')}
            </p>
          </CardContent>
        </Card>

        {/* Average Duration */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('webhooks:stats.avgDuration')}
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {stats.avg_duration_ms < 1000
                ? `${stats.avg_duration_ms.toFixed(0)}ms`
                : `${(stats.avg_duration_ms / 1000).toFixed(2)}s`}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {t('webhooks:stats.avgDurationDescription')}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
