import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../ui/collapsible';
import { cn } from '../../lib/utils';

export interface ExplainMoreSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
}

/**
 * ExplainMoreSection Component
 *
 * Expandable section for detailed explanations in the tutorial wizard.
 * Provides progressive disclosure for users who want to learn more
 * about what's happening in each phase.
 *
 * Features:
 * - Collapsible content with chevron indicator
 * - Supports controlled and uncontrolled state
 * - Consistent styling with tutorial design
 * - Accessible keyboard navigation
 *
 * @example
 * ```tsx
 * <ExplainMoreSection title="What is a spec?">
 *   <p>A spec is a detailed description of what the agent will build...</p>
 * </ExplainMoreSection>
 * ```
 */
export function ExplainMoreSection({
  title,
  children,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  className,
}: ExplainMoreSectionProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setIsOpen = onOpenChange || setInternalOpen;

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn('border rounded-lg bg-card', className)}
    >
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="w-full p-3 flex items-center gap-2 text-sm font-medium text-foreground hover:bg-muted/30 transition-colors rounded-lg"
        >
          <div className="shrink-0">
            {isOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
          <span>{title}</span>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="px-3 pb-3 pt-1 text-sm text-muted-foreground leading-relaxed space-y-2">
          {children}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
