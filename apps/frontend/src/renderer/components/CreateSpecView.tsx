/**
 * CreateSpecView - Pattern Suggestion Display for Spec Creation
 *
 * Displays intelligent pattern suggestions during spec creation based on
 * past implementations. Users can confirm, reject, or modify suggested patterns.
 *
 * Features:
 * - Display categorized pattern suggestions
 * - Confirm/reject/modify actions per pattern
 * - Relevance score and confidence indicators
 * - Integration with Graphiti memory system
 *
 * @example
 * ```tsx
 * <CreateSpecView
 *   projectId={projectId}
 *   taskDescription="Add authentication feature"
 *   onPatternConfirmed={(pattern) => console.log('Confirmed:', pattern)}
 *   onPatternRejected={(pattern) => console.log('Rejected:', pattern)}
 * />
 * ```
 */
import { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  Edit3,
  Sparkles,
  TrendingUp,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Info
} from 'lucide-react';
import { Card, CardContent, CardHeader } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { cn } from '../lib/utils';

/**
 * Pattern suggestion from Graphiti memory system
 */
export interface PatternSuggestion {
  /** Pattern description */
  pattern: string;
  /** Pattern category (e.g., "state-management", "error-handling") */
  category: string;
  /** Categorization confidence (0.0-1.0) */
  confidence: number;
  /** Reasoning for categorization */
  reasoning: string;
  /** Semantic search relevance score (0.0-1.0) */
  score: number;
  /** Spec ID where pattern originated */
  spec_id: string;
  /** When pattern was created */
  timestamp: string;
}

/**
 * Pattern action state
 */
type PatternAction = 'pending' | 'confirmed' | 'rejected' | 'modified';

/**
 * Pattern with action tracking
 */
interface PatternWithAction extends PatternSuggestion {
  action: PatternAction;
  modifiedPattern?: string;
}

/**
 * Props for CreateSpecView
 */
