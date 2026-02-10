import { Webhook, Info } from 'lucide-react';
import { CollapsibleSection } from './CollapsibleSection';
import { StatusBadge } from './StatusBadge';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Separator } from '../ui/separator';
import type { WebhookConfig, WebhookIntegrationStatus } from '../../../shared/types';

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
  const badge = webhooksEnabled ? (
    <StatusBadge status="success" label="Enabled" />
  ) : null;

  // Count enabled integrations
  const enabledCount = integrationStatuses.filter((s) => s.enabled).length;

  return (
    <CollapsibleSection
      title="Webhooks & Integrations"
      icon={<Webhook className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      badge={badge}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">Enable Webhooks</Label>
          <p className="text-xs text-muted-foreground">
            Trigger builds from external events and send notifications
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
                <p className="text-sm font-medium text-foreground">Webhook Integrations</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Configure outgoing webhooks to send build notifications to Slack, Discord, Teams,
                  or Jira. Set up incoming webhooks to trigger builds from GitHub or GitLab events.
                </p>
                {enabledCount > 0 && (
                  <p className="text-xs text-info mt-2">
                    {enabledCount} integration{enabledCount > 1 ? 's' : ''} configured
                  </p>
                )}
              </div>
            </div>
          </div>

          <Separator />

          {/* Outgoing Integrations */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">Outgoing Notifications</Label>
            <p className="text-xs text-muted-foreground">
              Send build status updates to external services
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
                          {status.integration === 'teams' ? 'Microsoft Teams' : status.integration}
                        </span>
                        {status.connected ? (
                          <span className="text-xs text-success">Connected</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Not configured</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {status.enabled && (
                        <StatusBadge status="success" label="Active" />
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onConfigureIntegration(status.integration)}
                      >
                        {status.connected ? 'Configure' : 'Setup'}
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <Separator />

          {/* Incoming Integrations */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">Incoming Webhooks</Label>
            <p className="text-xs text-muted-foreground">
              Trigger builds from external events
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
                          {status.integration === 'generic' ? 'Generic Webhook' : status.integration}
                        </span>
                        {status.connected ? (
                          <span className="text-xs text-success">Active</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Not configured</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {status.enabled && (
                        <StatusBadge status="success" label="Active" />
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onConfigureIntegration(status.integration)}
                      >
                        {status.connected ? 'Configure' : 'Setup'}
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
              View detailed webhook delivery logs and troubleshooting information in the Webhook
              Logs viewer.
            </p>
          </div>
        </>
      )}
    </CollapsibleSection>
  );
}
