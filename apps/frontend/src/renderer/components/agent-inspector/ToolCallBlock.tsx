/**
 * ToolCallBlock Component
 *
 * Displays agent tool calls with syntax-highlighted input and output
 * for debugging and understanding agent actions.
 */

import { useState, useCallback, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, Wrench, Clock } from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { json } from '@codemirror/lang-json';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

/**
 * Agent tool call data structure
 */
export interface AgentToolCall {
  /** Unique identifier */
  id: string;
  /** Tool name (e.g., Read, Write, Bash, Edit) */
  name: string;
  /** Tool input parameters */
  input: Record<string, unknown>;
  /** Tool output/result (optional) */
  output?: Record<string, unknown> | string;
  /** Timestamp of when tool was called */
  timestamp: string;
  /** Current phase (planning, coding, validation, etc.) */
  phase?: string;
  /** Subtask context (optional) */
  subtask?: string;
  /** Duration in milliseconds (optional) */
  duration_ms?: number;
  /** Whether the tool call succeeded */
  success?: boolean;
  /** Error message if failed */
  error?: string;
}

interface ToolCallBlockProps {
  /** Tool call data to display */
  toolCall: AgentToolCall;
  /** Whether the details are expanded by default */
  defaultExpanded?: boolean;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Custom comparator for React.memo - only re-render when tool call changes
 */
function toolCallBlockPropsAreEqual(
  prevProps: ToolCallBlockProps,
  nextProps: ToolCallBlockProps
): boolean {
  const prevToolCall = prevProps.toolCall;
  const nextToolCall = nextProps.toolCall;

  // Fast path: same reference
  if (
    prevToolCall === nextToolCall &&
    prevProps.className === nextProps.className &&
    prevProps.defaultExpanded === nextProps.defaultExpanded
  ) {
    return true;
  }

  // Compare only the fields that affect rendering
  return (
    prevProps.className === nextProps.className &&
    prevProps.defaultExpanded === nextProps.defaultExpanded &&
    prevToolCall.id === nextToolCall.id &&
    prevToolCall.name === nextToolCall.name &&
    prevToolCall.timestamp === nextToolCall.timestamp &&
    prevToolCall.success === nextToolCall.success &&
    prevToolCall.phase === nextToolCall.phase &&
    prevToolCall.subtask === nextToolCall.subtask &&
    prevToolCall.error === nextToolCall.error &&
    prevToolCall.duration_ms === nextToolCall.duration_ms &&
    JSON.stringify(prevToolCall.input) === JSON.stringify(nextToolCall.input) &&
    JSON.stringify(prevToolCall.output) === JSON.stringify(nextToolCall.output)
  );
}

/** Shared CodeMirror basicSetup config for read-only JSON viewers */
const CODE_MIRROR_SETUP = {
  lineNumbers: true,
  highlightActiveLineGutter: false,
  highlightSpecialChars: true,
  foldGutter: true,
  syntaxHighlighting: true,
  bracketMatching: true,
  highlightActiveLine: false,
} as const;

/**
 * ToolCallBlock component with expandable input/output sections
 * Shows tool calls with syntax-highlighted JSON for debugging
 */
export const ToolCallBlock = memo(function ToolCallBlock({
  toolCall,
  defaultExpanded = false,
  className,
}: ToolCallBlockProps) {
  const { t } = useTranslation('agent-inspector');
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Memoize toggle callback to avoid recreating on every render
  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  // Detect dark mode from DOM - no memoization so it responds to theme changes
  const isDarkMode = typeof document !== 'undefined'
    ? document.documentElement.classList.contains('dark')
    : false;

  // Memoize status badge color
  const statusBadgeColor = useMemo(() => {
    if (toolCall.error) {
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    }
    if (toolCall.success === false) {
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    }
    return 'bg-green-500/20 text-green-400 border-green-500/30';
  }, [toolCall.error, toolCall.success]);

  // Memoize formatted input JSON
  const formattedInput = useMemo(() => {
    try {
      return JSON.stringify(toolCall.input, null, 2);
    } catch {
      return String(toolCall.input);
    }
  }, [toolCall.input]);

  // Memoize formatted output JSON
  const formattedOutput = useMemo(() => {
    if (!toolCall.output) return '';
    try {
      if (typeof toolCall.output === 'string') {
        return toolCall.output;
      }
      return JSON.stringify(toolCall.output, null, 2);
    } catch {
      return String(toolCall.output);
    }
  }, [toolCall.output]);

  // Memoize duration display
  const durationDisplay = useMemo(() => {
    if (!toolCall.duration_ms) return null;
    const ms = toolCall.duration_ms;
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  }, [toolCall.duration_ms]);

  return (
    <div className={cn('border border-warning/30 rounded-lg bg-warning/5 overflow-hidden', className)}>
      {/* Header - Always Visible */}
      <button
        type="button"
        onClick={toggleExpanded}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-warning/10 transition-colors text-left"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? t('collapseThought') : t('expandThought')}
      >
        {/* Icon */}
        <div className="shrink-0">
          <Wrench className="h-5 w-5 text-warning" />
        </div>

        {/* Title and Metadata */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium font-mono">{toolCall.name}</span>
            <Badge variant="outline" className={cn('gap-1 text-xs', statusBadgeColor)}>
              {toolCall.error ? t('toolStatus.error') : toolCall.success === false ? t('toolStatus.failed') : t('toolStatus.success')}
            </Badge>
            {toolCall.phase && (
              <Badge variant="outline" className="gap-1 text-xs text-muted-foreground">
                {toolCall.phase}
              </Badge>
            )}
          </div>
          {toolCall.subtask && (
            <div className="text-xs text-muted-foreground truncate">{toolCall.subtask}</div>
          )}
        </div>

        {/* Duration and Expand Icon */}
        <div className="shrink-0 flex items-center gap-2">
          {durationDisplay && (
            <span className="text-xs text-muted-foreground">{durationDisplay}</span>
          )}
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expandable Details */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-warning/20 pt-4">
          {/* Input Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-sm font-medium">{t('input')}</h4>
            </div>
            <div className="border border-border rounded-md overflow-hidden">
              <CodeMirror
                value={formattedInput}
                extensions={[json()]}
                theme={isDarkMode ? 'dark' : 'light'}
                editable={false}
                basicSetup={CODE_MIRROR_SETUP}
                className="text-xs"
                style={{
                  fontSize: '12px',
                }}
              />
            </div>
          </div>

          {/* Output Section */}
          {(toolCall.output || toolCall.error) && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h4 className="text-sm font-medium">{t('output')}</h4>
              </div>
              <div className="border border-border rounded-md overflow-hidden">
                {toolCall.error ? (
                  <div className="text-xs text-destructive bg-destructive/10 p-3 font-mono whitespace-pre-wrap">
                    {toolCall.error}
                  </div>
                ) : (
                  <CodeMirror
                    value={formattedOutput}
                    extensions={typeof toolCall.output === 'string' ? [] : [json()]}
                    theme={isDarkMode ? 'dark' : 'light'}
                    editable={false}
                    basicSetup={{
                      lineNumbers: true,
                      highlightActiveLineGutter: false,
                      highlightSpecialChars: true,
                      foldGutter: true,
                      syntaxHighlighting: true,
                      bracketMatching: true,
                      highlightActiveLine: false,
                    }}
                    className="text-xs"
                    style={{
                      fontSize: '12px',
                    }}
                  />
                )}
              </div>
            </div>
          )}

          {/* Metadata Footer */}
          <div className="pt-2 border-t border-border">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{new Date(toolCall.timestamp).toLocaleString()}</span>
              </div>
              {durationDisplay && (
                <div>
                  {t('duration')}: {durationDisplay}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}, toolCallBlockPropsAreEqual);
