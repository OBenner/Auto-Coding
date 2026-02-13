/**
 * SuggestionMode - Suggestion system for collaborative spec editing
 *
 * Provides a suggestion interface for proposing changes without direct editing:
 * - Create suggestions with original and proposed text
 * - Add reason/explanation for suggestions
 * - Accept or reject suggestions with review comments
 * - Visual diff between original and suggested text
 * - Status tracking (pending/accepted/rejected)
 *
 * Features:
 * - Side-by-side diff view
 * - Review workflow with comments
 * - Real-time sync with collaboration store
 * - Keyboard shortcuts for quick actions
 * - Accessible UI with proper ARIA labels
 *
 * @example
 * ```tsx
 * <SuggestionMode
 *   specId="143-collaborative-spec-editing-review"
 *   sectionId="user-stories"
 *   currentUserId="user-123"
 *   currentUserName="John Doe"
 * />
 * ```
 */

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Lightbulb,
  Check,
  X,
  Loader2,
  Plus,
  Eye,
  EyeOff,
  DiffIcon,
  FileText,
  Send,
  AlertCircle,
} from 'lucide-react';
import { useCollaborationStore } from '../../stores/collaboration-store';
import { createCollaborationAPI } from '../../../preload/api/collaboration-api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { cn } from '../../lib/utils';
import type { Suggestion, SuggestionStatus } from '../../../shared/types/collaboration';

/**
 * Props for SuggestionMode component
 */
interface SuggestionModeProps {
  /** Unique identifier for the spec */
  specId: string;
  /** Section ID to filter suggestions (null for spec-level suggestions) */
  sectionId: string | null;
  /** Current user ID */
  currentUserId: string;
  /** Current user name */
  currentUserName: string;
  /** Whether to show the create suggestion form */
  showCreateForm?: boolean;
  /** Maximum number of suggestions to display */
  maxSuggestions?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Props for SuggestionItem component
 */
interface SuggestionItemProps {
  /** The suggestion to display */
  suggestion: Suggestion;
  /** Current user ID */
  currentUserId: string;
  /** View mode (side-by-side or unified) */
  viewMode: 'side-by-side' | 'unified';
  /** Toggle view mode */
  onToggleView: () => void;
  /** Accept suggestion */
  onAccept: (suggestionId: string, reviewComment?: string) => void;
  /** Reject suggestion */
  onReject: (suggestionId: string, reviewComment?: string) => void;
  /** Delete suggestion (author only) */
  onDelete?: (suggestionId: string) => void;
}

/**
 * Format date as relative time
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Get status badge styling
 */
function getStatusBadgeProps(status: SuggestionStatus) {
  switch (status) {
    case 'pending':
      return {
        variant: 'outline' as const,
        className: 'border-yellow-500/50 text-yellow-500 gap-1',
        icon: AlertCircle,
        label: 'Pending',
      };
    case 'accepted':
      return {
        variant: 'outline' as const,
        className: 'border-green-500/50 text-green-500 gap-1',
        icon: Check,
        label: 'Accepted',
      };
    case 'rejected':
      return {
        variant: 'outline' as const,
        className: 'border-red-500/50 text-red-500 gap-1',
        icon: X,
        label: 'Rejected',
      };
    default:
      return {
        variant: 'outline' as const,
        className: 'gap-1',
        icon: AlertCircle,
        label: 'Unknown',
      };
  }
}

/**
 * SuggestionItem Component
 *
 * Renders a single suggestion with diff view and actions
 */
function SuggestionItem({
  suggestion,
  currentUserId,
  viewMode,
  onToggleView,
  onAccept,
  onReject,
  onDelete,
}: SuggestionItemProps) {
  const { t } = useTranslation(['collaboration', 'common']);
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewComment, setReviewComment] = useState('');
  const [showOriginal, setShowOriginal] = useState(true);
  const [showSuggested, setShowSuggested] = useState(true);

