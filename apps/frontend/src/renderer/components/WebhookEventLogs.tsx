import { Clock, CheckCircle, XCircle, AlertCircle, Loader2, ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from './ui/collapsible';
import type { WebhookDelivery, WebhookDeliveryStatus } from '../../shared/types/webhook';

interface WebhookEventLogsProps {
  deliveries: WebhookDelivery[];
  loading: boolean;
  error: string | null;
  onRetry?: (deliveryId: string) => void;
}

export function WebhookEventLogs({ deliveries, loading, error, onRetry }: Readonly<WebhookEventLogsProps>) {
  const { t } = useTranslation(['webhooks', 'common']);

  // Get status icon and variant
  const getStatusInfo = (status: WebhookDeliveryStatus) => {
    switch (status) {
      case 'success':
        return {
          icon: CheckCircle,
          variant: 'default' as const,
          label: t('webhooks:history.status.success')
        };
      case 'failed':
      case 'permanent_failure':
        return {
          icon: XCircle,
          variant: 'destructive' as const,
          label: t('webhooks:history.status.failed')
        };
      case 'pending':
      case 'sending':
        return {
          icon: Loader2,
          variant: 'secondary' as const,
          label: t('webhooks:history.status.pending')
        };
      case 'timeout':
        return {
          icon: AlertCircle,
          variant: 'destructive' as const,
          label: t('webhooks:history.status.timeout')
        };
      default:
        return {
          icon: AlertCircle,
          variant: 'secondary' as const,
          label: status
        };
    }
  };

  // Format duration
  const formatDuration = (ms?: number): string => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return t('webhooks:history.time.justNow');
    if (diffMins < 60) return t('webhooks:history.time.minsAgo', { count: diffMins });
    if (diffHours < 24) return t('webhooks:history.time.hoursAgo', { count: diffHours });
    if (diffDays < 7) return t('webhooks:history.time.daysAgo', { count: diffDays });

    return date.toLocaleDateString();
  };

  // Loading state
  if (loading && deliveries.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h3 className="mt-4 text-lg font-semibold">{t('webhooks:history.error.title')}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (deliveries.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center py-12">
          <Clock className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">{t('webhooks:history.empty.title')}</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {t('webhooks:history.empty.description')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-3">
        {deliveries.map((delivery) => {
          const statusInfo = getStatusInfo(delivery.status);
          const StatusIcon = statusInfo.icon;

          return (
            <Collapsible key={delivery.delivery_id} className="border rounded-md">
              <div className="flex items-center gap-3 p-4">
                {/* Status Icon */}
                <div className={`flex-shrink-0 ${delivery.status === 'sending' ? 'animate-spin' : ''}`}>
                  <StatusIcon className="h-5 w-5" />
                </div>

                {/* Main Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{delivery.event}</span>
                    <Badge variant={statusInfo.variant} className="flex-shrink-0">
                      {statusInfo.label}
                    </Badge>
                    {delivery.attempt_number > 1 && (
                      <Badge variant="outline" className="flex-shrink-0">
                        {t('webhooks:history.attempts', { count: delivery.attempt_number })}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                    <span>{formatTimestamp(delivery.created_at)}</span>
                    {delivery.duration_ms && (
                      <>
                        <span>•</span>
                        <span>{formatDuration(delivery.duration_ms)}</span>
                      </>
                    )}
                    {delivery.response_status_code && (
                      <>
                        <span>•</span>
                        <span
                          className={
                            delivery.response_status_code >= 200 && delivery.response_status_code < 300
                              ? 'text-green-600'
                              : 'text-destructive'
                          }
                        >
                          {delivery.response_status_code}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Expand Trigger */}
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="icon" className="flex-shrink-0">
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </CollapsibleTrigger>
              </div>

              {/* Expanded Details */}
              <CollapsibleContent className="border-t border-border bg-muted/30">
                <div className="p-4 space-y-3">
                  {/* Error Message */}
                  {delivery.error_message && (
                    <div>
                      <div className="text-sm font-medium mb-1">
                        {t('webhooks:history.details.error')}
                      </div>
                      <div className="text-sm text-destructive font-mono bg-destructive/10 p-2 rounded">
                        {delivery.error_message}
                      </div>
                    </div>
                  )}

                  {/* Response Body */}
                  {delivery.response_body && (
                    <div>
                      <div className="text-sm font-medium mb-1">
                        {t('webhooks:history.details.response')}
                      </div>
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-32">
                        {JSON.stringify(delivery.response_body, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Payload Preview */}
                  {delivery.payload && (
                    <div>
                      <div className="text-sm font-medium mb-1">
                        {t('webhooks:history.details.payload')}
                      </div>
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-32">
                        {JSON.stringify(delivery.payload, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Retry Info */}
                  {delivery.next_retry_at && (
                    <div className="text-sm text-muted-foreground">
                      {t('webhooks:history.details.nextRetry', {
                        time: formatTimestamp(delivery.next_retry_at)
                      })}
                    </div>
                  )}

                  {/* Retry Button (for failed deliveries) */}
                  {(delivery.status === 'failed' || delivery.status === 'permanent_failure') && onRetry && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onRetry(delivery.delivery_id)}
                    >
                      {t('webhooks:history.retry')}
                    </Button>
                  )}
                </div>
              </CollapsibleContent>
            </Collapsible>
          );
        })}
      </div>
    </ScrollArea>
  );
}
