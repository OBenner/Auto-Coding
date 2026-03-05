/**
 * PatternDetector Component
 *
 * Analyzes agent thought blocks and tool calls to detect suspicious patterns
 * such as infinite loops, repeated failures, and other anomalies.
 *
 * Inspired by apps/backend/analysis/error_pattern_matcher.py
 */

import { useMemo, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, RefreshCw, XCircle, TrendingDown, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { AgentToolCall } from './ToolCallBlock';
import type { AgentThinkingBlock } from './ThoughtBlock';

/**
 * Detected pattern types
 */
export enum PatternType {
  INFINITE_LOOP = 'infinite_loop',
  REPEATED_FAILURES = 'repeated_failures',
  RAPID_TOOL_CALLS = 'rapid_tool_calls',
  SAME_ERROR_REPEATED = 'same_error_repeated',
  NO_PROGRESS = 'no_progress',
}

/**
 * Severity levels for detected patterns
 */
export enum PatternSeverity {
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * Detected pattern data structure
 */
export interface DetectedPattern {
  /** Pattern type */
  type: PatternType;
  /** Severity level */
  severity: PatternSeverity;
  /** Human-readable description */
  description: string;
  /** Suggested action to resolve */
  suggestion: string;
  /** Number of occurrences */
  occurrences: number;
  /** Affected tool calls or thoughts (IDs) */
  affectedItems: string[];
}

interface PatternDetectorProps {
  /** Tool calls to analyze */
  toolCalls: AgentToolCall[];
  /** Thinking blocks to analyze */
  thoughts: AgentThinkingBlock[];
  /** Optional CSS class name */
  className?: string;
  /** Whether to show details for each pattern */
  showDetails?: boolean;
}

/**
 * Configuration thresholds for pattern detection
 */
const DETECTION_THRESHOLDS = {
  /** Number of same tool calls in sequence to trigger infinite loop warning */
  INFINITE_LOOP_THRESHOLD: 5,
  /** Number of consecutive failures to trigger repeated failures warning */
  REPEATED_FAILURES_THRESHOLD: 3,
  /** Number of tool calls per second to trigger rapid calls warning */
  RAPID_CALLS_PER_SECOND: 10,
  /** Number of same errors to trigger same error warning */
  SAME_ERROR_THRESHOLD: 3,
  /** Time window for no progress detection (ms) */
  NO_PROGRESS_WINDOW_MS: 300000, // 5 minutes
};

/**
 * Analyze tool calls and thoughts for suspicious patterns
 */
function detectPatterns(
  toolCalls: AgentToolCall[],
  thoughts: AgentThinkingBlock[]
): DetectedPattern[] {
  const patterns: DetectedPattern[] = [];

  // Pattern 1: Infinite loops (same tool called repeatedly)
  const infiniteLoopPattern = detectInfiniteLoop(toolCalls);
  if (infiniteLoopPattern) patterns.push(infiniteLoopPattern);

  // Pattern 2: Repeated failures
  const repeatedFailuresPattern = detectRepeatedFailures(toolCalls);
  if (repeatedFailuresPattern) patterns.push(repeatedFailuresPattern);

  // Pattern 3: Rapid tool calls (potential runaway agent)
  const rapidCallsPattern = detectRapidToolCalls(toolCalls);
  if (rapidCallsPattern) patterns.push(rapidCallsPattern);

  // Pattern 4: Same error repeated
  const sameErrorPattern = detectSameErrorRepeated(toolCalls);
  if (sameErrorPattern) patterns.push(sameErrorPattern);

  // Pattern 5: No progress (stuck agent)
  const noProgressPattern = detectNoProgress(toolCalls, thoughts);
  if (noProgressPattern) patterns.push(noProgressPattern);

  return patterns;
}

/**
 * Detect infinite loop pattern (same tool called repeatedly)
 */
function detectInfiniteLoop(toolCalls: AgentToolCall[]): DetectedPattern | null {
  if (toolCalls.length < DETECTION_THRESHOLDS.INFINITE_LOOP_THRESHOLD) return null;

  // Track consecutive same tool calls
  let currentTool = '';
  let consecutiveCount = 0;
  let maxConsecutive = 0;
  let maxConsecutiveTool = '';
  const affectedItems: string[] = [];

  for (const call of toolCalls) {
    if (call.name === currentTool) {
      consecutiveCount++;
      affectedItems.push(call.id);
      if (consecutiveCount > maxConsecutive) {
        maxConsecutive = consecutiveCount;
        maxConsecutiveTool = currentTool;
      }
    } else {
      currentTool = call.name;
      consecutiveCount = 1;
      affectedItems.length = 0;
      affectedItems.push(call.id);
    }
  }

  if (maxConsecutive >= DETECTION_THRESHOLDS.INFINITE_LOOP_THRESHOLD) {
    return {
      type: PatternType.INFINITE_LOOP,
      severity: PatternSeverity.CRITICAL,
      description: `Tool "${maxConsecutiveTool}" called ${maxConsecutive} times in sequence`,
      suggestion: 'Agent may be stuck in a loop. Consider interrupting and providing guidance.',
      occurrences: maxConsecutive,
      affectedItems: affectedItems.slice(-maxConsecutive),
    };
  }

  return null;
}

/**
 * Detect repeated failures pattern
 */
function detectRepeatedFailures(toolCalls: AgentToolCall[]): DetectedPattern | null {
  if (toolCalls.length < DETECTION_THRESHOLDS.REPEATED_FAILURES_THRESHOLD) return null;

  let consecutiveFailures = 0;
  const affectedItems: string[] = [];

  for (const call of toolCalls) {
    if (call.success === false || call.error) {
      consecutiveFailures++;
      affectedItems.push(call.id);
    } else if (call.success === true) {
      consecutiveFailures = 0;
      affectedItems.length = 0;
    }
  }

  if (consecutiveFailures >= DETECTION_THRESHOLDS.REPEATED_FAILURES_THRESHOLD) {
    return {
      type: PatternType.REPEATED_FAILURES,
      severity: PatternSeverity.ERROR,
      description: `${consecutiveFailures} consecutive tool call failures`,
      suggestion: 'Agent is repeatedly failing. Check error messages and consider adjusting the task.',
      occurrences: consecutiveFailures,
      affectedItems: affectedItems.slice(-consecutiveFailures),
    };
  }

  return null;
}

/**
 * Detect rapid tool calls pattern (potential runaway agent)
 */
function detectRapidToolCalls(toolCalls: AgentToolCall[]): DetectedPattern | null {
  if (toolCalls.length < 10) return null;

  // Calculate calls per second in recent window (last 10 calls)
  const recentCalls = toolCalls.slice(-10);
  const timestamps = recentCalls.map((call) => new Date(call.timestamp).getTime());

  if (timestamps.length < 2) return null;

  const timeSpanMs = timestamps[timestamps.length - 1] - timestamps[0];
  const callsPerSecond = (recentCalls.length / timeSpanMs) * 1000;

  if (callsPerSecond >= DETECTION_THRESHOLDS.RAPID_CALLS_PER_SECOND) {
    return {
      type: PatternType.RAPID_TOOL_CALLS,
      severity: PatternSeverity.WARNING,
      description: `${Math.round(callsPerSecond)} tool calls per second`,
      suggestion: 'Agent is making rapid tool calls. May indicate inefficient approach or runaway behavior.',
      occurrences: Math.round(callsPerSecond),
      affectedItems: recentCalls.map((c) => c.id),
    };
  }

  return null;
}

/**
 * Detect same error repeated pattern
 */
function detectSameErrorRepeated(toolCalls: AgentToolCall[]): DetectedPattern | null {
  if (toolCalls.length < DETECTION_THRESHOLDS.SAME_ERROR_THRESHOLD) return null;

  // Count error occurrences
  const errorCounts = new Map<string, { count: number; ids: string[] }>();

  for (const call of toolCalls) {
    if (call.error) {
      // Normalize error message (first 100 chars for grouping)
      const normalizedError = call.error.substring(0, 100).toLowerCase().trim();

      const existing = errorCounts.get(normalizedError) || { count: 0, ids: [] };
      existing.count++;
      existing.ids.push(call.id);
      errorCounts.set(normalizedError, existing);
    }
  }

  // Find most common error
  let maxErrorCount = 0;
  let maxErrorMessage = '';
  let maxErrorIds: string[] = [];

  for (const [error, { count, ids }] of errorCounts.entries()) {
    if (count > maxErrorCount) {
      maxErrorCount = count;
      maxErrorMessage = error;
      maxErrorIds = ids;
    }
  }

  if (maxErrorCount >= DETECTION_THRESHOLDS.SAME_ERROR_THRESHOLD) {
    return {
      type: PatternType.SAME_ERROR_REPEATED,
      severity: PatternSeverity.ERROR,
      description: `Same error occurred ${maxErrorCount} times: "${maxErrorMessage}..."`,
      suggestion: 'Agent is encountering the same error repeatedly. Consider fixing the underlying issue.',
      occurrences: maxErrorCount,
      affectedItems: maxErrorIds,
    };
  }

  return null;
}

/**
 * Detect no progress pattern (agent stuck)
 */
function detectNoProgress(
  toolCalls: AgentToolCall[],
  thoughts: AgentThinkingBlock[]
): DetectedPattern | null {
  const allItems = [...toolCalls, ...thoughts].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  if (allItems.length < 2) return null;

  const now = Date.now();
  const lastItemTime = new Date(allItems[allItems.length - 1].timestamp).getTime();
  const timeSinceLastActivity = now - lastItemTime;

  // Check if agent has been inactive for too long
  if (timeSinceLastActivity >= DETECTION_THRESHOLDS.NO_PROGRESS_WINDOW_MS) {
    const itemIds = allItems.map((item) => item.id);
    return {
      type: PatternType.NO_PROGRESS,
      severity: PatternSeverity.WARNING,
      description: `No activity for ${Math.round(timeSinceLastActivity / 60000)} minutes`,
      suggestion: 'Agent appears to be stuck or waiting. Consider checking the task status.',
      occurrences: 1,
      affectedItems: itemIds.slice(-5), // Last 5 items
    };
  }

  return null;
}

/**
 * Get icon component for pattern severity
 */
function getSeverityIcon(severity: PatternSeverity): React.ComponentType<{ className?: string }> {
  switch (severity) {
    case PatternSeverity.CRITICAL:
      return XCircle;
    case PatternSeverity.ERROR:
      return AlertTriangle;
    case PatternSeverity.WARNING:
      return AlertCircle;
    default:
      return AlertCircle;
  }
}

/**
 * Get color classes for pattern severity
 */
function getSeverityColors(severity: PatternSeverity): string {
  switch (severity) {
    case PatternSeverity.CRITICAL:
      return 'border-red-500/50 bg-red-500/10';
    case PatternSeverity.ERROR:
      return 'border-orange-500/50 bg-orange-500/10';
    case PatternSeverity.WARNING:
      return 'border-yellow-500/50 bg-yellow-500/10';
    default:
      return 'border-gray-500/50 bg-gray-500/10';
  }
}

/**
 * Get badge color for pattern severity
 */
function getSeverityBadgeColor(severity: PatternSeverity): string {
  switch (severity) {
    case PatternSeverity.CRITICAL:
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    case PatternSeverity.ERROR:
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case PatternSeverity.WARNING:
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  }
}

/**
 * Get icon for pattern type
 */
function getPatternIcon(type: PatternType): React.ComponentType<{ className?: string }> {
  switch (type) {
    case PatternType.INFINITE_LOOP:
      return RefreshCw;
    case PatternType.REPEATED_FAILURES:
      return XCircle;
    case PatternType.RAPID_TOOL_CALLS:
      return TrendingDown;
    case PatternType.SAME_ERROR_REPEATED:
      return AlertTriangle;
    case PatternType.NO_PROGRESS:
      return AlertCircle;
    default:
      return AlertCircle;
  }
}

/**
 * PatternDetector component
 * Analyzes and displays suspicious patterns in agent behavior
 */
export const PatternDetector = memo(function PatternDetector({
  toolCalls,
  thoughts,
  className,
  showDetails = true,
}: PatternDetectorProps) {
  const { t } = useTranslation('agent-inspector');

  // Detect patterns
  const detectedPatterns = useMemo(() => {
    return detectPatterns(toolCalls, thoughts);
  }, [toolCalls, thoughts]);

  // If no patterns detected, show success state
  if (detectedPatterns.length === 0) {
    return (
      <Card className={cn('border-green-500/50 bg-green-500/10', className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertCircle className="h-5 w-5 text-green-500" />
            {t('patterns.noIssues', 'No Issues Detected')}
          </CardTitle>
          <CardDescription>
            {t('patterns.noIssuesDescription', 'Agent behavior appears normal with no suspicious patterns.')}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Show detected patterns
  return (
    <div className={cn('space-y-4', className)}>
      {/* Summary Card */}
      <Card className="border-orange-500/50 bg-orange-500/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            {t('patterns.issuesDetected', 'Suspicious Patterns Detected')}
          </CardTitle>
          <CardDescription>
            {t('patterns.issuesCount', {
              count: detectedPatterns.length,
              defaultValue: `Found ${detectedPatterns.length} potential issues that may require attention.`,
            })}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Individual Pattern Cards */}
      {detectedPatterns.map((pattern, index) => {
        const Icon = getPatternIcon(pattern.type);
        const SeverityIcon = getSeverityIcon(pattern.severity);
        const severityColors = getSeverityColors(pattern.severity);
        const badgeColor = getSeverityBadgeColor(pattern.severity);

        return (
          <Card key={`${pattern.type}-${index}`} className={cn(severityColors, 'border')}>
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="shrink-0 mt-0.5">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="text-base">{pattern.description}</CardTitle>
                    <Badge variant="outline" className={cn('gap-1 text-xs', badgeColor)}>
                      <SeverityIcon className="h-3 w-3" />
                      {pattern.severity.toUpperCase()}
                    </Badge>
                  </div>

                  {showDetails && (
                    <div className="space-y-2">
                      <CardDescription className="text-sm">{pattern.suggestion}</CardDescription>

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div>
                          {t('patterns.occurrences', 'Occurrences')}: {pattern.occurrences}
                        </div>
                        <div>
                          {t('patterns.affectedItems', 'Affected items')}: {pattern.affectedItems.length}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardHeader>
          </Card>
        );
      })}
    </div>
  );
});