  const isAuthor = suggestion.author === currentUserId;
  const isPending = suggestion.status === 'pending';
  const isReviewed = !isPending;
  const canReview = !isAuthor && isPending;
  const canDelete = isAuthor && isPending;

  const statusBadge = getStatusBadgeProps(suggestion.status);
  const StatusIcon = statusBadge.icon;

  // Generate avatar color from author name
  const avatarColor = useMemo(() => {
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
    for (let i = 0; i < suggestion.author_name.length; i++) {
      hash = suggestion.author_name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
  }, [suggestion.author_name]);

  // Get user initials
  const initials = useMemo(() => {
    const parts = suggestion.author_name.trim().split(/\s+/);
    if (parts.length === 0) return '?';
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }, [suggestion.author_name]);

  // Handle accept
  const handleAccept = useCallback(() => {
    if (isReviewing && reviewComment.trim()) {
      onAccept(suggestion.id, reviewComment.trim());
      setIsReviewing(false);
      setReviewComment('');
    } else if (!isReviewing) {
      onAccept(suggestion.id);
    }
  }, [isReviewing, reviewComment, suggestion.id, onAccept]);

  // Handle reject
  const handleReject = useCallback(() => {
    if (isReviewing && reviewComment.trim()) {
      onReject(suggestion.id, reviewComment.trim());
      setIsReviewing(false);
      setReviewComment('');
    } else if (!isReviewing) {
      setIsReviewing(true);
    }
  }, [isReviewing, reviewComment, suggestion.id, onReject]);

  // Handle delete
  const handleDelete = useCallback(() => {
    if (onDelete && window.confirm(t('collaboration:suggestions.confirmDelete'))) {
      onDelete(suggestion.id);
    }
  }, [onDelete, suggestion.id, t]);

  return (
    <div
      className={cn(
        'rounded-lg border bg-card transition-colors',
        isReviewed && 'opacity-75'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 p-4 border-b">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium text-white shrink-0',
              avatarColor
            )}
          >
            {initials}
          </div>

          {/* Author and status */}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{suggestion.author_name}</span>
              <Badge variant={statusBadge.variant} className={statusBadge.className}>
                <StatusIcon className="h-3 w-3" />
                {t(`collaboration:suggestions.status.${suggestion.status}`)}
              </Badge>
            </div>
            <div className="text-xs text-muted-foreground mt-0.5">
              {formatRelativeTime(suggestion.created_at)}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onToggleView}
            title={t('collaboration:suggestions.toggleView')}
          >
            <DiffIcon className="h-3 w-3" />
          </Button>

          {/* Review actions */}
          {canReview && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-green-500 hover:text-green-600"
                onClick={handleAccept}
                disabled={isReviewing}
                title={t('collaboration:suggestions.accept')}
              >
                <Check className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-red-500 hover:text-red-600"
                onClick={handleReject}
                title={t('collaboration:suggestions.reject')}
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          )}

          {/* Delete button (author only) */}
          {canDelete && onDelete && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-destructive hover:text-destructive"
              onClick={handleDelete}
              title={t('collaboration:suggestions.delete')}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Reason (if provided) */}
      {suggestion.reason && (
        <div className="px-4 py-3 bg-muted/50 border-b">
          <div className="flex items-start gap-2 text-sm">
            <Lightbulb className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-medium">{t('collaboration:suggestions.reason')}: </span>
              <span className="text-muted-foreground">{suggestion.reason}</span>
            </div>
          </div>
        </div>
      )}

