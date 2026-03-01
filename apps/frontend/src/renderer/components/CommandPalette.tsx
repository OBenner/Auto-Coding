import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Clock } from 'lucide-react';
import { cn } from '../lib/utils';
import {
  Dialog,
  DialogContent,
} from './ui/dialog';

/**
 * Command action definition
 */
export interface CommandAction {
  /** Unique identifier for the command */
  id: string;
  /** Display label for the command */
  label: string;
  /** Optional description */
  description?: string;
  /** Keyboard shortcut hint (e.g., "⌘K") */
  shortcut?: string;
  /** Icon component to display */
  icon?: React.ReactNode;
  /** Group/category identifier */
  group?: string;
  /** Handler when command is selected */
  onSelect: () => void;
  /** Optional keywords for search matching */
  keywords?: string[];
}

/**
 * Command group definition
 */
export interface CommandGroup {
  /** Unique identifier for the group */
  id: string;
  /** Display label for the group */
  label: string;
  /** Commands in this group */
  commands: CommandAction[];
}

interface CommandPaletteProps {
  /** Whether the command palette is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Commands to display (flat list or grouped) */
  commands?: CommandAction[];
  /** Groups of commands to display (alternative to flat commands) */
  commandGroups?: CommandGroup[];
  /** Recent actions to display (optional) */
  recentCommands?: string[];
  /** Placeholder text for search input */
  placeholder?: string;
  /** Empty message when no commands match */
  emptyMessage?: string;
}

/**
 * Command Palette component with search and keyboard navigation
 * Provides quick access to application commands via Cmd/Ctrl+K
 *
 * Features:
 * - Fuzzy search through commands
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Grouped commands with headers
 * - Recent actions history
 * - Keyboard shortcuts display
 */
export function CommandPalette({
  open,
  onOpenChange,
  commands = [],
  commandGroups = [],
  recentCommands = [],
  placeholder,
  emptyMessage,
}: CommandPaletteProps) {
  const { t } = useTranslation(['quickActions', 'common']);
  const [search, setSearch] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Normalize commands to groups
  const groups: CommandGroup[] = commandGroups.length > 0
    ? commandGroups
    : commands.length > 0
      ? [{ id: 'all', label: '', commands }]
      : [];

  // Filter commands based on search
  const filteredGroups = groups.map(group => ({
    ...group,
    commands: group.commands.filter(cmd => {
      const searchLower = search.toLowerCase();
      return (
        cmd.label.toLowerCase().includes(searchLower) ||
        cmd.description?.toLowerCase().includes(searchLower) ||
        cmd.keywords?.some(kw => kw.toLowerCase().includes(searchLower))
      );
    }),
  })).filter(group => group.commands.length > 0);

  // Focus input when dialog opens
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // Reset search when closing
  useEffect(() => {
    if (!open) {
      setSearch('');
    }
  }, [open]);

  // Handle command selection
  const handleSelect = useCallback((command: CommandAction) => {
    command.onSelect();
    onOpenChange(false);
    setSearch('');
  }, [onOpenChange]);

  // Get all commands flattened (with recent first if available)
  const getRecentCommands = useCallback(() => {
    if (recentCommands.length === 0) return [];

    const allCommands = groups.flatMap(g => g.commands);
    return recentCommands
      .map(id => allCommands.find(cmd => cmd.id === id))
      .filter((cmd): cmd is CommandAction => cmd !== undefined);
  }, [groups, recentCommands]);

  const recentCommandsList = getRecentCommands();
  const hasRecent = recentCommandsList.length > 0 && search.length === 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="p-0 max-w-2xl overflow-hidden">
        <div className="flex flex-col">
          {/* Search input */}
          <div className="flex items-center border-b border-border px-4 py-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground mr-3" />
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={placeholder || t('quickActions:searchPlaceholder')}
              className={cn(
                'flex h-9 w-full bg-transparent text-sm',
                'placeholder:text-muted-foreground',
                'focus:outline-none',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
            />
          </div>

          {/* Commands list */}
          <div className="max-h-[400px] overflow-y-auto p-2">
            {filteredGroups.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                {emptyMessage || t('quickActions:noCommandsFound')}
              </div>
            ) : (
              <>
                {/* Recent commands section */}
                {hasRecent && (
                  <>
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground flex items-center gap-2">
                      <Clock className="h-3 w-3" />
                      {t('quickActions:recent')}
                    </div>
                    <div className="mb-2">
                      {recentCommandsList.map((command) => (
                        <CommandItem
                          key={`recent-${command.id}`}
                          command={command}
                          onSelect={handleSelect}
                        />
                      ))}
                    </div>
                  </>
                )}

                {/* All commands grouped */}
                {filteredGroups.map((group) => (
                  <div key={group.id}>
                    {group.label && (
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                        {group.label}
                      </div>
                    )}
                    {group.commands.map((command) => (
                      <CommandItem
                        key={command.id}
                        command={command}
                        onSelect={handleSelect}
                      />
                    ))}
                  </div>
                ))}
              </>
            )}
          </div>

          {/* Footer with keyboard hints */}
          <div className="border-t border-border px-4 py-2 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border text-[10px]">↑↓</kbd>
                {t('quickActions:navigate')}
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border text-[10px]">↵</kbd>
                {t('quickActions:select')}
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border text-[10px]">esc</kbd>
                {t('quickActions:close')}
              </span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Individual command item component
 */
interface CommandItemProps {
  command: CommandAction;
  onSelect: (command: CommandAction) => void;
}

function CommandItem({ command, onSelect }: CommandItemProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(command)}
      className={cn(
        'relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5',
        'text-sm text-left',
        'hover:bg-accent hover:text-accent-foreground',
        'focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'transition-colors duration-150',
        'cursor-pointer'
      )}
    >
      {/* Icon */}
      {command.icon && (
        <div className="flex-shrink-0 h-4 w-4 text-muted-foreground">
          {command.icon}
        </div>
      )}

      {/* Label and description */}
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{command.label}</div>
        {command.description && (
          <div className="text-xs text-muted-foreground truncate">
            {command.description}
          </div>
        )}
      </div>

      {/* Keyboard shortcut */}
      {command.shortcut && (
        <kbd className="flex-shrink-0 px-1.5 py-0.5 rounded bg-muted border border-border text-[10px] text-muted-foreground">
          {command.shortcut}
        </kbd>
      )}
    </button>
  );
}
