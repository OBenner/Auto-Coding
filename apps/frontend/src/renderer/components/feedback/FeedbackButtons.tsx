import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ThumbsUp, ThumbsDown, Edit2, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';
import { useToast } from '../../hooks/use-toast';

export type FeedbackType = 'accepted' | 'rejected' | 'modified';

interface FeedbackButtonsProps {
  /** Task ID for feedback context */
  taskId?: string;
  /** Agent type that produced the output */
  agentType?: string;
  /** Description of what was produced (e.g., "spec", "code implementation") */
  outputDescription?: string;
  /** Additional context for the feedback */
  context?: string;
  /** Callback when feedback is submitted */
  onFeedbackSubmit?: (feedbackType: FeedbackType) => void;
  /** Optional custom class name */
  className?: string;
  /** Size variant for buttons */
  size?: 'sm' | 'default' | 'lg';
  /** Show labels alongside icons */
  showLabels?: boolean;
}

/**
 * FeedbackButtons component - Allows users to provide feedback on agent outputs
 *
 * This component displays three feedback buttons:
 * - Accept (thumbs up): User accepts the agent output as-is
 * - Reject (thumbs down): User rejects the agent output
 * - Modified (edit): User accepted but made modifications
 *
 * Feedback is recorded via IPC to the backend for adaptive learning.
 */
export function FeedbackButtons({
  taskId,
  agentType = 'unknown',
  outputDescription = 'agent output',
  context,
  onFeedbackSubmit,
  className,
  size = 'sm',
  showLabels = false
}: FeedbackButtonsProps) {
  const { t } = useTranslation(['common']);
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackType | null>(null);

  const handleFeedback = async (feedbackType: FeedbackType) => {
    if (isSubmitting) return;

    setIsSubmitting(true);
    setSelectedFeedback(feedbackType);

    try {
      // Submit feedback via IPC (handler will be implemented in subtask-5-2)
      if (window.electronAPI?.submitFeedback) {
        const result = await window.electronAPI.submitFeedback({
          feedbackType,
          taskId,
          agentType,
          taskDescription: outputDescription,
          context: context || ''
        });

        if (result.success) {
          toast({
            title: t('common:labels.success'),
            description: t('common:feedback.submitted'),
            variant: 'default'
          });

          // Trigger callback if provided
          onFeedbackSubmit?.(feedbackType);
        } else {
          throw new Error(result.error || 'Failed to submit feedback');
        }
      } else {
        // Gracefully handle when IPC handler is not yet implemented
        toast({
          title: t('common:feedback.notAvailable'),
          description: t('common:feedback.notAvailableDescription'),
          variant: 'default'
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast({
        title: t('common:labels.error'),
        description: t('common:feedback.submitError', { error: errorMessage }),
        variant: 'destructive'
      });
    } finally {
      setIsSubmitting(false);
      // Clear selection after a delay for visual feedback
      setTimeout(() => setSelectedFeedback(null), 1000);
    }
  };

  return (
    <div className={cn('flex items-center gap-2', className)} role="group" aria-label="Agent output feedback">
      <Button
        variant={selectedFeedback === 'accepted' ? 'success' : 'ghost'}
        size={size}
        onClick={() => handleFeedback('accepted')}
        disabled={isSubmitting}
        className={cn(
          'transition-all',
          selectedFeedback === 'accepted' && 'scale-105'
        )}
        title={t('common:feedback.acceptTooltip')}
        aria-label={t('common:feedback.accept')}
      >
        {isSubmitting && selectedFeedback === 'accepted' ? (
          <Loader2 className={cn('animate-spin', showLabels && 'mr-2')} size={16} />
        ) : (
          <ThumbsUp className={cn(showLabels && 'mr-2')} size={16} />
        )}
        {showLabels && t('common:feedback.accept')}
      </Button>

      <Button
        variant={selectedFeedback === 'rejected' ? 'destructive' : 'ghost'}
        size={size}
        onClick={() => handleFeedback('rejected')}
        disabled={isSubmitting}
        className={cn(
          'transition-all',
          selectedFeedback === 'rejected' && 'scale-105'
        )}
        title={t('common:feedback.rejectTooltip')}
        aria-label={t('common:feedback.reject')}
      >
        {isSubmitting && selectedFeedback === 'rejected' ? (
          <Loader2 className={cn('animate-spin', showLabels && 'mr-2')} size={16} />
        ) : (
          <ThumbsDown className={cn(showLabels && 'mr-2')} size={16} />
        )}
        {showLabels && t('common:feedback.reject')}
      </Button>

      <Button
        variant={selectedFeedback === 'modified' ? 'warning' : 'ghost'}
        size={size}
        onClick={() => handleFeedback('modified')}
        disabled={isSubmitting}
        className={cn(
          'transition-all',
          selectedFeedback === 'modified' && 'scale-105'
        )}
        title={t('common:feedback.modifiedTooltip')}
        aria-label={t('common:feedback.modified')}
      >
        {isSubmitting && selectedFeedback === 'modified' ? (
          <Loader2 className={cn('animate-spin', showLabels && 'mr-2')} size={16} />
        ) : (
          <Edit2 className={cn(showLabels && 'mr-2')} size={16} />
        )}
        {showLabels && t('common:feedback.modified')}
      </Button>
    </div>
  );
}
