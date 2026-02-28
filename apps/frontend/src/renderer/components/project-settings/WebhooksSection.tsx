import { useTranslation } from 'react-i18next';
import { Webhook, Info } from 'lucide-react';
import { CollapsibleSection } from './CollapsibleSection';
import { StatusBadge } from './StatusBadge';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Separator } from '../ui/separator';
import type { WebhookIntegrationStatus } from '../../../shared/types';

interface WebhooksSectionProps {
  isExpanded: boolean;
  onToggle: () => void;
  webhooksEnabled: boolean;
  onWebhooksEnabledChange: (enabled: boolean) => void;
  integrationStatuses: WebhookIntegrationStatus[];
  onConfigureIntegration: (integration: string) => void;
}

export function WebhooksSection({
  isExpanded,
  onToggle,
  webhooksEnabled,
  onWebhooksEnabledChange,
  integrationStatuses,
  onConfigureIntegration,
}: WebhooksSectionProps) {
  const { t } = useTranslation(['settings']);

  const badge = webhooksEnabled ? (
    <StatusBadge status="success" label={t('settings:webhooks.status.enabled')} />
  ) : null;

  // Count enabled integrations
  const enabledCount = integrationStatuses.filter((s) => s.enabled).length;

  const getIntegrationName = (integration: string): string => {
    return t(`settings:webhooks.integrations.${integration}`, { defaultValue: integration });
  };

  return (
    <CollapsibleSection
      title={t('settings:webhooks.title')}
      icon={<Webhook className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      badge={badge}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">
            {t('settings:webhooks.enableWebhooks')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {t('settings:webhooks.enableDescription')}
          </p>
        </div>
        <Switch
          checked={webhooksEnabled}
          onCheckedChange={onWebhooksEnabledChange}
        />
      </div>

      {webhooksEnabled && (
        <>
          {/* Integration overview */}
          <div className="rounded-lg border border-info/30 bg-info/5 p-3">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-info mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">
                  {t('settings:webhooks.integrationOverviewTitle')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('settings:webhooks.integrationOverviewDescription')}
                </p>
                {enabledCount > 0 && (
                  <p className="text-xs text-info mt-2">
                    {t('settings:webhooks.integrationsConfigured', { count: enabledCount })}
                  </p>
                )}
              </div>
            </div>
          </div>

          <Separator />

          {/* Outgoing Integrations */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:webhooks.outgoingTitle')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:webhooks.outgoingDescription')}
            </p>

            <div className="space-y-2">
              {integrationStatuses
                .filter((s) => ['slack', 'discord', 'teams', 'jira'].includes(s.integration))
                .map((status) => (
                  <div
                    key={status.integration}
                    className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-info/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-foreground capitalize">
                          {getIntegrationName(status.integration)}
                        </span>
                        {status.connected ? (
                          <span className="text-xs text-success">
                            {t('settings:webhooks.status.connected')}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {t('settings:webhooks.status.notConfigured')}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {status.enabled && (
                        <StatusBadge
                          status="success"
                          label={t('settings:webhooks.status.active')}
                        />
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onConfigureIntegration(status.integration)}
                      >
                        {status.connected
                          ? t('settings:webhooks.actions.configure')
                          : t('settings:webhooks.actions.setup')}
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <Separator />

          {/* Incoming Integrations */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:webhooks.incomingTitle')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:webhooks.incomingDescription')}
            </p>

            <div className="space-y-2">
              {integrationStatuses
                .filter((s) => ['github', 'gitlab', 'generic'].includes(s.integration))
                .map((status) => (
                  <div
                    key={status.integration}
                    className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-info/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-foreground capitalize">
                          {getIntegrationName(status.integration)}
                        </span>
                        {status.connected ? (
                          <span className="text-xs text-success">
                            {t('settings:webhooks.status.active')}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {t('settings:webhooks.status.notConfigured')}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {status.enabled && (
                        <StatusBadge
                          status="success"
                          label={t('settings:webhooks.status.active')}
                        />
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onConfigureIntegration(status.integration)}
                      >
                        {status.connected
                          ? t('settings:webhooks.actions.configure')
                          : t('settings:webhooks.actions.setup')}
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <Separator />

          {/* Webhook Logs Link */}
          <div className="rounded-lg border border-muted-foreground/20 bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">
              {t('settings:webhooks.logsHint')}
            </p>
          </div>
        </>
      )}
    </CollapsibleSection>
  );
}
