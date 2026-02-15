import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { cn } from '../lib/utils';

export type FeedbackRating = 'positive' | 'negative' | null;

interface FeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit?: (rating: FeedbackRating, comment: string) => Promise<void> | void;
  title?: string;
  description?: string;
}

/**
 * Dialog for collecting user feedback on agent outputs
 * Shows thumbs up/down rating and optional comment field
 */
export function FeedbackDialog({
  open,
  onOpenChange,
  onSubmit,
  title,
  description
}: FeedbackDialogProps) {
  const { t } = useTranslation(['common', 'dialogs']);

  const [rating, setRating] = useState<FeedbackRating>(null);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!rating) return;

    setIsSubmitting(true);
    try {
      await onSubmit?.(rating, comment);

      // Reset form on successful submission
      setRating(null);
      setComment('');
      onOpenChange(false);
    } catch (error) {
      console.error('[FeedbackDialog] Submission error:', error);
      // Re-throw so parent can handle (e.g., show toast notification)
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (isSubmitting) return;

    // Reset form state when closing
    setRating(null);
    setComment('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {title || t('common:feedback.dialogTitle', 'Rate Agent Output')}
          </DialogTitle>
          <DialogDescription>
            {description || t('common:feedback.dialogDescription', 'Help us improve by rating the quality of the agent\'s work.')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Rating Selection */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground">
              {t('common:feedback.ratingLabel', 'How would you rate this output?')}
            </label>
            <div className="flex gap-3 justify-center">
              <Button
                type="button"
                variant={rating === 'positive' ? 'default' : 'outline'}
                size="lg"
                onClick={() => setRating('positive')}
                disabled={isSubmitting}
                className={cn(
                  'flex-1 h-20 flex-col gap-2',
                  rating === 'positive' && 'bg-green-600 hover:bg-green-700 border-green-600'
                )}
              >
                <ThumbsUp className="h-6 w-6" />
                <span>{t('common:feedback.positive', 'Good')}</span>
              </Button>
              <Button
                type="button"
                variant={rating === 'negative' ? 'default' : 'outline'}
                size="lg"
                onClick={() => setRating('negative')}
                disabled={isSubmitting}
                className={cn(
                  'flex-1 h-20 flex-col gap-2',
                  rating === 'negative' && 'bg-red-600 hover:bg-red-700 border-red-600'
                )}
              >
                <ThumbsDown className="h-6 w-6" />
                <span>{t('common:feedback.negative', 'Needs Work')}</span>
              </Button>
            </div>
          </div>

          {/* Comment Field */}
          <div className="space-y-3">
            <label htmlFor="feedback-comment" className="text-sm font-medium text-foreground">
              {t('common:feedback.commentLabel', 'Additional comments')}
              <span className="text-muted-foreground ml-2">
                ({t('common:labels.optional', 'Optional')})
              </span>
            </label>
            <Textarea
              id="feedback-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t('common:feedback.commentPlaceholder', 'Tell us what could be improved...')}
              disabled={isSubmitting}
              className="min-h-[100px] resize-none"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            {t('common:buttons.cancel', 'Cancel')}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!rating || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('common:feedback.submitting', 'Submitting...')}
              </>
            ) : (
              t('common:feedback.submit', 'Submit Feedback')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
