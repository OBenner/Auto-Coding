/**
 * CommentThread - Discussion Thread for Spec Collaboration
 *
 * Displays and manages threaded comments on specs with @mention support.
 * Users can comment, reply, resolve threads, and mention team members.
 *
 * Features:
 * - Threaded comment display with nested replies
 * - @mention autocomplete for team members
 * - Comment resolution to close threads
 * - Real-time comment updates
 * - Visual indicators for mentions and resolved comments
 *
 * @example
 * ```tsx
 * <CommentThread
 *   specId="001-feature"
 *   onCommentAdded={(comment) => console.log('Added:', comment)}
 *   onCommentResolved={(commentId) => console.log('Resolved:', commentId)}
 * />
 * ```
 */
import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MessageSquare,
  MessageCircle,
  Reply,
  CheckCircle2,
  XCircle,
  Send,
  User,
  Loader2,
  AtSign,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import { cn } from '../../lib/utils';
import type { Comment, CollaborationUser } from '../../../shared/types';
import {
  CollaborationLoadingState,
  CollaborationErrorState,
  CollaborationSectionHeader,
  CollaborationEmptyState,
  formatTimestamp,
} from './shared';

/**
 * Props for CommentThread
 */
interface CommentThreadProps {
  /** Spec ID to load comments for */
  specId: string;
  /** Callback when a comment is added */
  onCommentAdded?: (comment: Comment) => void;
  /** Callback when a comment is updated */
  onCommentUpdated?: (comment: Comment) => void;
  /** Callback when a comment is deleted */
  onCommentDeleted?: (commentId: string) => void;
  /** Callback when a comment is resolved */
  onCommentResolved?: (commentId: string) => void;
  /** Callback when a reply is added */
  onReplyAdded?: (comment: Comment, parentId: string) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Mention suggestion for autocomplete
 */
interface MentionSuggestion {
  user: CollaborationUser;
  start: number;
  end: number;
}

/**
 * Comment with reply hierarchy
 */
interface CommentWithReplies extends Comment {
  replies?: CommentWithReplies[];
}

/**
 * Highlight @mentions in text
 */
function highlightMentions(text: string): React.ReactNode {
  const mentionRegex = /@(\w+)/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionRegex.exec(text)) !== null) {
    // Add text before mention
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    // Add highlighted mention
    parts.push(
      <span key={match.index} className="font-medium text-primary">
        {match[0]}
      </span>
    );

    lastIndex = mentionRegex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
}

/**
 * Comment Input Component with @mention support
 */
