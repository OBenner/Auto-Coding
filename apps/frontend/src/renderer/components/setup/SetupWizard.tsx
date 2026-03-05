/**
 * SetupWizard - Multi-step wizard for first-run setup
 *
 * Features:
 * - Guided setup for first-time users
 * - Python version validation
 * - Claude SDK OAuth authentication
 * - Graphiti memory system configuration
 * - .env file creation
 * - Hello-world test run verification
 * - Progress tracking with visual indicators
 */
import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronRight, ChevronLeft, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import { PythonCheckStep } from './PythonCheckStep';

// Step configuration
const SETUP_STEPS = [
  {
    id: 'python-check',
    title: 'setup:steps.pythonCheck.title',
    description: 'setup:steps.pythonCheck.description',
  },
  {
    id: 'authentication',
    title: 'setup:steps.authentication.title',
    description: 'setup:steps.authentication.description',
  },
  {
    id: 'graphiti',
    title: 'setup:steps.graphiti.title',
    description: 'setup:steps.graphiti.description',
  },
  {
    id: 'env-config',
    title: 'setup:steps.envConfig.title',
    description: 'setup:steps.envConfig.description',
  },
  {
    id: 'test-run',
    title: 'setup:steps.testRun.title',
    description: 'setup:steps.testRun.description',
  },
  {
    id: 'success',
    title: 'setup:steps.success.title',
    description: 'setup:steps.success.description',
  },
] as const;

type StepId = typeof SETUP_STEPS[number]['id'];

interface StepStatus {
  completed: boolean;
  valid: boolean;
  error?: string;
}

interface SetupWizardProps {
  onComplete: () => void;
  onCancel?: () => void;
}

/**
 * Placeholder step component - will be replaced by actual step components
 */
function StepPlaceholder({
  stepId,
  onValidate
}: {
  stepId: StepId;
  onValidate: (valid: boolean, error?: string) => void
}) {
  const { t } = useTranslation();

  useEffect(() => {
    // Auto-validate placeholder steps (will be removed when real steps are implemented)
    onValidate(true);
  }, [onValidate]);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-dashed border-border p-6 text-center">
        <p className="text-sm text-muted-foreground">
          {t('setup:placeholder.stepComponent', { step: stepId })}
        </p>
      </div>
    </div>
  );
}

/**
 * Main SetupWizard component
 */
