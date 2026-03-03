import { useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Clock,
  Play,
  StopCircle,
  CheckCircle2,
  Layers,
  Trash2,
  MoreHorizontal
} from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from './ui/dropdown-menu';
import { cn } from '../lib/utils';
import {
  useQuickActionsStore,
  getActionLabel,
  canRepeatAction,
  getTimeAgo,
  type RecentAction
} from '../stores/quick-actions-store';

interface QuickActionsMenuProps {
  /** Callback when an action is selected */
  onActionSelect?: (action: RecentAction) => void;
  /** Optional className for styling */
  className?: string;
}

/**
 * Get icon component for an action type
 */
function getActionIcon(type: RecentAction['type']) {
  switch (type) {
    case 'batch_qa':
      return CheckCircle2;
    case 'batch_status_update':
      return Layers;
    case 'create_task':
      return Play;
    case 'start_task':
      return Play;
    case 'stop_task':
      return StopCircle;
    default:
      return MoreHorizontal;
  }
}

/**
 * Quick Actions Menu component
 *
 * Displays a dropdown menu with recent actions for quick access.
 * Actions are persisted across sessions and can be repeated with one click.
 *
 * Features:
 * - Shows recent actions with timestamps
 * - One-click repeat for batch operations
 * - Clear history option
 * - Auto-loads from localStorage on mount
 */
export function QuickActionsMenu({ onActionSelect, className }: QuickActionsMenuProps) {
  const { t } = useTranslation(['quickActions', 'common']);
  const recentActions = useQuickActionsStore((state) => state.recentActions);
  const clearRecentActions = useQuickActionsStore((state) => state.clearRecentActions);
  const removeRecentAction = useQuickActionsStore((state) => state.removeRecentAction);
  const loadRecentActions = useQuickActionsStore((state) => state.loadRecentActions);

  // Load recent actions on mount
  useEffect(() => {
    loadRecentActions();
  }, [loadRecentActions]);

  // Handle action selection
  const handleActionSelect = useCallback(
    (action: RecentAction) => {
      if (onActionSelect) {
        onActionSelect(action);
      }
    },
    [onActionSelect]
  );

  // Handle clear all
  const handleClearAll = useCallback(() => {
    clearRecentActions();
  }, [clearRecentActions]);

  // Handle remove individual action
  const handleRemoveAction = useCallback(
    (e: React.MouseEvent, actionId: string) => {
      e.stopPropagation();
      removeRecentAction(actionId);
    },
    [removeRecentAction]
  );

  const hasRecentActions = recentActions.length > 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'relative',
            hasRecentActions && 'text-accent-foreground',
            className
          )}
        >
          <Clock className="h-4 w-4 mr-2" />
          <span>{t('quickActions:title')}</span>
          {hasRecentActions && (
            <span
              className={cn(
                'ml-2 flex h-5 w-5 items-center justify-center rounded-full',
                'bg-primary text-primary-foreground text-xs',
                'font-medium'
              )}
            >
              {recentActions.length}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center gap-2">
          <Clock className="h-4 w-4" />
          <span>{t('quickActions:recentActions')}</span>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        {hasRecentActions ? (
          <>
            <DropdownMenuGroup>
              {recentActions.map((action) => {
                const IconComponent = getActionIcon(action.type);
                const canRepeat = canRepeatAction(action);
                const timeAgo = getTimeAgo(action.timestamp);
                const label = getActionLabel(action);

                return (
                  <DropdownMenuItem
                    key={action.id}
                    disabled={!canRepeat}
                    className={cn(
                      'group flex items-center gap-2 py-2',
                      canRepeat && 'cursor-pointer'
                    )}
                    onClick={() => canRepeat && handleActionSelect(action)}
                  >
                    <div
                      className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-md',
                        'bg-muted text-muted-foreground',
                        canRepeat && 'group-hover:bg-accent group-hover:text-accent-foreground'
                      )}
                    >
                      <IconComponent className="h-4 w-4" />
                    </div>

                    <div className="flex flex-1 flex-col gap-0.5 overflow-hidden">
                      <span className="truncate text-sm font-medium">
                        {label}
                      </span>
                      <span className="truncate text-xs text-muted-foreground">
                        {timeAgo}
                      </span>
                    </div>

                    {canRepeat && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                        onClick={(e) => handleRemoveAction(e, action.id)}
                      >
                        <Trash2 className="h-3 w-3 text-muted-foreground" />
                      </Button>
                    )}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              className="cursor-pointer text-destructive focus:text-destructive"
              onClick={handleClearAll}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              <span>{t('quickActions:clearHistory')}</span>
            </DropdownMenuItem>
          </>
        ) : (
          <div className="py-8 text-center text-sm text-muted-foreground">
            <Clock className="mx-auto h-8 w-8 mb-2 opacity-50" />
            <p>{t('quickActions:noRecentActions')}</p>
            <p className="mt-1 text-xs">
              {t('quickActions:noRecentActionsHint')}
            </p>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
