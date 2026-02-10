import { CheckCircle2, Settings, Plug } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { Button } from '../ui/button';
import type { WebhookIntegrationStatus } from '../../../shared/types';

interface WebhookIntegrationCardProps {
  status: WebhookIntegrationStatus;
  onConfigure: () => void;
  disabled?: boolean;
}

/**
 * Integration icon mapping
 */
const INTEGRATION_ICONS: Record<string, React.ReactNode> = {
  slack: '💬',
  discord: '🎮',
  teams: '👥',
  jira: '📋',
  github: '🐙',
  gitlab: '🦊',
  generic: '🔗',
};

/**
 * Integration name display mapping
 */
const INTEGRATION_NAMES: Record<string, string> = {
  slack: 'Slack',
  discord: 'Discord',
  teams: 'Microsoft Teams',
  jira: 'Jira',
  github: 'GitHub',
  gitlab: 'GitLab',
  generic: 'Generic Webhook',
};

/**
 * Card component for displaying individual webhook integration status and configuration
 *
 * Used in WebhooksSection to show each integration (Slack, Discord, Teams, Jira, GitHub, GitLab, Generic)
 * with its connection status, enabled state, and configuration button.
 *
 * Features:
 * - Displays integration icon and name
 * - Shows connection status (Connected/Not configured)
 * - Shows enabled/disabled badge
 * - Configure/Setup button with appropriate label
 * - Visual feedback for connection state
 * - Hover effects for better UX
 *
 * @example
 * ```tsx
 * <WebhookIntegrationCard
 *   status={slackStatus}
 *   onConfigure={() => handleConfigure('slack')}
 * />
 * ```
 */
export function WebhookIntegrationCard({
  status,
  onConfigure,
  disabled = false,
}: WebhookIntegrationCardProps) {
  const integrationName = INTEGRATION_NAMES[status.integration] || status.integration;
  const icon = INTEGRATION_ICONS[status.integration] || '🔌';

  const buttonLabel = status.connected ? 'Configure' : 'Setup';

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border border-border transition-colors ${
        !disabled ? 'hover:border-info/50 cursor-pointer' : 'opacity-50'
      }`}
      onClick={!disabled ? onConfigure : undefined}
      role="button"
      tabIndex={!disabled ? 0 : undefined}
      onKeyDown={!disabled ? (e) => e.key === 'Enter' && onConfigure() : undefined}
      aria-label={`Configure ${integrationName} integration`}
    >
      {/* Integration Info */}
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-muted text-lg">
          {icon}
        </div>

        {/* Name and Status */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{integrationName}</span>
            {status.connected && (
              <CheckCircle2 className="h-3.5 w-3.5 text-success" aria-label="Connected" />
            )}
          </div>
          {status.connected ? (
            <span className="text-xs text-success flex items-center gap-1">
              Connected
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">Not configured</span>
          )}
          {status.error && (
            <span className="text-xs text-warning" title={status.error}>
              Configuration error
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Enabled Badge */}
        {status.enabled && (
          <StatusBadge status="success" label="Active" />
        )}

        {/* Configure Button */}
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
