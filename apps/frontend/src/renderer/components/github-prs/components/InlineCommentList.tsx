/**
 * InlineCommentList - Display inline code review comments grouped by file
 */

import { MessageSquare, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { cn } from '../../../lib/utils';
import { CollapsibleCard } from './CollapsibleCard';

/**
 * Inline comment from GitHub PR review
 */
export interface InlineComment {
  id: number;
  user: { login: string };
  body: string;
  path: string;
  position?: number;
  line?: number;
  commit_id: string;
  created_at: string;
  updated_at: string;
  in_reply_to_id?: number;
}

interface InlineCommentListProps {
  comments: InlineComment[];
  onReply?: (comment: InlineComment) => void;
  onApplySuggestion?: (comment: InlineComment) => void;
}

/**
 * Extract suggested changes from GitHub's suggestion syntax
 * ```suggestion
 * new code here
 * ```
 */
function extractSuggestion(body: string): string | null {
  const suggestionMatch = body.match(/```suggestion\s*\n([\s\S]*?)\n```/);
  return suggestionMatch ? suggestionMatch[1] : null;
}

/**
 * Group comments by file path
 */
function groupCommentsByFile(comments: InlineComment[]): Map<string, InlineComment[]> {
  const grouped = new Map<string, InlineComment[]>();

  for (const comment of comments) {
    const existing = grouped.get(comment.path) || [];
    existing.push(comment);
    grouped.set(comment.path, existing);
  }

  // Sort comments within each file by line number
  for (const [path, fileComments] of grouped.entries()) {
    fileComments.sort((a, b) => {
      const lineA = a.line || 0;
      const lineB = b.line || 0;
      return lineA - lineB;
    });
  }

  return grouped;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
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
 * Individual comment display
 */
function CommentItem({
  comment,
  onReply,
  onApplySuggestion,
}: {
  comment: InlineComment;
  onReply?: (comment: InlineComment) => void;
  onApplySuggestion?: (comment: InlineComment) => void;
}) {
  const { t } = useTranslation('common');
  const suggestion = extractSuggestion(comment.body);
  const hasReplyHandler = !!onReply;
  const hasApplySuggestionHandler = !!onApplySuggestion;

  return (
    <div className="border-b last:border-b-0 p-3 space-y-2">
      {/* Comment Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <User className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="font-medium text-sm truncate">{comment.user.login}</span>
          <span className="text-xs text-muted-foreground shrink-0">
            {formatTimestamp(comment.created_at)}
          </span>
        </div>
        {comment.line && (
          <Badge variant="outline" className="text-xs shrink-0">
            Line {comment.line}
          </Badge>
        )}
      </div>

      {/* Comment Body */}
      <div className="text-sm text-muted-foreground whitespace-pre-wrap break-words">
        {comment.body}
      </div>

      {/* Suggested Fix (if present) */}
      {suggestion && (
        <div className="mt-2">
          <span className="text-xs text-muted-foreground font-medium">
            {t('inlineComments.suggestedChange', { defaultValue: 'Suggested change:' })}
          </span>
          <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto max-w-full whitespace-pre-wrap break-words">
            {suggestion}
          </pre>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 pt-1">
        {hasReplyHandler && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onReply(comment)}
            className="h-7 text-xs"
          >
            <MessageSquare className="h-3 w-3 mr-1" />
            {t('inlineComments.reply')}
          </Button>
        )}
        {suggestion && hasApplySuggestionHandler && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onApplySuggestion(comment)}
            className="h-7 text-xs"
          >
            {t('inlineComments.applySuggestion', { defaultValue: 'Apply Suggestion' })}
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * InlineCommentList Component
 * Displays inline review comments grouped by file
 */
export function InlineCommentList({
  comments,
  onReply,
  onApplySuggestion,
}: InlineCommentListProps) {
  const { t } = useTranslation('common');

  if (comments.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">{t('inlineComments.noComments')}</p>
      </div>
    );
  }

  const groupedComments = groupCommentsByFile(comments);

  return (
    <div className="space-y-3">
      {Array.from(groupedComments.entries()).map(([path, fileComments]) => {
        const commentCount = fileComments.length;

        return (
          <CollapsibleCard
            key={path}
            title={path}
            icon={<MessageSquare className="h-4 w-4 text-muted-foreground" />}
            badge={
              <Badge variant="secondary" className="text-xs">
                {t('inlineComments.commentCount', { count: commentCount })}
              </Badge>
            }
            defaultOpen={true}
          >
            <div className="bg-background">
              {fileComments.map((comment) => (
                <CommentItem
                  key={comment.id}
                  comment={comment}
                  onReply={onReply}
                  onApplySuggestion={onApplySuggestion}
                />
              ))}
            </div>
          </CollapsibleCard>
        );
      })}
    </div>
  );
}
