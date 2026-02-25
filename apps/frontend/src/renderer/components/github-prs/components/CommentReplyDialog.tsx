/**
 * CommentReplyDialog - Dialog for replying to inline review comments
 */

import { useState } from 'react';
import { MessageSquare, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Textarea } from '../../ui/textarea';
import type { InlineComment } from './InlineCommentList';

interface CommentReplyDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** The comment being replied to */
  comment: InlineComment | null;
  /** Callback when the dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when reply is submitted */
  onReply: (commentId: number, body: string) => Promise<void>;
}

/**
 * CommentReplyDialog Component
 * Dialog for composing and sending replies to inline review comments
 */
export function CommentReplyDialog({
  open,
  comment,
  onOpenChange,
  onReply,
}: CommentReplyDialogProps) {
  const { t } = useTranslation('common');
  const [replyBody, setReplyBody] = useState('');
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when dialog opens/closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setReplyBody('');
      setError(null);
    }
    onOpenChange(newOpen);
  };

  // Handle reply submission
  const handleSend = async () => {
    if (!comment || !replyBody.trim()) {
      return;
    }

    setIsPosting(true);
    setError(null);

    try {
      await onReply(comment.id, replyBody.trim());
      // Success - close dialog and reset state
      setReplyBody('');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('inlineComments.postFailed'));
    } finally {
      setIsPosting(false);
    }
  };

  // Handle Enter key (Ctrl+Enter to send)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const isValid = replyBody.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            {t('inlineComments.reply')}
          </DialogTitle>
          <DialogDescription>
            {comment && (
              <span>
                {t('inlineComments.accessibility.commentByAuthor', {
                  author: comment.user.login,
                  defaultValue: `Replying to ${comment.user.login}'s comment`,
                })}
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Original comment preview */}
        {comment && (
          <div className="rounded-lg border bg-muted/50 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{comment.user.login}</span>
              {comment.line && (
                <span className="text-xs text-muted-foreground">Line {comment.line}</span>
              )}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-wrap break-words">
              {comment.body}
            </p>
          </div>
        )}

        {/* Reply textarea */}
        <div className="space-y-2">
          <Textarea
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('inlineComments.replyPlaceholder')}
            className="min-h-[120px]"
            disabled={isPosting}
            autoFocus
          />
        </div>

        {/* Error message */}
        {error && (
          <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
            {error}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isPosting}>
            {t('inlineComments.cancel')}
          </Button>
          <Button onClick={handleSend} disabled={isPosting || !isValid}>
            {isPosting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('inlineComments.posting')}
              </>
            ) : (
              <>
                <MessageSquare className="mr-2 h-4 w-4" />
                {t('inlineComments.submit')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
