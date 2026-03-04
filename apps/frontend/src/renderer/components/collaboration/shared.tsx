/**
 * Shared Collaboration Components
 *
 * Reusable UI patterns shared across collaboration panels
 * (CommentThread, ApprovalWorkflow, PermissionsPanel).
 */
import type { ReactNode } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '../ui/card';

/**
 * Standardised loading state for collaboration panels.
 */
export function CollaborationLoadingState({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-center gap-3 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>{message}</span>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Standardised error state for collaboration panels.
 */
export function CollaborationErrorState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <Card className="border-destructive/30 bg-destructive/5">
      <CardContent className="p-4">
        <div className="flex items-start gap-3 text-destructive">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{title}</p>
            <p className="text-sm mt-1">{detail}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Format a timestamp into a human-readable relative string.
 *
 * Shared between CommentThread and ApprovalWorkflow so the logic
 * (and i18n keys) are not duplicated.
 */
export function formatTimestamp(
  timestamp: string,
  t: (key: string, params?: Record<string, unknown>) => string,
): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return t('collaboration:comments.justNow');
  if (diffMins < 60) return t('collaboration:comments.minutesAgo', { mins: diffMins });
  if (diffHours < 24) return t('collaboration:comments.hoursAgo', { hours: diffHours });
  if (diffDays < 7) return t('collaboration:comments.daysAgo', { days: diffDays });

  return date.toLocaleDateString();
}

/**
 * Standardised section header for collaboration panels.
 */
export function CollaborationSectionHeader({
  icon,
  title,
  description,
  badge,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  badge?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          {icon}
          {title}
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          {description}
        </p>
      </div>
      {badge}
    </div>
  );
}

/**
 * Standardised empty state for collaboration panels.
 */
export function CollaborationEmptyState({
  icon,
  title,
  subtitle,
}: {
  icon: ReactNode;
  title: string;
  subtitle?: string;
}) {
  return (
    <Card>
      <CardContent className="p-8">
        <div className="flex flex-col items-center gap-3 text-center text-muted-foreground">
          {icon}
          <div>
            <p className="font-medium text-foreground">{title}</p>
            {subtitle && <p className="text-sm mt-1">{subtitle}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
