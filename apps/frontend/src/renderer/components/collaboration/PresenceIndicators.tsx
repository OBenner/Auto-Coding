/**
 * PresenceIndicators - Real-time user presence indicators for collaborative editing
 *
 * Displays which users are currently viewing or editing a spec with visual indicators:
 * - User avatars with status colors
 * - Presence type badges (viewing/editing/idle)
 * - Hover tooltips with detailed info
 * - Stack layout for multiple users
 *
 * Features:
 * - Shows active users with real-time presence updates
 * - Visual distinction between viewing/editing/idle states
 * - Smooth animations for presence changes
 * - Accessible tooltips with user information
 *
 * @example
 * ```tsx
 * <PresenceIndicators
 *   specId="143-collaborative-spec-editing-review"
 *   currentUserId="user-123"
 *   maxVisible={3}
 * />
 * ```
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Eye,
  Edit3,
  Clock,
  User,
  Users as UsersIcon,
} from 'lucide-react';
import { useCollaborationStore } from '../../stores/collaboration-store';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { Presence, PresenceType } from '../../../shared/types/collaboration';

/**
 * Props for PresenceIndicators component
 */
interface PresenceIndicatorsProps {
  /** Unique identifier for the spec */
  specId: string;
  /** Current user ID to exclude from display */
  currentUserId: string;
  /** Maximum number of avatars to show before showing "+N more" */
  maxVisible?: number;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show labels alongside indicators */
  showLabels?: boolean;
}

/**
 * Get presence icon component
 */
function getPresenceIcon(presenceType: PresenceType) {
  switch (presenceType) {
    case 'viewing':
      return Eye;
    case 'editing':
      return Edit3;
    case 'idle':
      return Clock;
    default:
      return User;
  }
}

/**
 * Get presence color class
 */
function getPresenceColor(presenceType: PresenceType): string {
  switch (presenceType) {
    case 'viewing':
      return 'bg-blue-500';
    case 'editing':
      return 'bg-green-500';
    case 'idle':
      return 'bg-yellow-500';
    default:
      return 'bg-muted-foreground';
  }
}

/**
 * Get presence border color
 */
function getPresenceBorderColor(presenceType: PresenceType): string {
  switch (presenceType) {
    case 'viewing':
      return 'border-blue-500';
    case 'editing':
      return 'border-green-500';
    case 'idle':
      return 'border-yellow-500';
    default:
      return 'border-muted-foreground';
  }
}

/**
 * Check if presence is stale (no activity for 60 seconds)
 */
function isPresenceStale(presence: Presence): boolean {
  const elapsed = (Date.now() - presence.last_seen.getTime()) / 1000;
  return elapsed > 60;
}

/**
 * Generate avatar color from user name
 */
function getAvatarColor(userName: string): string {
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-green-500',
    'bg-emerald-500',
    'bg-teal-500',
    'bg-cyan-500',
    'bg-blue-500',
    'bg-indigo-500',
    'bg-violet-500',
    'bg-purple-500',
    'bg-fuchsia-500',
    'bg-pink-500',
    'bg-rose-500',
  ];

  let hash = 0;
  for (let i = 0; i < userName.length; i++) {
    hash = userName.charCodeAt(i) + ((hash << 5) - hash);
  }

  const index = Math.abs(hash) % colors.length;
  return colors[index];
}

/**
 * Get user initials from name
 */