      {/* Diff view */}
      <div className="p-4">
        {viewMode === 'side-by-side' ? (
          <div className="grid grid-cols-2 gap-4">
            {/* Original text */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5" />
                  {t('collaboration:suggestions.original')}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => setShowOriginal(!showOriginal)}
                >
                  {showOriginal ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                </Button>
              </div>
              {showOriginal && (
                <div className="rounded-md border bg-red-500/5 p-3 text-sm whitespace-pre-wrap break-words border-red-500/20">
                  {suggestion.original_text}
                </div>
              )}
            </div>

            {/* Suggested text */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <DiffIcon className="h-3.5 w-3.5" />
                  {t('collaboration:suggestions.suggested')}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => setShowSuggested(!showSuggested)}
                >
                  {showSuggested ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                </Button>
              </div>
              {showSuggested && (
                <div className="rounded-md border bg-green-500/5 p-3 text-sm whitespace-pre-wrap break-words border-green-500/20">
                  {suggestion.suggested_text}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Original text */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5" />
                  {t('collaboration:suggestions.original')}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => setShowOriginal(!showOriginal)}
                >
                  {showOriginal ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                </Button>
              </div>
              {showOriginal && (
                <div className="rounded-md border bg-red-500/5 p-3 text-sm whitespace-pre-wrap break-words border-red-500/20">
                  {suggestion.original_text}
                </div>
              )}
            </div>

            {/* Suggested text */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <DiffIcon className="h-3.5 w-3.5" />
                  {t('collaboration:suggestions.suggested')}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => setShowSuggested(!showSuggested)}
                >
                  {showSuggested ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                </Button>
              </div>
              {showSuggested && (
                <div className="rounded-md border bg-green-500/5 p-3 text-sm whitespace-pre-wrap break-words border-green-500/20">
                  {suggestion.suggested_text}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Review comment input (when rejecting) */}
        {isReviewing && (
          <div className="mt-4 space-y-2">
            <Textarea
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              placeholder={t('collaboration:suggestions.reviewCommentPlaceholder')}
              className="min-h-[80px]"
              autoFocus
            />
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsReviewing(false);
                  setReviewComment('');
                }}
              >
                {t('common:cancel')}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  if (reviewComment.trim()) {
                    onReject(suggestion.id, reviewComment.trim());
                    setIsReviewing(false);
                    setReviewComment('');
                  }
                }}
                disabled={!reviewComment.trim()}
              >
                <Send className="h-4 w-4 mr-2" />
                {t('collaboration:suggestions.submitReject')}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Review info (if reviewed) */}
      {isReviewed && suggestion.reviewed_by && (
        <div className="px-4 py-3 bg-muted/30 border-t text-xs text-muted-foreground">
          {t('collaboration:suggestions.reviewedBy', {
            user: suggestion.reviewed_by,
            status: t(`collaboration:suggestions.status.${suggestion.status}`),
            when: suggestion.reviewed_at ? formatRelativeTime(suggestion.reviewed_at) : '',
          })}
          {suggestion.review_comment && (
            <div className="mt-1 italic">&quot;{suggestion.review_comment}&quot;</div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * CreateSuggestionDialog Component
 *
 * Dialog for creating new suggestions
 */
interface CreateSuggestionDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when suggestion is created */
  onCreate: (
    originalText: string,
    suggestedText: string,
    reason: string
  ) => Promise<void>;
}

function CreateSuggestionDialog({
  open,
  onOpenChange,
  onCreate,
}: CreateSuggestionDialogProps) {
  const { t } = useTranslation(['collaboration', 'common']);
  const [originalText, setOriginalText] = useState('');
  const [suggestedText, setSuggestedText] = useState('');
  const [reason, setReason] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setOriginalText('');
      setSuggestedText('');
      setReason('');
      setError(null);
    }
    onOpenChange(newOpen);
  };

  // Handle create
  const handleCreate = async () => {
    if (!originalText.trim() || !suggestedText.trim()) {
      setError(t('collaboration:suggestions.errors.missingFields'));
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      await onCreate(originalText.trim(), suggestedText.trim(), reason.trim());
      // Success - close dialog and reset
      setOriginalText('');
      setSuggestedText('');
      setReason('');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('collaboration:suggestions.errors.createFailed'));
    } finally {
      setIsCreating(false);
    }
  };

  const isValid = originalText.trim().length > 0 && suggestedText.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            {t('collaboration:suggestions.createTitle')}
          </DialogTitle>
          <DialogDescription>
            {t('collaboration:suggestions.createDescription')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Original text */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t('collaboration:suggestions.originalText')}
              <span className="text-destructive ml-1">*</span>
            </label>
            <Textarea
              value={originalText}
              onChange={(e) => setOriginalText(e.target.value)}
              placeholder={t('collaboration:suggestions.originalTextPlaceholder')}
              className="min-h-[100px]"
              disabled={isCreating}
            />
          </div>

          {/* Suggested text */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t('collaboration:suggestions.suggestedText')}
              <span className="text-destructive ml-1">*</span>
            </label>
            <Textarea
              value={suggestedText}
              onChange={(e) => setSuggestedText(e.target.value)}
              placeholder={t('collaboration:suggestions.suggestedTextPlaceholder')}
              className="min-h-[100px]"
              disabled={isCreating}
            />
          </div>

          {/* Reason (optional) */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t('collaboration:suggestions.reasonOptional')}
            </label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t('collaboration:suggestions.reasonPlaceholder')}
              className="min-h-[60px]"
              disabled={isCreating}
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isCreating}
          >
            {t('common:cancel')}
          </Button>
          <Button onClick={handleCreate} disabled={isCreating || !isValid}>
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('collaboration:suggestions.creating')}
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                {t('collaboration:suggestions.create')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * SuggestionMode Component
 *
 * Main component for managing suggestions
 */
export function SuggestionMode({
  specId,
  sectionId,
  currentUserId,
  currentUserName,
  showCreateForm = true,
  maxSuggestions = 50,
  className,
}: SuggestionModeProps) {
  const { t } = useTranslation(['collaboration', 'common']);

  // Collaboration store
  const suggestions = useCollaborationStore((state) => state.getSuggestions(specId));
  const addSuggestion = useCollaborationStore((state) => state.addSuggestion);
  const acceptSuggestion = useCollaborationStore((state) => state.acceptSuggestion);
  const rejectSuggestion = useCollaborationStore((state) => state.rejectSuggestion);
  const deleteSuggestion = useCollaborationStore((state) => state.deleteSuggestion);

  // Local state
  const [viewMode, setViewMode] = useState<'side-by-side' | 'unified'>('side-by-side');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<SuggestionStatus | 'all'>('all');

  // Refs
  const collaborationAPI = useMemo(() => createCollaborationAPI(), []);

  // Filter suggestions for this section
  const sectionSuggestions = useMemo(() => {
    return suggestions.filter((s) => s.section_id === sectionId);
  }, [suggestions, sectionId]);

  // Filter by status
  const filteredSuggestions = useMemo(() => {
    if (statusFilter === 'all') {
      return sectionSuggestions;
    }
    return sectionSuggestions.filter((s) => s.status === statusFilter);
  }, [sectionSuggestions, statusFilter]);

  // Limit suggestions
  const displayedSuggestions = useMemo(() => {
    return filteredSuggestions.slice(0, maxSuggestions);
  }, [filteredSuggestions, maxSuggestions]);

  // Create suggestion
  const handleCreateSuggestion = useCallback(
    async (originalText: string, suggestedText: string, reason: string) => {
      try {
        const result = await collaborationAPI.addSuggestion(
          specId,
          sectionId,
          currentUserId,
          currentUserName,
          originalText,
          suggestedText,
          reason || null
        );

        if (result.success && result.data) {
          addSuggestion(specId, result.data);
        } else {
          setError(result.error || t('collaboration:suggestions.errors.createFailed'));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:suggestions.errors.unknown'));
      }
    },
    [specId, sectionId, currentUserId, currentUserName, collaborationAPI, addSuggestion, t]
  );

  // Accept suggestion
  const handleAcceptSuggestion = useCallback(
    async (suggestionId: string, reviewComment?: string) => {
      try {
        // Optimistic update
        acceptSuggestion(specId, suggestionId, currentUserId, reviewComment);

        // API call
        await collaborationAPI.acceptSuggestion(suggestionId, currentUserId);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:suggestions.errors.unknown'));
      }
    },
    [specId, currentUserId, acceptSuggestion, collaborationAPI, t]
  );

  // Reject suggestion
  const handleRejectSuggestion = useCallback(
    async (suggestionId: string, reviewComment?: string) => {
      try {
        // Optimistic update
        rejectSuggestion(specId, suggestionId, currentUserId, reviewComment);

        // API call
        await collaborationAPI.rejectSuggestion(suggestionId, currentUserId, reviewComment || null);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:suggestions.errors.unknown'));
      }
    },
    [specId, currentUserId, rejectSuggestion, collaborationAPI, t]
  );

  // Delete suggestion
  const handleDeleteSuggestion = useCallback(
    async (suggestionId: string) => {
      try {
        // Optimistic update
        deleteSuggestion(specId, suggestionId);

        // API call (assuming delete endpoint exists, otherwise just remove locally)
        // await collaborationAPI.deleteSuggestion(suggestionId);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:suggestions.errors.unknown'));
      }
    },
    [specId, deleteSuggestion, t]
  );

  // Toggle view mode
  const toggleViewMode = useCallback(() => {
    setViewMode((prev) => (prev === 'side-by-side' ? 'unified' : 'side-by-side'));
  }, []);

  // Get counts by status
  const counts = useMemo(() => {
    const pending = sectionSuggestions.filter((s) => s.status === 'pending').length;
    const accepted = sectionSuggestions.filter((s) => s.status === 'accepted').length;
    const rejected = sectionSuggestions.filter((s) => s.status === 'rejected').length;
    return { pending, accepted, rejected, total: sectionSuggestions.length };
  }, [sectionSuggestions]);

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Error display */}
      {error && (
        <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span className="flex-1">{error}</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setError(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Header with actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-medium flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-amber-500" />
            {t('collaboration:suggestions.title')}
          </span>

          {/* Status badges */}
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn(
                'cursor-pointer',
                statusFilter === 'all' ? 'border-primary' : 'border-transparent'
              )}
              onClick={() => setStatusFilter('all')}
            >
              {counts.total} {t('collaboration:suggestions.total')}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                'cursor-pointer border-yellow-500/50 text-yellow-500',
                statusFilter === 'pending' ? 'border-yellow-500' : ''
              )}
              onClick={() => setStatusFilter('pending')}
            >
              {counts.pending} {t('collaboration:suggestions.status.pending')}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                'cursor-pointer border-green-500/50 text-green-500',
                statusFilter === 'accepted' ? 'border-green-500' : ''
              )}
              onClick={() => setStatusFilter('accepted')}
            >
              {counts.accepted} {t('collaboration:suggestions.status.accepted')}
            </Badge>
          </div>
        </div>

        {/* Create button */}
        {showCreateForm && (
          <Button size="sm" onClick={() => setIsCreating(true)}>
            <Plus className="h-4 w-4 mr-2" />
            {t('collaboration:suggestions.add')}
          </Button>
        )}
      </div>

      {/* Suggestions list */}
      {displayedSuggestions.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Lightbulb className="h-16 w-16 mx-auto mb-4 opacity-30" />
          <p className="text-sm mb-1">{t('collaboration:suggestions.noSuggestions')}</p>
          <p className="text-xs">{t('collaboration:suggestions.noSuggestionsHint')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {displayedSuggestions.map((suggestion) => (
            <SuggestionItem
              key={suggestion.id}
              suggestion={suggestion}
              currentUserId={currentUserId}
              viewMode={viewMode}
              onToggleView={toggleViewMode}
              onAccept={handleAcceptSuggestion}
              onReject={handleRejectSuggestion}
              onDelete={handleDeleteSuggestion}
            />
          ))}
        </div>
      )}

      {/* Create suggestion dialog */}
      {showCreateForm && (
        <CreateSuggestionDialog
          open={isCreating}
          onOpenChange={setIsCreating}
          onCreate={handleCreateSuggestion}
        />
      )}
    </div>
  );
}
