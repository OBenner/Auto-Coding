/**
 * CommentThread - Threaded comment system for collaborative spec editing
 *
 * Provides a threaded comment interface for discussing spec sections:
 * - Add new comments
 * - Reply to existing comments (threaded)
 * - Resolve/unresolve comments
 * - Real-time updates via WebSocket
 * - Markdown rendering for content
 *
 * Features:
 * - Hierarchical threading via parent_id
 * - Visual distinction between top-level and reply comments
 * - Comment status indicators (active/resolved)
 * - Real-time sync with collaboration store
 * - Accessible keyboard navigation
 *
 * @example
 * ```tsx
 * <CommentThread
 *   specId="143-collaborative-spec-editing-review"
 *   sectionId="user-stories"
 *   currentUserId="user-123"
 * />
 * ```
 */

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MessageSquare,
  Reply,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Send,
  X,
} from 'lucide-react';
import { useCollaborationStore } from '../../stores/collaboration-store';
import { createCollaborationAPI } from '../../../preload/api/collaboration-api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { Comment, CommentStatus } from '../../../shared/types/collaboration';

/**
 * Props for CommentThread component
 */
interface CommentThreadProps {
  /** Unique identifier for the spec */
  specId: string;
  /** Section ID to filter comments (null for general comments) */
  sectionId: string | null;
  /** Current user ID */
  currentUserId: string;
  /** Current user name */
  currentUserName?: string;
  /** Maximum depth for nested replies */
  maxDepth?: number;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the add comment form */
  showAddForm?: boolean;
}

/**
 * Props for individual CommentItem component
 */
interface CommentItemProps {
  /** The comment to display */
  comment: Comment;
  /** All comments (for threading) */
  allComments: Comment[];
  /** Current user ID */
  currentUserId: string;
  /** Current depth in thread */
  depth: number;
  /** Maximum depth before collapsing */
  maxDepth: number;
  /** Whether to show replies */
  showReplies: boolean;
  /** Toggle replies visibility */
  onToggleReplies: (commentId: string) => void;
  /** Reply to this comment */
  onReply: (commentId: string) => void;
  /** Resolve/unresolve comment */
  onResolve: (commentId: string) => void;
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
 * CommentItem Component
 *
 * Renders a single comment with threading support
 */
function CommentItem({
  comment,
  allComments,
  currentUserId,
  depth,
  maxDepth,
  showReplies,
  onToggleReplies,
  onReply,
  onResolve,
}: CommentItemProps) {
  const { t } = useTranslation(['collaboration', 'common']);

  // Find replies to this comment
  const replies = useMemo(() => {
    return allComments.filter((c) => c.parent_id === comment.id);
  }, [allComments, comment.id]);

  const hasReplies = replies.length > 0;
  const isResolved = comment.status === 'resolved';
  const isAuthor = comment.author === currentUserId;
  const canResolve = isAuthor || !isResolved;

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
    for (let i = 0; i < comment.author_name.length; i++) {
      hash = comment.author_name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
  }, [comment.author_name]);

  // Get user initials
  const initials = useMemo(() => {
    const parts = comment.author_name.trim().split(/\s+/);
    if (parts.length === 0) return '?';
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }, [comment.author_name]);

  const isAtMaxDepth = depth >= maxDepth;

  return (
    <div
      className={cn(
        'group',
        depth > 0 && 'ml-8 pl-4 border-l-2 border-border/50'
      )}
    >
      {/* Comment card */}
      <div
        className={cn(
          'rounded-lg border bg-card p-4 transition-colors',
          isResolved && 'opacity-60'
        )}
      >
        {/* Header: author and metadata */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            {/* Avatar */}
            <div
              className={cn(
                'flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium text-white shrink-0',
                avatarColor
              )}
            >
              {initials}
            </div>

            {/* Author name */}
            <span className="font-medium text-sm">{comment.author_name}</span>

            {/* Status badge */}
            {isResolved && (
              <Badge variant="outline" className="gap-1 text-xs border-green-500/50 text-green-500">
                <CheckCircle2 className="h-3 w-3" />
                {t('collaboration:comments.resolved')}
              </Badge>
            )}
          </div>

          {/* Timestamp */}
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {formatRelativeTime(comment.created_at)}
          </span>
        </div>

        {/* Comment content */}
        <div className="text-sm whitespace-pre-wrap break-words mb-3">
          {comment.content}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Reply button */}
          {!isResolved && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={() => onReply(comment.id)}
            >
              <Reply className="h-3 w-3 mr-1" />
              {t('collaboration:comments.reply')}
            </Button>
          )}

