/**
 * BookmarkPanel Component
 *
 * Displays and manages bookmarks for session replay.
 * Shows a list of bookmarks with remove functionality.
 */

import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Bookmark, X, Clock, Tag, FileText } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { Bookmark as BookmarkType } from '../../../shared/types';

interface BookmarkPanelProps {
  /** Bookmarks to display */
  bookmarks: BookmarkType[];
  /** Callback when a bookmark is removed */
  onRemove: (id: string) => void;
  /** Callback when a bookmark is clicked */
  onBookmarkClick?: (bookmark: BookmarkType) => void;
  /** Maximum number of bookmarks to display */
  maxBookmarks?: number;
  /** Disable remove functionality */
  disabled?: boolean;
  /** Additional className */
  className?: string;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string | undefined | null): string {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Get phase badge color
 */
function getPhaseBadgeColor(phase: string): string {
  const phaseColors: Record<string, string> = {
    planning: 'bg-blue-500/20 text-blue-400',
    coding: 'bg-purple-500/20 text-purple-400',
    validation: 'bg-green-500/20 text-green-400',
  };
  return phaseColors[phase] || 'bg-gray-500/20 text-gray-400';
}

/**
 * BookmarkPanel displays a list of bookmarks with remove functionality
 * Styled similarly to ReferencedFilesSection
 */
export function BookmarkPanel({
  bookmarks,
  onRemove,
  onBookmarkClick,
  maxBookmarks = 50,
  disabled = false,
  className,
}: BookmarkPanelProps) {
  const { t } = useTranslation('session-replay');
  const [expandedBookmark, setExpandedBookmark] = useState<string | null>(null);

  // Display bookmarks up to max limit
  const displayBookmarks = useMemo(() => {
    return bookmarks.slice(0, maxBookmarks);
  }, [bookmarks, maxBookmarks]);

  const hasMoreBookmarks = bookmarks.length > maxBookmarks;

  // Toggle bookmark expansion
  const toggleExpand = useCallback(
    (bookmarkId: string) => {
      setExpandedBookmark((prev) => (prev === bookmarkId ? null : bookmarkId));
    },
    []
  );

  // Handle bookmark click
  const handleBookmarkClick = useCallback(
    (bookmark: BookmarkType) => {
      if (onBookmarkClick) {
        onBookmarkClick(bookmark);
      }
    },
    [onBookmarkClick]
  );

  // Handle remove
  const handleRemove = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      onRemove(id);
    },
    [onRemove]
  );

  if (bookmarks.length === 0) {
    return (
      <div className={cn('text-center py-8', className)}>
        <Bookmark className="h-8 w-8 mx-auto mb-2 text-muted-foreground opacity-50" />
        <p className="text-sm text-muted-foreground">{t('sessionList.noBookmarks')}</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {/* Header with count badge */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          {t('sessionList.bookmarks')}
          <span className="ml-2 text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
            {bookmarks.length}
          </span>
        </span>
      </div>

      {/* Bookmark list */}
      <div className="space-y-2">
        {displayBookmarks.map((bookmark) => (
          <button
            type="button"
            key={bookmark.id}
            className={cn(
              'group relative w-full text-left',
              onBookmarkClick && 'cursor-pointer hover:bg-muted/50 transition-colors'
            )}
            onClick={() => handleBookmarkClick(bookmark)}
          >
            {/* Main bookmark card */}
            <div
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg',
                'bg-muted/30 border border-border',
                'hover:border-border/80 transition-colors'
              )}
            >
              {/* Bookmark icon */}
              <div className="shrink-0 mt-0.5">
                <Bookmark className="h-4 w-4 text-primary fill-primary" />
              </div>

              {/* Bookmark content */}
              <div className="flex-1 min-w-0">
                {/* Label and phase badge */}
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-foreground truncate">
                    {bookmark.label ?? ''}
                  </span>
                  <Badge className={cn('gap-1 shrink-0', getPhaseBadgeColor(bookmark.phase ?? ''))}>
                    <span className="text-xs uppercase">{bookmark.phase ?? ''}</span>
                  </Badge>
                </div>

                {/* Metadata row */}
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  {/* Timestamp */}
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3 shrink-0" />
                    <span>{formatTimestamp(bookmark.timestamp)}</span>
                  </div>

                  {/* Session */}
                  {bookmark.session && (
                    <div className="flex items-center gap-1">
                      <Tag className="h-3 w-3 shrink-0" />
                      <span>{t('sessionPlayer.session')} {bookmark.session}</span>
                    </div>
                  )}

                  {/* Subtask */}
                  {bookmark.subtask_id && (
                    <div className="truncate" title={bookmark.subtask_id}>
                      {bookmark.subtask_id}
                    </div>
                  )}
                </div>

                {/* Note (expandable) */}
                {bookmark.note && (
                  <div className="mt-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(bookmark.id);
                      }}
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <FileText className="h-3 w-3" />
                      <span>
                        {expandedBookmark === bookmark.id
                          ? t('sessionPlayer.collapseDetails')
                          : t('sessionPlayer.expandDetails')}
                      </span>
                    </button>
                    {expandedBookmark === bookmark.id && (
                      <div className="mt-2 text-xs text-muted-foreground bg-secondary/50 rounded p-2">
                        {bookmark.note}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Remove button */}
              {!disabled && (
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity',
                    'hover:bg-destructive/10 hover:text-destructive shrink-0'
                  )}
                  onClick={(e) => handleRemove(e, bookmark.id)}
                  aria-label={t('sessionPlayer.removeBookmark')}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* More indicator */}
      {hasMoreBookmarks && (
        <div className="text-xs text-muted-foreground text-center pt-2">
          {t('bookmarks.moreBookmarks', {
            count: bookmarks.length - maxBookmarks,
          })}
        </div>
      )}
    </div>
  );
}