function CommentInput({
  value,
  onChange,
  onSubmit,
  placeholder,
  onCancel,
  submitLabel,
  isLoading = false,
  disabled = false,
  autoFocus = false,
  t
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  onCancel?: () => void;
  submitLabel?: string;
  isLoading?: boolean;
  disabled?: boolean;
  autoFocus?: boolean;
  t: (key: string, params?: any) => string;
}) {
  const [mentionSuggestions, setMentionSuggestions] = useState<MentionSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // TODO: Replace with actual user list from spec permissions
  // For now, use placeholder users
  const availableUsers: CollaborationUser[] = [];

  // Detect @mentions and show suggestions
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    onChange(newValue);

    // Check if we're typing a mention
    const cursorPosition = e.target.selectionStart;
    const textBeforeCursor = newValue.slice(0, cursorPosition);
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);

    if (mentionMatch && availableUsers.length > 0) {
      const searchTerm = mentionMatch[1].toLowerCase();
      const matchingUsers = availableUsers.filter(user =>
        user.username.toLowerCase().includes(searchTerm)
      );

      const suggestions: MentionSuggestion[] = matchingUsers.map(user => ({
        user,
        start: cursorPosition - mentionMatch[0].length,
        end: cursorPosition
      }));

      setMentionSuggestions(suggestions);
      setShowSuggestions(suggestions.length > 0);
      setSelectedSuggestionIndex(0);
    } else {
      setShowSuggestions(false);
      setMentionSuggestions([]);
    }
  };

  // Insert selected mention
  const insertMention = (suggestion: MentionSuggestion) => {
    const beforeMention = value.slice(0, suggestion.start);
    const afterMention = value.slice(suggestion.end);
    const mentionText = `@${suggestion.user.username} `;
    const newValue = beforeMention + mentionText + afterMention;
    onChange(newValue);
    setShowSuggestions(false);

    // Focus textarea after mention
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  };

  // Handle keyboard navigation in suggestions
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSuggestions && mentionSuggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedSuggestionIndex(prev =>
          prev < mentionSuggestions.length - 1 ? prev + 1 : 0
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedSuggestionIndex(prev =>
          prev > 0 ? prev - 1 : mentionSuggestions.length - 1
        );
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        insertMention(mentionSuggestions[selectedSuggestionIndex]);
      } else if (e.key === 'Escape') {
        setShowSuggestions(false);
      }
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="relative">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="min-h-[80px] pr-10"
        disabled={disabled || isLoading}
        autoFocus={autoFocus}
      />
      {/* Mention Suggestions Dropdown */}
      {showSuggestions && mentionSuggestions.length > 0 && (
        <Card className="absolute z-10 mt-1 max-h-60 overflow-auto">
          <CardContent className="p-0">
            {mentionSuggestions.map((suggestion, index) => (
              <button
                key={suggestion.user.user_id}
                type="button"
                onClick={() => insertMention(suggestion)}
                className={cn(
                  'w-full px-3 py-2 text-left text-sm hover:bg-muted flex items-center gap-2',
                  index === selectedSuggestionIndex && 'bg-muted'
                )}
              >
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{suggestion.user.username}</span>
                {suggestion.user.email && (
                  <span className="text-xs text-muted-foreground">
                    ({suggestion.user.email})
                  </span>
                )}
              </button>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between mt-2">
        {onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={isLoading}>
            {t('collaboration:comments.cancel')}
          </Button>
        )}
        <div className={cn('flex items-center gap-2', onCancel && 'ml-auto')}>
          <span className="text-xs text-muted-foreground">
            {t('collaboration:comments.pressEnter')}
          </span>
          <Button
            size="sm"
            onClick={onSubmit}
            disabled={disabled || isLoading || !value.trim()}
            className="gap-1"
          >
            {isLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Send className="h-3 w-3" />
            )}
            {submitLabel || t('collaboration:comments.send')}
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Single Comment Display Component
 */
function CommentItem({
  comment,
  depth = 0,
  onReply,
  onResolve,
  onEdit,
  onDelete,
  isReplying,
  onReplySubmit,
  onReplyCancel,
  t
}: {
  comment: CommentWithReplies;
  depth?: number;
  onReply?: (commentId: string) => void;
  onResolve?: (commentId: string) => void;
  onEdit?: (commentId: string) => void;
  onDelete?: (commentId: string) => void;
  isReplying?: boolean;
  onReplySubmit?: (content: string) => void;
  onReplyCancel?: () => void;
  t: (key: string, params?: any) => string;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [replyText, setReplyText] = useState('');
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);

  const hasReplies = comment.replies && comment.replies.length > 0;
  const isRoot = depth === 0;

  const handleReplySubmit = async () => {
    if (!replyText.trim()) return;

    setIsSubmittingReply(true);
    try {
      await onReplySubmit?.(replyText);
      setReplyText('');
    } finally {
      setIsSubmittingReply(false);
    }
  };

  return (
    <div className={cn(depth > 0 && 'ml-8 border-l-2 border-muted pl-4')}>
      <Card
        className={cn(
          'transition-all',
          comment.resolved && 'opacity-60 bg-muted/30',
          depth > 0 && 'border-border/50'
        )}
      >
        <CardContent className="p-4">
          {/* Comment Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 flex-1">
              {/* User Avatar */}
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <User className="h-4 w-4 text-primary" />
              </div>

              {/* User Info & Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm text-foreground">
                    {comment.author.username}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatTimestamp(comment.created_at, t)}
                  </span>
                  {comment.resolved && (
                    <Badge variant="outline" className="gap-1 text-xs bg-success/10 text-success border-success/20">
                      <CheckCircle2 className="h-3 w-3" />
                      {t('collaboration:comments.resolved')}
                    </Badge>
                  )}
                  {comment.mentions && comment.mentions.length > 0 && (
                    <Badge variant="outline" className="gap-1 text-xs bg-info/10 text-info border-info/20">
                      <AtSign className="h-3 w-3" />
                      {comment.mentions.length}
                    </Badge>
                  )}
                </div>

                {/* Comment Content */}
                <div className="mt-2 text-sm text-foreground leading-relaxed">
                  {highlightMentions(comment.content)}
                </div>

                {/* Reply Preview */}
                {hasReplies && !isExpanded && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsExpanded(true)}
                    className="mt-2 h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                  >
                    <ChevronDown className="h-3 w-3 mr-1" />
                    {t('collaboration:comments.expandReplies', {
                      count: comment.replies!.length,
                      type: comment.replies!.length === 1 ? t('collaboration:comments.reply') : t('collaboration:comments.replies')
                    })}
                  </Button>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            {!comment.resolved && isRoot && (
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onReply?.(comment.comment_id)}
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                  title="Reply"
                >
                  <Reply className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onResolve?.(comment.comment_id)}
                  className="h-8 w-8 p-0 text-success hover:bg-success/10 hover:text-success"
                  title="Resolve thread"
                >
                  <CheckCircle2 className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Reply Input */}
          {isReplying && (
            <div className="mt-4 pt-4 border-t border-border">
              <CommentInput
                value={replyText}
                onChange={setReplyText}
                onSubmit={handleReplySubmit}
                onCancel={onReplyCancel}
                placeholder={t('collaboration:comments.writeReply')}
                submitLabel={t('collaboration:comments.reply')}
                isLoading={isSubmittingReply}
                t={t}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Nested Replies */}
      {hasReplies && isExpanded && (
        <div className="mt-3 space-y-3">
          {comment.replies!.map(reply => (
            <CommentItem
              key={reply.comment_id}
              comment={reply}
              depth={depth + 1}
              onReply={onReply}
              onResolve={onResolve}
              onEdit={onEdit}
              onDelete={onDelete}
              t={t}
            />
          ))}
          {comment.replies!.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(false)}
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
            >
              <ChevronUp className="h-3 w-3 mr-1" />
              {t('collaboration:comments.collapseReplies')}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * CommentThread Component
 */
export function CommentThread({
  specId,
  onCommentAdded,
  onCommentUpdated,
  onCommentDeleted,
  onCommentResolved,
  onReplyAdded,
  className
}: CommentThreadProps) {
  const [comments, setComments] = useState<CommentWithReplies[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newCommentText, setNewCommentText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [replyingToId, setReplyingToId] = useState<string | null>(null);
  const { t } = useTranslation(['collaboration', 'common']);

  // Load comments when component mounts
  useEffect(() => {
    loadComments();
  }, [specId]);

  const loadComments = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call once handler is implemented
      // const result = await window.electronAPI.collaboration.comments.get(specId);
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to load comments');
      // }
      // const loadedComments = result.data || [];
      // setComments(buildCommentTree(loadedComments));

      // Placeholder: Empty comments until IPC handler is implemented
      setComments([]);
    } catch (err) {
      console.error('Failed to load comments:', err);
      setError(err instanceof Error ? err.message : 'Failed to load comments');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Build comment tree from flat comment list
   */
  const buildCommentTree = (flatComments: Comment[]): CommentWithReplies[] => {
    const commentMap = new Map<string, CommentWithReplies>();
    const rootComments: CommentWithReplies[] = [];

    // First pass: create map
    flatComments.forEach(comment => {
      commentMap.set(comment.comment_id, { ...comment, replies: [] });
    });

    // Second pass: build tree
    flatComments.forEach(comment => {
      const commentWithReplies = commentMap.get(comment.comment_id)!;
      if (comment.parent_id) {
        const parent = commentMap.get(comment.parent_id);
        if (parent) {
          if (!parent.replies) parent.replies = [];
          parent.replies.push(commentWithReplies);
        }
      } else {
        rootComments.push(commentWithReplies);
      }
    });

    return rootComments;
  };

  const handleAddComment = async () => {
    if (!newCommentText.trim()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaboration.comments.create({
      //   spec_id: specId,
      //   content: newCommentText
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to add comment');
      // }
      // onCommentAdded?.(result.data);
      // await loadComments();

      // Placeholder: Just clear input for now
      setNewCommentText('');
    } catch (err) {
      console.error('Failed to add comment:', err);
      setError(err instanceof Error ? err.message : 'Failed to add comment');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResolveComment = async (_commentId: string) => {
    setError(null);
    // TODO: Replace with actual IPC call
    // const result = await window.electronAPI.collaboration.comments.resolve(commentId);
    // if (!result.success) {
    //   throw new Error(result.error || 'Failed to resolve comment');
    // }
    // onCommentResolved?.(commentId);
    // await loadComments();
  };

  const handleReply = (commentId: string) => {
    setReplyingToId(commentId);
  };

  const handleReplyCancel = () => {
    setReplyingToId(null);
  };

  const handleReplySubmit = async (content: string) => {
    if (!content.trim() || !replyingToId) return;

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaboration.comments.reply({
      //   parent_id: replyingToId,
      //   content
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to add reply');
      // }
      // onReplyAdded?.(result.data, replyingToId);
      // await loadComments();

      setReplyingToId(null);
    } catch (err) {
      console.error('Failed to add reply:', err);
      setError(err instanceof Error ? err.message : 'Failed to add reply');
    }
  };

  // Calculate stats
  const totalComments = comments.reduce((acc, c) => {
    const replyCount = c.replies?.length || 0;
    return acc + 1 + replyCount;
  }, 0);
  const resolvedCount = comments.filter(c => c.resolved).length;

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <CollaborationSectionHeader
        icon={<MessageSquare className="h-5 w-5 text-primary" />}
        title={t('collaboration:comments.title')}
        description={t('collaboration:comments.description')}
        badge={comments.length > 0 ? (
          <div className="flex items-center gap-2 text-xs">
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
              {totalComments} {totalComments === 1 ? t('collaboration:comments.comment') : t('collaboration:comments.comments')}
            </Badge>
            {resolvedCount > 0 && (
              <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                {t('collaboration:comments.resolvedBadge', { count: resolvedCount })}
              </Badge>
            )}
          </div>
        ) : undefined}
      />

      {/* Loading State */}
      {isLoading && (
        <CollaborationLoadingState message={t('collaboration:comments.loading')} />
      )}

      {/* Error State */}
      {error && (
        <CollaborationErrorState title={t('collaboration:common.error')} detail={error} />
      )}

      {/* New Comment Input */}
      {!isLoading && (
        <Card>
          <CardContent className="p-4">
            <CommentInput
              value={newCommentText}
              onChange={setNewCommentText}
              onSubmit={handleAddComment}
              placeholder={t('collaboration:comments.addComment')}
              submitLabel={t('collaboration:comments.send')}
              isLoading={isSubmitting}
              t={t}
            />
          </CardContent>
        </Card>
      )}

      {/* Comments List */}
      {!isLoading && !error && comments.length > 0 && (
        <div className="space-y-4">
          {comments.map(comment => (
            <CommentItem
              key={comment.comment_id}
              comment={comment}
              onReply={handleReply}
              onResolve={handleResolveComment}
              isReplying={replyingToId === comment.comment_id}
              onReplySubmit={handleReplySubmit}
              onReplyCancel={handleReplyCancel}
              t={t}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && comments.length === 0 && (
        <CollaborationEmptyState
          icon={<MessageCircle className="h-12 w-12 opacity-20" />}
          title={t('collaboration:comments.noComments')}
          subtitle={t('collaboration:comments.startDiscussion')}
        />
      )}
    </div>
  );
}
