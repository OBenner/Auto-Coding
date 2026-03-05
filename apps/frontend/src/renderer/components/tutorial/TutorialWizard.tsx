import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { GraduationCap } from 'lucide-react';
import {
  FullScreenDialog,
  FullScreenDialogContent,
  FullScreenDialogHeader,
  FullScreenDialogBody,
  FullScreenDialogTitle,
  FullScreenDialogDescription
} from '../ui/full-screen-dialog';
import { ScrollArea } from '../ui/scroll-area';
import { WizardProgress, WizardStep } from '../onboarding/WizardProgress';
import { Button } from '../ui/button';

interface TutorialWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}

// Tutorial step identifiers
type TutorialStepId = 'intro' | 'spec_phase' | 'planning_phase' | 'coding_phase' | 'qa_phase' | 'completion';

// Step configuration with translation keys
const TUTORIAL_STEPS: { id: TutorialStepId; labelKey: string }[] = [
  { id: 'intro', labelKey: 'steps.intro' },
  { id: 'spec_phase', labelKey: 'steps.specPhase' },
  { id: 'planning_phase', labelKey: 'steps.planningPhase' },
  { id: 'coding_phase', labelKey: 'steps.codingPhase' },
  { id: 'qa_phase', labelKey: 'steps.qaPhase' },
  { id: 'completion', labelKey: 'steps.completion' }
];

/**
 * Main tutorial wizard component.
 * Provides a full-screen, multi-step guided tutorial experience that walks
 * users through their first autonomous build, explaining each phase
 * (spec creation, planning, coding, QA) with real-time feedback.
 *
 * Features:
 * - Step progress indicator
 * - Navigation between steps (next, back)
 * - Real-time phase explanations
 * - Expandable "Explain more" sections
 * - Completion with mergeable branch
 */
export function TutorialWizard({
  open,
  onOpenChange,
  onComplete
}: TutorialWizardProps) {
  const { t } = useTranslation('tutorial');
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<TutorialStepId>>(new Set());

  // Get current step ID
  const currentStepId = TUTORIAL_STEPS[currentStepIndex].id;

  // Build step data for progress indicator
  const steps: WizardStep[] = TUTORIAL_STEPS.map((step, index) => ({
    id: step.id,
    label: t(step.labelKey, { defaultValue: step.id }),
    completed: completedSteps.has(step.id) || index < currentStepIndex
  }));

  // Navigation handlers
  const goToNextStep = useCallback(() => {
    // Mark current step as completed
    setCompletedSteps(prev => new Set(prev).add(currentStepId));

    if (currentStepIndex < TUTORIAL_STEPS.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  }, [currentStepIndex, currentStepId]);

  const goToPreviousStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  }, [currentStepIndex]);

  // Reset tutorial state
  const resetTutorial = useCallback(() => {
    setCurrentStepIndex(0);
    setCompletedSteps(new Set());
  }, []);

  const completeTutorial = useCallback(() => {
    if (onComplete) {
      onComplete();
    }
    onOpenChange(false);
    resetTutorial();
  }, [onComplete, onOpenChange, resetTutorial]);

  // Handle cancel/close
  const handleCancel = useCallback(() => {
    onOpenChange(false);
    resetTutorial();
  }, [onOpenChange, resetTutorial]);

  // Render current step content
  const renderStepContent = () => {
    // Placeholder step components - will be replaced with actual step components in later subtasks
    const StepPlaceholder = ({ stepId }: { stepId: TutorialStepId }) => (
      <div className="flex flex-col items-center justify-center h-full p-8 space-y-6">
        <GraduationCap className="h-16 w-16 text-primary" />
        <h2 className="text-2xl font-semibold">
          {t(`${stepId}.title`, { defaultValue: stepId })}
        </h2>
        <p className="text-muted-foreground text-center max-w-md">
          {t(`${stepId}.description`, { defaultValue: `Step: ${stepId}` })}
        </p>
        <div className="flex gap-3 mt-8">
          {currentStepIndex > 0 && (
            <Button variant="outline" onClick={goToPreviousStep}>
              {t('navigation.back', { defaultValue: 'Back' })}
            </Button>
          )}
          {currentStepIndex < TUTORIAL_STEPS.length - 1 ? (
            <Button onClick={goToNextStep}>
              {t('navigation.next', { defaultValue: 'Next' })}
            </Button>
          ) : (
            <Button onClick={completeTutorial}>
              {t('navigation.finish', { defaultValue: 'Finish' })}
            </Button>
          )}
        </div>
      </div>
    );

    return <StepPlaceholder stepId={currentStepId} />;
  };

  return (
    <FullScreenDialog open={open} onOpenChange={onOpenChange}>
      <FullScreenDialogContent>
        <FullScreenDialogHeader>
          <div className="flex items-center gap-3">
            <GraduationCap className="h-6 w-6 text-primary" />
            <div>
              <FullScreenDialogTitle>
                {t('title', { defaultValue: 'Getting Started Tutorial' })}
              </FullScreenDialogTitle>
              <FullScreenDialogDescription>
                {t('description', { defaultValue: 'Learn how Auto Code works with a hands-on example' })}
              </FullScreenDialogDescription>
            </div>
          </div>
          {/* Progress indicator */}
          <div className="mt-6">
            <WizardProgress currentStep={currentStepIndex} steps={steps} />
          </div>
        </FullScreenDialogHeader>

        <FullScreenDialogBody>
          <ScrollArea className="h-full">
            <div className="p-6">
              {renderStepContent()}
            </div>
          </ScrollArea>
        </FullScreenDialogBody>
      </FullScreenDialogContent>
    </FullScreenDialog>
  );
}
