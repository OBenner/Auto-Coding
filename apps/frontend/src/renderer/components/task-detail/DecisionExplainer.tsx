import { useState } from 'react';
import {
  Brain,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Info,
  Lightbulb,
  GitBranch,
  Target,
  TrendingUp,
  Layers,
  X
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { DecisionPoint, DecisionType, ConfidenceLevel, Alternative } from '../../../shared/types';

interface DecisionExplainerProps {
  decisions: DecisionPoint[];
  className?: string;
}

// Decision type metadata
const DECISION_TYPE_META: Record<DecisionType, { label: string; icon: typeof Brain; color: string }> = {
  approach: {
    label: 'Approach',
    icon: Target,
    color: 'text-blue-500 bg-blue-500/10 border-blue-500/30'
  },
  implementation: {
    label: 'Implementation',
    icon: Layers,
    color: 'text-purple-500 bg-purple-500/10 border-purple-500/30'
  },
  tool_selection: {
    label: 'Tool Selection',
    icon: Brain,
    color: 'text-cyan-500 bg-cyan-500/10 border-cyan-500/30'
  },
  file_modification: {
    label: 'File Change',
    icon: GitBranch,
    color: 'text-amber-500 bg-amber-500/10 border-amber-500/30'
  },
  error_recovery: {
    label: 'Error Recovery',
    icon: AlertTriangle,
    color: 'text-orange-500 bg-orange-500/10 border-orange-500/30'
  },
  architecture: {
    label: 'Architecture',
    icon: Layers,
    color: 'text-indigo-500 bg-indigo-500/10 border-indigo-500/30'
  },
  optimization: {
    label: 'Optimization',
    icon: TrendingUp,
    color: 'text-green-500 bg-green-500/10 border-green-500/30'
  },
  other: {
    label: 'Other',
    icon: Info,
    color: 'text-gray-500 bg-gray-500/10 border-gray-500/30'
  }
};

// Confidence level metadata
const CONFIDENCE_META: Record<ConfidenceLevel, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  very_low: {
    label: 'Very Low',
    color: 'text-red-500 bg-red-500/10 border-red-500/30',
    icon: AlertTriangle
  },
  low: {
    label: 'Low',
    color: 'text-orange-500 bg-orange-500/10 border-orange-500/30',
    icon: AlertTriangle
  },
  medium: {
    label: 'Medium',
    color: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
    icon: Info
  },
  high: {
    label: 'High',
    color: 'text-green-500 bg-green-500/10 border-green-500/30',
    icon: CheckCircle2
  },
  very_high: {
    label: 'Very High',
    color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
    icon: CheckCircle2
  }
};