interface CreateSpecViewProps {
  /** Project ID for memory context */
  projectId: string;
  /** Task description to find relevant patterns */
  taskDescription: string;
  /** Callback when a pattern is confirmed */
  onPatternConfirmed?: (pattern: PatternSuggestion) => void;
  /** Callback when a pattern is rejected */
  onPatternRejected?: (pattern: PatternSuggestion) => void;
  /** Callback when a pattern is modified */
  onPatternModified?: (pattern: PatternSuggestion, modifiedText: string) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Get category display info (icon, label, color)
 */
function getCategoryInfo(category: string): {
  icon: React.ReactNode;
  label: string;
  colorClass: string;
} {
  const categoryMap: Record<string, { icon: React.ReactNode; label: string; colorClass: string }> = {
    'state-management': {
      icon: <Sparkles className="h-3 w-3" />,
      label: 'State Management',
      colorClass: 'bg-blue-500/10 text-blue-500 border-blue-500/20'
    },
    'error-handling': {
      icon: <AlertCircle className="h-3 w-3" />,
      label: 'Error Handling',
      colorClass: 'bg-red-500/10 text-red-500 border-red-500/20'
    },
    'architecture': {
      icon: <TrendingUp className="h-3 w-3" />,
      label: 'Architecture',
      colorClass: 'bg-purple-500/10 text-purple-500 border-purple-500/20'
    },
    'testing': {
      icon: <CheckCircle2 className="h-3 w-3" />,
      label: 'Testing',
      colorClass: 'bg-green-500/10 text-green-500 border-green-500/20'
    },
    'ui-ux': {
      icon: <Sparkles className="h-3 w-3" />,
      label: 'UI/UX',
      colorClass: 'bg-pink-500/10 text-pink-500 border-pink-500/20'
    },
    'performance': {
      icon: <TrendingUp className="h-3 w-3" />,
      label: 'Performance',
      colorClass: 'bg-orange-500/10 text-orange-500 border-orange-500/20'
    },
    'security': {
      icon: <AlertCircle className="h-3 w-3" />,
      label: 'Security',
      colorClass: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
    }
  };

  return categoryMap[category] || {
    icon: <Info className="h-3 w-3" />,
    label: category.charAt(0).toUpperCase() + category.slice(1).replace(/-/g, ' '),
    colorClass: 'bg-muted text-muted-foreground border-border'
  };
}

/**
 * Get confidence level display (label and color)
 */
function getConfidenceLevel(confidence: number): { label: string; colorClass: string } {
  if (confidence >= 0.8) {
    return { label: 'High', colorClass: 'text-success' };
  } else if (confidence >= 0.6) {
    return { label: 'Medium', colorClass: 'text-warning' };
  } else {
    return { label: 'Low', colorClass: 'text-muted-foreground' };
  }
}

/**
 * Pattern Card Component
 */
function PatternCard({
  pattern,
  onConfirm,
  onReject,
  onModify
}: {
  pattern: PatternWithAction;
  onConfirm: () => void;
  onReject: () => void;
  onModify: (text: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(pattern.pattern);

  const categoryInfo = getCategoryInfo(pattern.category);
  const confidenceLevel = getConfidenceLevel(pattern.confidence);

  const handleSaveEdit = () => {
    onModify(editedText);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedText(pattern.pattern);
    setIsEditing(false);
  };

  return (
    <Card
      className={cn(
        'border transition-all',
        pattern.action === 'confirmed' && 'border-success/50 bg-success/5',
        pattern.action === 'rejected' && 'border-destructive/30 bg-destructive/5 opacity-60',
        pattern.action === 'modified' && 'border-info/50 bg-info/5',
        pattern.action === 'pending' && 'border-border'
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-2">
            {/* Category Badge */}
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn('flex items-center gap-1 text-xs', categoryInfo.colorClass)}
              >
                {categoryInfo.icon}
                {categoryInfo.label}
              </Badge>
              <span className={cn('text-xs font-medium', confidenceLevel.colorClass)}>
                {confidenceLevel.label} Confidence
              </span>
            </div>

            {/* Pattern Text (editable) */}
            {isEditing ? (
              <Textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="min-h-[80px] text-sm"
                placeholder="Modify the pattern..."
              />
            ) : (
              <p className="text-sm text-foreground leading-relaxed">
                {pattern.action === 'modified' && pattern.modifiedPattern
                  ? pattern.modifiedPattern
                  : pattern.pattern}
              </p>
            )}
          </div>

          {/* Action Icons */}
          {!isEditing && (
            <div className="flex items-center gap-1">
              {pattern.action === 'pending' && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onConfirm}
                    className="h-8 w-8 p-0 text-success hover:bg-success/10 hover:text-success"
                    title="Confirm pattern"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditing(true)}
                    className="h-8 w-8 p-0 text-info hover:bg-info/10 hover:text-info"
                    title="Modify pattern"
                  >
                    <Edit3 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onReject}
                    className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                    title="Reject pattern"
                  >
                    <XCircle className="h-4 w-4" />
                  </Button>
                </>
              )}
              {pattern.action === 'confirmed' && (
                <CheckCircle2 className="h-5 w-5 text-success" />
              )}
              {pattern.action === 'rejected' && (
                <XCircle className="h-5 w-5 text-destructive" />
              )}
              {pattern.action === 'modified' && (
                <Edit3 className="h-5 w-5 text-info" />
              )}
            </div>
          )}
        </div>

        {/* Edit Actions */}
        {isEditing && (
          <div className="flex items-center gap-2 pt-2">
            <Button size="sm" onClick={handleSaveEdit} className="gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Save
            </Button>
            <Button size="sm" variant="outline" onClick={handleCancelEdit}>
              Cancel
            </Button>
          </div>
        )}
      </CardHeader>

      {/* Expandable Details */}
      <CardContent className="pt-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              Hide details
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              Show details
            </>
          )}
        </Button>

        {isExpanded && (
          <div className="mt-3 space-y-2 text-xs">
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground font-medium">Reasoning:</span>
              <span className="text-foreground flex-1">{pattern.reasoning}</span>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground font-medium">Relevance:</span>
                <span className="text-foreground">{Math.round(pattern.score * 100)}%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground font-medium">From:</span>
                <span className="text-foreground">{pattern.spec_id}</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * CreateSpecView Component
 */
export function CreateSpecView({
  projectId,
  taskDescription,
  onPatternConfirmed,
  onPatternRejected,
  onPatternModified,
  className
}: CreateSpecViewProps) {
  const [patterns, setPatterns] = useState<PatternWithAction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load pattern suggestions when component mounts
  useEffect(() => {
    loadPatternSuggestions();
  }, [projectId, taskDescription]);

  const loadPatternSuggestions = async () => {
    if (!taskDescription.trim()) {
      setPatterns([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call once handler is implemented (subtask 4-2)
      // For now, return empty array as placeholder
      // const result = await window.electronAPI.getPatternSuggestions(projectId, taskDescription);
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to load pattern suggestions');
      // }
      // const loadedPatterns: PatternWithAction[] = (result.data || []).map(p => ({
      //   ...p,
      //   action: 'pending' as PatternAction
      // }));
      // setPatterns(loadedPatterns);

      // Placeholder: Empty patterns until IPC handler is implemented
      setPatterns([]);
    } catch (err) {
      console.error('Failed to load pattern suggestions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load pattern suggestions');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = (index: number) => {
    const updatedPatterns = [...patterns];
    updatedPatterns[index].action = 'confirmed';
    setPatterns(updatedPatterns);
    onPatternConfirmed?.(patterns[index]);
  };

  const handleReject = (index: number) => {
    const updatedPatterns = [...patterns];
    updatedPatterns[index].action = 'rejected';
    setPatterns(updatedPatterns);
    onPatternRejected?.(patterns[index]);
  };

  const handleModify = (index: number, modifiedText: string) => {
    const updatedPatterns = [...patterns];
    updatedPatterns[index].action = 'modified';
    updatedPatterns[index].modifiedPattern = modifiedText;
    setPatterns(updatedPatterns);
    onPatternModified?.(patterns[index], modifiedText);
  };

  // Don't render if no patterns and not loading
  if (!isLoading && patterns.length === 0 && !error) {
    return null;
  }

  const confirmedCount = patterns.filter(p => p.action === 'confirmed').length;
  const rejectedCount = patterns.filter(p => p.action === 'rejected').length;
  const modifiedCount = patterns.filter(p => p.action === 'modified').length;

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Suggested Patterns
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Based on similar past implementations. Review and select patterns to include.
          </p>
        </div>
        {patterns.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            {confirmedCount > 0 && (
              <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                {confirmedCount} confirmed
              </Badge>
            )}
            {modifiedCount > 0 && (
              <Badge variant="outline" className="bg-info/10 text-info border-info/20">
                {modifiedCount} modified
              </Badge>
            )}
            {rejectedCount > 0 && (
              <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">
                {rejectedCount} rejected
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center gap-3 text-muted-foreground">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <span>Finding relevant patterns...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3 text-destructive">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Failed to load pattern suggestions</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pattern Cards */}
      {!isLoading && !error && patterns.length > 0 && (
        <div className="space-y-3">
          {patterns.map((pattern, index) => (
            <PatternCard
              key={`${pattern.spec_id}-${index}`}
              pattern={pattern}
              onConfirm={() => handleConfirm(index)}
              onReject={() => handleReject(index)}
              onModify={(text) => handleModify(index, text)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