function getUserInitials(userName: string): string {
  const parts = userName.trim().split(/\s+/);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * PresenceIndicators Component
 *
 * Shows real-time presence of users viewing/editing the spec
 */
export function PresenceIndicators({
  specId,
  currentUserId,
  maxVisible = 3,
  className,
  showLabels = false,
}: PresenceIndicatorsProps) {
  const { t } = useTranslation(['collaboration', 'common']);

  // Get active presences from store (exclude current user and stale presences)
  const activePresences = useCollaborationStore(
    (state) => state.getPresences(specId).filter(
      (p) => p.user_id !== currentUserId && !isPresenceStale(p)
    )
  );

  // Sort presences: editing first, then viewing, then idle
  const sortedPresences = useMemo(() => {
    const priority: Record<PresenceType, number> = {
      editing: 0,
      viewing: 1,
      idle: 2,
    };

    return [...activePresences].sort((a, b) => {
      const priorityDiff = priority[a.presence_type] - priority[b.presence_type];
      if (priorityDiff !== 0) return priorityDiff;
      // If same presence type, sort by name
      return a.user_name.localeCompare(b.user_name);
    });
  }, [activePresences]);

  // Separate visible and hidden presences
  const visiblePresences = sortedPresences.slice(0, maxVisible);
  const hiddenCount = sortedPresences.length - maxVisible;

  // If no active users, show empty state or null
  if (sortedPresences.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* User avatars with presence indicators */}
      <div className="flex items-center -space-x-2">
        {visiblePresences.map((presence) => {
          const PresenceIcon = getPresenceIcon(presence.presence_type);
          const avatarColor = getAvatarColor(presence.user_name);
          const presenceColor = getPresenceColor(presence.presence_type);
          const borderColor = getPresenceBorderColor(presence.presence_type);

          return (
            <div
              key={presence.user_id}
              className="group relative inline-flex items-center justify-center"
              title={`${presence.user_name} - ${t(`collaboration:presence.${presence.presence_type}`)}`}
            >
              {/* Avatar circle */}
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium text-white ring-2 ring-background transition-all',
                  avatarColor
                )}
              >
                {getUserInitials(presence.user_name)}
              </div>

              {/* Presence indicator dot */}
              <div
                className={cn(
                  'absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-background transition-all',
                  borderColor,
                  'border-2'
                )}
              >
                <div
                  className={cn(
                    'h-2 w-2 rounded-full',
                    presenceColor
                  )}
                />
              </div>

              {/* Tooltip with detailed info */}
              <div className="pointer-events-none absolute inset-0 rounded-full opacity-0 transition-opacity group-hover:opacity-100">
                <div className="absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-popover px-3 py-1.5 text-xs shadow-md">
                  <div className="flex items-center gap-1.5 font-medium">
                    <PresenceIcon className="h-3 w-3" />
                    <span>{presence.user_name}</span>
                  </div>
                  <div className="text-muted-foreground">
                    {t(`collaboration:presence.${presence.presence_type}`)}
                  </div>
                  {/* Arrow */}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-popover" />
                </div>
              </div>
            </div>
          );
        })}

        {/* "+N more" indicator */}
        {hiddenCount > 0 && (
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground ring-2 ring-background"
            title={`${t('collaboration:presence.additionalUsers', { count: hiddenCount })}`}
          >
            +{hiddenCount}
          </div>
        )}
      </div>

      {/* User count badge (optional, when showLabels is true) */}
      {showLabels && (
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <UsersIcon className="h-4 w-4" aria-hidden="true" />
          <span>
            {sortedPresences.length} {t('collaboration:presence.activeUsers')}
          </span>
        </div>
      )}

      {/* Presence type breakdown (optional, when showLabels is true) */}
      {showLabels && sortedPresences.length > 1 && (
        <div className="flex items-center gap-2">
          {sortedPresences.some((p) => p.presence_type === 'editing') && (
            <Badge variant="outline" className="gap-1.5 text-xs border-green-500/50 text-green-500">
              <Edit3 className="h-3 w-3" aria-hidden="true" />
              {sortedPresences.filter((p) => p.presence_type === 'editing').length}{' '}
              {t('collaboration:presence.editing')}
            </Badge>
          )}
          {sortedPresences.some((p) => p.presence_type === 'viewing') && (
            <Badge variant="outline" className="gap-1.5 text-xs border-blue-500/50 text-blue-500">
              <Eye className="h-3 w-3" aria-hidden="true" />
              {sortedPresences.filter((p) => p.presence_type === 'viewing').length}{' '}
              {t('collaboration:presence.viewing')}
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
