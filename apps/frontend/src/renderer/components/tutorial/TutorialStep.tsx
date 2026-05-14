import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { PhaseExplainer } from './PhaseExplainer';
import { ExplainMoreSection } from './ExplainMoreSection';
import { ProgressTimeline, TutorialPhase } from './ProgressTimeline';
import type { ExecutionPhase, Subtask, TaskLogs } from '../../../shared/types';

export interface TutorialStepProps {
  title: string;
  description?: string;
  phase?: ExecutionPhase;
  subtasks?: Subtask[];
  explanationText?: string;
  phaseLogs?: TaskLogs | null;
  phaseProgress?: number;
  isStuck?: boolean;
  isRunning?: boolean;
  explainMoreTitle?: string;
  explainMoreContent?: React.ReactNode;
  timelinePhases?: TutorialPhase[];
  currentPhaseIndex?: number;
  onNext?: () => void;
  onBack?: () => void;
  onFinish?: () => void;
  showBack?: boolean;
  showNext?: boolean;
  showFinish?: boolean;
  nextLabel?: string;
  backLabel?: string;
  finishLabel?: string;
  children?: React.ReactNode;
}

/**
 * Generic tutorial step component with structured layout.
 * Provides a consistent structure for tutorial steps with header,
 * phase explanation, expandable details, progress timeline, and navigation.
 *
 * Features:
 * - Optional header with title and description
 * - PhaseExplainer for showing current phase progress
 * - ExplainMoreSection for expandable detailed explanations
 * - ProgressTimeline for visual progress tracking
 * - Flexible navigation buttons (back, next, finish)
 * - Custom content via children prop
 *
 * @example
 * ```tsx
 * <TutorialStep
 *   title="Spec Creation Phase"
 *   description="The agent is creating a specification for your feature"
 *   phase="spec_creation"
 *   subtasks={subtasks}
 *   explanationText="The spec defines what will be built..."
 *   explainMoreTitle="What is a spec?"
 *   explainMoreContent={<p>A spec is a detailed description...</p>}
 *   timelinePhases={phases}
 *   currentPhaseIndex={0}
 *   onNext={handleNext}
 *   onBack={handleBack}
 *   showBack
 *   showNext
 * />
 * ```
 */
export function TutorialStep({
  title,
  description,
  phase,
  subtasks = [],
  explanationText,
  phaseLogs,
  phaseProgress,
  isStuck = false,
  isRunning = false,
  explainMoreTitle,
  explainMoreContent,
  timelinePhases,
  currentPhaseIndex = 0,
  onNext,
  onBack,
  onFinish,
  showBack = false,
  showNext = false,
  showFinish = false,
  nextLabel,
  backLabel,
  finishLabel,
  children,
}: TutorialStepProps) {
  const { t } = useTranslation('tutorial');

  return (
    <div className="flex h-full flex-col items-center justify-start px-8 py-6">
      <div className="w-full max-w-4xl space-y-8">
        {/* Header Section */}
        {(title || description) && (
          <div className="text-center space-y-2">
            {title && (
              <h2 className="text-2xl font-bold text-foreground tracking-tight">
                {title}
              </h2>
            )}
            {description && (
              <p className="text-muted-foreground text-lg">
                {description}
              </p>
            )}
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left/Main Content Area (2 columns on large screens) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Phase Explainer */}
            {phase && explanationText && (
              <Card className="border border-border bg-card/50 backdrop-blur-sm">
                <CardContent className="p-6">
                  <PhaseExplainer
                    phase={phase}
                    subtasks={subtasks}
                    explanationText={explanationText}
                    phaseLogs={phaseLogs}
                    phaseProgress={phaseProgress}
                    isStuck={isStuck}
                    isRunning={isRunning}
                  />
                </CardContent>
              </Card>
            )}

            {/* Custom Content */}
            {children && (
              <div>
                {children}
              </div>
            )}

            {/* Explain More Section */}
            {explainMoreTitle && explainMoreContent && (
              <ExplainMoreSection title={explainMoreTitle}>
                {explainMoreContent}
              </ExplainMoreSection>
            )}
          </div>

          {/* Right Sidebar - Progress Timeline */}
          {timelinePhases && timelinePhases.length > 0 && (
            <div className="lg:col-span-1">
              <Card className="border border-border bg-card/50 backdrop-blur-sm sticky top-6">
                <CardContent className="p-6">
                  <h3 className="text-sm font-medium text-muted-foreground mb-6 uppercase tracking-wide">
                    {t('progress', { defaultValue: 'Progress' })}
                  </h3>
                  <ProgressTimeline
                    currentPhase={currentPhaseIndex}
                    phases={timelinePhases}
                  />
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* Navigation Buttons */}
        {(showBack || showNext || showFinish) && (
          <div className="flex justify-between items-center pt-6 border-t border-border">
            {/* Back Button */}
            <div>
              {showBack && onBack && (
                <Button
                  variant="outline"
                  onClick={onBack}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  {backLabel || t('navigation.back', { defaultValue: 'Back' })}
                </Button>
              )}
            </div>

            {/* Next/Finish Button */}
            <div className="ml-auto">
              {showFinish && onFinish ? (
                <Button
                  onClick={onFinish}
                  className="gap-2"
                >
                  <Check className="h-5 w-5" />
                  {finishLabel || t('navigation.finish', { defaultValue: 'Finish Tutorial' })}
                </Button>
              ) : showNext && onNext ? (
                <Button
                  onClick={onNext}
                  className="gap-2"
                >
                  {nextLabel || t('navigation.next', { defaultValue: 'Next' })}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