export function SetupWizard({ onComplete, onCancel }: SetupWizardProps) {
  const { t } = useTranslation();

  // Current step state
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // Track status of each step
  const [stepStatuses, setStepStatuses] = useState<Record<StepId, StepStatus>>(() => {
    const statuses: Record<string, StepStatus> = {};
    SETUP_STEPS.forEach(step => {
      statuses[step.id] = { completed: false, valid: false };
    });
    return statuses as Record<StepId, StepStatus>;
  });

  const currentStep = SETUP_STEPS[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === SETUP_STEPS.length - 1;
  const currentStepStatus = stepStatuses[currentStep.id];

  // Calculate progress percentage
  const progressPercentage = ((currentStepIndex + 1) / SETUP_STEPS.length) * 100;

  /**
   * Validate current step
   */
  const handleStepValidate = useCallback((valid: boolean, error?: string) => {
    setStepStatuses(prev => ({
      ...prev,
      [currentStep.id]: {
        ...prev[currentStep.id],
        valid,
        error,
      },
    }));
  }, [currentStep.id]);

  /**
   * Move to next step
   */
  const handleNext = useCallback(async () => {
    if (!currentStepStatus.valid) {
      return;
    }

    setIsProcessing(true);

    try {
      // Mark current step as completed
      setStepStatuses(prev => ({
        ...prev,
        [currentStep.id]: {
          ...prev[currentStep.id],
          completed: true,
        },
      }));

      // Move to next step or complete
      if (isLastStep) {
        // Wizard complete
        onComplete();
      } else {
        setCurrentStepIndex(prev => prev + 1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setStepStatuses(prev => ({
        ...prev,
        [currentStep.id]: {
          ...prev[currentStep.id],
          valid: false,
          error: errorMessage,
        },
      }));
    } finally {
      setIsProcessing(false);
    }
  }, [currentStep.id, currentStepStatus.valid, isLastStep, onComplete]);

  /**
   * Move to previous step
   */
  const handleBack = useCallback(() => {
    if (isFirstStep) {
      return;
    }
    setCurrentStepIndex(prev => prev - 1);
  }, [isFirstStep]);

  /**
   * Handle cancel
   */
  const handleCancel = useCallback(() => {
    if (onCancel) {
      onCancel();
    }
  }, [onCancel]);

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background p-4">
      <Card className="w-full max-w-3xl">
        <CardHeader>
          <div className="mb-4 flex items-center justify-between">
            <CardTitle className="text-2xl">
              {t('setup:title')}
            </CardTitle>
            <Badge variant="secondary">
              {t('setup:stepCounter', {
                current: currentStepIndex + 1,
                total: SETUP_STEPS.length
              })}
            </Badge>
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <Progress value={progressPercentage} className="h-2" />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{t(currentStep.title)}</span>
              <span>{Math.round(progressPercentage)}%</span>
            </div>
          </div>

          <CardDescription className="mt-4">
            {t(currentStep.description)}
          </CardDescription>
        </CardHeader>

        <CardContent className="min-h-[300px]">
          {/* Step indicators */}
          <div className="mb-6 flex justify-center">
            <div className="flex items-center gap-2">
              {SETUP_STEPS.map((step, index) => {
                const status = stepStatuses[step.id];
                const isCurrent = index === currentStepIndex;
                const isPast = index < currentStepIndex;

                return (
                  <div key={step.id} className="flex items-center">
                    <div
                      className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium transition-all',
                        isCurrent && 'border-primary bg-primary text-primary-foreground',
                        isPast && status.completed && 'border-primary bg-primary text-primary-foreground',
                        !isCurrent && !isPast && 'border-border bg-muted text-muted-foreground'
                      )}
                    >
                      {isPast && status.completed ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    {index < SETUP_STEPS.length - 1 && (
                      <div
                        className={cn(
                          'mx-1 h-0.5 w-8 transition-all',
                          isPast ? 'bg-primary' : 'bg-border'
                        )}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step content */}
          <div className="mt-6">
            {currentStep.id === 'python-check' && (
              <PythonCheckStep onValidate={handleStepValidate} />
            )}
            {currentStep.id === 'authentication' && (
              <StepPlaceholder stepId="authentication" onValidate={handleStepValidate} />
            )}
            {currentStep.id === 'graphiti' && (
              <StepPlaceholder stepId="graphiti" onValidate={handleStepValidate} />
            )}
            {currentStep.id === 'env-config' && (
              <StepPlaceholder stepId="env-config" onValidate={handleStepValidate} />
            )}
            {currentStep.id === 'test-run' && (
              <StepPlaceholder stepId="test-run" onValidate={handleStepValidate} />
            )}
            {currentStep.id === 'success' && (
              <StepPlaceholder stepId="success" onValidate={handleStepValidate} />
            )}
          </div>

          {/* Error message */}
          {currentStepStatus.error && (
            <div className="mt-4 rounded-lg border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
              {currentStepStatus.error}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between">
          <div>
            {onCancel && !isLastStep && (
              <Button
                variant="ghost"
                onClick={handleCancel}
                disabled={isProcessing}
              >
                {t('setup:actions.cancel')}
              </Button>
            )}
          </div>

          <div className="flex gap-2">
            {!isFirstStep && !isLastStep && (
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={isProcessing}
              >
                <ChevronLeft className="mr-2 h-4 w-4" />
                {t('setup:actions.back')}
              </Button>
            )}

            <Button
              onClick={handleNext}
              disabled={!currentStepStatus.valid || isProcessing}
            >
              {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLastStep ? t('setup:actions.finish') : t('setup:actions.next')}
              {!isLastStep && !isProcessing && <ChevronRight className="ml-2 h-4 w-4" />}
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
