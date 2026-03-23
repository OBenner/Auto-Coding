/**
 * FilterPanel Component
 *
 * Provides filtering controls for agent inspector tool calls.
 * Allows users to filter tool calls by type using checkboxes.
 *
 * Features:
 * - Checkbox filters for common tool types (Read, Write, Bash, Edit, etc.)
 * - Select All / Clear All functionality
 * - Active filter count display
 * - Collapsible panel for compact view
 *
 * @example
 * ```tsx
 * <FilterPanel
 *   selectedToolTypes={['Read', 'Write']}
 *   onToolTypesChange={(types) => setSelectedToolTypes(types)}
 * />
 * ```
 */
import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Filter, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { cn } from '../../lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible';

/**
 * Common tool types used by agents
 */
const TOOL_TYPES = [
  'Read',
  'Write',
  'Edit',
  'Bash',
  'Grep',
  'Glob',
  'Agent',
  'AskUserQuestion',
  'WebSearch',
  'WebFetch',
] as const;

export type ToolType = typeof TOOL_TYPES[number];

/**
 * Props for the FilterPanel component
 */
interface FilterPanelProps {
  /** Currently selected tool types */
  selectedToolTypes: string[];
  /** Callback when selected tool types change */
  onToolTypesChange: (toolTypes: string[]) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * FilterPanel component for tool type filtering
 */
export function FilterPanel({
  selectedToolTypes,
  onToolTypesChange,
  className,
}: FilterPanelProps) {
  const { t } = useTranslation(['agent-inspector', 'common']);

  // Calculate active filter count
  const activeFilterCount = useMemo(() => {
    return selectedToolTypes.length;
  }, [selectedToolTypes.length]);

  // Handle checkbox toggle
  const handleToolTypeToggle = useCallback(
    (toolType: string) => {
      const isSelected = selectedToolTypes.includes(toolType);
      if (isSelected) {
        // Remove from selection
        onToolTypesChange(selectedToolTypes.filter((t) => t !== toolType));
      } else {
        // Add to selection
        onToolTypesChange([...selectedToolTypes, toolType]);
      }
    },
    [selectedToolTypes, onToolTypesChange]
  );

  // Handle select all
  const handleSelectAll = useCallback(() => {
    onToolTypesChange([...TOOL_TYPES]);
  }, [onToolTypesChange]);

  // Handle clear all
  const handleClearAll = useCallback(() => {
    onToolTypesChange([]);
  }, [onToolTypesChange]);

  // Check if all are selected
  const allSelected = useMemo(() => {
    return TOOL_TYPES.every((type) => selectedToolTypes.includes(type));
  }, [selectedToolTypes]);

  // Check if none are selected
  const noneSelected = useMemo(() => {
    return selectedToolTypes.length === 0;
  }, [selectedToolTypes.length]);

  return (
    <div className={cn('border-b border-border/50', className)}>
      <Collapsible defaultOpen={true}>
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 p-0 h-auto font-semibold hover:bg-transparent"
              >
                <span>{t('agent-inspector:filterByToolType')}</span>
                {activeFilterCount > 0 && (
                  <span className="ml-1 px-2 py-0.5 text-xs font-medium bg-primary text-primary-foreground rounded-full">
                    {activeFilterCount}
                  </span>
                )}
              </Button>
            </CollapsibleTrigger>
          </div>

          {/* Quick actions */}
          <div className="flex items-center gap-2">
            {!allSelected && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSelectAll}
                className="h-8 text-xs"
              >
                {t('common:actions.selectAll')}
              </Button>
            )}
            {!noneSelected && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearAll}
                className="h-8 text-xs"
              >
                <X className="h-3 w-3 mr-1" />
                {t('agent-inspector:clearFilters')}
              </Button>
            )}
          </div>
        </div>

        <CollapsibleContent>
          <div className="px-6 pb-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {TOOL_TYPES.map((toolType) => {
                const isChecked = selectedToolTypes.includes(toolType);
                const id = `tool-type-${toolType}`;

                return (
                  <div key={toolType} className="flex items-center space-x-2">
                    <Checkbox
                      id={id}
                      checked={isChecked}
                      onCheckedChange={() => handleToolTypeToggle(toolType)}
                      aria-label={`Filter by ${toolType} tool calls`}
                    />
                    <Label
                      htmlFor={id}
                      className="text-sm font-normal cursor-pointer select-none"
                    >
                      {toolType}
                    </Label>
                  </div>
                );
              })}
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
