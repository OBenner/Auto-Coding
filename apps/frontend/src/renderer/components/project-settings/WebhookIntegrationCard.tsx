import type { ReactNode, KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, Settings } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { Button } from '../ui/button';
import type { WebhookIntegrationStatus } from '../../../shared/types';

interface WebhookIntegrationCardProps {
  status: WebhookIntegrationStatus;
  onConfigure: () => void;
  disabled?: boolean;
}

const INTEGRATION_ICONS: Record<string, ReactNode> = {
  slack: '💬',
  discord: '🎮',
  teams: '👥',
  jira: '📋',
  github: '🐙',
  gitlab: '🦊',
  generic: '🔗',
};

export function WebhookIntegrationCard({
  status,
  onConfigure,
  disabled = false,
}: WebhookIntegrationCardProps) {
  const { t } = useTranslation(['settings']);

  const integrationName = t(`settings:webhooks.integrations.${status.integration}`, {
    defaultValue: status.integration,
  });
  const icon = INTEGRATION_ICONS[status.integration] || '🔗';
  const buttonLabel = status.connected
    ? t('settings:webhooks.actions.configure')
    : t('settings:webhooks.actions.setup');

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onConfigure();
    }
  };

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border border-border transition-colors ${
        !disabled ? 'hover:border-info/50 cursor-pointer' : 'opacity-50'
      }`}
      onClick={!disabled ? onConfigure : undefined}
      role="button"
      tabIndex={!disabled ? 0 : undefined}
      onKeyDown={!disabled ? handleKeyDown : undefined}
      aria-disabled={disabled || undefined}
      aria-label={t('settings:webhooks.actions.configureAriaLabel', {
        integration: integrationName,
      })}
    >
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-muted text-lg">
          {icon}
        </div>

        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{integrationName}</span>
            {status.connected && (
              <CheckCircle2
                className="h-3.5 w-3.5 text-success"
                aria-label={t('settings:webhooks.status.connected')}
              />
            )}
          </div>
          {status.connected ? (
            <span className="text-xs text-success flex items-center gap-1">
              {t('settings:webhooks.status.connected')}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">
              {t('settings:webhooks.status.notConfigured')}
            </span>
          )}
          {status.error && (
            <span className="text-xs text-warning" title={status.error}>
              {t('settings:webhooks.status.configError')}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {status.enabled && (
          <StatusBadge status="success" label={t('settings:webhooks.status.active')} />
        )}

        <Button
          size="sm"
          variant="outline"
          onClick={(e) => {
            e.stopPropagation();
            onConfigure();
          }}
          disabled={disabled}
          aria-label={buttonLabel}
        >
          <Settings className="h-3.5 w-3.5 mr-1.5" />
          {buttonLabel}
        </Button>
      </div>
    </div>
  );
}