export function DecisionExplainer({ decisions, className }: DecisionExplainerProps) {
  const [expandedDecisions, setExpandedDecisions] = useState<Set<number>>(new Set());

  const toggleDecision = (index: number) => {
    setExpandedDecisions(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  if (decisions.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-8 text-muted-foreground', className)}>
        <Brain className="mr-2 h-5 w-5" />
        <span>No decisions recorded yet</span>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {decisions.map((decision, index) => {
        const isExpanded = expandedDecisions.has(index);
        const typeMeta = DECISION_TYPE_META[decision.decision_type];
        const confidenceMeta = CONFIDENCE_META[decision.confidence_level];
        const TypeIcon = typeMeta.icon;
        const ConfidenceIcon = confidenceMeta.icon;

        return (
          <div
            key={index}
            className={cn(
              'rounded-lg border bg-card/50',
              decision.requires_review && 'border-amber-500/50 bg-amber-500/5'
            )}
          >
            {/* Decision Header */}
            <button
              onClick={() => toggleDecision(index)}
              className="w-full px-4 py-3 flex items-start gap-3 hover:bg-accent/50 transition-colors"
            >
              {/* Expand/Collapse Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </div>

              {/* Decision Type Icon */}
              <div className="flex-shrink-0">
                <div className={cn('rounded p-1.5 border', typeMeta.color)}>
                  <TypeIcon className="h-4 w-4" />
                </div>
              </div>

              {/* Decision Content */}
              <div className="flex-1 text-left min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-medium text-sm">{typeMeta.label}</span>

                  {/* Confidence Badge */}
                  <Badge variant="outline" className={cn('text-xs', confidenceMeta.color)}>
                    <ConfidenceIcon className="mr-1 h-3 w-3" />
                    {confidenceMeta.label} ({Math.round(decision.confidence * 100)}%)
                  </Badge>

                  {/* Review Required Badge */}
                  {decision.requires_review && (
                    <Badge variant="outline" className="text-xs text-amber-500 bg-amber-500/10 border-amber-500/30">
                      <AlertTriangle className="mr-1 h-3 w-3" />
                      Review Needed
                    </Badge>
                  )}

                  {/* Phase Badge */}
                  {decision.phase && (
                    <Badge variant="outline" className="text-xs">
                      {decision.phase}
                    </Badge>
                  )}

                  {/* Subtask Badge */}
                  {decision.subtask_id && (
                    <Badge variant="outline" className="text-xs">
                      {decision.subtask_id}
                    </Badge>
                  )}
                </div>

                <p className="text-sm text-foreground line-clamp-2">
                  {decision.chosen_approach}
                </p>

                {/* Show hint about expandable content */}
                {!isExpanded && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {decision.alternatives && decision.alternatives.length > 0 && (
                      <span>• {decision.alternatives.length} alternative{decision.alternatives.length !== 1 ? 's' : ''} considered</span>
                    )}
                    {decision.reasoning_chain && decision.reasoning_chain.length > 0 && (
                      <span className="ml-2">• {decision.reasoning_chain.length} reasoning step{decision.reasoning_chain.length !== 1 ? 's' : ''}</span>
                    )}
                  </p>
                )}
              </div>

              {/* Timestamp */}
              <div className="flex-shrink-0 text-xs text-muted-foreground">
                {new Date(decision.timestamp).toLocaleTimeString()}
              </div>
            </button>

            {/* Expanded Details */}
            {isExpanded && (
              <div className="px-4 pb-4 space-y-4 border-t">
                {/* Context */}
                {decision.context && (
                  <div className="pt-4">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                      Context
                    </h4>
                    <p className="text-sm text-foreground">{decision.context}</p>
                  </div>
                )}

                {/* Chosen Approach */}
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2 flex items-center">
                    <CheckCircle2 className="mr-1.5 h-3.5 w-3.5 text-green-500" />
                    Chosen Approach
                  </h4>
                  <p className="text-sm text-foreground">{decision.chosen_approach}</p>
                </div>

                {/* Reasoning */}
                {decision.reasoning && (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2 flex items-center">
                      <Lightbulb className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
                      Reasoning
                    </h4>
                    <p className="text-sm text-foreground">{decision.reasoning}</p>
                  </div>
                )}

                {/* Reasoning Chain */}
                {decision.reasoning_chain && decision.reasoning_chain.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                      Reasoning Steps
                    </h4>
                    <ol className="space-y-2">
                      {decision.reasoning_chain.map((step, stepIndex) => (
                        <li key={stepIndex} className="flex gap-2 text-sm">
                          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-medium">
                            {stepIndex + 1}
                          </span>
                          <span className="flex-1 text-foreground">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Alternatives */}
                {decision.alternatives && decision.alternatives.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2 flex items-center">
                      <GitBranch className="mr-1.5 h-3.5 w-3.5 text-muted-foreground" />
                      Alternatives Considered ({decision.alternatives.length})
                    </h4>
                    <div className="space-y-3">
                      {decision.alternatives.map((alt, altIndex) => (
                        <AlternativeCard key={altIndex} alternative={alt} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Additional Info */}
                <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                  {decision.impact && (
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                        Impact
                      </h4>
                      <p className="text-sm text-foreground">{decision.impact}</p>
                    </div>
                  )}

                  {decision.reversible !== undefined && (
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                        Reversible
                      </h4>
                      <Badge variant="outline" className={cn(
                        'text-xs',
                        decision.reversible
                          ? 'text-green-500 bg-green-500/10 border-green-500/30'
                          : 'text-red-500 bg-red-500/10 border-red-500/30'
                      )}>
                        {decision.reversible ? 'Yes' : 'No'}
                      </Badge>
                    </div>
                  )}

                  {decision.dependencies && decision.dependencies.length > 0 && (
                    <div className="col-span-2">
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                        Dependencies
                      </h4>
                      <div className="flex flex-wrap gap-1">
                        {decision.dependencies.map((dep, depIndex) => (
                          <Badge key={depIndex} variant="outline" className="text-xs">
                            {dep}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Alternative card component
function AlternativeCard({ alternative }: { alternative: Alternative }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="rounded border bg-card/30 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-start gap-2 hover:bg-accent/50 transition-colors text-left"
      >
        <div className="flex-shrink-0 mt-0.5">
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <X className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
            <span className="text-sm font-medium text-foreground line-clamp-1">
              {alternative.description}
            </span>
          </div>
          {!isExpanded && (
            <p className="text-xs text-muted-foreground line-clamp-1">
              {alternative.rejected_reason}
            </p>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-2 border-t">
          <div className="pt-2">
            <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
              Why Considered
            </h5>
            <p className="text-xs text-foreground">{alternative.reasoning}</p>
          </div>

          <div>
            <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
              Why Rejected
            </h5>
            <p className="text-xs text-foreground">{alternative.rejected_reason}</p>
          </div>

          {alternative.confidence_impact && (
            <div>
              <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                Confidence Impact
              </h5>
              <p className="text-xs text-foreground">{alternative.confidence_impact}</p>
            </div>
          )}

          {alternative.tradeoffs && alternative.tradeoffs.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                Tradeoffs
              </h5>
              <ul className="space-y-1">
                {alternative.tradeoffs.map((tradeoff, idx) => (
                  <li key={idx} className="text-xs text-foreground flex gap-1.5">
                    <span className="text-muted-foreground">•</span>
                    <span>{tradeoff}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