          {/* Resolve/unresolve button */}
          {canResolve && (
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'h-7 text-xs',
                isResolved && 'text-muted-foreground'
              )}
              onClick={() => onResolve(comment.id)}
            >
              {isResolved ? (
                <>
                  <Circle className="h-3 w-3 mr-1" />
                  {t('collaboration:comments.reopen')}
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  {t('collaboration:comments.resolve')}
                </>
              )}
            </Button>
          )}

          {/* Toggle replies (if at max depth or has many replies) */}
          {hasReplies && (isAtMaxDepth || replies.length > 3) && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => onToggleReplies(comment.id)}
            >
              {showReplies ? (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  {t('collaboration:comments.hideReplies', { count: replies.length })}
                </>
              ) : (
                <>
                  <ChevronRight className="h-3 w-3 mr-1" />
                  {t('collaboration:comments.showReplies', { count: replies.length })}
                </>
              )}
            </Button>
          )}
        </div>

        {/* Resolved info */}
        {isResolved && comment.resolved_by && (
          <div className="mt-2 text-xs text-muted-foreground">
            {t('collaboration:comments.resolvedBy', {
              user: comment.resolved_by,
              when: comment.resolved_at
                ? formatRelativeTime(comment.resolved_at)
                : '',
            })}
          </div>
        )}
      </div>

      {/* Replies (if not at max depth or replies are shown) */}
      {hasReplies && (!isAtMaxDepth || showReplies) && (
        <div className="mt-3 space-y-3">
          {replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              allComments={allComments}
              currentUserId={currentUserId}
              depth={depth + 1}
              maxDepth={maxDepth}
              showReplies={showReplies}
              onToggleReplies={onToggleReplies}
              onReply={onReply}
              onResolve={onResolve}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * CommentThread Component
 *
 * Manages threaded comments for a spec section
 */
export function CommentThread({
  specId,
  sectionId,
  currentUserId,
  currentUserName = 'Current User',
  maxDepth = 3,
  className,
  showAddForm = true,
}: CommentThreadProps) {
  const { t } = useTranslation(['collaboration', 'common']);

  // Collaboration store
  const comments = useCollaborationStore((state) => state.getComments(specId));
  const addComment = useCollaborationStore((state) => state.addComment);
  const updateComment = useCollaborationStore((state) => state.updateComment);
  const resolveComment = useCollaborationStore((state) => state.resolveComment);

  // Local state
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [replyToId, setReplyToId] = useState<string | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const [collapsedReplies, setCollapsedReplies] = useState<Set<string>>(new Set());

  // Refs
  const collaborationAPI = useMemo(() => createCollaborationAPI(), []);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const replyTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Filter comments for this section (or general comments if sectionId is null)
  const sectionComments = useMemo(() => {
    return comments.filter((c) => c.section_id === sectionId);
  }, [comments, sectionId]);

  // Get top-level comments (no parent)
  const topLevelComments = useMemo(() => {
    return sectionComments.filter((c) => c.parent_id === null);
  }, [sectionComments]);

  // Check if a comment has replies
  const commentHasReplies = useCallback(
    (commentId: string): boolean => {
      return sectionComments.some((c) => c.parent_id === commentId);
    },
    [sectionComments]
  );

  // Toggle replies visibility
  const toggleReplies = useCallback((commentId: string) => {
    setCollapsedReplies((prev) => {
      const next = new Set(prev);
      if (next.has(commentId)) {
        next.delete(commentId);
      } else {
        next.add(commentId);
      }
      return next;
    });
  }, []);

  // Check if replies are shown
  const areRepliesShown = useCallback(
    (commentId: string): boolean => {
      // If collapsed, hide replies
      // Otherwise, show replies if not at max depth or if explicitly shown
      return !collapsedReplies.has(commentId);
    },
    [collapsedReplies]
  );

  // Submit new comment
  const submitComment = useCallback(
    async (content: string, parentId: string | null) => {
      if (!content.trim() || isPosting) {
        return;
      }

      setIsPosting(true);
      setError(null);

      try {
        const result = await collaborationAPI.addComment(
          specId,
          content.trim(),
          sectionId,
          parentId,
          currentUserId,
          currentUserName
        );

        if (result.success && result.data) {
          // Add to store
          addComment(specId, result.data);

          // Clear form
          if (parentId === null) {
            setNewComment('');
          } else {
            setReplyContent('');
            setReplyToId(null);
          }
        } else {
          setError(result.error || t('collaboration:errors.addCommentFailed'));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:errors.unknown'));
      } finally {
        setIsPosting(false);
      }
    },
    [
      specId,
      sectionId,
      currentUserId,
      currentUserName,
      isPosting,
      collaborationAPI,
      addComment,
      t,
    ]
  );

  // Handle reply submission
  const handleReplySubmit = useCallback(
    (commentId: string, content: string) => {
      submitComment(content, commentId);
    },
    [submitComment]
  );

  // Handle comment resolve toggle
  const handleResolveToggle = useCallback(
    async (commentId: string) => {
      const comment = sectionComments.find((c) => c.id === commentId);
      if (!comment) return;

      const isResolved = comment.status === 'resolved';

      try {
        if (isResolved) {
          // Reopen - update locally and via API
          updateComment(specId, commentId, {
            status: 'active' as CommentStatus,
            resolved_by: null,
            resolved_at: null,
          });
          await collaborationAPI.updateComment(specId, commentId, {
            status: 'active',
          });
        } else {
          // Resolve - update locally and via API
          resolveComment(specId, commentId, currentUserId);
          await collaborationAPI.resolveComment(specId, commentId);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:errors.unknown'));
      }
    },
    [
      sectionComments,
      specId,
      currentUserId,
      updateComment,
      resolveComment,
      collaborationAPI,
      t,
    ]
  );

  // Focus textarea when reply starts
  useEffect(() => {
    if (replyToId && replyTextareaRef.current) {
      replyTextareaRef.current.focus();
    }
  }, [replyToId]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>, isReply = false) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (isReply && replyToId) {
          handleReplySubmit(replyToId, replyContent);
        } else {
          submitComment(newComment, null);
        }
      } else if (e.key === 'Escape') {
        if (isReply) {
          setReplyToId(null);
          setReplyContent('');
        } else {
          setNewComment('');
        }
      }
    },
    [
      newComment,
      replyContent,
      replyToId,
      submitComment,
      handleReplySubmit,
    ]
  );

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Error display */}
      {error && (
        <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3 flex items-start gap-2">
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

      {/* Top-level comments */}
      {topLevelComments.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">{t('collaboration:comments.noComments')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {topLevelComments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              allComments={sectionComments}
              currentUserId={currentUserId}
              depth={0}
              maxDepth={maxDepth}
              showReplies={areRepliesShown(comment.id)}
              onToggleReplies={toggleReplies}
              onReply={(commentId) => setReplyToId(commentId)}
              onResolve={handleResolveToggle}
            />
          ))}
        </div>
      )}

      {/* Reply form (when replying to a comment) */}
      {replyToId && (
        <div className="ml-8 mt-3">
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">
                {t('collaboration:comments.replyingTo')}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => {
                  setReplyToId(null);
                  setReplyContent('');
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <Textarea
              ref={replyTextareaRef}
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, true)}
              placeholder={t('collaboration:comments.replyPlaceholder')}
              className="min-h-[80px] mb-2"
              disabled={isPosting}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Ctrl+Enter to submit
              </span>
              <Button
                size="sm"
                onClick={() => handleReplySubmit(replyToId, replyContent)}
                disabled={isPosting || !replyContent.trim()}
              >
                {isPosting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {t('collaboration:comments.posting')}
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    {t('collaboration:comments.submitReply')}
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add new comment form */}
      {showAddForm && !replyToId && (
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="h-5 w-5 text-primary" />
            <span className="font-medium">
              {t('collaboration:comments.addComment')}
            </span>
          </div>
          <Textarea
            ref={textareaRef}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={(e) => handleKeyDown(e, false)}
            placeholder={t('collaboration:comments.newCommentPlaceholder')}
            className="min-h-[100px] mb-3"
            disabled={isPosting}
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {t('collaboration:comments.keyboardHint')}
            </span>
            <Button
              onClick={() => submitComment(newComment, null)}
              disabled={isPosting || !newComment.trim()}
            >
              {isPosting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t('collaboration:comments.posting')}
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  {t('collaboration:comments.submit')}
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
